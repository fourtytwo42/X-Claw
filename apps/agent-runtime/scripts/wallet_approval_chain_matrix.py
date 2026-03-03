#!/usr/bin/env python3
"""Slice 120 chain-matrix runner for wallet approval harness.

Execution order is strict:
1) hardhat_local (smoke)
2) base_sepolia (full)
3) ethereum_sepolia (full)
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any

CHAIN_ORDER = ["hardhat_local", "base_sepolia", "ethereum_sepolia"]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _trim_text(value: str, max_len: int = 800) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_harness(
    *,
    harness_bin: str,
    base_url: str,
    chain: str,
    agent_id: str,
    bootstrap_token_file: str,
    runtime_bin: str,
    agent_api_key: str,
    wallet_passphrase: str,
    hardhat_rpc_url: str,
    hardhat_evidence_report: str,
    scenario_set: str,
    json_report: str,
    expected_wallet_address: str,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        harness_bin,
        "--base-url",
        base_url,
        "--chain",
        chain,
        "--agent-id",
        agent_id,
        "--bootstrap-token-file",
        bootstrap_token_file,
        "--runtime-bin",
        runtime_bin,
        "--approve-driver",
        "management_api",
        "--scenario-set",
        scenario_set,
        "--hardhat-rpc-url",
        hardhat_rpc_url,
        "--hardhat-evidence-report",
        hardhat_evidence_report,
        "--json-report",
        json_report,
    ]
    if agent_api_key:
        cmd.extend(["--agent-api-key", agent_api_key])
    if wallet_passphrase:
        cmd.extend(["--wallet-passphrase", wallet_passphrase])
    if expected_wallet_address:
        cmd.extend(["--expected-wallet-address", expected_wallet_address])

    proc = subprocess.run(cmd, text=True, capture_output=True)
    report_payload: dict[str, Any] = {}
    report_path = pathlib.Path(json_report)
    if report_path.exists():
        try:
            report_payload = _read_json(report_path)
        except Exception:
            report_payload = {}
    return {
        "chain": chain,
        "scenarioSet": scenario_set,
        "ok": proc.returncode == 0 and bool(report_payload.get("ok")),
        "returnCode": proc.returncode,
        "command": cmd,
        "reportPath": str(report_path),
        "report": report_payload,
        "stdout": _trim_text(proc.stdout),
        "stderr": _trim_text(proc.stderr),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Slice 117 chain matrix runner")
    parser.add_argument("--base-url", default=os.environ.get("XCLAW_HARNESS_BASE_URL", "http://127.0.0.1:3000"))
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--bootstrap-token-file", required=True)
    parser.add_argument("--runtime-bin", default="apps/agent-runtime/bin/xclaw-agent")
    parser.add_argument("--harness-bin", default="apps/agent-runtime/scripts/wallet_approval_harness.py")
    parser.add_argument("--agent-api-key", default=os.environ.get("XCLAW_AGENT_API_KEY", ""))
    parser.add_argument("--wallet-passphrase", default=os.environ.get("XCLAW_WALLET_PASSPHRASE", ""))
    parser.add_argument("--hardhat-rpc-url", default="http://127.0.0.1:8545")
    parser.add_argument("--harvy-address", required=True)
    parser.add_argument("--reports-dir", default="/tmp")
    parser.add_argument("--json-report", required=True)
    parser.add_argument("--start-chain", choices=CHAIN_ORDER, default="hardhat_local")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reports_dir = pathlib.Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    hardhat_report = reports_dir / "xclaw-slice117-hardhat-smoke.json"
    base_report = reports_dir / "xclaw-slice117-base-full.json"
    eth_report = reports_dir / "xclaw-slice117-ethereum-sepolia-full.json"
    report_map = {
        "hardhat_local": hardhat_report,
        "base_sepolia": base_report,
        "ethereum_sepolia": eth_report,
    }

    steps: list[dict[str, Any]] = []
    start_idx = CHAIN_ORDER.index(args.start_chain)
    for chain in CHAIN_ORDER[start_idx:]:
        expected_wallet_address = str(args.harvy_address or "").strip() if chain == "ethereum_sepolia" else ""
        scenario_set = "smoke" if chain == "hardhat_local" else "full"
        step = _run_harness(
            harness_bin=args.harness_bin,
            base_url=args.base_url,
            chain=chain,
            agent_id=args.agent_id,
            bootstrap_token_file=args.bootstrap_token_file,
            runtime_bin=args.runtime_bin,
            agent_api_key=args.agent_api_key,
            wallet_passphrase=args.wallet_passphrase,
            hardhat_rpc_url=args.hardhat_rpc_url,
            hardhat_evidence_report=str(hardhat_report),
            scenario_set=scenario_set,
            json_report=str(report_map[chain]),
            expected_wallet_address=expected_wallet_address,
        )
        steps.append(step)
        if not step.get("ok"):
            consolidated = {
                "ok": False,
                "failedAt": chain,
                "generatedAt": _now_iso(),
                "steps": steps,
            }
            pathlib.Path(args.json_report).write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
            print(json.dumps(consolidated, separators=(",", ":")))
            return 1

    consolidated = {
        "ok": all(bool(step.get("ok")) for step in steps),
        "generatedAt": _now_iso(),
        "steps": steps,
    }
    pathlib.Path(args.json_report).write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
    print(json.dumps(consolidated, separators=(",", ":")))
    return 0 if bool(consolidated.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
