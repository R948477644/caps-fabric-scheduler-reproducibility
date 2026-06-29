#!/usr/bin/env bash
set -euo pipefail

SCHEDULER="${WORKLOAD_SCHEDULER:-vll-scd}"
WORKLOAD="${WORKLOAD_NAME:-w2}"
RATES="${WORKLOAD_RATES:-50 100 200 300 500}"
DURATION="${WORKLOAD_DURATION:-20}"
CLIENTS="${WORKLOAD_CLIENTS:-100}"
BATCH_SIZE="${WORKLOAD_BATCH_SIZE:-4}"
AUDIT_SIZE="${WORKLOAD_AUDIT_SIZE:-8}"
HOT_ACCOUNTS="${WORKLOAD_HOT_ACCOUNTS:-100}"
ACCOUNT_COUNT="${WORKLOAD_ACCOUNT_COUNT:-1000}"
MAX_OUTSTANDING="${WORKLOAD_MAX_OUTSTANDING:-10000}"
MAX_SOCKETS="${WORKLOAD_MAX_SOCKETS:-10000}"

case "$SCHEDULER" in
  traditional-lock)
    PORT="${TRAD_LOCK_DISPATCHER_PORT:-8082}"
    ;;
  ed-mvcc)
    PORT="${ED_MVCC_DISPATCHER_PORT:-8087}"
    ;;
  drt)
    PORT="${DRT_DISPATCHER_PORT:-8088}"
    ;;
  vll-only)
    PORT="${VLL_ONLY_DISPATCHER_PORT:-8083}"
    ;;
  vll-scd)
    PORT="${VLL_SCD_DISPATCHER_PORT:-8084}"
    ;;
  *)
    echo "unknown scheduler: $SCHEDULER" >&2
    exit 1
    ;;
esac

mkdir -p results

for rate in $RATES; do
  prefix="results/${WORKLOAD}-${SCHEDULER}-100clients-b${BATCH_SIZE}-${rate}tps"
  echo "=== ${WORKLOAD} ${SCHEDULER} ${rate} TPS batch=${BATCH_SIZE} ==="
  curl -fsS -X POST "http://127.0.0.1:${PORT}/reset" >/dev/null
  node tools/workload-loadgen.js \
    --url "http://127.0.0.1:${PORT}/submit" \
    --clients "$CLIENTS" \
    --tps "$rate" \
    --duration "$DURATION" \
    --accountCount "$ACCOUNT_COUNT" \
    --hotAccountCount "$HOT_ACCOUNTS" \
    --workload "$WORKLOAD" \
    --batchSize "$BATCH_SIZE" \
    --auditSize "$AUDIT_SIZE" \
    --maxOutstanding "$MAX_OUTSTANDING" \
    --maxSockets "$MAX_SOCKETS" \
    --out "${prefix}-client.json" | tee "${prefix}-client.log"
  curl -fsS "http://127.0.0.1:${PORT}/metrics" | tee "${prefix}-metrics.json"
  echo
done
