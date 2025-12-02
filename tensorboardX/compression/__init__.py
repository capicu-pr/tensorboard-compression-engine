"""
Compression-specific utilities for TensorBoard visualization.

This package provides tools for visualizing model compression results,
including benchmark parsers and training metrics loggers.
"""

# Import CompressionWriter from the sibling compression.py module
# We need to import it directly from the file to avoid circular import
import importlib.util
from pathlib import Path

_compression_module_path = Path(__file__).parent.parent / 'compression.py'
spec = importlib.util.spec_from_file_location("tensorboardX.compression_module", _compression_module_path)
_compression_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_compression_module)
CompressionWriter = _compression_module.CompressionWriter

from .benchmark import BenchmarkParser, log_benchmark_results
from .training import TrainingLogger, create_training_logger

__all__ = [
    'CompressionWriter',
    'BenchmarkParser',
    'log_benchmark_results',
    'TrainingLogger',
    'create_training_logger',
]

