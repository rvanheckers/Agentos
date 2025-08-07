#!/bin/bash

# 🧪 Jobs & Queue Test Runner
# Hergebruikt bestaande Python test scripts

echo "🧪 Jobs & Queue Test Suite"
echo "=========================="
echo "Hergebruikt bestaande AgentOS test scripts"
echo ""

cd "$(dirname "$0")/../.."

# Test 1: SSOT Performance (bevat queue data)
echo "📊 Running SSOT Performance Test..."
python3 test_ssot_performance.py

echo ""

# Test 2: Database Real Data (bevat job creation)  
echo "🗄️  Running Database Real Data Test..."
python3 test_database_real_data.py

echo ""

# Test 3: SSOT Scale (bevat concurrent admin UI access)
echo "🚀 Running SSOT Scale Test..."
python3 test_ssot_scale.py

echo ""

# Test 4: Onze custom Jobs & Queue test
echo "🎯 Running Custom Jobs & Queue Test..."
python3 testing/jobs-queue/test_jobs_queue.py

echo ""
echo "✅ All Jobs & Queue tests completed!"
echo "💡 Voor individuele tests: gebruik de originele scripts in de root directory"