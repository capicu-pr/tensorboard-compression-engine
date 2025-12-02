#!/usr/bin/env python3
"""
CLI tool to visualize compression engine benchmark results in TensorBoard.

This script reads benchmark JSON files from the compression engine and
converts them to TensorBoard event files for visualization.

Usage:
    python scripts/visualize_benchmark.py <path_to_json>
    python scripts/visualize_benchmark.py ../compression-engine/results/models_benchmark_results.json
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tensorboardX.compression.benchmark import BenchmarkParser


def main():
    """Main entry point for the visualization script."""
    parser = argparse.ArgumentParser(
        description='Visualize compression engine benchmark results in TensorBoard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize a benchmark JSON file
  python scripts/visualize_benchmark.py ../compression-engine/results/models_benchmark_results.json
  
  # Specify custom output directory
  python scripts/visualize_benchmark.py benchmark.json --logdir runs/my_benchmark
  
  # Visualize multiple files
  for file in ../compression-engine/results/*.json; do
    python scripts/visualize_benchmark.py "$file"
  done
        """
    )
    
    parser.add_argument(
        'json_path',
        type=str,
        help='Path to the benchmark JSON file'
    )
    
    parser.add_argument(
        '--logdir',
        type=str,
        default=None,
        help='Directory for TensorBoard logs (default: runs/compression_benchmark/{filename})'
    )
    
    parser.add_argument(
        '--step',
        type=int,
        default=0,
        help='Global step for logging (default: 0 for benchmark results)'
    )
    
    args = parser.parse_args()
    
    # Validate JSON file exists
    if not os.path.exists(args.json_path):
        print(f"Error: File not found: {args.json_path}", file=sys.stderr)
        sys.exit(1)
    
    if not args.json_path.endswith('.json'):
        print(f"Warning: File does not have .json extension: {args.json_path}", file=sys.stderr)
    
    # Create parser and log results
    try:
        print(f"Loading benchmark results from: {args.json_path}")
        parser = BenchmarkParser()
        writer = parser.log_benchmark_results(args.json_path, logdir=args.logdir, step=args.step)
        
        print(f"\n✅ Successfully converted benchmark results to TensorBoard format")
        print(f"📊 Log directory: {writer.logdir}")
        print(f"\nTo view in TensorBoard, run:")
        print(f"  tensorboard --logdir {writer.logdir}")
        print(f"\nOr use the compression board launcher:")
        print(f"  compression-board --logdir {writer.logdir}")
        
        writer.close()
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if 'JSON' in str(type(e).__name__):
            print(f"Error: Invalid JSON file: {e}", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

