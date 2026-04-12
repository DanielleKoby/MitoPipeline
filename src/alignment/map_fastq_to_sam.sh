#!/bin/bash
# A script to align multiple paired-end FASTQ files using bwa-mem2

# Exit immediately if a command exits with a non-zero status.
set -e

# Get project root from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"
source "${PROJECT_ROOT}/tools/tool_paths.config"

# --- Parameters ---
NUM_OF_THREADS=40
REF_FILE="${PROJECT_ROOT}/reference/GCA_011100685.1_UU_Cfam_GSD_1.0_genomic.fna"
IN_DIR="${PROJECT_ROOT}/data/raw/fastq/all_samples"
OUT_DIR="${PROJECT_ROOT}/data/processed/alignment/sorted"

# Suffixes to identify the paired-end files
FASTQ_FWD_SUFFIX="_1.fastq.gz"
FASTQ_REV_SUFFIX="_2.fastq.gz"

# Create the output directory if it doesn't exist
mkdir -p "$OUT_DIR"

# Find all the forward reads in the input directory and loop through them
for FWD_FILE in "${IN_DIR}"/*"${FASTQ_FWD_SUFFIX}"; do
    
    # Extract the base name (Sample ID) from the forward read filename
    SAMPLE_ID=$(basename "$FWD_FILE" "$FASTQ_FWD_SUFFIX")
    
    # Construct the full path for the reverse read file
    REV_FILE="${IN_DIR}/${SAMPLE_ID}${FASTQ_REV_SUFFIX}"
    
    # Construct the output SAM file path
    OUT_FILE="${OUT_DIR}/${SAMPLE_ID}.sam"
    
    # Construct the Read Group header for this specific sample
    HEADER="@RG\tID:group1\tSM:${SAMPLE_ID}"
    
    # Check if the reverse file exists before running
    if [ -f "$REV_FILE" ]; then
        echo "--- Processing Sample: ${SAMPLE_ID} ---"
        
        # --- Execution ---
        # Run the alignment command
        "$BWA_EXEC" mem -t "$NUM_OF_THREADS" -Y -R "$HEADER" "$REF_FILE" "$FWD_FILE" "$REV_FILE" > "$OUT_FILE"
        
        echo "--- Finished processing ${SAMPLE_ID}. Output saved to ${OUT_FILE} ---"
    else
        echo "Warning: Reverse file not found for ${FWD_FILE}. Skipping."
    fi
done

echo "All samples processed."