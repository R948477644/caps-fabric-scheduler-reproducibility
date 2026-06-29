# Supply-Chain Formal Matrix Results

## Scope

- Workloads: SC-W1, SC-W2, SC-W3
- Methods: Native Fabric, Traditional Lock, ED-MVCC-Reimpl, CAPS
- Offered load: 300 and 500 tx/s
- Repetitions: 10 per configuration
- Total formal runs: 240
- Network: 4 peers, 1 Raft orderer, open-loop generator configured with `clients=100`
- Measurement duration: 20 seconds per run
- State: 20 warehouses, 50 SKUs, 10 hot SKUs, 100 active batch IDs

All 240 runs passed per-SKU inventory conservation and non-negative inventory checks. The 100 active batch IDs cover the complete batch-status working set; unused batch IDs were not initialized because they do not affect conflicts or transaction execution.

The current workload generator is one Node.js process. Its `clients=100` field preserves the existing experiment configuration but does not create 100 independent Fabric identities or 100 Caliper worker processes. The results compare scheduling mechanisms under the same open-loop offered load. A claim about 100 physically or cryptographically independent clients requires a separate Caliper worker or client-pool experiment.

## Main results

The table reports mean values over ten repetitions. Client latency includes committed, rejected, failed, and timed-out requests. Committed latency is calculated only from successful Fabric submissions.

| Workload | Load | Method | Committed | Goodput (tx/s) | Valid ratio | Client latency (ms) | Committed latency (ms) | MVCC invalid |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| SC-W1 | 300 | Native | 4769.3 | 127.10 | 79.5% | 4677.42 | 369.41 | 1065.5 |
| SC-W1 | 300 | Traditional Lock | 2153.8 | 72.66 | 35.9% | 1970.28 | 5469.65 | 0 |
| SC-W1 | 300 | ED-MVCC | 4458.2 | 203.30 | 74.3% | 275.86 | 185.79 | 0 |
| SC-W1 | 300 | CAPS | 4334.2 | 192.64 | 72.2% | 684.28 | 661.92 | 0 |
| SC-W1 | 500 | Native | 8124.3 | 108.91 | 81.2% | 15281.62 | 295.81 | 1534.0 |
| SC-W1 | 500 | Traditional Lock | 2148.4 | 73.02 | 21.5% | 1207.83 | 5588.44 | 0 |
| SC-W1 | 500 | ED-MVCC | 4725.6 | 207.05 | 47.3% | 389.66 | 474.52 | 0 |
| SC-W1 | 500 | CAPS | 4392.0 | 187.77 | 43.9% | 570.19 | 695.07 | 0 |
| SC-W2 | 300 | Native | 2566.7 | 74.67 | 42.8% | 3522.66 | 336.92 | 3119.9 |
| SC-W2 | 300 | Traditional Lock | 1884.0 | 8.24 | 31.4% | 7530.87 | 23984.20 | 0 |
| SC-W2 | 300 | ED-MVCC | 3153.2 | 144.67 | 52.6% | 42.62 | 73.57 | 0 |
| SC-W2 | 300 | CAPS | 4387.0 | 163.36 | 73.1% | 540.66 | 676.25 | 0 |
| SC-W2 | 500 | Native | 5204.0 | 81.34 | 52.0% | 14462.46 | 207.36 | 4025.0 |
| SC-W2 | 500 | Traditional Lock | 1882.0 | 8.12 | 18.8% | 4576.96 | 24295.48 | 0 |
| SC-W2 | 500 | ED-MVCC | 3824.5 | 178.58 | 38.2% | 53.34 | 100.83 | 0 |
| SC-W2 | 500 | CAPS | 4313.2 | 161.44 | 43.1% | 358.21 | 715.20 | 0 |
| SC-W3 | 300 | Native | 1715.5 | 44.68 | 28.6% | 4075.61 | 318.29 | 3998.1 |
| SC-W3 | 300 | Traditional Lock | 778.9 | 29.61 | 13.0% | 1902.04 | 3046.53 | 0 |
| SC-W3 | 300 | ED-MVCC | 1741.3 | 79.04 | 29.0% | 28.03 | 90.14 | 35.4 |
| SC-W3 | 300 | CAPS | 2609.2 | 86.32 | 43.5% | 205.59 | 341.20 | 0 |
| SC-W3 | 500 | Native | 3381.6 | 53.40 | 33.8% | 14211.99 | 205.81 | 5826.6 |
| SC-W3 | 500 | Traditional Lock | 822.9 | 31.69 | 8.2% | 1147.72 | 2940.06 | 0 |
| SC-W3 | 500 | ED-MVCC | 2695.1 | 122.29 | 27.0% | 25.90 | 77.27 | 0 |
| SC-W3 | 500 | CAPS | 3562.8 | 120.27 | 35.6% | 180.61 | 388.80 | 0 |

