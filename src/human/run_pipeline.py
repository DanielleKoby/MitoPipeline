#!/usr/bin/env python3

# ============================================================================
# HUMAN MITOCHONDRIAL PIPELINE - Python Wrapper
# ============================================================================
# EXECUTION MODEL: This script runs INSIDE the Docker container
#
# The host spins up Docker ONCE with proper mounts and overlay paths.
# This script then handles all sample iteration internally via direct
# subprocess calls (no Docker wrapping).
#
# DOCKER IMAGE LOADING:
# The Docker image (mito_pipeline_env:v1) must be pre-loaded on the host.
# To load the image from a tar file:
#   docker load -i /home/ec2-user/studies/MitoPipeline/mito_pipeline_env_v1.tar
#
# RESUMABLE EXECUTION:
# If the server crashes during processing, the pipeline will skip samples
# that have already been completed. Check /pipeline/data/human/processed/alignment/deduplicated/
# for existing output BAM files. The pipeline automatically detects and skips them.
#
# If a sample was interrupted mid-processing, partial files (.parts, .tmp) will be
# automatically detected and cleaned up on re-run before re-processing.
#
# GRACEFUL TERMINATION:
# Press Ctrl+C at any time to pause processing. Already-processed samples are safe.
# Re-run the same command to resume from where you left off.
#
# HOST COMMAND (example - replace paths as needed):
# docker run --rm \
#   -v /home/ec2-user/studies:/studies \
#   -v /home/ec2-user/studies/MitoPipeline/MitoPipeline-main10:/pipeline \
#   -v /home/ec2-user/pipeline_logs:/pipeline/data/human/qc/logs \
#   -w /pipeline \
#   mito_pipeline_env:v1 python src/human/run_pipeline.py --step prep
#
# ============================================================================

import subprocess
from pathlib import Path
import argparse
import sys
import logging
from datetime import datetime
import signal
import shutil
import os

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n" + "="*70)
    print("⚠️  PIPELINE INTERRUPTED BY USER")
    print("="*70)
    print("Gracefully shutting down...")
    print("Run the same command again to resume processing.")
    print("Already-completed samples will be skipped automatically.")
    sys.exit(0)

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)


