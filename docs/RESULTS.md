# Results and research evidence

For the current full-study midterm results, external replication and longitudinal
measurement audit, read the [integrated research report](../reports/WEEK1_REPORT.md)
and [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).
The pilot and earlier handoff evidence below is historical and uses different
reference targets. Its scores must not be compared as a controlled improvement.

The sections below preserve earlier baseline and handoff evidence. Their independent pair demos use different reference targets. The integrated report linked above describes the current Midterm 1 study. Ownership remains in ../PHAN-CONG-SNA-8-TUAN.md.

## Contents

- [Final delivery verification](#final-delivery-verification)
- [Current event support and scores](#current-event-support-and-scores)
- [External evidence still required](#external-evidence-still-required)
- [Historical evidence](#historical-evidence)
- [Presentation outline](#presentation-outline)

## Baseline provenance

At main aa110ac on 17 October 2026, all 148 tests passed without skips. An independent forecast from the original producer's twelve-month annual inputs completed in 54.269 seconds and reproduced 1,333 eligible samples, 762/571 train/test rows and macro-F1 0.159672/0.360540 for Majority/Logistic Regression. Reloaded models reproduced all saved predictions. This was verified-input replay, not a raw rescan.

## Final-delivery verification

Verified on 17 October 2026 using the approved delivery working tree based on aa110ac:

| Check | Actual result |
|---|---|
| Full regression suite | 161/161 passed; zero skips/errors; runner wall 167.530s |
| Full raw demo | All 15 ZIPs → annual preparation → tracking/features → baselines → evaluation → figures; exit 0, 1005.348s |
| Final-source verified replay | Exit 0, 78.129s; samples/features/labels/splits/predictions/metrics byte-identical to the raw demo |
| Preparation notebook | 10/10 code cells, 14 embedded figures, fresh kernel, no errors |
| Forecast notebook | 7/7 code cells, 6 embedded figure families, fresh kernel, no errors; both model confusion matrices are included |
| Model/CSV acceptance | Both saved models reproduce every prediction; independent checks verify hashes, joins, support, per-class scores and confusion matrices |
| Regular wheel | All 41 Python modules exactly match source bytes/inventory; installed-package imports and CLI verified outside the checkout |
| Blinded review preparation | 31 cases, including weak-overlap cases and the single available stable case; 62 blank reviewer rows; no generated human judgments |

The raw run is `artifacts/core/week1-demo-input` plus `artifacts/core/week1-demo/{forecast,report}`. The final-source replay is `artifacts/core/week1-final-replay`. Review evidence stays in `artifacts/core/week1-label-review-20261017`. These are local runtime outputs, not files committed to Git. Both notebooks contain explicitly authorized, reviewed actual execution snapshots.

Raw normalization scanned 22,853,483 rows and retained 5,006,366 before 2016. Forecast results reproduce 2,320 feature rows, 2,065 source transitions and 1,333 eligible samples, with train/test 762/571. There are 732 unresolved exclusions (35.45%). Six-class macro-F1 is 0.159672 for Majority and 0.360540 for Logistic Regression. Stable has zero test support; 525/571 test labels are dissolve. Grow/merge recall is zero in the Logistic Regression run; aggregate improvement does not hide those failures.

The raw execution preceded the final status-wording/source-containment refinements; its source hashes and immutable legacy producer metadata were preserved. The final code was subsequently verified by the full synthetic suite, regular-wheel checks and an actual real-input replay. No detector, tracker threshold, feature definition, label split or scientific model was changed to improve the recorded scores. Runtime figures are descriptive and include validation/I/O; native peak memory was not measured.

Verification caught and resolved an exception-expectation mismatch, a legacy CLI status assertion and duplicate inline auto-display in the new notebook. Final tests and both actual notebooks pass. This is engineering acceptance of the week-one baseline, not social-event ground truth or a fresh confirmatory research result.

The owner-approved documentation revision consolidates the product into six Markdown files. All local document links/anchors and notebook references were rechecked. Both core notebooks were rerun from fresh kernels after the path changes (17 code cells, 20 figure families). The expanded suite includes a real offline-bundle regression: extracted artifact verification, all six document bytes/layout, and overwrite refusal. The raw run and final-source forecast replay above are retained prior executions; documentation consolidation does not rerun or change the scientific models or their scores.

## External evidence still required

- Two independent reviewer submissions and adjudication. A generated blank annotation file is preparation evidence only.
- Confirmation and freeze of a genuinely untouched evaluation period. No candidate future data have been read by this task.
- Actual rehearsal, classroom presentation and attendance. A presentation outline is not proof of these activities.
- Collaborator invitation acceptance/permissions, if required by the instructor. The owner confirmed all five invitations were sent; acceptance was not independently audited.
- Independent evidence of novelty, fair research comparisons and substantive SNA insights before any paper-level claim.

These pending external activities do not mean the implemented week-one baseline is missing HeTCo or multislice: those methods are explicitly outside the minimum week-one requirement. They do prevent a claim that the project already has validated social ground truth, a fresh confirmatory test or a guaranteed maximum grade.

## Current event support and scores

| Model | Six-class macro-F1 | Balanced accuracy on present test classes |
|---|---:|---:|
| majority | 0.159672 | 0.200000 |
| logistic_regression | 0.360540 | 0.482190 |

| Event | Train | Test |
|---|---:|---:|
| stable | 1 | 0 |
| grow | 10 | 8 |
| shrink | 20 | 12 |
| merge | 38 | 20 |
| split | 22 | 6 |
| dissolve | 671 | 525 |

GED parameters remain alpha=beta=0.5, dissolve=0.1, tolerance 1e-12; six expanding-window development folds use training label months only. These scores describe inspected pseudo-labels, not independently validated social events or a fresh confirmatory test.

## Historical evidence

Earlier run IDs, protocols, scores and test counts below are historical; they do not override the current delivery status above. Jaccard and GED label references/populations differ, so their scores are not a controlled improvement comparison.

### Annual GED delivery provenance

Executed 16 October 2026 at `artifacts/core/forecast-ged-history-v3`. The independent 17 October audit at aa110ac reproduced 1,333 eligible samples and the current score table from the original annual inputs in 54.269s, with both saved models reproducing predictions. The original suite discovered 148 tests (146 passed, two optional plot skips); the later audit passed all 148 without skips, including 38 forecast/tracking/history checks. Local original log: `artifacts/forecast-delivery-suite.log`.


<details>
<summary>Preparation and SNA diagnostics: quarter/v2 and ordered annual pilot</summary>

**Current canonical delivery:** the twelve-month `reply-r-v3-order1` pilot described in [Extended ordered pilot](#extended-ordered-pilot-january-december-2015). The earlier sections preserve historical quarter/v2 results and are labeled by their original run IDs.

The implemented preparation path audits 15 ZIPs, normalizes metadata, builds monthly R reply graphs and runs Independent Leiden. At this historical preparation-only checkpoint, tracking, features and prediction evaluation were unfinished; these diagnostics do not establish H1–H3 or a complete core demo.

## Reproduce and inspect

Follow README for Python 3.11+, graph/notebook extras and the `.venv` kernel. Run `python -m reddit_sna prepare --config configs/core.toml --run-id reddit-pilot-001` with a fresh ID to rebuild from raw. The notebook `notebooks/core/01_reddit_pilot.ipynb` defaults to replay of `reddit-pilot-detection-v1` and follows its recorded graph/normalization ancestors. Select another run with `REDDIT_DETECTION_RUN`. Restart kernel and Run All.

The functional historical handoff is:

- Graphs: `artifacts/core/reddit-pilot-graphs-v1/snapshots/<month>/{R,directed_R,users}.csv` and `snapshots/corpus_month_audit.csv`.
- Memberships: `artifacts/core/reddit-pilot-detection-v1/memberships/<month>/membership-seed0.csv`.
- Source normalization manifest SHA-256: `d59c71d1dc4f4b76dcb0b50756d2eab2b7f5cecd50f8b77cc3f4a4897a7ec1cd`.

Historical artifacts remain immutable. A replay is a verification of recorded outputs, not a new raw-data run or a claim that current plotting code produced the old pipeline artifacts. Per-month cluster names have no temporal identity; users are comparable only inside their normalized identity scope.

## Recorded scope and semantics

The January–March 2015 UTC pilot lies inside official train. The baseline audited 15 ZIPs totaling 3,355,101,263 compressed bytes, with full CRC and SHA-256 checks. It scanned 22,853,483 raw rows and retained 2,997,193 pre-cutoff metadata rows: **205,500 inside the pilot**, **2,791,693 historical rows before it**. Do not report all retained metadata as pilot activity. No invalid rows or conflicting duplicates were observed in the baseline.

Replies point from child author to parent author at child time; the parent cannot follow the child. R sums both directions. Self-replies and unknown/deleted/removed/AutoModerator authors are excluded; other bots and missing historical parents remain limitations. Only endpoint users are partitioned. An isolate is not evidence of dissolution.

Independent Leiden uses weighted RBConfiguration gamma 1, seeds 0/1/2, igraph 1.0.0 and leidenalg 0.12.0. Seed 0 is canonical. All recorded communities are connected for all three seeds/months. Modularity describes graph quality; seed ARI describes repeatability, not social accuracy.

| Month | Active authors | Reply endpoints | R edges | Reply events | Active coverage | Isolates | Communities seed 0 | Modularity | Seed ARI min–max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015-01 | 8,686 | 8,222 | 28,143 | 50,458 | 94.01% | 520 | 134 | 0.6418 | 0.9588–0.9672 |
| 2015-02 | 8,575 | 8,229 | 27,221 | 49,841 | 95.21% | 411 | 100 | 0.6731 | 0.9680–0.9811 |
| 2015-03 | 9,839 | 9,357 | 32,889 | 60,407 | 94.17% | 574 | 116 | 0.6550 | 0.9740–0.9824 |

Active coverage = active authors incident to valid edges / active authors. Reply endpoints may include parent-only users. Isolates are counted over the union of active authors and endpoints. The values above describe the historical pilot, not a forecasting test.

## Corpus-month support

| Corpus | Rows 01/2015 | Rows 02/2015 | Rows 03/2015 | Valid reply events in pilot |
|---|---:|---:|---:|---:|
| AskALiberal | 14 | 6 | 3 | 15 |
| AskThe_Donald | 0 | 0 | 0 | 0 |
| AskTrumpSupporters | 0 | 0 | 0 | 0 |
| Ask_Politics | 2,648 | 1,849 | 2,688 | 5,526 |
| Conservative | 16,442 | 16,923 | 18,289 | 34,644 |
| EnoughTrumpSpam | 0 | 0 | 0 | 0 |
| NeutralPolitics | 1,320 | 2,583 | 3,711 | 6,360 |
| PoliticalDiscussion | 21,661 | 20,479 | 28,140 | 62,371 |
| Political_Revolution | 0 | 0 | 0 | 0 |
| Republican | 1,730 | 2,528 | 3,027 | 5,209 |
| SandersForPresident | 330 | 420 | 960 | 1,305 |
| democrats | 1,569 | 1,879 | 2,320 | 3,511 |
| hillaryclinton | 3 | 4 | 27 | 9 |
| moderatepolitics | 238 | 226 | 351 | 650 |
| socialism | 19,238 | 16,465 | 17,429 | 41,106 |

All 45 corpus-month cells are present, including 12 with no observed activity. Zero does not establish nonexistence or complete historical coverage. Large corpora dominate events; corpus sensitivity remains necessary. Corpus author counts are not additive as unique network users.

Every comment has one priority outcome: no pointer, missing parent, excluded child, excluded parent, future parent, self-reply or valid. Outcomes sum to comments and valid totals equal monthly graph events. Legacy incidence counters overlap and cannot be summed as losses.

## Notebook figures and evidence

The executable notebook generates eight named figure families from verified artifacts: overlapping data-scope populations, annotated corpus support (including zeros), monthly graph volume, coverage denominators, exclusive reply outcomes, full-graph community-size ECDFs, modularity/seed-ARI diagnostics and a clearly labeled network display sample. The sample uses seeded BFS in the first month's largest component; it is biased, omits user labels and does not determine any reported full-graph metric.

Each execution exports PNG/SVG figures to a fresh local directory with source-manifest hashes, graph reference, plotting source hashes/versions and sampling policy. At that historical checkpoint, tracked notebooks had outputs stripped; the two current core notebooks contain reviewed execution snapshots. Empty partitions and undefined quality/coverage remain absent rather than fabricated zeros. See the notebook for figure-specific interpretation and README for kernel troubleshooting.

Historical verification before this notebook extension passed 67 tests in editable and installed-wheel environments and executed five former notebook code cells. Those counts describe the previous verification only. The current reporting extension passed 84/84 tests in the editable environment (44.615s) and 84/84 in an installed wheel environment (44.450s), with no skips. The revised notebook executed 7/7 code cells in a fresh kernel (19.378s replay), displayed eight figures once each and exported eight PNG plus eight SVG files with verified hashes. All four tracked notebooks are output-free; an English-language audit reviewed 65 technical files. Executed notebooks and figures remain local artifacts.

Protocol is `reply-r-v2`, cohort fingerprint `e9d0b8ab9d892db3045b8223f1c1250e709380b609506a1e815570cc591a8c86`. Membership references bind identity, cohort, detector, gamma and seed. Adding months changes cohort identity; per-month hashes distinguish changed historical inputs. Never automatically join legacy/new references.

The historical functional graph/detection stages took 12.08s/10.34s after preflight/output reservation; peak memory was unmeasured. Their graphs and seed-0 partitions matched the earlier baseline across all three months. This was version equivalence, not a future-append Reddit experiment. Synthetic causal-prefix tests explicitly align users, detect changed past edges/partitions and reject invalid alignments; they do not validate unfinished forecasting.

## Research limitations and next work

Three months suffice for a data-to-membership smoke test, not forecasting conclusions. Next: difficult planted benchmarks, gamma/perturbation sensitivity, longer train-only pilot, validated tracking, causal features, out-of-time baselines and closest-work comparison. T projection, multislice, consensus, GED/proposed model and H1–H3 remain unfinished. Do not tune to official test results.

Pseudonyms do not guarantee anonymity. Repository structure, charts and passing tests alone establish neither novelty, paper potential, participation nor a 9–10 grade. Report null results, corpus/label biases and alternative explanations honestly.

## Extended ordered pilot: January-December 2015

The canonical week-one preparation delivery is now `reddit-2015-ordered-detection-v1` with matching graph run `reddit-2015-ordered-graphs-v1`. Analysis/handoff is `reddit-2015-ordered-validation-v1`; the separate quarter sensitivity run is `reddit-quarter-ordered-validation-v1`. Historical quarter/v2 results above remain prior evidence, not the new canonical handoff. All raw inputs and earlier artifacts were preserved.

The twelve-month all15 pilot contains **2,214,673 pilot records**, **1,781,082 valid reply events**, and 2,791,693 older metadata rows for parent lookup. All **180 corpus-month cells** are audited; **44 have no observed activity**. Retained metadata totals 5,006,366 out of 22,853,483 scanned rows. The last retained month is before 2016-01; no official validation/test data were used. Twelve months give eleven potential transitions, not guaranteed downstream label support or a valid forecasting split.

### Observed SNA findings and alternatives

1. **Coverage does not imply balanced participation.** Active coverage ranges 94.01%-96.41%, while the top ceil(1% of observed users) carries 23.78%-33.92% of incident strength by month. Strength counts both edge endpoints, so it is not a share of unique reply events. A heavy tail here does not establish a power law or an influence mechanism.
2. **The aggregate network is context-imbalanced.** SandersForPresident contributes 46.62% and PoliticalDiscussion 26.13% of attributed reply events over the year. Together they account for 72.75%. This limits claims about a representative fifteen-context Reddit network. Coverage gaps, corpus history and different participation volumes are alternative explanations; subreddit context is not a ground-truth community label.
3. **Most observed users belong to a large connected component, with smaller components and isolates remaining.** Largest-component support ranges 92.90%-95.91% of observed users. Degree, weighted strength, density and the three predeclared context graphs are reported separately. Context user sets overlap; they cannot be added as unique users or interpreted as independent samples.
4. **Partition conclusions depend on resolution.** Quarter gamma 0.5 has 55-80 communities and ARI 0.736-0.819 against same-seed gamma 1. Gamma 2 has 118-154 communities and ARI 0.383-0.600. Keep gamma 1 canonical; do not select a winner from modularity or these diagnostics.
5. **Edge-drop stability must be read with support loss.** Across 27 predeclared quarter perturbation runs, common-user ARI ranges 0.907-0.965; only 98.08%-98.43% of baseline endpoint users remain in the comparison. Exactly floor(5% of unique undirected edges) is dropped per run; retained weights do not change. These repeats are dependent and do not provide an accuracy estimate or an independent-sample confidence interval.

| Month | Observed users | Components | Largest-component support | Top-1% strength share | Communities, seed 0 |
|---|---:|---:|---:|---:|---:|
| 2015-01 | 8,742 | 569 | 92.90% | 23.78% | 129 |
| 2015-02 | 8,640 | 454 | 94.14% | 24.11% | 105 |
| 2015-03 | 9,931 | 630 | 93.03% | 26.05% | 115 |
| 2015-04 | 12,573 | 678 | 94.12% | 26.08% | 98 |
| 2015-05 | 17,249 | 830 | 94.74% | 25.87% | 128 |
| 2015-06 | 18,402 | 922 | 94.55% | 28.74% | 143 |
| 2015-07 | 23,673 | 963 | 95.64% | 31.58% | 217 |
| 2015-08 | 29,726 | 1,159 | 95.82% | 33.92% | 285 |
| 2015-09 | 29,328 | 1,189 | 95.58% | 32.49% | 277 |
| 2015-10 | 38,123 | 1,664 | 95.33% | 32.85% | 308 |
| 2015-11 | 29,078 | 1,339 | 95.12% | 29.90% | 260 |
| 2015-12 | 34,981 | 1,337 | 95.91% | 29.39% | 255 |

### Real cross-cutoff ordering correction

A real comparison aligned **116,642 users** through shared pre-April record IDs, keeping the mapping in memory. Historical v2 quarter/annual graphs matched for January-March, but partitions differed in all three months despite fixed seeds: ordinal user allocation changed detector vertex/edge insertion order. Seed repeats within one run had not detected this dependency.

Protocol **reply-r-v3-order1** now binds `node_order.csv` into graph hashes. Each endpoint's order key hashes its minimum retained authored record identifier through the snapshot month; no future record or raw author name orders the detector. Both vertices and edge indices are canonicalized. New ordered quarter and annual runs preserve past graph and partition content in **all three months for all three seeds** under explicit alignment. All nine same-seed gamma-1 sensitivity replays also match their recorded partitions. Old/new references remain separate; this is an ordering/reproducibility correction, not a novel detector or validation of tracking/features/forecasting.

Annual graph reference: `reply-r-v3-order1:985fb8e035ef51d69ef2b22c343c047d1302a6bc6b8fbba1d0e641b51d8f14de`. Quarter sensitivity reference: `reply-r-v3-order1:1c9d128e23f24f5596cba3eed883feda90babd9dff9280906b8ce50d895e6589`. Sharing a month or seed does not authorize joining these cohorts' IDs. Neither hashed order keys nor ordinal pseudonyms guarantee anonymity.

### Reproduction, resources and handoff boundary

The complete new notebook ran **10/10 code cells** from a fresh kernel, displayed **14 figures** and exported **14 PNG plus 14 SVG** with source and validation provenance. Runtime was 25.543s replay, not raw processing. The initial raw-to-v2 run took 812.329s stage wall. Reusing its verified normalization, ordered annual snapshots took 82.799s and detection 131.895s; annual validation took 16.102s and ordered quarter analysis/sensitivity 34.991s. Stage walls exclude source-integrity preflight. Native peak memory remains unmeasured, not zero.

The independent standard-library consumer accepted canonical membership keys, month/reference/schema and endpoint coverage across all twelve months. Handoff files are `snapshots/<month>/{R,directed_R,users,node_order}.csv` and `memberships/<month>/membership-seed0.csv`, with manifests. Community IDs stay local to each month. Automated acceptance is **not** partner review. At the original producer-only checkpoint no handoff message had been sent and forecasting was pending. The current core-pair forecast and independent replay now verify the same annual inputs through tracking/features/model/evaluation; see RESULTS.md#annual-ged-delivery-provenance and RUNBOOK.md. This paragraph preserves the historical boundary rather than asserting that the new stage is unfinished.

The repository owner confirmed all five collaborators have been invited. Acceptance/permissions were not independently audited. Software tests, local clean-environment installation and these train-only diagnostics do not establish social ground truth, independent replication on another machine, novelty, paper potential or a guaranteed grade.

</details>

<details>
<summary>Jaccard fallback: reproduction, split, class support and confusion matrix</summary>

Current GED-adaptation delivery: [results](RESULTS.md#annual-ged-delivery-provenance) and [handoff contract](METHODS.md#forecast-handoff-schema-2). The scores below belong to the original fallback label reference.

Executed on 2026-10-16, using Python 3.12.10. Source:
[Cornell ConvoKit Reddit corpus](https://convokit.cornell.edu/documentation/subreddit.html).
All 15 declared ZIP archives were downloaded, with a total of 3,355,101,263 bytes.
Each passed CRC verification; local download_manifest.json records URLs and SHA-256.
Matching byte totals alone do not prove equality with another machine's raw files.

## Reproduction

Preparation run: `artifacts/core/reddit-2015-reproduced-v1`.
Forecast run: `artifacts/core/forecast-2015-v1`.

```powershell
python scripts/download_reddit.py --download
python -m reddit_sna prepare --config configs/core.toml --run-id reddit-2015-reproduced-v1 --start 2015-01 --end 2016-01
python -m reddit_sna forecast --graph-run artifacts/core/reddit-2015-reproduced-v1 --detection-run artifacts/core/reddit-2015-reproduced-v1 --output artifacts/core/forecast-2015-v1 --test-start 2015-10
```

These IDs now exist locally. Use new IDs for another run; outputs are immutable.
Normalization scanned 22,853,483 rows and retained 5,006,366 before 2016.
Of retained rows, 2,214,673 are in the 2015 pilot; 2,791,693 are older parent-lookup
metadata. The pilot has 1,781,082 valid reply events. Preparation stage wall time
was 508.93 seconds, excluding the download; native peak memory was not measured.

Graph reference matches the annual ordered reference reported on the upstream branch:
`reply-r-v3-order1:985fb8e035ef51d69ef2b22c343c047d1302a6bc6b8fbba1d0e641b51d8f14de`.
Canonical seed-0 community counts match all twelve reported months:

| Month | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Communities | 129 | 105 | 115 | 98 | 128 | 143 | 217 | 285 | 277 | 308 | 260 | 255 |

Matching graph hashes and community counts validate these aspects of reproduction;
community counts alone do not prove identical partitions. Membership reference IDs
include the new run's identity scope and must not be joined to another cohort.

## Temporal holdout

There are 2,065 source-community transition samples from eleven month pairs.
Training uses label months February-September (1,220 samples); held-out evaluation
uses label months October-December (845 samples). Current-month features only,
threshold 0.25, seed 42; the held-out results were not used to change the threshold.
Models, predictions and metrics are saved in the forecast run.

| Model | Macro-F1 over the six declared events |
|---|---:|
| Majority | 0.165774 |
| Logistic Regression | 0.308928 |

| Event | Train support | Held-out support |
|---|---:|---:|
| stable | 13 | 3 |
| grow | 9 | 4 |
| shrink | 9 | 2 |
| merge | 0 | 0 |
| split | 0 | 0 |
| dissolve | 1,189 | 836 |

Logistic Regression confusion matrix (rows = actual pseudo-label, columns = prediction):

| Actual / predicted | stable | grow | shrink | merge | split | dissolve |
|---|---:|---:|---:|---:|---:|---:|
| stable | 0 | 0 | 0 | 0 | 0 | 3 |
| grow | 0 | 3 | 0 | 0 | 0 | 1 |
| shrink | 0 | 0 | 0 | 0 | 0 | 2 |
| merge | 0 | 0 | 0 | 0 | 0 | 0 |
| split | 0 | 0 | 0 | 0 | 0 | 0 |
| dissolve | 0 | 0 | 0 | 0 | 0 | 836 |

The Majority confusion matrix predicts dissolve for all 845 held-out samples;
both matrices and per-class precision/recall/F1 are saved in metrics.json.

## Interpretation and limits

98.93% of held-out labels are dissolve under this fallback rule. Many small,
transient reply-network groups and the chosen overlap threshold may contribute;
this has not been established as a causal explanation. No merge/split support means
this run cannot assess prediction of those events. Absent classes receive zero F1
in the reported fixed-six-class average. The small number of non-dissolve samples
makes the apparent improvement fragile. Accuracy near 99% would obscure this issue.

These are predictions of tracker-generated pseudo-labels, not validated social
events. A lack of overlap is not proof a social group dissolved. This historical run used Jaccard; the current declared GED adaptation is documented separately. Full original GED and HeTCo remain unimplemented. Synthetic tests exercise all six event rules; that does not supply
missing real-data event support. Keep this run as the initial fallback baseline.
Any later tracker changes need training-only development decisions and a fresh
evaluation plan; do not tune this threshold to the October-December scores.

</details>

<details>
<summary>Historical fallback software verification (16 October 2026)</summary>

## Automated results

- Forecast-specific tests: 22 passed (13 unit, 9 integration), no skips.
- Full repository suite: 132 discovered, 130 passed, 2 skipped because optional
  notebook plotting dependencies are absent. These skips concern upstream figures.
- Full suite command: `python -m unittest discover -v`.
- Local captured log: `artifacts/test-forecast-suite.log`.

## Real Reddit replay

Re-ran only the forecast stage with existing verified preparation inputs, using
the same threshold 0.25, split 2015-10 and seed 42. New immutable run:
`artifacts/core/forecast-2015-verified-v2`.

Samples, tracking, predictions and metrics are byte-identical to `forecast-2015-v1`.
There are 2,065 samples: 1,220 training and 845 held out. All output hashes match;
sample keys are unique and every label month immediately follows its feature month.
Both reloaded models reproduce all saved predictions. Independent counting of
prediction pairs reproduces confusion matrices and six-class macro-F1 exactly
within 1e-12. Scores remain Majority 0.165774 and Logistic Regression 0.308928.

## Repairs made during verification

Public helpers now reject invalid/overlapping membership partitions, duplicate
edges, mixed snapshot months, malformed/duplicate sample keys, mixed references,
invalid labels, invalid seed ranges and nonfinite features. Output paths and
existing runs are checked before model fitting. A write-stage failure attempts to
record a `failed` manifest rather than leaving an unmarked partial output.

This is broad regression coverage, not proof against every possible failure.
The write-failure test injects an OSError; it does not fill the physical disk.
If the filesystem refuses every write, even a failed manifest cannot be guaranteed.
The historical fallback did not implement GED/HeTCo. The current schema-2 GED adaptation has separate tests; full original GED and HeTCo remain planned. Passing tests does not resolve
the real-data class imbalance or the absence of merge/split samples; see
[results and limits](RESULTS.md#historical-evidence).

</details>

## Presentation outline

This is presentation material, not evidence that a presentation or attendance occurred. Individual ownership remains in ../PHAN-CONG-SNA-8-TUAN.md. Show verified actual run IDs/hashes and the current notebook outputs during rehearsal; do not type demonstration predictions into slides.

| Slide | Message | Evidence to show |
|---|---|---|
| 1 | Forecast observed user-community transitions, with subreddits as contexts | Question, unit of analysis, declared limits |
| 2 | One independent pair pipeline reaches evaluation | `week1` raw/replay command and stage completion manifests |
| 3 | Fifteen-corpus annual preparation has audited scope and biased participation | Preparation notebook scope, corpus-month support and coverage |
| 4 | Independent Leiden provides temporary month-local memberships | Fixed gamma/seeds, graph reference, node/edge ordering and detected community sizes |
| 5 | GED-strength topology is a declared adaptation | Inclusion definition, current/internal strength, one-to-one and ambiguous-case example |
| 6 | Features are known at t and labels at t+1 | Current/history feature list, lineage age/reset policy, whole-label-month split and training-only scaler tests |
| 7 | Eligibility and missing classes constrain every score | Forecast notebook class-support and exclusion-coverage chart; never omit the excluded population |
| 8 | Compare Majority and Logistic Regression on the same eligible samples | Six-class macro-F1, classwise recall/F1 and both confusion matrices |
| 9 | Inspect errors and month-to-month variation | Actual saved errors, monthly scores and training-only development folds; show unsuccessful classes |
| 10 | Engineering baseline passes; research validation remains open | Test log, independent consumer/model replay, blinded-review package, proposed untouched-period protocol |

Historical reference values reproduced at aa110ac: 2,320 feature rows, 2,065 source transitions, 1,333 eligible samples; 732 unresolved (35.45%); train/test 762/571. Majority macro-F1 0.159672, Logistic Regression 0.360540. Test support: stable 0, grow 8, shrink 12, merge 20, split 6, dissolve 525. Use actual current run values if they differ and investigate the cause; do not edit results to match this outline.

Explain that grow and merge recall were zero in the historical model despite its higher aggregate score. The 2015 held-out period was already inspected, so scores are descriptive. Jaccard versus GED scores use different reference labels/populations and are not a controlled improvement. No claim of full original GED, HeTCo, social ground truth or paper novelty is justified yet.

Rehearse a missing-dependency or missing-artifact explanation, immutable output behavior and how to reproduce the notebook from the new demo. Each contributor should explain their own modules, tests, scientific assumptions and remaining limitations. Record actual attendance/rehearsal/peer review only after they occur.
