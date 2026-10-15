"""Temporal splits and metrics (Anh), leakage/bootstrap checks (Đăng).

Implement splits by label_month and compare identical sample/reference keys.
Metric computations and bootstrap are not implemented yet.

Separate graph/partition quality, tracker validity and forecast accuracy.
Split by whole label months rather than arbitrary community rows. Compare
identical sample keys/truth/reference versions; report missing classes and
excluded samples. Algorithm seeds measure stochastic variability, not new
independent datasets. Use paired time-block comparisons for temporal outcomes
and report uncertainty limitations when only a few months are available.
"""
