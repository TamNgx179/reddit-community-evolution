# Community tracking and forecasting handoff, schema 2

This delivery covers the core partner's membership-to-prediction work. Upstream
Reddit preparation and Leiden remain the original producer's work; rebuilding
them locally supplies input, not a new detection contribution. This does not
replace the other pairs' synthetic tracking benchmarks or baseline implementations.

## Run and consume

```powershell
python -m pip install -e ".[forecast]"
python -m reddit_sna forecast --graph-run artifacts/core/reddit-2015-reproduced-v1 --detection-run artifacts/core/reddit-2015-reproduced-v1 --output artifacts/core/forecast-ged-history-v3 --test-start 2015-10 --tracker ged --history
```

The output ID must be new. Split boundary and fixed tracker parameters are not
selected by held-out scores. Input manifests/hashes and source code hashes must
remain unchanged throughout the run. Model environment versions are recorded.

Recipients can verify and read tables without importing sklearn or unpickling:

```python
from pathlib import Path
from reddit_sna.reporting.forecast_handoff import read_handoff
delivery = read_handoff(Path("artifacts/core/forecast-ged-history-v3"))
features = delivery["features"]
labels = delivery["labels"]
samples = delivery["samples"]
feature_order = delivery["manifest"]["features"]
label_reference_id = delivery["manifest"]["label_reference_id"]
```

The consumer verifies every hash, exact CSV column order, unique keys, feature
availability, complete source-label coverage, eligibility, joins, held-out sample
coverage and confusion matrices/macro-F1 recomputed independently from predictions.

## Tables and join rules

CSV encoding is UTF-8 with a header. Keys are **reference_id, feature_month,
community_id**. `reference_id` is the upstream detector/cohort reference, not the
tracker. Local community IDs do not imply lineage. All label comparisons must
also keep **label_reference_id**, a SHA-256 binding the detector reference and
tracker configuration. Never merge label references just because month/seed match.

| File | Grain / purpose |
|---|---|
| features.csv | Every observed community/month, including the final unlabeled month; explicit available_through_month equals feature_month |
| labels.csv | Every source community for consecutive t->t+1; label_month, nullable label, eligible 0/1, reason and label_reference_id |
| samples.csv | Exact join of features with eligible labels only, in manifest feature order; no imputed labels |
| tracking.csv | Source-to-target accepted links, match_score, event/reason; null target represented by empty string |
| inclusion_pairs.csv | GED mode only: every nonzero-overlap pair, shared-member count, forward/backward inclusion and accepted flag; omitted pairs have zero overlap |
| splits.csv | One row per eligible sample; train iff label_month < test_start_label_month, otherwise test |
| predictions.csv | Held-out prediction per sample/model with y_true and y_pred |
| errors.csv | Subset of predictions whose y_true differs from y_pred |
| metrics.json | Fixed six-class macro-F1, present-class balanced accuracy, per-class precision/recall/F1/support and confusion matrix |
| quality.json | Monthly class support, ambiguity exclusions, train/test support, missing history, absent test classes and dominant-class fraction |
| development_folds.json | Expanding-window scores only inside training label months; first two observed training months warm up, one later label month per fold |
| *.joblib | Trusted locally generated fitted models; use manifest feature order and recorded environment |
| manifest.json | Completion/failure, schema, cohort and label reference, parameters, feature order, versions, source/output hashes |

There is no `forming` class in the six source-community forecast targets. Newly
observed target communities still appear in features.csv with missing-history
flags. Features for a final month are available for downstream inference but
cannot have a future label until the next snapshot is actually observed.

## GED adaptation and ambiguity

Based on [Brodka et al., GED](https://arxiv.org/pdf/1207.4297), use directional
inclusion = member-overlap fraction times the fraction of member importance in
the overlap. Importance here is internal weighted degree in the current R graph;
zero-degree members receive unit weight. This is not the paper's social-position
iteration. Parameters are fixed alpha=beta=0.5, dissolve=0.1. Inclusive comparisons use a declared 1e-12 numerical tolerance to prevent roundoff from flipping boundary cases.

Project event reduction: accept a pair when either inclusion passes its respective
threshold. One-to-one links compare sizes; multiple successors split, multiple
predecessors merge. Many-to-many cases remain unresolved. With no accepted link,
call dissolve only if both inclusions to every target fall below 0.1; otherwise
leave a weak-overlap case unresolved. Both kinds retain explicit reasons and
are excluded from supervised samples. This topology reduction is a declared
adaptation, not a claim of verbatim original GED event rules.

`--tracker jaccard` preserves the earlier fallback with threshold 0.25 and
split-first precedence. Its no-link dissolve semantics differ from GED mode.
Keep separate label references. Do not compare model scores as if the target
populations were identical when one mode excludes ambiguous samples.

## Features and timing

Current-month features: size, internal_edges, internal_weight, boundary_weight,
density. Internal edges count unique undirected pairs, weight is reply count,
boundary weight counts an edge once for each incident community, and density is
2*internal_edges/(size*(size-1)), or zero for a singleton.

`--history` adds seven features computed exclusively from t-1->t accepted links:

| Feature | Definition |
|---|---|
| community_age | Start at 1; increment on unique one-to-one lineage; reset to 1 after merge/split |
| history_missing | 1 when no accepted predecessor exists, otherwise 0 |
| predecessor_count | Number of accepted predecessor communities |
| past_growth | (current_size - previous_union_size)/previous_union_size |
| past_retention | Intersection size / previous_union_size |
| inflow_fraction | Current members outside predecessor union / current_size |
| outflow_fraction | Predecessor-union members outside current / previous_union_size |

For merges/splits, use the union of accepted predecessor member sets. Missing
history rates are represented as zero with history_missing=1, not fabricated
observations. Weak/unresolved topology can still have accepted lineage links;
the uncertainty is reflected in predecessor_count and the reset-age policy.
No outgoing event, t+1 overlap, t+1 size, current transition retention, or collected
Reddit score enters features. Scaling and model fit use training rows only.

## Limits

GED adaptation and Jaccard labels remain algorithmic pseudo-labels. Ground-truth
tracking verification on a planted benchmark remains the other pair's task.
HeTCo, original GED social-position iteration and original pair event rules are
not implemented here. Subreddit/thread features need a separately agreed causal
input contract and are not silently inferred from complete future threads.

Previously inspected held-out data cannot now become a fresh confirmatory test.
The new implementation's held-out scores are descriptive development results.
For any later scientific comparison, freeze the feature/label definitions and
declare an untouched evaluation period in advance. No parameter search is run.
