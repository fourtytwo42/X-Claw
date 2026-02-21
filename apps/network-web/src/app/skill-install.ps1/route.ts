import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

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
  return `$ErrorActionPreference = "Stop"

Write-Host "[xclaw] bootstrap start"

if (-not $env:XCLAW_WORKDIR) { $env:XCLAW_WORKDIR = Join-Path $HOME "xclaw" }
if (-not $env:XCLAW_REPO_REF) { $env:XCLAW_REPO_REF = "main" }
if (-not $env:XCLAW_REPO_URL) { $env:XCLAW_REPO_URL = "https://github.com/fourtytwo42/ETHDenver2026" }
$env:XCLAW_INSTALL_ORIGIN = "${origin}"
if (-not $env:XCLAW_INSTALL_FORCE_LOCAL_API) { $env:XCLAW_INSTALL_FORCE_LOCAL_API = "0" }
if ($env:XCLAW_INSTALL_FORCE_LOCAL_API -eq "1") {
  $env:XCLAW_INSTALL_CANONICAL_API_BASE = "http://127.0.0.1:3000/api/v1"
} elseif ($env:XCLAW_INSTALL_ORIGIN -match '^https?://(127\\.0\\.0\\.1|localhost)(:[0-9]+)?$') {
  $env:XCLAW_INSTALL_CANONICAL_API_BASE = "https://xclaw.trade/api/v1"
} elseif ($env:XCLAW_INSTALL_ORIGIN -match '^https?://xclaw\\.trade$') {
  $env:XCLAW_INSTALL_CANONICAL_API_BASE = "https://xclaw.trade/api/v1"
} else {
  $env:XCLAW_INSTALL_CANONICAL_API_BASE = "${origin}/api/v1"
}
if (-not $env:XCLAW_API_BASE_URL) { $env:XCLAW_API_BASE_URL = "$($env:XCLAW_INSTALL_CANONICAL_API_BASE)" }
if (-not $env:XCLAW_DEFAULT_CHAIN) { $env:XCLAW_DEFAULT_CHAIN = "base_sepolia" }

function Resolve-Python {
  if ($env:XCLAW_AGENT_PYTHON_BIN -and (Test-Path $env:XCLAW_AGENT_PYTHON_BIN)) {
    return @($env:XCLAW_AGENT_PYTHON_BIN)
  }

  $py = Get-Command python -ErrorAction SilentlyContinue
  if ($py) {
    return @($py.Source)
  }

  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    return @($pyLauncher.Source, "-3")
  }

  throw "python (or py -3) was not found on PATH."
}

function Invoke-Python {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
  $cmd = Resolve-Python
  $exe = $cmd[0]
  $prefix = @()
  if ($cmd.Count -gt 1) {
    $prefix = $cmd[1..($cmd.Count - 1)]
  }
  & $exe @prefix @Args
}

function Test-PythonImport {
  param([string]$ModuleName)
  try {
    Invoke-Python "-c" "import importlib; importlib.import_module('$ModuleName')" | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Ensure-PythonRuntimeDeps {
  $requirementsPath = Join-Path $env:XCLAW_WORKDIR "apps\\agent-runtime\\requirements.txt"
  if (-not (Test-Path $requirementsPath)) {
    throw "Runtime requirements file not found: $requirementsPath"
  }

  $hasArgon2 = Test-PythonImport -ModuleName "argon2"
  $hasKeccak = Test-PythonImport -ModuleName "Crypto.Hash.keccak"
  $hasCrypto = Test-PythonImport -ModuleName "cryptography.hazmat.primitives.asymmetric.ec"
  if ($hasArgon2 -and $hasKeccak -and $hasCrypto) {
    Write-Host "[xclaw] python runtime deps already installed for selected interpreter"
    return
  }

  Write-Host "[xclaw] ensuring pip is available for selected Python interpreter"
  try {
    Invoke-Python "-m" "pip" "--version" | Out-Null
  } catch {
    try {
      Invoke-Python "-m" "ensurepip" "--upgrade" | Out-Null
    } catch {
      # Continue to get-pip fallback.
    }
  }

  try {
    Invoke-Python "-m" "pip" "--version" | Out-Null
  } catch {
    $getPipPath = Join-Path $tmpRoot "get-pip.py"
    Write-Host "[xclaw] pip still unavailable; bootstrapping via get-pip.py"
    try {
      Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPipPath
      Invoke-Python $getPipPath "--user" | Out-Null
    } catch {
      # Continue to venv fallback.
    }
  }

  $usingVenv = $false
  try {
    Invoke-Python "-m" "pip" "--version" | Out-Null
  } catch {
    $venvDir = Join-Path $HOME ".xclaw-agent\\runtime-venv"
    Write-Host "[xclaw] pip unavailable on system interpreter; creating fallback venv at $venvDir"
    try {
      Invoke-Python "-m" "venv" $venvDir | Out-Null
    } catch {
      Write-Host "[xclaw] standard venv creation failed; retrying with --without-pip"
      try {
        Invoke-Python "-m" "venv" "--without-pip" $venvDir | Out-Null
      } catch {
        throw "Unable to provision pip or create venv fallback. Install python3-venv or provide XCLAW_AGENT_PYTHON_BIN."
      }
    }
    $venvPython = Join-Path $venvDir "Scripts\\python.exe"
    if (-not (Test-Path $venvPython)) {
      throw "Fallback venv python not found: $venvPython"
    }
    $env:XCLAW_AGENT_PYTHON_BIN = $venvPython
    $usingVenv = $true
    try {
      Invoke-Python "-m" "pip" "--version" | Out-Null
    } catch {
      $getPipPath = Join-Path $tmpRoot "get-pip.py"
      try {
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPipPath
        Invoke-Python $getPipPath | Out-Null
      } catch {
        throw "Venv created but pip bootstrap failed. Install python3-pip or provide XCLAW_AGENT_PYTHON_BIN."
      }
    }
    Invoke-Python "-m" "pip" "--version" | Out-Null
  }

  Write-Host "[xclaw] installing python runtime deps from $requirementsPath"
  if ($usingVenv) {
    Invoke-Python "-m" "pip" "install" "--disable-pip-version-check" "-r" $requirementsPath | Out-Null
  } else {
    Invoke-Python "-m" "pip" "install" "--disable-pip-version-check" "--user" "-r" $requirementsPath | Out-Null
  }

  $hasArgon2 = Test-PythonImport -ModuleName "argon2"
  $hasKeccak = Test-PythonImport -ModuleName "Crypto.Hash.keccak"
  $hasCrypto = Test-PythonImport -ModuleName "cryptography.hazmat.primitives.asymmetric.ec"
  if (-not ($hasArgon2 -and $hasKeccak -and $hasCrypto)) {
    throw "Python runtime dependency verification failed after install."
  }
}

function Get-JsonStringProperty {
  param([string]$JsonText, [string]$PropertyName)
  if ([string]::IsNullOrWhiteSpace($JsonText)) {
    return ""
  }
  try {
    $obj = $JsonText | ConvertFrom-Json
  } catch {
    return ""
  }
  $value = $obj.$PropertyName
  if ($null -eq $value) {
    return ""
  }
  return [string]$value
}

function Set-OpenClawConfigSafe {
  param([string]$Key, [string]$Value)
  try {
    & openclaw config set $Key $Value | Out-Null
  } catch {
    return
  }
}

function Get-OpenClawConfigValue {
  param([string]$Key)
  try {
    $raw = & openclaw config get $Key 2>$null
    if (-not $raw) {
      return ""
    }
    $lines = @($raw | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -eq 0) {
      return ""
    }
    $last = [string]$lines[$lines.Count - 1]
    $trimmed = $last.Trim()
    if ($trimmed -eq "null") {
      return ""
    }
    if ($trimmed.StartsWith('"') -and $trimmed.EndsWith('"') -and $trimmed.Length -ge 2) {
      return $trimmed.Substring(1, $trimmed.Length - 2)
    }
    return $trimmed
  } catch {
    return ""
  }
}

function Repo-ArchiveBase {
  param([string]$RepoUrl)
  $clean = $RepoUrl -replace '\\.git$', ''
  $clean = $clean -replace '^https?://github\\.com/', ''
  return $clean.Trim('/')
}

function Ensure-Cast {
  $foundryBin = Join-Path $HOME ".foundry\\bin"
  if (Test-Path $foundryBin) {
    $env:PATH = "$foundryBin;$($env:PATH)"
  }

  if (Get-Command cast -ErrorAction SilentlyContinue) {
    Write-Host "[xclaw] cast already installed"
    return
  }

  Write-Host "[xclaw] cast not found; attempting foundryup if available"
  if (Get-Command foundryup -ErrorAction SilentlyContinue) {
    try {
      & foundryup | Out-Null
      if (Get-Command cast -ErrorAction SilentlyContinue) {
        $castVersion = (& cast --version | Select-Object -First 1)
        Write-Host "[xclaw] cast installed: $castVersion"
        return
      }
    } catch {
      # fall through to actionable error
    }
  }

  throw "cast is unavailable. Install Foundry for Windows and ensure cast is on PATH, then rerun."
}

function Resolve-XclawAgentBin {
  $homeLauncherDir = Join-Path $HOME ".xclaw-agent\\bin"
  if (Test-Path $homeLauncherDir) {
    $env:PATH = "$homeLauncherDir;$($env:PATH)"
  }

  $configured = Get-OpenClawConfigValue "skills.entries.xclaw-agent.env.XCLAW_AGENT_RUNTIME_BIN"
  if ($configured -and (Test-Path $configured)) {
    return $configured
  }

  $cmd = Get-Command xclaw-agent -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  $workspaceBin = Join-Path $env:XCLAW_WORKDIR "apps\\agent-runtime\\bin\\xclaw-agent"
  if (Test-Path $workspaceBin) {
    return $workspaceBin
  }

  throw "xclaw-agent launcher not found after setup. Expected ~/.xclaw-agent/bin or apps/agent-runtime/bin."
}

function Persist-UserPath {
  param([string]$RuntimeBin)
  if (-not $RuntimeBin) {
    return
  }
  $localBin = Join-Path $HOME ".local\\bin"
  New-Item -ItemType Directory -Path $localBin -Force | Out-Null
  $shimPath = Join-Path $localBin "xclaw-agent.cmd"
  @(
    "@echo off",
    "setlocal",
    ('"' + $RuntimeBin + '" %*')
  ) | Set-Content -Path $shimPath -Encoding ASCII

  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $parts = @()
  if ($userPath) {
    $parts = $userPath.Split(';') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
  }
  foreach ($entry in @((Join-Path $HOME ".xclaw-agent\\bin"), $localBin)) {
    if ($parts -notcontains $entry) {
      $parts += $entry
    }
  }
  [Environment]::SetEnvironmentVariable("Path", ($parts -join ';'), "User")
}

function Write-PassphraseBackup {
  param([string]$BackupPath, [string]$Passphrase)
  if ([string]::IsNullOrWhiteSpace($BackupPath) -or [string]::IsNullOrWhiteSpace($Passphrase)) {
    return
  }
  try {
    $env:XCLAW_PASSPHRASE_BACKUP_PATH = $BackupPath
    $env:XCLAW_WALLET_PASSPHRASE = $Passphrase
    Invoke-Python "-c" @'
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
for candidate in (
    os.environ.get("COMPUTERNAME", ""),
    os.environ.get("USERDOMAIN", ""),
):
    if candidate:
        machine_id = candidate
        break

ikm = hashlib.sha256(("|".join([machine_id, os.environ.get("USERNAME", ""), str(pathlib.Path.home())])).encode("utf-8")).digest()
hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"xclaw-passphrase-backup-v1", info=b"xclaw", backend=None)
key = hkdf.derive(ikm)

nonce = os.urandom(12)
aad = b"xclaw-passphrase-backup-v1"
ct = AESGCM(key).encrypt(nonce, passphrase.encode("utf-8"), aad)

payload = {
    "schemaVersion": 1,
    "algo": "AES-256-GCM+HKDF-SHA256(machine,user,home)",
    "nonceB64": base64.b64encode(nonce).decode("ascii"),
    "ciphertextB64": base64.b64encode(ct).decode("ascii"),
}
backup_path.write_text(json.dumps(payload, separators=(",", ":")) + "\\n", encoding="utf-8")
'@ | Out-Null
  } catch {
    return
  }
}

function Read-PassphraseBackup {
  param([string]$BackupPath)
  if ([string]::IsNullOrWhiteSpace($BackupPath) -or -not (Test-Path $BackupPath)) {
    return ""
  }
  try {
    $env:XCLAW_PASSPHRASE_BACKUP_PATH = $BackupPath
    $out = Invoke-Python "-c" @'
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
for candidate in (
    os.environ.get("COMPUTERNAME", ""),
    os.environ.get("USERDOMAIN", ""),
):
    if candidate:
        machine_id = candidate
        break

ikm = hashlib.sha256(("|".join([machine_id, os.environ.get("USERNAME", ""), str(pathlib.Path.home())])).encode("utf-8")).digest()
hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"xclaw-passphrase-backup-v1", info=b"xclaw", backend=None)
key = hkdf.derive(ikm)

aad = b"xclaw-passphrase-backup-v1"
pt = AESGCM(key).decrypt(nonce, ct, aad)
sys.stdout.write(pt.decode("utf-8"))
'@
    if (-not $out) {
      return ""
    }
    return ([string]$out).Trim()
  } catch {
    return ""
  }
}

$runtimePlatform = "windows"
if ($IsMacOS) {
  $runtimePlatform = "macos"
} elseif (-not $IsWindows) {
  $runtimePlatform = "linux"
}

$tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("xclaw-install-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmpRoot | Out-Null
try {
  $workdir = $env:XCLAW_WORKDIR
  if (Test-Path (Join-Path $workdir ".git")) {
    Write-Host "[xclaw] existing git workspace found: $workdir"
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
      throw "git is required for updating an existing git workspace."
    }
    Push-Location $workdir
    try {
      & git fetch --all --prune
      & git checkout $env:XCLAW_REPO_REF
      & git pull --ff-only
    } finally {
      Pop-Location
    }
  } else {
    $archiveBase = Repo-ArchiveBase -RepoUrl $env:XCLAW_REPO_URL
    $archiveUrl = "https://codeload.github.com/$archiveBase/zip/refs/heads/$($env:XCLAW_REPO_REF)"
    $zipPath = Join-Path $tmpRoot "repo.zip"
    Write-Host "[xclaw] downloading source archive: $archiveUrl"
    Invoke-WebRequest -Uri $archiveUrl -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $tmpRoot -Force

    $srcDir = Get-ChildItem -Path $tmpRoot -Directory | Where-Object { $_.Name -like "ETHDenver2026-*" } | Select-Object -First 1
    if (-not $srcDir) {
      throw "Unable to find extracted repository directory."
    }

    if (-not (Test-Path $workdir)) {
      Write-Host "[xclaw] creating workspace: $workdir"
      New-Item -ItemType Directory -Path $workdir -Force | Out-Null
    } else {
      Write-Host "[xclaw] existing non-git directory at $workdir; updating in place"
    }

    Get-ChildItem -Path $srcDir.FullName -Force | ForEach-Object {
      Copy-Item -Path $_.FullName -Destination $workdir -Recurse -Force
    }
  }

  Push-Location $workdir
  try {
    Ensure-Cast
    Ensure-PythonRuntimeDeps

    Write-Host "[xclaw] running setup_agent_skill.py"
    Invoke-Python "skills/xclaw-agent/scripts/setup_agent_skill.py"
    $xclawAgentBin = Resolve-XclawAgentBin
    Write-Host "[xclaw] using runtime launcher: $xclawAgentBin"
    Persist-UserPath -RuntimeBin $xclawAgentBin

    Write-Host "[xclaw] configuring OpenClaw skill env defaults"
    if (-not $env:XCLAW_BUILDER_CODE_BASE) {
      $existingBuilderBase = Get-OpenClawConfigValue "skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE"
      if ($existingBuilderBase) {
        $env:XCLAW_BUILDER_CODE_BASE = $existingBuilderBase
      } else {
        $env:XCLAW_BUILDER_CODE_BASE = "xclaw"
        Write-Host "[xclaw] defaulted XCLAW_BUILDER_CODE_BASE=xclaw"
      }
    }
    if (-not $env:XCLAW_BUILDER_CODE_BASE_SEPOLIA) {
      $existingBuilderBaseSepolia = Get-OpenClawConfigValue "skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE_SEPOLIA"
      if ($existingBuilderBaseSepolia) {
        $env:XCLAW_BUILDER_CODE_BASE_SEPOLIA = $existingBuilderBaseSepolia
      } else {
        $env:XCLAW_BUILDER_CODE_BASE_SEPOLIA = $env:XCLAW_BUILDER_CODE_BASE
        Write-Host "[xclaw] defaulted XCLAW_BUILDER_CODE_BASE_SEPOLIA=$($env:XCLAW_BUILDER_CODE_BASE_SEPOLIA)"
      }
    }
    Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_API_BASE_URL" "$($env:XCLAW_API_BASE_URL)"
    Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_DEFAULT_CHAIN" "$($env:XCLAW_DEFAULT_CHAIN)"
    Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_AGENT_PYTHON_BIN" "$($env:XCLAW_AGENT_PYTHON_BIN)"
    Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE" "$($env:XCLAW_BUILDER_CODE_BASE)"
    Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_BUILDER_CODE_BASE_SEPOLIA" "$($env:XCLAW_BUILDER_CODE_BASE_SEPOLIA)"
    Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_TELEGRAM_APPROVALS_FORCE_MANAGEMENT" "disabled"
    if ($env:XCLAW_AGENT_ID) {
      Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_AGENT_ID" "$($env:XCLAW_AGENT_ID)"
    }
    if ($env:XCLAW_AGENT_NAME) {
      Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_AGENT_NAME" "$($env:XCLAW_AGENT_NAME)"
    }

    $walletHome = if ($env:XCLAW_AGENT_HOME) { $env:XCLAW_AGENT_HOME } else { Join-Path $HOME ".xclaw-agent" }
    $walletStorePath = Join-Path $walletHome "wallets.json"
    $walletExists = $false
    if (Test-Path $walletStorePath) {
      $existingWalletJson = Invoke-Python "skills/xclaw-agent/scripts/xclaw_agent_skill.py" "wallet-address"
      $existingWalletAddress = (Get-JsonStringProperty -JsonText $existingWalletJson -PropertyName "address").Trim()
      if ($existingWalletAddress) {
        $walletExists = $true
      }
    }

    if (-not $env:XCLAW_WALLET_PASSPHRASE) {
      $existingCfgPassphrase = Get-OpenClawConfigValue "skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE"
      if ($existingCfgPassphrase) {
        $env:XCLAW_WALLET_PASSPHRASE = $existingCfgPassphrase
      } elseif (-not $walletExists) {
        $env:XCLAW_WALLET_PASSPHRASE = (Invoke-Python "-c" "import secrets; print(secrets.token_urlsafe(32))").Trim()
        Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE" "$($env:XCLAW_WALLET_PASSPHRASE)"
        Write-Host "[xclaw] generated new wallet passphrase for first install"
      } else {
        Write-Host "[xclaw] existing wallet detected; preserving existing passphrase/config"
      }
    }
    if ($env:XCLAW_WALLET_PASSPHRASE) {
      Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE" "$($env:XCLAW_WALLET_PASSPHRASE)"
    }

    $passphraseBackupPath = Join-Path $walletHome "passphrase.backup.v1.json"
    Write-PassphraseBackup -BackupPath $passphraseBackupPath -Passphrase $env:XCLAW_WALLET_PASSPHRASE

    if ($walletExists -and -not $env:XCLAW_WALLET_PASSPHRASE) {
      $recovered = Read-PassphraseBackup -BackupPath $passphraseBackupPath
      if ($recovered) {
        $env:XCLAW_WALLET_PASSPHRASE = $recovered
        Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE" "$($env:XCLAW_WALLET_PASSPHRASE)"
      }
    }

    if ($env:XCLAW_AGENT_API_KEY) {
      Set-OpenClawConfigSafe "skills.entries.xclaw-agent.apiKey" "$($env:XCLAW_AGENT_API_KEY)"
      Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_AGENT_API_KEY" "$($env:XCLAW_AGENT_API_KEY)"
      Write-Host "[xclaw] saved XCLAW_AGENT_API_KEY into OpenClaw config for xclaw-agent"
    } else {
      Write-Host "[xclaw] XCLAW_AGENT_API_KEY not provided; installer will request credentials from /api/v1/agent/bootstrap"
    }

    if ($walletExists) {
      Write-Host "[xclaw] wallet already exists; keeping existing wallet"
    } else {
      Write-Host "[xclaw] first install detected; creating wallet"
      & $xclawAgentBin wallet create --chain "$($env:XCLAW_DEFAULT_CHAIN)" --json | Out-Null
    }

    Write-Host "[xclaw] wallet address"
    $walletJson = Invoke-Python "skills/xclaw-agent/scripts/xclaw_agent_skill.py" "wallet-address"
    Write-Output $walletJson
    $walletAddress = (Get-JsonStringProperty -JsonText $walletJson -PropertyName "address").Trim()

    if ($walletExists) {
      if (-not $env:XCLAW_WALLET_PASSPHRASE) {
        throw "[xclaw] existing wallet detected but XCLAW_WALLET_PASSPHRASE is not configured. Restore the original passphrase and rerun."
      }

      $walletHealthJson = ""
      try {
        $walletHealthJson = & $xclawAgentBin wallet health --chain "$($env:XCLAW_DEFAULT_CHAIN)" --json
      } catch {
        $walletHealthJson = ""
      }
      $walletHealthOk = (Get-JsonStringProperty -JsonText $walletHealthJson -PropertyName "ok")
      $walletIntegrity = (Get-JsonStringProperty -JsonText $walletHealthJson -PropertyName "integrityChecked")
      if ($walletHealthOk -ne "True" -or $walletIntegrity -ne "True") {
        $recovered = Read-PassphraseBackup -BackupPath $passphraseBackupPath
        if ($recovered) {
          $env:XCLAW_WALLET_PASSPHRASE = $recovered
          Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_WALLET_PASSPHRASE" "$($env:XCLAW_WALLET_PASSPHRASE)"
        }
        try {
          $walletHealthJson = & $xclawAgentBin wallet health --chain "$($env:XCLAW_DEFAULT_CHAIN)" --json
        } catch {
          $walletHealthJson = ""
        }
        $walletHealthOk = (Get-JsonStringProperty -JsonText $walletHealthJson -PropertyName "ok")
        $walletIntegrity = (Get-JsonStringProperty -JsonText $walletHealthJson -PropertyName "integrityChecked")
        if ($walletHealthOk -ne "True" -or $walletIntegrity -ne "True") {
          throw "[xclaw] wallet health check failed; wallet cannot be decrypted with current passphrase."
        }
      }
    }

    $runtimeWalletChains = @()
    try {
      $chainsPayload = & $xclawAgentBin chains --json | ConvertFrom-Json
      if ($chainsPayload -and $chainsPayload.chains) {
        foreach ($row in $chainsPayload.chains) {
          $chainKey = if ($null -eq $row.chainKey) { "" } else { [string]$row.chainKey }
          if (-not $chainKey) { continue }
          $walletCap = $true
          if ($row.capabilities -and $null -ne $row.capabilities.wallet) {
            $walletCap = [bool]$row.capabilities.wallet
          }
          if (-not $walletCap) { continue }
          if (-not ($runtimeWalletChains -contains $chainKey)) {
            $runtimeWalletChains += $chainKey
          }
        }
      }
    } catch {
      $runtimeWalletChains = @()
    }
    if (-not ($runtimeWalletChains -contains $env:XCLAW_DEFAULT_CHAIN)) {
      $runtimeWalletChains = @($env:XCLAW_DEFAULT_CHAIN) + $runtimeWalletChains
    }
    if ($runtimeWalletChains.Count -eq 0) {
      $runtimeWalletChains = @($env:XCLAW_DEFAULT_CHAIN)
    }

    $walletRows = @()
    $walletBindingFailed = $false
    foreach ($chainKey in $runtimeWalletChains) {
      if (-not $chainKey) { continue }
      Write-Host "[xclaw] ensuring portable wallet is bound on $chainKey"
      $bindOutput = ""
      try {
        $bindOutput = & $xclawAgentBin wallet create --chain $chainKey --json 2>&1
        if ($LASTEXITCODE -ne 0) { throw "wallet_create_failed" }
      } catch {
        $bindCode = (Get-JsonStringProperty -JsonText "$bindOutput" -PropertyName "code").Trim()
        if ($bindCode -eq "wallet_exists") {
          Write-Host "[xclaw] wallet already bound for $chainKey"
        } else {
          $walletBindingFailed = $true
          Write-Host "[xclaw] warning: wallet auto-bind failed for chain=$chainKey"
          if ($bindOutput) { Write-Output $bindOutput }
        }
      }

      $addrJson = ""
      $addr = ""
      try {
        $addrJson = & $xclawAgentBin wallet address --chain $chainKey --json 2>$null
        $addr = (Get-JsonStringProperty -JsonText "$addrJson" -PropertyName "address").Trim()
      } catch {
        $addr = ""
      }
      if (-not $addr -and $chainKey -eq $env:XCLAW_DEFAULT_CHAIN) {
        $addr = $walletAddress
      }
      if ($addr) {
        $walletRows += @{ chainKey = $chainKey; address = $addr }
      }
    }

    if ($walletBindingFailed) {
      Write-Host "[xclaw] warning: one or more wallet chain bindings failed; installer will continue with available bindings"
    }

    $bootstrapOk = $false
    if (-not $env:XCLAW_AGENT_API_KEY -and $walletAddress) {
      Write-Host "[xclaw] no API key provided; requesting auto-bootstrap credentials from server"
      $challengePayload = @{
        schemaVersion = 1
        chainKey = $env:XCLAW_DEFAULT_CHAIN
        walletAddress = $walletAddress
      } | ConvertTo-Json -Depth 4 -Compress

      $challenge = Invoke-RestMethod -Method Post -Uri "$($env:XCLAW_API_BASE_URL)/agent/bootstrap/challenge" -ContentType "application/json" -Body $challengePayload
      $challengeId = if ($null -eq $challenge.challengeId) { "" } else { [string]$challenge.challengeId }
      $challengeMessage = if ($null -eq $challenge.challengeMessage) { "" } else { [string]$challenge.challengeMessage }
      if (-not $challengeId -or -not $challengeMessage) {
        throw "[xclaw] bootstrap challenge failed; unable to continue"
      }

      Write-Host "[xclaw] signing bootstrap challenge with local wallet"
      $sigJson = Invoke-Python "skills/xclaw-agent/scripts/xclaw_agent_skill.py" "wallet-sign-challenge" "$challengeMessage"
      $signature = (Get-JsonStringProperty -JsonText $sigJson -PropertyName "signature").Trim()
      if (-not $signature) {
        throw "[xclaw] unable to sign bootstrap challenge (missing signature). Ensure XCLAW_WALLET_PASSPHRASE is configured and cast is installed."
      }

      $bootstrapPayload = @{
        schemaVersion = 2
        walletAddress = $walletAddress
        runtimePlatform = $runtimePlatform
        chainKey = $env:XCLAW_DEFAULT_CHAIN
        challengeId = $challengeId
        signature = $signature
        mode = "real"
        approvalMode = "per_trade"
        publicStatus = "active"
      }
      if ($env:XCLAW_AGENT_NAME) {
        $bootstrapPayload["agentName"] = $env:XCLAW_AGENT_NAME
      }

      $bootstrap = Invoke-RestMethod -Method Post -Uri "$($env:XCLAW_API_BASE_URL)/agent/bootstrap" -ContentType "application/json" -Body ($bootstrapPayload | ConvertTo-Json -Depth 8 -Compress)
      $bootAgentId = if ($null -eq $bootstrap.agentId) { "" } else { [string]$bootstrap.agentId }
      $bootApiKey = if ($null -eq $bootstrap.agentApiKey) { "" } else { [string]$bootstrap.agentApiKey }
      $bootAgentName = if ($null -eq $bootstrap.agentName) { "" } else { [string]$bootstrap.agentName }
      if ($bootAgentId -and $bootApiKey) {
        $env:XCLAW_AGENT_ID = $bootAgentId
        $env:XCLAW_AGENT_API_KEY = $bootApiKey
        if ($bootAgentName) {
          $env:XCLAW_AGENT_NAME = $bootAgentName
        }
        $bootstrapOk = $true
        Set-OpenClawConfigSafe "skills.entries.xclaw-agent.apiKey" "$($env:XCLAW_AGENT_API_KEY)"
        Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_AGENT_API_KEY" "$($env:XCLAW_AGENT_API_KEY)"
        Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_AGENT_ID" "$($env:XCLAW_AGENT_ID)"
        if ($env:XCLAW_AGENT_NAME) {
          Set-OpenClawConfigSafe "skills.entries.xclaw-agent.env.XCLAW_AGENT_NAME" "$($env:XCLAW_AGENT_NAME)"
        }
        Write-Host "[xclaw] bootstrap issued agent credentials and wrote OpenClaw config (agentId=$($env:XCLAW_AGENT_ID), agentName=$($env:XCLAW_AGENT_NAME))"
      } else {
        Write-Host "[xclaw] bootstrap endpoint did not return agent credentials; falling back to manual/inferred registration path"
      }
    }

    if (-not $env:XCLAW_AGENT_ID -and $env:XCLAW_AGENT_API_KEY) {
      Write-Host "[xclaw] attempting to infer XCLAW_AGENT_ID from API token"
      try {
        $pending = Invoke-RestMethod -Method Get -Uri "$($env:XCLAW_API_BASE_URL)/limit-orders/pending?chainKey=$($env:XCLAW_DEFAULT_CHAIN)&limit=1" -Headers @{ Authorization = "Bearer $($env:XCLAW_AGENT_API_KEY)" }
        $inferred = if ($null -eq $pending.agentId) { "" } else { [string]$pending.agentId }
        if ($inferred) {
          $env:XCLAW_AGENT_ID = $inferred
          Write-Host "[xclaw] inferred agent id: $($env:XCLAW_AGENT_ID)"
        }
      } catch {
        # best effort only
      }
    }

    if ($bootstrapOk) {
      Write-Host "[xclaw] register + heartbeat already completed by bootstrap endpoint"
    } elseif ($env:XCLAW_AGENT_API_KEY -and $env:XCLAW_AGENT_ID -and $walletAddress) {
      Write-Host "[xclaw] registering agent first (required before runtime polling)"
      $epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
      $registerKey = "register-$($env:XCLAW_AGENT_ID)-$epoch"
      $heartbeatKey = "heartbeat-$($env:XCLAW_AGENT_ID)-$epoch"
      $registerPayload = @{
        schemaVersion = 1
        agentId = $env:XCLAW_AGENT_ID
        agentName = $env:XCLAW_AGENT_NAME
        runtimePlatform = $runtimePlatform
        wallets = if ($walletRows.Count -gt 0) { $walletRows } else { @(@{ chainKey = $env:XCLAW_DEFAULT_CHAIN; address = $walletAddress }) }
      } | ConvertTo-Json -Depth 8 -Compress

      $heartbeatPayload = @{
        schemaVersion = 1
        agentId = $env:XCLAW_AGENT_ID
        publicStatus = "active"
        mode = "real"
        approvalMode = "per_trade"
      } | ConvertTo-Json -Depth 6 -Compress

      Invoke-RestMethod -Method Post -Uri "$($env:XCLAW_API_BASE_URL)/agent/register" -Headers @{ Authorization = "Bearer $($env:XCLAW_AGENT_API_KEY)"; "Idempotency-Key" = $registerKey } -ContentType "application/json" -Body $registerPayload | Out-Null
      Invoke-RestMethod -Method Post -Uri "$($env:XCLAW_API_BASE_URL)/agent/heartbeat" -Headers @{ Authorization = "Bearer $($env:XCLAW_AGENT_API_KEY)"; "Idempotency-Key" = $heartbeatKey } -ContentType "application/json" -Body $heartbeatPayload | Out-Null
      Write-Host "[xclaw] register + heartbeat attempted"
    } else {
      Write-Host "[xclaw] skipped auto-register. Provide XCLAW_AGENT_API_KEY and XCLAW_AGENT_ID, or ensure /api/v1/agent/bootstrap is enabled."
    }

    Write-Host "[xclaw] running final strict setup pass (run-loop health required)"
    $env:XCLAW_API_BASE_URL = "$($env:XCLAW_INSTALL_CANONICAL_API_BASE)"
    if ($env:XCLAW_AGENT_ID) { $env:XCLAW_BOOTSTRAP_AGENT_ID = "$($env:XCLAW_AGENT_ID)" }
    if ($env:XCLAW_AGENT_API_KEY) { $env:XCLAW_BOOTSTRAP_AGENT_API_KEY = "$($env:XCLAW_AGENT_API_KEY)" }

    $env:XCLAW_SETUP_REQUIRE_RUN_LOOP_READY = "1"
    $setupFinalJson = Invoke-Python "skills/xclaw-agent/scripts/setup_agent_skill.py"
    $setupFinalParsed = $null
    try {
      $setupFinalParsed = $setupFinalJson | ConvertFrom-Json
    } catch {
      throw "[xclaw] final strict setup returned non-JSON output; cannot verify run-loop health."
    }
    $runLoop = $setupFinalParsed.approvalsRunLoop
    $health = if ($null -ne $runLoop) { $runLoop.health } else { $null }
    $runLoopEnabled = if ($null -ne $runLoop -and $null -ne $runLoop.enabled) { [bool]$runLoop.enabled } else { $false }
    $envValidated = if ($null -ne $runLoop -and $null -ne $runLoop.envValidated) { [bool]$runLoop.envValidated } else { $false }
    $walletSigningReady = if ($null -ne $health -and $null -ne $health.walletSigningReady) { [bool]$health.walletSigningReady } else { $false }
    if (-not $runLoopEnabled -or -not $envValidated -or -not $walletSigningReady) {
      throw "[xclaw] final strict setup failed run-loop health validation (enabled/envValidated/walletSigningReady required)."
    }
    Write-Host "[xclaw] xclaw.runloop.apiBase=$($health.apiBaseUrl)"
    Write-Host "[xclaw] xclaw.runloop.agentId=$($health.agentId)"
    Write-Host "[xclaw] xclaw.runloop.walletSigningReady=$walletSigningReady"

    Write-Host "[xclaw] restarting OpenClaw gateway to apply updated skill/env config"
    try {
      & openclaw gateway restart | Out-Null
      Write-Host "[xclaw] gateway restarted"
    } catch {
      try {
        & openclaw gateway stop | Out-Null
        & openclaw gateway start | Out-Null
        Write-Host "[xclaw] gateway restarted via stop/start fallback"
      } catch {
        Write-Host "[xclaw] warning: gateway restart failed; run 'openclaw gateway restart' manually"
      }
    }
  } finally {
    Pop-Location
  }

  Write-Host ""
  Write-Host "[xclaw] install complete"
  Write-Host ""
  Write-Host "Next steps:"
  Write-Host "1) Fetch full instructions:"
  Write-Host "   irm ${origin}/skill.md"
  Write-Host "2) Verify skill availability in OpenClaw:"
  Write-Host "   openclaw skills info xclaw-agent"
  Write-Host "3) Register + heartbeat:"
  Write-Host "   attempted automatically via bootstrap endpoint or provided credentials"
  Write-Host "4) Gateway:"
  Write-Host "   restarted automatically (fallback warning shown if restart failed)"
  Write-Host "5) Runtime checks:"
  Write-Host "   python skills/xclaw-agent/scripts/xclaw_agent_skill.py status"
  Write-Host "6) Verify installed script versions/hashes:"
  Write-Host "   python skills/xclaw-agent/scripts/xclaw_agent_skill.py version"
} finally {
  if (Test-Path $tmpRoot) {
    Remove-Item -Path $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}
`;
}

export async function GET(req: NextRequest) {
  const publicBaseUrl = resolvePublicBaseUrl(req);
  const body = buildInstallerScript(publicBaseUrl);
  return new NextResponse(body, {
    status: 200,
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'cache-control': 'public, max-age=300'
    }
  });
}
