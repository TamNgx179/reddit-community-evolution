"""Coverage and paired forecast diagnostics, separate from model selection.

Counts refer to community-months. Repeated seeds share the same observations.
Unresolved targets are not converted to dissolve or silently scored as labels.
"""
from collections import Counter, defaultdict
import numpy as np
from reddit_sna.contracts import next_month
from reddit_sna.evaluation.research import KEY, EVENTS, score, matrix_score


def size_band(row):
    n = float(row["size"])

    if not np.isfinite(n) or n < 1 or not n.is_integer():
        raise ValueError(
            f"Invalid community size for stratification: {n}"
        )

    if n == 1:
        return "singleton"
    if n == 2:
        return "2"
    if n <= 4:
        return "3-4"
    if n <= 20:
        return "5-20"
    return ">20"

def _feature_map(features):
    """Build a feature lookup after validating composite keys."""
    identity = KEY[:3]
    feature_map = {}

    for index, row in enumerate(features):
        try:
            key = tuple(row[k] for k in identity)
        except KeyError as exc:
            raise ValueError(
                f"Feature row {index} lacks key field: {exc.args[0]}"
            ) from exc

        if any(value is None or value == "" for value in key):
            raise ValueError(
                f"Feature row {index} has an empty composite key: {key}"
            )

        if key in feature_map:
            raise ValueError(f"Duplicate feature key: {key}")

        feature_map[key] = row

    return feature_map

def _smd(left, right):
    """Standardized mean difference using pooled sample standard deviation."""
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)

    if len(left) < 2 or len(right) < 2:
        return None

    pooled_variance = (
        (len(left) - 1) * np.var(left, ddof=1)
        + (len(right) - 1) * np.var(right, ddof=1)
    ) / (len(left) + len(right) - 2)

    if pooled_variance <= 0:
        return 0.0 if np.mean(left) == np.mean(right) else None

    return float(
        (np.mean(left) - np.mean(right))
        / np.sqrt(pooled_variance)
    )


def _ks_statistic(left, right):
    """Two-sample empirical Kolmogorov-Smirnov statistic."""
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)

    if len(left) == 0 or len(right) == 0:
        return None

    values = np.sort(np.concatenate((left, right)))

    left_cdf = np.searchsorted(
        np.sort(left), values, side="right"
    ) / len(left)

    right_cdf = np.searchsorted(
        np.sort(right), values, side="right"
    ) / len(right)

    return float(np.max(np.abs(left_cdf - right_cdf)))


def _cramers_v(left, right):
    """Cramer's V for association between a categorical feature and eligibility."""
    if not left or not right:
        return None

    categories = sorted(set(left) | set(right), key=str)

    if len(categories) < 2:
        return None

    table = np.asarray(
        [
            [sum(value == category for value in left) for category in categories],
            [sum(value == category for value in right) for category in categories],
        ],
        dtype=float,
    )

    row_totals = table.sum(axis=1)
    column_totals = table.sum(axis=0)
    total = table.sum()

    if np.any(row_totals == 0) or np.any(column_totals == 0):
        return None

    expected = np.outer(row_totals, column_totals) / total
    chi_squared = np.sum((table - expected) ** 2 / expected)

    denominator = total * min(table.shape[0] - 1, table.shape[1] - 1)

    if denominator <= 0:
        return None

    return float(np.sqrt(chi_squared / denominator))

