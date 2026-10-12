import os
import numpy as np
import pandas as pd


# ============================================================
# NASA IMS BEARING DATASET
# ALL TEST SETS FEATURE EXTRACTION
# ============================================================

BASE_FOLDER = os.path.join(
    "data",
    "NASA_IMS_Bearings",
    "4. Bearings",
    "IMS"
)

OUTPUT_FILE = os.path.join(
    "data",
    "nasa_ims_all_features.csv"
)


# Actual folder locations found in our dataset
TEST_FOLDERS = {
    "1st_test": os.path.join(
        BASE_FOLDER,
        "1st_test",
        "1st_test"
    ),

    "2nd_test": os.path.join(
        BASE_FOLDER,
        "2nd_test",
        "2nd_test"
    ),

    "3rd_test": os.path.join(
        BASE_FOLDER,
        "3rd_test",
        "4th_test",
        "txt"
    )
}


def calculate_features(signal):
    """
    Calculate statistical vibration features
    from one vibration signal.
    """

    signal = np.asarray(signal, dtype=float)

    # Remove invalid values
    signal = signal[np.isfinite(signal)]

    if len(signal) == 0:
        return None

    # Mean
    mean = np.mean(signal)

    # Standard deviation
    std = np.std(signal)

    # RMS
    rms = np.sqrt(np.mean(signal ** 2))

    # Maximum
    maximum = np.max(signal)

    # Minimum
    minimum = np.min(signal)

    # Absolute peak
    peak = np.max(np.abs(signal))

    # Peak-to-peak
    peak_to_peak = maximum - minimum

    # Crest factor
    if rms != 0:
        crest_factor = peak / rms
    else:
        crest_factor = 0.0

    # Kurtosis
    if std != 0:
        kurtosis = np.mean(
            ((signal - mean) / std) ** 4
        )
    else:
        kurtosis = 0.0

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

        # Convert 2D vibration data into
        # one continuous signal
        signal = data.flatten()

        return signal

    except Exception as error:
        print()
        print(f"Could not read file: {file_path}")
        print(f"Error: {error}")

        return None


def process_test(test_name, folder_path):
    """
    Process all vibration files belonging
    to one NASA IMS test set.
    """

    print()
    print("=" * 70)
    print(f"PROCESSING {test_name}")
    print("=" * 70)

    if not os.path.exists(folder_path):
        print()
        print("ERROR: Folder not found:")
        print(folder_path)

        return []

    files = [
        file
        for file in os.listdir(folder_path)
        if os.path.isfile(
            os.path.join(folder_path, file)
        )
    ]

    files.sort()

    print()
    print(f"Files found : {len(files)}")
    print()
    print("Processing...")

    results = []

    for index, filename in enumerate(files, start=1):

        file_path = os.path.join(
            folder_path,
            filename
        )

        signal = read_vibration_file(file_path)

        if signal is None:
            continue

        features = calculate_features(signal)

        if features is None:
            continue

        row = {
            "test_set": test_name,
            "file_name": filename,
            "sample_count": len(signal),
            **features
        }

        results.append(row)

        if (
            index % 500 == 0
            or index == len(files)
        ):
            print(
                f"Processed {index}/{len(files)} files"
            )

    print()
    print(
        f"{test_name} completed: "
        f"{len(results)} files"
    )

    return results


def main():

    print("=" * 70)
    print("NASA IMS BEARING DATASET")
    print("ALL TEST SETS FEATURE EXTRACTION")
    print("=" * 70)

    all_results = []

    # Process all three test sets
    for test_name, folder_path in TEST_FOLDERS.items():

        results = process_test(
            test_name,
            folder_path
        )

        all_results.extend(results)

    # Convert to dataframe
    dataframe = pd.DataFrame(all_results)

    if dataframe.empty:
        print()
        print("ERROR: No vibration data was processed.")
        return

    # Sort by test set and filename
    dataframe = dataframe.sort_values(
        by=["test_set", "file_name"]
    ).reset_index(drop=True)

    # Save
    dataframe.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("ALL NASA IMS FEATURE EXTRACTION COMPLETED")
    print("=" * 70)

    print()
    print(f"Total files processed : {len(dataframe)}")
    print(f"Total features        : {len(dataframe.columns)}")

    print()
    print("Files by test set:")

    print(
        dataframe["test_set"]
        .value_counts()
        .sort_index()
    )

    print()
    print("Output file:")
    print(OUTPUT_FILE)

    print()
    print("Feature columns:")

    print(
        list(dataframe.columns)
    )

    print()
    print("First 5 rows:")

    print(
        dataframe.head().to_string(
            index=False
        )
    )

    print()
    print("=" * 70)
    print("SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    main()