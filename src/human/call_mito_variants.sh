#!/bin/bash

# ============================================================================
# HUMAN MITOCHONDRIAL VARIANT CALLING & CONSENSUS
# ============================================================================
# This script is designed to run in Docker. To execute in Docker:
#
# REQUIREMENTS:
#   - Docker image must contain: gatk, bcftools, samtools, bgzip
#   - Tools expected at: /opt/conda/bin/
#   - Input BAMs from prep_mito.sh already present
#
# MOUNT POINTS (required):
#   /pipeline     <- Project directory (MitoPipeline-main)
#   /studies      <- External data (MitoPipeline folder with references)
#
# EXECUTION:
  docker run --rm \
    -v /home/ec2-user/studies:/studies \
    -v /home/ec2-user/studies/MitoPipeline/MitoPipeline-main10:/pipeline \
    -v /home/ec2-user/pipeline_logs:/pipeline/data/human/qc/logs \
    -w /pipeline \
    mito_pipeline_env:v1 bash src/human/call_mito_variants.sh 00114249-518b
#
# ============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

SAMPLE_ID=$1

# ============================================================================
# ENVIRONMENT SETUP FOR DOCKER
# ============================================================================

# In Docker, use fixed mount points
PROJECT_ROOT="/pipeline"
EXTERNAL_DATA_ROOT="/studies"

# Tool paths (Docker conda environment)
GATK_PATH="/opt/conda/bin/gatk"
JAVA_HOME="/opt/conda"

# Verify tools exist
if [ ! -f "$GATK_PATH" ]; then
    echo "ERROR: GATK not found at $GATK_PATH"
    exit 1
fi

if ! command -v bcftools &> /dev/null; then
    echo "ERROR: bcftools not found in PATH"
    exit 1
fi

# ============================================================================
# PATHS - Input (from completed prep_mito.sh)
# ============================================================================

DATA_ROOT="${PROJECT_ROOT}/data"
INPUT_BAM="${DATA_ROOT}/human/processed/alignment/deduplicated/${SAMPLE_ID}.bam"

# Reference files (from mounted /studies)
REF_FASTA="${EXTERNAL_DATA_ROOT}/MitoPipeline/ncbi_dataset/ncbi_dataset/data/GCF_000001405.26/GCF_000001405.26_GRCh38_genomic.fna"
MITO_REF_CLEAN="${EXTERNAL_DATA_ROOT}/MitoPipeline/NC_012920.1.fasta"

# ============================================================================
# PATHS - Output (fixed version: v_01)
# ============================================================================

VERSION="01"

# Output directories
RAW_DIR="${DATA_ROOT}/human/processed/variants/raw"
VARIANTS_VERSION_DIR="${DATA_ROOT}/human/processed/variants/v_${VERSION}"
FILTERED_DIR="${VARIANTS_VERSION_DIR}/filtered"
FINAL_DIR="${VARIANTS_VERSION_DIR}/final"
CONSENSUS_VERSION_DIR="${DATA_ROOT}/human/processed/consensus/v_${VERSION}"
CONSENSUS_DIR="${CONSENSUS_VERSION_DIR}/fasta"

# Output files
RAW_VCF="${RAW_DIR}/${SAMPLE_ID}.raw_mito_calls.vcf.gz"
FILTERED_VCF="${FILTERED_DIR}/${SAMPLE_ID}.vcf.gz"
FINAL_VCF="${FINAL_DIR}/${SAMPLE_ID}.vcf.gz"
CONSENSUS_FILE="${CONSENSUS_DIR}/${SAMPLE_ID}.fa"

# Create output directories
mkdir -p "$RAW_DIR" "$FILTERED_DIR" "$FINAL_DIR" "$CONSENSUS_DIR"

# Logging
LOGS="${DATA_ROOT}/human/qc/logs"
LOG_FILE="${LOGS}/${SAMPLE_ID}_vcf.log"
mkdir -p "$LOGS"

