#!/usr/bin/env bash
set -euo pipefail

PORT="${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}"
ADMIN_URL="${SC_ADMIN_URL:-http://127.0.0.1:8090}"
RESULT_ROOT="${CAPS_OVERHEAD_RESULT_ROOT:-results/caps-overhead}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WORKLOAD="${CAPS_OVERHEAD_WORKLOAD:-sc-w3}"
RATES="${CAPS_OVERHEAD_RATES:-300 500}"
REPEATS="${CAPS_OVERHEAD_REPEATS:-10}"
DURATION="${CAPS_OVERHEAD_DURATION:-20}"
CLIENTS="${CAPS_OVERHEAD_CLIENTS:-100}"
WAREHOUSES="${SC_WAREHOUSES:-20}"
SKUS="${SC_SKUS:-50}"
HOT_SKUS="${SC_HOT_SKUS:-10}"
INITIAL_QUANTITY="${SC_INITIAL_QUANTITY:-1000000}"
BATCH_COUNT="${SC_BATCH_COUNT:-10000}"
BATCH_SIZE="${SC_BATCH_SIZE:-4}"
AUDIT_SIZE="${SC_AUDIT_SIZE:-8}"

admin_payload() {
  printf '{"warehouseCount":%s,"skuCount":%s,"initialQuantity":%s,"batchCount":%s}' \
    "$WAREHOUSES" "$SKUS" "$INITIAL_QUANTITY" "$BATCH_COUNT"
}

admin_call() {
  local operation="$1"
  local output="$2"
  curl -fsS -X POST "${ADMIN_URL}/${operation}" \
    -H 'content-type: application/json' \
    --data "$(admin_payload)" > "$output"
}

wait_for_idle() {
  for _ in $(seq 1 600); do
    if curl -fsS "http://127.0.0.1:${PORT}/metrics" |
      jq -e '((.active // 0) == 0) and (((.queueLength // .waiting) // 0) == 0)' >/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  echo "CAPS scheduler did not become idle on port ${PORT}" >&2
  return 1
}

mkdir -p "$RESULT_ROOT"
curl -fsS "${ADMIN_URL}/health" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null

for rate in $RATES; do
  group_dir="${RESULT_ROOT}/${WORKLOAD}/${rate}tps"
  mkdir -p "$group_dir"
  admin_call init "${group_dir}/group-initialization.json"

  for repeat in $(seq 1 "$REPEATS"); do
    run_dir="${group_dir}/repeat-${repeat}"
    mkdir -p "$run_dir"

    if [[ -s "${run_dir}/client.json" && -s "${run_dir}/scheduler-metrics.json" && -s "${run_dir}/invariant-check.json" ]] &&
      node -e "const x=require(process.argv[1]); process.exit(x.valid===true?0:1)" "${run_dir}/invariant-check.json"; then
      echo "=== skip completed CAPS overhead ${WORKLOAD} ${rate} tx/s repeat ${repeat}/${REPEATS} ==="
      continue
    fi

    echo "=== CAPS overhead ${WORKLOAD} ${rate} tx/s repeat ${repeat}/${REPEATS} ==="
    wait_for_idle
    curl -fsS -X POST "http://127.0.0.1:${PORT}/reset" > "${run_dir}/scheduler-reset.json"

    node "${SCRIPT_DIR}/supply-chain-loadgen.js" \
      --url "http://127.0.0.1:${PORT}/submit" \
      --clients "$CLIENTS" \
      --tps "$rate" \
      --duration "$DURATION" \
      --workload "$WORKLOAD" \
      --warehouseCount "$WAREHOUSES" \
      --skuCount "$SKUS" \
      --hotSkuCount "$HOT_SKUS" \
      --batchCount "$BATCH_COUNT" \
      --batchSize "$BATCH_SIZE" \
      --auditSize "$AUDIT_SIZE" \
      --out "${run_dir}/client.json" \
      > "${run_dir}/client.log"

    wait_for_idle
    curl -fsS "http://127.0.0.1:${PORT}/metrics" > "${run_dir}/scheduler-metrics.json"
    admin_call verify "${run_dir}/invariant-check.json"
  done
done

node "${SCRIPT_DIR}/summarize-caps-overhead.js" \
  --root "$RESULT_ROOT" \
  --out "${RESULT_ROOT}/caps-overhead-summary"