def coverage_tables(labels, features, graph=None):
    """Reconcile omitted terminal targets and retain independent denominators."""
    valid_eligibility = {"0", "1"}

    if any(
        str(row.get("eligible")) not in valid_eligibility
        for row in labels
    ):
        raise ValueError(
            "Invalid eligibility value; expected 0 or 1"
        )
    identity = KEY[:3]
    fm = _feature_map(features)
    lm = {tuple(r[k] for k in identity): r for r in labels}
    if not features or len(fm) != len(features) or len(lm) != len(labels) or set(lm) - set(fm):
        raise ValueError('Coverage requires unique matching feature/label keys')
    last = max(r['feature_month'] for r in features)
    missing = set(fm) - set(lm)
    if any(k[1] != last for k in missing):
        raise ValueError('Only the final snapshot can lack target rows')
    rows = list(labels) + [dict(**{k: fm[key][k] for k in identity}, eligible='0',
                              label='', reason='final_snapshot_censored') for key in sorted(missing)]
    if any(r['available_through_month'] != r['feature_month'] or float(r['size']) <= 0 for r in features):
        raise ValueError('Invalid feature availability or community size')
    result, distributions = [], []
    axes = {'all': lambda f: 'all', 'month': lambda f: f['feature_month'], 'size': size_band,
            'lineage_history': lambda f: 'missing' if float(f['history_missing']) else 'available'}
    for axis, group in axes.items():
        for value in sorted({group(f) for f in features}):
            selected = [r for r in rows if group(fm[tuple(r[k] for k in identity)]) == value]
            censored = [r for r in selected if r['reason'] == 'final_snapshot_censored']
            observed = [r for r in selected if r['reason'] != 'final_snapshot_censored']
            eligible = [r for r in observed if str(r['eligible']) == '1']
            mass = lambda rs: sum(float(fm[tuple(r[k] for k in identity)]['size']) for r in rs)
            record = dict(
                axis=axis,
                stratum=value,
                month_basis="feature_month" if axis == "month" else None,
                observed=len(observed),
                eligible=len(eligible),
                unresolved=len(observed) - len(eligible),
                censored=len(censored),
                coverage=len(eligible) / len(observed) if observed else None,
                observed_member_months=mass(observed),
                eligible_member_months=mass(eligible),
                member_month_coverage=(
                    mass(eligible) / mass(observed) if observed else None
                ),
            )
            if graph and axis == 'month':
                g = graph[value]
                if mass(selected) != g['reply_endpoints']:
                    raise ValueError('Community members do not cover the graph endpoints')
                record.update(reply_endpoints=g['reply_endpoints'], observed_users=g['observed_users'],
                              graph_observed_user_coverage=g['reply_coverage_observed_users'],
                              graph_active_author_coverage=g['reply_coverage_active_authors'])
            result.append(record)
            # Build distribution strata independently from coverage strata.
    distribution_axes = {
        "all": lambda f: "all",
        "month": lambda f: f["feature_month"],
        "size": size_band,
        "lineage_history": lambda f: (
            "missing" if float(f["history_missing"]) else "available"
        ),
        "member_activity_history": lambda f: (
            "available"
            if float(f.get("context_history_missing", 1)) == 0
            else "missing_or_not_recorded"
        ),
        "size_history": lambda f: (
            f"{size_band(f)}|"
            f"{'missing' if float(f['history_missing']) else 'available'}"
        ),
    }

    fields = (
        "size",
        "density",
        "community_age",
        "history_missing",
        "internal_weight",
        "boundary_weight",
        "records_per_member_log",
        "past_window_fraction",
        "context_history_missing",
    )

    for dist_axis, dist_group in distribution_axes.items():
        dist_strata = sorted(
            {dist_group(fm[key]) for key in fm},
            key=str,
        )

        for dist_value in dist_strata:
            dist_selected = [
                row for row in rows
                if dist_group(
                    fm[tuple(row[k] for k in identity)]
                ) == dist_value
            ]

            dist_observed = [
                row for row in dist_selected
                if row["reason"] != "final_snapshot_censored"
            ]

            for status, subset in (
                (
                    "eligible",
                    [r for r in dist_observed if str(r["eligible"]) == "1"],
                ),
                (
                    "unresolved",
                    [r for r in dist_observed if str(r["eligible"]) == "0"],
                ),
            ):
                for field in fields:
                    raw_values = [
                        fm[tuple(r[k] for k in identity)].get(field)
                        for r in subset
                    ]

                    values = []
                    for raw in raw_values:
                        if raw is None:
                            continue

                        try:
                            number = float(raw)
                        except (TypeError, ValueError):
                            continue

                        if np.isfinite(number):
                            values.append(number)

                    missing_n = len(subset) - len(values)

                    stats = dict(
                        axis=dist_axis,
                        stratum=dist_value,
                        status=status,
                        field=field,
                        n=len(values),
                        missing_n=missing_n,
                        missing_fraction=(
                            missing_n / len(subset) if subset else None
                        ),
                        q10=None,
                        q25=None,
                        median=None,
                        q75=None,
                        q90=None,
                        mean=None,
                        std=None,
                    )

                    if values:
                        stats.update(
                            q10=float(np.quantile(values, 0.10)),
                            q25=float(np.quantile(values, 0.25)),
                            median=float(np.median(values)),
                            q75=float(np.quantile(values, 0.75)),
                            q90=float(np.quantile(values, 0.90)),
                            mean=float(np.mean(values)),
                            std=float(np.std(values)),
                        )

                    distributions.append(stats)
    return result, distributions



