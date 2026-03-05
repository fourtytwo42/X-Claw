# X-Claw Wallet Command Contract (MVP)

This document defines the canonical wallet command surface for the Python-first skill wrapper:

- `python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py <command> [args...]`

The wrapper delegates wallet operations to `xclaw-agent` and enforces JSON I/O and input validation.

## 1) Command Set

Required wallet commands:

1. `wallet-health [chain_key]`
2. `wallet-create`
3. `wallet-import`
4. `wallet-address [chain_key]`
5. `wallet-sign-challenge <message> [chain_key]`
6. `wallet-send <to> <amount_wei> [chain_key]`
7. `wallet-balance [chain_key]`
8. `wallet-token-balance <token_address> [chain_key]`
9. `wallet-send-token <token_or_symbol> <to> <amount_wei> [chain_key]`
10. `wallet-track-token <token_address> [chain_key]`
11. `wallet-untrack-token <token_address> [chain_key]`
12. `wallet-tracked-tokens [chain_key]`
13. `wallet-remove`
14. `transfer-policy-get`
15. `transfer-policy-set`
16. `transfer-resume`
17. `transfer-decide`
18. `liquidity-add`
19. `liquidity-remove`
20. `liquidity-positions`
21. `liquidity-quote-add`
22. `liquidity-quote-remove`
23. `default-chain-get`
24. `default-chain-set <chain_key>`
25. `wallet-wrap-native <amount> [chain_key]`

Notes:
- explicit `--chain` remains authoritative for chain-scoped commands.
- chain inference for omitted chain uses runtime/web-synced default chain (`state.json.defaultChain`) first, then `XCLAW_DEFAULT_CHAIN` env fallback.
- `wallet-send` uses base-unit amount for deterministic automation.
- Supported chain keys for this contract are config-driven enabled chains (`config/chains/*.json` where `enabled=true` and `family in {evm, solana}`). Current visible examples include EVM chains plus `solana_localnet`, `solana_devnet`, `solana_testnet`, and `solana_mainnet_beta`.

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
- `xclaw-agent wallet track-token --token <token_address> --chain <chain_key> --json`
- `xclaw-agent wallet untrack-token --token <token_address> --chain <chain_key> --json`
- `xclaw-agent wallet tracked-tokens --chain <chain_key> --json`
- `xclaw-agent wallet wrap-native --amount <amount> --chain <chain_key> --json`
- `xclaw-agent wallet remove --chain <chain_key> --json`
- `xclaw-agent transfers policy-get --chain <chain_key> --json`
- `xclaw-agent transfers policy-set --chain <chain_key> --global <auto|per_transfer> --native-preapproved <0|1> [--allowed-token <0x...>] --json`
- `xclaw-agent approvals resume-transfer --approval-id <xfr_id> --chain <chain_key> --json`
- `xclaw-agent approvals decide-transfer --approval-id <xfr_id> --decision <approve|deny> --chain <chain_key> --json`
- `xclaw-agent liquidity add --chain <chain_key> --dex <dex> --token-a <token_or_symbol> --token-b <token_or_symbol> --amount-a <amount_a> --amount-b <amount_b> [--position-type <v2|v3>] [--v3-range <range>] [--slippage-bps <bps>] --json`
- `xclaw-agent liquidity remove --chain <chain_key> --dex <dex> --position-id <position_id> [--percent <1-100>] [--slippage-bps <bps>] [--position-type <v2|v3>] --json`
- `xclaw-agent liquidity positions --chain <chain_key> [--dex <dex>] [--status <status>] --json`
- `xclaw-agent liquidity quote-add --chain <chain_key> --dex <dex> --token-a <token_or_symbol> --token-b <token_or_symbol> --amount-a <amount_a> --amount-b <amount_b> [--position-type <v2|v3>] [--slippage-bps <bps>] --json`
- `xclaw-agent liquidity quote-remove --chain <chain_key> --dex <dex> --position-id <position_id> [--percent <1-100>] [--position-type <v2|v3>] --json`
- `xclaw-agent liquidity discover-pairs --chain <chain_key> --dex <dex> [--min-reserve <base_units>] [--limit <1-100>] [--scan-max <1-2000>] --json`
- `xclaw-agent liquidity execute --intent <liquidity_intent_id> --chain <chain_key> --json`
- `xclaw-agent liquidity resume --intent <liquidity_intent_id> --chain <chain_key> --json`
- `xclaw-agent approvals decide-liquidity --intent-id <liquidity_intent_id> --decision <approve|reject> --chain <chain_key> [--source <web|telegram|runtime>] [--reason-message <text>] --json`
- `xclaw-agent auth recover --chain <chain_key> --json`
- `xclaw-agent default-chain get --json`
- `xclaw-agent default-chain set --chain <chain_key> --json`

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

