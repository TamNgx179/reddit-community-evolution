"""Community tracking: Jaccard (Đăng) and adapted GED (Thanh), not yet implemented.

Use explicit TrackingLink records; do not equate cluster IDs across snapshots.
Keep different tracker reference IDs separate.

Tracking links, event assignment and lineage are distinct operations. Validate
the tracker on ground-truth partitions before evaluating detection+tracking.
Document GED adaptations and member-importance measures; plain overlap is not
the full GED method. Track forming groups separately from the six forecast
labels, and never mark the last unobserved transition as dissolve.
"""
