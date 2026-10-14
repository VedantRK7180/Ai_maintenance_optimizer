import os
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# NASA IMS BEARING DATASET
# FEATURE EXTRACTION
# ============================================================

# Path to NASA IMS 1st test dataset
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_FOLDER = (
    PROJECT_ROOT / "data" / "NASA_IMS_Bearings" / "4. Bearings"
    / "IMS" / "1st_test" / "1st_test"
)

# Output file
OUTPUT_FILE = PROJECT_ROOT / "data" / "nasa_ims_features.csv"


def calculate_features(signal):
    """
    Calculate useful statistical features from
    one vibration signal.
    """

    signal = np.asarray(signal, dtype=float)

    # Remove invalid values if any
    signal = signal[np.isfinite(signal)]

    if len(signal) == 0:
        return None

    # RMS
    rms = np.sqrt(np.mean(signal ** 2))

    # Mean
    mean = np.mean(signal)

    # Standard deviation
    std = np.std(signal)

    # Maximum and minimum
    maximum = np.max(signal)
    minimum = np.min(signal)

    # Peak-to-peak
    peak_to_peak = maximum - minimum

    # Absolute peak
    peak = np.max(np.abs(signal))

    # Crest factor
    if rms != 0:
        crest_factor = peak / rms
    else:
        crest_factor = 0

    # Kurtosis
    if std != 0:
        kurtosis = np.mean(((signal - mean) / std) ** 4)
    else:
        kurtosis = 0

    return {
        "rms": rms,
        "mean": mean,
        "std": std,
        "max": maximum,
        "min": minimum,
        "peak_to_peak": peak_to_peak,
        "peak": peak,
        "crest_factor": crest_factor,
        "kurtosis": kurtosis
    }


def read_vibration_file(file_path):
    """
    Read one NASA IMS vibration file.

    The files contain whitespace-separated
    numerical vibration samples.
    """

    try:
        data = np.loadtxt(file_path)

        # Convert the complete 2D data into one signal
        signal = data.flatten()

        return signal

    except Exception as error:
        print(f"Could not read {file_path}")
        print(f"Error: {error}")
        return None


def main():

    print("=" * 70)
    print("NASA IMS BEARING DATASET")
    print("VIBRATION FEATURE EXTRACTION")
    print("=" * 70)

    # Check folder
    if not os.path.exists(DATA_FOLDER):
        print()
        print("ERROR: NASA IMS dataset folder not found.")
        print()
        print("Expected folder:")
        print(DATA_FOLDER)
        return

    # Get files
    files = [
        file
        for file in os.listdir(DATA_FOLDER)
        if os.path.isfile(os.path.join(DATA_FOLDER, file))
    ]

    # Sort according to timestamp filename
    files.sort()

    print()
    print(f"NASA IMS files found : {len(files)}")

    if len(files) == 0:
        print("ERROR: No data files found.")
        return

    print()
    print("Processing vibration files...")
    print()

    results = []

    for index, filename in enumerate(files, start=1):

        file_path = os.path.join(DATA_FOLDER, filename)

        signal = read_vibration_file(file_path)

        if signal is None:
            continue

        features = calculate_features(signal)

        if features is None:
            continue

        # Store file information
        row = {
            "file_name": filename,
            "sample_count": len(signal),
            **features
        }

        results.append(row)

        # Progress display
        if index % 100 == 0 or index == len(files):
            print(
                f"Processed {index}/{len(files)} files"
            )

    # Create dataframe
    dataframe = pd.DataFrame(results)

    # Save CSV
    dataframe.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 70)
    print("FEATURE EXTRACTION COMPLETED")
    print("=" * 70)

    print()
    print(f"Files processed : {len(dataframe)}")
    print(f"Features created: {len(dataframe.columns)}")

    print()
    print("Output file:")
    print(OUTPUT_FILE)

    print()
    print("First 5 rows:")
    print(dataframe.head())

    print()
    print("Feature columns:")
    print(list(dataframe.columns))

    print()
    print("=" * 70)
    print("SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    main()