import pathlib
import sys
import unittest
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.solana_rpc_client import (  # noqa: E402
    SolanaRpcClientError,
    rpc_post,
    select_rpc_endpoint,
)


class SolanaRpcClientTests(unittest.TestCase):
    def test_select_rpc_endpoint_prefers_healthy_primary(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "XCLAW_SOLANA_RPC_PROVIDER_SOLANA_DEVNET": "standard",
                "XCLAW_SOLANA_RPC_URL_SOLANA_DEVNET": "https://primary.example",
                "XCLAW_SOLANA_RPC_FALLBACK_URL_SOLANA_DEVNET": "https://fallback.example",
            },
            clear=False,
        ), mock.patch(
            "xclaw_agent.solana_rpc_client.get_chain",
            return_value={"chainKey": "solana_devnet", "family": "solana", "rpc": {"primary": "https://rpc.example"}},
        ), mock.patch(
            "urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"jsonrpc":"2.0","id":1,"result":"ok"}'
            selected = select_rpc_endpoint("solana_devnet")
        self.assertEqual(selected.endpoint, "https://primary.example")

    def test_rpc_post_falls_back_to_second_candidate(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "XCLAW_SOLANA_RPC_PROVIDER_SOLANA_DEVNET": "standard",
                "XCLAW_SOLANA_RPC_URL_SOLANA_DEVNET": "https://primary.example",
                "XCLAW_SOLANA_RPC_FALLBACK_URL_SOLANA_DEVNET": "https://fallback.example",
            },
            clear=False,
        ), mock.patch(
            "xclaw_agent.solana_rpc_client.get_chain",
            return_value={"chainKey": "solana_devnet", "family": "solana", "rpc": {"primary": "https://rpc.example"}},
        ), mock.patch(
            "urllib.request.urlopen"
        ) as urlopen:
            def _response(payload: bytes):
                handle = mock.Mock()
                handle.read.return_value = payload
                return handle

            http_error = Exception("primary down")
            urlopen.side_effect = [
                http_error,
                mock.Mock(__enter__=mock.Mock(return_value=_response(b'{"jsonrpc":"2.0","id":1,"result":{"value":123}}')), __exit__=mock.Mock(return_value=False)),
            ]
            result = rpc_post("getBalance", ["addr"], chain_key="solana_devnet")
        self.assertEqual(result, {"value": 123})

    def test_rpc_post_falls_back_to_server_proxy_when_public_candidates_fail(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
                "XCLAW_AGENT_API_KEY": "xak_test",
                "XCLAW_SOLANA_RPC_URL_SOLANA_DEVNET": "https://primary.example",
                "XCLAW_SOLANA_RPC_FALLBACK_URL_SOLANA_DEVNET": "https://fallback.example",
            },
            clear=False,
        ), mock.patch(
            "xclaw_agent.solana_rpc_client.get_chain",
            return_value={"chainKey": "solana_devnet", "family": "solana", "rpc": {"primary": "https://rpc.example"}},
        ), mock.patch(
            "urllib.request.urlopen"
        ) as urlopen:

            def _fake_urlopen(req, timeout=20.0):  # type: ignore[override]
                url = str(getattr(req, "full_url", "") or getattr(req, "fullurl", "") or "")
                if url == "https://primary.example":
                    raise Exception("primary down")
                if url == "https://fallback.example":
                    raise Exception("fallback down")
                if url == "https://xclaw.trade/api/v1/agent/solana/rpc":
                    handle = mock.Mock()
                    handle.read.return_value = b'{"ok":true,"providerUsed":"tatum_fallback","result":{"value":321}}'
                    return mock.Mock(__enter__=mock.Mock(return_value=handle), __exit__=mock.Mock(return_value=False))
                raise AssertionError(f"Unexpected URL {url}")

            urlopen.side_effect = _fake_urlopen
            result = rpc_post("getBalance", ["addr"], chain_key="solana_devnet")
        self.assertEqual(result, {"value": 321})

    def test_rpc_post_without_proxy_context_returns_direct_rpc_error(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "XCLAW_SOLANA_RPC_URL_SOLANA_DEVNET": "https://primary.example",
                "XCLAW_SOLANA_RPC_FALLBACK_URL_SOLANA_DEVNET": "https://fallback.example",
            },
            clear=False,
        ), mock.patch(
            "xclaw_agent.solana_rpc_client.get_chain",
            return_value={"chainKey": "solana_devnet", "family": "solana", "rpc": {"primary": "https://rpc.example"}},
        ), mock.patch(
            "urllib.request.urlopen",
            side_effect=Exception("public rpc down"),
        ):
            with self.assertRaises(SolanaRpcClientError) as ctx:
                rpc_post("getBalance", ["addr"], chain_key="solana_devnet")
        self.assertIn(ctx.exception.code, {"rpc_unavailable", "chain_config_invalid"})


if __name__ == "__main__":
    unittest.main()
