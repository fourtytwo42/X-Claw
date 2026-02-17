import json
import pathlib
import sys
import unittest
from unittest import mock

SKILL_SCRIPTS = pathlib.Path("skills/xclaw-agent/scripts").resolve()
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import xclaw_agent_skill as skill  # noqa: E402


class X402SkillWrapperTests(unittest.TestCase):
    def _capture(self, argv):
        with mock.patch.object(skill, "_print_json") as print_json:
            code = skill.main(argv)
            payload = None
            if print_json.call_args:
                payload = print_json.call_args.args[0]
        return code, payload

    def test_request_x402_payment_calls_hosted_receive_request(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(["xclaw_agent_skill.py", "request-x402-payment"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "x402",
                "receive-request",
                "--network",
                "base_sepolia",
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "0.01",
                "--asset-kind",
                "native",
                "--json",
            ]
        )

    def test_x402_pay_decide_rejects_invalid_decision(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "x402-pay-decide", "xfr_1", "maybe"])
        self.assertEqual(code, 2)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_x402_networks_delegates_to_runtime(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(["xclaw_agent_skill.py", "x402-networks"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["x402", "networks", "--json"])

if __name__ == "__main__":
    unittest.main()
