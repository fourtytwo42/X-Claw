from __future__ import annotations

import json
import os
import shlex
import subprocess
from typing import Any

from xclaw_agent.liquidity_adapter import HederaSdkUnavailable


def _require_hedera_sdk() -> None:
    try:
        __import__("hedera")
    except Exception as exc:  # pragma: no cover - runtime dependency check
        raise HederaSdkUnavailable(
            "Hedera SDK module is not installed for HTS plugin bridge execution."
        ) from exc


def _bridge_command() -> list[str]:
    raw = str(os.environ.get("XCLAW_HEDERA_HTS_BRIDGE_CMD") or "").strip()
    if not raw:
        raise HederaSdkUnavailable(
            "Hedera HTS plugin bridge command is not configured. "
            "Set XCLAW_HEDERA_HTS_BRIDGE_CMD to a JSON-IO bridge executable."
        )
    parts = shlex.split(raw)
    if not parts:
        raise HederaSdkUnavailable(
            "Hedera HTS plugin bridge command is empty after parsing."
        )
    return parts


def execute_liquidity(
    *,
    action: str,
    chain: str,
    dex: str,
    position_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_hedera_sdk()
    command = _bridge_command()
    bridge_input = {
        "action": str(action or "").strip().lower(),
        "chain": str(chain or "").strip(),
        "dex": str(dex or "").strip().lower(),
        "positionType": str(position_type or "").strip().lower(),
        "payload": payload if isinstance(payload, dict) else {},
    }
    try:
        proc = subprocess.run(
            command,
            input=json.dumps(bridge_input, separators=(",", ":")),
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HederaSdkUnavailable(
            "Hedera HTS bridge timed out. Ensure bridge command is healthy and retry."
        ) from exc
    except OSError as exc:
        raise HederaSdkUnavailable(
            f"Hedera HTS bridge command failed to launch: {exc}"
        ) from exc

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        detail = stderr or stdout or f"exit {proc.returncode}"
        raise HederaSdkUnavailable(
            f"Hedera HTS bridge command failed: {detail}"
        )
    try:
        out = json.loads(stdout or "{}")
    except Exception as exc:
        raise HederaSdkUnavailable(
            "Hedera HTS bridge returned invalid JSON output."
        ) from exc
    if not isinstance(out, dict):
        raise HederaSdkUnavailable(
            "Hedera HTS bridge output must be a JSON object."
        )
    tx_hash = str(out.get("txHash") or "").strip()
    if not tx_hash:
        raise HederaSdkUnavailable(
            "Hedera HTS bridge output is missing txHash."
        )
    response: dict[str, Any] = {"txHash": tx_hash}
    if out.get("positionId") is not None:
        response["positionId"] = out.get("positionId")
    if isinstance(out.get("details"), dict):
        response["details"] = out.get("details")
    return response
