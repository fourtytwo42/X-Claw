from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from xclaw_agent.chains import get_chain


class SolanaRpcClientError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = str(code or "rpc_unavailable").strip() or "rpc_unavailable"
        self.details = details or {}


@dataclass(frozen=True)
class SolanaRpcRequest:
    endpoint: str
    headers: dict[str, str]
    provider: str


def _env_suffix(chain_key: str) -> str:
    return str(chain_key or "").strip().replace("-", "_").upper()


def _resolve_env(prefix: str, chain_key: str) -> str:
    scoped = str(os.getenv(f"{prefix}_{_env_suffix(chain_key)}", "") or "").strip()
    if scoped:
        return scoped
    return str(os.getenv(prefix, "") or "").strip()


def _provider_for_chain(chain_key: str) -> str:
    # Public/direct RPC remains primary. Paid/provider fallback is server-proxied.
    return "standard"


def _headers_for_chain(chain_key: str, provider: str) -> dict[str, str]:
    return {"content-type": "application/json"}


def rpc_candidates(chain_key: str) -> list[str]:
    if not str(chain_key or "").strip():
        raise SolanaRpcClientError("invalid_input", "Chain key is required for Solana RPC selection.")
    cfg = get_chain(chain_key, include_disabled=True)
    if not cfg:
        raise SolanaRpcClientError("unsupported_chain", f"Unsupported chain '{chain_key}'.")
    family = str(cfg.get("family") or "").strip().lower()
    if family != "solana":
        raise SolanaRpcClientError("unsupported_chain", f"Chain '{chain_key}' is not Solana family.")

    primary_override = _resolve_env("XCLAW_SOLANA_RPC_URL", chain_key)
    fallback_override = _resolve_env("XCLAW_SOLANA_RPC_FALLBACK_URL", chain_key)

    rpc_cfg = cfg.get("rpc") if isinstance(cfg.get("rpc"), dict) else {}
    candidates: list[str] = []
    for candidate in [
        primary_override,
        fallback_override,
        str((rpc_cfg or {}).get("primary") or "").strip(),
        str((rpc_cfg or {}).get("fallback") or "").strip(),
    ]:
        text = str(candidate or "").strip()
        if text and text not in candidates:
            candidates.append(text)
    if not candidates:
        raise SolanaRpcClientError("chain_config_invalid", f"No Solana RPC candidates configured for '{chain_key}'.")
    return candidates


def select_rpc_endpoint(chain_key: str) -> SolanaRpcRequest:
    provider = _provider_for_chain(chain_key)
    headers = _headers_for_chain(chain_key, provider)
    for endpoint in rpc_candidates(chain_key):
        try:
            rpc_post(
                "getLatestBlockhash",
                [{"commitment": "confirmed"}],
                chain_key=chain_key,
                rpc_url=endpoint,
                timeout_sec=2.5,
                allow_proxy_fallback=False,
            )
            return SolanaRpcRequest(endpoint=endpoint, headers=headers, provider=provider)
        except SolanaRpcClientError:
            continue
    # Fail closed after trying all endpoints.
    raise SolanaRpcClientError(
        "rpc_unavailable",
        "All Solana RPC candidates are unavailable.",
        {"chain": chain_key, "candidates": rpc_candidates(chain_key), "provider": provider},
    )


def rpc_post(
    method: str,
    params: list[Any],
    *,
    chain_key: str | None = None,
    rpc_url: str | None = None,
    timeout_sec: float = 20.0,
    allow_proxy_fallback: bool = True,
) -> Any:
    selected_chain = str(chain_key or "").strip()
    if rpc_url:
        endpoint = str(rpc_url).strip()
        provider = _provider_for_chain(selected_chain) if selected_chain else "standard"
        headers = _headers_for_chain(selected_chain, provider) if selected_chain else {"content-type": "application/json"}
        candidates = [endpoint]
    else:
        if not selected_chain:
            raise SolanaRpcClientError("invalid_input", "chain_key is required when rpc_url is not provided.")
        provider = _provider_for_chain(selected_chain)
        headers = _headers_for_chain(selected_chain, provider)
        candidates = rpc_candidates(selected_chain)

    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    last_error: SolanaRpcClientError | None = None
    for endpoint in candidates:
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = SolanaRpcClientError(
                "rpc_unavailable",
                f"Solana RPC {method} failed with HTTP {exc.code}.",
                {"method": method, "status": int(exc.code), "endpoint": endpoint, "provider": provider},
            )
            continue
        except Exception as exc:
            last_error = SolanaRpcClientError(
                "rpc_unavailable",
                f"Solana RPC {method} request failed.",
                {"method": method, "error": str(exc), "endpoint": endpoint, "provider": provider},
            )
            continue

        if isinstance(parsed, dict) and parsed.get("error"):
            last_error = SolanaRpcClientError(
                "rpc_unavailable",
                str((parsed["error"] or {}).get("message") or f"RPC {method} returned error."),
                {"method": method, "error": parsed.get("error"), "endpoint": endpoint, "provider": provider},
            )
            continue
        if not isinstance(parsed, dict) or "result" not in parsed:
            last_error = SolanaRpcClientError(
                "rpc_unavailable",
                f"Solana RPC {method} returned malformed payload.",
                {"method": method, "endpoint": endpoint, "provider": provider},
            )
            continue
        return parsed["result"]

    # Server-side paid fallback: keeps provider API keys off skill/openclaw runtime hosts.
    if allow_proxy_fallback and selected_chain:
        try:
            return _rpc_post_via_server_proxy(selected_chain, method, params, timeout_sec=timeout_sec)
        except SolanaRpcClientError as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise SolanaRpcClientError("rpc_unavailable", f"Solana RPC {method} failed.", {"method": method})


