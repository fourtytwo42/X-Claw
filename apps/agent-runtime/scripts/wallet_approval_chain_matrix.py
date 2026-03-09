#!/usr/bin/env python3
"""Slice 120 chain-matrix runner for wallet approval harness.

Execution order is strict:
1) hardhat_local (smoke)
2) base_sepolia (full)
3) ethereum_sepolia (full)
4) solana_localnet (full)
5) solana_devnet (full)
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

CHAIN_ORDER = ["hardhat_local", "base_sepolia", "ethereum_sepolia", "solana_localnet", "solana_devnet"]
SOLANA_LOCALNET_RPC_URL = os.environ.get("XCLAW_SOLANA_LOCALNET_RPC_URL", "http://127.0.0.1:8899").strip() or "http://127.0.0.1:8899"
SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE = pathlib.Path(
    os.environ.get(
        "XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE",
        pathlib.Path("infrastructure/seed-data/solana-localnet-faucet.env").resolve().as_posix(),
    )
)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _trim_text(value: str, max_len: int = 800) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_env_file(path: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            out[key] = value.strip()
    return out


def _probe_solana_rpc(rpc_url: str, *, timeout: int = 5) -> tuple[bool, str]:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getHealth"}).encode("utf-8")
    req = urllib.request.Request(rpc_url, data=payload, method="POST", headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw) if raw else {}
        if parsed.get("result") == "ok":
            return True, "ok"
        return False, _trim_text(parsed)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return False, _trim_text(body or exc)
    except Exception as exc:
        return False, _trim_text(exc)


def _resolve_validator_command() -> list[str]:
    configured = str(os.environ.get("XCLAW_SOLANA_LOCALNET_VALIDATOR_CMD") or "").strip()
    if configured:
        return shlex.split(configured)
    for candidate in ("solana-test-validator", "agave-test-validator"):
        path = shutil.which(candidate)
        if path:
            return [path, "--reset", "--quiet"]
    return []


def _start_solana_localnet_validator(*, reports_dir: pathlib.Path, rpc_url: str) -> tuple[subprocess.Popen[str] | None, dict[str, Any]]:
    cmd = _resolve_validator_command()
    if not cmd:
        return None, {
            "ok": False,
            "code": "solana_localnet_validator_missing",
            "message": "No local Solana validator binary is installed.",
            "details": {"rpcUrl": rpc_url, "expectedCommands": ["solana-test-validator", "agave-test-validator"]},
        }

    log_path = reports_dir / "xclaw-slice244-solana-localnet-validator.log"
    log_handle = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log_handle, stderr=subprocess.STDOUT, text=True)

    def _cleanup() -> None:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        log_handle.close()

    atexit.register(_cleanup)
    for _ in range(30):
        ok, detail = _probe_solana_rpc(rpc_url, timeout=3)
        if ok:
            return proc, {"ok": True, "started": True, "command": cmd, "logPath": str(log_path), "rpcUrl": rpc_url}
        if proc.poll() is not None:
            return None, {
                "ok": False,
                "code": "solana_localnet_validator_failed",
                "message": "Local Solana validator exited before RPC became healthy.",
                "details": {"rpcUrl": rpc_url, "command": cmd, "logPath": str(log_path)},
            }
        time.sleep(2)
    return None, {
        "ok": False,
        "code": "solana_localnet_rpc_unavailable",
        "message": "Local Solana validator did not become healthy before timeout.",
        "details": {"rpcUrl": rpc_url, "command": cmd, "logPath": str(log_path)},
    }


def _ensure_solana_localnet_bootstrap(*, reports_dir: pathlib.Path) -> tuple[dict[str, str], dict[str, Any]]:
    rpc_ok, rpc_detail = _probe_solana_rpc(SOLANA_LOCALNET_RPC_URL, timeout=3)
    validator_proc: subprocess.Popen[str] | None = None
    provision: dict[str, Any] = {
        "rpcUrl": SOLANA_LOCALNET_RPC_URL,
        "bootstrapEnvFile": str(SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE),
        "rpcReady": rpc_ok,
        "rpcDetail": rpc_detail,
        "validatorStarted": False,
    }
    if not rpc_ok:
        validator_proc, provision_result = _start_solana_localnet_validator(reports_dir=reports_dir, rpc_url=SOLANA_LOCALNET_RPC_URL)
        provision.update(provision_result)
        if not provision_result.get("ok"):
            return {}, provision
        provision["validatorStarted"] = True
        rpc_ok, rpc_detail = _probe_solana_rpc(SOLANA_LOCALNET_RPC_URL, timeout=3)
        provision["rpcReady"] = rpc_ok
        provision["rpcDetail"] = rpc_detail
    bootstrap_env = os.environ.copy()
    bootstrap_env["SOLANA_LOCALNET_RPC_URL"] = SOLANA_LOCALNET_RPC_URL
    bootstrap_env["SOLANA_LOCALNET_BOOTSTRAP_OUT"] = str(SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE)
    proc = subprocess.run(["npm", "run", "solana:localnet:bootstrap"], text=True, capture_output=True, env=bootstrap_env)
    provision["bootstrapCommand"] = ["npm", "run", "solana:localnet:bootstrap"]
    provision["bootstrapStdout"] = _trim_text(proc.stdout)
    provision["bootstrapStderr"] = _trim_text(proc.stderr)
    provision["bootstrapReturnCode"] = proc.returncode
    if proc.returncode != 0:
        provision["ok"] = False
        provision["code"] = "solana_localnet_bootstrap_failed"
        provision["message"] = "Solana localnet bootstrap command failed."
        return {}, provision
    env_values = _read_env_file(SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE)
    missing = [
        key
        for key in (
            "XCLAW_SOLANA_FAUCET_SIGNER_SECRET_SOLANA_LOCALNET",
            "XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET",
            "XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET",
        )
        if not str(env_values.get(key) or "").strip()
    ]
    if missing:
        provision["ok"] = False
        provision["code"] = "solana_localnet_bootstrap_env_invalid"
        provision["message"] = "Solana localnet bootstrap env file is missing required keys."
        provision["details"] = {"missingKeys": missing}
        return {}, provision
    env_values["XCLAW_SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE"] = str(SOLANA_LOCALNET_BOOTSTRAP_ENV_FILE)
    provision["ok"] = True
    provision["validatorManaged"] = bool(validator_proc)
    provision["resolvedWrappedMint"] = str(env_values.get("XCLAW_SOLANA_FAUCET_WRAPPED_MINT_SOLANA_LOCALNET") or "").strip()
    provision["resolvedStableMint"] = str(env_values.get("XCLAW_SOLANA_FAUCET_STABLE_MINT_SOLANA_LOCALNET") or "").strip()
    return env_values, provision


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
    recipient_address: str,
    extra_env: dict[str, str] | None = None,
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
    if recipient_address:
        cmd.extend(["--recipient-address", recipient_address])

    child_env = os.environ.copy()
    if extra_env:
        child_env.update(extra_env)
    proc = subprocess.run(cmd, text=True, capture_output=True, env=child_env)
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
    parser.add_argument("--solana-wallet-address", default=os.environ.get("XCLAW_SOLANA_WALLET_ADDRESS", ""))
    parser.add_argument("--solana-recipient-address", default=os.environ.get("XCLAW_SOLANA_RECIPIENT", ""))
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
    sol_local_report = reports_dir / "xclaw-slice243-solana-localnet-full.json"
    sol_dev_report = reports_dir / "xclaw-slice243-solana-devnet-full.json"
    report_map = {
        "hardhat_local": hardhat_report,
        "base_sepolia": base_report,
        "ethereum_sepolia": eth_report,
        "solana_localnet": sol_local_report,
        "solana_devnet": sol_dev_report,
    }

    steps: list[dict[str, Any]] = []
    start_idx = CHAIN_ORDER.index(args.start_chain)
    for chain in CHAIN_ORDER[start_idx:]:
        expected_wallet_address = ""
        recipient_address = ""
        extra_env: dict[str, str] | None = None
        if chain == "ethereum_sepolia":
            expected_wallet_address = str(args.harvy_address or "").strip()
        elif chain in {"solana_localnet", "solana_devnet"}:
            expected_wallet_address = str(args.solana_wallet_address or "").strip()
            recipient_address = str(args.solana_recipient_address or "").strip()
        if chain == "solana_localnet":
            extra_env, provision = _ensure_solana_localnet_bootstrap(reports_dir=reports_dir)
            if not provision.get("ok"):
                failed_step = {
                    "chain": chain,
                    "scenarioSet": "full",
                    "ok": False,
                    "returnCode": 1,
                    "command": provision.get("bootstrapCommand") or [],
                    "reportPath": str(report_map[chain]),
                    "report": {
                        "ok": False,
                        "generatedAt": _now_iso(),
                        "chain": chain,
                        "preflight": {"solanaLocalnetProvisioning": provision},
                        "results": [],
                    },
                    "stdout": _trim_text(provision.get("bootstrapStdout") or ""),
                    "stderr": _trim_text(provision.get("bootstrapStderr") or ""),
                }
                pathlib.Path(report_map[chain]).write_text(json.dumps(failed_step["report"], indent=2), encoding="utf-8")
                steps.append(failed_step)
                consolidated = {"ok": False, "failedAt": chain, "generatedAt": _now_iso(), "steps": steps}
                pathlib.Path(args.json_report).write_text(json.dumps(consolidated, indent=2), encoding="utf-8")
                print(json.dumps(consolidated, separators=(",", ":")))
                return 1
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
            recipient_address=recipient_address,
            extra_env=extra_env,
        )
        if chain == "solana_localnet":
            report_payload = step.get("report")
            if isinstance(report_payload, dict):
                preflight = report_payload.get("preflight")
                if not isinstance(preflight, dict):
                    preflight = {}
                    report_payload["preflight"] = preflight
                preflight["solanaLocalnetProvisioning"] = provision
                pathlib.Path(report_map[chain]).write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
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
