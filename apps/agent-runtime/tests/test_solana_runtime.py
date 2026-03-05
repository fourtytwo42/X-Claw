import io
import json
import pathlib
import sys
import unittest
from unittest import mock
import urllib.error

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import solana_runtime  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class SolanaRuntimeTests(unittest.TestCase):
    def test_jupiter_quote_retries_transport_error_then_succeeds(self) -> None:
        def _urlopen_side_effect(req, timeout=0):  # type: ignore[no-untyped-def]
            if _urlopen_side_effect.calls == 0:
                _urlopen_side_effect.calls += 1
                raise urllib.error.URLError("timeout")
            return _FakeResponse({"outAmount": "12345", "routePlan": []})

        _urlopen_side_effect.calls = 0

        with mock.patch.object(solana_runtime, "is_solana_address", return_value=True), mock.patch.object(
            solana_runtime.time, "sleep"
        ) as sleep_mock, mock.patch(
            "urllib.request.urlopen", side_effect=_urlopen_side_effect
        ):
            quote = solana_runtime.jupiter_quote(
                chain_key="solana_mainnet_beta",
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount_units="7000000",
                slippage_bps=100,
            )

        self.assertEqual(quote.amount_out_units, "12345")
        self.assertEqual(quote.route_kind, "jupiter_route")
        sleep_mock.assert_called_once()

    def test_jupiter_quote_non_retryable_http_fails_closed(self) -> None:
        http_error = urllib.error.HTTPError(
            "https://quote-api.jup.ag/v6/quote",
            400,
            "Bad Request",
            None,
            io.BytesIO(b'{"error":"invalid request"}'),
        )
        with mock.patch.object(solana_runtime, "is_solana_address", return_value=True), mock.patch(
            "urllib.request.urlopen", side_effect=http_error
        ):
            with self.assertRaises(solana_runtime.SolanaRuntimeError) as ctx:
                solana_runtime.jupiter_quote(
                    chain_key="solana_mainnet_beta",
                    input_mint="So11111111111111111111111111111111111111112",
                    output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    amount_units="7000000",
                    slippage_bps=100,
                )

        self.assertEqual(ctx.exception.code, "rpc_unavailable")
        self.assertEqual(ctx.exception.details.get("status"), 400)
        self.assertEqual(ctx.exception.details.get("retryable"), False)

    def test_jupiter_quote_retry_exhaustion_reports_diagnostics(self) -> None:
        def _http_503(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise urllib.error.HTTPError(
                "https://quote-api.jup.ag/v6/quote",
                503,
                "Service Unavailable",
                None,
                io.BytesIO(b'{"error":"upstream unavailable"}'),
            )

        with mock.patch.object(solana_runtime, "is_solana_address", return_value=True), mock.patch.dict(
            solana_runtime.os.environ, {"XCLAW_JUPITER_QUOTE_MAX_ATTEMPTS": "3"}, clear=False
        ), mock.patch.object(solana_runtime.time, "sleep"), mock.patch(
            "urllib.request.urlopen", side_effect=_http_503
        ):
            with self.assertRaises(solana_runtime.SolanaRuntimeError) as ctx:
                solana_runtime.jupiter_quote(
                    chain_key="solana_mainnet_beta",
                    input_mint="So11111111111111111111111111111111111111112",
                    output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    amount_units="7000000",
                    slippage_bps=100,
                )

        self.assertEqual(ctx.exception.code, "rpc_unavailable")
        self.assertEqual(ctx.exception.details.get("retryExhausted"), True)
        self.assertEqual(ctx.exception.details.get("attempts"), 3)
        self.assertEqual(ctx.exception.details.get("lastStatus"), 503)


if __name__ == "__main__":
    unittest.main()
