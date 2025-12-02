#!/usr/bin/env python3
"""
Custom TensorBoard launcher for compression visualization.

This script launches TensorBoard with compression-specific optimizations
and provides helpful information about which tabs to use.

Usage:
    compression-board --logdir runs/compression_benchmark
    compression-board --logdir runs/compression_benchmark --port 6006
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .config import RELEVANT_TABS, LESS_RELEVANT_TABS


def find_tensorboard():
    """Find the tensorboard executable."""
    # Try to find tensorboard in the current environment
    try:
        result = subprocess.run(
            ['which', 'tensorboard'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Try python -m tensorboard
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'tensorboard', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        return f"{sys.executable} -m tensorboard"
    except subprocess.CalledProcessError:
        pass
    
    return None


def launch_tensorboard(logdir, port=6006, host='0.0.0.0', reload_interval=30):
    """Launch TensorBoard with compression-specific settings.
    
    Args:
        logdir: Directory containing TensorBoard logs
        port: Port to run TensorBoard on (default: 6006)
        host: Host to bind to (default: 0.0.0.0)
        reload_interval: Data reload interval in seconds (default: 30)
    """
    tensorboard_cmd = find_tensorboard()
    
    if tensorboard_cmd is None:
        print("Error: TensorBoard not found. Please install it with:", file=sys.stderr)
        print("  pip install tensorboard", file=sys.stderr)
        sys.exit(1)
    
    # Build command
    if ' -m tensorboard' in tensorboard_cmd:
        cmd = tensorboard_cmd.split() + [
            '--logdir', logdir,
            '--port', str(port),
            '--host', host,
            '--reload_interval', str(reload_interval),
        ]
    else:
        cmd = [
            tensorboard_cmd,
            '--logdir', logdir,
            '--port', str(port),
            '--host', host,
            '--reload_interval', str(reload_interval),
        ]
    
    # Print helpful information
    print("=" * 70)
    print("Compression Board - TensorBoard Launcher")
    print("=" * 70)
    print(f"\n📊 Log directory: {logdir}")
    print(f"🌐 TensorBoard will be available at: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"\n📋 Relevant tabs for compression analysis:")
    for tab in RELEVANT_TABS:
        print(f"   • {tab}")
    print(f"\n💡 Tips:")
    print(f"   • Use SCALARS tab to compare FP32 vs INT8 metrics")
    print(f"   • Filter by model name using the tag filter")
    print(f"   • Look for compression ratios in the 'compression' tag group")
    print(f"   • Training metrics are under 'training' and 'validation' tags")
    print(f"\n🚀 Starting TensorBoard...")
    print("=" * 70)
    print()
    
    # Launch TensorBoard
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nTensorBoard stopped by user.")
    except subprocess.CalledProcessError as e:
        print(f"\nError: TensorBoard exited with code {e.returncode}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for compression board launcher."""
    parser = argparse.ArgumentParser(
        description='Launch TensorBoard optimized for compression visualization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch with default settings
  compression-board --logdir runs/compression_benchmark
  
  # Specify custom port
  compression-board --logdir runs/compression_benchmark --port 6007
  
  # Launch for specific benchmark
  compression-board --logdir runs/compression_benchmark/models_benchmark_results
        """
    )
    
    parser.add_argument(
        '--logdir',
        type=str,
        required=True,
        help='Directory containing TensorBoard logs'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=6006,
        help='Port to run TensorBoard on (default: 6006)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--reload-interval',
        type=int,
        default=30,
        help='Data reload interval in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Validate logdir exists
    if not os.path.exists(args.logdir):
        print(f"Warning: Log directory does not exist: {args.logdir}", file=sys.stderr)
        print("TensorBoard will create it, but there may be no data to display.", file=sys.stderr)
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    launch_tensorboard(
        logdir=args.logdir,
        port=args.port,
        host=args.host,
        reload_interval=args.reload_interval
    )


if __name__ == '__main__':
    main()

