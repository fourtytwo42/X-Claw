'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { rememberManagedAgent } from '@/components/management-header-controls';
import { SidebarIcon } from '@/components/sidebar-icons';
import { ThemeToggle } from '@/components/theme-toggle';
import { SETTINGS_SECURITY_CAPABILITIES } from '@/lib/settings-security-capabilities';

import styles from './page.module.css';

type TabKey = 'access' | 'security' | 'danger';

type OwnerContext =
  | { phase: 'loading' }
  | { phase: 'none' }
  | { phase: 'error'; message: string }
  | { phase: 'ready'; activeAgentId: string; managedAgents: string[] };

type SessionAgentsPayload = {
  managedAgents?: string[];
  activeAgentId?: string;
};

type PreferencesState = {
  approvalPosture: 'per_trade' | 'allowlist' | 'global_allowed';
  requireUnlimitedAllowanceConfirmation: boolean;
  requireLargeWithdrawConfirmation: boolean;
  showSpenderDiffBeforeSigning: boolean;
  autoLock: 'never' | '5m' | '15m' | '1h';
  requireReconfirm: boolean;
  extraConfirmForDanger: boolean;
  storeFavorites: boolean;
};

const PREFERENCES_STORAGE_KEY = 'xclaw_settings_security_preferences_v1';
const MANAGED_AGENT_IDS_KEY = 'xclaw_managed_agent_ids';

const DEFAULT_PREFERENCES: PreferencesState = {
  approvalPosture: 'per_trade',
  requireUnlimitedAllowanceConfirmation: true,
  requireLargeWithdrawConfirmation: true,
  showSpenderDiffBeforeSigning: true,
  autoLock: '15m',
  requireReconfirm: true,
  extraConfirmForDanger: true,
  storeFavorites: true
};

function getCsrfToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const raw = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith('xclaw_csrf='));
  if (!raw) {
    return null;
  }
  return decodeURIComponent(raw.split('=')[1] ?? '');
}

function parseStoredManagedAgentIds(): string[] {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(MANAGED_AGENT_IDS_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is string => typeof item === 'string' && item.length > 0);
  } catch {
    return [];
  }
}

function storeManagedAgentIds(agentIds: string[]) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(MANAGED_AGENT_IDS_KEY, JSON.stringify(Array.from(new Set(agentIds))));
}

function loadPreferences(): PreferencesState {
  if (typeof window === 'undefined') {
    return DEFAULT_PREFERENCES;
  }
  try {
    const raw = window.localStorage.getItem(PREFERENCES_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_PREFERENCES;
    }
    const parsed = JSON.parse(raw) as Partial<PreferencesState>;
    return {
      approvalPosture:
        parsed.approvalPosture === 'allowlist' || parsed.approvalPosture === 'global_allowed' ? parsed.approvalPosture : 'per_trade',
      requireUnlimitedAllowanceConfirmation:
        typeof parsed.requireUnlimitedAllowanceConfirmation === 'boolean'
          ? parsed.requireUnlimitedAllowanceConfirmation
          : DEFAULT_PREFERENCES.requireUnlimitedAllowanceConfirmation,
      requireLargeWithdrawConfirmation:
        typeof parsed.requireLargeWithdrawConfirmation === 'boolean'
          ? parsed.requireLargeWithdrawConfirmation
          : DEFAULT_PREFERENCES.requireLargeWithdrawConfirmation,
      showSpenderDiffBeforeSigning:
        typeof parsed.showSpenderDiffBeforeSigning === 'boolean'
          ? parsed.showSpenderDiffBeforeSigning
          : DEFAULT_PREFERENCES.showSpenderDiffBeforeSigning,
      autoLock:
        parsed.autoLock === 'never' || parsed.autoLock === '5m' || parsed.autoLock === '1h' ? parsed.autoLock : '15m',
      requireReconfirm: typeof parsed.requireReconfirm === 'boolean' ? parsed.requireReconfirm : DEFAULT_PREFERENCES.requireReconfirm,
      extraConfirmForDanger:
        typeof parsed.extraConfirmForDanger === 'boolean' ? parsed.extraConfirmForDanger : DEFAULT_PREFERENCES.extraConfirmForDanger,
      storeFavorites: typeof parsed.storeFavorites === 'boolean' ? parsed.storeFavorites : DEFAULT_PREFERENCES.storeFavorites
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

function persistPreferences(preferences: PreferencesState) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(preferences));
}

function parseManagementLink(input: string): { agentId: string; token: string } | null {
  const raw = input.trim();
  if (!raw) {
    return null;
  }

  try {
    const parsed = new URL(raw);
    const token = parsed.searchParams.get('token')?.trim() ?? '';
    const agentIdFromPath = (() => {
      const match = parsed.pathname.match(/^\/agents\/([^/]+)$/);
      return match ? decodeURIComponent(match[1]) : '';
    })();
    const agentIdFromQuery = parsed.searchParams.get('agentId')?.trim() ?? '';
    const agentId = agentIdFromPath || agentIdFromQuery;

    if (!agentId || !token) {
      return null;
    }

    return { agentId, token };
  } catch {
    return null;
  }
}

async function postJson(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }

  const response = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(payload)
  });

  const json = (await response.json().catch(() => null)) as { message?: string; actionHint?: string; code?: string } | null;
  if (!response.ok) {
    const error = new Error(json?.message ?? 'Request failed.') as Error & { code?: string; actionHint?: string };
    if (json?.code) {
      error.code = json.code;
    }
    if (json?.actionHint) {
      error.actionHint = json.actionHint;
    }
    throw error;
  }

  return json;
}

