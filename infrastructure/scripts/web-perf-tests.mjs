#!/usr/bin/env node

const BASE_URL = (process.env.XCLAW_E2E_BASE_URL || 'http://127.0.0.1:3000').replace(/\/$/, '');
const ITERATIONS = Number.parseInt(process.env.XCLAW_PERF_ITERATIONS || '5', 10);
const WARMUP = Number.parseInt(process.env.XCLAW_PERF_WARMUP || '1', 10);
const REQUEST_TIMEOUT_MS = Number.parseInt(process.env.XCLAW_PERF_TIMEOUT_MS || '10000', 10);
const WARN_P95_MS = Number.parseInt(process.env.XCLAW_PERF_WARN_P95_MS || '1200', 10);
const FAIL_P95_MS = Number.parseInt(process.env.XCLAW_PERF_FAIL_P95_MS || '0', 10);

const AGENT_ID = process.env.XCLAW_E2E_AGENT_ID || 'ag_slice7';
const CHAIN_KEY = process.env.XCLAW_E2E_CHAIN_KEY || 'base_sepolia';

const ROUTES = [
  { name: 'page_landing', path: '/', type: 'page', expectedStatuses: [200] },
  { name: 'page_dashboard', path: '/dashboard', type: 'page', expectedStatuses: [200] },
  { name: 'page_explore', path: '/explore', type: 'page', expectedStatuses: [200] },
  { name: 'page_agents', path: '/agents', type: 'page', expectedStatuses: [200] },
  { name: 'page_status', path: '/status', type: 'page', expectedStatuses: [200] },
  { name: 'page_room', path: '/room', type: 'page', expectedStatuses: [200] },
  { name: 'page_agent_profile', path: `/agents/${encodeURIComponent(AGENT_ID)}`, type: 'page', expectedStatuses: [200, 404] },
  { name: 'api_health', path: '/api/health', type: 'api', expectedStatuses: [200] },
  { name: 'api_status', path: '/api/status', type: 'api', expectedStatuses: [200] },
  {
    name: 'api_public_agents',
    path: `/api/v1/public/agents?page=1&pageSize=25&includeMetrics=true&chain=${encodeURIComponent(CHAIN_KEY)}`,
    type: 'api',
    expectedStatuses: [200],
  },
  {
    name: 'api_public_leaderboard',
    path: `/api/v1/public/leaderboard?window=7d&mode=real&chain=${encodeURIComponent(CHAIN_KEY)}`,
    type: 'api',
    expectedStatuses: [200],
  },
  {
    name: 'api_public_activity',
    path: `/api/v1/public/activity?limit=100&chainKey=${encodeURIComponent(CHAIN_KEY)}`,
    type: 'api',
    expectedStatuses: [200],
  },
  {
    name: 'api_dashboard_summary',
    path: `/api/v1/public/dashboard/summary?chainKey=${encodeURIComponent(CHAIN_KEY)}&range=24h`,
    type: 'api',
    expectedStatuses: [200],
  },
  {
    name: 'api_dashboard_trending_tokens',
    path: `/api/v1/public/dashboard/trending-tokens?chainKey=${encodeURIComponent(CHAIN_KEY)}&limit=10`,
    type: 'api',
    expectedStatuses: [200],
  },
  { name: 'api_chat_messages', path: '/api/v1/chat/messages?limit=40', type: 'api', expectedStatuses: [200] },
];

function nowMs() {
  return Number(process.hrtime.bigint()) / 1e6;
}

function toFixed(value, digits = 2) {
  return Number(value.toFixed(digits));
}

function percentile(sortedValues, p) {
  if (sortedValues.length === 0) return 0;
  const clamped = Math.min(1, Math.max(0, p));
  const index = Math.ceil(sortedValues.length * clamped) - 1;
  return sortedValues[Math.max(0, index)];
}

