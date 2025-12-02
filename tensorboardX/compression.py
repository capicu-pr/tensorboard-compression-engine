#!/usr/bin/env python3
"""
Compression-specific TensorBoard writer for model compression visualization.

This module provides a CompressionWriter class that extends SummaryWriter
with compression-specific logging methods for FP32 vs INT8 comparisons,
compression ratios, and model metadata.
"""

from typing import Dict, Optional, Union
import numpy as np
from .writer import SummaryWriter


class CompressionWriter(SummaryWriter):
    """Specialized SummaryWriter for compression metrics visualization.
    
    Extends SummaryWriter with compression-specific methods for logging
    FP32 vs INT8 comparisons, compression ratios, speedups, and model metadata.
    Uses hierarchical tag structure optimized for compression analysis.
    
    Example:
        >>> writer = CompressionWriter('runs/compression')
        >>> writer.log_compression_comparison('alexnet', fp32_metrics, int8_metrics)
        >>> writer.log_compression_ratios('alexnet', fp32_metrics, int8_metrics)
        >>> writer.close()
    """
    
    def log_compression_comparison(
        self,
        model_name: str,
        fp32_metrics: Dict[str, Union[float, int]],
        int8_metrics: Dict[str, Union[float, int]],
        step: int = 0,
    ) -> None:
        """Log FP32 vs INT8 metrics side-by-side for comparison.

        NOTE: We intentionally avoid :meth:`add_scalars` here, since
        tensorboardX implements it by creating a new ``FileWriter`` per
        sub-tag, which shows up in TensorBoard as multiple *runs*. For
        compression benchmarks we want one run per model, so we only use
        :meth:`add_scalar` with fully-qualified tag names.
        """
        # Accuracy metrics
        if "accuracy" in fp32_metrics and "accuracy" in int8_metrics:
            self.add_scalar(
                f"{model_name}/metrics/accuracy/fp32",
                fp32_metrics["accuracy"],
                step,
            )
            self.add_scalar(
                f"{model_name}/metrics/accuracy/int8",
                int8_metrics["accuracy"],
                step,
            )

        # F1 Score
        if "f1_score" in fp32_metrics and "f1_score" in int8_metrics:
            self.add_scalar(
                f"{model_name}/metrics/f1_score/fp32",
                fp32_metrics["f1_score"],
                step,
            )
            self.add_scalar(
                f"{model_name}/metrics/f1_score/int8",
                int8_metrics["f1_score"],
                step,
            )

        # Latency (mean)
        if "latency_mean_ms" in fp32_metrics and "latency_mean_ms" in int8_metrics:
            self.add_scalar(
                f"{model_name}/performance/latency_ms/fp32",
                fp32_metrics["latency_mean_ms"],
                step,
            )
            self.add_scalar(
                f"{model_name}/performance/latency_ms/int8",
                int8_metrics["latency_mean_ms"],
                step,
            )

        # Model size
        if "model_size_mb" in fp32_metrics and "model_size_mb" in int8_metrics:
            self.add_scalar(
                f"{model_name}/performance/model_size_mb/fp32",
                fp32_metrics["model_size_mb"],
                step,
            )
            self.add_scalar(
                f"{model_name}/performance/model_size_mb/int8",
                int8_metrics["model_size_mb"],
                step,
            )

        # Memory usage
        if "memory_usage_mb" in fp32_metrics and "memory_usage_mb" in int8_metrics:
            self.add_scalar(
                f"{model_name}/performance/memory_usage_mb/fp32",
                fp32_metrics["memory_usage_mb"],
                step,
            )
            self.add_scalar(
                f"{model_name}/performance/memory_usage_mb/int8",
                int8_metrics["memory_usage_mb"],
                step,
            )

        # Loss
        if "loss" in fp32_metrics and "loss" in int8_metrics:
            self.add_scalar(
                f"{model_name}/metrics/loss/fp32",
                fp32_metrics["loss"],
                step,
            )
            self.add_scalar(
                f"{model_name}/metrics/loss/int8",
                int8_metrics["loss"],
                step,
            )
    
    def log_compression_ratios(
        self,
        model_name: str,
        fp32_metrics: Dict[str, Union[float, int]],
        int8_metrics: Dict[str, Union[float, int]],
        step: int = 0
    ) -> None:
        """Calculate and log compression ratios (size, latency, memory).
        
        Args:
            model_name: Name of the model
            fp32_metrics: Dictionary of FP32 metrics
            int8_metrics: Dictionary of INT8 metrics
            step: Global step for logging (default: 0)
        """
        # Size compression ratio
        if "model_size_mb" in fp32_metrics and "model_size_mb" in int8_metrics:
            fp32_size = fp32_metrics["model_size_mb"]
            int8_size = int8_metrics["model_size_mb"]
            if int8_size > 0:
                size_ratio = fp32_size / int8_size
                self.add_scalar(
                    f"{model_name}/compression/size_ratio", size_ratio, step
                )
                
                # Size reduction percentage
                size_reduction = ((fp32_size - int8_size) / fp32_size) * 100
                self.add_scalar(
                    f"{model_name}/compression/size_reduction_pct",
                    size_reduction,
                    step,
                )
        
        # Latency speedup
        if "latency_mean_ms" in fp32_metrics and "latency_mean_ms" in int8_metrics:
            fp32_latency = fp32_metrics["latency_mean_ms"]
            int8_latency = int8_metrics["latency_mean_ms"]
            if int8_latency > 0:
                speedup = fp32_latency / int8_latency
                self.add_scalar(f"{model_name}/compression/speedup", speedup, step)
        
        # Memory reduction
        if "memory_usage_mb" in fp32_metrics and "memory_usage_mb" in int8_metrics:
            fp32_memory = fp32_metrics["memory_usage_mb"]
            int8_memory = int8_metrics["memory_usage_mb"]
            memory_reduction = fp32_memory - int8_memory
            self.add_scalar(
                f"{model_name}/compression/memory_reduction_mb",
                memory_reduction,
                step,
            )
        
        # Accuracy drop
        if "accuracy" in fp32_metrics and "accuracy" in int8_metrics:
            accuracy_drop = fp32_metrics["accuracy"] - int8_metrics["accuracy"]
            self.add_scalar(
                f"{model_name}/compression/accuracy_drop", accuracy_drop, step
            )
            
            # Accuracy retention percentage
            if fp32_metrics["accuracy"] > 0:
                accuracy_retention = (
                    int8_metrics["accuracy"] / fp32_metrics["accuracy"]
                ) * 100
                self.add_scalar(
                    f"{model_name}/compression/accuracy_retention_pct",
                    accuracy_retention,
                    step,
                )
    
    def log_model_metadata(
        self,
        model_name: str,
        model_info: Dict[str, Union[str, list]],
        step: int = 0
    ) -> None:
        """Log model metadata (library, category, input shape, description).
        
        Args:
            model_name: Name of the model
            model_info: Dictionary containing model metadata
            step: Global step for logging (default: 0)
        """
        # Log metadata as text summary
        metadata_text = f"Model: {model_name}\n"
        
        if "library" in model_info:
            metadata_text += f"Library: {model_info['library']}\n"
        
        if "category" in model_info:
            metadata_text += f"Category: {model_info['category']}\n"
        
        if "description" in model_info:
            metadata_text += f"Description: {model_info['description']}\n"
        
        if "input_shape" in model_info:
            input_shape = model_info["input_shape"]
            metadata_text += f"Input Shape: {input_shape}\n"
            # Log input shape dimensions as scalars
            if isinstance(input_shape, list) and len(input_shape) > 0:
                self.add_scalar(
                    f"{model_name}/metadata/input_channels", input_shape[0], step
                )
                if len(input_shape) > 1:
                    self.add_scalar(
                        f"{model_name}/metadata/input_height", input_shape[1], step
                    )
                if len(input_shape) > 2:
                    self.add_scalar(
                        f"{model_name}/metadata/input_width", input_shape[2], step
                    )
        
        self.add_text(f'{model_name}/metadata/info', metadata_text, step)
    
    def log_energy_comparison(
        self,
        model_name: str,
        fp32_metrics: Dict[str, Union[float, int]],
        int8_metrics: Dict[str, Union[float, int]],
        step: int = 0
    ) -> None:
        """Log energy consumption comparison between FP32 and INT8.
        
        Args:
            model_name: Name of the model
            fp32_metrics: Dictionary of FP32 metrics
            int8_metrics: Dictionary of INT8 metrics
            step: Global step for logging (default: 0)
        """
        if "energy_consumption_mw" in fp32_metrics and "energy_consumption_mw" in int8_metrics:
            self.add_scalar(
                f"{model_name}/performance/energy_mw/fp32",
                fp32_metrics["energy_consumption_mw"],
                step,
            )
            self.add_scalar(
                f"{model_name}/performance/energy_mw/int8",
                int8_metrics["energy_consumption_mw"],
                step,
            )
            
            # Energy reduction
            energy_reduction = (
                fp32_metrics["energy_consumption_mw"]
                - int8_metrics["energy_consumption_mw"]
            )
            self.add_scalar(
                f"{model_name}/compression/energy_reduction_mw",
                energy_reduction,
                step,
            )
            
            # Energy efficiency ratio
            if int8_metrics["energy_consumption_mw"] > 0:
                energy_ratio = (
                    fp32_metrics["energy_consumption_mw"]
                    / int8_metrics["energy_consumption_mw"]
                )
                self.add_scalar(
                    f"{model_name}/compression/energy_ratio",
                    energy_ratio,
                    step,
                )
    
    def log_latency_distribution(
        self,
        model_name: str,
        fp32_latencies: np.ndarray,
        int8_latencies: np.ndarray,
        step: int = 0
    ) -> None:
        """Log latency distribution histograms for FP32 and INT8.
        
        Args:
            model_name: Name of the model
            fp32_latencies: Array of FP32 latency measurements
            int8_latencies: Array of INT8 latency measurements
            step: Global step for logging (default: 0)
        """
        self.add_histogram(f'{model_name}/latency_distribution/fp32', fp32_latencies, step)
        self.add_histogram(f'{model_name}/latency_distribution/int8', int8_latencies, step)

