import argparse
import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from unittest import mock

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

    def test_parse_uint_text_accepts_cast_scientific_suffix(self) -> None:
        self.assertEqual(cli._parse_uint_text("20000000000000000000000 [2e22]"), 20000000000000000000000)
        self.assertEqual(cli._parse_uint_text("0x2a [4.2e1]"), 42)

    def test_wallet_wrap_native_success_uses_wrapped_token_deposit(self) -> None:
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
            mock.patch.object(cli, "_discover_wallet_tokens", return_value=([], []), create=True),
        ):
            holdings = cli._fetch_wallet_holdings("base_sepolia")
        symbols = {str(t.get("symbol")) for t in holdings.get("tokens", []) if isinstance(t, dict)}
        self.assertIn("USDCX", symbols)

    def test_resolve_token_address_uses_unique_tracked_symbol(self) -> None:
        with mock.patch.object(
            cli,
            "_tracked_tokens_for_chain",
            return_value=[{"token": "0x" + "11" * 20, "symbol": "USDCX"}],
        ), mock.patch.object(cli, "_canonical_token_map", return_value={}):
            resolved = cli._resolve_token_address("base_sepolia", "USDCX")
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
                cli._resolve_token_address("base_sepolia", "USDCX")
        self.assertEqual(ctx.exception.code, "token_symbol_ambiguous")

    def test_cmd_wallet_track_token_persists_local_state(self) -> None:
        args = argparse.Namespace(chain="base_sepolia", token="0x" + "11" * 20, json=True)
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
        tracked = (((state.get("trackedTokens") or {}).get("base_sepolia") or {}).get("addresses") or [])
        self.assertIn("0x" + "11" * 20, tracked)


if __name__ == "__main__":
    unittest.main()
