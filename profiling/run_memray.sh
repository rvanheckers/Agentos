#!/bin/bash
# Memray Memory Leak Detection Script
# ====================================
# Fast and accurate memory profiling for Python
#
# Usage: bash profiling/run_memray.sh [agent_module] [video_path]
#
# Features:
# - Traces ALL memory allocations (Python + native)
# - Detects memory leaks and unclosed resources
# - Generates flame graphs and reports
# - Minimal overhead

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/profiling_results"

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

# Get agent module from argument or profile all
AGENT_MODULE="${1:-all}"
VIDEO_PATH="${2:-$PROJECT_ROOT/io/input/video_1751932054.mp4}"

if [ ! -f "$VIDEO_PATH" ]; then
    echo "❌ Error: Video file not found: $VIDEO_PATH"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=================================="
echo "Memray Memory Leak Detection"
echo "=================================="
echo "Agent: $AGENT_MODULE"
echo "Video: $VIDEO_PATH"
echo "=================================="
echo ""

if [ "$AGENT_MODULE" == "all" ]; then
    echo "Profiling entire pipeline with memray..."
    echo ""

    BIN_OUTPUT="$RESULTS_DIR/memray_full_${TIMESTAMP}.bin"

    # Run memray on full profiling script
    # --trace-python-allocators: Trace Python's internal allocators (for leak detection)
    # --native: Also trace C/C++ allocations
    memray run \
        --output "$BIN_OUTPUT" \
        --trace-python-allocators \
        --native \
        "$PROJECT_ROOT/profiling/profile_agentos.py" "$VIDEO_PATH"

    echo ""
    echo "Generating reports..."
    echo ""

    # Generate flame graph
    FLAMEGRAPH_OUTPUT="$RESULTS_DIR/memray_flamegraph_${TIMESTAMP}.html"
    memray flamegraph \
        --output "$FLAMEGRAPH_OUTPUT" \
        --leaks \
        "$BIN_OUTPUT"

    # Generate table summary
    echo ""
    echo "Memory allocation summary:"
    memray summary "$BIN_OUTPUT" --temporary-allocations

    echo ""
    echo "✅ Memray profiling complete!"
    echo ""
    echo "Binary data: $BIN_OUTPUT"
    echo "Flame graph: $FLAMEGRAPH_OUTPUT"
    echo ""
    echo "To view:"
    echo "  1. Open $FLAMEGRAPH_OUTPUT in a web browser"
    echo "  2. Look for:"
    echo "     - Wide bars = high memory allocation"
    echo "     - Memory leaks (allocations without corresponding frees)"
    echo "     - Temporary allocations (high churn)"
    echo ""
    echo "Additional analysis commands:"
    echo "  memray table $BIN_OUTPUT                      # Detailed table"
    echo "  memray tree $BIN_OUTPUT                       # Tree view"
    echo "  memray summary $BIN_OUTPUT --temporary-allocations  # Find inefficient code"
    echo ""

else
    echo "Profiling specific agent: $AGENT_MODULE"
    echo ""
    echo "⚠️  This feature requires a custom wrapper script."
    echo "    For now, use 'all' to profile the entire pipeline."
    echo ""
fi