from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RuntimeStateServiceContext:
    os_module: Any
    pathlib_module: Any
    json_module: Any
    ensure_app_dir: Callable[[], None]
    load_state: Callable[[], dict[str, Any]]
    save_state: Callable[[dict[str, Any]], None]
    utc_now: Callable[[], str]
    pending_trade_intents_file: Any
    pending_spot_trade_flows_file: Any
    state_file: Any
    env_get: Callable[[str], str | None]
    extract_agent_id_from_signed_key: Callable[[str], str | None]
    wallet_store_error: type[BaseException]


def load_agent_runtime_auth(ctx: RuntimeStateServiceContext) -> tuple[str | None, str | None]:
    state = ctx.load_state()
    state_agent_id = state.get("agentId")
    state_api_key = state.get("agentApiKey")
    agent_id = str(state_agent_id).strip() if isinstance(state_agent_id, str) else None
    api_key = str(state_api_key).strip() if isinstance(state_api_key, str) else None
    return agent_id, api_key


def save_agent_runtime_auth(ctx: RuntimeStateServiceContext, agent_id: str | None, api_key: str) -> None:
    state = ctx.load_state()
    state["agentApiKey"] = api_key
    if agent_id:
        state["agentId"] = agent_id
    ctx.save_state(state)


def resolve_api_key(ctx: RuntimeStateServiceContext) -> str:
    env_api_key = str(ctx.env_get("XCLAW_AGENT_API_KEY") or "").strip()
    if env_api_key:
        return env_api_key
    _, state_api_key = load_agent_runtime_auth(ctx)
    if state_api_key:
        return state_api_key
    raise ctx.wallet_store_error("Missing required auth: XCLAW_AGENT_API_KEY (or recovered key in runtime state).")


def resolve_agent_id(ctx: RuntimeStateServiceContext, api_key: str) -> str | None:
    env_agent_id = str(ctx.env_get("XCLAW_AGENT_ID") or "").strip()
    if env_agent_id:
        return env_agent_id
    state_agent_id, _ = load_agent_runtime_auth(ctx)
    if state_agent_id:
        return state_agent_id
    return ctx.extract_agent_id_from_signed_key(api_key)


def _default_pending_payload(key: str) -> dict[str, Any]:
    return {"version": 1, key: {}}


def _load_versioned_mapping_file(ctx: RuntimeStateServiceContext, file_path: Any, mapping_key: str) -> dict[str, Any]:
    try:
        ctx.ensure_app_dir()
        if not file_path.exists():
            return _default_pending_payload(mapping_key)
        raw = file_path.read_text(encoding="utf-8")
        payload = ctx.json_module.loads(raw or "{}")
        if not isinstance(payload, dict):
            return _default_pending_payload(mapping_key)
        rows = payload.get(mapping_key)
        if not isinstance(rows, dict):
            payload[mapping_key] = {}
        if payload.get("version") != 1:
            return _default_pending_payload(mapping_key)
        return payload
    except Exception:
        return _default_pending_payload(mapping_key)


def _save_versioned_mapping_file(ctx: RuntimeStateServiceContext, file_path: Any, mapping_key: str, payload: dict[str, Any]) -> None:
    ctx.ensure_app_dir()
    if payload.get("version") != 1:
        payload["version"] = 1
    if not isinstance(payload.get(mapping_key), dict):
        payload[mapping_key] = {}
    tmp = f"{file_path}.{ctx.os_module.getpid()}.tmp"
    ctx.pathlib_module.Path(tmp).write_text(ctx.json_module.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if ctx.os_module.name != "nt":
        ctx.os_module.chmod(tmp, 0o600)
    ctx.pathlib_module.Path(tmp).replace(file_path)
    if ctx.os_module.name != "nt":
        ctx.os_module.chmod(file_path, 0o600)


def load_pending_trade_intents(ctx: RuntimeStateServiceContext) -> dict[str, Any]:
    return _load_versioned_mapping_file(ctx, ctx.pending_trade_intents_file, "intents")


def save_pending_trade_intents(ctx: RuntimeStateServiceContext, payload: dict[str, Any]) -> None:
    _save_versioned_mapping_file(ctx, ctx.pending_trade_intents_file, "intents", payload)


def get_pending_trade_intent(ctx: RuntimeStateServiceContext, intent_key: str) -> dict[str, Any] | None:
    state = load_pending_trade_intents(ctx)
    intents = state.get("intents")
    if not isinstance(intents, dict):
        return None
    entry = intents.get(intent_key)
    return entry if isinstance(entry, dict) else None


def record_pending_trade_intent(ctx: RuntimeStateServiceContext, intent_key: str, entry: dict[str, Any]) -> None:
    state = load_pending_trade_intents(ctx)
    intents = state.get("intents")
    if not isinstance(intents, dict):
        intents = {}
        state["intents"] = intents
    intents[intent_key] = {**entry, "updatedAt": ctx.utc_now()}
    save_pending_trade_intents(ctx, state)


def remove_pending_trade_intent(ctx: RuntimeStateServiceContext, intent_key: str) -> None:
    state = load_pending_trade_intents(ctx)
    intents = state.get("intents")
    if not isinstance(intents, dict):
        return
    if intent_key in intents:
        intents.pop(intent_key, None)
        save_pending_trade_intents(ctx, state)


def load_pending_spot_trade_flows(ctx: RuntimeStateServiceContext) -> dict[str, Any]:
    return _load_versioned_mapping_file(ctx, ctx.pending_spot_trade_flows_file, "flows")


def save_pending_spot_trade_flows(ctx: RuntimeStateServiceContext, payload: dict[str, Any]) -> None:
    _save_versioned_mapping_file(ctx, ctx.pending_spot_trade_flows_file, "flows", payload)


def get_pending_spot_trade_flow(ctx: RuntimeStateServiceContext, trade_id: str) -> dict[str, Any] | None:
    state = load_pending_spot_trade_flows(ctx)
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return None
    entry = flows.get(trade_id)
    return entry if isinstance(entry, dict) else None


def record_pending_spot_trade_flow(ctx: RuntimeStateServiceContext, trade_id: str, entry: dict[str, Any]) -> None:
    state = load_pending_spot_trade_flows(ctx)
    flows = state.get("flows")
    if not isinstance(flows, dict):
        flows = {}
        state["flows"] = flows
    flows[trade_id] = {**entry, "updatedAt": ctx.utc_now()}
    save_pending_spot_trade_flows(ctx, state)


def remove_pending_spot_trade_flow(ctx: RuntimeStateServiceContext, trade_id: str) -> None:
    state = load_pending_spot_trade_flows(ctx)
    flows = state.get("flows")
    if not isinstance(flows, dict):
        return
    if trade_id in flows:
        flows.pop(trade_id, None)
        save_pending_spot_trade_flows(ctx, state)
