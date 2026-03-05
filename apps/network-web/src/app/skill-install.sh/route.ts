import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

const DEFAULT_REPO_URL = 'https://github.com/fourtytwo42/X-Claw';

function resolvePublicBaseUrl(req: NextRequest): string {
  const configured = process.env.XCLAW_PUBLIC_BASE_URL?.trim();
  if (configured) {
    return configured;
  }

  const host = req.nextUrl.hostname;
  if (host === '0.0.0.0' || host === '::' || host === '[::]') {
    return 'https://xclaw.trade';
  }
  return req.nextUrl.origin;
}

function buildInstallerScript(origin: string): string {
  return `#!/usr/bin/env bash
set -euo pipefail

echo "[xclaw] bootstrap start"

XCLAW_INSTALL_TARGET_USER="$USER"
XCLAW_INSTALL_TARGET_HOME="$HOME"
if [ "$(id -u)" -eq 0 ] && [ -n "\${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
  XCLAW_INSTALL_TARGET_USER="$SUDO_USER"
  XCLAW_INSTALL_TARGET_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6 || true)"
  if [ -z "$XCLAW_INSTALL_TARGET_HOME" ]; then
    XCLAW_INSTALL_TARGET_HOME="$(eval echo "~$SUDO_USER")"
  fi
  if [ -z "$XCLAW_INSTALL_TARGET_HOME" ] || [ ! -d "$XCLAW_INSTALL_TARGET_HOME" ]; then
    echo "[xclaw] unable to resolve home directory for sudo user: $SUDO_USER"
    exit 1
  fi
  export HOME="$XCLAW_INSTALL_TARGET_HOME"
  echo "[xclaw] sudo detected; targeting user context: $XCLAW_INSTALL_TARGET_USER ($XCLAW_INSTALL_TARGET_HOME)"
fi

export XCLAW_WORKDIR="\${XCLAW_WORKDIR:-$HOME/xclaw}"
export XCLAW_REPO_REF="\${XCLAW_REPO_REF:-main}"
export XCLAW_REPO_URL="\${XCLAW_REPO_URL:-${DEFAULT_REPO_URL}}"
export XCLAW_INSTALL_ORIGIN="${origin}"
export XCLAW_INSTALL_FORCE_LOCAL_API="\${XCLAW_INSTALL_FORCE_LOCAL_API:-0}"
if [ "$XCLAW_INSTALL_FORCE_LOCAL_API" = "1" ]; then
  export XCLAW_INSTALL_CANONICAL_API_BASE="http://127.0.0.1:3000/api/v1"
elif echo "$XCLAW_INSTALL_ORIGIN" | grep -Eq '^https?://(127\\.0\\.0\\.1|localhost)(:[0-9]+)?$'; then
  export XCLAW_INSTALL_CANONICAL_API_BASE="https://xclaw.trade/api/v1"
elif echo "$XCLAW_INSTALL_ORIGIN" | grep -Eq '^https?://xclaw\\.trade$'; then
  export XCLAW_INSTALL_CANONICAL_API_BASE="https://xclaw.trade/api/v1"
else
  export XCLAW_INSTALL_CANONICAL_API_BASE="${origin}/api/v1"
fi
export XCLAW_API_BASE_URL="\${XCLAW_API_BASE_URL:-$XCLAW_INSTALL_CANONICAL_API_BASE}"
export XCLAW_DEFAULT_CHAIN="\${XCLAW_DEFAULT_CHAIN:-base_sepolia}"

tmp_dir="$(mktemp -d)"
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

ensure_cast() {
  export PATH="$HOME/.foundry/bin:$PATH"
  if command -v cast >/dev/null 2>&1; then
    echo "[xclaw] cast already installed"
    return 0
  fi

  echo "[xclaw] cast not found; installing Foundry (user-space, no sudo)"
  if ! command -v foundryup >/dev/null 2>&1; then
    curl -fsSL https://foundry.paradigm.xyz | bash
    export PATH="$HOME/.foundry/bin:$PATH"
  fi

  if ! command -v foundryup >/dev/null 2>&1; then
    echo "[xclaw] foundryup is unavailable after install attempt"
    exit 1
  fi

  foundryup >/dev/null
  export PATH="$HOME/.foundry/bin:$PATH"
  if ! command -v cast >/dev/null 2>&1; then
    echo "[xclaw] cast is still unavailable after foundryup"
    echo "[xclaw] add ~/.foundry/bin to PATH and retry"
    exit 1
  fi
  echo "[xclaw] cast installed: $(cast --version | head -n1)"
}

ensure_system_python_packages() {
  if [ "$(id -u)" -ne 0 ]; then
    return 1
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    return 1
  fi
  echo "[xclaw] attempting to install missing system python packages (python3-venv python3-pip)"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y >/dev/null 2>&1 || true
  apt-get install -y python3-venv python3-pip >/dev/null 2>&1
}

resolve_python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

ensure_python_runtime_deps() {
  local py_bin="$1"
  local req_file="$XCLAW_WORKDIR/apps/agent-runtime/requirements.txt"
  if [ ! -f "$req_file" ]; then
    echo "[xclaw] runtime requirements file not found: $req_file"
    exit 1
  fi

  if "$py_bin" - <<'PY' >/dev/null 2>&1
import importlib
import sys
missing = []
for mod in ("argon2", "Crypto.Hash.keccak", "cryptography.hazmat.primitives.asymmetric.ec"):
    try:
        importlib.import_module(mod)
    except Exception:
        missing.append(mod)
if missing:
    raise SystemExit(1)
PY
  then
    echo "[xclaw] python runtime deps already installed for $py_bin"
    export XCLAW_PYTHON_BIN="$py_bin"
    return 0
  fi

  echo "[xclaw] ensuring pip is available for $py_bin"
  if ! "$py_bin" -m pip --version >/dev/null 2>&1; then
    "$py_bin" -m ensurepip --upgrade >/dev/null 2>&1 || true
  fi

  if ! "$py_bin" -m pip --version >/dev/null 2>&1; then
    echo "[xclaw] pip still unavailable; bootstrapping via get-pip.py"
    if curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$tmp_dir/get-pip.py"; then
      "$py_bin" "$tmp_dir/get-pip.py" --user >/dev/null 2>&1 || true
    fi
  fi

  if ! "$py_bin" -m pip --version >/dev/null 2>&1; then
    local venv_dir="$HOME/.xclaw-agent/runtime-venv"
    local venv_python="$venv_dir/bin/python"
    echo "[xclaw] pip unavailable on system interpreter; creating fallback venv at $venv_dir"
    if ! "$py_bin" -m venv "$venv_dir" >/dev/null 2>&1; then
      ensure_system_python_packages >/dev/null 2>&1 || true
      if ! "$py_bin" -m venv "$venv_dir" >/dev/null 2>&1; then
        echo "[xclaw] standard venv creation failed; retrying with --without-pip"
      fi
    fi
    if [ ! -x "$venv_python" ]; then
      if ! "$py_bin" -m venv --without-pip "$venv_dir" >/dev/null 2>&1; then
        if command -v virtualenv >/dev/null 2>&1; then
          virtualenv "$venv_dir" >/dev/null 2>&1 || true
        fi
      fi
    fi

    if [ ! -x "$venv_python" ]; then
      ensure_system_python_packages >/dev/null 2>&1 || true
      echo "[xclaw] standard venv creation failed; retrying with --without-pip"
      if ! "$py_bin" -m venv --without-pip "$venv_dir" >/dev/null 2>&1; then
        if command -v virtualenv >/dev/null 2>&1; then
          virtualenv "$venv_dir" >/dev/null 2>&1 || true
        fi
      fi
    fi

    if [ ! -x "$venv_python" ]; then
      echo "[xclaw] unable to provision pip or create venv fallback"
      echo "[xclaw] install python3-venv (or provide XCLAW_AGENT_PYTHON_BIN), then rerun installer"
      exit 1
    fi

    if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
      ensure_system_python_packages >/dev/null 2>&1 || true
      if [ ! -f "$tmp_dir/get-pip.py" ]; then
        curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$tmp_dir/get-pip.py" || true
      fi
      if [ -f "$tmp_dir/get-pip.py" ]; then
        "$venv_python" "$tmp_dir/get-pip.py" >/dev/null 2>&1 || true
      fi
    fi

    if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
      echo "[xclaw] venv created but pip bootstrap failed"
      echo "[xclaw] install python3-pip or set XCLAW_AGENT_PYTHON_BIN to a Python with pip, then rerun installer"
      exit 1
    fi

    py_bin="$venv_python"
    export XCLAW_PYTHON_BIN="$py_bin"
    export XCLAW_PYTHON_IN_VENV="1"
  fi

  echo "[xclaw] installing python runtime deps from $req_file"
  install_output=""
  install_status=0
  set +e
  if [ "\${XCLAW_PYTHON_IN_VENV:-0}" = "1" ]; then
    install_output="$("$py_bin" -m pip install --disable-pip-version-check -r "$req_file" 2>&1)"
    install_status=$?
  else
    install_output="$("$py_bin" -m pip install --disable-pip-version-check --user -r "$req_file" 2>&1)"
    install_status=$?
  fi
  set -e

  if [ "$install_status" -ne 0 ] && [ "\${XCLAW_PYTHON_IN_VENV:-0}" != "1" ] && printf '%s' "$install_output" | grep -qi "externally-managed-environment"; then
    local venv_dir="$HOME/.xclaw-agent/runtime-venv"
    local venv_python="$venv_dir/bin/python"
    echo "[xclaw] detected externally managed python (PEP 668); creating fallback venv at $venv_dir"
    if ! "$py_bin" -m venv "$venv_dir" >/dev/null 2>&1; then
      ensure_system_python_packages >/dev/null 2>&1 || true
      if ! "$py_bin" -m venv "$venv_dir" >/dev/null 2>&1; then
        echo "[xclaw] standard venv creation failed; retrying with --without-pip"
      fi
    fi
    if [ ! -x "$venv_python" ]; then
      ensure_system_python_packages >/dev/null 2>&1 || true
      echo "[xclaw] standard venv creation failed; retrying with --without-pip"
      if ! "$py_bin" -m venv --without-pip "$venv_dir" >/dev/null 2>&1; then
        if command -v virtualenv >/dev/null 2>&1; then
          virtualenv "$venv_dir" >/dev/null 2>&1 || true
        fi
      fi
    fi
    if [ ! -x "$venv_python" ]; then
      printf '%s\n' "$install_output"
      echo "[xclaw] unable to provision fallback venv for externally managed python"
      exit 1
    fi
    if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
      ensure_system_python_packages >/dev/null 2>&1 || true
      if [ ! -f "$tmp_dir/get-pip.py" ]; then
        curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$tmp_dir/get-pip.py" || true
      fi
      if [ -f "$tmp_dir/get-pip.py" ]; then
        "$venv_python" "$tmp_dir/get-pip.py" >/dev/null 2>&1 || true
      fi
    fi
    if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
      printf '%s\n' "$install_output"
      echo "[xclaw] venv created for externally managed python, but pip bootstrap failed"
      exit 1
    fi

    py_bin="$venv_python"
    export XCLAW_PYTHON_BIN="$py_bin"
    export XCLAW_PYTHON_IN_VENV="1"
    set +e
    install_output="$("$py_bin" -m pip install --disable-pip-version-check -r "$req_file" 2>&1)"
    install_status=$?
    set -e
  fi

  if [ "$install_status" -ne 0 ]; then
    printf '%s\n' "$install_output"
    exit "$install_status"
  fi

  if ! "$py_bin" - <<'PY' >/dev/null 2>&1
import importlib
for mod in ("argon2", "Crypto.Hash.keccak", "cryptography.hazmat.primitives.asymmetric.ec"):
    importlib.import_module(mod)
PY
  then
    echo "[xclaw] python runtime deps verification failed after install"
    exit 1
  fi
}

if [ -d "$XCLAW_WORKDIR/.git" ]; then
  echo "[xclaw] existing git workspace found: $XCLAW_WORKDIR"
  cd "$XCLAW_WORKDIR"
  git fetch --all --prune
  git checkout "$XCLAW_REPO_REF"
  git pull --ff-only
elif [ ! -e "$XCLAW_WORKDIR" ]; then
  archive_base="$(echo "$XCLAW_REPO_URL" | sed -E 's#https?://github.com/##' | sed -E 's#\\.git$##')"
  repo_archive_prefix="$(basename "$archive_base")"
  archive_url="https://codeload.github.com/$archive_base/tar.gz/refs/heads/$XCLAW_REPO_REF"
  echo "[xclaw] downloading source archive: $archive_url"
  curl -fsSL "$archive_url" -o "$tmp_dir/repo.tar.gz"
  tar -xzf "$tmp_dir/repo.tar.gz" -C "$tmp_dir"

  src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d -name "$repo_archive_prefix-*" | head -n1)"
  if [ -z "$src_dir" ]; then
    echo "[xclaw] unable to find extracted repository directory"
    exit 1
  fi

  mkdir -p "$(dirname "$XCLAW_WORKDIR")"
  mv "$src_dir" "$XCLAW_WORKDIR"
else
  echo "[xclaw] existing non-git directory at $XCLAW_WORKDIR"
  archive_base="$(echo "$XCLAW_REPO_URL" | sed -E 's#https?://github.com/##' | sed -E 's#\\.git$##')"
  repo_archive_prefix="$(basename "$archive_base")"
  archive_url="https://codeload.github.com/$archive_base/tar.gz/refs/heads/$XCLAW_REPO_REF"
  echo "[xclaw] downloading source archive for in-place update: $archive_url"
  curl -fsSL "$archive_url" -o "$tmp_dir/repo.tar.gz"
  tar -xzf "$tmp_dir/repo.tar.gz" -C "$tmp_dir"

  src_dir="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d -name "$repo_archive_prefix-*" | head -n1)"
  if [ -z "$src_dir" ]; then
    echo "[xclaw] unable to find extracted repository directory"
    exit 1
  fi

  echo "[xclaw] updating existing workspace in place"
  mkdir -p "$XCLAW_WORKDIR"
  cp -a "$src_dir"/. "$XCLAW_WORKDIR"/
fi

cd "$XCLAW_WORKDIR"
ensure_cast
if ! XCLAW_PYTHON_BIN="$(resolve_python_bin)"; then
  echo "[xclaw] python3/python is unavailable on PATH"
  exit 1
fi
ensure_python_runtime_deps "$XCLAW_PYTHON_BIN"
export XCLAW_AGENT_PYTHON_BIN="$XCLAW_PYTHON_BIN"
echo "[xclaw] running setup_agent_skill.py"
xclaw_telegram_force_management="disabled"
set +e
setup_output="$("$XCLAW_PYTHON_BIN" skills/xclaw-agent/scripts/setup_agent_skill.py 2>&1)"
setup_status=$?
set -e
if [ -n "$setup_output" ]; then
  printf '%s\n' "$setup_output"
fi
if [ "$setup_status" -ne 0 ]; then
  if printf '%s' "$setup_output" | grep -qi 'write_failed:.*permission denied'; then
    printf '\n\\033[1;37;44m[xclaw] INSTALLER NOTE\\033[0m\n'
    printf '\\033[1;31m[xclaw] Gateway patch write is not available in current install context.\\033[0m\n'
    printf '\\033[1;33m[xclaw] Continuing in fallback mode: Telegram approvals will use management-link flow (no inline buttons).\\033[0m\n'
    printf '\\033[1;31m[xclaw] For full Telegram inline button support, rerun with sudo (recommended):\\033[0m\n'
    printf '\\033[1;33m  curl -fsSL https://xclaw.trade/skill-install.sh | sudo bash\\033[0m\n\n'
    echo "[xclaw] retrying setup with gateway patch disabled"
    set +e
    setup_output="$(
      XCLAW_OPENCLAW_AUTO_PATCH=0 \
      XCLAW_OPENCLAW_PATCH_STRICT=0 \
      "$XCLAW_PYTHON_BIN" skills/xclaw-agent/scripts/setup_agent_skill.py 2>&1
    )"
    setup_status=$?
    set -e
    if [ -n "$setup_output" ]; then
      printf '%s\n' "$setup_output"
    fi
    if [ "$setup_status" -eq 0 ]; then
      xclaw_telegram_force_management="enabled"
    fi
  fi
  if [ "$setup_status" -ne 0 ]; then
  exit "$setup_status"
  fi
fi

resolve_xclaw_agent_bin() {
  export PATH="$HOME/.xclaw-agent/bin:$PATH"
  local configured
  configured="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_AGENT_RUNTIME_BIN 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -n "$configured" ] && [ -x "$configured" ]; then
    echo "$configured"
    return 0
  fi
  if command -v xclaw-agent >/dev/null 2>&1; then
    command -v xclaw-agent
    return 0
  fi
  if [ -x "$XCLAW_WORKDIR/apps/agent-runtime/bin/xclaw-agent" ]; then
    echo "$XCLAW_WORKDIR/apps/agent-runtime/bin/xclaw-agent"
    return 0
  fi
  return 1
}

ensure_shell_path_entry() {
  local rc_file="$1"
  local export_line='export PATH="$HOME/.xclaw-agent/bin:$HOME/.local/bin:$PATH"'
  if [ ! -f "$rc_file" ]; then
    return 0
  fi
  if grep -Fq "$export_line" "$rc_file"; then
    return 0
  fi
  printf "\n# X-Claw runtime launcher path\n%s\n" "$export_line" >> "$rc_file"
}

persist_runtime_path() {
  mkdir -p "$HOME/.local/bin"
  ln -sf "$XCLAW_AGENT_BIN" "$HOME/.local/bin/xclaw-agent"
  ensure_shell_path_entry "$HOME/.profile"
  ensure_shell_path_entry "$HOME/.bashrc"
  ensure_shell_path_entry "$HOME/.zshrc"
}

if ! XCLAW_AGENT_BIN="$(resolve_xclaw_agent_bin)"; then
  echo "[xclaw] unable to resolve xclaw-agent launcher after setup"
  echo "[xclaw] expected launcher in ~/.xclaw-agent/bin or apps/agent-runtime/bin"
  exit 1
fi
echo "[xclaw] using runtime launcher: $XCLAW_AGENT_BIN"
persist_runtime_path

echo "[xclaw] configuring OpenClaw skill env defaults"

if [ -z "\${XCLAW_BUILDER_CODE_BASE:-}" ]; then
  existing_cfg_builder_base="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -n "$existing_cfg_builder_base" ] && [ "$existing_cfg_builder_base" != "null" ]; then
    export XCLAW_BUILDER_CODE_BASE="$existing_cfg_builder_base"
  else
    export XCLAW_BUILDER_CODE_BASE="xclaw"
    echo "[xclaw] defaulted XCLAW_BUILDER_CODE_BASE=xclaw"
  fi
fi

if [ -z "\${XCLAW_BUILDER_CODE_BASE_SEPOLIA:-}" ]; then
  existing_cfg_builder_base_sepolia="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE_SEPOLIA 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -n "$existing_cfg_builder_base_sepolia" ] && [ "$existing_cfg_builder_base_sepolia" != "null" ]; then
    export XCLAW_BUILDER_CODE_BASE_SEPOLIA="$existing_cfg_builder_base_sepolia"
  else
    export XCLAW_BUILDER_CODE_BASE_SEPOLIA="$XCLAW_BUILDER_CODE_BASE"
    echo "[xclaw] defaulted XCLAW_BUILDER_CODE_BASE_SEPOLIA=$XCLAW_BUILDER_CODE_BASE_SEPOLIA"
  fi
fi

openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_RUNTIME_BIN "$XCLAW_AGENT_BIN" || true
openclaw config set skills.entries.xclaw-agent.env.XCLAW_API_BASE_URL "$XCLAW_API_BASE_URL" || true
openclaw config set skills.entries.xclaw-agent.env.XCLAW_DEFAULT_CHAIN "$XCLAW_DEFAULT_CHAIN" || true
openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_PYTHON_BIN "$XCLAW_AGENT_PYTHON_BIN" || true
openclaw config set skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE "$XCLAW_BUILDER_CODE_BASE" || true
openclaw config set skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE_SEPOLIA "$XCLAW_BUILDER_CODE_BASE_SEPOLIA" || true
openclaw config set skills.entries.xclaw-agent.env.XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT "$xclaw_telegram_force_management" || true
if [ -n "\${XCLAW_AGENT_ID:-}" ]; then
  openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_ID "$XCLAW_AGENT_ID" || true
fi
if [ -n "\${XCLAW_AGENT_NAME:-}" ]; then
  openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_NAME "$XCLAW_AGENT_NAME" || true
fi

wallet_home="\${XCLAW_AGENT_HOME:-$HOME/.xclaw-agent}"
wallet_store_path="$wallet_home/wallets.json"
wallet_exists=0
if [ -f "$wallet_store_path" ]; then
  existing_wallet_address="$(python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-address \
    | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("address") or "").strip())
except Exception:
 print("")' || true)"
  if [ -n "$existing_wallet_address" ]; then
    wallet_exists=1
  fi
fi

if [ -z "\${XCLAW_WALLET_PASSPHRASE:-}" ]; then
  existing_cfg_passphrase="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -n "$existing_cfg_passphrase" ] && [ "$existing_cfg_passphrase" != "null" ]; then
    export XCLAW_WALLET_PASSPHRASE="$existing_cfg_passphrase"
  elif [ "$wallet_exists" = "0" ]; then
    XCLAW_WALLET_PASSPHRASE="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    export XCLAW_WALLET_PASSPHRASE
    openclaw config set skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE "$XCLAW_WALLET_PASSPHRASE" || true
    echo "[xclaw] generated new wallet passphrase for first install"
  else
    echo "[xclaw] existing wallet detected; preserving existing passphrase/config"
  fi
fi
if [ -n "\${XCLAW_WALLET_PASSPHRASE:-}" ]; then
  openclaw config set skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE "$XCLAW_WALLET_PASSPHRASE" || true
fi

if [ -z "\${XCLAW_AGENT_API_KEY:-}" ]; then
  existing_cfg_api_key="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_AGENT_API_KEY 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -z "$existing_cfg_api_key" ] || [ "$existing_cfg_api_key" = "null" ]; then
    existing_cfg_api_key="$(openclaw config get skills.entries.xclaw-agent.apiKey 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  fi
  if [ -n "$existing_cfg_api_key" ] && [ "$existing_cfg_api_key" != "null" ]; then
    export XCLAW_AGENT_API_KEY="$existing_cfg_api_key"
    echo "[xclaw] recovered XCLAW_AGENT_API_KEY from existing OpenClaw config"
  fi
fi

if [ -z "\${XCLAW_AGENT_ID:-}" ]; then
  existing_cfg_agent_id="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_AGENT_ID 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -n "$existing_cfg_agent_id" ] && [ "$existing_cfg_agent_id" != "null" ]; then
    export XCLAW_AGENT_ID="$existing_cfg_agent_id"
    echo "[xclaw] recovered XCLAW_AGENT_ID from existing OpenClaw config"
  fi
fi

if [ -z "\${XCLAW_AGENT_NAME:-}" ]; then
  existing_cfg_agent_name="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_AGENT_NAME 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -n "$existing_cfg_agent_name" ] && [ "$existing_cfg_agent_name" != "null" ]; then
    export XCLAW_AGENT_NAME="$existing_cfg_agent_name"
    echo "[xclaw] recovered XCLAW_AGENT_NAME from existing OpenClaw config"
  fi
fi

# Encrypted passphrase backup (non-interactive, no prompting).
# This provides redundancy if OpenClaw config is accidentally overwritten or lost.
passphrase_backup_path="$wallet_home/passphrase.backup.v1.json"

backup_write() {
  if [ -z "\${XCLAW_WALLET_PASSPHRASE:-}" ]; then
    return 0
  fi
  python3 - <<'PY' >/dev/null 2>&1 || true
import base64, hashlib, json, os, pathlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

backup_path = pathlib.Path(os.environ.get("XCLAW_PASSPHRASE_BACKUP_PATH", "")).expanduser()
if not str(backup_path):
    raise SystemExit(0)
backup_path.parent.mkdir(parents=True, exist_ok=True)

passphrase = os.environ.get("XCLAW_WALLET_PASSPHRASE", "")
if not passphrase:
    raise SystemExit(0)

machine_id = ""
for candidate in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
    try:
        machine_id = pathlib.Path(candidate).read_text(encoding="utf-8").strip()
        if machine_id:
            break
    except Exception:
        pass

ikm = hashlib.sha256(("|".join([machine_id, str(os.getuid()), str(pathlib.Path.home())])).encode("utf-8")).digest()
hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"xclaw-passphrase-backup-v1", info=b"xclaw", backend=None)
key = hkdf.derive(ikm)

nonce = os.urandom(12)
aad = b"xclaw-passphrase-backup-v1"
ct = AESGCM(key).encrypt(nonce, passphrase.encode("utf-8"), aad)

payload = {
    "schemaVersion": 1,
    "algo": "AES-256-GCM+HKDF-SHA256(machine-id,uid,home)",
    "nonceB64": base64.b64encode(nonce).decode("ascii"),
    "ciphertextB64": base64.b64encode(ct).decode("ascii"),
}
backup_path.write_text(json.dumps(payload, separators=(",", ":")) + "\\n", encoding="utf-8")
try:
    os.chmod(backup_path, 0o600)
except Exception:
    pass
PY
}

backup_read() {
  python3 - <<'PY' 2>/dev/null || true
import base64, hashlib, json, os, pathlib, sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

backup_path = pathlib.Path(os.environ.get("XCLAW_PASSPHRASE_BACKUP_PATH", "")).expanduser()
if not backup_path.exists():
    raise SystemExit(0)

payload = json.loads(backup_path.read_text(encoding="utf-8"))
nonce = base64.b64decode(payload.get("nonceB64", ""))
ct = base64.b64decode(payload.get("ciphertextB64", ""))

machine_id = ""
for candidate in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
    try:
        machine_id = pathlib.Path(candidate).read_text(encoding="utf-8").strip()
        if machine_id:
            break
    except Exception:
        pass

ikm = hashlib.sha256(("|".join([machine_id, str(os.getuid()), str(pathlib.Path.home())])).encode("utf-8")).digest()
hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"xclaw-passphrase-backup-v1", info=b"xclaw", backend=None)
key = hkdf.derive(ikm)

aad = b"xclaw-passphrase-backup-v1"
pt = AESGCM(key).decrypt(nonce, ct, aad)
sys.stdout.write(pt.decode("utf-8"))
PY
}

export XCLAW_PASSPHRASE_BACKUP_PATH="$passphrase_backup_path"
backup_write

# If a wallet exists and passphrase is missing, attempt to recover from encrypted backup.
if [ "$wallet_exists" = "1" ] && [ -z "\${XCLAW_WALLET_PASSPHRASE:-}" ]; then
  recovered="$(backup_read || true)"
  if [ -n "$recovered" ]; then
    export XCLAW_WALLET_PASSPHRASE="$recovered"
    openclaw config set skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE "$XCLAW_WALLET_PASSPHRASE" >/dev/null 2>&1 || true
  fi
fi
if [ -n "\${XCLAW_AGENT_API_KEY:-}" ]; then
  openclaw config set skills.entries.xclaw-agent.apiKey "$XCLAW_AGENT_API_KEY" || true
  openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_API_KEY "$XCLAW_AGENT_API_KEY" || true
  echo "[xclaw] saved XCLAW_AGENT_API_KEY into OpenClaw config for xclaw-agent"
else
  echo "[xclaw] XCLAW_AGENT_API_KEY not provided; installer will request credentials from /api/v1/agent/bootstrap"
fi

if [ "$wallet_exists" = "1" ]; then
  echo "[xclaw] wallet already exists; keeping existing wallet"
else
  echo "[xclaw] first install detected; creating wallet"
  # Create wallet via runtime CLI (signing boundary stays local).
  "$XCLAW_AGENT_BIN" wallet create --chain "$XCLAW_DEFAULT_CHAIN" --json >/dev/null
fi

runtime_platform="linux"
uname_s="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$uname_s" in
  *darwin*) runtime_platform="macos" ;;
  *mingw*|*msys*|*cygwin*) runtime_platform="windows" ;;
  *) runtime_platform="linux" ;;
esac

echo "[xclaw] wallet address"
wallet_json="$(python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-address || true)"
printf "%s\n" "$wallet_json"
wallet_address="$(printf "%s" "$wallet_json" | python3 -c 'import json,sys; s=sys.stdin.read().strip(); 
try:
 d=json.loads(s) if s else {}
 print(d.get("address",""))
except Exception:
 print("")'
)"

# If a wallet exists, verify we can decrypt/sign before attempting signed bootstrap or on-chain trades.
if [ "$wallet_exists" = "1" ]; then
  if [ -z "\${XCLAW_WALLET_PASSPHRASE:-}" ]; then
    echo "[xclaw] ERROR: existing wallet detected but XCLAW_WALLET_PASSPHRASE is not configured."
    echo "[xclaw] Fix: set skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE in ~/.openclaw/openclaw.json to the original value used when the wallet was created, then rerun installer."
    exit 1
  fi

  set +e
  wallet_health_json="$("$XCLAW_AGENT_BIN" wallet health --chain "$XCLAW_DEFAULT_CHAIN" --json 2>/dev/null)"
  wallet_health_ok="$(printf "%s" "$wallet_health_json" | python3 -c 'import json,sys\ns=sys.stdin.read().strip()\ntry:\n d=json.loads(s) if s else {}\n print(\"1\" if d.get(\"ok\") else \"0\")\nexcept Exception:\n print(\"0\")')"
  wallet_integrity_checked="$(printf "%s" "$wallet_health_json" | python3 -c 'import json,sys\ns=sys.stdin.read().strip()\ntry:\n d=json.loads(s) if s else {}\n print(\"1\" if d.get(\"integrityChecked\") else \"0\")\nexcept Exception:\n print(\"0\")')"
  set -e

  if [ "$wallet_health_ok" != "1" ] || [ "$wallet_integrity_checked" != "1" ]; then
    # Try encrypted local backup recovery before failing.
    recovered="$(backup_read || true)"
    if [ -n "$recovered" ]; then
      export XCLAW_WALLET_PASSPHRASE="$recovered"
      openclaw config set skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE "$XCLAW_WALLET_PASSPHRASE" >/dev/null 2>&1 || true
      set +e
      wallet_health_json="$("$XCLAW_AGENT_BIN" wallet health --chain "$XCLAW_DEFAULT_CHAIN" --json 2>/dev/null)"
      wallet_health_ok="$(printf "%s" "$wallet_health_json" | python3 -c 'import json,sys\ns=sys.stdin.read().strip()\ntry:\n d=json.loads(s) if s else {}\n print(\"1\" if d.get(\"ok\") else \"0\")\nexcept Exception:\n print(\"0\")')"
      wallet_integrity_checked="$(printf "%s" "$wallet_health_json" | python3 -c 'import json,sys\ns=sys.stdin.read().strip()\ntry:\n d=json.loads(s) if s else {}\n print(\"1\" if d.get(\"integrityChecked\") else \"0\")\nexcept Exception:\n print(\"0\")')"
      set -e
    fi

    if [ "$wallet_health_ok" != "1" ] || [ "$wallet_integrity_checked" != "1" ]; then
      echo "[xclaw] ERROR: wallet health check failed; wallet cannot be decrypted with current passphrase."
      echo "[xclaw] This usually means XCLAW_WALLET_PASSPHRASE does not match the wallet encryption key (AES-GCM InvalidTag)."
      echo "[xclaw] Fix: restore the original passphrase in OpenClaw config, then restart gateway: openclaw gateway restart"
      exit 1
    fi
  fi
fi

discover_wallet_chains() {
  "$XCLAW_AGENT_BIN" chains --json 2>/dev/null | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
except Exception:
 d={}
items=d.get("chains")
if not isinstance(items,list):
 print("")
 raise SystemExit(0)
out=[]
seen=set()
for row in items:
 if not isinstance(row,dict):
  continue
 key=str(row.get("chainKey") or "").strip()
 if not key:
  continue
 low=key.lower()
 if low in seen:
  continue
 caps=row.get("capabilities")
 if isinstance(caps,dict):
  wallet_cap=caps.get("wallet")
  if isinstance(wallet_cap,bool) and not wallet_cap:
   continue
 out.append(key)
 seen.add(low)
print(" ".join(out))'
}

runtime_wallet_chains="$(discover_wallet_chains || true)"
if [ -z "$runtime_wallet_chains" ]; then
  runtime_wallet_chains="$XCLAW_DEFAULT_CHAIN"
fi
case " $runtime_wallet_chains " in
  *" $XCLAW_DEFAULT_CHAIN "*) ;;
  *) runtime_wallet_chains="$XCLAW_DEFAULT_CHAIN $runtime_wallet_chains" ;;
esac

wallet_binding_failed=0
for chain_key in $runtime_wallet_chains; do
  [ -n "$chain_key" ] || continue
  echo "[xclaw] ensuring portable wallet is bound on $chain_key"
  set +e
  bind_json="$("$XCLAW_AGENT_BIN" wallet create --chain "$chain_key" --json 2>&1)"
  bind_rc=$?
  set -e
  if [ "$bind_rc" -ne 0 ]; then
    bind_code="$(printf "%s" "$bind_json" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("code") or "").strip())
except Exception:
 print("")')"
    if [ "$bind_code" = "wallet_exists" ]; then
      echo "[xclaw] wallet already bound for $chain_key"
      continue
    fi
    wallet_binding_failed=1
    echo "[xclaw] warning: wallet auto-bind failed for chain=$chain_key"
    printf "%s\n" "$bind_json"
    continue
  fi
done

wallet_rows_json="$(python3 - "$XCLAW_AGENT_BIN" "$wallet_address" "$runtime_wallet_chains" <<'PY'
import json
import subprocess
import sys

agent_bin = str(sys.argv[1] or "").strip() or "xclaw-agent"
default_addr = str(sys.argv[2] or "").strip()
chains_raw = str(sys.argv[3] or "").strip()
chains = [item for item in chains_raw.split() if item]

rows = []
seen = set()

def add(chain_key: str, address: str) -> None:
    ck = (chain_key or "").strip()
    ad = (address or "").strip()
    if not ck or not ad:
        return
    key = (ck.lower(), ad.lower())
    if key in seen:
        return
    seen.add(key)
    rows.append({"chainKey": ck, "address": ad})

for chain_key in chains:
    addr = ""
    try:
        proc = subprocess.run(
            [agent_bin, "wallet", "address", "--chain", chain_key, "--json"],
            check=False,
            text=True,
            capture_output=True,
        )
        payload = json.loads((proc.stdout or "").strip() or "{}")
        addr = str(payload.get("address") or "").strip()
    except Exception:
        addr = ""
    if not addr and chain_key == chains[0]:
        addr = default_addr
    add(chain_key, addr)

print(json.dumps(rows, separators=(",", ":")))
PY
)"

if [ "$wallet_binding_failed" = "1" ]; then
  echo "[xclaw] warning: one or more wallet chain bindings failed; installer will continue with available bindings"
fi

bootstrap_ok=0
if [ -z "\${XCLAW_AGENT_API_KEY:-}" ] && [ -n "$wallet_address" ]; then
  echo "[xclaw] no API key provided; requesting auto-bootstrap credentials from server"
  agent_name_field=""
  if [ -n "\${XCLAW_AGENT_NAME:-}" ]; then
    agent_name_field="\"agentName\": \"$XCLAW_AGENT_NAME\","
  fi

  recover_passphrase_from_runloop_env() {
    local env_file="$HOME/.xclaw-agent/approvals-run-loop.env"
    if [ ! -f "$env_file" ]; then
      return 1
    fi
    local recovered=""
    recovered="$(grep '^XCLAW_WALLET_PASSPHRASE=' "$env_file" | tail -n1 | cut -d= -f2- || true)"
    if [ -z "$recovered" ]; then
      return 1
    fi
    export XCLAW_WALLET_PASSPHRASE="$recovered"
    openclaw config set skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE "$XCLAW_WALLET_PASSPHRASE" >/dev/null 2>&1 || true
    echo "[xclaw] recovered wallet passphrase from approvals run-loop env"
    return 0
  }

  bootstrap_chain=""
  bootstrap_wallet=""
  challenge_id=""
  challenge_message=""
  signature=""
  attempted_signing=0
  bootstrap_chain_candidates="$XCLAW_DEFAULT_CHAIN base_sepolia ethereum_sepolia"

  for candidate_chain in $bootstrap_chain_candidates; do
    [ -n "$candidate_chain" ] || continue
    candidate_wallet=""
    if [ "$candidate_chain" = "$XCLAW_DEFAULT_CHAIN" ]; then
      candidate_wallet="$wallet_address"
    else
      candidate_wallet="$("$XCLAW_AGENT_BIN" wallet address --chain "$candidate_chain" --json 2>/dev/null | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("address") or "").strip())
except Exception:
 print("")' || true)"
    fi
    if [ -z "$candidate_wallet" ]; then
      continue
    fi

    echo "[xclaw] requesting signed bootstrap challenge (chain=$candidate_chain)"
    challenge_payload="$(cat <<JSON
{
  "schemaVersion": 1,
  "chainKey": "$candidate_chain",
  "walletAddress": "$candidate_wallet"
}
JSON
)"
    set +e
    challenge_response="$(curl -fsS "$XCLAW_API_BASE_URL/agent/bootstrap/challenge" \
      -H "Content-Type: application/json" \
      -d "$challenge_payload" 2>/dev/null)"
    challenge_rc=$?
    set -e
    if [ "$challenge_rc" -ne 0 ]; then
      continue
    fi

    challenge_id="$(printf "%s" "$challenge_response" | python3 -c 'import json,sys;
try:
 d=json.load(sys.stdin)
 print(d.get("challengeId",""))
except Exception:
 print("")')"
    challenge_message="$(printf "%s" "$challenge_response" | python3 -c 'import json,sys;
try:
 d=json.load(sys.stdin)
 print(d.get("challengeMessage",""))
except Exception:
 print("")')"
    if [ -z "$challenge_id" ] || [ -z "$challenge_message" ]; then
      continue
    fi

    echo "[xclaw] signing bootstrap challenge with local wallet (chain=$candidate_chain)"
    attempted_signing=1
    sig_json="$(python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-sign-challenge "$challenge_message" "$candidate_chain" \
      | python3 -c 'import sys; print(sys.stdin.read().strip())' || true)"
    signature="$(printf "%s" "$sig_json" | python3 -c 'import json,sys;
try:
 d=json.load(sys.stdin)
 print((d.get("signature") or "").strip())
except Exception:
 print("")' || true)"

    if [ -z "$signature" ] && recover_passphrase_from_runloop_env; then
      sig_json="$(python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-sign-challenge "$challenge_message" "$candidate_chain" \
        | python3 -c 'import sys; print(sys.stdin.read().strip())' || true)"
      signature="$(printf "%s" "$sig_json" | python3 -c 'import json,sys;
try:
 d=json.load(sys.stdin)
 print((d.get("signature") or "").strip())
except Exception:
 print("")' || true)"
    fi

    if [ -n "$signature" ]; then
      bootstrap_chain="$candidate_chain"
      bootstrap_wallet="$candidate_wallet"
      break
    fi
  done

  if [ -z "$signature" ]; then
    if [ "$attempted_signing" = "1" ]; then
      echo "[xclaw] unable to sign bootstrap challenge (missing signature) after chain/passphrase recovery attempts."
    else
      echo "[xclaw] bootstrap challenge failed; no signable wallet chain candidate found."
    fi
    echo "[xclaw] Ensure XCLAW_WALLET_PASSPHRASE is configured and cast is installed."
    exit 1
  fi

  bootstrap_payload="$(cat <<JSON
{
  "schemaVersion": 2,
  $agent_name_field
  "walletAddress": "$bootstrap_wallet",
  "runtimePlatform": "$runtime_platform",
  "chainKey": "$bootstrap_chain",
  "challengeId": "$challenge_id",
  "signature": "$signature",
  "mode": "real",
  "approvalMode": "per_trade",
  "publicStatus": "active"
}
JSON
)"

  bootstrap_response="$(curl -fsS "$XCLAW_API_BASE_URL/agent/bootstrap" \
    -H "Content-Type: application/json" \
    -d "$bootstrap_payload")"
  if [ -n "$bootstrap_response" ]; then
    boot_agent_id="$(printf "%s" "$bootstrap_response" | python3 -c 'import json,sys;
try:
 d=json.load(sys.stdin)
 print(d.get("agentId",""))
except Exception:
 print("")')"
    boot_api_key="$(printf "%s" "$bootstrap_response" | python3 -c 'import json,sys;
try:
 d=json.load(sys.stdin)
 print(d.get("agentApiKey",""))
except Exception:
 print("")')"
    boot_agent_name="$(printf "%s" "$bootstrap_response" | python3 -c 'import json,sys;
try:
 d=json.load(sys.stdin)
 print(d.get("agentName",""))
except Exception:
 print("")')"
    if [ -n "$boot_agent_id" ] && [ -n "$boot_api_key" ]; then
      export XCLAW_AGENT_ID="$boot_agent_id"
      export XCLAW_AGENT_API_KEY="$boot_api_key"
      if [ -n "$boot_agent_name" ]; then
        export XCLAW_AGENT_NAME="$boot_agent_name"
      fi
      if [ -z "\${XCLAW_AGENT_NAME:-}" ]; then
        export XCLAW_AGENT_NAME="$XCLAW_AGENT_ID"
      fi
      bootstrap_ok=1
      openclaw config set skills.entries.xclaw-agent.apiKey "$XCLAW_AGENT_API_KEY" || true
      openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_API_KEY "$XCLAW_AGENT_API_KEY" || true
      openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_ID "$XCLAW_AGENT_ID" || true
      openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_NAME "$XCLAW_AGENT_NAME" || true
      echo "[xclaw] bootstrap issued agent credentials and wrote OpenClaw config (agentId=$XCLAW_AGENT_ID, agentName=$XCLAW_AGENT_NAME)"
    else
      echo "[xclaw] bootstrap endpoint did not return agent credentials; falling back to manual/inferred registration path"
    fi
  fi
fi

if [ -z "\${XCLAW_AGENT_ID:-}" ] && [ -n "\${XCLAW_AGENT_API_KEY:-}" ]; then
  echo "[xclaw] attempting to infer XCLAW_AGENT_ID from API token"
  inferred_agent_id="$(curl -fsS "$XCLAW_API_BASE_URL/limit-orders/pending?chainKey=$XCLAW_DEFAULT_CHAIN&limit=1" \
    -H "Authorization: Bearer $XCLAW_AGENT_API_KEY" \
    | python3 -c 'import json,sys; 
try:
 d=json.load(sys.stdin)
 print(d.get("agentId",""))
except Exception:
 print("")' || true)"
  if [ -n "$inferred_agent_id" ]; then
    export XCLAW_AGENT_ID="$inferred_agent_id"
    echo "[xclaw] inferred agent id: $XCLAW_AGENT_ID"
  fi
fi

if [ -n "\${XCLAW_AGENT_ID:-}" ] && [ -z "\${XCLAW_AGENT_NAME:-}" ]; then
  export XCLAW_AGENT_NAME="$XCLAW_AGENT_ID"
fi

wallets_json="$wallet_rows_json"

refresh_api_key_from_config() {
  local cfg_api_key=""
  cfg_api_key="$(openclaw config get skills.entries.xclaw-agent.env.XCLAW_AGENT_API_KEY 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  if [ -z "$cfg_api_key" ] || [ "$cfg_api_key" = "null" ]; then
    cfg_api_key="$(openclaw config get skills.entries.xclaw-agent.apiKey 2>/dev/null | tail -n1 | sed -E 's/^\"(.*)\"$/\\1/' || true)"
  fi
  if [ -n "$cfg_api_key" ] && [ "$cfg_api_key" != "null" ]; then
    export XCLAW_AGENT_API_KEY="$cfg_api_key"
    return 0
  fi
  return 1
}

refresh_agent_identity_from_auth_recover_json() {
  local recover_json="$1"
  local recovered_agent_id=""
  recovered_agent_id="$(printf "%s" "$recover_json" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("agentId") or "").strip())
except Exception:
 print("")' || true)"
  if [ -n "$recovered_agent_id" ]; then
    export XCLAW_AGENT_ID="$recovered_agent_id"
    if [ -z "\${XCLAW_AGENT_NAME:-}" ]; then
      export XCLAW_AGENT_NAME="$recovered_agent_id"
    fi
    openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_ID "$XCLAW_AGENT_ID" >/dev/null 2>&1 || true
    openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_NAME "$XCLAW_AGENT_NAME" >/dev/null 2>&1 || true
    return 0
  fi
  return 1
}

attempt_bootstrap_refresh_credentials() {
  local candidate_chain candidate_wallet challenge_payload challenge_response challenge_id challenge_message signature
  local bootstrap_payload bootstrap_response boot_agent_id boot_api_key boot_agent_name
  local bootstrap_chain_candidates="$XCLAW_DEFAULT_CHAIN base_sepolia ethereum_sepolia solana_mainnet_beta"
  for candidate_chain in $bootstrap_chain_candidates; do
    [ -n "$candidate_chain" ] || continue
    candidate_wallet="$("$XCLAW_AGENT_BIN" wallet address --chain "$candidate_chain" --json 2>/dev/null | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("address") or "").strip())
except Exception:
 print("")' || true)"
    if [ -z "$candidate_wallet" ]; then
      continue
    fi
    challenge_payload="$(cat <<JSON
{
  "schemaVersion": 1,
  "chainKey": "$candidate_chain",
  "walletAddress": "$candidate_wallet"
}
JSON
)"
    challenge_response="$(curl -sS "$XCLAW_API_BASE_URL/agent/bootstrap/challenge" \
      -H "Content-Type: application/json" \
      -d "$challenge_payload" 2>/dev/null || true)"
    challenge_id="$(printf "%s" "$challenge_response" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("challengeId") or "").strip())
except Exception:
 print("")' || true)"
    challenge_message="$(printf "%s" "$challenge_response" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("challengeMessage") or "").strip())
except Exception:
 print("")' || true)"
    if [ -z "$challenge_id" ] || [ -z "$challenge_message" ]; then
      continue
    fi
    signature="$(python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py wallet-sign-challenge "$challenge_message" "$candidate_chain" \
      | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("signature") or "").strip())
except Exception:
 print("")' || true)"
    if [ -z "$signature" ]; then
      continue
    fi

    bootstrap_payload="$(cat <<JSON
{
  "schemaVersion": 2,
  "agentName": "$XCLAW_AGENT_NAME",
  "walletAddress": "$candidate_wallet",
  "runtimePlatform": "$runtime_platform",
  "chainKey": "$candidate_chain",
  "challengeId": "$challenge_id",
  "signature": "$signature",
  "mode": "real",
  "approvalMode": "per_trade",
  "publicStatus": "active"
}
JSON
)"
    bootstrap_response="$(curl -sS "$XCLAW_API_BASE_URL/agent/bootstrap" \
      -H "Content-Type: application/json" \
      -d "$bootstrap_payload" 2>/dev/null || true)"
    boot_agent_id="$(printf "%s" "$bootstrap_response" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("agentId") or "").strip())
except Exception:
 print("")' || true)"
    boot_api_key="$(printf "%s" "$bootstrap_response" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("agentApiKey") or "").strip())
except Exception:
 print("")' || true)"
    boot_agent_name="$(printf "%s" "$bootstrap_response" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print((d.get("agentName") or "").strip())
except Exception:
 print("")' || true)"
    if [ -n "$boot_agent_id" ] && [ -n "$boot_api_key" ]; then
      export XCLAW_AGENT_ID="$boot_agent_id"
      export XCLAW_AGENT_API_KEY="$boot_api_key"
      if [ -n "$boot_agent_name" ]; then
        export XCLAW_AGENT_NAME="$boot_agent_name"
      elif [ -z "\${XCLAW_AGENT_NAME:-}" ]; then
        export XCLAW_AGENT_NAME="$boot_agent_id"
      fi
      openclaw config set skills.entries.xclaw-agent.apiKey "$XCLAW_AGENT_API_KEY" >/dev/null 2>&1 || true
      openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_API_KEY "$XCLAW_AGENT_API_KEY" >/dev/null 2>&1 || true
      openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_ID "$XCLAW_AGENT_ID" >/dev/null 2>&1 || true
      openclaw config set skills.entries.xclaw-agent.env.XCLAW_AGENT_NAME "$XCLAW_AGENT_NAME" >/dev/null 2>&1 || true
      echo "[xclaw] refreshed agent credentials via signed bootstrap (agentId=$XCLAW_AGENT_ID)"
      return 0
    fi
  done
  return 1
}

post_agent_with_recovery() {
  local path="$1"
  local idem_key="$2"
  local payload="$3"
  local label="$4"
  local url="$XCLAW_API_BASE_URL$path"
  local first http_code body
  first="$(curl -sS -w '\n%{http_code}' "$url" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $XCLAW_AGENT_API_KEY" \
    -H "Idempotency-Key: $idem_key" \
    -d "$payload" 2>/dev/null || true)"
  http_code="$(printf "%s" "$first" | tail -n1 | tr -d '\r')"
  body="$(printf "%s" "$first" | sed '$d')"
  if [ "$http_code" -ge 200 ] 2>/dev/null && [ "$http_code" -lt 300 ] 2>/dev/null; then
    [ -n "$body" ] && printf "%s\n" "$body"
    return 0
  fi
  if [ "$http_code" = "401" ]; then
    echo "[xclaw] $label returned 401; attempting auth recovery via wallet signature"
    recover_ok=0
    for recover_chain in "$XCLAW_DEFAULT_CHAIN" base_sepolia ethereum_sepolia; do
      [ -n "$recover_chain" ] || continue
      recover_json="$("$XCLAW_AGENT_BIN" auth recover --chain "$recover_chain" --json 2>/dev/null || true)"
      recover_flag="$(printf "%s" "$recover_json" | python3 -c 'import json,sys
try:
 d=json.load(sys.stdin)
 print("1" if d.get("ok") else "0")
except Exception:
 print("0")' || true)"
      if [ "$recover_flag" = "1" ]; then
        refresh_agent_identity_from_auth_recover_json "$recover_json" || true
        recover_ok=1
        break
      fi
    done
    if [ "$recover_ok" = "1" ] && refresh_api_key_from_config; then
      retry="$(curl -sS -w '\n%{http_code}' "$url" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $XCLAW_AGENT_API_KEY" \
        -H "Idempotency-Key: $idem_key" \
        -d "$payload" 2>/dev/null || true)"
      retry_code="$(printf "%s" "$retry" | tail -n1 | tr -d '\r')"
      retry_body="$(printf "%s" "$retry" | sed '$d')"
      if [ "$retry_code" -ge 200 ] 2>/dev/null && [ "$retry_code" -lt 300 ] 2>/dev/null; then
        [ -n "$retry_body" ] && printf "%s\n" "$retry_body"
        echo "[xclaw] $label succeeded after auth recovery"
        return 0
      fi
      body="$retry_body"
      http_code="$retry_code"
    fi
    if [ "$http_code" = "401" ] && [ "$path" = "/agent/register" ]; then
      echo "[xclaw] register still unauthorized after auth recovery; attempting signed bootstrap credential refresh"
      if attempt_bootstrap_refresh_credentials; then
        payload="$(cat <<JSON
{
  "schemaVersion": 1,
  "agentId": "$XCLAW_AGENT_ID",
  "agentName": "$XCLAW_AGENT_NAME",
  "runtimePlatform": "$runtime_platform",
  "wallets": $wallets_json
}
JSON
)"
        retry="$(curl -sS -w '\n%{http_code}' "$url" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $XCLAW_AGENT_API_KEY" \
          -H "Idempotency-Key: $idem_key" \
          -d "$payload" 2>/dev/null || true)"
        retry_code="$(printf "%s" "$retry" | tail -n1 | tr -d '\r')"
        retry_body="$(printf "%s" "$retry" | sed '$d')"
        if [ "$retry_code" -ge 200 ] 2>/dev/null && [ "$retry_code" -lt 300 ] 2>/dev/null; then
          [ -n "$retry_body" ] && printf "%s\n" "$retry_body"
          echo "[xclaw] register succeeded after signed bootstrap credential refresh"
          return 0
        fi
        body="$retry_body"
        http_code="$retry_code"
      fi
    fi
  fi
  echo "[xclaw] $label failed (http=$http_code)"
  [ -n "$body" ] && printf "%s\n" "$body"
  return 1
}

if [ -n "\${XCLAW_AGENT_API_KEY:-}" ] && [ -n "\${XCLAW_AGENT_ID:-}" ] && [ -n "$wallet_address" ]; then
  if [ "$bootstrap_ok" = "1" ]; then
    echo "[xclaw] bootstrap completed; syncing wallet chain bindings via register upsert"
  else
    echo "[xclaw] registering agent first (required before runtime polling)"
  fi
  register_key="register-$XCLAW_AGENT_ID-$(date +%s)"
  heartbeat_key="heartbeat-$XCLAW_AGENT_ID-$(date +%s)-sync"
  register_payload="$(cat <<JSON
{
  "schemaVersion": 1,
  "agentId": "$XCLAW_AGENT_ID",
  "agentName": "$XCLAW_AGENT_NAME",
  "runtimePlatform": "$runtime_platform",
  "wallets": $wallets_json
}
JSON
)"
  heartbeat_payload="$(cat <<JSON
{
  "schemaVersion": 1,
  "agentId": "$XCLAW_AGENT_ID",
  "publicStatus": "active",
  "mode": "real",
  "approvalMode": "per_trade"
}
JSON
)"

  post_agent_with_recovery "/agent/register" "$register_key" "$register_payload" "register"
  post_agent_with_recovery "/agent/heartbeat" "$heartbeat_key" "$heartbeat_payload" "heartbeat"
  if [ "$bootstrap_ok" = "1" ]; then
    echo "[xclaw] register wallet-chain sync + heartbeat attempted"
  else
    echo "[xclaw] register + heartbeat attempted"
  fi
else
  echo "[xclaw] skipped auto-register. Provide XCLAW_AGENT_API_KEY and XCLAW_AGENT_ID, or ensure /api/v1/agent/bootstrap is enabled."
fi

echo "[xclaw] running final strict setup pass (run-loop health required)"
export XCLAW_API_BASE_URL="$XCLAW_INSTALL_CANONICAL_API_BASE"
if [ -n "\${XCLAW_AGENT_ID:-}" ]; then
  export XCLAW_BOOTSTRAP_AGENT_ID="$XCLAW_AGENT_ID"
fi
if [ -n "\${XCLAW_AGENT_API_KEY:-}" ]; then
  export XCLAW_BOOTSTRAP_AGENT_API_KEY="$XCLAW_AGENT_API_KEY"
fi
set +e
final_setup_output="$(
  XCLAW_SETUP_REQUIRE_RUN_LOOP_READY=1 \
  "$XCLAW_PYTHON_BIN" skills/xclaw-agent/scripts/setup_agent_skill.py 2>&1
)"
final_setup_status=$?
set -e
if [ -n "$final_setup_output" ]; then
  printf '%s\n' "$final_setup_output"
fi
if [ "$final_setup_status" -ne 0 ]; then
  echo "[xclaw] final strict setup failed; refusing to complete install with unhealthy run-loop wiring"
  exit "$final_setup_status"
fi

runloop_summary="$(printf '%s\n' "$final_setup_output" | "$XCLAW_PYTHON_BIN" - <<'PY'
import json, sys
last={}
for raw in sys.stdin:
    line=raw.strip()
    if line.startswith("{") and line.endswith("}"):
        try:
            parsed=json.loads(line)
            if isinstance(parsed, dict):
                last=parsed
        except Exception:
            pass
ar=last.get("approvalsRunLoop") if isinstance(last, dict) else None
health=ar.get("health") if isinstance(ar, dict) else {}
print("apiBase=" + str((health or {}).get("apiBaseUrl") or ""))
print("agentId=" + str((health or {}).get("agentId") or ""))
print("walletSigningReady=" + ("true" if bool((health or {}).get("walletSigningReady")) else "false"))
PY
)"
echo "[xclaw] xclaw.runloop.apiBase=$(printf '%s' "$runloop_summary" | awk -F= '/^apiBase=/{print $2}')"
echo "[xclaw] xclaw.runloop.agentId=$(printf '%s' "$runloop_summary" | awk -F= '/^agentId=/{print $2}')"
echo "[xclaw] xclaw.runloop.walletSigningReady=$(printf '%s' "$runloop_summary" | awk -F= '/^walletSigningReady=/{print $2}')"

echo "[xclaw] restarting OpenClaw gateway to apply updated skill/env config"
if openclaw gateway restart >/dev/null 2>&1; then
  echo "[xclaw] gateway restarted"
elif openclaw gateway stop >/dev/null 2>&1 && openclaw gateway start >/dev/null 2>&1; then
  echo "[xclaw] gateway restarted via stop/start fallback"
else
  echo "[xclaw] warning: gateway restart failed; run 'openclaw gateway restart' manually"
fi

if [ "$(id -u)" -eq 0 ] && [ -n "\${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
  echo "[xclaw] fixing ownership for user context artifacts"
  chown -R "$XCLAW_INSTALL_TARGET_USER":"$XCLAW_INSTALL_TARGET_USER" "$HOME/.openclaw" "$HOME/.xclaw-agent" "$HOME/.foundry" "$XCLAW_WORKDIR" 2>/dev/null || true
fi

if [ "$xclaw_telegram_force_management" = "enabled" ]; then
  printf '\n\\033[1;37;41m[xclaw] TELEGRAM FALLBACK MODE ENABLED\\033[0m\n'
  printf '\\033[1;33m[xclaw] Inline Approve/Deny buttons are disabled in this install context.\\033[0m\n'
  printf '\\033[1;33m[xclaw] Agent will route Telegram approvals through X-Claw management links.\\033[0m\n'
  printf '\\033[1;31m[xclaw] For full Telegram inline button functionality, rerun with sudo (recommended):\\033[0m\n'
  printf '\\033[1;33m  curl -fsSL https://xclaw.trade/skill-install.sh | sudo bash\\033[0m\n\n'
fi

echo "[xclaw] install complete"
`;
}

export async function GET(req: NextRequest) {
  const publicBaseUrl = resolvePublicBaseUrl(req);
  const body = buildInstallerScript(publicBaseUrl);
  return new NextResponse(body, {
    status: 200,
    headers: {
      'content-type': 'text/x-shellscript; charset=utf-8',
      'cache-control': 'public, max-age=300'
    }
  });
}
