#!/bin/bash
# py-spy CPU Profiling Script
# ===========================
# Production-safe CPU profiling with flame graph generation
#
# Usage: bash profiling/run_pyspy.sh [video_path]
#
# Features:
# - Minimal overhead (<5%)
# - Non-blocking profiling
# - Interactive SVG flame graph output

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
OUTPUT_FILE="$RESULTS_DIR/pyspy_cpu_${TIMESTAMP}.svg"

echo "=================================="
echo "py-spy CPU Profiling"
echo "=================================="
echo "Video: $VIDEO_PATH"
echo "Output: $OUTPUT_FILE"
echo "=================================="
echo ""
echo "Starting profiling... (this may take several minutes)"
echo ""

# Run py-spy with production-safe settings
# --nonblocking: Minimal performance impact
# --rate 100: Sample every 10ms (good balance of accuracy vs overhead)
# --format speedscope: Modern flame graph format
py-spy record \
    --output "$OUTPUT_FILE" \
    --format speedscope \
    --rate 100 \
    --nonblocking \
    -- python3 "$PROJECT_ROOT/profiling/profile_agentos.py" "$VIDEO_PATH"

echo ""
echo "✅ Profiling complete!"
echo ""
echo "Flame graph saved to: $OUTPUT_FILE"
echo ""
echo "To view:"
echo "  1. Open $OUTPUT_FILE in a web browser"
echo "  2. Look for wide bars (high CPU time)"
echo "  3. Identify functions taking >10% of total time"
echo ""
echo "Common bottlenecks to look for:"
echo "  - cv2.VideoCapture operations (frame decoding)"
echo "  - OpenCV processing functions"
echo "  - Numpy array operations"
echo "  - API calls or network I/O"
echo ""