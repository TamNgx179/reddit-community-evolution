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

### Phuc's frozen handoff downloads — 3 November 2026

Existing collaborators with push access can download the files from the
[repository Releases page](https://github.com/TamNgx179/reddit-community-evolution/releases)
after signing in to their own GitHub account. Open the draft named
`Midterm 2 frozen team handoff - 3 November 2026` and keep it in draft.
Download `pilot-reviewer_1.zip` first, then `main-reviewer_1.zip` after the rubric
is agreed. Verify the downloads against `RELEASE_SHA256SUMS.txt`.
Dang's separate `pilot-reviewer_2.zip` and `main-reviewer_2.zip` are also attached,
with their own `REVIEWER_2_SHA256SUMS.txt`. Use only the worksheet for your assigned role.

`Phuc_Coverage_Snapshots_AFTER_REVIEW_LOCK_20261103.zip` contains the separate
full-study and 2016 graph, membership, feature and machine-label inputs.
Open it only after independent annotations are locked, or let a non-reviewer
run coverage in parallel. The snapshot README includes the commands and explains
the legacy 2016 transport manifests. The delivered snapshots passed graph audits
on all 45 full-study and 12 replication months. These checks do not complete human review.

PR #21's reviewer intake currently rejects the original packets because some
decompressed cases exceed its 64 MiB inspection limit. The largest pilot case is
93,781,624 bytes and the largest main case is 72,726,472 bytes. Revise the bounded
limit with a regression test before using that intake command. Do not truncate
the evidence. Reviewer 2, answer keys and longitudinal follow-up remain separate.

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

### Proposed rubric v1.1 from the coordinator's message

The [Vietnamese rubric proposal v1.1](REVIEW-RUBRIC-V1.1.md) records Tâm's
clarifications supplied by Phúc on 3 November. It remains proposed, not frozen.
In particular, no graph membership or authored activity can support an
observed-network dissolve judgment only when the two-month data scope and
filters are established; missing or unknown observation warrants unresolved.
Internal packet consistency alone does not establish that observation condition.
Small groups entering large groups and diffuse memberships require explicit
continuation evidence before grow/merge/split judgments. Keep AI suggestions and
actual human decisions separate, disclose assistance and preserve every version.
Record actual pilot agreement and a freeze date before main annotation.

On 4 November, Phúc selected this v1.1 proposal as the working guidance he
asks Đăng to use. The [Vietnamese practical guide](PHUC-DANG-CACH-CHAM.md)
provides a case checklist, label explanations, responsibilities and a draft
handoff message without publishing case-level recommendations. It changes no
label definitions or thresholds. Đăng's acknowledgement and a shared post-pilot
freeze remain unconfirmed; Phúc's selection is not recorded as someone else's
agreement.

### Recipient helpers for Phúc

The Vietnamese [week 3–4 work plan](PHUC-WEEK3-WEEK4.md) separates technical
preparation, real packet receipt and actual human judgments. The recipient
helper `scripts/prepare_phuc_review.py` checks an isolated reviewer-1 ZIP and
creates a private working copy plus an empty evidence checklist. It never
chooses labels or records a human submission. Its filename/field checks are
not a guarantee of complete blinding or sufficient evidence; inspect the real
packet against this rubric before main annotation.

The 3 November draft handoff is available to the intended collaborators in
[GitHub Releases](https://github.com/TamNgx179/reddit-community-evolution/releases).
Select the draft named `Midterm 2 frozen team handoff - 3 November 2026`
(CLI tag `midterm2-review-handoff-20261103`) while signed in as a collaborator.
The release now includes both reviewers' separate pilot/main ZIPs; Đăng uses
only `pilot-reviewer_2.zip`, `main-reviewer_2.zip` and
`REVIEWER_2_SHA256SUMS.txt`. Reviewer 1's local helper intentionally rejects
reviewer-2 packets; Đăng extracts his own ZIP and preserves the blank original
before editing a separate working worksheet. Asset availability is not a receipt
or annotation claim. See the work plan for download and hash-check commands.
The real pilot has a 93,781,624-byte decompressed case,
so the recipient reader uses a bounded 128 MiB case limit and preserves the full
evidence. Original ZIPs remain unchanged. The coverage snapshot is **unblinded**:
reviewers must lock their independent submissions before opening it, or have a
non-reviewer run coverage in parallel. Keep the transfer release in draft.

On 4 November, following Phúc's working-guide selection, the main reviewer-1
ZIP passed technical intake and its 60 payloads passed supplied membership,
overlap, incident-edge and focal-observation consistency checks. All 181 local
links across 61 HTML pages resolved. The private workspace is
`artifacts/review/phuc-main-20261104-001/`; its README links the blank worksheet,
case index and neutral technical table. `preparation.json` records this main
payload access before shared post-pilot acknowledgement. Actual annotation is
0/60 and the shared freeze remains pending. The technical report is in
`artifacts/review/phuc-main-audit-20261104-001/`.

A supplementary automated assessment now covers all 60 main cases under Phúc's
selected v1.1 working proposal. Private outputs at
`artifacts/review/phuc-main-assisted-20261104-001/` include per-case suggestions,
confidence, evidence-based rationales, ambiguity and explicit automated
provenance. The CSV and JSON agree on 60 unique cases. Case-specific evidence
checks cover concentrated predecessor contributions and persistent interaction
cores. The assessment records prior exposure to pilot AI suggestions, general
tracker code and the sampling design. Human annotation remains 0/60, with the
original worksheets preserved for actual decisions and submissions. Shared
post-pilot acknowledgement and paired evaluation remain pending.

`scripts/run_phuc_coverage.py` exports the existing coverage diagnostics from a
hash-bound feature/label run, keeping final-snapshot censoring outside the
eligible-plus-unresolved denominator. Optional monthly graph inputs must match
the consuming sample manifest. Without those inputs the graph audit remains
explicitly pending. Run full-study and 2016 separately. Local results and review
worksheets remain under ignored `artifacts/`, not Git.

### Independent judgments

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
