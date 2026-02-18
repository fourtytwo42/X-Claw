from __future__ import annotations

import json
import pathlib
from typing import Any


class ChainRegistryError(Exception):
    pass


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CHAIN_CONFIG_DIR = REPO_ROOT / "config" / "chains"

CapabilityKey = str


def _read_chain_file(path: pathlib.Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ChainRegistryError(f"Invalid chain config JSON at '{path}': {exc}") from exc
    if not isinstance(payload, dict):
        raise ChainRegistryError(f"Chain config '{path}' must be a JSON object.")
    return payload


def _is_enabled(cfg: dict[str, Any]) -> bool:
    return cfg.get("enabled", True) is not False


def list_chains(include_disabled: bool = False) -> list[dict[str, Any]]:
    if not CHAIN_CONFIG_DIR.exists():
        raise ChainRegistryError(f"Chain config directory missing: '{CHAIN_CONFIG_DIR}'")
    rows: list[dict[str, Any]] = []
    for path in sorted(CHAIN_CONFIG_DIR.glob("*.json")):
        cfg = _read_chain_file(path)
        chain_key = str(cfg.get("chainKey") or "").strip()
        if not chain_key:
            continue
        if not include_disabled and not _is_enabled(cfg):
            continue
        rows.append(cfg)
    return rows


def get_chain(chain: str, include_disabled: bool = False) -> dict[str, Any] | None:
    for cfg in list_chains(include_disabled=include_disabled):
        if str(cfg.get("chainKey") or "").strip() == chain:
            return cfg
    return None


def supported_chain_hint() -> str:
    keys = [str(row.get("chainKey")) for row in list_chains() if str(row.get("chainKey") or "").strip()]
    if not keys:
        return "No enabled chains are configured."
    return f"Use one of: {', '.join(keys)}."


def chain_enabled(chain: str) -> bool:
    return get_chain(chain) is not None


def chain_capability(chain: str, capability: CapabilityKey) -> bool:
    cfg = get_chain(chain)
    if not cfg:
        return False
    caps = cfg.get("capabilities")
    if not isinstance(caps, dict):
        return capability == "wallet"
    value = caps.get(capability)
    if isinstance(value, bool):
        return value
    return capability == "wallet"


def assert_chain_supported(chain: str) -> None:
    if not get_chain(chain):
        raise ChainRegistryError(f"Unsupported chain '{chain}'. {supported_chain_hint()}")


def assert_capability(chain: str, capability: CapabilityKey) -> None:
    assert_chain_supported(chain)
    if not chain_capability(chain, capability):
        raise ChainRegistryError(f"Chain '{chain}' does not support capability '{capability}'.")

