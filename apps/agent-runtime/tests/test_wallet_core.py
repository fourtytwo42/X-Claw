import json
import argparse
import io
import os
import pathlib
import stat
import subprocess
import shutil
import sys
import site
import tempfile
import unittest
import textwrap
from decimal import Decimal
from contextlib import redirect_stdout
from typing import Any
from unittest import mock
from datetime import datetime, timedelta, timezone

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import cli  # noqa: E402


class WalletCoreUnitTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self) -> None:
        private_key_hex = "11" * 32
        encrypted = cli._encrypt_private_key(private_key_hex, "passphrase-123")
        entry = {"address": cli._derive_address(private_key_hex), "crypto": encrypted}
        decrypted = cli._decrypt_private_key(entry, "passphrase-123")
        self.assertEqual(decrypted.hex(), private_key_hex)

    def test_malformed_ciphertext_is_rejected(self) -> None:
        entry = {
            "address": "0x0000000000000000000000000000000000000001",
            "crypto": {
                "enc": "aes-256-gcm",
                "kdf": "argon2id",
                "kdfParams": {"timeCost": 3, "memoryCost": 65536, "parallelism": 1, "hashLen": 32},
                "saltB64": "AA==",
                "nonceB64": "AA==",
                "ciphertextB64": "AA==",
            },
        }
        with self.assertRaises(cli.WalletStoreError):
            cli._decrypt_private_key(entry, "pw")

    def test_api_request_recovers_on_auth_invalid(self) -> None:
        with (
            mock.patch.object(cli, "_require_api_base_url", return_value="https://xclaw.trade/api/v1"),
            mock.patch.object(cli, "_resolve_api_key", return_value="old-key"),
            mock.patch.object(cli, "_resolve_runtime_default_chain", return_value=("base_sepolia", "state")),
            mock.patch.object(cli, "_recover_api_key_with_wallet_signature", return_value="new-key") as recover_mock,
            mock.patch.object(
                cli,
                "_http_json_request",
                side_effect=[(401, {"code": "auth_invalid", "message": "bad key"}), (200, {"ok": True})],
            ) as http_mock,
        ):
            status, body = cli._api_request("GET", "/status")

        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        recover_mock.assert_called_once_with("https://xclaw.trade/api/v1", "old-key", "base_sepolia")
        self.assertEqual(http_mock.call_count, 2)

    def test_api_request_does_not_recover_for_non_auth_error(self) -> None:
        with (
            mock.patch.object(cli, "_require_api_base_url", return_value="https://xclaw.trade/api/v1"),
            mock.patch.object(cli, "_resolve_api_key", return_value="old-key"),
            mock.patch.object(cli, "_recover_api_key_with_wallet_signature") as recover_mock,
            mock.patch.object(
                cli,
                "_http_json_request",
                return_value=(500, {"code": "internal_error", "message": "boom"}),
            ),
        ):
            status, body = cli._api_request("GET", "/status")

        self.assertEqual(status, 500)
        self.assertEqual(body.get("code"), "internal_error")
        recover_mock.assert_not_called()

    def test_parse_uint_text_accepts_cast_scientific_suffix(self) -> None:
        self.assertEqual(cli._parse_uint_text("20000000000000000000000 [2e22]"), 20000000000000000000000)
        self.assertEqual(cli._parse_uint_text("0x2a [4.2e1]"), 42)

    def test_parse_uint_from_cast_output_handles_bracketed_arrays(self) -> None:
        raw = "[1000000000000000000 [1e18], 2057515000000000000000 [2.057e21]]"
        self.assertEqual(cli._parse_uint_from_cast_output(raw), 2057515000000000000000)

    def test_wallet_wrap_native_success_uses_helper_when_configured(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", amount="1", json=True)
        with (
            mock.patch.object(cli, "load_wallet_store", return_value={}),
            mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "11" * 20, "aa" * 32)),
            mock.patch.object(cli, "_resolve_wrapped_native_target", return_value=("0x" + "22" * 20, "0x" + "33" * 20, "WHBAR")),
            mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["100", "200"]),
            mock.patch.object(cli, "_cast_calldata", return_value="0x1234"),
            mock.patch.object(cli, "_cast_rpc_send_transaction", return_value="0x" + "44" * 32) as send_tx_mock,
            mock.patch.object(cli, "_require_cast_bin", return_value="cast"),
            mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc"),
            mock.patch.object(
                cli,
                "_run_subprocess",
                return_value=mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr=""),
            ),
            mock.patch.object(cli, "_fetch_erc20_metadata", return_value={"decimals": 8, "symbol": "WHBAR"}),
        ):
            code = cli.cmd_wallet_wrap_native(args)
        self.assertEqual(code, 0)
        send_payload = send_tx_mock.call_args.args[1]
        self.assertEqual(send_payload.get("to"), "0x" + "22" * 20)

    def test_wallet_wrap_native_success_non_hedera_uses_wrapped_token_deposit(self) -> None:
        args = argparse.Namespace(chain="ethereum_sepolia", amount="1", json=True)
        with (
            mock.patch.object(cli, "load_wallet_store", return_value={}),
            mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "11" * 20, "aa" * 32)),
            mock.patch.object(cli, "_resolve_wrapped_native_target", return_value=(None, "0x" + "33" * 20, "WETH")),
            mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["100", "200"]),
            mock.patch.object(cli, "_cast_calldata", return_value="0x1234"),
            mock.patch.object(cli, "_cast_rpc_send_transaction", return_value="0x" + "44" * 32) as send_tx_mock,
            mock.patch.object(cli, "_require_cast_bin", return_value="cast"),
            mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc"),
            mock.patch.object(
                cli,
                "_run_subprocess",
                return_value=mock.Mock(returncode=0, stdout='{"status":"0x1"}', stderr=""),
            ),
            mock.patch.object(cli, "_fetch_erc20_metadata", return_value={"decimals": 18, "symbol": "WETH"}),
        ):
            code = cli.cmd_wallet_wrap_native(args)
        self.assertEqual(code, 0)
        send_payload = send_tx_mock.call_args.args[1]
        self.assertEqual(send_payload.get("to"), "0x" + "33" * 20)

    def test_wallet_wrap_native_missing_helper_is_deterministic(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", amount="1", json=True)
        out = io.StringIO()
        with (
            redirect_stdout(out),
            mock.patch.object(cli, "load_wallet_store", return_value={}),
            mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "11" * 20, "aa" * 32)),
            mock.patch.object(
                cli,
                "_resolve_wrapped_native_target",
                side_effect=cli.WalletStoreError("Chain config for 'hedera_testnet' has invalid coreContracts.wrappedNativeHelper."),
            ),
        ):
            code = cli.cmd_wallet_wrap_native(args)
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue().strip())
        self.assertEqual(payload.get("code"), "wrapped_native_helper_missing")

    def test_wallet_wrap_native_missing_wrapped_token_is_deterministic(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", amount="1", json=True)
        out = io.StringIO()
        with (
            redirect_stdout(out),
            mock.patch.object(cli, "load_wallet_store", return_value={}),
            mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "11" * 20, "aa" * 32)),
            mock.patch.object(
                cli,
                "_resolve_wrapped_native_target",
                side_effect=cli.WalletStoreError("Chain config for 'base_sepolia' has no canonical wrapped native token for native symbol 'ETH'."),
            ),
        ):
            code = cli.cmd_wallet_wrap_native(args)
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue().strip())
        self.assertEqual(payload.get("code"), "wrapped_native_token_missing")

    def test_wallet_wrap_native_receipt_failure_returns_wrap_native_failed(self) -> None:
        args = argparse.Namespace(chain="ethereum_sepolia", amount="1", json=True)
        out = io.StringIO()
        with (
            redirect_stdout(out),
            mock.patch.object(cli, "load_wallet_store", return_value={}),
            mock.patch.object(cli, "_execution_wallet", return_value=("0x" + "11" * 20, "aa" * 32)),
            mock.patch.object(cli, "_resolve_wrapped_native_target", return_value=(None, "0x" + "33" * 20, "WETH")),
            mock.patch.object(cli, "_fetch_token_balance_wei", side_effect=["100", "200"]),
            mock.patch.object(cli, "_cast_calldata", return_value="0x1234"),
            mock.patch.object(cli, "_cast_rpc_send_transaction", return_value="0x" + "44" * 32),
            mock.patch.object(cli, "_require_cast_bin", return_value="cast"),
            mock.patch.object(cli, "_chain_rpc_url", return_value="https://rpc"),
            mock.patch.object(cli, "_run_subprocess", return_value=mock.Mock(returncode=0, stdout='{"status":"0x0"}', stderr="")),
            mock.patch.object(cli, "_fetch_erc20_metadata", return_value={"decimals": 18, "symbol": "WETH"}),
        ):
            code = cli.cmd_wallet_wrap_native(args)
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue().strip())
        self.assertEqual(payload.get("code"), "wrap_native_failed")

    def test_enforce_trade_caps_missing_caps_is_non_blocking(self) -> None:
        with (
            mock.patch.object(cli, "_fetch_outbound_transfer_policy", return_value={"chainEnabled": True}),
            mock.patch.object(cli, "_enforce_owner_chain_enabled"),
            mock.patch.object(cli, "_utc_day_key", return_value="2026-02-20"),
            mock.patch.object(cli, "load_state", return_value={}),
        ):
            state, day_key, current_spend, current_filled, caps = cli._enforce_trade_caps("ethereum_sepolia", Decimal("10"), 1)
        self.assertEqual(state, {})
        self.assertEqual(day_key, "2026-02-20")
        self.assertEqual(current_spend, Decimal("0"))
        self.assertEqual(current_filled, 0)
        self.assertEqual(caps.get("dailyCapUsdEnabled"), False)
        self.assertEqual(caps.get("dailyTradeCapEnabled"), False)
        self.assertIsNone(caps.get("maxDailyUsd"))
        self.assertIsNone(caps.get("maxDailyTradeCount"))

    def test_fetch_wallet_holdings_includes_hedera_discovered_tokens(self) -> None:
        wallet = {"address": "0x" + "11" * 20, "crypto": {"enc": "aes-256-gcm", "kdf": "argon2id", "kdfParams": {}, "saltB64": "AA==", "nonceB64": "AA==", "ciphertextB64": "AA=="}}
        with (
            mock.patch.object(cli, "load_wallet_store", return_value={"chains": {"hedera_testnet": "w1"}, "wallets": {"w1": wallet}}),
            mock.patch.object(cli, "_chain_wallet", return_value=("w1", wallet)),
            mock.patch.object(cli, "_validate_wallet_entry_shape"),
            mock.patch.object(cli, "_fetch_native_balance_wei", return_value=str(2 * 10**18)),
            mock.patch.object(cli, "_canonical_token_map", return_value={"WHBAR": "0x" + "22" * 20}),
            mock.patch.object(cli, "_fetch_token_balance_wei", return_value=str(500000000)),
            mock.patch.object(cli, "_fetch_erc20_metadata", return_value={"symbol": "WHBAR", "decimals": 8}),
            mock.patch.object(
                cli,
                "_discover_hedera_wallet_tokens",
                return_value=(
                    [
                        {
                            "symbol": "USDC",
                            "token": "0x" + "33" * 20,
                            "balanceWei": "130000",
                            "balance": "0.13",
                            "balancePretty": "0.13",
                            "decimals": 6,
                            "tokenId": "0.0.5449",
                        }
                    ],
                    [],
                ),
            ),
        ):
            holdings = cli._fetch_wallet_holdings("hedera_testnet")
        symbols = {str(t.get("symbol")) for t in holdings.get("tokens", []) if isinstance(t, dict)}
        self.assertIn("WHBAR", symbols)
        self.assertIn("USDC", symbols)

    def test_resolve_token_address_uses_unique_tracked_symbol(self) -> None:
        with mock.patch.object(
            cli,
            "_tracked_tokens_for_chain",
            return_value=[{"token": "0x" + "11" * 20, "symbol": "USDCX"}],
        ), mock.patch.object(cli, "_canonical_token_map", return_value={}):
            resolved = cli._resolve_token_address("hedera_testnet", "USDCX")
        self.assertEqual(resolved, "0x" + "11" * 20)

    def test_resolve_token_address_rejects_ambiguous_tracked_symbol(self) -> None:
        with mock.patch.object(
            cli,
            "_tracked_tokens_for_chain",
            return_value=[
                {"token": "0x" + "11" * 20, "symbol": "USDCX"},
                {"token": "0x" + "22" * 20, "symbol": "USDCX"},
            ],
        ), mock.patch.object(cli, "_canonical_token_map", return_value={}):
            with self.assertRaises(cli.TokenResolutionError) as ctx:
                cli._resolve_token_address("hedera_testnet", "USDCX")
        self.assertEqual(ctx.exception.code, "token_symbol_ambiguous")

    def test_cmd_wallet_track_token_persists_local_state(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", token="0x" + "11" * 20, json=True)
        state: dict = {}

        def _load() -> dict:
            return json.loads(json.dumps(state))

        def _save(new_state: dict) -> None:
            state.clear()
            state.update(json.loads(json.dumps(new_state)))

        with (
            mock.patch.object(cli, "load_state", side_effect=_load),
            mock.patch.object(cli, "save_state", side_effect=_save),
            mock.patch.object(cli, "_sync_tracked_tokens_from_remote", return_value=False),
            mock.patch.object(cli, "_fetch_erc20_metadata", return_value={"symbol": "USDCX", "name": "USD Coin X", "decimals": 6}),
            mock.patch.object(cli, "_mirror_tracked_tokens", return_value=True),
        ):
            code = cli.cmd_wallet_track_token(args)
        self.assertEqual(code, 0)
        tracked = (((state.get("trackedTokens") or {}).get("hedera_testnet") or {}).get("addresses") or [])
        self.assertIn("0x" + "11" * 20, tracked)

    def test_cmd_wallet_untrack_token_reports_not_tracked(self) -> None:
        args = argparse.Namespace(chain="hedera_testnet", token="0x" + "11" * 20, json=True)
        with (
            mock.patch.object(cli, "_sync_tracked_tokens_from_remote", return_value=False),
            mock.patch.object(cli, "load_state", return_value={}),
            mock.patch.object(cli, "save_state"),
        ):
            code = cli.cmd_wallet_untrack_token(args)
        self.assertEqual(code, 1)

    def test_fetch_wallet_holdings_includes_nonzero_tracked_token(self) -> None:
        wallet = {"address": "0x" + "11" * 20, "crypto": {"enc": "aes-256-gcm", "kdf": "argon2id", "kdfParams": {}, "saltB64": "AA==", "nonceB64": "AA==", "ciphertextB64": "AA=="}}
        with (
            mock.patch.object(cli, "load_wallet_store", return_value={"chains": {"base_sepolia": "w1"}, "wallets": {"w1": wallet}}),
            mock.patch.object(cli, "_chain_wallet", return_value=("w1", wallet)),
            mock.patch.object(cli, "_validate_wallet_entry_shape"),
            mock.patch.object(cli, "_fetch_native_balance_wei", return_value=str(2 * 10**18)),
            mock.patch.object(cli, "_canonical_token_map", return_value={}),
            mock.patch.object(cli, "_tracked_tokens_for_chain", return_value=[{"token": "0x" + "33" * 20, "symbol": "USDCX", "decimals": 6}]),
            mock.patch.object(cli, "_fetch_token_balance_wei", return_value=str(130000)),
            mock.patch.object(cli, "_fetch_erc20_metadata", return_value={"symbol": "USDCX", "decimals": 6}),
            mock.patch.object(cli, "_is_hedera_chain", return_value=False),
        ):
            holdings = cli._fetch_wallet_holdings("base_sepolia")
        symbols = {str(t.get("symbol")) for t in holdings.get("tokens", []) if isinstance(t, dict)}
        self.assertIn("USDCX", symbols)


class WalletCoreCliTests(unittest.TestCase):
    def _base_test_env(self, home: str) -> dict[str, str]:
        # Hermetic subprocess env: keep only essentials and test-owned runtime paths.
        user_site = site.getusersitepackages()
        py_path = str(user_site) if isinstance(user_site, str) and user_site else ""
        return {
            "HOME": str(home),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONPATH": py_path,
            "XCLAW_AGENT_HOME": str(pathlib.Path(home) / ".xclaw-agent"),
        }

    def _run(self, *args: str, home: str, extra_env: dict[str, str] | None = None) -> tuple[int, dict]:
        cmd = ["apps/agent-runtime/bin/xclaw-agent", *args]
        env = self._base_test_env(home)
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        payload = json.loads(proc.stdout.strip())
        return proc.returncode, payload

    def _seed_wallet(self, home: str, chain: str = "base_sepolia") -> tuple[str, str]:
        private_key_hex = "22" * 32
        address = cli._derive_address(private_key_hex)
        encrypted = cli._encrypt_private_key(private_key_hex, "passphrase-123")
        wallet_dir = pathlib.Path(home) / ".xclaw-agent"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        store = {
            "version": 1,
            "defaultWalletId": "wlt_test",
            "wallets": {
                "wlt_test": {
                    "walletId": "wlt_test",
                    "address": address,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "crypto": encrypted,
                }
            },
            "chains": {chain: "wlt_test"},
        }
        wallet_path = wallet_dir / "wallets.json"
        wallet_path.write_text(json.dumps(store), encoding="utf-8")
        if os.name != "nt":
            os.chmod(wallet_dir, stat.S_IRWXU)
            os.chmod(wallet_path, stat.S_IRUSR | stat.S_IWUSR)
        return address, private_key_hex

    def test_wallet_health_includes_next_action_on_ok(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            self._seed_wallet(home)
            code, payload = self._run("wallet", "health", "--chain", "base_sepolia", "--json", home=home)
            self.assertEqual(code, 0)
            self.assertTrue(payload.get("ok"))
            self.assertIsInstance(payload.get("nextAction"), str)
            self.assertIsInstance(payload.get("actionHint"), str)
            self.assertEqual(payload.get("nextAction"), payload.get("actionHint"))

    def test_default_chain_get_returns_fallback_when_unset(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            code, payload = self._run("default-chain", "get", "--json", home=home)
            self.assertEqual(code, 0)
            self.assertTrue(payload.get("ok"))
            self.assertEqual(payload.get("chainKey"), "base_sepolia")
            self.assertEqual(payload.get("source"), "fallback")

    def test_default_chain_set_and_get_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            set_code, set_payload = self._run("default-chain", "set", "--chain", "kite_ai_testnet", "--json", home=home)
            self.assertEqual(set_code, 0)
            self.assertTrue(set_payload.get("ok"))
            self.assertEqual(set_payload.get("chainKey"), "kite_ai_testnet")
            self.assertEqual(set_payload.get("source"), "state")

            get_code, get_payload = self._run("default-chain", "get", "--json", home=home)
            self.assertEqual(get_code, 0)
            self.assertTrue(get_payload.get("ok"))
            self.assertEqual(get_payload.get("chainKey"), "kite_ai_testnet")
            self.assertEqual(get_payload.get("source"), "state")

    def test_default_chain_set_rejects_unsupported_chain(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            code, payload = self._run("default-chain", "set", "--chain", "ethereum_mainnet", "--json", home=home)
            self.assertEqual(code, 2)
            self.assertFalse(payload.get("ok"))
            self.assertEqual(payload.get("code"), "unsupported_chain")

    def _seed_multi_chain_wallet(self, home: str) -> str:
        private_key_hex = "33" * 32
        address = cli._derive_address(private_key_hex)
        encrypted = cli._encrypt_private_key(private_key_hex, "passphrase-123")
        wallet_dir = pathlib.Path(home) / ".xclaw-agent"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        store = {
            "version": 1,
            "defaultWalletId": "wlt_test",
            "wallets": {
                "wlt_test": {
                    "walletId": "wlt_test",
                    "address": address,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "crypto": encrypted,
                }
            },
            "chains": {"base_sepolia": "wlt_test", "hardhat_local": "wlt_test"},
        }
        wallet_path = wallet_dir / "wallets.json"
        wallet_path.write_text(json.dumps(store), encoding="utf-8")
        if os.name != "nt":
            os.chmod(wallet_dir, stat.S_IRWXU)
            os.chmod(wallet_path, stat.S_IRUSR | stat.S_IWUSR)
        return address

    def _seed_policy(
        self,
        home: str,
        *,
        chain: str = "base_sepolia",
        chain_enabled: bool = True,
        paused: bool = False,
        approval_required: bool = True,
        approval_granted: bool = True,
        max_daily_native_wei: str = "1000000000000000000",
    ) -> None:
        wallet_dir = pathlib.Path(home) / ".xclaw-agent"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        policy = {
            "version": 1,
            "paused": paused,
            "chains": {chain: {"chain_enabled": chain_enabled}},
            "spend": {
                "approval_required": approval_required,
                "approval_granted": approval_granted,
                "max_daily_native_wei": max_daily_native_wei,
            },
        }
        policy_path = wallet_dir / "policy.json"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        if os.name != "nt":
            os.chmod(wallet_dir, stat.S_IRWXU)
            os.chmod(policy_path, stat.S_IRUSR | stat.S_IWUSR)

    def _seed_spend_state(self, home: str, *, chain: str, amount_wei: str) -> None:
        wallet_dir = pathlib.Path(home) / ".xclaw-agent"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = {"spendLedger": {chain: {day_key: amount_wei}}}
        state_path = wallet_dir / "state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        if os.name != "nt":
            os.chmod(wallet_dir, stat.S_IRWXU)
            os.chmod(state_path, stat.S_IRUSR | stat.S_IWUSR)

    def _seed_transfer_policy_cache(self, home: str, *, chain: str, destination: str) -> None:
        wallet_dir = pathlib.Path(home) / ".xclaw-agent"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        state_path = wallet_dir / "state.json"
        state: dict[str, Any] = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8") or "{}")
            except Exception:
                state = {}
        cache = state.setdefault("transferPolicyCache", {})
        cache[chain] = {
            "cachedAt": datetime.now(timezone.utc).isoformat(),
            "policy": {
                "chainEnabled": True,
                "outboundTransfersEnabled": True,
                "outboundMode": "whitelist",
                "outboundWhitelistAddresses": [destination.lower()],
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")
        if os.name != "nt":
            os.chmod(wallet_dir, stat.S_IRWXU)
            os.chmod(state_path, stat.S_IRUSR | stat.S_IWUSR)

    def _seed_transfer_approval_policy(
        self,
        home: str,
        *,
        chain: str,
        mode: str = "auto",
        native_preapproved: bool = True,
        allowed_tokens: list[str] | None = None,
    ) -> None:
        wallet_dir = pathlib.Path(home) / ".xclaw-agent"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        policy_path = wallet_dir / "transfer-policy.json"
        payload = {
            "schemaVersion": 1,
            "chains": {
                chain: {
                    "chainKey": chain,
                    "transferApprovalMode": mode,
                    "nativeTransferPreapproved": bool(native_preapproved),
                    "allowedTransferTokens": list(allowed_tokens or []),
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                }
            },
        }
        policy_path.write_text(json.dumps(payload), encoding="utf-8")
        if os.name != "nt":
            os.chmod(wallet_dir, stat.S_IRWXU)
            os.chmod(policy_path, stat.S_IRUSR | stat.S_IWUSR)

    def _install_fake_cast(self, home: str) -> str:
        if os.name == "nt":
            self.skipTest("fake cast script helper is POSIX-only")
        bin_dir = pathlib.Path(home) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        cast_path = bin_dir / "cast"
        cast_path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                cmd="${1:-}"
                if [ "$cmd" = "send" ]; then
                  echo '{"transactionHash":"0xabababababababababababababababababababababababababababababababab"}'
                  exit 0
                fi
                if [ "$cmd" = "receipt" ]; then
                  echo '{"status":"0x1"}'
                  exit 0
                fi
                if [ "$cmd" = "balance" ]; then
                  echo "123456789"
                  exit 0
                fi
                if [ "$cmd" = "call" ]; then
                  echo "0x2a"
                  exit 0
                fi
                echo "unsupported fake cast command" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        os.chmod(cast_path, stat.S_IRWXU)
        return str(bin_dir)

    def _install_bash_only_bin(self, home: str) -> str:
        if os.name == "nt":
            self.skipTest("bash-only helper is POSIX-only")
        bin_dir = pathlib.Path(home) / "bash-only-bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        bash_path = bin_dir / "bash"
        python_path = bin_dir / "python3"
        dirname_path = bin_dir / "dirname"
        target_python = shutil.which("python3")
        if not target_python:
            self.skipTest("python3 is required for launcher helper")
        os.symlink("/bin/bash", bash_path)
        os.symlink(target_python, python_path)
        os.symlink("/usr/bin/dirname", dirname_path)
        return str(bin_dir)

    def _canonical_message(self, chain: str = "base_sepolia", timestamp: datetime | None = None) -> str:
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        iso = ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return "\n".join(
            [
                "domain=xclaw.trade",
                f"chain={chain}",
                "nonce=nonce_1234567890ABCDEF",
                f"timestamp={iso}",
                "action=agent_token_recovery",
            ]
        )

    def test_wallet_create_non_interactive_rejected_without_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run("wallet", "create", "--chain", "base_sepolia", "--json", home=tmp_home)
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "non_interactive")

    def test_wallet_create_non_interactive_with_env_passphrase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run(
                "wallet",
                "create",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 0)
            self.assertEqual(payload["code"], "ok")
            self.assertTrue(payload["created"])

    def test_wallet_import_non_interactive_rejected_without_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run("wallet", "import", "--chain", "base_sepolia", "--json", home=tmp_home)
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "non_interactive")

    def test_wallet_import_non_interactive_with_env_private_key_and_passphrase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run(
                "wallet",
                "import",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={
                    "XCLAW_WALLET_IMPORT_PRIVATE_KEY": "0x" + ("11" * 32),
                    "XCLAW_WALLET_PASSPHRASE": "passphrase-123",
                },
            )
            self.assertEqual(code, 0)
            self.assertEqual(payload["code"], "ok")
            self.assertTrue(payload["imported"])

    @unittest.skipIf(os.name == "nt", "Permission mode assertions are POSIX-specific")
    def test_wallet_health_rejects_unsafe_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            wallet_dir = pathlib.Path(tmp_home) / ".xclaw-agent"
            wallet_dir.mkdir(parents=True, exist_ok=True)
            store = wallet_dir / "wallets.json"
            store.write_text(json.dumps({"version": 1, "defaultWalletId": None, "wallets": {}, "chains": {}}), encoding="utf-8")
            os.chmod(wallet_dir, 0o700)
            os.chmod(store, 0o644)

            code, payload = self._run("wallet", "health", "--chain", "base_sepolia", "--json", home=tmp_home)
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "unsafe_permissions")

    def test_wallet_address_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run("wallet", "address", "--chain", "base_sepolia", "--json", home=tmp_home)
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "wallet_missing")

    def test_wallet_sign_challenge_empty_message_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                " ",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
            )
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "invalid_input")

    def test_wallet_sign_challenge_missing_wallet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                self._canonical_message(),
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "wallet_missing")

    def test_wallet_sign_challenge_malformed_challenge_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            bad_message = "domain=xclaw.trade\nchain=base_sepolia\nnonce=abc"
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                bad_message,
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "invalid_challenge_format")

    def test_wallet_sign_challenge_chain_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                self._canonical_message(chain="hardhat_local"),
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "invalid_challenge_format")

    def test_wallet_sign_challenge_stale_timestamp_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            stale = datetime.now(timezone.utc) - timedelta(minutes=10)
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                self._canonical_message(timestamp=stale),
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "invalid_challenge_format")

    def test_wallet_sign_challenge_non_interactive_without_env_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                self._canonical_message(),
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
            )
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "non_interactive")

    def test_wallet_sign_challenge_cast_missing_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            bash_only = self._install_bash_only_bin(tmp_home)
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                self._canonical_message(),
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123", "PATH": bash_only},
            )
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "missing_dependency")

    def test_wallet_send_missing_policy_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            code, payload = self._run(
                "wallet",
                "send",
                "--to",
                "0x0000000000000000000000000000000000000001",
                "--amount-wei",
                "1",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "policy_blocked")

    def test_wallet_send_chain_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            self._seed_policy(tmp_home, chain_enabled=False)
            code, payload = self._run(
                "wallet",
                "send",
                "--to",
                "0x0000000000000000000000000000000000000001",
                "--amount-wei",
                "1",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "chain_disabled")

    def test_wallet_send_paused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            self._seed_policy(tmp_home, paused=True)
            code, payload = self._run(
                "wallet",
                "send",
                "--to",
                "0x0000000000000000000000000000000000000001",
                "--amount-wei",
                "1",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "agent_paused")

    def test_wallet_send_approval_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            self._seed_policy(tmp_home, approval_required=True, approval_granted=False)
            code, payload = self._run(
                "wallet",
                "send",
                "--to",
                "0x0000000000000000000000000000000000000001",
                "--amount-wei",
                "1",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "approval_required")

    def test_wallet_send_daily_cap_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            self._seed_policy(tmp_home, max_daily_native_wei="10")
            self._seed_spend_state(tmp_home, chain="base_sepolia", amount_wei="10")
            code, payload = self._run(
                "wallet",
                "send",
                "--to",
                "0x0000000000000000000000000000000000000001",
                "--amount-wei",
                "1",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 1)
            self.assertEqual(payload["code"], "daily_cap_exceeded")

    def test_wallet_send_success_updates_spend_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            self._seed_policy(tmp_home, max_daily_native_wei="50")
            self._seed_transfer_policy_cache(
                tmp_home,
                chain="base_sepolia",
                destination="0x0000000000000000000000000000000000000001",
            )
            self._seed_transfer_approval_policy(tmp_home, chain="base_sepolia", mode="auto", native_preapproved=True)
            fake_bin = self._install_fake_cast(tmp_home)
            code, payload = self._run(
                "wallet",
                "send",
                "--to",
                "0x0000000000000000000000000000000000000001",
                "--amount-wei",
                "7",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123", "PATH": f"{fake_bin}:/usr/bin:/bin"},
            )
            self.assertEqual(code, 0)
            self.assertEqual(payload["code"], "ok")
            self.assertRegex(payload["txHash"], r"^0x[a-fA-F0-9]{64}$")
            self.assertEqual(payload["dailySpendWei"], "7")

            state_path = pathlib.Path(tmp_home) / ".xclaw-agent" / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.assertEqual(state["spendLedger"]["base_sepolia"][day_key], "7")

    def test_wallet_balance_success_with_fake_cast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            address, _ = self._seed_wallet(tmp_home)
            fake_bin = self._install_fake_cast(tmp_home)
            code, payload = self._run(
                "wallet",
                "balance",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"PATH": f"{fake_bin}:/usr/bin:/bin"},
            )
            self.assertEqual(code, 0)
            self.assertEqual(payload["code"], "ok")
            self.assertEqual(payload["address"], address)
            self.assertEqual(payload["balanceWei"], "123456789")

    def test_wallet_token_balance_success_with_fake_cast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_wallet(tmp_home)
            fake_bin = self._install_fake_cast(tmp_home)
            code, payload = self._run(
                "wallet",
                "token-balance",
                "--token",
                "0x0000000000000000000000000000000000000001",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"PATH": f"{fake_bin}:/usr/bin:/bin"},
            )
            self.assertEqual(code, 0)
            self.assertEqual(payload["code"], "ok")
            self.assertEqual(payload["token"], "0x0000000000000000000000000000000000000001")
            self.assertEqual(payload["balanceWei"], "42")

    def test_wallet_token_balance_invalid_token_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            code, payload = self._run(
                "wallet",
                "token-balance",
                "--token",
                "bad",
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
            )
            self.assertEqual(code, 2)
            self.assertEqual(payload["code"], "invalid_input")

    def test_wallet_remove_multichain_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            self._seed_multi_chain_wallet(tmp_home)
            code, payload = self._run("wallet", "remove", "--chain", "base_sepolia", "--json", home=tmp_home)
            self.assertEqual(code, 0)
            self.assertTrue(payload["removed"])

            store_path = pathlib.Path(tmp_home) / ".xclaw-agent" / "wallets.json"
            store = json.loads(store_path.read_text(encoding="utf-8"))
            self.assertIn("hardhat_local", store["chains"])
            self.assertIn("wlt_test", store["wallets"])
            self.assertEqual(store["defaultWalletId"], "wlt_test")

            code2, payload2 = self._run("wallet", "remove", "--chain", "hardhat_local", "--json", home=tmp_home)
            self.assertEqual(code2, 0)
            self.assertTrue(payload2["removed"])

            store2 = json.loads(store_path.read_text(encoding="utf-8"))
            self.assertEqual(store2["chains"], {})
            self.assertEqual(store2["wallets"], {})
            self.assertIsNone(store2["defaultWalletId"])

    @unittest.skipUnless(shutil.which("cast"), "cast is required for signing happy-path test")
    def test_wallet_sign_challenge_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home:
            address, _ = self._seed_wallet(tmp_home)
            code, payload = self._run(
                "wallet",
                "sign-challenge",
                "--message",
                self._canonical_message(),
                "--chain",
                "base_sepolia",
                "--json",
                home=tmp_home,
                extra_env={"XCLAW_WALLET_PASSPHRASE": "passphrase-123"},
            )
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["code"], "ok")
            self.assertEqual(payload["address"], address)
            self.assertEqual(payload["scheme"], "eip191_personal_sign")
            self.assertEqual(payload["challengeFormat"], "xclaw-auth-v1")
            self.assertRegex(payload["signature"], r"^0x[a-fA-F0-9]{130}$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
