# Forecast workflow verification

Current delivery validation: 148 tests discovered, 146 passed, 2 upstream plotting tests skipped; 38 forecast-specific tests passed. Includes GED inclusion, ambiguous labels, history lineage, future append invariance and an independent schema-2 consumer. See [current results](FORECAST-GED-RESULTS.md). The earlier fallback audit is preserved below.

Verified 2026-10-16. Scope: membership handoff, Jaccard tracking, current-month
features, transition labels, temporal baseline evaluation and persisted outputs.

## Automated results

- Forecast-specific tests: 22 passed (13 unit, 9 integration), no skips.
- Full repository suite: 132 discovered, 130 passed, 2 skipped because optional
  notebook plotting dependencies are absent. These skips concern upstream figures.
- Full suite command: `python -m unittest discover -v`.
- Local captured log: `artifacts/test-forecast-suite.log`.

## Cases covered

| Stage | Checks |
|---|---|
| Tracker | All six events, many-to-many split precedence, exact Jaccard threshold boundary, births excluded from source samples, no successor, empty snapshots, invalid empty/overlapping communities |
| Tracker invariance | 100 seeded random partition pairs checked against independent pairwise overlap/event calculations; community renaming and insertion-order invariance |
| Features | Hand-calculated internal and boundary weights, density, singleton/empty cases, renamed users, reversed edge order/direction; reject duplicate edges, missing endpoint membership and mixed months |
| Samples | Unique reference/month/community keys; reject mixed references, duplicate samples, unknown labels, nonconsecutive label months, NaN/infinite/nonnumeric features |
| Temporal model | Train/test nonempty, exact label-month boundary, whole months held together, year boundary, scaler trained on training rows only, fitted coefficients unchanged by held-out feature/label changes |
| Baselines | Single-class Majority fallback, multiclass Logistic Regression, fixed seeds, repeated execution, six-class metric order and independent confusion counts |
| Handoff | Combined run and separately linked graph/detection runs, integrity corruption, source manifest changed during read, missing input and calendar gap rejection |
| End-to-end | Empty middle month retained as dissolve rather than joined across; no invented final-month sample; expected feature values and labels recovered from synthetic archives |
| Output | Saved models reload, hashes match, output cannot escape artifacts or overwrite prior runs, simulated CSV write error records failed manifest and preserves source |

Additional upstream handoff tests in the full suite check duplicate membership
users, missing endpoints, wrong references, altered schema and unverified inputs.

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
GED/HeTCo remain outside the implemented fallback. Passing tests does not resolve
the real-data class imbalance or the absence of merge/split samples; see
[results and limits](FORECAST-RESULTS.md).
