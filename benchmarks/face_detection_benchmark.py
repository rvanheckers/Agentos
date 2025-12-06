#!/usr/bin/env python3
"""
Performance Benchmark for FaceDetectorV2
=========================================

Measures:
- MediaPipe FPS (target: 180+)
- YOLO FPS (for comparison)
- Adaptive strategy effectiveness (target: 95%+ MediaPipe usage)
- Memory usage
- Fallback frequency

Usage:
    python face_detection_benchmark.py <video_path>

Example:
    python face_detection_benchmark.py io/output/67b38c64-526c-4594-a152-0fa8387f7135/clip_1_original.mp4
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents2.face_detection.face_detector_v2 import FaceDetectorV2
from security.path_sanitizer import PathSanitizer


def benchmark_video(video_path: str, runs: int = 3):
    """
    Benchmark adaptive face detector on a video

    Args:
        video_path: Path to video file
        runs: Number of runs to average

    Returns:
        Benchmark results
    """
    print(f"\nBenchmarking Adaptive Face Detector")
    print(f"Video: {video_path}")
    print(f"Runs: {runs}")
    print("=" * 60)

    # Configure development mode (less restrictive paths)
    PathSanitizer.configure_for_development()

    detector = FaceDetectorV2()
    results_per_run = []

    for run in range(1, runs + 1):
        print(f"\nRun {run}/{runs}...")

        start_time = time.time()

        result = detector.process_video_safely({
            "video_path": video_path
        })

        end_time = time.time()

        if not result["success"]:
            print(f"ERROR: {result.get('error')}")
            continue

        results_per_run.append(result)

        # Print run summary
        print(f"  Duration: {end_time - start_time:.2f}s")
        print(f"  Method: {result['detection_method']}")
        print(f"  Faces detected: {result['total_faces_detected']}")
        print(f"  FPS: {result['performance']['fps']}")
        print(f"  Avg confidence: {result['avg_confidence']}")
        print(f"  Fallback triggered: {result['adaptive_strategy']['fallback_triggered']}")

    if not results_per_run:
        print("\nNo successful runs. Exiting.")
        return

    # Calculate aggregate statistics
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)

    avg_fps = sum(r["performance"]["fps"] for r in results_per_run) / len(results_per_run)
    avg_processing_time = sum(r["performance"]["processing_time_seconds"] for r in results_per_run) / len(results_per_run)
    avg_confidence = sum(r["avg_confidence"] for r in results_per_run) / len(results_per_run)

    # Get final stats (accumulated across all runs)
    final_stats = results_per_run[-1]["statistics"]
    mediapipe_usage_pct = (
        final_stats["mediapipe_only"] / final_stats["total_detections"] * 100
        if final_stats["total_detections"] > 0 else 0
    )

    print(f"\nPerformance Metrics:")
    print(f"  Average FPS: {avg_fps:.1f}")
    print(f"  Average Processing Time: {avg_processing_time:.2f}s")
    print(f"  Average Confidence: {avg_confidence:.3f}")

    print(f"\nAdaptive Strategy Effectiveness:")
    print(f"  Total Detections: {final_stats['total_detections']}")
    print(f"  MediaPipe Only: {final_stats['mediapipe_only']} ({mediapipe_usage_pct:.1f}%)")
    print(f"  YOLO Fallback: {final_stats['yolo_fallback']}")

    print(f"\nTarget Validation:")
    print(f"  MediaPipe FPS > 180: {'PASS' if avg_fps > 180 else 'FAIL'} (actual: {avg_fps:.1f})")
    print(f"  MediaPipe usage > 95%: {'PASS' if mediapipe_usage_pct > 95 else 'FAIL'} (actual: {mediapipe_usage_pct:.1f}%)")

    # Check if targets met
    targets_met = avg_fps > 180 and mediapipe_usage_pct > 95

    if targets_met:
        print("\n✅ ALL PERFORMANCE TARGETS MET!")
    else:
        print("\n⚠️  Some performance targets not met (may need optimization)")

    print("\n" + "=" * 60)

    # Return summary for programmatic use
    return {
        "avg_fps": avg_fps,
        "avg_processing_time": avg_processing_time,
        "avg_confidence": avg_confidence,
        "mediapipe_usage_pct": mediapipe_usage_pct,
        "targets_met": targets_met,
        "statistics": final_stats
    }


def main():
    """CLI interface"""
    if len(sys.argv) != 2:
        print("Usage: python face_detection_benchmark.py <video_path>")
        print("\nExample:")
        print("  python face_detection_benchmark.py io/output/67b38c64-526c-4594-a152-0fa8387f7135/clip_1_original.mp4")
        sys.exit(1)

    video_path = sys.argv[1]

    if not Path(video_path).exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    try:
        results = benchmark_video(video_path, runs=3)

        # Save results to JSON
        output_file = Path("benchmark_results.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_file}")

    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
