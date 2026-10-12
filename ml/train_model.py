import pandas as pd
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "ai4i_model_data.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "cnc_model_baseline.joblib"
)

# ============================================================
# 2. LOAD DATA
# ============================================================

df = pd.read_csv(DATA_PATH)

print("\n========== RANDOM FOREST TRAINING ==========\n")

print("Dataset shape:")
print(df.shape)

# ============================================================
# 3. DEFINE FEATURES AND TARGET
# ============================================================

features = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]"
]

target = "Machine failure"

X = df[features].copy()
y = df[target].copy()

# ============================================================
# 4. CONVERT MACHINE TYPE INTO NUMERIC VALUES
# ============================================================

# AI4I uses M, L and H for product type.
# Machine learning algorithms need numerical input.

X = pd.get_dummies(
    X,
    columns=["Type"],
    dtype=int
)

print("\nFeatures after encoding:")
print(X.columns.tolist())

# ============================================================
# 5. TRAIN-TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))

# ============================================================
# 6. CREATE RANDOM FOREST MODEL
# ============================================================

model = RandomForestClassifier(
    n_estimators=200,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

# ============================================================
# 7. TRAIN MODEL
# ============================================================

print("\nTraining Random Forest...")

model.fit(X_train, y_train)

print("Training completed.")

# ============================================================
# 8. PREDICT TEST DATA
# ============================================================

y_pred = model.predict(X_test)

# ============================================================
# 9. MODEL EVALUATION
# ============================================================

accuracy = accuracy_score(y_test, y_pred)

print("\n========== MODEL RESULTS ==========\n")

print("Accuracy:")
print(f"{accuracy:.4f}")

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# ============================================================
# 10. SAVE MODEL
# ============================================================

# Save both the model and the exact feature order.
model_package = {
    "model": model,
    "features": X.columns.tolist()
}

joblib.dump(model_package, MODEL_PATH)

print("\nModel saved to:")
print(MODEL_PATH)

print("\n====================================\n")