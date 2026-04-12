#!/bin/bash
#
# sam_to_bam_converter_v2.sh
#
# This script automatically finds the data_processing directory relative to its own location,
# converts all SAM files to BAM, and saves them in a new bam_files directory.

# --- Configuration ---
# Exit immediately if a command fails
set -e

# --- Path Setup ---
# Find the directory where this script is located
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# Define the input and output directories based on the script's location
SAM_DIR="${SCRIPT_DIR}/../data_processing"
BAM_DIR="${SCRIPT_DIR}/../bam_files"

# Create the output directory if it doesn't exist
mkdir -p "$BAM_DIR"

# --- Main Logic ---
echo "Looking for SAM files in: ${SAM_DIR}"

# Check if any SAM files exist before starting the loop
if ! ls "${SAM_DIR}"/*.sam &>/dev/null; then
    echo "No .sam files found in ${SAM_DIR}. Exiting."
    exit 0
fi

echo "Starting SAM to BAM conversion..."

# Loop through every file that ends with .sam in the specified directory
for sam_file in "${SAM_DIR}"/*.sam; do
  
  # Extract just the base filename (e.g., "SRR28218949")
  base_name=$(basename "$sam_file" .sam)
  
  # Create the full path for the output BAM file
  bam_file="${BAM_DIR}/${base_name}.bam"
  
  echo "Converting ${sam_file} to ${bam_file}..."
  
  # Run the samtools command
  samtools view -bS "$sam_file" > "$bam_file"
    
done

echo "Conversion complete. BAM files are in ${BAM_DIR}"