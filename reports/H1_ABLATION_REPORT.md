# H1: declared proposed model and matched ablation

Delivery checkpoint: 9 November 2026. Due: 11 November 2026.

The H1 experiment is reproduced under a pre-fit frozen schedule, then checked
against its source inventories and earlier predictions. H1 is not supported
in its predicted direction.
The pilot retains HeTCo v4 as primary and reports v5 as an adverse-mechanism
ablation. This checkpoint reruns the same declared models and selection procedure, with
no new model, threshold candidate, relabelling or selection on evaluation scores.

## Relationship to the group's results

The group's [diagnostic report](MIDTERM2_DIAGNOSTIC_REPORT.md) concerns the
full-study `hier_lr_dynamic` primary and 1,269 final samples. This delivery
concerns the separate 2015 HeTCo pilot, with 571 main-window samples per seed.
The two studies have different references; their scores are not a matched
comparison. The full-study primary remains unchanged.

The direction follows the existing H1 declaration and recorded diagnostic
evidence. It preserves the group primary and does not assert completion of
independent human label review.

## Declared hypothesis and finite budget

H1: selecting only the dissolve-versus-event decision threshold on inner
origins will increase event recall where lineage overlaps, without increasing
false events. See [mechanisms and refutation criteria](../docs/ERROR_MECHANISMS.md).

- Declaration: [hetco_threshold.toml](../configs/hetco_threshold.toml), originally
  committed in `a937eea943d8cde7a6a62b3a8614c3208b167011` before the saved run.
- Fixed model: hierarchical head, balanced weights, extended member attributes;
  HeTCo hidden size 8, 300 epochs, learning rate 0.01, L2 0.001.
- Selection: label months 2015-07, 08, 09; main evaluation starts 2015-10.
  Each origin trains only on earlier label months.
- Grid: argmax, 0.3, 0.4, 0.5, 0.6, 0.7. Objective: mean seed-specific
  fixed-six-class Macro-F1. Ties keep declaration order, favoring argmax.
- Families: attention, mean pooling, hierarchical community-only LR.
  Seeds: 42, 43, 44. LR uses C=1, balanced weights and training-fitted scaling.
- Finite schedule: 27 inner fits and 63 evaluation fits, declared before
  extraction/fitting in `frozen-protocol.json`. `fits.json` records the actual
  order, family, seed, train/test counts, latest training label and duration.
  Grid thresholds reuse probabilities and require no additional estimator fits.
  A fit outside the order or budget fails the run.

This is a decision-rule experiment. Mean pooling remains a control, rather
than a new proposed component. It does not select the pooling direction for
which the assignment requires a new 2×2 factorial experiment.

## Matched results

Every argmax/threshold pair uses the same fitted model and input schema. The
verifier checks full five-part sample keys, truth, seed/window coverage, identical
stored dissolve probabilities and consistency with the selected decision rule.

| Family / decision | Main Macro-F1 | Rolling Macro-F1 |
|---|---:|---:|
| Attention, v4 argmax (pilot primary) | 0.3976 | 0.3924 |
| Attention, v5 threshold 0.3 | 0.4109 | 0.3967 |
| Mean pooling, argmax | 0.3490 | 0.3750 |
| Mean pooling, selected rule = argmax | 0.3490 | 0.3750 |
| Community-only hierarchical LR, argmax | 0.3974 | 0.3812 |
| Same LR, selected rule = argmax | 0.3974 | 0.3812 |

Attention's main delta is +0.0133; its saved exploratory community-bootstrap
interval is [-0.004, 0.028]. Its rolling delta is +0.0043, with saved month-block
interval [-0.014, 0.013]. Both include zero. The replay recomputes the paired
intervals; the delivery script verifies their
payload hashes and exports them without further resampling.

The mean main-window missed-event count increases from 18 to 22 per seed, while
false events decrease from 46.7 to 26.0. In the predeclared overlap stratum,
the read-only replay mechanism audit finds tier-1 recall decreasing from 0.651 to
0.508. Thus the observed gain does not recover the events predicted by H1.
All adverse results remain in the delivery.

Main and rolling windows overlap. Rolling July–September also overlaps threshold
selection, so rolling scores are descriptive and optimistic for selection.
These are previously inspected development data, not unseen confirmation.
Seeds are repeated predictions of the same communities, not independent cases.

## Outputs and reproduction

