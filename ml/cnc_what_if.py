"""Pure helpers for model-based CNC what-if predictions (no database writes)."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from ml.model_utils import predict_failure_probability

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = BASE_DIR / "ml" / "cnc_model_baseline.joblib"
REQUIRED_SENSOR_VALUES = ("Temperature", "RPM", "Torque", "Tool Wear")


def build_cnc_model_input(sensor_values: dict[str, Any], features: list[str]) -> pd.DataFrame:
    """Build the same ordered AI4I feature columns used by the existing CNC model."""
    missing = [name for name in REQUIRED_SENSOR_VALUES if name not in sensor_values]
    if missing:
        raise ValueError("Missing sensor values: " + ", ".join(missing))

    values = {}
    for name in REQUIRED_SENSOR_VALUES:
        try:
            value = float(sensor_values[name])
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a finite number.") from None
        if not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number.")
        values[name] = value

    if values["Temperature"] < -273.15:
        raise ValueError("Temperature cannot be below absolute zero.")
    if values["RPM"] < 0 or values["Torque"] < 0 or values["Tool Wear"] < 0:
        raise ValueError("RPM, Torque, and Tool Wear cannot be negative.")

    air_temperature = values["Temperature"] + 273.15
    frame = pd.DataFrame([{
        "Type": "M",
        "Air temperature [K]": air_temperature,
        "Process temperature [K]": air_temperature + 10.0,
        "Rotational speed [rpm]": values["RPM"],
        "Torque [Nm]": values["Torque"],
        "Tool wear [min]": values["Tool Wear"],
    }])
    frame = pd.get_dummies(frame, columns=["Type"], dtype=int)
    for feature in features:
        if feature not in frame.columns:
            frame[feature] = 0
    return frame[list(features)]


def predict_cnc_risk(sensor_values: dict[str, Any], model_path: str | Path | None = None) -> float:
    """Return model-estimated failure risk in percent for one set of sensor values."""
    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not path.is_file():
        raise FileNotFoundError("The CNC model file is unavailable.")
    package = joblib.load(path)
    if not isinstance(package, dict) or "model" not in package:
        raise ValueError("The CNC model package has an unexpected format.")
    model = package["model"]
    features = package.get("features") or list(getattr(model, "feature_names_in_", []))
    if not features:
        raise ValueError("The CNC model does not declare its expected input features.")
    model_input = build_cnc_model_input(sensor_values, list(features))
    return round(predict_failure_probability(model, model_input) * 100.0, 2)
