import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def _load_setup_module():
    module_path = pathlib.Path("skills/xclaw-agent/scripts/setup_agent_skill.py").resolve()
    spec = importlib.util.spec_from_file_location("xclaw_setup_agent_skill", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load setup_agent_skill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetupAgentSkillTests(unittest.TestCase):
    def _write_openclaw_config(self, home: pathlib.Path, env: dict[str, str], api_key: str = "") -> None:
        cfg = home / ".openclaw" / "openclaw.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "skills": {
                "entries": {
                    "xclaw-agent": {
                        "env": env,
                    }
                }
            }
        }
        if api_key:
            payload["skills"]["entries"]["xclaw-agent"]["apiKey"] = api_key
        cfg.write_text(json.dumps(payload), encoding="utf-8")

    def _write_backup(self, home: pathlib.Path, passphrase: str, uid: int = 1000) -> None:
        backup = home / ".xclaw-agent" / "passphrase.backup.v1.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        machine_id = "test-machine-id"
        ikm = hashlib.sha256(("|".join([machine_id, str(uid), str(home)])).encode("utf-8")).digest()
        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"xclaw-passphrase-backup-v1", info=b"xclaw")
        key = hkdf.derive(ikm)
        nonce = b"0123456789ab"
        ciphertext = AESGCM(key).encrypt(nonce, passphrase.encode("utf-8"), b"xclaw-passphrase-backup-v1")
        payload = {
            "schemaVersion": 1,
            "algo": "AES-256-GCM+HKDF-SHA256(machine-id,uid,home)",
            "nonceB64": base64.b64encode(nonce).decode("ascii"),
            "ciphertextB64": base64.b64encode(ciphertext).decode("ascii"),
        }
        backup.write_text(json.dumps(payload), encoding="utf-8")

    def test_resolve_run_loop_env_uses_openclaw_config(self) -> None:
        module = _load_setup_module()
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            self._write_openclaw_config(
                home,
                {
                    "XCLAW_API_BASE_URL": "http://127.0.0.1:3000/api/v1",
                    "XCLAW_AGENT_ID": "ag_cfg",
                    "XCLAW_AGENT_API_KEY": "cfg_key",
                    "XCLAW_DEFAULT_CHAIN": "base_sepolia",
                    "XCLAW_WALLET_PASSPHRASE": "cfg_pw",
                },
            )
            with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                values, missing = module._resolve_run_loop_env("base_sepolia")
            self.assertEqual(missing, [])
            self.assertEqual(values["XCLAW_AGENT_ID"], "ag_cfg")
            self.assertEqual(values["XCLAW_API_BASE_URL"], "http://127.0.0.1:3000/api/v1")
            self.assertEqual(values["XCLAW_WALLET_PASSPHRASE"], "cfg_pw")

    def test_resolve_run_loop_env_falls_back_to_backup_passphrase(self) -> None:
        module = _load_setup_module()
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            self._write_openclaw_config(
                home,
                {
                    "XCLAW_API_BASE_URL": "http://127.0.0.1:3000/api/v1",
                    "XCLAW_AGENT_ID": "ag_cfg",
                    "XCLAW_DEFAULT_CHAIN": "base_sepolia",
                },
                api_key="cfg_key_from_api",
            )
            with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False), mock.patch.object(
                module, "_decrypt_passphrase_backup", return_value="backup_pw"
            ):
                values, missing = module._resolve_run_loop_env("base_sepolia")
            self.assertEqual(missing, [])
            self.assertEqual(values["XCLAW_AGENT_API_KEY"], "cfg_key_from_api")
            self.assertEqual(values["XCLAW_WALLET_PASSPHRASE"], "backup_pw")

    def test_resolve_run_loop_env_missing_passphrase_when_unavailable(self) -> None:
        module = _load_setup_module()
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            self._write_openclaw_config(
                home,
                {
                    "XCLAW_API_BASE_URL": "http://127.0.0.1:3000/api/v1",
                    "XCLAW_AGENT_ID": "ag_cfg",
                    "XCLAW_AGENT_API_KEY": "cfg_key",
                    "XCLAW_DEFAULT_CHAIN": "base_sepolia",
                },
            )
            with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                values, missing = module._resolve_run_loop_env("base_sepolia")
            self.assertIn("XCLAW_WALLET_PASSPHRASE", missing)
            self.assertEqual(values["XCLAW_WALLET_PASSPHRASE"], "")

    def test_ensure_approvals_run_loop_service_fails_when_health_not_ready(self) -> None:
        module = _load_setup_module()
        resolved = {
            "XCLAW_API_BASE_URL": "http://127.0.0.1:3000/api/v1",
            "XCLAW_AGENT_ID": "ag_cfg",
            "XCLAW_AGENT_API_KEY": "cfg_key",
            "XCLAW_DEFAULT_CHAIN": "base_sepolia",
            "XCLAW_WALLET_PASSPHRASE": "pw",
            "XCLAW_APPROVALS_RUN_LOOP": "1",
        }
        with mock.patch.object(module.os, "name", "posix"), mock.patch.object(
            module.shutil, "which", side_effect=lambda name: "/bin/systemctl" if name == "systemctl" else "/usr/bin/xclaw-agent"
        ), mock.patch.object(
            module, "_resolve_run_loop_env", return_value=(resolved, [])
        ), mock.patch.object(
            module, "_write_run_loop_env", return_value=None
        ), mock.patch.object(
            module, "run", return_value=mock.Mock(stdout="", stderr="")
        ), mock.patch.object(
            module, "_probe_run_loop_health", return_value={"walletSigningReady": False, "walletSigningReasonCode": "wallet_passphrase_missing", "readinessPublishStatus": 200}
        ):
            with self.assertRaises(RuntimeError):
                module.ensure_approvals_run_loop_service("base_sepolia", runtime_bin="/usr/bin/xclaw-agent", require_healthy=True)

    def test_ensure_default_policy_file_hydrates_missing_solana_chains(self) -> None:
        module = _load_setup_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = pathlib.Path(tmp)
            app_dir = tmpdir / ".xclaw-agent"
            policy_path = app_dir / "policy.json"
            app_dir.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(
                json.dumps(
                    {
                        "paused": False,
                        "chains": {"base_sepolia": {"chain_enabled": True}},
                        "spend": {"approval_required": False, "approval_granted": True, "max_daily_native_wei": "1"},
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(module, "APP_DIR", app_dir), mock.patch.object(module, "POLICY_FILE", policy_path):
                module.ensure_default_policy_file("base_sepolia")

            payload = json.loads(policy_path.read_text(encoding="utf-8"))
            chains = payload.get("chains", {})
            self.assertTrue(bool(chains["base_sepolia"]["chain_enabled"]))
            self.assertTrue(bool(chains["solana_mainnet_beta"]["chain_enabled"]))
            self.assertTrue(bool(chains["solana_testnet"]["chain_enabled"]))
            self.assertTrue(bool(chains["solana_devnet"]["chain_enabled"]))
            self.assertTrue(bool(chains["solana_localnet"]["chain_enabled"]))

    def test_ensure_default_policy_file_keeps_existing_chain_disabled_flags(self) -> None:
        module = _load_setup_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = pathlib.Path(tmp)
            app_dir = tmpdir / ".xclaw-agent"
            policy_path = app_dir / "policy.json"
            app_dir.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(
                json.dumps(
                    {
                        "paused": False,
                        "chains": {
                            "base_sepolia": {"chain_enabled": True},
                            "solana_mainnet_beta": {"chain_enabled": False},
                        },
                        "spend": {"approval_required": True, "approval_granted": False, "max_daily_native_wei": "2"},
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(module, "APP_DIR", app_dir), mock.patch.object(module, "POLICY_FILE", policy_path):
                module.ensure_default_policy_file("base_sepolia")

            payload = json.loads(policy_path.read_text(encoding="utf-8"))
            self.assertFalse(bool(payload["chains"]["solana_mainnet_beta"]["chain_enabled"]))
            self.assertTrue(bool(payload["spend"]["approval_required"]))
            self.assertFalse(bool(payload["spend"]["approval_granted"]))
            self.assertEqual(str(payload["spend"]["max_daily_native_wei"]), "2")


if __name__ == "__main__":
    unittest.main()
