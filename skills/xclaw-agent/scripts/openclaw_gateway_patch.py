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
DECISION_ACK_MARKER = "xclaw: telegram approval decision ack"
DECISION_ACK_MARKER_V2 = "xclaw: telegram approval decision ack v2"
DECISION_ACK_MARKER_V3 = "xclaw: telegram approval decision ack v3"
QUEUED_BUTTONS_MARKER = "xclaw: telegram queued approval buttons"
QUEUED_BUTTONS_MARKER_V2 = "xclaw: telegram queued approval buttons v2"
QUEUED_BUTTONS_MARKER_V3 = "xclaw: telegram queued approval buttons v3"
LEGACY_DM_SENTINEL = 'Allow in DMs even when inlineButtonsScope is "allowlist", gated by chatId == senderId.'
# Bump when patch semantics change so we invalidate the cached "already patched" fast-path.
STATE_SCHEMA_VERSION = 18
STATE_DIR = Path.home() / ".openclaw" / "xclaw"
STATE_FILE = STATE_DIR / "openclaw_patch_state.json"
LOCK_FILE = STATE_DIR / "openclaw_patch.lock"
LEGACY_SOURCE_SNIPPET_RE = re.compile(
    r",\s*source\s*:\s*\{\s*channel\s*:\s*\"telegram\"[^}]*\}",
    flags=re.MULTILINE,
)

