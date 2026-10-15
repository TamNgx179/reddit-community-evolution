"""Full-population SNA and frozen sensitivity figures, with explicit units."""

from reddit_sna.reporting.figures import plotting_dependencies


def build_validation_figures(analysis: dict, sensitivity: dict | None = None) -> dict:
    """Plot verified aggregate diagnostics; no scores or user IDs are invented.

    CCDF is P(X >= x) among the observed user union, including isolates at x=0.
    Its log-x plot omits x=0 and states that omission explicitly. Sensitivity
    points are dependent repeats; they have no confidence-interval interpretation.
    """
    plt, np = plotting_dependencies()
    monthly = analysis["months"]
    months = [r["month"] for r in monthly]
    figures = {}
    def values(key):
        return [np.nan if r[key] is None else r[key] for r in monthly]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout="constrained")
    axes[0].plot(months, values("largest_component_fraction_observed"), "o-")
    axes[0].set(ylabel="Largest component / observed users", ylim=(0, 1.02))
    axes[1].plot(months, values("density_observed_union"), "o-", color="#009E73")
    axes[1].set(ylabel="Unweighted density (observed union)", ylim=(0, None))
    fig.suptitle("Full R: component support and density, including isolates")
    figures["09_components_density"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout="constrained")
    # Show predeclared quarterly starts for readability, never select by the tail.
    selected = monthly[::3]
    for row in selected:
        for ax, field in zip(axes, ("degree_distribution", "strength_distribution")):
            total = row["observed_users"]
            cumulative = 0
            x, y = [], []
            for value, count in row[field]:
                if value > 0 and total:
                    x.append(value); y.append((total-cumulative)/total)
                cumulative += count
            if x:
                ax.step(x, y, where="pre", label=row["month"])
    for ax, label in zip(axes, ("Distinct neighbors", "Incident reply weight")):
        ax.set(xscale="log", yscale="log", xlabel=label, ylabel="P(X >= x), observed user denominator")
        if ax.lines:
            ax.legend(fontsize=8)
    fig.suptitle("Quarter-start CCDFs; x=0 isolates omitted from log axis, retained in denominator")
    figures["10_degree_strength"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout="constrained")
    axes[0].plot(months, values("top_one_percent_strength_share"), "o-", color="#0072B2")
    axes[0].set(ylabel="Top ceil(1% * observed users) / total strength", ylim=(0, 1))
    axes[1].plot(months, values("corpus_share_hhi"), "o-", color="#D55E00")
    axes[1].set(ylabel="Sum of squared corpus reply-event shares", ylim=(0, 1))
    fig.suptitle("Concentration: user strength and child-corpus event attribution")
    figures["11_interaction_concentration"] = fig

    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout="constrained")
    for corpus in analysis["contexts"]:
        rows = [r["predeclared_contexts"].get(corpus) for r in monthly]
        axes[0].plot(months, [r["strength_sum"]/2 if r else np.nan for r in rows], "o-", label=corpus)
        axes[1].plot(months, [np.nan if not r or r["largest_component_fraction_observed"] is None
                                else r["largest_component_fraction_observed"] for r in rows], "o-", label=corpus)
    axes[0].set(ylabel="Reply events attributed to child corpus", yscale="symlog", ylim=(0, None))
    axes[1].set(ylabel="Largest component / context observed union", ylim=(0, 1.02))
    axes[0].legend(fontsize=8)
    fig.suptitle("Predeclared contexts: overlapping users, distinct attributed events")
    figures["12_context_diagnostics"] = fig

    if sensitivity is not None:
        records = sensitivity["runs"]
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        gammas = sensitivity["schedule"]["gammas"]
        for i, gamma in enumerate(gammas):
            rows = [r for r in records if r["gamma"] == gamma and r["drop_seed"] is None]
            for ax, field in zip(axes, ("communities", "common_user_ARI")):
                data = [r[field] for r in rows if r[field] is not None]
                ax.scatter([i]*len(data), data, alpha=.65, s=22)
        for ax in axes:
            ax.set_xticks(range(len(gammas)), [str(g) for g in gammas]); ax.set_xlabel("RB resolution gamma")
        axes[0].set_ylabel("Communities (each month/seed shown)")
        axes[1].set(ylabel="Common-user ARI vs same-seed gamma1 baseline", ylim=(-1, 1.02))
        fig.suptitle("Frozen quarter gamma sensitivity; repeats are dependent, baseline unchanged")
        figures["13_gamma_sensitivity"] = fig

        fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        smonths = sensitivity["schedule"]["months"]
        for i, month in enumerate(smonths):
            rows = [r for r in records if r["month"] == month and r["drop_seed"] is not None]
            for ax, field in zip(axes, ("common_user_ARI", "baseline_support_retained")):
                data = [r[field] for r in rows if r[field] is not None]
                ax.scatter([i]*len(data), data, alpha=.65, s=22)
        for ax in axes:
            ax.set_xticks(range(len(smonths)), smonths)
        axes[0].set(ylabel="ARI on common endpoint users only", ylim=(-1, 1.02))
        axes[1].set(ylabel="Common / baseline endpoint users", ylim=(0, 1.02))
        fig.suptitle("Drop floor(5% of unique edges), unchanged retained weights; support loss shown")
        figures["14_edge_perturbation"] = fig
    for fig in figures.values():
        for ax in fig.axes:
            if len(months) > 6 and ax.get_xlabel() != "RB resolution gamma":
                ax.tick_params(axis="x", labelrotation=45)
    return figures
