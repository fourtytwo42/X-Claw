# X-Claw Wallet Command Contract (MVP)

This document defines the canonical wallet command surface for the Python-first skill wrapper:

- `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py <command> [args...]`

The wrapper delegates wallet operations to `xclaw-agent` and enforces JSON I/O and input validation.

## 1) Command Set

Required wallet commands:

1. `wallet-health`
2. `wallet-create`
3. `wallet-import`
4. `wallet-address`
5. `wallet-sign-challenge <message>`
6. `wallet-send <to> <amount_wei>`
7. `wallet-balance`
8. `wallet-token-balance <token_address>`
9. `wallet-send-token <token_or_symbol> <to> <amount_wei>`
10. `wallet-remove`
11. `transfer-policy-get`
12. `transfer-policy-set`
13. `transfer-resume`
14. `transfer-decide`

Notes:
- `chain` is sourced from `XCLAW_DEFAULT_CHAIN`.
- `wallet-send` uses base-unit amount for deterministic automation.
- Supported chain keys for this contract include `base_sepolia`, `kite_ai_testnet`, and `hardhat_local` (where configured).

## 2) Delegated Runtime Commands

Wrapper delegation target commands:

- `xclaw-agent wallet health --chain <chain_key> --json`
- `xclaw-agent wallet create --chain <chain_key> --json`
- `xclaw-agent wallet import --chain <chain_key> --json`
- `xclaw-agent wallet address --chain <chain_key> --json`
- `xclaw-agent wallet sign-challenge --message <message> --chain <chain_key> --json`
- `xclaw-agent wallet send --to <address> --amount-wei <amount_wei> --chain <chain_key> --json`
- `xclaw-agent wallet send-token --token <token_or_symbol> --to <address> --amount-wei <amount_wei> --chain <chain_key> --json`
- `xclaw-agent wallet balance --chain <chain_key> --json`
- `xclaw-agent wallet token-balance --token <token_address> --chain <chain_key> --json`
- `xclaw-agent wallet remove --chain <chain_key> --json`
- `xclaw-agent transfers policy-get --chain <chain_key> --json`
- `xclaw-agent transfers policy-set --chain <chain_key> --global <auto|per_transfer> --native-preapproved <0|1> [--allowed-token <0x...>] --json`
- `xclaw-agent approvals resume-transfer --approval-id <xfr_id> --chain <chain_key> --json`
- `xclaw-agent approvals decide-transfer --approval-id <xfr_id> --decision <approve|deny> --chain <chain_key> --json`

Wrapper binary resolution order:
1. PATH lookup (`shutil.which("xclaw-agent")`)
2. Repo-local fallback (`apps/agent-runtime/bin/xclaw-agent`)
3. Structured `missing_binary` error with exit code `127`

## 3) JSON Success Shape

Commands MUST return JSON on stdout.

Minimum shape:

```json
{
  "ok": true,
  "code": "ok",
  "message": "..."
}
```

Runtime-specific fields may be appended (for example `address`, `txHash`, `balanceWei`, `signature`).

## 4) JSON Error Shape

Errors MUST be machine-parseable and human-readable:

```json
{
  "ok": false,
  "code": "...",
  "message": "...",
  "actionHint": "...",
  "details": {}
}
```

`actionHint` and `details` are optional but recommended.

## 5) Validation Rules

1. `wallet-send` validates recipient address format before delegation.
2. `wallet-send` validates amount is non-negative integer string.
3. `wallet-send-token` accepts canonical token symbol (for example `USDC`) or `0x` token address and resolves to canonical token address before execution.
4. `wallet-token-balance` validates token address format before delegation.
5. `wallet-sign-challenge` rejects empty message.
6. `wallet-create` and `wallet-import` support non-interactive automation when required env vars are provided:
- `wallet-create`: requires `XCLAW_WALLET_PASSPHRASE`
- `wallet-import`: requires both `XCLAW_WALLET_IMPORT_PRIVATE_KEY` and `XCLAW_WALLET_PASSPHRASE`
  Without these env vars, non-interactive calls fail with `non_interactive`.
7. `wallet-send` fails closed when spend policy file is missing, invalid, or unsafe (`~/.xclaw-agent/policy.json`).
8. `wallet-send` enforces policy preconditions:
- local policy: `paused`, `chains.<chain>.chain_enabled`, approval gate, `max_daily_native_wei`
- owner policy: `chainEnabled == true` (from `GET /api/v1/agent/transfers/policy?chainKey=...`).

## 6) Canonical Challenge Format (`wallet-sign-challenge`)

`wallet-sign-challenge` requires line-based `key=value` message with exactly:

1. `domain`
2. `chain`
3. `nonce`
4. `timestamp`
5. `action`

