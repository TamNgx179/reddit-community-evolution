# Reddit pilot: audited data to community membership

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
