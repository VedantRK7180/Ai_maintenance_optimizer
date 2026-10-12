import pandas as pd
import numpy as np


# ============================================================
# NASA C-MAPSS FD001 DATA INSPECTION
# ============================================================

TRAIN_FILE = "data/NASA_CMAPSS/train_FD001.txt"
TEST_FILE = "data/NASA_CMAPSS/test_FD001.txt"
RUL_FILE = "data/NASA_CMAPSS/RUL_FD001.txt"


# ============================================================
# LOAD DATA
# ============================================================

train = pd.read_csv(
    TRAIN_FILE,
    sep=r"\s+",
    header=None
)

test = pd.read_csv(
    TEST_FILE,
    sep=r"\s+",
    header=None
)

rul = pd.read_csv(
    RUL_FILE,
    sep=r"\s+",
    header=None
)


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


train.columns = columns
test.columns = columns


# ============================================================
# BASIC INFORMATION
# ============================================================

print("=" * 70)
print("NASA C-MAPSS FD001 DATA INSPECTION")
print("=" * 70)

print()

print("TRAINING SHAPE:", train.shape)
print("TEST SHAPE    :", test.shape)
print("RUL SHAPE     :", rul.shape)


# ============================================================
# ENGINE INFORMATION
# ============================================================

print()
print("=" * 70)
print("ENGINE INFORMATION")
print("=" * 70)

print(
    "Training engines:",
    train["engine_id"].nunique()
)

print(
    "Testing engines :",
    test["engine_id"].nunique()
)


# ============================================================
# CYCLE INFORMATION
# ============================================================

print()
print("=" * 70)
print("CYCLE INFORMATION")
print("=" * 70)

print(
    "Training cycle range:",
    train["cycle"].min(),
    "to",
    train["cycle"].max()
)

print(
    "Test cycle range:",
    test["cycle"].min(),
    "to",
    test["cycle"].max()
)


# ============================================================
# TRAINING ENGINE LIFETIMES
# ============================================================

train_lifetimes = (
    train
    .groupby("engine_id")["cycle"]
    .max()
)

print()
print("=" * 70)
print("TRAINING ENGINE LIFETIMES")
print("=" * 70)

print(
    train_lifetimes.describe()
    .round(2)
    .to_string()
)


# ============================================================
# TEST ENGINE LAST CYCLES
# ============================================================

test_last_cycles = (
    test
    .groupby("engine_id")["cycle"]
    .max()
)

print()
print("=" * 70)
print("TEST ENGINE LAST CYCLES")
print("=" * 70)

print(
    test_last_cycles.describe()
    .round(2)
    .to_string()
)


# ============================================================
# RUL INFORMATION
# ============================================================

print()
print("=" * 70)
print("TEST RUL INFORMATION")
print("=" * 70)

print(
    rul[0]
    .describe()
    .round(2)
    .to_string()
)


# ============================================================
# SENSOR VARIABILITY
# ============================================================

sensor_columns = [
    f"sensor_{i}"
    for i in range(1, 22)
]

sensor_stats = []

for sensor in sensor_columns:

    values = train[sensor]

    sensor_stats.append({
        "sensor": sensor,
        "min": values.min(),
        "max": values.max(),
        "mean": values.mean(),
        "std": values.std(),
        "unique_values": values.nunique()
    })


sensor_stats_df = pd.DataFrame(sensor_stats)


# ============================================================
# DISPLAY SENSOR STATISTICS
# ============================================================

print()
print("=" * 70)
print("SENSOR VARIABILITY")
print("=" * 70)

print(
    sensor_stats_df
    .round(4)
    .to_string(index=False)
)


# ============================================================
# CONSTANT / NEAR-CONSTANT SENSORS
# ============================================================

constant_sensors = sensor_stats_df[
    sensor_stats_df["unique_values"] <= 1
]["sensor"].tolist()


near_constant_sensors = sensor_stats_df[
    sensor_stats_df["std"] < 0.01
]["sensor"].tolist()


print()
print("=" * 70)
print("CONSTANT SENSORS")
print("=" * 70)

if constant_sensors:
    print(constant_sensors)
else:
    print("None")


print()
print("=" * 70)
print("NEAR-CONSTANT SENSORS (STD < 0.01)")
print("=" * 70)

if near_constant_sensors:
    print(near_constant_sensors)
else:
    print("None")


# ============================================================
# FIRST ENGINE PROGRESSION
# ============================================================

engine_1 = train[
    train["engine_id"] == 1
].copy()

print()
print("=" * 70)
print("ENGINE 1")
print("=" * 70)

print(
    "Number of cycles:",
    len(engine_1)
)

print()
print("First 5 cycles:")

print(
    engine_1.head()
    .round(4)
    .to_string(index=False)
)

print()
print("Last 5 cycles:")

print(
    engine_1.tail()
    .round(4)
    .to_string(index=False)
)


# ============================================================
# COMPLETED
# ============================================================

print()
print("=" * 70)
print("FD001 INSPECTION COMPLETED")
print("=" * 70)