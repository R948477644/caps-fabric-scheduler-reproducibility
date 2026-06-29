#!/usr/bin/env bash
set -euo pipefail

SCHEDULERS="${SC_SCHEDULERS:-native traditional-lock caps ed-mvcc}"
WORKLOADS="${SC_WORKLOADS:-sc-w1 sc-w2 sc-w3}"
RATES="${SC_RATES:-300 500}"
REPEATS="${SC_REPEATS:-10}"
DURATION="${SC_DURATION:-20}"
CLIENTS="${SC_CLIENTS:-100}"
WAREHOUSES="${SC_WAREHOUSES:-20}"
SKUS="${SC_SKUS:-50}"
HOT_SKUS="${SC_HOT_SKUS:-10}"
INITIAL_QUANTITY="${SC_INITIAL_QUANTITY:-1000000}"
BATCH_COUNT="${SC_BATCH_COUNT:-10000}"
BATCH_SIZE="${SC_BATCH_SIZE:-4}"
AUDIT_SIZE="${SC_AUDIT_SIZE:-8}"
RESULT_ROOT="${SC_RESULT_ROOT:-results/supply-chain}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESET_EACH_REPEAT="${SC_RESET_EACH_REPEAT:-0}"
ADMIN_URL="${SC_ADMIN_URL:-http://127.0.0.1:8090}"

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
  local port="$1"
  for _ in $(seq 1 600); do
    if curl -fsS "http://127.0.0.1:${port}/metrics" |
      jq -e '((.active // 0) == 0) and (((.queueLength // .waiting) // 0) == 0)' >/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  echo "scheduler on port ${port} did not become idle" >&2
  return 1
}

port_for_scheduler() {
  case "$1" in
    native) echo "${NATIVE_FABRIC_GATEWAY_PORT:-8089}" ;;
    traditional-lock) echo "${TRAD_LOCK_DISPATCHER_PORT:-8082}" ;;
    caps) echo "${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}" ;;
    ed-mvcc) echo "${ED_MVCC_DISPATCHER_PORT:-8087}" ;;
    drt) echo "${DRT_DISPATCHER_PORT:-8088}" ;;
    *) echo "unknown scheduler: $1" >&2; return 1 ;;
  esac
}

mkdir -p "$RESULT_ROOT"
curl -fsS "${ADMIN_URL}/health" >/dev/null

for workload in $WORKLOADS; do
  for scheduler in $SCHEDULERS; do
    port="$(port_for_scheduler "$scheduler")"
    curl -fsS "http://127.0.0.1:${port}/health" >/dev/null
    for rate in $RATES; do
      group_dir="${RESULT_ROOT}/${workload}/${scheduler}/${rate}tps"
      mkdir -p "$group_dir"
      if [[ "$RESET_EACH_REPEAT" != "1" ]]; then
        admin_call init "${group_dir}/group-initialization.json"
      fi
      for repeat in $(seq 1 "$REPEATS"); do
        run_dir="${RESULT_ROOT}/${workload}/${scheduler}/${rate}tps/repeat-${repeat}"
        mkdir -p "$run_dir"
        if [[ -s "${run_dir}/client.json" && -s "${run_dir}/scheduler-metrics.json" && -s "${run_dir}/invariant-check.json" ]] &&
          node -e "const x=require(process.argv[1]); process.exit(x.valid===true?0:1)" "${run_dir}/invariant-check.json"; then
          echo "=== skip completed ${workload} ${scheduler} ${rate} tx/s repeat ${repeat}/${REPEATS} ==="
          continue
        fi
        echo "=== ${workload} ${scheduler} ${rate} tx/s repeat ${repeat}/${REPEATS} ==="

        if [[ "$RESET_EACH_REPEAT" == "1" ]]; then
          admin_call init "${run_dir}/initialization.json"
        fi

        wait_for_idle "$port"
        curl -fsS -X POST "http://127.0.0.1:${port}/reset" > "${run_dir}/scheduler-reset.json"

        node "${SCRIPT_DIR}/supply-chain-loadgen.js" \
          --url "http://127.0.0.1:${port}/submit" \
          --clients "$CLIENTS" \
          --tps "$rate" \
          --duration "$DURATION" \
          --workload "$workload" \
          --warehouseCount "$WAREHOUSES" \
          --skuCount "$SKUS" \
          --hotSkuCount "$HOT_SKUS" \
          --batchCount "$BATCH_COUNT" \
          --batchSize "$BATCH_SIZE" \
          --auditSize "$AUDIT_SIZE" \
          --out "${run_dir}/client.json" \
          > "${run_dir}/client.log"

        wait_for_idle "$port"
        curl -fsS "http://127.0.0.1:${port}/metrics" > "${run_dir}/scheduler-metrics.json"

        admin_call verify "${run_dir}/invariant-check.json"
      done
    done
  done
done

node "${SCRIPT_DIR}/summarize-supply-chain.js" \
  --root "$RESULT_ROOT" \
  --out "${RESULT_ROOT}/summary"
