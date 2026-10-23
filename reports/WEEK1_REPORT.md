# Forecasting Structural Evolution of Reddit User Communities

**Midterm research report**

## Executive summary

We implemented an end-to-end prototype that converts observed Reddit replies into monthly user networks, detects communities, derives structural evolution labels and forecasts each existing community's next-month event. The research question is whether past member activity and sustained interaction add predictive value beyond current structure and activity, and whether a two-stage forecast helps with the highly imbalanced event distribution.

The verified run contains **45 monthly snapshots**, **5,295 training**, **926 validation** and **1,269 final-evaluation community–month samples**. The frozen proposed model scores **0.4117 six-class Macro-F1** versus **0.3880** for the strongest of the five reported baselines. This is a preliminary improvement on an algorithm-derived structural target, not proof of accurate social-community prediction. Rare events and unresolved transitions remain central limitations.

## 1. Problem, motivation and research questions

The unit of interest is a **community of interacting users detected in a network**, rather than a subreddit, post or individual account. At the end of month t, can information already available predict whether that community will retain its size, grow, shrink, merge, split or lose meaningful observed continuity in t+1? This directly addresses temporal community evolution in SNA. The intended use is monitoring observed community continuity; the system does not infer political affiliation, social intent or causal mechanisms.

- **RQ1 — Dynamic information:** Do returning-member activity and sustained replies add value beyond structure, predecessor history, subreddit context and current activity?
- **RQ2 — Forecast architecture:** Does separating observed disappearance from the other events outperform a direct classifier with the same features?
- **RQ3 — Robustness:** Where does improvement hold across months, classes and community sizes, and how sensitive is the measurement to graph/label choices?

The working hypothesis is that equally large and dense communities may differ in repeated participation and interaction persistence. These measurable differences motivate the features; they do not guarantee better forecasts.

## 2. Exact task: input, output and information boundary

**Raw input:** utterance ID, author pseudonym, parent-reply ID, conversation/thread ID, subreddit and UTC timestamp from the ConvoKit Reddit corpus [1], [2], [7]. Text and eventual popularity are not required for the proposed activity features.

**Model input:** one community C_t detected at the end of t, its current weighted reply structure, predecessor information already known at t, and member activity/replies in t and up to three earlier observed months. Historical activity is computed on the fixed current member set C_t. No t+1 memberships, replies or target labels enter a forecast feature.

**Output:** a six-element probability vector and its highest-probability event for C_t at t+1. At evaluation time, the forecast is compared against the structural label derived after observing t+1. Probabilities have not been established as calibrated. Future graph observations are used to construct evaluation targets, never as prediction inputs.

![System flow](figures/temporal-study-001/flow.png)

