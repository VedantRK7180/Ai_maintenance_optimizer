import os
import joblib
import pandas as pd
from model_utils import predict_failure_probability

from ml.model_utils import predict_failure_probability

# ============================================================
# 1. FIND THE TRAINED MODEL
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "cnc_model_baseline.joblib"
)

# ============================================================
# 2. LOAD THE TRAINED MODEL
# ============================================================

model_package = joblib.load(MODEL_PATH)

model = model_package["model"]
model_features = model_package["features"]

# ============================================================
# 3. PREDICTION FUNCTION
# ============================================================

def predict_machine(
    machine_type,
    air_temperature,
    process_temperature,
    rotational_speed,
    torque,
    tool_wear
):

    # Create a DataFrame containing the new machine reading
    input_data = pd.DataFrame([{
        "Type": machine_type,
        "Air temperature [K]": air_temperature,
        "Process temperature [K]": process_temperature,
        "Rotational speed [rpm]": rotational_speed,
        "Torque [Nm]": torque,
        "Tool wear [min]": tool_wear
    }])

    # Convert Type (M/L/H) into numerical columns
    input_data = pd.get_dummies(
        input_data,
        columns=["Type"],
        dtype=int
    )

    # Make sure all model features exist
    for column in model_features:
        if column not in input_data.columns:
            input_data[column] = 0

    # Keep the exact same feature order used during training
    input_data = input_data[model_features]

    # Predict machine class
    prediction = model.predict(input_data)[0]

    # Predict probability
    failure_probability = predict_failure_probability(model, input_data)

    # Convert probability to percentage
    failure_risk = failure_probability * 100

    # Determine machine condition
    if prediction == 1:
        condition = "FAILURE RISK"
    else:
        condition = "NORMAL"

    return condition, failure_risk


# ============================================================
# 4. TEST 1 — NORMAL MACHINE
# ============================================================

print("\n========== MACHINE PREDICTION TEST ==========\n")

normal_condition, normal_risk = predict_machine(
    machine_type="M",
    air_temperature=300.0,
    process_temperature=310.0,
    rotational_speed=1500,
    torque=50.0,
    tool_wear=100.0
)

print("TEST 1: NORMAL OPERATING CONDITION")
print("------------------------------------")
print("Machine Type        : M")
print("Air Temperature     : 300 K")
print("Process Temperature : 310 K")
print("Rotational Speed    : 1500 rpm")
print("Torque              : 50 Nm")
print("Tool Wear           : 100 min")

print("\nPrediction:")
print("Condition            :", normal_condition)
print(f"Failure Risk         : {normal_risk:.2f}%")


# ============================================================
# 5. TEST 2 — STRESSED MACHINE
# ============================================================

stressed_condition, stressed_risk = predict_machine(
    machine_type="L",
    air_temperature=305.0,
    process_temperature=315.0,
    rotational_speed=1400,
    torque=70.0,
    tool_wear=200.0
)

print("\n\nTEST 2: STRESSED OPERATING CONDITION")
print("-------------------------------------")
print("Machine Type        : L")
print("Air Temperature     : 305 K")
print("Process Temperature : 315 K")
print("Rotational Speed    : 1400 rpm")
print("Torque              : 70 Nm")
print("Tool Wear           : 200 min")

print("\nPrediction:")
print("Condition            :", stressed_condition)
print(f"Failure Risk         : {stressed_risk:.2f}%")


# ============================================================
# 6. COMPARISON
# ============================================================

print("\n\n========== COMPARISON ==========\n")

print(f"Normal machine risk   : {normal_risk:.2f}%")
print(f"Stressed machine risk : {stressed_risk:.2f}%")

print("\n================================\n")