def has_partial_artifacts(step_name, project_root):
    """Check once per step whether interrupted-run temporary artifacts exist."""
    if step_name == "prep":
        search_dirs = [
            project_root / "data" / "human" / "processed" / "temp",
            project_root / "data" / "human" / "processed" / "alignment" / "mito_extracted",
            project_root / "data" / "human" / "processed" / "alignment" / "read_groups",
            project_root / "data" / "human" / "processed" / "alignment" / "sorted",
            project_root / "data" / "human" / "processed" / "alignment" / "deduplicated",
            project_root / "data" / "human" / "qc" / "dedup_metrics",
        ]
    else:
        search_dirs = [
            project_root / "data" / "human" / "processed" / "variants" / "raw",
            project_root / "data" / "human" / "processed" / "variants" / "v_01" / "filtered",
            project_root / "data" / "human" / "processed" / "variants" / "v_01" / "final",
            project_root / "data" / "human" / "processed" / "consensus" / "v_01" / "fasta",
        ]

    partial_patterns = ["*.parts", "*.tmp.*", "*.sort.tmp*", "*~"]

    for directory in search_dirs:
        if not directory.exists():
            continue
        for pattern in partial_patterns:
            if any(directory.glob(pattern)):
                return True
    return False

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
    logger.info(f"Execution context: Inside Docker container (single lifecycle)")
    
    parser = argparse.ArgumentParser(
        description="Run mitochondrial pipeline inside Docker container (prep, vcf, or both)",
        epilog="""
EXECUTION CONTEXT:
This script is designed to run INSIDE the Docker container.
The host invokes it with a single 'docker run' command that includes:
  - Overlay logs mount: /home/ec2-user/pipeline_logs:/pipeline/data/human/qc/logs
  - This overlay enables append operations (>>) on local EBS storage

DOCKER IMAGE SETUP:
Before running the docker run command, load the image from the tar file:
  docker load -i /home/ec2-user/studies/MitoPipeline/mito_pipeline_env_v1.tar
  
The image will be loaded as: mito_pipeline_env:v1
Verify with: docker images | grep mito

HOST COMMAND EXAMPLE:
  docker run --rm \
    -v /home/ec2-user/studies:/studies \
    -v /home/ec2-user/studies/MitoPipeline/MitoPipeline-main10:/pipeline \
    -v /home/ec2-user/pipeline_logs:/pipeline/data/human/qc/logs \
    -w /pipeline \
    mito_pipeline_env:v1 python src/human/run_pipeline.py --step vcf

USAGE INSIDE CONTAINER:
  # Process all samples (default)
  python src/human/run_pipeline.py --step prep
  
  # Process single sample
  python src/human/run_pipeline.py --step prep --sample-id 00114249-518b
  
  # Run both steps for all samples
  python src/human/run_pipeline.py --step both
  
  # Custom input directory
  python src/human/run_pipeline.py --step prep --input-dir /path/to/bam

OUTPUT:
  - Pipeline logs: logs/pipeline_YYYYMMDD_HHMMSS.log
  - Processing logs: /pipeline/data/human/qc/logs/ (overlay mounted to local EBS)
  - Processed samples: /pipeline/data/human/processed/
  - Exit code 0 = success, non-zero = error

RESUMABLE EXECUTION:
  If the server crashes during prep processing, re-run the same command.
  The pipeline automatically detects already-processed samples and skips them.
  Look for completed output BAM files at:
    /pipeline/data/human/processed/alignment/deduplicated/{sample_id}.bam
  Already-processed samples will show as "SKIPPED" in the logs.

PARTIAL FILE CLEANUP:
  If a sample is interrupted mid-processing, partial files (.parts, .tmp) may be left behind.
  On re-run, the pipeline automatically detects and cleans up these partial files before
  re-processing the sample. No manual cleanup is needed.

GRACEFUL TERMINATION:
  Press Ctrl+C at any time to pause the pipeline. The container will shut down gracefully.
  Run the same command again to resume from where you left off.
  Already-processed samples will be skipped automatically.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--step",
        required=True,
        choices=["prep", "vcf", "both"],
        help="""
Pipeline step(s) to execute:
  prep  - Preprocessing: Extract MT reads, add read groups, sort, mark duplicates
  vcf   - Variant calling: Filter variants, apply thresholds, create consensus
  both  - Run prep then vcf sequentially
        """
    )
    
    parser.add_argument(
        "--sample-id",
        default=None,
        help="Process single sample by ID (e.g. '00114249-518b'). If not provided, processes ALL samples."
    )
    
    parser.add_argument(
        "--input-dir",
        default=None,
        help="""
Custom input directory. Defaults:
  prep: /studies/human_genetics_bulk/reads/bam/
  vcf:  /pipeline/data/human/processed/alignment/deduplicated/
        """
    )
    
    args = parser.parse_args()
    
    # Get script paths
    prep_script = script_dir / "prep_mito.sh"
    vcf_script = script_dir / "call_mito_variants.sh"
    
    logger.info(f"Project root: {project_root}")
    logger.info(f"Processing mode: {'Single sample (' + args.sample_id + ')' if args.sample_id else 'All samples'}")
    
    # ========================================================================
    # DETERMINE WHICH STEPS TO RUN
    # ========================================================================
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
        
        # Get input directory (uses Docker mount points)
        if args.input_dir:
            input_dir = Path(args.input_dir)
        else:
            if step_name == "prep":
                # Inside Docker: /studies maps to host's /home/ec2-user/studies
                input_dir = Path("/studies/human_genetics_bulk/reads/bam")
            else:  # vcf
                # /pipeline maps to host's MitoPipeline-main10/
                input_dir = project_root / "data" / "human" / "processed" / "alignment" / "deduplicated"
        
        # Get file pattern
        pattern = "gencove__*.bam" if step_name == "prep" else "*.bam"
        
        # Determine which samples to process
        if args.sample_id:
            # Single sample mode
            samples = [args.sample_id]
        else:
            # Process all samples
            if input_dir.exists():
                input_files = list(input_dir.glob(pattern))
                if not input_files:
                    logger.warning(f"No files matching '{pattern}' in {input_dir}")
                    continue
                # Extract sample IDs from filenames
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
        
        # ====================================================================
        # EXECUTE BASH SCRIPTS FOR EACH SAMPLE
        # (Direct subprocess calls - no Docker wrapping since we're in-container)
        # ====================================================================
        logger.info(f"Found {len(samples)} sample(s) to process")

        # Check once before step execution whether cleanup is needed.
        enable_partial_cleanup = has_partial_artifacts(step_name, project_root)
        logger.info(
            "Partial-file cleanup: %s",
            "ENABLED (partial artifacts detected)" if enable_partial_cleanup else "DISABLED (no artifacts detected)",
        )
        
        skipped_count = 0
        processed_count = 0
        
        for idx, sample_id in enumerate(sorted(samples), 1):
            # For prep step: check if output already exists (resumability after crashes)
            if step_name == "prep":
                output_bam = project_root / "data" / "human" / "processed" / "alignment" / "deduplicated" / f"{sample_id}.bam"
                if output_bam.exists():
                    logger.info(f"[{idx}/{len(samples)}] SKIPPED: {sample_id} (already processed)")
                    skipped_count += 1
                    continue
            
            logger.info(f"[{idx}/{len(samples)}] Processing: {sample_id}")
            
            # Execute bash script directly via subprocess
            # We're already inside the container, so no docker wrapping needed
            cmd = ["bash", str(bash_script), sample_id]
            env = os.environ.copy()
            env["PIPELINE_ENABLE_PARTIAL_CLEANUP"] = "1" if enable_partial_cleanup else "0"
            
            try:
                subprocess.run(cmd, check=True, env=env)
                logger.info(f"  ✓ Completed: {sample_id}")
                processed_count += 1
            except subprocess.CalledProcessError as e:
                logger.error(f"  ✗ Failed: {sample_id} (exit code: {e.returncode})")
                sys.exit(1)
        
        summary = f"Processed {processed_count} sample(s)"
        if skipped_count > 0:
            summary += f", Skipped {skipped_count} (already completed)"
        logger.info(f"\n✓ {step_name.upper()} complete. {summary}")
    
    logger.info("\n" + "="*70)
    logger.info("✓ PIPELINE EXECUTION COMPLETE")
    logger.info("="*70)


if __name__ == "__main__":
    main()
