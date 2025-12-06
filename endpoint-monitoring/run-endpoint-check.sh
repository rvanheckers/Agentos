#!/bin/bash
# AgentOS Endpoint Health Check Runner
# Dubbelklik dit bestand om de endpoint check te draaien

echo "🚀 Starting AgentOS Endpoint Health Checker..."
echo ""

# Change to the script directory
cd "$(dirname "$0")"

# Run the Python script
python3 run_endpoint_check.py

# Keep terminal open to see results
echo ""
echo "Press any key to close..."
read -n 1 -s