# Slice 228 Spec: Explicit Adapters for Wallet and Limit-Orders (2026-03-08)

Issue mapping: `#81`

## Goal
1. Replace dynamic runtime binding for wallet and limit-order command modules with explicit typed adapters.
2. Preserve all current CLI verbs, flags, JSON response shapes, exit codes, and custody/auth boundaries.
3. Keep `cli.py` as router + adapter factory for wallet and limit-order entrypoints.

## Non-goals
1. No API route/schema/database changes.
2. No runtime behavior redesign for wallet or limit-order execution engines.
3. No approvals/trade/liquidity/x402 behavior changes in this slice beyond compatibility wiring already introduced.

## Locked scope
1. `apps/agent-runtime/xclaw_agent/cli.py`
2. `apps/agent-runtime/xclaw_agent/commands/wallet.py`
3. `apps/agent-runtime/xclaw_agent/commands/limit_orders.py`
4. `apps/agent-runtime/xclaw_agent/runtime/adapters/wallet.py`
5. `apps/agent-runtime/xclaw_agent/runtime/adapters/limit_orders.py`
6. `apps/agent-runtime/tests/test_runtime_adapters.py`
7. `apps/agent-runtime/tests/test_wallet_core.py`
8. `apps/agent-runtime/tests/test_trade_path.py`
9. `docs/XCLAW_SOURCE_OF_TRUTH.md`
10. `docs/XCLAW_SLICE_TRACKER.md`
11. `docs/XCLAW_BUILD_ROADMAP.md`
12. `docs/CONTEXT_PACK.md`
13. `spec.md`
14. `tasks.md`
15. `acceptance.md`
