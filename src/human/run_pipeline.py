#!/usr/bin/env python3

# ============================================================================
# HUMAN MITOCHONDRIAL PIPELINE - Python Wrapper
# ============================================================================
# Runs bioinformatics processing for mitochondrial data.
#
# DOCKER SETUP:
# The pipeline automatically handles Docker image management:
#   1. Checks if image (mito_pipeline_env:latest) already exists
#   2. If not found, looks for tar file: mito_pipeline_env_latest.tar
#   3. If tar exists, loads it (no need to build)
#   4. If no tar, builds from Dockerfile automatically
#   5. Runs all processing inside Docker container
#
# Docker mounts:
#   /pipeline  → project root (e.g., MitoPipeline-main3/)
#   /studies   → parent studies folder
#
# Examples - all work automatically with no Docker commands needed:
#   python src/human/run_pipeline.py --step prep --main-folder MitoPipeline-main --sample-id 00114249-518b
#   python src/human/run_pipeline.py --step both --main-folder MitoPipeline-main3 --sample-id 00114249-518b
#
# ============================================================================

import subprocess
from pathlib import Path
import argparse
import sys
import logging
from datetime import datetime
import shutil


def check_docker_installed(logger):
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        logger.info(f"✓ Docker found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        logger.error("✗ Docker is not installed or not in PATH")
        return False


def build_docker_image(dockerfile_path, image_name, image_tag, logger):
    """Build Docker image from Dockerfile."""
    if not dockerfile_path.exists():
        logger.error(f"Dockerfile not found at: {dockerfile_path}")
        return False
    
    logger.info(f"Building Docker image: {image_name}:{image_tag}")
    logger.info(f"Using Dockerfile: {dockerfile_path}")
    
    try:
        cmd = [
            "docker", "build",
            "-t", f"{image_name}:{image_tag}",
            "-f", str(dockerfile_path),
            str(dockerfile_path.parent)
        ]
        logger.info(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True)
        logger.info(f"✓ Docker image built successfully: {image_name}:{image_tag}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to build Docker image: {e}")
        return False


def load_docker_image_from_tar(tar_path, logger):
    """Load Docker image from tar file."""
    if not Path(tar_path).exists():
        logger.error(f"Docker tar file not found: {tar_path}")
        return False
    
    logger.info(f"Loading Docker image from tar: {tar_path}")
    
    try:
        with open(tar_path, 'rb') as f:
            result = subprocess.run(
                ["docker", "load"],
                stdin=f,
                capture_output=True,
                text=True,
                check=True
            )
        logger.info(f"✓ Docker image loaded: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to load Docker image: {e.stderr}")
        return False


def image_exists(image_name, image_tag, logger):
    """Check if Docker image already exists locally."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", f"{image_name}:{image_tag}"],
            capture_output=True,
            check=False
        )
        exists = result.returncode == 0
        if exists:
            logger.info(f"✓ Docker image already exists: {image_name}:{image_tag}")
        return exists
    except Exception as e:
        logger.warning(f"Could not check if image exists: {e}")
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
    
    parser = argparse.ArgumentParser(
        description="Run mitochondrial pipeline: prep, vcf, or both",
        epilog="""
EXAMPLES:
  # Run prep step for single sample (auto Docker setup)
  python run_pipeline.py --step prep --sample-id 00114249-518b
  
  # Run vcf step for all samples in input directory (auto Docker setup)
  python run_pipeline.py --step vcf
  
  # Run both steps sequentially for single sample (auto Docker setup)
  python run_pipeline.py --step both --sample-id 00114249-518b
  
  # Use custom input directory
  python run_pipeline.py --step prep --input-dir /path/to/bam/files
  
  # Use custom Docker image name/tag
  python run_pipeline.py --step both --sample-id 00114249-518b --docker-image my_image --docker-tag v2

OUTPUT:
  - Log files created in: logs/pipeline_YYYYMMDD_HHMMSS.log
  - Both console and file output enabled
  - Exit code 0 = success, non-zero = error
  
AUTOMATIC DOCKER SETUP:
  - Checks Docker installation
  - Checks if Docker image exists locally
  - If image not found, automatically builds it from Dockerfile
  - If image found, loads and uses it
  - All processes run inside Docker container
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
  vcf:  /pipeline/data/human/processed/alignment/deduplicated/
        """
    )
    
    parser.add_argument(
        "--docker-image",
        default="mito_pipeline_env",
        help="Docker image name (default: mito_pipeline_env)"
    )
    
    parser.add_argument(
        "--docker-tag",
        default="v1",
        help="Docker image tag (default: v1)"
    )
    
    args = parser.parse_args()
    
    # Get script paths (already defined in logging setup above)
    prep_script = script_dir / "prep_mito.sh"
    vcf_script = script_dir / "call_mito_variants.sh"
    
    logger.info(f"Project root: {project_root}")
    
    # ========================================================================
    # AUTOMATIC DOCKER SETUP (always run)
    # ========================================================================
    logger.info(f"\n{'='*70}")
    logger.info("DOCKER SETUP (AUTOMATIC)")
    logger.info(f"{'='*70}")
    
    # Check if Docker is available
    if not check_docker_installed(logger):
        logger.error("Docker is required but not available. Exiting.")
        sys.exit(1)
    
    # Check if image exists
    image_name = args.docker_image
    image_tag = args.docker_tag
    logger.info(f"Checking for Docker image: {image_name}:{image_tag}")
    
    if not image_exists(image_name, image_tag, logger):
        logger.info(f"Image not found. Attempting to load from tar file or build...")
        
        # Try loading from tar file first (check in MitoPipeline parent folder)
        tar_file = project_root.parent / f"{image_name}_{image_tag}.tar"
        if tar_file.exists():
            logger.info(f"Found tar file: {tar_file}")
            if load_docker_image_from_tar(tar_file, logger):
                logger.info(f"✓ Successfully loaded image from tar")
            else:
                logger.warning(f"Failed to load tar file, will attempt to build...")
                dockerfile = project_root / "Dockerfile"
                if not build_docker_image(dockerfile, image_name, image_tag, logger):
                    logger.error("Failed to build Docker image. Exiting.")
                    sys.exit(1)
        else:
            # No tar file, try building from Dockerfile
            logger.info(f"No tar file found. Building from Dockerfile...")
            dockerfile = project_root / "Dockerfile"
            if not build_docker_image(dockerfile, image_name, image_tag, logger):
                logger.error("Failed to build Docker image. Exiting.")
                sys.exit(1)
    
    logger.info(f"✓ Docker image ready: {image_name}:{image_tag}")
    
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
        
        # Get input directory
        if args.input_dir:
            input_dir = Path(args.input_dir)
        else:
            if step_name == "prep":
                input_dir = Path("/studies/human_genetics_bulk/reads/bam")
            else:  # vcf
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
            
            # Always run inside Docker container
            studies_root = project_root.parent.parent  # Go up 2 levels from project to studies/
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{project_root}:/pipeline",
                "-v", f"{studies_root}:/studies",
                "-w", "/pipeline",
                f"{image_name}:{image_tag}",
                "bash", str(bash_script), sample_id
            ]
            
            subprocess.run(cmd, check=True)
            logger.info(f"✓ Done: {sample_id}")
        
        logger.info(f"\n✓ {step_name.upper()} complete. Processed {len(samples)} sample(s)")


if __name__ == "__main__":
    main()