def eligibility_comparison_tables(labels, features):
    """Compare eligible and unresolved feature distributions by strata.

    Censored feature rows without labels are excluded.
    Numerical features use SMD and KS; categorical features use Cramer's V.
    Missing values are counted separately and excluded from each statistic.
    """
    identity = KEY[:3]
    valid_eligibility = {"0", "1"}

    if not features:
        raise ValueError("Eligibility comparison requires features")

    if any(
        str(row.get("eligible")) not in valid_eligibility
        for row in labels
    ):
        raise ValueError(
            "Invalid eligibility value; expected 0 or 1"
        )

    fm = _feature_map(features)
    lm = {}

    for index, row in enumerate(labels):
        try:
            key = tuple(row[k] for k in identity)
        except KeyError as exc:
            raise ValueError(
                f"Label row {index} lacks key field: {exc.args[0]}"
            ) from exc

        if any(value is None or value == "" for value in key):
            raise ValueError(
                f"Label row {index} has an empty composite key: {key}"
            )

        if key in lm:
            raise ValueError(f"Duplicate label key: {key}")

        lm[key] = row

    if set(lm) - set(fm):
        raise ValueError(
            "Eligibility comparison requires matching feature/label keys"
        )

    last = max(row["feature_month"] for row in features)
    missing = set(fm) - set(lm)

    if any(key[1] != last for key in missing):
        raise ValueError(
            "Only the final snapshot can lack target rows"
        )

    if any(
        row["available_through_month"] != row["feature_month"]
        or float(row["size"]) <= 0
        for row in features
    ):
        raise ValueError(
            "Invalid feature availability or community size"
        )

    # Only actual labeled observations enter the comparison.
    observations = [
        (key, lm[key], fm[key])
        for key in sorted(lm)
    ]

    def lineage_status(feature):
        return (
            "missing"
            if float(feature["history_missing"])
            else "available"
        )

    def member_history_status(feature):
        return (
            "available"
            if float(feature.get("context_history_missing", 1)) == 0
            else "missing_or_not_recorded"
        )

    axes = {
        "all": lambda f: "all",
        "month": lambda f: f["feature_month"],
        "size": size_band,
        "lineage_history": lineage_status,
        "member_activity_history": member_history_status,
        "size_history": lambda f: (
            f"{size_band(f)}|{lineage_status(f)}"
        ),
    }

    numerical_fields = (
        "size",
        "density",
        "community_age",
        "internal_weight",
        "boundary_weight",
        "records_per_member_log",
        "past_window_fraction",
    )

    categorical_fields = (
        "history_missing",
        "context_history_missing",
    )

    def numeric_value(raw):
        if raw is None:
            return None

        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None

        return value if np.isfinite(value) else None

    def categorical_value(raw):
        if raw is None:
            return None

        if isinstance(raw, str) and not raw.strip():
            return None

        try:
            number = float(raw)
        except (TypeError, ValueError):
            return str(raw)

        if not np.isfinite(number):
            return None

        return str(number)

    comparisons = []

    for axis, group in axes.items():
        strata = sorted(
            {group(feature) for _, _, feature in observations},
            key=str,
        )

        for stratum in strata:
            selected = [
                (key, label, feature)
                for key, label, feature in observations
                if group(feature) == stratum
            ]

            eligible = [
                feature
                for _, label, feature in selected
                if str(label["eligible"]) == "1"
            ]

            unresolved = [
                feature
                for _, label, feature in selected
                if str(label["eligible"]) == "0"
            ]

            base = {
                "axis": axis,
                "stratum": stratum,
                "eligible_n": len(eligible),
                "unresolved_n": len(unresolved),
                "month_basis": (
                    "feature_month" if axis == "month" else None
                ),
            }

            for field in numerical_fields:
                left = [
                    value
                    for feature in eligible
                    if (value := numeric_value(feature.get(field)))
                    is not None
                ]

                right = [
                    value
                    for feature in unresolved
                    if (value := numeric_value(feature.get(field)))
                    is not None
                ]

                missing_left = len(eligible) - len(left)
                missing_right = len(unresolved) - len(right)

                for method, statistic in (
                    ("smd", _smd(left, right)),
                    ("ks", _ks_statistic(left, right)),
                ):
                    reason = None

                    if statistic is None:
                        reason = (
                            "insufficient_samples_or_zero_variance"
                            if method == "smd"
                            else "empty_valid_group"
                        )

                    comparisons.append(
                        dict(
                            **base,
                            field=field,
                            method=method,
                            eligible_valid_n=len(left),
                            unresolved_valid_n=len(right),
                            eligible_missing_n=missing_left,
                            unresolved_missing_n=missing_right,
                            eligible_mean=(
                                float(np.mean(left)) if left else None
                            ),
                            unresolved_mean=(
                                float(np.mean(right)) if right else None
                            ),
                            statistic=statistic,
                            reason=reason,
                        )
                    )

            for field in categorical_fields:
                left = [
                    value
                    for feature in eligible
                    if (value := categorical_value(
                        feature.get(field)
                    )) is not None
                ]

                right = [
                    value
                    for feature in unresolved
                    if (value := categorical_value(
                        feature.get(field)
                    )) is not None
                ]

                statistic = _cramers_v(left, right)

                comparisons.append(
                    dict(
                        **base,
                        field=field,
                        method="cramers_v",
                        eligible_valid_n=len(left),
                        unresolved_valid_n=len(right),
                        eligible_missing_n=len(eligible) - len(left),
                        unresolved_missing_n=len(unresolved) - len(right),
                        eligible_mean=None,
                        unresolved_mean=None,
                        statistic=statistic,
                        reason=(
                            "empty_group_or_single_category"
                            if statistic is None
                            else None
                        ),
                    )
                )

    return comparisons


