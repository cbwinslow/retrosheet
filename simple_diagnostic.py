#!/usr/bin/env python3
"""Simple diagnostic script to collect system information."""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, timeout=5):
    """Run a command with timeout and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

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
    
    # Test Python imports
    print("=== PYTHON IMPORT TESTS ===")
    try:
        import os
        print("✓ os module imported")
    except Exception as e:
        print(f"✗ os import failed: {e}")
    
    try:
        import sys
        print("✓ sys module imported")
    except Exception as e:
        print(f"✗ sys import failed: {e}")
    
    try:
        import subprocess
        print("✓ subprocess module imported")
    except Exception as e:
        print(f"✗ subprocess import failed: {e}")
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
    stdout, stderr, returncode = run_command("echo 'test'", timeout=2)
    if returncode == 0:
        print(f"✓ Echo command successful: '{stdout}'")
    else:
        print(f"✗ Echo command failed: {stderr}")
    
    stdout, stderr, returncode = run_command("pwd", timeout=2)
    if returncode == 0:
        print(f"✓ PWD command successful: '{stdout}'")
    else:
        print(f"✗ PWD command failed: {stderr}")
    print()
    
    print("=== END DIAGNOSTIC REPORT ===")

if __name__ == "__main__":
    main()
