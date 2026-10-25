"""Equally budgeted flat and disappearance-conditional event forecasters."""

from collections import Counter
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from reddit_sna.evaluation.temporal_protocol import COUNT_FIELDS, EVENTS, SETTINGS
from reddit_sna.evaluation.research import score


def feature_matrix(rows, fields, settings):
    """Log only declared counts; retain signed dynamics and all bounded ratios."""
    values = np.asarray([[float(r[f]) for f in fields] for r in rows], dtype=float).reshape(len(rows), len(fields))
    if not fields or not np.isfinite(values).all():
        raise ValueError("Finite nonempty feature schema required")
    for index, field in enumerate(fields):
        if field in COUNT_FIELDS:
            if (values[:, index] < 0).any():
                raise ValueError("Count features must be nonnegative")
            if settings.get('transform') == 'log_counts':
                values[:, index] = np.log1p(values[:, index])
    return values


def _head(matrix, labels, settings, seed):
    if not labels:
        return None
    if len(set(labels)) == 1:
        model = DummyClassifier(strategy='most_frequent')
    elif settings['estimator'] == 'lr':
        model = make_pipeline(StandardScaler(), LogisticRegression(C=settings['C'],
            class_weight=settings['class_weight'], max_iter=3000, random_state=seed))
    else:
        model = HistGradientBoostingClassifier(learning_rate=.05, max_iter=150,
            max_leaf_nodes=settings['max_leaf_nodes'], min_samples_leaf=settings['min_samples_leaf'],
            class_weight=settings['class_weight'], l2_regularization=1., early_stopping=False,
            random_state=seed)
    return model.fit(matrix, labels)


def fit_activity_model(rows, fields, settings, hierarchical=False, seed=42):
    """Fit using training labels only; never infer classes from evaluation data."""
    estimator = settings.get('estimator')
    if not rows or estimator not in SETTINGS or settings not in SETTINGS[estimator]:
        raise ValueError("Nonempty training data and frozen candidate settings required")
    labels = [r['label'] for r in rows]
    if any(label not in EVENTS for label in labels):
        raise ValueError("Unknown training event")
    matrix = feature_matrix(rows, fields, settings)
    output = dict(fields=tuple(fields), settings=dict(settings), hierarchical=bool(hierarchical),
        seed=seed, support=dict(Counter(labels)), latest_train_label=max(r['label_month'] for r in rows))
    if hierarchical:
        output['gate'] = _head(matrix, ['dissolve' if v == 'dissolve' else 'other' for v in labels], settings, seed)
        mask = np.asarray([v != 'dissolve' for v in labels])
        output['conditional'] = _head(matrix[mask], [v for v in labels if v != 'dissolve'], settings, seed)
        output['fallback'] = len(set(labels)) == 1 or len(set(v for v in labels if v != 'dissolve')) < 2
    else:
        output['flat'] = _head(matrix, labels, settings, seed)
        output['fallback'] = len(set(labels)) == 1
    return output


def _probabilities(model, matrix, labels):
    values = np.zeros((len(matrix), len(labels)))
    if model is not None and len(matrix):
        probabilities=model.predict_proba(matrix)
        for index, label in enumerate(model.classes_):
            if label not in labels:
                raise ValueError("Unexpected fitted head class")
            values[:, labels.index(label)] = probabilities[:, index]
    return values


def predict_activity_model(fitted, rows):
    """Compose six probabilities; numpy argmax preserves fixed event-order ties."""
    matrix = feature_matrix(rows, fitted['fields'], fitted['settings'])
    if fitted['hierarchical']:
        gate = _probabilities(fitted['gate'], matrix, ('dissolve', 'other'))[:, 0]
        values = _probabilities(fitted['conditional'], matrix, EVENTS)
        values *= (1 - gate[:, None])
        values[:, EVENTS.index('dissolve')] = gate
    else:
        values = _probabilities(fitted['flat'], matrix, EVENTS)
    if not np.isfinite(values).all() or (values < 0).any() or not np.allclose(values.sum(axis=1), 1):
        raise ValueError("Event probabilities must be finite and sum to one")
    predicted = [EVENTS[i] for i in values.argmax(axis=1)]
    return predicted, values.tolist(), [int(fitted['fallback'])] * len(rows)


def select_activity_model(rows, fields, estimator, hierarchical, origins):
    """Expanding whole-month validation; current/future outcomes never enter fits."""
    if estimator not in SETTINGS or not origins or origins != sorted(set(origins)):
        raise ValueError("Declared estimator and ordered validation months required")
    folds = []
    for month in origins:
        train = [r for r in rows if r['label_month'] < month]
        valid = [r for r in rows if r['label_month'] == month]
        if not train or not valid:
            raise ValueError("Every declared validation origin needs train and validation samples")
        folds.append((month, train, valid))
    candidates, evidence = [], []
    for candidate, settings in enumerate(SETTINGS[estimator]):
        predictions, metadata = [], []
        for month, train, valid in folds:
            fitted = fit_activity_model(train, fields, settings, hierarchical)
            guessed, _, flags = predict_activity_model(fitted, valid)
            for row, pred, fallback in zip(valid, guessed, flags):
                record = {k:row[k] for k in ('reference_id','feature_month','community_id','label_month','label_reference_id')}
                record.update(candidate=candidate, y_true=row['label'], y_pred=pred, fallback=fallback)
                evidence.append(record)
                predictions.append(record)
            metadata.append(dict(month=month, train_n=len(train), validation_n=len(valid),
                latest_train_label=fitted['latest_train_label'], support=fitted['support'], fallback=fitted['fallback']))
        candidates.append(dict(candidate=candidate, settings=settings, folds=metadata,
                               macro_f1=score(predictions)['macro_f1_six']))
    chosen = max(candidates, key=lambda r:r['macro_f1'])
    return dict(selected=chosen['candidate'], settings=chosen['settings'],
                macro_f1=chosen['macro_f1'], candidates=candidates), evidence
