#!/usr/bin/env python3
"""
Configuration for compression-focused TensorBoard dashboard.

This module defines which TensorBoard tabs/views are most relevant for
compression analysis and provides default settings.
"""

# TensorBoard tabs that are relevant for compression visualization
RELEVANT_TABS = [
    'SCALARS',      # Compression metrics, training curves, comparisons
    'HISTOGRAMS',   # Latency distributions (if available)
    'HPARAMS',      # Compression configurations (future)
]

# TensorBoard tabs that are less relevant for compression
LESS_RELEVANT_TABS = [
    'IMAGES',       # Not typically used for compression analysis
    'AUDIO',        # Not used for compression
    'TEXT',         # Only for metadata summaries
    'GRAPHS',       # Model architecture graphs (less relevant)
    'EMBEDDINGS',   # Not used for compression
    'MESH',         # Not used for compression
]

# Default tag organization for compression metrics
COMPRESSION_TAG_PATTERNS = [
    '{model_name}/accuracy',           # Accuracy comparisons
    '{model_name}/latency',            # Latency comparisons
    '{model_name}/model_size',        # Size comparisons
    '{model_name}/compression/',      # Compression ratios
    '{model_name}/training/',         # Training metrics
    '{model_name}/validation/',       # Validation metrics
    '{model_name}/energy',            # Energy consumption
    '{model_name}/memory_usage',      # Memory usage
]

# Default view settings
DEFAULT_SETTINGS = {
    'reload_interval': 30,  # Reload data every 30 seconds
    'samples_per_plugin': 500,  # Show up to 500 samples per plugin
}

# Compression-specific scalar groups for easy comparison
SCALAR_GROUPS = {
    'accuracy': ['fp32', 'int8'],
    'latency': ['fp32', 'int8'],
    'model_size': ['fp32', 'int8'],
    'memory_usage': ['fp32', 'int8'],
    'energy': ['fp32', 'int8'],
    'loss': ['train', 'val'],
    'f1_score': ['train', 'val'],
}

