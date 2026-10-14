import numpy as np

from ml.nasa_ims_features import calculate_features


def test_calculate_features_for_known_signal():
    result = calculate_features(np.array([-1.0, 0.0, 1.0]))

    assert result is not None
    assert result["mean"] == 0.0
    assert result["min"] == -1.0
    assert result["max"] == 1.0
    assert result["peak_to_peak"] == 2.0
    assert result["peak"] == 1.0
    assert np.isclose(result["rms"], np.sqrt(2.0 / 3.0))
    assert np.isclose(result["crest_factor"], 1.0 / np.sqrt(2.0 / 3.0))
    assert np.isclose(result["kurtosis"], 1.5)


def test_calculate_features_ignores_non_finite_samples():
    result = calculate_features(np.array([1.0, np.nan, np.inf, 3.0]))

    assert result is not None
    assert result["mean"] == 2.0
    assert result["min"] == 1.0
    assert result["max"] == 3.0
    assert result["sample_count"] if "sample_count" in result else True


def test_calculate_features_returns_none_for_empty_or_invalid_signal():
    assert calculate_features(np.array([])) is None
    assert calculate_features(np.array([np.nan, np.inf, -np.inf])) is None


def test_constant_signal_has_zero_std_and_kurtosis():
    result = calculate_features(np.array([4.0, 4.0, 4.0]))

    assert result is not None
    assert result["std"] == 0.0
    assert result["crest_factor"] == 1.0
    assert result["kurtosis"] == 0.0
