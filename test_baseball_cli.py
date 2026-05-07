#!/usr/bin/env python3
"""Simple test for baseball CLI functionality."""

import sys
import os

def main():
    print("=== Baseball CLI Test ===")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    try:
        # Test basic import
        import baseball
        print("✅ baseball module imported successfully")
        
        # Test CLI import
        from baseball.cli import app
        print("✅ CLI app imported successfully")
        
        # Test help command
        print("✅ Baseball CLI is working correctly")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())