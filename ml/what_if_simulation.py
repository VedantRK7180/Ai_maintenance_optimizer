import mysql.connector
import joblib
import pandas as pd

from pymongo import MongoClient

from fuzzy_logic import calculate_urgency


# ============================================================
# SETTINGS
# ============================================================

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "#123Vrk7"
MYSQL_DATABASE = "AI_Maintenance_DB"

MODEL_FILE = "ml/cnc_model_baseline.joblib"

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DATABASE = "AI_Maintenance_Mongo"
MONGO_COLLECTION = "WHAT_IF_SCENARIOS"


# ============================================================
# LOAD AI MODEL
# ============================================================

print("=" * 70)
print("AI MAINTENANCE OPTIMIZER")
print("WHAT-IF SIMULATION")
print("=" * 70)

print()
print("Loading AI model...")

model_data = joblib.load(MODEL_FILE)

if not isinstance(model_data, dict):

    print("ERROR: Model file format is unexpected.")

    exit()


print("Model file contains a dictionary.")

print(
    "Available keys:",
    list(model_data.keys())
)


if "model" not in model_data:

    print()
    print("ERROR: Trained model not found.")

    exit()


model = model_data["model"]

saved_features = model_data.get(
    "features",
    None
)


print("AI model loaded successfully.")

print(
    "Model type:",
    type(model).__name__
)

print(
    "Saved features:",
    saved_features
)


# ============================================================
# CONNECT TO MYSQL
# ============================================================

print()
print("Connecting to MySQL...")

connection = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)

print("MySQL connected successfully.")


# ============================================================
# CONNECT TO MONGODB
# ============================================================

print()
print("Connecting to MongoDB...")

mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

mongo_client.admin.command("ping")

mongo_db = mongo_client[MONGO_DATABASE]

mongo_collection = mongo_db[MONGO_COLLECTION]

print("MongoDB connected successfully.")

print(
    "MongoDB collection:",
    MONGO_COLLECTION
)


# ============================================================
# SELECT MACHINE
# ============================================================

machine_name = input(
    "\nEnter CNC machine name (example: CNC-102): "
).strip()


# ============================================================
# GET MACHINE INFORMATION
# ============================================================

cursor = connection.cursor(dictionary=True)

query = """
SELECT
    machine_id,
    machine_name,
    operating_hours,
    criticality,
    production_importance
FROM MACHINE
WHERE machine_name = %s;
"""

cursor.execute(
    query,
    (machine_name,)
)

machine = cursor.fetchone()

cursor.close()


if machine is None:

    print()
    print("Machine not found.")

    connection.close()
    mongo_client.close()

    exit()


# ============================================================
# GET LATEST SENSOR READING
# ============================================================

cursor = connection.cursor(dictionary=True)

query = """
SELECT
    sr.reading_id,
    sr.recorded_at,
    sm.sensor_name,
    sm.sensor_value,
    sm.unit
FROM SENSOR_READING sr
JOIN SENSOR_MEASUREMENT sm
    ON sr.reading_id = sm.reading_id
WHERE sr.machine_id = %s
AND sr.recorded_at = (
    SELECT MAX(recorded_at)
    FROM SENSOR_READING
    WHERE machine_id = %s
)
ORDER BY sm.sensor_name;
"""

cursor.execute(
    query,
    (
        machine["machine_id"],
        machine["machine_id"]
    )
)

rows = cursor.fetchall()

cursor.close()


if not rows:

    print()
    print("No sensor data found for this machine.")

    connection.close()
    mongo_client.close()

    exit()


# ============================================================
# CONVERT SENSOR DATA
# ============================================================

sensor_data = {}

for row in rows:

    sensor_data[row["sensor_name"]] = float(
        row["sensor_value"]
    )


required_sensors = [
    "Temperature",
    "RPM",
    "Torque",
    "Tool Wear"
]


for sensor in required_sensors:

    if sensor not in sensor_data:

        print()
        print(
            "Missing sensor:",
            sensor
        )

        connection.close()
        mongo_client.close()

        exit()


# ============================================================
# CURRENT SENSOR VALUES
# ============================================================

temperature = sensor_data["Temperature"]

rpm = sensor_data["RPM"]

torque = sensor_data["Torque"]

tool_wear = sensor_data["Tool Wear"]


# ============================================================
# MODEL INPUT FUNCTION
# ============================================================

