#!/bin/bash
SAMPLE_ID=$1

# Source tool configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"
REPO_PROJECT_ROOT="$PROJECT_ROOT"
source "${PROJECT_ROOT}/tools/tool_paths.config"
# Restore repository root; tool_paths.config may redefine PROJECT_ROOT
PROJECT_ROOT="$REPO_PROJECT_ROOT"

REF_FASTA="${PROJECT_ROOT}/reference/GCA_011100685.1_UU_Cfam_GSD_1.0_genomic.fna"
INPUT_BAM="${PROJECT_ROOT}/data/processed/alignment/deduplicated/${SAMPLE_ID}.bam"

MITO_NAME="CM022001.1"
MITO_READ_LEN=150
MITO_SEQ_LEN=16728
ROTATION_STRAT=$MITO_READ_LEN
ROTATION_END=$((MITO_SEQ_LEN - MITO_READ_LEN))

# Output files
RAW_DIR="${PROJECT_ROOT}/data/processed/variants/raw"
FILTERED_DIR="${PROJECT_ROOT}/data/processed/variants/filtered_01"
FINAL_DIR="${PROJECT_ROOT}/data/processed/variants/final_01"
CONSENSUS_DIR="${PROJECT_ROOT}/data/processed/consensus/fasta_01"

RAW_VCF="${RAW_DIR}/${SAMPLE_ID}.raw_mito_calls.vcf.gz"
FILTERED_VCF="${FILTERED_DIR}/${SAMPLE_ID}.vcf.gz"
FINAL_VCF="${FINAL_DIR}/${SAMPLE_ID}.vcf.gz"

CONSENSUS_FILE="${CONSENSUS_DIR}/${SAMPLE_ID}.fa"
MITO_REF_CLEAN="${PROJECT_ROOT}/reference/clean_mito_ref.fna"

# Create output directories if they do not exist
mkdir -p "$RAW_DIR" "$FILTERED_DIR" "$FINAL_DIR" "$CONSENSUS_DIR"

source "${CONDA_INIT}"

# Parameters
THRESHOLD=0.5

conda deactivate
conda activate danielle

# Step 1- Variants calling
# echo "Running Mutect2 for $SAMPLE_ID..."
# gatk Mutect2 \
#     -R "$REF_FASTA" \
#     -I "$INPUT_BAM" \
#     -O "$RAW_VCF" \
#     -L "$MITO_NAME" \
#     --mitochondria-mode \
#     --max-reads-per-alignment-start 50 \
#     --max-mnp-distance 1 \
#     --annotation StrandBiasBySample

# Step 2 - Filter Mutect Calls 
echo "Filtering calls for $SAMPLE_ID..."
gatk FilterMutectCalls \
    -V "$RAW_VCF" \
    -O "$FILTERED_VCF" \
    -R "$REF_FASTA" \
    --mitochondria-mode

echo "Done. Final results are in $FILTERED_VCF"

conda deactivate
conda activate danielle

# # Step 3- Alisa's V
# bcftools view -r CM022001.1 "$FILTERED_VCF" |
# awk -F '\t' '
# /^#/ { print; next }
# {

# n = split($9, h, ":")
# afi = 0
# for(i=1;i<=n;i++){
# if(h[i]=="AF"){ afi = i; break }
# }
# if(afi==0) next # no AF field
# split($10, f, ":")

# af = f[afi] + 0 # cast to number
# if(af >= 0.4 && $2 > 200 && $2 < 16578) {
# print
# }
# }
# ' | bgzip -c > "$FINAL_VCF"

# Step 3- Apply custom AF and position filters
bcftools view -r CM022001.1 "$FILTERED_VCF" |
awk -F '\t' '
/^#/ { print; next }
{
    # Split the FORMAT column (e.g., GT:AD:AF:DP:...)
    n = split($9, h, ":")
    afi = 0; dpi = 0
    
    # Find which position holds the AF and the DP
    for(i=1;i<=n;i++){
        if(h[i]=="AF"){ afi = i }
        if(h[i]=="DP"){ dpi = i }
    }
    
    # If it is missing AF or DP, skip the line
    if(afi==0 || dpi==0) next 
    
    # Split the actual data column for the dog
    split($10, f, ":")
    
    af = f[afi] + 0 # Cast AF to a number
    dp = f[dpi] + 0 # Cast DP to a number
    
    if($7 == "PASS" && af >= 0.5 && dp >= 10 && $2 > 200 && $2 < 16578) {
        print
    }
}
' | bgzip -c > "$FINAL_VCF"

bcftools index -c "$FINAL_VCF"

# Step 4 - creating consensus mito

echo "STARTING CONSENSUS PROCESSS for $SAMPLE_ID..."

bcftools consensus \
    -f "$MITO_REF_CLEAN" "$FINAL_VCF" > "$CONSENSUS_FILE"
