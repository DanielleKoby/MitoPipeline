#!/usr/bin/env python3

# ============================================================================
# DOCKER SETUP NOTES
# ============================================================================
# This script is designed to run inside a Docker container.
#
# REQUIREMENTS:
#   - Docker image must contain: Python 3.6+, gatk, samtools, bcftools, Java 17+
#   - Tools expected at: /opt/conda/bin/
#
# MOUNT POINTS (required):
#   /pipeline     <- Project directory (MitoPipeline-main)
#   /studies      <- External data (studies/human_genetics_bulk/reads/bam, studies/MitoPipeline)
#
# EXAMPLE DOCKER RUN:
#   docker run --rm \
#     -v /home/ec2-user/studies:/studies \
#     -v /path/to/MitoPipeline-main:/pipeline \
#     -w /pipeline \
#     mito-image python src/human/run_pipeline.py --step prep
#
# For single sample:
#   docker run --rm \
#     -v /home/ec2-user/studies:/studies \
#     -v /path/to/MitoPipeline-main:/pipeline \
#     -w /pipeline \
#     mito-image python src/human/run_pipeline.py --step prep --sample-id 00114249-518b
#
# ============================================================================

import os
import subprocess
from pathlib import Path
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Human Mitochondrial Pipeline Wrapper for preprocessing and variant calling"
    )
    
    parser.add_argument(
        "--step",
        required=True,
        choices=["prep", "vcf"],
        help="Pipeline step to execute: 'prep' for preprocessing or 'vcf' for variant calling"
    )
    
    parser.add_argument(
        "--sample-id",
        default=None,
        help="Process a single sample by ID (e.g., '00114249-518b'). If not provided, processes all samples in the directory."
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them"
    )
    
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Custom input directory. Defaults to appropriate folder based on --step"
    )
    
    args = parser.parse_args()
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Define bash script paths
    prep_script = script_dir / "prep_mito.sh"
    vcf_script = script_dir / "call_mito_variants.sh"
    
    # Check that bash scripts exist
    if not prep_script.exists():
        print(f"ERROR: Preprocessing script not found: {prep_script}", file=sys.stderr)
        sys.exit(1)
    if not vcf_script.exists():
        print(f"ERROR: Variant calling script not found: {vcf_script}", file=sys.stderr)
        sys.exit(1)
    
    # Determine input directory and script based on step
    if args.step == "prep":
        if args.input_dir:
            input_dir = Path(args.input_dir)
        else:
            input_dir = project_root / "data" / "human" / "raw" / "bam"
        
        bash_script = prep_script
        pattern = "gencove__*.bam"
        
        # Extract sample ID from gencove__<ID>.bam format
        def extract_sample_id(filepath):
            filename = filepath.name
            # Remove "gencove__" prefix and ".bam" suffix
            sample_id = filename.replace("gencove__", "").replace(".bam", "")
            return sample_id
        
    elif args.step == "vcf":
        if args.input_dir:
            input_dir = Path(args.input_dir)
        else:
            input_dir = project_root / "data" / "human" / "processed" / "alignment" / "deduplicated"
        
        bash_script = vcf_script
        pattern = "*.bam"
        
        # Extract sample ID from <ID>.bam format
        def extract_sample_id(filepath):
            filename = filepath.name
            sample_id = filename.replace(".bam", "")
            return sample_id
    
    # Check that input directory exists
    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Find all input files
    if args.sample_id:
        # Single sample mode
        if args.step == "prep":
            input_file = input_dir / f"gencove__{args.sample_id}.bam"
        else:
            input_file = input_dir / f"{args.sample_id}.bam"
        
        if not input_file.exists():
            print(f"ERROR: Input file not found: {input_file}", file=sys.stderr)
            sys.exit(1)
        
        samples = [args.sample_id]
    else:
        # Find all matching files
        input_files = list(input_dir.glob(pattern))
        
        if not input_files:
            print(f"WARNING: No files matching '{pattern}' found in {input_dir}", file=sys.stderr)
            sys.exit(0)
        
        samples = [extract_sample_id(f) for f in input_files]
    
    print(f"Running {args.step} step on {len(samples)} sample(s)...")
    print(f"Input directory: {input_dir}")
    print(f"Bash script: {bash_script}")
    
    completed = []
    failed = []
    skipped = []
    
    for sample_id in sorted(samples):
        print(f"\n{'='*70}")
        print(f"Processing sample: {sample_id}")
        print(f"{'='*70}")
        
        # Build command
        cmd = ["bash", str(bash_script), sample_id]
        
        if args.dry_run:
            print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
            completed.append(sample_id)
        else:
            try:
                result = subprocess.run(cmd, check=True)
                completed.append(sample_id)
                print(f"✓ Successfully processed {sample_id}")
            except subprocess.CalledProcessError as e:
                failed.append(sample_id)
                print(f"✗ FAILED for {sample_id}: {e}", file=sys.stderr)
            except Exception as e:
                failed.append(sample_id)
                print(f"✗ ERROR for {sample_id}: {e}", file=sys.stderr)
    
    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Completed: {len(completed)}/{len(samples)}")
    if completed:
        for sample_id in completed:
            print(f"  ✓ {sample_id}")
    
    if failed:
        print(f"\nFailed: {len(failed)}/{len(samples)}")
        for sample_id in failed:
            print(f"  ✗ {sample_id}")
    
    if skipped:
        print(f"\nSkipped: {len(skipped)}/{len(samples)}")
        for sample_id in skipped:
            print(f"  - {sample_id}")
    
    # Exit with error if any failures
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
