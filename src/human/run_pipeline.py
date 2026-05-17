#!/usr/bin/env python3

# ============================================================================
# HUMAN MITOCHONDRIAL PIPELINE - Python Wrapper
# ============================================================================
# Runs bioinformatics processing for mitochondrial data.
#
# DOCKER EXAMPLE:
#   docker run --rm \
#     -v /home/ec2-user/studies:/studies \
#     -v /home/ec2-user/studies/MitoPipeline/MitoPipeline-main:/pipeline \
#     -v /home/ec2-user/output:/output \
#     -w /pipeline \
#     mito_pipeline_env:v1 python src/human/run_pipeline.py --step both --sample-id 00114249-518b
#
# ============================================================================

import subprocess
from pathlib import Path
import argparse
import sys
import logging
from datetime import datetime


def main():
    # Setup logging to file
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"pipeline_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Pipeline started. Log file: {log_file}")
    
    parser = argparse.ArgumentParser(
        description="Run mitochondrial pipeline: prep, vcf, or both",
        epilog="""
EXAMPLES:
  # Run prep step for single sample
  python run_pipeline.py --step prep --sample-id 00114249-518b
  
  # Run vcf step for all samples in input directory
  python run_pipeline.py --step vcf
  
  # Run both steps sequentially for single sample
  python run_pipeline.py --step both --sample-id 00114249-518b
  
  # Use custom input directory
  python run_pipeline.py --step prep --input-dir /path/to/bam/files
  
  # Docker example (all mounts required)
  docker run --rm \\
    -v /home/ec2-user/studies:/studies \\
    -v /home/ec2-user/studies/MitoPipeline/MitoPipeline-main:/pipeline \\
    -v /home/ec2-user/output:/output \\
    -w /pipeline \\
    mito_pipeline_env:v1 python src/human/run_pipeline.py --step both

OUTPUT:
  - Log files created in: logs/pipeline_YYYYMMDD_HHMMSS.log
  - Both console and file output enabled
  - Exit code 0 = success, non-zero = error
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--step",
        required=True,
        choices=["prep", "vcf", "both"],
        help="""
Pipeline step(s) to execute:
  prep  - Preprocessing: Extract MT reads, add read groups, sort, mark duplicates, index
  vcf   - Variant calling: Filter variants, apply AF/DP thresholds, create consensus
  both  - Run prep then vcf sequentially
        """
    )
    
    parser.add_argument(
        "--sample-id",
        default=None,
        help="""
Process single sample by ID (e.g. '00114249-518b').
If not provided, processes ALL samples found in input directory.
        """
    )
    
    parser.add_argument(
        "--input-dir",
        default=None,
        help="""
Custom input directory. If not provided, uses defaults:
  prep: /studies/human_genetics_bulk/reads/bam/
  vcf:  /output/data/human/processed/alignment/deduplicated/ (or local project/data/)
        """
    )
    
    args = parser.parse_args()
    
    # Get script paths (already defined in logging setup above)
    prep_script = script_dir / "prep_mito.sh"
    vcf_script = script_dir / "call_mito_variants.sh"
    
    # Determine which steps to run
    steps = []
    if args.step in ["prep", "both"]:
        steps.append(("prep", prep_script))
    if args.step in ["vcf", "both"]:
        steps.append(("vcf", vcf_script))
    
    # Process each step
    for step_name, bash_script in steps:
        logger.info(f"\n{'='*70}")
        logger.info(f"RUNNING: {step_name.upper()}")
        logger.info(f"{'='*70}")
        
        # Get input directory
        if args.input_dir:
            input_dir = Path(args.input_dir)
        else:
            if step_name == "prep":
                input_dir = Path("/studies/human_genetics_bulk/reads/bam")
            else:  # vcf
                if Path("/output").exists():
                    input_dir = Path("/output/data/human/processed/alignment/deduplicated")
                else:
                    input_dir = project_root / "data" / "human" / "processed" / "alignment" / "deduplicated"
        
        # Get file pattern
        pattern = "gencove__*.bam" if step_name == "prep" else "*.bam"
        
        # Determine samples
        if args.sample_id:
            samples = [args.sample_id]
        else:
            if input_dir.exists():
                input_files = list(input_dir.glob(pattern))
                if not input_files:
                    logger.warning(f"No files matching '{pattern}' in {input_dir}")
                    continue
                # Extract sample IDs
                samples = []
                for f in input_files:
                    if step_name == "prep":
                        sample_id = f.name.replace("gencove__", "").replace(".bam", "")
                    else:
                        sample_id = f.name.replace(".bam", "")
                    samples.append(sample_id)
            else:
                logger.error(f"Input directory not found: {input_dir}")
                sys.exit(1)
        
        # Run for each sample
        for sample_id in sorted(samples):
            logger.info(f"Processing: {sample_id}")
            cmd = ["bash", str(bash_script), sample_id]
            subprocess.run(cmd, check=True)
            logger.info(f"✓ Done: {sample_id}")
        
        logger.info(f"\n✓ {step_name.upper()} complete. Processed {len(samples)} sample(s)")


if __name__ == "__main__":
    main()
