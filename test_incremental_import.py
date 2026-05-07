#!/usr/bin/env python3
"""Incremental import test to isolate issue."""

import sys
import os

def main():
    print("=== Incremental Import Test ===")
    print(f"Python version: {sys.version}")
    
    try:
        # Test 1: Basic import
        print("Test 1: Basic import...")
        print("✅ Basic Python working")
        
        # Test 2: Add current directory to path
        print("Test 2: Add current directory to path...")
        sys.path.insert(0, os.getcwd())
        print("✅ Path updated")
        
        # Test 3: Try importing baseball module step by step
        print("Test 3: Try baseball.core.db...")
        try:
            from baseball.core.db import get_db_connection
            print("✅ baseball.core.db imported")
        except Exception as e:
            print(f"❌ baseball.core.db failed: {e}")
            
        print("Test 4: Try baseball.models.schemas...")
        try:
            from baseball.models.schemas import SimulationType
            print("✅ baseball.models.schemas imported")
        except Exception as e:
            print(f"❌ baseball.models.schemas failed: {e}")
            
        print("Test 5: Try baseball.cli...")
        try:
            from baseball.cli import app
            print("✅ baseball.cli imported")
        except Exception as e:
            print(f"❌ baseball.cli failed: {e}")
            import traceback
            traceback.print_exc()
        
        return 0
        
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())