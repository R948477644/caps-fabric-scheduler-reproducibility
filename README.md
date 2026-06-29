# CAPS Fabric Scheduler Reproducibility Package

This repository contains the code, configurations, raw measurements, processed
tables, plotting scripts, and manuscript assets for:

> CAPS: Conflict-Aware and Pressure-Adaptive Scheduling for High-Contention
> Supply-Chain Transactions in Hyperledger Fabric

CAPS is an external scheduler placed before the Hyperledger Fabric Gateway. It
uses predicted read/write sets, compatible-batch selection, and pressure-aware
admission control to reduce MVCC-invalid work and bound queueing delay under
high-contention supply-chain workloads.

## Repository Layout

```text
src/
  chaincode/                 Go chaincode used by the benchmarks
  scheduler/                 Native, Traditional Lock, CAPS, ED-MVCC, and DRT runners
fabric-network/              Fabric test-network patches and connection profiles
scripts/                     Summarization, plotting, and experiment helper scripts
data/
  raw/                       Formal repeated runs and supporting experiments
  processed/                 Manuscript-ready summary tables
figures/                     Final manuscript figures
manuscript/                  PeerJ Computer Science LaTeX draft and review PDF
docs/                        Environment snapshot and release notes
```

## Main Experimental Claims

The formal supply-chain matrix uses:

- Hyperledger Fabric network: 4 peers and 1 Raft orderer
- Clients: 100 logical clients
- Methods: Native Fabric, Traditional Lock, ED-MVCC-Reimpl, CAPS
- Workloads: SC-W1, SC-W2, SC-W3
- Offered load: 300 and 500 tx/s
- Repetitions: 10 per setting

The raw data are under `data/raw/experiment7_supply_chain`, and processed tables
used in the manuscript are under `data/processed/paper_stat_tables`.

## Quick Start

The full Fabric experiment requires Docker, Docker Compose, Node.js, Go, and a
Linux/WSL2 environment. See `REPRODUCIBILITY.md` for the full environment and
step-by-step workflow.

Typical workflow:

```bash
npm install

# Bring up the Fabric network using the patched test-network scripts.
cd fabric-network/test-network-scripts
./network.sh up createChannel
./deployCC.sh

# Run a workload matrix from the repository root.
cd ../..
bash src/scheduler/run-supply-chain-matrix.sh

# Summarize supply-chain data.
node src/scheduler/summarize-supply-chain.js data/raw/experiment7_supply_chain/formal_results_20260625
```

Exact command paths may need adjustment if the Fabric binaries are installed in a
different location.

## Data Availability Statement

For submission, replace the placeholder below with the final GitHub release URL
and Zenodo DOI:

> The source code, experimental configurations, raw data, processed data, and
> plotting scripts are available at `GITHUB_RELEASE_URL`. The version used for
> the manuscript is archived on Zenodo under DOI `ZENODO_DOI`.

## License

Code and scripts are released under the MIT License. Experimental data are
released under CC BY 4.0 unless otherwise stated.