## CAPS versus Traditional Lock

CAPS increases committed transactions by:

- SC-W1: 101.2% at 300 tx/s and 104.4% at 500 tx/s.
- SC-W2: 132.9% at 300 tx/s and 129.2% at 500 tx/s.
- SC-W3: 235.0% at 300 tx/s and 333.0% at 500 tx/s.

Committed-transaction latency falls by 87.6%-87.9% in SC-W1, 97.1%-97.2% in SC-W2, and 86.8%-88.8% in SC-W3. The SC-W3 result is caused by central-warehouse and multi-key batch contention: conservative exclusive locking serializes hotspot audits and writes, while its five-second queue deadline prevents the lock queue from carrying unfinished work into the next repetition.

## CAPS versus Native Fabric

- SC-W1 is the low-contention boundary. Native commits more requests, but CAPS provides 51.6%-72.4% higher goodput and reduces aggregate client latency by 85.4%-96.3%.
- SC-W2 at 300 tx/s: CAPS commits 70.9% more transactions and provides 118.8% higher goodput. At 500 tx/s, CAPS commits 17.1% fewer transactions but provides 98.5% higher goodput and substantially lower aggregate latency.
- SC-W3: CAPS commits 52.1% more transactions at 300 tx/s and 5.4% more at 500 tx/s. Goodput improves by 93.2% and 125.2%, while CAPS records zero MVCC-invalid transactions.

Native Fabric can show low latency for the subset that commits successfully, while conflicting or failed requests remain outstanding much longer. Therefore, committed latency and aggregate client latency must be reported separately.

## CAPS versus ED-MVCC

ED-MVCC is the latency-oriented baseline because it rejects conflicts almost immediately. CAPS accepts more useful work under application hotspots:

- SC-W2 committed transactions: +39.1% at 300 tx/s and +12.8% at 500 tx/s.
- SC-W3 committed transactions: +49.8% at 300 tx/s and +32.2% at 500 tx/s.

ED-MVCC retains lower latency, and at 500 tx/s its goodput is slightly higher than CAPS in SC-W2 and SC-W3. This confirms that CAPS is a balanced scheduling policy rather than a universal minimum-latency policy.

## Experimental correction

The first Traditional Lock implementation left read-only inventory audit keys unlocked. Under SC-W2 this allowed audits to overlap writes and caused MVCC conflicts, which violates the conservative-lock baseline definition. The implementation was corrected so that Traditional Lock takes exclusive locks over the union of predicted read and write keys. All affected runs were rerun.

A second audit found that SC-W3 clients could reach their 240-second HTTP deadline while the lock scheduler still held queued work. Traditional Lock was therefore given an explicit five-second queue deadline, and the runner was changed to require an empty active set and queue before recording metrics or starting another repetition. The 20 non-independent SC-W3 Traditional Lock runs were rerun. Both sets of superseded data are archived separately and excluded from `summary.csv`.

## Artifacts

- `formal_results_20260625/`: 240 valid raw runs and summaries.
- `formal_results_20260625/summary.csv`: 24 group means and standard deviations.
- `formal_results_20260625/summary-runs.json`: normalized metrics for all 240 runs.
- `formal_results_20260625/caps_comparisons.csv`: CAPS percentage changes relative to each baseline.
