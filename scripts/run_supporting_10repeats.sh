#!/usr/bin/env bash
set -euo pipefail

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/rd/fabric-exp/fabric-samples/bin

ROOT="${FABRIC_EXP_ROOT:-/home/rd/fabric-exp/caliper-vll}"
OUT_ROOT="${SUPPORTING_OUT_ROOT:-/mnt/c/Users/94847/Documents/paper_2026/results/supporting_10repeats_20260626}"
REPEATS="${SUPPORTING_REPEATS:-10}"
DURATION="${SUPPORTING_DURATION:-20}"
CLIENTS="${SUPPORTING_CLIENTS:-100}"
ACCOUNT_COUNT="${SUPPORTING_ACCOUNT_COUNT:-1000}"
BATCH_SIZE="${SUPPORTING_BATCH_SIZE:-2}"
AUDIT_SIZE="${SUPPORTING_AUDIT_SIZE:-8}"
MAX_OUTSTANDING="${SUPPORTING_MAX_OUTSTANDING:-10000}"
MAX_SOCKETS="${SUPPORTING_MAX_SOCKETS:-10000}"
COOLDOWN_SECONDS="${SUPPORTING_COOLDOWN_SECONDS:-8}"
NODE_BIN="${NODE_BIN:-/usr/bin/node}"
EXPERIMENTS="${SUPPORTING_EXPERIMENTS:-2 3 4 5 6}"

mkdir -p "${OUT_ROOT}/logs" "${OUT_ROOT}/pids"
cd "$ROOT"

method_port() {
  case "$1" in
    traditional-lock) echo 8082 ;;
    pacc-dabs) echo 8084 ;;
    pa-vscd) echo 8086 ;;
    pacc-lpaac) echo 8087 ;;
    ed-mvcc) echo 8087 ;;
    drt) echo 8088 ;;
    *) echo "unknown method: $1" >&2; return 1 ;;
  esac
}

method_script() {
  case "$1" in
    traditional-lock) echo gateway/traditional-lock-dispatcher.js ;;
    pacc-dabs) echo gateway/vll-scd-dispatcher.js ;;
    pa-vscd) echo gateway/vll-scd-adaptive-dispatcher.js ;;
    pacc-lpaac) echo gateway/pacc-lpaac-dispatcher.js ;;
    ed-mvcc) echo gateway/ed-mvcc-reimpl-dispatcher.js ;;
    drt) echo gateway/drt-reimpl-dispatcher.js ;;
    *) echo "unknown method: $1" >&2; return 1 ;;
  esac
}

health_ok() {
  local port="$1"
  curl -fsS --max-time 2 "http://127.0.0.1:${port}/health" >/dev/null 2>&1
}

start_method() {
  local method="$1"
  local port script pid_file log_file
  port="$(method_port "$method")"
  script="$(method_script "$method")"
  pid_file="${OUT_ROOT}/pids/${method}.pid"
  log_file="${OUT_ROOT}/logs/${method}-dispatcher.log"

  if health_ok "$port"; then
    echo "[$(date '+%F %T')] ${method} already healthy on ${port}; reusing it."
    return
  fi

  echo "[$(date '+%F %T')] starting ${method} on ${port}"
  setsid "$NODE_BIN" "$script" > "$log_file" 2>&1 < /dev/null &
  echo "$!" > "$pid_file"

  for _ in $(seq 1 30); do
    if health_ok "$port"; then
      echo "[$(date '+%F %T')] ${method} healthy on ${port}"
      return
    fi
    sleep 1
  done

  echo "dispatcher failed to start: ${method}" >&2
  tail -80 "$log_file" >&2 || true
  return 1
}

stop_method_if_started() {
  local method="$1"
  local pid_file="${OUT_ROOT}/pids/${method}.pid"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[$(date '+%F %T')] stopping ${method} pid=${pid}"
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$pid_file"
  fi
}

run_w3_case() {
  local exp="$1"
  local scenario="$2"
  local method="$3"
  local rate="$4"
  local hot="$5"
  local repeat="$6"
  local port prefix

  port="$(method_port "$method")"
  prefix="${OUT_ROOT}/${exp}/${scenario}/exp${exp}-${scenario}-w3-${method}-hot${hot}-${rate}tps-rep$(printf '%02d' "$repeat")"
  mkdir -p "$(dirname "$prefix")"

  if [[ -s "${prefix}-client.json" && -s "${prefix}-metrics.json" ]]; then
    echo "[$(date '+%F %T')] SKIP exp${exp} ${scenario} ${method} hot=${hot} rate=${rate} rep=${repeat}"
    return
  fi

  echo "[$(date '+%F %T')] RUN exp${exp} ${scenario} ${method} hot=${hot} rate=${rate} rep=${repeat}"
  curl -fsS -X POST "http://127.0.0.1:${port}/reset" >/dev/null
  "$NODE_BIN" tools/workload-loadgen.js \
    --url "http://127.0.0.1:${port}/submit" \
    --clients "$CLIENTS" \
    --tps "$rate" \
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
  sleep "$COOLDOWN_SECONDS"
}

