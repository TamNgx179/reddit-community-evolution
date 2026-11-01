# Proposed-model error mechanisms (Midterm 2, week 3)

Owner: Thanh. Status: diagnostic for the 04/11 decision with Tâm. No label,
tracker, threshold or model was changed, and no model was selected from these
scores.

## Scope and inputs

- Study: the 2015 HeTCo pilot only (inspected development data, never unseen).
  The full-study and 2016 frozen packets are covered by
  [the reference audit](RESULTS.md#frozen-reference-and-lineage-audit-31-october-2026).
- Proposed: `HeTCo_v4` (attention, balanced, hierarchical, extended members).
- Controls, all stored predictions on identical keys and seeds 42/43/44:
  HGB `B5_matched_boosting`, LR `B4_logreg`, flat head `HeTCo_v1`, no-D
  `A4v1_no_dynamics` (flat attention) and `A4_no_dynamics` (HGB), mean pooling
  `A7v4_mean_pool`, `HeTCo_v2`.
- Main window: 571 communities per seed, 46 non-dissolve events (8 grow,
  20 merge). Rolling: 982 per seed, 83 events. Counts below are seed means.
  The three seeds are not independent cases.
- Lineage evidence uses only the `t-1 -> t` GED inclusion pairs, available at
  feature month `t`. Lineage zones follow the tracker's thresholds
  (dissolve 0.1, beta 0.5).

Reproduce (writes to a new local directory):

```bash
python scripts/diagnose_proposed_errors.py --output artifacts/diagnostics/thanh-error-mechanisms-20261101
```

## Where the errors are

Tier 1 is dissolve versus any event, and tier 2 is the event type among the
five remaining classes.

| Main window | Macro-F1 | Missed event (→ dissolve) | False event (dissolve →) | Wrong event type |
|---|---:|---:|---:|---:|
| HeTCo_v4 (proposed) | 0.398 | 18.0 | 46.7 | 10.3 |
| HeTCo_v2 | 0.365 | 15.3 | 67.3 | 13.7 |
| HeTCo_v1 (flat) | 0.283 | 7.0 | 246.7 | 16.3 |
| A4v1 no-D (flat) | 0.288 | 6.3 | 250.3 | 16.3 |
| A7v4 mean pool | 0.349 | 23.3 | 41.7 | 7.7 |
| B5 HGB | 0.289 | 16.0 | 163.0 | 16.0 |
| B4 LR | 0.361 | 29.0 | 3.0 | 6.0 |

About 86% of proposed errors (64.7 of 75) are tier-1 errors. Rolling gives the
same picture: 33.7 missed, 81.3 false events and 17.0 wrong event types.

## Error-mechanism table

| # | Mechanism | Evidence available at t | Verdict |
|---|---|---|---|
| M1 | Grow/merge → dissolve in tiny groups with no lineage | v4 predicts dissolve for 4.3/8 grow and 12.7/20 merge. In the main window, 289 cases share **no** member with any `t-1` community, and 8 of them are events. v4 tier-1 recall there is 0.08, B4 and mean pooling 0.00. 20 of 46 events are 2-person groups. The flat head reaches 0.67 recall only by flagging 41% of true dissolves | Information-limited, not a pipeline bug. At t these cases look identical to dissolving pairs |
| M2 | `history_missing` is the norm | 94% of samples carry the flag in every month 2015-02..11 (89–97%). Only 80 of 1,333 samples have an accepted predecessor. Large communities lose predecessors even with 12–36% shared members, because GED inclusion multiplies member and importance fractions and stays below 0.5 under monthly Reddit turnover. Tâm's audit reproduced these values exactly | Semantics of the declared tracker, not an implementation error. It explains why D carries almost no signal |
| M3 | Chain reset of age | `community_age` is reset to 1 on ambiguous lineage and never exceeds 3 in 11 months. In the main window only 25 cases are resets with `history_missing=0`. The proposed model performs about the same there (tier-1 recall 0.71 vs 0.59) | Small effect on this pilot. Report it, but do not prioritize |
| M4 | no-D gives no change | A4v1 no-D vs v1: Macro-F1 0.288 vs 0.283 (main), 0.32 vs 0.31 (rolling). A4 vs v0 (HGB): 0.288 vs 0.291. D fields are zero for every missing-lineage row | Consistent with M2. Conditional use of history would affect at most 33 main cases (11 events) |
| M5 | Attention unstable across seeds | Cases whose prediction differs across seeds: v4 48/571 (rolling 90/982), mean pool 5 (8), HGB/LR 0. Instability peaks in 5–20 member groups (20%). There the effective member share is 0.28 and the maximum attention 0.60. Per-seed main Macro-F1 for v4 is 0.406/0.405/0.381. In 2016, attention seed SD was 0.0365 vs 0.0044 for mean pooling | Real. It hurts confirmation more than mean scores. The size bands with most events (2, >20) are stable |
| M6 | Flat vs hierarchical operating point | With the same features, the flat head catches more events (7 missed) but at about 247 false events. The hierarchical head cuts false events 5× at the cost of about 11 more misses. HGB sits in between (163 false). In the 0.1–beta overlap zone (170 cases, 21 events), v4 reaches tier-1 recall 0.65 at a 0.19 false-alarm rate, and Macro-F1 is 0.54 there vs 0.16 in the no-overlap zone | The main lever is the tier-1 decision, not member pooling. Agrees with the 2016 controlled-pooling contrast (hierarchy +0.077, member means +0.0002 in LR) |

Paired against HGB (main, per seed): proposed-only 138–141, HGB-only 17–22,
both wrong 54–57. HGB's extra losses are mostly false events on dissolving
pairs. Case lists with every control's three-seed predictions are in
`main_grow_merge_cases.csv` (local).

### Note for the label reviewers (no relabelling)

8 of the 20 main-window merges are 2-person groups with **no** shared member
with any `t-1` community. Their label comes from both members joining a larger
`t+1` target with several predecessors. Phúc–Đăng's packet can check whether
such tiny "merges" are structurally plausible. Until their sealed review is
done, the tracker rule stays as is.

## Proposed single change (for the 04/11 decision with Tâm)

**Hypothesis H1.** Most remaining proposed errors are tier-1 operating-point
errors. Balanced weighting fixes the dissolve/event threshold implicitly.
Selecting only the tier-1 decision threshold on inner origins 2015-07..09
(labels strictly before the main window) will raise event recall where
lineage overlap exists, without raising false events.

- **Expected to improve:** events in the 0.1–beta overlap zone and the
  observed-lineage cases. These are size 2–4 groups with partial overlap.
  Grow and merge recall there should rise, with dissolve false alarms ≤ the
  current 0.19.
- **Not expected to improve (placebo stratum):** the 289 no-shared-member
  cases (M1). If the gain comes mainly from there, or comes with a rise in
  false events, the change is fitting noise and H1 is rejected.
- **Refuting controls:** (1) the same threshold procedure on hierarchical LR
  with community attributes and identical scaler, seeds and budget. If it gains
  as much, the effect is a decision-rule effect, not a HeTCo effect, and is
  reported as such. (2) Flat vs hierarchical with identical features. (3) Per-class
  recall and false alarms for each class, plus paired wins/losses against HGB and LR.
- **Not chosen:**
  - Lineage/ID fix (M2/M3): the audit found no mismatch.
  - Conditional history (M4): too few observed cases.
  - Attention → mean pooling as the new primary (M5): it would be chosen after
    seeing 2016 scores. Mean pooling stays a reported control. Its stability is a
    reason to keep it in the ablation, not to promote it.
- The hypothesis, threshold grid and run list were committed before any fit
  (see the result below). Tâm can still overrule the choice at the 04/11 decision.

## Result of the pre-declared v5 run (H1 not supported)

The declaration `configs/hetco_threshold.toml` was committed in `a937eea`
before any fit. Run `artifacts/hetco/hetco-v5-001` (local) took 264 s.
Reproduce:

```bash
python -m reddit_sna hetco-threshold --research-run artifacts/research/midterm-thanh-001 \
  --preparation-run artifacts/core/reddit-2015-reproduced-v1 \
  --reference-hetco-run artifacts/hetco/hetco-v4-001 --run-id hetco-v5-001
```

The refit argmax models reproduce all 9,318 stored v4 and mean-pooling
predictions exactly, so v5 − v4 differs only by the threshold.

Inner selection on 2015-07..09 chose 0.3 for attention, a gain of only 0.003
over argmax (0.3815 vs 0.3783). It chose argmax, meaning no change, for mean
pooling and for hierarchical LR.

| Model | Main Macro-F1 (per seed) | Rolling Macro-F1 | Missed / false / wrong-type events (main) |
|---|---|---:|---|
| HeTCo_v4 (argmax) | 0.398 (0.406 / 0.405 / 0.381) | 0.392 | 18.0 / 46.7 / 10.3 |
| **HeTCo_v5 (threshold 0.3)** | 0.411 (0.418 / 0.435 / 0.380) | 0.397 | 22.0 / 26.0 / 7.0 |
| LR_hier_community (= its t1 variant) | 0.397 | 0.381 | 23.0 / 25.0 / 8.0 |
| A7v4 = A7v5 mean pool | 0.349 | 0.375 | 23.3 / 41.7 / 7.7 |
| B4_logreg | 0.361 | 0.378 | 29.0 / 3.0 / 6.0 |
| B5 HGB | 0.289 | 0.278 | 16.0 / 163.0 / 16.0 |

| Difference | Main community bootstrap | Rolling month blocks |
|---|---|---|
| HeTCo_v5 − HeTCo_v4 | +0.013, [−0.004, 0.028], 94% > 0 | [−0.014, 0.013], 51% > 0 |
| HeTCo_v5 − B4 | +0.050, [−0.029, 0.123], 88% > 0 | [−0.003, 0.037], 94% > 0 |
| HeTCo_v5 − LR_hier_community | +0.013, [−0.055, 0.086], 63% > 0 | [−0.022, 0.047], 87% > 0 |

The 0.1–beta overlap zone is the stratum where H1 predicted a gain (main):

| Model | Event recall (tier 1) | Dissolve false alarm | Macro-F1 |
|---|---:|---:|---:|
| HeTCo_v4 | 0.651 | 0.186 | 0.539 |
| HeTCo_v5 | 0.508 | 0.081 | 0.561 |

Verdict:

- **H1 is not supported in its predicted direction.** The selected point
  made the model *more* conservative. Event recall in the overlap zone fell
  and missed events rose from 18 to 22. The small Macro-F1 gain comes from
  fewer false events (46.7 → 26.0), not from recovering grow/merge. Grow → dissolve
  rose from 4.3 to 5.7, and merge → dissolve from 12.7 to 15.0.
- **The placebo stratum shows no spurious gain.** In the no-shared stratum,
  event recall went from 0.08 to 0.00.
- **The procedure does not transfer.** Mean pooling and hierarchical LR keep
  argmax. The attention choice rests on a 0.003 inner difference, and both
  v5 − v4 intervals include zero. Rolling months 07–09 were used for
  selection, so the rolling score is optimistic.
- **Seed instability drops but remains:** cases that change across seeds
  fall from 48 to 34 (main) and from 90 to 67 (rolling).
- **Hierarchical LR on community attributes nearly matches v4 on main**
  (0.397 vs 0.398), consistent with the 2016 controlled contrast where
  hierarchy carries the gain.

Decision: v4 stays the declared primary. v5 is reported as a pre-declared,
neutral-to-adverse ablation. No further threshold variants are run on this
pilot. Recovering tiny grow/merge cases needs information that is absent at
t (M1), not a different operating point.
