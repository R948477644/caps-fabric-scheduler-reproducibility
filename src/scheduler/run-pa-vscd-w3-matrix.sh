#!/usr/bin/env bash
set -euo pipefail

RATES="${VLL_SCD_ADAPTIVE_RATES:-100 150 200 300 400 500}"
DURATION="${VLL_SCD_ADAPTIVE_DURATION:-20}"
CLIENTS="${VLL_SCD_ADAPTIVE_CLIENTS:-100}"
BATCH_SIZE="${VLL_SCD_ADAPTIVE_BATCH_SIZE:-2}"
AUDIT_SIZE="${VLL_SCD_ADAPTIVE_AUDIT_SIZE:-8}"
PORT="${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}"

mkdir -p results

for rate in $RATES; do
  prefix="results/w3-vll-scd-adaptive-100clients-b${BATCH_SIZE}-${rate}tps"
  echo "=== W3 VLL+SCD-Adaptive ${rate} TPS batch=${BATCH_SIZE} ==="
  curl -fsS -X POST "http://127.0.0.1:${PORT}/reset" >/dev/null
  node tools/workload-loadgen.js \
    --url "http://127.0.0.1:${PORT}/submit" \
    --clients "$CLIENTS" \
    --tps "$rate" \
    --duration "$DURATION" \
    --workload w3 \
    --batchSize "$BATCH_SIZE" \
    --auditSize "$AUDIT_SIZE" \
    --maxOutstanding 10000 \
    --maxSockets 10000 \
    --out "${prefix}-client.json" | tee "${prefix}-client.log"
  curl -fsS "http://127.0.0.1:${PORT}/metrics" | tee "${prefix}-metrics.json"
  echo
done
