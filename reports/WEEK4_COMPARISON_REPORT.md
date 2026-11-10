# Comparative Evaluation & Baseline Verification Report (Week 4)

**Audit Date:** 2026-11-08 (Midterm 2 Benchmark Milestone)
**Evaluation Window:** Final Chronological Horizon (January–September 2018)
**Target Cohort:** 1,269 community-month units per seed (Seeds: 42, 43, 44)
**Proposed Model Under Evaluation:** `hier_lr_dynamic`
> **Note:** `hier_lr_dynamic` is the full-study proposed model. No post-improvement model exists for the 1,269-case cohort (the H1 threshold study was run on the separate 2015 HeTCo pilot and was not supported in its predicted direction; the full-study primary is unchanged — see `reports/H1_ABLATION_REPORT.md` Section 1).
**Data Provenance:** Discovered handoff artifact (D:\reddit-community-evolution\artifacts\handoff\tam-f1-20261104\export\predictions_final.csv) [SHA-256: a3015a93febcd92069079f88389902e18acd2e8603d99a37e88e07318a0f376f]
**Predictions SHA-256:** `a3015a93febcd92069079f88389902e18acd2e8603d99a37e88e07318a0f376f`

---

## 1. Primary Benchmark Model Comparison

Comparative evaluation across five reference baselines, pre-declared HGB and LR comparators, the proposed model, and historical ablation controls. Evaluated over seeds 42, 43, 44 on identical keys.

| Model Name | Role | N/seed | Macro-F1 (Mean) | Macro-F1 (SD) | Accuracy (Mean) | Seed 42 | Seed 43 | Seed 44 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `hier_lr_dynamic` | Proposed (hier_lr_dynamic) | 1,269 | **0.4117** | 0.0000 | 0.9046 | 0.4117 | 0.4117 | 0.4117 |
| `hier_hgb_dynamic` | Reference Comparator (Hierarchical HGB Dynamic) | 1,269 | **0.3880** | 0.0000 | 0.9094 | 0.3880 | 0.3880 | 0.3880 |
| `flat_lr_dynamic` | Linear Comparator (Flat LR Dynamic) | 1,269 | **0.3616** | 0.0000 | 0.9496 | 0.3616 | 0.3616 | 0.3616 |
| `B4_logreg` | Linear Baseline (Logistic Regression) | 1,269 | **0.3311** | 0.0000 | 0.9472 | 0.3311 | 0.3311 | 0.3311 |
| `B2_random_forest` | Tree Baseline (Random Forest) | 1,269 | **0.2565** | 0.0033 | 0.1524 | 0.2529 | 0.2594 | 0.2573 |
| `B5_matched_boosting` | Tree Baseline (Matched Boosting HGB) | 1,269 | **0.2330** | 0.0000 | 0.1789 | 0.2330 | 0.2330 | 0.2330 |
| `B1_majority` | Trivial Baseline (Majority) | 1,269 | **0.1597** | 0.0000 | 0.9196 | 0.1597 | 0.1597 | 0.1597 |
| `B1_persistence` | Heuristic Baseline (Persistence) | 1,269 | **0.1562** | 0.0000 | 0.8605 | 0.1562 | 0.1562 | 0.1562 |
| `A_no_context_drift_matched` | Ablation Control (No Context Drift Matched) | 1,269 | **0.4069** | 0.0000 | 0.9086 | 0.4069 | 0.4069 | 0.4069 |
| `hier_hgb_static` | Control (Hierarchical HGB Static) | 1,269 | **0.3728** | 0.0000 | 0.9157 | 0.3728 | 0.3728 | 0.3728 |
| `A_no_dynamics_matched` | Ablation Control (No Dynamics Matched) | 1,269 | **0.3643** | 0.0000 | 0.9173 | 0.3643 | 0.3643 | 0.3643 |
| `flat_hgb_dynamic` | Ablation Baseline (Flat HGB Dynamic) | 1,269 | **0.3641** | 0.0000 | 0.8085 | 0.3641 | 0.3641 | 0.3641 |
| `hier_lr_static` | Control (Hierarchical LR Static) | 1,269 | **0.3477** | 0.0000 | 0.9188 | 0.3477 | 0.3477 | 0.3477 |
| `flat_hgb_static` | Control (Flat HGB Static) | 1,269 | **0.3451** | 0.0000 | 0.9448 | 0.3451 | 0.3451 | 0.3451 |
| `A_flat_matched` | Ablation Control (Flat Matched) | 1,269 | **0.3321** | 0.0000 | 0.5674 | 0.3321 | 0.3321 | 0.3321 |
| `flat_lr_static` | Control (Flat LR Static) | 1,269 | **0.3317** | 0.0000 | 0.9472 | 0.3317 | 0.3317 | 0.3317 |
| `flat_lr_SHL` | Feature Control (Flat LR SHL) | 1,269 | **0.3311** | 0.0000 | 0.9472 | 0.3311 | 0.3311 | 0.3311 |
| `flat_hgb_SHL` | Feature Control (Flat HGB SHL) | 1,269 | **0.3683** | 0.0000 | 0.9456 | 0.3683 | 0.3683 | 0.3683 |
| `HeTCo_v0` | Historical Context Model (HeTCo v0) | 1,269 | **0.2526** | 0.0000 | 0.3373 | 0.2526 | 0.2526 | 0.2526 |

