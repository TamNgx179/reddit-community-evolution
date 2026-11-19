# GED Threshold Sensitivity — 2026-11-19

## Purpose

This directory contains supplementary outputs from the independent
reproduction of the GED threshold sensitivity analysis.

The analysis evaluates how changes to GED link and dissolve thresholds
affect community labels, evaluation eligibility, coverage, and frozen
prediction metrics.

## Experiment configurations

| Link threshold | Dissolve threshold |
|---:|---:|
| 0.50 | 0.10 (baseline) |
| 0.45 | 0.10 |
| 0.55 | 0.10 |
| 0.50 | 0.05 |
| 0.50 | 0.15 |

The link threshold is applied to both forward and backward inclusion
thresholds (alpha and beta).

## Files

- `ged_threshold_case_changes.csv`: case-level label and eligibility
  changes under each alternative threshold configuration.
- `ged_frozen_prediction_sensitivity_per_seed.csv`: frozen prediction
  evaluation results reported separately for each model and seed.

## Related scripts

- `scripts/analyze_ged_threshold_sensitivity.py`
- `scripts/analyze_ged_frozen_prediction_sensitivity.py`

## Relationship to the 2026-11-11 results

The aggregate tables already stored in
`reports/tables/sna-feedback-20261111/` were independently reproduced
and matched the new results.

Those historical aggregate files are retained in their original
directory. This directory stores supplementary case-level and
per-seed outputs; it does not duplicate the aggregate tables.

## Evaluation protocol

- Six-class pooled Macro-F1.
- Frozen models: `hier_lr_dynamic` and `hier_hgb_dynamic`.
- Seeds: 42, 43, and 44.
- Baseline frozen test cases: 1,269.
- Scores are calculated separately for each seed and then averaged.
- Unresolved and censored cases are excluded from six-class metrics.
- Unresolved cases are not recoded as dissolve.
- No model retraining is performed.
- Alternative newly eligible cases without frozen predictions are not
  treated as if predictions existed for them.

## Reproduction summary

The baseline label reconstruction matched the original labels exactly.

| Link | Dissolve | Eligible | Unresolved | Censored | Changed labels |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.10 | 7,490 | 4,072 | 183 | 0 |
| 0.45 | 0.10 | 7,501 | 4,061 | 183 | 15 |
| 0.55 | 0.10 | 7,446 | 4,116 | 183 | 63 |
| 0.50 | 0.05 | 6,867 | 4,695 | 183 | 623 |
| 0.50 | 0.15 | 7,842 | 3,720 | 183 | 352 |

The observed denominator is 11,562. Coverage is calculated as
eligible / observed.

The frozen prediction sensitivity analysis completed for both models,
three seeds, and all five configurations.

See `reports/GED_THRESHOLD_SENSITIVITY_20261119.md` for the interpretation
and full analysis.