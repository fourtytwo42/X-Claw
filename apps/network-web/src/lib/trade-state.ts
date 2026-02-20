const allowedTransitions = new Map<string, Set<string>>([
  ['proposed', new Set(['approval_pending', 'approved'])],
  ['approval_pending', new Set(['approved', 'rejected', 'expired'])],
  ['approved', new Set(['executing', 'failed'])],
  ['executing', new Set(['verifying', 'failed'])],
  ['verifying', new Set(['filled', 'failed', 'verification_timeout'])],
  ['failed', new Set(['executing'])],
  ['rejected', new Set()],
  ['expired', new Set()],
  ['filled', new Set()],
  ['verification_timeout', new Set()]
]);

const statusToEventType = new Map<string, string>([
  ['approval_pending', 'trade_approval_pending'],
  ['approved', 'trade_approved'],
  ['rejected', 'trade_rejected'],
  ['executing', 'trade_executing'],
  ['verifying', 'trade_verifying'],
  ['filled', 'trade_filled'],
  ['failed', 'trade_failed'],
  ['expired', 'trade_expired'],
  ['verification_timeout', 'trade_verification_timeout']
]);

export function isAllowedTransition(fromStatus: string, toStatus: string): boolean {
  const allowedSet = allowedTransitions.get(fromStatus);
  if (!allowedSet) {
    return false;
  }

  return allowedSet.has(toStatus);
}

export function eventTypeForTradeStatus(status: string): string {
  return statusToEventType.get(status) ?? 'trade_proposed';
}
