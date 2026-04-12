import pandas as pd
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# --- Configuration ---
# Please update these filenames to match your actual files.
CSV_FILE = str(PROJECT_ROOT / 'data/raw/metadata/DAP_b1-7_sample_map.csv')
TSV_FILE = str(PROJECT_ROOT / 'data/raw/metadata/DogAgingProject_GeneticData_CuratedRelease_2024.tsv')
CSV_ID_COLUMN = 'clinical_dog_id'
TSV_ID_COLUMN = 'dog'
BIOSAMPLE_COLUMN = 'biosample'
# Breed_Status,Breed
# --- Output Filenames ---
FILTERED_TSV_OUTPUT = str(PROJECT_ROOT / 'data/raw/metadata/filtered_metadata.tsv')
BIOSAMPLE_OUTPUT = str(PROJECT_ROOT / 'data/raw/metadata/biosample_ids.txt')

# Step 1: Read the CSV and get a unique set of dog IDs for fast lookup.
print(f"Reading clinical IDs from {CSV_FILE}...")
breed_df = pd.read_csv(CSV_FILE)
# clinical_dog_ids = set(breed_df[CSV_ID_COLUMN].dropna())
# print(f"Found {len(clinical_dog_ids)} unique clinical dog IDs.")

# # Step 2: Read the main TSV file.
# print(f"Reading metadata from {TSV_FILE}...")
# metadata_df = pd.read_csv(TSV_FILE, sep='\t')

# # Step 3: Filter the TSV data to keep only rows where the dog ID is in our set.
# print("Finding overlapping records...")
# overlapping_records_df = metadata_df[metadata_df[TSV_ID_COLUMN].isin(clinical_dog_ids)]

# # Step 4: Save the filtered TSV data to a new file.
# overlapping_records_df.to_csv(FILTERED_TSV_OUTPUT, sep='\t', index=False)
# print(f"Successfully saved {len(overlapping_records_df)} overlapping records to {FILTERED_TSV_OUTPUT}")

# # --- Statistics and BioSample Filtering ---

# # Print the number of overlapping records found.
# print(f"\n--- Statistics ---")
# print(f"Total overlapping records found: {len(overlapping_records_df)}")

# # Calculate and print how many of the overlapping records have 'NA' for biosample.
# # We'll treat both the string 'NA' and actual missing values (NaN) as NA.
# na_biosample_count = overlapping_records_df[BIOSAMPLE_COLUMN].isna().sum() + \
#                         (overlapping_records_df[BIOSAMPLE_COLUMN] == 'NA').sum()
# print(f"Number of overlapping records with NA biosample: {na_biosample_count}")

# # Step 5: Filter out the 'NA' biosamples to create the second file.
# valid_biosamples_df = overlapping_records_df[overlapping_records_df[BIOSAMPLE_COLUMN].notna()]
# valid_biosamples_df = valid_biosamples_df[valid_biosamples_df[BIOSAMPLE_COLUMN] != 'NA']

# # Step 6: Save only the biosample column from this final filtered list.
# valid_biosamples_df[BIOSAMPLE_COLUMN].to_csv(BIOSAMPLE_OUTPUT, index=False, header=False)
# print(f"Successfully saved {len(valid_biosamples_df)} valid biosample IDs to {BIOSAMPLE_OUTPUT}")

