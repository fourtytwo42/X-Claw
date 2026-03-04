import pathlib
import sys
import unittest

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.liquidity_adapter import (  # noqa: E402
    AmmV2LiquidityAdapter,
    AmmV3LiquidityAdapter,
    LiquidityAdapterError,
    UnsupportedLiquidityAdapter,
    UnsupportedLiquidityOperation,
    build_liquidity_adapter,
    build_liquidity_adapter_for_request,
)


class LiquidityAdapterTests(unittest.TestCase):
    def test_build_selects_v2_adapter(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "aerodrome", "amm_v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)
        self.assertEqual(adapter.protocol_family, "amm_v2")

    def test_build_selects_v3_adapter(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "uniswap_v3", "amm_v3", position_type="v3")
        self.assertIsInstance(adapter, AmmV3LiquidityAdapter)
        self.assertEqual(adapter.position_type, "v3")

    def test_build_rejects_unknown_family(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter("base_sepolia", "mystery", "amm_v9")

    def test_resolve_adapter_from_chain_config(self) -> None:
        adapter = build_liquidity_adapter_for_request("base_sepolia", "aerodrome", "v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)
        self.assertEqual(adapter.dex, "aerodrome")

    def test_resolve_v3_without_explicit_dex(self) -> None:
        adapter = build_liquidity_adapter_for_request("base_sepolia", "", "v3")
        self.assertIsInstance(adapter, AmmV3LiquidityAdapter)
        self.assertEqual(adapter.protocol_family, "amm_v3")

    def test_resolve_rejects_v3_on_v2_only_adapter(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter_for_request("base_sepolia", "aerodrome", "v3")

    def test_resolve_rejects_disabled_protocol(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter_for_request("kite_ai_testnet", "tesseract_univ3", "v3")

    def test_resolve_uniswap_alias_to_v2(self) -> None:
        adapter = build_liquidity_adapter_for_request("ethereum_sepolia", "uniswap", "v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)
        self.assertEqual(adapter.dex, "uniswap_v2")

    def test_quote_add_rejects_invalid_amount(self) -> None:
        adapter = AmmV2LiquidityAdapter(chain="base_sepolia", dex="aerodrome", protocol_family="amm_v2", position_type="v2")
        with self.assertRaises(LiquidityAdapterError):
            adapter.quote_add({"amountA": "0", "amountB": "1", "slippageBps": 100})

    def test_quote_remove_requires_position_id(self) -> None:
        adapter = AmmV2LiquidityAdapter(chain="base_sepolia", dex="aerodrome", protocol_family="amm_v2", position_type="v2")
        with self.assertRaises(LiquidityAdapterError):
            adapter.quote_remove({"percent": 50})

    def test_claim_fees_fails_closed_for_amm_v2(self) -> None:
        adapter = AmmV2LiquidityAdapter(chain="base_sepolia", dex="aerodrome", protocol_family="amm_v2", position_type="v2")
        with self.assertRaises(UnsupportedLiquidityOperation):
            adapter.claim_fees({"positionId": "pos_1"})


if __name__ == "__main__":
    unittest.main()
