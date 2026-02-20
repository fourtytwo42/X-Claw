#!/usr/bin/env python3
"""Idempotent one-command setup for X-Claw OpenClaw skill runtime."""

from __future__ import annotations

import json
import base64
import hashlib
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

APP_DIR = Path.home() / ".xclaw-agent"
POLICY_FILE = APP_DIR / "policy.json"
PATCHER = Path(__file__).resolve().parent / "openclaw_gateway_patch.py"
RUN_LOOP_ENV_FILE = APP_DIR / "approvals-run-loop.env"
RUN_LOOP_SERVICE = Path.home() / ".config" / "systemd" / "user" / "xclaw-agent-approvals-loop.service"
PASSPHRASE_BACKUP_FILE = APP_DIR / "passphrase.backup.v1.json"


def run(
    cmd: list[str],
    check: bool = True,
    capture: bool = True,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
        env=env,
    )


def _python_command() -> list[str]:
    if sys.executable:
        return [sys.executable]
    fallback = shutil.which("python3") or shutil.which("python")
    if fallback:
        return [fallback]
    raise RuntimeError("Python interpreter not found.")


def fail(message: str, action_hint: str = "") -> int:
    payload = {"ok": False, "code": "setup_failed", "message": message}
    if action_hint:
        payload["actionHint"] = action_hint
    print(json.dumps(payload))
    return 1


def _parse_last_json_line(text: str) -> dict | None:
    for raw in reversed((text or "").splitlines()):
        line = raw.strip()
        if not line:
            continue
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return None


def resolve_openclaw() -> Optional[Path]:
    found = shutil.which("openclaw")
    if found:
        return Path(found)

    nvm_versions = Path.home() / ".nvm" / "versions" / "node"
    if nvm_versions.exists():
        candidates = sorted(nvm_versions.glob("*/bin/openclaw"))
        if candidates:
            return candidates[-1]
    return None


def ensure_openclaw(workspace: Path) -> Path:
    openclaw_bin = resolve_openclaw()
    if openclaw_bin is None:
        raise RuntimeError("openclaw CLI not found. Install OpenClaw first, then rerun this setup command.")
    os.environ["PATH"] = f"{openclaw_bin.parent}:{os.environ.get('PATH', '')}"

    cfg = Path.home() / ".openclaw" / "openclaw.json"
    if not cfg.exists():
        run(
            [
                str(openclaw_bin),
                "onboard",
                "--non-interactive",
                "--accept-risk",
                "--mode",
                "local",
                "--flow",
                "manual",
                "--auth-choice",
                "skip",
                "--skip-channels",
                "--skip-daemon",
                "--skip-ui",
                "--skip-health",
                "--workspace",
                str(workspace),
                "--json",
            ]
        )
    else:
        # Preserve existing workspace unless explicitly requested to update.
        if os.environ.get("XCLAW_OPENCLAW_SET_WORKSPACE", "").strip().lower() in {"1", "true", "yes"}:
            run([str(openclaw_bin), "config", "set", "agents.defaults.workspace", str(workspace)])
    return openclaw_bin


def ensure_managed_skill_copy(workspace: Path) -> Path:
    source = workspace / "skills" / "xclaw-agent"
    if not source.exists():
        raise RuntimeError(f"Missing skill source directory: {source}")

    target = Path.home() / ".openclaw" / "skills" / "xclaw-agent"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    return target


def ensure_launcher(workspace: Path, openclaw_bin: Path) -> Path:
    launcher_dir = openclaw_bin.parent
    fallback_dir = APP_DIR / "bin"
    target = workspace / "apps" / "agent-runtime"
    target_entry = target / "bin" / "xclaw-agent"
    if not target_entry.exists():
        raise RuntimeError(f"Missing runtime binary: {target_entry}")

    try_dirs = [launcher_dir]
    if fallback_dir != launcher_dir:
        try_dirs.append(fallback_dir)

    write_errors: list[str] = []
    for current_dir in try_dirs:
        try:
            current_dir.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                launcher_path = current_dir / "xclaw-agent.cmd"
                python_cmd = _python_command()[0]
                content = "\n".join(
                    [
                        "@echo off",
                        "setlocal",
                        f'set "PYTHONPATH={target};%PYTHONPATH%"',
                        f'"{python_cmd}" -m xclaw_agent.cli %*',
                        "",
                    ]
                )
                launcher_path.write_text(content, encoding="utf-8")
                ps1_path = current_dir / "xclaw-agent.ps1"
                ps1_content = "\n".join(
                    [
                        "$ErrorActionPreference = 'Stop'",
                        f'$env:PYTHONPATH = "{target};" + $env:PYTHONPATH',
                        f'& "{python_cmd}" -m xclaw_agent.cli $args',
                        "",
                    ]
                )
                ps1_path.write_text(ps1_content, encoding="utf-8")
            else:
                launcher_path = current_dir / "xclaw-agent"
                content = "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        "set -euo pipefail",
                        f'exec "{target_entry}" "$@"',
                        "",
                    ]
                )
                launcher_path.write_text(content, encoding="utf-8")
                launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            os.environ["PATH"] = f"{current_dir}:{os.environ.get('PATH', '')}"
            return launcher_path
        except OSError as exc:
            write_errors.append(f"{current_dir}: {exc}")

    raise RuntimeError("Unable to create xclaw-agent launcher. " + "; ".join(write_errors))


