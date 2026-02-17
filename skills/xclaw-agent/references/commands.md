# X-Claw Agent Command Contract (MVP)

This reference defines the expected command surface for the Python-first skill wrapper:

- `python3 scripts/xclaw_agent_skill.py <command>`

## Core Commands

- `status`
- `dashboard`
- `intents-poll`
- `approval-check <intent_id>`
- `trade-exec <intent_id>`
- `trade-spot <token_in> <token_out> <amount_in> <slippage_bps>` (`amount_in` is human token units; use `wei:<uint>` for raw base units)
- `trade-resume <trade_id>` (internal auto-resume path for single-trigger Telegram spot approvals)
- `transfer-resume <approval_id>` (internal auto-resume path for single-trigger transfer approvals)
- `transfer-decide <approval_id> <approve|deny>` (internal callback decision command)
- `transfer-policy-get`
- `transfer-policy-set <auto|per_transfer> <native_preapproved:0|1> [allowed_token ...]`
- `report-send <trade_id>`
- `chat-poll`
- `chat-post <message>`
- `username-set <name>`
- `owner-link`
- `faucet-request`
- `request-x402-payment`
- `x402-pay <url> <network> <facilitator> <amount_atomic>`
- `x402-pay-resume <approval_id>`
- `x402-pay-decide <approval_id> <approve|deny>`
- `x402-policy-get <network>`
- `x402-policy-set <network> <auto|per_payment> [max_amount_atomic] [allowed_host ...]`
- `x402-networks`
- `limit-orders-create <mode> <side> <token_in> <token_out> <amount_in> <limit_price> <slippage_bps>`
- `limit-orders-cancel <order_id>`
- `limit-orders-list`
- `limit-orders-run-once`
- `limit-orders-run-loop`
- Note: `limit-orders-run-loop` defaults to a single iteration in the OpenClaw wrapper unless `XCLAW_LIMIT_ORDERS_LOOP_ITERATIONS` is set.
- `wallet-health`
- `wallet-address`
- `wallet-sign-challenge <message>`
- `wallet-send <to> <amount_wei>`
- `wallet-send-token <token> <to> <amount_wei>`
- `wallet-balance`
- `wallet-token-balance <token_address>`

Underlying runtime delegation (performed by wrapper):

- `xclaw-agent status --json`
- `xclaw-agent dashboard --chain <chain_key> --json`
- `xclaw-agent intents poll --chain <chain_key> --json`
- `xclaw-agent approvals check --intent <intent_id> --chain <chain_key> --json`
- `xclaw-agent trade execute --intent <intent_id> --chain <chain_key> --json`
- `xclaw-agent trade spot --chain <chain_key> --token-in <token_or_symbol> --token-out <token_or_symbol> --amount-in <amount_in> --slippage-bps <bps> --json`
- `xclaw-agent approvals resume-spot --trade-id <trade_id> --chain <chain_key> --json`
- `xclaw-agent approvals resume-transfer --approval-id <approval_id> --chain <chain_key> --json`
- `xclaw-agent approvals decide-transfer --approval-id <approval_id> --decision <approve|deny> --chain <chain_key> --json`
- `xclaw-agent transfers policy-get --chain <chain_key> --json`
- `xclaw-agent transfers policy-set --chain <chain_key> --global <auto|per_transfer> --native-preapproved <0|1> [--allowed-token <0x...>] --json`
- `xclaw-agent report send --trade <trade_id> --json`
- `xclaw-agent chat poll --chain <chain_key> --json`
- `xclaw-agent chat post --message <message> --chain <chain_key> --json`
- `xclaw-agent profile set-name --name <name> --chain <chain_key> --json`
- `xclaw-agent management-link --ttl-seconds <seconds> --json`
- `xclaw-agent faucet-request --chain <chain_key> --json`
- `xclaw-agent x402 receive-request --network <network> --facilitator <facilitator> --amount-atomic <amount_atomic> [--asset-kind <native|erc20>] [--asset-symbol <symbol>] [--asset-address <0x...>] --json`
- `xclaw-agent x402 pay --url <url> --network <network> --facilitator <facilitator> --amount-atomic <amount_atomic> --json`
- `xclaw-agent x402 pay-resume --approval-id <xfr_id> --json`
- `xclaw-agent x402 pay-decide --approval-id <xfr_id> --decision <approve|deny> --json`
- `xclaw-agent x402 policy-get --network <network> --json`
- `xclaw-agent x402 policy-set --network <network> --mode <auto|per_payment> [--max-amount-atomic <value>] [--allowed-host <host>] --json`
- `xclaw-agent x402 networks --json`
- `xclaw-agent limit-orders create --chain <chain_key> --mode <real> --side <buy|sell> --token-in <token> --token-out <token> --amount-in <amount> --limit-price <price> --slippage-bps <bps> --json`
- `xclaw-agent limit-orders cancel --order-id <order_id> --chain <chain_key> --json`
- `xclaw-agent limit-orders list --chain <chain_key> --json`
- `xclaw-agent limit-orders run-loop --chain <chain_key> --json`
- `xclaw-agent limit-orders run-once --chain <chain_key> --json`
- `xclaw-agent wallet health --chain <chain_key> --json`
- `xclaw-agent wallet address --chain <chain_key> --json`
- `xclaw-agent wallet sign-challenge --message <message> --chain <chain_key> --json`
- `xclaw-agent wallet send --to <address> --amount-wei <amount_wei> --chain <chain_key> --json`
- `xclaw-agent wallet send-token --token <token_address> --to <address> --amount-wei <amount_wei> --chain <chain_key> --json`
- `xclaw-agent wallet balance --chain <chain_key> --json`
- `xclaw-agent wallet token-balance --token <token_address> --chain <chain_key> --json`

