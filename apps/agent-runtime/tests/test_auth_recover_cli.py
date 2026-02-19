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


class AuthRecoverCliTests(unittest.TestCase):
    def _run(self, fn):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fn()
        payload = json.loads(buf.getvalue().strip())
        return code, payload

    def test_auth_recover_success_persists_without_leaking_key(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", json=True)
        with mock.patch.object(cli, "_require_api_base_url", return_value="https://xclaw.trade/api/v1"), mock.patch.object(
            cli, "_resolve_api_key", side_effect=cli.WalletStoreError("missing key")
        ), mock.patch.object(
            cli, "_recover_api_key_with_wallet_signature", return_value="xak1.ag_test.signed.payload"
        ), mock.patch.object(
            cli, "_resolve_agent_id", return_value="ag_test"
        ):
            code, payload = self._run(lambda: cli.cmd_auth_recover(args))
        self.assertEqual(code, 0)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("chain"), "hedera_testnet")
        self.assertEqual(payload.get("agentId"), "ag_test")
        self.assertNotIn("agentApiKey", payload)

    def test_auth_recover_failure_is_structured(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", json=True)
        with mock.patch.object(cli, "_require_api_base_url", return_value="https://xclaw.trade/api/v1"), mock.patch.object(
            cli, "_resolve_api_key", return_value="xak1.ag_test.signed.payload"
        ), mock.patch.object(
            cli, "_recover_api_key_with_wallet_signature", side_effect=cli.WalletStoreError("challenge failed")
        ):
            code, payload = self._run(lambda: cli.cmd_auth_recover(args))
        self.assertEqual(code, 1)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "auth_recovery_failed")


if __name__ == "__main__":
    unittest.main()
