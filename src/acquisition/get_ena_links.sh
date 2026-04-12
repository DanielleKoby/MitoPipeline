#!/bin/bash
#
# This script takes a file with a list of Run (SRR) accessions, splits it
# into chunks, and uses the new ENA API to fetch a list of FASTQ FTP
# download links.

# --- Configuration ---
set -e

# Get project root from script location
SCRIPT_DIR="$( cd \"$( dirname \"${BASH_SOURCE[0]}\" )\" && pwd )"
PROJECT_ROOT="$( cd \"${SCRIPT_DIR}/../../\" && pwd )"

CHUNK_SIZE=50
OUTPUT_DIR=\"${PROJECT_ROOT}/data/raw/metadata\"

# --- Argument Validation ---
if [ "$#" -ne 2 ]; then
  echo "Error: Incorrect number of arguments."
  echo "Usage: ./get_ena_links.sh <id_type> <input_file.txt>"
  echo "This script is designed for 'run' id_type, e.g.: ./get_ena_links.sh run srr_list.txt"
  exit 1
fi

ID_TYPE="$1" # Should be 'run'
INPUT_FILE="$2"
REPORT_FILE="${OUTPUT_DIR}/ena_report.tsv"
URL_FILE="${OUTPUT_DIR}/urls_to_download.txt"
TEMP_DIR="${OUTPUT_DIR}/tmp_id_chunks"

# --- Main Logic ---

# 1. Split the input file into chunks
echo "Step 1: Splitting SRR list into chunks..."
mkdir -p "$TEMP_DIR"
split -l "$CHUNK_SIZE" "$INPUT_FILE" "${TEMP_DIR}/chunk_"

# 2. Initialize the final report file with a header
echo "Step 2: Fetching header for the report file..."
FIRST_ID=$(head -n 1 "$INPUT_FILE")
FIRST_ID_QUERY_RAW="accession=\"${FIRST_ID}\""
FIRST_ID_QUERY_ENCODED=$(echo "$FIRST_ID_QUERY_RAW" | sed 's/ /%20/g; s/"/%22/g')
wget -O "$REPORT_FILE" "https://www.ebi.ac.uk/ena/portal/api/search?result=${ID_TYPE}&query=${FIRST_ID_QUERY_ENCODED}&fields=fastq_ftp&format=tsv&download=true"

# 3. Loop through each chunk and append results
echo "Step 3: Fetching FTP links from ENA for each chunk..."
for chunk_file in "${TEMP_DIR}"/chunk_*; do
    
    # Build and URL Encode the query string
    QUERY_STRING_RAW=$(awk '{printf "%saccession=\"%s\"", (NR==1 ? "" : " OR "), $0}' "$chunk_file")
    QUERY_STRING_ENCODED=$(echo "$QUERY_STRING_RAW" | sed 's/ /%20/g; s/"/%22/g')

    # Fetch the report, skip its header, and append to the main report
    wget -O - "https://www.ebi.ac.uk/ena/portal/api/search?result=${ID_TYPE}&query=${QUERY_STRING_ENCODED}&fields=fastq_ftp&format=tsv&download=true" | tail -n +2 >> "$REPORT_FILE"
done

# 4. Clean up the temporary directory
rm -r "$TEMP_DIR"

# 5. Process the final combined report to create a clean URL list for aria2c
echo "Step 4: Processing final report and creating ${URL_FILE}..."
tail -n +2 "$REPORT_FILE" | cut -f1 | tr ';' '\n' > "$URL_FILE"

echo "---"
echo "Success! Your download list is ready at ${URL_FILE}"