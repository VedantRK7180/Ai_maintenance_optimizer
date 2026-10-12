from pymongo import MongoClient
from datetime import datetime


# ============================================================
# MONGODB SETTINGS
# ============================================================

MONGO_URI = "mongodb://localhost:27017/"

DATABASE_NAME = "AI_Maintenance_Mongo"

COLLECTION_NAME = "WHAT_IF_SCENARIOS"


# ============================================================
# CONNECT TO MONGODB
# ============================================================

print("=" * 70)
print("AI MAINTENANCE OPTIMIZER")
print("MONGODB WHAT-IF SCENARIO LOGGER")
print("=" * 70)

print()
print("Connecting to MongoDB...")


client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)


# Test connection
client.admin.command("ping")


db = client[DATABASE_NAME]

collection = db[COLLECTION_NAME]


print("MongoDB connected successfully.")

print(
    "Database   :",
    DATABASE_NAME
)

print(
    "Collection :",
    COLLECTION_NAME
)


# ============================================================
# ENTER SCENARIO INFORMATION
# ============================================================

print()
print("=" * 70)
print("ENTER WHAT-IF SCENARIO")
print("=" * 70)


machine_name = input(
    "\nMachine name: "
).strip()


changed_sensor = input(
    "Changed sensor: "
).strip()


current_temperature = float(
    input("Current temperature (C): ")
)


scenario_temperature = float(
    input("Scenario temperature (C): ")
)


current_rpm = float(
    input("Current RPM: ")
)


scenario_rpm = float(
    input("Scenario RPM: ")
)


current_torque = float(
    input("Current Torque (Nm): ")
)


scenario_torque = float(
    input("Scenario Torque (Nm): ")
)


current_tool_wear = float(
    input("Current Tool Wear (min): ")
)


scenario_tool_wear = float(
    input("Scenario Tool Wear (min): ")
)


# ============================================================
# AI RESULTS
# ============================================================

print()
print("=" * 70)
print("ENTER AI RESULTS")
print("=" * 70)


current_risk = float(
    input("Current Failure Risk (%): ")
)


scenario_risk = float(
    input("Scenario Failure Risk (%): ")
)


current_health = float(
    input("Current Health (%): ")
)


scenario_health = float(
    input("Scenario Health (%): ")
)


current_urgency = float(
    input("Current Urgency Score: ")
)


scenario_urgency = float(
    input("Scenario Urgency Score: ")
)


current_urgency_level = input(
    "Current Urgency Level: "
).strip()


scenario_urgency_level = input(
    "Scenario Urgency Level: "
).strip()


# ============================================================
# CALCULATE CHANGES
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
    scenario_urgency -
    current_urgency
)


# ============================================================
# CREATE MONGODB DOCUMENT
# ============================================================

scenario_document = {

    "machine": {

        "machine_name": machine_name

    },

    "scenario": {

        "changed_sensor": changed_sensor,

        "current": {

            "temperature_C": current_temperature,

            "rpm": current_rpm,

            "torque_Nm": current_torque,

            "tool_wear_min": current_tool_wear

        },

        "what_if": {

            "temperature_C": scenario_temperature,

            "rpm": scenario_rpm,

            "torque_Nm": scenario_torque,

            "tool_wear_min": scenario_tool_wear

        }

    },

    "ai_results": {

        "current": {

            "failure_risk": current_risk,

            "health_score": current_health,

            "urgency_score": current_urgency,

            "urgency_level": current_urgency_level

        },

        "what_if": {

            "failure_risk": scenario_risk,

            "health_score": scenario_health,

            "urgency_score": scenario_urgency,

            "urgency_level": scenario_urgency_level

        },

        "change": {

            "risk_change": risk_change,

            "health_change": health_change,

            "urgency_change": urgency_change

        }

    },

    "event_type": "what_if_simulation",

    "created_at": datetime.now()

}


# ============================================================
# INSERT DOCUMENT
# ============================================================

result = collection.insert_one(
    scenario_document
)


# ============================================================
# DISPLAY RESULT
# ============================================================

print()
print("=" * 70)
print("WHAT-IF SCENARIO SAVED")
print("=" * 70)

print()

print(
    "MongoDB Document ID:",
    result.inserted_id
)

print(
    "Machine:",
    machine_name
)

print(
    "Changed Sensor:",
    changed_sensor
)

print(
    "Risk Change:",
    round(risk_change, 2),
    "percentage points"
)

print(
    "Health Change:",
    round(health_change, 2),
    "percentage points"
)

print(
    "Urgency Change:",
    round(urgency_change, 2)
)


print()
print(
    "Total What-If scenarios:",
    collection.count_documents({})
)


# ============================================================
# CLOSE CONNECTION
# ============================================================

client.close()


print()
print("MongoDB connection closed.")

print()
print("=" * 70)
print("MONGODB LOGGING COMPLETED")
print("=" * 70)