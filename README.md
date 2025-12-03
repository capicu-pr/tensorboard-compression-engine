# TensorBoard Compression Plugin

[![PyPI version](https://badge.fury.io/py/tensorboardX.svg)](https://badge.fury.io/py/tensorboardX)

A TensorBoard plugin for visualizing and analyzing model compression metrics with dynamic theme support, interactive charts, and comprehensive metrics visualization.

## 🎯 Compression Plugin

The **COMPRESSION** plugin provides a dedicated TensorBoard tab for visualizing and analyzing model compression metrics with:

- **📊 Interactive Pareto Charts**: Visualize accuracy vs. model size, latency, memory, and energy consumption
- **📋 Comprehensive Tables**: View relative metrics (ratios) and raw metrics (FP32/INT8 comparisons)
- **🎨 Dynamic Theme Support**: Automatically matches TensorBoard's light/dark theme
- **🔍 Run Filtering**: Sidebar with search and selection for comparing multiple models
- **📥 Data Export**: Export compression data to CSV

### Quick Start

```bash
# Clone this repository
git clone https://github.com/capicu-pr/tensorboard-compression-engine.git

# Install the compression plugin
pip install -e compression_board_plugin/

# Start TensorBoard with your log directory
tensorboard --logdir runs/compression_benchmark

# Open http://localhost:6006 and navigate to the COMPRESSION tab
```

### Data Format

The plugin expects TensorBoard scalar metrics with the following tag structure:

```
{model_name}/metrics/accuracy/fp32
{model_name}/metrics/accuracy/int8
{model_name}/compression/speedup
{model_name}/compression/size_ratio
{model_name}/compression/accuracy_drop
{model_name}/performance/model_size_mb/fp32
{model_name}/performance/model_size_mb/int8
{model_name}/performance/latency_ms/fp32
{model_name}/performance/latency_ms/int8
{model_name}/performance/energy_mw/fp32
{model_name}/performance/energy_mw/int8
```

### Usage Examples

#### Logging Compression Metrics

```python
from tensorboardX import SummaryWriter

writer = SummaryWriter('runs/compression_benchmark')

# Log FP32 metrics
writer.add_scalar('alexnet/metrics/accuracy/fp32', 0.95, 0)
writer.add_scalar('alexnet/performance/model_size_mb/fp32', 217.61, 0)
writer.add_scalar('alexnet/performance/latency_ms/fp32', 261.02, 0)

# Log INT8 metrics
writer.add_scalar('alexnet/metrics/accuracy/int8', 0.94, 0)
writer.add_scalar('alexnet/performance/model_size_mb/int8', 54.40, 0)
writer.add_scalar('alexnet/performance/latency_ms/int8', 65.25, 0)

# Log compression metrics
writer.add_scalar('alexnet/compression/speedup', 4.0, 0)
writer.add_scalar('alexnet/compression/size_ratio', 4.0, 0)
writer.add_scalar('alexnet/compression/accuracy_drop', 0.01, 0)

writer.close()
```

#### Using CompressionWriter (if available)

```python
from tensorboardX.compression import CompressionWriter

writer = CompressionWriter('runs/my_experiment')

# Log FP32 vs INT8 comparison
writer.log_compression_comparison('alexnet', fp32_metrics, int8_metrics)

# Log compression ratios
writer.log_compression_ratios('alexnet', fp32_metrics, int8_metrics)

writer.close()
```

### Compression Metrics

#### Tag Organization

Metrics are organized hierarchically:
- `{model_name}/metrics/accuracy/fp32` - FP32 accuracy
- `{model_name}/metrics/accuracy/int8` - INT8 accuracy
- `{model_name}/compression/size_ratio` - Compression ratio
- `{model_name}/compression/speedup` - Speedup factor
- `{model_name}/compression/accuracy_drop` - Accuracy drop
- `{model_name}/performance/` - Performance metrics (latency, model size, energy, memory)

#### Key Metrics

- **Compression Ratio**: `fp32_size / int8_size`
- **Speedup**: `fp32_latency / int8_latency`
- **Accuracy Drop**: `fp32_accuracy - int8_accuracy`
- **Size Reduction**: Percentage reduction in model size

---

## tensorboardX

This repository extends [tensorboardX](https://github.com/lanpa/tensorboardX) with compression-specific features. The base tensorboardX functionality is fully preserved.

Write TensorBoard events with simple function call.

The current release (v2.6.3) is tested with PyTorch 2.6 / torchvision 0.21.0 / tensorboard 2.19.0 on Python 3.9 to 3.12

* Support `scalar`, `image`, `figure`, `histogram`, `audio`, `text`, `graph`, `onnx_graph`, `embedding`, `pr_curve`, `mesh`, `hyper-parameters`
  and `video` summaries.

* [FAQ](https://github.com/lanpa/tensorboardX/wiki)

## Install

### Base tensorboardX

`pip install tensorboardX`

or build from source:

`pip install 'git+https://github.com/lanpa/tensorboardX'`

You can optionally install [`crc32c`](https://github.com/ICRAR/crc32c) to speed up.

`pip install crc32c`

Starting from tensorboardX 2.1, You need to install `soundfile` for the `add_audio()` function (200x speedup).

`pip install soundfile`

### Compression Plugin

```bash
# Install the compression plugin
cd compression_board_plugin/
pip install -e .
```

## Example

* Clone the files in https://github.com/lanpa/tensorboardX/tree/master/examples
* Run the demo script: e.g. `python examples/demo.py`
* Start TensorBoard with `tensorboard --logdir runs`  

```python
# demo.py

import torch
import torchvision.utils as vutils
import numpy as np
import torchvision.models as models
from torchvision import datasets
from tensorboardX import SummaryWriter

resnet18 = models.resnet18(False)
writer = SummaryWriter()
sample_rate = 44100
freqs = [262, 294, 330, 349, 392, 440, 440, 440, 440, 440, 440]

for n_iter in range(100):

    dummy_s1 = torch.rand(1)
    dummy_s2 = torch.rand(1)
    # data grouping by `slash`
    writer.add_scalar('data/scalar1', dummy_s1[0], n_iter)
    writer.add_scalar('data/scalar2', dummy_s2[0], n_iter)

    writer.add_scalars('data/scalar_group', {'xsinx': n_iter * np.sin(n_iter),
                                             'xcosx': n_iter * np.cos(n_iter),
                                             'arctanx': np.arctan(n_iter)}, n_iter)

    dummy_img = torch.rand(32, 3, 64, 64)  # output from network
    if n_iter % 10 == 0:
        x = vutils.make_grid(dummy_img, normalize=True, scale_each=True)
        writer.add_image('Image', x, n_iter)

        dummy_audio = torch.zeros(sample_rate * 2)
        for i in range(x.size(0)):
            # amplitude of sound should in [-1, 1]
            dummy_audio[i] = np.cos(freqs[n_iter // 10] * np.pi * float(i) / float(sample_rate))
        writer.add_audio('myAudio', dummy_audio, n_iter, sample_rate=sample_rate)

        writer.add_text('Text', 'text logged at step:' + str(n_iter), n_iter)

        for name, param in resnet18.named_parameters():
            writer.add_histogram(name, param.clone().cpu().data.numpy(), n_iter)

        # needs tensorboard 0.4RC or later
        writer.add_pr_curve('xoxo', np.random.randint(2, size=100), np.random.rand(100), n_iter)

dataset = datasets.MNIST('mnist', train=False, download=True)
images = dataset.test_data[:100].float()
label = dataset.test_labels[:100]

features = images.view(100, 784)
writer.add_embedding(features, metadata=label, label_img=images.unsqueeze(1))

# export scalar data to JSON for external processing
writer.export_scalars_to_json("./all_scalars.json")
writer.close()
```

## Screenshots

<img src="screenshots/Demo.gif">

## Using TensorboardX with Comet

TensorboardX now supports logging directly to [Comet](https://www.comet.com/site/products/ml-experiment-tracking/?utm_source=tensorboardx&utm_medium=partner&utm_campaign=partner_tensorboardx_2023). Comet is a **free** cloud based solution that allows you to automatically track, compare and explain your experiments. It adds a lot of functionality on top of tensorboard such as dataset management, diffing experiments, seeing the code that generated the results and more.

This works out of the box and just require an additional line of code. See a full code example in this [Colab Notebook](https://colab.research.google.com/drive/1cTO3tgZ03nuJQ8kOjZhEiwbB-45tV4lm?usp=sharing)

<p align="center">
<img src="screenshots/comet.gif" width="750" height="400">
</p>

## Tweaks

To add more ticks for the slider (show more image history), check https://github.com/lanpa/tensorboardX/issues/44 or 
https://github.com/tensorflow/tensorboard/pull/1138

## Reference

* [TeamHG-Memex/tensorboard_logger](https://github.com/TeamHG-Memex/tensorboard_logger)
* [dmlc/tensorboard](https://github.com/dmlc/tensorboard)

## License

MIT License

## Contributing

This project extends tensorboardX for compression-specific use cases. Contributions welcome!

## Related Projects

* [tensorboardX](https://github.com/lanpa/tensorboardX) - Base library
