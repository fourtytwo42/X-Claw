'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { ChainHeaderControl } from '@/components/chain-header-control';
import { rememberManagedAgent } from '@/components/management-header-controls';
import { PrimaryNav } from '@/components/primary-nav';
import { ThemeToggle } from '@/components/theme-toggle';
import { fetchWithTimeout, uiFetchTimeoutMs } from '@/lib/fetch-timeout';

import styles from './page.module.css';

type TabKey = 'access' | 'security';

type OwnerContext =
  | { phase: 'loading' }
  | { phase: 'none' }
  | { phase: 'error'; message: string }
  | { phase: 'ready'; activeAgentId: string; managedAgents: string[] };

type SessionAgentsPayload = {
  managedAgents?: string[];
  activeAgentId?: string;
};

type SessionAgentDetachPayload = {
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
const MANAGED_AGENT_TOKENS_KEY = 'xclaw_managed_agent_tokens';

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

function parseStoredManagedAgentTokens(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(MANAGED_AGENT_TOKENS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }
    const out: Record<string, string> = {};
    for (const [agentId, token] of Object.entries(parsed)) {
      if (typeof agentId !== 'string' || !agentId.trim() || typeof token !== 'string' || !token.trim()) {
        continue;
      }
      out[agentId.trim()] = token.trim();
    }
    return out;
  } catch {
    return {};
  }
}

function storeManagedAgentTokens(tokens: Record<string, string>) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(MANAGED_AGENT_TOKENS_KEY, JSON.stringify(tokens));
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

  const response = await fetchWithTimeout(path, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(payload)
  }, uiFetchTimeoutMs());

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

