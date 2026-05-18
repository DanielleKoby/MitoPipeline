#!/bin/bash

# ============================================================================
# DOCKER SETUP NOTES
# ============================================================================
# This script is designed to run in Docker. To execute in Docker:
#
# 1. Mount the project: -v /path/to/MitoPipeline-main:/pipeline
# 2. Set working directory: -w /pipeline
# 3. Ensure tool_paths.config is available at: /pipeline/tools/tool_paths.config
#    (Use tool_paths.docker.config as template)
# 4. Required tools in Docker image:
#    - gatk (GATK 4.x)
#    - samtools
#    - bcftools (with bgzip)
#    - conda (with "danielle" environment pre-created)
#    - Java 17+
#
# Example Docker run:
#   docker run -v /path/to/data:/pipeline -w /pipeline \
#     my-docker-image bash src/human/call_mito_variants.sh 00114249-518b
#
# ============================================================================

SAMPLE_ID=$1

# Source tool configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"
REPO_PROJECT_ROOT="$PROJECT_ROOT"
source "${PROJECT_ROOT}/tools/tool_paths.config"
# Restore repository root; tool_paths.config may redefine PROJECT_ROOT
PROJECT_ROOT="$REPO_PROJECT_ROOT"

# ============================================================================
# DOCKER ENVIRONMENT DETECTION
# ============================================================================
# When running in Docker with /output mount, preprocessed BAMs are in /output/data
# Otherwise, use the project directory structure
if [ -d "/output/data" ]; then
    DATA_ROOT="/output/data"
else
    DATA_ROOT="${PROJECT_ROOT}/data"
fi

# Reference files
REF_FASTA="${PROJECT_ROOT}/reference/human/ncbi_dataset/ncbi_dataset/data/GCF_000001405.26/GCF_000001405.26_GRCh38_genomic.fna"
INPUT_BAM="${DATA_ROOT}/human/processed/alignment/deduplicated/${SAMPLE_ID}.bam"

# Human mitochondrial parameters
MITO_NAME="MT"
MITO_READ_LEN=150
MITO_SEQ_LEN=16569
ROTATION_STRAT=$MITO_READ_LEN
ROTATION_END=$((MITO_SEQ_LEN - MITO_READ_LEN))

# Atomic version detection for parallel Slurm tasks (all tasks in one job use same version)
get_version_atomic() {
    local base_dir="$1"
    local lock_file="${base_dir}/.version_lock"
    local version_cache="${base_dir}/.version_cache"
    (
        flock -x 200 || { echo "ERROR: Cannot acquire lock"; exit 1; }
        if [ -f "$version_cache" ]; then
            cat "$version_cache"
        else
            local max_v=0
            [ -d "$base_dir" ] && for d in "${base_dir}/v_"*; do
                [ -d "$d" ] || continue
                v=$(basename "$d" | sed "s/v_//")
                [[ "$v" =~ ^[0-9]+$ ]] && (( v > max_v )) && max_v=$v
            done
            next_v=$((max_v + 1))
            printf "%02d" "$next_v" | tee "$version_cache"
        fi
    ) 200>"$lock_file"
}
FILTERED_VERSION=$(get_version_atomic "${DATA_ROOT}/human/processed/variants")
CONSENSUS_VERSION=$(get_version_atomic "${DATA_ROOT}/human/processed/consensus")
(( 10#$FILTERED_VERSION > 10#$CONSENSUS_VERSION )) && CONSENSUS_VERSION=$FILTERED_VERSION || FILTERED_VERSION=$CONSENSUS_VERSION

# Output files
RAW_DIR="${DATA_ROOT}/human/processed/variants/raw"
VARIANTS_VERSION_DIR="${DATA_ROOT}/human/processed/variants/v_${FILTERED_VERSION}"
FILTERED_DIR="${VARIANTS_VERSION_DIR}/filtered"
FINAL_DIR="${VARIANTS_VERSION_DIR}/final"
CONSENSUS_VERSION_DIR="${DATA_ROOT}/human/processed/consensus/v_${CONSENSUS_VERSION}"
CONSENSUS_DIR="${CONSENSUS_VERSION_DIR}/fasta"

RAW_VCF="${RAW_DIR}/${SAMPLE_ID}.raw_mito_calls.vcf.gz"
FILTERED_VCF="${FILTERED_DIR}/${SAMPLE_ID}.vcf.gz"
FINAL_VCF="${FINAL_DIR}/${SAMPLE_ID}.vcf.gz"

CONSENSUS_FILE="${CONSENSUS_DIR}/${SAMPLE_ID}.fa"
MITO_REF_CLEAN="${PROJECT_ROOT}/reference/human/NC_012920.1.fasta"

# Create output directories if they do not exist
mkdir -p "$RAW_DIR" "$FILTERED_DIR" "$FINAL_DIR" "$CONSENSUS_DIR"

# Tools are in /opt/conda/bin/ in the Docker image
export PATH="/opt/conda/bin:${PATH}"

# Parameters
THRESHOLD=0.5

# ============================================================================
# Step 1 - Variants calling with Mutect2
# ============================================================================
# Uncomment the following to run Mutect2. This step can be computationally
# intensive. If Mutect2 has already been run for this sample, skip this step.
# 
# echo "Running Mutect2 for $SAMPLE_ID..."
# gatk Mutect2 \
#     -R "$REF_FASTA" \
#     -I "$INPUT_BAM" \
#     -O "$RAW_VCF" \
#     -L "$MITO_NAME" \
#     --mitochondria-mode \
#     --max-reads-per-alignment-start 50 \
#     --max-mnp-distance 1 \
#     --annotation StrandBiasSample

# ============================================================================
# Step 2 - Filter Mutect Calls
# ============================================================================
echo "Filtering calls for $SAMPLE_ID..."
gatk FilterMutectCalls \
    -V "$RAW_VCF" \
    -O "$FILTERED_VCF" \
    -R "$REF_FASTA" \
    --mitochondria-mode

echo "Done filtering. Results in $FILTERED_VCF"

# ============================================================================
# Step 3 - Apply custom AF and position filters
# ============================================================================
# Filter for: PASS variants, AF >= 0.5, DP >= 10
# Note: Human MT genome is 16569 bp (includes edges)
#
bcftools view -r MT "$FILTERED_VCF" |
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
    if($7 == "PASS" && af >= 0.5 && dp >= 10) print
}' | bgzip -c > "$FINAL_VCF"

bcftools index -c "$FINAL_VCF"

# ============================================================================
# Step 4 - Create consensus sequence from filtered variants
# ============================================================================

echo "STARTING CONSENSUS PROCESS for $SAMPLE_ID..."

bcftools consensus \
    -f "$MITO_REF_CLEAN" "$FINAL_VCF" > "$CONSENSUS_FILE"

echo "Consensus sequence written to: $CONSENSUS_FILE"
