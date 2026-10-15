# Source architecture

One functional package, `src/reddit_sna`, serves CLI and notebooks. The implemented path is ZIP audit → normalization → monthly R → Independent Leiden. Full core tracking/features/forecasting and the synthetic pair demos remain planned. Filenames describe responsibilities; ownership is in the administrative assignment.

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

Algorithm modules never import CLI or pipelines; pipelines do not import each other. Imports perform no file reads or expensive computation. `contracts.py` contains small records and invariants, without graph/ML dependencies. No general utils module, plugin registry or service/repository layer is needed.

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
| `tracking/`, `features/`, `models/`, `benchmarks/` | Responsibility descriptions, not completed algorithms |

## Notebooks and reporting

The three notebook directories support independent pair prototypes. `00_research_plan.ipynb` files are deliberately unfinished templates. `core/01_reddit_pilot.ipynb` is executable with an installed graph/notebook environment: it checks the actual kernel, resolves repository paths, replays verified results or rebuilds from raw, displays diagnostics and exports figures. Follow the setup in README. No `sys.path` modification is allowed.

Keep exploratory prototypes in notebooks until stable. Reusable replay, validation and plotting belong in the package and are behavior-tested independently. Restart and run all cells before handing off; store executed copies/figures in fresh local artifact folders and commit output-free source notebooks. Plots are derived from recorded aggregates, never hardcoded scientific results. Network sampling is display-only; full graph data determine metrics and memberships.

## Input, graph and identity semantics

Normalization excludes future rows before ordinal identity allocation and retains older metadata for parent lookup. Raw author mappings exist only in memory, never on disk. Pseudonyms are local to a normalized run and do not guarantee anonymity. Deleted/removed/unknown/AutoModerator authors are excluded; other bots remain a limitation. Identical duplicates are counted; conflicting duplicates abort. SQLite connections are explicitly closed on Windows.

Replies use child time and point from comment author to parent author. A parent may precede the pilot but must not follow the child. R adds directed weights in both directions and excludes self-loops. Active authors and endpoints can differ; their union defines observed users. Isolates are retained for coverage but not assigned a community.

The corpus audit includes every declared corpus-month, even zero activity. Each comment receives exactly one priority outcome: no pointer → missing parent → excluded child → excluded parent → future parent → self → valid. These sum to comments; legacy incidence counters can overlap. Coverage uses active authors incident to attributed replies divided by active authors in the same corpus-month. Corpus author counts overlap and are not additive.

Leiden runs weighted RBConfiguration with a specified gamma, independent months, predetermined seeds and convergence. Canonical membership is the first seed, not a chosen winner. Empty graphs produce no quality estimate. Modularity, RB objective, connectivity, size and seed ARI have distinct meanings; none validates social truth alone.

Graph protocol/cohort checksums bind all monthly inputs and retain separate per-month hashes. Membership references additionally include identity, detector version, gamma and seed, shared across one cohort's months. Adding a month changes cohort reference without necessarily changing past partitions. Legacy inputs use a distinct protocol/reference; do not join references automatically. Detection inherits source bounds and rejects explicit mismatched intervals before reserving output; create a separate snapshot run for a subset.

The causal-prefix diagnostic requires caller-provided bijective user alignments, compares R/directed_R/users and partitions up to a cutoff under cluster renaming, and ignores later months. Ordinal IDs and node order can differ across runs. Report actual differences rather than changing seeds to obtain a pass. This does not validate unimplemented tracking/features/forecasting.

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