# ============================================================================
# RESUMABLE EXECUTION - Check if sample already processed
# ============================================================================
if [ -f "$CONSENSUS_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SKIPPED: $SAMPLE_ID (consensus already exists)" >> "$LOG_FILE"
    exit 0
fi

# ============================================================================
# AUTO-CLEANUP - Remove partial files from interrupted runs
# ============================================================================
cleanup_partial_files() {
    local search_dirs=("$RAW_DIR" "$FILTERED_DIR" "$FINAL_DIR" "$CONSENSUS_DIR")

    for dir in "${search_dirs[@]}"; do
        if [ -d "$dir" ]; then
            local removed_in_dir
            removed_in_dir=$(find "$dir" -type f -name "${SAMPLE_ID}*" \
                \( -name "*.parts" -o -name "*.tmp.*" -o -name "*~" \) \
                -print -delete 2>/dev/null || true)

            if [ -n "$removed_in_dir" ]; then
                {
                    echo "[$(date '+%Y-%m-%d %H:%M:%S')] CLEANUP: Removed partial files in $dir"
                    echo "$removed_in_dir"
                } >> "$LOG_FILE"
            fi
        fi
    done
}

if [ "${PIPELINE_ENABLE_PARTIAL_CLEANUP:-0}" = "1" ]; then
    cleanup_partial_files
fi
echo "[$(date '+%Y-%m-%d %H:%M:%S')] SAMPLE START: $SAMPLE_ID" >> "$LOG_FILE"

# ============================================================================
# HUMAN MITOCHONDRIAL PARAMETERS
# ============================================================================
MITO_NAME="MT"
MITO_THRESHOLD=0.5  # AF threshold for consensus variants

# ============================================================================
# VALIDATE INPUTS
# ============================================================================
if [ ! -f "$INPUT_BAM" ]; then
    echo "ERROR: Input BAM file not found: $INPUT_BAM" | tee -a "$LOG_FILE"
    exit 1
fi

if [ ! -f "$REF_FASTA" ]; then
    echo "ERROR: Reference FASTA not found: $REF_FASTA" | tee -a "$LOG_FILE"
    exit 1
fi

if [ ! -f "$MITO_REF_CLEAN" ]; then
    echo "ERROR: Clean mitochondrial reference not found: $MITO_REF_CLEAN" | tee -a "$LOG_FILE"
    exit 1
fi

# ============================================================================
# PRE-PROCESSING - Ensure reference files are indexed
# ============================================================================
echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP 0: Verifying and indexing reference files" >> "$LOG_FILE"

for ref in "$REF_FASTA" "$MITO_REF_CLEAN"; do
  if [ -f "$ref" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing: $ref" | tee -a "$LOG_FILE"
    samtools faidx "$ref" && \
    $GATK_PATH CreateSequenceDictionary -R "$ref"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: File not found at $ref" | tee -a "$LOG_FILE"
    exit 1
  fi
done

# ============================================================================
# Step 1 - Variants calling with Mutect2
# ============================================================================
#
echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP 1: Running Mutect2 variant calling" >> "$LOG_FILE"
$GATK_PATH Mutect2 \
    -R "$MITO_REF_CLEAN" \
    -I "$INPUT_BAM" \
    -O "$RAW_VCF" \
    -L "$MITO_NAME" \
    --mitochondria-mode \
    --max-reads-per-alignment-start 50 \
    --max-mnp-distance 1 \
    --annotation StrandBiasBySample

# ============================================================================
# Step 2 - Filter Mutect Calls
# ============================================================================
echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP 2: Filtering Mutect2 calls" >> "$LOG_FILE"

$GATK_PATH FilterMutectCalls \
    -V "$RAW_VCF" \
    -O "$FILTERED_VCF" \
    -R "$MITO_REF_CLEAN" \
    --mitochondria-mode

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Filtering complete: $FILTERED_VCF" >> "$LOG_FILE"

# ============================================================================
# Step 3 - Apply custom AF and position filters
# ============================================================================
# Filter for: PASS variants, AF >= 0.5, DP >= 10
# Human MT genome is 16569 bp (includes edges)
#
echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP 3: Applying custom filters (AF >= $MITO_THRESHOLD, DP >= 10)" >> "$LOG_FILE"

bcftools view -r "$MITO_NAME" "$FILTERED_VCF" |
awk -F '\t' '
/^#/ { print; next }
{
    n = split($9, h, ":")
    afi = dpi = 0
    for(i=1;i<=n;i++) {
        if(h[i]=="AF") afi = i
        if(h[i]=="DP") dpi = i
    }
    if(afi==0 || dpi==0) next
    split($10, f, ":")
    af = f[afi] + 0; dp = f[dpi] + 0
    if($7 == "PASS" && af >= '$MITO_THRESHOLD' && dp >= 10) print
}' | bgzip -c > "$FINAL_VCF"

bcftools index -c "$FINAL_VCF"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Filtered variants: $FINAL_VCF" >> "$LOG_FILE"

# ============================================================================
# Step 4 - Create consensus sequence from filtered variants
# ============================================================================
echo "[$(date '+%Y-%m-%d %H:%M:%S')] STEP 4: Generating consensus sequence" >> "$LOG_FILE"

bcftools consensus \
    -f "$MITO_REF_CLEAN" "$FINAL_VCF" > "$CONSENSUS_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Consensus complete: $CONSENSUS_FILE" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === SAMPLE COMPLETE: $SAMPLE_ID ===" >> "$LOG_FILE"
