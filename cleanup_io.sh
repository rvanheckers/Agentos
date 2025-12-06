#!/bin/bash
# Quick IO cleanup script - keeps only 3 newest job folders

echo "🧹 Running IO cleanup..."
python scripts/io_cleanup.py "$@"