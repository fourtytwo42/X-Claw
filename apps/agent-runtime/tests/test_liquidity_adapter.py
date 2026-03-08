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
        self.assertEqual(adapter.protocol_family, "position_manager_v3")

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
        self.assertEqual(adapter.protocol_family, "position_manager_v3")

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

    def test_resolve_solana_raydium_clmm_v3(self) -> None:
        adapter = build_liquidity_adapter_for_request("solana_devnet", "raydium_clmm", "v3")
        self.assertEqual(adapter.protocol_family, "raydium_clmm")
        self.assertEqual(adapter.dex, "raydium_clmm")
        self.assertTrue(isinstance(adapter.adapter_metadata, dict))
        self.assertTrue(bool((adapter.adapter_metadata or {}).get("programIds")))
        self.assertTrue(adapter.supports_operation("increase"))
        self.assertTrue(adapter.supports_operation("claim_fees"))
        self.assertTrue(adapter.supports_operation("claim_rewards"))
        self.assertTrue(adapter.supports_operation("migrate"))

    def test_solana_mainnet_advanced_ops_enabled(self) -> None:
        adapter = build_liquidity_adapter_for_request("solana_mainnet_beta", "raydium_clmm", "v3")
        self.assertTrue(adapter.supports_operation("increase"))
        self.assertTrue(adapter.supports_operation("claim_fees"))
        self.assertTrue(adapter.supports_operation("claim_rewards"))
        self.assertTrue(adapter.supports_operation("migrate"))

    def test_reject_local_clmm_on_non_localnet(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter("solana_devnet", "local_clmm", "local_clmm", position_type="v3")

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

    def test_v3_build_increase_plan_uses_position_manager_family(self) -> None:
        adapter = AmmV3LiquidityAdapter(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            protocol_family="position_manager_v3",
            position_type="v3",
            position_manager="0x" + "44" * 20,
            capabilities={"increase": True},
            operations={"increase": {"method": "increaseLiquidity"}},
        )
        plan = adapter.build_increase_plan(
            {
                "positionId": "123",
                "tokenA": "0x" + "11" * 20,
                "tokenB": "0x" + "22" * 20,
                "amountAUnits": "100",
                "amountBUnits": "200",
                "minAmountAUnits": "99",
                "minAmountBUnits": "198",
                "deadline": "123456",
            },
            "0x" + "33" * 20,
            build_calldata=lambda signature, args: f"{signature}:{args[0]}",
        )
        self.assertEqual(plan.execution_family, "position_manager_v3")
        self.assertEqual(plan.execution_adapter, "uniswap_v3")
        self.assertEqual(plan.route_kind, "position_manager")
        self.assertEqual(len(plan.approvals), 2)

    def test_v3_build_remove_plan_uses_position_manager_family(self) -> None:
        adapter = AmmV3LiquidityAdapter(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            protocol_family="position_manager_v3",
            position_type="v3",
            position_manager="0x" + "44" * 20,
            capabilities={"remove": True},
            operations={"decrease": {"method": "decreaseLiquidity"}, "claimFees": {"method": "collect"}},
        )
        plan = adapter.build_remove_plan(
            {
                "positionId": "123",
                "liquidityUnits": "1000",
                "minAmountAUnits": "0",
                "minAmountBUnits": "0",
                "deadline": "123456",
            },
            "0x" + "33" * 20,
            build_calldata=lambda signature, args: f"{signature}:{args[0]}",
        )
        self.assertEqual(plan.execution_family, "position_manager_v3")
        self.assertEqual(plan.execution_adapter, "uniswap_v3")
        self.assertEqual(plan.route_kind, "position_manager")
        self.assertEqual(len(plan.calls), 2)

    def test_v3_claim_rewards_requires_reward_contracts(self) -> None:
        adapter = AmmV3LiquidityAdapter(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            protocol_family="position_manager_v3",
            position_type="v3",
            position_manager="0x" + "44" * 20,
            capabilities={"claimRewards": True},
            operations={"claimRewards": {"method": "claimRewards(uint256,address[])", "rewardContracts": []}},
        )
        with self.assertRaises(ValueError):
            adapter.build_claim_rewards_plan(
                {"positionId": "123"},
                "0x" + "33" * 20,
                build_calldata=lambda signature, args: f"{signature}:{args}",
            )

    def test_v3_migrate_builds_without_request_calls(self) -> None:
        adapter = AmmV3LiquidityAdapter(
            chain="ethereum_sepolia",
            dex="uniswap_v3",
            protocol_family="position_manager_v3",
            position_type="v3",
            position_manager="0x" + "44" * 20,
            capabilities={"migrate": True},
            operations={"migrate": {"method": "multicall", "targetAdapterKey": "uniswap_v3"}},
        )
        plan = adapter.build_migrate_plan(
            {"positionId": "123", "liquidityUnits": "500", "minAmountAUnits": "0", "minAmountBUnits": "0", "deadline": "123456"},
            "0x" + "33" * 20,
            build_calldata=lambda signature, args: f"{signature}:{args[0] if args else ''}",
        )
        self.assertEqual(plan.execution_family, "position_manager_v3")
        self.assertEqual(plan.route_kind, "position_manager")
        self.assertEqual(plan.details.get("migrationMode"), "withdraw_only")
        self.assertEqual(len(plan.calls), 2)


if __name__ == "__main__":
    unittest.main()
