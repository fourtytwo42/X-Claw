import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402


class TrackedRuntimeTests(unittest.TestCase):
    def _run(self, fn, args: SimpleNamespace):
        buf = StringIO()
        with redirect_stdout(buf):
            code = fn(args)
        payload = json.loads(buf.getvalue().strip())
        return code, payload

    def test_tracked_list_success(self) -> None:
        with mock.patch.object(cli, "_api_request", return_value=(200, {"items": [{"trackedAgentId": "ag_1"}]})):
            code, payload = self._run(cli.cmd_tracked_list, SimpleNamespace(chain="base_sepolia", json=True))
        self.assertEqual(code, 0)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("count"), 1)

    def test_tracked_trades_invalid_limit(self) -> None:
        code, payload = self._run(cli.cmd_tracked_trades, SimpleNamespace(chain="base_sepolia", limit="abc", agent=None, json=True))
        self.assertEqual(code, 2)
        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_tracked_trades_success_with_filter(self) -> None:
        with mock.patch.object(cli, "_api_request", return_value=(200, {"items": [{"tradeId": "trd_1"}]})):
            code, payload = self._run(
                cli.cmd_tracked_trades,
                SimpleNamespace(chain="base_sepolia", limit="20", agent="ag_x", json=True),
            )
        self.assertEqual(code, 0)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("count"), 1)


if __name__ == "__main__":
    unittest.main()
