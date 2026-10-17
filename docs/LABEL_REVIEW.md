# Independent structural-label review

Use [the runbook](RUNBOOK.md) to produce matching inputs and [methods](METHODS.md#ged-adaptation-and-ambiguity) for the declared machine rules. Current review preparation and pending human work are recorded in [results](RESULTS.md#external-evidence-still-required).

The generated tracker labels are operational pseudo-labels. This procedure reviews whether observed membership transitions support the documented structural labels. Membership evidence alone cannot establish that a social group formed or dissolved. Independent social validation would also require an ethically reviewed, separately specified context/annotation design.

## Prepare a local blinded package

```powershell
python -m reddit_sna review-labels --forecast-run artifacts/core/week1-demo/forecast --graph-run artifacts/core/week1-demo-input --detection-run artifacts/core/week1-demo-input --output artifacts/core/label-review-001 --per-stratum 5 --seed 42
```

Use actual matching graph/detection paths when replaying separate runs. All input manifests, cohort references and hashes must match. Sampling is without replacement within each supported event or unresolved-reason stratum. Small strata contribute only their available cases; absent strata contribute none. This diagnostic sample cannot estimate event prevalence without a separate sampling/weighting design. Review size and seed must be frozen before annotating.

Give each reviewer only `reviewer/cases.json`, a private copy of `reviewer/annotations.csv` and this rubric. The coordinator retains `coordinator/answer_key.json` and the manifest containing stratum information. Directory separation does not enforce access control: distribute copies separately. Do not show model predictions, tracker labels, reasons or inclusion thresholds to reviewers. Preserve original manifests/checksums; annotation edits create separate reviewed copies, not a silently resealed machine evidence package.

Evidence includes the focal source group, every next-month group sharing at least one focal member and the source predecessors overlapping those targets. Cases use locally linked member tokens and case-local community names to avoid exposing raw identities. This is still sensitive local research evidence, not an anonymity guarantee. A missing overlapping target means no observed shared member; it does not prove social dissolution. Large groups can produce large evidence files, so pilot reviewer burden before expanding the sample.

## Two independent reviewers

Prefer reviewers who did not implement the tracker. Each reviewer must work without the answer key and without discussing cases before submitting:

- Choose `stable`, `grow`, `shrink`, `merge`, `split`, `dissolve` or `unresolved` for the **focal source**. No birth label exists for a nonexistent source.
- Record confidence `low`, `medium` or `high` and a concrete rationale based on member retention, relative sizes and predecessor/successor topology.
- Stable means a defensible one-to-one continuation of roughly unchanged size, grow/shrink a one-to-one change, merge multiple plausible predecessors and split multiple plausible successors. Since thresholds are intentionally blinded, borderline or many-to-many evidence may reasonably be unresolved. Do not force a label to match the machine rule.
- Dissolve is restricted to an **observed-network structural** interpretation with insufficient continuation evidence. Distinguish loss of observation from any social claim. Weak retention, absent context or competing lineages can remain unresolved.

The coordinator records completion timestamps and exposure history, then compares the two sealed annotation copies, reports raw agreement and the full reviewer-by-reviewer confusion table **including unresolved**, and uses an explicitly named third reviewer or documented joint adjudication for disagreements. Store original annotations and adjudicated outcomes separately. Compute agreement only after actual nonblank submissions; no metric is defined by empty templates.

## Required report after real annotation

Report sampled/annotated/adjudicated counts by hidden sampling stratum, missing submissions, disagreements, unresolved cases and confidence. Compare algorithm labels only after adjudication and include both all-reviewed coverage and the eligible subset; do not discard disagreement to inflate agreement. Distinguish exact rule conformance from independent structural plausibility and from social ground truth. Preserve failed/negative cases. Do not revise thresholds using inspected held-out cases and then call the same cases independent validation.

Current generated status is `prepared_pending_human_annotation`. No human labels, agreement scores or social validation are produced automatically by the tool.
