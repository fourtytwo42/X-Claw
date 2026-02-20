#!/usr/bin/env python3
"""Slice 96 wallet/approval E2E harness (Base Sepolia-focused).

This harness executes real runtime + management API flows with Telegram dispatch
suppressed via XCLAW_TEST_HARNESS_DISABLE_TELEGRAM=1.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from http import cookiejar
from typing import Any


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_num(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _extract_trade_id(payload: dict[str, Any]) -> str:
    direct = str(payload.get("tradeId") or "").strip()
    if direct:
        return direct
    details = payload.get("details")
    if isinstance(details, dict):
        nested = str(details.get("tradeId") or "").strip()
        if nested:
            return nested
    trade = payload.get("trade")
    if isinstance(trade, dict):
        nested = str(trade.get("tradeId") or "").strip()
        if nested:
            return nested
    return ""


def _extract_transfer_approval_id(payload: dict[str, Any]) -> str:
    direct = str(payload.get("approvalId") or "").strip()
    if direct:
        return direct
    details = payload.get("details")
    if isinstance(details, dict):
        nested = str(details.get("approvalId") or "").strip()
        if nested:
            return nested
    approval = payload.get("approval")
    if isinstance(approval, dict):
        nested = str(approval.get("approvalId") or "").strip()
        if nested:
            return nested
    return ""


def _extract_liquidity_intent_id(payload: dict[str, Any]) -> str:
    direct = str(payload.get("liquidityIntentId") or "").strip()
    if direct:
        return direct
    details = payload.get("details")
    if isinstance(details, dict):
        nested = str(details.get("liquidityIntentId") or "").strip()
        if nested:
            return nested
    return ""


def _within_tolerance(before: Decimal, after: Decimal, bps: int, floor: Decimal) -> tuple[bool, Decimal, Decimal]:
    delta = abs(after - before)
    pct_window = abs(before) * Decimal(bps) / Decimal(10000)
    window = pct_window if pct_window > floor else floor
    return delta <= window, delta, window


@dataclass
class ScenarioResult:
    name: str
    ok: bool
    message: str
    details: dict[str, Any]


class HarnessError(RuntimeError):
    pass


class WalletApprovalHarness:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.base_url = args.base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.agent_id = args.agent_id
        self.chain = args.chain
        self.runtime_bin = args.runtime_bin
        self.api_key = (args.agent_api_key or os.environ.get("XCLAW_AGENT_API_KEY") or "").strip()
        if not self.api_key:
            raise HarnessError("Missing agent API key. Provide --agent-api-key or XCLAW_AGENT_API_KEY.")
        self.wallet_passphrase = (args.wallet_passphrase or os.environ.get("XCLAW_WALLET_PASSPHRASE") or "").strip()
        self.cookie_jar = cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.csrf_token = ""
        self.results: list[ScenarioResult] = []
        self.created_trade_ids: list[str] = []
        self.created_transfer_approval_ids: list[str] = []
        self.created_liquidity_intent_ids: list[str] = []
        self.created_x402_approval_ids: list[str] = []
        self.initial_state: dict[str, Any] = {}

    def _record(self, name: str, ok: bool, message: str, details: dict[str, Any] | None = None) -> None:
        payload = details or {}
        self.results.append(ScenarioResult(name=name, ok=ok, message=message, details=payload))
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")

    def _http(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        auth_mode: str = "management",
        timeout: int = 30,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.api_base}{path}"
        data = None
        headers = {"content-type": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        if auth_mode == "management":
            if self.csrf_token:
                headers["X-CSRF-Token"] = self.csrf_token
        elif auth_mode == "agent":
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url=url, data=data, method=method.upper())
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw) if raw.strip() else {}
                return int(resp.status), parsed if isinstance(parsed, dict) else {"raw": parsed}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            parsed = {}
            if raw.strip():
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"raw": raw}
            return int(exc.code), parsed if isinstance(parsed, dict) else {"raw": parsed}

    def _runtime(self, args: list[str], *, timeout: int = 240) -> tuple[int, dict[str, Any], str, str]:
        cmd = [self.runtime_bin, *args, "--json"]
        env = {
            **os.environ,
            "XCLAW_API_BASE_URL": self.api_base,
            "XCLAW_AGENT_ID": self.agent_id,
            "XCLAW_DEFAULT_CHAIN": self.chain,
            "XCLAW_AGENT_API_KEY": self.api_key,
            "XCLAW_TEST_HARNESS_DISABLE_TELEGRAM": "1",
        }
        if self.wallet_passphrase:
            env["XCLAW_WALLET_PASSPHRASE"] = self.wallet_passphrase
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
        out = (proc.stdout or "").strip()
        payload: dict[str, Any] = {}
        for line in reversed(out.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                payload = candidate
                break
        return proc.returncode, payload, proc.stdout or "", proc.stderr or ""

    def _load_bootstrap_token(self) -> str:
        data = _read_json(pathlib.Path(self.args.bootstrap_token_file))
        token = str(data.get("token") or "").strip()
        if not token:
            raise HarnessError("Bootstrap token file does not contain a token field.")
        return token

    def _bootstrap_management(self) -> None:
        token = self._load_bootstrap_token()
        status, body = self._http(
            "POST",
            "/management/session/bootstrap",
            body={"agentId": self.agent_id, "token": token},
            auth_mode="none",
        )
        if status != 200:
            raise HarnessError(f"Management bootstrap failed ({status}): {body}")
        csrf = ""
        for cookie in self.cookie_jar:
            if cookie.name == "xclaw_csrf":
                csrf = cookie.value
                break
        if not csrf:
            raise HarnessError("Management bootstrap succeeded but xclaw_csrf cookie is missing.")
        self.csrf_token = csrf

    def _management_state(self) -> dict[str, Any]:
        status, body = self._http(
            "GET",
            f"/management/agent-state?agentId={urllib.parse.quote(self.agent_id)}&chainKey={urllib.parse.quote(self.chain)}",
            auth_mode="management",
        )
        if status != 200 or not bool(body.get("ok")):
            raise HarnessError(f"management agent-state failed ({status}): {body}")
        return body

    def _trade_read(self, trade_id: str) -> dict[str, Any]:
        status, body = self._http("GET", f"/trades/{urllib.parse.quote(trade_id)}", auth_mode="agent")
        if status != 200 or not bool(body.get("ok")):
            raise HarnessError(f"trade read failed ({status}) for {trade_id}: {body}")
        trade = body.get("trade")
        if not isinstance(trade, dict):
            raise HarnessError(f"trade read missing trade object: {body}")
        return trade

    def _wait_for_trade_status(self, trade_id: str, allowed: set[str], timeout_sec: int = 240) -> dict[str, Any]:
        deadline = time.time() + timeout_sec
        last: dict[str, Any] = {}
        while time.time() < deadline:
            trade = self._trade_read(trade_id)
            status = str(trade.get("status") or "").strip().lower()
            last = trade
            if status in allowed:
                return trade
            time.sleep(2)
        raise HarnessError(f"Timed out waiting for trade {trade_id} status in {sorted(allowed)}; last={last}")

    def _post_permissions_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        status, body = self._http("POST", "/management/permissions/update", body=payload, auth_mode="management")
        if status != 200 or not bool(body.get("ok")):
            raise HarnessError(f"permissions update failed ({status}): {body}")
        return body

    def _restore_permissions(self) -> None:
        state = self.initial_state
        latest_policy = state.get("latestPolicy") if isinstance(state.get("latestPolicy"), dict) else {}
        transfer_policy = state.get("transferApprovalPolicy") if isinstance(state.get("transferApprovalPolicy"), dict) else {}
        trade_approval_mode = str(latest_policy.get("approval_mode") or "per_trade")
        allowed_tokens = latest_policy.get("allowed_tokens") if isinstance(latest_policy.get("allowed_tokens"), list) else []
        transfer_approval_mode = str(transfer_policy.get("transferApprovalMode") or "per_transfer")
        native_pre = bool(transfer_policy.get("nativeTransferPreapproved"))
        allowed_transfer_tokens = transfer_policy.get("allowedTransferTokens") if isinstance(transfer_policy.get("allowedTransferTokens"), list) else []
        payload = {
            "agentId": self.agent_id,
            "chainKey": self.chain,
            "tradeApprovalMode": trade_approval_mode,
            "allowedTokens": allowed_tokens,
            "transferApprovalMode": transfer_approval_mode,
            "nativeTransferPreapproved": native_pre,
            "allowedTransferTokens": allowed_transfer_tokens,
            "outboundTransfersEnabled": True,
            "outboundMode": "allow_all",
            "outboundWhitelistAddresses": [],
        }
        self._post_permissions_update(payload)

    def _balance_snapshot(self) -> dict[str, Decimal]:
        code, payload, _, stderr = self._runtime(["wallet", "balance", "--chain", self.chain], timeout=120)
        if code != 0 or not bool(payload.get("ok")):
            raise HarnessError(f"wallet balance failed: code={code} payload={payload} stderr={stderr}")
        out: dict[str, Decimal] = {}
        out["NATIVE"] = _safe_num(payload.get("balanceWei"))
        tokens = payload.get("tokens")
        if isinstance(tokens, list):
            for token in tokens:
                if not isinstance(token, dict):
                    continue
                symbol = str(token.get("symbol") or "").strip().upper()
                address = str(token.get("address") or "").strip().lower()
                balance = _safe_num(token.get("balanceWei"))
                if symbol:
                    out[symbol] = balance
                if address:
                    out[address] = balance
        return out

    def _wallet_address(self) -> str:
        code, payload, _, stderr = self._runtime(["wallet", "address", "--chain", self.chain], timeout=60)
        if code != 0 or not bool(payload.get("ok")):
            raise HarnessError(f"wallet address failed: code={code} payload={payload} stderr={stderr}")
        addr = str(payload.get("address") or "").strip()
        if not addr:
            raise HarnessError("wallet address response missing address")
        return addr

    def _scenario_trade_pending_approve(self) -> None:
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        code, payload, _, stderr = self._runtime(
            [
                "trade",
                "spot",
                "--chain",
                self.chain,
                "--token-in",
                "USDC",
                "--token-out",
                "WETH",
                "--amount-in",
                "20",
                "--slippage-bps",
                "100",
            ]
        )
        if code == 0 and str(payload.get("status") or "").strip().lower() != "approval_pending":
            raise HarnessError(f"trade expected approval_pending but command succeeded: {payload}")
        if code != 0 and str(payload.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"trade proposal failed unexpectedly: {payload} stderr={stderr}")
        trade_id = _extract_trade_id(payload)
        if not trade_id:
            raise HarnessError(f"trade proposal missing tradeId: {payload}")
        self.created_trade_ids.append(trade_id)

        status, body = self._http(
            "POST",
            "/management/approvals/decision",
            body={"agentId": self.agent_id, "tradeId": trade_id, "decision": "approve"},
            auth_mode="management",
        )
        if status != 200:
            raise HarnessError(f"management trade approve failed ({status}): {body}")

        code, resume_payload, _, resume_stderr = self._runtime(
            ["approvals", "resume-spot", "--trade-id", trade_id, "--chain", self.chain], timeout=420
        )
        if code != 0 or not bool(resume_payload.get("ok")):
            raise HarnessError(f"trade resume failed: {resume_payload} stderr={resume_stderr}")

        terminal = self._wait_for_trade_status(trade_id, {"filled", "failed", "rejected"}, timeout_sec=420)
        if str(terminal.get("status") or "") != "filled":
            raise HarnessError(f"trade terminal status expected filled, got {terminal}")

    def _scenario_trade_reject(self) -> None:
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        code, payload, _, stderr = self._runtime(
            [
                "trade",
                "spot",
                "--chain",
                self.chain,
                "--token-in",
                "USDC",
                "--token-out",
                "WETH",
                "--amount-in",
                "15",
                "--slippage-bps",
                "100",
            ]
        )
        if code != 0 and str(payload.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"trade reject scenario proposal failed: {payload} stderr={stderr}")
        trade_id = _extract_trade_id(payload)
        if not trade_id:
            raise HarnessError("trade reject scenario missing tradeId")
        self.created_trade_ids.append(trade_id)

        status, body = self._http(
            "POST",
            "/management/approvals/decision",
            body={"agentId": self.agent_id, "tradeId": trade_id, "decision": "reject", "reasonMessage": "harness reject path"},
            auth_mode="management",
        )
        if status != 200:
            raise HarnessError(f"management trade reject failed ({status}): {body}")

        terminal = self._wait_for_trade_status(trade_id, {"rejected"}, timeout_sec=180)
        if terminal.get("txHash"):
            raise HarnessError(f"rejected trade should not have txHash: {terminal}")

    def _scenario_trade_dedupe(self) -> None:
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        args = [
            "trade",
            "spot",
            "--chain",
            self.chain,
            "--token-in",
            "USDC",
            "--token-out",
            "WETH",
            "--amount-in",
            "12",
            "--slippage-bps",
            "100",
        ]
        c1, p1, _, _ = self._runtime(args)
        c2, p2, _, _ = self._runtime(args)
        if c1 != 0 and str(p1.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"dedupe first proposal failed: {p1}")
        if c2 != 0 and str(p2.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"dedupe second proposal failed: {p2}")
        t1 = _extract_trade_id(p1)
        t2 = _extract_trade_id(p2)
        if not t1 or not t2:
            raise HarnessError(f"dedupe trade ids missing: t1={t1} t2={t2}")
        if t1 != t2:
            raise HarnessError(f"dedupe expected same pending trade id, got {t1} vs {t2}")
        self.created_trade_ids.append(t1)

        status, body = self._http(
            "POST",
            "/management/approvals/decision",
            body={"agentId": self.agent_id, "tradeId": t1, "decision": "reject", "reasonMessage": "dedupe cleanup"},
            auth_mode="management",
        )
        if status != 200:
            raise HarnessError(f"dedupe reject cleanup failed ({status}): {body}")
        _ = self._wait_for_trade_status(t1, {"rejected"}, timeout_sec=180)

        c3, p3, _, _ = self._runtime(args)
        if c3 != 0 and str(p3.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"dedupe post-terminal proposal failed: {p3}")
        t3 = _extract_trade_id(p3)
        if not t3:
            raise HarnessError(f"dedupe post-terminal missing trade id: {p3}")
        if t3 == t1:
            raise HarnessError("dedupe expected new trade id after terminal state")
        self.created_trade_ids.append(t3)
        # cleanup
        status, body = self._http(
            "POST",
            "/management/approvals/decision",
            body={"agentId": self.agent_id, "tradeId": t3, "decision": "reject", "reasonMessage": "dedupe cleanup 2"},
            auth_mode="management",
        )
        if status == 200:
            _ = self._wait_for_trade_status(t3, {"rejected"}, timeout_sec=180)

    def _scenario_global_and_allowlist(self) -> None:
        # Global auto on
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "auto",
            }
        )
        c_auto, p_auto, _, err_auto = self._runtime(
            [
                "trade",
                "spot",
                "--chain",
                self.chain,
                "--token-in",
                "USDC",
                "--token-out",
                "WETH",
                "--amount-in",
                "5",
                "--slippage-bps",
                "100",
            ]
        )
        if c_auto != 0:
            raise HarnessError(f"global auto trade failed: {p_auto} stderr={err_auto}")

        # per-trade + allowlist via approve-allowlist-token
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
                "allowedTokens": [],
            }
        )
        c2, p2, _, err2 = self._runtime(
            [
                "trade",
                "spot",
                "--chain",
                self.chain,
                "--token-in",
                "USDC",
                "--token-out",
                "WETH",
                "--amount-in",
                "8",
                "--slippage-bps",
                "100",
            ]
        )
        if c2 != 0 and str(p2.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"allowlist proposal failed: {p2} stderr={err2}")
        trade_id = _extract_trade_id(p2)
        if not trade_id:
            raise HarnessError("allowlist proposal missing trade id")
        self.created_trade_ids.append(trade_id)

        status, body = self._http(
            "POST",
            "/management/approvals/approve-allowlist-token",
            body={"agentId": self.agent_id, "tradeId": trade_id},
            auth_mode="management",
        )
        if status != 200:
            raise HarnessError(f"approve-allowlist-token failed ({status}): {body}")

        code, resume_payload, _, resume_err = self._runtime(
            ["approvals", "resume-spot", "--trade-id", trade_id, "--chain", self.chain], timeout=420
        )
        if code != 0 or not bool(resume_payload.get("ok")):
            raise HarnessError(f"allowlist resume failed: {resume_payload} stderr={resume_err}")

        state = self._management_state()
        latest_policy = state.get("latestPolicy") if isinstance(state.get("latestPolicy"), dict) else {}
        allowed_tokens = latest_policy.get("allowed_tokens") if isinstance(latest_policy.get("allowed_tokens"), list) else []
        if not any(str(v).lower() == str(body.get("allowlistedToken") or "").lower() for v in allowed_tokens):
            raise HarnessError(f"allowlisted token missing from latest policy: {allowed_tokens}")

    def _scenario_transfer_and_x402(self) -> None:
        recipient = (self.args.recipient_address or self._wallet_address()).strip()
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "transferApprovalMode": "per_transfer",
                "nativeTransferPreapproved": False,
                "allowedTransferTokens": [],
                "outboundTransfersEnabled": True,
                "outboundMode": "allow_all",
                "outboundWhitelistAddresses": [],
            }
        )

        # Native transfer approve
        c1, p1, _, e1 = self._runtime(
            ["wallet", "send", "--to", recipient, "--amount-wei", "1000000000000000", "--chain", self.chain]
        )
        if c1 != 0 and str(p1.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"native transfer proposal failed: {p1} stderr={e1}")
        appr1 = _extract_transfer_approval_id(p1)
        if not appr1:
            raise HarnessError(f"native transfer missing approval id: {p1}")
        self.created_transfer_approval_ids.append(appr1)

        s1, b1 = self._http(
            "POST",
            "/management/transfer-approvals/decision",
            body={"agentId": self.agent_id, "approvalId": appr1, "decision": "approve", "chainKey": self.chain},
            auth_mode="management",
        )
        if s1 != 200:
            raise HarnessError(f"native transfer approve decision failed ({s1}): {b1}")
        _ = self._runtime(["approvals", "resume-transfer", "--approval-id", appr1, "--chain", self.chain], timeout=240)

        # ERC20 deny
        c2, p2, _, e2 = self._runtime(
            [
                "wallet",
                "send-token",
                "--token",
                "USDC",
                "--to",
                recipient,
                "--amount-wei",
                "1000000000000000000",
                "--chain",
                self.chain,
            ]
        )
        if c2 != 0 and str(p2.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"erc20 transfer proposal failed: {p2} stderr={e2}")
        appr2 = _extract_transfer_approval_id(p2)
        if not appr2:
            raise HarnessError(f"erc20 transfer missing approval id: {p2}")
        self.created_transfer_approval_ids.append(appr2)

        s2, b2 = self._http(
            "POST",
            "/management/transfer-approvals/decision",
            body={"agentId": self.agent_id, "approvalId": appr2, "decision": "deny", "chainKey": self.chain, "reasonMessage": "harness deny path"},
            auth_mode="management",
        )
        if s2 != 200:
            raise HarnessError(f"erc20 transfer deny decision failed ({s2}): {b2}")

        # x402 receive + pay deny/approve
        c_recv, p_recv, _, e_recv = self._runtime(
            [
                "x402",
                "receive-request",
                "--network",
                self.chain,
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "0.00001",
                "--asset-kind",
                "native",
                "--resource-description",
                "slice96 harness loopback",
            ]
        )
        if c_recv != 0 or not bool(p_recv.get("ok")):
            raise HarnessError(f"x402 receive request failed: {p_recv} stderr={e_recv}")
        payment_url = str(p_recv.get("paymentUrl") or "").strip()
        if not payment_url:
            raise HarnessError(f"x402 receive request missing paymentUrl: {p_recv}")

        code_pay, pay_payload, _, pay_err = self._runtime(
            [
                "x402",
                "pay",
                "--url",
                payment_url,
                "--network",
                self.chain,
                "--facilitator",
                "cdp",
                "--amount-atomic",
                "0.00001",
            ]
        )
        if code_pay != 0 and str(pay_payload.get("code") or "") not in {"approval_required", "approval_pending"}:
            raise HarnessError(f"x402 pay proposal failed: {pay_payload} stderr={pay_err}")
        approval = pay_payload.get("approval") if isinstance(pay_payload.get("approval"), dict) else {}
        approval_id = str(approval.get("approvalId") or "").strip()
        if not approval_id:
            raise HarnessError(f"x402 pay approval id missing: {pay_payload}")
        self.created_x402_approval_ids.append(approval_id)

        s3, b3 = self._http(
            "POST",
            "/management/transfer-approvals/decision",
            body={"agentId": self.agent_id, "approvalId": approval_id, "decision": "approve", "chainKey": self.chain},
            auth_mode="management",
        )
        if s3 != 200:
            raise HarnessError(f"x402 approve decision failed ({s3}): {b3}")
        _ = self._runtime(["x402", "pay-resume", "--approval-id", approval_id], timeout=240)

    def _scenario_liquidity_and_pause(self) -> None:
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "per_trade",
            }
        )
        c_add, p_add, _, e_add = self._runtime(
            [
                "liquidity",
                "add",
                "--chain",
                self.chain,
                "--dex",
                "uniswap_v2",
                "--token-a",
                "USDC",
                "--token-b",
                "WETH",
                "--amount-a",
                "50",
                "--amount-b",
                "0.02",
                "--slippage-bps",
                "100",
            ],
            timeout=300,
        )
        if c_add != 0 and str(p_add.get("code") or "") not in {"approval_required", "approval_pending", "liquidity_preflight_failed"}:
            raise HarnessError(f"liquidity add proposal failed: {p_add} stderr={e_add}")
        liq_id = _extract_liquidity_intent_id(p_add)
        if liq_id:
            self.created_liquidity_intent_ids.append(liq_id)
            s, b = self._http(
                "POST",
                "/management/approvals/decision",
                body={
                    "agentId": self.agent_id,
                    "subjectType": "liquidity",
                    "liquidityIntentId": liq_id,
                    "decision": "approve",
                },
                auth_mode="management",
            )
            if s != 200:
                raise HarnessError(f"liquidity approval failed ({s}): {b}")
            _ = self._runtime(["liquidity", "resume", "--intent", liq_id, "--chain", self.chain], timeout=420)

        # Pause -> spend blocked
        s_pause, b_pause = self._http("POST", "/management/pause", body={"agentId": self.agent_id}, auth_mode="management")
        if s_pause != 200:
            raise HarnessError(f"management pause failed ({s_pause}): {b_pause}")
        c_send, p_send, _, _ = self._runtime(
            ["wallet", "send", "--to", self._wallet_address(), "--amount-wei", "100000000000000", "--chain", self.chain]
        )
        if c_send == 0 or str(p_send.get("code") or "") != "agent_paused":
            raise HarnessError(f"paused spend expected agent_paused, got code={c_send} payload={p_send}")

        s_resume, b_resume = self._http("POST", "/management/resume", body={"agentId": self.agent_id}, auth_mode="management")
        if s_resume != 200:
            raise HarnessError(f"management resume failed ({s_resume}): {b_resume}")

    def _scenario_balance_reversion(self, baseline: dict[str, Decimal]) -> None:
        # Best-effort rebalance via reverse swap.
        self._post_permissions_update(
            {
                "agentId": self.agent_id,
                "chainKey": self.chain,
                "tradeApprovalMode": "auto",
            }
        )
        _ = self._runtime(
            [
                "trade",
                "spot",
                "--chain",
                self.chain,
                "--token-in",
                "WETH",
                "--token-out",
                "USDC",
                "--amount-in",
                "0.01",
                "--slippage-bps",
                "150",
            ],
            timeout=300,
        )

        after = self._balance_snapshot()
        bps = int(self.args.balance_tolerance_bps)
        native_floor_wei = Decimal("1000000000000000000") * Decimal(str(self.args.balance_tolerance_floor_native))
        stable_floor_wei = Decimal("1000000000000000000") * Decimal(str(self.args.balance_tolerance_floor_stable))

        keys = {"NATIVE", "USDC", "WETH"}
        failures: dict[str, Any] = {}
        for key in sorted(keys):
            before_v = baseline.get(key, Decimal("0"))
            after_v = after.get(key, Decimal("0"))
            floor = native_floor_wei if key == "NATIVE" else stable_floor_wei
            ok, delta, allowed = _within_tolerance(before_v, after_v, bps=bps, floor=floor)
            if not ok:
                failures[key] = {
                    "before": str(before_v),
                    "after": str(after_v),
                    "delta": str(delta),
                    "allowed": str(allowed),
                }
        if failures:
            raise HarnessError(f"balance tolerance exceeded: {failures}")

    def run(self) -> int:
        if self.args.approve_driver != "management_api":
            raise HarnessError("Slice 96 harness only supports --approve-driver management_api")

        self._record("bootstrap", True, "starting harness", {"at": _now_iso(), "chain": self.chain, "agentId": self.agent_id})
        self._bootstrap_management()
        state = self._management_state()
        self.initial_state = {
            "latestPolicy": state.get("latestPolicy") if isinstance(state.get("latestPolicy"), dict) else {},
            "transferApprovalPolicy": state.get("transferApprovalPolicy") if isinstance(state.get("transferApprovalPolicy"), dict) else {},
            "publicStatus": ((state.get("agent") or {}).get("publicStatus") if isinstance(state.get("agent"), dict) else None),
        }
        baseline_balances = self._balance_snapshot()

        scenario_funcs: list[tuple[str, Any]] = [
            ("trade_pending_approve", self._scenario_trade_pending_approve),
            ("trade_reject", self._scenario_trade_reject),
            ("trade_dedupe", self._scenario_trade_dedupe),
        ]
        if self.args.scenario_set == "full":
            scenario_funcs.extend(
                [
                    ("global_and_allowlist", self._scenario_global_and_allowlist),
                    ("transfer_and_x402", self._scenario_transfer_and_x402),
                    ("liquidity_and_pause", self._scenario_liquidity_and_pause),
                ]
            )

        for name, fn in scenario_funcs:
            try:
                fn()
                self._record(name, True, "scenario passed")
            except Exception as exc:
                self._record(name, False, "scenario failed", {"error": str(exc)})

        try:
            self._scenario_balance_reversion(baseline_balances)
            self._record("balance_reversion", True, "within tolerance window")
        except Exception as exc:
            self._record("balance_reversion", False, "tolerance check failed", {"error": str(exc)})

        try:
            self._restore_permissions()
            self._record("restore_permissions", True, "restored baseline policies")
        except Exception as exc:
            self._record("restore_permissions", False, "restore failed", {"error": str(exc)})

        if str(self.initial_state.get("publicStatus") or "").lower() == "paused":
            try:
                self._http("POST", "/management/pause", body={"agentId": self.agent_id}, auth_mode="management")
                self._record("restore_public_status", True, "re-paused agent to baseline")
            except Exception as exc:
                self._record("restore_public_status", False, "failed to restore pause status", {"error": str(exc)})

        report = {
            "ok": all(result.ok for result in self.results),
            "generatedAt": _now_iso(),
            "chain": self.chain,
            "agentId": self.agent_id,
            "scenarioSet": self.args.scenario_set,
            "approveDriver": self.args.approve_driver,
            "telegramSuppressed": True,
            "results": [
                {
                    "name": item.name,
                    "ok": item.ok,
                    "message": item.message,
                    "details": item.details,
                }
                for item in self.results
            ],
        }

        out_path = pathlib.Path(self.args.json_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(json.dumps(report, separators=(",", ":")))
        return 0 if bool(report.get("ok")) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Slice 96 wallet/approval harness")
    parser.add_argument("--base-url", default=os.environ.get("XCLAW_HARNESS_BASE_URL", "http://127.0.0.1:3000"))
    parser.add_argument("--chain", default="base_sepolia")
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--bootstrap-token-file", required=True)
    parser.add_argument("--runtime-bin", default="apps/agent-runtime/bin/xclaw-agent")
    parser.add_argument("--agent-api-key", default=os.environ.get("XCLAW_AGENT_API_KEY", ""))
    parser.add_argument("--wallet-passphrase", default=os.environ.get("XCLAW_WALLET_PASSPHRASE", ""))
    parser.add_argument("--mode", choices=["full"], default="full")
    parser.add_argument("--scenario-set", choices=["smoke", "full"], default="full")
    parser.add_argument("--approve-driver", choices=["management_api"], default="management_api")
    parser.add_argument("--balance-tolerance-bps", type=int, default=40)
    parser.add_argument("--balance-tolerance-floor-native", type=str, default="0.0005")
    parser.add_argument("--balance-tolerance-floor-stable", type=str, default="5")
    parser.add_argument("--recipient-address", default=os.environ.get("XCLAW_HARNESS_RECIPIENT", ""))
    parser.add_argument("--json-report", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        runner = WalletApprovalHarness(args)
        return runner.run()
    except HarnessError as exc:
        payload = {
            "ok": False,
            "code": "harness_failed",
            "message": str(exc),
            "at": _now_iso(),
        }
        print(json.dumps(payload, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    sys.exit(main())