def create_model_input(
    temperature_value,
    rpm_value,
    torque_value,
    tool_wear_value
):

    air_temperature_k = (
        temperature_value + 273.15
    )

    process_temperature_k = (
        air_temperature_k + 10
    )

    raw_data = pd.DataFrame([
        {
            "Type": "M",

            "Air temperature [K]":
                air_temperature_k,

            "Process temperature [K]":
                process_temperature_k,

            "Rotational speed [rpm]":
                rpm_value,

            "Torque [Nm]":
                torque_value,

            "Tool wear [min]":
                tool_wear_value
        }
    ])


    # ========================================================
    # ONE-HOT ENCODE TYPE
    # ========================================================

    raw_data = pd.get_dummies(
        raw_data,
        columns=["Type"],
        dtype=int
    )


    # ========================================================
    # MATCH TRAINING FEATURES
    # ========================================================

    if saved_features is not None:

        for feature in saved_features:

            if feature not in raw_data.columns:

                raw_data[feature] = 0


        raw_data = raw_data[
            [
                feature
                for feature in saved_features
            ]
        ]


    return raw_data


# ============================================================
# CURRENT AI PREDICTION
# ============================================================

current_input = create_model_input(
    temperature,
    rpm,
    torque,
    tool_wear
)


print()
print("Model input prepared successfully.")

print()
print("Model input columns:")

print(
    list(current_input.columns)
)


current_prediction = model.predict_proba(
    current_input
)[0][1]


current_risk = current_prediction * 100

current_health = 100 - current_risk


current_urgency_score, current_urgency_level = calculate_urgency(
    current_risk,
    machine["operating_hours"],
    machine["criticality"]
)


# ============================================================
# DISPLAY CURRENT STATE
# ============================================================

print()
print("=" * 70)
print("CURRENT MACHINE STATE")
print("=" * 70)

print()

print(
    "Machine           :",
    machine["machine_name"]
)

print(
    "Temperature       :",
    temperature,
    "C"
)

print(
    "RPM               :",
    rpm
)

print(
    "Torque            :",
    torque,
    "Nm"
)

print(
    "Tool Wear         :",
    tool_wear,
    "min"
)

print(
    "Operating Hours   :",
    machine["operating_hours"]
)

print(
    "Criticality       :",
    machine["criticality"]
)

print()

print(
    "Current Failure Risk :",
    round(current_risk, 2),
    "%"
)

print(
    "Current Health       :",
    round(current_health, 2),
    "%"
)

print(
    "Current Urgency      :",
    round(current_urgency_score, 2)
)

print(
    "Current Urgency Level:",
    current_urgency_level
)


# ============================================================
# WHAT-IF INPUT
# ============================================================

print()
print("=" * 70)
print("WHAT-IF SCENARIO")
print("=" * 70)

print()

print(
    "Change one sensor value and see how the AI prediction changes."
)

print()

print("Available sensors:")

print("1. Temperature")

print("2. RPM")

print("3. Torque")

print("4. Tool Wear")


choice = input(
    "\nEnter sensor number (1-4): "
).strip()


# ============================================================
# TEMPERATURE
# ============================================================

if choice == "1":

    new_temperature = float(
        input(
            "Enter new Temperature (C): "
        )
    )

    scenario_temperature = new_temperature

    scenario_rpm = rpm

    scenario_torque = torque

    scenario_tool_wear = tool_wear

    changed_sensor = "Temperature"


# ============================================================
# RPM
# ============================================================

elif choice == "2":

    new_rpm = float(
        input(
            "Enter new RPM: "
        )
    )

    scenario_temperature = temperature

    scenario_rpm = new_rpm

    scenario_torque = torque

    scenario_tool_wear = tool_wear

    changed_sensor = "RPM"


# ============================================================
# TORQUE
# ============================================================

elif choice == "3":

    new_torque = float(
        input(
            "Enter new Torque (Nm): "
        )
    )

    scenario_temperature = temperature

    scenario_rpm = rpm

    scenario_torque = new_torque

    scenario_tool_wear = tool_wear

    changed_sensor = "Torque"


# ============================================================
# TOOL WEAR
# ============================================================

elif choice == "4":

    new_tool_wear = float(
        input(
            "Enter new Tool Wear (min): "
        )
    )

    scenario_temperature = temperature

    scenario_rpm = rpm

    scenario_torque = torque

    scenario_tool_wear = new_tool_wear

    changed_sensor = "Tool Wear"


# ============================================================
# INVALID INPUT
# ============================================================

else:

    print()

    print("Invalid sensor selection.")

    connection.close()
    mongo_client.close()

    exit()


# ============================================================
# WHAT-IF AI PREDICTION
# ============================================================

scenario_input = create_model_input(
    scenario_temperature,
    scenario_rpm,
    scenario_torque,
    scenario_tool_wear
)


scenario_prediction = model.predict_proba(
    scenario_input
)[0][1]


scenario_risk = scenario_prediction * 100

scenario_health = 100 - scenario_risk


scenario_urgency_score, scenario_urgency_level = calculate_urgency(
    scenario_risk,
    machine["operating_hours"],
    machine["criticality"]
)


# ============================================================
# COMPARE RESULTS
# ============================================================

risk_change = (
    scenario_risk -
    current_risk
)

health_change = (
    scenario_health -
    current_health
)

