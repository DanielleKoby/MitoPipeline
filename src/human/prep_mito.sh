#!/bin/bash

# ============================================================================
# DOCKER SETUP NOTES
# ============================================================================
# This script is designed to run inside a Docker container.
#
# REQUIREMENTS:
#   - Docker image must contain: gatk, samtools, bcftools, Java 17+
#   - Tools expected at: /opt/conda/bin/
#
# MOUNT POINTS (required):
#   /pipeline     <- Project directory (MitoPipeline-main)
#   /studies      <- External data (studies/human_genetics_bulk/reads/bam, studies/MitoPipeline)
#
# EXAMPLE DOCKER RUN:
#   docker run --rm \
#     -v /home/ec2-user/studies:/studies \
#     -v /home/ec2-user/studies/MitoPipeline/MitoPipeline-main:/pipeline \
#     -v /home/ec2-user/output:/output \
#
# ============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# ============================================================================
# ENVIRONMENT SETUP FOR DOCKER
# ============================================================================

# In Docker, use fixed mount points
PROJECT_ROOT="/pipeline"
EXTERNAL_DATA_ROOT="/studies"
OUTPUT_ROOT="/output"

# Tool paths (Docker conda environment)
GATK_PATH="/opt/conda/bin/gatk"
JAVA_HOME="/opt/conda"

# Verify tools exist
if [ ! -f "$GATK_PATH" ]; then
    echo "ERROR: GATK not found at $GATK_PATH"
    exit 1
fi

if ! command -v samtools &> /dev/null; then
    echo "ERROR: samtools not found in PATH"
    exit 1
fi

SAMPLE_ID=$1
NUM_OF_THREADS=40

# ============================================================================
# PATHS - Input (read-only, external data mounted at /studies)
# ============================================================================

# Raw BAM input directory (from mounted /studies)
RAW_BAM_DIR="${EXTERNAL_DATA_ROOT}/human_genetics_bulk/reads/bam"
INPUT_BAM="${RAW_BAM_DIR}/gencove__${SAMPLE_ID}.bam"

# Reference FASTA (from mounted /studies)
REF_FASTA="${EXTERNAL_DATA_ROOT}/MitoPipeline/ncbi_dataset/ncbi_dataset/data/GCF_000001405.26/GCF_000001405.26_GRCh38_genomic.fna"

# ============================================================================
# PATHS - Output (created in MitoPipeline-main/data)
# ============================================================================

# Data root directory
DATA_ROOT="${OUTPUT_ROOT}/data"

# Create data directories if they don't exist
mkdir -p "$DATA_ROOT"

# Output directories (auto-created)
TMP_DIR="${DATA_ROOT}/human/processed/temp"
MITO_EXTRACTED_DIR="${DATA_ROOT}/human/processed/alignment/mito_extracted"
RG_DIR="${DATA_ROOT}/human/processed/alignment/read_groups"
SORTED_DIR="${DATA_ROOT}/human/processed/alignment/sorted"
DUPS_REMOVED="${DATA_ROOT}/human/processed/alignment/deduplicated"
METRICS_DIR="${DATA_ROOT}/human/qc/dedup_metrics"
LOGS="${DATA_ROOT}/human/qc/logs"
LOG_FILE="${LOGS}/${SAMPLE_ID}_prep.log"
CONFIG_LOG="${LOGS}/pipeline_config.log"

mkdir -p "$MITO_EXTRACTED_DIR" "$RG_DIR" "$SORTED_DIR" "$DUPS_REMOVED" "$METRICS_DIR" "$LOGS" "$TMP_DIR"

# ============================================================================
# CONFIGURATION LOG - Write once on first sample
# ============================================================================

if [ ! -f "$CONFIG_LOG" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] === PIPELINE CONFIGURATION ===" > "$CONFIG_LOG"
    echo "Project Root: $PROJECT_ROOT" >> "$CONFIG_LOG"
    echo "External Data Root: $EXTERNAL_DATA_ROOT" >> "$CONFIG_LOG"
    echo "GATK Path: $GATK_PATH" >> "$CONFIG_LOG"
    echo "Java Home: $JAVA_HOME" >> "$CONFIG_LOG"
    echo "Reference FASTA: $REF_FASTA" >> "$CONFIG_LOG"
    echo "Input BAM Directory: ${RAW_BAM_DIR}" >> "$CONFIG_LOG"
    echo "============================================" >> "$CONFIG_LOG"
fi

# ============================================================================
# VALIDATION - Check that input files and directories exist
# ============================================================================

if [ ! -f "$INPUT_BAM" ]; then
    echo "ERROR: Input BAM file not found: $INPUT_BAM"
    exit 1
