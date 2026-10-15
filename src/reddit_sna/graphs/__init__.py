"""Graph definitions, temporal snapshots and user projections (Tâm).

Planned responsibilities, not implemented algorithms:
- Preserve directed reply observations and UTC observation cutoffs.
- Define user/post/comment/subreddit nodes and typed heterogeneous relations.
- Build R (reply) and T (co-thread) user layers; version projection weights.
- Separate active users from edge-covered users; report isolates and losses.
- Record graph identity, window, direction, weights and detector objective.
- Bound thread projection costs explicitly; never silently sample or drop edges.

Detection consumes graph representations from here. A user projection is not
the original heterogeneous graph. See experiments/study.toml and ARCHITECTURE.
"""