async function deleteJson(path: string, payload: Record<string, unknown>) {
  const csrf = getCsrfToken();
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (csrf) {
    headers['x-csrf-token'] = csrf;
  }

  const response = await fetchWithTimeout(path, {
    method: 'DELETE',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(payload)
  }, uiFetchTimeoutMs());

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
  const [managedAgentNames, setManagedAgentNames] = useState<Record<string, string>>({});
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
        const response = await fetchWithTimeout(
          '/api/v1/management/session/agents',
          { credentials: 'same-origin', cache: 'no-store' },
          uiFetchTimeoutMs(),
        );
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

  function managedAgentLabel(agentId: string): string {
    return managedAgentNames[agentId] || 'Unnamed Agent';
  }

  useEffect(() => {
    if (ownerContext.phase !== 'ready') {
      setManagedAgentNames({});
      return;
    }

    const managedAgents = ownerContext.managedAgents;
    let cancelled = false;
    async function loadManagedAgentNames() {
      const names: Record<string, string> = {};
      await Promise.all(
        managedAgents.map(async (agentId) => {
          try {
            const response = await fetchWithTimeout(
              `/api/v1/public/agents/${encodeURIComponent(agentId)}`,
              { cache: 'no-store' },
              uiFetchTimeoutMs(),
            );
            if (!response.ok) {
              names[agentId] = 'Unnamed Agent';
              return;
            }
            const payload = (await response.json()) as { agent?: { agent_name?: string | null } };
            names[agentId] = payload.agent?.agent_name?.trim() || 'Unnamed Agent';
          } catch {
            names[agentId] = 'Unnamed Agent';
          }
        })
      );

      if (!cancelled) {
        setManagedAgentNames(names);
      }
    }

    void loadManagedAgentNames();
    return () => {
      cancelled = true;
    };
  }, [ownerContext]);

  async function onAddAccess(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    setError(null);

    const parsed = parseManagementLink(linkInput);
    if (!parsed) {
      setError('This link format looks wrong. Paste the full agent key link URL.');
      return;
    }

    setPendingAction('add-access');
    try {
      await postJson('/api/v1/management/session/select', { agentId: parsed.agentId, token: parsed.token });
      rememberManagedAgent(parsed.agentId);
      const nextAgents = Array.from(new Set([...parseStoredManagedAgentIds(), parsed.agentId]));
      storeManagedAgentIds(nextAgents);
      const tokens = parseStoredManagedAgentTokens();
      tokens[parsed.agentId] = parsed.token;
      storeManagedAgentTokens(tokens);
      setOwnerContext({ phase: 'ready', activeAgentId: parsed.agentId, managedAgents: nextAgents });
      setLinkInput('');
      setNotice('Access added on this device.');
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
      storeManagedAgentTokens({});
      setOwnerContext({ phase: 'none' });
      setNotice('Local access cleared on this device. On-chain approvals are unchanged.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to clear local access.');
    } finally {
      setPendingAction(null);
    }
  }

  async function onRemoveAgentAccess(agentId: string) {
    if (typeof window === 'undefined') {
      return;
    }

    const agentName = managedAgentLabel(agentId);
    const confirmed = window.confirm(
      `Remove access to "${agentName}" on this browser?\n\nThis detaches this browser session from that agent. On-chain approvals are unchanged.`
    );
    if (!confirmed) {
      return;
    }

    setNotice(null);
    setError(null);
    setPendingAction(`remove-access:${agentId}`);

    try {
      const activeAgentId = ownerContext.phase === 'ready' ? ownerContext.activeAgentId : null;
      const isActiveAgent = activeAgentId === agentId;

      if (isActiveAgent) {
        await postJson('/api/v1/management/logout', {});
        storeManagedAgentIds([]);
        storeManagedAgentTokens({});
        setOwnerContext({ phase: 'none' });
        setNotice(`Removed ${agentName} from this browser session.`);
        return;
      }

      const detached = (await deleteJson('/api/v1/management/session/agents', { agentId })) as SessionAgentDetachPayload | null;
      const serverManagedAgents =
        Array.isArray(detached?.managedAgents) && detached?.managedAgents
          ? detached.managedAgents.filter((id): id is string => typeof id === 'string' && id.trim().length > 0)
          : ownerContext.phase === 'ready'
            ? ownerContext.managedAgents.filter((id) => id !== agentId)
            : [];

      const nextStoredAgents = parseStoredManagedAgentIds().filter((id) => id !== agentId);
      storeManagedAgentIds(nextStoredAgents.filter((id) => serverManagedAgents.includes(id)));
      const tokens = parseStoredManagedAgentTokens();
      delete tokens[agentId];
      storeManagedAgentTokens(tokens);
      setManagedAgentNames((current) => {
        const copy = { ...current };
        delete copy[agentId];
        return copy;
      });

      if (ownerContext.phase === 'ready') {
        if (serverManagedAgents.length === 0) {
          setOwnerContext({ phase: 'none' });
        } else {
          setOwnerContext({
            phase: 'ready',
            activeAgentId: detached?.activeAgentId && typeof detached.activeAgentId === 'string' ? detached.activeAgentId : ownerContext.activeAgentId,
            managedAgents: serverManagedAgents
          });
        }
      }

      setNotice(`Removed ${agentName} from this browser session.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to remove access.');
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className={styles.root}>
      <PrimaryNav />

      <section className={styles.mainSurface}>
        <header className={styles.topbar}>
          <div>
            <h1 className={styles.title}>Settings &amp; Security</h1>
            <p className={styles.subtitle}>Manage device access and safety settings. There are no usernames or passwords.</p>
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
        </section>

        {activeTab === 'access' ? (
          <div className={styles.panelGrid}>
            <section className={styles.card}>
              <h2>This Device</h2>
              <p className={styles.muted}>Access is stored in secure browser cookies on this device.</p>
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
                  <strong>Stays active in this browser until you clear or revoke it.</strong>
                </div>
              </div>
              <button type="button" onClick={() => void onClearLocalAccess()} disabled={pendingAction === 'clear-access'}>
                Clear local access
              </button>
              <p className={styles.helper}>This only removes browser access. It does not change on-chain approvals.</p>
            </section>

            <section className={styles.card}>
              <h2>Agents You Can Control</h2>
              <p className={styles.muted}>These are the agents this browser can manage.</p>
              {ownerContext.phase === 'loading' ? <p className={styles.helper}>Loading your agent access...</p> : null}
              {ownerContext.phase === 'error' ? <p className={styles.warningInline}>{ownerContext.message}</p> : null}
              {ownerContext.phase === 'none' ? <p className={styles.helper}>No agent access found on this device.</p> : null}
              {ownerContext.phase === 'ready' ? (
                <div className={styles.agentList}>
                  {ownerContext.managedAgents.map((agentId) => (
                    <article key={agentId} className={styles.agentRow}>
                      <div>
                        <strong>{managedAgentLabel(agentId)}</strong>
                        <p>Owner access granted by key link</p>
                      </div>
                      <div className={styles.agentActions}>
                        <Link href={`/agents/${encodeURIComponent(agentId)}`}>Open</Link>
                        <button
                          type="button"
                          className={styles.dangerButton}
                          disabled={pendingAction === `remove-access:${agentId}`}
                          onClick={() => void onRemoveAgentAccess(agentId)}
                        >
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
              <p className={styles.muted}>Paste a full key link. Keep these links private.</p>
              <form className={styles.inlineForm} onSubmit={(event) => void onAddAccess(event)}>
                <input
                  value={linkInput}
                  onChange={(event) => setLinkInput(event.target.value)}
                  placeholder="https://.../agents/.../?token=..."
                  aria-label="Paste agent key link"
                />
                <button type="submit" disabled={pendingAction === 'add-access'}>
                  Add Access
                </button>
              </form>
              <p className={styles.helper}>Tip: You can also open the key link directly in this browser.</p>
            </section>
          </div>
        ) : null}

        {activeTab === 'security' ? (
          <div className={styles.panelGrid}>
            <section className={styles.card}>
              <h2>Approval Defaults</h2>
              <p className={styles.muted}>These are default safety choices for this device.</p>
              <p className={styles.helper}>Ask every trade is active (recommended).</p>

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
              <p className={styles.helper}>Your agent list is stored locally to keep this device experience consistent.</p>
            </section>
          </div>
        ) : null}

      </section>
    </div>
  );
}
