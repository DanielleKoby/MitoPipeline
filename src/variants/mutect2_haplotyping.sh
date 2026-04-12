#!/bin/bash
SAMPLE_ID=$1

# Source tool configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"
source "${PROJECT_ROOT}/tools/tool_paths.config"

REF_FASTA="${PROJECT_ROOT}/reference/GCA_011100685.1_UU_Cfam_GSD_1.0_genomic.fna"
INPUT_BAM="${PROJECT_ROOT}/data/processed/alignment/deduplicated/${SAMPLE_ID}.bam"
BED_FILE="${SCRIPT_DIR}/coords_to_extract_only_mito.bed"

MITO_NAME="CM022001.1"
MITO_READ_LEN=150
MITO_SEQ_LEN=16728
ROTATION_STRAT=$MITO_READ_LEN
ROTATION_END=$((MITO_SEQ_LEN - MITO_READ_LEN))

# Output files
OUTPUT_DIR="${PROJECT_ROOT}/data/processed/variants/raw"
RAW_VCF="${OUTPUT_DIR}/${SAMPLE_ID}.raw_mito_calls.vcf.gz"
FINAL_VCF="${OUTPUT_DIR}/${SAMPLE_ID}.final_mito_calls.vcf.gz"
FILTERED_DIR="${PROJECT_ROOT}/data/processed/variants/filtered"
FILTERED_VCF="${FILTERED_DIR}/${SAMPLE_ID}.filtered_mito_calls.vcf.gz"
CONSENSUS_DIR="${PROJECT_ROOT}/data/processed/consensus/fasta"
CONSENSUS_FILE="${CONSENSUS_DIR}/${SAMPLE_ID}.fa"
MITO_REF_CLEAN="${PROJECT_ROOT}/reference/clean_mito_ref.fna"

source "${CONDA_INIT}"

# Parameters
THRESHOLD=0.4

# conda deactivate
# conda activate danielle
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

# # Step 2 - Filter Mutect Calls
# echo "Filtering calls for $SAMPLE_ID..."
# gatk FilterMutectCalls \
#     -V "$RAW_VCF" \
#     -O "$FINAL_VCF" \
#     -R "$REF_FASTA" \
#     --mitochondria-mode

# echo "Done. Final results are in $FINAL_VCF"

# Step 3 danielle v- 
# Filter Mutect Calls (with af > 0.5) - using our own filterig script since --min-allele-fraction of FilterMutectCalls (GATK) doesn't work
# conda deactivate
# conda activate alisa

# echo "Filtering calls for $SAMPLE_ID..."

# zcat "$RAW_VCF" | \
# awk -v thresh="$THRESHOLD" -v R_START="$ROTATION_STRAT" -v R_END="$ROTATION_END" '
# BEGIN {
#     FS = "\t"
#     OFS = "\t"
# }
# /^##/ {
#     print $0;
#     next;
# }

# /^#CHROM/ {
#     print $0;
#     next;
# }

# $1 == "CM022001.1" {
#     split($10, sample_parts, ":");
#     af= sample_parts[3];
#     split(af, values, ",");

#     af_sum = 0;

#     for (i = 1; i <= length(values); i++) {
#         af_sum += values[i];
#     }

# }
# ' | bgzip -c > "$FILTERED_VCF" \

conda deactivate
conda activate danielle

# Step 3- Alisa's v
bcftools view -r CM022001.1 "$RAW_VCF" |
awk -F '\t' '
/^#/ { print; next }
{

n = split($9, h, ":")
afi = 0
for(i=1;i<=n;i++){
if(h[i]=="AF"){ afi = i; break }
}
if(afi==0) next # no AF field
split($10, f, ":")

af = f[afi] + 0 # cast to number
if(af >= 0.4 && $2 > 200 && $2 < 16578) {
print
}
}
' | bgzip -c > "$FILTERED_VCF"


bcftools index -c "$FILTERED_VCF"

# Step 4 - creating consensus mito

echo "STARTING CONSENSUS PROCESSS for $SAMPLE_ID..."

bcftools consensus \
    -f "$MITO_REF_CLEAN" "$FILTERED_VCF" > "$CONSENSUS_FILE"
