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
#   /pipeline     <- Project directory (MitoPipeline-main10)
#   /studies      <- External data (studies/human_genetics_bulk/reads/bam, studies/MitoPipeline)
#
# EXAMPLE DOCKER RUN:
    # docker run --rm \
    # -v /home/ec2-user/studies:/studies \
    # -v /home/ec2-user/studies/MitoPipeline/MitoPipeline-main10:/pipeline \
    # -w /pipeline \
    # mito_pipeline_env:v1 bash src/human/tree_assembly.sh 
# ============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# ============================================================================
# ENVIRONMENT SETUP FOR DOCKER
# ============================================================================

# In Docker, use fixed mount points
PROJECT_ROOT="/pipeline"
EXTERNAL_DATA_ROOT="/studies"

# Tool paths (Docker conda environment)
GATK_PATH="/opt/conda/bin/gatk"
JAVA_HOME="/opt/conda"
IQTREE_PATH="/opt/conda/bin/iqtree"

# Verify tools exist
if [ ! -f "$IQTREE_PATH" ]; then
    echo "ERROR: IQTREE not found at $IQTREE_PATH"
    exit 1
fi

if ! command -v samtools &> /dev/null; then
    echo "ERROR: samtools not found in PATH"
    exit 1
fi
if ! command -v bcftools &> /dev/null; then
    echo "ERROR: bcftools not found in PATH"
    exit 1
fi

# Mitochondrial reference FASTA (rCRS - Revised Cambridge Reference Sequence)
MITO_REF="${EXTERNAL_DATA_ROOT}/MitoPipeline/NC_012920.1.fasta"

# ============================================================================
# PATHS - Output (created in MitoPipeline-main10/data)
# ============================================================================

DATA_ROOT="${PROJECT_ROOT}/data"
# Output directories (auto-created)

# Atomic version detection (safe for parallel execution)
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
CONSENSUS_VERSION=$(get_version_atomic "${PROJECT_ROOT}/data/processed/consensus")

CONSENSUS_VERSION_DIR="${PROJECT_ROOT}/data/processed/consensus/v_${CONSENSUS_VERSION}"
CONSENSUS_DIR="${CONSENSUS_VERSION_DIR}/fasta"
TREES_DIR="${CONSENSUS_VERSION_DIR}/iqtree_output"

if [ ! -d "$CONSENSUS_DIR" ]; then
    echo "ERROR: Consensus directory not found: $CONSENSUS_DIR"
    exit 1
fi
if ! find "$CONSENSUS_DIR" -maxdepth 1 -type f -name "*.fa" | grep -q .; then
    echo "ERROR: No .fa files found in $CONSENSUS_DIR. Variant/consensus step may not be complete."
    exit 1
fi

mkdir -p "$TREES_DIR"

# First time execution - combining all .fa files and aligning using mafft msa method - converts all bases to lowercase if dna (and not amino acids etc.)
# Combined fasta creation for the use of iqtree
COMB_FASTA="${TREES_DIR}/comb_consensus.fa"
MSA_CONSENSUS="${TREES_DIR}/msa_consensus.fa"


# --- STEP 1: Combine FASTA files ---
if [ ! -f "$COMB_FASTA" ]; then
    NUM_OF_FASTAS=$(ls "${CONSENSUS_DIR}"/*.fa 2>/dev/null | wc -l)
    echo "Combining ${NUM_OF_FASTAS} consensus samples..."
    for filename in "${CONSENSUS_DIR}"/*.fa; do
        BASE_NAME=$(basename "$filename")
        NEW_ID=$(echo "$BASE_NAME" | sed 's/\.fa$//')        
        
        # Using >> will automatically create the file if it doesn't exist
        echo ">$NEW_ID" >> "$COMB_FASTA"
        grep -v "^>" "$filename" >> "$COMB_FASTA"        
    done
    echo "Combination complete. Output saved to $COMB_FASTA"
else
    echo "Combined FASTA already exists. Skipping combination step."
fi

echo "-----------------------------------"

# --- STEP 2: Multiple Sequence Alignment (MAFFT) ---
if [ ! -f "$MSA_CONSENSUS" ]; then
    echo "Running MAFFT..."
    mafft --auto "${COMB_FASTA}" > "${MSA_CONSENSUS}"
    echo "MSA ended."
else
    echo "MSA file already exists. Skipping MAFFT step."
fi

CLEAN_MSA="${TREES_DIR}/msa_consensus_cleaned.fa"
echo "Cleaning MSA to remove empty sequences..."

awk '
/^>/ {
    if (h != "") {
        if (s ~ /[acgtACGT]/) print block
        else print "Dropped: " h > "/dev/stderr"
    }
    h = $0; s = ""; block = $0; next
}
{
    s = s $0
    block = block "\n" $0
}
END {
    if (h != "") {
        if (s ~ /[acgtACGT]/) print block
        else print "Dropped: " h > "/dev/stderr"
    }
}' "${MSA_CONSENSUS}" > "${CLEAN_MSA}"

echo "Cleaning complete. MSA saved to ${CLEAN_MSA}"

echo "-----------------------------------"

# --- STEP 3: Phylogenetic Tree (IQ-TREE) ---
echo "Starting IQ-TREE..."
# Using -redo forces IQ-TREE to overwrite previous runs if you are tweaking parameters
# Updated April 20th - use MFP ModelFinder Plus to automatically select the best model, and use more rate categories (G4) for better fit to mito data
iqtree -s "${CLEAN_MSA}" -m MFP -nt AUTO -redo

echo "Pipeline complete!"



