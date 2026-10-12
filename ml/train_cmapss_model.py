import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# NASA C-MAPSS FD001
# RANDOM FOREST RUL MODEL
# ============================================================

TRAIN_FILE = "data/cmapss_fd001_train_rul.csv"
MODEL_FILE = "ml/cmapss_rul_random_forest.joblib"


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("NASA C-MAPSS FD001")
print("RANDOM FOREST RUL MODEL TRAINING")
print("=" * 70)

print()
print("Loading training dataset...")

df = pd.read_csv(TRAIN_FILE)

print("Rows:", len(df))
print("Columns:", len(df.columns))


# ============================================================
# FEATURES
# ============================================================

feature_columns = [
    "cycle",
    "setting_1",
    "setting_2",
    "setting_3",
    "sensor_2",
    "sensor_3",
    "sensor_4",
    "sensor_6",
    "sensor_7",
    "sensor_8",
    "sensor_9",
    "sensor_11",
    "sensor_12",
    "sensor_13",
    "sensor_14",
    "sensor_15",
    "sensor_17",
    "sensor_20",
    "sensor_21"
]

target_column = "RUL"


# ============================================================
# IMPORTANT:
# SPLIT BY ENGINE, NOT RANDOM ROWS
# ============================================================

print()
print("=" * 70)
print("CREATING ENGINE-BASED TRAIN/VALIDATION SPLIT")
print("=" * 70)

engine_ids = sorted(
    df["engine_id"].unique()
)

# Use the first 80 engines for training
# and the last 20 engines for validation.

split_index = int(
    len(engine_ids) * 0.80
)

train_engine_ids = engine_ids[:split_index]
validation_engine_ids = engine_ids[split_index:]


train_df = df[
    df["engine_id"].isin(train_engine_ids)
].copy()

validation_df = df[
    df["engine_id"].isin(validation_engine_ids)
].copy()


print()
print("Training engines   :", len(train_engine_ids))
print("Validation engines :", len(validation_engine_ids))

print(
    "Training rows      :",
    len(train_df)
)

print(
    "Validation rows    :",
    len(validation_df)
)


# ============================================================
# PREPARE X AND Y
# ============================================================

X_train = train_df[feature_columns]
y_train = train_df[target_column]

X_validation = validation_df[feature_columns]
y_validation = validation_df[target_column]


# ============================================================
# TRAIN RANDOM FOREST
# ============================================================

print()
print("=" * 70)
print("TRAINING RANDOM FOREST REGRESSOR")
print("=" * 70)

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=18,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)


print()
print("Random Forest training completed.")


# ============================================================
# VALIDATION PREDICTION
# ============================================================

print()
print("=" * 70)
print("VALIDATION")
print("=" * 70)

predictions = model.predict(
    X_validation
)


# ============================================================
# METRICS
# ============================================================

mae = mean_absolute_error(
    y_validation,
    predictions
)

rmse = np.sqrt(
    mean_squared_error(
        y_validation,
        predictions
    )
)

r2 = r2_score(
    y_validation,
    predictions
)


print()
print("Mean Absolute Error (MAE):", round(mae, 2))
print("Root Mean Squared Error (RMSE):", round(rmse, 2))
print("R2 Score:", round(r2, 4))


# ============================================================
# SAMPLE PREDICTIONS
# ============================================================

results = validation_df[
    [
        "engine_id",
        "cycle",
        "RUL"
    ]
].copy()

results["Predicted_RUL"] = predictions

results["Absolute_Error"] = (
    abs(
        results["RUL"]
        -
        results["Predicted_RUL"]
    )
)


print()
print("=" * 70)
print("SAMPLE VALIDATION PREDICTIONS")
print("=" * 70)

print(
    results
    .head(20)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

importance = pd.DataFrame({
    "feature": feature_columns,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)


print()
print("=" * 70)
print("TOP 10 FEATURE IMPORTANCES")
print("=" * 70)

print(
    importance
    .head(10)
    .round(4)
    .to_string(index=False)
)


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    {
        "model": model,
        "features": feature_columns
    },
    MODEL_FILE
)


print()
print("=" * 70)
print("MODEL SAVED")
print("=" * 70)

print(
    "Model file:",
    MODEL_FILE
)

print()
print("=" * 70)
print("C-MAPSS RUL MODEL TRAINING COMPLETED")
print("=" * 70)