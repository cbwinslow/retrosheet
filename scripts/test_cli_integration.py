#!/usr/bin/env python3
"""
CLI Integration Test Suite

Verifies all baseball CLI commands are properly registered and functional.

Usage:
    python scripts/test_cli_integration.py
    python scripts/test_cli_integration.py --verbose
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a CLI command and return exit code, stdout, stderr."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )
    return result.returncode, result.stdout, result.stderr


def test_baseball_help():
    """Test main baseball CLI help."""
    code, stdout, stderr = run_command([sys.executable, '-m', 'baseball', '--help'])
    
    assert code == 0, f"Help failed: {stderr}"
    assert 'predict' in stdout.lower(), "predict command not in help"
    assert 'live' in stdout.lower(), "live command not in help"
    assert 'ingest' in stdout.lower(), "ingest command not in help"
    print("✓ Main CLI help works")


def test_predict_help():
    """Test predict subcommand help."""
    code, stdout, stderr = run_command([sys.executable, '-m', 'baseball', 'predict', '--help'])
    
    assert code == 0, f"Predict help failed: {stderr}"
    assert 'game' in stdout.lower(), "game command not in predict"
    assert 'today' in stdout.lower() or 'live' in stdout.lower(), "prediction commands missing"
    print("✓ Predict subcommand works")


def test_live_help():
    """Test live subcommand help."""
    code, stdout, stderr = run_command([sys.executable, '-m', 'baseball', 'live', '--help'])
    
    assert code == 0, f"Live help failed: {stderr}"
    assert 'games' in stdout.lower(), "games command not in live"
    assert 'watch' in stdout.lower(), "watch command not in live"
    assert 'poll' in stdout.lower(), "poll command not in live"
    assert 'next-pitch' in stdout.lower(), "next-pitch command not in live"
    print("✓ Live subcommand works")


def test_namespace_imports():
    """Test that baseball namespace exports work."""
    try:
        import baseball
        
        # Check key exports exist
        assert hasattr(baseball, 'LivePredictionEngine'), "LivePredictionEngine not exported"
        assert hasattr(baseball, 'MarkovPitchPredictor'), "MarkovPitchPredictor not exported"
        assert hasattr(baseball, 'Prediction'), "Prediction not exported"
        assert hasattr(baseball, 'get_prediction_engine'), "get_prediction_engine not exported"
        
        print("✓ Baseball namespace exports work")
    except Exception as e:
        print(f"✗ Namespace import failed: {e}")
        raise


def test_predictions_module():
    """Test predictions module structure."""
    try:
        from baseball import predictions
        
        assert hasattr(predictions, 'LivePredictionEngine'), "LivePredictionEngine not in predictions"
        assert hasattr(predictions, 'MarkovPitchPredictor'), "MarkovPitchPredictor not in predictions"
        assert hasattr(predictions, 'Prediction'), "Prediction not in predictions"
        assert hasattr(predictions, 'PredictionType'), "PredictionType not in predictions"
        
        print("✓ Predictions module structure correct")
    except Exception as e:
        print(f"✗ Predictions module failed: {e}")
        raise


def main():
    print("=" * 60)
    print("BASEBALL CLI INTEGRATION TESTS")
    print("=" * 60)
    
    tests = [
        test_namespace_imports,
        test_predictions_module,
        test_baseball_help,
        test_predict_help,
        test_live_help,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