- [Ablation scores and tier-1 errors](tables/h1-ablation-20261109/ablation.csv).
- [Matched differences](tables/h1-ablation-20261109/contrasts.csv).
- [Per-class F1, recall and support](tables/h1-ablation-20261109/per-class.csv).
- [Replay paired intervals](tables/h1-ablation-20261109/saved-intervals.json).
- [Verification record](tables/h1-ablation-20261109/verification.json).
- [Actual 90-fit log](tables/h1-ablation-20261109/fit-log.csv).
- [Main history/size strata](tables/h1-ablation-20261109/main-strata.csv), including
  the overlap target stratum and no-shared-member placebo.
- [Executed notebook](../notebooks/core/08_h1_ablation.ipynb), with two figures.
- Private predictions: `artifacts/hetco/thanh-h1-reproduction-20261109/predictions.csv`; all
  27,954 rows were checked. All 9,318 v4/mean argmax refit predictions match the
  original archived predictions. All 27,954 keyed replay predictions also match
  the previous H1 run. The public exports contain aggregates only.

The real-data pipeline completed 90/90 fits in **275.59 seconds**. All keyed
predictions, selected thresholds and dissolve probabilities reproduce the prior
run exactly (maximum probability difference 0). Its comparison, selection and
evaluation files also retain the historical byte hashes. Runtime describes this
run only; it is not a controlled performance benchmark.

The local handoff archive is
`artifacts/handoff/h1-midterm2-20261109.zip`, with a `.sha256` sidecar and an
internal per-file inventory. It contains code, tests, fixed configurations,
report, executed notebook, figures, aggregates, replay predictions, fit/source
provenance and logs. Frozen raw/research input datasets are not duplicated in
the archive; full refitting still requires the local input artifacts.

From the repository root, with the local source artifacts present:

```powershell
.venv/Scripts/python.exe scripts/verify_h1_delivery.py --run artifacts/hetco/thanh-h1-reproduction-20261109 --compare-run artifacts/hetco/hetco-v5-001 --output artifacts/diagnostics/thanh-h1-new
```

Use a new output directory. The command verifies payload and source hashes,
sample joins, schedule, selection order and scores before exporting tables.
It does not fit models. The declaration uses LF checkout bytes so Windows Git
line-ending conversion cannot invalidate its pre-fit byte hash.

To rerun the same experiment, use a fresh run ID:

```powershell
.venv/Scripts/python.exe -u -m reddit_sna hetco-threshold --research-run artifacts/research/midterm-thanh-001 --preparation-run artifacts/core/reddit-2015-reproduced-v1 --reference-hetco-run artifacts/hetco/hetco-v4-001 --run-id thanh-h1-reproduction-new
```

The mechanism tables are reproduced without fitting:

```powershell
.venv/Scripts/python.exe scripts/diagnose_proposed_errors.py --output artifacts/diagnostics/thanh-h1-mechanisms-new --extra-run hetco/thanh-h1-reproduction-20261109
```

The notebook verifies all aggregate export hashes and executes five code cells
with two saved figures. Its results require no private input artifacts.

## Validation and acceptance

Twenty-one focused tests pass: HeTCo behavior and causal member features,
selection cutoff and fit reuse, tie handling, invalid grid/settings rejection,
and payload corruption/path-traversal rejection. The complete estimator
integration test also passes, pairing both decision rules on reference keys.
Earlier attempts encountered Windows Application Control DLL-load errors;
the final complete test command below passed all 21 tests:

```powershell
.venv/Scripts/python.exe -m unittest tests.integration.test_hetco_threshold tests.unit.test_hetco tests.unit.test_threshold_selection tests.unit.test_h1_delivery -q
```

The fixture integration and real-data reproduction both pass. The replay archives
actual package source bytes, environment metadata, frozen settings and all six
event probabilities; its source/declaration/protocol hashes are rechecked before
completion. Historical artifacts remain intact. The technical deliverables in
the implementation assignment are complete; independent human label review belongs to the
group's separate review workflow.

| Acceptance item | Evidence | Status |
|---|---|---|
| One declared hypothesis and proposed version | H1 declaration, unchanged v4 primary / v5 ablation | Complete |
| Configuration and budget locked before fit | Frozen protocol, source snapshot, 90 measured fit records | Complete |
| Primary and ablation share keys, features, scaler and seeds | Paired probabilities from the same fitted model; keyed replay verification | Complete |
| Corresponding implementation and tests | 21 tests pass, including integration and reference-mismatch rejection | Complete |
| Predictions and matched ablation tables | 27,954 replay rows; aggregate/class/strata/contrast exports | Complete |
| Preserve adverse evidence and stop adding models | H1 rejected in predicted direction; historical runs retained; no new variant | Complete |
