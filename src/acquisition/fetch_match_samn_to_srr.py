import pandas as pd
import requests
import io
import time
import os
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# --- Configuration ---
INPUT_CSV = str(PROJECT_ROOT / 'data/raw/metadata/SAMN_Breed_Mapping.csv')
OUTPUT_CSV = str(PROJECT_ROOT / 'data/raw/metadata/Final_Dataset_With_SRR.csv')
CHUNK_SIZE = 50                          

# 1. Load the Input Data
print(f"Loading data from {INPUT_CSV}...")
df = pd.read_csv(INPUT_CSV)

# Ensure SAMN column is a clean string
df['SAMN'] = df['SAMN'].astype(str).str.strip()

# Get a unique list of SAMNs to query
samn_list = df['SAMN'].unique().tolist()
print(f"Found {len(samn_list)} unique SAMN IDs to query.")

# 2. Define Function to Query ENA API
def fetch_srr_from_ena_chunk(samn_chunk):
    query_parts = [f'sample_accession="{s}"' for s in samn_chunk]
    query = " OR ".join(query_parts)
    
    base_url = "https://www.ebi.ac.uk/ena/portal/api/search"
    params = {
        'result': 'read_run',
        'query': query,
        'fields': 'sample_accession,run_accession',
        'format': 'tsv',
        'download': 'true'
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        if not response.text.strip():
            return pd.DataFrame()
        return pd.read_csv(io.StringIO(response.text), sep='\t')
    except Exception as e:
        print(f"Error querying chunk: {e}")
        return pd.DataFrame()

# 3. Iterate over chunks
ena_results = []
total_chunks = (len(samn_list) // CHUNK_SIZE) + 1

print("Starting API queries...")
for i in range(0, len(samn_list), CHUNK_SIZE):
    chunk = samn_list[i:i + CHUNK_SIZE]
    print(f"Processing chunk {i // CHUNK_SIZE + 1}/{total_chunks} ({len(chunk)} IDs)...")
    
    df_chunk_res = fetch_srr_from_ena_chunk(chunk)
    if not df_chunk_res.empty:
        ena_results.append(df_chunk_res)
    time.sleep(0.5)

# 4. Concatenate API results
if ena_results:
    df_ena = pd.concat(ena_results, ignore_index=True)
else:
    df_ena = pd.DataFrame(columns=['sample_accession', 'run_accession'])

# 5. Prepare Data for Merging
df_ena.rename(columns={'sample_accession': 'SAMN', 'run_accession': 'SRR'}, inplace=True)

# 6. Merge
final_df = pd.merge(df, df_ena, on='SAMN', how='left')

# 7. Reorder Columns
cols = ['SRR'] + [c for c in final_df.columns if c != 'SRR']
final_df = final_df[cols]

# 8. CLEAN DUPLICATES (This is the new fix)
print(f"Rows before deduplication: {len(final_df)}")
final_df.drop_duplicates(inplace=True)
print(f"Rows after deduplication: {len(final_df)}")

# 9. Save
final_df.to_csv(OUTPUT_CSV, index=False)

print("-" * 30)
print("Preview of Final Data:")
print(final_df.head())
print("-" * 30)
print(f"Done! Final file saved to:\n{os.path.abspath(OUTPUT_CSV)}")