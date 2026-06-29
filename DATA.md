# Data Description

## Raw Data

`data/raw/experiment7_supply_chain`

: Formal supply-chain workload matrix. This is the primary dataset used in the
  manuscript.

`data/raw/supporting_10repeats_20260626`

: Supporting 10-repeat microbenchmarks, including conflict sensitivity, module
  ablation, policy checks, configuration robustness, and related-work baselines.

`data/raw/pac_param_sensitivity_20260627`

: PAC threshold sensitivity experiments.

## Processed Data

`data/processed/paper_stat_tables`

: LaTeX table rows generated from the repeated experiments and used in the
  manuscript.

`data/processed/experiment1_summary`

: Earlier baseline-performance summaries retained for traceability.

## Figure Outputs

`figures`

: Final manuscript figures used in the PeerJ Computer Science draft.

## Data Integrity

The formal supply-chain runs include repeated-run directories with client logs,
scheduler metrics, initialization records, and invariant checks. The manuscript
reports mean, standard deviation, and confidence intervals derived from these
files.
