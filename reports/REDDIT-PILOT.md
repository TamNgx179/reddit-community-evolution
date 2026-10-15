# Reddit pilot: audited data to community membership

**Current canonical delivery:** the twelve-month `reply-r-v3-order1` pilot described in [Extended ordered pilot](#extended-ordered-pilot-january-december-2015). The earlier sections preserve historical quarter/v2 results and are labeled by their original run IDs.

The implemented preparation path audits 15 ZIPs, normalizes metadata, builds monthly R reply graphs and runs Independent Leiden. Tracking, features and prediction evaluation remain unfinished; these diagnostics do not establish H1–H3 or a complete core demo.

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

Each execution exports PNG/SVG figures to a fresh local directory with source-manifest hashes, graph reference, plotting source hashes/versions and sampling policy. Tracked notebooks have outputs stripped. Empty partitions and undefined quality/coverage remain absent rather than fabricated zeros. See the notebook for figure-specific interpretation and README for kernel troubleshooting.

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

The independent standard-library consumer accepted canonical membership keys, month/reference/schema and endpoint coverage across all twelve months. Handoff files are `snapshots/<month>/{R,directed_R,users,node_order}.csv` and `memberships/<month>/membership-seed0.csv`, with manifests. Community IDs stay local to each month. Automated acceptance is **not** partner review. No handoff message was sent; the partner's tracker/features/model and complete pair prediction evaluation remain unfinished.

The repository owner confirmed all five collaborators have been invited. Acceptance/permissions were not independently audited. Software tests, local clean-environment installation and these train-only diagnostics do not establish social ground truth, independent replication on another machine, novelty, paper potential or a guaranteed grade.
