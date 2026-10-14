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


def test_failure_probability_uses_label():
    model = FakeClassifier([0, 1], [0.91, 0.09])
    assert predict_failure_probability(model, [[1]]) == pytest.approx(0.09)


def test_failure_probability_handles_reversed_class_order():
    model = FakeClassifier([1, 0], [0.09, 0.91])
    assert predict_failure_probability(model, [[1]]) == pytest.approx(0.09)


def test_failure_probability_supports_string_labels():
    model = FakeClassifier(["failure", "normal"], [0.23, 0.77])
    assert predict_failure_probability(model, [[1]]) == pytest.approx(0.23)


def test_unknown_class_labels_raise_clear_error():
    model = FakeClassifier(["A", "B"], [0.5, 0.5])
    with pytest.raises(ValueError, match="Cannot identify failure class"):
        predict_failure_probability(model, [[1]])


def test_probability_is_clamped_to_valid_range():
    model = FakeClassifier([0, 1], [0.2, 1.5])
    assert predict_failure_probability(model, [[1]]) == pytest.approx(1.0)
