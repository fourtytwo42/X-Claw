#!/usr/bin/env python3
"""Check upstream OpenClaw Telegram patch anchors for X-Claw compatibility.

This is an operator utility for upgrade verification only.
It does not modify files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


OLD_HTML_ANCHOR = 'const htmlText = (opts?.textMode ?? "markdown") === "html" ? text : markdownToTelegramHtml(text);'
NEW_HTML_ANCHOR = 'const htmlText = textMode === "html" ? text : markdownToTelegramHtml(text);'
HTML_ANCHOR_REGEX = re.compile(r"const htmlText\s*=\s*[^;]*\?\s*text\s*:\s*markdownToTelegramHtml\(text\);")
CALLBACK_ANCHOR = 'bot.on("callback_query", async (ctx) => {'
PAGINATION_ANCHOR = "const paginationMatch = data.match(/^commands_page_"
REPLY_MARKUP_ANCHOR = "const replyMarkup = buildInlineKeyboard(opts.buttons);"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _result(ok: bool, code: str, message: str, details: dict[str, Any]) -> int:
    print(
        json.dumps(
            {
                "ok": ok,
                "code": code,
                "message": message,
                "details": details,
            },
            separators=(",", ":"),
        )
    )
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openclaw-root",
        default="Research/openclaw",
        help="Path to local OpenClaw checkout root (default: Research/openclaw).",
    )
    args = parser.parse_args(argv)

    root = Path(args.openclaw_root).expanduser().resolve()
    delivery_send = root / "src" / "telegram" / "bot" / "delivery.send.ts"
    bot_handlers = root / "src" / "telegram" / "bot-handlers.ts"
    send_ts = root / "src" / "telegram" / "send.ts"

    missing_paths = [str(path) for path in (delivery_send, bot_handlers, send_ts) if not path.exists()]
    if missing_paths:
        return _result(
            False,
            "openclaw_paths_missing",
            "Required OpenClaw source files not found.",
            {"openclawRoot": str(root), "missingPaths": missing_paths},
        )

    delivery_text = _read(delivery_send)
    handlers_text = _read(bot_handlers)
    send_text = _read(send_ts)

    old_present = OLD_HTML_ANCHOR in delivery_text
    new_present = NEW_HTML_ANCHOR in delivery_text
    regex_present = bool(HTML_ANCHOR_REGEX.search(delivery_text))
    callback_present = CALLBACK_ANCHOR in handlers_text
    pagination_present = PAGINATION_ANCHOR in handlers_text
    reply_markup_present = REPLY_MARKUP_ANCHOR in send_text

    checks = {
        "deliveryOldAnchorPresent": old_present,
        "deliveryNewAnchorPresent": new_present,
        "deliveryRegexAnchorPresent": regex_present,
        "callbackAnchorPresent": callback_present,
        "paginationAnchorPresent": pagination_present,
        "replyMarkupAnchorPresent": reply_markup_present,
    }

    ok = regex_present and callback_present and pagination_present and reply_markup_present
    code = "ok" if ok else "alignment_drift_detected"
    message = (
        "OpenClaw anchor compatibility check passed."
        if ok
        else "OpenClaw anchor drift detected; patch alignment update required."
    )
    return _result(
        ok,
        code,
        message,
        {
            "openclawRoot": str(root),
            "checks": checks,
            "notes": {
                "htmlAnchorMode": "old_or_new_or_regex",
                "required": [
                    "deliveryRegexAnchorPresent",
                    "callbackAnchorPresent",
                    "paginationAnchorPresent",
                    "replyMarkupAnchorPresent",
                ],
            },
        },
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
