#!/usr/bin/env bash
set -euo pipefail

PORT="${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}"
RESULT_ROOT="${CAPS_OVERHEAD_RESULT_ROOT:-results/caps-overhead-sensitivity}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NODE_PATH_VALUE="${NODE_PATH:-/home/rd/fabric-exp/caliper-vll/node_modules}"

RATE="${CAPS_OVERHEAD_RATE:-500}"
REPEATS="${CAPS_OVERHEAD_REPEATS:-5}"
DURATION="${CAPS_OVERHEAD_DURATION:-20}"
CLIENTS="${CAPS_OVERHEAD_CLIENTS:-100}"
BATCH_SIZE="${CAPS_OVERHEAD_BATCH_SIZE:-2}"
AUDIT_SIZE="${CAPS_OVERHEAD_AUDIT_SIZE:-8}"
ACCOUNT_COUNT="${CAPS_OVERHEAD_ACCOUNT_COUNT:-1000}"

stop_caps() {
  local pids
  pids="$(pgrep -f 'scripts/pa-vscd-dispatcher.js' || true)"
  if [[ -n "$pids" ]]; then
    kill $pids || true
    sleep 2
  fi
}

start_caps() {
  local run_dir="$1"
  local max_active="$2"
  local window="$3"
  local max_queue="$4"
  local la_queue="$5"
  local hot_pending="$6"
  mkdir -p "$run_dir"
  stop_caps
  (
    cd "$PROJECT_ROOT"
    NODE_PATH="$NODE_PATH_VALUE" \
    VLL_SCD_MAX_ACTIVE="$max_active" \
    VLL_SCD_WINDOW="$window" \
    VLL_SCD_ADAPTIVE_MAX_QUEUE="$max_queue" \
    VLL_SCD_ADAPTIVE_LA_MAX_QUEUE="$la_queue" \
    VLL_SCD_LA_MAX_PENDING_PER_KEY="$hot_pending" \
    setsid node scripts/pa-vscd-dispatcher.js > "${run_dir}/caps-dispatcher.log" 2>&1 < /dev/null &
  )
  for _ in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:${PORT}/health" > "${run_dir}/health.json" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
  done
  echo "failed to start CAPS dispatcher" >&2
  return 1
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

run_config() {
  local name="$1"
  local max_active="$2"
  local window="$3"
  local max_queue="$4"
  local la_queue="$5"
  local hot_pending="$6"
  local hot_accounts="$7"
  local group_dir="${RESULT_ROOT}/${name}"
  mkdir -p "$group_dir"

  start_caps "$group_dir" "$max_active" "$window" "$max_queue" "$la_queue" "$hot_pending"
  cat > "${group_dir}/config.json" <<JSON
{"name":"${name}","rate":${RATE},"repeats":${REPEATS},"duration":${DURATION},"clients":${CLIENTS},"maxActive":${max_active},"scdWindow":${window},"maxQueue":${max_queue},"laMaxQueue":${la_queue},"maxPendingPerKey":${hot_pending},"hotAccountCount":${hot_accounts}}
JSON

  for repeat in $(seq 1 "$REPEATS"); do
    local run_dir="${group_dir}/repeat-${repeat}"
    mkdir -p "$run_dir"
    if [[ -s "${run_dir}/client.json" && -s "${run_dir}/scheduler-metrics.json" ]]; then
      echo "=== skip completed ${name} repeat ${repeat}/${REPEATS} ==="
      continue
    fi
    echo "=== CAPS overhead sensitivity ${name} repeat ${repeat}/${REPEATS} ==="
    wait_for_idle
    curl -fsS -X POST "http://127.0.0.1:${PORT}/reset" > "${run_dir}/scheduler-reset.json"
    node "${SCRIPT_DIR}/workload-loadgen.js" \
      --url "http://127.0.0.1:${PORT}/submit" \
      --clients "$CLIENTS" \
      --tps "$RATE" \
      --duration "$DURATION" \
      --workload w3 \
      --accountCount "$ACCOUNT_COUNT" \
      --hotAccountCount "$hot_accounts" \
      --batchSize "$BATCH_SIZE" \
      --auditSize "$AUDIT_SIZE" \
      --maxOutstanding 10000 \
      --maxSockets 10000 \
      --out "${run_dir}/client.json" \
      > "${run_dir}/client.log"
    wait_for_idle
    curl -fsS "http://127.0.0.1:${PORT}/metrics" > "${run_dir}/scheduler-metrics.json"
  done
}

mkdir -p "$RESULT_ROOT"

run_config "active16_window256_hot100" 16 256 500 128 8 100
run_config "active32_window64_hot100" 32 64 500 128 8 100
run_config "active32_window256_hot100" 32 256 500 128 8 100
run_config "active32_window512_hot100" 32 512 500 128 8 100
run_config "active64_window256_hot100" 64 256 500 128 8 100
run_config "active32_window256_hot20" 32 256 500 128 8 20

stop_caps

node "${SCRIPT_DIR}/summarize-caps-overhead-sensitivity.js" \
  --root "$RESULT_ROOT" \
  --out "${RESULT_ROOT}/caps-overhead-sensitivity-summary"