set_policy() {
  local label="$1"
  local channel="${FABRIC_CHANNEL:-vllchannel}"
  local cc_name="${FABRIC_CHAINCODE:-hotkey}"
  local package_id="${FABRIC_CHAINCODE_PACKAGE_ID:-hotkey_1.2:4f3db01660894ecfa8f9d846fe34fc7b5503dd0403dcfdc18b127d970b4d9d2c}"
  local test_network="${TEST_NETWORK_HOME:-/home/rd/fabric-exp/fabric-samples/test-network}"
  local orderer_ca="${test_network}/organizations/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem"
  local org1_ca="${test_network}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem"
  local org2_ca="${test_network}/organizations/peerOrganizations/org2.example.com/tlsca/tlsca.org2.example.com-cert.pem"
  local current_seq next_seq version policy_args=()

  export FABRIC_CFG_PATH=/home/rd/fabric-exp/fabric-samples/config
  export CORE_PEER_TLS_ENABLED=true
  export CORE_PEER_LOCALMSPID=Org1MSP
  export CORE_PEER_TLS_ROOTCERT_FILE="$org1_ca"
  export CORE_PEER_MSPCONFIGPATH="${test_network}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
  export CORE_PEER_ADDRESS=localhost:7051

  current_seq="$(peer lifecycle chaincode querycommitted -C "$channel" -n "$cc_name" --output json | jq -r '.sequence')"
  next_seq="$((current_seq + 1))"

  case "$label" in
    default-policy)
      version="1.2-default-r${next_seq}"
      policy_args=()
      ;;
    or-policy)
      version="1.2-or-r${next_seq}"
      policy_args=(--signature-policy "OR('Org1MSP.peer','Org2MSP.peer')")
      ;;
    *) echo "unknown policy label: $label" >&2; return 1 ;;
  esac

  approve_org() {
    local org="$1"
    if [[ "$org" == "org1" ]]; then
      export CORE_PEER_LOCALMSPID=Org1MSP
      export CORE_PEER_TLS_ROOTCERT_FILE="$org1_ca"
      export CORE_PEER_MSPCONFIGPATH="${test_network}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
      export CORE_PEER_ADDRESS=localhost:7051
    else
      export CORE_PEER_LOCALMSPID=Org2MSP
      export CORE_PEER_TLS_ROOTCERT_FILE="$org2_ca"
      export CORE_PEER_MSPCONFIGPATH="${test_network}/organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp"
      export CORE_PEER_ADDRESS=localhost:9051
    fi
    peer lifecycle chaincode approveformyorg \
      -o localhost:7050 \
      --ordererTLSHostnameOverride orderer.example.com \
      --channelID "$channel" \
      --name "$cc_name" \
      --version "$version" \
      --package-id "$package_id" \
      --sequence "$next_seq" \
      "${policy_args[@]}" \
      --tls \
      --cafile "$orderer_ca"
  }

  echo "[$(date '+%F %T')] switching ${cc_name} to ${label}: sequence ${current_seq} -> ${next_seq}"
  approve_org org1
  approve_org org2

  export CORE_PEER_LOCALMSPID=Org1MSP
  export CORE_PEER_TLS_ROOTCERT_FILE="$org1_ca"
  export CORE_PEER_MSPCONFIGPATH="${test_network}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
  export CORE_PEER_ADDRESS=localhost:7051

  peer lifecycle chaincode checkcommitreadiness \
    --channelID "$channel" \
    --name "$cc_name" \
    --version "$version" \
    --sequence "$next_seq" \
    "${policy_args[@]}" \
    --tls \
    --cafile "$orderer_ca" \
    --output json

  peer lifecycle chaincode commit \
    -o localhost:7050 \
    --ordererTLSHostnameOverride orderer.example.com \
    --channelID "$channel" \
    --name "$cc_name" \
    --version "$version" \
    --sequence "$next_seq" \
    "${policy_args[@]}" \
    --tls \
    --cafile "$orderer_ca" \
    --peerAddresses localhost:7051 \
    --tlsRootCertFiles "$org1_ca" \
    --peerAddresses localhost:9051 \
    --tlsRootCertFiles "$org2_ca"

  peer lifecycle chaincode querycommitted -C "$channel" -n "$cc_name" --output json
  sleep 5
}

