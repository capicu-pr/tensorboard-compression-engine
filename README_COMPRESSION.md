# Compression Board - TensorBoard for Model Compression

A TensorBoard-based visualization platform specifically designed for model compression analysis and comparison.

## Features

- **FP32 vs INT8 Comparisons**: Side-by-side visualization of accuracy, latency, model size, and more
- **Compression Ratios**: Automatic calculation and visualization of compression ratios, speedups, and reductions
- **Training Metrics**: Per-epoch logging of training and validation metrics
- **Multi-Model Comparison**: Compare multiple models in a single dashboard
- **Energy & Memory Analysis**: Track energy consumption and memory usage differences

## Installation

```bash
# Install dependencies
pip install -e .

# Install TensorBoard (if not already installed)
pip install tensorboard
```

## Quick Start

### 1. Visualize Benchmark Results

```bash
# Convert compression engine JSON results to TensorBoard format
python scripts/visualize_benchmark.py ../compression-engine/results/models_benchmark_results.json

# Launch TensorBoard
compression-board --logdir runs/compression_benchmark
```

Or use standard TensorBoard:

```bash
tensorboard --logdir runs/compression_benchmark
```

### 2. View in Browser

Open `http://localhost:6006` in your browser.

## Usage Examples

### Basic Usage

```python
from tensorboardX.compression import CompressionWriter

writer = CompressionWriter('runs/my_experiment')

# Log FP32 vs INT8 comparison
writer.log_compression_comparison('alexnet', fp32_metrics, int8_metrics)

# Log compression ratios
writer.log_compression_ratios('alexnet', fp32_metrics, int8_metrics)

writer.close()
```

### Benchmark Parser

```python
from tensorboardX.compression.benchmark import log_benchmark_results

# Convert JSON benchmark file
writer = log_benchmark_results('results/benchmark.json')
writer.close()
```

### Training Logger

```python
from tensorboardX.compression.training import TrainingLogger

logger = TrainingLogger('alexnet')

for epoch in range(num_epochs):
    logger.log_epoch(epoch, train_loss, train_acc, train_f1,
                     val_loss, val_acc, val_f1)

logger.close()
```

## Project Structure

```
tensorboard-compression-engine/
├── tensorboardX/
│   ├── compression.py              # CompressionWriter class
│   └── compression/
│       ├── benchmark.py            # Benchmark JSON parser
│       └── training.py             # Training metrics logger
├── compression_board/
│   ├── launch.py                   # Custom TensorBoard launcher
│   └── config.py                   # Dashboard configuration
├── scripts/
│   └── visualize_benchmark.py     # CLI tool for visualizing JSON
└── examples/
    └── compression_benchmark_example.py
```

## Key Components

### CompressionWriter

Extends `SummaryWriter` with compression-specific methods:
- `log_compression_comparison()` - Log FP32 vs INT8 metrics
- `log_compression_ratios()` - Calculate and log compression ratios
- `log_energy_comparison()` - Energy consumption comparison
- `log_model_metadata()` - Model information and metadata

### BenchmarkParser

Parses compression engine JSON results and converts to TensorBoard format:
- Reads benchmark JSON files
- Extracts FP32 and INT8 metrics
- Calculates derived metrics (ratios, speedups)
- Logs to TensorBoard

### TrainingLogger

Logs training metrics during model training:
- Per-epoch training/validation metrics
- Early stopping information
- Training summaries

## Compression Metrics

### Tag Organization

Metrics are organized hierarchically:
- `{model_name}/accuracy` - Accuracy comparison
- `{model_name}/latency` - Latency comparison
- `{model_name}/compression/size_ratio` - Compression ratio
- `{model_name}/compression/speedup` - Speedup factor
- `{model_name}/training/` - Training metrics

### Key Metrics

- **Compression Ratio**: `fp32_size / int8_size`
- **Speedup**: `fp32_latency / int8_latency`
- **Accuracy Drop**: `fp32_accuracy - int8_accuracy`
- **Size Reduction**: Percentage reduction in model size

## CLI Tools

### visualize_benchmark.py

Convert benchmark JSON files to TensorBoard format:

```bash
python scripts/visualize_benchmark.py <path_to_json>
python scripts/visualize_benchmark.py --logdir runs/custom ../compression-engine/results/benchmark.json
```

### compression-board

Custom TensorBoard launcher with compression-specific optimizations:

```bash
compression-board --logdir runs/compression_benchmark
compression-board --logdir runs/compression_benchmark --port 6007
```

## Integration with Compression Engine

### During Benchmarking

The compression engine can be modified to log directly to TensorBoard during benchmarking.

### After Benchmarking

Use the benchmark parser to visualize existing JSON results:

```python
from tensorboardX.compression.benchmark import log_benchmark_results

writer = log_benchmark_results('compression-engine/results/benchmark.json')
writer.close()
```

### During Training

Add TensorBoard logging to the training loop:

```python
from tensorboardX.compression.training import TrainingLogger

logger = TrainingLogger(model_name)

# In training loop
logger.log_epoch(epoch, train_loss, train_acc, train_f1,
                 val_loss, val_acc, val_f1)
```

## Examples

See `examples/compression_benchmark_example.py` for complete examples:
- Basic CompressionWriter usage
- Benchmark parser usage
- Multiple models comparison
- Training logger usage

## Documentation

- [User Guide](docs/COMPRESSION_GUIDE.md) - Detailed usage guide
- [API Reference](docs/) - API documentation (coming soon)

## Requirements

- Python 3.9+
- tensorboardX (included)
- tensorboard (for viewing)
- numpy

## License

MIT License (same as tensorboardX)

## Contributing

This project extends tensorboardX for compression-specific use cases. Contributions welcome!

## Related Projects

- [Compression Engine](../compression-engine/) - Model compression engine
- [tensorboardX](https://github.com/lanpa/tensorboardX) - Base library

