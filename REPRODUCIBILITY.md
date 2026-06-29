# Reproducibility Guide

## Tested Environment

The experiments were prepared and executed in a WSL2 + Docker Desktop workflow.
The main local environment snapshot is stored in:

```text
docs/environment_snapshot.txt
```

The manuscript experiments use a real containerized Hyperledger Fabric network,
not a discrete-event simulator.

Core components:

- OS: Ubuntu 22.04 under WSL2
- Container runtime: Docker Desktop
- Fabric: Hyperledger Fabric test-network derived setup
- Ordering service: 1 Raft orderer
- Peers: 4 peers
- Client load: 100 logical clients
- Chaincode: Go
- Scheduler/client layer: Node.js

## Experimental Groups

### Main supply-chain matrix

Location:

```text
data/raw/experiment7_supply_chain/formal_results_20260625
```

Configuration:

- Workloads: `sc-w1`, `sc-w2`, `sc-w3`
- Methods: `native`, `traditional-lock`, `ed-mvcc`, `caps`
- Offered loads: `300tps`, `500tps`
- Repetitions: 10 per setting

Important summary files:

```text
data/raw/experiment7_supply_chain/formal_results_20260625/summary.csv
data/raw/experiment7_supply_chain/formal_results_20260625/summary.json
data/raw/experiment7_supply_chain/formal_results_20260625/caps_comparisons.csv
```

### Supporting experiments

Location:

```text
data/raw/supporting_10repeats_20260626
```

This directory contains repeated experiments for:

- conflict sensitivity
- module ablation
- endorsement-policy checks
- block-cutting parameter checks
- related-work-inspired baselines

### PAC parameter sensitivity

Location:

```text
data/raw/pac_param_sensitivity_20260627
```

### Scheduler overhead

Location:

```text
data/raw/experiment1_reproducibility_package/results
```

If this directory is not present in a lightweight clone, download the matching
release asset from GitHub/Zenodo.

## Re-running Experiments

1. Install Docker Desktop and enable WSL2 integration.
2. Install Node.js, Go, jq, curl, and Git inside WSL2.
3. Install Hyperledger Fabric binaries and Docker images.
4. Bring up the network using the scripts in `fabric-network/test-network-scripts`.
5. Deploy the chaincode in `src/chaincode`.
6. Run the scheduler/workload scripts in `src/scheduler`.
7. Summarize results using the `summarize-*.js` scripts.
8. Regenerate manuscript tables and figures using scripts in `scripts`.

## Notes on Reproduction

The experiments are sensitive to:

- CPU availability and Docker Desktop resource limits
- Fabric block-cutting parameters
- Gateway/endorser concurrency
- WSL2 memory and networking behavior
- background processes on the host machine

For exact manuscript comparisons, use the committed raw data and summary scripts.
For fresh performance reproduction, report hardware, Docker Desktop version,
Fabric version, and resource limits alongside the results.
