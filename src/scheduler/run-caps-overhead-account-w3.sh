#!/usr/bin/env bash
set -euo pipefail

PORT="${VLL_SCD_ADAPTIVE_DISPATCHER_PORT:-8086}"
RESULT_ROOT="${CAPS_OVERHEAD_RESULT_ROOT:-results/caps-overhead-account-w3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RATES="${CAPS_OVERHEAD_RATES:-300 500}"
REPEATS="${CAPS_OVERHEAD_REPEATS:-10}"
DURATION="${CAPS_OVERHEAD_DURATION:-20}"
CLIENTS="${CAPS_OVERHEAD_CLIENTS:-100}"
BATCH_SIZE="${CAPS_OVERHEAD_BATCH_SIZE:-2}"
AUDIT_SIZE="${CAPS_OVERHEAD_AUDIT_SIZE:-8}"
ACCOUNT_COUNT="${CAPS_OVERHEAD_ACCOUNT_COUNT:-1000}"
HOT_ACCOUNT_COUNT="${CAPS_OVERHEAD_HOT_ACCOUNT_COUNT:-100}"

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
curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null

for rate in $RATES; do
  group_dir="${RESULT_ROOT}/account-w3/${rate}tps"
  mkdir -p "$group_dir"

  for repeat in $(seq 1 "$REPEATS"); do
    run_dir="${group_dir}/repeat-${repeat}"
    mkdir -p "$run_dir"

    if [[ -s "${run_dir}/client.json" && -s "${run_dir}/scheduler-metrics.json" ]]; then
      echo "=== skip completed CAPS overhead account-w3 ${rate} tx/s repeat ${repeat}/${REPEATS} ==="
      continue
    fi

    echo "=== CAPS overhead account-w3 ${rate} tx/s repeat ${repeat}/${REPEATS} ==="
    wait_for_idle
    curl -fsS -X POST "http://127.0.0.1:${PORT}/reset" > "${run_dir}/scheduler-reset.json"

    node "${SCRIPT_DIR}/workload-loadgen.js" \
      --url "http://127.0.0.1:${PORT}/submit" \
      --clients "$CLIENTS" \
      --tps "$rate" \
      --duration "$DURATION" \
      --workload w3 \
      --accountCount "$ACCOUNT_COUNT" \
      --hotAccountCount "$HOT_ACCOUNT_COUNT" \
      --batchSize "$BATCH_SIZE" \
      --auditSize "$AUDIT_SIZE" \
      --maxOutstanding 10000 \
      --maxSockets 10000 \
      --out "${run_dir}/client.json" \
      > "${run_dir}/client.log"

    wait_for_idle
    curl -fsS "http://127.0.0.1:${PORT}/metrics" > "${run_dir}/scheduler-metrics.json"
  done
done

node "${SCRIPT_DIR}/summarize-caps-overhead.js" \
  --root "$RESULT_ROOT" \
  --out "${RESULT_ROOT}/caps-overhead-account-w3-summary"