function inferDeviceLabel(): string {
  if (typeof navigator === 'undefined') {
    return 'Current browser session';
  }

  const ua = navigator.userAgent;
  const browser = ua.includes('Edg/')
    ? 'Edge'
    : ua.includes('Chrome/')
      ? 'Chrome'
      : ua.includes('Firefox/')
        ? 'Firefox'
        : ua.includes('Safari/')
          ? 'Safari'
          : 'Browser';

  const os = ua.includes('Windows')
    ? 'Windows'
    : ua.includes('Mac OS X')
      ? 'macOS'
      : ua.includes('Linux')
        ? 'Linux'
        : ua.includes('Android')
          ? 'Android'
          : ua.includes('iPhone') || ua.includes('iPad')
            ? 'iOS'
            : 'Device';

  return `${browser} on ${os}`;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('access');
  const [ownerContext, setOwnerContext] = useState<OwnerContext>({ phase: 'loading' });
  const [preferences, setPreferences] = useState<PreferencesState>(DEFAULT_PREFERENCES);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [linkInput, setLinkInput] = useState('');
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  useEffect(() => {
    setPreferences(loadPreferences());
  }, []);

  useEffect(() => {
    persistPreferences(preferences);
  }, [preferences]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const hash = window.location.hash.toLowerCase();
    if (hash === '#security') {
      setActiveTab('security');
    } else if (hash === '#danger') {
      setActiveTab('danger');
    } else {
      setActiveTab('access');
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const nextHash = `#${activeTab}`;
    if (window.location.hash !== nextHash) {
      window.history.replaceState(null, '', `${window.location.pathname}${nextHash}`);
    }
  }, [activeTab]);

  useEffect(() => {
    let cancelled = false;

    async function loadOwnerContext() {
      try {
        setError(null);
        const response = await fetch('/api/v1/management/session/agents', { credentials: 'same-origin', cache: 'no-store' });
        if (!response.ok) {
          if (!cancelled) {
            setOwnerContext({ phase: 'none' });
          }
          return;
        }

        const payload = (await response.json()) as SessionAgentsPayload;
        const fromSession = Array.isArray(payload.managedAgents) ? payload.managedAgents : [];
        const merged = Array.from(new Set([...fromSession, ...parseStoredManagedAgentIds()]));
        const activeAgentId = payload.activeAgentId ?? merged[0];

        if (!cancelled && activeAgentId) {
          setOwnerContext({ phase: 'ready', activeAgentId, managedAgents: merged.length > 0 ? merged : [activeAgentId] });
        }
      } catch (loadError) {
        if (!cancelled) {
          setOwnerContext({ phase: 'error', message: loadError instanceof Error ? loadError.message : 'Failed to load access context.' });
        }
      }
    }

    void loadOwnerContext();

    return () => {
      cancelled = true;
    };
  }, []);

  const deviceLabel = useMemo(() => inferDeviceLabel(), []);

  const lastActive = useMemo(() => new Date().toLocaleString('en-US', { timeZone: 'UTC' }), []);

  const activeAgentId = ownerContext.phase === 'ready' ? ownerContext.activeAgentId : null;

  async function onAddAccess(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    setError(null);

    const parsed = parseManagementLink(linkInput);
    if (!parsed) {
      setError('Invalid key link format. Paste a full /agents/{agentId}?token=... URL.');
      return;
    }

    setPendingAction('add-access');
    try {
      await postJson('/api/v1/management/session/select', { agentId: parsed.agentId, token: parsed.token });
      rememberManagedAgent(parsed.agentId);
      const nextAgents = Array.from(new Set([...parseStoredManagedAgentIds(), parsed.agentId]));
      storeManagedAgentIds(nextAgents);
      setOwnerContext({ phase: 'ready', activeAgentId: parsed.agentId, managedAgents: nextAgents });
      setLinkInput('');
      setNotice(`Access granted on this device for ${parsed.agentId}.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to add access.');
    } finally {
      setPendingAction(null);
    }
  }

  async function onClearLocalAccess() {
    setNotice(null);
    setError(null);
    setPendingAction('clear-access');
    try {
      await postJson('/api/v1/management/logout', {});
      storeManagedAgentIds([]);
      setOwnerContext({ phase: 'none' });
      setNotice('Local access cleared on this device. On-chain approvals are unchanged.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to clear local access.');
    } finally {
      setPendingAction(null);
    }
  }

  async function onDangerAction(action: 'pause' | 'resume' | 'revoke-all') {
    if (!activeAgentId) {
      return;
    }

    const confirmLabel =
      action === 'pause'
        ? 'Pause this active agent on this device session?'
        : action === 'resume'
          ? 'Resume this active agent on this device session?'
          : 'Revoke all management sessions for this active agent?';

    if (!window.confirm(confirmLabel)) {
      return;
    }

    setNotice(null);
    setError(null);
    setPendingAction(action);

    try {
      if (action === 'pause') {
        await postJson('/api/v1/management/pause', { agentId: activeAgentId });
        setNotice(`Agent ${activeAgentId} paused.`);
      } else if (action === 'resume') {
        await postJson('/api/v1/management/resume', { agentId: activeAgentId });
        setNotice(`Agent ${activeAgentId} resumed.`);
      } else {
        await postJson('/api/v1/management/revoke-all', { agentId: activeAgentId });
        storeManagedAgentIds([]);
        setOwnerContext({ phase: 'none' });
        setNotice('Revoked all management sessions for the active agent. Local access has been cleared.');
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to execute action.');
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <Link href="/dashboard" className={styles.sidebarLogo} aria-label="X-Claw dashboard">
          <Image src="/X-Claw-Logo.png" alt="X-Claw" width={900} height={280} className={styles.sidebarLogoImage} priority />
        </Link>
        <nav className={styles.sidebarNav} aria-label="Settings sections">
          <Link className={styles.sidebarItem} href="/dashboard" aria-label="Dashboard" title="Dashboard">
            <SidebarIcon name="dashboard" />
          </Link>
          <Link className={styles.sidebarItem} href="/explore" aria-label="Explore" title="Explore">
            <SidebarIcon name="explore" />
          </Link>
          <Link className={styles.sidebarItem} href="/approvals" aria-label="Approvals Center" title="Approvals Center">
            <SidebarIcon name="approvals" />
          </Link>
          <Link
            className={`${styles.sidebarItem} ${styles.sidebarItemActive}`}
            href="/settings"
            aria-label="Settings & Security"
            title="Settings & Security"
          >
            <SidebarIcon name="settings" />
          </Link>
        </nav>
      </aside>

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div>
            <h1 className={styles.title}>Settings &amp; Security</h1>
            <p className={styles.subtitle}>Device-level access and safety preferences. There are no user accounts.</p>
          </div>
          <div className={styles.topbarControls}>
            <ChainHeaderControl className={styles.chainControl} id="settings-chain-select" />
            <ThemeToggle className={styles.topbarThemeToggle} />
          </div>
        </header>

        {notice ? <p className={styles.successBanner}>{notice}</p> : null}
        {error ? <p className={styles.warningBanner}>{error}</p> : null}

        <section className={styles.tabs}>
          <button type="button" className={activeTab === 'access' ? styles.tabActive : styles.tabButton} onClick={() => setActiveTab('access')}>
            Access
          </button>
          <button type="button" className={activeTab === 'security' ? styles.tabActive : styles.tabButton} onClick={() => setActiveTab('security')}>
            Security
          </button>
          <button type="button" className={activeTab === 'danger' ? styles.tabActive : styles.tabButton} onClick={() => setActiveTab('danger')}>
            Danger Zone
          </button>
        </section>

        {activeTab === 'access' ? (
          <div className={styles.panelGrid}>
            <section className={styles.card}>
              <h2>This Device</h2>
              <p className={styles.muted}>Device access is managed via secure cookies in this browser.</p>
              <div className={styles.kvList}>
                <div>
                  <span>Device label</span>
                  <strong>{deviceLabel}</strong>
                </div>
                <div>
                  <span>Last active (UTC)</span>
                  <strong>{lastActive}</strong>
                </div>
                <div>
                  <span>Access persistence</span>
                  <strong>Persists in this browser until cleared or revoked.</strong>
                </div>
              </div>
              <button type="button" onClick={() => void onClearLocalAccess()} disabled={pendingAction === 'clear-access'}>
                Clear local access
              </button>
              <p className={styles.helper}>Clearing access removes local control only. On-chain allowances are unchanged.</p>
            </section>

            <section className={styles.card}>
              <h2>Agents You Can Control</h2>
              <p className={styles.muted}>Access is device-scoped. Multi-agent verification and per-agent removal are placeholder-only in v1.</p>
              {ownerContext.phase === 'loading' ? <p className={styles.helper}>Loading access context...</p> : null}
              {ownerContext.phase === 'error' ? <p className={styles.warningInline}>{ownerContext.message}</p> : null}
              {ownerContext.phase === 'none' ? <p className={styles.helper}>No agent access found on this device.</p> : null}
              {ownerContext.phase === 'ready' ? (
                <div className={styles.agentList}>
                  {ownerContext.managedAgents.map((agentId) => (
                    <article key={agentId} className={styles.agentRow}>
                      <div>
                        <strong>{agentId}</strong>
                        <p>Owner Access · Granted via key link</p>
                      </div>
                      <div className={styles.agentActions}>
                        <Link href={`/agents/${encodeURIComponent(agentId)}`}>Open</Link>
                        <button type="button" disabled={!SETTINGS_SECURITY_CAPABILITIES.perAgentRemoveAccess}>
                          Remove Access
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
            </section>

            <section className={styles.card}>
              <h2>Add Agent Access</h2>
              <p className={styles.muted}>Paste a full key link. Treat key links as sensitive credentials.</p>
              <form className={styles.inlineForm} onSubmit={(event) => void onAddAccess(event)}>
                <input
                  value={linkInput}
                  onChange={(event) => setLinkInput(event.target.value)}
                  placeholder="https://.../agents/{agentId}?token=..."
                  aria-label="Paste agent key link"
                />
                <button type="submit" disabled={pendingAction === 'add-access'}>
                  Add Access
                </button>
              </form>
              <p className={styles.helper}>Primary flow remains opening the key link directly in this browser.</p>
            </section>
          </div>
        ) : null}

        {activeTab === 'security' ? (
          <div className={styles.panelGrid}>
            <section className={styles.card}>
              <h2>Approval Defaults</h2>
              <p className={styles.muted}>These are local defaults for this device and do not directly mutate agent policy until actioned elsewhere.</p>

              <div className={styles.radioGroup}>
                <label>
                  <input
                    type="radio"
                    checked={preferences.approvalPosture === 'per_trade'}
                    onChange={() => setPreferences((current) => ({ ...current, approvalPosture: 'per_trade' }))}
                  />
                  Per-trade approvals (recommended)
                </label>
                <label>
                  <input
                    type="radio"
                    checked={preferences.approvalPosture === 'allowlist'}
                    onChange={() => setPreferences((current) => ({ ...current, approvalPosture: 'allowlist' }))}
                  />
                  Token allowlist first
                </label>
                <label>
                  <input
                    type="radio"
                    checked={preferences.approvalPosture === 'global_allowed'}
                    onChange={() => setPreferences((current) => ({ ...current, approvalPosture: 'global_allowed' }))}
                  />
                  Global approval allowed (advanced)
                </label>
              </div>

              <div className={styles.toggleList}>
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.requireUnlimitedAllowanceConfirmation}
                    onChange={(event) =>
                      setPreferences((current) => ({ ...current, requireUnlimitedAllowanceConfirmation: event.target.checked }))
                    }
                  />
                  Require confirmation for unlimited allowances
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.requireLargeWithdrawConfirmation}
                    onChange={(event) => setPreferences((current) => ({ ...current, requireLargeWithdrawConfirmation: event.target.checked }))}
                  />
                  Require confirmation for large withdrawals
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.showSpenderDiffBeforeSigning}
                    onChange={(event) => setPreferences((current) => ({ ...current, showSpenderDiffBeforeSigning: event.target.checked }))}
                  />
                  Always show spender + allowance diff before signing
                </label>
              </div>
            </section>

            <section className={styles.card}>
              <h2>Auto-Lock / Safety</h2>
              <div className={styles.inlineForm}>
                <label htmlFor="settings-autolock">Auto-lock approvals after idle</label>
                <select
                  id="settings-autolock"
                  value={preferences.autoLock}
                  onChange={(event) =>
                    setPreferences((current) => ({
                      ...current,
                      autoLock: event.target.value as PreferencesState['autoLock']
                    }))
                  }
                >
                  <option value="never">Never</option>
                  <option value="5m">5m</option>
                  <option value="15m">15m</option>
                  <option value="1h">1h</option>
                </select>
              </div>
              <div className={styles.toggleList}>
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.requireReconfirm}
                    onChange={(event) => setPreferences((current) => ({ ...current, requireReconfirm: event.target.checked }))}
                  />
                  Require re-confirmation before approving
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.extraConfirmForDanger}
                    onChange={(event) => setPreferences((current) => ({ ...current, extraConfirmForDanger: event.target.checked }))}
                  />
                  Hide high-risk actions behind extra confirmation
                </label>
              </div>
            </section>

            <section className={styles.card}>
              <h2>Privacy</h2>
              <div className={styles.toggleList}>
                <label>
                  <input
                    type="checkbox"
                    checked={preferences.storeFavorites}
                    onChange={(event) => setPreferences((current) => ({ ...current, storeFavorites: event.target.checked }))}
                  />
                  Store favorites locally on this device
                </label>
              </div>
              <p className={styles.helper}>Agent access list is stored locally to improve device UX continuity.</p>
            </section>
          </div>
        ) : null}

        {activeTab === 'danger' ? (
          <div className={styles.panelGrid}>
            <section className={`${styles.card} ${styles.dangerCard}`}>
              <h2>Emergency Controls</h2>
              <p className={styles.muted}>These actions apply to the active session agent only in v1.</p>
              <div className={styles.actionRow}>
                <button type="button" onClick={() => void onDangerAction('pause')} disabled={!activeAgentId || pendingAction === 'pause'}>
                  Pause Active Agent
                </button>
                <button type="button" onClick={() => void onDangerAction('resume')} disabled={!activeAgentId || pendingAction === 'resume'}>
                  Resume Active Agent
                </button>
                <button
                  type="button"
                  className={styles.dangerButton}
                  onClick={() => void onDangerAction('revoke-all')}
                  disabled={!activeAgentId || pendingAction === 'revoke-all'}
                >
                  Revoke All Sessions
                </button>
              </div>
              <p className={styles.helper}>
                Global panic controls for all owned agents and on-chain allowance sweep require dedicated aggregation APIs and are placeholder-only.
              </p>
            </section>

            <section className={`${styles.card} ${styles.dangerCard}`}>
              <h2>Global Panic Controls (Placeholder)</h2>
              <div className={styles.actionRow}>
                <button type="button" disabled={!SETTINGS_SECURITY_CAPABILITIES.globalPanicActions}>
                  Pause All Owned Agents
                </button>
                <button type="button" disabled={!SETTINGS_SECURITY_CAPABILITIES.allowanceInventorySweep}>
                  Revoke All Allowances
                </button>
                <button type="button" disabled={!SETTINGS_SECURITY_CAPABILITIES.globalPanicActions}>
                  Disable All Copy Trading
                </button>
              </div>
              <p className={styles.helper}>Use per-agent controls today from `/agents/:id` and `/approvals` until global APIs are available.</p>
            </section>
          </div>
        ) : null}
      </section>
    </div>
  );
}
