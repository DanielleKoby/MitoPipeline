#!/bin/bash

########################
# - GENERAL SETTINGS - #
########################

#SBATCH --job-name=mito_alignment
#SBATCH --partition=cpu-elbo
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=30
#SBATCH --mail-type=ALL,TIME_LIMIT_80
#SBATCH --time=13-00:00
#SBATCH --output=slurm_logs/slurm.%A.%a.out
#SBATCH --array=0-979%10   # <-- adjust automatically below if you want

########################
# ------- JOBS ------- #
########################

# Get project root from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"

PATH_TO_SAMPLES="${PROJECT_ROOT}/data/raw/metadata/srr_list.txt"
# Read all non-empty lines from the file into a bash array
mapfile -t SAMPLES < <(awk 'NF' ${PATH_TO_SAMPLES})

# Pick the sample for this task (0-based indexing)
SAMPLE="${SAMPLES[$SLURM_ARRAY_TASK_ID]}"

echo "Processing sample: $SAMPLE"
srun bash preprocessing_single_sample.sh $SAMPLE 