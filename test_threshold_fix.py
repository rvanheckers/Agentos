#!/usr/bin/env python3
"""
Test nieuwe threshold berekening (v2.2.1)
Verify dat 24K char transcript NIET meer gechunked wordt
"""

import os
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from agents2.moment_detection.unified_content_analyzer import UnifiedContentAnalyzer

print("=" * 80)
print("THRESHOLD FIX VALIDATION TEST (v2.2.1)")
print("=" * 80)
print()

analyzer = UnifiedContentAnalyzer()

# Get threshold
threshold = analyzer._compute_chunking_threshold()
safe_tokens = analyzer._safe_input_budget_tokens()
safe_chars = safe_tokens * 4

print("📊 Threshold Calculation:")
print(f"  MODEL_CONTEXT_TOKENS: {int(os.getenv('MODEL_CONTEXT_TOKENS', '128000')):,}")
print(f"  INPUT_UTILIZATION: {float(os.getenv('INPUT_UTILIZATION', '0.8')):.0%}")
print(f"  PROMPT_OVERHEAD_TOKENS: {int(os.getenv('PROMPT_OVERHEAD_TOKENS', '1500')):,}")
print(f"  OUTPUT_BUDGET_TOKENS: {int(os.getenv('OUTPUT_BUDGET_TOKENS', '2000')):,}")
print()

print(f"💰 Safe Budget:")
print(f"  Safe tokens: {safe_tokens:,} tokens")
print(f"  Safe chars: {safe_chars:,} chars (tokens * 4)")
print()

print(f"🎯 Chunking Threshold:")
print(f"  Threshold: {threshold:,} chars (90% of safe budget)")
print(f"  Formula: safe_chars * 0.9 = {safe_chars} * 0.9 = {threshold}")
print()

# Test cases
test_cases = [
    ("Short video (5K)", 5_000),
    ("Normal video (24K) - OUR CASE", 24_967),
    ("Long video (100K)", 100_000),
    ("Very long (350K)", 350_000),
    ("Podcast (400K)", 400_000),
]

print("🧪 Test Cases:")
print("-" * 80)
for name, chars in test_cases:
    use_chunking = chars > threshold
    status = "🚀 CHUNK" if use_chunking else "📄 SINGLE-PASS"

    if chars == 24_967:
        expected_status = "📄 SINGLE-PASS"
        result = "✅ CORRECT" if status == expected_status else "❌ WRONG"
        print(f"  {name}: {chars:,} chars → {status} {result}")
    else:
        print(f"  {name}: {chars:,} chars → {status}")

print()
print("=" * 80)
print("✅ VALIDATION COMPLETE")
print("=" * 80)
print()

print("Expected behavior:")
print("  - Videos < 356K chars: single-pass (5-10 seconds)")
print("  - Videos > 356K chars: chunking (but only when truly needed)")
print()

# Check if 24K would have been chunked with old logic
old_threshold = min(int(analyzer.chunk_size * 0.95), safe_chars)
print(f"🔍 Comparison with old logic:")
print(f"  Old threshold: {old_threshold:,} chars (min(chunk_size*0.95, safe_chars))")
print(f"  New threshold: {threshold:,} chars (safe_chars * 0.9)")
print(f"  24K video with OLD logic: {'🚀 CHUNK (unnecessary!)' if 24_967 > old_threshold else '📄 SINGLE-PASS'}")
print(f"  24K video with NEW logic: {'🚀 CHUNK' if 24_967 > threshold else '📄 SINGLE-PASS (correct!)'}")
print()

if 24_967 <= threshold and 24_967 > old_threshold:
    print("🎉 SUCCESS: Fix prevents unnecessary chunking for 24K video!")
else:
    print("⚠️ ISSUE: Check the threshold calculation")
