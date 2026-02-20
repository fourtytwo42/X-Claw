const DEFAULT_UI_FETCH_TIMEOUT_MS = Number.parseInt(process.env.NEXT_PUBLIC_XCLAW_UI_FETCH_TIMEOUT_MS || '8000', 10);
const DEFAULT_UPSTREAM_FETCH_TIMEOUT_MS = Number.parseInt(process.env.XCLAW_UPSTREAM_FETCH_TIMEOUT_MS || '5000', 10);

function resolvedTimeoutMs(timeoutMs: number | undefined, fallbackMs: number): number {
  if (typeof timeoutMs === 'number' && Number.isFinite(timeoutMs) && timeoutMs > 0) {
    return timeoutMs;
  }
  return fallbackMs;
}

export function uiFetchTimeoutMs(timeoutMs?: number): number {
  return resolvedTimeoutMs(timeoutMs, DEFAULT_UI_FETCH_TIMEOUT_MS);
}

export function upstreamFetchTimeoutMs(timeoutMs?: number): number {
  return resolvedTimeoutMs(timeoutMs, DEFAULT_UPSTREAM_FETCH_TIMEOUT_MS);
}

export async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs?: number): Promise<Response> {
  const effectiveTimeoutMs = uiFetchTimeoutMs(timeoutMs);
  const controller = new AbortController();
  const parentSignal = init.signal;

  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  const onParentAbort = () => controller.abort(parentSignal?.reason);

  if (parentSignal) {
    if (parentSignal.aborted) {
      controller.abort(parentSignal.reason);
    } else {
      parentSignal.addEventListener('abort', onParentAbort, { once: true });
    }
  }

  timeoutId = setTimeout(() => {
    controller.abort(new Error(`fetch_timeout_${effectiveTimeoutMs}ms`));
  }, effectiveTimeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    if (parentSignal) {
      parentSignal.removeEventListener('abort', onParentAbort);
    }
  }
}