def prediction_units(predictions):
    """Reject duplicates and any unequal keys or truths within a window."""
    units = defaultdict(dict)
    truths = {}
    for row in predictions:
        key = tuple(row[k] for k in KEY)
        unit = (row.get('window','final'), row['model'], int(row['seed']))
        if (key in units[unit] or row['label_month'] != next_month(row['feature_month'])
                or row['y_true'] not in EVENTS or row['y_pred'] not in EVENTS):
            raise ValueError('Duplicate or invalid prediction key/event')
        if (unit[0],key) in truths and truths[(unit[0],key)] != row['y_true']:
            raise ValueError('Prediction truths differ')
        truths[(unit[0],key)] = row['y_true']
        units[unit][key] = row
    for window in {u[0] for u in units}:
        if len({frozenset(rows) for u,rows in units.items() if u[0]==window}) != 1:
            raise ValueError('Predictions must share full keys within each window')
    return units


def forecast_tables(predictions, features):
    """Fixed-six metrics and confusion tables by month and community strata."""
    units = prediction_units(predictions)
    fm = _feature_map(features)

    metrics, classes, confusion = [], [], []
    dissolve_idx = EVENTS.index("dissolve")

    for (window, model, seed), rows in sorted(units.items()):
        if any(key[:3] not in fm for key in rows):
            raise ValueError("Prediction lacks a feature row")

        def history_status(key):
            return (
                "missing"
                if float(fm[key[:3]]["history_missing"])
                else "available"
            )

        def member_history_status(key):
            return (
                "available"
                if float(fm[key[:3]].get("context_history_missing", 1)) == 0
                else "missing_or_not_recorded"
            )

        def size_history_group(key):
            return f"{size_band(fm[key[:3]])}|{history_status(key)}"

        axes = {
            "all": lambda k: "all",
            "month": lambda k: k[3],
            "size": lambda k: size_band(fm[k[:3]]),
            "lineage_history": history_status,
            "member_activity_history": member_history_status,
            "size_history": size_history_group,
        }

        for axis, group in axes.items():
            strata = sorted({group(key) for key in rows}, key=str)

            for value in strata:
                selected = [
                    row for key, row in rows.items()
                    if group(key) == value
                ]

                s = score(selected)
                matrix = np.asarray(s["confusion"], dtype=int)

                base = dict(
                    window=window,
                    model=model,
                    seed=seed,
                    axis=axis,
                    stratum=value,
                    month_basis="label_month" if axis == "month" else None,
                )

                n = int(s["n"])
                metrics.append(
                    dict(
                        **base,
                        n=n,
                        macro_f1_six=s["macro_f1_six"],
                        accuracy=float(np.trace(matrix) / n),
                    )
                )

                for i, event in enumerate(EVENTS):
                    support = int(matrix[i].sum())
                    predicted = int(matrix[:, i].sum())
                    true_positive = int(matrix[i, i])

                    precision = (
                        true_positive / predicted if predicted else 0.0
                    )
                    recall = (
                        true_positive / support if support else 0.0
                    )
                    f1 = (
                        2 * precision * recall / (precision + recall)
                        if precision + recall
                        else 0.0
                    )

                    classes.append(
                        dict(
                            **base,
                            label=event,
                            support=support,
                            precision=precision,
                            recall=recall,
                            f1=f1,
                            to_dissolve=int(matrix[i, dissolve_idx]),
                            predicted=predicted,
                        )
                    )

                    for j, predicted_event in enumerate(EVENTS):
                        confusion.append(
                            dict(
                                **base,
                                truth=event,
                                prediction=predicted_event,
                                count=int(matrix[i, j]),
                            )
                        )

    return metrics, classes, confusion


