#!/bin/bash
#
# samn_to_srr.sh (v5 - Corrected API Logic)
#
# This script converts a list of BioSample (SAMN) accessions to Run (SRR)
# accessions using the correct new ENA API logic.

# --- Configuration ---
set -e

# Get project root from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"

CHUNK_SIZE=50
OUTPUT_DIR="${PROJECT_ROOT}/data/raw/metadata"

# --- Argument Validation ---
if [ -z "$1" ]; then
  echo "Usage: ./samn_to_srr.sh <samn_input_file.txt>"
  exit 1
fi

INPUT_FILE="$1"
REPORT_FILE="${OUTPUT_DIR}/samn_to_srr_report.tsv"
OUTPUT_FILE="${OUTPUT_DIR}/srr_list.txt"
TEMP_DIR="${OUTPUT_DIR}/tmp_samn_chunks"

# --- Main Logic ---

# 1. Split the input file into chunks
echo "Step 1: Splitting SAMN list into chunks..."
mkdir -p "$TEMP_DIR"
split -l "$CHUNK_SIZE" "$INPUT_FILE" "${TEMP_DIR}/chunk_"

# 2. Initialize the final report file with a header
echo "Step 2: Fetching header for the report file..."
FIRST_ID=$(head -n 1 "$INPUT_FILE")
# CORRECTED: The query now uses 'sample_accession'
FIRST_ID_QUERY_RAW="sample_accession=\"${FIRST_ID}\""
FIRST_ID_QUERY_ENCODED=$(echo "$FIRST_ID_QUERY_RAW" | sed 's/ /%20/g; s/"/%22/g')
# CORRECTED: The result type is now 'read_run'
wget -O "$REPORT_FILE" "https://www.ebi.ac.uk/ena/portal/api/search?result=read_run&query=${FIRST_ID_QUERY_ENCODED}&fields=run_accession&format=tsv&download=true"

# 3. Loop through each chunk and append results
echo "Step 3: Fetching SRR accessions from ENA for each chunk..."
for chunk_file in "${TEMP_DIR}"/chunk_*; do
    
    # CORRECTED: Build the query using 'sample_accession'
    QUERY_STRING_RAW=$(awk '{printf "%ssample_accession=\"%s\"", (NR==1 ? "" : " OR "), $0}' "$chunk_file")
    
    # URL Encode the query string
    QUERY_STRING_ENCODED=$(echo "$QUERY_STRING_RAW" | sed 's/ /%20/g; s/"/%22/g')

    # CORRECTED: The result type is now 'read_run'
    # Fetch the report, skip its header, and append to the main report
    wget -O - "https://www.ebi.ac.uk/ena/portal/api/search?result=read_run&query=${QUERY_STRING_ENCODED}&fields=run_accession&format=tsv&download=true" | tail -n +2 >> "$REPORT_FILE"
done

# 4. Clean up the temporary directory
rm -r "$TEMP_DIR"

# 5. Process the final report to create a clean list of SRR IDs
echo "Step 4: Creating clean SRR list: ${OUTPUT_FILE}"
# The report now contains only run_accession, so we just need to skip the header
tail -n +2 "$REPORT_FILE" > "$OUTPUT_FILE"

echo "---"
echo "Success! SRR list created at ${OUTPUT_FILE}"