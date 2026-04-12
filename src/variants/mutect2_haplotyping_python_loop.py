#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path

########################
# - GENERAL SETTINGS - #
########################

# Get project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

input_folder = PROJECT_ROOT / "data/processed/variants/raw"
output_folder = PROJECT_ROOT / "data/processed/variants/filtered"
bash_script = str(SCRIPT_DIR / "mutect2_haplotyping.sh")
ext = "raw_mito_calls.vcf.gz"

########################
# ------- RUN ------- #
########################

# Find all files in folder with the specified extension
vcf_files = [f for f in input_folder.iterdir() if f.is_file() and f.name.endswith(ext)]

# Loop over files and run the Bash script for each
for vcf_file in vcf_files:
    sample_name = vcf_file.stem.split(".")[0]  # Extract sample name

    # Define the expected output file of the Bash script
    # output_file = output_folder / f"{sample_name}.filtered_mito_calls.vcf.gz"

    # Skip if output file already exists
    # if output_file.exists():
    #     print(f"Skipping {sample_name}, output already exists.")
    #     continue

    # Run Bash script with the sample name as argument
    subprocess.run(["bash", bash_script, sample_name], check=True)
