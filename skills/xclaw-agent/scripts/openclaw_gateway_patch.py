#!/usr/bin/env python3
"""Idempotent OpenClaw gateway patcher for X-Claw Telegram approvals.

This script patches the installed OpenClaw gateway bundle so Telegram inline-button callbacks
(`xappr|a|<tradeId>|<chainKey>`) approve X-Claw trades strictly via agent-auth, without routing
through the LLM/message pipeline.

Design constraints:
- Portable: no dependency on repo-local OpenClaw sources.
- No external patch tooling required (no git/patch).
- Safe: restart only when a new patch was applied, with cooldown + lock to avoid loops.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


MARKER = "xclaw: telegram approval callback received"
STATE_DIR = Path.home() / ".openclaw" / "xclaw"
STATE_FILE = STATE_DIR / "openclaw_patch_state.json"
LOCK_FILE = STATE_DIR / "openclaw_patch.lock"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, separators=(",", ":")))
    return 0


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass


class LockTimeout(RuntimeError):
    pass


@dataclass
class PatchResult:
    ok: bool
    patched: bool
    restarted: bool
    openclaw_version: str | None = None
    openclaw_root: str | None = None
    loader_paths: list[str] | None = None
    error: str | None = None


def _acquire_lock(timeout_sec: int = 10) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()
    while True:
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            return
        except FileExistsError:
            # Stale lock guard: if lock is old, remove it.
            try:
                age = time.time() - LOCK_FILE.stat().st_mtime
                if age > 120:
                    LOCK_FILE.unlink(missing_ok=True)  # type: ignore[arg-type]
                    continue
            except Exception:
                pass
            if time.time() - start > timeout_sec:
                raise LockTimeout("openclaw patch lock timed out")
            time.sleep(0.1)


def _release_lock() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)  # type: ignore[arg-type]
    except Exception:
        pass


def _resolve_openclaw_bin() -> str | None:
    return shutil.which("openclaw")


def _openclaw_pkg_root(openclaw_bin: str) -> Path | None:
    try:
        resolved = Path(openclaw_bin).resolve()
    except Exception:
        resolved = Path(openclaw_bin)
    # For npm global install, openclaw_bin points to .../openclaw/openclaw.mjs
    parent = resolved.parent
    if (parent / "package.json").exists():
        return parent
    # If invoked via bin symlink, walk up a few levels.
    for candidate in [parent, *parent.parents]:
        if (candidate / "package.json").exists():
            return candidate
        if candidate == candidate.parent:
            break
    return None


def _read_openclaw_version(openclaw_bin: str, pkg_root: Path | None) -> str | None:
    try:
        proc = subprocess.run([openclaw_bin, "--version"], text=True, capture_output=True, timeout=5)
        if proc.returncode == 0:
            value = (proc.stdout or "").strip()
            if value:
                return value
    except Exception:
        pass
    if pkg_root and (pkg_root / "package.json").exists():
        try:
            payload = json.loads((pkg_root / "package.json").read_text(encoding="utf-8"))
            version = payload.get("version")
            return str(version) if isinstance(version, str) and version.strip() else None
        except Exception:
            return None
    return None


def _find_loader_bundles(pkg_root: Path) -> list[Path]:
    dist_dir = pkg_root / "dist"
    if not dist_dir.exists():
        return []
    candidates = sorted(dist_dir.glob("loader-*.js"))
    # Filter to those that actually contain the callback_query handler.
    bundles: list[Path] = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if 'bot.on("callback_query"' in text:
            bundles.append(path)
    return bundles


def _inject_after_anchor(text: str, anchor: str, injection: str) -> tuple[str, bool]:
    idx = text.find(anchor)
    if idx < 0:
        return text, False
    insert_at = idx + len(anchor)
    return text[:insert_at] + injection + text[insert_at:], True


def _patch_loader_bundle(raw: str) -> tuple[str, bool, str | None]:
    if MARKER in raw:
        return raw, False, None

    # 1) DM fast-path injection: after senderUsername is defined.
    dm_anchor = 'const senderUsername = callback.from?.username ?? "";\n'
    dm_injection = (
        '\n'
        '\t\t\t\t// X-Claw Telegram approvals: approve-only inline button handling (strict, no LLM).\n'
        '\t\t\t\t// Expected callback_data: xappr|a|<tradeId>|<chainKey>\n'
        '\t\t\t\t// Allow in DMs even when inlineButtonsScope is "allowlist", gated by chatId == senderId.\n'
        '\t\t\t\tif (!isGroup && data.startsWith("xappr|") && senderId && String(chatId) === senderId) {\n'
        '\t\t\t\t\tconst parts = data.split("|").map((p) => String(p || "").trim());\n'
        '\t\t\t\t\tif (parts.length === 4 && parts[1] === "a" && parts[2] && parts[3]) {\n'
        '\t\t\t\t\t\tconst tradeId = parts[2];\n'
        '\t\t\t\t\t\tconst chainKey = parts[3];\n'
        f'\t\t\t\t\t\ttry {{ logger.info({{ tradeId, chainKey, chatId, senderId, isGroup }}, "{MARKER}"); }} catch {{}}\n'
        '\t\t\t\t\t\tconst skill = cfg?.skills?.entries?.["xclaw-agent"];\n'
        '\t\t\t\t\t\tconst env = skill?.env ?? {};\n'
        '\t\t\t\t\t\tconst rawBase = String(env?.XCLAW_API_BASE_URL ?? process.env.XCLAW_API_BASE_URL ?? "").trim().replace(/\\/+$/, "");\n'
        '\t\t\t\t\t\tconst apiBase = rawBase ? rawBase.endsWith("/api/v1") ? rawBase : `${rawBase}/api/v1` : "";\n'
        '\t\t\t\t\t\tconst apiKey = String(skill?.apiKey ?? env?.XCLAW_API_KEY ?? process.env.XCLAW_API_KEY ?? "").trim();\n'
        '\t\t\t\t\t\tif (!apiBase) { await bot.api.editMessageText(chatId, callbackMessage.message_id, "Approval failed: missing XCLAW_API_BASE_URL in OpenClaw config."); return; }\n'
        '\t\t\t\t\t\tif (!apiKey) { await bot.api.editMessageText(chatId, callbackMessage.message_id, "Approval failed: missing xclaw-agent apiKey in OpenClaw config."); return; }\n'
        '\t\t\t\t\t\ttry {\n'
        '\t\t\t\t\t\t\tconst res = await fetch(`${apiBase}/trades/${encodeURIComponent(tradeId)}/status`, {\n'
        '\t\t\t\t\t\t\t\tmethod: "POST",\n'
        '\t\t\t\t\t\t\t\theaders: { "content-type": "application/json", authorization: `Bearer ${apiKey}`, "idempotency-key": `tg-approve-${tradeId}-${callbackMessage.message_id}` },\n'
        '\t\t\t\t\t\t\t\tbody: JSON.stringify({ tradeId, fromStatus: "approval_pending", toStatus: "approved", reasonCode: null, reasonMessage: null, at: (/* @__PURE__ */ new Date()).toISOString(), source: { channel: "telegram", chainKey, senderId, to: String(chatId), messageId: String(callbackMessage.message_id) } })\n'
        '\t\t\t\t\t\t\t});\n'
        '\t\t\t\t\t\t\ttry { logger.info({ tradeId, chainKey, status: res.status }, "xclaw: telegram approval callback server response"); } catch {}\n'
        '\t\t\t\t\t\t\tif (res.ok) { await bot.api.deleteMessage(chatId, callbackMessage.message_id); return; }\n'
        '\t\t\t\t\t\t\tlet errCode = "api_error"; let errMsg = `HTTP ${res.status}`;\n'
        '\t\t\t\t\t\t\ttry { const body = await res.json(); if (typeof body?.code === "string" && body.code.trim()) errCode = body.code.trim(); if (typeof body?.message === "string" && body.message.trim()) errMsg = body.message.trim(); if (res.status === 409 && (body?.details?.currentStatus === "approved" || body?.details?.currentStatus === "filled")) { await bot.api.deleteMessage(chatId, callbackMessage.message_id); return; } } catch {}\n'
        '\t\t\t\t\t\t\tawait bot.api.editMessageText(chatId, callbackMessage.message_id, `Approval failed: ${errCode} (${errMsg}).`);\n'
        '\t\t\t\t\t\t\treturn;\n'
        '\t\t\t\t\t\t} catch (err) {\n'
        '\t\t\t\t\t\t\tawait bot.api.editMessageText(chatId, callbackMessage.message_id, `Approval failed: ${String(err)}`);\n'
        '\t\t\t\t\t\t\treturn;\n'
        '\t\t\t\t\t\t}\n'
        '\t\t\t\t\t}\n'
        '\t\t\t\t}\n'
        '\t\t\t\t\n'
    )

    out, dm_ok = _inject_after_anchor(raw, dm_anchor, dm_injection)
    if not dm_ok:
        return raw, False, "dm_anchor_not_found"

    # 2) Post-allowlist injection: place just before pagination handler in the callback_query handler.
    pagination_anchor = "const paginationMatch = data.match(/^commands_page_"
    idx = out.find(pagination_anchor)
    if idx < 0:
        return raw, False, "pagination_anchor_not_found"

    # Find the allowlist block right before pagination and insert after it.
    # Keep it simple: insert immediately before pagination.
    general_injection = (
        '\n'
        '\t\t\t\t// X-Claw Telegram approvals: approve-only inline button handling (strict, no LLM).\n'
        '\t\t\t\t// Expected callback_data: xappr|a|<tradeId>|<chainKey>\n'
        '\t\t\t\t// This runs after allowlist/group policy checks, so group callbacks are permitted only when allowed.\n'
        '\t\t\t\tif (data.startsWith("xappr|")) {\n'
        '\t\t\t\t\tconst parts = data.split("|").map((p) => String(p || "").trim());\n'
        '\t\t\t\t\tif (parts.length === 4 && parts[1] === "a" && parts[2] && parts[3]) {\n'
        '\t\t\t\t\t\tconst tradeId = parts[2];\n'
        '\t\t\t\t\t\tconst chainKey = parts[3];\n'
        f'\t\t\t\t\t\ttry {{ logger.info({{ tradeId, chainKey, chatId, senderId, isGroup }}, "{MARKER}"); }} catch {{}}\n'
        '\t\t\t\t\t\tconst skill = cfg?.skills?.entries?.["xclaw-agent"];\n'
        '\t\t\t\t\t\tconst env = skill?.env ?? {};\n'
        '\t\t\t\t\t\tconst rawBase = String(env?.XCLAW_API_BASE_URL ?? process.env.XCLAW_API_BASE_URL ?? "").trim().replace(/\\/+$/, "");\n'
        '\t\t\t\t\t\tconst apiBase = rawBase ? rawBase.endsWith("/api/v1") ? rawBase : `${rawBase}/api/v1` : "";\n'
        '\t\t\t\t\t\tconst apiKey = String(skill?.apiKey ?? env?.XCLAW_API_KEY ?? process.env.XCLAW_API_KEY ?? "").trim();\n'
        '\t\t\t\t\t\tif (!apiBase) { await bot.api.editMessageText(chatId, callbackMessage.message_id, "Approval failed: missing XCLAW_API_BASE_URL in OpenClaw config."); return; }\n'
        '\t\t\t\t\t\tif (!apiKey) { await bot.api.editMessageText(chatId, callbackMessage.message_id, "Approval failed: missing xclaw-agent apiKey in OpenClaw config."); return; }\n'
        '\t\t\t\t\t\ttry {\n'
        '\t\t\t\t\t\t\tconst res = await fetch(`${apiBase}/trades/${encodeURIComponent(tradeId)}/status`, {\n'
        '\t\t\t\t\t\t\t\tmethod: "POST",\n'
        '\t\t\t\t\t\t\t\theaders: { "content-type": "application/json", authorization: `Bearer ${apiKey}`, "idempotency-key": `tg-approve-${tradeId}-${callbackMessage.message_id}` },\n'
        '\t\t\t\t\t\t\t\tbody: JSON.stringify({ tradeId, fromStatus: "approval_pending", toStatus: "approved", reasonCode: null, reasonMessage: null, at: (/* @__PURE__ */ new Date()).toISOString(), source: { channel: "telegram", chainKey, senderId, to: String(chatId), messageId: String(callbackMessage.message_id) } })\n'
        '\t\t\t\t\t\t\t});\n'
        '\t\t\t\t\t\t\ttry { logger.info({ tradeId, chainKey, status: res.status }, "xclaw: telegram approval callback server response"); } catch {}\n'
        '\t\t\t\t\t\t\tif (res.ok) { await bot.api.deleteMessage(chatId, callbackMessage.message_id); return; }\n'
        '\t\t\t\t\t\t\tlet errCode = "api_error"; let errMsg = `HTTP ${res.status}`;\n'
        '\t\t\t\t\t\t\ttry { const body = await res.json(); if (typeof body?.code === "string" && body.code.trim()) errCode = body.code.trim(); if (typeof body?.message === "string" && body.message.trim()) errMsg = body.message.trim(); if (res.status === 409 && (body?.details?.currentStatus === "approved" || body?.details?.currentStatus === "filled")) { await bot.api.deleteMessage(chatId, callbackMessage.message_id); return; } } catch {}\n'
        '\t\t\t\t\t\t\tawait bot.api.editMessageText(chatId, callbackMessage.message_id, `Approval failed: ${errCode} (${errMsg}).`);\n'
        '\t\t\t\t\t\t\treturn;\n'
        '\t\t\t\t\t\t} catch (err) {\n'
        '\t\t\t\t\t\t\tawait bot.api.editMessageText(chatId, callbackMessage.message_id, `Approval failed: ${String(err)}`);\n'
        '\t\t\t\t\t\t\treturn;\n'
        '\t\t\t\t\t\t}\n'
        '\t\t\t\t\t}\n'
        '\t\t\t\t}\n'
        '\n'
    )

    out2 = out[:idx] + general_injection + out[idx:]
    if MARKER not in out2:
        return raw, False, "marker_missing_after_patch"
    return out2, True, None


def _restart_gateway_best_effort(cooldown_sec: int, state: dict[str, Any]) -> bool:
    now = time.time()
    last = state.get("lastRestartAtEpoch")
    try:
        last_epoch = float(last) if last is not None else 0.0
    except Exception:
        last_epoch = 0.0
    if now - last_epoch < cooldown_sec:
        return False

    # Prefer systemd user service when present.
    if shutil.which("systemctl"):
        try:
            active = subprocess.run(
                ["systemctl", "--user", "is-active", "openclaw-gateway.service"],
                text=True,
                capture_output=True,
                timeout=5,
            )
            if active.returncode == 0:
                subprocess.run(["systemctl", "--user", "restart", "openclaw-gateway.service"], timeout=15)
                state["lastRestartAtEpoch"] = now
                state["lastRestartAt"] = _utc_now()
                _write_json(STATE_FILE, state)
                return True
        except Exception:
            return False

    # Fall back: try openclaw CLI restart if available (may be a no-op in some setups).
    openclaw = _resolve_openclaw_bin()
    if openclaw:
        try:
            proc = subprocess.run([openclaw, "gateway", "restart"], text=True, capture_output=True, timeout=20)
            if proc.returncode == 0:
                state["lastRestartAtEpoch"] = now
                state["lastRestartAt"] = _utc_now()
                _write_json(STATE_FILE, state)
                return True
        except Exception:
            return False
    return False


def ensure_patched(*, restart: bool, cooldown_sec: int) -> PatchResult:
    try:
        _acquire_lock()
    except Exception as exc:
        return PatchResult(ok=False, patched=False, restarted=False, error=str(exc))

    try:
        openclaw_bin = _resolve_openclaw_bin()
        if not openclaw_bin:
            return PatchResult(ok=False, patched=False, restarted=False, error="openclaw_not_found")
        pkg_root = _openclaw_pkg_root(openclaw_bin)
        if not pkg_root:
            return PatchResult(ok=False, patched=False, restarted=False, error="openclaw_pkg_root_not_found")
        version = _read_openclaw_version(openclaw_bin, pkg_root)

        bundles = _find_loader_bundles(pkg_root)
        if not bundles:
            return PatchResult(ok=False, patched=False, restarted=False, openclaw_version=version, openclaw_root=str(pkg_root), error="loader_bundle_not_found")

        state = _read_json(STATE_FILE)
        state.setdefault("schemaVersion", 1)
        state.setdefault("bundles", {})
        state["lastAttemptAt"] = _utc_now()
        state["openclawVersion"] = version
        state["openclawRoot"] = str(pkg_root)

        # Failure backoff: if we recently failed to patch this same OpenClaw version, avoid thrashing.
        last_error_version = state.get("lastErrorVersion")
        last_error_epoch = state.get("lastErrorAtEpoch")
        try:
            last_error_epoch_f = float(last_error_epoch) if last_error_epoch is not None else 0.0
        except Exception:
            last_error_epoch_f = 0.0
        if last_error_version == version and (time.time() - last_error_epoch_f) < 600:
            return PatchResult(
                ok=False,
                patched=False,
                restarted=False,
                openclaw_version=version,
                openclaw_root=str(pkg_root),
                loader_paths=[str(p) for p in bundles],
                error=str(state.get("lastError") or "backoff_active"),
            )

        patched_any = False
        changed_any = False
        loader_paths: list[str] = []
        for bundle in bundles:
            loader_paths.append(str(bundle))
            try:
                stat = bundle.stat()
                size = int(stat.st_size)
                mtime = float(stat.st_mtime)
            except Exception:
                size = -1
                mtime = -1.0

            # Fast path: if state indicates this bundle is already patched and unchanged, avoid re-reading.
            bundles_state = state.get("bundles")
            if isinstance(bundles_state, dict):
                cached = bundles_state.get(str(bundle))
                if (
                    isinstance(cached, dict)
                    and bool(cached.get("patched")) is True
                    and cached.get("size") == size
                    and cached.get("mtime") == mtime
                    and state.get("openclawVersion") == version
                ):
                    patched_any = True
                    continue

            try:
                raw = bundle.read_text(encoding="utf-8")
            except Exception as exc:
                state["lastErrorAt"] = _utc_now()
                state["lastErrorAtEpoch"] = time.time()
                state["lastErrorVersion"] = version
                state["lastError"] = f"read_failed:{bundle}:{exc}"
                continue

            before_hash = _sha256_text(raw)
            patched_text, changed, err = _patch_loader_bundle(raw)
            if err:
                state["lastErrorAt"] = _utc_now()
                state["lastErrorAtEpoch"] = time.time()
                state["lastErrorVersion"] = version
                state["lastError"] = f"patch_failed:{bundle}:{err}"
                continue

            if changed:
                try:
                    bundle.write_text(patched_text, encoding="utf-8")
                    changed_any = True
                except Exception as exc:
                    state["lastErrorAt"] = _utc_now()
                    state["lastErrorAtEpoch"] = time.time()
                    state["lastErrorVersion"] = version
                    state["lastError"] = f"write_failed:{bundle}:{exc}"
                    continue

            after_hash = _sha256_text(patched_text)
            patched_any = patched_any or (MARKER in patched_text)
            bundles_state = state.get("bundles")
            if isinstance(bundles_state, dict):
                try:
                    stat2 = bundle.stat()
                    size2 = int(stat2.st_size)
                    mtime2 = float(stat2.st_mtime)
                except Exception:
                    size2 = size
                    mtime2 = mtime
                bundles_state[str(bundle)] = {
                    "beforeSha256": before_hash,
                    "afterSha256": after_hash,
                    "patched": MARKER in patched_text,
                    "size": size2,
                    "mtime": mtime2,
                    "updatedAt": _utc_now(),
                }

        state["lastPatchedAt"] = _utc_now() if changed_any else state.get("lastPatchedAt")
        _write_json(STATE_FILE, state)

        restarted = False
        if restart and changed_any:
            restarted = _restart_gateway_best_effort(cooldown_sec=cooldown_sec, state=state)

        return PatchResult(
            ok=patched_any,
            patched=changed_any or patched_any,
            restarted=restarted,
            openclaw_version=version,
            openclaw_root=str(pkg_root),
            loader_paths=loader_paths,
            error=None if patched_any else state.get("lastError") or None,
        )
    finally:
        _release_lock()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--restart-cooldown-sec", type=int, default=int(os.environ.get("XCLAW_OPENCLAW_PATCH_RESTART_COOLDOWN_SEC", "1800")))
    args = parser.parse_args(argv)

    result = ensure_patched(restart=bool(args.restart), cooldown_sec=int(args.restart_cooldown_sec))
    if args.json:
        return _emit(
            {
                "ok": result.ok,
                "patched": result.patched,
                "restarted": result.restarted,
                "openclawVersion": result.openclaw_version,
                "openclawRoot": result.openclaw_root,
                "loaderPaths": result.loader_paths,
                "error": result.error,
            }
        )
    if not result.ok:
        sys.stderr.write(f"[xclaw] openclaw patch failed: {result.error}\\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
