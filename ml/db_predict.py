import os
from pathlib import Path
import mysql.connector
import joblib
import pandas as pd

from model_utils import predict_failure_probability
from dotenv import load_dotenv
from model_utils import predict_failure_probability

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# ============================================================
# 1. PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "cnc_model_baseline.joblib"
)


# ============================================================
# 2. MYSQL CONNECTION
# ============================================================

mysql_password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD"))
if not mysql_password:
    raise RuntimeError("MYSQL_PASSWORD is missing. Add your existing MySQL password to the local .env file.")

connection = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost")),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", os.getenv("DB_USER", "root")),
    password=mysql_password,
    database=os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "AI_Maintenance_DB"))
)

print("\n========== DATABASE AI PREDICTION ==========\n")
print("Connected to MySQL.")


# ============================================================
# 3. LOAD TRAINED RANDOM FOREST MODEL
# ============================================================

model_package = joblib.load(MODEL_PATH)

model = model_package["model"]
model_features = model_package["features"]

print("Random Forest model loaded.")


# ============================================================
# 4. GET LATEST SENSOR READING FOR CNC-102
# ============================================================

query = """
SELECT
    m.machine_name,
    sr.reading_id,
    sr.recorded_at,
    sm.sensor_name,
    sm.sensor_value,
    sm.unit

FROM MACHINE m

JOIN SENSOR_READING sr
    ON m.machine_id = sr.machine_id

JOIN SENSOR_MEASUREMENT sm
    ON sr.reading_id = sm.reading_id

WHERE m.machine_name = 'CNC-102'

AND sr.reading_id = (
    SELECT MAX(sr2.reading_id)
    FROM SENSOR_READING sr2
    WHERE sr2.machine_id = m.machine_id
)

ORDER BY sm.sensor_name;
"""


cursor = connection.cursor(dictionary=True)

cursor.execute(query)

rows = cursor.fetchall()


# ============================================================
# 5. DISPLAY SENSOR DATA
# ============================================================

print("\n---------- SENSOR DATA FROM MYSQL ----------\n")

if not rows:
    print("No sensor data found.")
    cursor.close()
    connection.close()
    exit()

for row in rows:
    print(
        f"{row['sensor_name']:15} : "
        f"{row['sensor_value']} {row['unit']}"
    )


# ============================================================
# 6. CONVERT SENSOR DATA INTO MODEL INPUT
# ============================================================

sensor_data = {}

for row in rows:
    sensor_data[row["sensor_name"]] = float(row["sensor_value"])


# ============================================================
# 7. PREPARE VALUES FOR AI4I MODEL
# ============================================================

# Database stores temperature in Celsius.
# AI4I model expects Kelvin.

air_temperature = sensor_data["Temperature"] + 273.15

# AI4I requires process temperature.
# For this prototype we use air temperature + 10 K.

process_temperature = air_temperature + 10.0

rotational_speed = sensor_data["RPM"]

torque = sensor_data["Torque"]

tool_wear = sensor_data["Tool Wear"]


# ============================================================
# 8. CREATE MODEL INPUT
# ============================================================

input_data = pd.DataFrame([{
    "Type": "M",
    "Air temperature [K]": air_temperature,
    "Process temperature [K]": process_temperature,
    "Rotational speed [rpm]": rotational_speed,
    "Torque [Nm]": torque,
    "Tool wear [min]": tool_wear
}])


# ============================================================
# 9. ONE-HOT ENCODE MACHINE TYPE
# ============================================================

input_data = pd.get_dummies(
    input_data,
    columns=["Type"],
    dtype=int
)


# ============================================================
# 10. MATCH TRAINING FEATURES
# ============================================================

for column in model_features:

    if column not in input_data.columns:
        input_data[column] = 0


input_data = input_data[model_features]


# ============================================================
# 11. RUN RANDOM FOREST PREDICTION
# ============================================================

prediction = model.predict(input_data)[0]

failure_risk = predict_failure_probability(model, input_data) * 100


# ============================================================
# 12. DETERMINE CONDITION
# ============================================================

if prediction == 1:
    condition = "FAILURE RISK"
else:
    condition = "NORMAL"


# ============================================================
# 13. DISPLAY AI RESULT
# ============================================================

print("\n---------- AI PREDICTION ----------\n")

print("Machine             : CNC-102")
print(f"Air Temperature     : {air_temperature:.2f} K")
print(f"Process Temperature : {process_temperature:.2f} K")
print(f"RPM                 : {rotational_speed:.0f}")
print(f"Torque              : {torque:.2f} Nm")
print(f"Tool Wear           : {tool_wear:.2f} min")

print("\nPrediction:")
print("Condition            :", condition)
print(f"Failure Risk         : {failure_risk:.2f}%")


# ============================================================
# 14. CLOSE DATABASE CONNECTION
# ============================================================

cursor.close()
connection.close()

print("\nMySQL connection closed.")

print("\n============================================\n")

