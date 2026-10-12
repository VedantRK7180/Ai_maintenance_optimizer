import pandas as pd
import os

# Get the project folder path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Dataset path
DATA_PATH = os.path.join(BASE_DIR, "data", "ai4i2020.csv")

# Read dataset
df = pd.read_csv(DATA_PATH)

print("\n========== DATASET INSPECTION ==========\n")

print("Dataset shape:")
print(df.shape)

print("\nColumn names:")
for column in df.columns:
    print("-", column)

print("\nFirst 5 rows:")
print(df.head())

print("\nMissing values:")
print(df.isnull().sum())

print("\nTarget value counts:")
print(df["Machine failure"].value_counts())

print("\n========================================\n")