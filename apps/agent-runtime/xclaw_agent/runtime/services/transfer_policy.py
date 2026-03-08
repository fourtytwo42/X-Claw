from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TransferPolicyServiceContext:
    transfer_policy_file: Any
    read_json: Callable[[Any], dict[str, Any]]
    write_json: Callable[[Any, dict[str, Any]], None]
    utc_now: Callable[[], str]
    re_module: Any
    api_request: Callable[..., tuple[int, dict[str, Any]]]
    urllib_parse: Any
    datetime_cls: Any


def default_transfer_policy() -> dict[str, Any]:
    return {"schemaVersion": 1, "chains": {}}


def load_transfer_policy_state(ctx: TransferPolicyServiceContext) -> dict[str, Any]:
    try:
        if not ctx.transfer_policy_file.exists():
            return default_transfer_policy()
        payload = ctx.read_json(ctx.transfer_policy_file)
        if not isinstance(payload, dict):
            return default_transfer_policy()
        if payload.get("schemaVersion") != 1:
            return default_transfer_policy()
        chains = payload.get("chains")
        if not isinstance(chains, dict):
            payload["chains"] = {}
        return payload
    except Exception:
        return default_transfer_policy()


def save_transfer_policy_state(ctx: TransferPolicyServiceContext, payload: dict[str, Any]) -> None:
    if payload.get("schemaVersion") != 1:
        payload["schemaVersion"] = 1
    chains = payload.get("chains")
    if not isinstance(chains, dict):
        payload["chains"] = {}
    ctx.write_json(ctx.transfer_policy_file, payload)


def normalize_transfer_policy(ctx: TransferPolicyServiceContext, chain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    mode = str(payload.get("transferApprovalMode") or "per_transfer").strip().lower()
    if mode not in {"auto", "per_transfer"}:
        mode = "per_transfer"
    native_preapproved = bool(payload.get("nativeTransferPreapproved", False))
    raw_tokens = payload.get("allowedTransferTokens")
    out_tokens: list[str] = []
    if isinstance(raw_tokens, list):
        seen: set[str] = set()
        for token in raw_tokens:
            if not isinstance(token, str):
                continue
            normalized = token.strip().lower()
            if ctx.re_module.fullmatch(r"0x[a-f0-9]{40}", normalized) and normalized not in seen:
                seen.add(normalized)
                out_tokens.append(normalized)
    updated_at = str(payload.get("updatedAt") or "").strip() or ctx.utc_now()
    return {
        "chainKey": chain,
        "transferApprovalMode": mode,
        "nativeTransferPreapproved": native_preapproved,
        "allowedTransferTokens": out_tokens,
        "updatedAt": updated_at,
    }


def get_transfer_policy(ctx: TransferPolicyServiceContext, chain: str) -> dict[str, Any]:
    state = load_transfer_policy_state(ctx)
    chains = state.get("chains")
    if not isinstance(chains, dict):
        chains = {}
    row = chains.get(chain)
    if not isinstance(row, dict):
        row = {}
    return normalize_transfer_policy(ctx, chain, row)


def set_transfer_policy(ctx: TransferPolicyServiceContext, chain: str, policy: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_transfer_policy(ctx, chain, policy)
    state = load_transfer_policy_state(ctx)
    chains = state.get("chains")
    if not isinstance(chains, dict):
        chains = {}
        state["chains"] = chains
    chains[chain] = normalized
    save_transfer_policy_state(ctx, state)
    return normalized


def sync_transfer_policy_from_remote(ctx: TransferPolicyServiceContext, chain: str) -> dict[str, Any]:
    local = get_transfer_policy(ctx, chain)
    try:
        status_code, body = ctx.api_request("GET", f"/agent/transfer-policy?chainKey={ctx.urllib_parse.quote(chain)}")
        if status_code < 200 or status_code >= 300:
            return local
        remote_raw = body.get("transferPolicy")
        if not isinstance(remote_raw, dict):
            return local
        remote = normalize_transfer_policy(ctx, chain, remote_raw)
        try:
            local_updated = ctx.datetime_cls.fromisoformat(str(local.get("updatedAt")).replace("Z", "+00:00"))
            remote_updated = ctx.datetime_cls.fromisoformat(str(remote.get("updatedAt")).replace("Z", "+00:00"))
            if remote_updated <= local_updated:
                return local
        except Exception:
            pass
        return set_transfer_policy(ctx, chain, remote)
    except Exception:
        return local
