#!/bin/bash
# Run security tests with correct Python path

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
source "${PROJECT_ROOT}/venv/bin/activate"

# Set PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Run pytest
python -m pytest "${PROJECT_ROOT}/tests/test_security/" -v --disable-warnings --tb=short "$@"