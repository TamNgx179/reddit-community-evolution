"""HeTCo: group-node attention forecaster in NumPy (after Revelle et al. 2021).

A community embedding pools its member node attributes with learned additive
attention, alpha_i = softmax_i(v . tanh(W x_i + b)), then a head reads
[sum_i alpha_i x_i, community attributes]. `pooling="mean"` replaces attention
with uniform weights as the matched ablation.

Two heads exist. "flat" is one six-class softmax. "hierarchical" estimates
dissolve versus other with a sigmoid, then the five other events conditional on
other, and multiplies them into the six-event vector. `class_weight` sets the
cross-entropy weights for each head: "balanced" (n / (K * count)), "sqrt" (its
square root) or "none". Settings are fixed in HETCO, and scaling statistics come
from training rows only. This is a lightweight reproduction of the group-node
attention idea, not the authors' full GNN.
"""

import numpy as np

from reddit_sna.contracts import Event

EVENTS = tuple(e.value for e in Event)
DISSOLVE = EVENTS.index("dissolve")
OTHERS = tuple(i for i in range(len(EVENTS)) if i != DISSOLVE)
HETCO = dict(hidden=8, epochs=300, learning_rate=0.01, l2=1e-3)
CLASS_WEIGHTS = ("balanced", "sqrt", "none")
HEADS = ("flat", "hierarchical")


def class_weights(target, classes, scheme):
    """Per-row weights for integer targets in range(classes); absent classes get none."""
    if scheme not in CLASS_WEIGHTS:
        raise ValueError("Unknown HeTCo class weighting")
    if not len(target) or scheme == "none":
        return np.ones(len(target))
    counts = np.bincount(target, minlength=classes)
    balanced = len(target) / (np.count_nonzero(counts) * counts[target])
    return np.sqrt(balanced) if scheme == "sqrt" else balanced


def _segments(bags):
    sizes = np.array([len(b) for b in bags])
    if (sizes == 0).any():
        raise ValueError("Every community needs at least one member")
    return np.concatenate(bags).astype(float), np.repeat(np.arange(len(bags)), sizes), np.r_[0, np.cumsum(sizes)[:-1]]


def _softmax(logits):
    logits = logits - logits.max(axis=1, keepdims=True)
    proba = np.exp(logits)
    return proba / proba.sum(axis=1, keepdims=True)


def _pool(params, members, owner, starts, groups, pooling):
    if pooling == "attention":
        hidden = np.tanh(members @ params["W"].T + params["b"])
        scores = hidden @ params["v"]
        scores = scores - np.maximum.reduceat(scores, starts)[owner]
        weight = np.exp(scores)
        alpha = weight / np.add.reduceat(weight, starts)[owner]
    else:
        hidden = None
        alpha = 1.0 / np.bincount(owner)[owner]
    pooled = np.add.reduceat(alpha[:, None] * members, starts)
    return np.hstack([pooled, groups]), dict(hidden=hidden, alpha=alpha)


def _head(params, z, head):
    """Six-event probabilities plus the intermediate head outputs."""
    if head == "flat":
        return _softmax(z @ params["U"].T + params["c"]), {}
    dissolve = 1.0 / (1.0 + np.exp(-(z @ params["u"] + params["d"][0])))
    other = _softmax(z @ params["U"].T + params["c"])
    proba = np.zeros((len(z), len(EVENTS)))
    proba[:, DISSOLVE] = dissolve
    proba[:, list(OTHERS)] = (1.0 - dissolve)[:, None] * other
    return proba, dict(dissolve=dissolve, other=other)


def _loss_and_grad(params, members, owner, starts, groups, target, weights, pooling, l2, head="flat"):
    """`weights` is one row vector (flat) or a (binary, inner) pair (hierarchical)."""
    z, cache = _pool(params, members, owner, starts, groups, pooling)
    proba, parts = _head(params, z, head)
    n = len(target)
    penalty = 0.5 * l2 * sum(np.sum(params[k] ** 2) for k in ("U", "u", "W", "v") if k in params)
    if head == "flat":
        loss = -np.sum(weights * np.log(proba[np.arange(n), target] + 1e-12)) / n
        dlogits = proba.copy()
        dlogits[np.arange(n), target] -= 1.0
        dlogits *= weights[:, None] / n
        grad = dict(U=dlogits.T @ z + l2 * params["U"], c=dlogits.sum(axis=0))
        dz = dlogits @ params["U"]
    else:
        binary, inner = weights
        is_dissolve = (target == DISSOLVE).astype(float)
        p = parts["dissolve"]
        loss = -np.sum(binary * (is_dissolve * np.log(p + 1e-12)
                                 + (1 - is_dissolve) * np.log(1 - p + 1e-12))) / n
        dbinary = binary * (p - is_dissolve) / n
        rest = np.flatnonzero(target != DISSOLVE)
        inner_target = np.array([OTHERS.index(t) for t in target[rest]], dtype=int)
        dlogits = np.zeros((n, len(OTHERS)))
        if len(rest):
            q = parts["other"][rest]
            loss -= np.sum(inner * np.log(q[np.arange(len(rest)), inner_target] + 1e-12)) / n
            local = q.copy()
            local[np.arange(len(rest)), inner_target] -= 1.0
            dlogits[rest] = local * inner[:, None] / n
        grad = dict(U=dlogits.T @ z + l2 * params["U"], c=dlogits.sum(axis=0),
                    u=dbinary @ z + l2 * params["u"], d=np.array([dbinary.sum()]))
        dz = dlogits @ params["U"] + np.outer(dbinary, params["u"])
    if pooling == "attention":
        dpooled = dz[:, :members.shape[1]]
        alpha, hidden = cache["alpha"], cache["hidden"]
        dalpha = np.sum(dpooled[owner] * members, axis=1)
        dscore = alpha * (dalpha - np.add.reduceat(alpha * dalpha, starts)[owner])
        dpre = np.outer(dscore, params["v"]) * (1.0 - hidden ** 2)
        grad.update(v=hidden.T @ dscore + l2 * params["v"],
                    W=dpre.T @ members + l2 * params["W"], b=dpre.sum(axis=0))
    return loss + penalty, grad


