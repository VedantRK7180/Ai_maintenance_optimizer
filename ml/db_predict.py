"""Run one CNC failure-risk prediction from the latest MySQL sensor reading.

This script is intentionally safe to import: database connections and model inference
only happen when run as a script or when main() is called explicitly.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from ml.cnc_what_if import build_cnc_model_input
from ml.model_utils import predict_failure_probability

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ml" / "cnc_model_baseline.joblib"
DEFAULT_MACHINE_NAME = "CNC-102"


def main() -> int:
    """Load configuration, read the latest machine data, predict risk, and clean up."""
    load_dotenv(BASE_DIR / ".env")

    mysql_password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD"))
    if not mysql_password:
        raise RuntimeError(
            "MYSQL_PASSWORD is missing. Add your existing MySQL password to the local .env file."
        )
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Model file is missing: {MODEL_PATH}")

    import joblib
    import mysql.connector

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost")),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", os.getenv("DB_USER", "root")),
            password=mysql_password,
            database=os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "AI_Maintenance_DB")),
            connection_timeout=5,
        )
        print("\n========== DATABASE AI PREDICTION ==========\n")
        print("Connected to MySQL.")

        package = joblib.load(MODEL_PATH)
        if not isinstance(package, dict) or "model" not in package:
            raise ValueError("The CNC model package has an unexpected format.")
        model = package["model"]
        model_features = package.get("features") or list(
            getattr(model, "feature_names_in_", [])
        )
        if not model_features:
            raise ValueError("The CNC model does not declare its expected input features.")
        print("Random Forest model loaded.")

        machine_name = os.getenv("PREDICTION_MACHINE_NAME", DEFAULT_MACHINE_NAME).strip()
        if not machine_name:
            raise ValueError("PREDICTION_MACHINE_NAME cannot be empty.")

        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                m.machine_name,
                sr.reading_id,
                sr.recorded_at,
                sm.sensor_name,
                sm.sensor_value,
                sm.unit
            FROM MACHINE m
            JOIN SENSOR_READING sr ON sr.machine_id = m.machine_id
            JOIN SENSOR_MEASUREMENT sm ON sm.reading_id = sr.reading_id
            WHERE m.machine_name = %s
              AND sr.reading_id = (
                  SELECT sr2.reading_id
                  FROM SENSOR_READING sr2
                  WHERE sr2.machine_id = m.machine_id
                  ORDER BY sr2.recorded_at DESC, sr2.reading_id DESC
                  LIMIT 1
              )
            ORDER BY sm.sensor_name
            """,
            (machine_name,),
        )
        rows = cursor.fetchall()
        if not rows:
            print(f"No sensor data found for {machine_name}.")
            return 1

        sensor_data = {row["sensor_name"]: row["sensor_value"] for row in rows}
        required = ("Temperature", "RPM", "Torque", "Tool Wear")
        missing = [name for name in required if name not in sensor_data]
        if missing:
            raise ValueError(
                "Latest reading is missing required model inputs: " + ", ".join(missing)
            )

        print("\n---------- SENSOR DATA FROM MYSQL ----------\n")
        for row in rows:
            print(f"{row['sensor_name']:15} : {row['sensor_value']} {row['unit']}")

        model_input = build_cnc_model_input(sensor_data, list(model_features))
        prediction = model.predict(model_input)[0]
        risk = predict_failure_probability(model, model_input) * 100.0

        print("\n---------- AI PREDICTION ----------\n")
        print(f"Machine             : {machine_name}")
        print(f"Air Temperature     : {float(sensor_data['Temperature']) + 273.15:.2f} K")
        print(f"Process Temperature : {float(sensor_data['Temperature']) + 283.15:.2f} K")
        print(f"RPM                 : {float(sensor_data['RPM']):.0f}")
        print(f"Torque              : {float(sensor_data['Torque']):.2f} Nm")
        print(f"Tool Wear           : {float(sensor_data['Tool Wear']):.2f} min")
        print("\nPrediction:")
        label = str(prediction).strip().lower()
        if label in {"1", "true", "failure", "failed", "fail", "yes"}:
            condition = "FAILURE RISK"
        elif label in {"0", "false", "normal", "healthy", "no"}:
            condition = "NORMAL"
        else:
            condition = f"UNRECOGNIZED MODEL LABEL ({prediction})"
        print("Condition            :", condition)
        print(f"Failure Risk         : {risk:.2f}%")
        print("\nMySQL connection closed.")
        print("\n============================================\n")
        return 0
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
