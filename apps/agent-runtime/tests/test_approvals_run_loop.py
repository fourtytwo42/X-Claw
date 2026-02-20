import argparse
import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402


class ApprovalsRunLoopTests(unittest.TestCase):
    def _run(self, fn):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fn()
        payload = json.loads(buf.getvalue().strip())
        return code, payload

    def test_wallet_signing_readiness_missing_passphrase(self) -> None:
        with mock.patch.object(
            cli,
            "load_wallet_store",
            return_value={"chains": {"base_sepolia": "wlt_1"}, "wallets": {"wlt_1": {"crypto": {}}}},
        ), mock.patch.dict(
            "os.environ", {"XCLAW_WALLET_PASSPHRASE": ""}, clear=False
        ):
            readiness = cli._runtime_wallet_signing_readiness("base_sepolia")
        self.assertFalse(readiness.get("walletSigningReady"))
        self.assertEqual(readiness.get("walletSigningReasonCode"), "wallet_passphrase_missing")

    def test_run_loop_once_emits_sync_summary(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", interval_ms=1500, once=True, json=True)
        with mock.patch.object(
            cli,
            "_runtime_wallet_signing_readiness",
            return_value={
                "walletSigningReady": True,
                "walletSigningReasonCode": None,
                "walletSigningCheckedAt": "2026-02-20T00:00:00Z",
            },
        ), mock.patch.object(
            cli, "_publish_runtime_signing_readiness", return_value=(200, {"ok": True})
        ), mock.patch.object(
            cli,
            "_run_approvals_sync_inline",
            return_value=(
                0,
                {
                    "ok": True,
                    "code": "ok",
                    "transferDecisionsChecked": 1,
                    "transferDecisionsApplied": 1,
                    "transferDecisionsFailed": 0,
                },
            ),
        ):
            code, payload = self._run(lambda: cli.cmd_approvals_run_loop(args))
        self.assertEqual(code, 0)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("transferDecisionsApplied"), 1)
        self.assertTrue(payload.get("walletSigningReady"))
        self.assertEqual(payload.get("readinessPublishStatus"), 200)

    def test_run_loop_retries_after_failure(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", interval_ms=1000, once=False, json=True)
        with mock.patch.object(
            cli,
            "_runtime_wallet_signing_readiness",
            return_value={
                "walletSigningReady": True,
                "walletSigningReasonCode": None,
                "walletSigningCheckedAt": "2026-02-20T00:00:00Z",
            },
        ), mock.patch.object(
            cli, "_publish_runtime_signing_readiness", return_value=(200, {"ok": True})
        ), mock.patch.object(
            cli,
            "_run_approvals_sync_inline",
            side_effect=[
                (1, {"ok": False, "code": "sync_failed"}),
                (0, {"ok": True, "code": "ok"}),
            ],
        ) as sync_mock, mock.patch.object(
            cli.time, "sleep", side_effect=[None, SystemExit("stop_loop")]
        ) as sleep_mock:
            with self.assertRaises(SystemExit):
                cli.cmd_approvals_run_loop(args)
        self.assertEqual(sync_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_args_list[0].args[0], 2.0)
        self.assertEqual(sleep_mock.call_args_list[1].args[0], 1.0)


if __name__ == "__main__":
    unittest.main()
