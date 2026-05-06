#!/usr/bin/env python3
"""Simple environment test to work around bash issues."""

import sys
print("Environment test running...")
print(f"Python version: {sys.version}")
print("If you see this, Python execution is working!")

try:
    import baseball
    print("Baseball module imported successfully!")
    print(f"Baseball version: {baseball.__version__}")
except ImportError as e:
    print(f"Baseball import failed: {e}")

print("Environment test complete.")