def ensure_runtime_bin_env(launcher_path: Path) -> None:
    cfg = Path.home() / ".openclaw" / "openclaw.json"
    if not cfg.exists():
        return
    payload = json.loads(cfg.read_text(encoding="utf-8"))
    skills = payload.setdefault("skills", {})
    entries = skills.setdefault("entries", {})
    xclaw = entries.setdefault("xclaw-agent", {})
    env = xclaw.setdefault("env", {})
    current = str(env.get("XCLAW_AGENT_RUNTIME_BIN", "")).strip()
    expected = str(launcher_path)
    if current == expected:
        return
    env["XCLAW_AGENT_RUNTIME_BIN"] = expected
    cfg.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def ensure_ready(openclaw_bin: Path) -> dict[str, str]:
    python_cmd = _python_command()

    if shutil.which("xclaw-agent") is None:
        raise RuntimeError("xclaw-agent launcher was not found on PATH after setup")

    run(["xclaw-agent", "status", "--json"])
    run([str(openclaw_bin), "skills", "info", "xclaw-agent"])
    run([str(openclaw_bin), "skills", "list", "--eligible"])

    python_version = run([*python_cmd, "--version"])
    version_text = (python_version.stdout or "").strip() or (python_version.stderr or "").strip()
    versions = {
        "python": version_text,
        "openclaw": run([str(openclaw_bin), "--version"]).stdout.strip(),
    }
    return versions


def _chmod_if_posix(path: Path, mode: int) -> None:
    if os.name == "nt":
        return
    os.chmod(path, mode)


def _load_openclaw_config() -> dict[str, Any]:
    cfg = Path.home() / ".openclaw" / "openclaw.json"
    if not cfg.exists():
        return {}
    try:
        return json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _openclaw_skill_entry(config: dict[str, Any]) -> dict[str, Any]:
    skills = config.get("skills")
    if not isinstance(skills, dict):
        return {}
    entries = skills.get("entries")
    if not isinstance(entries, dict):
        return {}
    entry = entries.get("xclaw-agent")
    if not isinstance(entry, dict):
        return {}
    return entry


def _openclaw_skill_env(config: dict[str, Any]) -> dict[str, str]:
    entry = _openclaw_skill_entry(config)
    env = entry.get("env")
    if not isinstance(env, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in env.items():
        if isinstance(key, str) and isinstance(value, str):
            out[key] = value.strip()
    return out


def _openclaw_skill_api_key(config: dict[str, Any]) -> str:
    entry = _openclaw_skill_entry(config)
    value = entry.get("apiKey")
    if isinstance(value, str):
        return value.strip()
    return ""


def _decrypt_passphrase_backup(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        payload = json.loads(path.read_text(encoding="utf-8"))
        nonce_b64 = str(payload.get("nonceB64") or "").strip()
        ciphertext_b64 = str(payload.get("ciphertextB64") or "").strip()
        if not nonce_b64 or not ciphertext_b64:
            return ""

        machine_id = ""
        for candidate in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            probe = Path(candidate)
            if not probe.exists():
                continue
            raw = probe.read_text(encoding="utf-8").strip()
            if raw:
                machine_id = raw
                break

        ikm = hashlib.sha256(("|".join([machine_id, str(os.getuid()), str(Path.home())])).encode("utf-8")).digest()
        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"xclaw-passphrase-backup-v1", info=b"xclaw")
        key = hkdf.derive(ikm)
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, b"xclaw-passphrase-backup-v1")
        return plaintext.decode("utf-8").strip()
    except Exception:
        return ""


