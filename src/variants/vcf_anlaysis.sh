#!/bin/bash

# Get project root from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/../../" && pwd )"

VCF_FOLDER="${PROJECT_ROOT}/data/processed/variants/filtered"
EXT=".vcf.gz"
OUTPUT_FILE="${PROJECT_ROOT}/data/processed/variants/qc/vcf_stats_0.5.txt"

# AWK Logic:
# 1. Skip headers (starting with #).
# 2. Split column 10 by ':', then the AF field by ','.
# 3. For each AF value:
#    - Convert it to a number.
#    - Find which bin (0-9) it belongs to.
#    - Handle the 1.0 edge case (put it in the 0.9-1.0 bin).
#    - Increment the counter for the correct bin in the 'bins' array.
# 4. At the end of the file, print the counts for all 10 bins.
AWK_LOGIC='
/^#/ {next} 
{
    split($10, format_fields, ":")
    af_string = format_fields[3]
    
    n_afs = split(af_string, af_values, ",")
    
    for (i=1; i<=n_afs; i++) {
        af = af_values[i]
        if (af == "." || af == "") continue # Skip missing values
        
        af_num = af + 0 # Convert to number

        bin_index = 9 # Default to the last bin (for 1.0)
        if (af_num < 1.0) {
            bin_index = int(af_num * 10) # 0.0-0.999...
        }
        
        bins[bin_index]++
    }
}
END { 
    print "--- AF Distribution ---"
    for (b=0; b<=9; b++) {
        # awk will treat non-existent bins[b] as 0
        printf "%.1f - %.1f: %d\n", b/10.0, (b+1)/10.0, bins[b]
    }
}
'

# 1. Clear (overwrite) the old output file to start fresh
> "$OUTPUT_FILE"

for file in "$VCF_FOLDER"/*"$EXT"; do
  if [ -f "$file" ]; then 
    # echo "Processing file: $file" # This prints to your terminal
    
    # # 2. Write the filename to the output file
    echo "File: $file" >> "$OUTPUT_FILE" 
    
    # 3. Run zcat and awk, and append the output to the results file
    zcat "${file}" | awk "$AWK_LOGIC" >> "$OUTPUT_FILE"

    # 4. Add a separator line in the output file
    echo "=========================================" >> "$OUTPUT_FILE"
  fi
done

echo "Processing finished. Results saved to: $OUTPUT_FILE"