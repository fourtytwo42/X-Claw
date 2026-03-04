import pathlib
import sys
import tempfile
import unittest
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import solana_liquidity_local as local_liq  # noqa: E402


class SolanaLiquidityLocalTests(unittest.TestCase):
    def test_increase_claim_and_migrate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            state_path = pathlib.Path(td) / "solana_local_liquidity_positions.json"
            with mock.patch.object(local_liq, "_STATE_FILE", state_path):
                created = local_liq.create_position(
                    chain="solana_localnet",
                    dex="local_clmm",
                    owner="Owner1111111111111111111111111111111111",
                    token_a="So11111111111111111111111111111111111111112",
                    token_b="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    amount_a="10",
                    amount_b="20",
                    details={},
                )
                position_id = str(created.get("positionId") or "")
                self.assertTrue(position_id.startswith("solpos_"))

                increased = local_liq.increase_position(
                    chain="solana_localnet",
                    dex="local_clmm",
                    owner="Owner1111111111111111111111111111111111",
                    position_id=position_id,
                    amount_a="1",
                    amount_b="2",
                )
                self.assertEqual(str(increased.get("amountATotal")), "11")
                self.assertEqual(str(increased.get("amountBTotal")), "22")

                claimed = local_liq.claim_rewards(
                    chain="solana_localnet",
                    dex="local_clmm",
                    owner="Owner1111111111111111111111111111111111",
                    position_id=position_id,
                    reward_contracts=["LOCAL_REWARD_PROGRAM"],
                )
                self.assertTrue(str(claimed.get("txHash")).startswith("solsig_"))

                migrated = local_liq.migrate_position(
                    chain="solana_localnet",
                    dex="local_clmm",
                    owner="Owner1111111111111111111111111111111111",
                    position_id=position_id,
                    target_dex="local_clmm",
                    recreate=False,
                )
                self.assertEqual(str(migrated.get("migrationMode")), "withdraw_only")


if __name__ == "__main__":
    unittest.main()
