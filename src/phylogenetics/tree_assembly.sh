#!/bin/bash

# Source tool configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"
REPO_PROJECT_ROOT="$PROJECT_ROOT"
source "${PROJECT_ROOT}/tools/tool_paths.config"
# Restore repository root; tool_paths.config may redefine PROJECT_ROOT
PROJECT_ROOT="$REPO_PROJECT_ROOT"

source "${CONDA_INIT}"

conda deactivate
conda activate alisa

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

echo "-----------------------------------"

# --- STEP 3: Phylogenetic Tree (IQ-TREE) ---
echo "Starting IQ-TREE..."
# Using -redo forces IQ-TREE to overwrite previous runs if you are tweaking parameters
# Updated April 20th - use MFP ModelFinder Plus to automatically select the best model, and use more rate categories (G4) for better fit to mito data
iqtree -s "${CLEAN_MSA}" -m MFP -nt AUTO -redo

echo "Pipeline complete!"