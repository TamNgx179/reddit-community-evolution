# Forecasting Structural Evolution of Reddit User Communities

**Midterm 1 research report**

We built a reproducible prototype from Reddit reply metadata to monthly user
networks, community detection, structural evolution labels and next-month
forecasts. The original frozen proposed model has higher Macro-F1 point
estimates than five named baselines in the original and first external cohorts.
A later predeclared replication on three newly acquired corpora tests a
35-field candidate without retuning. It scores 0.3631 versus 0.4044 for the
strongest baseline, so the earlier advantage does not establish general
superiority. The report separates predictive results, component evidence and
the validity of the operational structural labels.


## 1. Problem and research questions

At the end of month t, can we predict the structural event of an existing
community of interacting users in t+1? A community is a detected group of
accounts, **not a subreddit**, post, political identity or verified social group.
This addresses temporal community evolution in SNA. The intended application
is monitoring observed interaction groups, without inferring intent or causes.

- **RQ1:** Do past member activity and sustained replies add predictive value
  beyond current structure, predecessor history, context and current activity?
- **RQ2:** Does a two-stage disappearance/conditional-event forecast outperform
  direct classification on the same task?
- **RQ3:** How dependable are the measured groups/events, and where do forecasts
  fail across classes, months and cohorts?

The hypothesis is that communities with similar current size and density can
differ in repeated participation and interaction persistence. These differences
motivate features, they do not guarantee an improvement.

## 2. Dataset, scope and exact input/output

We use Reddit conversation corpora distributed through ConvoKit [1], [2], [7].
Raw fields are utterance ID, pseudonymous author, parent ID, conversation ID,
subreddit and UTC time. Comment text is not required for the proposed dynamics.
Incomplete thread histories and missing parents limit what the graph observes.

The original cohort contains 15 corpora: Ask_Politics, AskALiberal,
AskThe_Donald, AskTrumpSupporters, Conservative, democrats, EnoughTrumpSpam,
hillaryclinton, moderatepolitics, NeutralPolitics, Political_Revolution,
PoliticalDiscussion, Republican, SandersForPresident and socialism. Its
45 monthly snapshots span January 2015–September 2018 and include
**18,567,881 comment records** before graph-event exclusions. Monthly graphs
have **8,222–93,006 reply endpoints** and **27,221–693,866 unique undirected
edges**. Records, users, edges and community–month samples are distinct units.

| Original label-month partition | stable | grow | shrink | merge | split | dissolve | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Training | 11 | 54 | 82 | 192 | 102 | 4854 | 5295 |
| Validation | 1 | 14 | 18 | 22 | 25 | 846 | 926 |
| Final evaluation | 4 | 19 | 25 | 15 | 39 | 1167 | 1269 |

The external cohort contains AustralianPolitics, CanadaPolitics and ukpolitics:
975 development samples and 286 final samples. It is another political-discussion
collection, not a representative Reddit sample. External final supports are
stable 1, grow 8, shrink 14, merge 9, split 4 and dissolve 250.

**Forecast input:** current detected community C_t, its weighted reply graph,
known predecessor information, context/current activity, member activity and
interaction history through t. Past activity is computed on the fixed current
member set. **Output:** probabilities for six next-month events and the largest-
probability event. Probability calibration is not established. Future t+1
observations construct evaluation labels only, they never enter input features.

![Prototype data flow](figures/temporal-study-001/flow.png)

*Figure 1. End-to-end prototype. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

## 3. Network construction

1. A valid reply in UTC month t adds directed weight from its author u to the
   parent author v. Repeated replies add weight, a parent may be older than t.
2. Reject invalid authors, self-replies, missing parents and parents timestamped
   after their replies. Deduplicate IDs, reject inconsistent duplicates and
   record exclusions/coverage. Overlapping loss counters are not disjoint totals.
3. Detect on the undirected projection R_t(u,v)=w_t(u,v)+w_t(v,u). Nodes are
   accounts incident to a valid reply. Do not build a clique from thread members
   or include isolated accounts as if they had observed interactions.
4. Original measurement uses independent monthly weighted RB Leiden, gamma=1,
   canonical seed 0 [3]. Seeds 1/2 measure repeatability, not ground truth. Link
   communities afterward, community IDs are local to a snapshot.

For example, three replies A→B and one B→A give R_t(A,B)=4. A reply B→C
with unresolved parent contributes no edge. Thus the graph represents observed
reply interaction, not friendship. All original graph/label choices remain fixed.