urgency_change = (
    scenario_urgency_score -
    current_urgency_score
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("=" * 70)

print("WHAT-IF SIMULATION RESULT")

print("=" * 70)

print()

print(
    "Machine:",
    machine["machine_name"]
)

print(
    "Changed sensor:",
    changed_sensor
)


# ============================================================
# CURRENT
# ============================================================

print()

print(
    "---------------- CURRENT ----------------"
)

print(
    "Temperature      :",
    round(temperature, 2),
    "C"
)

print(
    "RPM              :",
    round(rpm, 2)
)

print(
    "Torque           :",
    round(torque, 2),
    "Nm"
)

print(
    "Tool Wear        :",
    round(tool_wear, 2),
    "min"
)

print(
    "Failure Risk     :",
    round(current_risk, 2),
    "%"
)

print(
    "Health Score     :",
    round(current_health, 2),
    "%"
)

print(
    "Urgency Score    :",
    round(current_urgency_score, 2)
)

print(
    "Urgency Level    :",
    current_urgency_level
)


# ============================================================
# WHAT-IF
# ============================================================

print()

print(
    "---------------- WHAT-IF ----------------"
)

print(
    "Temperature      :",
    round(scenario_temperature, 2),
    "C"
)

print(
    "RPM              :",
    round(scenario_rpm, 2)
)

print(
    "Torque           :",
    round(scenario_torque, 2),
    "Nm"
)

print(
    "Tool Wear        :",
    round(scenario_tool_wear, 2),
    "min"
)

print(
    "Failure Risk     :",
    round(scenario_risk, 2),
    "%"
)

print(
    "Health Score     :",
    round(scenario_health, 2),
    "%"
)

print(
    "Urgency Score    :",
    round(scenario_urgency_score, 2)
)

print(
    "Urgency Level    :",
    scenario_urgency_level
)


# ============================================================
# CHANGE
# ============================================================

print()

print(
    "---------------- CHANGE ----------------"
)

print(
    "Risk Change      :",
    round(risk_change, 2),
    "percentage points"
)

print(
    "Health Change    :",
    round(health_change, 2),
    "percentage points"
)

print(
    "Urgency Change   :",
    round(urgency_change, 2)
)


# ============================================================
# AI RECOMMENDATION
# ============================================================

print()

print("=" * 70)

print("AI RECOMMENDATION")

print("=" * 70)


if scenario_risk >= 60:

    recommendation = (
        "High risk detected. "
        "Schedule maintenance immediately."
    )

elif scenario_risk >= 40:

    recommendation = (
        "Moderate risk detected. "
        "Schedule maintenance soon."
    )

else:

    recommendation = (
        "Risk is currently low. "
        "Continue monitoring the machine."
    )


print()

print(recommendation)


# ============================================================
# SAVE WHAT-IF SCENARIO TO MONGODB
# ============================================================

print()

print("=" * 70)

print("SAVING WHAT-IF SCENARIO TO MONGODB")

print("=" * 70)


scenario_document = {

    "machine": {

        "machine_id":
            machine["machine_id"],

        "machine_name":
            machine["machine_name"],

        "operating_hours":
            float(machine["operating_hours"]),

        "criticality":
            machine["criticality"],

        "production_importance":
            machine["production_importance"]

    },

    "scenario": {

        "changed_sensor":
            changed_sensor,

        "current": {

            "temperature_C":
                temperature,

            "rpm":
                rpm,

            "torque_Nm":
                torque,

            "tool_wear_min":
                tool_wear

        },

        "what_if": {

            "temperature_C":
                scenario_temperature,

            "rpm":
                scenario_rpm,

            "torque_Nm":
                scenario_torque,

            "tool_wear_min":
                scenario_tool_wear

        }

    },

    "ai_results": {

        "current": {

            "failure_risk":
                current_risk,

            "health_score":
                current_health,

            "urgency_score":
                current_urgency_score,

            "urgency_level":
                current_urgency_level

        },

        "what_if": {

            "failure_risk":
                scenario_risk,

            "health_score":
                scenario_health,

            "urgency_score":
                scenario_urgency_score,

            "urgency_level":
                scenario_urgency_level

        },

        "change": {

            "risk_change":
                risk_change,

            "health_change":
                health_change,

            "urgency_change":
                urgency_change

        }

    },

    "recommendation":
        recommendation,

    "event_type":
        "what_if_simulation",

    "model":
        "AI4I-RandomForest",

    "created_at":
        __import__("datetime").datetime.now()

}


result = mongo_collection.insert_one(
    scenario_document
)


print()

print(
    "What-If scenario saved successfully."
)

print(
    "MongoDB Document ID:",
    result.inserted_id
)


# ============================================================
# CLOSE CONNECTIONS
# ============================================================

connection.close()

mongo_client.close()


print()

print("MySQL connection closed.")

print("MongoDB connection closed.")

print()

print("=" * 70)

print("WHAT-IF SIMULATION COMPLETED")

print("=" * 70)