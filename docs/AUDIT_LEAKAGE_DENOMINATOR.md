# Audit of Leakage, Key-Label Joins, Matched Samples, Denominators, and Month-Block Bootstrap

**Responsible:** Đăng  
**Date:** 2026-11-11  
**Input:** `Week4_Frozen_Core_Acceptance_20261109.zip`  
**SHA-256:** `3a36ca98...5e132` (matches the `.sha256` file)

**Scope:** Full-study cohort (final, 1,269 samples, `label_month` 2018-01 to 2018-09) and 2016 cohort (main: 494, rolling: 1,107). H1 is outside the scope of this audit.

## 1. Integrity and Replay

- `package_week4_handoff.py --verify`: all 45 files verified.
- `verify_week4_inputs.py` and `run_week4_acceptance.py` completed successfully for both cohorts, using new outputs `dang-inputs-001` and `dang-replay-001`.
- `replayed-metrics.csv` is byte-for-byte identical to `week4-replay-002` in the package.
- H1 status: `pending_missing_inputs` (the four required H1 paths are not included in the frozen package). This is expected behavior, not an error.

## 2. Join Keys and Labels

| Check | Full-study | 2016 |
|---|---:|---:|
| Duplicate prediction rows (5 keys + model/seed/window) | 0 | 0 |
| Duplicate label keys | 0 | 0 |
| Predictions without a matching label | 0 | 0 |
| Number of rows changed after joining | No | No |
| `y_true` differs from the original label | 0 | 0 |
| Predictions belonging to ineligible samples | 0 | 0 |

## 3. Matched Samples Across Models

- **Full-study:** 57 model/seed groups, all using exactly the same sample set (1,269 samples). Total: 72,333 = 57 × 1,269.
- **2016:** Main uses one sample set (494); rolling uses one sample set (1,107). There are 33 model/seed groups for each window (66 groups in total).

## 4. Cutoff and Leakage

- `label_month <= feature_month`: 0 rows in both cohorts.
- `available_through_month` differs from `feature_month`: 0 rows.
- Tests: 102 passed (leakage, causal order, split, and acceptance) and 55 passed (diagnostics and research evaluation).
- **Limitation:** The training cutoff was checked only against the protocol. The package does not contain model-fitting logs.

## 5. Denominator (Full-study)

The label table contains 11,745 rows:

- 7,490 resolved.
- 4,072 unresolved (`weak_overlap_unresolved`).
- 183 censored (`final_snapshot_censored`).

Predictions cover only 1,269 final samples, not all 7,490 resolved samples. Unresolved and censored samples were not reclassified as dissolve.

Coverage:

- Community-month: 64.78%.
- Member-month: 79.31%.

## 6. Month-Block Bootstrap

**Configuration:** `paired_tables`, 1,000 draws, block size 2, 9 months, with the 3 seeds pooled within each draw.

**Pipeline verification:** The pipeline exactly reproduced Table 6.3 of `MIDTERM2_DIAGNOSTIC_REPORT`:

- +0.0474 [-0.0073; +0.0934]
- +0.0049 [-0.0195; +0.0191]
- +0.0796 [+0.0292; +0.1321]

The outcome proportions were also reproduced: 55.40/35.07/1.34/8.20.

Rerunning with the same seed produced identical results.

| Proposed `hier_lr_dynamic` compared with | Macro-F1 Delta | 95% CI | Includes 0? |
|---|---:|---|---|
| `hier_hgb_dynamic` | +0.0237 | [-0.0694; +0.0945] | Yes |
| `flat_hgb_dynamic` | +0.0476 | [-0.0303; +0.1163] | Yes |
| `flat_lr_dynamic` | +0.0502 | [-0.0294; +0.1176] | Yes |
| `B4_logreg` | +0.0806 | [-0.0101; +0.1418] | Yes |
| `B5_matched_boosting` | +0.1788 | [+0.0843; +0.2524] | No |

**Bootstrap seed sensitivity:** Across 4 bootstrap seeds, the conclusion remained unchanged: the comparison with B5 was always positive, while all other paired comparisons continued to include zero.

**Paired outcomes against `hier_hgb_dynamic`:**

- Both correct: 88.18%.
- Proposed-only correct: 2.29%.
- Reference-only correct: 2.76%.
- Both wrong: 6.78%.

## 7. Findings Requiring Attention

1. **Claim C04 in the INTEGRATED report:** The statement that "the proposed model achieves the highest Macro-F1" is numerically correct (0.4117 compared with 0.3880). However, the paired confidence intervals against `hier_hgb_dynamic`, `flat_*`, and `B4_logreg` all include zero. The result should therefore be described as a score advantage, not as a statistically significant difference. The current report does not publish the confidence interval for the proposed-versus-HGB comparison.

2. **Proposed versus HGB:** The reference-only proportion (2.76%) is higher than the proposed-only proportion (2.29%). Therefore, although the proposed model achieves a higher Macro-F1, it gets fewer individual cases correct than HGB. This distinction is already correctly reported in Section 6.1 of the report.

## 8. Checks Not Yet Completed

- **Training cutoff:** Cannot be independently verified because model-fitting logs are unavailable.
- **Versioning after label changes:** No label modification has occurred for comparison. `test_mixed_reference` provides only partial coverage.
- **H1:** Outside the scope of this audit, as previously agreed.
- **Bootstrap:** This is exploratory analysis on the 9 months already examined, not an independent confirmation.

## 9. Handoff Status and Remaining Limitations

### Reproducibility Status

- Frozen inputs for Full-study and Replication 2016 passed package integrity and input validation checks.
- Saved metrics were successfully replayed for both cohorts.
- Model, seed, window, sample key, label join, and reconciliation checks passed.
- The delivered archive is a selected export. It does not include the complete historical runtime payload or all model-fitting logs. The replay validates saved predictions and metrics; it does not independently refit the historical models.
- The original source commit SHA was not independently confirmed with Tâm. This remains a provenance limitation and must not be inferred from the current repository HEAD.

### H1 Independent Acceptance

The separate 2015 H1 pilot has a verified delivery record, including 27,954 prediction rows, a 90-fit execution record, saved outputs, and focused passing tests.

However, independent H1 acceptance under the Week 4 frozen-core package remains `pending_missing_inputs`. The following required input directories are not included in the frozen package:

- `artifacts/research/midterm-thanh-001`
- `artifacts/core/reddit-2015-reproduced-v1`
- `artifacts/hetco/hetco-v4-001`
- `artifacts/hetco/thanh-h1-reproduction-20261109`

The existing H1 delivery verification must not be interpreted as independent acceptance using the complete frozen source inputs.

### Final Handoff Decision

Full-study and Replication 2016 replay evidence is complete within the scope of the selected export. Historical runtime reproducibility and original source commit provenance remain limited. H1 independent acceptance remains pending until the required source inputs and manifests become available.