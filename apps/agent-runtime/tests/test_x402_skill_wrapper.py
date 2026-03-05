import json
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

SKILL_SCRIPTS = pathlib.Path("skills/xclaw-agent/scripts").resolve()
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import xclaw_agent_skill as skill  # noqa: E402


class X402SkillWrapperTests(unittest.TestCase):
    _ENV = {
        "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
        "XCLAW_AGENT_API_KEY": "test-key",
        "XCLAW_DEFAULT_CHAIN": "base_sepolia",
    }

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

    def test_resolve_agent_binary_prefers_configured_runtime_bin(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = pathlib.Path(f.name)
        p.chmod(0o755)
        self.addCleanup(lambda: p.unlink(missing_ok=True))
        with mock.patch.dict(skill.os.environ, {"XCLAW_AGENT_RUNTIME_BIN": str(p)}, clear=False):
            resolved = skill._resolve_agent_binary()
        self.assertEqual(resolved, str(p))

    def test_resolve_agent_binary_falls_back_when_configured_bin_not_executable(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = pathlib.Path(f.name)
        p.chmod(0o644)
        self.addCleanup(lambda: p.unlink(missing_ok=True))
        with mock.patch.dict(skill.os.environ, {"XCLAW_AGENT_RUNTIME_BIN": str(p)}, clear=False):
            with mock.patch.object(skill.os, "access", return_value=False):
                with mock.patch.object(skill.shutil, "which", return_value="/usr/bin/xclaw-agent"):
                    resolved = skill._resolve_agent_binary()
        self.assertEqual(resolved, "/usr/bin/xclaw-agent")

    def test_request_x402_payment_rejects_positional_text(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "request-x402-payment", "please", "request", "$5", "usdc"])
        self.assertEqual(code, 2)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("code"), "invalid_input")
        self.assertIn("rejects positional text", str(payload.get("message")))

    def test_request_x402_payment_supports_explicit_flag_overrides(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(
                [
                    "xclaw_agent_skill.py",
                    "request-x402-payment",
                    "--network",
                    "base_sepolia",
                    "--facilitator",
                    "cdp",
                    "--amount-atomic",
                    "5000000",
                    "--asset-kind",
                    "token",
                    "--asset-symbol",
                    "USDC",
                    "--resource-description",
                    "Invoice #42",
                ]
            )
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
                "5000000",
                "--asset-kind",
                "token",
                "--json",
                "--asset-symbol",
                "USDC",
                "--resource-description",
                "Invoice #42",
            ]
        )

    def test_request_x402_payment_supports_solana_token_address(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(
                [
                    "xclaw_agent_skill.py",
                    "request-x402-payment",
                    "--network",
                    "solana_devnet",
                    "--facilitator",
                    "xclaw_hosted",
                    "--amount-atomic",
                    "1000000",
                    "--asset-kind",
                    "token",
                    "--asset-address",
                    "So11111111111111111111111111111111111111112",
                ]
            )
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "x402",
                "receive-request",
                "--network",
                "solana_devnet",
                "--facilitator",
                "xclaw_hosted",
                "--amount-atomic",
                "1000000",
                "--asset-kind",
                "token",
                "--json",
                "--asset-address",
                "So11111111111111111111111111111111111111112",
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

    def test_liquidity_positions_status_shorthand_routes_to_status_filter(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "liquidity-positions", "active"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["liquidity", "positions", "--chain", "base_sepolia", "--status", "active", "--json"])

    def test_liquidity_positions_with_dex_and_status_keeps_both_filters(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "liquidity-positions", "saucerswap", "active"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            ["liquidity", "positions", "--chain", "base_sepolia", "--dex", "saucerswap", "--status", "active", "--json"]
        )

    def test_liquidity_positions_open_alias_routes_to_active_status(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "liquidity-positions", "open"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["liquidity", "positions", "--chain", "base_sepolia", "--status", "active", "--json"])

    def test_version_emits_skill_metadata_without_runtime_call(self) -> None:
        expected = {
            "ok": True,
            "code": "skill_version",
            "skillScriptSha256": "abc123",
            "patchState": {"schemaVersion": 43, "lastError": None},
        }
        with mock.patch.object(skill, "_skill_version_payload", return_value=expected), mock.patch.object(
            skill, "_run_agent"
        ) as run_mock:
            code, payload = self._capture(["xclaw_agent_skill.py", "version"])
        self.assertEqual(code, 0)
        self.assertEqual(payload, expected)
        run_mock.assert_not_called()

    def test_tracked_list_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "tracked-list"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["tracked", "list", "--chain", "base_sepolia", "--json"])

    def test_resolve_active_chain_prefers_runtime_default_chain(self) -> None:
        runtime_payload = {"ok": True, "code": "ok", "chainKey": "ethereum_sepolia", "source": "state"}
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"), mock.patch.object(
                skill.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    args=["/usr/bin/xclaw-agent", "default-chain", "get", "--json"],
                    returncode=0,
                    stdout=json.dumps(runtime_payload),
                    stderr="",
                ),
            ):
                resolved = skill._resolve_active_chain()
        self.assertEqual(resolved, "ethereum_sepolia")

    def test_resolve_active_chain_falls_back_to_env_without_api_context(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            resolved = skill._resolve_active_chain()
        self.assertEqual(resolved, "base_sepolia")

    def test_tracked_trades_with_agent_and_limit(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "tracked-trades", "ag_test", "15"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["tracked", "trades", "--chain", "base_sepolia", "--json", "--agent", "ag_test", "--limit", "15"])

    def test_api_commands_accept_runtime_state_api_key_when_env_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = pathlib.Path(tmp_dir) / ".xclaw-agent"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "state.json").write_text(json.dumps({"agentApiKey": "state-key", "agentId": "ag_state"}), encoding="utf-8")
            env = {
                "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
                "XCLAW_DEFAULT_CHAIN": "base_sepolia",
                "HOME": tmp_dir,
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                    code = skill.main(["xclaw_agent_skill.py", "tracked-list"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["tracked", "list", "--chain", "base_sepolia", "--json"])

    def test_wallet_send_token_accepts_symbol_and_delegates(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(
                    [
                        "xclaw_agent_skill.py",
                        "wallet-send-token",
                        "USDC",
                        "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                        "10000000",
                    ]
                )
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "wallet",
                "send-token",
                "--token",
                "USDC",
                "--to",
                "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                "--amount-wei",
                "10000000",
                "--chain",
                "base_sepolia",
                "--json",
            ]
        )

    def test_trade_spot_uses_runtime_active_chain_when_chain_omitted(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="ethereum_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "trade-spot", "WETH", "USDC", "0.25", "100"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "trade",
                "spot",
                "--chain",
                "ethereum_sepolia",
                "--token-in",
                "WETH",
                "--token-out",
                "USDC",
                "--amount-in",
                "0.25",
                "--slippage-bps",
                "100",
                "--json",
            ]
        )

    def test_trade_spot_allows_explicit_chain_override(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "trade-spot", "WETH", "USDC", "0.25", "100", "ethereum_sepolia"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "trade",
                "spot",
                "--chain",
                "ethereum_sepolia",
                "--token-in",
                "WETH",
                "--token-out",
                "USDC",
                "--amount-in",
                "0.25",
                "--slippage-bps",
                "100",
                "--json",
            ]
        )

    def test_wallet_create_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-create"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "create", "--chain", "base_sepolia", "--json"])

    def test_wallet_wrap_native_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-wrap-native", "1"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "wrap-native", "--amount", "1", "--chain", "base_sepolia", "--json"])

    def test_wallet_track_token_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-track-token", "0x0000000000000000000000000000000000001549"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            ["wallet", "track-token", "--token", "0x0000000000000000000000000000000000001549", "--chain", "base_sepolia", "--json"]
        )

    def test_wallet_balance_allows_explicit_chain_override(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-balance", "ethereum_sepolia"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "balance", "--chain", "ethereum_sepolia", "--json"])

    def test_wallet_send_token_allows_explicit_chain_override(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(
                    [
                        "xclaw_agent_skill.py",
                        "wallet-send-token",
                        "USDC",
                        "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                        "10000000",
                        "ethereum_sepolia",
                    ]
                )
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "wallet",
                "send-token",
                "--token",
                "USDC",
                "--to",
                "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                "--amount-wei",
                "10000000",
                "--chain",
                "ethereum_sepolia",
                "--json",
            ]
        )

    def test_wallet_send_allows_solana_recipient_on_solana_chain(self) -> None:
        recipient = "So11111111111111111111111111111111111111112"
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-send", recipient, "1000", "solana_devnet"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "send", "--to", recipient, "--amount-wei", "1000", "--chain", "solana_devnet", "--json"])

    def test_wallet_send_rejects_solana_recipient_on_evm_chain(self) -> None:
        recipient = "So11111111111111111111111111111111111111112"
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            code, payload = self._capture(["xclaw_agent_skill.py", "wallet-send", recipient, "1000"])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_wallet_send_token_allows_solana_recipient_on_solana_chain(self) -> None:
        recipient = "So11111111111111111111111111111111111111112"
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-send-token", "USDC", recipient, "1000000", "solana_devnet"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            ["wallet", "send-token", "--token", "USDC", "--to", recipient, "--amount-wei", "1000000", "--chain", "solana_devnet", "--json"]
        )

    def test_wallet_send_token_rejects_invalid_solana_recipient(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            code, payload = self._capture(["xclaw_agent_skill.py", "wallet-send-token", "USDC", "bad_sol", "1000000", "solana_devnet"])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_wallet_token_balance_allows_solana_mint_on_solana_chain(self) -> None:
        mint = "So11111111111111111111111111111111111111112"
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-token-balance", mint, "solana_devnet"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "token-balance", "--token", mint, "--chain", "solana_devnet", "--json"])

    def test_wallet_track_token_allows_solana_mint_on_solana_chain(self) -> None:
        mint = "So11111111111111111111111111111111111111112"
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-track-token", mint, "solana_devnet"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "track-token", "--token", mint, "--chain", "solana_devnet", "--json"])

    def test_wallet_track_token_rejects_solana_mint_on_evm_chain(self) -> None:
        mint = "So11111111111111111111111111111111111111112"
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            code, payload = self._capture(["xclaw_agent_skill.py", "wallet-track-token", mint])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_wallet_untrack_token_allows_solana_mint_on_solana_chain(self) -> None:
        mint = "So11111111111111111111111111111111111111112"
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-untrack-token", mint, "solana_devnet"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "untrack-token", "--token", mint, "--chain", "solana_devnet", "--json"])

    def test_wallet_untrack_token_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-untrack-token", "0x0000000000000000000000000000000000001549"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            ["wallet", "untrack-token", "--token", "0x0000000000000000000000000000000000001549", "--chain", "base_sepolia", "--json"]
        )

    def test_wallet_tracked_tokens_delegates_to_runtime(self) -> None:
        with mock.patch.dict("os.environ", {"XCLAW_DEFAULT_CHAIN": "base_sepolia"}, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-tracked-tokens"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "tracked-tokens", "--chain", "base_sepolia", "--json"])

    def test_wallet_track_token_requires_address(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            code, payload = self._capture(["xclaw_agent_skill.py", "wallet-track-token"])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "usage")

    def test_dexscreener_search_returns_trimmed_pairs(self) -> None:
        payload = {
            "schemaVersion": "1.0.0",
            "pairs": [
                {
                    "chainId": "base",
                    "dexId": "aerodrome",
                    "pairAddress": "0xpair1",
                    "url": "https://dexscreener.com/base/0xpair1",
                    "baseToken": {"address": "0xbase1", "symbol": "SOL", "name": "Solana"},
                    "quoteToken": {"address": "0xquote1", "symbol": "USDC", "name": "USD Coin"},
                    "priceUsd": "100",
                    "liquidity": {"usd": 12345},
                    "volume": {"h24": 5000},
                    "txns": {"h24": {"buys": 12, "sells": 8}},
                },
                {
                    "chainId": "base",
                    "dexId": "uniswap",
                    "pairAddress": "0xpair2",
                    "url": "https://dexscreener.com/base/0xpair2",
                    "baseToken": {"address": "0xbase2", "symbol": "ETH", "name": "Ether"},
                    "quoteToken": {"address": "0xquote2", "symbol": "USDC", "name": "USD Coin"},
                    "priceUsd": "2500",
                    "liquidity": {"usd": 9999},
                    "volume": {"h24": 3333},
                    "txns": {"h24": {"buys": 20, "sells": 10}},
                },
            ],
        }
        with mock.patch.object(skill, "_fetch_dexscreener_json", return_value=(payload, None, 0)) as fetch_mock:
            code, result = self._capture(["xclaw_agent_skill.py", "dexscreener-search", "SOL/USDC", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(result.get("code"), "ok")
        self.assertEqual(result.get("source"), "dexscreener")
        self.assertEqual(result.get("pairCount"), 1)
        self.assertEqual(len(result.get("pairs") or []), 1)
        self.assertEqual((result.get("pairs") or [{}])[0].get("dexId"), "aerodrome")
        called_url = fetch_mock.call_args.args[0]
        self.assertIn("latest/dex/search", called_url)
        self.assertIn("q=SOL%2FUSDC", called_url)

    def test_dexscreener_search_requires_query(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "dexscreener-search", ""])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_dexscreener_top_sorts_by_liquidity_and_formats_numbers(self) -> None:
        payload = {
            "schemaVersion": "1.0.0",
            "pairs": [
                {
                    "chainId": "base",
                    "dexId": "lowliq",
                    "pairAddress": "0xpair-low",
                    "url": "https://dexscreener.com/base/0xpair-low",
                    "baseToken": {"address": "0xbase1", "symbol": "AAA", "name": "AAA"},
                    "quoteToken": {"address": "0xquote1", "symbol": "USDC", "name": "USD Coin"},
                    "priceUsd": "1.123456789",
                    "liquidity": {"usd": 999.1},
                    "volume": {"h24": 2222.987},
                },
                {
                    "chainId": "base",
                    "dexId": "highliq",
                    "pairAddress": "0xpair-high",
                    "url": "https://dexscreener.com/base/0xpair-high",
                    "baseToken": {"address": "0xbase2", "symbol": "BBB", "name": "BBB"},
                    "quoteToken": {"address": "0xquote2", "symbol": "USDC", "name": "USD Coin"},
                    "priceUsd": "2.987654321",
                    "liquidity": {"usd": 12345.6789},
                    "volume": {"h24": 4000.333},
                },
            ],
        }
        with mock.patch.object(skill, "_fetch_dexscreener_json", return_value=(payload, None, 0)):
            code, result = self._capture(["xclaw_agent_skill.py", "dexscreener-top", "base usdc", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(result.get("endpoint"), "top")
        self.assertEqual(result.get("sortBy"), "liquidityUsd_desc")
        pairs = result.get("pairs") or []
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0].get("dexId"), "highliq")
        self.assertEqual(pairs[0].get("liquidityUsd"), "12345.68")
        self.assertEqual(pairs[0].get("priceUsd"), "2.98765432")
        self.assertEqual(pairs[1].get("dexId"), "lowliq")
        self.assertEqual(pairs[1].get("liquidityUsd"), "999.10")

    def test_dexscreener_top_requires_query(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "dexscreener-top", ""])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_token_research_runs_search_and_drilldown(self) -> None:
        search_payload = {
            "pairs": [
                {
                    "chainId": "base",
                    "dexId": "aerodrome",
                    "pairAddress": "0xpair1",
                    "url": "https://dexscreener.com/base/0xpair1",
                    "baseToken": {"address": "0xbase1", "symbol": "AAA", "name": "Token AAA"},
                    "quoteToken": {"address": "0xquote1", "symbol": "USDC", "name": "USD Coin"},
                    "priceUsd": "1.5",
                    "liquidity": {"usd": 2000.01},
                    "volume": {"h24": 101.2},
                }
            ]
        }
        drill_payload = [
            {
                "chainId": "base",
                "dexId": "uniswap",
                "pairAddress": "0xpair2",
                "url": "https://dexscreener.com/base/0xpair2",
                "baseToken": {"address": "0xbase1", "symbol": "AAA", "name": "Token AAA"},
                "quoteToken": {"address": "0xquote2", "symbol": "WETH", "name": "Wrapped Ether"},
                "priceUsd": "1.6",
                "liquidity": {"usd": 1800.0},
                "volume": {"h24": 55.0},
            }
        ]
        with mock.patch.object(
            skill,
            "_fetch_dexscreener_json",
            side_effect=[(search_payload, None, 0), (drill_payload, None, 0)],
        ) as fetch_mock:
            code, payload = self._capture(["xclaw_agent_skill.py", "token-research", "AAA", "3"])
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("endpoint"), "token-research")
        self.assertEqual((payload.get("primaryToken") or {}).get("symbol"), "AAA")
        self.assertEqual(len(payload.get("topPairs") or []), 1)
        self.assertEqual(len(payload.get("drilldownPairs") or []), 1)
        self.assertEqual(fetch_mock.call_count, 2)

    def test_token_research_requires_query(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "token-research", ""])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_token_research_handles_no_results(self) -> None:
        with mock.patch.object(skill, "_fetch_dexscreener_json", return_value=({"pairs": []}, None, 0)):
            code, payload = self._capture(["xclaw_agent_skill.py", "token-research", "nonexistent"])
        self.assertEqual(code, 1)
        self.assertEqual(payload.get("code"), "dexscreener_no_results")

    def test_dexscreener_token_pairs_rejects_bad_chain_id(self) -> None:
        code, payload = self._capture(["xclaw_agent_skill.py", "dexscreener-token-pairs", "base/mainnet", "0xabc"])
        self.assertEqual(code, 2)
        self.assertEqual(payload.get("code"), "invalid_input")

    def test_dexscreener_token_pairs_accepts_list_response(self) -> None:
        pairs = [
            {
                "chainId": "base",
                "dexId": "aerodrome",
                "pairAddress": "0xpair1",
                "url": "https://dexscreener.com/base/0xpair1",
                "baseToken": {"address": "0x4200000000000000000000000000000000000006", "symbol": "WETH", "name": "Wrapped Ether"},
                "quoteToken": {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "symbol": "USDC", "name": "USD Coin"},
            }
        ]
        with mock.patch.object(skill, "_fetch_dexscreener_json", return_value=(pairs, None, 0)) as fetch_mock:
            code, payload = self._capture(
                ["xclaw_agent_skill.py", "dexscreener-token-pairs", "base", "0x4200000000000000000000000000000000000006", "5"]
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload.get("code"), "ok")
        self.assertEqual(payload.get("endpoint"), "token-pairs")
        self.assertEqual(payload.get("pairCount"), 1)
        called_url = fetch_mock.call_args.args[0]
        self.assertIn("/token-pairs/v1/base/0x4200000000000000000000000000000000000006", called_url)

    def test_faucet_request_native_only_uses_all_asset_default(self) -> None:
        env = {
            "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
            "XCLAW_AGENT_API_KEY": "test-key",
            "XCLAW_DEFAULT_CHAIN": "base_sepolia",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "faucet-request", "native"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["faucet-request", "--chain", "base_sepolia", "--json"])

    def test_faucet_request_hbar_alias_uses_all_asset_default(self) -> None:
        env = {
            "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
            "XCLAW_AGENT_API_KEY": "test-key",
            "XCLAW_DEFAULT_CHAIN": "base_sepolia",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "faucet-request", "hbar"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["faucet-request", "--chain", "base_sepolia", "--json"])

    def test_faucet_request_chain_and_specific_asset_preserved(self) -> None:
        env = {
            "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
            "XCLAW_AGENT_API_KEY": "test-key",
            "XCLAW_DEFAULT_CHAIN": "base_sepolia",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "faucet-request", "base_sepolia", "stable"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["faucet-request", "--chain", "base_sepolia", "--asset", "stable", "--json"])

    def test_auth_recover_delegates_to_runtime(self) -> None:
        env = {
            "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
            "XCLAW_DEFAULT_CHAIN": "base_sepolia",
            "XCLAW_AGENT_ID": "ag_demo",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "auth-recover"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["auth", "recover", "--chain", "base_sepolia", "--json"])

    def test_agent_register_delegates_to_profile_set_name(self) -> None:
        env = {
            "XCLAW_API_BASE_URL": "https://xclaw.trade/api/v1",
            "XCLAW_DEFAULT_CHAIN": "base_sepolia",
            "XCLAW_AGENT_API_KEY": "test-key",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "agent-register", "Slice95Runner"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["profile", "set-name", "--name", "Slice95Runner", "--chain", "base_sepolia", "--json"])

    def test_wallet_send_token_rejects_empty_token(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            code, payload = self._capture(
                [
                    "xclaw_agent_skill.py",
                    "wallet-send-token",
                    "",
                    "0x9099d24D55c105818b4e9eE117d87BC11063CF10",
                    "10000000",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("code"), "invalid_input")
        self.assertIn("token", (payload.get("details") or {}))

    def test_run_agent_normalizes_pending_approval_to_success(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "actionHint": "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
            "details": {
                "approvalId": "xfr_123",
                "chain": "base_sepolia",
                "status": "approval_pending",
                "queuedMessage": "Approval required (transfer)\nStatus: approval_pending"
            }
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=None
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("details", {}).get("approvalId"), "xfr_123")

    def test_run_agent_keeps_non_approval_error_nonzero(self) -> None:
        payload = {"ok": False, "code": "send_failed", "message": "boom"}
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 1)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "send_failed")

    def test_run_agent_keeps_approval_sync_failed_nonzero(self) -> None:
        payload = {
            "ok": False,
            "code": "approval_sync_failed",
            "message": "Transfer approval could not be synced to management inbox.",
            "details": {"approvalId": "xfr_abc"},
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 1)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_sync_failed")
        self.assertFalse(emitted.get("ok"))

    def test_run_agent_normalizes_symbol_unit_mismatch_to_nonfatal(self) -> None:
        payload = {
            "ok": False,
            "code": "invalid_input",
            "message": "Amount is too small for symbol-based transfer and looks like a base-unit mistake.",
            "details": {"token": "USDC", "amountWei": "10000000"},
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token", "--token", "USDC"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "input_guarded")

    def test_run_agent_normalizes_pending_approval_even_when_exit_zero(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_999", "status": "approval_pending"},
        }
        child = mock.Mock()
        child.returncode = 0
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=None
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("details", {}).get("approvalId"), "xfr_999")
        self.assertNotIn("queuedMessage", emitted.get("details", {}))
        self.assertIn("management approval", str(emitted.get("message", "")).lower())

    def test_run_agent_normalizes_trade_pending_with_last_status(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Trade is waiting for management approval.",
            "details": {"tradeId": "trd_abc", "chain": "base_sepolia", "lastStatus": "approval_pending"},
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["trade", "spot"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertTrue(emitted.get("ok"))
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("details", {}).get("tradeId"), "trd_abc")

    def test_run_agent_sanitizes_transfer_queued_message(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "actionHint": "Send queuedMessage verbatim so Telegram buttons can attach, then wait for Approve/Deny.",
            "details": {
                "approvalId": "xfr_abc",
                "status": "approval_pending",
                "queuedMessage": "Approval required (transfer)\nStatus: approval_pending",
            },
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=None
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(emitted.get("message"), "Transfer queued for management approval.")
        self.assertNotIn("queuedMessage", emitted.get("details", {}))
        self.assertIn("wait for owner approve/deny", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_transfer_pending_includes_management_url(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_mgmt", "status": "approval_pending"},
        }
        owner_link = {
            "ok": True,
            "code": "ok",
            "managementUrl": "https://xclaw.trade/agents/ag_1?token=ol_abc",
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_fetch_owner_link_payload", return_value=owner_link
                ), mock.patch.object(
                    skill, "_last_delivery_is_telegram", return_value=False
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(
            (emitted.get("details") or {}).get("managementUrl"),
            "https://xclaw.trade/agents/ag_1?token=ol_abc",
        )
        self.assertIn("share managementurl", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_transfer_pending_skips_owner_link_lookup_when_telegram_active(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_tg", "status": "approval_pending"},
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                    skill, "_last_delivery_is_telegram", return_value=True
                ), mock.patch.object(
                    skill, "_fetch_owner_link_payload"
                ) as owner_link_mock:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        owner_link_mock.assert_not_called()
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertNotIn("managementUrl", emitted.get("details", {}))
        self.assertIn("wait for owner approve/deny", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_transfer_pending_forces_management_flow_when_configured(self) -> None:
        pending_payload = {
            "ok": False,
            "code": "approval_required",
            "message": "Transfer is waiting for management approval.",
            "details": {"approvalId": "xfr_force", "status": "approval_pending"},
        }
        owner_link = {
            "ok": True,
            "code": "ok",
            "managementUrl": "https://xclaw.trade/agents/ag_1?token=ol_force",
        }
        child = mock.Mock()
        child.returncode = 1
        child.communicate.return_value = (json.dumps(pending_payload), "")
        with mock.patch.dict(skill.os.environ, {"XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT": "1"}, clear=False):
            with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
                with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                    with mock.patch.object(skill.subprocess, "Popen", return_value=child), mock.patch.object(
                        skill, "_last_delivery_is_telegram", return_value=True
                    ), mock.patch.object(
                        skill, "_fetch_owner_link_payload", return_value=owner_link
                    ):
                        buf = io.StringIO()
                        with redirect_stdout(buf):
                            code = skill._run_agent(["wallet", "send-token"])
        self.assertEqual(code, 0)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "approval_pending")
        self.assertEqual(
            (emitted.get("details") or {}).get("managementUrl"),
            "https://xclaw.trade/agents/ag_1?token=ol_force",
        )
        self.assertIn("share managementurl", str(emitted.get("actionHint", "")).lower())

    def test_run_agent_timeout_kills_process_group(self) -> None:
        child = mock.Mock()
        child.pid = 12345
        child.communicate.side_effect = [
            skill.subprocess.TimeoutExpired(cmd=["xclaw-agent", "trade", "spot"], timeout=1),
            ("", ""),
        ]
        with mock.patch.object(skill, "_resolve_agent_binary", return_value="/usr/bin/xclaw-agent"):
            with mock.patch.object(skill, "_maybe_patch_openclaw_gateway"):
                with mock.patch.object(skill.subprocess, "Popen", return_value=child):
                    with mock.patch.object(skill.os, "killpg") as killpg_mock:
                        buf = io.StringIO()
                        with redirect_stdout(buf):
                            code = skill._run_agent(["trade", "spot"])
        self.assertEqual(code, 124)
        killpg_mock.assert_called_once_with(12345, skill.signal.SIGKILL)
        emitted = json.loads(buf.getvalue().strip())
        self.assertEqual(emitted.get("code"), "timeout")

    def test_extract_json_payload_handles_prefixed_line_noise(self) -> None:
        payload = {"ok": False, "code": "approval_required", "details": {"status": "approval_pending"}}
        raw = "warning: transient rpc error\n" + json.dumps(payload)
        extracted = skill._extract_json_payload(raw)
        self.assertIsInstance(extracted, dict)
        self.assertEqual(extracted.get("code"), "approval_required")

    def test_limit_orders_create_routes_to_runtime(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(
                [
                    "xclaw_agent_skill.py",
                    "limit-orders-create",
                    "buy",
                    "So11111111111111111111111111111111111111112",
                    "DezXAZ8z7PnrnRJjz3A8C5W97R6A6nhz6M8mM4fowwWf",
                    "10",
                    "0.95",
                    "200",
                    "solana_devnet",
                ]
            )
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(
            [
                "limit-orders",
                "create",
                "--chain",
                "solana_devnet",
                "--mode",
                "real",
                "--side",
                "buy",
                "--token-in",
                "So11111111111111111111111111111111111111112",
                "--token-out",
                "DezXAZ8z7PnrnRJjz3A8C5W97R6A6nhz6M8mM4fowwWf",
                "--amount-in",
                "10",
                "--limit-price",
                "0.95",
                "--slippage-bps",
                "200",
                "--json",
            ]
        )

    def test_limit_orders_run_once_routes_to_runtime(self) -> None:
        with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
            code = skill.main(["xclaw_agent_skill.py", "limit-orders-run-once", "solana_localnet", "sync"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["limit-orders", "run-once", "--chain", "solana_localnet", "--sync", "--json"])

    def test_withdraws_list_routes_to_runtime_with_explicit_chain(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "withdraws-list", "solana_devnet"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["withdraws", "list", "--chain", "solana_devnet", "--json"])

    def test_withdraws_list_routes_to_runtime_with_default_chain(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="base_sepolia"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "withdraws-list"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["withdraws", "list", "--chain", "base_sepolia", "--json"])

    def test_wallet_rpc_health_routes_to_runtime_with_explicit_chain(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_run_agent", return_value=0) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-rpc-health", "solana_devnet"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "rpc-health", "--chain", "solana_devnet", "--json"])

    def test_wallet_rpc_health_routes_to_runtime_with_default_chain(self) -> None:
        with mock.patch.dict("os.environ", self._ENV, clear=False):
            with mock.patch.object(skill, "_resolve_active_chain", return_value="solana_devnet"), mock.patch.object(
                skill, "_run_agent", return_value=0
            ) as run_mock:
                code = skill.main(["xclaw_agent_skill.py", "wallet-rpc-health"])
        self.assertEqual(code, 0)
        run_mock.assert_called_once_with(["wallet", "rpc-health", "--chain", "solana_devnet", "--json"])

if __name__ == "__main__":
    unittest.main()
