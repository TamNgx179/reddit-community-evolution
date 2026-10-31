"""Fixed-width member means for a controlled, causal feature comparison.

The extractor owns observation cutoffs. This module only aggregates its thirteen
declared attributes, without consulting community targets or future membership.
"""
import numpy as np
from reddit_sna.features.members import MEMBER_FEATURES, EXTENDED_FEATURES

MEAN_FIELDS = tuple('member_mean_' + f for f in MEMBER_FEATURES + EXTENDED_FEATURES)


def member_mean(bag):
    """Return thirteen finite means, rejecting empty or incompatible member bags."""
    values = np.asarray(bag, dtype=float)
    if (values.ndim != 2 or not len(values) or values.shape[1] != len(MEAN_FIELDS)
            or not np.isfinite(values).all()):
        raise ValueError('Member summary requires a nonempty finite thirteen-column bag')
    return dict(zip(MEAN_FIELDS, map(float, values.mean(axis=0))))
