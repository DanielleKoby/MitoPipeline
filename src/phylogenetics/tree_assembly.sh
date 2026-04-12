#!/bin/bash
TAKE_NUM=$1

# Source tool configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"
source "${PROJECT_ROOT}/tools/tool_paths.config"

source "${CONDA_INIT}"

# Step 1- Data preprocessing for tree creation using W-IQ-TREE)
conda deactivate
conda activate alisa

CONSENSUS_DIR="${PROJECT_ROOT}/data/processed/consensus/fasta"
TREES_DIR="${PROJECT_ROOT}/data/processed/consensus/iqtree_output"

# First time execution - combining all .fa files and aligning using mafft msa method - converts all bases to lowercase if dna (and not amino acids etc.)
# Combined fasta creation for the use of iqtree
COMB_FASTA="${TREES_DIR}/comb_consensus.fa"
MSA_CONSENSUS="${TREES_DIR}/msa_consensus_clean_headers.fa"
NUM_OF_FASTAS=$(ls "${CONSENSUS_DIR}"/*.fa | wc -l)

# if [ ! -f "$COMB_FASTA" ]; then
#     touch "$COMB_FASTA"
#     echo "Combining ${NUM_OF_FASTAS} consensus samples."

#     for filename in "${CONSENSUS_DIR}"/*.fa; do
#         BASE_NAME=$(basename "$filename")
#         NEW_ID=$(echo "$BASE_NAME" | sed 's/\.fa$//')        
#         echo ">$NEW_ID" >> "$COMB_FASTA"
#         grep -v "^>" "$filename" >> "$COMB_FASTA"        
#     done
# else
#     echo "File already exists."
# fi


# echo "---"
# echo "Combination complete. Output saved to $COMB_FASTA"

# echo "MSA start"
# mafft --auto "${COMB_FASTA}" > "${MSA_CONSENSUS}"
# echo "MSA ended"

# Step 6 - iqtree execution - need to review all optional params, used defualt ones

iqtree -s "${MSA_CONSENSUS}" -m TN+F+I+G4 -nt AUTO -redo