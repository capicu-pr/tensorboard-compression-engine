#!/usr/bin/env python3
"""
Example: Visualizing Compression Engine Benchmark Results

This example demonstrates how to use the CompressionWriter and BenchmarkParser
to visualize compression engine benchmark results in TensorBoard.

Usage:
    python examples/compression_benchmark_example.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tensorboardX.compression import CompressionWriter
from tensorboardX.compression.benchmark import BenchmarkParser, log_benchmark_results


def example_basic_usage():
    """Example 1: Basic usage with CompressionWriter."""
    print("=" * 70)
    print("Example 1: Basic CompressionWriter Usage")
    print("=" * 70)
    
    # Create a CompressionWriter
    writer = CompressionWriter('runs/example/basic')
    
    # Example FP32 and INT8 metrics
    fp32_metrics = {
        'accuracy': 0.9945,
        'f1_score': 0.9945,
        'latency_mean_ms': 261.02,
        'model_size_mb': 217.61,
        'memory_usage_mb': 9.46,
        'energy_consumption_mw': 375.78,
        'loss': 0.0246,
    }
    
    int8_metrics = {
        'accuracy': 0.9945,
        'f1_score': 0.9945,
        'latency_mean_ms': 217.14,
        'model_size_mb': 9.42,
        'memory_usage_mb': 5.23,
        'energy_consumption_mw': 402.38,
        'loss': 0.0246,
    }
    
    model_info = {
        'library': 'torchvision',
        'category': 'CNN',
        'description': 'AlexNet architecture for image classification',
        'input_shape': [3, 224, 224]
    }
    
    # Log compression comparison
    writer.log_compression_comparison('alexnet', fp32_metrics, int8_metrics)
    
    # Log compression ratios
    writer.log_compression_ratios('alexnet', fp32_metrics, int8_metrics)
    
    # Log energy comparison
    writer.log_energy_comparison('alexnet', fp32_metrics, int8_metrics)
    
    # Log model metadata
    writer.log_model_metadata('alexnet', model_info)
    
    writer.close()
    
    print("✅ Logged compression metrics for alexnet")
    print(f"📊 View results: tensorboard --logdir runs/example/basic")
    print()


def example_benchmark_parser():
    """Example 2: Using BenchmarkParser to visualize JSON results."""
    print("=" * 70)
    print("Example 2: BenchmarkParser Usage")
    print("=" * 70)
    
    # Path to benchmark JSON (adjust as needed)
    json_path = Path(__file__).parent.parent / 'results' / 'models_benchmark_results.json'
    
    if not json_path.exists():
        print(f"⚠️  Benchmark file not found: {json_path}")
        print("   Skipping this example. To use it:")
        print("   1. Run compression engine benchmarks")
        print("   2. Update the json_path variable in this script")
        print()
        return
    
    # Method 1: Using the convenience function
    print("Method 1: Using log_benchmark_results() convenience function")
    writer = log_benchmark_results(str(json_path), logdir='runs/example/benchmark')
    writer.close()
    
    print("✅ Converted benchmark JSON to TensorBoard format")
    print(f"📊 View results: tensorboard --logdir runs/example/benchmark")
    print()
    
    # Method 2: Using BenchmarkParser class directly
    print("Method 2: Using BenchmarkParser class directly")
    parser = BenchmarkParser()
    writer = parser.log_benchmark_results(
        str(json_path),
        logdir='runs/example/benchmark_parser'
    )
    writer.close()
    
    print("✅ Converted benchmark JSON using BenchmarkParser")
    print(f"📊 View results: tensorboard --logdir runs/example/benchmark_parser")
    print()


def example_multiple_models():
    """Example 3: Logging multiple models for comparison."""
    print("=" * 70)
    print("Example 3: Multiple Models Comparison")
    print("=" * 70)
    
    writer = CompressionWriter('runs/example/multi_model')
    
    # Define multiple models
    models = {
        'alexnet': {
            'fp32': {'accuracy': 0.9945, 'latency_mean_ms': 261.02, 'model_size_mb': 217.61},
            'int8': {'accuracy': 0.9945, 'latency_mean_ms': 217.14, 'model_size_mb': 9.42},
        },
        'resnet18': {
            'fp32': {'accuracy': 0.9956, 'latency_mean_ms': 145.23, 'model_size_mb': 44.55},
            'int8': {'accuracy': 0.9954, 'latency_mean_ms': 98.76, 'model_size_mb': 11.12},
        },
        'mobilenetv2': {
            'fp32': {'accuracy': 0.9934, 'latency_mean_ms': 89.45, 'model_size_mb': 13.45},
            'int8': {'accuracy': 0.9932, 'latency_mean_ms': 45.67, 'model_size_mb': 3.56},
        },
    }
    
    # Log each model
    for model_name, metrics in models.items():
        writer.log_compression_comparison(
            model_name,
            metrics['fp32'],
            metrics['int8']
        )
        writer.log_compression_ratios(
            model_name,
            metrics['fp32'],
            metrics['int8']
        )
    
    writer.close()
    
    print("✅ Logged compression metrics for multiple models")
    print("📊 Compare models side-by-side in TensorBoard")
    print(f"📊 View results: tensorboard --logdir runs/example/multi_model")
    print()


def example_training_logger():
    """Example 4: Using TrainingLogger for training metrics."""
    print("=" * 70)
    print("Example 4: TrainingLogger Usage")
    print("=" * 70)
    
    from tensorboardX.compression.training import TrainingLogger
    
    # Create training logger
    logger = TrainingLogger('alexnet', logdir='runs/example/training')
    
    # Simulate training epochs
    num_epochs = 10
    for epoch in range(num_epochs):
        # Simulated metrics (in real usage, these come from training)
        train_loss = 0.5 * (0.9 ** epoch)
        train_acc = 0.8 + 0.15 * (1 - 0.9 ** epoch)
        train_f1 = train_acc * 0.98
        
        val_loss = train_loss * 1.1
        val_acc = train_acc * 0.95
        val_f1 = val_acc * 0.98
        
        learning_rate = 0.001 * (0.95 ** epoch)
        
        logger.log_epoch(
            epoch=epoch,
            train_loss=train_loss,
            train_acc=train_acc,
            train_f1=train_f1,
            val_loss=val_loss,
            val_acc=val_acc,
            val_f1=val_f1,
            learning_rate=learning_rate
        )
    
    # Log early stopping info
    logger.log_early_stopping(
        epoch=num_epochs - 1,
        patience=5,
        min_delta=0.001,
        stopped=False
    )
    
    # Log training summary
    logger.log_training_summary(
        total_epochs=num_epochs,
        final_train_loss=train_loss,
        final_train_acc=train_acc,
        final_train_f1=train_f1,
        final_val_loss=val_loss,
        final_val_acc=val_acc,
        final_val_f1=val_f1,
        early_stopped=False
    )
    
    logger.close()
    
    print("✅ Logged training metrics")
    print(f"📊 View results: tensorboard --logdir runs/example/training")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Compression Board - Example Scripts")
    print("=" * 70)
    print()
    
    example_basic_usage()
    example_benchmark_parser()
    example_multiple_models()
    example_training_logger()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print("\nTo view all results, run:")
    print("  tensorboard --logdir runs/example")
    print("\nOr use the compression board launcher:")
    print("  compression-board --logdir runs/example")
    print()


if __name__ == '__main__':
    main()