def _rpc_post_via_server_proxy(chain_key: str, method: str, params: list[Any], *, timeout_sec: float) -> Any:
    base_url = str(os.getenv("XCLAW_API_BASE_URL", "") or "").strip().rstrip("/")
    api_key = str(os.getenv("XCLAW_AGENT_API_KEY", "") or "").strip()
    if not base_url or not api_key:
        raise SolanaRpcClientError(
            "rpc_unavailable",
            "Server-side Solana RPC fallback is unavailable (missing API context).",
            {"chain": chain_key, "missingEnv": ["XCLAW_API_BASE_URL", "XCLAW_AGENT_API_KEY"]},
        )

    url = f"{base_url}/agent/solana/rpc"
    payload = json.dumps(
        {"schemaVersion": 1, "chainKey": chain_key, "method": method, "params": params},
        separators=(",", ":"),
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: dict[str, Any] = {}
        try:
            payload_json = json.loads(raw or "{}")
            if isinstance(payload_json, dict):
                parsed = payload_json
        except Exception:
            parsed = {}
        raise SolanaRpcClientError(
            str(parsed.get("code") or "rpc_unavailable"),
            str(parsed.get("message") or f"Solana fallback proxy returned HTTP {exc.code}."),
            {
                "chain": chain_key,
                "method": method,
                "status": int(exc.code),
                "provider": "tatum_fallback",
                "details": parsed.get("details"),
            },
        ) from exc
    except Exception as exc:
        raise SolanaRpcClientError(
            "rpc_unavailable",
            "Solana fallback proxy request failed.",
            {"chain": chain_key, "method": method, "provider": "tatum_fallback", "error": str(exc)},
        ) from exc

    if not isinstance(parsed, dict) or parsed.get("ok") is not True:
        raise SolanaRpcClientError(
            "rpc_unavailable",
            "Solana fallback proxy returned malformed payload.",
            {"chain": chain_key, "method": method, "provider": "tatum_fallback"},
        )
    if "result" not in parsed:
        raise SolanaRpcClientError(
            "rpc_unavailable",
            "Solana fallback proxy response missing result.",
            {"chain": chain_key, "method": method, "provider": "tatum_fallback"},
        )
    return parsed.get("result")


def rpc_health(chain_key: str) -> dict[str, Any]:
    chain = str(chain_key or "").strip()
    candidates = rpc_candidates(chain)
    probe_method = "getLatestBlockhash"
    probe_params: list[Any] = [{"commitment": "confirmed"}]
    direct_errors: list[dict[str, Any]] = []
    for endpoint in candidates:
        try:
            result = rpc_post(
                probe_method,
                probe_params,
                chain_key=chain,
                rpc_url=endpoint,
                timeout_sec=2.5,
                allow_proxy_fallback=False,
            )
            return {
                "chain": chain,
                "mode": "public_ok",
                "providerUsed": "public_direct",
                "rpcEndpoint": endpoint,
                "proxyFallbackUsed": False,
                "resultPreview": result if isinstance(result, dict) else None,
                "candidates": candidates,
                "errors": direct_errors,
            }
        except SolanaRpcClientError as exc:
            direct_errors.append(
                {
                    "endpoint": endpoint,
                    "code": exc.code,
                    "message": str(exc),
                }
            )

    try:
        result = _rpc_post_via_server_proxy(chain, probe_method, probe_params, timeout_sec=5.0)
        return {
            "chain": chain,
            "mode": "proxy_fallback_used",
            "providerUsed": "tatum_fallback",
            "rpcEndpoint": None,
            "proxyFallbackUsed": True,
            "resultPreview": result if isinstance(result, dict) else None,
            "candidates": candidates,
            "errors": direct_errors,
        }
    except SolanaRpcClientError as exc:
        return {
            "chain": chain,
            "mode": "fallback_unavailable",
            "providerUsed": "none",
            "rpcEndpoint": None,
            "proxyFallbackUsed": False,
            "resultPreview": None,
            "candidates": candidates,
            "errors": [
                *direct_errors,
                {"endpoint": "server_proxy", "code": exc.code, "message": str(exc)},
            ],
        }
