import os
import pandas as pd
import numpy as np
from scipy.stats import kurtosis


# ============================================================
# NASA IMS BEARING FEATURE EXTRACTION
# 2nd Test - Channel-wise analysis
# ============================================================

INPUT_FOLDER = (
    "data/NASA_IMS_Bearings/"
    "4. Bearings/IMS/2nd_test/2nd_test"
)

OUTPUT_FILE = "data/nasa_ims_2nd_test_channel_features.csv"


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_features(signal):
    signal = np.asarray(signal, dtype=float)

    rms = np.sqrt(np.mean(signal ** 2))
    mean_value = np.mean(signal)
    std_value = np.std(signal)

    maximum = np.max(signal)
    minimum = np.min(signal)

    peak_to_peak = maximum - minimum

    peak = np.max(np.abs(signal))

    if rms == 0:
        crest_factor = 0
    else:
        crest_factor = peak / rms

    kurtosis_value = kurtosis(
        signal,
        fisher=False,
        bias=False
    )

    return {
        "sample_count": len(signal),
        "rms": rms,
        "mean": mean_value,
        "std": std_value,
        "max": maximum,
        "min": minimum,
        "peak_to_peak": peak_to_peak,
        "peak": peak,
        "crest_factor": crest_factor,
        "kurtosis": kurtosis_value
    }


# ============================================================
# FIND DATA FILES
# ============================================================

if not os.path.exists(INPUT_FOLDER):
    print("ERROR: NASA IMS folder was not found.")
    print()
    print("Expected folder:")
    print(INPUT_FOLDER)
    raise SystemExit


files = sorted(
    [
        file_name
        for file_name in os.listdir(INPUT_FOLDER)
        if os.path.isfile(
            os.path.join(INPUT_FOLDER, file_name)
        )
    ]
)


print("=" * 70)
print("NASA IMS BEARING FEATURE EXTRACTION")
print("=" * 70)

print()
print("Input folder:")
print(INPUT_FOLDER)

print()
print("Files found:", len(files))


# ============================================================
# PROCESS FILES
# ============================================================

all_features = []

for file_number, file_name in enumerate(files, start=1):

    file_path = os.path.join(
        INPUT_FOLDER,
        file_name
    )

    try:
        data = pd.read_csv(
            file_path,
            sep=r"\s+",
            header=None
        )

    except Exception as error:
        print()
        print("Could not read:", file_name)
        print("Error:", error)
        continue

    # --------------------------------------------------------
    # Check number of channels
    # --------------------------------------------------------

    number_of_channels = data.shape[1]

    # NASA IMS files should normally contain 8 channels.
    # We process whatever channels are actually present.
    # This prevents the script from crashing if a file differs.
    for channel_number in range(number_of_channels):

        signal = data.iloc[:, channel_number].values

        features = extract_features(signal)

        row = {
            "file_name": file_name,
            "channel": channel_number + 1
        }

        row.update(features)

        all_features.append(row)

    # --------------------------------------------------------
    # Progress display
    # --------------------------------------------------------

    if file_number == 1 or file_number % 100 == 0:

        print(
            f"Processed {file_number}/{len(files)} files"
        )


# ============================================================
# CREATE DATAFRAME
# ============================================================

features_df = pd.DataFrame(all_features)


# ============================================================
# SAVE DATASET
# ============================================================

features_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("=" * 70)
print("FEATURE EXTRACTION COMPLETED")
print("=" * 70)

print()
print("Rows generated:", len(features_df))

print()
print("Columns:")
print(list(features_df.columns))

print()
print("Output file:")
print(OUTPUT_FILE)

print()
print("First 10 rows:")
print(
    features_df.head(10).round(4).to_string(
        index=False
    )
)

print()
print("=" * 70)