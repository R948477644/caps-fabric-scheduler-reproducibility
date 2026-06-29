#!/usr/bin/env bash
set -euo pipefail

RATE="${EXP3_RATE:-300}"
DURATION="${EXP3_DURATION:-20}"
CLIENTS="${EXP3_CLIENTS:-100}"
ACCOUNT_COUNT="${EXP3_ACCOUNT_COUNT:-1000}"
HOT_ACCOUNTS="${EXP3_HOT_ACCOUNTS:-100}"
BATCH_SIZE="${EXP3_BATCH_SIZE:-2}"
AUDIT_SIZE="${EXP3_AUDIT_SIZE:-8}"
MAX_OUTSTANDING="${EXP3_MAX_OUTSTANDING:-10000}"
MAX_SOCKETS="${EXP3_MAX_SOCKETS:-10000}"

mkdir -p results

run_case() {
  local method="$1"
  local port="$2"
  local prefix="results/exp3-w3-${method}-hot${HOT_ACCOUNTS}-${RATE}tps"

  echo "=== EXP3 W3 ${method} hot=${HOT_ACCOUNTS} rate=${RATE} TPS ==="
  curl -fsS -X POST "http://127.0.0.1:${port}/reset" >/dev/null
  node tools/workload-loadgen.js \
    --url "http://127.0.0.1:${port}/submit" \
    --clients "$CLIENTS" \
    --tps "$RATE" \
    --duration "$DURATION" \
    --accountCount "$ACCOUNT_COUNT" \
    --hotAccountCount "$HOT_ACCOUNTS" \
    --workload w3 \
    --batchSize "$BATCH_SIZE" \
    --auditSize "$AUDIT_SIZE" \
    --maxOutstanding "$MAX_OUTSTANDING" \
    --maxSockets "$MAX_SOCKETS" \
    --out "${prefix}-client.json" | tee "${prefix}-client.log"
  curl -fsS "http://127.0.0.1:${port}/metrics" | tee "${prefix}-metrics.json"
  echo
}

run_case "traditional-lock" "${TRAD_LOCK_DISPATCHER_PORT:-8082}"
run_case "pacc-dabs" "${VLL_SCD_DISPATCHER_PORT:-8084}"
run_case "pacc-lpaac" "${PACC_LPAAC_DISPATCHER_PORT:-8087}"
run_case "pa-vscd" "${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}"
