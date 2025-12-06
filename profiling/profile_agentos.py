#!/usr/bin/env python3
"""
AgentOS Performance Profiling Script
=====================================

Modern profiling infrastructure using 2025 best practices:
- py-spy for production-safe CPU profiling
- psutil for system resource monitoring
- Statistical analysis with baseline comparisons

This script measures ACTUAL performance, not assumptions.

Usage:
    python profiling/profile_agentos.py /path/to/test_video.mp4
"""

import os
import sys
import json
import time
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class AgentProfiler:
    """Modern profiler for AgentOS video processing agents"""

    def __init__(self, video_path: str):
        self.video_path = video_path
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "video_path": video_path,
            "system_info": self._get_system_info(),
            "agents": {},
            "summary": {}
        }
        self.process = psutil.Process()

    def _get_system_info(self) -> Dict[str, Any]:
        """Capture system baseline metrics"""
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

    def profile_agent(self, agent_name: str, agent_module: str, method: str) -> Dict[str, Any]:
        """
        Profile a single agent with comprehensive metrics

        Uses psutil for accurate resource tracking WITHOUT modifying code
        """
        print(f"\n{'='*60}")
        print(f"Profiling: {agent_name}")
        print(f"{'='*60}")

        # Baseline measurements BEFORE agent execution
        baseline_cpu = psutil.cpu_percent(interval=0.5)
        baseline_memory = self.process.memory_info().rss / (1024**2)  # MB

        # Start timing
        start_time = time.perf_counter()
        start_cpu_time = self.process.cpu_times()

        try:
            # Import and execute agent
            module = __import__(agent_module, fromlist=[agent_name])
            agent_class = getattr(module, agent_name)
            agent = agent_class()

            # Execute the profiling method
            if hasattr(agent, method):
                result = getattr(agent, method)(self.video_path)
            else:
                result = agent.process(self.video_path)

            # End timing
            end_time = time.perf_counter()
            end_cpu_time = self.process.cpu_times()

            # Post-execution measurements
            post_cpu = psutil.cpu_percent(interval=0.5)
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
                "cpu_percent_avg": round((baseline_cpu + post_cpu) / 2, 2),
                "memory_delta_mb": round(memory_delta, 2),
                "memory_peak_mb": round(post_memory, 2),
                "result_summary": str(result)[:200] if result else "No result"
            }

            # Performance assessment
            if elapsed_time > 30:
                metrics["priority"] = "HIGH"
                metrics["issue"] = f"Agent exceeds 30s threshold ({elapsed_time:.1f}s)"
            elif elapsed_time > 15:
                metrics["priority"] = "MEDIUM"
                metrics["issue"] = f"Agent slower than expected ({elapsed_time:.1f}s)"
            else:
                metrics["priority"] = "LOW"
                metrics["issue"] = None

            print(f"✅ Execution time: {elapsed_time:.3f}s")
            print(f"   CPU time: {cpu_time_user:.3f}s user + {cpu_time_system:.3f}s system")
            print(f"   Memory delta: {memory_delta:+.2f} MB")
            print(f"   Priority: {metrics['priority']}")

            return metrics

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time_seconds": 0,
                "priority": "HIGH",
                "issue": f"Agent failed: {str(e)}"
            }

    def profile_all_agents(self) -> Dict[str, Any]:
        """Profile all video processing agents in sequence"""

        agents_config = [
            {
                "name": "VideoDownloader",
                "module": "agents2.video_processing.video_downloader",
                "method": "download",
                "expected_time": 60
            },
            {
                "name": "AudioTranscriber",
                "module": "agents2.audio_processing.audio_transcriber",
                "method": "transcribe",
                "expected_time": 120
            },
            {
                "name": "MomentDetector",
                "module": "agents2.moment_detection.moment_detector",
                "method": "detect_moments",
                "expected_time": 30
            },
            {
                "name": "FaceDetector",
                "module": "agents2.face_detection.face_detector",
                "method": "detect_faces",
                "expected_time": 90
            },
            {
                "name": "FaceDetectorMediaPipe",
                "module": "agents2.face_detection.face_detector_mediapipe",
                "method": "detect_faces",
                "expected_time": 60
            },
            {
                "name": "IntelligentCropper",
                "module": "agents2.intelligent_cropping.intelligent_cropper",
                "method": "crop_video",
                "expected_time": 40
            },
            {
                "name": "VideoCutter",
                "module": "agents2.video_processing.video_cutter",
                "method": "cut_video",
                "expected_time": 180
            }
        ]

        total_start = time.perf_counter()

        for agent_config in agents_config:
            agent_name = agent_config["name"]

            try:
                metrics = self.profile_agent(
                    agent_name,
                    agent_config["module"],
                    agent_config["method"]
                )
                metrics["expected_time_seconds"] = agent_config["expected_time"]
                self.results["agents"][agent_name] = metrics

            except Exception as e:
                print(f"❌ Failed to profile {agent_name}: {e}")
                self.results["agents"][agent_name] = {
                    "status": "error",
                    "error": str(e),
                    "priority": "HIGH"
                }

        total_elapsed = time.perf_counter() - total_start

        # Generate summary
        self.results["summary"] = self._generate_summary(total_elapsed)

        return self.results

    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate executive summary of profiling results"""

        successful_agents = [
            name for name, metrics in self.results["agents"].items()
            if metrics.get("status") == "success"
        ]

        failed_agents = [
            name for name, metrics in self.results["agents"].items()
            if metrics.get("status") == "error"
        ]

        # Find slowest agents
        slowest = sorted(
            [
                (name, metrics.get("execution_time_seconds", 0))
                for name, metrics in self.results["agents"].items()
                if metrics.get("status") == "success"
            ],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Find memory-heavy agents
        memory_heavy = sorted(
            [
                (name, metrics.get("memory_delta_mb", 0))
                for name, metrics in self.results["agents"].items()
                if metrics.get("status") == "success"
            ],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Identify HIGH priority issues
        high_priority_issues = [
            {"agent": name, "issue": metrics.get("issue")}
            for name, metrics in self.results["agents"].items()
            if metrics.get("priority") == "HIGH"
        ]

        return {
            "total_pipeline_time_seconds": round(total_time, 2),
            "successful_agents": len(successful_agents),
            "failed_agents": len(failed_agents),
            "slowest_agents": [
                {"agent": name, "time_seconds": round(time, 2)}
                for name, time in slowest
            ],
            "memory_heavy_agents": [
                {"agent": name, "memory_delta_mb": round(mem, 2)}
                for name, mem in memory_heavy
            ],
            "high_priority_issues_count": len(high_priority_issues),
            "high_priority_issues": high_priority_issues
        }

    def save_results(self, output_path: str):
        """Save profiling results to JSON"""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✅ Results saved to: {output_path}")

    def print_summary(self):
        """Print executive summary to console"""
        summary = self.results["summary"]

        print("\n" + "="*60)
        print("PROFILING SUMMARY")
        print("="*60)
        print(f"Total Pipeline Time: {summary['total_pipeline_time_seconds']}s")
        print(f"Successful Agents: {summary['successful_agents']}")
        print(f"Failed Agents: {summary['failed_agents']}")

        print(f"\nSlowest Agents (TOP 3):")
        for agent in summary['slowest_agents']:
            print(f"  - {agent['agent']}: {agent['time_seconds']}s")

        print(f"\nMemory-Heavy Agents (TOP 3):")
        for agent in summary['memory_heavy_agents']:
            print(f"  - {agent['agent']}: {agent['memory_delta_mb']:+.2f} MB")

        if summary['high_priority_issues_count'] > 0:
            print(f"\n⚠️  HIGH PRIORITY ISSUES ({summary['high_priority_issues_count']}):")
            for issue in summary['high_priority_issues']:
                print(f"  - {issue['agent']}: {issue['issue']}")
        else:
            print(f"\n✅ No high-priority performance issues detected")

        print("="*60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python profiling/profile_agentos.py <video_path>")
        print("\nExample:")
        print("  python profiling/profile_agentos.py io/input/video_1751932054.mp4")
        sys.exit(1)

    video_path = sys.argv[1]

    if not os.path.exists(video_path):
        print(f"❌ Error: Video file not found: {video_path}")
        sys.exit(1)

    print("="*60)
    print("AgentOS Performance Profiler")
    print("="*60)
    print(f"Video: {video_path}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    profiler = AgentProfiler(video_path)
    profiler.profile_all_agents()

    # Save results
    output_dir = project_root / "profiling_results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"profiling_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    profiler.save_results(str(output_file))
    profiler.print_summary()

    print(f"\n📊 Next steps:")
    print(f"  1. Run py-spy for CPU flame graph:")
    print(f"     bash profiling/run_pyspy.sh {video_path}")
    print(f"  2. Run Scalene for comprehensive analysis:")
    print(f"     bash profiling/run_scalene.sh")
    print(f"  3. Run memray on slow agents for memory leak detection:")
    print(f"     bash profiling/run_memray.sh")


if __name__ == "__main__":
    main()