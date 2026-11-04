# B2 Random Forest Seed Agreement

This diagnostic evaluates prediction consistency across random seeds for
B2 Random Forest on the frozen final prediction window.

- Model: B2 Random Forest
- Seeds: 42, 43, 44
- Unique final samples: 1,269
- All three seeds agree: 1,238 (97.56%)
- At least one seed differs: 31 (2.44%)

Pairwise agreement:
- Seeds 42 and 43: 98.98%
- Seeds 42 and 44: 98.35%
- Seeds 43 and 44: 97.79%

Agreement measures consistency between runs, not predictive correctness.
The three seeds are repeated model runs on the same samples, not independent
sample observations.

The sample-level agreement export is retained in the external analysis
output folder and is not included in this repository package.