set_batch_params() {
  local label="$1"
  local desired_timeout desired_count
  case "$label" in
    batch10-timeout2s) desired_timeout=2s; desired_count=10 ;;
    batch5-timeout1s) desired_timeout=1s; desired_count=5 ;;
    batch50-timeout2s) desired_timeout=2s; desired_count=50 ;;
    *) echo "unknown batch label: $label" >&2; return 1 ;;
  esac

  local current_file current_timeout current_count
  current_file="${OUT_ROOT}/logs/current-batch-${label}.txt"
  bash tools/get-channel-batch-params.sh "${OUT_ROOT}/tmp/batch-check-${label}" > "$current_file"
  current_timeout="$(grep '^BatchTimeout=' "$current_file" | cut -d= -f2)"
  current_count="$(grep '^MaxMessageCount=' "$current_file" | cut -d= -f2)"

  if [[ "$current_timeout" == "$desired_timeout" && "$current_count" == "$desired_count" ]]; then
    echo "[$(date '+%F %T')] channel already uses ${label}; skipping config update."
  else
    BATCH_TIMEOUT="$desired_timeout" MAX_MESSAGE_COUNT="$desired_count" bash tools/set-channel-batch-params.sh
  fi
  sleep 8
}

echo "started_at=$(date --iso-8601=seconds)" | tee "${OUT_ROOT}/run-info.txt"
echo "repeats=${REPEATS}" | tee -a "${OUT_ROOT}/run-info.txt"
echo "duration=${DURATION}" | tee -a "${OUT_ROOT}/run-info.txt"

want_exp() {
  local exp="$1"
  for selected in $EXPERIMENTS; do
    [[ "$selected" == "$exp" ]] && return 0
  done
  return 1
}

# Experiment 2: contention sensitivity.
if want_exp 2; then
  for method in traditional-lock pa-vscd; do
    start_method "$method"
    for hot in 20 50 100 200 500; do
      for rep in $(seq 1 "$REPEATS"); do
        run_w3_case 2 "contention" "$method" 300 "$hot" "$rep"
      done
    done
    stop_method_if_started "$method"
  done
fi

# Experiment 3: module ablation.
if want_exp 3; then
  for method in traditional-lock pacc-dabs pacc-lpaac pa-vscd; do
    start_method "$method"
    for rate in 300 500; do
      for rep in $(seq 1 "$REPEATS"); do
        run_w3_case 3 "ablation" "$method" "$rate" 100 "$rep"
      done
    done
    stop_method_if_started "$method"
  done
fi

# Experiment 4: endorsement-policy robustness.
if want_exp 4; then
  for policy in default-policy or-policy; do
    set_policy "$policy"
    for method in traditional-lock pa-vscd; do
      start_method "$method"
      for rate in 300 500; do
        for rep in $(seq 1 "$REPEATS"); do
          run_w3_case 4 "$policy" "$method" "$rate" 100 "$rep"
        done
      done
      stop_method_if_started "$method"
    done
  done
  set_policy default-policy
fi

# Experiment 5: Fabric block-cutting robustness.
if want_exp 5; then
  for params in batch10-timeout2s batch5-timeout1s batch50-timeout2s; do
    set_batch_params "$params"
    for method in traditional-lock pa-vscd; do
      start_method "$method"
      for rate in 300 500; do
        for rep in $(seq 1 "$REPEATS"); do
          run_w3_case 5 "$params" "$method" "$rate" 100 "$rep"
        done
      done
      stop_method_if_started "$method"
    done
  done
  set_batch_params batch10-timeout2s
fi

# Experiment 6: related-work-inspired baselines.
if want_exp 6; then
  for method in traditional-lock ed-mvcc drt pa-vscd; do
    start_method "$method"
    for rate in 300 500; do
      for rep in $(seq 1 "$REPEATS"); do
        run_w3_case 6 "related-baselines" "$method" "$rate" 100 "$rep"
      done
    done
    stop_method_if_started "$method"
  done
fi

echo "finished_at=$(date --iso-8601=seconds)" | tee -a "${OUT_ROOT}/run-info.txt"
