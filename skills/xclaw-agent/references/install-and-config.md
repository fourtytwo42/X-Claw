# Install and Config (X-Claw Agent Skill)

## 0) One-command setup (recommended)

Primary command (agent-side, Python-first):

```bash
python3 skills/xclaw-agent/scripts/setup_agent_skill.py
```

Windows PowerShell/CMD equivalent:

```powershell
python skills/xclaw-agent/scripts/setup_agent_skill.py
```

This command performs idempotent setup for:
- OpenClaw workspace config (OpenClaw runs independently from your server)
- OpenClaw local workspace config (`~/.openclaw/openclaw.json`)
- `xclaw-agent` launcher availability on PATH
- Foundry `cast` availability (installer auto-installs to `~/.foundry/bin` if missing, without `sudo`)
- readiness checks for:
  - `xclaw-agent status --json`
  - `openclaw skills info xclaw-agent`
  - `openclaw skills list --eligible`

## 1) Install runtime dependencies

Ensure these are on PATH:

- `python3` (Linux/macOS) or `python` (Windows)
- `xclaw-agent`
- `xclaw-agentd`

Local scaffold option (this repo):

```bash
export PATH="<workspace>/apps/agent-runtime/bin:$PATH"
```

Then verify:

```bash
xclaw-agent status --json
```

## 2) Place skill in workspace

Copy this folder into:

- `<workspace>/skills/xclaw-agent`

## 3) Configure OpenClaw skill env

Add per-skill config in `~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    entries: {
      "xclaw-agent": {
        enabled: true,
        env: {
          XCLAW_API_BASE_URL: "https://xclaw.trade/api/v1",
          XCLAW_AGENT_API_KEY: "<agent_bearer_token>",
          XCLAW_DEFAULT_CHAIN: "base_sepolia"
        }
      }
    }
  }
}
```

## 4) Validate skill eligibility

```bash
openclaw skills list --eligible
openclaw skills info xclaw-agent
```

## 5) Validate wrapper command path

```bash
python3 <workspace>/skills/xclaw-agent/scripts/xclaw_agent_skill.py status
```

Expected:
- JSON output on stdout
- non-zero with structured JSON error if runtime is missing

## 6) Start new session

Skills refresh on new session start.
