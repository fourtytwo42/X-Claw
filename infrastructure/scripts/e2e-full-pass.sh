#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BASE_URL="${XCLAW_E2E_BASE_URL:-http://127.0.0.1:3000}"
API_BASE="${BASE_URL}/api/v1"
AGENT_ID="${XCLAW_E2E_AGENT_ID:-ag_slice7}"
TOKEN_FILE="${XCLAW_E2E_BOOTSTRAP_TOKEN_FILE:-$HOME/.xclaw-secrets/management/${AGENT_ID}-bootstrap-token.json}"
DEFAULT_CHAIN="${XCLAW_DEFAULT_CHAIN:-base_sepolia}"
AGENT_API_KEY="${XCLAW_E2E_AGENT_API_KEY:-slice7_token_abc12345}"
PASS_PHRASE="${XCLAW_E2E_WALLET_PASSPHRASE:-passphrase-123}"
ENABLE_DEPOSITS="${XCLAW_E2E_ENABLE_DEPOSITS:-1}"
ENABLE_LIMIT_ORDERS="${XCLAW_E2E_ENABLE_LIMIT_ORDERS:-1}"
SIMULATE_API_OUTAGE="${XCLAW_E2E_SIMULATE_API_OUTAGE:-0}"
VERIFY_AGENT_APPROVALS_UI="${XCLAW_E2E_VERIFY_AGENT_APPROVALS_UI:-1}"
WORK_DIR="${XCLAW_E2E_WORK_DIR:-/tmp/xclaw-e2e-full}"
AGENT_HOME="${WORK_DIR}/agent-home"
COOKIE_JAR="${WORK_DIR}/cookies.txt"
STARTED_SERVER_PID=""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
RESULTS_FILE="${WORK_DIR}/results.ndjson"
mkdir -p "$WORK_DIR"
: > "$RESULTS_FILE"

