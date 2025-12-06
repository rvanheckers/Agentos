#!/usr/bin/env python3
"""
AgentOS Video Pipeline Profiler
=================================

Profile the actual Celery video processing tasks to identify bottlenecks.

This script simulates a video processing job and measures performance
of each task in the pipeline using modern profiling techniques.

Usage:
    python profiling/profile_video_pipeline.py <video_url_or_path>
"""

import os
import sys
import json
import time
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment (force override to ensure API keys are loaded)
from dotenv import load_dotenv
load_dotenv(override=True)


class VideoPipelineProfiler:
    """Profile video processing pipeline with real metrics"""

    def __init__(self, video_input: str):
        self.video_input = video_input
        self.job_id = f"profile_{int(time.time())}"
        self.process = psutil.Process()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "video_input": video_input,
            "job_id": self.job_id,
            "system_info": self._get_system_info(),
            "tasks": {},
            "summary": {}
        }

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system baseline metrics"""
        cpu_count = psutil.cpu_count(logical=True)
        memory = psutil.virtual_memory()

        return {
            "cpu_count": cpu_count,
            "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "total_memory_gb": round(memory.total / (1024**3), 2),
            "available_memory_gb": round(memory.available / (1024**3), 2),
            "platform": sys.platform,
            "python_version": sys.version.split()[0]
        }

    def profile_task(self, task_name: str, task_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Profile a single Celery task synchronously

        Uses psutil for accurate resource tracking
        """
        print(f"\n{'='*60}")
        print(f"Profiling Task: {task_name}")
        print(f"{'='*60}")

        # Baseline measurements
        baseline_memory = self.process.memory_info().rss / (1024**2)  # MB
        start_time = time.perf_counter()
        start_cpu_time = self.process.cpu_times()

        try:
            # Execute task synchronously (not through Celery queue)
            result = task_func(*args, **kwargs)

            # End measurements
            end_time = time.perf_counter()
            end_cpu_time = self.process.cpu_times()
            post_memory = self.process.memory_info().rss / (1024**2)  # MB

            # Calculate metrics
            elapsed_time = end_time - start_time
            cpu_time_user = end_cpu_time.user - start_cpu_time.user
            cpu_time_system = end_cpu_time.system - start_cpu_time.system
            memory_delta = post_memory - baseline_memory

            metrics = {
                "status": "success",
                "execution_time_seconds": round(elapsed_time, 3),
                "cpu_time_user_seconds": round(cpu_time_user, 3),
                "cpu_time_system_seconds": round(cpu_time_system, 3),
                "memory_delta_mb": round(memory_delta, 2),
                "memory_peak_mb": round(post_memory, 2),
                "result_type": type(result).__name__
            }

            # Performance assessment based on video processing standards
            if elapsed_time > 30:
                metrics["priority"] = "HIGH"
                metrics["issue"] = f"Task exceeds 30s threshold ({elapsed_time:.1f}s)"
            elif elapsed_time > 15:
                metrics["priority"] = "MEDIUM"
                metrics["issue"] = f"Task slower than expected ({elapsed_time:.1f}s)"
            else:
                metrics["priority"] = "LOW"
                metrics["issue"] = None

            print(f"✅ Execution time: {elapsed_time:.3f}s")
            print(f"   CPU time: {cpu_time_user:.3f}s user + {cpu_time_system:.3f}s system")
            print(f"   Memory delta: {memory_delta:+.2f} MB")
            print(f"   Priority: {metrics['priority']}")

            return metrics, result

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time_seconds": 0,
                "priority": "HIGH",
                "issue": f"Task failed: {str(e)}"
            }, None

    def profile_pipeline(self):
        """Profile the complete video processing pipeline"""

        print("="*60)
        print("AgentOS Video Pipeline Profiler")
        print("="*60)
        print(f"Video Input: {self.video_input}")
        print(f"Job ID: {self.job_id}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        total_start = time.perf_counter()

        # Import tasks
        try:
            from tasks.video_processing import (
                download_video,
                transcribe_audio,
                detect_moments,
                detect_faces,
                intelligent_crop,
                cut_videos
            )
        except ImportError as e:
            print(f"❌ Failed to import tasks: {e}")
            return

        # Prepare job data
        job_data = {
            "video_url": self.video_input,
            "clip_duration_preference": 60,
            "user_id": "profiler",
            "trim_start": None,
            "trim_end": None
        }

        pipeline_data = {}

        # Task 1: Download Video
        print("\n" + "="*60)
        print("TASK 1/6: Download Video")
        print("="*60)
        metrics, result = self.profile_task(
            "download_video",
            download_video,
            self.job_id,
            job_data
        )
        self.results["tasks"]["download_video"] = metrics
        if result:
            pipeline_data = result

        if metrics["status"] != "success":
            print("❌ Pipeline failed at download_video")
            return

        # Task 2: Transcribe Audio
        print("\n" + "="*60)
        print("TASK 2/6: Transcribe Audio")
        print("="*60)
        metrics, result = self.profile_task(
            "transcribe_audio",
            transcribe_audio,
            pipeline_data
        )
        self.results["tasks"]["transcribe_audio"] = metrics
        if result:
            pipeline_data = result

        if metrics["status"] != "success":
            print("⚠️  Pipeline continuing despite transcription issues")

        # Task 3: Detect Moments
        print("\n" + "="*60)
        print("TASK 3/6: Detect Moments")
        print("="*60)
        metrics, result = self.profile_task(
            "detect_moments",
            detect_moments,
            pipeline_data
        )
        self.results["tasks"]["detect_moments"] = metrics
        if result:
            pipeline_data = result

        # Task 4: Detect Faces
        print("\n" + "="*60)
        print("TASK 4/6: Detect Faces")
        print("="*60)
        metrics, result = self.profile_task(
            "detect_faces",
            detect_faces,
            pipeline_data
        )
        self.results["tasks"]["detect_faces"] = metrics
        if result:
            pipeline_data = result

        # Task 5: Intelligent Crop
        print("\n" + "="*60)
        print("TASK 5/6: Intelligent Crop")
        print("="*60)
        metrics, result = self.profile_task(
            "intelligent_crop",
            intelligent_crop,
            pipeline_data
        )
        self.results["tasks"]["intelligent_crop"] = metrics
        if result:
            pipeline_data = result

        # Task 6: Cut Videos
        print("\n" + "="*60)
        print("TASK 6/6: Cut Videos")
        print("="*60)
        metrics, result = self.profile_task(
            "cut_videos",
            cut_videos,
            pipeline_data
        )
        self.results["tasks"]["cut_videos"] = metrics

        total_elapsed = time.perf_counter() - total_start

        # Generate summary
        self.results["summary"] = self._generate_summary(total_elapsed)

    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate executive summary"""

        successful_tasks = [
            name for name, metrics in self.results["tasks"].items()
            if metrics.get("status") == "success"
        ]

        failed_tasks = [
            name for name, metrics in self.results["tasks"].items()
            if metrics.get("status") == "error"
        ]

        # Find slowest tasks
        slowest = sorted(
            [
                (name, metrics.get("execution_time_seconds", 0))
                for name, metrics in self.results["tasks"].items()
                if metrics.get("status") == "success"
            ],
            key=lambda x: x[1],
            reverse=True
        )

        # Find memory-heavy tasks
        memory_heavy = sorted(
            [
                (name, metrics.get("memory_delta_mb", 0))
                for name, metrics in self.results["tasks"].items()
                if metrics.get("status") == "success"
            ],
            key=lambda x: x[1],
            reverse=True
        )

        # HIGH priority issues
        high_priority = [
            {"task": name, "issue": metrics.get("issue")}
            for name, metrics in self.results["tasks"].items()
            if metrics.get("priority") == "HIGH"
        ]

        return {
            "total_pipeline_time_seconds": round(total_time, 2),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "slowest_tasks": [
                {"task": name, "time_seconds": round(time, 2)}
                for name, time in slowest
            ],
            "memory_heavy_tasks": [
                {"task": name, "memory_delta_mb": round(mem, 2)}
                for name, mem in memory_heavy
            ],
            "high_priority_issues_count": len(high_priority),
            "high_priority_issues": high_priority
        }

    def save_results(self, output_path: str):
        """Save profiling results to JSON"""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✅ Results saved to: {output_path}")

    def print_summary(self):
        """Print executive summary"""
        summary = self.results["summary"]

        print("\n" + "="*60)
        print("PROFILING SUMMARY")
        print("="*60)
        print(f"Total Pipeline Time: {summary['total_pipeline_time_seconds']}s")
        print(f"Successful Tasks: {summary['successful_tasks']}/6")
        print(f"Failed Tasks: {summary['failed_tasks']}")

        print(f"\nSlowest Tasks:")
        for task in summary['slowest_tasks']:
            print(f"  - {task['task']}: {task['time_seconds']}s")

        print(f"\nMemory-Heavy Tasks:")
        for task in summary['memory_heavy_tasks']:
            print(f"  - {task['task']}: {task['memory_delta_mb']:+.2f} MB")

        if summary['high_priority_issues_count'] > 0:
            print(f"\n⚠️  HIGH PRIORITY ISSUES ({summary['high_priority_issues_count']}):")
            for issue in summary['high_priority_issues']:
                print(f"  - {issue['task']}: {issue['issue']}")
        else:
            print(f"\n✅ No high-priority performance issues detected")

        print("="*60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python profiling/profile_video_pipeline.py <video_url_or_path>")
        print("\nExamples:")
        print("  python profiling/profile_video_pipeline.py https://www.youtube.com/watch?v=X1AFgQZW0aA")
        print("  python profiling/profile_video_pipeline.py io/input/video_1751932054.mp4")
        sys.exit(1)

    video_input = sys.argv[1]

    # Check if local file exists
    if not video_input.startswith("http") and not os.path.exists(video_input):
        print(f"❌ Error: Video file not found: {video_input}")
        sys.exit(1)

    profiler = VideoPipelineProfiler(video_input)
    profiler.profile_pipeline()

    # Save results
    output_dir = project_root / "profiling_results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"pipeline_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    profiler.save_results(str(output_file))
    profiler.print_summary()

    print(f"\n📊 Next steps:")
    print(f"  1. Review bottlenecks in: {output_file}")
    print(f"  2. Run py-spy for detailed CPU profiling")
    print(f"  3. Run Scalene for line-by-line analysis")
    print(f"  4. Run memray on slow tasks for memory leak detection")


if __name__ == "__main__":
    main()