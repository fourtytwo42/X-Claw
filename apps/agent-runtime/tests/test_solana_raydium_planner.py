import pathlib
import sys
import unittest
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import solana_raydium_planner as planner  # noqa: E402
from xclaw_agent.solana_runtime import SolanaRuntimeError  # noqa: E402


class SolanaRaydiumPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter_metadata = {
            "programIds": {"clmm": "CAMMCzo5YL8w4VFF8KVHrK22GGUQw1pV9akxb8qzVD3"},
            "poolRegistry": {
                "default": {
                    "poolId": "So11111111111111111111111111111111111111112",
                    "tokenA": "So11111111111111111111111111111111111111112",
                    "tokenB": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    "feeBps": 100,
                }
            },
            "operations": {
                "increase": {
                    "method": "increase_liquidity",
                    "accountsTemplate": [
                        {"pubkey": "$OWNER", "isSigner": True, "isWritable": True},
                        {"pubkey": "$POOL", "isSigner": False, "isWritable": True},
                    ],
                },
                "remove": {
                    "method": "decrease_liquidity",
                    "accountsTemplate": [
                        {"pubkey": "$OWNER", "isSigner": True, "isWritable": True},
                        {"pubkey": "$POOL", "isSigner": False, "isWritable": True},
                    ],
                },
                "claimFees": {
                    "method": "collect_fees",
                    "accountsTemplate": [
                        {"pubkey": "$OWNER", "isSigner": True, "isWritable": True},
                        {"pubkey": "$POOL", "isSigner": False, "isWritable": True},
                    ],
                },
                "claimRewards": {
                    "method": "collect_rewards",
                    "accountsTemplate": [
                        {"pubkey": "$OWNER", "isSigner": True, "isWritable": True},
                        {"pubkey": "$POOL", "isSigner": False, "isWritable": True},
                    ],
                },
                "migrate": {"method": "migrate_position"},
            },
        }

    def test_claim_rewards_requires_reward_contracts(self) -> None:
        request = {"poolId": "So11111111111111111111111111111111111111112", "positionId": "123"}
        with mock.patch.object(planner, "_ensure_pool_exists", return_value=None):
            with self.assertRaises(SolanaRuntimeError) as ctx:
                planner.build_execution_plan(
                    chain="solana_devnet",
                    rpc_url="https://api.devnet.solana.com",
                    owner="Owner1111111111111111111111111111111111",
                    adapter_metadata=self.adapter_metadata,
                    request=request,
                    operation_key="claim_rewards",
                )
        self.assertEqual(ctx.exception.code, "claim_rewards_not_configured")

    def test_migrate_requires_target_adapter(self) -> None:
        request = {"poolId": "So11111111111111111111111111111111111111112", "positionId": "123"}
        with mock.patch.object(planner, "_ensure_pool_exists", return_value=None):
            with self.assertRaises(SolanaRuntimeError) as ctx:
                planner.build_execution_plan(
                    chain="solana_devnet",
                    rpc_url="https://api.devnet.solana.com",
                    owner="Owner1111111111111111111111111111111111",
                    adapter_metadata=self.adapter_metadata,
                    request=request,
                    operation_key="migrate",
                )
        self.assertEqual(ctx.exception.code, "migration_target_not_configured")

    def test_increase_builds_instruction_plan(self) -> None:
        request = {
            "poolId": "So11111111111111111111111111111111111111112",
            "positionId": "123",
            "amountAUnits": "1000",
            "amountBUnits": "2000",
            "minAmountAUnits": "990",
            "minAmountBUnits": "1980",
        }
        with mock.patch.object(planner, "_ensure_pool_exists", return_value=None):
            plan = planner.build_execution_plan(
                chain="solana_devnet",
                rpc_url="https://api.devnet.solana.com",
                owner="Owner1111111111111111111111111111111111",
                adapter_metadata=self.adapter_metadata,
                request=request,
                operation_key="increase",
            )
        self.assertEqual(plan.details.get("operationKey"), "increase")
        self.assertEqual(len(plan.instructions), 1)
        self.assertEqual(plan.instructions[0].operation_key, "increase")


if __name__ == "__main__":
    unittest.main()
