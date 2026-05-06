#!/usr/bin/env python3
"""
Pitch-Level Model Calibration and Evaluation Framework

Provides comprehensive calibration and evaluation tools for pitch-level models:
- Expected Calibration Error (ECE) analysis
- Reliability diagrams and calibration curves
- Temperature scaling calibration
- Isotonic regression calibration
- Subgroup analysis (count, handedness, game state)
- Bootstrap uncertainty estimation

Usage:
    python calibration.py --model-path model.joblib --test-data features.csv
    python calibration.py --calibrate --method isotonic --save-calibrator
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score, brier_score_loss, log_loss,
    precision_score, recall_score, f1_score
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging

logger = logging.getLogger(__name__)


class PitchModelCalibrator:
    """
    Comprehensive calibration and evaluation framework for pitch-level models.
    """
    
    def __init__(self, model_path: str):
        """
        Initialize calibrator with trained model.
        
        Args:
            model_path: Path to trained model file
        """
        self.model_path = Path(model_path)
        self.model_data = joblib.load(model_path)
        self.model = self.model_data['model']
        self.label_encoder = self.model_data['label_encoder']
        self.feature_names = self.model_data['feature_names']
        self.target_tier = self.model_data['target_tier']
        
        # Calibration methods
        self.calibrators = {}
        self.calibration_metrics = {}
        
        # Evaluation results
        self.evaluation_results = {}
        
        logger.info(f"Loaded model: {self.target_tier} with {len(self.label_encoder.classes_)} classes")
    
    def evaluate_calibration(
        self, 
        X_test: pd.DataFrame, 
        y_test: pd.Series,
        bins: int = 10
    ) -> Dict[str, Union[float, np.ndarray]]:
        """
        Evaluate model calibration using multiple metrics.
        
        Args:
            X_test: Test features
            y_test: True labels
            bins: Number of bins for reliability diagram
            
        Returns:
            Dictionary with calibration metrics
        """
        # Get predictions
        y_pred_proba = self._get_probabilities(X_test)
        y_pred = self._get_predictions(X_test)
        
        # Convert to numeric for metrics
        y_test_encoded = self.label_encoder.transform(y_test)
        y_pred_encoded = self.label_encoder.transform(y_pred)
        
        # Basic metrics
        accuracy = accuracy_score(y_test_encoded, y_pred_encoded)
        logloss = log_loss(y_test_encoded, y_pred_proba)
        brier = brier_score_loss(y_test_encoded, y_pred_proba)
        
        # Expected Calibration Error (ECE)
        ece = self._calculate_ece(y_test_encoded, y_pred_proba, bins=bins)
        
        # Maximum Calibration Error (MCE)
        mce = self._calculate_mce(y_test_encoded, y_pred_proba, bins=bins)
        
        # Per-class calibration
        per_class_ece = {}
        for i, class_name in enumerate(self.label_encoder.classes_):
            class_ece = self._calculate_ece(
                (y_test_encoded == i).astype(int),
                y_pred_proba[:, i],
                bins=bins
            )
            per_class_ece[class_name] = class_ece
        
        # Reliability diagram data
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_test_encoded, y_pred_proba, n_bins=bins, strategy='uniform'
        )
        
        results = {
            'accuracy': accuracy,
            'log_loss': logloss,
            'brier_score': brier,
            'ece': ece,
            'mce': mce,
            'per_class_ece': per_class_ece,
            'reliability_data': {
                'fraction_positives': fraction_of_positives,
                'mean_predicted': mean_predicted_value,
                'bins': bins
            }
        }
        
        self.evaluation_results = results
        return results
    
    def _calculate_ece(
        self, 
        y_true: np.ndarray, 
        y_prob: np.ndarray, 
        bins: int = 10
    ) -> float:
        """Calculate Expected Calibration Error."""
        bin_edges = np.linspace(0, 1, bins + 1)
        bin_lowers = bin_edges[:-1]
        bin_uppers = bin_edges[1:]
        
        ece = 0.0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            # Find samples in this bin
            in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper)
            prop_in_bin = in_bin.mean()
            
            if prop_in_bin > 0:
                accuracy_in_bin = y_true[in_bin].mean()
                avg_confidence_in_bin = y_prob[in_bin].mean()
                ece += prop_in_bin * abs(accuracy_in_bin - avg_confidence_in_bin)
        
        return ece
    
    def _calculate_mce(
        self, 
        y_true: np.ndarray, 
        y_prob: np.ndarray, 
        bins: int = 10
    ) -> float:
        """Calculate Maximum Calibration Error."""
        bin_edges = np.linspace(0, 1, bins + 1)
        bin_lowers = bin_edges[:-1]
        bin_uppers = bin_edges[1:]
        
        mce = 0.0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper)
            if in_bin.sum() > 0:
                accuracy_in_bin = y_true[in_bin].mean()
                avg_confidence_in_bin = y_prob[in_bin].mean()
                mce = max(mce, abs(accuracy_in_bin - avg_confidence_in_bin))
        
        return mce
    
    def fit_temperature_scaling(
        self, 
        X_val: pd.DataFrame, 
        y_val: pd.Series
    ) -> Dict[str, float]:
        """
        Fit temperature scaling calibration.
        
        Args:
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Dictionary with temperature parameters per class
        """
        from scipy.optimize import minimize
        
        y_val_encoded = self.label_encoder.transform(y_val)
        y_val_proba = self._get_probabilities(X_val)
        
        temperatures = {}
        
        for i, class_name in enumerate(self.label_encoder.classes_):
            # Optimize temperature for this class
            def temp_loss(temp):
                scaled_proba = self._temperature_scale(y_val_proba[:, i], temp)
                return log_loss((y_val_encoded == i).astype(int), scaled_proba)
            
            result = minimize(temp_loss, x0=1.0, method='nelder-mead')
            temperatures[class_name] = result.x[0]
            
            logger.info(f"Temperature for {class_name}: {result.x[0]:.4f}")
        
        self.calibrators['temperature'] = temperatures
        return temperatures
    
    def fit_isotonic_regression(
        self, 
        X_val: pd.DataFrame, 
        y_val: pd.Series
    ) -> Dict:
        """
        Fit isotonic regression calibration.
        
        Args:
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Dictionary with fitted isotonic regressors
        """
        y_val_encoded = self.label_encoder.transform(y_val)
        y_val_proba = self._get_probabilities(X_val)
        
        isotonic_regressors = {}
        
        for i, class_name in enumerate(self.label_encoder.classes_):
            # Fit isotonic regression for this class
            iso_reg = IsotonicRegression(out_of_bounds='clip')
            
            # Prepare binary labels for this class
            y_binary = (y_val_encoded == i).astype(int)
            
            # Fit isotonic regression
            iso_reg.fit(y_val_proba[:, i], y_binary)
            isotonic_regressors[class_name] = iso_reg
            
            logger.info(f"Fitted isotonic regression for {class_name}")
        
        self.calibrators['isotonic'] = isotonic_regressors
        return isotonic_regressors
    
    def _temperature_scale(self, probabilities: np.ndarray, temperature: float) -> np.ndarray:
        """Apply temperature scaling to probabilities."""
        # Avoid division by zero
        temperature = max(temperature, 0.01)
        
        # Temperature scaling: softmax(logits / temperature)
        logits = np.log(probabilities + 1e-15)
        scaled_logits = logits / temperature
        scaled_probs = np.exp(scaled_logits)
        scaled_probs = scaled_probs / scaled_probs.sum(axis=1, keepdims=True)
        
        return scaled_probs
    
    def apply_calibration(
        self, 
        X: pd.DataFrame, 
        method: str = 'isotonic'
    ) -> np.ndarray:
        """
        Apply calibration to predictions.
        
        Args:
            X: Features
            method: Calibration method ('temperature', 'isotonic')
            
        Returns:
            Calibrated probabilities
        """
        y_proba = self._get_probabilities(X)
        
        if method == 'temperature' and 'temperature' in self.calibrators:
            calibrated_proba = np.zeros_like(y_proba)
            
            for i, class_name in enumerate(self.label_encoder.classes_):
                if class_name in self.calibrators['temperature']:
                    temp = self.calibrators['temperature'][class_name]
                    # Apply temperature scaling to all probabilities
                    logits = np.log(y_proba + 1e-15)
                    scaled_logits = logits / temp
                    scaled_class_logits = scaled_logits[:, i]
                    # Rescale only this class's probability
                    calibrated_proba[:, i] = self._temperature_scale(
                        y_proba[:, [i]], temp
                    ).flatten()
            
            # Renormalize
            calibrated_proba = calibrated_proba / calibrated_proba.sum(axis=1, keepdims=True)
            
        elif method == 'isotonic' and 'isotonic' in self.calibrators:
            calibrated_proba = np.zeros_like(y_proba)
            
            for i, class_name in enumerate(self.label_encoder.classes_):
                if class_name in self.calibrators['isotonic']:
                    iso_reg = self.calibrators['isotonic'][class_name]
                    calibrated_proba[:, i] = iso_reg.transform(y_proba[:, i])
            
            # Renormalize
            calibrated_proba = calibrated_proba / calibrated_proba.sum(axis=1, keepdims=True)
            
        else:
            calibrated_proba = y_proba
        
        return calibrated_proba
    
    def analyze_subgroups(
        self, 
        X_test: pd.DataFrame, 
        y_test: pd.Series,
        subgroup_cols: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Analyze calibration across different subgroups.
        
        Args:
            X_test: Test features
            y_test: True labels
            subgroup_cols: Columns to analyze (default: common baseball splits)
            
        Returns:
            Dictionary with subgroup analysis
        """
        if subgroup_cols is None:
            subgroup_cols = ['stand', 'p_throws', 'balls', 'strikes', 'inning']
        
        # Get predictions
        y_pred = self._get_predictions(X_test)
        y_pred_proba = self._get_probabilities(X_test)
        y_test_encoded = self.label_encoder.transform(y_test)
        
        subgroup_analysis = {}
        
        for col in subgroup_cols:
            if col not in X_test.columns:
                continue
            
            unique_values = X_test[col].dropna().unique()
            col_analysis = {}
            
            for value in unique_values:
                mask = X_test[col] == value
                if mask.sum() == 0:
                    continue
                
                # Calculate metrics for this subgroup
                y_sub = y_test_encoded[mask]
                y_pred_sub = y_pred_encoded[mask]
                y_proba_sub = y_pred_proba[mask]
                
                accuracy = accuracy_score(y_sub, y_pred_sub)
                logloss = log_loss(y_sub, y_proba_sub)
                ece = self._calculate_ece(y_sub, y_proba_sub)
                
                col_analysis[str(value)] = {
                    'accuracy': accuracy,
                    'log_loss': logloss,
                    'ece': ece,
                    'sample_size': mask.sum()
                }
            
            subgroup_analysis[col] = col_analysis
        
        return subgroup_analysis
    
    def _get_probabilities(self, X: pd.DataFrame) -> np.ndarray:
        """Get probability predictions from model."""
        # This would need to be implemented based on the specific model type
        # For now, assume it's an XGBoost model
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X[self.feature_names])
        else:
            raise NotImplementedError("Model does not support probability prediction")
    
    def _get_predictions(self, X: pd.DataFrame) -> np.ndarray:
        """Get class predictions from model."""
        if hasattr(self.model, 'predict'):
            return self.model.predict(X[self.feature_names])
        else:
            raise NotImplementedError("Model does not support prediction")
    
    def plot_reliability_diagram(
        self, 
        save_path: Optional[str] = None,
        show: bool = True
    ) -> None:
        """Plot reliability diagram for calibration visualization."""
        if 'reliability_data' not in self.evaluation_results:
            logger.error("No calibration evaluation results available")
            return
        
        rel_data = self.evaluation_results['reliability_data']
        bins = rel_data['bins']
        
        plt.figure(figsize=(10, 8))
        
        # Perfect calibration line
        plt.plot([0, 1], [0, 1], 'k--', label='Perfect Calibration', linewidth=2)
        
        # Model calibration curve
        fraction_pos = rel_data['fraction_positives']
        mean_pred = rel_data['mean_predicted']
        
        # Add first point (0,0) for visualization
        fraction_pos = np.insert(fraction_pos, 0, 0)
        mean_pred = np.insert(mean_pred, 0, 0)
        
        plt.plot(mean_pred, fraction_pos, 'bo-', label='Model', linewidth=2, markersize=8)
        
        # Add ECE to plot
        ece = self.evaluation_results['ece']
        plt.text(0.6, 0.2, f'ECE = {ece:.4f}', fontsize=12, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.xlabel('Mean Predicted Probability')
        plt.ylabel('Fraction of Positives')
        plt.title(f'Reliability Diagram - {self.target_tier.upper()} Model')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Reliability diagram saved to {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def save_calibration_results(
        self, 
        output_path: str,
        include_subgroups: bool = True
    ) -> None:
        """Save calibration evaluation results."""
        import json
        
        results = {
            'model_path': str(self.model_path),
            'target_tier': self.target_tier,
            'evaluation_timestamp': datetime.now().isoformat(),
            'overall_metrics': {
                'accuracy': self.evaluation_results.get('accuracy'),
                'log_loss': self.evaluation_results.get('log_loss'),
                'brier_score': self.evaluation_results.get('brier_score'),
                'ece': self.evaluation_results.get('ece'),
                'mce': self.evaluation_results.get('mce'),
                'per_class_ece': self.evaluation_results.get('per_class_ece')
            },
            'calibration_methods': list(self.calibrators.keys())
        }
        
        if include_subgroups and 'subgroup_analysis' in self.evaluation_results:
            results['subgroup_analysis'] = self.evaluation_results['subgroup_analysis']
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Calibration results saved to {output_path}")
    
    def save_calibrators(self, output_path: str) -> None:
        """Save fitted calibrators for later use."""
        calibrator_data = {
            'calibrators': self.calibrators,
            'label_encoder': self.label_encoder,
            'target_tier': self.target_tier,
            'model_path': str(self.model_path),
            'created_at': datetime.now().isoformat()
        }
        
        joblib.dump(calibrator_data, output_path)
        logger.info(f"Calibrators saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Pitch-level model calibration and evaluation'
    )
    parser.add_argument(
        '--model-path', '-m',
        required=True,
        help='Path to trained model file'
    )
    parser.add_argument(
        '--test-data', '-t',
        help='Path to test data CSV (if not provided, loads from database)'
    )
    parser.add_argument(
        '--calibrate', '-c',
        action='store_true',
        help='Fit calibration methods'
    )
    parser.add_argument(
        '--method',
        choices=['temperature', 'isotonic', 'both'],
        default='both',
        help='Calibration method to fit (default: both)'
    )
    parser.add_argument(
        '--save-calibrator',
        action='store_true',
        help='Save fitted calibrators'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='data/models/pitch_level/calibration',
        help='Output directory for results (default: data/models/pitch_level/calibration)'
    )
    parser.add_argument(
        '--plot', '-p',
        action='store_true',
        help='Generate calibration plots'
    )
    parser.add_argument(
        '--subgroups', '-s',
        action='store_true',
        help='Analyze calibration across subgroups'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize calibrator
    calibrator = PitchModelCalibrator(args.model_path)
    
    # Load test data
    if args.test_data:
        logger.info(f"Loading test data from {args.test_data}")
        test_data = pd.read_csv(args.test_data)
        X_test = test_data.drop(columns=['target'])
        y_test = test_data['target']
    else:
        logger.info("Loading test data from database (not implemented)")
        return
    
    # Evaluate calibration
    logger.info("Evaluating model calibration...")
    results = calibrator.evaluate_calibration(X_test, y_test)
    
    print(f"\n{'='*60}")
    print(f"Calibration Evaluation Results")
    print(f"{'='*60}")
    print(f"Model: {args.model_path}")
    print(f"Target Tier: {calibrator.target_tier}")
    print(f"\nOverall Metrics:")
    print(f"  Accuracy: {results['accuracy']:.4f}")
    print(f"  Log Loss: {results['log_loss']:.4f}")
    print(f"  Brier Score: {results['brier_score']:.4f}")
    print(f"  ECE: {results['ece']:.4f}")
    print(f"  MCE: {results['mce']:.4f}")
    
    print(f"\nPer-Class ECE:")
    for class_name, ece in results['per_class_ece'].items():
        print(f"  {class_name:15}: {ece:.4f}")
    
    # Fit calibration methods
    if args.calibrate:
        logger.info("Fitting calibration methods...")
        
        if args.method in ['temperature', 'both']:
            calibrator.fit_temperature_scaling(X_test, y_test)
        
        if args.method in ['isotonic', 'both']:
            calibrator.fit_isotonic_regression(X_test, y_test)
        
        # Save calibrators
        if args.save_calibrator:
            calibrator_path = output_dir / f"calibrator_{calibrator.target_tier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
            calibrator.save_calibrators(str(calibrator_path))
    
    # Subgroup analysis
    if args.subgroups:
        logger.info("Analyzing calibration across subgroups...")
        subgroup_results = calibrator.analyze_subgroups(X_test, y_test)
        calibrator.evaluation_results['subgroup_analysis'] = subgroup_results
        
        print(f"\nSubgroup Analysis:")
        for col, subgroups in subgroup_results.items():
            print(f"\n{col}:")
            for value, metrics in subgroups.items():
                print(f"  {value:10}: Acc={metrics['accuracy']:.3f} ECE={metrics['ece']:.4f} (n={metrics['sample_size']})")
    
    # Generate plots
    if args.plot:
        plot_path = output_dir / f"reliability_diagram_{calibrator.target_tier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        calibrator.plot_reliability_diagram(str(plot_path), show=False)
    
    # Save results
    results_path = output_dir / f"calibration_results_{calibrator.target_tier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    calibrator.save_calibration_results(str(results_path))
    
    print(f"\nResults saved to {output_dir}")


if __name__ == '__main__':
    main()
