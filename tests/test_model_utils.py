import numpy as np
import pytest

from ml.model_utils import classify_failure_prediction, predict_failure_probability


class FakeClassifier:
    def __init__(self, classes, probabilities, prediction=0):
        self.classes_ = np.asarray(classes)
        self.probabilities = np.asarray(probabilities, dtype=float)
        self.prediction = prediction

    def predict_proba(self, features):
        return np.asarray([self.probabilities])

    def predict(self, features):
        return np.asarray([self.prediction])


class PredictionOnlyClassifier:
    def __init__(self, prediction):
        self.prediction = prediction

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


def test_probability_output_must_match_class_count():
    model = FakeClassifier([0, 1], [0.2])
    with pytest.raises(ValueError, match="class labels do not match"):
        predict_failure_probability(model, [[1]])


def test_prediction_only_model_returns_binary_estimate():
    assert predict_failure_probability(PredictionOnlyClassifier(1), [[1]]) == 1.0
    assert predict_failure_probability(PredictionOnlyClassifier(0), [[1]]) == 0.0


def test_prediction_only_model_rejects_unknown_label():
    with pytest.raises(ValueError, match="Unrecognized binary failure label"):
        predict_failure_probability(PredictionOnlyClassifier("unknown"), [[1]])


@pytest.mark.parametrize(
    ("prediction", "expected"),
    [(1, "FAILURE RISK"), (0, "NORMAL"), (True, "FAILURE RISK"), (False, "NORMAL"), ("failure", "FAILURE RISK"), ("healthy", "NORMAL")],
)
def test_classify_failure_prediction_recognizes_supported_labels(prediction, expected):
    assert classify_failure_prediction(prediction) == expected


def test_classify_failure_prediction_rejects_unknown_label():
    with pytest.raises(ValueError, match="Unrecognized binary failure label"):
        classify_failure_prediction("unknown")
