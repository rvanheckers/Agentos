#!/usr/bin/env python3
"""Calculate statistics across multiple profiling samples"""
import json
import glob
import statistics
from pathlib import Path
from typing import Dict, List, Any

def calculate_stats() -> Dict[str, Any]:
    """Calculate statistics from profiling samples"""

    # Find all profiling results
    result_files = sorted(glob.glob("profiling_results/pipeline_profile_*.json"))

    print(f"\n📊 Found {len(result_files)} profiling samples")

    if len(result_files) < 3:
        print(f"⚠️ WARNING: Only {len(result_files)} samples (need 3)")
        return None

    # Collect data per task
    task_data = {}

    for result_file in result_files:
        with open(result_file) as f:
            data = json.load(f)

        # Support both "tasks" and "task_results" keys
        tasks = data.get("tasks", data.get("task_results", {}))

        for task_name, task_result in tasks.items():
            if task_name not in task_data:
                task_data[task_name] = {
                    "times": [],
                    "cpu_times": [],
                    "memory": [],
                    "success": []
                }

            # Support different field naming conventions
            exec_time = task_result.get("execution_time_seconds", task_result.get("time", 0))
            cpu_user = task_result.get("cpu_time_user_seconds", 0)
            cpu_system = task_result.get("cpu_time_system_seconds", 0)
            cpu_total = task_result.get("cpu_time", cpu_user + cpu_system)
            memory = task_result.get("memory_delta_mb", task_result.get("memory_mb", 0))
            status = task_result.get("status", "unknown")
            success = status == "success" or task_result.get("success", False)

            task_data[task_name]["times"].append(exec_time)
            task_data[task_name]["cpu_times"].append(cpu_total)
            task_data[task_name]["memory"].append(memory)
            task_data[task_name]["success"].append(success)

    # Calculate statistics
    stats = {}

    for task_name, data in task_data.items():
        times = data["times"]
        cpu_times = data["cpu_times"]
        memory = data["memory"]

        if len(times) < 2:
            continue

        mean_time = statistics.mean(times)
        stddev_time = statistics.stdev(times) if len(times) > 1 else 0
        variance_pct = (stddev_time / mean_time * 100) if mean_time > 0 else 0

        mean_cpu = statistics.mean(cpu_times)
        stddev_cpu = statistics.stdev(cpu_times) if len(cpu_times) > 1 else 0

        mean_memory = statistics.mean(memory)
        stddev_memory = statistics.stdev(memory) if len(memory) > 1 else 0

        stats[task_name] = {
            "time": {
                "mean": round(mean_time, 2),
                "stddev": round(stddev_time, 2),
                "min": round(min(times), 2),
                "max": round(max(times), 2),
                "samples": len(times)
            },
            "cpu_time": {
                "mean": round(mean_cpu, 2),
                "stddev": round(stddev_cpu, 2)
            },
            "memory": {
                "mean": round(mean_memory, 2),
                "stddev": round(stddev_memory, 2)
            },
            "variance_percent": round(variance_pct, 1),
            "consistent": variance_pct < 20,
            "success_rate": round(sum(data["success"]) / len(data["success"]) * 100, 1)
        }

    # Identify bottlenecks (sorted by mean time)
    sorted_tasks = sorted(stats.items(), key=lambda x: x[1]["time"]["mean"], reverse=True)
    top_3 = sorted_tasks[:3]

    # Check consistency
    consistent_bottlenecks = [name for name, stat in top_3 if stat["consistent"]]
    inconsistent_bottlenecks = [
        {"task": name, "variance": stat["variance_percent"]}
        for name, stat in top_3
        if not stat["consistent"]
    ]

    # Generate report
    report = {
        "statistical_summary": {
            "samples": len(result_files),
            "statistically_significant": len(result_files) >= 3,
            "top_3_bottlenecks": [name for name, _ in top_3],
            "consistent_bottlenecks": consistent_bottlenecks,
            "inconsistent_bottlenecks": inconsistent_bottlenecks,
            "all_bottlenecks_consistent": len(inconsistent_bottlenecks) == 0
        },
        "task_statistics": stats,
        "top_3_analysis": {
            name: stats[name] for name, _ in top_3
        }
    }

    # Save
    output_file = "profiling_results/statistical_analysis.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("📊 STATISTICAL ANALYSIS")
    print("="*60)
    print(f"Samples: {len(result_files)}")
    print(f"Statistically significant: ✅ YES" if len(result_files) >= 3 else "❌ NO")

    print("\n🎯 TOP 3 BOTTLENECKS:")
    for i, (task_name, stat) in enumerate(top_3, 1):
        consistent_icon = "✅" if stat["consistent"] else "⚠️"
        print(f"{i}. {consistent_icon} {task_name}:")
        print(f"   Mean: {stat['time']['mean']}s ± {stat['time']['stddev']}s")
        print(f"   Variance: {stat['variance_percent']}%")
        print(f"   Range: {stat['time']['min']}s - {stat['time']['max']}s")
        print(f"   CPU: {stat['cpu_time']['mean']}s ± {stat['cpu_time']['stddev']}s")
        print(f"   Memory: {stat['memory']['mean']}MB ± {stat['memory']['stddev']}MB")

    if inconsistent_bottlenecks:
        print("\n⚠️ INCONSISTENT RESULTS (variance >20%):")
        for item in inconsistent_bottlenecks:
            print(f"  - {item['task']}: {item['variance']:.1f}% variance")
    else:
        print("\n✅ All top 3 bottlenecks are CONSISTENT (<20% variance)")

    print(f"\n📄 Report saved: {output_file}")

    return report

if __name__ == "__main__":
    result = calculate_stats()
    if result:
        print("\n✅ Statistical analysis complete")
    else:
        print("\n❌ Statistical analysis failed")