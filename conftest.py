"""Pytest configuration for AgentOS"""
import sys
import os
from pathlib import Path

# CRITICAL: Add project root to Python path BEFORE any other imports
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set environment for development testing
os.environ['AGENTOS_ENV'] = 'testing'

# Verify imports work
try:
    import security.video_validator
    import security.path_sanitizer
    import security.resource_limiter
except ImportError as e:
    print(f"CONFTEST ERROR: Failed to import security modules: {e}")
    print(f"sys.path: {sys.path}")
    raise