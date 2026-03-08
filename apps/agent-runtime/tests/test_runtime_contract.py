import pathlib
import sys
import unittest
from types import SimpleNamespace

RUNTIME_ROOT = pathlib.Path('apps/agent-runtime').resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.runtime import errors as runtime_errors  # noqa: E402
from xclaw_agent.runtime import preconditions as runtime_preconditions  # noqa: E402
from xclaw_agent.runtime import validators as runtime_validators  # noqa: E402


class RuntimeContractHelperTests(unittest.TestCase):
    def test_validate_recipient_evm_invalid(self) -> None:
        rt = SimpleNamespace(
            _is_solana_chain=lambda chain: False,
            is_solana_address=lambda value: False,
            is_hex_address=lambda value: False,
        )
        with self.assertRaises(runtime_errors.RuntimeCommandFailure) as ctx:
            runtime_validators.validate_recipient(rt, 'base_sepolia', 'bad')
        self.assertEqual(ctx.exception.code, 'invalid_input')
        self.assertEqual(ctx.exception.details.get('to'), 'bad')

    def test_validate_recipient_solana_invalid(self) -> None:
        rt = SimpleNamespace(
            _is_solana_chain=lambda chain: True,
            is_solana_address=lambda value: False,
            is_hex_address=lambda value: False,
        )
        with self.assertRaises(runtime_errors.RuntimeCommandFailure) as ctx:
            runtime_validators.validate_recipient(rt, 'solana_devnet', 'bad_sol')
        self.assertEqual(ctx.exception.code, 'invalid_input')
        self.assertEqual(ctx.exception.details.get('to'), 'bad_sol')

    def test_require_distinct_trade_assets_is_case_sensitive_for_solana(self) -> None:
        runtime_validators.require_distinct_trade_assets('AbC123', 'abc123', 'solana_devnet')

    def test_require_distinct_trade_assets_is_case_insensitive_for_evm(self) -> None:
        with self.assertRaises(runtime_errors.RuntimeCommandFailure) as ctx:
            runtime_validators.require_distinct_trade_assets('0xAbC', '0xabc', 'base_sepolia')
        self.assertEqual(ctx.exception.code, 'invalid_input')

    def test_require_real_mode_rejects_mock(self) -> None:
        with self.assertRaises(runtime_errors.RuntimeCommandFailure) as ctx:
            runtime_validators.require_real_mode('mock', chain='base_sepolia', details={'tradeId': 'trd_1'})
        self.assertEqual(ctx.exception.code, 'unsupported_mode')
        self.assertEqual(ctx.exception.details.get('tradeId'), 'trd_1')

    def test_prepare_transfer_flow_calls_shared_guards(self) -> None:
        calls = []

        def enforce(chain: str, amount_wei: int) -> None:
            calls.append(('enforce', chain, amount_wei))

        def evaluate(chain: str, recipient: str) -> dict[str, bool]:
            calls.append(('evaluate', chain, recipient))
            return {'allowed': True}

        rt = SimpleNamespace(
            _enforce_spend_preconditions=enforce,
            _evaluate_outbound_transfer_policy=evaluate,
        )
        result = runtime_preconditions.prepare_transfer_flow(rt, 'base_sepolia', 123, '0xabc')
        self.assertEqual(result, {'allowed': True})
        self.assertEqual(calls, [('enforce', 'base_sepolia', 123), ('evaluate', 'base_sepolia', '0xabc')])

    def test_ensure_trade_actionable_rejects_non_retryable_failed_trade(self) -> None:
        rt = SimpleNamespace(MAX_TRADE_RETRIES=3, RETRY_WINDOW_SEC=3600)
        with self.assertRaises(runtime_errors.RuntimeCommandFailure) as ctx:
            runtime_preconditions.ensure_trade_actionable(rt, trade_id='trd_1', status='failed', retry={'eligible': False})
        self.assertEqual(ctx.exception.code, 'policy_denied')
        self.assertEqual(ctx.exception.details.get('tradeId'), 'trd_1')

    def test_emit_failure_uses_cli_fail_shape(self) -> None:
        captured = {}

        def fail(code, message, action_hint=None, details=None, exit_code=1):
            captured.update(
                code=code,
                message=message,
                action_hint=action_hint,
                details=details,
                exit_code=exit_code,
            )
            return exit_code

        rt = SimpleNamespace(fail=fail)
        code = runtime_errors.emit_failure(rt, runtime_errors.invalid_input('bad input', 'retry', {'field': 'value'}))
        self.assertEqual(code, 2)
        self.assertEqual(captured['code'], 'invalid_input')
        self.assertEqual(captured['details'], {'field': 'value'})


if __name__ == '__main__':
    unittest.main()