async function timedFetch(url) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const startedAt = nowMs();
  try {
    const response = await fetch(url, {
      method: 'GET',
      cache: 'no-store',
      signal: controller.signal,
    });
    const body = await response.text();
    const endedAt = nowMs();
    return {
      ok: true,
      status: response.status,
      durationMs: endedAt - startedAt,
      sizeBytes: Buffer.byteLength(body, 'utf8'),
      contentType: response.headers.get('content-type') || null,
    };
  } catch (error) {
    const endedAt = nowMs();
    return {
      ok: false,
      status: 0,
      durationMs: endedAt - startedAt,
      error: String(error?.name === 'AbortError' ? `timeout_after_${REQUEST_TIMEOUT_MS}ms` : error?.message || error),
      sizeBytes: 0,
      contentType: null,
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

async function sampleRoute(route) {
  const url = `${BASE_URL}${route.path}`;
  const samples = [];

  for (let i = 0; i < WARMUP; i += 1) {
    await timedFetch(url);
  }

  for (let i = 0; i < ITERATIONS; i += 1) {
    const sample = await timedFetch(url);
    samples.push(sample);
  }

  const durations = samples.map((item) => item.durationMs).sort((a, b) => a - b);
  const last = samples[samples.length - 1] || {};
  const statusSet = [...new Set(samples.map((item) => item.status))];
  const errors = samples.filter((item) => !item.ok || !route.expectedStatuses.includes(item.status));

  const p50 = percentile(durations, 0.5);
  const p95 = percentile(durations, 0.95);
  const avg = durations.length === 0 ? 0 : durations.reduce((acc, value) => acc + value, 0) / durations.length;
  const max = durations.length === 0 ? 0 : durations[durations.length - 1];
  const min = durations.length === 0 ? 0 : durations[0];

  return {
    name: route.name,
    type: route.type,
    path: route.path,
    expectedStatuses: route.expectedStatuses,
    observedStatuses: statusSet,
    samples: samples.length,
    avgMs: toFixed(avg),
    p50Ms: toFixed(p50),
    p95Ms: toFixed(p95),
    minMs: toFixed(min),
    maxMs: toFixed(max),
    bytesLast: last.sizeBytes || 0,
    contentTypeLast: last.contentType || null,
    failedSamples: errors.length,
    warnings: [
      ...(p95 > WARN_P95_MS ? [`p95_above_warn_threshold_${WARN_P95_MS}ms`] : []),
      ...(errors.length > 0 ? ['unexpected_status_or_transport_error'] : []),
    ],
    errors: errors.map((item, index) => ({
      id: index + 1,
      status: item.status,
      durationMs: toFixed(item.durationMs),
      error: item.error || null,
    })),
  };
}

async function main() {
  const health = await timedFetch(`${BASE_URL}/api/health`);
  if (!health.ok || health.status !== 200) {
    console.log(
      JSON.stringify(
        {
          ok: false,
          blocker: 'server_unreachable',
          baseUrl: BASE_URL,
          healthProbe: health,
          actionHint: 'start the web app first, then rerun this script',
        },
        null,
        2,
      ),
    );
    process.exit(1);
  }

  const rows = [];
  for (const route of ROUTES) {
    // Keep sequential by default so latency is attributable to each route.
    // Use XCLAW_PERF_ITERATIONS/WARMUP to tune run duration and confidence.
    // eslint-disable-next-line no-await-in-loop
    rows.push(await sampleRoute(route));
  }

  rows.sort((a, b) => b.p95Ms - a.p95Ms);

  const slowRoutes = rows.filter((row) => row.p95Ms > WARN_P95_MS).map((row) => ({
    name: row.name,
    path: row.path,
    p95Ms: row.p95Ms,
    avgMs: row.avgMs,
    warnings: row.warnings,
  }));
  const failingRoutes = rows.filter((row) => row.failedSamples > 0);
  const failThresholdBreaches = FAIL_P95_MS > 0 ? rows.filter((row) => row.p95Ms > FAIL_P95_MS) : [];

  const report = {
    ok: failingRoutes.length === 0 && failThresholdBreaches.length === 0,
    baseUrl: BASE_URL,
    config: {
      iterations: ITERATIONS,
      warmup: WARMUP,
      requestTimeoutMs: REQUEST_TIMEOUT_MS,
      warnP95Ms: WARN_P95_MS,
      failP95Ms: FAIL_P95_MS,
    },
    summary: {
      totalRoutes: rows.length,
      slowRouteCount: slowRoutes.length,
      failingRouteCount: failingRoutes.length,
      failThresholdBreaches: failThresholdBreaches.length,
    },
    slowRoutes,
    failingRoutes: failingRoutes.map((row) => ({
      name: row.name,
      path: row.path,
      observedStatuses: row.observedStatuses,
      failedSamples: row.failedSamples,
      errors: row.errors,
    })),
    failThresholdRoutes: failThresholdBreaches.map((row) => ({
      name: row.name,
      path: row.path,
      p95Ms: row.p95Ms,
    })),
    rows,
  };

  console.log(JSON.stringify(report, null, 2));
  if (!report.ok) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.log(
    JSON.stringify(
      {
        ok: false,
        blocker: 'web_perf_test_exception',
        error: String(error?.message || error),
      },
      null,
      2,
    ),
  );
  process.exit(1);
});
