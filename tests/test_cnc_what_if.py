import numpy as np
import pandas as pd
import pytest

from ml import cnc_what_if


class FakeClassifier:
    classes_ = np.asarray([0, 1])
    feature_names_in_ = np.asarray([
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]",
        "Type_L",
        "Type_M",
        "Type_H",
    ])

    def predict_proba(self, features):
        assert list(features.columns) == list(self.feature_names_in_)
        assert len(features) == 1
        return np.asarray([[0.82, 0.18]])


def test_build_cnc_model_input_converts_temperature_and_aligns_features():
    features = [
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]",
        "Type_L",
        "Type_M",
        "Type_H",
    ]
    result = cnc_what_if.build_cnc_model_input(
        {"Temperature": 25, "RPM": 1200, "Torque": 30, "Tool Wear": 45},
        features,
    )

    assert list(result.columns) == features
    assert result.loc[0, "Air temperature [K]"] == pytest.approx(298.15)
    assert result.loc[0, "Process temperature [K]"] == pytest.approx(308.15)
    assert result.loc[0, "Rotational speed [rpm]"] == 1200
    assert result.loc[0, "Torque [Nm]"] == 30
    assert result.loc[0, "Tool wear [min]"] == 45
    assert result.loc[0, "Type_M"] == 1
    assert result.loc[0, "Type_L"] == 0
    assert result.loc[0, "Type_H"] == 0


@pytest.mark.parametrize(
    "values",
    [
        {"Temperature": 25, "RPM": 1200, "Torque": 30},
        {"Temperature": "hot", "RPM": 1200, "Torque": 30, "Tool Wear": 45},
        {"Temperature": float("nan"), "RPM": 1200, "Torque": 30, "Tool Wear": 45},
        {"Temperature": -300, "RPM": 1200, "Torque": 30, "Tool Wear": 45},
        {"Temperature": 25, "RPM": -1, "Torque": 30, "Tool Wear": 45},
        {"Temperature": 25, "RPM": 1200, "Torque": 30, "Tool Wear": -1},
    ],
)
def test_build_cnc_model_input_rejects_invalid_sensor_values(values):
    with pytest.raises(ValueError):
        cnc_what_if.build_cnc_model_input(
            values,
            ["Air temperature [K]", "Type_M"],
        )


def test_predict_cnc_risk_loads_model_package_and_returns_percent(tmp_path, monkeypatch):
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"test")
    model = FakeClassifier()
    monkeypatch.setattr(
        cnc_what_if.joblib,
        "load",
        lambda path: {"model": model, "features": list(model.feature_names_in_)},
    )

    risk = cnc_what_if.predict_cnc_risk(
        {"Temperature": 25, "RPM": 1200, "Torque": 30, "Tool Wear": 45},
        model_path=model_path,
    )

    assert risk == 18.0


def test_predict_cnc_risk_rejects_unexpected_model_package(tmp_path, monkeypatch):
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(b"test")
    monkeypatch.setattr(cnc_what_if.joblib, "load", lambda path: [])
    with pytest.raises(ValueError, match="unexpected format"):
        cnc_what_if.predict_cnc_risk(
            {"Temperature": 25, "RPM": 1200, "Torque": 30, "Tool Wear": 45},
            model_path=model_path,
        )


def test_predict_cnc_risk_requires_existing_model_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="unavailable"):
        cnc_what_if.predict_cnc_risk(
            {"Temperature": 25, "RPM": 1200, "Torque": 30, "Tool Wear": 45},
            model_path=tmp_path / "missing.joblib",
        )
