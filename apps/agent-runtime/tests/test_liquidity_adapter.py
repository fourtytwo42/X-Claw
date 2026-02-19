import pathlib
import sys
import unittest
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.liquidity_adapter import (  # noqa: E402
    AmmV2LiquidityAdapter,
    AmmV3LiquidityAdapter,
    HederaHtsLiquidityAdapter,
    HederaSdkUnavailable,
    LiquidityAdapterError,
    UnsupportedLiquidityAdapter,
    build_liquidity_adapter,
    build_liquidity_adapter_for_request,
)


class LiquidityAdapterTests(unittest.TestCase):
    def test_build_selects_v2_default(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "uniswap_v2", "amm_v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)

    def test_build_selects_v3(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "uniswap_v3", "amm_v3", position_type="v3")
        self.assertIsInstance(adapter, AmmV3LiquidityAdapter)

    def test_build_selects_hedera_hts(self) -> None:
        adapter = build_liquidity_adapter("hedera_testnet", "hedera_hts", "hedera_hts")
        self.assertIsInstance(adapter, HederaHtsLiquidityAdapter)

    def test_hedera_adapter_fails_closed_without_sdk(self) -> None:
        adapter = HederaHtsLiquidityAdapter(chain="hedera_testnet", dex="hedera_hts", protocol_family="hedera_hts", position_type="v2")
        with mock.patch("builtins.__import__", side_effect=ModuleNotFoundError("no module named hedera")):
            with self.assertRaises(HederaSdkUnavailable):
                adapter.quote_add({"amountA": "1", "amountB": "1", "slippageBps": 100})

    def test_resolve_adapter_from_chain_config(self) -> None:
        adapter = build_liquidity_adapter_for_request("base_sepolia", "aerodrome", "v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)
        self.assertEqual(adapter.protocol_family, "amm_v2")

    def test_resolve_v3_without_explicit_dex(self) -> None:
        adapter = build_liquidity_adapter_for_request("base_sepolia", "", "v3")
        self.assertIsInstance(adapter, AmmV3LiquidityAdapter)

    def test_resolve_rejects_v3_on_v2_only_adapter(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter_for_request("base_sepolia", "aerodrome", "v3")

    def test_resolve_rejects_disabled_protocol(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter_for_request("kite_ai_testnet", "tesseract_univ3", "v3")

    def test_quote_add_rejects_invalid_amount(self) -> None:
        adapter = AmmV2LiquidityAdapter(chain="base_sepolia", dex="aerodrome", protocol_family="amm_v2", position_type="v2")
        with self.assertRaises(LiquidityAdapterError):
            adapter.quote_add({"amountA": "0", "amountB": "1", "slippageBps": 100})


if __name__ == "__main__":
    unittest.main()
