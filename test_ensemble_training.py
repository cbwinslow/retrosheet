#!/usr/bin/env python3
"""Simple test script for ensemble training functionality."""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from baseball.models.ensemble.training_manager import EnsembleTrainingManager

logging.basicConfig(level=logging.INFO)

def main():
    print("Testing ensemble training manager...")
    
    try:
        manager = EnsembleTrainingManager()
        print("Manager created successfully")
        
        # Test with very small dataset for quick validation
        print("Starting ensemble training with minimal data...")
        results = manager.train_ensemble(
            model_types=['xgboost', 'hist_gb'],
            target_level='pitch',
            seasons=[2015],  # Just one year for testing
            sample_rate=0.001,  # Very small sample
            concurrent=True
        )
        
        print("Ensemble training completed!")
        print("Results summary:")
        print(f"  - Target level: {results['target_level']}")
        print(f"  - Model types: {results['model_types']}")
        
        ensemble_results = results.get('ensemble_results', {})
        if ensemble_results:
            print(f"  - Ensemble accuracy: {ensemble_results.get('ensemble_accuracy', 'N/A')}")
            print(f"  - Best individual accuracy: {ensemble_results.get('best_individual_accuracy', 'N/A')}")
            print(f"  - Improvement: {ensemble_results.get('improvement', 'N/A')}")
        
        individual_results = results.get('individual_results', {})
        for model_type, result in individual_results.items():
            if result.get('status') == 'success':
                metrics = result.get('metrics', {})
                print(f"  - {model_type} accuracy: {metrics.get('accuracy', 'N/A')}")
            else:
                print(f"  - {model_type} failed: {result.get('error', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print(f"Error during ensemble training: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("✅ Ensemble training test successful!")
    else:
        print("❌ Ensemble training test failed!")
