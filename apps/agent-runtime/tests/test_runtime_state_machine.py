import pathlib
import sys
import unittest
from types import SimpleNamespace

RUNTIME_ROOT = pathlib.Path('apps/agent-runtime').resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.runtime import errors as runtime_errors  # noqa: E402
from xclaw_agent.runtime import state_machine as runtime_state_machine  # noqa: E402


class RuntimeStateMachineTests(unittest.TestCase):
    def test_run_json_command_parses_nested_payload(self) -> None:
        args = SimpleNamespace()

        def nested(_args):
            print('{"ok":true,"code":"ok","value":7}')
            return 0

        code, payload = runtime_state_machine.run_json_command(
            nested,
            args,
            fallback_payload={"ok": False, "code": "missing"},
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['value'], 7)

    def test_emit_prompt_cleanup_result_returns_failure_shape(self) -> None:
        captured = {}
        rt = SimpleNamespace(
            _clear_telegram_approval_buttons=lambda subject_type, subject_id: {
                'ok': False,
                'code': 'approval_prompt_cleanup_failed',
                'promptCleanup': {'subjectType': subject_type, 'subjectId': subject_id},
            },
            ok=lambda *args, **kwargs: ('ok', args, kwargs),
            fail=lambda code, message, action_hint=None, details=None, exit_code=1: captured.update(
                code=code,
                message=message,
                action_hint=action_hint,
                details=details,
                exit_code=exit_code,
            ) or exit_code,
        )
        exit_code = runtime_state_machine.emit_prompt_cleanup_result(
            rt,
            subject_type='trade',
            subject_id='trd_1',
            success_message='ok',
            failure_message='failed',
            failure_hint='retry',
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(captured['code'], 'approval_prompt_cleanup_failed')
        self.assertEqual(captured['details']['subjectId'], 'trd_1')

    def test_limit_order_failure_details_extracts_known_code(self) -> None:
        payload = runtime_state_machine.limit_order_failure_details(Exception('chain_config_invalid: bad rpc'))
        self.assertEqual(payload['reasonCode'], 'chain_config_invalid')
        self.assertEqual(payload['reasonMessage'], 'chain_config_invalid: bad rpc')

    def test_ensure_real_mode_rejects_mock(self) -> None:
        with self.assertRaises(runtime_errors.RuntimeCommandFailure) as ctx:
            runtime_state_machine.ensure_real_mode('mock', chain='base_sepolia')
        self.assertEqual(ctx.exception.code, 'unsupported_mode')
        self.assertEqual(ctx.exception.details['supportedMode'], 'real')

    def test_liquidity_status_helpers_classify_terminal_and_in_progress(self) -> None:
        self.assertTrue(runtime_state_machine.is_liquidity_terminal_status('filled'))
        self.assertTrue(runtime_state_machine.is_liquidity_in_progress_status('verifying'))
        self.assertFalse(runtime_state_machine.is_liquidity_terminal_status('approved'))


if __name__ == '__main__':
    unittest.main()