> **Note on Secondary and Historical Controls:** `flat_lr_SHL` and `flat_hgb_SHL` are SHL feature-set variants (definition per the frozen handoff, where `flat_lr_SHL` yields identical Macro-F1 [0.3311] to `B4_logreg`), and `HeTCo_v0` is a historical context model carried in the frozen predictions. These are preserved from the frozen predictions for lineage completeness and are secondary to the primary protocol baselines.

> **HGB Empirical Confirmation:** `hier_hgb_dynamic` is the strongest HGB variant evaluated by Macro-F1. Ranking: `hier_hgb_dynamic` [0.3880], `hier_hgb_static` [0.3728], `flat_hgb_SHL` [0.3683], `flat_hgb_dynamic` [0.3641], `flat_hgb_static` [0.3451], `B5_matched_boosting` [0.2330]. Note that this is an empirical post-hoc confirmation, as `hier_hgb_dynamic` was already pre-declared as the primary reference comparator in evaluation protocols.

---

## 2. Per-Class and Monthly Metric Breakdowns

### 2.1. Class-Level Performance & Tier-1 Dissolve Bias

Performance by event class (averaged over seeds 42, 43, 44). Communities with ground-truth `grow` (19 cases) and `merge` (15 cases) are prominently highlighted to monitor tier-1 binary classification errors.