*Figure 1. Forecasting pipeline. Source: [executed study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

## 3. Dataset and feasibility

The observed collection comprises **15 subreddit corpora**: AskALiberal, AskThe_Donald, AskTrumpSupporters, Ask_Politics, Conservative, EnoughTrumpSpam, NeutralPolitics, PoliticalDiscussion, Political_Revolution, Republican, SandersForPresident, democrats, hillaryclinton, moderatepolitics, socialism. This is a topic-biased observational collection, not a representative sample of all Reddit. A user can participate in several subreddits; a subreddit is an activity context, not a ground-truth community label. The source documentation also warns that incomplete thread histories and duplicate processing entries can occur [1]. Our normalizer deduplicates record IDs, rejects inconsistent duplicates and records graph losses.

Across the study snapshots there are **18,567,881 comment records** before graph-event exclusions, **8,222–93,006 monthly reply endpoints**, and **27,221–693,866 unique undirected edges per month**. Comment records, account endpoints, edges and labeled community–months are different units; their counts must not be conflated. Parent records may predate the first study month and are retained for reply resolution rather than treated as extra forecast samples.

| Label-month partition | stable | grow | shrink | merge | split | dissolve | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| Training | 11 | 54 | 82 | 192 | 102 | 4854 | 5,295 |
| Validation | 1 | 14 | 18 | 22 | 25 | 846 | 926 |
| Final evaluation | 4 | 19 | 25 | 15 | 39 | 1167 | 1,269 |

Metadata are streamed into an indexed local store and graphs are processed month by month. We do not generate a quadratic clique among all users in a thread. Runtime stops enforce the declared 30 GiB working budget, 8 GiB sampled process-tree RSS ceiling and 12 GiB minimum free disk. The maximum RSS recorded in completed phases is **1.08 GiB**; one-second monitoring can miss brief peaks. These measurements support feasibility on the observed collection, not unlimited scaling.

## 4. Network construction before forecasting

1. For each valid reply written in UTC month t, add a directed interaction from its author u to the parent author v. The parent timestamp must not exceed the reply timestamp. Count repeated replies as weight.
2. Exclude self-replies, invalid authors, missing parents and temporally invalid links from graph edges, recording the exclusions and coverage. Loss incidence counters may overlap and should not be summed as disjoint records.
3. Detect communities on the weighted undirected projection **R_t(u,v)=w_t(u,v)+w_t(v,u)**. A node is a pseudonymous account incident to a valid reply; accounts without a valid edge are counted separately.
4. Run independent weighted Leiden with the RB objective, resolution gamma=1 and canonical seed0 [3]. Seeds1/2 are measurement diagnostics, not additional independent datasets. Communities are detected independently each month and linked afterward.

![Network scale](figures/temporal-study-001/graph_scale.png)

*Figure 2. Monthly network scale and reply coverage. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

![Observed community network](figures/temporal-study-001/community_graph.png)

*Figure 3. Observed community interaction graph. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

Figure 3 is a quotient graph of up to the twenty largest detected communities, showing up to forty strongest between-community reply links. The display filter does not remove communities, edges or samples from the experiment. It illustrates the measured network, not an independent validation of social groups.

## 5. Labels: definition, generation and validity

Reddit supplies **no native community-evolution class labels**. We create **GED-adapted operational pseudo-labels** using consecutive detected partitions [4]. For source A and successor B, weighted inclusion is

$$I(A,B)=\frac{|A\cap B|}{|A|}\frac{\sum_{u\in A\cap B}q_A(u)}{\sum_{u\in A}q_A(u)}.$$

Here q_A(u) is internal weighted degree, replaced by 1 if zero. A link is accepted if either directional inclusion reaches 0.5. This is our documented adaptation, not a claim to reproduce every original GED rule.

| Target | Exact operational rule |
|---|---|
| split | More than one accepted successor, without a many-to-many conflict |
| merge | One accepted successor with more than one accepted predecessor |
| grow / shrink / stable | One-to-one link; successor size is larger / smaller / equal |
| dissolve | No accepted link and no overlap with directional inclusion reaching 0.1 |
| unresolved, excluded from classification | Weak-overlap ambiguity or a many-to-many conflict |
| censored, not a class | Last snapshot has no observed successor month |

**Worked example, synthetic:** if two equally important four-person groups share three members, each directional inclusion is(3/4)×(3/4)=0.5625. A one-to-one link receives `stable` because sizes match, even though a member changed. Thus stable means equal observed size, not unchanged membership. Dissolve means loss of sufficient observed inclusion, not verified social disappearance. Forming is outside this source-community task because a newly born future community has no existing C_t to forecast from.

The audit records **11,562 source transitions with an observed next snapshot**, including **4,072 unresolved (35.22%)**. Classification results therefore apply to the **64.78%** with resolvable labels, not all detected transitions. Missing data, monthly aggregation and detector resolution may influence labels. Automated recomputation checks rule consistency; two-person blinded review forms exist, but **human annotation and agreement are still pending**. The labels are suitable for a clearly bounded structural forecasting experiment; their social validity remains unestablished.

Development-only sensitivity: threshold 0.4: 5/1,652 changed source-transition labels; threshold 0.6: 4/1,652 changed source-transition labels. On the measured development graph, gamma=0.5: ARI=0.501, gamma=1.5: ARI=0.403. These checks do not retune the forecast target or demonstrate robustness under every network construction. In particular, resolution sensitivity remains a limitation.

## 6. Evaluation plan and why each experiment exists

Training label months are February 2015–June 2017. Six expanding validation origins cover July–December 2017; each fit uses only earlier labels. After choosing settings, models are refitted through December 2017 and frozen before evaluating January–September 2018. Scalers and class weights learn only from training folds. There is no random row split and no model refitting on final labels [5].

**Primary metric:** Macro-F1 with a fixed six-class list and zero_division=0. We retain absent/rare classes in the metric and report per-class F1/support, confusion, monthly and size-stratum results. All methods predict identical sample keys, targets and dates. Three estimator seeds measure algorithm variability, not independent temporal replications.

| Experiment | Scientific purpose |
|---|---|
| B1 Majority and B2 Persistence | Establish frequency and temporal-repeatability reference levels |
| B3 Flat LR, same full features | Isolate the hierarchy comparison within a linear model family |
| B4 Hierarchical HGB static | Compare with the original strong champion already given current activity |
| B5 Hierarchical HGB dynamic | Test whether the proposed advantage survives a nonlinear model with the same full inputs |
| Proposed without D, settings fixed | Check the contribution of activity/interaction dynamics |
| Class, month, size and measurement diagnostics | Identify where the aggregate improvement does and does not hold |

The compact forward protocol has **five baselines, one proposed model and one ablation**. Four tuned families receive eight configurations and the same six origins: **192 configuration–fold evaluations**. Two-head configurations fit up to two estimators per evaluation, so192 is not a count of individual head fits. Majority/Persistence have fixed rules; the ablation reuses selected primary settings. This replaces the original480 configuration–fold design without adding new test-driven searches.

The submitted seven-configuration view is a retrospective reduction of a completed broader study. The original primary, predictions, validation champion and full archived results are retained. HGB dynamic was an alternative architecture in that study and is now explicitly treated as a strong nonlinear reference. This role change is disclosed; it is not a new preregistered comparison or an independent rerun.

The original validation champion remains **hier_hgb_static**. A paired moving-block bootstrap uses three-month blocks,2,000 draws and a fixed seed, following the time-block resampling principle [8], with pooled confusion matrices and mean-over-seed F1 differences. The nine-month interval is exploratory. We additionally compute the same descriptive contrast against the stronger expanded reference, clearly distinguishing it from the original frozen primary comparison. Past post-2015 outcome exposure has not been independently certified; the chronology alone does not establish an untouched confirmation set.

## 7. Proposed method and relation to prior work

Feature groups are **S**(current structure), **H**(community history), **L**(known predecessor state), **C**(subreddit activity context), **A**(current member activity/replies) and **D**(past activity and interaction dynamics). Static uses S+H+L+C+A; dynamic adds D. D includes returning-member fraction, observed active-month fraction, log changes in records and internal replies, repeated dyads and subreddit-distribution drift. Empty or missing histories carry explicit flags; missing observations are not proof of inactivity.

The proposed **hierarchical Logistic Regression with dynamics** first predicts P(dissolve). A second Logistic Regression predicts the other five classes conditional on non-dissolution. Composition uses P(event)=(1−P(dissolve))P(event|non-dissolve), with an explicit dissolve probability and fixed-class argmax. Single-class or empty-conditional training folds use documented training-only fallbacks. The selected primary setting is **estimator=lr, C=1.0, class_weight=balanced, transform=standard**; model outputs are not claimed to be calibrated.

The two-stage design is motivated by a common disappearance event and heterogeneous surviving-community transitions. It is still evaluated against the same-input flat LR and nonlinear hierarchical controls, rather than assumed to help. The no-D ablation fixes selected primary settings; it measures that fitted design's dependence on D, not the best possible independently retuned static LR.

GED provides the structural-event framework [4]. Prior work already predicts community evolution from historical states [6]. We therefore claim an implemented and measured activity/interaction feature design on this observed Reddit task, **not invention of community-evolution prediction, a complete HeTCo implementation, or established methodological novelty**. More complex representation models are future comparators, not methods already reproduced here.

## 8. Measured results and interpretation

| Method | Six-class Macro-F1, mean of three seeds | Why it is included |
|---|---:|---|
| B1 Majority | 0.1597 | Most frequent training label; minimum sanity check |
| B2 Persistence | 0.1562 | Known predecessor event; training-majority fallback |
| B3 Flat LR + dynamics | 0.3616 | Same full inputs, direct six-class prediction; tests hierarchy |
| B4 Hierarchical HGB static | 0.3728 | Strong original validation champion; already includes current activity |
| B5 Hierarchical HGB + dynamics | 0.3880 | Same full inputs and hierarchy; strong nonlinear reference |
| Proposed hierarchical LR + dynamics | 0.4117 | Two-stage linear forecast with interpretable past-activity features |
| Ablation: proposed without D | 0.3643 | Same selected primary settings, removing dynamic features only |

The frozen proposed model exceeds the strongest reported baseline **hier_hgb_dynamic** by **+0.0237**. Against the original validation champion, its difference is **+0.0390**, with 95% paired interval **[+0.0056, +0.0744]**. The secondary strongest-reference interval is **[-0.0828, +0.0984]**; its automatic descriptive criterion is **not_demonstrated**. A higher point estimate alone must not be described as confirmed superiority if this interval includes zero. These are preliminary observed-cohort results with rule-derived labels.

![Method comparison](figures/temporal-study-001/comparison.png)

*Figure 4. Five baselines, proposed and ablation. Source: [executed study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

![Monthly results](figures/temporal-study-001/monthly.png)

*Figure 5. Monthly generalization. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

The proposed method wins **5/9** observed months against the strongest expanded reference. It is not uniformly superior over time.

### 8.1. Rare classes and errors

| Event | Final support | Proposed F1, mean seeds | Strongest-reference F1, mean seeds |
|---|---:|---:|---:|
| stable | 4 | 0.0000 | 0.0000 |
| grow | 19 | 0.0968 | 0.1277 |
| shrink | 25 | 0.4444 | 0.4667 |
| merge | 15 | 0.2308 | 0.1132 |
| split | 39 | 0.7397 | 0.6567 |
| dissolve | 1167 | 0.9587 | 0.9640 |

Dissolve accounts for **91.96%** of final samples. Stable has only **4** final cases. The headline metric must therefore be read with the class table: the current system cannot be presented as reliably forecasting all six events. Better aggregate performance does not resolve rare-class validity or guarantee useful forecasts for growth/stability.

![Class support](figures/temporal-study-001/support.png)

*Figure 6. Class support by temporal split. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

![Proposed confusion](figures/temporal-study-001/confusion.png)

*Figure 7. Proposed confusion matrix, seed42. Source: [study notebook](../notebooks/core/05_temporal_activity_study.ipynb).*

### 8.2. Component and size diagnostics

Removing D at fixed settings changes Macro-F1 from **0.4117** to **0.3643**. Same-input flat LR achieves **0.3616**. These contrasts support investigating activity dynamics and hierarchy on this cohort; they do not establish social causality or a separately significance-tested contribution for every component.

| Source-community size | Proposed Macro-F1 | Strongest-reference Macro-F1 |
|---|---:|---:|
| 2 or fewer members | 0.2078 | 0.1967 |
| 3–9 members | 0.2396 | 0.2148 |
| 10 or more members | 0.3474 | 0.3414 |

Each size bucket retains the fixed six-class metric, so class absence and composition affect its score. Size-stratum results are descriptive, not independent validation datasets. No small-community exclusion was introduced to improve the headline result.

## 9. Prototype, reproducibility and midterm status

The runnable path is **raw archives → normalized metadata → monthly graphs → Leiden partitions → audited event labels → causal features → temporal selection/freeze → prediction/evaluation → report/notebook**. The CLI stages are normalize-development, develop, select, evaluate and report. Completed stages carry hashes; incomplete/failed attempts are retained, and verified completed months can be resumed. The evaluation gate rejects source/config/model drift after selection. Historical run readers validate saved targets, probability vectors and metrics without loading model pickles.

The [executed notebook](../notebooks/core/05_temporal_activity_study.ipynb) contains code, saved metric output and all seven figures. [README](../README.md) and the [runbook](../docs/RUNBOOK.md) document environment and execution. A fresh checkout needs the documented raw data/environment and either a completed local run or an explicit new run; saved GitHub notebook output is a static evidence snapshot, not a hosted executable service.

| Midterm requirement | Evidence and status |
|---|---|
| Detailed experimental plan | RQs, exact task, five baseline roles, tuning budgets, split/metric/uncertainty rules in this report and runtime protocol |
| Baseline results | Five methods evaluated on identical frozen community–month targets |
| Preliminary proposed results | Selected two-stage LR, actual scores, probabilities and per-class errors |
| Basic comparison | Strongest-reference, original champion, ablation, temporal and size analysis |
| Prototype demonstration | End-to-end CLI, resumable artifacts and executed seven-figure notebook |

**Next work, prioritized by scientific risk:** independently review a blinded sample spanning all event classes and unresolved cases, report agreement/adjudication and investigate detector/target errors; establish a new genuinely unexposed confirmation cohort before further model selection; examine rare-event support and monthly-resolution sensitivity on development data; then evaluate additional architectures only against the same audited task. Any change to label semantics or eligibility creates a new versioned target and requires a new evaluation, not a replacement of these results.

The midterm demonstrates a functioning research prototype and interpretable preliminary evidence. Human target validity, rare-event reliability, unseen confirmation and novelty remain incomplete. Improving the report cannot substitute for those experiments or justify a guaranteed grade.

## References

[1] CornellNLP, “Reddit Corpus (by subreddit),” ConvoKit documentation. [Online]. Available: [corpus documentation](https://convokit.cornell.edu/documentation/subreddit.html).

[2] J. Baumgartner et al., “The Pushshift Reddit Dataset,” Proceedings of ICWSM, vol.14, pp.830–839,2020. [doi:10.1609/icwsm.v14i1.7347](https://doi.org/10.1609/icwsm.v14i1.7347).

[3] V. A. Traag, L. Waltman, and N. J. van Eck, “From Louvain to Leiden: Guaranteeing well-connected communities,” Scientific Reports, vol.9, Art.5233,2019. [doi:10.1038/s41598-019-41695-z](https://doi.org/10.1038/s41598-019-41695-z).

[4] P. Bródka, S. Saganowski, and P. Kazienko, “GED: The method for group evolution discovery in social networks,” Social Network Analysis and Mining, vol.3, pp.1–14,2013. [doi:10.1007/s13278-012-0058-8](https://doi.org/10.1007/s13278-012-0058-8).

[5] Scikit-learn developers, “Cross-validation: Evaluating estimator performance.” [Online]. Available: [documentation](https://scikit-learn.org/stable/modules/cross_validation.html).

[6] S. Saganowski et al., “Predicting Community Evolution in Social Networks,” Entropy, vol.17, pp.3053–3096,2015. [doi:10.3390/e17053053](https://doi.org/10.3390/e17053053).

[7] J. P. Chang et al., “ConvoKit: A Toolkit for the Analysis of Conversations,” Proceedings of SIGDIAL,2020. [Paper](https://www.cs.cornell.edu/~cristian/ConvoKit_Demo_Paper_files/convokit-demo-paper.pdf).

[8] H. R. Künsch, “The Jackknife and the Bootstrap for General Stationary Observations,” The Annals of Statistics, vol.17, no.3, pp.1217–1241,1989. [doi:10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265).
