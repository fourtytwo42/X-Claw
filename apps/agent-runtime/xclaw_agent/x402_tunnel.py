from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from typing import Any

APP_DIR = pathlib.Path(os.environ.get("XCLAW_AGENT_HOME", str(pathlib.Path.home() / ".xclaw-agent")))
MANAGED_BIN_DIR = APP_DIR / "bin"
CLOUDFLARED_VERSION = os.environ.get("XCLAW_CLOUDFLARED_VERSION", "2026.2.1")


class TunnelError(Exception):
    pass


def ensure_app_dir() -> None:
    APP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(APP_DIR, 0o700)


def _managed_cloudflared_path() -> pathlib.Path:
    return MANAGED_BIN_DIR / ("cloudflared.exe" if os.name == "nt" else "cloudflared")


def _cloudflared_download_url(version: str) -> str:
    machine = os.uname().machine.lower() if hasattr(os, "uname") else os.environ.get("PROCESSOR_ARCHITECTURE", "amd64").lower()
    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        arch = "amd64"

    if os.name == "nt":
        return f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-{arch}.exe"

    platform = os.uname().sysname.lower() if hasattr(os, "uname") else "linux"
    if "darwin" in platform:
        return f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-{arch}.tgz"
    return f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"


def _download_cloudflared(version: str = CLOUDFLARED_VERSION) -> pathlib.Path:
    if os.environ.get("XCLAW_ALLOW_CLOUDFLARED_DOWNLOAD", "1").strip().lower() in {"0", "false", "no"}:
        raise TunnelError("cloudflared is missing and auto-download is disabled (XCLAW_ALLOW_CLOUDFLARED_DOWNLOAD=0).")
    ensure_app_dir()
    MANAGED_BIN_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(MANAGED_BIN_DIR, 0o700)

    target = _managed_cloudflared_path()
    url = _cloudflared_download_url(version)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        tmp_path.write_bytes(data)
        if url.endswith(".tgz"):
            raise TunnelError("cloudflared .tgz package is not auto-extracted in this runtime; install cloudflared manually on macOS.")
        shutil.move(str(tmp_path), str(target))
        if os.name != "nt":
            os.chmod(target, 0o755)
        return target
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def ensure_cloudflared() -> str:
    path_binary = shutil.which("cloudflared")
    if path_binary:
        return path_binary

    managed = _managed_cloudflared_path()
    if managed.exists() and os.access(managed, os.X_OK):
        return str(managed)

    downloaded = _download_cloudflared()
    return str(downloaded)


def start_quick_tunnel(local_port: int, cloudflared_bin: str | None = None, timeout_sec: int = 30) -> dict[str, Any]:
    if local_port < 1 or local_port > 65535:
        raise TunnelError("Invalid local tunnel port.")

    binary = cloudflared_bin or ensure_cloudflared()
    cmd = [binary, "tunnel", "--url", f"http://127.0.0.1:{local_port}", "--no-autoupdate"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    started = time.time()
    public_url: str | None = None
    lines: list[str] = []
    pattern = re.compile(r"https://[a-z0-9.-]+\.trycloudflare\.com", flags=re.IGNORECASE)

    while time.time() - started < timeout_sec:
        if proc.poll() is not None:
            break
        line = ""
        if proc.stdout is not None:
            line = proc.stdout.readline().strip()
        if line:
            lines.append(line)
            match = pattern.search(line)
            if match:
                public_url = match.group(0)
                break
        else:
            time.sleep(0.1)

    if not public_url:
        try:
            proc.terminate()
        except Exception:
            pass
        raise TunnelError("Failed to establish Cloudflare Quick Tunnel URL.")

    return {
        "pid": proc.pid,
        "publicUrl": public_url,
        "cloudflaredBin": binary,
        "command": cmd,
        "logs": lines[-20:],
    }


def stop_process(pid: int | None) -> None:
    if not isinstance(pid, int) or pid <= 0:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True, text=True)
        else:
            os.kill(pid, 15)
    except Exception:
        return
