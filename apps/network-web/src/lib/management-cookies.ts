import type { NextRequest, NextResponse } from 'next/server';

export const MGMT_COOKIE_NAME = 'xclaw_mgmt';
export const CSRF_COOKIE_NAME = 'xclaw_csrf';

export const MGMT_COOKIE_MAX_AGE_SEC = 30 * 24 * 60 * 60;

function isLoopbackHost(hostname: string): boolean {
  const host = hostname.toLowerCase();
  return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

function normalizeHostHeader(value: string): string {
  const first = String(value || "")
    .split(",")[0]
    ?.trim() ?? "";
  if (!first) {
    return "";
  }
  if (first.startsWith("[")) {
    const closing = first.indexOf("]");
    return closing > 0 ? first.slice(1, closing).trim().toLowerCase() : first.trim().toLowerCase();
  }
  const colonCount = first.split(":").length - 1;
  if (colonCount === 1) {
    return first.split(":")[0]?.trim().toLowerCase() ?? "";
  }
  return first.trim().toLowerCase();
}

function resolveRequestHostname(req: NextRequest): string {
  const forwardedHost = normalizeHostHeader(req.headers.get("x-forwarded-host") ?? "");
  if (forwardedHost) {
    return forwardedHost;
  }
  const host = normalizeHostHeader(req.headers.get("host") ?? "");
  if (host) {
    return host;
  }
  return String(req.nextUrl.hostname || "").trim().toLowerCase();
}

export function shouldUseSecureCookies(req: NextRequest): boolean {
  return !isLoopbackHost(resolveRequestHostname(req));
}

export function setManagementCookie(res: NextResponse, req: NextRequest, value: string): void {
  res.cookies.set(MGMT_COOKIE_NAME, value, {
    httpOnly: true,
    secure: shouldUseSecureCookies(req),
    sameSite: 'strict',
    maxAge: MGMT_COOKIE_MAX_AGE_SEC,
    path: '/'
  });
}

export function setCsrfCookie(res: NextResponse, req: NextRequest, value: string): void {
  res.cookies.set(CSRF_COOKIE_NAME, value, {
    httpOnly: false,
    secure: shouldUseSecureCookies(req),
    sameSite: 'strict',
    maxAge: MGMT_COOKIE_MAX_AGE_SEC,
    path: '/'
  });
}

function clearCookie(res: NextResponse, req: NextRequest, name: string): void {
  res.cookies.set(name, '', {
    httpOnly: name !== CSRF_COOKIE_NAME,
    secure: shouldUseSecureCookies(req),
    sameSite: 'strict',
    maxAge: 0,
    path: '/'
  });
}

export function clearManagementCookie(res: NextResponse, req: NextRequest): void {
  clearCookie(res, req, MGMT_COOKIE_NAME);
}

export function clearCsrfCookie(res: NextResponse, req: NextRequest): void {
  clearCookie(res, req, CSRF_COOKIE_NAME);
}

export function clearAllManagementCookies(res: NextResponse, req: NextRequest): void {
  clearManagementCookie(res, req);
  clearCsrfCookie(res, req);
}
