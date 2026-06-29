#!/usr/bin/env bash
set -euo pipefail

RATE="${EXP2_RATE:-300}"
DURATION="${EXP2_DURATION:-20}"
CLIENTS="${EXP2_CLIENTS:-100}"
ACCOUNT_COUNT="${EXP2_ACCOUNT_COUNT:-1000}"
HOT_ACCOUNTS="${EXP2_HOT_ACCOUNTS:-20 50 100 200 500}"
BATCH_SIZE="${EXP2_BATCH_SIZE:-2}"
AUDIT_SIZE="${EXP2_AUDIT_SIZE:-8}"
MAX_OUTSTANDING="${EXP2_MAX_OUTSTANDING:-10000}"
MAX_SOCKETS="${EXP2_MAX_SOCKETS:-10000}"

mkdir -p results

run_case() {
  local scheduler="$1"
  local port="$2"
  local hot="$3"
  local prefix="results/exp2-w3-${scheduler}-hot${hot}-${RATE}tps"

  echo "=== EXP2 W3 ${scheduler} hot=${hot} rate=${RATE} TPS ==="
  curl -fsS -X POST "http://127.0.0.1:${port}/reset" >/dev/null
  node tools/workload-loadgen.js \
    --url "http://127.0.0.1:${port}/submit" \
    --clients "$CLIENTS" \
    --tps "$RATE" \
    --duration "$DURATION" \
    --accountCount "$ACCOUNT_COUNT" \
    --hotAccountCount "$hot" \
    --workload w3 \
    --batchSize "$BATCH_SIZE" \
    --auditSize "$AUDIT_SIZE" \
    --maxOutstanding "$MAX_OUTSTANDING" \
    --maxSockets "$MAX_SOCKETS" \
    --out "${prefix}-client.json" | tee "${prefix}-client.log"
  curl -fsS "http://127.0.0.1:${port}/metrics" | tee "${prefix}-metrics.json"
  echo
}

for hot in $HOT_ACCOUNTS; do
  run_case "traditional-lock" "${TRAD_LOCK_DISPATCHER_PORT:-8082}" "$hot"
  run_case "pa-vscd" "${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}" "$hot"
done