def _scale(values, mean, std):
    return (np.asarray(values, dtype=float) - mean) / std


def fit_hetco(bags, groups, labels, seed, pooling="attention", settings=HETCO,
              class_weight="balanced", head="flat"):
    """Fit on training communities; unseen classes keep only their learned bias."""
    if pooling not in {"attention", "mean"} or head not in HEADS or class_weight not in CLASS_WEIGHTS:
        raise ValueError("Unknown HeTCo pooling, head or class weighting")
    if not bags or len(bags) != len(groups) or len(bags) != len(labels):
        raise ValueError("HeTCo needs aligned nonempty training bags, attributes and labels")
    members, owner, starts = _segments(bags)
    groups = np.asarray(groups, dtype=float)
    if not (np.isfinite(members).all() and np.isfinite(groups).all()):
        raise ValueError("HeTCo inputs must be finite")
    scaling = dict(member_mean=members.mean(axis=0), member_std=members.std(axis=0) + 1e-9,
                   group_mean=groups.mean(axis=0), group_std=groups.std(axis=0) + 1e-9)
    members = _scale(members, scaling["member_mean"], scaling["member_std"])
    groups = _scale(groups, scaling["group_mean"], scaling["group_std"])
    target = np.array([EVENTS.index(y) for y in labels])
    counts = np.bincount(target, minlength=len(EVENTS))
    rng = np.random.default_rng(seed)
    d, h = members.shape[1], settings["hidden"]
    width = d + groups.shape[1]
    if head == "flat":
        weights = class_weights(target, len(EVENTS), class_weight)
        params = dict(U=rng.normal(0, 0.1, (len(EVENTS), width)), c=np.zeros(len(EVENTS)))
    else:
        rest = target[target != DISSOLVE]
        weights = (class_weights((target == DISSOLVE).astype(int), 2, class_weight),
                   class_weights(np.array([OTHERS.index(t) for t in rest], dtype=int), len(OTHERS), class_weight))
        params = dict(U=rng.normal(0, 0.1, (len(OTHERS), width)), c=np.zeros(len(OTHERS)),
                      u=rng.normal(0, 0.1, width), d=np.zeros(1))
    if pooling == "attention":
        params.update(W=rng.normal(0, 0.1, (h, d)), b=np.zeros(h), v=rng.normal(0, 0.1, h))
    moment = {key: np.zeros_like(value) for key, value in params.items()}
    second = {key: np.zeros_like(value) for key, value in params.items()}
    losses = []
    for step in range(1, settings["epochs"] + 1):
        loss, grad = _loss_and_grad(params, members, owner, starts, groups, target, weights,
                                    pooling, settings["l2"], head)
        losses.append(float(loss))
        for key in params:
            moment[key] = 0.9 * moment[key] + 0.1 * grad[key]
            second[key] = 0.999 * second[key] + 0.001 * grad[key] ** 2
            corrected = moment[key] / (1 - 0.9 ** step)
            params[key] -= settings["learning_rate"] * corrected / (
                np.sqrt(second[key] / (1 - 0.999 ** step)) + 1e-8)
    return dict(params=params, scaling=scaling, pooling=pooling, head=head, class_weight=class_weight,
                seed=seed, settings=dict(settings), train_loss=losses, single_class=len(set(labels)) < 2,
                missing_train_classes=[e for e, n in zip(EVENTS, counts) if n == 0])


def predict_hetco(fitted, bags, groups):
    """Return predicted events, six-class probabilities and per-member attention."""
    members, owner, starts = _segments(bags)
    s = fitted["scaling"]
    z, cache = _pool(fitted["params"], _scale(members, s["member_mean"], s["member_std"]),
                     owner, starts, _scale(groups, s["group_mean"], s["group_std"]), fitted["pooling"])
    proba, _ = _head(fitted["params"], z, fitted.get("head", "flat"))
    attention = np.split(cache["alpha"], starts[1:])
    return [EVENTS[i] for i in proba.argmax(axis=1)], proba, attention
