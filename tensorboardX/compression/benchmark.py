#!/usr/bin/env python3
"""
Benchmark parser for compression engine JSON results.

This module provides functionality to parse compression engine benchmark
results from JSON files and convert them to TensorBoard event format.
"""

import json
import os
from typing import Dict, Optional, Union
from ..compression import CompressionWriter


class BenchmarkParser:
    """Parser for compression engine benchmark JSON results.
    
    Reads JSON files from compression-engine/results/ and converts them
    to TensorBoard events using CompressionWriter.
    
    Example:
        >>> parser = BenchmarkParser()
        >>> parser.log_benchmark_results('compression-engine/results/benchmark.json')
    """
    
    def __init__(self, writer: Optional[CompressionWriter] = None):
        """Initialize BenchmarkParser.
        
        Args:
            writer: Optional CompressionWriter instance. If None, creates a new one.
        """
        self.writer = writer
    
    def load_benchmark_json(self, json_path: str) -> Dict:
        """Load benchmark results from JSON file.
        
        Args:
            json_path: Path to the benchmark JSON file
            
        Returns:
            Dictionary containing benchmark results
            
        Raises:
            FileNotFoundError: If JSON file doesn't exist
            json.JSONDecodeError: If JSON file is invalid
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Benchmark file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            return json.load(f)
    
    def log_benchmark_results(
        self,
        json_path: str,
        logdir: Optional[str] = None,
        step: int = 0,
    ) -> CompressionWriter:
        """Convert benchmark JSON results to TensorBoard events.
        
        Args:
            json_path: Path to the benchmark JSON file
            logdir: Directory for TensorBoard logs (default: runs/compression_benchmark)
            step: Global step for logging (default: 0 for benchmark results)
            
        Returns:
            CompressionWriter instance used for logging
        """
        # Load benchmark data
        benchmark_data = self.load_benchmark_json(json_path)
        
        # Determine base logdir for per-model runs (scalars)
        if logdir is None:
            # Extract filename without extension for logdir name
            base_name = os.path.splitext(os.path.basename(json_path))[0]
            base_logdir = f'runs/compression_benchmark/{base_name}'
        else:
            base_logdir = logdir

        # Separate logdir for HParams dashboard so its runs do NOT pollute
        # the main scalar run list. Users can point TensorBoard at this
        # directory when they want the table view.
        hparams_logdir = f'{base_logdir}_hparams'
        hparams_writer = CompressionWriter(logdir=hparams_logdir)
        
        # Process each model in the benchmark results
        # Create one run per model for better organization in TensorBoard
        writers = []
        for model_name, model_data in benchmark_data.items():
            if not isinstance(model_data, dict):
                continue
            
            # Extract FP32 and INT8 metrics
            fp32_metrics = model_data.get('fp32', {})
            int8_metrics = model_data.get('int8', {})
            model_info = model_data.get('model_info', {})
            
            # Skip if missing required data
            if not fp32_metrics or not int8_metrics:
                continue
            
            # Create a separate writer for each model (one run per model)
            if self.writer is None:
                model_writer = CompressionWriter(logdir=f'{base_logdir}/{model_name}')
            else:
                # If writer provided, use it but still organize by model name in tags
                model_writer = self.writer
            
            # Log compression comparison (side-by-side metrics)
            model_writer.log_compression_comparison(
                model_name, fp32_metrics, int8_metrics, step
            )
            
            # Log compression ratios (derived metrics)
            model_writer.log_compression_ratios(
                model_name, fp32_metrics, int8_metrics, step
            )
            
            # Log energy comparison
            model_writer.log_energy_comparison(
                model_name, fp32_metrics, int8_metrics, step
            )
            
            # Log model metadata
            if model_info:
                model_writer.log_model_metadata(model_name, model_info, step)
            
            # Log additional metrics individually for detailed analysis
            self._log_additional_metrics(model_name, fp32_metrics, int8_metrics, step, model_writer)

            # Log compression metrics as HParams row for dashboard-style view
            # Use a dedicated writer rooted at ``*_hparams`` so these runs
            # live in a separate tree from the main scalar runs.
            self._log_hparams(
                model_name,
                fp32_metrics,
                int8_metrics,
                model_info,
                hparams_writer,
            )
            
            if self.writer is None:
                model_writer.close()
                writers.append(model_writer)
        
        # Return the first writer if using shared writer, or create a dummy return
        if self.writer is not None:
            return self.writer
        elif writers:
            # Return a reference to the last writer for compatibility
            # In practice, all writers are already closed
            return writers[-1]
        else:
            # Create a dummy writer if no models processed
            if logdir is None:
                base_name = os.path.splitext(os.path.basename(json_path))[0]
                logdir = f'runs/compression_benchmark/{base_name}'
            return CompressionWriter(logdir=logdir)
    
    def _log_additional_metrics(
        self,
        model_name: str,
        fp32_metrics: Dict,
        int8_metrics: Dict,
        step: int,
        writer: Optional[CompressionWriter] = None
    ) -> None:
        """Log additional metrics that aren't covered by main methods.
        
        Args:
            model_name: Name of the model
            fp32_metrics: FP32 metrics dictionary
            int8_metrics: INT8 metrics dictionary
            step: Global step for logging
            writer: CompressionWriter to use (defaults to self.writer)
        """
        if writer is None:
            writer = self.writer
        if writer is None:
            return
        
        # Sensitivity and Specificity
        if 'sensitivity' in fp32_metrics and 'sensitivity' in int8_metrics:
            writer.add_scalar(
                f'{model_name}/metrics/sensitivity/fp32',
                fp32_metrics['sensitivity'],
                step,
            )
            writer.add_scalar(
                f'{model_name}/metrics/sensitivity/int8',
                int8_metrics['sensitivity'],
                step,
            )
        
        if 'specificity' in fp32_metrics and 'specificity' in int8_metrics:
            writer.add_scalar(
                f'{model_name}/metrics/specificity/fp32',
                fp32_metrics['specificity'],
                step,
            )
            writer.add_scalar(
                f'{model_name}/metrics/specificity/int8',
                int8_metrics['specificity'],
                step,
            )
        
        # Latency standard deviation
        if 'latency_std_ms' in fp32_metrics and 'latency_std_ms' in int8_metrics:
            writer.add_scalar(
                f'{model_name}/performance/latency_std_ms/fp32',
                fp32_metrics['latency_std_ms'],
                step,
            )
            writer.add_scalar(
                f'{model_name}/performance/latency_std_ms/int8',
                int8_metrics['latency_std_ms'],
                step,
            )
        
        # GPU memory usage (if available)
        if 'gpu_memory_usage_mb' in fp32_metrics and 'gpu_memory_usage_mb' in int8_metrics:
            fp32_gpu = fp32_metrics['gpu_memory_usage_mb']
            int8_gpu = int8_metrics['gpu_memory_usage_mb']
            if fp32_gpu > 0 or int8_gpu > 0:  # Only log if GPU was used
                writer.add_scalar(
                    f'{model_name}/performance/gpu_memory_mb/fp32',
                    fp32_gpu,
                    step,
                )
                writer.add_scalar(
                    f'{model_name}/performance/gpu_memory_mb/int8',
                    int8_gpu,
                    step,
                )
        
        # Evaluation device
        if 'evaluated_on' in fp32_metrics:
            device = fp32_metrics['evaluated_on']
            # Encode device as numeric for visualization
            device_code = 1 if device == 'gpu' else 0
            writer.add_scalar(f'{model_name}/metadata/device_gpu', device_code, step)

    def _log_hparams(
        self,
        model_name: str,
        fp32_metrics: Dict,
        int8_metrics: Dict,
        model_info: Dict,
        hparams_writer: CompressionWriter,
    ) -> None:
        """Log per-model compression metrics using the HParams API.

        This turns the HParams tab into a compression dashboard where each row
        is a model and columns are metrics like accuracy, size_ratio, speedup.
        """
        # Build hparam dict (can contain strings and numbers)
        hparams: Dict[str, Union[str, float, int]] = {
            "model_name": model_name,
        }

        if "library" in model_info:
            hparams["library"] = model_info["library"]
        if "category" in model_info:
            hparams["category"] = model_info["category"]

        # Build metric dict (must be numeric). Prefix with 'hparam/' to keep
        # them separate from regular scalar plots.
        metrics: Dict[str, float] = {}

        acc_fp32 = fp32_metrics.get("accuracy")
        acc_int8 = int8_metrics.get("accuracy")
        if isinstance(acc_fp32, (int, float)):
            metrics["hparam/accuracy_fp32"] = float(acc_fp32)
        if isinstance(acc_int8, (int, float)):
            metrics["hparam/accuracy_int8"] = float(acc_int8)
        if isinstance(acc_fp32, (int, float)) and isinstance(acc_int8, (int, float)):
            metrics["hparam/accuracy_drop"] = float(acc_fp32) - float(acc_int8)

        size_fp32 = fp32_metrics.get("model_size_mb")
        size_int8 = int8_metrics.get("model_size_mb")
        if isinstance(size_fp32, (int, float)) and isinstance(size_int8, (int, float)) and size_int8 > 0:
            metrics["hparam/size_ratio"] = float(size_fp32) / float(size_int8)

        lat_fp32 = fp32_metrics.get("latency_mean_ms")
        lat_int8 = int8_metrics.get("latency_mean_ms")
        if isinstance(lat_fp32, (int, float)) and isinstance(lat_int8, (int, float)) and lat_int8 > 0:
            metrics["hparam/speedup"] = float(lat_fp32) / float(lat_int8)

        mem_fp32 = fp32_metrics.get("memory_usage_mb")
        mem_int8 = int8_metrics.get("memory_usage_mb")
        if isinstance(mem_fp32, (int, float)) and isinstance(mem_int8, (int, float)):
            metrics["hparam/memory_reduction_mb"] = float(mem_fp32) - float(mem_int8)

        energy_fp32 = fp32_metrics.get("energy_consumption_mw")
        energy_int8 = int8_metrics.get("energy_consumption_mw")
        if isinstance(energy_fp32, (int, float)) and isinstance(energy_int8, (int, float)):
            metrics["hparam/energy_reduction_mw"] = float(energy_fp32) - float(energy_int8)

        # If we have no numeric metrics, skip logging hparams for this model
        if not metrics:
            return

        # Use model_name as the hparam session name so each model becomes one
        # row in the HParams table.
        hparams_writer.add_hparams(
            hparam_dict=hparams,
            metric_dict=metrics,
            name=model_name,
        )


def log_benchmark_results(
    json_path: str,
    logdir: Optional[str] = None,
    step: int = 0
) -> CompressionWriter:
    """Convenience function to log benchmark results.
    
    Args:
        json_path: Path to the benchmark JSON file
        logdir: Directory for TensorBoard logs (default: runs/compression_benchmark)
        step: Global step for logging (default: 0)
        
    Returns:
        CompressionWriter instance used for logging
        
    Example:
        >>> from tensorboardX.compression.benchmark import log_benchmark_results
        >>> writer = log_benchmark_results('results/benchmark.json')
        >>> writer.close()
    """
    parser = BenchmarkParser()
    return parser.log_benchmark_results(json_path, logdir, step)

