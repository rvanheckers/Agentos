#!/bin/bash
# Scalene Comprehensive Profiling Script
# ========================================
# CPU + Memory + GPU profiling with AI-powered optimization suggestions
#
# Usage: bash profiling/run_scalene.sh [video_path]
#
# Features:
# - Line-by-line CPU profiling
# - Memory allocation tracking
# - GPU usage monitoring (NVIDIA only)
# - AI-powered optimization recommendations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/profiling_results"

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

# Get video path from argument or use default
VIDEO_PATH="${1:-$PROJECT_ROOT/io/input/video_1751932054.mp4}"

if [ ! -f "$VIDEO_PATH" ]; then
    echo "❌ Error: Video file not found: $VIDEO_PATH"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HTML_OUTPUT="$RESULTS_DIR/scalene_report_${TIMESTAMP}.html"
JSON_OUTPUT="$RESULTS_DIR/scalene_report_${TIMESTAMP}.json"

echo "=================================="
echo "Scalene Comprehensive Profiling"
echo "=================================="
echo "Video: $VIDEO_PATH"
echo "HTML Output: $HTML_OUTPUT"
echo "JSON Output: $JSON_OUTPUT"
echo "=================================="
echo ""
echo "Starting comprehensive profiling... (this will take several minutes)"
echo ""

# Run Scalene with comprehensive settings
# --html: Generate HTML report with visualizations
# --json: Also save JSON for programmatic analysis
# --cpu-only: Disable GPU profiling if no NVIDIA GPU available (comment out if you have one)
# --reduced-profile: Only show lines with non-zero activity
scalene \
    --html \
    --outfile "$HTML_OUTPUT" \
    --json \
    --profile-all \
    --reduced-profile \
    --cpu-percent-threshold 1 \
    --malloc-threshold 100 \
    "$PROJECT_ROOT/profiling/profile_agentos.py" "$VIDEO_PATH"

# Also save JSON output
scalene \
    --json \
    --outfile "$JSON_OUTPUT" \
    --profile-all \
    --reduced-profile \
    --cpu-percent-threshold 1 \
    --malloc-threshold 100 \
    "$PROJECT_ROOT/profiling/profile_agentos.py" "$VIDEO_PATH" 2>/dev/null || true

echo ""
echo "✅ Profiling complete!"
echo ""
echo "HTML Report: $HTML_OUTPUT"
echo "JSON Report: $JSON_OUTPUT"
echo ""
echo "To view:"
echo "  1. Open $HTML_OUTPUT in a web browser"
echo "  2. Review the sparklines for memory trends"
echo "  3. Look for:"
echo "     - High 'Time Python %' (CPU bottlenecks)"
echo "     - High 'Memory Python' (memory allocation hotspots)"
echo "     - Growing memory trends (potential leaks)"
echo "     - High 'Copy (MB/s)' (data transfer between Python/C)"
echo ""
echo "Key metrics to examine:"
echo "  - Time Python: Time spent in Python code"
echo "  - native: Time spent in C/C++ libraries (OpenCV, numpy)"
echo "  - system: Time spent in OS calls (I/O bottlenecks)"
echo "  - Memory Python: Memory allocated by Python"
echo "  - net: Net memory allocation/deallocation"
echo ""