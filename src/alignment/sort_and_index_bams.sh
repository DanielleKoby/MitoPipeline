#!/bin/bash
#
# sort_and_index_bams.sh
#
# This script sorts and then indexes all BAM files from a source directory.

# --- Configuration ---
set -e
IN_DIR="data_processing/bam_files"
SORTED_DIR="data_processing/sorted_bam_files"

# --- Main Logic ---
echo "Starting to sort and index BAM files from: ${IN_DIR}"

# Loop through every file that ends with .bam
for in_bam in "${IN_DIR}"/*.bam; do
  
  if [ -f "$in_bam" ]; then
    
    base_name=$(basename "$in_bam" .bam)
    sorted_bam="${SORTED_DIR}/${base_name}.sorted.bam"
    
    echo "---"
    # Step 1: Sorting the file
    echo "Sorting ${in_bam}..."
    samtools sort "$in_bam" -o "$sorted_bam"
    
    # Step 2: Indexing the NEW sorted file
    echo "Indexing ${sorted_bam}..."
    samtools index "$sorted_bam"
    
  fi
done

echo "---"
echo "All files have been sorted and indexed. Output is in ${SORTED_DIR}"