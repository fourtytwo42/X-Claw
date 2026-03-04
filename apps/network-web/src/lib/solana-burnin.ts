import { dbQuery } from '@/lib/db';

export type BurninStatus = 'burnin_ready' | 'burnin_hold' | 'burnin_blocked';

type BurninMetrics = {
  transfer: { filled: number; failed: number };
  x402: { filled: number; failed: number; proofInvalid: number };
  limitOrders: { triggered: number; filled: number; failed: number };
  advancedLiquidity: { filled: number; failed: number; failedNonDeterministic: number };
  deposits: { syncTotal: number; syncDegraded: number };
};

export type SolanaBurninSnapshot = {
  chainKey: string;
  family: 'solana';
  generatedAt: string;
  windows: {
    phaseAHours: number;
    phaseBCHours: number;
    phaseDHours: number;
  };
  metrics: BurninMetrics;
  gates: {
    phaseA: {
      status: BurninStatus;
      degradedRate: number | null;
      threshold: '<0.05';
      reason: string | null;
    };
    phaseBC: {
      status: BurninStatus;
      x402FailureRate: number | null;
      x402Threshold: '<0.01';
      limitFailureRate: number | null;
      limitThreshold: '<0.05';
      proofInvalidCount: number;
      reason: string | null;
    };
    phaseD: {
      status: BurninStatus;
      advancedLiquidityFailureRate: number | null;
      threshold: '<0.08';
      reason: string | null;
    };
    overall: BurninStatus;
  };
  rollback: {
    configKillSwitch: 'capability_false';
    noDbRollbackRequired: true;
    toggles: {
      deposits: string;
      limitOrders: string;
      x402: string;
      advancedLiquidity: string;
    };
  };
};

function toInt(value: string | number | null | undefined): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? Math.max(0, Math.trunc(parsed)) : 0;
}

function rate(numerator: number, denominator: number): number | null {
  if (denominator <= 0) {
    return null;
  }
  return numerator / denominator;
}

function composeOverall(phases: Array<BurninStatus>): BurninStatus {
  if (phases.some((value) => value === 'burnin_blocked')) {
    return 'burnin_blocked';
  }
  if (phases.some((value) => value === 'burnin_hold')) {
    return 'burnin_hold';
  }
  return 'burnin_ready';
}

