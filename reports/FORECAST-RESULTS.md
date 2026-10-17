# Historical Jaccard fallback and reproduced Reddit pilot

Current GED-adaptation delivery: [results](FORECAST-GED-RESULTS.md) and [handoff contract](FORECAST-HANDOFF.md). The scores below belong to the original fallback label reference.

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
events. A lack of overlap is not proof a social group dissolved. GED/HeTCo remain
unimplemented. Synthetic tests exercise all six event rules; that does not supply
missing real-data event support. Keep this run as the initial fallback baseline.
Any later tracker changes need training-only development decisions and a fresh
evaluation plan; do not tune this threshold to the October-December scores.
