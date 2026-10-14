import pandas as pd
import numpy as np
import glob
import os
from pathlib import Path
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


# ============================================================
# 1. LOAD ROBOT DATA
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FOLDER = Path(os.getenv(
    "ROBOT_DATA_FOLDER",
    str(PROJECT_ROOT / "data" / "robot-predictive-maintenance"
        / "training_data" / "training_data" / "20240426_140055")
))
OUTPUT_PATH = PROJECT_ROOT / "ml" / "robot_model_improved.joblib"

files = sorted(glob.glob(str(DATA_FOLDER / "data_motor_*.csv")))

print("=" * 60)
print("AI MAINTENANCE OPTIMIZER")
print("IMPROVED ROBOT PREDICTIVE MAINTENANCE MODEL")
print("=" * 60)

print(f"\nMotor files found : {len(files)}")

if not files:
    raise FileNotFoundError(
        f"No data_motor_*.csv files found in {DATA_FOLDER}. "
        "Set ROBOT_DATA_FOLDER in your environment to the dataset directory."
    )

dataframes = []

for file in files:
    df = pd.read_csv(file)
    df["motor_id"] = os.path.basename(file)
    dataframes.append(df)

data = pd.concat(dataframes, ignore_index=True)

print(f"Total samples     : {len(data)}")


# ============================================================
# 2. SORT DATA BY MOTOR AND TIME
# ============================================================

data = data.sort_values(
    by=["motor_id", "time"]
).reset_index(drop=True)


# ============================================================
# 3. CREATE TIME-SERIES FEATURES
# ============================================================

for column in ["position", "temperature", "voltage"]:

    # Change from previous reading
    data[f"{column}_change"] = (
        data.groupby("motor_id")[column].diff()
    )

    # Rolling average
    data[f"{column}_rolling_mean"] = (
        data.groupby("motor_id")[column]
        .transform(lambda x: x.rolling(window=10, min_periods=1).mean())
    )

    # Rolling standard deviation
    data[f"{column}_rolling_std"] = (
        data.groupby("motor_id")[column]
        .transform(lambda x: x.rolling(window=10, min_periods=1).std())
    )


# Replace NaN values created by diff/std
data = data.fillna(0)


# ============================================================
# 4. SELECT FEATURES
# ============================================================

features = [
    "position",
    "temperature",
    "voltage",

    "position_change",
    "temperature_change",
    "voltage_change",

    "position_rolling_mean",
    "temperature_rolling_mean",
    "voltage_rolling_mean",

    "position_rolling_std",
    "temperature_rolling_std",
    "voltage_rolling_std"
]

X = data[features]
y = data["label"]


# ============================================================
# 5. TRAIN / TEST SPLIT
# ============================================================

# Keep each motor entirely in either train or test to avoid leakage
# from adjacent time-series observations of the same physical motor.
groups = data["motor_id"]
if groups.nunique() < 2:
    raise ValueError(
        "At least two motor CSV files are required for a motor-wise holdout. "
        "A random row split would leak nearby time-series samples."
    )

splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
train_indices, test_indices = next(splitter.split(X, y, groups=groups))
X_train, X_test = X.iloc[train_indices], X.iloc[test_indices]
y_train, y_test = y.iloc[train_indices], y.iloc[test_indices]


print(f"Training samples  : {len(X_train)}")
print(f"Testing samples   : {len(X_test)}")


# ============================================================
# 6. TRAIN RANDOM FOREST
# ============================================================

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    class_weight="balanced",
    n_jobs=-1
)

print("\nTraining improved Random Forest...")

model.fit(X_train, y_train)


# ============================================================
# 7. EVALUATE MODEL
# ============================================================

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\n" + "=" * 60)
print("MODEL PERFORMANCE")
print("=" * 60)

print(f"\nAccuracy : {accuracy * 100:.2f}%")

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        y_pred,
        labels=[0, 1],
        target_names=["NORMAL", "FAILURE"],
        zero_division=0,
    )
)

print("Confusion Matrix:")

print(confusion_matrix(y_test, y_pred, labels=[0, 1]))


# ============================================================
# 8. FEATURE IMPORTANCE
# ============================================================

print("\nFeature Importance:")

importance = pd.Series(
    model.feature_importances_,
    index=features
).sort_values(ascending=False)

for feature, value in importance.items():
    print(f"{feature:25s}: {value:.4f}")


# ============================================================
# 9. SAVE MODEL
# ============================================================

model_package = {
    "model": model,
    "features": features,
    "model_key": "robot",
    "description": "Improved Robot Predictive Maintenance Random Forest"
}

output_path = OUTPUT_PATH

joblib.dump(model_package, output_path)

print("\n" + "=" * 60)
print("MODEL SAVED")
print("=" * 60)

print(f"\nSaved to: {output_path}")

print("\nRobot model training completed successfully.")