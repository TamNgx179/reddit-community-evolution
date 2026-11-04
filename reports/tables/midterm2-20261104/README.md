# Midterm 2 — Evaluation and Diagnostic Outputs

This directory contains the evaluation tables, diagnostic outputs, validation audits, and supporting documentation for the Midterm 2 study.

The consolidated report is available at [MIDTERM2_DIAGNOSTIC_REPORT.md](../../MIDTERM2_DIAGNOSTIC_REPORT.md).

## Directory structure

| Directory / file | Contents |
|---|---|
| `A1/tables/` | Overall and monthly predictive metrics, class-level metrics, confusion matrices, and summary tables |
| `A2/tables/` | Performance by community size, lineage history, member-activity history, and joint strata |
| `A3/tables/` | Resolved, unresolved, and censored label-status comparisons and descriptive feature summaries |
| `B/tables/` | Coverage tables by month, size, and history |
| `error_analysis/tables/` | Class-level error summaries and frequent misclassification pairs |
| `model_comparison/tables/` | Matched monthly model comparison |
| `paired_bootstrap/tables/` | Paired Macro-F1 intervals and stratified bootstrap summaries |
| `seed_agreement/` | B2 Random Forest prediction agreement across seeds |
| `audits/` | Validation audit records for A1/A2 outputs |
| `README.md` | This output index |

## Figures

Figures are stored separately from the table directories under `reports/figures/midterm2-20261104/`.

- [A1 figures](../../figures/midterm2-20261104/A1/)
  - `FIG_A1_class_f1.png`
  - `FIG_A1_monthly_macro_f1.png`
  - `FIG_A1_overall_macro_f1.png`
- [A2 figures](../../figures/midterm2-20261104/A2/)
  - `FIG_A2_lineage_history.png`
  - `FIG_A2_member_activity_history.png`
  - `FIG_A2_size_history.png`
  - `FIG_A2_size_macro_f1.png`
- [B figures](../../figures/midterm2-20261104/B/)
  - `B_history_coverage.png`
  - `B_monthly_resolved_coverage.png`
  - `B_monthly_status_counts.png`
  - `B_size_coverage.png`

## Reproducibility scripts

The reproducibility scripts are located in the repository's `scripts/` directory:

- [run_a1_a2.py](../../../scripts/run_a1_a2.py): Generates A1 and A2 tables from frozen prediction, feature, and label exports.
- [aggregate_a1_a2.py](../../../scripts/aggregate_a1_a2.py): Aggregates per-seed results and generates summary outputs.
- [analyze_seed_agreement.py](../../../scripts/analyze_seed_agreement.py): Evaluates prediction agreement across B2 Random Forest seeds.

The scripts accept input and output paths through command-line arguments. Refer to each script's `--help` output for usage.

## Evaluation scope

- Predictive metrics use the frozen final prediction window.
- The final prediction export contains 1,269 unique samples from January–September 2018.
- A1/A2 include 19 model configurations and three seeds (42, 43, and 44).
- Predictive evaluation uses a fixed six-class Macro-F1.
- Unresolved and terminally censored records are not converted into event labels.
- Coverage analysis includes 11,745 community-month records: 7,490 resolved, 4,072 unresolved, and 183 terminally censored.
- Paired bootstrap results are exploratory and use temporal blocks across nine months.
- Seed agreement measures consistency across repeated runs, not predictive correctness.

## Interpretation cautions

The final predictive evaluation covers 1,269 samples, not all 7,490 resolved records. Results should not be generalized beyond the evaluated prediction window without additional evidence.

The dataset is highly imbalanced, with dissolve representing 91.96% of the final sample. Rare-class metrics and small subgroup results require caution.

A3 is descriptive and does not include formal inferential effect sizes or statistical tests. Matched comparisons and subgroup differences do not establish causal effects.

Random seeds are repeated runs on the same evaluation samples, not independent observations.

For detailed findings, tables, and limitations, see [MIDTERM2_DIAGNOSTIC_REPORT.md](../../MIDTERM2_DIAGNOSTIC_REPORT.md).