Validation rules:
- `domain` allowlist: `xclaw.trade`, `staging.xclaw.trade`, `localhost`, `127.0.0.1`, `::1`
- `chain` must match command `--chain`
- `nonce` regex: `[A-Za-z0-9_-]{16,128}`
- `timestamp` must be ISO-8601 UTC (`Z` or `+00:00`) and within 5 minutes
- `action` must be non-empty

Success payload fields for signing include:
- `signature` (65-byte hex, `0x`-prefixed)
- `scheme: "eip191_personal_sign"`
- `challengeFormat: "xclaw-auth-v1"`
- `address`
- `chain`

## 7) Runtime-Behavior Alignment (Slice 06)

Current behavior in `apps/agent-runtime/xclaw_agent/cli.py`:

1. `wallet-create` is implemented with encrypted-at-rest storage and supports:
   - interactive TTY passphrase prompt, or
   - non-interactive `XCLAW_WALLET_PASSPHRASE`.
2. `wallet-import` is implemented with encrypted-at-rest storage and supports:
   - interactive TTY private-key + passphrase prompts, or
   - non-interactive `XCLAW_WALLET_IMPORT_PRIVATE_KEY` + `XCLAW_WALLET_PASSPHRASE`.
3. `wallet-address` returns active chain-bound address or `wallet_missing`.
4. `wallet-health` reports live runtime state (`hasCast`, `hasWallet`, `address`, `metadataValid`, `filePermissionsSafe`, `integrityChecked`, `timestamp`) and includes `nextAction` + `actionHint` guidance even on ok responses. It fails closed on unsafe permissions/invalid wallet metadata.
5. `wallet-sign-challenge` is implemented with canonical challenge validation and cast-backed EIP-191 signing.
6. Non-interactive signing requires `XCLAW_WALLET_PASSPHRASE`; otherwise interactive TTY prompt is used.
7. `wallet-send` is implemented with fail-closed policy precondition checks from `~/.xclaw-agent/policy.json` before any chain spend:
   - `paused == false`
   - `chains.<chain>.chain_enabled == true`
   - owner chain access enabled: `chainEnabled == true` from `GET /api/v1/agent/transfers/policy?chainKey=...`
   - if `spend.approval_required == true`, then `spend.approval_granted == true`
   - `spend.max_daily_native_wei` not exceeded (UTC day ledger in `state.json`)
8. Slice 72 policy-override behavior:
   - outbound policy blocks (`outbound disabled` or `destination not whitelisted`) route to transfer approval flow (`xfr_...`) instead of immediate hard-fail,
   - approve executes one-off override for that transfer (`executionMode=policy_override`) without mutating outbound policy,
   - deny marks transfer `rejected`,
   - `chain_disabled` remains hard block.
8. `wallet-balance` returns combined holdings for wallet address and chain RPC:
   - native balance fields (`balanceWei`, `balanceEth`, `symbol`, `decimals`),
   - canonical token balances in `tokens[]` (best effort per configured chain canonical tokens),
   - token query failures in `tokenErrors[]` without failing native balance fetch.
9. `wallet-token-balance` is implemented via cast-backed ERC-20 `balanceOf(address)` query.
10. Missing cast dependency returns structured `missing_dependency` error.
11. Wrapper-level input validation executes before runtime delegation.
12. On delegated non-zero exits, wrapper passes runtime JSON through unchanged when stdout is parseable JSON payload with `ok` and `code`; otherwise wrapper emits structured `agent_command_failed`.

This is contract-compliant for Slice 06 because spend/balance command handlers are implemented and guarded by policy preconditions.

## 8) Security Rules

1. Never print private keys, mnemonics, or raw secret material.
2. No persistent plaintext password stash in production runtime.
3. No persistent plaintext private-key files in production runtime.
4. Wallet signing is local-only; server receives signatures/tx metadata, never key material.
5. All sensitive values in logs/output must be redacted.

## 9) Exit Codes

- `0`: success
- `1`: runtime command failure
- `2`: usage or required environment missing
- `124`: wrapper timeout exceeded (structured JSON `code=timeout`)
- `127`: missing runtime binary (`xclaw-agent`)

## 10) Operational Command Output Extensions (Slice 26)

The following non-wallet commands are part of the same Python-first wrapper contract and are relied on by automated agents:

1. `status`
- includes `agentName` best-effort when resolvable.
- may include `identityWarnings` when profile lookup is unavailable; this must not fail the command.

2. `faucet-request` (error path)
- when API returns rate-limit details, runtime surfaces `retryAfterSec` for machine schedulability.
- supports chain-aware selectable assets via `--asset native|wrapped|stable` and returns resolved `requestedAssets`/`fulfilledAssets`.

3. `faucet-networks`
- returns supported faucet chains and per-chain asset capability metadata for agent-side tool routing.

4. `chains`
- returns enabled chain registry metadata and capability map for runtime/skill routing.
- accepts optional `--include-disabled` for diagnostics.

