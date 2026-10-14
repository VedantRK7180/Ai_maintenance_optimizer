"""Pure feature construction helpers for robot sensor time-series inference."""

import pandas as pd

REQUIRED_SENSOR_NAMES = ("Position", "Temperature", "Voltage")
DEFAULT_FEATURES = [
    "position", "temperature", "voltage",
    "position_change", "temperature_change", "voltage_change",
    "position_rolling_mean", "temperature_rolling_mean", "voltage_rolling_mean",
    "position_rolling_std", "temperature_rolling_std", "voltage_rolling_std",
]


def build_robot_feature_row(sensor_data, sensor_history=None, feature_names=None):
    """Build model inputs from current values and up to 10 complete recent readings.

    The input history must be oldest-first. Missing/incomplete sensor readings are
    ignored; when history lacks the current reading, current values are appended.
    """
    missing = [name for name in REQUIRED_SENSOR_NAMES if sensor_data.get(name) is None]
    if missing:
        raise ValueError("Robot sensor data missing: " + ", ".join(missing))

    current = {
        "position": float(sensor_data["Position"]),
        "temperature": float(sensor_data["Temperature"]),
        "voltage": float(sensor_data["Voltage"]),
    }
    complete_history = []
    for reading in sensor_history or []:
        if all(reading.get(name) is not None for name in REQUIRED_SENSOR_NAMES):
            complete_history.append({
                "position": float(reading["Position"]),
                "temperature": float(reading["Temperature"]),
                "voltage": float(reading["Voltage"]),
            })

    if not complete_history or complete_history[-1] != current:
        complete_history.append(current)
    frame = pd.DataFrame(complete_history[-10:])

    feature_row = {}
    for column in ("position", "temperature", "voltage"):
        values = frame[column]
        feature_row[column] = float(values.iloc[-1])
        feature_row[f"{column}_change"] = (
            float(values.iloc[-1] - values.iloc[-2]) if len(values) >= 2 else 0.0
        )
        feature_row[f"{column}_rolling_mean"] = float(values.mean())
        feature_row[f"{column}_rolling_std"] = (
            float(values.std(ddof=1)) if len(values) >= 2 else 0.0
        )

    expected = feature_names or DEFAULT_FEATURES
    missing_features = [name for name in expected if name not in feature_row]
    if missing_features:
        raise ValueError("Missing robot model features: " + ", ".join(missing_features))
    return feature_row