def paired_tables(predictions, features, contrasts, *, draws=1000, block_length=2, bootstrap_seed=20261031):
    """Paired cases and whole-month uncertainty, never treating seeds as samples."""
    units = prediction_units(predictions)
    fm = _feature_map(features)
    cases, intervals = [], []
    for window in sorted({u[0] for u in units}):
        seeds=sorted({u[2] for u in units if u[0]==window})
        for proposed,reference in contrasts:
            if any((window,m,s) not in units for m in (proposed,reference) for s in seeds):
                raise ValueError('Missing paired model/seed')
            for seed in seeds:
                left,right=units[(window,proposed,seed)],units[(window,reference,seed)]
                for key in sorted(left):
                    p,r=left[key],right[key]
                    pc,rc=p['y_pred']==p['y_true'],r['y_pred']==r['y_true']
                    outcome='both_correct' if pc and rc else 'proposed_only' if pc else 'reference_only' if rc else 'both_wrong'
                    f=fm[key[:3]]
                    cases.append(dict(**dict(zip(KEY,key)),window=window,proposed=proposed,reference=reference,seed=seed,
                        y_true=p['y_true'],proposed_prediction=p['y_pred'],reference_prediction=r['y_pred'],outcome=outcome,
                        size=f['size'],
                        size_band=size_band(f),
                        history_missing=f['history_missing'],
                        context_history_missing=f.get('context_history_missing', 1),
                        ))
            sample=units[(window,proposed,seeds[0])]
            months=sorted({k[3] for k in sample})
            observed=float(np.mean([score(list(units[(window,proposed,s)].values()))['macro_f1_six']-
                                    score(list(units[(window,reference,s)].values()))['macro_f1_six'] for s in seeds]))
            base=dict(window=window,proposed=proposed,reference=reference,delta=observed,months=len(months))
            if len(months)<6:
                intervals.append(dict(**base,low=None,high=None,draws=0,block_length=None,
                                      reason='Fewer than six distinct months'))
                continue
            matrices={}
            for model in (proposed,reference):
                for seed in seeds:
                    for month in months:
                        matrices[(model,seed,month)]=np.asarray(score([r for k,r in units[(window,model,seed)].items() if k[3]==month])['confusion'])
            rng=np.random.default_rng(bootstrap_seed); deltas=[]
            for _ in range(draws):
                starts=rng.integers(0,len(months)-block_length+1,size=-(-len(months)//block_length))
                selected=[months[i+j] for i in starts for j in range(block_length)][:len(months)]
                values=[np.mean([matrix_score(sum(matrices[(m,s,t)] for t in selected))['macro_f1_six'] for s in seeds])
                        for m in (proposed,reference)]
                deltas.append(values[0]-values[1])
            intervals.append(dict(**base,low=float(np.quantile(deltas,.025)),high=float(np.quantile(deltas,.975)),
                                  draws=draws,block_length=block_length,reason='Exploratory paired month blocks'))
    return cases, intervals

def paired_aggregation_tables(cases):
    """Aggregate paired outcomes without treating seeds as independent cases.

    Returns:
        summary: mean outcome rates across seeds for each stratum.
        per_seed: outcome counts and rates for each seed and stratum.
    """
    outcomes = (
        "both_correct",
        "proposed_only",
        "reference_only",
        "both_wrong",
    )
    identity = KEY

    required = (
        *identity,
        "window",
        "proposed",
        "reference",
        "seed",
        "y_true",
        "outcome",
        "size",
        "size_band",
        "history_missing",
        "context_history_missing",
    )

    if not cases:
        raise ValueError("Paired aggregation requires cases")

    seen = set()
    normalized = []

    for index, case in enumerate(cases):
        missing = [field for field in required if field not in case]
        if missing:
            raise ValueError(
                f"Paired case {index} lacks fields: {missing}"
            )

        if case["outcome"] not in outcomes:
            raise ValueError(
                f"Invalid paired outcome: {case['outcome']}"
            )

        key = tuple(case[field] for field in identity)
        if any(value is None or value == "" for value in key):
            raise ValueError(
                f"Paired case {index} has an empty identity key"
            )

        seed = int(case["seed"])
        case_id = (
            case["window"],
            case["proposed"],
            case["reference"],
            seed,
            key,
        )

        if case_id in seen:
            raise ValueError(
                f"Duplicate paired case: {case_id}"
            )

        seen.add(case_id)
        normalized.append((case, key, seed))

    seed_units = defaultdict(dict)

    for case, key, seed in normalized:
        contrast = (
            case["window"],
            case["proposed"],
            case["reference"],
        )
        seed_units[(*contrast, seed)][key] = case

    contrasts = sorted(
        {
            (case["window"], case["proposed"], case["reference"])
            for case, _, _ in normalized
        },
        key=lambda value: tuple(map(str, value)),
    )

    invariant_fields = (
        "y_true",
        "size",
        "size_band",
        "history_missing",
        "context_history_missing",
    )

    for contrast in contrasts:
        seed_ids = sorted(
            seed
            for window, proposed, reference, seed in seed_units
            if (window, proposed, reference) == contrast
        )

        reference_seed = seed_ids[0]
        reference_rows = seed_units[(*contrast, reference_seed)]
        reference_keys = set(reference_rows)

        for seed in seed_ids[1:]:
            current_rows = seed_units[(*contrast, seed)]

            if set(current_rows) != reference_keys:
                raise ValueError(
                    "Paired seeds must share identical community-month keys"
                )

            for key in reference_keys:
                reference_case = reference_rows[key]
                current_case = current_rows[key]

                if any(
                    reference_case[field] != current_case[field]
                    for field in invariant_fields
                ):
                    raise ValueError(
                        "Paired seed metadata differs for the same case"
                    )

    def history_status(case):
        return (
            "missing"
            if float(case["history_missing"])
            else "available"
        )

    def member_history_status(case):
        return (
            "available"
            if float(case["context_history_missing"]) == 0
            else "missing_or_not_recorded"
        )

    axes = {
        "all": lambda case: "all",
        "class": lambda case: case["y_true"],
        "month": lambda case: case["label_month"],
        "size": lambda case: case["size_band"],
        "lineage_history": history_status,
        "member_activity_history": member_history_status,
        "size_history": lambda case: (
            f"{case['size_band']}|{history_status(case)}"
        ),
    }

    grouped = defaultdict(list)

    for case, key, seed in normalized:
        contrast = (
            case["window"],
            case["proposed"],
            case["reference"],
        )

        for axis, group in axes.items():
            stratum = group(case)
            grouped[(*contrast, axis, stratum, seed)].append(
                (case, key)
            )

    per_seed = []

    for group_key, rows in sorted(
        grouped.items(),
        key=lambda item: tuple(map(str, item[0])),
    ):
        window, proposed, reference, axis, stratum, seed = group_key

        counts = {
            outcome: sum(
                case["outcome"] == outcome
                for case, _ in rows
            )
            for outcome in outcomes
        }

        n = len({key for _, key in rows})

        if n != len(rows):
            raise ValueError(
                "A seed contains duplicate community-months "
                "within a paired stratum"
            )

        per_seed.append(
            dict(
                window=window,
                proposed=proposed,
                reference=reference,
                axis=axis,
                stratum=stratum,
                seed=seed,
                n_community_months=n,
                **{
                    f"{outcome}_count": counts[outcome]
                    for outcome in outcomes
                },
                **{
                    f"{outcome}_rate": counts[outcome] / n
                    for outcome in outcomes
                },
            )
        )

    summary_groups = defaultdict(list)

    for row in per_seed:
        key = (
            row["window"],
            row["proposed"],
            row["reference"],
            row["axis"],
            row["stratum"],
        )
        summary_groups[key].append(row)

    summary = []

    for group_key, seed_rows in sorted(
        summary_groups.items(),
        key=lambda item: tuple(map(str, item[0])),
    ):
        window, proposed, reference, axis, stratum = group_key

        summary.append(
            dict(
                window=window,
                proposed=proposed,
                reference=reference,
                axis=axis,
                stratum=stratum,
                seed_count=len(seed_rows),
                n_community_months=max(
                    row["n_community_months"]
                    for row in seed_rows
                ),
                **{
                    f"mean_{outcome}_rate": float(
                        np.mean([
                            row[f"{outcome}_rate"]
                            for row in seed_rows
                        ])
                    )
                    for outcome in outcomes
                },
            )
        )

    return summary, per_seed


def paired_strata_bootstrap(
    cases,
    *,
    draws=1000,
    block_length=2,
    bootstrap_seed=20261102,
):
    """Bootstrap paired outcome rates by strata using calendar-month blocks.

    Seeds are summarized within each bootstrap draw, not treated as
    independent observations. The original calendar-month axis is retained
    even when a stratum has no observations in some months.

    Returns one row per contrast, stratum, and paired outcome.
    """
    outcomes = (
        "both_correct",
        "proposed_only",
        "reference_only",
        "both_wrong",
    )

    if isinstance(draws, bool) or not isinstance(draws, int) or draws < 1:
        raise ValueError("draws must be a positive integer")

    if (
        isinstance(block_length, bool)
        or not isinstance(block_length, int)
        or block_length < 1
    ):
        raise ValueError("block_length must be a positive integer")

    # Reuse the aggregation validation:
    # duplicate cases, matching seed keys, and consistent metadata.
    summary, per_seed = paired_aggregation_tables(cases)

    def history_status(case):
        return (
            "missing"
            if float(case["history_missing"])
            else "available"
        )

    def member_history_status(case):
        return (
            "available"
            if float(case["context_history_missing"]) == 0
            else "missing_or_not_recorded"
        )

    axes = {
        "all": lambda case: "all",
        "class": lambda case: case["y_true"],
        "month": lambda case: case["label_month"],
        "size": lambda case: case["size_band"],
        "lineage_history": history_status,
        "member_activity_history": member_history_status,
        "size_history": lambda case: (
            f"{case['size_band']}|{history_status(case)}"
        ),
    }

    def calendar_month_range(month_values):
        """Return every calendar month between the observed endpoints."""
        ordinals = []

        for value in month_values:
            try:
                year_text, month_text = value.split("-")
                year = int(year_text)
                month = int(month_text)
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid label_month: {value}"
                ) from exc

            if month < 1 or month > 12:
                raise ValueError(f"Invalid label_month: {value}")

            ordinals.append(year * 12 + month - 1)

        first = min(ordinals)
        last = max(ordinals)

        return [
            f"{ordinal // 12:04d}-{ordinal % 12 + 1:02d}"
            for ordinal in range(first, last + 1)
        ]

    # Organize observations by contrast and seed.
    contrasts = defaultdict(list)

    for case in cases:
        contrast = (
            case["window"],
            case["proposed"],
            case["reference"],
        )
        contrasts[contrast].append(case)

    summary_lookup = {
        (
            row["window"],
            row["proposed"],
            row["reference"],
            row["axis"],
            row["stratum"],
        ): row
        for row in summary
    }

    seed_lookup = defaultdict(list)

    for row in per_seed:
        key = (
            row["window"],
            row["proposed"],
            row["reference"],
            row["axis"],
            row["stratum"],
        )
        seed_lookup[key].append(row)

    results = []
    rng = np.random.default_rng(bootstrap_seed)

    for contrast in sorted(
        contrasts,
        key=lambda value: tuple(map(str, value)),
    ):
        window, proposed, reference = contrast
        contrast_cases = contrasts[contrast]

        seeds = sorted({
            int(case["seed"])
            for case in contrast_cases
        })

        months = calendar_month_range([
            case["label_month"]
            for case in contrast_cases
        ])

        # Build one shared set of month-block draws for every stratum
        # in this contrast. This keeps the uncertainty comparisons paired.
        month_draws = []

        can_bootstrap = (
            len(months) >= 6
            and block_length <= len(months)
        )

        if can_bootstrap:
            blocks_per_draw = (
                len(months) + block_length - 1
            ) // block_length

            for _ in range(draws):
                starts = rng.integers(
                    0,
                    len(months) - block_length + 1,
                    size=blocks_per_draw,
                )

                selected = [
                    months[start + offset]
                    for start in starts
                    for offset in range(block_length)
                ][:len(months)]

                month_draws.append(selected)

        for axis, group in axes.items():
            strata = sorted(
                {group(case) for case in contrast_cases},
                key=str,
            )

            for stratum in strata:
                selected_cases = [
                    case
                    for case in contrast_cases
                    if group(case) == stratum
                ]

                # Determine the unique community-month count using
                # the complete composite prediction key.
                unique_keys = {
                    tuple(case[field] for field in KEY)
                    for case in selected_cases
                }

                n_community_months = len(unique_keys)

                buckets = defaultdict(list)

                for case in selected_cases:
                    buckets[
                        (
                            int(case["seed"]),
                            case["label_month"],
                        )
                    ].append(case)

                bootstrap_rates = {
                    outcome: []
                    for outcome in outcomes
                }

                for selected_months in month_draws:
                    seed_rates = {
                        outcome: []
                        for outcome in outcomes
                    }

                    valid_draw = True

                    for seed in seeds:
                        sampled = [
                            case
                            for month in selected_months
                            for case in buckets.get((seed, month), [])
                        ]

                        if not sampled:
                            valid_draw = False
                            break

                        denominator = len(sampled)

                        for outcome in outcomes:
                            count = sum(
                                case["outcome"] == outcome
                                for case in sampled
                            )

                            seed_rates[outcome].append(
                                count / denominator
                            )

                    if not valid_draw:
                        continue

                    for outcome in outcomes:
                        bootstrap_rates[outcome].append(
                            float(np.mean(seed_rates[outcome]))
                        )

                aggregate_key = (
                    window,
                    proposed,
                    reference,
                    axis,
                    stratum,
                )

                aggregate = summary_lookup[aggregate_key]
                seed_rows = seed_lookup[aggregate_key]

                for outcome in outcomes:
                    values = bootstrap_rates[outcome]

                    if axis == "month":
                        ci_low = None
                        ci_high = None
                        reason = "single_month_stratum_not_estimable_with_month_block_bootstrap"

                    elif values:
                        ci_low = float(np.quantile(values, 0.025))
                        ci_high = float(np.quantile(values, 0.975))
                        reason = (
                            None
                            if len(values) == draws
                            else "some_draws_dropped_for_empty_stratum"
                        )

                    else:
                        ci_low = None
                        ci_high = None
                        reason = (
                            "fewer_than_six_calendar_months"
                            if len(months) < 6
                            else "block_length_exceeds_month_range"
                            if block_length > len(months)
                            else "no_valid_bootstrap_draws"
                        )

                    results.append(
                        dict(
                            window=window,
                            proposed=proposed,
                            reference=reference,
                            axis=axis,
                            stratum=stratum,
                            outcome=outcome,
                            mean_rate=aggregate[
                                f"mean_{outcome}_rate"
                            ],
                            ci_low=ci_low,
                            ci_high=ci_high,
                            n_community_months=n_community_months,
                            seed_count=len(seed_rows),
                            months=len(months),
                            draws=draws,
                            valid_draws=len(values),
                            block_length=block_length,
                            bootstrap_method=(
                                "paired_calendar_month_blocks"
                            ),
                            reason=reason,
                        )
                    )

    return results
