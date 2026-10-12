import pandas as pd
import numpy as np


# ============================================================
# NASA IMS SMOOTHED HEALTH / DEGRADATION INDEX
# ============================================================

INPUT_FILE = "data/nasa_ims_2nd_test_channel_features.csv"
OUTPUT_FILE = "data/nasa_ims_health_index.csv"

CHANNEL_TO_ANALYZE = 1

# Number of neighboring measurements used for smoothing.
# 25 measurements = approximately 4 hours of data
# because measurements are roughly 10 minutes apart.
ROLLING_WINDOW = 25


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(INPUT_FILE)

print("=" * 70)
print("NASA IMS SMOOTHED HEALTH INDEX")
print("=" * 70)

print()
print("Input file:")
print(INPUT_FILE)

print()
print("Total records:", len(df))


# ============================================================
# SELECT CHANNEL
# ============================================================

channel_df = df[
    df["channel"] == CHANNEL_TO_ANALYZE
].copy()

channel_df = channel_df.reset_index(drop=True)

print()
print("Channel selected:", CHANNEL_TO_ANALYZE)
print("Channel records:", len(channel_df))


# ============================================================
# TIME POSITION
# ============================================================

channel_df["position"] = (
    np.arange(len(channel_df))
    / (len(channel_df) - 1)
)


# ============================================================
# SORT BY TIME
# ============================================================

channel_df = channel_df.sort_values(
    "file_name"
).reset_index(drop=True)


# ============================================================
# FEATURES USED FOR DEGRADATION
# ============================================================

features = [
    "rms",
    "peak",
    "crest_factor",
    "kurtosis"
]


# ============================================================
# ROLLING SMOOTHING
# ============================================================

print()
print("Applying rolling window:", ROLLING_WINDOW)

for feature in features:

    channel_df[
        feature + "_smooth"
    ] = (
        channel_df[feature]
        .rolling(
            window=ROLLING_WINDOW,
            center=True,
            min_periods=1
        )
        .mean()
    )


# ============================================================
# HEALTHY BASELINE
# ============================================================

# The first 10% of the experiment is used as the healthy
# reference condition.

baseline_count = max(
    25,
    int(len(channel_df) * 0.10)
)

baseline = channel_df.head(
    baseline_count
)

print()
print("Healthy baseline records:", baseline_count)


# ============================================================
# CALCULATE BASELINE VALUES
# ============================================================

baseline_values = {}

for feature in features:

    baseline_values[feature] = (
        baseline[feature + "_smooth"].mean()
    )


print()
print("Healthy baseline:")

for feature in features:

    print(
        f"{feature:15s}: "
        f"{baseline_values[feature]:.6f}"
    )


# ============================================================
# RELATIVE DEGRADATION
# ============================================================

for feature in features:

    baseline_value = baseline_values[feature]

    if baseline_value == 0:

        channel_df[
            feature + "_degradation"
        ] = 0

    else:

        channel_df[
            feature + "_degradation"
        ] = (
            (
                channel_df[
                    feature + "_smooth"
                ]
                - baseline_value
            )
            / baseline_value
        )


# ============================================================
# LIMIT EXTREME VALUES
# ============================================================

for feature in features:

    column = feature + "_degradation"

    channel_df[column] = (
        channel_df[column]
        .clip(lower=0, upper=5)
    )


# ============================================================
# CONVERT EACH FEATURE TO 0-100
# ============================================================

for feature in features:

    column = feature + "_degradation"

    channel_df[
        feature + "_score"
    ] = (
        channel_df[column] / 5
    ) * 100


# ============================================================
# COMBINED DEGRADATION SCORE
# ============================================================

channel_df["degradation_score"] = (
    0.35 * channel_df["rms_score"]
    + 0.25 * channel_df["peak_score"]
    + 0.20 * channel_df["crest_factor_score"]
    + 0.20 * channel_df["kurtosis_score"]
)


# ============================================================
# HEALTH SCORE
# ============================================================

channel_df["health_score"] = (
    100 - channel_df["degradation_score"]
)

channel_df["health_score"] = (
    channel_df["health_score"]
    .clip(0, 100)
)


# ============================================================
# CONDITION
# ============================================================

def determine_condition(score):

    if score < 25:
        return "Healthy"

    elif score < 50:
        return "Monitoring"

    elif score < 75:
        return "Degrading"

    else:
        return "Critical"


channel_df["condition"] = (
    channel_df["degradation_score"]
    .apply(determine_condition)
)


# ============================================================
# SAVE
# ============================================================

channel_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

display_columns = [
    "file_name",
    "position",
    "rms",
    "peak",
    "crest_factor",
    "kurtosis",
    "degradation_score",
    "health_score",
    "condition"
]


print()
print("=" * 70)
print("FIRST 5 RECORDS")
print("=" * 70)

print(
    channel_df[display_columns]
    .head()
    .round(4)
    .to_string(index=False)
)


print()
print("=" * 70)
print("MIDDLE 5 RECORDS")
print("=" * 70)

middle = len(channel_df) // 2

print(
    channel_df[display_columns]
    .iloc[middle - 2:middle + 3]
    .round(4)
    .to_string(index=False)
)


print()
print("=" * 70)
print("LAST 10 RECORDS")
print("=" * 70)

print(
    channel_df[display_columns]
    .tail(10)
    .round(4)
    .to_string(index=False)
)


# ============================================================
# STAGE SUMMARY
# ============================================================

channel_df["stage"] = pd.cut(
    channel_df["position"],
    bins=[
        -0.01,
        0.25,
        0.50,
        0.75,
        1.01
    ],
    labels=[
        "Beginning",
        "25%",
        "50%",
        "End"
    ]
)


print()
print("=" * 70)
print("DEGRADATION BY EXPERIMENT STAGE")
print("=" * 70)

stage_summary = (
    channel_df
    .groupby(
        "stage",
        observed=True
    )[
        [
            "rms_smooth",
            "peak_smooth",
            "crest_factor_smooth",
            "kurtosis_smooth",
            "degradation_score",
            "health_score"
        ]
    ]
    .mean()
)


print(
    stage_summary
    .round(4)
    .to_string()
)


# ============================================================
# CONDITION DISTRIBUTION
# ============================================================

print()
print("=" * 70)
print("CONDITION DISTRIBUTION")
print("=" * 70)

print(
    channel_df["condition"]
    .value_counts()
    .to_string()
)


print()
print("=" * 70)
print("NASA SMOOTHED HEALTH INDEX COMPLETED")
print("=" * 70)

print()
print("Output file:")
print(OUTPUT_FILE)