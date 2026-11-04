# Midterm 2 — Evaluation and Diagnostic Outputs

This directory contains the evaluation tables, figures, diagnostic analyses, and report prepared for the Midterm 2 study.

## Directory structure

| Directory / file | Contents |
|---|---|
| `A1/` | Overall and monthly predictive metrics, class-level metrics, confusion matrices, aggregate tables, and figures |
| `A2/` | Performance by community size, lineage history, member-activity history, and joint strata |
| `A3/` | Resolved, unresolved, and censored label-status comparisons and descriptive feature summaries |
| `B/` | Coverage tables and visualizations by month, size, and history |
| `error_analysis/` | Class-level error summaries and frequent misclassification pairs |
| `model_comparison/` | Matched monthly model comparison |
| `paired_bootstrap/` | Paired Macro-F1 intervals and stratified bootstrap summaries |
| `seed_agreement/` | B2 Random Forest prediction agreement across seeds |
| `diagnostic_report.md` | Consolidated evaluation and diagnostic report |

## Reproducibility scripts

The following scripts are located at the repository root:

- `run_a1_a2.py`: Generates A1 and A2 tables from frozen prediction, feature, and label exports.
- `aggregate_a1_a2.py`: Aggregates per-seed results and generates summary figures.
- `analyze_seed_agreement.py`: Evaluates prediction agreement across B2 Random Forest seeds.

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

See `diagnostic_report.md` for detailed findings, tables, and limitations.