1. `wallet-send` validates recipient address format by chain family before delegation (`0x...` for EVM, base58 for Solana).
2. `wallet-send` validates amount is non-negative integer string.
3. `wallet-send-token` accepts canonical token symbol, tracked token symbol (when unique), or chain-valid token identifier (`0x` token address on EVM, mint address on Solana) before execution.
4. `wallet-track-token` and `wallet-untrack-token` require chain-valid token identifiers for the selected chain.
5. `wallet-send-token` returns deterministic `token_symbol_ambiguous` when a tracked symbol maps to multiple token addresses.
6. `wallet-token-balance` validates token address format by chain family before delegation.
7. `wallet-sign-challenge` rejects empty message.
6. `wallet-create` and `wallet-import` support non-interactive automation when required env vars are provided:
- `wallet-create`: requires `XCLAW_WALLET_PASSPHRASE`
- `wallet-import`: requires both `XCLAW_WALLET_IMPORT_PRIVATE_KEY` and `XCLAW_WALLET_PASSPHRASE`
  Without these env vars, non-interactive calls fail with `non_interactive`.
8. `wallet-send` fails closed when spend policy file is missing, invalid, or unsafe (`~/.xclaw-agent/policy.json`).
9. `wallet-send` enforces policy preconditions:
- local policy: `paused`, `chains.<chain>.chain_enabled`, approval gate, `max_daily_native_wei`
- owner policy: `chainEnabled == true` (from `GET /api/v1/agent/transfers/policy?chainKey=...`).
10. `wallet-wrap-native` requires a positive amount and chain config with wrapped-native target resolution; it fails deterministically with `invalid_amount`, `wrapped_native_helper_missing`, `wrapped_native_token_missing`, or `wrap_native_failed` when runtime preconditions are not met.
11. `wallet-send` / `wallet-send-token` fail closed with `approval_sync_failed` when a required transfer approval cannot be mirrored to management inbox.
12. Runtime transfer approval mirror endpoint (`POST /api/v1/agent/transfer-approvals/mirror`) may return deterministic `transfer_mirror_unavailable` when mirror schema/storage is unavailable; runtime must keep transfer send fail-closed and must not emit queued approval success text in this case.

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
   - token holdings in `tokens[]` include only non-zero balances (canonical + tracked + discovered),
   - token query/discovery failures in `tokenErrors[]` without failing native balance fetch.
9. `wallet-token-balance` is chain-family aware:
   - EVM path uses cast-backed ERC-20 `balanceOf(address)` query.
   - Solana path resolves balances from runtime Solana holdings payload.
10. `wallet-wrap-native` is implemented as config-driven cross-chain behavior:
   - if `coreContracts.wrappedNativeHelper` exists and is valid, runtime calls payable `deposit()` on helper contract.
   - otherwise runtime resolves canonical wrapped-native token from `canonicalTokens` via native-symbol mapping (`W<NativeSymbol>` + strict aliases) and calls payable `deposit()` on that token contract.
   - runtime verifies receipt and reports `txHash`, wrapped token address, wrapped balance delta, and helper address only when helper path is used.
