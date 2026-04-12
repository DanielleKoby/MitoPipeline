#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Source tool configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"
source "${PROJECT_ROOT}/tools/tool_paths.config"

RUN_ID=$1
NUM_OF_THREADS=40
REF_FILE="${PROJECT_ROOT}/reference/GCA_011100685.1_UU_Cfam_GSD_1.0_genomic.fna"
IN_DIR="${PROJECT_ROOT}/data/raw/fastq/all_samples"
TMP_DIR="${PROJECT_ROOT}/data/processed/temp"
# Metadata
METADATA_CSV="${PROJECT_ROOT}/data/raw/metadata/metadata.csv"

# Suffixes to identify the paired-end files
FASTQ_FWD_SUFFIX="_1.fastq.gz"
FASTQ_REV_SUFFIX="_2.fastq.gz"
FWD_FILE="${IN_DIR}/${RUN_ID}${FASTQ_FWD_SUFFIX}"
REV_FILE="${IN_DIR}/${RUN_ID}${FASTQ_REV_SUFFIX}"

# Output directories
MAPPING_DIR="${PROJECT_ROOT}/data/processed/alignment/mapped"
RG_DIR="${PROJECT_ROOT}/data/processed/alignment/read_groups"
SORTED_DIR="${PROJECT_ROOT}/data/processed/alignment/sorted"
DUPS_REMOVED="${PROJECT_ROOT}/data/processed/alignment/deduplicated"
METRICS_DIR="${PROJECT_ROOT}/data/qc/dedup_metrics" 
LOGS="${PROJECT_ROOT}/data/processed/analysis/logs"
LOG_FILE="${LOGS}/${RUN_ID}_log.txt"
# Folders and files preperations

mkdir -p "$MAPPING_DIR"
mkdir -p "$RG_DIR"
mkdir -p "$SORTED_DIR"
mkdir -p "$DUPS_REMOVED"
mkdir -p "$METRICS_DIR"
mkdir -p "$LOGS"
mkdir -p "$TMP_DIR"


if [ ! -f "${LOGS}/${RUN_ID}_log.txt" ]; then
    touch "${LOGS}/${RUN_ID}_log.txt"
fi

# Tool paths already loaded from tool_paths.config
export PATH="${JAVA_HOME}/bin:${PATH}"
source "${CONDA_INIT}"

FILE="${MAPPING_DIR}/${RUN_ID}.bam"

# Step 1- executing wba-mem2 
# check if both reverse and forward file exists
if [ -f "$REV_FILE" ] && [ -f "$FWD_FILE" ]; then
    conda activate alisa
    echo "--- step 1- Processing Sample: ${RUN_ID} ---" >> $LOG_FILE
    # Run the alignment command
    "$BWA_EXEC" mem -t "$NUM_OF_THREADS" \
    -Y \
    "$REF_FILE" "$FWD_FILE" "$REV_FILE" \
    | samtools view -bS - > "$FILE"
    echo "--- step 1- DONE!: ${RUN_ID} ---" >> $LOG_FILE
 
    conda deactivate

else
    echo "--- ${RUN_ID} ERROR step 1 ---" >> $LOG_FILE
    exit 1
fi

# Step 1.1- adding RG data
conda activate alisa
BAM_WO_RG="$FILE"
FILE="${RG_DIR}/${RUN_ID}.bam"

if [ -f "$BAM_WO_RG" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- step 1.1 @RG addition - Processing Sample: ${RUN_ID} ---" >> $LOG_FILE
    METADATA_LINE=$(grep "$RUN_ID" "$METADATA_CSV")

    # Check if the Run ID was found in the CSV
    if [ -z "$METADATA_LINE" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- ERROR: Run ID ${RUN_ID} not found in ${METADATA_CSV}. Exiting. ---" >> $LOG_FILE
        exit 1
    fi

    # Extract the required fields using awk. -F',' sets the delimiter to a comma.
    LIBRARY_NAME=$(echo "$METADATA_LINE" | awk -F',' '{print $16}') 
    SAMPLE_NAME=$(echo "$METADATA_LINE" | awk -F',' '{print $25}')
    PLATFORM=$(echo "$METADATA_LINE" | awk -F',' '{print $21}')     
    echo "Found Metadata: Sample Name=${SAMPLE_NAME}, Library Name=${LIBRARY_NAME}, Platform Name=${PLATFORM}" >> $LOG_FILE

    # --- Run AddOrReplaceReadGroups ---
    echo "Running gatk AddOrReplaceReadGroups..." >> $LOG_FILE
    "${GATK_PATH}" AddOrReplaceReadGroups \
        -I "$BAM_WO_RG" \
        -O "$FILE" \
        --RGLB "$LIBRARY_NAME" \
        --RGPL "$PLATFORM" \
        --RGSM "$SAMPLE_NAME" \
        --RGPU "$RUN_ID"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finished creating ${FILE}" >> $LOG_FILE
fi
conda deactivate


# Step 2- sorting and mark duplicates 
# check if bam file exists
UNSORTED_FILE="$FILE"
FILE="${SORTED_DIR}/${RUN_ID}.bam"
if [ -f "$UNSORTED_FILE" ]; then
    conda activate alisa
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- step 2- Processing Sample: ${RUN_ID} ---" >> $LOG_FILE
    
    samtools sort -@ "$NUM_OF_THREADS" -T "${SORTED_DIR}/${RUN_ID}.sort.tmp" -o "$FILE" "$UNSORTED_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- step 2- sorted completed! ${RUN_ID} ---" >> $LOG_FILE

    # Removing dups
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Marking duplicates with GATK..."
    WITH_DUPS="${FILE}"
    FILE="${DUPS_REMOVED}/${RUN_ID}.bam"
    "${GATK_PATH}" MarkDuplicatesSpark \
        --java-options '-DGATK_STACKTRACE_ON_USER_EXCEPTION=true' \
        -I "$WITH_DUPS" \
        -O "$FILE" \
        -M "${METRICS_DIR}/${RUN_ID}.txt" \
        --conf "spark.executor.cores=${NUM_OF_THREADS}" \
        --conf "spark.local.dir=${DUPS_REMOVED}" \
        --tmp-dir "$TMP_DIR"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- step 2- DONE!: ${RUN_ID} ---" >> $LOG_FILE
   
    # Clean up the temporary BAM file
    # rm $TMP_FILE
    # conda deactivate

else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] --- ${RUN_ID} ERROR - Step 2 ---" >> $LOG_FILE
    exit 1
fi

# # Step 3- Indexing 
# if [ -f "$FILE" ]; then
#     conda activate danielle
#     gatk BuildBamIndex -I "$FILE"
#     conda deactivate
# else
#     echo "--- ${RUN_ID} ERROR - Step 3 ---" >> $LOG_FILE
# fi

