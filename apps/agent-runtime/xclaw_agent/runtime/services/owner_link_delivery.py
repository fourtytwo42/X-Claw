from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class OwnerLinkDeliveryServiceContext:
    read_openclaw_last_delivery: Callable[[], dict[str, Any] | None]
    shutil_module: Any
    run_subprocess: Callable[..., Any]
    extract_openclaw_message_id: Callable[[str], str | None]


def maybe_send_owner_link_to_active_chat(ctx: OwnerLinkDeliveryServiceContext, management_url: str, expires_at: str | None) -> dict[str, Any]:
    delivery = ctx.read_openclaw_last_delivery()
    if not delivery:
        return {"sent": False, "reason": "no_active_delivery"}
    channel = str(delivery.get("lastChannel") or "").strip().lower()
    target = str(delivery.get("lastTo") or "").strip()
    if not channel or not target:
        return {"sent": False, "reason": "missing_channel_or_target"}
    if channel == "telegram":
        return {"sent": False, "reason": "telegram_channel_skipped"}
    openclaw = ctx.shutil_module.which("openclaw")
    if not openclaw:
        return {"sent": False, "reason": "openclaw_missing"}
    message = f"Owner management link:\n{management_url}"
    if isinstance(expires_at, str) and expires_at.strip():
        message += f"\nExpires: {expires_at.strip()}"
    message += "\nShort-lived one-time link. Do not forward."
    cmd = [openclaw, "message", "send", "--channel", channel, "--target", target, "--message", message, "--json"]
    proc = ctx.run_subprocess(cmd, timeout_sec=20, kind="openclaw_send")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        return {"sent": False, "reason": "send_failed", "error": stderr or stdout or "openclaw message send failed"}
    message_id = ctx.extract_openclaw_message_id(proc.stdout or "")
    return {"sent": True, "channel": channel, "messageId": message_id}