export async function getSolanaBurninSnapshot(agentId: string, chainKey: string): Promise<SolanaBurninSnapshot | null> {
  if (chainKey !== 'solana_mainnet_beta') {
    return null;
  }

  const phaseAHours = 48;
  const phaseBCHours = 72;
  const phaseDHours = 72;

  const [
    transferRows,
    x402Rows,
    limitRows,
    liquidityRows,
    depositRows,
  ] = await Promise.all([
    dbQuery<{ filled: string; failed: string }>(
      `
      select
        count(*) filter (where status = 'filled')::text as filled,
        count(*) filter (where status = 'failed')::text as failed
      from agent_transfer_approval_mirror
      where agent_id = $1
        and chain_key = $2
        and approval_source = 'transfer'
        and terminal_at >= now() - ($3::int * interval '1 hour')
      `,
      [agentId, chainKey, phaseBCHours]
    ),
    dbQuery<{ filled: string; failed: string; proof_invalid: string }>(
      `
      select
        count(*) filter (where status = 'filled')::text as filled,
        count(*) filter (where status = 'failed')::text as failed,
        count(*) filter (where reason_code = 'x402_settlement_proof_invalid')::text as proof_invalid
      from agent_x402_payment_mirror
      where agent_id = $1
        and network_key = $2
        and coalesce(terminal_at, updated_at, created_at) >= now() - ($3::int * interval '1 hour')
      `,
      [agentId, chainKey, phaseBCHours]
    ),
    dbQuery<{ triggered: string; filled: string; failed: string }>(
      `
      select
        count(*) filter (where status = 'triggered')::text as triggered,
        count(*) filter (where status = 'filled')::text as filled,
        count(*) filter (where status = 'failed')::text as failed
      from limit_orders
      where agent_id = $1
        and chain_key = $2
        and coalesce(updated_at, created_at) >= now() - ($3::int * interval '1 hour')
      `,
      [agentId, chainKey, phaseBCHours]
    ),
    dbQuery<{ filled: string; failed: string; failed_nondeterministic: string }>(
      `
      select
        count(*) filter (where status = 'filled')::text as filled,
        count(*) filter (where status = 'failed')::text as failed,
        count(*) filter (
          where status = 'failed'
            and coalesce(reason_code, '') <> ''
            and coalesce(reason_code, '') not in (
              'invalid_input',
              'unsupported_liquidity_operation',
              'claim_rewards_not_configured',
              'migration_target_not_configured',
              'pool_not_found',
              'unsupported_liquidity_execution_family',
              'unsupported_execution_adapter',
              'unsupported_chain_capability'
            )
        )::text as failed_nondeterministic
      from liquidity_intents
      where agent_id = $1
        and chain_key = $2
        and coalesce(details->>'liquidityOperation', '') in ('increase', 'claim_fees', 'claim_rewards', 'migrate')
        and updated_at >= now() - ($3::int * interval '1 hour')
      `,
      [agentId, chainKey, phaseDHours]
    ),
    dbQuery<{ sync_total: string; sync_degraded: string }>(
      `
      select
        count(*)::text as sync_total,
        count(*) filter (where coalesce(private_payload->>'syncStatus', '') = 'degraded')::text as sync_degraded
      from management_audit_log
      where agent_id = $1
        and action_type = 'deposit.sync'
        and coalesce(private_payload->>'chainKey', '') = $2
        and created_at >= now() - ($3::int * interval '1 hour')
      `,
      [agentId, chainKey, phaseAHours]
    ),
  ]);

  const transfer = {
    filled: toInt(transferRows.rows[0]?.filled),
    failed: toInt(transferRows.rows[0]?.failed),
  };
  const x402 = {
    filled: toInt(x402Rows.rows[0]?.filled),
    failed: toInt(x402Rows.rows[0]?.failed),
    proofInvalid: toInt(x402Rows.rows[0]?.proof_invalid),
  };
  const limitOrders = {
    triggered: toInt(limitRows.rows[0]?.triggered),
    filled: toInt(limitRows.rows[0]?.filled),
    failed: toInt(limitRows.rows[0]?.failed),
  };
  const advancedLiquidity = {
    filled: toInt(liquidityRows.rows[0]?.filled),
    failed: toInt(liquidityRows.rows[0]?.failed),
    failedNonDeterministic: toInt(liquidityRows.rows[0]?.failed_nondeterministic),
  };
  const deposits = {
    syncTotal: toInt(depositRows.rows[0]?.sync_total),
    syncDegraded: toInt(depositRows.rows[0]?.sync_degraded),
  };

  const depositRate = rate(deposits.syncDegraded, deposits.syncTotal);
  const x402FailureRate = rate(x402.failed, x402.filled + x402.failed);
  const limitFailureRate = rate(limitOrders.failed, limitOrders.filled + limitOrders.failed);
  const advancedFailureRate = rate(
    advancedLiquidity.failedNonDeterministic,
    advancedLiquidity.filled + advancedLiquidity.failedNonDeterministic
  );

  const phaseAStatus: { status: BurninStatus; reason: string | null } =
    deposits.syncTotal <= 0
      ? { status: 'burnin_hold', reason: 'No deposit sync observations in the 48h window.' }
      : depositRate !== null && depositRate < 0.05
        ? { status: 'burnin_ready', reason: null }
        : { status: 'burnin_blocked', reason: 'Deposit degraded rate is above threshold.' };

  const phaseBCStatus: { status: BurninStatus; reason: string | null } =
    x402.filled + x402.failed + limitOrders.filled + limitOrders.failed <= 0
      ? { status: 'burnin_hold', reason: 'No x402/limit-order terminal activity in the 72h window.' }
      : x402.proofInvalid > 0
        ? { status: 'burnin_blocked', reason: 'x402 settlement proof verification failures detected.' }
        : x402FailureRate !== null && x402FailureRate >= 0.01
          ? { status: 'burnin_blocked', reason: 'x402 failed ratio is above threshold.' }
          : limitFailureRate !== null && limitFailureRate >= 0.05
            ? { status: 'burnin_blocked', reason: 'Limit-order failed ratio is above threshold.' }
            : { status: 'burnin_ready', reason: null };

  const phaseDStatus: { status: BurninStatus; reason: string | null } =
    advancedLiquidity.filled + advancedLiquidity.failedNonDeterministic <= 0
      ? { status: 'burnin_hold', reason: 'No advanced-liquidity terminal activity in the 72h window.' }
      : advancedFailureRate !== null && advancedFailureRate < 0.08
        ? { status: 'burnin_ready', reason: null }
        : { status: 'burnin_blocked', reason: 'Advanced-liquidity failed ratio is above threshold.' };

  return {
    chainKey,
    family: 'solana',
    generatedAt: new Date().toISOString(),
    windows: {
      phaseAHours,
      phaseBCHours,
      phaseDHours,
    },
    metrics: {
      transfer,
      x402,
      limitOrders,
      advancedLiquidity,
      deposits,
    },
    gates: {
      phaseA: {
        status: phaseAStatus.status,
        degradedRate: depositRate,
        threshold: '<0.05',
        reason: phaseAStatus.reason,
      },
      phaseBC: {
        status: phaseBCStatus.status,
        x402FailureRate,
        x402Threshold: '<0.01',
        limitFailureRate,
        limitThreshold: '<0.05',
        proofInvalidCount: x402.proofInvalid,
        reason: phaseBCStatus.reason,
      },
      phaseD: {
        status: phaseDStatus.status,
        advancedLiquidityFailureRate: advancedFailureRate,
        threshold: '<0.08',
        reason: phaseDStatus.reason,
      },
      overall: composeOverall([phaseAStatus.status, phaseBCStatus.status, phaseDStatus.status]),
    },
    rollback: {
      configKillSwitch: 'capability_false',
      noDbRollbackRequired: true,
      toggles: {
        deposits: 'config/chains/solana_mainnet_beta.json -> capabilities.deposits=false',
        limitOrders: 'config/chains/solana_mainnet_beta.json -> capabilities.limitOrders=false',
        x402: 'config/chains/solana_mainnet_beta.json + config/x402/networks.json -> enabled=false',
        advancedLiquidity:
          'config/chains/solana_mainnet_beta.json -> execution.liquidity.adapters.raydium_clmm.capabilities.{increase,claimFees,claimRewards,migrate}=false',
      },
    },
  };
}
