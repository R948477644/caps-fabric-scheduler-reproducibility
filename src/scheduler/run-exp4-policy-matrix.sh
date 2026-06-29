#!/usr/bin/env bash
set -euo pipefail

POLICY_LABEL="${EXP4_POLICY_LABEL:-default-policy}"
RATES="${EXP4_RATES:-300 500}"
DURATION="${EXP4_DURATION:-20}"
CLIENTS="${EXP4_CLIENTS:-100}"
ACCOUNT_COUNT="${EXP4_ACCOUNT_COUNT:-1000}"
HOT_ACCOUNTS="${EXP4_HOT_ACCOUNTS:-100}"
BATCH_SIZE="${EXP4_BATCH_SIZE:-2}"
AUDIT_SIZE="${EXP4_AUDIT_SIZE:-8}"
MAX_OUTSTANDING="${EXP4_MAX_OUTSTANDING:-10000}"
MAX_SOCKETS="${EXP4_MAX_SOCKETS:-10000}"

mkdir -p results

run_case() {
  local method="$1"
  local port="$2"
  local rate="$3"
  local prefix="results/exp4-${POLICY_LABEL}-w3-${method}-hot${HOT_ACCOUNTS}-${rate}tps"

  echo "=== EXP4 ${POLICY_LABEL} W3 ${method} hot=${HOT_ACCOUNTS} rate=${rate} TPS ==="
  curl -fsS -X POST "http://127.0.0.1:${port}/reset" >/dev/null
  node tools/workload-loadgen.js \
    --url "http://127.0.0.1:${port}/submit" \
    --clients "$CLIENTS" \
    --tps "$rate" \
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

for rate in $RATES; do
  run_case "traditional-lock" "${TRAD_LOCK_DISPATCHER_PORT:-8082}" "$rate"
  run_case "pa-vscd" "${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}" "$rate"
done
