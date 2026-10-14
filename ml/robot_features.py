"""Pure feature construction helpers for robot sensor time-series inference."""

import math

import pandas as pd

REQUIRED_SENSOR_NAMES = ("Position", "Temperature", "Voltage")
DEFAULT_FEATURES = [
    "position", "temperature", "voltage",
    "position_change", "temperature_change", "voltage_change",
    "position_rolling_mean", "temperature_rolling_mean", "voltage_rolling_mean",
    "position_rolling_std", "temperature_rolling_std", "voltage_rolling_std",
]


def _normalise_reading(reading):
    """Return a complete finite sensor reading, or None if it is incomplete/invalid."""
    if not all(reading.get(name) is not None for name in REQUIRED_SENSOR_NAMES):
        return None

    try:
        values = {
            "position": float(reading["Position"]),
            "temperature": float(reading["Temperature"]),
            "voltage": float(reading["Voltage"]),
        }
    except (TypeError, ValueError):
        return None

    if not all(math.isfinite(value) for value in values.values()):
        return None
    return values


def build_robot_feature_row(sensor_data, sensor_history=None, feature_names=None):
    """Build model inputs from current values and up to 10 complete recent readings.

    History must be oldest-first. Incomplete, non-numeric, and non-finite historical
    readings are ignored. The current reading must be complete and finite.
    """
    current = _normalise_reading(sensor_data)
    if current is None:
        missing = [
            name for name in REQUIRED_SENSOR_NAMES
            if sensor_data.get(name) is None
        ]
        if missing:
            raise ValueError("Robot sensor data missing or invalid: " + ", ".join(missing))
        raise ValueError("Robot sensor data must contain finite numeric values.")

    complete_history = []
    for reading in sensor_history or []:
        normalised = _normalise_reading(reading)
        if normalised is not None:
            complete_history.append(normalised)

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