record() {
  local status="$1"
  local name="$2"
  local detail="$3"
  printf '{"status":"%s","name":"%s","detail":"%s"}\n' "$status" "$name" "$(printf '%s' "$detail" | sed 's/"/\\"/g')" >> "$RESULTS_FILE"
  if [ "$status" = "PASS" ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
  elif [ "$status" = "FAIL" ]; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
  else
    WARN_COUNT=$((WARN_COUNT + 1))
  fi
  printf '[%s] %s :: %s\n' "$status" "$name" "$detail"
}

cleanup() {
  if [ -n "$STARTED_SERVER_PID" ]; then
    kill "$STARTED_SERVER_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    record "FAIL" "tool:${tool}" "missing required tool '${tool}'"
    return 1
  fi
  record "PASS" "tool:${tool}" "found"
  return 0
}

http_status() {
  local url="$1"
  curl -s -o /dev/null -w '%{http_code}' "$url" || true
}

ensure_server() {
  local status
  status="$(http_status "${BASE_URL}/api/health")"
  if [ "$status" = "200" ]; then
    record "PASS" "server:health" "already running at ${BASE_URL}"
    return
  fi

  nohup npm run dev >/tmp/xclaw-e2e-dev.log 2>&1 &
  STARTED_SERVER_PID="$!"
  sleep 3
  status="$(http_status "${BASE_URL}/api/health")"
  if [ "$status" = "200" ]; then
    record "PASS" "server:start" "started dev server pid=${STARTED_SERVER_PID}"
  else
    record "FAIL" "server:start" "unable to reach ${BASE_URL}/api/health after start attempt (status=${status})"
  fi
}

skill_cmd() {
  XCLAW_DEFAULT_CHAIN="$DEFAULT_CHAIN" \
  XCLAW_AGENT_HOME="$AGENT_HOME" \
  XCLAW_API_BASE_URL="$API_BASE" \
  XCLAW_AGENT_API_KEY="$AGENT_API_KEY" \
  XCLAW_WALLET_PASSPHRASE="$PASS_PHRASE" \
  python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py "$@"
}

skill_cmd_with_api() {
  local api_base="$1"
  shift
  XCLAW_DEFAULT_CHAIN="$DEFAULT_CHAIN" \
  XCLAW_AGENT_HOME="$AGENT_HOME" \
  XCLAW_API_BASE_URL="$api_base" \
  XCLAW_AGENT_API_KEY="$AGENT_API_KEY" \
  XCLAW_WALLET_PASSPHRASE="$PASS_PHRASE" \
  python3 skills/xclaw-agent/scripts/xclaw_agent_skill.py "$@"
}

post_json() {
  local method="$1"
  local url="$2"
  local payload="$3"
  local out="$4"
  shift 4
  local code
  code="$(curl -s -o "$out" -w '%{http_code}' -X "$method" "$url" -H 'Content-Type: application/json' "$@" --data "$payload" || true)"
  printf '%s' "$code"
}

setup_agent_wallet_home() {
  rm -rf "$AGENT_HOME"
  mkdir -p "$AGENT_HOME"
}

main() {
  require_tool curl || exit 1
  require_tool jq || exit 1
  require_tool python3 || exit 1
  require_tool node || exit 1

  if npm run db:migrate >/tmp/xclaw-e2e-migrate.log 2>&1; then
    record "PASS" "db:migrate" "applied migrations"
  else
    record "FAIL" "db:migrate" "failed (see /tmp/xclaw-e2e-migrate.log)"
    exit 1
  fi

  ensure_server
  if [ ! -f "$TOKEN_FILE" ]; then
    record "FAIL" "bootstrap-token:file" "missing token file: ${TOKEN_FILE}"
    exit 1
  fi

  local bootstrap_token
  bootstrap_token="$(jq -r '.token' "$TOKEN_FILE" 2>/dev/null)"
  if [ -z "$bootstrap_token" ] || [ "$bootstrap_token" = "null" ]; then
    record "FAIL" "bootstrap-token:parse" "unable to parse token from ${TOKEN_FILE}"
    exit 1
  fi
  record "PASS" "bootstrap-token:parse" "loaded"

  setup_agent_wallet_home
  record "PASS" "agent:wallet-home-reset" "${AGENT_HOME}"

  # Agent skill: status + wallet checks
  local out
  out="$(skill_cmd status 2>&1)"
  if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
    record "PASS" "agent:status" "$(printf '%s' "$out" | jq -c '.')"
  else
    record "FAIL" "agent:status" "$out"
  fi

  out="$(skill_cmd wallet-create 2>&1)"
  if printf '%s' "$out" | jq -e '.ok == true and .created == true' >/dev/null 2>&1; then
    record "PASS" "agent:wallet-create-via-skill" "$(printf '%s' "$out" | jq -c '{ok,code,message,chain,address,created}')"
  else
    record "FAIL" "agent:wallet-create-via-skill" "$out"
  fi

  out="$(skill_cmd wallet-health 2>&1)"
  if printf '%s' "$out" | jq -e '.ok == true and .hasWallet == true' >/dev/null 2>&1; then
    record "PASS" "agent:wallet-health" "$(printf '%s' "$out" | jq -c '.')"
  else
    record "FAIL" "agent:wallet-health" "$out"
  fi

  out="$(skill_cmd wallet-address 2>&1)"
  if printf '%s' "$out" | jq -e '.ok == true and (.address|type=="string")' >/dev/null 2>&1; then
    record "PASS" "agent:wallet-address" "$(printf '%s' "$out" | jq -c '.')"
  else
    record "FAIL" "agent:wallet-address" "$out"
  fi

  out="$(skill_cmd wallet-balance 2>&1)"
  if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
    record "PASS" "agent:wallet-balance" "$(printf '%s' "$out" | jq -c '.')"
  else
    record "FAIL" "agent:wallet-balance" "$out"
  fi

  local challenge nonce challenge_ts
  nonce="nonce_e2e_$(date +%s)ABCDEF"
  challenge_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  challenge=$'domain=xclaw.trade\nchain='"${DEFAULT_CHAIN}"$'\nnonce='"${nonce}"$'\ntimestamp='"${challenge_ts}"$'\naction=management_recovery'
  out="$(skill_cmd wallet-sign-challenge "$challenge" 2>&1)"
  if printf '%s' "$out" | jq -e '.ok == true and .signature' >/dev/null 2>&1; then
    record "PASS" "agent:wallet-sign-challenge" "$(printf '%s' "$out" | jq -c '{ok,code,scheme,challengeFormat}')"
  else
    record "FAIL" "agent:wallet-sign-challenge" "$out"
  fi

  # Agent proposes trade; initial status is assigned server-side (`approved` or `approval_pending`).
  local idem trade_resp trade_id trade_status code
  idem="e2e-propose-$(date +%s)"
  trade_resp="${WORK_DIR}/trade_proposed.json"
  code="$(post_json "POST" "${API_BASE}/trades/proposed" \
    "{\"schemaVersion\":1,\"agentId\":\"${AGENT_ID}\",\"chainKey\":\"base_sepolia\",\"mode\":\"real\",\"tokenIn\":\"WETH\",\"tokenOut\":\"USDC\",\"amountIn\":\"1.0\",\"slippageBps\":50,\"reason\":\"e2e-full-pass\"}" \
    "$trade_resp" \
    -H "Authorization: Bearer ${AGENT_API_KEY}" \
    -H "Idempotency-Key: ${idem}")"
  if [ "$code" = "200" ]; then
    trade_id="$(jq -r '.tradeId' "$trade_resp")"
    trade_status="$(jq -r '.status' "$trade_resp" 2>/dev/null || echo "")"
    record "PASS" "agent:trade-proposed" "tradeId=${trade_id} status=${trade_status}"
  else
    trade_id=""
    record "FAIL" "agent:trade-proposed" "status=${code} body=$(cat "$trade_resp" 2>/dev/null)"
  fi

  if [ -n "$trade_id" ] && [ "$trade_id" != "null" ]; then
    out="$(skill_cmd approval-check "$trade_id" 2>&1)"
    if [ "$trade_status" = "approval_pending" ]; then
      if printf '%s' "$out" | jq -e '.ok == false and .code == "approval_required"' >/dev/null 2>&1; then
        record "PASS" "agent:approval-check-pending" "$(printf '%s' "$out" | jq -c '{ok,code,message}')"
      else
        record "FAIL" "agent:approval-check-pending" "$out"
      fi
    else
      if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
        record "PASS" "agent:approval-check-approved" "$(printf '%s' "$out" | jq -c '{ok,code,message}')"
      else
        record "FAIL" "agent:approval-check-approved" "$out"
      fi
    fi
  fi

  # User/management bootstrap and approve
  rm -f "$COOKIE_JAR"
  code="$(post_json "POST" "${API_BASE}/management/session/bootstrap" \
    "{\"agentId\":\"${AGENT_ID}\",\"token\":\"${bootstrap_token}\"}" \
    "${WORK_DIR}/bootstrap.json" \
    -c "$COOKIE_JAR")"
  if [ "$code" = "200" ]; then
    record "PASS" "user:management-bootstrap" "$(cat "${WORK_DIR}/bootstrap.json")"
  else
    record "FAIL" "user:management-bootstrap" "status=${code} body=$(cat "${WORK_DIR}/bootstrap.json" 2>/dev/null)"
  fi

  if [ "${VERIFY_AGENT_APPROVALS_UI}" = "1" ]; then
    if [ -z "${XCLAW_E2E_AGENT_API_KEY:-}" ]; then
      record "WARN" "user:verify-ui-agent-approvals" "skipped: set XCLAW_E2E_AGENT_API_KEY to run browser approval-row verification."
    else
      if XCLAW_UI_VERIFY_BASE_URL="$BASE_URL" \
        XCLAW_UI_VERIFY_AGENT_ID="$AGENT_ID" \
        XCLAW_UI_VERIFY_CHAIN_KEY="$DEFAULT_CHAIN" \
        XCLAW_UI_VERIFY_AGENT_API_KEY="$AGENT_API_KEY" \
        XCLAW_UI_VERIFY_BOOTSTRAP_TOKEN_FILE="$TOKEN_FILE" \
        npm run verify:ui:agent-approvals >"${WORK_DIR}/verify_ui_agent_approvals.json" 2>&1; then
        record "PASS" "user:verify-ui-agent-approvals" "$(cat "${WORK_DIR}/verify_ui_agent_approvals.json")"
      else
        record "FAIL" "user:verify-ui-agent-approvals" "$(cat "${WORK_DIR}/verify_ui_agent_approvals.json" 2>/dev/null)"
      fi
    fi
  fi

  local csrf
  csrf="$(awk '$6=="xclaw_csrf" {print $7}' "$COOKIE_JAR" | tail -n 1)"
  if [ -n "$csrf" ]; then
    record "PASS" "user:csrf-cookie" "present"
  else
    record "FAIL" "user:csrf-cookie" "missing"
  fi

  if [ -n "${trade_id}" ] && [ -n "${csrf}" ]; then
    code="$(post_json "POST" "${API_BASE}/management/approvals/decision" \
      "{\"agentId\":\"${AGENT_ID}\",\"tradeId\":\"${trade_id}\",\"decision\":\"approve\"}" \
      "${WORK_DIR}/approval_decision.json" \
      -b "$COOKIE_JAR" \
      -H "X-CSRF-Token: ${csrf}")"
    if [ "$code" = "200" ]; then
      record "PASS" "user:approve-trade" "$(cat "${WORK_DIR}/approval_decision.json")"
    else
      record "FAIL" "user:approve-trade" "status=${code} body=$(cat "${WORK_DIR}/approval_decision.json" 2>/dev/null)"
    fi

    out="$(skill_cmd approval-check "$trade_id" 2>&1)"
    if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
      record "PASS" "agent:approval-check-approved" "$(printf '%s' "$out" | jq -c '{ok,code,message,status}')"
    else
      record "FAIL" "agent:approval-check-approved" "$out"
    fi

    out="$(skill_cmd trade-exec "$trade_id" 2>&1)"
    if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
      record "PASS" "agent:trade-exec" "$(printf '%s' "$out" | jq -c '{ok,code,message,status,tradeId,mode}')"
    else
      record "FAIL" "agent:trade-exec" "$out"
    fi

    out="$(skill_cmd report-send "$trade_id" 2>&1)"
    if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
      record "PASS" "agent:report-send" "$(printf '%s' "$out" | jq -c '{ok,code,message,eventType}')"
    else
      record "FAIL" "agent:report-send" "$out"
    fi
  fi

  # Management withdraw flow
  if [ -n "${csrf}" ]; then
    code="$(post_json "POST" "${API_BASE}/management/withdraw/destination" \
      "{\"agentId\":\"${AGENT_ID}\",\"chainKey\":\"base_sepolia\",\"destination\":\"0x1111111111111111111111111111111111111111\"}" \
      "${WORK_DIR}/withdraw_dest.json" \
      -b "$COOKIE_JAR" \
      -H "X-CSRF-Token: ${csrf}")"
    if [ "$code" = "200" ]; then
      record "PASS" "user:withdraw-destination" "$(cat "${WORK_DIR}/withdraw_dest.json")"
    else
      record "FAIL" "user:withdraw-destination" "status=${code} body=$(cat "${WORK_DIR}/withdraw_dest.json" 2>/dev/null)"
    fi

    code="$(post_json "POST" "${API_BASE}/management/withdraw" \
      "{\"agentId\":\"${AGENT_ID}\",\"chainKey\":\"base_sepolia\",\"asset\":\"ETH\",\"amount\":\"0.001\",\"destination\":\"0x1111111111111111111111111111111111111111\"}" \
      "${WORK_DIR}/withdraw_req.json" \
      -b "$COOKIE_JAR" \
      -H "X-CSRF-Token: ${csrf}")"
    if [ "$code" = "200" ]; then
      record "PASS" "user:withdraw-request" "$(cat "${WORK_DIR}/withdraw_req.json")"
    else
      record "FAIL" "user:withdraw-request" "status=${code} body=$(cat "${WORK_DIR}/withdraw_req.json" 2>/dev/null)"
    fi
  fi

  # Public/user page + data checks
  local page_code
  for page in "/" "/agents" "/agents/${AGENT_ID}"; do
    page_code="$(http_status "${BASE_URL}${page}")"
    if [ "$page_code" = "200" ]; then
      record "PASS" "public:page:${page}" "200"
    else
      record "FAIL" "public:page:${page}" "status=${page_code}"
    fi
  done

  page_code="$(http_status "${API_BASE}/public/leaderboard?window=7d&mode=mock&chain=all")"
  if [ "$page_code" = "200" ]; then
    record "PASS" "public:leaderboard" "200"
  else
    record "FAIL" "public:leaderboard" "status=${page_code}"
  fi

  page_code="$(http_status "${API_BASE}/public/agents?query=slice7")"
  if [ "$page_code" = "200" ]; then
    record "PASS" "public:search-agent" "200"
  else
    record "FAIL" "public:search-agent" "status=${page_code}"
  fi

  page_code="$(http_status "${API_BASE}/public/agents?query=0x1111111111111111111111111111111111111111")"
  if [ "$page_code" = "200" ]; then
    record "PASS" "public:search-wallet" "200"
  else
    record "FAIL" "public:search-wallet" "status=${page_code}"
  fi

  page_code="$(http_status "${API_BASE}/public/activity?limit=20")"
  if [ "$page_code" = "200" ]; then
    record "PASS" "public:activity-feed" "200"
  else
    record "FAIL" "public:activity-feed" "status=${page_code}"
  fi

  if [ "$ENABLE_DEPOSITS" = "1" ] && [ -n "${csrf}" ]; then
    code="$(curl -s -o "${WORK_DIR}/deposit.json" -w '%{http_code}' \
      "${API_BASE}/management/deposit?agentId=${AGENT_ID}" \
      -b "$COOKIE_JAR" \
      -H "X-CSRF-Token: ${csrf}" || true)"
    if [ "$code" = "200" ]; then
      record "PASS" "user:deposit-flow" "$(cat "${WORK_DIR}/deposit.json")"
    else
      record "FAIL" "user:deposit-flow" "status=${code} body=$(cat "${WORK_DIR}/deposit.json" 2>/dev/null)"
    fi
  fi

  if [ "$ENABLE_LIMIT_ORDERS" = "1" ] && [ -n "${csrf}" ]; then
    local limit_order_id
    code="$(post_json "POST" "${API_BASE}/management/limit-orders" \
      "{\"agentId\":\"${AGENT_ID}\",\"chainKey\":\"${DEFAULT_CHAIN}\",\"mode\":\"real\",\"side\":\"buy\",\"tokenIn\":\"0x4200000000000000000000000000000000000006\",\"tokenOut\":\"0x036CbD53842c5426634e7929541eC2318f3dCF7e\",\"amountIn\":\"0.01\",\"limitPrice\":\"999999999\",\"slippageBps\":50}" \
      "${WORK_DIR}/limit_create.json" \
      -b "$COOKIE_JAR" \
      -H "X-CSRF-Token: ${csrf}")"
    if [ "$code" = "200" ]; then
      limit_order_id="$(jq -r '.orderId' "${WORK_DIR}/limit_create.json")"
      record "PASS" "user:limit-order-create" "orderId=${limit_order_id}"
    else
      limit_order_id=""
      record "FAIL" "user:limit-order-create" "status=${code} body=$(cat "${WORK_DIR}/limit_create.json" 2>/dev/null)"
    fi

    if [ -n "$limit_order_id" ] && [ "$limit_order_id" != "null" ]; then
      out="$(skill_cmd limit-orders-sync 2>&1)"
      if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
        record "PASS" "agent:limit-orders-sync" "$(printf '%s' "$out" | jq -c '.')"
      else
        record "FAIL" "agent:limit-orders-sync" "$out"
      fi

      out="$(skill_cmd limit-orders-run-once 2>&1)"
      if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
        record "PASS" "agent:limit-orders-run-once" "$(printf '%s' "$out" | jq -c '.')"
      else
        record "FAIL" "agent:limit-orders-run-once" "$out"
      fi

      code="$(curl -s -o "${WORK_DIR}/limit_list.json" -w '%{http_code}' \
        "${API_BASE}/management/limit-orders?agentId=${AGENT_ID}&limit=50" \
        -b "$COOKIE_JAR" || true)"
      if [ "$code" = "200" ] && jq -e --arg id "$limit_order_id" '.items[] | select(.orderId == $id and .status == "filled")' "${WORK_DIR}/limit_list.json" >/dev/null 2>&1; then
        record "PASS" "user:limit-order-filled" "orderId=${limit_order_id}"
      else
        record "FAIL" "user:limit-order-filled" "status=${code} body=$(cat "${WORK_DIR}/limit_list.json" 2>/dev/null)"
      fi
    fi

    if [ "$SIMULATE_API_OUTAGE" = "1" ]; then
      local outage_order_id
      code="$(post_json "POST" "${API_BASE}/management/limit-orders" \
        "{\"agentId\":\"${AGENT_ID}\",\"chainKey\":\"${DEFAULT_CHAIN}\",\"mode\":\"real\",\"side\":\"buy\",\"tokenIn\":\"0x4200000000000000000000000000000000000006\",\"tokenOut\":\"0x036CbD53842c5426634e7929541eC2318f3dCF7e\",\"amountIn\":\"0.02\",\"limitPrice\":\"999999999\",\"slippageBps\":50}" \
        "${WORK_DIR}/limit_create_outage.json" \
        -b "$COOKIE_JAR" \
        -H "X-CSRF-Token: ${csrf}")"
      if [ "$code" = "200" ]; then
        outage_order_id="$(jq -r '.orderId' "${WORK_DIR}/limit_create_outage.json")"
        record "PASS" "user:limit-order-create-outage" "orderId=${outage_order_id}"
      else
        outage_order_id=""
        record "FAIL" "user:limit-order-create-outage" "status=${code} body=$(cat "${WORK_DIR}/limit_create_outage.json" 2>/dev/null)"
      fi

      if [ -n "$outage_order_id" ] && [ "$outage_order_id" != "null" ]; then
        out="$(skill_cmd limit-orders-sync 2>&1)"
        if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
          record "PASS" "agent:limit-orders-sync-outage" "$(printf '%s' "$out" | jq -c '.')"
        else
          record "FAIL" "agent:limit-orders-sync-outage" "$out"
        fi

        out="$(XCLAW_LIMIT_ORDERS_SYNC_ONCE=0 skill_cmd_with_api "http://127.0.0.1:3999/api/v1" limit-orders-run-once 2>&1)"
        if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
          record "PASS" "agent:limit-orders-run-once-api-down" "$(printf '%s' "$out" | jq -c '.')"
        else
          record "FAIL" "agent:limit-orders-run-once-api-down" "$out"
        fi

        out="$(skill_cmd limit-orders-run-once 2>&1)"
        if printf '%s' "$out" | jq -e '.ok == true' >/dev/null 2>&1; then
          record "PASS" "agent:limit-orders-replay-after-recovery" "$(printf '%s' "$out" | jq -c '.')"
        else
          record "FAIL" "agent:limit-orders-replay-after-recovery" "$out"
        fi
      fi
    fi
  fi

  local summary_file="${WORK_DIR}/summary.json"
  jq -s --arg baseUrl "$BASE_URL" --arg agentId "$AGENT_ID" \
    --arg tokenFile "$TOKEN_FILE" \
    --argjson pass "$PASS_COUNT" \
    --argjson fail "$FAIL_COUNT" \
    --argjson warn "$WARN_COUNT" \
    '{baseUrl:$baseUrl,agentId:$agentId,tokenFile:$tokenFile,pass:$pass,fail:$fail,warn:$warn,results:.}' \
    "$RESULTS_FILE" > "$summary_file"

  echo
  echo "Summary written: $summary_file"
  cat "$summary_file" | jq '.'

  if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
  fi
}

main "$@"
