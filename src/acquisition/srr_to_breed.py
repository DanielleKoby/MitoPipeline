import pandas as pd
import os
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# 1. Load the Phenotype/Metadata Table (Table 1)
pheno_path = str(PROJECT_ROOT / 'data/raw/metadata/DAP_b1-7_sample_map.csv')
df_pheno = pd.read_csv(pheno_path)

# 2. Load the Genetic Data Table (Table 3)
geno_path = str(PROJECT_ROOT / 'data/raw/metadata/DogAgingProject_GeneticData_CuratedRelease_2024.tsv')
df_geno = pd.read_csv(geno_path, sep='\t')

# 3. Data Cleaning: Prepare IDs for Merging
# We convert IDs to strings and strip whitespace to ensure ' 101' matches '101'
df_pheno['dap_dog_id'] = df_pheno['dap_dog_id'].astype(str).str.strip()
df_geno['dog'] = df_geno['dog'].astype(str).str.strip()

# 4. Merge the DataFrames
# We use a left join to keep genetic records, but we will filter missing ones later
merged_df = pd.merge(
    df_geno, 
    df_pheno, 
    left_on='dog', 
    right_on='dap_dog_id', 
    how='left'
)

# 5. Extract and Rename Columns
# Create a copy to avoid SettingWithCopyWarning
final_df = merged_df[['biosample', 'Breed', 'Breed_Status']].copy()

# Rename columns as requested
final_df.rename(columns={
    'biosample': 'SAMN',
    'Breed_Status': 'Breed_Type'
}, inplace=True)

# 6. Remove Rows with Missing Data (NaN)
# This removes rows where 'Breed' is NaN (merge failed) or 'SAMN' is NaN
print(f"Rows before cleaning: {len(final_df)}")
final_df.dropna(subset=['SAMN', 'Breed'], inplace=True)
print(f"Rows after removing NaNs: {len(final_df)}")

# 7. Save and Locate File
output_filename = str(PROJECT_ROOT / 'data/raw/metadata/SAMN_Breed_Mapping.csv')
final_df.to_csv(output_filename, index=False)

# Print the absolute path so you know exactly where the file is
print("-" * 30)
print(f"File successfully saved at:\n{os.path.abspath(output_filename)}")
print("-" * 30)

# Preview the final clean data
print(final_df.head())