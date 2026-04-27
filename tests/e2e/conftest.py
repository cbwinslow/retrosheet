"""Pytest configuration for E2E tests.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# Set environment for tests
os.environ.setdefault('PGHOST', 'localhost')
os.environ.setdefault('PGPORT', '5432')
os.environ.setdefault('PGDATABASE', 'retrosheet')
os.environ.setdefault('PGUSER', 'postgres')
