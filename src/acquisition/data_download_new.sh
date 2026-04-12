#!/usr/bin/env bash

# Get project root from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"

OUTPUT_DIR="${PROJECT_ROOT}/data/raw/fastq/all_samples"
mkdir -p "$OUTPUT_DIR"

# Example FASTQ downloads
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/054/SRR28218954/SRR28218954_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218954_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/054/SRR28218954/SRR28218954_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218954_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/049/SRR28218949/SRR28218949_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218949_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/049/SRR28218949/SRR28218949_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218949_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/053/SRR28218953/SRR28218953_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218953_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/053/SRR28218953/SRR28218953_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218953_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/050/SRR28218950/SRR28218950_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218950_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/050/SRR28218950/SRR28218950_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218950_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/051/SRR28218951/SRR28218951_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218951_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/051/SRR28218951/SRR28218951_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218951_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/052/SRR28218952/SRR28218952_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218952_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/052/SRR28218952/SRR28218952_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218952_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/048/SRR28218948/SRR28218948_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218948_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/048/SRR28218948/SRR28218948_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218948_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/045/SRR28218945/SRR28218945_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218945_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/045/SRR28218945/SRR28218945_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218945_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/047/SRR28218947/SRR28218947_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218947_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/047/SRR28218947/SRR28218947_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218947_2.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/046/SRR28218946/SRR28218946_1.fastq.gz -o "${OUTPUT_DIR}/SRR28218946_1.fastq.gz"
curl -L ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR282/046/SRR28218946/SRR28218946_2.fastq.gz -o "${OUTPUT_DIR}/SRR28218946_2.fastq.gz"