5. `limit-orders-run-loop`
- emits exactly one JSON object per invocation (no multiple JSON lines).
- in JSON mode, `--iterations 0` is rejected with `code=invalid_input`.

6. `trade-spot`
- retains exact gas wei values (`...GasCostWei`) and includes:
  - `totalGasCostEthExact` (numeric string),
  - `totalGasCostEthPretty` (display string),
  - `totalGasCostEth` (compat alias of exact).

7. `trade-resume`
- internal orchestration command used for single-trigger Telegram spot approvals.
- delegates to runtime `approvals resume-spot --trade-id <id> --chain <key> --json`.
- returns JSON with `tradeId`, `chain`, `status`, and execution fields (for example `txHash`) when available.

8. `transfer-resume`
- internal orchestration command used for single-trigger transfer approvals.
- delegates to runtime `approvals resume-transfer --approval-id <xfr_id> --chain <key> --json`.
- returns JSON with terminal transfer fields (`status`, `approvalId`, `txHash` when available).

9. `transfer-decide`
- internal orchestration command used by Telegram/web callback flows.
- delegates to runtime `approvals decide-transfer --approval-id <xfr_id> --decision <approve|deny> --chain <key> --json`.
- `approve` path continues execution; `deny` path marks transfer `rejected`.

## 11) x402 Runtime/Skill Command Extensions (Slice 79)

The following x402 commands are part of the same Python-first wrapper contract and are relied on by automated agents:

1. `request-x402-payment [resource_description]`
- delegates to runtime `xclaw-agent x402 receive-request --network <key> --facilitator <key> --amount-atomic <value> [--asset-kind <native|erc20>] [--asset-symbol <symbol>] [--asset-address <0x...>] [--resource-description <text>] --json`.
- creates hosted receive URL records on website endpoint `/api/v1/agent/x402/inbound/proposed`.
- returns `paymentId`, `paymentUrl`, `network`, `facilitator`, `assetKind`, `assetSymbol`, `amountAtomic`, optional `resourceDescription`, `status`.

2. `x402-pay <url> <network> <facilitator> <amount_atomic>`
- delegates to runtime `xclaw-agent x402 pay --url <url> --network <key> --facilitator <key> --amount-atomic <value> --json`.
- if policy mode is `per_payment`, returns queued approval with `approvalId: xfr_...` and `status: approval_pending`.
- if policy mode is `auto`, executes immediately and returns terminal status.
- runtime mirrors x402 outbound lifecycle to server read model (`/agent/x402/outbound/mirror`) and transfer-approval mirror (`approvalSource: x402`).

3. `x402-pay-resume <approval_id>`
- delegates to runtime `xclaw-agent x402 pay-resume --approval-id <xfr_id> --json`.
- resumes execution for approved x402 payment approvals.

4. `x402-pay-decide <approval_id> <approve|deny>`
- delegates to runtime `xclaw-agent x402 pay-decide --approval-id <xfr_id> --decision <approve|deny> --json`.
- `approve` continues execution; `deny` transitions to terminal `rejected`.

5. `x402-policy-get <network>`
- delegates to runtime `xclaw-agent x402 policy-get --network <key> --json`.
- returns local policy (`payApprovalMode`, `maxAmountAtomic`, `allowedHosts`).

6. `x402-policy-set <network> <auto|per_payment> [max_amount_atomic] [allowed_host ...]`
- delegates to runtime `xclaw-agent x402 policy-set --network <key> --mode <auto|per_payment> ... --json`.
- persists local x402 policy state.

7. `x402-networks`
- delegates to runtime `xclaw-agent x402 networks --json`.
- returns configured x402 network/facilitator map and enabled/disabled flags.

## 12) Tracked-Agent Runtime/Skill Extensions (Slice 82)

The following tracked-agent commands are part of the Python-first wrapper contract and are used by OpenClaw agent operations:

1. `dashboard`
- includes `trackedAgents` and `trackedRecentTrades` in output when API/auth context is available.
- tracked recent trades default to `filled` only and latest-first (`limit=20`).

2. `tracked-list`
- delegates to runtime `xclaw-agent tracked list --chain <chain_key> --json`.
- reads `GET /api/v1/agent/tracked-agents?chainKey=...`.
- returns canonical tracked list for the authenticated agent.

3. `tracked-trades [tracked_agent_id] [limit]`
- delegates to runtime `xclaw-agent tracked trades --chain <chain_key> [--agent <tracked_agent_id>] [--limit <1-100>] --json`.
- reads `GET /api/v1/agent/tracked-trades?chainKey=...&limit=...&trackedAgentId=...`.
- default behavior: `filled` trades only, newest first, `limit=20`.

4. Product semantics:
- tracked agents are idea-flow inputs only.
- no automatic copy execution is implied by tracked-agent commands.
