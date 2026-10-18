# Methods and architecture

Read [the runbook](RUNBOOK.md) for commands and [results](RESULTS.md) for executed evidence.

## Contents

- [Dependencies and boundaries](#dependencies-and-boundaries)
- [Input, graph and identity semantics](#input-graph-and-identity-semantics)
- [Data contracts](#data-contracts-v1)
- [Configuration and artifact policy](#config-and-artifact-policy)
- [Forecast tables and joins](#tables-and-join-rules)
- [GED adaptation and ambiguity](#ged-adaptation-and-ambiguity)
- [Features and timing](#features-and-timing)
- [Jaccard fallback](#jaccard-fallback-semantics)

One functional package, `src/reddit_sna`, serves CLI and notebooks. The implemented core-pair baseline connects ZIP audit → normalization → monthly R → Independent Leiden → Jaccard/GED adaptation → current/history features → temporal baselines → verified evaluation. HeTCo, full original GED, heterogeneous/temporal detection and the synthetic pair demos remain planned. Filenames describe responsibilities; ownership is in the administrative assignment.

## Dependencies and boundaries

```text
CLI → config + selected pipeline
notebook → config + functional modules / implemented pipeline
pipeline → data / graphs / detection / tracking / features / models / evaluation / benchmarks
pipeline → artifacts
reporting → recorded artifacts + graph contracts; optional plotting libraries
algorithm modules → contracts
artifacts → config + contracts
```

Algorithm modules never import CLI or pipelines. The dedicated week-one orchestrator delegates to the implemented preparation and forecast stages; those stages do not import the orchestrator. Imports perform no file reads or expensive computation. `contracts.py` contains small records and invariants, without graph/ML dependencies. No general utils module, plugin registry or service/repository layer is needed.

| Location | Responsibility and implemented state |
|---|---|
| `data/archive.py` | Explicit ZIP allowlist, streaming SHA-256, full member CRC and sampled schema audit |
| `data/normalize.py` | Full-row validation, UTC cutoff, namespaced record IDs and indexed SQLite metadata |
| `graphs/audit.py` | Complete corpus-month support and exclusive reply outcomes |
| `graphs/snapshots.py` | Child-month directed replies, symmetric R, users, isolates and coverage |
| `graphs/provenance.py` | Cohort month/schema validation, month hashes and protocol-bound references |
| `detection/leiden.py` | Independent monthly RBConfiguration partitions, seed repeats and diagnostics |
| `reporting/pilot.py` | Verify recorded artifacts, source-chain hashes, periods, identity and count conservation |
| `reporting/figures.py` | Eight descriptive figure families, labeled display sampling and PNG/SVG provenance |
| `evaluation/causality.py` | Explicitly aligned past graph/partition comparisons through a cutoff |
| `pipelines/preparation.py` | One stage or raw-to-membership orchestration; stops before tracking |
| `pipelines/core.py` | Planned complete Reddit pipeline, explicitly unfinished |
| `pipelines/detection_tracking.py` | Planned independent synthetic graph demo |
| `pipelines/prediction.py` | Planned independent synthetic table demo |
| `tracking/`, `features/` | Jaccard/GED adaptation, current snapshot features and past-only lineage history |
| `pipelines/forecast.py`, `pipelines/week1.py` | Temporal baseline training/evaluation and full raw/replay demo orchestration |
| `reporting/forecast.py`, `reporting/forecast_handoff.py` | Independent table/metric verification, six figure families and source-bound exports |
| `reporting/label_review.py` | Seeded blinded structural-label evidence; human annotation remains pending |
| `models/`, `benchmarks/` | Proposed model and independent planted benchmarks remain planned |

## Notebooks and reporting

The three notebook directories support independent pair prototypes. `00_research_plan.ipynb` files are deliberately unfinished templates. `core/01_reddit_pilot.ipynb` is executable with an installed graph/notebook environment: it checks the actual kernel, resolves repository paths, replays verified results or rebuilds from raw, displays diagnostics and exports figures. Follow the setup in README. No `sys.path` modification is allowed.

Keep exploratory prototypes in notebooks until stable. Reusable replay, validation and plotting belong in the package and are behavior-tested independently. Restart and run all cells before handing off; store executed copies/figures in fresh local artifact folders and commit only explicitly reviewed execution snapshots in the two core notebooks; keep standalone artifacts local. Plots are derived from recorded aggregates, never hardcoded scientific results. Network sampling is display-only; full graph data determine metrics and memberships.

## Input, graph and identity semantics

Normalization excludes future rows before ordinal identity allocation and retains older metadata for parent lookup. Raw author mappings exist only in memory, never on disk. Pseudonyms are local to a normalized run and do not guarantee anonymity. Deleted/removed/unknown/AutoModerator authors are excluded; other bots remain a limitation. Identical duplicates are counted; conflicting duplicates abort. SQLite connections are explicitly closed on Windows.

Replies use child time and point from comment author to parent author. A parent may precede the pilot but must not follow the child. R adds directed weights in both directions and excludes self-loops. Active authors and endpoints can differ; their union defines observed users. Isolates are retained for coverage but not assigned a community.

The corpus audit includes every declared corpus-month, even zero activity. Each comment receives exactly one priority outcome: no pointer → missing parent → excluded child → excluded parent → future parent → self → valid. These sum to comments; legacy incidence counters can overlap. Coverage uses active authors incident to attributed replies divided by active authors in the same corpus-month. Corpus author counts overlap and are not additive.

Leiden runs weighted RBConfiguration with a specified gamma, independent months, predetermined seeds and convergence. Canonical membership is the first seed, not a chosen winner. Empty graphs produce no quality estimate. Modularity, RB objective, connectivity, size and seed ARI have distinct meanings; none validates social truth alone.

Graph protocol/cohort checksums bind all monthly inputs and retain separate per-month hashes. Membership references additionally include identity, detector version, gamma and seed, shared across one cohort's months. Adding a month changes cohort reference without necessarily changing past partitions. Legacy inputs use a distinct protocol/reference; do not join references automatically. Detection inherits source bounds and rejects explicit mismatched intervals before reserving output; create a separate snapshot run for a subset.

The causal-prefix diagnostic requires caller-provided bijective user alignments, compares R/directed_R/users and partitions up to a cutoff under cluster renaming, and ignores later months. Ordinal IDs and node order can differ across runs. Report actual differences rather than changing seeds to obtain a pass. Separate forecast tests check past-only history and training-only fitting; graph invariance alone does not establish those properties.

## Data contracts v1

| Record | Invariants |
|---|---|
| `SnapshotEdge` | YYYY-MM, two distinct endpoints, finite positive weight |
| `Membership` | reference, month, local community ID, user ID |
| `SampleKey` | reference + feature month + local community ID |
| `TrackingLink` | Source/optional target keys; same reference and consecutive months |
| `CommunitySample` | Feature key, next label month, event and features |
| `Prediction` | Same sample key/label month, model, truth and prediction |

Events are `stable`, `grow`, `shrink`, `merge`, `split`, `dissolve`. An unmatched link alone does not prove dissolution; check coverage, small groups and whether t+1 was observed. The final month without its successor cannot be labeled dissolve. Cluster names do not establish temporal identity. Split/merge can have multiple links; freeze one sample-label precedence policy before evaluation.

Dataclasses validate structure and basic month relations, not feature availability, dataset uniqueness, event validity or leakage. Split **whole label-month groups**, never row-count slices that put one month into multiple sets. Fit preprocessing on train only. Retention t→t+1 is a target-derived quantity; only historical retention t−1→t can be a feature at t. Reddit tracker labels remain proxy references, not social ground truth.

## Config and artifact policy

Strict TOML allows only schema_version, pipeline, project_root, seed, input and output. Paths resolve from the config directory; unknown fields are rejected. Seeds are integers in [0, 2^32); run IDs are 1–64 portable letters/digits/hyphens/underscores and exclude Windows devices and traversal. Core uses an existing Reddit input directory; synthetic pair demos do not need that input.

Outputs remain in project artifacts and cannot overlap inputs or data. Validate before creating directories and reserve each run exclusively; even failed runs require a new ID. Preparation checks source status and all declared hashes, then records config/source/environment/Git provenance, stage status, elapsed time and output hashes. Time excludes preflight checks; peak memory is unmeasured (null). Completion through detection does not imply forecasting completion. Other future pipelines must implement their own corresponding provenance.

Reporting treats manifests as trusted local inputs and checks changes relative to them; checksums do not authenticate simultaneous replacement of metadata and artifacts. Exports preserve source manifest hashes, graph reference, plotting source/version and sampling parameters. Replay verifies recorded results; it does not claim the current source produced historical artifacts.

## Research evidence and planned extensions

The supplied rubric allocates A1/A2 50% each and requires paper potential for maximum project credit. Distinguish software correctness, method validation on controlled truth, and out-of-time Reddit results. Passing tests or arranging source does not establish the latter two, novelty or a grade.

`experiments/study.toml` is a draft task/graph/label/split/hypothesis/fairness design. Experiment E1–E5, ablation A1–A7, feature and literature catalogs are planning records; CLI does not enforce them. `reports/claim_evidence.csv` has unverified claims and `contribution_log.csv` is a blank record of actual work, not attendance evidence. Every final result must trace to data/version/reference/config/seed/environment/prediction keys and exclusions.

| Next component | Evidence required before claiming completion |
|---|---|
| Controlled benchmarks | Independent development/evaluation seeds, easy and difficult communities, small groups and all six events |
| Tracking | True-membership tests first, detector-plus-tracker second; Jaccard versus full importance-based GED; fixed thresholds and precedence |
| Graph extensions | Explicit heterogeneous versus user-projection meaning, co-thread construction cost and cutoff-safe participants |
| Features | Source/window/availability for structural, thread and historical membership features; leakage negative controls |
| Forecasting | B1/B4 first; matched-capacity B5 and proposed model on identical samples, labels and budgets |
| Evaluation | Whole label-month splits, class/month support, paired predictions, time-block uncertainty and short-test limitations |
| Novelty/insights | Closest temporal/multiplex forecasting work, quantitative cases, alternative explanations and null results |

Research questions ask whether thread context and membership history add value beyond reply structure; novelty is unconfirmed. High modularity can miss small groups, repeatable partitions can suppress real change, and a strong predictor can learn tracker artifacts. Compare alternate reference pipelines separately, report detector/tracker errors and do not tune on official test. Seed repeats are not independent test datasets. Prioritize a validated minimal chain before expensive temporal/consensus methods.

Method starting points: [ConvoKit](https://convokit.cornell.edu/documentation/subreddit.html), [Leiden](https://doi.org/10.1038/s41598-019-41695-z), [GED](https://doi.org/10.1007/s13278-012-0058-8), [modularity resolution limit](https://arxiv.org/abs/physics/0607100). These do not establish project novelty.

## Pilot validation boundary

`reporting/validation.py` computes exact graph/corpus diagnostics and bounded, predeclared gamma/edge-drop experiments. It uses verified artifacts, preserves the canonical baseline and reports support loss. `reporting/handoff.py` is an independent standard-library consumer of public files; it does not import normalization, graph construction or detection and does not create a tracker. `reporting/validation_figures.py` displays these aggregate results with explicit populations. All three are reachable from the installed validation CLI or executable pilot notebook.

A completed validation artifact means recorded interface/analysis checks ran, not that another person accepted the handoff. The fixed twelve-month pilot remains inside train and provides eleven possible transitions; later label support and split feasibility require downstream evaluation. Other pairs' formal benchmarks remain separate. The core pair's tracking/features/models now consume the public handoff through `pipelines/forecast.py`. Source/experiment records must preserve that distinction.
`reply-r-v3-order1` adds a hash-bound causal ordering sidecar without changing membership columns. `graphs/snapshots.py` computes per-user anchor hashes from records through each snapshot month; it never orders by raw author names or future records. `graphs/provenance.py` requires unique valid keys covering exactly the R endpoints. `detection/leiden.py` uses that order and sorted canonical edge indices; sensitivity uses the identical ordering policy. Reading old v2 inputs preserves their original ordinal semantics. The real cross-cutoff regression must align identities explicitly and compare graph/partition content, not byte hashes or cohort labels. Keys/identities remain local artifacts and may enable correlation; they are not an anonymity guarantee.

## Forecast handoff: schema 2

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

## Jaccard fallback semantics

This section describes the original Jaccard fallback, which
consumes verified graph/detection runs without rerunning detection. This fallback
uses Jaccard >= 0.25 (fixed before evaluation). All qualifying links are kept.
For each source community: no successor -> dissolve; multiple successors ->
split; one successor with multiple predecessors -> merge; otherwise exact
member counts determine grow/shrink/stable. Split takes precedence in many-to-many
cases. Births are not source-community forecasting samples. Disappearance from
the observed reply graph is not proof of social dissolution.

Community IDs are local to each month. Joins use the verified canonical reference
and pseudonymous users inside a single cohort. Never join quarter and annual IDs.
Inputs must cover consecutive months. Empty snapshots are retained, not skipped.

Features use only the current month's memberships and undirected R graph:
size, internal edge count, internal weight, boundary weight and internal density.
Each row labels the source community's transition to the next month. No final-month
label is invented. Features do not use target size, overlap or future labels.

The split uses **label month**: train < `--test-start`, test >= it. Scaling and
Logistic Regression fit only on train. Majority is also reported, with a Majority
fallback for single-class training. Seeds default to 42. There is no hyperparameter
search. Macro-F1 and confusion matrices always use the six declared event classes;
absent classes receive zero F1. Per-class support is included. Labels are
tracker-derived pseudo-labels, so these metrics evaluate prediction of this rule,
not tracking accuracy against independently annotated truth.
