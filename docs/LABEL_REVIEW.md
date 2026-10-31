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

## Current Midterm 2 review packet

The frozen local packet is
`artifacts/diagnostics/midterm2-reference-label-audit-20261031-003`.
Its `reference-contract.json` binds the separate full-study and 2016 inputs.
The input inventory and technical audit are described in
[results](RESULTS.md#frozen-reference-and-lineage-audit-31-october-2026).

The main packet samples 60 original-study development cases from feature months
January–March 2017: 24 dissolve, 24 unresolved, six grow and six merge. Six
separate pilot cases come from October–December 2016: two dissolve, two
unresolved, one grow and one merge. A fixed seed of 20261031 and round-robin
month/size bins determine selection within each machine-event stratum. No model
prediction selects these cases. This targeted diagnostic sample does not estimate
population prevalence or whole-dataset label accuracy.

The coordinator keeps `coordinator/answer_key.json`, sampling strata and source
mapping private. Distribute **only** the appropriate reviewer ZIP:

| Phase | Reviewer 1 | Reviewer 2 |
|---|---|---|
| Pilot | `pilot-reviewer_1.zip` | `pilot-reviewer_2.zip` |
| Main | `main-reviewer_1.zip` | `main-reviewer_2.zip` |

The assignment names Phúc and Đăng for these two independent roles. Each receives
a separate copy, opens the phase's `index.html` and edits only their own CSV.
Pilot decisions are excluded from the 60 main cases. If the pilot changes the
rubric or packet, declare and freeze a new version before main annotation.

All focal successors, all predecessors sharing their members, and alternate
successors of those predecessors are retained. Full membership lists and all
incident weighted edges are in each case's losslessly compressed `JSON.gz`.
The HTML shows every included group and overlap count, with ten example member
tokens per group as a display preview. It does not replace the full evidence.
User tokens are case-local. Next-month per-member flags distinguish authored
records from membership in the reply graph. Lack of a reply edge is not proof
of absent activity or social dissolution.

The coordinator's `followup/` files trace the original focal members through
three observed months, separately from the one-step task. Open them only after
locking the initial judgments. Any follow-up assessment is a separately recorded
second stage and cannot silently replace the original answer or become a
forecast feature.

All 132 worksheet rows across the two phases and two reviewers are blank at
preparation. Record actual identities, roles, exposure and submission times.
Preserve and hash both submitted originals before revealing answers or comparing
decisions. Agreement, seven-label confusion and adjudication require those real
submissions. The completed technical audit does not count as human annotation.

The pilot reviewer ZIP also passed a recipient-style technical check: all six
compressed case payloads opened, local HTML links resolved, ZIP CRC passed and
the coordinator key/label fields were absent. This checks package usability,
not acknowledgement or annotation by the intended recipients. Recipient
confirmation remains pending. The [public lineage illustrations](METHODS.md#observed-lineage-traces)
use four different development examples, with no overlap with the pilot/main
review cases. Do not distribute coordinator material with the reviewer ZIP.

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

## Full-study panels and submitted assessments

The temporal study uses `study-review --study-root <root> --output <new-panel>
--period development` or `--period final`. It samples the two periods separately,
including available unresolved strata. Give each assessor only `reviewer/cases.json`.
These compact summaries contain sizes, all successor overlaps, retention and
the five largest predecessor summaries, with truncation disclosed. They omit
machine labels, thresholds and model predictions. Keep the coordinator key local.

Each actual submission is a separate JSON object containing `reviewer_id`,
`reviewer_type` (`human` or `automated`), truthful `provenance`, the exact
`payload_sha256`, a timezone-aware `submitted_utc`, and `attestations` confirming
`answer_key_not_seen`, `predictions_not_seen`, `other_assessment_not_seen`.
`judgments` must include each case exactly once with `case_id`, `label`,
`confidence` and a nonblank evidence-based `rationale`.

`study-agreement --panel <panel> --first <first.json> --second <second.json>
--output <new-result>` verifies panel integrity, complete submissions, distinct
identities and common reviewer type. It preserves originals and computes a
seven-label confusion table, raw agreement and unweighted Cohen kappa (explicitly
undefined for degenerate marginals). Optional `--adjudication <third.json>`
requires a separate actual assessor and decisions for every disagreement.

Automated assessments are supplementary structural plausibility checks. Shared
model priors can inflate their agreement. They cannot be attributed to people,
certify independent human validation, replace original tracker labels or establish
social ground truth. Human review remains pending until genuine submissions arrive.
