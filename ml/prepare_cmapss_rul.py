import pandas as pd
import numpy as np


# ============================================================
# NASA C-MAPSS FD001
# RUL DATASET PREPARATION
# ============================================================

TRAIN_FILE = "data/NASA_CMAPSS/train_FD001.txt"
TEST_FILE = "data/NASA_CMAPSS/test_FD001.txt"
RUL_FILE = "data/NASA_CMAPSS/RUL_FD001.txt"

TRAIN_OUTPUT = "data/cmapss_fd001_train_rul.csv"
TEST_OUTPUT = "data/cmapss_fd001_test_rul.csv"


# ============================================================
# COLUMN NAMES
# ============================================================

columns = [
    "engine_id",
    "cycle",
    "setting_1",
    "setting_2",
    "setting_3",
]

for i in range(1, 22):
    columns.append(f"sensor_{i}")


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("NASA C-MAPSS FD001 RUL DATA PREPARATION")
print("=" * 70)

print()
print("Loading training data...")

train = pd.read_csv(
    TRAIN_FILE,
    sep=r"\s+",
    header=None
)

print("Loading test data...")

test = pd.read_csv(
    TEST_FILE,
    sep=r"\s+",
    header=None
)

print("Loading official test RUL values...")

rul = pd.read_csv(
    RUL_FILE,
    sep=r"\s+",
    header=None
)


train.columns = columns
test.columns = columns


# ============================================================
# TRAINING RUL
# ============================================================

print()
print("=" * 70)
print("CREATING TRAINING RUL TARGET")
print("=" * 70)

# Find the final cycle of every training engine.

max_cycle_per_engine = (
    train
    .groupby("engine_id")["cycle"]
    .max()
)

# Map the final cycle back to every row.

train["final_cycle"] = (
    train["engine_id"]
    .map(max_cycle_per_engine)
)

# Remaining Useful Life.

train["RUL"] = (
    train["final_cycle"] - train["cycle"]
)


# ============================================================
# TEST RUL
# ============================================================

print()
print("=" * 70)
print("CREATING TEST RUL TARGET")
print("=" * 70)

# RUL_FD001 contains one RUL value for each test engine.
# Engine IDs are 1 to 100.

official_rul = rul[0].values

if len(official_rul) != test["engine_id"].nunique():
    raise ValueError(
        "Number of RUL values does not match "
        "number of test engines."
    )

# Find the final observed cycle for every test engine.

test_last_cycle = (
    test
    .groupby("engine_id")["cycle"]
    .max()
)

test["final_cycle"] = (
    test["engine_id"]
    .map(test_last_cycle)
)

# Only the LAST observed cycle of each test engine
# receives the official RUL value.

test["RUL"] = np.nan

for engine_id in sorted(test["engine_id"].unique()):

    engine_rows = test[
        test["engine_id"] == engine_id
    ]

    last_index = engine_rows["cycle"].idxmax()

    test.loc[last_index, "RUL"] = (
        official_rul[engine_id - 1]
    )


# ============================================================
# SELECT MODEL FEATURES
# ============================================================

selected_features = [
    "engine_id",
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
    "sensor_21",
    "RUL"
]


train_output = train[selected_features].copy()

test_output = test[selected_features].copy()


# ============================================================
# SAVE DATASETS
# ============================================================

train_output.to_csv(
    TRAIN_OUTPUT,
    index=False
)

test_output.to_csv(
    TEST_OUTPUT,
    index=False
)


# ============================================================
# DISPLAY INFORMATION
# ============================================================

print()
print("=" * 70)
print("TRAINING DATASET")
print("=" * 70)

print(
    "Rows:",
    len(train_output)
)

print(
    "Columns:",
    len(train_output.columns)
)

print(
    "RUL minimum:",
    train_output["RUL"].min()
)

print(
    "RUL maximum:",
    train_output["RUL"].max()
)

print()
print("First 5 training rows:")

print(
    train_output
    .head()
    .round(4)
    .to_string(index=False)
)


# ============================================================
# TEST DATASET INFORMATION
# ============================================================

print()
print("=" * 70)
print("TEST DATASET")
print("=" * 70)

print(
    "Rows:",
    len(test_output)
)

print(
    "Columns:",
    len(test_output.columns)
)

print(
    "Rows with official RUL:",
    test_output["RUL"].notna().sum()
)

print()
print("Final test rows containing official RUL:")

print(
    test_output[
        test_output["RUL"].notna()
    ]
    .head(10)
    .round(4)
    .to_string(index=False)
)


# ============================================================
# CHECK TRAINING RUL
# ============================================================

print()
print("=" * 70)
print("TRAINING RUL CHECK")
print("=" * 70)

engine_1_check = train_output[
    train_output["engine_id"] == 1
]

print()
print("Engine 1 first 5 cycles:")

print(
    engine_1_check[
        ["engine_id", "cycle", "RUL"]
    ]
    .head()
    .to_string(index=False)
)

print()
print("Engine 1 last 5 cycles:")

print(
    engine_1_check[
        ["engine_id", "cycle", "RUL"]
    ]
    .tail()
    .to_string(index=False)
)


# ============================================================
# COMPLETED
# ============================================================

print()
print("=" * 70)
print("C-MAPSS FD001 RUL PREPARATION COMPLETED")
print("=" * 70)

print()
print("Training output:")
print(TRAIN_OUTPUT)

print()
print("Test output:")
print(TEST_OUTPUT)