import joblib
import pandas as pd

MODEL_PATH = "ml/robot_model.joblib"

DATA_PATH = (
    r"C:\Users\Vedant\Downloads\robot-predictive-maintenance"
    r"\training_data\training_data\20240426_140055\data_motor_1.csv"
)

# Load model
package = joblib.load(MODEL_PATH)

model = package["model"]

# Load real dataset
df = pd.read_csv(DATA_PATH)

features = [
    "position",
    "temperature",
    "voltage"
]


def predict_robot(row):

    data = pd.DataFrame([{
        "position": row["position"],
        "temperature": row["temperature"],
        "voltage": row["voltage"]
    }])

    probability = model.predict_proba(data)[0]

    failure_risk = probability[1] * 100

    prediction = model.predict(data)[0]

    condition = "FAILURE RISK" if prediction == 1 else "NORMAL"

    return condition, failure_risk


print("==============================================")
print("ROBOT MODEL REAL-DATA VALIDATION")
print("==============================================")


# ------------------------------------------------
# REAL NORMAL SAMPLE
# ------------------------------------------------

normal_sample = df[df["label"] == 0].iloc[0]

condition, risk = predict_robot(normal_sample)

print()
print("TEST 1: REAL NORMAL SAMPLE")
print("--------------------------------")

print(f"Position     : {normal_sample['position']}")
print(f"Temperature  : {normal_sample['temperature']}")
print(f"Voltage      : {normal_sample['voltage']}")
print(f"Actual Label : {normal_sample['label']}")

print()
print("Model Prediction:")
print(f"Condition    : {condition}")
print(f"Failure Risk : {risk:.2f}%")


# ------------------------------------------------
# REAL FAILURE SAMPLE
# ------------------------------------------------

failure_sample = df[df["label"] == 1].iloc[0]

condition, risk = predict_robot(failure_sample)

print()
print("TEST 2: REAL FAILURE SAMPLE")
print("--------------------------------")

print(f"Position     : {failure_sample['position']}")
print(f"Temperature  : {failure_sample['temperature']}")
print(f"Voltage      : {failure_sample['voltage']}")
print(f"Actual Label : {failure_sample['label']}")

print()
print("Model Prediction:")
print(f"Condition    : {condition}")
print(f"Failure Risk : {risk:.2f}%")


print()
print("==============================================")