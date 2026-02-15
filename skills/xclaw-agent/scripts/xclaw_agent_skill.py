#!/usr/bin/env python3
"""Python-first OpenClaw skill wrapper for xclaw-agent CLI.

This wrapper standardizes command invocation and error formatting for skill usage.
It does not perform wallet signing itself; it delegates to the local xclaw-agent binary.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional


def _print_json(data: dict) -> None:
    print(json.dumps(data, separators=(",", ":")))


def _err(code: str, message: str, action_hint: Optional[str] = None, details: Optional[dict] = None, exit_code: int = 1) -> int:
    payload = {
        "ok": False,
        "code": code,
        "message": message,
    }
    if action_hint:
        payload["actionHint"] = action_hint
    if details:
        payload["details"] = details
    _print_json(payload)
    return exit_code


def _resolve_agent_binary() -> Optional[str]:
    script_dir = Path(__file__).resolve().parent
    repo_binary = script_dir.parent.parent.parent / "apps" / "agent-runtime" / "bin" / "xclaw-agent"
    if repo_binary.exists() and os.access(repo_binary, os.X_OK):
        return str(repo_binary)

    path_binary = shutil.which("xclaw-agent")
    if path_binary:
        return path_binary

    return None


def _show_sensitive() -> bool:
    # Default: redact sensitive fields because stdout is often logged/transcribed.
    return os.environ.get("XCLAW_SHOW_SENSITIVE", "").strip() == "1"


def _redact_sensitive_payload(payload: dict) -> dict:
    sensitive = payload.get("sensitive") is True
    fields = payload.get("sensitiveFields")
    if not sensitive or not isinstance(fields, list) or not fields:
        return payload
    redacted = dict(payload)
    for field in fields:
        if isinstance(field, str) and field in redacted:
            redacted[field] = "<REDACTED:SENSITIVE>"
    return redacted


def _redact_sensitive_stdout(stdout: str) -> str:
    # Support multi-JSON stdout (one JSON per line) used by some commands.
    lines = (stdout or "").splitlines()
    out_lines: list[str] = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            out_lines.append(line)
            continue
        try:
            parsed = json.loads(trimmed)
        except json.JSONDecodeError:
            out_lines.append(line)
            continue
        if isinstance(parsed, dict):
            parsed = _redact_sensitive_payload(parsed)
            out_lines.append(json.dumps(parsed, separators=(",", ":")))
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _extract_json_payload(stdout: str) -> Optional[dict]:
    trimmed = (stdout or "").strip()
    if not trimmed:
        return None
    try:
        payload = json.loads(trimmed)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and "ok" in payload and "code" in payload:
        return payload
    return None


def _require_env(*keys: str) -> Optional[int]:
    missing = [k for k in keys if not os.environ.get(k)]
    if not missing:
        return None
    return _err(
        "missing_env",
        f"Missing required environment variable(s): {', '.join(missing)}",
        "Set required env vars in skills.entries.xclaw-agent.env in ~/.openclaw/openclaw.json and restart session.",
        {"missing": missing},
        exit_code=2,
    )


def _run_agent(args: Iterable[str]) -> int:
    binary = _resolve_agent_binary()
    if not binary:
        return _err(
            "missing_binary",
            "xclaw-agent is not installed or not discoverable.",
            "Install xclaw-agent/xclaw-agentd or ensure apps/agent-runtime/bin/xclaw-agent exists and is executable.",
            exit_code=127,
        )

    cmd: List[str] = [binary, *args]
    raw_timeout = os.environ.get("XCLAW_SKILL_TIMEOUT_SEC", "").strip()
    timeout_sec = 240
    if raw_timeout:
        if not re.fullmatch(r"[0-9]+", raw_timeout):
            return _err("invalid_env", "XCLAW_SKILL_TIMEOUT_SEC must be an integer number of seconds.", exit_code=2)
        timeout_sec = int(raw_timeout)
        if timeout_sec < 1:
            return _err("invalid_env", "XCLAW_SKILL_TIMEOUT_SEC must be >= 1.", exit_code=2)

    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        return _err(
            "timeout",
            "Command timed out.",
            "Increase XCLAW_SKILL_TIMEOUT_SEC or investigate RPC/cast health, then retry.",
            {"command": cmd, "timeoutSec": timeout_sec},
            exit_code=124,
        )

    if proc.returncode == 0:
        # Preserve native CLI JSON output when available.
        out = proc.stdout.strip()
        if out and not _show_sensitive():
            out = _redact_sensitive_stdout(out)
        if out:
            print(out)
        else:
            _print_json({"ok": True, "code": "ok", "message": "Command completed successfully."})
        return 0

    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    runtime_json = _extract_json_payload(stdout)
    if runtime_json is not None:
        _print_json(runtime_json)
        return proc.returncode

    return _err(
        "agent_command_failed",
        stderr or "xclaw-agent command failed.",
        "Review command args and agent runtime status, then retry.",
        {
            "returnCode": proc.returncode,
            "stdout": stdout[:2000],
            "stderr": stderr[:2000],
            "command": cmd,
        },
        exit_code=proc.returncode,
    )


def _chain_from_env() -> str:
    return os.environ.get("XCLAW_DEFAULT_CHAIN", "base_sepolia")


def _is_hex_address(value: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", value))


def _is_uint_string(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9]+", value))


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        return _err(
            "usage",
            "Missing command.",
            "Use one of: status, dashboard, intents-poll, approval-check, trade-exec, trade-spot, report-send, chat-poll, chat-post, username-set, owner-link, faucet-request, limit-orders-create, limit-orders-cancel, limit-orders-list, limit-orders-run-once, limit-orders-run-loop, wallet-health, wallet-address, wallet-sign-challenge, wallet-send, wallet-send-token, wallet-balance, wallet-token-balance",
            exit_code=2,
        )

    cmd = argv[1]

    api_commands = {
        "status",
        "dashboard",
        "intents-poll",
        "approval-check",
        "trade-exec",
        "trade-spot",
        "report-send",
        "chat-poll",
        "chat-post",
        "username-set",
        "owner-link",
        "faucet-request",
        "limit-orders-create",
        "limit-orders-cancel",
        "limit-orders-list",
        "limit-orders-run-once",
        "limit-orders-run-loop",
    }
    wallet_commands = {
        "wallet-health",
        "wallet-address",
        "wallet-sign-challenge",
        "wallet-send",
        "wallet-send-token",
        "wallet-balance",
        "wallet-token-balance",
    }

    if cmd in api_commands:
        env_required = _require_env("XCLAW_API_BASE_URL", "XCLAW_AGENT_API_KEY", "XCLAW_DEFAULT_CHAIN")
    elif cmd in wallet_commands:
        env_required = _require_env("XCLAW_DEFAULT_CHAIN")
    else:
        env_required = None

    if env_required is not None:
        return env_required

    chain = _chain_from_env()

    if cmd == "status":
        return _run_agent(["status", "--json"])

    if cmd == "dashboard":
        return _run_agent(["dashboard", "--chain", chain, "--json"])

    if cmd == "intents-poll":
        return _run_agent(["intents", "poll", "--chain", chain, "--json"])

    if cmd == "approval-check":
        if len(argv) < 3:
            return _err("usage", "approval-check requires <intent_id>", "usage: approval-check <intent_id>", exit_code=2)
        return _run_agent(["approvals", "check", "--intent", argv[2], "--chain", chain, "--json"])

    if cmd == "trade-exec":
        if len(argv) < 3:
            return _err("usage", "trade-exec requires <intent_id>", "usage: trade-exec <intent_id>", exit_code=2)
        return _run_agent(["trade", "execute", "--intent", argv[2], "--chain", chain, "--json"])

    if cmd == "trade-spot":
        if len(argv) < 6:
            return _err(
                "usage",
                "trade-spot requires <token_in> <token_out> <amount_in> <slippage_bps>",
                "usage: trade-spot <token_in> <token_out> <amount_in> <slippage_bps>",
                exit_code=2,
            )
        token_in = argv[2]
        token_out = argv[3]
        amount_in = argv[4]
        slippage_bps = argv[5]
        # token values may be canonical symbols; validate only when they look like addresses.
        if _is_hex_address(token_in) is False and token_in.strip() == "":
            return _err("invalid_input", "token_in cannot be empty.", exit_code=2)
        if _is_hex_address(token_out) is False and token_out.strip() == "":
            return _err("invalid_input", "token_out cannot be empty.", exit_code=2)
        if amount_in.strip() == "":
            return _err("invalid_input", "amount_in cannot be empty.", exit_code=2)
        if not re.fullmatch(r"([0-9]+(\.[0-9]+)?|(wei|base|units):[0-9]+)", amount_in.strip(), flags=re.IGNORECASE):
            return _err(
                "invalid_input",
                "Invalid amount_in format.",
                "Use a number like 500 or 0.25 (human token units). For base units, use wei:<uint>.",
                {"amountIn": amount_in},
                exit_code=2,
            )
        if not _is_uint_string(slippage_bps):
            return _err("invalid_input", "Invalid slippage_bps format.", "Use an integer like 50 or 500.", {"slippageBps": slippage_bps}, exit_code=2)
        return _run_agent(
            [
                "trade",
                "spot",
                "--chain",
                chain,
                "--token-in",
                token_in,
                "--token-out",
                token_out,
                "--amount-in",
                amount_in,
                "--slippage-bps",
                slippage_bps,
                "--json",
            ]
        )

    if cmd == "report-send":
        if len(argv) < 3:
            return _err("usage", "report-send requires <trade_id>", "usage: report-send <trade_id>", exit_code=2)
        return _run_agent(["report", "send", "--trade", argv[2], "--json"])

    if cmd == "chat-poll":
        return _run_agent(["chat", "poll", "--chain", chain, "--json"])

    if cmd == "chat-post":
        if len(argv) < 3:
            return _err("usage", "chat-post requires <message>", "usage: chat-post <message>", exit_code=2)
        return _run_agent(["chat", "post", "--message", argv[2], "--chain", chain, "--json"])

    if cmd == "username-set":
        if len(argv) < 3:
            return _err("usage", "username-set requires <name>", "usage: username-set <name>", exit_code=2)
        return _run_agent(["profile", "set-name", "--name", argv[2], "--chain", chain, "--json"])

    if cmd == "owner-link":
        args = ["management-link", "--json"]
        ttl = os.environ.get("XCLAW_OWNER_LINK_TTL_SECONDS")
        if ttl:
            args.extend(["--ttl-seconds", ttl])
        return _run_agent(args)

    if cmd == "faucet-request":
        return _run_agent(["faucet-request", "--chain", chain, "--json"])

    if cmd == "wallet-health":
        return _run_agent(["wallet", "health", "--chain", chain, "--json"])

    if cmd == "wallet-address":
        return _run_agent(["wallet", "address", "--chain", chain, "--json"])

    if cmd == "wallet-sign-challenge":
        if len(argv) < 3:
            return _err(
                "usage",
                "wallet-sign-challenge requires <message>",
                "usage: wallet-sign-challenge <message>",
                exit_code=2,
            )
        message = argv[2].strip()
        if not message:
            return _err("invalid_input", "Challenge message cannot be empty.", exit_code=2)
        return _run_agent(["wallet", "sign-challenge", "--message", message, "--chain", chain, "--json"])

    if cmd == "wallet-send":
        if len(argv) < 4:
            return _err("usage", "wallet-send requires <to> <amount_wei>", "usage: wallet-send <to> <amount_wei>", exit_code=2)
        to_addr = argv[2]
        amount_wei = argv[3]
        if not _is_hex_address(to_addr):
            return _err("invalid_input", "Invalid recipient address format.", "Use 0x-prefixed 20-byte hex address.", {"to": to_addr}, exit_code=2)
        if not _is_uint_string(amount_wei):
            return _err("invalid_input", "Invalid amount_wei format.", "Use base-unit integer string, for example 10000000000000000.", {"amountWei": amount_wei}, exit_code=2)
        return _run_agent(["wallet", "send", "--to", to_addr, "--amount-wei", amount_wei, "--chain", chain, "--json"])

    if cmd == "wallet-send-token":
        if len(argv) < 5:
            return _err(
                "usage",
                "wallet-send-token requires <token> <to> <amount_wei>",
                "usage: wallet-send-token <token> <to> <amount_wei>",
                exit_code=2,
            )
        token_addr = argv[2]
        to_addr = argv[3]
        amount_wei = argv[4]
        if not _is_hex_address(token_addr):
            return _err(
                "invalid_input",
                "Invalid token address format.",
                "Use 0x-prefixed 20-byte hex address.",
                {"token": token_addr},
                exit_code=2,
            )
        if not _is_hex_address(to_addr):
            return _err("invalid_input", "Invalid recipient address format.", "Use 0x-prefixed 20-byte hex address.", {"to": to_addr}, exit_code=2)
        if not _is_uint_string(amount_wei):
            return _err("invalid_input", "Invalid amount_wei format.", "Use base-unit integer string.", {"amountWei": amount_wei}, exit_code=2)
        return _run_agent(
            [
                "wallet",
                "send-token",
                "--token",
                token_addr,
                "--to",
                to_addr,
                "--amount-wei",
                amount_wei,
                "--chain",
                chain,
                "--json",
            ]
        )

    if cmd == "wallet-balance":
        return _run_agent(["wallet", "balance", "--chain", chain, "--json"])

    if cmd == "wallet-token-balance":
        if len(argv) < 3:
            return _err("usage", "wallet-token-balance requires <token_address>", "usage: wallet-token-balance <token_address>", exit_code=2)
        token_addr = argv[2]
        if not _is_hex_address(token_addr):
            return _err("invalid_input", "Invalid token address format.", "Use 0x-prefixed 20-byte hex address.", {"token": token_addr}, exit_code=2)
        return _run_agent(["wallet", "token-balance", "--token", token_addr, "--chain", chain, "--json"])

    if cmd == "limit-orders-create":
        if len(argv) < 9:
            return _err(
                "usage",
                "limit-orders-create requires <mode> <side> <token_in> <token_out> <amount_in> <limit_price> <slippage_bps>",
                "usage: limit-orders-create <mode> <side> <token_in> <token_out> <amount_in> <limit_price> <slippage_bps>",
                exit_code=2,
            )
        mode = str(argv[2]).strip().lower()
        if mode == "mock":
            return _err(
                "unsupported_mode",
                "Mock mode is deprecated for agent skill commands.",
                "Use network mode (`real`) on base_sepolia.",
                {"mode": argv[2], "supportedMode": "real", "chain": chain},
                exit_code=2,
            )
        return _run_agent(
            [
                "limit-orders",
                "create",
                "--chain",
                chain,
                "--mode",
                mode,
                "--side",
                argv[3],
                "--token-in",
                argv[4],
                "--token-out",
                argv[5],
                "--amount-in",
                argv[6],
                "--limit-price",
                argv[7],
                "--slippage-bps",
                argv[8],
                "--json",
            ]
        )

    if cmd == "limit-orders-cancel":
        if len(argv) < 3:
            return _err("usage", "limit-orders-cancel requires <order_id>", "usage: limit-orders-cancel <order_id>", exit_code=2)
        return _run_agent(["limit-orders", "cancel", "--order-id", argv[2], "--chain", chain, "--json"])

    if cmd == "limit-orders-list":
        args = ["limit-orders", "list", "--chain", chain, "--json"]
        status = os.environ.get("XCLAW_LIMIT_ORDERS_LIST_STATUS")
        limit = os.environ.get("XCLAW_LIMIT_ORDERS_LIST_LIMIT")
        if status:
            args.extend(["--status", status])
        if limit:
            args.extend(["--limit", limit])
        return _run_agent(args)

    if cmd == "limit-orders-run-loop":
        args = ["limit-orders", "run-loop", "--chain", chain, "--json"]
        if os.environ.get("XCLAW_LIMIT_ORDERS_SYNC_LOOP", "1") != "0":
            args.append("--sync")
        iterations = os.environ.get("XCLAW_LIMIT_ORDERS_LOOP_ITERATIONS")
        interval = os.environ.get("XCLAW_LIMIT_ORDERS_LOOP_INTERVAL_SEC")
        if not iterations:
            # Default to a single iteration so the skill does not hang by default.
            iterations = "1"
        if iterations:
            args.extend(["--iterations", iterations])
        if interval:
            args.extend(["--interval-sec", interval])
        return _run_agent(args)

    if cmd == "limit-orders-run-once":
        args = ["limit-orders", "run-once", "--chain", chain, "--json"]
        if os.environ.get("XCLAW_LIMIT_ORDERS_SYNC_LOOP", "1") != "0":
            args.append("--sync")
        return _run_agent(args)

        return _err(
            "unknown_command",
            f"Unknown command: {cmd}",
            "Use one of: status, dashboard, intents-poll, approval-check, trade-exec, report-send, chat-poll, chat-post, username-set, owner-link, faucet-request, limit-orders-create, limit-orders-cancel, limit-orders-list, limit-orders-run-once, limit-orders-run-loop, wallet-health, wallet-address, wallet-sign-challenge, wallet-send, wallet-send-token, wallet-balance, wallet-token-balance",
            exit_code=2,
        )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
