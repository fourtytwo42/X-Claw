#!/usr/bin/env python3
"""Idempotent one-command setup for X-Claw OpenClaw skill runtime."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional

APP_DIR = Path.home() / ".xclaw-agent"
POLICY_FILE = APP_DIR / "policy.json"
PATCHER = Path(__file__).resolve().parent / "openclaw_gateway_patch.py"


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
    )


def fail(message: str, action_hint: str = "") -> int:
    payload = {"ok": False, "code": "setup_failed", "message": message}
    if action_hint:
        payload["actionHint"] = action_hint
    print(json.dumps(payload))
    return 1


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
                "openclaw",
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
            run(["openclaw", "config", "set", "agents.defaults.workspace", str(workspace)])
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
    launcher_dir.mkdir(parents=True, exist_ok=True)

    launcher_path = launcher_dir / "xclaw-agent"
    target = workspace / "apps" / "agent-runtime" / "bin" / "xclaw-agent"
    if not target.exists():
        raise RuntimeError(f"Missing runtime binary: {target}")

    content = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            f'exec "{target}" "$@"',
            "",
        ]
    )
    launcher_path.write_text(content, encoding="utf-8")
    launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    os.environ["PATH"] = f"{launcher_dir}:{os.environ.get('PATH', '')}"
    return launcher_path


def ensure_ready() -> dict[str, str]:
    if shutil.which("python3") is None:
        raise RuntimeError("python3 is required")

    if shutil.which("xclaw-agent") is None:
        raise RuntimeError("xclaw-agent launcher was not found on PATH after setup")

    run(["xclaw-agent", "status", "--json"])
    run(["openclaw", "skills", "info", "xclaw-agent"])
    run(["openclaw", "skills", "list", "--eligible"])

    versions = {
        "python": run(["python3", "--version"]).stdout.strip(),
        "openclaw": run(["openclaw", "--version"]).stdout.strip(),
    }
    return versions


def _chmod_if_posix(path: Path, mode: int) -> None:
    if os.name == "nt":
        return
    os.chmod(path, mode)


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


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir.parent.parent.parent.resolve()

    try:
        openclaw_bin = ensure_openclaw(workspace)
        managed_skill = ensure_managed_skill_copy(workspace)
        launcher = ensure_launcher(workspace, openclaw_bin)
        ensure_default_policy_file(os.environ.get("XCLAW_DEFAULT_CHAIN", "base_sepolia"))
        # Portable Telegram approvals: patch OpenClaw gateway bundle idempotently.
        try:
            if os.environ.get("XCLAW_OPENCLAW_AUTO_PATCH", "1").strip().lower() not in {"0", "false", "no"} and PATCHER.exists():
                # Restart is best-effort and guarded by cooldown+lock inside patcher.
                run(["python3", str(PATCHER), "--json", "--restart"], check=False)
        except Exception:
            pass
        versions = ensure_ready()
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
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
