import pandas as pd
import numpy as np
import joblib

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


MODEL_FILE = "ml/cmapss_rul_random_forest.joblib"
TEST_FILE = "data/cmapss_fd001_test_rul.csv"
OUTPUT_FILE = "data/cmapss_fd001_rul_predictions.csv"


print("=" * 70)
print("NASA C-MAPSS FD001")
print("RUL PREDICTION ON TEST ENGINES")
print("=" * 70)


# ------------------------------------------------------------
# LOAD MODEL
# ------------------------------------------------------------

print()
print("Loading trained Random Forest model...")

saved_model = joblib.load(MODEL_FILE)

model = saved_model["model"]
feature_columns = saved_model["features"]

print("Model loaded successfully.")

print()
print("Number of model features:", len(feature_columns))


# ------------------------------------------------------------
# LOAD TEST DATA
# ------------------------------------------------------------

print()
print("=" * 70)
print("LOADING TEST DATA")
print("=" * 70)

df = pd.read_csv(TEST_FILE)

print()
print("Test rows:", len(df))
print("Test columns:", len(df.columns))


# ------------------------------------------------------------
# SELECT FINAL OBSERVATION OF EACH ENGINE
# ------------------------------------------------------------

print()
print("=" * 70)
print("SELECTING FINAL OBSERVED CYCLE")
print("=" * 70)

final_rows = (
    df.sort_values(["engine_id", "cycle"])
    .groupby("engine_id")
    .tail(1)
    .copy()
)

final_rows = final_rows.sort_values("engine_id")


print()
print("Number of test engines:", len(final_rows))


# ------------------------------------------------------------
# PREDICT RUL
# ------------------------------------------------------------

print()
print("=" * 70)
print("PREDICTING REMAINING USEFUL LIFE")
print("=" * 70)

X_test = final_rows[feature_columns]

predictions = model.predict(X_test)

predictions = np.maximum(predictions, 0)

final_rows["Predicted_RUL"] = predictions


# ------------------------------------------------------------
# COMPARE WITH OFFICIAL RUL
# ------------------------------------------------------------

if "RUL" in final_rows.columns:

    print()
    print("=" * 70)
    print("TEST PERFORMANCE")
    print("=" * 70)

    actual_rul = final_rows["RUL"]

    mae = mean_absolute_error(
        actual_rul,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual_rul,
            predictions
        )
    )

    r2 = r2_score(
        actual_rul,
        predictions
    )

    print()
    print("Mean Absolute Error (MAE):", round(mae, 2))
    print("Root Mean Squared Error (RMSE):", round(rmse, 2))
    print("R2 Score:", round(r2, 4))


# ------------------------------------------------------------
# CLASSIFY RUL CONDITION
# ------------------------------------------------------------

def classify_rul(rul):

    if rul <= 20:
        return "Critical"

    elif rul <= 50:
        return "Degrading"

    elif rul <= 100:
        return "Monitoring"

    else:
        return "Healthy"


final_rows["Condition"] = (
    final_rows["Predicted_RUL"]
    .apply(classify_rul)
)


# ------------------------------------------------------------
# DISPLAY RESULTS
# ------------------------------------------------------------

print()
print("=" * 70)
print("RUL PREDICTIONS FOR TEST ENGINES")
print("=" * 70)

display_columns = [
    "engine_id",
    "cycle",
    "Predicted_RUL"
]

if "RUL" in final_rows.columns:
    display_columns.append("RUL")

display_columns.append("Condition")

print()

print(
    final_rows[display_columns]
    .round(2)
    .to_string(index=False)
)


# ------------------------------------------------------------
# CONDITION DISTRIBUTION
# ------------------------------------------------------------

print()
print("=" * 70)
print("PREDICTED CONDITION DISTRIBUTION")
print("=" * 70)

print()

print(
    final_rows["Condition"]
    .value_counts()
    .to_string()
)


# ------------------------------------------------------------
# SAVE RESULTS
# ------------------------------------------------------------

output_columns = [
    "engine_id",
    "cycle",
    "Predicted_RUL",
    "Condition"
]

if "RUL" in final_rows.columns:
    output_columns.append("RUL")

final_rows[output_columns].to_csv(
    OUTPUT_FILE,
    index=False
)


print()
print("=" * 70)
print("PREDICTIONS SAVED")
print("=" * 70)

print()
print("Output file:", OUTPUT_FILE)

print()
print("=" * 70)
print("C-MAPSS RUL PREDICTION COMPLETED")
print("=" * 70)