import pandas as pd
import os

# Find project folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Input and output paths
INPUT_PATH = os.path.join(BASE_DIR, "data", "ai4i2020.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "ai4i_model_data.csv")

# Load original dataset
df = pd.read_csv(INPUT_PATH)

# Features we will use for the first AI model
features = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]"
]

# Target variable
target = "Machine failure"

# Create model dataset
model_df = df[features + [target]].copy()

# Save prepared dataset
model_df.to_csv(OUTPUT_PATH, index=False)

print("\n========== DATA PREPARATION ==========\n")

print("Original dataset shape:")
print(df.shape)

print("\nModel dataset shape:")
print(model_df.shape)

print("\nFeatures used:")
for feature in features:
    print("-", feature)

print("\nTarget:")
print("-", target)

print("\nExcluded columns:")
print("- UDI")
print("- Product ID")
print("- TWF")
print("- HDF")
print("- PWF")
print("- OSF")
print("- RNF")

print("\nPrepared dataset saved to:")
print(OUTPUT_PATH)

print("\n======================================\n")