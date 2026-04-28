#!/usr/bin/env python3
"""
File: scripts/vector/install_faiss_check.py
Purpose: Check if faiss-cpu is installed and provide installation instructions
Author: Agent KiloSwift
Date: 2026-04-27
Usage: uv run python scripts/vector/install_faiss_check.py
Dependencies: faiss-cpu (optional), numpy
Notes: faiss-cpu is used for vector similarity search on player embeddings
"""

import importlib

import importlib
import subprocess
import sys
from pathlib import Path

def check_faiss_installation() -> bool:
    """Check if faiss-cpu is importable."""
    try:
        importlib.import_module('faiss')
        return True
    except ImportError:
        return False

def main():
    print("faiss-cpu Installation Check")
    print("=" * 40)

    if check_faiss_installation():
        print("✅ faiss-cpu is installed and importable.")
        import faiss
        print(f"   Version: {faiss.__version__ if hasattr(faiss, '__version__') else 'unknown'}")
        return 0
    else:
        print("⚠️  faiss-cpu is NOT installed.")
        print("\n📦 Installation Options:")
        print("\n   Option 1: Install faiss-cpu via pip (CPU-only, simpler)")
        print("   $ uv add faiss-cpu")
        print("   OR")
        print("   $ pip install faiss-cpu")
        print("\n   Option 2: Install faiss-gpu (requires CUDA)")
        print("   $ uv add faiss-gpu")
        print("\n📚 Use cases in this project:")
        print("   - Player embedding similarity search (pgvector companion)")
        print("   - Fast nearest-neighbor lookup for real-time predictions")
        print("   - Clustering players by performance features")
        print("   - Pitch sequence similarity search")
        print("\n🔗 See docs/vector/FAISS_INTEGRATION.md for usage examples.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
