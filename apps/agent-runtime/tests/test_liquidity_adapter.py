import pathlib
import sys
import unittest
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.liquidity_adapter import (
    AmmV2LiquidityAdapter,
    AmmV3LiquidityAdapter,
    HederaHtsLiquidityAdapter,
    HederaSdkUnavailable,
    build_liquidity_adapter,
)


class LiquidityAdapterTests(unittest.TestCase):
    def test_build_selects_v2_default(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "uniswap", "amm_v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)

    def test_build_selects_v3(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "uniswap", "amm_v3")
        self.assertIsInstance(adapter, AmmV3LiquidityAdapter)

    def test_build_selects_hedera_hts(self) -> None:
        adapter = build_liquidity_adapter("hedera_testnet", "saucerswap", "hedera_hts")
        self.assertIsInstance(adapter, HederaHtsLiquidityAdapter)

    def test_hedera_adapter_fails_closed_without_sdk(self) -> None:
        adapter = HederaHtsLiquidityAdapter(chain="hedera_testnet", dex="saucerswap", protocol_family="hedera_hts")
        with mock.patch("builtins.__import__", side_effect=ModuleNotFoundError("no module named hedera")):
            with self.assertRaises(HederaSdkUnavailable):
                adapter.quote_add({"amountA": "1", "amountB": "1"})


if __name__ == "__main__":
    unittest.main()