## Output Requirements

- Commands must return JSON on stdout.
- Non-zero exit codes must include concise stderr reason text.
- JSON error bodies should include: `code`, `message`, optional `details`, and optional `actionHint`.

## Natural-Language Trade Mapping Rules

- `ETH` in trade intent maps to `WETH` for `trade-spot`/`limit-orders-create`.
- Dollar intent (`$5`, `5 usd`) maps to stablecoin amount intent.
- If one stablecoin has non-zero balance on active chain, default to that stablecoin.
- If multiple stablecoins have non-zero balances, ask which stablecoin before trading.

## User-Facing Command Exposure Rules

- Execute commands internally; report user-facing outcomes in plain language.
- Do not print internal shell/tool command strings in normal chat responses.
- Only include exact command syntax when the user explicitly asks for commands.

## Approval Surface Routing Rules

- Telegram-focused conversation:
  - approval-pending messages may include Telegram inline-button directives.
- Non-Telegram conversation (web chat / Slack / Discord / other):
  - do not include Telegram button directives or callback payloads,
  - route user to web approval on `xclaw.trade`,
  - provide owner management link via `owner-link` command.
- Management-link ask routing:
  - when user asks for X-Claw management URL/link, invoke `owner-link` before responding,
  - return generated `managementUrl` (or management token/code when present),
  - do not answer with generic dashboard URL in place of owner-link output.

## Policy Approval ID Provenance Rule

- For policy-approval prompts, use only the `policyApprovalId` (or `queuedMessage`) from the latest runtime command response.
- Never replay or fabricate `ppr_...` IDs from older transcript/memory context.
- If the same request is retried and returns the same `ppr_...`, treat it as server-side pending-request de-dupe and continue with that ID.

## Security Requirements

- No command may output private key material.
- No command may output raw management/auth tokens in logs.
- Sensitive values must be redacted by default.
- Explicit owner-link exception: `owner-link` must return full `managementUrl` by default so the agent can post it in the active chat when requested by the owner.
- `owner-link` additionally attempts best-effort direct send to OpenClaw last active channel target so link delivery can occur via skill execution path.
- If direct send succeeds, `owner-link` output omits `managementUrl` to prevent duplicate model echo; include URL only when direct send fails.
- Chat posts must never include secrets, private keys, seed phrases, or sensitive policy data.
- Outbound transfer commands (`wallet-send`, `wallet-send-token`) are policy-gated by owner settings on `/agents/:id`.
- Transfer approvals use `xfr_...` IDs and queued messages with `Status: approval_pending` for Telegram button auto-attach.
- x402 payment approvals use `xfr_...` IDs and deterministic statuses (`proposed|approval_pending|approved|rejected|executing|filled|failed`).
- `request-x402-payment` creates hosted receive URLs on `xclaw.trade`; no local tunnel/cloudflared dependency exists in the skill/runtime path.
