import pandas as pd
import os
import re
from pathlib import Path

# Get project root from script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# --- Configuration ---
# 1. Path to the metadata CSV created in previous steps
METADATA_CSV = str(PROJECT_ROOT / 'data/raw/metadata/Final_Dataset_With_SRR.csv')

# 2. Path to the original FASTA file
INPUT_FASTA = str(PROJECT_ROOT / 'data/processed/consensus/fasta/msa_consensus.fa')

# 3. Path for the output file - this file will have "clean" headers safe for IQ-TREE
OUTPUT_FASTA = str(PROJECT_ROOT / 'data/processed/consensus/trees/msa_consensus_clean_headers.fa')

# --- Helper Function for Cleaning Names ---
def clean_name(text):
    """
    Replaces problematic characters (spaces, commas, parentheses, slashes) with underscores.
    This prevents phylogenetic software (like IQ-TREE) from truncating or misinterpreting names.
    
    Example: "Golden Retriever" -> "Golden_Retriever"
             "Dachshund/West"   -> "Dachshund_West"
    """
    if pd.isna(text): return "NA"
    text = str(text)
    
    # Replace any character that is NOT alphanumeric with an underscore
    clean_text = re.sub(r'[^a-zA-Z0-9]', '_', text)
    
    # Collapse multiple consecutive underscores into a single one
    clean_text = re.sub(r'_+', '_', clean_text)
    
    # Remove leading or trailing underscores
    return clean_text.strip('_')

# --- Main Logic ---

# 1. Load Metadata
print(f"Loading metadata from: {METADATA_CSV}")
if not os.path.exists(METADATA_CSV):
    print("Error: Metadata CSV not found.")
    exit(1)

df = pd.read_csv(METADATA_CSV)
# Ensure SRR column is string and clean of whitespace
df['SRR'] = df['SRR'].astype(str).str.strip()

# 2. Create Lookup Dictionary
# Goal: Create a safe suffix string in the format: _SAMN_Breed_Type
srr_lookup = {}

for _, row in df.iterrows():
    # Clean all relevant fields using the helper function
    # Spaces will become underscores here
    srr = clean_name(row['SRR'])
    samn = clean_name(row['SAMN'])
    breed = clean_name(row['Breed'])
    b_type = clean_name(row['Breed_Type'])
    
    # Construct the suffix using underscores as separators
    # Format: _SAMN_Breed_Type
    suffix = f"_{samn}_{breed}_{b_type}"
    
    # Store in dictionary using the cleaned SRR as the key
    srr_lookup[srr] = suffix

print(f"Loaded metadata for {len(srr_lookup)} samples.")

# 3. Process FASTA File
print(f"Processing FASTA: {INPUT_FASTA}...")

if not os.path.exists(INPUT_FASTA):
    print("Error: Input FASTA not found.")
    exit(1)

count_updated = 0
with open(INPUT_FASTA, 'r') as f_in, open(OUTPUT_FASTA, 'w') as f_out:
    for line in f_in:
        if line.startswith('>'):
            # Extract the original ID from the FASTA header
            original_id = line.strip().replace('>', '')
            
            # Clean the ID from the file to match it against our dictionary keys
            clean_id = clean_name(original_id)
            
            # Check if the cleaned ID exists in our metadata
            # (We prioritize the cleaned version since our dict keys are cleaned)
            lookup_key = clean_id
            
            if lookup_key in srr_lookup:
                # Construct the new, safe header
                # Example result: >SRR18400027_SAMN25330754_Belgian_Sheepdog_Purebred
                new_header = f">{lookup_key}{srr_lookup[lookup_key]}\n"
                f_out.write(new_header)
                count_updated += 1
            else:
                # If no metadata is found, write the cleaned ID to ensure safety
                f_out.write(f">{clean_id}\n")
        else:
            # Write sequence lines exactly as they are
            f_out.write(line)

# 4. Final Summary
print("-" * 30)
print(f"Done! Updated {count_updated} headers.")
print(f"Saved CLEAN file to:\n{os.path.abspath(OUTPUT_FASTA)}")
print("You can now run IQ-TREE on this file without warnings.")