"""Helpers for interpreting classifier failure risk by class label."""
from __future__ import annotations

from typing import Any
import numpy as np

_FAILURE_LABELS = {"1", "true", "yes", "failure", "failed", "fail", "positive"}
_NORMAL_LABELS = {"0", "false", "no", "normal", "healthy", "negative"}


def _label_kind(label: Any) -> str | None:
    if isinstance(label, (bool, np.bool_)):
        return "failure" if bool(label) else "normal"
    if isinstance(label, (int, np.integer)):
        if int(label) == 1:
            return "failure"
        if int(label) == 0:
            return "normal"
    if isinstance(label, (float, np.floating)) and np.isfinite(label):
        if float(label) == 1.0:
            return "failure"
        if float(label) == 0.0:
            return "normal"
    normalized = str(label).strip().lower()
    if normalized in _FAILURE_LABELS:
        return "failure"
    if normalized in _NORMAL_LABELS:
        return "normal"
    return None


def predict_failure_probability(model: Any, features: Any) -> float:
    """Return risk from 0 to 1; fail explicitly when class meaning is unclear."""
    if hasattr(model, "predict_proba"):
        probabilities = np.asarray(model.predict_proba(features)[0], dtype=float)
        classes = list(getattr(model, "classes_", []))
        if len(classes) != len(probabilities):
            raise ValueError("Model class labels do not match predict_proba output.")
        indices = [i for i, label in enumerate(classes) if _label_kind(label) == "failure"]
        if len(indices) == 1:
            risk = float(probabilities[indices[0]])
            if not np.isfinite(risk):
                raise ValueError("Model returned a non-finite failure probability.")
            return float(np.clip(risk, 0.0, 1.0))
        if len(classes) == 1:
            kind = _label_kind(classes[0])
            if kind == "failure":
                return 1.0
            if kind == "normal":
                return 0.0
        raise ValueError(f"Cannot identify failure class from model labels: {classes!r}")
    prediction = model.predict(features)[0]
    kind = _label_kind(prediction)
    if kind == "failure":
        return 1.0
    if kind == "normal":
        return 0.0
    raise ValueError(f"Unrecognized binary failure label: {prediction!r}")


def classify_failure_prediction(prediction: Any) -> str:
    """Map a model prediction to a safe display label; reject unknown classes."""
    kind = _label_kind(prediction)
    if kind == "failure":
        return "FAILURE RISK"
    if kind == "normal":
        return "NORMAL"
    raise ValueError(f"Unrecognized binary failure label: {prediction!r}")
