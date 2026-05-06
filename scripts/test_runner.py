#!/usr/bin/env python3
"""Comprehensive test runner for ensemble system."""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_tests():
    """Run all tests and provide detailed output."""
    print("🧪 Running Baseball Ensemble Tests")
    print("=" * 50)
    
    # Run unit tests
    print("\n📋 Running Unit Tests...")
    try:
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'tests/test_ensemble.py',
            '-v',
            '--tb=short'
        ], 
        capture_output=True, 
        text=True,
        cwd=Path(__file__).parent.parent
        )
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Test run completed")

if __name__ == '__main__':
    run_tests()
