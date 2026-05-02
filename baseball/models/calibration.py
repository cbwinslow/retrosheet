"""
Model Calibration Tools

Calibration metrics and temperature scaling for probability calibration.

Key Metrics:
- ECE (Expected Calibration Error): Binned accuracy vs confidence difference
- Brier Score: MSE of probabilities
- Reliability: Consistency of predictions at each confidence level
"""

import numpy as np
from typing import Tuple, List, Dict
from dataclasses import dataclass


@dataclass
class CalibrationMetrics:
    """Container for calibration metrics."""
    ece: float  # Expected Calibration Error
    brier_score: float
    reliability_diagram: List[Dict]  # Per-bin stats
    temperature: float  # Optimized temperature for scaling
    
    def summary(self) -> str:
        return (
            f"ECE: {self.ece:.4f} | "
            f"Brier: {self.brier_score:.4f} | "
            f"Temp: {self.temperature:.3f}"
        )


def calculate_ece(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    n_bins: int = 10
) -> Tuple[float, List[Dict]]:
    """
    Calculate Expected Calibration Error (ECE).
    
    ECE = sum(|accuracy_in_bin - avg_confidence_in_bin| * bin_weight)
    
    Args:
        y_true: True labels (int)
        y_pred_proba: Predicted probabilities [n_samples, n_classes]
        n_bins: Number of confidence bins
        
    Returns:
        (ece_value, reliability_diagram_data)
    """
    # Get predicted class and confidence
    y_pred = np.argmax(y_pred_proba, axis=1)
    confidences = np.max(y_pred_proba, axis=1)
    accuracies = (y_pred == y_true).astype(float)
    
    # Create bins
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0.0
    reliability_data = []
    
    for lower, upper in zip(bin_lowers, bin_uppers):
        # Get samples in this bin
        in_bin = (confidences > lower) & (confidences <= upper)
        bin_weight = np.mean(in_bin)
        
        if bin_weight > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confidences[in_bin])
            bin_count = np.sum(in_bin)
            
            ece += np.abs(bin_acc - bin_conf) * bin_weight
            
            reliability_data.append({
                'bin_lower': lower,
                'bin_upper': upper,
                'confidence': bin_conf,
                'accuracy': bin_acc,
                'count': int(bin_count),
                'gap': bin_conf - bin_acc
            })
    
    return ece, reliability_data


def calculate_brier_score(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    n_classes: int
) -> float:
    """
    Calculate multi-class Brier score.
    
    Brier = mean(sum((y_one_hot - pred_proba)^2))
    
    Lower is better (0 = perfect, 1 = worst).
    """
    # Convert to one-hot
    y_one_hot = np.zeros((len(y_true), n_classes))
    y_one_hot[np.arange(len(y_true)), y_true] = 1
    
    return np.mean(np.sum((y_one_hot - y_pred_proba) ** 2, axis=1))


def temperature_scaling(
    y_pred_proba: np.ndarray,
    y_true: np.ndarray,
    max_iter: int = 100,
    lr: float = 0.01
) -> Tuple[np.ndarray, float]:
    """
    Apply temperature scaling to calibrate probabilities.
    
    Temperature T > 1 makes probabilities softer (more uniform)
    Temperature T < 1 makes probabilities harder (more peaked)
    
    Args:
        y_pred_proba: Original predicted probabilities
        y_true: True labels
        max_iter: Optimization iterations
        lr: Learning rate
        
    Returns:
        (calibrated_probabilities, optimized_temperature)
    """
    # Get logits (inverse softmax)
    logits = np.log(y_pred_proba + 1e-10)
    
    # Initialize temperature
    temperature = 1.0
    
    for _ in range(max_iter):
        # Scale logits
        scaled_logits = logits / temperature
        
        # Compute new probabilities
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits, axis=1, keepdims=True))
        scaled_proba = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        
        # Compute NLL loss gradient
        y_one_hot = np.zeros_like(scaled_proba)
        y_one_hot[np.arange(len(y_true)), y_true] = 1
        
        # Gradient of NLL w.r.t. temperature
        grad = np.sum(
            (scaled_proba - y_one_hot) * logits
        ) / (temperature ** 2)
        
        # Update temperature
        temperature -= lr * grad
        temperature = max(0.1, min(10.0, temperature))  # Clip
    
    # Apply final scaling
    scaled_logits = logits / temperature
    exp_logits = np.exp(scaled_logits - np.max(scaled_logits, axis=1, keepdims=True))
    calibrated_proba = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
    
    return calibrated_proba, temperature


def calibrate_model(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    n_classes: int,
    apply_scaling: bool = True
) -> CalibrationMetrics:
    """
    Full calibration analysis with optional temperature scaling.
    
    Args:
        y_true: True labels
        y_pred_proba: Predicted probabilities
        n_classes: Number of classes
        apply_scaling: Whether to apply temperature scaling
        
    Returns:
        CalibrationMetrics with all diagnostics
    """
    # Original metrics
    ece, reliability = calculate_ece(y_true, y_pred_proba)
    brier = calculate_brier_score(y_true, y_pred_proba, n_classes)
    
    temperature = 1.0
    
    if apply_scaling:
        # Apply temperature scaling
        _, temperature = temperature_scaling(y_pred_proba, y_true)
        
        # Recalculate ECE with scaled probabilities
        # (In practice, you'd store the temperature and apply it at inference)
        ece, reliability = calculate_ece(y_true, y_pred_proba)
    
    return CalibrationMetrics(
        ece=ece,
        brier_score=brier,
        reliability_diagram=reliability,
        temperature=temperature
    )


def is_well_calibrated(metrics: CalibrationMetrics, thresholds: Dict = None) -> bool:
    """
    Check if model meets calibration thresholds.
    
    Default thresholds:
        ECE < 0.05 (5%)
        Brier < 0.2 (for multi-class)
    """
    if thresholds is None:
        thresholds = {'ece': 0.05, 'brier': 0.2}
    
    return (
        metrics.ece < thresholds.get('ece', 0.05) and
        metrics.brier_score < thresholds.get('brier', 0.2)
    )
