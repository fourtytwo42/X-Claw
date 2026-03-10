#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();

function expect(condition, name, details = {}) {
  return { ok: !!condition, name, details };
}

function failPayload(checks) {
  const failed = checks.filter((check) => !check.ok);
  console.log(JSON.stringify({ ok: failed.length === 0, passed: checks.length - failed.length, failed: failed.length, checks }, null, 2));
  if (failed.length > 0) process.exit(1);
}

const checks = [];

const bootstrapRoute = fs.readFileSync(path.join(root, 'apps/network-web/src/app/api/v1/management/session/bootstrap/route.ts'), 'utf8');
checks.push(expect(bootstrapRoute.includes('setManagementCookie(response, req, result.data.managementCookieValue)'), 'bootstrap_route_sets_management_cookie'));
checks.push(expect(bootstrapRoute.includes('setCsrfCookie(response, req, result.data.csrfToken)'), 'bootstrap_route_sets_csrf_cookie'));
checks.push(expect(bootstrapRoute.includes('augmentBootstrapAuthError'), 'bootstrap_route_preserves_auth_error_contract'));

const mgmtAuth = fs.readFileSync(path.join(root, 'apps/network-web/src/lib/management-auth.ts'), 'utf8');
checks.push(expect(/code:\s*'csrf_invalid'/.test(mgmtAuth), 'management_auth_exposes_csrf_invalid'));
checks.push(expect(/requireCsrfToken\(req, requestId\)/.test(mgmtAuth), 'management_auth_has_require_csrf_helper'));

const defaultChainBatch = fs.readFileSync(path.join(root, 'apps/network-web/src/app/api/v1/management/default-chain/update-batch/route.ts'), 'utf8');
checks.push(expect(defaultChainBatch.includes('const csrf = requireCsrfToken(req, requestId);'), 'default_chain_update_batch_requires_csrf'));

const sessionAgentsRoute = fs.readFileSync(path.join(root, 'apps/network-web/src/app/api/v1/management/session/agents/route.ts'), 'utf8');
checks.push(expect(sessionAgentsRoute.includes('requireManagementSession(req, requestId)'), 'session_agents_route_requires_management_session'));

const agentPage = fs.readFileSync(path.join(root, 'apps/network-web/src/app/agents/[agentId]/page.tsx'), 'utf8');
checks.push(expect(agentPage.includes('/api/v1/management/session/bootstrap'), 'agents_page_bootstraps_management_session'));
checks.push(expect(agentPage.includes("headers['x-csrf-token'] = csrf;"), 'agents_page_sends_csrf_header_for_management_writes'));

const source = fs.readFileSync(path.join(root, 'docs/XCLAW_SOURCE_OF_TRUTH.md'), 'utf8');
checks.push(expect(source.includes('sensitive management writes require `xclaw_mgmt` + `xclaw_csrf`'), 'source_of_truth_management_cookie_csrf_contract'));
checks.push(expect(source.includes('no step-up layer'), 'source_of_truth_no_stepup_contract'));

const roadmap = fs.readFileSync(path.join(root, 'docs/XCLAW_BUILD_ROADMAP.md'), 'utf8');
checks.push(expect(!roadmap.includes('step-up sensitive action flow verified (blocked: bootstrap token unavailable in session)'), 'roadmap_stale_stepup_blocker_removed'));

failPayload(checks);