| Model | Event | Support | Predicted | Pred Dissolve | Dissolve Rate | Recall | Precision | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `hier_lr_dynamic` | stable | 4 | 18 | 3 | 75.0% | 0.0000 | 0.0000 | 0.0000 |
| `hier_lr_dynamic` | **grow** | 19 | 43 | 14 | 73.7% | 0.1579 | 0.0698 | 0.0968 |
| `hier_lr_dynamic` | shrink | 25 | 29 | 6 | 24.0% | 0.4800 | 0.4138 | 0.4444 |
| `hier_lr_dynamic` | **merge** | 15 | 11 | 8 | 53.3% | 0.2000 | 0.2727 | 0.2308 |
| `hier_lr_dynamic` | split | 39 | 34 | 0 | 0.0% | 0.6923 | 0.7941 | 0.7397 |
| `hier_lr_dynamic` | dissolve | 1167 | 1134 | 1103 | 94.5% | 0.9452 | 0.9727 | 0.9587 |
| `hier_hgb_dynamic` | stable | 4 | 0 | 3 | 75.0% | 0.0000 | 0.0000 | 0.0000 |
| `hier_hgb_dynamic` | **grow** | 19 | 28 | 12 | 63.2% | 0.1579 | 0.1071 | 0.1277 |
| `hier_hgb_dynamic` | shrink | 25 | 35 | 4 | 16.0% | 0.5600 | 0.4000 | 0.4667 |
| `hier_hgb_dynamic` | **merge** | 15 | 38 | 9 | 60.0% | 0.2000 | 0.0789 | 0.1132 |
| `hier_hgb_dynamic` | split | 39 | 28 | 0 | 0.0% | 0.5641 | 0.7857 | 0.6567 |
| `hier_hgb_dynamic` | dissolve | 1167 | 1140 | 1112 | 95.3% | 0.9529 | 0.9754 | 0.9640 |
| `B4_logreg` | stable | 4 | 0 | 4 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B4_logreg` | **grow** | 19 | 0 | 19 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B4_logreg` | shrink | 25 | 14 | 9 | 36.0% | 0.2000 | 0.3571 | 0.2564 |
| `B4_logreg` | **merge** | 15 | 0 | 15 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B4_logreg` | split | 39 | 41 | 0 | 0.0% | 0.7692 | 0.7317 | 0.7500 |
| `B4_logreg` | dissolve | 1167 | 1214 | 1167 | 100.0% | 1.0000 | 0.9613 | 0.9803 |
| `flat_lr_dynamic` | stable | 4 | 0 | 4 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `flat_lr_dynamic` | **grow** | 19 | 0 | 18 | 94.7% | 0.0000 | 0.0000 | 0.0000 |
| `flat_lr_dynamic` | shrink | 25 | 21 | 6 | 24.0% | 0.4000 | 0.4762 | 0.4348 |
| `flat_lr_dynamic` | **merge** | 15 | 1 | 15 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `flat_lr_dynamic` | split | 39 | 38 | 0 | 0.0% | 0.7436 | 0.7632 | 0.7532 |
| `flat_lr_dynamic` | dissolve | 1167 | 1209 | 1166 | 99.9% | 0.9991 | 0.9644 | 0.9815 |
| `B2_random_forest` | stable | 4 | 572 | 0 | 0.0% | 1.0000 | 0.0070 | 0.0139 |
| `B2_random_forest` | **grow** | 19 | 280 | 0 | 0.0% | 0.3158 | 0.0215 | 0.0402 |
| `B2_random_forest` | shrink | 25 | 24 | 1 | 4.0% | 0.4533 | 0.4661 | 0.4594 |
| `B2_random_forest` | **merge** | 15 | 214 | 0 | 0.0% | 0.3778 | 0.0265 | 0.0495 |
| `B2_random_forest` | split | 39 | 42 | 0 | 0.0% | 0.7949 | 0.7441 | 0.7686 |
| `B2_random_forest` | dissolve | 1167 | 137 | 135 | 11.6% | 0.1160 | 0.9903 | 0.2076 |
| `B1_majority` | stable | 4 | 0 | 4 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B1_majority` | **grow** | 19 | 0 | 19 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B1_majority` | shrink | 25 | 0 | 25 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B1_majority` | **merge** | 15 | 0 | 15 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B1_majority` | split | 39 | 0 | 39 | 100.0% | 0.0000 | 0.0000 | 0.0000 |
| `B1_majority` | dissolve | 1167 | 1269 | 1167 | 100.0% | 1.0000 | 0.9196 | 0.9581 |

### 2.2. Monthly Macro-F1 Trajectory (January–September 2018)

Monthly performance trajectory across the 9 evaluation months. *(Note: Extreme rare events occur in small counts in isolated months; monthly Macro-F1 should not be over-interpreted).* 

| Model | Month | Support | Macro-F1 | Accuracy |
|---|:---:|---:|---:|---:|
| `hier_lr_dynamic` | 2018-01 | 144 | 0.3824 | 0.9028 |
| `hier_lr_dynamic` | 2018-02 | 116 | 0.4349 | 0.8966 |
| `hier_lr_dynamic` | 2018-03 | 150 | 0.2622 | 0.8467 |
| `hier_lr_dynamic` | 2018-04 | 147 | 0.2445 | 0.9116 |
| `hier_lr_dynamic` | 2018-05 | 123 | 0.2881 | 0.9431 |
| `hier_lr_dynamic` | 2018-06 | 140 | 0.4690 | 0.9143 |
| `hier_lr_dynamic` | 2018-07 | 146 | 0.3544 | 0.8836 |
| `hier_lr_dynamic` | 2018-08 | 160 | 0.5496 | 0.9375 |
| `hier_lr_dynamic` | 2018-09 | 143 | 0.4608 | 0.9091 |
| `hier_hgb_dynamic` | 2018-01 | 144 | 0.4275 | 0.9375 |
| `hier_hgb_dynamic` | 2018-02 | 116 | 0.3666 | 0.8793 |
| `hier_hgb_dynamic` | 2018-03 | 150 | 0.4724 | 0.9133 |
| `hier_hgb_dynamic` | 2018-04 | 147 | 0.3053 | 0.9252 |
| `hier_hgb_dynamic` | 2018-05 | 123 | 0.2576 | 0.9268 |
| `hier_hgb_dynamic` | 2018-06 | 140 | 0.4793 | 0.9286 |
| `hier_hgb_dynamic` | 2018-07 | 146 | 0.2694 | 0.8699 |
| `hier_hgb_dynamic` | 2018-08 | 160 | 0.4365 | 0.9187 |
| `hier_hgb_dynamic` | 2018-09 | 143 | 0.3202 | 0.8811 |
| `B4_logreg` | 2018-01 | 144 | 0.3118 | 0.9444 |
| `B4_logreg` | 2018-02 | 116 | 0.3287 | 0.9483 |
| `B4_logreg` | 2018-03 | 150 | 0.3603 | 0.9267 |
| `B4_logreg` | 2018-04 | 147 | 0.2488 | 0.9592 |
| `B4_logreg` | 2018-05 | 123 | 0.3141 | 0.9837 |
| `B4_logreg` | 2018-06 | 140 | 0.3712 | 0.9429 |
| `B4_logreg` | 2018-07 | 146 | 0.2893 | 0.9178 |
| `B4_logreg` | 2018-08 | 160 | 0.4220 | 0.9500 |
| `B4_logreg` | 2018-09 | 143 | 0.2601 | 0.9580 |

---

## 3. Paired Wins and Losses Breakdown

Paired case outcomes comparing Proposed (`hier_lr_dynamic`) against each comparator. Evaluated on identical keys: `Wins` (Proposed correct, Comparator wrong), `Losses` (Comparator correct, Proposed wrong), `Net = Wins - Losses`.

### 3.1. Overall Summary per Seed:

| Proposed | Comparator | Seed | Total | Both Correct | Wins | Losses | Both Wrong | Net Wins |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `hier_lr_dynamic` | `hier_hgb_dynamic` | 42 | 1,269 | 1,119 | 29 | 35 | 86 | **-6** |
| `hier_lr_dynamic` | `hier_hgb_dynamic` | 43 | 1,269 | 1,119 | 29 | 35 | 86 | **-6** |
| `hier_lr_dynamic` | `hier_hgb_dynamic` | 44 | 1,269 | 1,119 | 29 | 35 | 86 | **-6** |
| `hier_lr_dynamic` | `B4_logreg` | 42 | 1,269 | 1,132 | 16 | 70 | 51 | **-54** |
| `hier_lr_dynamic` | `B4_logreg` | 43 | 1,269 | 1,132 | 16 | 70 | 51 | **-54** |
| `hier_lr_dynamic` | `B4_logreg` | 44 | 1,269 | 1,132 | 16 | 70 | 51 | **-54** |
| `hier_lr_dynamic` | `flat_lr_dynamic` | 42 | 1,269 | 1,139 | 9 | 66 | 55 | **-57** |
| `hier_lr_dynamic` | `flat_lr_dynamic` | 43 | 1,269 | 1,139 | 9 | 66 | 55 | **-57** |
| `hier_lr_dynamic` | `flat_lr_dynamic` | 44 | 1,269 | 1,139 | 9 | 66 | 55 | **-57** |
| `hier_lr_dynamic` | `A_no_dynamics_matched` | 42 | 1,269 | 1,120 | 28 | 44 | 77 | **-16** |
| `hier_lr_dynamic` | `A_no_dynamics_matched` | 43 | 1,269 | 1,120 | 28 | 44 | 77 | **-16** |
| `hier_lr_dynamic` | `A_no_dynamics_matched` | 44 | 1,269 | 1,120 | 28 | 44 | 77 | **-16** |
| `hier_lr_dynamic` | `A_flat_matched` | 42 | 1,269 | 703 | 445 | 17 | 104 | **+428** |
| `hier_lr_dynamic` | `A_flat_matched` | 43 | 1,269 | 703 | 445 | 17 | 104 | **+428** |
| `hier_lr_dynamic` | `A_flat_matched` | 44 | 1,269 | 703 | 445 | 17 | 104 | **+428** |

### 3.2. Decomposed Wins/Losses by Ground Truth Event (Canonical Seed 42):

| Comparator | True Class | Both Correct | Wins | Losses | Both Wrong | Net |
|---|---|---:|---:|---:|---:|---:|
| `hier_hgb_dynamic` | stable | 0 | 0 | 0 | 4 | +0 |
| `hier_hgb_dynamic` | grow | 2 | 1 | 1 | 15 | +0 |
| `hier_hgb_dynamic` | shrink | 11 | 1 | 3 | 10 | -2 |
| `hier_hgb_dynamic` | merge | 0 | 3 | 3 | 9 | +0 |
| `hier_hgb_dynamic` | split | 20 | 7 | 2 | 10 | +5 |
| `hier_hgb_dynamic` | dissolve | 1086 | 17 | 26 | 38 | -9 |
| `B4_logreg` | stable | 0 | 0 | 0 | 4 | +0 |
| `B4_logreg` | grow | 0 | 3 | 0 | 16 | +3 |
| `B4_logreg` | shrink | 4 | 8 | 1 | 12 | +7 |
| `B4_logreg` | merge | 0 | 3 | 0 | 12 | +3 |
| `B4_logreg` | split | 25 | 2 | 5 | 7 | -3 |
| `B4_logreg` | dissolve | 1103 | 0 | 64 | 0 | -64 |
| `flat_lr_dynamic` | stable | 0 | 0 | 0 | 4 | +0 |
| `flat_lr_dynamic` | grow | 0 | 3 | 0 | 16 | +3 |
| `flat_lr_dynamic` | shrink | 9 | 3 | 1 | 12 | +2 |
| `flat_lr_dynamic` | merge | 0 | 3 | 0 | 12 | +3 |
| `flat_lr_dynamic` | split | 27 | 0 | 2 | 10 | -2 |
| `flat_lr_dynamic` | dissolve | 1103 | 0 | 63 | 1 | -63 |
| `A_no_dynamics_matched` | stable | 0 | 0 | 0 | 4 | +0 |
| `A_no_dynamics_matched` | grow | 0 | 3 | 0 | 16 | +3 |
| `A_no_dynamics_matched` | shrink | 9 | 3 | 1 | 12 | +2 |
| `A_no_dynamics_matched` | merge | 2 | 1 | 0 | 12 | +1 |
| `A_no_dynamics_matched` | split | 24 | 3 | 0 | 12 | +3 |
| `A_no_dynamics_matched` | dissolve | 1085 | 18 | 43 | 21 | -25 |
| `A_flat_matched` | stable | 0 | 0 | 1 | 3 | -1 |
| `A_flat_matched` | grow | 3 | 0 | 7 | 9 | -7 |
| `A_flat_matched` | shrink | 12 | 0 | 2 | 11 | -2 |
| `A_flat_matched` | merge | 3 | 0 | 6 | 6 | -6 |
| `A_flat_matched` | split | 22 | 5 | 0 | 12 | +5 |
| `A_flat_matched` | dissolve | 663 | 440 | 1 | 63 | +439 |

---

## 4. Target Case Diagnostic Verification

> **[NOTICE] Target cases not provided by model owner.**
> Pre-declared target cases were not supplied via `--target-cases`. Per protocol, target sets are not fabricated. The following breakdown is **DESCRIPTIVE ONLY - target set not pre-declared by owner** covering all 34 ground-truth `grow` (19) and `merge` (15) cases:

| Event | Support | Baseline Correct | Baseline Predicted Dissolve | Dissolve Default Rate |
|---|---:|---:|---:|---:|
| **grow** | 19 | 3 | 14 | 73.7% |
| **merge** | 15 | 3 | 8 | 53.3% |

---

## 5. Lineage Reconciliation against Frozen Handoff

Verification audit comparing evaluated keys and metrics against Tâm's frozen handoff deliverables:

| Audit Target | Expected Value | Evaluated Value | Status |
|---|---|---|:---:|
| Four-group Case Counts (Seed 42) | 1119 / 29 / 35 / 86 | 1119 / 29 / 35 / 86 | **PASS** |
| 64-Case Correctness Contrasts | 64 keys | 64 keys | **PASS** |
| Macro-F1 (Proposed / HGB) | 0.4117 / 0.3880 | 0.4117 / 0.3880 | **PASS** |
| Overall Lineage Consistency | Frozen Reference | Unchanged Frozen Source | **PASS** |

---

## 6. Primary Cohort Citation & Evidence Basis

The designation of the evaluation cohort is established through the following exact citations in project documentation:

1. **`reports/MIDTERM2_DIAGNOSTIC_REPORT.md` (Section 1):**
   > *"The predictive evaluation uses the final prediction window only, covering January–September 2018. It contains 1,269 unique community-month samples, 19 model configurations, and three random seeds (42, 43, and 44)."*

2. **`reports/tables/midterm2-20261104/README.md` (Evaluation Scope):**
   > *"- Predictive metrics use the frozen final prediction window.
   - The final prediction export contains 1,269 unique samples from January–September 2018."*

3. **`PHAN-CONG-SNA-8-TUAN.md` (Quy định chung, Mục 3):**
   > *"Giữ tách ba nghiên cứu: full-study LR–HGB, HeTCo pilot 2015 và tái lập 2016. B4 trong pilot là LR, không được nhầm với ký hiệu baseline của bảng full-study."*

> **Formal Cohort Status:** Confirmed as the primary full-study cohort in `reports/MIDTERM2_DIAGNOSTIC_REPORT.md` Section 6.1 and `reports/H1_ABLATION_REPORT.md` Section 1.

---

## 7. Limitations

1. **Development/Replication Window Status:** The final prediction window (January–September 2018) was previously inspected during exploratory stages and serves as a retrospective replication/development cohort rather than an unseen prospective test set.
2. **Zero Seed Standard Deviation:** The random seeds (42, 43, 44) yield identical predictions and zero standard deviation (SD = 0.0000) for deterministic classifiers. This reflects fixed deterministic argmax resolution and identical input matrices, and must not be interpreted as algorithmic stability under sampling perturbation.
3. **Accuracy Decoupled from Ranking:** Accuracy is strongly distorted by class imbalance (91.96% dissolution in the final cohort). Trivial baseline `B1_majority` achieves 91.96% accuracy while scoring only 0.1597 Macro-F1. Macro-F1 on the six fixed classes is the sole valid metric for model comparison.
4. **Pilot 2015 Study Boundary:** The 2015 pilot study (571 cases) utilized different reference labels and older baseline definitions. Metric scores from the pilot cannot be pooled or compared against the 1,269 final cohort.

---

## 8. Not Available Yet

| Missing Component | Current Status |
|---|---|
| **Pre-Declared Target Cases** | No target cases were declared for the 1,269-case cohort; not applicable since no post-improvement model exists for the full-study cohort (H1 was run on the separate 2015 HeTCo pilot and was not supported). |