def _resolve_canonical_api_base(config_env: dict[str, str]) -> str:
    explicit = os.environ.get("XCLAW_API_BASE_URL", "").strip()
    if explicit:
        return explicit
    canonical = os.environ.get("XCLAW_INSTALL_CANONICAL_API_BASE", "").strip()
    if canonical:
        return canonical
    return str(config_env.get("XCLAW_API_BASE_URL") or "").strip()


def _resolve_run_loop_env(default_chain: str) -> tuple[dict[str, str], list[str]]:
    config = _load_openclaw_config()
    config_env = _openclaw_skill_env(config)
    cfg_api_key = _openclaw_skill_api_key(config)

    api_base = _resolve_canonical_api_base(config_env)
    bootstrap_agent_id = os.environ.get("XCLAW_BOOTSTRAP_AGENT_ID", "").strip()
    bootstrap_agent_api_key = os.environ.get("XCLAW_BOOTSTRAP_AGENT_API_KEY", "").strip()
    agent_id = os.environ.get("XCLAW_AGENT_ID", "").strip() or bootstrap_agent_id or str(config_env.get("XCLAW_AGENT_ID") or "").strip()
    api_key = (
        os.environ.get("XCLAW_AGENT_API_KEY", "").strip()
        or bootstrap_agent_api_key
        or str(config_env.get("XCLAW_AGENT_API_KEY") or "").strip()
        or cfg_api_key
    )
    chain = os.environ.get("XCLAW_DEFAULT_CHAIN", "").strip() or str(config_env.get("XCLAW_DEFAULT_CHAIN") or "").strip() or default_chain
    passphrase = (
        os.environ.get("XCLAW_WALLET_PASSPHRASE", "").strip()
        or str(config_env.get("XCLAW_WALLET_PASSPHRASE") or "").strip()
        or _decrypt_passphrase_backup(PASSPHRASE_BACKUP_FILE)
    )

    values = {
        "XCLAW_API_BASE_URL": api_base,
        "XCLAW_AGENT_ID": agent_id,
        "XCLAW_AGENT_API_KEY": api_key,
        "XCLAW_DEFAULT_CHAIN": chain,
        "XCLAW_WALLET_PASSPHRASE": passphrase,
        "XCLAW_APPROVALS_RUN_LOOP": "1",
    }
    missing = [key for key in ["XCLAW_API_BASE_URL", "XCLAW_AGENT_ID", "XCLAW_AGENT_API_KEY", "XCLAW_DEFAULT_CHAIN", "XCLAW_WALLET_PASSPHRASE"] if not values.get(key, "").strip()]
    return values, missing


def _write_run_loop_env(values: dict[str, str]) -> None:
    required = ["XCLAW_API_BASE_URL", "XCLAW_AGENT_ID", "XCLAW_AGENT_API_KEY", "XCLAW_DEFAULT_CHAIN", "XCLAW_WALLET_PASSPHRASE"]
    for key in required:
        if not str(values.get(key) or "").strip():
            raise RuntimeError(f"run-loop env write refused: missing {key}.")
    APP_DIR.mkdir(parents=True, exist_ok=True)
    _chmod_if_posix(APP_DIR, 0o700)
    tmp = RUN_LOOP_ENV_FILE.with_suffix(".env.tmp")
    lines = [f"{key}={str(values.get(key) or '').strip()}" for key in ["XCLAW_API_BASE_URL", "XCLAW_AGENT_ID", "XCLAW_AGENT_API_KEY", "XCLAW_DEFAULT_CHAIN", "XCLAW_WALLET_PASSPHRASE", "XCLAW_APPROVALS_RUN_LOOP"]]
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _chmod_if_posix(tmp, 0o600)
    os.replace(tmp, RUN_LOOP_ENV_FILE)


def _probe_run_loop_health(default_chain: str, runtime_bin: str, env_values: dict[str, str]) -> dict[str, Any]:
    env = dict(os.environ)
    env.update(env_values)
    proc = run([runtime_bin, "approvals", "run-loop", "--chain", default_chain, "--once", "--json"], check=False, capture=True, env=env)
    stdout = (proc.stdout or "").strip()
    parsed: dict[str, Any] = {}
    if stdout:
        for line in reversed(stdout.splitlines()):
            raw = line.strip()
            if not raw:
                continue
            if raw.startswith("{") and raw.endswith("}"):
                try:
                    value = json.loads(raw)
                    if isinstance(value, dict):
                        parsed = value
                        break
                except Exception:
                    continue
    if not parsed:
        parsed = {"ok": False, "code": "health_probe_output_missing", "message": (stdout or (proc.stderr or "").strip() or "health probe output missing")[:300]}
    parsed["statusCode"] = proc.returncode
    return parsed


