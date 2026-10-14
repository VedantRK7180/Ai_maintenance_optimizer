import pytest

from ml.robot_features import build_robot_feature_row


def reading(position, temperature, voltage):
    return {"Position": position, "Temperature": temperature, "Voltage": voltage}


def test_builds_delta_and_rolling_features_from_history():
    row = build_robot_feature_row(
        reading(3, 30, 220),
        [reading(1, 20, 200), reading(2, 25, 210), reading(3, 30, 220)],
    )
    assert row["position"] == 3.0
    assert row["position_change"] == 1.0
    assert row["temperature_change"] == 5.0
    assert row["voltage_change"] == 10.0
    assert row["position_rolling_mean"] == 2.0
    assert row["position_rolling_std"] == pytest.approx(1.0)


def test_single_reading_uses_zero_delta_and_std():
    row = build_robot_feature_row(reading(4, 40, 240))
    assert row["position_change"] == 0.0
    assert row["position_rolling_std"] == 0.0
    assert row["temperature_rolling_mean"] == 40.0


def test_missing_required_sensor_raises_clear_error():
    with pytest.raises(ValueError, match="Temperature"):
        build_robot_feature_row({"Position": 1, "Voltage": 2})


def test_missing_model_feature_raises_clear_error():
    with pytest.raises(ValueError, match="unknown_feature"):
        build_robot_feature_row(reading(1, 2, 3), feature_names=["unknown_feature"])


def test_history_is_limited_to_latest_ten_readings():
    history = [reading(i, i * 10, i * 100) for i in range(1, 12)]
    row = build_robot_feature_row(reading(11, 110, 1100), history)
    assert row["position_rolling_mean"] == pytest.approx(6.5)