fi

if [ ! -f "$REF_FASTA" ]; then
    echo "ERROR: Reference FASTA not found: $REF_FASTA"
    exit 1
fi

# Log sample start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] SAMPLE START: $SAMPLE_ID" >> "$LOG_FILE"
echo "Input BAM: $INPUT_BAM" >> "$LOG_FILE"

# ============================================================================
# STEP A - Extract mitochondrial reads (MT chromosome only)
# ============================================================================

EXTRACTED_FILE="${MITO_EXTRACTED_DIR}/${SAMPLE_ID}.bam"

if [ -f "$INPUT_BAM" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP A: Extracting MT reads" >> "$LOG_FILE"
    
    # Extract only MT chromosome, retaining header
    samtools view -b -h "$INPUT_BAM" MT > "$EXTRACTED_FILE"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP A: Complete" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR STEP A: Input BAM not found: ${INPUT_BAM}" >> "$LOG_FILE"
    exit 1
fi

# ============================================================================
# STEP B - Add Read Groups using GATK
# ============================================================================

RG_BAM_INPUT="$EXTRACTED_FILE"
RG_BAM_OUTPUT="${RG_DIR}/${SAMPLE_ID}.bam"

if [ -f "$RG_BAM_INPUT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP B: Adding read groups" >> "$LOG_FILE"
    
    # Extract sample name from filename (e.g., "00114249-518b" from "gencove__00114249-518b.bam")
    RGSM="${SAMPLE_ID}"
    RGLB="LIB_1"
    RGPL="ILLUMINA"
    RGPU="${SAMPLE_ID}"
        
    # Run GATK AddOrReplaceReadGroups
    "${GATK_PATH}" AddOrReplaceReadGroups \
        -I "$RG_BAM_INPUT" \
        -O "$RG_BAM_OUTPUT" \
        --RGLB "$RGLB" \
        --RGPL "$RGPL" \
        --RGSM "$RGSM" \
        --RGPU "$RGPU"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP B: Complete" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR STEP B: Extracted BAM not found: ${RG_BAM_INPUT}" >> "$LOG_FILE"
    exit 1
fi

# ============================================================================
# STEP B.5 - Sort BAM file (required for MarkDuplicatesSpark efficiency)
# ============================================================================

UNSORTED_BAM="$RG_BAM_OUTPUT"
SORTED_BAM="${SORTED_DIR}/${SAMPLE_ID}.bam"

if [ -f "$UNSORTED_BAM" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP B.5: Sorting BAM" >> "$LOG_FILE"
    
    samtools sort -@ "$NUM_OF_THREADS" -T "${SORTED_DIR}/${SAMPLE_ID}.sort.tmp" -o "$SORTED_BAM" "$UNSORTED_BAM"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP B.5: Complete" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR STEP B.5: RG BAM not found: ${UNSORTED_BAM}" >> "$LOG_FILE"
    exit 1
fi

# ============================================================================
# STEP C - Mark Duplicates (Deduplication)
# ============================================================================

DEDUP_INPUT="$SORTED_BAM"
DEDUP_OUTPUT="${DUPS_REMOVED}/${SAMPLE_ID}.bam"
DEDUP_METRICS="${METRICS_DIR}/${SAMPLE_ID}.txt"

if [ -f "$DEDUP_INPUT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP C: Marking duplicates" >> "$LOG_FILE"
    
    "${GATK_PATH}" MarkDuplicatesSpark \
        --java-options '-DGATK_STACKTRACE_ON_USER_EXCEPTION=true' \
        -I "$DEDUP_INPUT" \
        -O "$DEDUP_OUTPUT" \
        -M "$DEDUP_METRICS" \
        --conf "spark.executor.cores=${NUM_OF_THREADS}" \
        --conf "spark.local.dir=${DUPS_REMOVED}" \
        --tmp-dir "$TMP_DIR"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP C: Complete" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR STEP C: RG BAM not found: ${DEDUP_INPUT}" >> "$LOG_FILE"
    exit 1
fi

# ============================================================================
# STEP D - Index BAM file for downstream processing (Mutect2 compatibility)
# ============================================================================

if [ -f "$DEDUP_OUTPUT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP D: Indexing BAM" >> "$LOG_FILE"
    
    gatk BuildBamIndex -I "$DEDUP_OUTPUT"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP D: Complete" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR STEP D: Deduplicated BAM not found: ${DEDUP_OUTPUT}" >> "$LOG_FILE"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] SAMPLE COMPLETE: ${SAMPLE_ID}" >> "$LOG_FILE"
