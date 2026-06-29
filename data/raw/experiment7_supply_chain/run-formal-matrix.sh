#!/usr/bin/env bash
set -euo pipefail

cd /home/rd/fabric-exp/caliper-vll

RESULT_ROOT="/home/rd/fabric-exp/caliper-vll/results/supply-chain-formal-20260625"
LOG_DIR="/home/rd/fabric-exp/caliper-vll/logs"
mkdir -p "$RESULT_ROOT" "$LOG_DIR"

export SC_REPEATS=10
export SC_RATES="300 500"
export SC_DURATION=20
export SC_CLIENTS=100
export SC_WORKLOADS="sc-w1 sc-w2 sc-w3"
export SC_SCHEDULERS="native traditional-lock ed-mvcc caps"
export SC_WAREHOUSES=20
export SC_SKUS=50
export SC_HOT_SKUS=10
export SC_BATCH_COUNT=100
export SC_BATCH_SIZE=4
export SC_AUDIT_SIZE=8
export SC_INITIAL_QUANTITY=1000000
export SC_RESET_EACH_REPEAT=0
export SC_RESULT_ROOT="$RESULT_ROOT"
export SC_ADMIN_URL="http://127.0.0.1:8090"

date --iso-8601=seconds > "${RESULT_ROOT}/started-at.txt"
bash tools/run-supply-chain-matrix.sh
date --iso-8601=seconds > "${RESULT_ROOT}/finished-at.txt"
