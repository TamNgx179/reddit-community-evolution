r"""Regenerate tests/fixtures/prediction/samples_mini.csv from the real generator.

Usage (from repo root, inside the venv):
    & .\.venv\Scripts\python.exe tests/fixtures/prediction/make_samples_mini.py

The fixture is a deterministic slice of generate_community_table(seed=42):
for each chosen feature month it keeps the first row of every label class, so
all 6 classes appear, community ids stay local per month, and rows are real
generator output (not hand-written). The slice covers:
  - train       (label_month 2015-02 .. 2016-12)
  - validation  (label_month 2017-01 .. 2017-06)
  - test        (label_month 2017-07 .. 2017-12)
  - rows with no history (age 0, size_tm1/size_tm2 empty)
  - rows with empty label (feature_month 2017-12)
"""
from pathlib import Path

from reddit_sna.benchmarks.community_table import generate_community_table

SEED = 42
# feature_month -> label_month is next month; 2017-12 has empty label.
MONTHS = [
    "2015-01", "2015-02",              # train (2015-01 rows have age 0, no history)
    "2016-10", "2016-11",              # train (label_month 2016-11 / 2016-12)
    "2016-12", "2017-05",              # validation (label_month 2017-01 / 2017-06)
    "2017-06", "2017-11",              # test (label_month 2017-07 / 2017-12)
]
LAST_MONTH = "2017-12"                 # label empty
N_LAST = 8                             # how many empty-label rows to keep


def build():
    df = generate_community_table(SEED)
    parts = []
    for month in MONTHS:
        m = df[df["feature_month"] == month].sort_values("community_id")
        for _, grp in m.groupby("label", sort=True):
            parts.append(grp.head(1))
    last = df[df["feature_month"] == LAST_MONTH].sort_values("community_id").head(N_LAST)
    parts.append(last)
    import pandas as pd
    out = pd.concat(parts).sort_values(["feature_month", "community_id"]).reset_index(drop=True)
    return out


if __name__ == "__main__":
    out = build()
    target = Path(__file__).resolve().parent / "samples_mini.csv"
    out.to_csv(target, index=False, lineterminator="\n", encoding="utf-8")
    print(f"wrote {len(out)} rows -> {target}")