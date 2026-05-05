#!/usr/bin/env python3
"""Process investigation script to identify hanging or problematic processes."""

import os
import sys
import time
import subprocess
from pathlib import Path

def run_command_safe(cmd, timeout=3):
    """Run a command safely with short timeout."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 1
    except Exception as e:
        return "", str(e), 1

def main():
    print("=== PROCESS INVESTIGATION REPORT ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current PID: {os.getpid()}")
    print(f"Current User: {os.getenv('USER', 'unknown')}")
    print()
    
    # Check Python processes specifically
    print("=== PYTHON PROCESSES ===")
    stdout, stderr, returncode = run_command_safe("ps aux | grep python | grep -v grep", timeout=2)
    if returncode == 0 and stdout:
        print("Found Python processes:")
        for line in stdout.split('\n')[:10]:  # Show first 10
            print(f"  {line}")
    else:
        print("No Python processes found or command failed")
    print()
    
    # Check processes by CPU usage
    print("=== TOP CPU PROCESSES ===")
    stdout, stderr, returncode = run_command_safe("ps aux --sort=-%cpu | head -11", timeout=2)
    if returncode == 0 and stdout:
        print("Top CPU-consuming processes:")
        for line in stdout.split('\n'):
            print(f"  {line}")
    else:
        print("Failed to get CPU process info")
    print()
    
    # Check processes by memory usage
    print("=== TOP MEMORY PROCESSES ===")
    stdout, stderr, returncode = run_command_safe("ps aux --sort=-%mem | head -11", timeout=2)
    if returncode == 0 and stdout:
        print("Top memory-consuming processes:")
        for line in stdout.split('\n'):
            print(f"  {line}")
    else:
        print("Failed to get memory process info")
    print()
    
    # Check for zombie processes
    print("=== ZOMBIE PROCESSES ===")
    stdout, stderr, returncode = run_command_safe("ps aux | awk '$8 ~ /^Z/ {print $2, $11}'", timeout=2)
    if returncode == 0 and stdout:
        print("Found zombie processes:")
        for line in stdout.split('\n'):
            if line.strip():
                print(f"  {line}")
    else:
        print("No zombie processes found or command failed")
    print()
    
    # Check for defunct processes
    print("=== DEFUNCT PROCESSES ===")
    stdout, stderr, returncode = run_command_safe("ps aux | grep defunct", timeout=2)
    if returncode == 0 and stdout:
        print("Found defunct processes:")
        for line in stdout.split('\n'):
            if line.strip():
                print(f"  {line}")
    else:
        print("No defunct processes found or command failed")
    print()
    
    # Check for hanging baseball-related processes
    print("=== BASEBALL-RELATED PROCESSES ===")
    stdout, stderr, returncode = run_command_safe("ps aux | grep -i baseball | grep -v grep", timeout=2)
    if returncode == 0 and stdout:
        print("Found baseball-related processes:")
        for line in stdout.split('\n'):
            if line.strip():
                print(f"  {line}")
    else:
        print("No baseball-related processes found or command failed")
    print()
    
    # Check system load
    print("=== SYSTEM LOAD ===")
    stdout, stderr, returncode = run_command_safe("uptime", timeout=2)
    if returncode == 0 and stdout:
        print(f"System uptime/load: {stdout}")
    else:
        print("Failed to get uptime info")
    print()
    
    # Check total process count
    print("=== PROCESS COUNT ===")
    stdout, stderr, returncode = run_command_safe("ps aux | wc -l", timeout=2)
    if returncode == 0 and stdout:
        print(f"Total processes: {stdout.strip()}")
    else:
        print("Failed to get process count")
    print()
    
    print("=== END PROCESS INVESTIGATION ===")

if __name__ == "__main__":
    main()