![Observed community graph](figures/temporal-study-001/community_graph.png)

*Figure 2. Quotient graph of detected groups. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

The display shows at most 20 largest groups and 40 strongest between-group links.
This visual filter does not filter experiment samples. It is not social validation.
Graphs are streamed month by month from indexed metadata. Original model-study
peak sampled process-tree RSS was 1.08 GiB. Bounds are 8 GiB RSS,30 GiB working
space and 12 GiB free disk, one-second sampling can miss brief peaks.

## 4. Labels: origin, rules and limits

Reddit provides **no native community-evolution labels**. Targets are operational
pseudo-labels from our documented GED adaptation [4]. For groups A and B:

$$I(A,B)=\frac{|A\cap B|}{|A|}\frac{\sum_{u\in A\cap B}q_A(u)}{\sum_{u\in A}q_A(u)}.$$

Here q_A is internal weighted degree, with unit fallback for a zero-degree
member. Accept a link if either directional inclusion is at least 0.5.

| Event | Operational rule |
|---|---|
| split | More than one accepted successor, without a many-to-many conflict |
| merge | One accepted successor with multiple accepted predecessors |
| grow / shrink / stable | One-to-one link, successor size larger / smaller / exactly equal |
| dissolve | No accepted link and every directional overlap below 0.1 |
| unresolved | Weak overlap or a many-to-many conflict, excluded from six-class forecasting |
| censored | No observed successor snapshot, not an event class |

**Worked example:** two four-person groups sharing three equally important
members have directional inclusion(3/4)²=0.5625. If linked one-to-one they are
`stable` because their sizes match, although a member changed. `Dissolve` means
insufficient next-month observed continuity, not verified disappearance of a
social group. Future births are outside a forecast about an existing C_t.

Original observation has 11,562 source transitions with a next snapshot:
4072 are unresolved(35.22%). Forecast results apply to the resolved 64.78%.
External final observation has 477 transitions:286 resolved and 191 unresolved,
39 last-snapshot groups are censored separately. No weak-overlap cases are
forced into classes to improve scores.

This target is reproducible, but social validity is unestablished. Genuine human
review is incomplete. A development follow-up finds later accepted candidates
for 20/2450 original and 12/781 external three-month-observed dissolve cases,
these are candidate membership matches, not verified group identities. Missing
coverage remains unknown. Separate controlled measurement investigations also
found weaknesses in detection-to-label recovery, repeatability is not validity.
Those exploratory investigations did not justify replacing the frozen reference.

## 5. Baselines and proposed forecast

Feature groups are current structure(S), known history(H), subreddit context(L),
current activity(A), and past activity/interaction dynamics(D). A subreddit is a
context, never the target community. Related work already uses historical
community features [6], [9], we do not claim to invent community forecasting.

| Method | Input and purpose |
|---|---|
| B1 Majority | Training-label majority, frequency sanity check |
| B2 Persistence | Last known predecessor event, majority fallback |
| B3 Flat logistic regression | S+H+L+A+D, direct six-class baseline |
| B4 Hierarchical HGB static | S+H+L+A, strong nonlinear baseline |
| B5 Hierarchical HGB dynamic | S+H+L+A+D, strong nonlinear matched-input baseline |
| Proposed hierarchical LR dynamic | S+H+L+A+D, interpretable two-stage forecast |
| Ablation: proposed without D | Same selected primary settings, remove D only |

The proposed first head estimates dissolve versus other. The second estimates
stable/grow/shrink/merge/split conditional on other, multiply by the first head's
other probability to obtain the six-event vector. Scaling uses training folds
only. Dynamics include returning members and sustained replies from observed
past months, with explicit missing-history indicators. This is an implemented
feature/hierarchy design, not a full HeTCo or graph-neural reproduction [10].

Five baseline roles are retained. More complex or failed exploratory methods
are diagnostics, not extra headline baselines or replacements selected on test.
This seven-row view is a retrospective reduction of the broader archived
study. Dynamic HGB was originally an alternative architecture and is now
reported as a strong control. The original primary and validation champion
remain unchanged, this is not a new preregistered five-baseline experiment.

## 6. Experimental plan and fair evaluation