11. Missing cast dependency returns structured `missing_dependency` error.
12. Wrapper-level input validation executes before runtime delegation.
13. On delegated non-zero exits, wrapper passes runtime JSON through unchanged when stdout is parseable JSON payload with `ok` and `code`; otherwise wrapper emits structured `agent_command_failed`.
14. Wrapper API command env gate accepts either:
   - `XCLAW_AGENT_API_KEY` in environment, or
   - previously recovered runtime auth stored in `~/.xclaw-agent/state.json`.
15. Runtime auth recovery command:
   - `auth recover` performs challenge/sign/recover with local wallet keys and persists recovered key to runtime state.
16. Runtime transaction fee planning for wallet/trade sends is EIP-1559-first by default:
   - default mode (`XCLAW_TX_FEE_MODE=rpc`) derives EIP-1559 fee caps from chain RPC (`eth_feeHistory`, `eth_maxPriorityFeePerGas`, reward fallback),
   - retry attempts apply bounded fee escalation via `XCLAW_TX_RETRY_BUMP_BPS` (default `1250`),
   - minimum priority floor is `XCLAW_TX_PRIORITY_FLOOR_GWEI` (default `1`),
   - when EIP-1559 RPC methods are unavailable/invalid, runtime falls back to `eth_gasPrice`,
   - rollback kill-switch `XCLAW_TX_FEE_MODE=legacy` restores legacy fixed `gasPrice` sender behavior.
17. Liquidity commands enforce adapter preflight before API proposal submission:
   - unsupported chain/dex/position combinations fail with `unsupported_liquidity_adapter`,
   - `liquidity execute/resume` supports router-adapter EVM families and rejects unsupported execution families with `unsupported_liquidity_execution_family`,
   - non-actionable statuses fail with `liquidity_not_actionable`,
   - v2 add execution emits deterministic preflight reject reasons (`liquidity_preflight_*`) before submit,
   - v2 remove accepts pair-address `positionRef` fallback when snapshot rows are unavailable,
   - runtime execution/verification failures return deterministic `liquidity_execution_failed` / `liquidity_verification_failed`.
18. Hosted installer (`/skill-install.sh`) wallet bootstrap behavior:
   - creates/binds wallet on `XCLAW_DEFAULT_CHAIN`,
   - auto-attempts wallet bind for every enabled chain with `capabilities.wallet=true` using the same portable wallet key,
   - continues on per-chain bind failures with deterministic warning output and registers available wallet bindings,
   - upserts register payload with deduplicated wallet rows for all successfully bound wallet-capable chains when auth context exists.
19. Wrapper `username-set` / `agent-register` delegates now submit register payload wallet rows for all enabled local wallet bindings (primary requested chain first) so server wallet rows stay chain-complete.

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
- Faucet failures must preserve deterministic server codes in runtime output (`faucet_config_invalid`, `faucet_native_insufficient`, `faucet_wrapped_insufficient`, `faucet_wrapped_autowrap_failed`, `faucet_stable_insufficient`, `faucet_send_preflight_failed`, `faucet_rpc_unavailable`, `faucet_recipient_not_eligible`) with `requestId` passthrough for diagnostics.
- Successful faucet responses include recipient provenance fields (`recipientAddress`, `faucetAddress`) for immediate verification.

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

10. `liquidity-add` / `liquidity-remove` (approval path)
- when proposal returns `status=approval_pending`, runtime returns `code=approval_required` with `details.liquidityIntentId`, `details.status`, and `details.queuedMessage`.
- when active channel is Telegram, runtime best-effort sends a direct inline approval prompt using callback ids:
  - approve: `xliq|a|<liquidityIntentId>|<chainKey>`
  - deny: `xliq|r|<liquidityIntentId>|<chainKey>`

## 11) x402 Runtime/Skill Command Extensions (Slice 79)

The following x402 commands are part of the same Python-first wrapper contract and are relied on by automated agents:

1. `request-x402-payment [resource_description]`
- delegates to runtime `xclaw-agent x402 receive-request --network <key> --facilitator <key> --amount-atomic <value> [--asset-kind <native|token>] [--asset-symbol <symbol>] [--asset-address <token-address>] [--resource-description <text>] --json` (`erc20` input alias accepted for compatibility).
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
