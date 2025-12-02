#!/usr/bin/env python3
"""
Training metrics logger for compression engine training loops.

This module provides functionality to log per-epoch training metrics
during model training, including loss, accuracy, F1 scores, and early
stopping information.
"""

from typing import Optional, Dict, List, Union
from ..compression import CompressionWriter


class TrainingLogger:
    """Logger for training metrics during model training.
    
    Integrates with compression engine's training loop to log per-epoch
    metrics including training/validation loss, accuracy, F1 scores, and
    early stopping information.
    
    Example:
        >>> logger = TrainingLogger('runs/training/alexnet')
        >>> for epoch in range(num_epochs):
        ...     train_loss, train_acc, train_f1 = train_epoch(...)
        ...     val_loss, val_acc, val_f1 = validate_epoch(...)
        ...     logger.log_epoch(epoch, train_loss, train_acc, train_f1,
        ...                      val_loss, val_acc, val_f1)
        >>> logger.close()
    """
    
    def __init__(
        self,
        model_name: str,
        writer: Optional[CompressionWriter] = None,
        logdir: Optional[str] = None
    ):
        """Initialize TrainingLogger.
        
        Args:
            model_name: Name of the model being trained
            writer: Optional CompressionWriter instance. If None, creates a new one.
            logdir: Directory for TensorBoard logs (default: runs/training/{model_name})
        """
        self.model_name = model_name
        
        if writer is None:
            if logdir is None:
                logdir = f'runs/training/{model_name}'
            self.writer = CompressionWriter(logdir=logdir)
        else:
            self.writer = writer
        
        self.best_val_f1 = 0.0
        self.best_epoch = 0
    
    def log_epoch(
        self,
        epoch: int,
        train_loss: float,
        train_acc: float,
        train_f1: float,
        val_loss: float,
        val_acc: float,
        val_f1: float,
        train_sensitivity: Optional[float] = None,
        train_specificity: Optional[float] = None,
        val_sensitivity: Optional[float] = None,
        val_specificity: Optional[float] = None,
        learning_rate: Optional[float] = None
    ) -> None:
        """Log metrics for a single training epoch.
        
        Args:
            epoch: Current epoch number
            train_loss: Training loss
            train_acc: Training accuracy
            train_f1: Training F1 score
            val_loss: Validation loss
            val_acc: Validation accuracy
            val_f1: Validation F1 score
            train_sensitivity: Training sensitivity (optional)
            train_specificity: Training specificity (optional)
            val_sensitivity: Validation sensitivity (optional)
            val_specificity: Validation specificity (optional)
            learning_rate: Current learning rate (optional)
        """
        # Log training metrics
        self.writer.add_scalar(f'{self.model_name}/training/loss', train_loss, epoch)
        self.writer.add_scalar(f'{self.model_name}/training/accuracy', train_acc, epoch)
        self.writer.add_scalar(f'{self.model_name}/training/f1_score', train_f1, epoch)
        
        # Log validation metrics
        self.writer.add_scalar(f'{self.model_name}/validation/loss', val_loss, epoch)
        self.writer.add_scalar(f'{self.model_name}/validation/accuracy', val_acc, epoch)
        self.writer.add_scalar(f'{self.model_name}/validation/f1_score', val_f1, epoch)
        
        # Log training/validation comparison
        self.writer.add_scalars(
            f'{self.model_name}/loss',
            {'train': train_loss, 'val': val_loss},
            epoch
        )
        self.writer.add_scalars(
            f'{self.model_name}/accuracy',
            {'train': train_acc, 'val': val_acc},
            epoch
        )
        self.writer.add_scalars(
            f'{self.model_name}/f1_score',
            {'train': train_f1, 'val': val_f1},
            epoch
        )
        
        # Log sensitivity and specificity if provided
        if train_sensitivity is not None:
            self.writer.add_scalar(f'{self.model_name}/training/sensitivity', train_sensitivity, epoch)
        if train_specificity is not None:
            self.writer.add_scalar(f'{self.model_name}/training/specificity', train_specificity, epoch)
        if val_sensitivity is not None:
            self.writer.add_scalar(f'{self.model_name}/validation/sensitivity', val_sensitivity, epoch)
        if val_specificity is not None:
            self.writer.add_scalar(f'{self.model_name}/validation/specificity', val_specificity, epoch)
        
        # Log learning rate if provided
        if learning_rate is not None:
            self.writer.add_scalar(f'{self.model_name}/training/learning_rate', learning_rate, epoch)
        
        # Track best validation F1
        if val_f1 > self.best_val_f1:
            self.best_val_f1 = val_f1
            self.best_epoch = epoch
    
    def log_early_stopping(
        self,
        epoch: int,
        patience: int,
        min_delta: float,
        stopped: bool
    ) -> None:
        """Log early stopping information.
        
        Args:
            epoch: Current epoch number
            patience: Patience parameter for early stopping
            min_delta: Minimum delta for improvement
            stopped: Whether early stopping was triggered
        """
        # Log early stopping parameters
        self.writer.add_scalar(f'{self.model_name}/training/early_stopping_patience', patience, epoch)
        self.writer.add_scalar(f'{self.model_name}/training/early_stopping_min_delta', min_delta, epoch)
        self.writer.add_scalar(f'{self.model_name}/training/early_stopped', 1 if stopped else 0, epoch)
        
        # Log best epoch information
        self.writer.add_scalar(f'{self.model_name}/training/best_epoch', self.best_epoch, epoch)
        self.writer.add_scalar(f'{self.model_name}/training/best_val_f1', self.best_val_f1, epoch)
    
    def log_training_summary(
        self,
        total_epochs: int,
        final_train_loss: float,
        final_train_acc: float,
        final_train_f1: float,
        final_val_loss: float,
        final_val_acc: float,
        final_val_f1: float,
        early_stopped: bool = False
    ) -> None:
        """Log training summary at the end of training.
        
        Args:
            total_epochs: Total number of epochs trained
            final_train_loss: Final training loss
            final_train_acc: Final training accuracy
            final_train_f1: Final training F1 score
            final_val_loss: Final validation loss
            final_val_acc: Final validation accuracy
            final_val_f1: Final validation F1 score
            early_stopped: Whether training was stopped early
        """
        summary_text = f"Training Summary for {self.model_name}\n"
        summary_text += f"Total Epochs: {total_epochs}\n"
        summary_text += f"Early Stopped: {early_stopped}\n"
        summary_text += f"Best Epoch: {self.best_epoch}\n"
        summary_text += f"Best Val F1: {self.best_val_f1:.4f}\n"
        summary_text += f"\nFinal Training Metrics:\n"
        summary_text += f"  Loss: {final_train_loss:.4f}\n"
        summary_text += f"  Accuracy: {final_train_acc:.4f}\n"
        summary_text += f"  F1 Score: {final_train_f1:.4f}\n"
        summary_text += f"\nFinal Validation Metrics:\n"
        summary_text += f"  Loss: {final_val_loss:.4f}\n"
        summary_text += f"  Accuracy: {final_val_acc:.4f}\n"
        summary_text += f"  F1 Score: {final_val_f1:.4f}\n"
        
        self.writer.add_text(f'{self.model_name}/training/summary', summary_text, total_epochs)
        
        # Log final metrics at a special step
        final_step = total_epochs + 1
        self.writer.add_scalar(f'{self.model_name}/training/final_train_loss', final_train_loss, final_step)
        self.writer.add_scalar(f'{self.model_name}/training/final_train_acc', final_train_acc, final_step)
        self.writer.add_scalar(f'{self.model_name}/training/final_train_f1', final_train_f1, final_step)
        self.writer.add_scalar(f'{self.model_name}/validation/final_val_loss', final_val_loss, final_step)
        self.writer.add_scalar(f'{self.model_name}/validation/final_val_acc', final_val_acc, final_step)
        self.writer.add_scalar(f'{self.model_name}/validation/final_val_f1', final_val_f1, final_step)
    
    def close(self) -> None:
        """Close the writer and flush all pending writes."""
        self.writer.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_training_logger(
    model_name: str,
    logdir: Optional[str] = None
) -> TrainingLogger:
    """Convenience function to create a TrainingLogger.
    
    Args:
        model_name: Name of the model being trained
        logdir: Directory for TensorBoard logs (default: runs/training/{model_name})
        
    Returns:
        TrainingLogger instance
        
    Example:
        >>> from tensorboardX.compression.training import create_training_logger
        >>> logger = create_training_logger('alexnet')
        >>> logger.log_epoch(0, 0.5, 0.9, 0.85, 0.4, 0.92, 0.87)
        >>> logger.close()
    """
    return TrainingLogger(model_name, logdir=logdir)