def ensure_default_policy_file(default_chain: str) -> None:
    """Create a safe default local policy file when missing.

    Policy is required for spend actions (spot swap, transfers) and is enforced by xclaw-agent runtime.
    """
    APP_DIR.mkdir(parents=True, exist_ok=True)
    _chmod_if_posix(APP_DIR, 0o700)

    if POLICY_FILE.exists():
        # Do not mutate an existing policy; owners may have tightened it.
        return

    # NOTE: Slice 06 policy caps are temporarily native-denominated. In practice, this cap is used
    # as a coarse safety brake for any spend-like action until USD-cap pipeline slices land.
    #
    # Defaults are intentionally permissive enough for testnet usage while still being finite.
    payload = {
        "paused": False,
        "chains": {
            # Enable the default chain to avoid "policy missing" spend failures after install.
            default_chain: {"chain_enabled": True},
            # Hardhat-local is commonly used for local verification; keep enabled when present.
            "hardhat_local": {"chain_enabled": True},
        },
        "spend": {
            # Keep spot swaps usable out-of-the-box. Owners can tighten to require explicit approval.
            "approval_required": False,
            "approval_granted": True,
            # 1000e18 (1,000 "native wei-denominated units") daily cap as a coarse brake.
            "max_daily_native_wei": "1000000000000000000000",
        },
    }

    POLICY_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _chmod_if_posix(POLICY_FILE, 0o600)


