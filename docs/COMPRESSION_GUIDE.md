# Compression Board - User Guide

## Overview

Compression Board is a TensorBoard-based visualization platform specifically designed for model compression analysis. It provides an intuitive interface for comparing FP32 vs INT8 models, analyzing compression ratios, and tracking training metrics.

## Quick Start

### 1. Visualize Existing Benchmark Results

If you have benchmark results from the compression engine:

```bash
# Convert JSON benchmark results to TensorBoard format
python scripts/visualize_benchmark.py ../compression-engine/results/models_benchmark_results.json

# Launch TensorBoard
tensorboard --logdir runs/compression_benchmark
```

Or use the compression board launcher:

```bash
compression-board --logdir runs/compression_benchmark
```

### 2. View in Browser

Open your browser to `http://localhost:6006` (or the port specified).

## Understanding Compression Metrics

### Tag Organization

Compression Board organizes metrics using a hierarchical tag structure:

- `{model_name}/accuracy` - Accuracy comparison (FP32 vs INT8)
- `{model_name}/latency` - Latency comparison
- `{model_name}/model_size` - Model size comparison
- `{model_name}/compression/size_ratio` - Compression ratio (FP32 size / INT8 size)
- `{model_name}/compression/speedup` - Speedup factor (FP32 latency / INT8 latency)
- `{model_name}/compression/accuracy_drop` - Accuracy degradation
- `{model_name}/training/` - Training metrics (loss, accuracy, F1)
- `{model_name}/validation/` - Validation metrics

### Key Metrics Explained

#### Compression Ratio
- **Size Ratio**: `fp32_size / int8_size` - Higher is better (more compression)
- **Size Reduction**: Percentage reduction in model size
- **Speedup**: `fp32_latency / int8_latency` - Higher is better (faster inference)

#### Accuracy Metrics
- **Accuracy Drop**: `fp32_accuracy - int8_accuracy` - Lower is better (less degradation)
- **Accuracy Retention**: Percentage of original accuracy retained

#### Energy & Memory
- **Energy Reduction**: Difference in energy consumption
- **Memory Reduction**: Reduction in memory usage

## Using TensorBoard Interface

### SCALARS Tab

The SCALARS tab is the most important for compression analysis:

1. **Filter by Model**: Use the tag filter to focus on specific models
2. **Compare Metrics**: Use `add_scalars()` groups to compare FP32 vs INT8 side-by-side
3. **View Compression Ratios**: Look for tags under `{model_name}/compression/`

### HISTOGRAMS Tab

Useful for viewing latency distributions (if available):
- `{model_name}/latency_distribution/fp32`
- `{model_name}/latency_distribution/int8`

### HPARAMS Tab

For comparing compression configurations (future feature):
- Compression settings
- Quantization parameters
- Pruning ratios

## Programmatic Usage

### Basic CompressionWriter Usage

```python
from tensorboardX.compression import CompressionWriter

writer = CompressionWriter('runs/my_experiment')

fp32_metrics = {
    'accuracy': 0.9945,
    'latency_mean_ms': 261.02,
    'model_size_mb': 217.61,
}

int8_metrics = {
    'accuracy': 0.9945,
    'latency_mean_ms': 217.14,
    'model_size_mb': 9.42,
}

# Log comparison
writer.log_compression_comparison('alexnet', fp32_metrics, int8_metrics)

# Log compression ratios
writer.log_compression_ratios('alexnet', fp32_metrics, int8_metrics)

writer.close()
```

### Benchmark Parser Usage

```python
from tensorboardX.compression.benchmark import log_benchmark_results

# Convert JSON benchmark file to TensorBoard format
writer = log_benchmark_results(
    'compression-engine/results/benchmark.json',
    logdir='runs/benchmark'
)
writer.close()
```

### Training Logger Usage

```python
from tensorboardX.compression.training import TrainingLogger

logger = TrainingLogger('alexnet', logdir='runs/training')

for epoch in range(num_epochs):
    # ... training code ...
    logger.log_epoch(
        epoch=epoch,
        train_loss=train_loss,
        train_acc=train_acc,
        train_f1=train_f1,
        val_loss=val_loss,
        val_acc=val_acc,
        val_f1=val_f1
    )

logger.close()
```

## Best Practices

### 1. Organize Runs by Experiment

Use descriptive logdir names:
```
runs/compression_benchmark/
runs/training/alexnet/
runs/comparison/resnet18_vs_mobilenet/
```

### 2. Use Consistent Model Names

Use the same model names across different runs for easy comparison:
- `alexnet`, `resnet18`, `mobilenetv2` (not `AlexNet`, `ResNet18`, etc.)

### 3. Filter Tags Effectively

In TensorBoard, use tag filters to focus on specific metrics:
- Filter by model: `alexnet`
- Filter by metric type: `compression`
- Filter by category: `training`

### 4. Compare Multiple Models

Log multiple models to the same run directory to compare them side-by-side:
```python
models = ['alexnet', 'resnet18', 'mobilenetv2']
for model_name in models:
    writer.log_compression_comparison(model_name, fp32, int8)
```

## Troubleshooting

### TensorBoard Shows No Data

1. Check that the logdir contains event files: `ls runs/your_experiment/`
2. Verify the logdir path is correct
3. Try refreshing the browser (Ctrl+F5 or Cmd+Shift+R)

### Metrics Not Appearing

1. Ensure you called `writer.close()` after logging
2. Check that metrics dictionaries contain the expected keys
3. Verify the tag names match the expected format

### Port Already in Use

If port 6006 is busy:
```bash
tensorboard --logdir runs/compression --port 6007
```

## Advanced Features

### Custom Tag Organization

You can customize tag organization by modifying the CompressionWriter methods or creating your own logging functions.

### Integration with Compression Engine

To integrate with the compression engine's training loop, add TensorBoard logging:

```python
from tensorboardX.compression.training import TrainingLogger

logger = TrainingLogger(model_name)

# In training loop
logger.log_epoch(epoch, train_loss, train_acc, train_f1, 
                 val_loss, val_acc, val_f1)
```

## Resources

- [TensorBoard Documentation](https://www.tensorflow.org/tensorboard)
- [tensorboardX Documentation](https://tensorboardx.readthedocs.io/)
- [Compression Engine](../compression-engine/README.md)

## Support

For issues or questions:
1. Check the examples in `examples/compression_benchmark_example.py`
2. Review the API documentation
3. Check compression engine documentation

