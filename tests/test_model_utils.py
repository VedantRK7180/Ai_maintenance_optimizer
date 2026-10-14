import numpy as np
import pytest

from ml.model_utils import predict_failure_probability


class FakeClassifier:
    def __init__(self, classes, probabilities, prediction=0):
        self.classes_ = np.asarray(classes)
        self.probabilities = np.asarray(probabilities, dtype=float)
        self.prediction = prediction

    def predict_proba(self, features):
        return np.asarray([self.probabilities])

    def predict(self, features):
        return np.asarray([self.prediction])


def test_failure_probability_uses_label_not_column_position():
    model = FakeClassifier(classes=[0, 1], probabilities=[0.91, 0.09])
    assert predict_failure_probability(model, [[1]]) == pytest.approx(0.09)


def test_failure_probability_handles_reversed_class_order():
    model = FakeClassifier(classes=[1, 0], probabilities=[0.09, 0.91])
    assert predict_failure_probability(model, [[1]]) == pytest.approx(0.09)


def test_failure_probability_supports_string_labels():
    model = FakeClassifier(
        classes=["failure", "normal"],
        probabilities=[0.23, 0.77],
    )
    assert predict_failure_probability(model, [[1]]) == pytest.approx(0.23)


def test_unknown_class_labels_raise_instead_of_guessing():
    model = FakeClassifier(classes=["normal", "warning"], probabilities=[0.7, 0.3])
    with pytest.raises(ValueError, match="Cannot identify"):
        predict_failure_probability(model, [[1]])


def test_single_class_normal_model_returns_zero_risk():
    model = FakeClassifier(classes=[0], probabilities=[1.0])
    assert predict_failure_probability(model, [[1]]) == 0.0
