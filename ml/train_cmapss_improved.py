import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


INPUT_FILE = "data/cmapss_fd001_train_rul.csv"
MODEL_FILE = "ml/cmapss_rul_random_forest_improved.joblib"


print("=" * 70)
print("NASA C-MAPSS FD001")
print("IMPROVED RANDOM FOREST RUL MODEL")
print("=" * 70)

print()
print("Loading dataset...")

df = pd.read_csv(INPUT_FILE)

print("Rows:", len(df))
print("Columns:", len(df.columns))


# ------------------------------------------------------------
# SENSOR FEATURES
# ------------------------------------------------------------

sensor_columns = [
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


# ------------------------------------------------------------
# CREATE TEMPORAL FEATURES
# ------------------------------------------------------------

print()
print("=" * 70)
print("CREATING TEMPORAL DEGRADATION FEATURES")
print("=" * 70)

df = df.sort_values(["engine_id", "cycle"]).copy()

feature_columns = [
    "cycle",
    "setting_1",
    "setting_2",
    "setting_3"
]

# Current sensor values
for sensor in sensor_columns:
    feature_columns.append(sensor)

# Rolling and change features
for sensor in sensor_columns:

    # Change from previous cycle
    change_name = sensor + "_change"
    df[change_name] = df.groupby("engine_id")[sensor].diff()

    # Rolling mean over recent 5 cycles
    rolling_mean_name = sensor + "_rolling_mean"
    df[rolling_mean_name] = (
        df.groupby("engine_id")[sensor]
        .transform(lambda x: x.rolling(window=5, min_periods=1).mean())
    )

    # Rolling standard deviation
    rolling_std_name = sensor + "_rolling_std"
    df[rolling_std_name] = (
        df.groupby("engine_id")[sensor]
        .transform(lambda x: x.rolling(window=5, min_periods=1).std())
    )

    feature_columns.append(change_name)
    feature_columns.append(rolling_mean_name)
    feature_columns.append(rolling_std_name)


# Fill values created by first-cycle differences
df[feature_columns] = df[feature_columns].replace(
    [np.inf, -np.inf],
    np.nan
)

df[feature_columns] = df[feature_columns].fillna(0)


print()
print("Original features :", 19)
print("New features      :", len(feature_columns))

print()
print("Temporal features created successfully.")


# ------------------------------------------------------------
# ENGINE-BASED TRAIN / VALIDATION SPLIT
# ------------------------------------------------------------

print()
print("=" * 70)
print("CREATING ENGINE-BASED TRAIN/VALIDATION SPLIT")
print("=" * 70)

engine_ids = sorted(df["engine_id"].unique())

split_index = int(len(engine_ids) * 0.80)

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
print("Training rows      :", len(train_df))
print("Validation rows    :", len(validation_df))


X_train = train_df[feature_columns]
y_train = train_df["RUL"]

X_validation = validation_df[feature_columns]
y_validation = validation_df["RUL"]


# ------------------------------------------------------------
# TRAIN RANDOM FOREST
# ------------------------------------------------------------

print()
print("=" * 70)
print("TRAINING IMPROVED RANDOM FOREST")
print("=" * 70)

model = RandomForestRegressor(
    n_estimators=250,
    max_depth=20,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

print()
print("Improved Random Forest training completed.")


# ------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------

print()
print("=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)

predictions = model.predict(X_validation)

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


# ------------------------------------------------------------
# SAMPLE PREDICTIONS
# ------------------------------------------------------------

results = validation_df[
    ["engine_id", "cycle", "RUL"]
].copy()

results["Predicted_RUL"] = predictions

results["Absolute_Error"] = abs(
    results["RUL"] -
    results["Predicted_RUL"]
)


print()
print("=" * 70)
print("SAMPLE VALIDATION PREDICTIONS")
print("=" * 70)

print(
    results.head(20)
    .round(2)
    .to_string(index=False)
)


# ------------------------------------------------------------
# FEATURE IMPORTANCE
# ------------------------------------------------------------

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
print("TOP 20 FEATURE IMPORTANCES")
print("=" * 70)

print(
    importance.head(20)
    .round(4)
    .to_string(index=False)
)


# ------------------------------------------------------------
# SAVE MODEL
# ------------------------------------------------------------

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

print("Model file:", MODEL_FILE)

print()
print("=" * 70)
print("IMPROVED C-MAPSS MODEL COMPLETED")
print("=" * 70)