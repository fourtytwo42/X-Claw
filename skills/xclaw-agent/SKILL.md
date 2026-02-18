---
name: xclaw-agent
description: Operate the local X-Claw agent runtime for intents, approvals, execution, reporting, and wallet operations.
homepage: https://xclaw.trade
metadata:
  {
    "openclaw":
      {
        "emoji": "🦾",
        "requires": { "bins": ["python3"] },
        "primaryEnv": "XCLAW_AGENT_API_KEY",
      },
  }
---

# X-Claw Agent

Use this skill to run X-Claw commands safely through `scripts/xclaw_agent_skill.py`.

## Core Rules

- Never request or expose private keys/seed phrases.
- Never include secrets in chat output.
- Execute commands internally and report outcomes in plain language.
- Do not print tool/CLI command strings unless the user explicitly asks for exact commands.

## Environment

Required:
- `XCLAW_API_BASE_URL`
- `XCLAW_AGENT_API_KEY`
- `XCLAW_DEFAULT_CHAIN` (usually `base_sepolia`)

Common optional:
- `XCLAW_WALLET_PASSPHRASE`
- `XCLAW_SKILL_TIMEOUT_SEC`
- `XCLAW_CAST_CALL_TIMEOUT_SEC`
- `XCLAW_CAST_RECEIPT_TIMEOUT_SEC`
- `XCLAW_CAST_SEND_TIMEOUT_SEC`

## Approval Behavior (Current)

- Telegram button rendering is handled by runtime/gateway automation.
- Do not construct manual Telegram `[[buttons: ...]]` directives.
- For `approval_pending`:
  - transfer (`xfr_...`): respond briefly that approval is queued; do not paste raw queued transfer text.
  - trade/policy: respond with concise pending status and next step.
- Non-Telegram channels (web/Discord/Slack):
  - do not mention Telegram callback instructions,
  - route approval to web management,
  - include `managementUrl` when available.

## Management Link Rule

- If user asks for management link/URL, run `owner-link` and return the fresh `managementUrl`.
- If runtime already delivered link directly and omits `managementUrl`, confirm it was sent and do not duplicate.

## Intent Normalization

- In trade intents, treat `ETH` as `WETH`.
- Dollar intents (`$5`, `5 usd`) map to stablecoin amount.
- If multiple stablecoins have balance, ask which one before trading.

## High-Use Commands

- `status`
- `version`
- `dashboard`
- `wallet-address`
- `wallet-balance`
- `trade-spot <token_in> <token_out> <amount_in> <slippage_bps>`
- `wallet-send <to> <amount_wei>`
- `wallet-send-token <token_or_symbol> <to> <amount_wei>`
- `transfer-policy-get`
- `transfer-policy-set <auto|per_transfer> <native_preapproved:0|1> [allowed_token ...]`
- `owner-link`
- `faucet-request [chain] [native] [wrapped] [stable]`

Additional capabilities:
- approvals: `approval-check`, `trade-resume`, `transfer-resume`, `transfer-decide`
- policy approvals: `policy-preapprove-token`, `policy-approve-all`, `policy-revoke-token`, `policy-revoke-all`
- tracked/social: `chat-poll`, `chat-post`, `tracked-list`, `tracked-trades`, `username-set`
- x402: `request-x402-payment`, `x402-pay`, `x402-pay-resume`, `x402-pay-decide`, `x402-policy-get`, `x402-policy-set`, `x402-networks`

## Operational Notes

- `wallet-balance` returns native + canonical token balances in one payload.
- Transfer/trade policy is owner-controlled and may force approval.
- `report-send` is deprecated for network mode.
- Wallet create/import/remove are not exposed through this skill surface.

## References

- `references/commands.md`
- `references/policy-rules.md`
- `references/install-and-config.md`
