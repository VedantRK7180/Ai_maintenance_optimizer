import os
import glob
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


# ============================================================
# PATHS
# ============================================================

DATA_PATH = os.path.expandvars(
    r"$USERPROFILE\Downloads\robot-predictive-maintenance\training_data\training_data\20240426_140055"
)

MODEL_PATH = "ml/robot_model.joblib"


# ============================================================
# LOAD ALL 6 MOTOR DATASETS
# ============================================================

files = sorted(
    glob.glob(os.path.join(DATA_PATH, "data_motor_*.csv"))
)

if len(files) == 0:
    raise FileNotFoundError("No robot motor CSV files found.")

print("==============================================")
print("ROBOT PREDICTIVE MAINTENANCE MODEL")
print("==============================================")
print(f"Motor files found : {len(files)}")


dataframes = []

for file in files:
    df = pd.read_csv(file)

    # Identify which motor produced the reading
    motor_name = os.path.basename(file).replace(".csv", "")

    df["motor"] = motor_name

    dataframes.append(df)


# Combine all motors
data = pd.concat(dataframes, ignore_index=True)


print(f"Total samples     : {len(data)}")
print(f"Normal samples    : {(data['label'] == 0).sum()}")
print(f"Failure samples   : {(data['label'] == 1).sum()}")


# ============================================================
# FEATURES AND TARGET
# ============================================================

features = [
    "position",
    "temperature",
    "voltage"
]

X = data[features]
y = data["label"]


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print()
print("Training samples  :", len(X_train))
print("Testing samples   :", len(X_test))


# ============================================================
# RANDOM FOREST
# ============================================================

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

print()
print("Training Random Forest...")

model.fit(X_train, y_train)


# ============================================================
# EVALUATION
# ============================================================

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print()
print("==============================================")
print("MODEL RESULTS")
print("==============================================")

print(f"Accuracy : {accuracy * 100:.2f}%")

print()
print("Classification Report:")
print(classification_report(
    y_test,
    y_pred,
    target_names=["NORMAL", "FAILURE"]
))

print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print()
print("Feature Importance:")

for feature, importance in zip(features, model.feature_importances_):
    print(f"{feature:12s} : {importance:.4f}")


# ============================================================
# SAVE MODEL
# ============================================================

package = {
    "model": model,
    "features": features,
    "model_key": "robot",
    "dataset": "Robot Predictive Maintenance",
    "description": "Random Forest failure classifier for robotic arm motors"
}

joblib.dump(package, MODEL_PATH)


print()
print("==============================================")
print("MODEL SAVED")
print("==============================================")
print(f"File : {MODEL_PATH}")
print("==============================================")