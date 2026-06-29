# Experiment 7: Supply-Chain Transaction Validation

This experiment validates CAPS with application-shaped supply-chain transactions rather than account-transfer labels.

## Research question

Can CAPS preserve useful ledger progress and bounded latency when multiple organizations concurrently transfer warehouse inventory, distribute popular SKUs, update batch states, and audit inventory?

## Fabric deployment

- Hyperledger Fabric 2.5.15
- 4 peers: two peers in each of two organizations
- 1 Raft orderer
- channel: `vllchannel`
- chaincode: `hotkey`, supply-chain extension version 2.1, sequence 7
- 100 logical clients

## Chaincode operations

- `TransferInventory(source,destination,sku,quantity)`
- `BatchTransferInventory(operations)`
- `UpdateBatchStatus(batchId,nextStatus)`
- `AuditInventory(inventoryKeys)`

Inventory keys use `inv:{warehouse}:{sku}`. Batch keys use `batch:{batchId}`.

## Workloads

| Workload | Operation mix and key distribution | Purpose |
|---|---|---|
| SC-W1 | 80% uniform inventory transfer, 20% uniform inventory audit | Low-contention overhead |
| SC-W2 | 80% inventory transfer, 20% audit; SKU popularity follows truncated Zipf(alpha=1.2) | Popular-SKU contention |
| SC-W3 | 60% central-warehouse transfer, 20% four-operation batch distribution, 15% hotspot audit, 5% batch-state update | Multi-key, high-contention distribution |

Default state: 20 warehouses, 50 SKUs, 10 hot SKUs, initial quantity 1,000,000 per warehouse-SKU key, and 10,000 batches.

## Compared schemes

- Native Fabric Gateway
- Traditional Lock
- ED-MVCC-Reimpl
- CAPS

The primary load points are 300 and 500 tx/s. Every workload, scheduler, and load combination is repeated 10 times.

## Correctness invariant

For every SKU `k`, the total quantity across all warehouses must remain constant:

```text
sum_w inventory[w,k] = warehouseCount * initialQuantity
```

Every inventory quantity must also remain non-negative. The matrix runner evaluates this invariant after every run and stores the result in `invariant-check.json`.

## Runnable files

The implementation is archived in:

```text
experiment1_reproducibility_package/chaincode/chaincode.go
experiment1_reproducibility_package/scripts/supply-chain-loadgen.js
experiment1_reproducibility_package/scripts/supply-chain-admin.js
experiment1_reproducibility_package/scripts/native-fabric-gateway.js
experiment1_reproducibility_package/scripts/run-supply-chain-matrix.sh
experiment1_reproducibility_package/scripts/summarize-supply-chain.js
```

The four scheduler services must be running before the matrix starts. Then run:

```bash
cd /home/rd/fabric-exp/caliper-vll
SC_REPEATS=10 SC_RATES="300 500" \
  SC_WORKLOADS="sc-w1 sc-w2 sc-w3" \
  SC_SCHEDULERS="native traditional-lock ed-mvcc caps" \
  bash tools/run-supply-chain-matrix.sh
```

For a short functional check:

```bash
SC_REPEATS=1 SC_RATES=10 SC_DURATION=2 \
  SC_WORKLOADS=sc-w3 SC_SCHEDULERS=caps \
  SC_WAREHOUSES=5 SC_SKUS=10 SC_HOT_SKUS=4 \
  bash tools/run-supply-chain-matrix.sh
```

## Completed smoke test

The first CAPS smoke run submitted ten requests covering all four chaincode operations. All ten completed successfully. Inventory conservation passed for all ten test SKUs, with no negative inventory. This run includes first-use chaincode-container startup and is retained only as a functional test; it must not be used as performance evidence.

## Completed formal matrix

The full `3 workloads x 4 methods x 2 rates x 10 repetitions` matrix was completed on 2026-06-25.

- Formal runs: 240
- Invariant passes: 240/240
- Non-idle scheduler snapshots: 0
- Group summaries: 24, each containing 10 repetitions

Results and analysis are stored in:

```text
formal_results_20260625/
FORMAL_RESULTS_20260625.md
../supply_chain_formal_results_20260625.zip
```

Traditional Lock uses a five-second queue deadline in the formal matrix. This prevents a client timeout from leaving queued lock work active during the next repetition. The runner also waits for every scheduler to report an empty active set and queue before collecting metrics or resetting the next run.

The formal matrix uses the current single-process open-loop generator with `clients=100` in its configuration. It does not instantiate 100 independent Fabric identities or Caliper workers. Use a separate worker-pool experiment before describing the setup as 100 independent clients.
