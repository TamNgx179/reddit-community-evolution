"""So sánh LR đầy đủ, LR bỏ nhóm D và HGB trên cùng tập ca final (1,269 mẫu).

Tái tính từ các bảng confusion đã lưu của Midterm 2 (A1 theo tháng, A2 theo
lịch sử). Không fit lại mô hình. Mỗi seed giữ riêng.

    python scripts/compare_lr_nod_hgb.py --out reports/tables/thanh-lr-nod-hgb-20261117
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports" / "tables" / "midterm2-20261104"
MODELS = {
    "hier_lr_dynamic": "LR đầy đủ",
    "A_no_dynamics_matched": "LR bỏ D",
    "hier_hgb_dynamic": "HGB",
}
CLASSES = ["stable", "grow", "shrink", "merge", "split", "dissolve"]
INPUTS = {
    "all": ("A1/tables/A1_overall_confusion.csv", "A1/tables/A1_overall_macro_summary.csv"),
    "month": ("A1/tables/A1_monthly_confusion.csv", "A1/tables/A1_monthly_macro_summary.csv"),
    "lineage_history": ("A2/tables/A2_lineage_history_confusion.csv",
                        "A2/tables/A2_lineage_history_macro_summary.csv"),
    "member_activity_history": ("A2/tables/A2_member_activity_history_confusion.csv",
                                "A2/tables/A2_member_activity_history_macro_summary.csv"),
    "size_history": ("A2/tables/A2_size_history_confusion.csv",
                     "A2/tables/A2_size_history_macro_summary.csv"),
}
GROUP = ["model", "seed", "axis", "stratum"]


def matrix(group):
    m = group.pivot_table(index="truth", columns="prediction", values="count",
                          aggfunc="sum", fill_value=0)
    return m.reindex(index=CLASSES, columns=CLASSES, fill_value=0).to_numpy()


def metrics(m):
    tp = np.diag(m)
    support, predicted = m.sum(1), m.sum(0)
    recall = np.divide(tp, support, out=np.zeros(6), where=support > 0)
    precision = np.divide(tp, predicted, out=np.zeros(6), where=predicted > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(6),
                   where=(precision + recall) > 0)
    return support, recall, precision, f1


def summarize(conf):
    d, g, s = CLASSES.index("dissolve"), CLASSES.index("grow"), CLASSES.index("merge")
    rows, class_rows = [], []
    for key, group in conf.groupby(GROUP, sort=True):
        m = matrix(group)
        support, recall, precision, f1 = metrics(m)
        n = int(m.sum())
        rows.append(dict(zip(GROUP, key), n=n, macro_f1=f1.mean(),
                         accuracy=np.trace(m) / n if n else np.nan,
                         errors=n - int(np.trace(m)),
                         grow_n=int(support[g]), grow_recall=recall[g],
                         grow_to_dissolve=int(m[g, d]),
                         merge_n=int(support[s]), merge_recall=recall[s],
                         merge_to_dissolve=int(m[s, d]),
                         grow_merge_to_dissolve=int(m[g, d] + m[s, d])))
        for i, c in enumerate(CLASSES):
            class_rows.append(dict(zip(GROUP, key), cls=c, support=int(support[i]),
                                   recall=recall[i], precision=precision[i], f1=f1[i],
                                   errors=int(support[i] - m[i, i]),
                                   to_dissolve=int(m[i, d]) if i != d else 0))
    return pd.DataFrame(rows), pd.DataFrame(class_rows)


def load(axis):
    conf_path, macro_path = (SRC / p for p in INPUTS[axis])
    conf = pd.read_csv(conf_path)
    conf = conf[conf.model.isin(MODELS)].copy()
    if axis == "all":
        conf["axis"], conf["stratum"] = "all", "all"
    macro = pd.read_csv(macro_path)
    macro = macro[macro.model.isin(MODELS)].copy()
    if axis == "all":
        macro["axis"], macro["stratum"] = "all", "all"
    return conf, macro


def check(summary, macro, axis):
    merged = summary.merge(macro[GROUP + ["n", "macro_f1_six"]], on=GROUP, suffixes=("", "_saved"))
    if len(merged) != len(summary):
        raise ValueError(f"{axis}: thiếu dòng macro đã lưu")
    if (merged.n != merged.n_saved).any():
        raise ValueError(f"{axis}: n tái tính khác bản lưu")
    gap = (merged.macro_f1 - merged.macro_f1_six).abs().max()
    if gap > 1e-9:
        raise ValueError(f"{axis}: Macro-F1 lệch {gap}")
    # Cùng tập ca: mỗi tầng phải có cùng n cho cả ba mô hình và mọi seed.
    same = summary.groupby(["axis", "stratum"]).n.nunique()
    if (same > 1).any():
        raise ValueError(f"{axis}: số ca khác nhau giữa mô hình/seed")
    return gap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    out = ap.parse_args().out
    out.mkdir(parents=True, exist_ok=False)

    summaries, classes, audit = [], [], []
    for axis in INPUTS:
        conf, macro = load(axis)
        s, c = summarize(conf)
        audit.append(dict(axis=axis, rows=len(s), max_macro_f1_gap=check(s, macro, axis),
                          n_total=int(s[s.model == "hier_lr_dynamic"].query("seed == 42").n.sum())))
        summaries.append(s)
        classes.append(c)
    summary = pd.concat(summaries, ignore_index=True)
    by_class = pd.concat(classes, ignore_index=True)
    summary["model_label"] = summary.model.map(MODELS)
    by_class["model_label"] = by_class.model.map(MODELS)

    # Seed có làm thay đổi kết quả không?
    seed_spread = (summary.groupby(["model", "axis", "stratum"])
                   .agg(macro_f1_sd=("macro_f1", "std"),
                        gm_dissolve_min=("grow_merge_to_dissolve", "min"),
                        gm_dissolve_max=("grow_merge_to_dissolve", "max"))
                   .reset_index())

    # Ảnh hưởng của D: LR đầy đủ − LR bỏ D, cùng tầng và cùng seed.
    cols = ["macro_f1", "errors", "grow_recall", "merge_recall", "grow_merge_to_dissolve"]
    wide = summary.pivot_table(index=["axis", "stratum", "seed", "n"], columns="model", values=cols)
    delta = pd.DataFrame(index=wide.index)
    for col in cols:
        delta[f"{col}_lr"] = wide[(col, "hier_lr_dynamic")]
        delta[f"{col}_nod"] = wide[(col, "A_no_dynamics_matched")]
        delta[f"{col}_hgb"] = wide[(col, "hier_hgb_dynamic")]
        delta[f"d_{col}_D"] = delta[f"{col}_lr"] - delta[f"{col}_nod"]
        delta[f"d_{col}_lr_vs_hgb"] = delta[f"{col}_lr"] - delta[f"{col}_hgb"]
    delta = delta.reset_index()

    order = dict(zip(MODELS, range(3)))
    summary = summary.sort_values(["axis", "stratum", "seed"], key=lambda s: s.map(order) if s.name == "model" else s)
    summary.to_csv(out / "summary_by_stratum.csv", index=False)
    by_class.to_csv(out / "class_metrics_by_stratum.csv", index=False)
    delta.to_csv(out / "delta_D_and_hgb.csv", index=False)
    seed_spread.to_csv(out / "seed_spread.csv", index=False)
    pd.DataFrame(audit).to_csv(out / "audit.csv", index=False)
    print(pd.DataFrame(audit).to_string(index=False))


if __name__ == "__main__":
    main()
