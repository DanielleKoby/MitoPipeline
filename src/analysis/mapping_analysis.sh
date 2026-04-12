#!/bin/bash

# Get project root from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"

# Define the output file name
ANALYSIS_DIR="${PROJECT_ROOT}/data/processed/analysis"
OUTPUT_CSV="${ANALYSIS_DIR}/preprocessing_metrics.csv"
PROCESSED_BAM_DIR="${PROJECT_ROOT}/data/processed/alignment/deduplicated"
LOG_DIR="${ANALYSIS_DIR}/logs"
LOG_FILE="${LOG_DIR}/analysis_run.log"
MISSING_FILES_LIST="${PROJECT_ROOT}/code/data_preprocessing/preprocessing_analysis/missing_files.txt"

mkdir -p "$ANALYSIS_DIR"
mkdir -p "$LOG_DIR"

if [ ! -f "${OUTPUT_CSV}" ]; then
    touch "${OUTPUT_CSV}"
fi

QUALITY_THRESHOLD=20


# # Write the header to the CSV file based on the parameters
# echo "Sample_ID,\
# Total_Reads,\
# Total_Mapped_Reads_w_Dups,Total_Mapped_Reads_wo_Dups,\
# Mito_Reads_w_Dups,Mito_Reads_wo_Dups,\
# Total_HQ_Reads_w_Dups,Total_HQ_Reads_wo_Dups,\
# Mito_HQ_Reads_w_Dups,Mito_HQ_Reads_wo_Dups,\
# Total_Depth_w_Dups,Total_Depth_wo_Dups,\
# Mito_Depth_w_Dups,\
# Mito_HQ_Depth_w_Dups" > $OUTPUT_CSV

for bam_file in "${PROCESSED_BAM_DIR}"/*.bam
do
  # Extract the sample ID from the filename
  SAMPLE_ID=$(basename "$bam_file" .bam)
  
  if grep -q -F -x "$SAMPLE_ID" "$MISSING_FILES_LIST"; then
      echo "${SAMPLE_ID} analysis start"
    
    # --- Calculations including unmapped reads and duplicates ---

    # Total reads in the BAM file (including unmapped)
    TOTAL_READS=$(samtools view -c "$bam_file")

    # Mapped reads (excluding unmapped reads, but including duplicates)
    TOTAL_MAPPED_W_DUPS=$(samtools view -c -F 4 "$bam_file")
    
    # Total mapped mitochondrial reads (including duplicates)
    MITO_READS_W_DUPS=$(samtools view -c -F 4 "$bam_file" "CM022001.1")
    
    # Total high-quality mapped reads (including duplicates)
    TOTAL_HQ_W_DUPS=$(samtools view -c -F 4 -q 20 "$bam_file")
    
    # Total high-quality mapped mitochondrial reads (including duplicates)
    MITO_HQ_W_DUPS=$(samtools view -c -F 4 -q 20 "$bam_file" "CM022001.1")
    
    echo "${SAMPLE_ID} Calculations including unmapped reads and duplicates- completed"

    # --- Calculations excluding duplicates (-F 1024) ---
    # Total mapped reads without duplicates
    TOTAL_MAPPED_WO_DUPS=$(samtools view -c -F 4 -F 1024 "$bam_file")
    
    # Total mapped mitochondrial reads without duplicates
    MITO_READS_WO_DUPS=$(samtools view -c -F 4 -F 1024 "$bam_file" "CM022001.1")
    
    # Total high-quality mapped reads without duplicates
    TOTAL_HQ_WO_DUPS=$(samtools view -c -F 4 -F 1024 -q 20 "$bam_file")
    
    # Total high-quality mapped mitochondrial reads without duplicates
    MITO_HQ_WO_DUPS=$(samtools view -c -F 4 -F 1024 -q 20 "$bam_file" "CM022001.1")
    
    echo "${SAMPLE_ID} Calculations excluding duplicates- completed"

    # --- Depth calculations ---
    # Total average depth (including duplicates)
    TOTAL_DEPTH_W_DUPS=$(samtools stats "$bam_file" | awk '/^COV/ {SUM_WEIGHTED += $3 * $4; SUM_BASES += $4;} END {if (SUM_BASES > 0) print SUM_WEIGHTED / SUM_BASES; else print 0;}')
    echo "${SAMPLE_ID}-TOTAL_DEPTH_W_DUPS"

    # Total average depth (without duplicates)
    TOTAL_DEPTH_WO_DUPS=$(samtools stats -F 1024 "$bam_file" | awk '/^COV/ {SUM_WEIGHTED += $3 * $4; SUM_BASES += $4;} END {if (SUM_BASES > 0) print SUM_WEIGHTED / SUM_BASES; else print 0;}')
    echo "${SAMPLE_ID}-TOTAL_DEPTH_WO_DUPS"

    # Mitochondrial average depth (including duplicates)
    MITO_DEPTH_W_DUPS=$(samtools depth -a "$bam_file" -r "CM022001.1" | awk '{sum+=$3} END { if (NR > 0) print sum/NR; else print 0 }')
    echo "${SAMPLE_ID}-MITO_DEPTH_W_DUPS"

    # High-quality mitochondrial average depth (including duplicates)
    MITO_HQ_DEPTH_W_DUPS=$(samtools depth -a -q 20 "$bam_file" -r "CM022001.1" | awk '{sum+=$3} END { if (NR > 0) print sum/NR; else print 0 }')
    echo "${SAMPLE_ID}-MITO_HQ_DEPTH_W_DUPS"
    
    echo "${SAMPLE_ID} Depth calculations- completed"

    # Append the data for the current sample to the CSV file
    echo "$SAMPLE_ID,$TOTAL_READS,$TOTAL_MAPPED_W_DUPS,$TOTAL_MAPPED_WO_DUPS,$MITO_READS_W_DUPS,$MITO_READS_WO_DUPS,$TOTAL_HQ_W_DUPS,$TOTAL_HQ_WO_DUPS,$MITO_HQ_W_DUPS,$MITO_HQ_WO_DUPS,$TOTAL_DEPTH_W_DUPS,$TOTAL_DEPTH_WO_DUPS,$MITO_DEPTH_W_DUPS,$MITO_HQ_DEPTH_W_DUPS" >> $OUTPUT_CSV
    echo "${SAMPLE_ID} saved data to csv- completed"
  
  else
    # This else block is optional, but good for logging.
    # It runs if the grep command fails (exit code 1), meaning the ID was NOT found in the list.
    echo "SKIPPING ${SAMPLE_ID}: Not in processing list."
  fi
  
done

echo "Data extraction complete. Results are in $OUTPUT_CSV"