def ensure_approvals_run_loop_service(default_chain: str, runtime_bin: str, require_healthy: bool) -> dict[str, object]:
    """Provision and validate systemd user wiring for continuous transfer decision consumption."""
    if os.name == "nt":
        if require_healthy:
            raise RuntimeError("Run-loop service requires Linux user-systemd; windows setup cannot satisfy strict readiness.")
        return {"enabled": False, "reason": "windows_unsupported", "envValidated": False}
    if shutil.which("systemctl") is None:
        if require_healthy:
            raise RuntimeError("Run-loop service requires systemctl --user; install cannot continue in strict readiness mode.")
        return {"enabled": False, "reason": "systemctl_missing", "envValidated": False}

    resolved, missing = _resolve_run_loop_env(default_chain)
    if missing:
        if require_healthy:
            raise RuntimeError(f"Run-loop env is missing required values: {', '.join(missing)}")
        return {"enabled": False, "reason": "env_missing", "missing": missing, "envValidated": False}

    _write_run_loop_env(resolved)

    RUN_LOOP_SERVICE.parent.mkdir(parents=True, exist_ok=True)
    unit = "\n".join(
        [
            "[Unit]",
            "Description=X-Claw agent approvals run-loop",
            "After=network-online.target",
            "",
            "[Service]",
            "Type=simple",
            f"EnvironmentFile={RUN_LOOP_ENV_FILE}",
            f"ExecStart={runtime_bin} approvals run-loop --chain {default_chain} --interval-ms 1500 --json",
            "Restart=always",
            "RestartSec=2",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        ]
    )
    RUN_LOOP_SERVICE.write_text(unit, encoding="utf-8")
    _chmod_if_posix(RUN_LOOP_SERVICE, 0o644)
    try:
        run(["systemctl", "--user", "daemon-reload"], check=True)
        run(["systemctl", "--user", "enable", "--now", RUN_LOOP_SERVICE.name], check=True)
        health = _probe_run_loop_health(default_chain, runtime_bin, resolved)
        ready = bool(health.get("walletSigningReady"))
        publish_status = int(health.get("readinessPublishStatus") or 0)
        healthy = ready and 200 <= publish_status < 300
        if require_healthy and not healthy:
            reason = str(health.get("walletSigningReasonCode") or "runtime_signing_unavailable")
            raise RuntimeError(
                f"Run-loop readiness probe failed (walletSigningReady={str(ready).lower()}, readinessPublishStatus={publish_status}, reason={reason})."
            )
        return {
            "enabled": True,
            "service": RUN_LOOP_SERVICE.name,
            "envFile": str(RUN_LOOP_ENV_FILE),
            "envValidated": True,
            "health": {
                "walletSigningReady": ready,
                "walletSigningReasonCode": health.get("walletSigningReasonCode"),
                "readinessPublishStatus": publish_status,
                "agentId": resolved.get("XCLAW_AGENT_ID"),
                "apiBaseUrl": resolved.get("XCLAW_API_BASE_URL"),
                "defaultChain": resolved.get("XCLAW_DEFAULT_CHAIN"),
                "probeCode": health.get("code"),
            },
        }
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        if require_healthy:
            raise RuntimeError(stderr or stdout or str(exc))
        return {
            "enabled": False,
            "reason": "systemctl_failed",
            "service": RUN_LOOP_SERVICE.name,
            "error": stderr or stdout or str(exc),
            "envValidated": True,
        }


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir.parent.parent.parent.resolve()

    try:
        openclaw_bin = ensure_openclaw(workspace)
        managed_skill = ensure_managed_skill_copy(workspace)
        launcher = ensure_launcher(workspace, openclaw_bin)
        ensure_runtime_bin_env(launcher)
        config_env = _openclaw_skill_env(_load_openclaw_config())
        default_chain = os.environ.get("XCLAW_DEFAULT_CHAIN", "").strip() or str(config_env.get("XCLAW_DEFAULT_CHAIN") or "").strip() or "base_sepolia"
        ensure_default_policy_file(default_chain)
        strict_setup = os.environ.get("XCLAW_SETUP_REQUIRE_RUN_LOOP_READY", "0").strip().lower() in {"1", "true", "yes"}
        runtime_bin = str(launcher)
        approvals_loop = ensure_approvals_run_loop_service(default_chain, runtime_bin=runtime_bin, require_healthy=strict_setup)
        gateway_patch: dict[str, object] | None = None
        # Portable Telegram approvals: patch OpenClaw gateway bundle idempotently.
        try:
            if os.environ.get("XCLAW_OPENCLAW_AUTO_PATCH", "1").strip().lower() not in {"0", "false", "no"} and PATCHER.exists():
                # Restart is best-effort and guarded by cooldown+lock inside patcher.
                patch_env = dict(os.environ)
                patch_env["OPENCLAW_BIN"] = str(openclaw_bin)
                patch_proc = run([*_python_command(), str(PATCHER), "--json", "--restart"], check=False, env=patch_env)
                gateway_patch = _parse_last_json_line((patch_proc.stdout or "").strip()) or {}
                if not gateway_patch:
                    gateway_patch = {
                        "ok": False,
                        "patched": False,
                        "error": "patch_output_parse_failed",
                        "stdout": (patch_proc.stdout or "").strip()[:300],
                        "stderr": (patch_proc.stderr or "").strip()[:300],
                    }
                strict_patch = os.environ.get("XCLAW_OPENCLAW_PATCH_STRICT", "1").strip().lower() not in {"0", "false", "no"}
                reported_bin = str(gateway_patch.get("openclawBin") or "").strip()
                if strict_patch and reported_bin:
                    expected_bin = str(openclaw_bin.resolve())
                    selected_bin = str(Path(reported_bin).resolve())
                    if selected_bin != expected_bin:
                        raise RuntimeError(
                            "OpenClaw gateway patch targeted a different binary than setup resolved "
                            f"(expected {expected_bin}, got {selected_bin})."
                        )
                if strict_patch and not bool(gateway_patch.get("ok")):
                    err = str(gateway_patch.get("error") or "unknown_patch_error")
                    hint = "Ensure OpenClaw is current, then rerun setup."
                    if "syntax_check_failed" in err:
                        hint = "OpenClaw bundle patch failed syntax check. Update OpenClaw and rerun setup."
                    if "write_failed" in err and "permission denied" in err.lower():
                        hint = (
                            "OpenClaw appears to be installed in a root-owned location. "
                            "Rerun the installer with sudo so gateway patching can write to the OpenClaw bundle."
                        )
                    raise RuntimeError(f"OpenClaw gateway patch failed: {err}. {hint}")
        except Exception:
            raise
        versions = ensure_ready(openclaw_bin)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        return fail(
            f"Command failed: {' '.join(exc.cmd)}",
            action_hint=stderr or stdout or "Inspect OpenClaw and xclaw-agent setup, then retry.",
        )
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc), "Ensure OpenClaw is installed and rerun this command.")

    payload = {
        "ok": True,
        "code": "setup_ok",
        "workspace": str(workspace),
        "launcher": str(launcher),
        "managedSkillPath": str(managed_skill),
        "openclawPath": str(openclaw_bin),
        "python": versions["python"],
        "openclaw": versions["openclaw"],
        "approvalsRunLoop": approvals_loop,
    }
    if gateway_patch is not None:
        payload["gatewayPatch"] = gateway_patch
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