# Match either older "approve-only" wording or newer "inline button handling" wording.
CANONICAL_BLOCK_START = "// X-Claw Telegram approvals:"
PAGINATION_ANCHOR = "const paginationMatch = data.match(/^commands_page_"


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
    # OpenClaw gateway mode (`dist/index.js`) imports hashed bundles (e.g. `reply-*.js`).
    # We patch any bundle that contains the Telegram callback_query handler we need.
    candidates = sorted(dist_dir.rglob("*.js"))
    bundles: list[Path] = []
    for path in candidates:
        # Safety: only patch the canonical gateway reply bundle(s). Patching multiple hashed bundles
        # has proven too risky (can brick the OpenClaw CLI if we ever mis-inject).
        if not path.name.startswith("reply-"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        # Heuristic: Telegram callback_query handler with inline command pagination lives in these bundles.
        if 'bot.on("callback_query"' in text and "const paginationMatch = data.match(/^commands_page_" in text:
            bundles.append(path)
    return bundles


def _node_check_js_text(js_text: str) -> tuple[bool, str | None]:
    """
    Validate JS syntax for a would-be patched bundle. If this fails, do not write to disk.
    """
    node = shutil.which("node")
    if not node:
        return False, "node_not_found"
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_DIR / f".tmp-openclaw-bundle-check-{os.getpid()}.mjs"
        tmp.write_text(js_text, encoding="utf-8")
        proc = subprocess.run([node, "--check", str(tmp)], text=True, capture_output=True, timeout=10)
        ok = proc.returncode == 0
        if not ok:
            err = (proc.stderr or proc.stdout or "").strip()
            return False, err[:600] if err else "node_check_failed"
        return True, None
    except Exception as exc:
        return False, f"node_check_exception:{exc}"
    finally:
        try:
            (STATE_DIR / f".tmp-openclaw-bundle-check-{os.getpid()}.mjs").unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass


def _inject_after_anchor(text: str, anchor: str, injection: str) -> tuple[str, bool]:
    idx = text.find(anchor)
    if idx < 0:
        return text, False
    insert_at = idx + len(anchor)
    return text[:insert_at] + injection + text[insert_at:], True


def _patch_loader_bundle(raw: str) -> tuple[str, bool, str | None]:
    # Normalize older patch variants to avoid duplicated intercept blocks (idempotent overwrite semantics).
    normalized = False
    # v1 legacy: payload had an extra `source` field that violates X-Claw trade-status schema.
    # Remove it in-place to upgrade older patched bundles without requiring marker removal.
    raw2, n_sub = LEGACY_SOURCE_SNIPPET_RE.subn("", raw)
    if n_sub:
        raw = raw2
        normalized = True

    if LEGACY_DM_SENTINEL in raw:
        sentinel_idx = raw.find(LEGACY_DM_SENTINEL)
        # Remove from the start of the legacy X-Claw block to just before the group-policy block.
        block_start = raw.rfind("// X-Claw Telegram approvals: approve-only inline button handling (strict, no LLM).", 0, sentinel_idx)
        if block_start >= 0:
            line_start = raw.rfind("\n", 0, block_start)
            if line_start < 0:
                line_start = 0
            block_end = raw.find("if (isGroup) {", sentinel_idx)
            if block_end > sentinel_idx:
                raw = raw[:line_start] + "\n" + raw[block_end:]
                normalized = True

    # Upgrade path: if an older canonical block exists, replace it with the current canonical block.
    # This lets us ship UX tweaks (e.g. remove keyboard immediately) without telling users to reinstall OpenClaw.
    if MARKER in raw and ("xappr|r|" not in raw or DECISION_ACK_MARKER_V3 not in raw):
        idx = raw.find(PAGINATION_ANCHOR)
        if idx < 0:
            return raw, False, "pagination_anchor_not_found"
        start = raw.rfind(CANONICAL_BLOCK_START, 0, idx)
        if start >= 0:
            raw = raw[:start] + raw[idx:]
            normalized = True

    # If the canonical decision block is already present (newest version), ensure queued-message auto-buttons are too.
    if MARKER in raw and DECISION_ACK_MARKER_V3 in raw:
        changed_any = False
        if QUEUED_BUTTONS_MARKER not in raw:
            raw2, changed2, err2 = _patch_queued_buttons(raw)
            if not err2:
                raw = raw2
                changed_any = changed_any or changed2
        # Always upgrade queued-buttons injection to v3 when needed (replaces v2 in-place).
        if QUEUED_BUTTONS_MARKER_V3 not in raw:
            raw3, changed3, err3 = _patch_queued_buttons_v2(raw)
            if not err3:
                raw = raw3
                changed_any = changed_any or changed3
        normalized = normalized or changed_any
        return raw, normalized, None

    idx = raw.find(PAGINATION_ANCHOR)
    if idx < 0:
        return raw, False, "pagination_anchor_not_found"

    # Insert immediately before pagination handling (after allowlist/group policy checks).
    general_injection = (
        '\n'
        '\t\t\t// X-Claw Telegram approvals: inline button handling (strict, no LLM).\n'
        '\t\t\t// Expected callback_data: xappr|a|<tradeId>|<chainKey> (approve) OR xappr|r|<tradeId>|<chainKey> (reject)\n'
        '\t\t\t// This runs after allowlist/group policy checks.\n'
        '\t\t\tif (data.startsWith("xappr|")) {\n'
        '\t\t\t\tconst parts = data.split("|").map((p) => String(p || "").trim());\n'
        '\t\t\t\tif (parts.length === 4 && (parts[1] === "a" || parts[1] === "r") && parts[2] && parts[3]) {\n'
        '\t\t\t\t\tconst action = parts[1];\n'
        '\t\t\t\t\tconst tradeId = parts[2];\n'
        '\t\t\t\t\tconst chainKey = parts[3];\n'
        f'\t\t\t\t\ttry {{ logger.info({{ tradeId, chainKey, chatId, senderId, isGroup }}, "{MARKER}"); }} catch {{}}\n'
        '\t\t\t\t\tconst skill = cfg?.skills?.entries?.["xclaw-agent"];\n'
        '\t\t\t\t\tconst env = skill?.env ?? {};\n'
        '\t\t\t\t\tconst rawBase = String(env?.XCLAW_API_BASE_URL ?? process.env.XCLAW_API_BASE_URL ?? "").trim().replace(/\\/+$/, "");\n'
        '\t\t\t\t\tconst apiBase = rawBase ? rawBase.endsWith("/api/v1") ? rawBase : `${rawBase}/api/v1` : "";\n'
        '\t\t\t\t\tconst apiKey = String(skill?.apiKey ?? env?.XCLAW_API_KEY ?? process.env.XCLAW_API_KEY ?? "").trim();\n'
        '\t\t\t\t\tif (!apiBase) { await bot.api.editMessageText(chatId, callbackMessage.message_id, "Approval failed: missing XCLAW_API_BASE_URL in OpenClaw config."); return; }\n'
        '\t\t\t\t\tif (!apiKey) { await bot.api.editMessageText(chatId, callbackMessage.message_id, "Approval failed: missing xclaw-agent apiKey in OpenClaw config."); return; }\n'
        '\t\t\t\t\t// Reduce perceived latency: best-effort stop spinner + remove buttons immediately.\n'
        '\t\t\t\t\ttry { bot.api.answerCallbackQuery(callback.id, { text: action === "r" ? "Denying..." : "Approving...", show_alert: false }); } catch {}\n'
        '\t\t\t\t\ttry { bot.api.editMessageReplyMarkup(chatId, callbackMessage.message_id, { inline_keyboard: [] }); } catch {}\n'
        '\t\t\t\t\ttry {\n'
        '\t\t\t\t\t\tconst atEpochSec = (typeof callback?.date === "number" ? callback.date : (typeof callbackMessage?.date === "number" ? callbackMessage.date : Math.floor(Date.now() / 1000)));\n'
        '\t\t\t\t\t\tconst atIso = (/* @__PURE__ */ new Date(atEpochSec * 1000)).toISOString();\n'
        '\t\t\t\t\t\tconst res = await fetch(`${apiBase}/trades/${encodeURIComponent(tradeId)}/status`, {\n'
        '\t\t\t\t\t\t\tmethod: "POST",\n'
        '\t\t\t\t\t\t\theaders: { "content-type": "application/json", authorization: `Bearer ${apiKey}`, "idempotency-key": `tg-cb-${callback.id}` },\n'
        '\t\t\t\t\t\t\tbody: JSON.stringify({ tradeId, fromStatus: "approval_pending", toStatus: action === "r" ? "rejected" : "approved", reasonCode: action === "r" ? "approval_rejected" : null, reasonMessage: action === "r" ? "Denied via Telegram" : null, at: atIso })\n'
        '\t\t\t\t\t\t});\n'
        '\t\t\t\t\t\ttry { logger.info({ tradeId, chainKey, status: res.status }, "xclaw: telegram approval callback server response"); } catch {}\n'
        '\t\t\t\t\t\t\tif (res.ok) {\n'
        f'\t\t\t\t\t\t\t\t// {DECISION_ACK_MARKER}\n'
        f'\t\t\t\t\t\t\t\t// {DECISION_ACK_MARKER_V2}\n'
        f'\t\t\t\t\t\t\t\t// {DECISION_ACK_MARKER_V3}\n'
        '\t\t\t\t\t\t\t\t// Delete the prompt ASAP, then send a confirmation message.\n'
        '\t\t\t\t\t\t\t\ttry { await bot.api.deleteMessage(chatId, callbackMessage.message_id); } catch {}\n'
        '\t\t\t\t\t\t\t\ttry {\n'
        '\t\t\t\t\t\t\t\t\tconst promptLine = (callbackMessage.text ?? \"\").split(\"\\n\")[1] ?? \"\";\n'
        '\t\t\t\t\t\t\t\t\tconst summary = promptLine.trim() ? `\\n${promptLine.trim()}` : \"\";\n'
        '\t\t\t\t\t\t\t\t\tconst msg = `${action === \"r\" ? \"Denied\" : \"Approved\"} trade ${tradeId}${summary}\\nChain: ${chainKey}`;\n'
        '\t\t\t\t\t\t\t\t\tawait bot.api.sendMessage(chatId, msg);\n'
        '\t\t\t\t\t\t\t\t\ttry { logger.info({ tradeId, chainKey, chatId, action }, \"xclaw: telegram approval decision ack sent\"); } catch {}\n'
        '\t\t\t\t\t\t\t\t} catch (err) {\n'
        '\t\t\t\t\t\t\t\t\ttry { logger.error({ tradeId, chainKey, chatId, action, err: String(err) }, \"xclaw: telegram approval decision ack failed\"); } catch {}\n'
        '\t\t\t\t\t\t\t\t}\n'
        '\t\t\t\t\t\t\t\treturn;\n'
        '\t\t\t\t\t\t\t}\n'
        '\t\t\t\t\t\t\tlet errCode = "api_error"; let errMsg = `HTTP ${res.status}`;\n'
        '\t\t\t\t\t\t\ttry { const body = await res.json(); if (typeof body?.code === "string" && body.code.trim()) errCode = body.code.trim(); if (typeof body?.message === "string" && body.message.trim()) errMsg = body.message.trim(); if (res.status === 409 && (body?.details?.currentStatus === "approved" || body?.details?.currentStatus === "filled" || body?.details?.currentStatus === "rejected")) { await bot.api.deleteMessage(chatId, callbackMessage.message_id); return; } } catch {}\n'
        '\t\t\t\t\t\t\ttry { await bot.api.editMessageReplyMarkup(chatId, callbackMessage.message_id, { inline_keyboard: [[{ text: "Approve", callback_data: `xappr|a|${tradeId}|${chainKey}` }, { text: "Deny", callback_data: `xappr|r|${tradeId}|${chainKey}` }]] }); } catch {}\n'
        '\t\t\t\t\t\t\tawait bot.api.editMessageText(chatId, callbackMessage.message_id, `Approval failed: ${errCode} (${errMsg}).`);\n'
        '\t\t\t\t\t\t\treturn;\n'
        '\t\t\t\t\t\t} catch (err) {\n'
        '\t\t\t\t\t\t\ttry { await bot.api.editMessageReplyMarkup(chatId, callbackMessage.message_id, { inline_keyboard: [[{ text: "Approve", callback_data: `xappr|a|${tradeId}|${chainKey}` }, { text: "Deny", callback_data: `xappr|r|${tradeId}|${chainKey}` }]] }); } catch {}\n'
        '\t\t\t\t\t\t\tawait bot.api.editMessageText(chatId, callbackMessage.message_id, `Approval failed: ${String(err)}`);\n'
        '\t\t\t\t\t\t\treturn;\n'
        '\t\t\t\t\t\t}\n'
        '\t\t\t\t\t}\n'
        '\t\t\t\t}\n'
        '\n'
    )

    out2 = raw[:idx] + general_injection + raw[idx:]
    if MARKER not in out2:
        return raw, False, "marker_missing_after_patch"
    # Ensure queued-message auto-buttons are present too (CLI + runtime send paths).
    out3, changed3, err3 = _patch_queued_buttons(out2)
    if err3:
        out3 = out2
        changed3 = False
    out4, changed4, err4 = _patch_queued_buttons_v2(out3)
    if err4:
        out4 = out3
        changed4 = False
    return out4, True or changed3 or changed4, None


def _patch_queued_buttons(raw: str) -> tuple[str, bool, str | None]:
    """
    Patch OpenClaw's Telegram send path so that when a message contains an X-Claw queued approval_pending
    trade summary, OpenClaw attaches Approve/Deny inline buttons to that same message.
    """
    if QUEUED_BUTTONS_MARKER in raw:
        return raw, False, None

    # Target: sendMessageTelegram(...) where the replyMarkup is derived from opts.buttons.
    # We change `const replyMarkup = ...` to `let replyMarkup = ...` and add a fallback builder.
    anchor = "const replyMarkup = buildInlineKeyboard(opts.buttons);"
    if anchor not in raw:
        # Already converted to `let`? Patch that variant too.
        anchor = "let replyMarkup = buildInlineKeyboard(opts.buttons);"
        if anchor not in raw:
            return raw, False, "queued_buttons_anchor_not_found"
        already_let = True
    else:
        already_let = False

    injection = (
        "\n\t// xclaw: telegram queued approval buttons\n"
        "\t// If the agent posts an approval_pending trade summary (queued message), attach inline Approve/Deny buttons.\n"
        "\t// This avoids sending a second Telegram prompt message.\n"
        "\tif (!replyMarkup && typeof text === \"string\" && /\\bStatus:\\s*approval_pending\\b/i.test(text)) {\n"
        "\t\tconst m = text.match(/\\bTrade ID:\\s*(trd_[a-z0-9]+)\\b/i) ?? text.match(/\\bTrade:\\s*(trd_[a-z0-9]+)\\b/i);\n"
        "\t\tif (m && m[1]) {\n"
        "\t\t\tconst tradeId = m[1];\n"
        "\t\t\tlet chainKey = \"\";\n"
        "\t\t\tconst cm = text.match(/\\bChain:\\s*([a-z0-9_]+)\\b/i);\n"
        "\t\t\tif (cm && cm[1]) chainKey = cm[1];\n"
        "\t\t\tif (!chainKey) {\n"
        "\t\t\t\tconst skill = cfg?.skills?.entries?.[\"xclaw-agent\"]; const env = skill?.env ?? {};\n"
        "\t\t\t\tchainKey = String(env?.XCLAW_DEFAULT_CHAIN ?? process.env.XCLAW_DEFAULT_CHAIN ?? \"base_sepolia\").trim() || \"base_sepolia\";\n"
        "\t\t\t}\n"
        "\t\t\treplyMarkup = { inline_keyboard: [[{ text: \"Approve\", callback_data: `xappr|a|${tradeId}|${chainKey}` }, { text: \"Deny\", callback_data: `xappr|r|${tradeId}|${chainKey}` }]] };\n"
        "\t\t}\n"
        "\t}\n"
    )

    text2 = raw
    if not already_let:
        text2 = text2.replace("const replyMarkup = buildInlineKeyboard(opts.buttons);", "let replyMarkup = buildInlineKeyboard(opts.buttons);", 1)
    text2, ok = _inject_after_anchor(text2, anchor if already_let else "let replyMarkup = buildInlineKeyboard(opts.buttons);", injection)
    if not ok:
        return raw, False, "queued_buttons_injection_failed"
    if QUEUED_BUTTONS_MARKER not in text2:
        return raw, False, "queued_buttons_marker_missing_after_patch"
    return text2, True, None


def _patch_queued_buttons_v2(raw: str) -> tuple[str, bool, str | None]:
    """
    Patch the Telegram *runtime* send path used by agent replies (`sendTelegramText(bot, ...)`),
    not the CLI send path (`sendMessageTelegram(...)`).
    """
    anchor = 'const htmlText = (opts?.textMode ?? "markdown") === "html" ? text : markdownToTelegramHtml(text);'
    if anchor not in raw:
        return raw, False, "queued_buttons_v2_anchor_not_found"

    # v3 is our current canonical behavior. If v2 exists near this anchor, remove it and replace with v3
    # so we can improve matching and add logging without duplicating blocks.
    if QUEUED_BUTTONS_MARKER_V3 in raw:
        return raw, False, None
    anchor_idx = raw.find(anchor)
    if QUEUED_BUTTONS_MARKER_V2 in raw:
        # Only remove v2 when it appears in the local window right after the anchor (inside sendTelegramText).
        window = raw[anchor_idx : min(len(raw), anchor_idx + 6000)]
        local_start = window.find(f"// {QUEUED_BUTTONS_MARKER_V2}")
        if local_start >= 0:
            start = anchor_idx + local_start
            end = raw.find("\n\t\ttry {", start)
            if end > start and end < anchor_idx + 8000:
                raw = raw[:start] + raw[end:]

    injection = (
        "\n\t// xclaw: telegram queued approval buttons v3\n"
        "\t// Auto-attach Approve/Deny buttons to queued approval_pending trade summaries sent by the agent runtime.\n"
        "\t// This avoids relying on the model to emit `[[buttons:...]]` directives.\n"
        "\tconst __xclawCheckText = String(opts?.plainText ?? text ?? \"\");\n"
        "\tconst __xclawNormalized = __xclawCheckText.replace(/<[^>]*>/g, \" \").replace(/&nbsp;/g, \" \").replace(/\\s+/g, \" \").trim();\n"
        "\tconst __xclawHasPending = /\\bStatus:\\s*approval_pending\\b/i.test(__xclawNormalized);\n"
        "\tif (__xclawHasPending && !opts?.replyMarkup) {\n"
        "\t\tconst m = __xclawNormalized.match(/\\bTrade ID:\\s*(trd_[a-z0-9]+)\\b/i) ?? __xclawNormalized.match(/\\bTrade:\\s*(trd_[a-z0-9]+)\\b/i) ?? __xclawNormalized.match(/\\b(trd_[a-z0-9]+)\\b/i);\n"
        "\t\tif (m && m[1]) {\n"
        "\t\t\tconst tradeId = m[1];\n"
        "\t\t\tlet chainKey = \"\";\n"
        "\t\t\tconst cm = __xclawNormalized.match(/\\bChain:\\s*([a-z0-9_]+)\\b/i);\n"
        "\t\t\tif (cm && cm[1]) chainKey = cm[1];\n"
        "\t\t\tif (!chainKey) chainKey = String(process.env.XCLAW_DEFAULT_CHAIN ?? \"base_sepolia\").trim() || \"base_sepolia\";\n"
        "\t\t\ttry {\n"
        "\t\t\t\t// Attach buttons to the same message. Callback routing is handled by the gateway callback intercept.\n"
        "\t\t\t\tif (!opts) opts = {};\n"
        "\t\t\t\topts.replyMarkup = { inline_keyboard: [[{ text: \"Approve\", callback_data: `xappr|a|${tradeId}|${chainKey}` }, { text: \"Deny\", callback_data: `xappr|r|${tradeId}|${chainKey}` }]] };\n"
        "\t\t\t\ttry { runtime.log?.(`xclaw: queued buttons attached tradeId=${tradeId} chainKey=${chainKey}`); } catch {}\n"
        "\t\t\t} catch (err) {\n"
        "\t\t\t\ttry { runtime.log?.(`xclaw: queued buttons attach failed err=${String(err)}`); } catch {}\n"
        "\t\t\t}\n"
        "\t\t} else {\n"
        "\t\t\ttry { runtime.log?.(`xclaw: queued buttons skipped (pending but missing trade id) sample=${__xclawNormalized.slice(0, 180)}`); } catch {}\n"
        "\t\t}\n"
        "\t} else if (__xclawHasPending && opts?.replyMarkup) {\n"
        "\t\ttry { runtime.log?.(`xclaw: queued buttons skipped (already has replyMarkup)`); } catch {}\n"
        "\t}\n"
    )

    out, ok = _inject_after_anchor(raw, anchor, injection)
    if not ok:
        return raw, False, "queued_buttons_v2_injection_failed"
    if QUEUED_BUTTONS_MARKER_V3 not in out:
        return raw, False, "queued_buttons_v2_marker_missing_after_patch"
    return out, True, None


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
            return PatchResult(ok=False, patched=False, restarted=False, openclaw_version=version, openclaw_root=str(pkg_root), error="callback_bundle_not_found")

        state = _read_json(STATE_FILE)
        # Bump schemaVersion when patch heuristics/normalization change to invalidate cached fast-path.
        state["schemaVersion"] = STATE_SCHEMA_VERSION
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
                and cached.get("schemaVersion") == STATE_SCHEMA_VERSION
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

            # Safety gate: never write a patched bundle that does not parse.
            ok_js, js_err = _node_check_js_text(patched_text)
            if not ok_js:
                state["lastErrorAt"] = _utc_now()
                state["lastErrorAtEpoch"] = time.time()
                state["lastErrorVersion"] = version
                state["lastError"] = f"syntax_check_failed:{bundle}:{js_err or 'node_check_failed'}"
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
                    "schemaVersion": STATE_SCHEMA_VERSION,
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
