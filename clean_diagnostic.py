#!/usr/bin/env python3
"""Simple diagnostic script to collect system information."""

import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    print("=== SYSTEM DIAGNOSTIC REPORT ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version}")
    print(f"Current Directory: {os.getcwd()}")
    print(f"User: {os.getenv('USER', 'unknown')}")
    print(f"Shell: {os.getenv('SHELL', 'unknown')}")
    print()
    
    # Test basic file operations
    print("=== FILE SYSTEM TESTS ===")
    try:
        test_file = "/tmp/diagnostic_test.txt"
        with open(test_file, 'w') as f:
            f.write("test")
        print("✓ File write successful")
        
        with open(test_file, 'r') as f:
            content = f.read()
        print("✓ File read successful")
        
        os.remove(test_file)
        print("✓ File delete successful")
    except Exception as e:
        print(f"✗ File operation failed: {e}")
    print()
    
    # Test directory listing
    print("=== DIRECTORY TESTS ===")
    try:
        files = list(Path('.').iterdir())[:10]
        print(f"✓ Current directory has {len(files)}+ files")
        for f in files[:5]:
            print(f"  - {f.name}")
    except Exception as e:
        print(f"✗ Directory listing failed: {e}")
    print()
    
    # Test baseball CLI import
    print("=== BASEBALL CLI TESTS ===")
    try:
        sys.path.insert(0, '.')
        from baseball.cli.main import app
        print("✓ Baseball CLI imported successfully")
    except Exception as e:
        print(f"✗ Baseball CLI import failed: {e}")
    print()
    
    # Test simple command execution
    print("=== COMMAND EXECUTION TESTS ===")
    try:
        result = subprocess.run("echo 'test'", shell=True, capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print(f"✓ Echo command successful: '{result.stdout.strip()}'")
        else:
            print(f"✗ Echo command failed: {result.stderr.strip()}")
    except Exception as e:
        print(f"✗ Echo command failed: {e}")
    
    try:
        result = subprocess.run("pwd", shell=True, capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print(f"✓ PWD command successful: '{result.stdout.strip()}'")
        else:
            print(f"✗ PWD command failed: {result.stderr.strip()}")
    except Exception as e:
        print(f"✗ PWD command failed: {e}")
    print()
    
    print("=== END DIAGNOSTIC REPORT ===")

if __name__ == "__main__":
    main()