Original training label months:February 2015–June 2017. Six expanding validation
origins:July–December 2017. Refit throughDecember 2017, then freeze before
January–September 2018 evaluation. No random row split, future-feature access or
final-label refitting [5]. External settings were copied before its final-period
evaluation and fitted on its pre-2018 data, without a new hyperparameter search.
These periods are now exposed, subsequent reuse is exploratory, not a fresh test.

Primary metric is Macro-F1 over a fixed six-class list, absent classes scoring 0.
All methods within each cohort/reference predict the same keys, dates and labels.
Report support/per-class F 1, confusion, monthly/size strata and paired uncertainty.
Seeds 42/43/44 measure estimator variation, not independent temporal replications.
Paired bootstrap uses three-month blocks,2000 draws and fixed seed 2026 [8].

| Experiment | Question answered |
|---|---|
| Five baseline comparison | Does proposed beat simple and strong alternatives on the same task? |
| Matched no-dynamics ablation | Is added history useful with primary settings fixed? |
| External cohort | Does the observed advantage transfer to another corpus collection? |
| Class/month/coverage audits | Which failures are hidden by an aggregate score? |
| Label observability and coverage audit | How much of the detected population is labeled, unresolved or censored? |

The original archived search used 480 configuration-fold evaluations. The
subsequent compact forward declaration has four tuned families×eight settings×
six validation origins=192 evaluations. This smaller budget is not retroactively
claimed for the historical run. The no-D control is matched, not an independently
retuned best static LR. Complete selections/results remain in the notebook.

## 7. Measured Reddit results

| Method | Original Macro-F1 | External Macro-F1 |
|---|---:|---:|
| B1 Majority | 0.1597 | 0.1555 |
| B2 Persistence | 0.1562 | 0.1550 |
| B3 Flat LR dynamic | 0.3616 | 0.3451 |
| B4 Hierarchical HGB static | 0.3728 | 0.2900 |
| B5 Hierarchical HGB dynamic | 0.3880 | 0.3500 |
| **Proposed hierarchical LR dynamic** | **0.4117** | **0.3690** |
| Matched proposed without D | 0.3643 | 0.3777 |

Proposed exceeds the strongest named baseline by+0.0237 original and+0.0190
external. However, paired strongest-baseline 95%intervals are[-0.0828,+0.0984]
and[-0.2631,+0.2101]. Both include 0, **stable superiority is not demonstrated**.
The original validation champion was HGBstatic: the proposed difference against
that preselected comparator is+0.0390, interval[+0.0056,+0.0744]. This narrower
positive comparison does not establish a win against the strongest alternative.

![Frozen forecast comparison](figures/temporal-study-001/comparison.png)

