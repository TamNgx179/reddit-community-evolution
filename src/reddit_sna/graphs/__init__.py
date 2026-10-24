"""Monthly reply observations, user projections and graph provenance.

The implemented snapshot builder preserves directed replies and UTC cutoffs,
constructs the weighted undirected R projection, and records active users,
isolates, losses and source hashes. Detection consumes these representations.
Typed heterogeneous relations and additional co-thread projection operators are
research extensions, not implemented by this package initializer. See
docs/METHODS.md and reports/WEEK1_REPORT.md for current semantics and scope.
"""
