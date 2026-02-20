#!/usr/bin/env node

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

import { chromium } from '@playwright/test';

const DEFAULT_BASE_URL = 'http://127.0.0.1:3000';
const DEFAULT_CHAIN_KEY = 'base_sepolia';

function nowIso() {
  return new Date().toISOString();
}

function safeJson(value) {
  try {
    return JSON.stringify(value);
  } catch {
    return JSON.stringify({ ok: false, code: 'serialization_failed' });
  }
}

function fail(code, message, extra = {}) {
  const payload = {
    ok: false,
    code,
    message,
    ...extra
  };
  console.error(safeJson(payload));
  process.exit(1);
}

async function main() {
  const baseUrl = String(process.env.XCLAW_UI_VERIFY_BASE_URL || DEFAULT_BASE_URL).trim().replace(/\/+$/, '');
  const agentId = String(process.env.XCLAW_UI_VERIFY_AGENT_ID || '').trim();
  const chainKey = String(process.env.XCLAW_UI_VERIFY_CHAIN_KEY || DEFAULT_CHAIN_KEY).trim();
  const agentApiKey = String(process.env.XCLAW_UI_VERIFY_AGENT_API_KEY || '').trim();
  const tokenFile = String(process.env.XCLAW_UI_VERIFY_BOOTSTRAP_TOKEN_FILE || '').trim();
  const timeoutMs = Number.parseInt(String(process.env.XCLAW_UI_VERIFY_TIMEOUT_MS || '20000'), 10);

  if (!agentId) {
    fail('missing_env', 'XCLAW_UI_VERIFY_AGENT_ID is required.');
  }
  if (!agentApiKey) {
    fail('missing_env', 'XCLAW_UI_VERIFY_AGENT_API_KEY is required.');
  }
  if (!tokenFile) {
    fail('missing_env', 'XCLAW_UI_VERIFY_BOOTSTRAP_TOKEN_FILE is required.');
  }

  let bootstrapToken = '';
  try {
    const parsed = JSON.parse(await readFile(tokenFile, 'utf8'));
    bootstrapToken = String(parsed?.token || '').trim();
  } catch (error) {
    fail('bootstrap_token_read_failed', 'Failed to read bootstrap token file.', {
      details: { tokenFile, error: error instanceof Error ? error.message : String(error) }
    });
  }
  if (!bootstrapToken) {
    fail('bootstrap_token_missing', 'Bootstrap token file does not include a non-empty token.', { details: { tokenFile } });
  }

  const approvalId = `xfr_ui_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`.toLowerCase();
  const receiver = '0x9099d24d55c105818b4e9ee117d87bc11063cf10';
  const mirrorPayload = {
    schemaVersion: 1,
    approvalId,
    chainKey,
    status: 'approval_pending',
    transferType: 'token',
    tokenAddress: '0x39a0c0d1b3ddce1b49faa5c6e1d300c14012f4e2',
    tokenSymbol: 'USDC',
    toAddress: receiver,
    amountWei: '10000000000000000000',
    policyBlockedAtCreate: true,
    policyBlockReasonCode: 'outbound_disabled',
    policyBlockReasonMessage: 'Policy blocked at create: outbound_disabled',
    executionMode: 'policy_override',
    createdAt: nowIso(),
    updatedAt: nowIso()
  };

  const mirrorResponse = await fetch(`${baseUrl}/api/v1/agent/transfer-approvals/mirror`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${agentApiKey}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify(mirrorPayload)
  });
  const mirrorJson = await mirrorResponse.json().catch(() => ({}));
  if (!mirrorResponse.ok) {
    fail(
      'mirror_write_failed',
      'Failed to write transfer approval mirror row before browser verification.',
      {
        details: {
          status: mirrorResponse.status,
          response: mirrorJson
        }
      }
    );
  }

  const artifactDir = path.join('/tmp', `xclaw-ui-verify-${approvalId}`);
  await mkdir(artifactDir, { recursive: true });

  const targetUrl = `${baseUrl}/agents/${encodeURIComponent(agentId)}?token=${encodeURIComponent(bootstrapToken)}`;
  const postBootstrapUrl = `${baseUrl}/agents/${encodeURIComponent(agentId)}`;
  const rowSelector = `[data-testid="approval-row-transfer-${approvalId}"]`;

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes('Host system is missing dependencies')) {
      fail('browser_dependency_missing', 'Playwright browser dependencies are missing on this host.', {
        actionHint: 'Install browser deps (`sudo npx playwright install-deps`) and rerun `npm run verify:ui:agent-approvals`.',
        details: { error: message }
      });
    }
    fail('browser_launch_failed', 'Failed to launch browser for UI verification.', {
      details: { error: message }
    });
  }
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
    await page.waitForURL((url) => {
      const href = String(url);
      return href.startsWith(postBootstrapUrl) && !href.includes('token=');
    }, { timeout: timeoutMs });

    const approvalsTitle = page.getByRole('heading', { name: 'Approvals' });
    await approvalsTitle.waitFor({ state: 'visible', timeout: timeoutMs });

    const row = page.locator(rowSelector).first();
    await row.waitFor({ state: 'visible', timeout: Math.max(timeoutMs, 15000) });

    const statusChip = row.locator('span').filter({ hasText: /waiting for approval|pending/i }).first();
    await statusChip.waitFor({ state: 'visible', timeout: timeoutMs });

    const payload = {
      ok: true,
      code: 'ok',
      message: 'Approval row rendered in /agents/:id under management session.',
      details: {
        baseUrl,
        agentId,
        chainKey,
        approvalId,
        selector: rowSelector,
        artifactDir
      }
    };
    console.log(safeJson(payload));
  } catch (error) {
    const screenshotPath = path.join(artifactDir, 'failure.png');
    const htmlPath = path.join(artifactDir, 'failure.html');
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => undefined);
    const html = await page.content().catch(() => '');
    await writeFile(htmlPath, html, 'utf8').catch(() => undefined);
    fail('approval_row_not_rendered', 'Approvals row was not rendered in /agents/:id.', {
      details: {
        error: error instanceof Error ? error.message : String(error),
        approvalId,
        selector: rowSelector,
        screenshotPath,
        htmlPath,
        currentUrl: page.url()
      }
    });
  } finally {
    await context.close().catch(() => undefined);
    await browser.close().catch(() => undefined);
  }
}

main().catch((error) => {
  fail('unexpected_error', 'Unhandled verifier failure.', {
    details: {
      error: error instanceof Error ? error.message : String(error)
    }
  });
});