*Figure 3. Frozen forecasts on identical original-cohort cases. Source: [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

Original proposed wins 5/9 months against the strongest reference. Its per-class
F 1 is stable 0.0000, grow 0.0968, shrink 0.4444, merge 0.2308, split 0.7397 and
dissolve 0.9587. Dissolve accounts for 91.96%of final samples, stable has only 4.
External no-D(0.3777)exceeds proposed(0.3690), so the dynamic mechanism is not
confirmed across cohorts. Neither a high aggregate score nor more raw comments
solves sparse-event support. Probabilities, human validity and novelty remain
unconfirmed, labels should be defended as measured structural events only.

## 8. Prototype, conclusions and next evidence

The prototype runs end-to-end: Reddit metadata → audited monthly reply graph →
Leiden communities → GED-adapted structural labels → past-only features →
five baseline methods and proposed hierarchical LR → matched evaluation.
The [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb)
contains the original and external-cohort results, graph/label diagnostics,
class supports, confusion and temporal comparisons. See the
[runbook](../docs/RUNBOOK.md) for environment setup and the original pipeline.

The retained proposed model has higher point Macro-F1 than the five named
baselines in both cohorts. It does **not** establish stable superiority:
strongest-baseline intervals include zero, and the no-dynamics ablation is
better externally. This is preliminary evidence, not a validated dynamic
mechanism, independent social ground truth or established methodological novelty.

| Instructor concern | Implemented evidence | Remaining limit |
|---|---|---|
| Problem and input/output | Next-month six-event forecast of existing user communities | No social intent or causal inference |
| Graph construction | Reply endpoints, weights, projection and Leiden rules with an example | Missing parents and resolution sensitivity |
| Label meaning | Explicit GED-adapted pseudo-label rules, worked example and excluded cases | Genuine social validity/human review incomplete |
| Why these experiments | Simple/strong same-task controls, matched ablation, external cohort and error analysis | Exposed periods cannot become new independent tests |
| Proposed contribution | Hierarchical forecast and activity/history features | Dynamic contribution does not transfer consistently |
| Dataset size | Completed streamed monthly processing and measured resource use | Rare-event support remains small |

Exploratory alternatives did not justify replacing the retained primary. Their
negative findings and evidence remain archived locally, they are not claimed
as improvements. The current notebook/source focus on the six-event pipeline.

The next research priorities are genuine blind label assessment, validated
measurement of rare transitions, and an evaluation cohort frozen before its
outcomes are inspected. More tuning on the same exposed periods does not
replace these checks.

## 9. Controlled component evidence

The finite comparison inventory was declared before this supplementary run.
Every configuration uses the primary LR settings (C=1, balanced class weighting,
standard scaling and max_iter=3000), seeds 42/43/44 and the same sample keys.
A2 changes only flat versus two-head organization. A1 removes all nine D fields.
The five grouped deletions remove member-return, activity-growth, repeated-dyad,
context-drift or observation/coverage fields separately. Behavioral deletions
retain the observation flags. The controls are ablations, not extra baselines.

Six expanding development origins cover July to December 2017. Final refits
use data through December 2017 and predict January to September 2018 without
refitting on those outcomes. Both periods were already exposed before this
supplementary study. No new primary is selected from these results.

| Configuration | Original development | Original final | External development | External final |
|---|---:|---:|---:|---:|
| full | 0.4350 | 0.4117 | 0.2712 | 0.3690 |
| A1_no_D | 0.3967 | 0.3643 | 0.2840 | 0.3777 |
| A2_flat_matched | 0.3338 | 0.3321 | 0.2809 | 0.3142 |
| without_member_return | 0.4239 | 0.3673 | 0.2533 | 0.3680 |
| without_activity_growth | 0.4394 | 0.4134 | 0.3124 | 0.3894 |
| without_repeated_dyads | 0.4150 | 0.3980 | 0.3082 | 0.3851 |
| without_context_drift | 0.4271 | 0.4255 | 0.2740 | 0.3657 |
| without_observation_flags | 0.4428 | 0.4126 | 0.2935 | 0.3551 |

Scores are means over three algorithm seeds. Historical full-primary and A1
final predictions were reproduced exactly before interpreting component effects.
The following differences are full minus the named control. Positive values
favor the full configuration. Intervals use the same paired three-month block
resamples for every comparison, 2000 draws and bootstrap seed 2026. These are
descriptive, unadjusted intervals across a finite set of comparisons, not a
new independent confirmation or a causal attribution to social mechanisms.
The six-month development window is too short for the declared minimum of
three block lengths, so its interval is explicitly unavailable.

| Cohort | Control | Full minus control | Descriptive 95% interval | Months full higher |
|---|---|---:|---|---:|
| original | A1_no_D | +0.0474 | [-0.0124, +0.0955] | 6/9 |
| original | A2_flat_matched | +0.0796 | [+0.0291, +0.1106] | 7/9 |
| original | without_member_return | +0.0445 | [-0.0160, +0.0916] | 5/9 |
| original | without_activity_growth | -0.0017 | [-0.0333, +0.0016] | 2/9 |
| original | without_repeated_dyads | +0.0137 | [-0.0116, +0.0272] | 3/9 |
| original | without_context_drift | -0.0138 | [-0.0375, +0.0012] | 1/9 |
| original | without_observation_flags | -0.0009 | [-0.0072, +0.0015] | 0/9 |
| external | A1_no_D | -0.0087 | [-0.0180, +0.0287] | 2/9 |
| external | A2_flat_matched | +0.0548 | [-0.0332, +0.0983] | 6/9 |
| external | without_member_return | +0.0010 | [-0.0191, +0.0350] | 3/9 |
| external | without_activity_growth | -0.0204 | [-0.0631, -0.0166] | 2/9 |
| external | without_repeated_dyads | -0.0161 | [-0.0521, -0.0088] | 1/9 |
| external | without_context_drift | +0.0033 | [-0.0031, +0.0056] | 1/9 |
| external | without_observation_flags | +0.0139 | [-0.0010, +0.0407] | 3/9 |

With settings matched, the two-head model exceeds flat LR by
+0.0796 original and
+0.0548 external Macro-F1.
The original descriptive interval is positive, while the external interval
includes zero. This better isolates organization of the classifier than B3,
whose independently selected hyperparameters differed from the primary.

Removing member-return fields reduces original final Macro-F1 from
0.4117 to
0.3673, but changes the external
score from 0.3690 to
0.3680. Removing activity-growth
fields instead gives 0.4134
original and 0.3894 external.
Thus the nine D fields do not have a uniform benefit. These observations support
a targeted follow-up of behavioral history and coverage rather than treating
all dynamic features as one confirmed mechanism. They do not authorize choosing
a replacement primary from exposed final results.


The same graph, operational labels and five headline baseline roles remain in
force. Group deletion measures conditional usefulness at fixed settings and can
reflect redundancy between features. Observation flags measure coverage rather
than a social interaction mechanism. Per-class support and monthly predictions
are retained with every configuration. Blinded development cases and blank
review forms are available locally. Verified rule consistency and automated
coverage checks are reported as automation, not completed human assessment.
Both cohorts in this component study are recorded as exposed. Their results
motivate the pre-acquisition protocol and separate replication in Section 10.
They do not themselves constitute an untouched evaluation or human agreement.

## 10. Predeclared new-cohort replication

### Design and candidate rationale

The supplementary component study motivated a candidate that removes only
record_log_growth and reply_log_growth. It retains 35 of the original 37 fields,
including member-return history, repeated interactions, context drift and
observation indicators. Its two-head LR uses C=1, balanced class weighting and
training-only standard scaling. This candidate and every comparator were fixed
before downloading Anarchism, Libertarian and GreenParty from Cornell.
These corpora had not been used in the recorded project studies. Prior exposure
by other team members is uncertified and users may overlap earlier collections.

Acquisition records observed SHA-256 and ZIP CRC checks. Development metadata,
graphs and labels end before January 2018. Models fit pre-2018 targets and freeze
before January to September 2018 graphs and outcome labels are constructed.
The development prefix is verified unchanged after extension. Graph, Leiden,
GED-adapted label rules and six event order remain consistent with the earlier
study. All methods share one reference, eligible sample set and context schema
inside this cohort. There is no new hyperparameter search or outcome-based
corpus substitution. Raw archives and private assessment cases remain local.

### Measured results

The new collection contributes 1577 resolved pre-2018 training transitions
and 493 resolved final transitions out of
746 observed final source transitions. Its final
resolved fraction is 66.09%. The remaining
253 observed transitions are unresolved and
are not forced into the six classes. There are 90 separately
censored last-snapshot groups. Raw archive size is an acquisition statistic,
not the number of independent training or evaluation samples.

| Configuration | New-cohort Macro-F1 |
|---|---:|
| B1_majority | 0.1576 |
| B1_persistence | 0.1526 |
| flat_lr_dynamic | 0.2789 |
| hier_hgb_static | 0.3214 |
| hier_hgb_dynamic | 0.4044 |
| hier_lr_dynamic | 0.3646 |
| A_no_dynamics_matched | 0.3320 |
| hier_lr_pruned_growth | 0.3631 |
| A_flat_pruned_matched | 0.3190 |

Scores average algorithm seeds 42/43/44. Candidate minus strongest realized
named baseline (hier_hgb_dynamic) is -0.0413, with
descriptive paired 95% interval [-0.0685, +0.0159], and a higher monthly score in
5/9 months. The primary comparator
was predeclared as dynamic HGB. The realized strongest alternative is identified
after evaluation for transparent reporting. Intervals are unadjusted exploratory
time-block comparisons, not a correction for choosing the strongest after evaluation.
Old final scores are not pooled with this new cohort and no model is replaced
because of the new final outcomes.

Candidate minus the original 37-field hierarchical LR is
-0.0014, with descriptive 95% interval [-0.0054, +0.0073].
This direct comparison tests whether removing activity-growth fields transfers
to the new collection, separately from whether either version beats a named
baseline. Both versions and all disagreements remain in the result inventory.

| Event | New-cohort support | Candidate F1 | Original full F1 | Strongest baseline F1 |
|---|---:|---:|---:|---:|
| stable | 0 | 0.0000 | 0.0000 | 0.0000 |
| grow | 7 | 0.1739 | 0.1739 | 0.3636 |
| shrink | 34 | 0.3194 | 0.3158 | 0.3488 |
| merge | 0 | 0.0000 | 0.0000 | 0.0000 |
| split | 10 | 0.8421 | 0.8421 | 0.8000 |
| dissolve | 442 | 0.8434 | 0.8557 | 0.9140 |

Per-class F1 averages the same three seeds. Support counts transitions once.
Unresolved and censored populations remain in the source audit denominators.
Operational labels describe measured structural continuation, not independent
social ground truth. Technical rule checks and case-based structural assessment
are separate from completed independent human validation.

### Source-bound structural case audit

A fixed-seed development panel contains 21 cases, sampled across
available event and unresolved strata. A technical assessment records the
source size, overlapping target count, largest observed overlap, a confidence
level and an evidence-based rationale for every case. Judgments were supplied
before opening the coordinator answer key, and model predictions were not shown.
The sealed assessment has explicit non-human provenance. Its concordance with
the operational tracker is 0.714, with
6 discrepancies retained for inspection. This is a
technical consistency/plausibility check, not population accuracy, inter-human
agreement or independent social ground truth. It does not replace actual human
validation. All six discrepancies are growth/merge cases assessed as unresolved:
the supplied marginal overlap summaries do not establish all accepted incoming
links needed to distinguish growth from absorption. They are retained as
uncertainty about interpretation, not counted as proven tracker errors.
Small fragment-based split/shrink cases also require a structural reading,
rather than a claim about deliberate social reorganization. Private cases,
submitted rationales and coordinator keys stay local.

### Measured computational feasibility

The 5 completed monitored phases used a maximum
one-second sampled process-tree RSS of
0.499 GiB. Their summed wall time was
2846.4 seconds, including acquisition,
normalization and graph work. This is an observed run on the recorded machine,
not a cross-model training-speed comparison or a guarantee about unsampled
allocation peaks. Numeric stores and monthly processing bound memory without
equating the raw archive size with the number of independent target events.

## References

[1] CornellNLP, “Reddit Corpus (by subreddit),” ConvoKit documentation. [Online]. Available: [corpus documentation](https://convokit.cornell.edu/documentation/subreddit.html).

[2] J. Baumgartner et al., “The Pushshift Reddit Dataset,” Proceedings of ICWSM, vol.14, pp.830–839,2020. [doi:10.1609/icwsm.v14i1.7347](https://doi.org/10.1609/icwsm.v14i1.7347).

[3] V. A. Traag, L. Waltman, and N. J. van Eck, “From Louvain to Leiden: Guaranteeing well-connected communities,” Scientific Reports, vol.9, Art.5233,2019. [doi:10.1038/s41598-019-41695-z](https://doi.org/10.1038/s41598-019-41695-z).

[4] P. Bródka, S. Saganowski, and P. Kazienko, “GED: The method for group evolution discovery in social networks,” Social Network Analysis and Mining, vol.3, pp.1–14,2013. [doi:10.1007/s13278-012-0058-8](https://doi.org/10.1007/s13278-012-0058-8).

[5] Scikit-learn developers, “Cross-validation: Evaluating estimator performance.” [Online]. Available: [documentation](https://scikit-learn.org/stable/modules/cross_validation.html).

[6] S. Saganowski et al., “Predicting Community Evolution in Social Networks,” Entropy, vol.17, pp.3053–3096,2015. [doi:10.3390/e17053053](https://doi.org/10.3390/e17053053).

[7] J. P. Chang et al., “ConvoKit: A Toolkit for the Analysis of Conversations,” Proceedings of SIGDIAL,2020. [Paper](https://www.cs.cornell.edu/~cristian/ConvoKit_Demo_Paper_files/convokit-demo-paper.pdf).

[8] H. R. Künsch, “The Jackknife and the Bootstrap for General Stationary Observations,” The Annals of Statistics, vol.17, no.3, pp.1217–1241,1989. [doi:10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265).

[9] M. Takaffoli, R. Rabbany, and O. R. Zaiane, “Community Evolution Prediction in Dynamic Social Networks,” ASONAM, 2014. [Author manuscript](https://webdocs.cs.ualberta.ca/~zaiane/postscript/evolution-ASONAM14.pdf).

[10] M. Revelle, C. Domeniconi, and M. Gelman, “Group-Node Attention for Community Evolution Prediction,” 2021, doi: [10.1145/3487351.3488348](https://doi.org/10.1145/3487351.3488348). [Author manuscript](https://arxiv.org/abs/2107.04522).
