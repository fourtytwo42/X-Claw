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
    def test_jupiter_base_urls_prefers_lite_api_by_default(self) -> None:
        urls = solana_runtime._jupiter_base_urls("solana_mainnet_beta")
        self.assertGreaterEqual(len(urls), 2)
        self.assertEqual(urls[0], "https://lite-api.jup.ag/swap/v1")
        self.assertIn("https://quote-api.jup.ag/v6", urls)

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
        self.assertGreaterEqual(int(ctx.exception.details.get("attempts") or 0), 3)
        self.assertEqual(ctx.exception.details.get("lastStatus"), 503)

    def test_jupiter_swap_prefers_quote_endpoint_before_default_candidates(self) -> None:
        called_urls: list[str] = []

        def _urlopen_side_effect(req, timeout=0):  # type: ignore[no-untyped-def]
            called_urls.append(str(getattr(req, "full_url", "")))
            raise urllib.error.URLError("dns failure")

        with mock.patch.object(solana_runtime, "_require_solana_dependencies"), mock.patch.object(
            solana_runtime, "is_solana_address", return_value=True
        ), mock.patch.dict(
            solana_runtime.os.environ, {"XCLAW_JUPITER_QUOTE_MAX_ATTEMPTS": "1"}, clear=False
        ), mock.patch.object(
            solana_runtime.time, "sleep"
        ), mock.patch(
            "urllib.request.urlopen", side_effect=_urlopen_side_effect
        ):
            with self.assertRaises(solana_runtime.SolanaRuntimeError) as ctx:
                solana_runtime.jupiter_execute_swap(
                    chain_key="solana_mainnet_beta",
                    rpc_url="http://localhost:8899",
                    private_key_bytes=b"\x00" * 64,
                    quote_payload={"routePlan": []},
                    user_address="ChcB9rcv6pFjFduThDckf6KN8eQdQAqUCHiSXSFFKSdA",
                    quote_endpoint="https://alt-api.jup.ag/swap/v1",
                )

        self.assertEqual(ctx.exception.code, "rpc_unavailable")
        self.assertEqual(ctx.exception.details.get("retryExhausted"), True)
        self.assertTrue(called_urls)
        self.assertTrue(called_urls[0].startswith("https://alt-api.jup.ag/swap/v1/swap"))
        self.assertTrue(any(url.startswith("https://lite-api.jup.ag/swap/v1/swap") for url in called_urls))


if __name__ == "__main__":
    unittest.main()
