#!/usr/bin/env python3
"""
Test runner script for the advanced testing infrastructure.

This script validates that our testing infrastructure components work correctly
and provides a quick way to verify the testing setup.
"""

import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, description, timeout=300):
    """Run a command and handle the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED ({duration:.2f}s)")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
        else:
            print(f"❌ {description} - FAILED ({duration:.2f}s)")
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT ({timeout}s)")
        return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False
    
    return True

def main():
    """Main test runner."""
    print("🧪 Advanced Testing Infrastructure Validation")
    print("=" * 60)
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    tests = [
        # Basic infrastructure tests
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestBaseClasses -v",
            "desc": "Base Test Classes Validation"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestDataFactories -v",
            "desc": "Data Factory Validation"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestPerformanceTimer -v",
            "desc": "Performance Timer Validation"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestDataValidator -v",
            "desc": "Data Validator Validation"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestDataComparator -v",
            "desc": "Data Comparator Validation"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestDataManipulator -v",
            "desc": "Data Manipulator Validation"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestConcurrencyTester -v",
            "desc": "Concurrency Tester Validation"
        },
        
        # Advanced testing features
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestPerformanceMarkers -v",
            "desc": "Performance Testing Markers"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestPropertyBasedTesting -v",
            "desc": "Property-Based Testing"
        },
        {
            "cmd": "python -m pytest tests/test_infrastructure.py::TestIntegrationScenarios -v",
            "desc": "Integration Testing Scenarios"
        },
        
        # Import validation
        {
            "cmd": "python -c \"from tests.base import *; from tests.factories import *; from tests.utils import *; print('All imports successful')\"",
            "desc": "Import Validation"
        },
        
        # Configuration validation
        {
            "cmd": "python -c \"import pytest; print('Pytest configuration loaded successfully')\"",
            "desc": "Pytest Configuration Validation"
        },
    ]
    
    # Run all tests
    passed = 0
    failed = 0
    
    for test in tests:
        if run_command(test["cmd"], test["desc"]):
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("🏁 TEST SUMMARY")
    print('='*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All infrastructure tests passed!")
        print("The advanced testing infrastructure is ready for use.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed.")
        print("Please address the issues before using the infrastructure.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
