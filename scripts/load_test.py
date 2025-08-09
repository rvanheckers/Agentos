#!/usr/bin/env python3
"""
Load Test Script for AgentOS
============================

Tests the system with multiple concurrent video processing jobs
to verify 10-worker Celery setup can handle high load.

Usage:
    python scripts/load_test.py [number_of_jobs]

Example:
    python scripts/load_test.py 50  # Submit 50 concurrent jobs
"""

import requests
import concurrent.futures
import time
import sys
from datetime import datetime

# API configuration
API_BASE = "http://localhost:8001"
CREATE_JOB_ENDPOINT = f"{API_BASE}/api/jobs/create"
JOB_STATUS_ENDPOINT = f"{API_BASE}/api/jobs"

def submit_job(index):
    """Submit een test job naar de API"""
    try:
        payload = {
            "video_url": "video_1751932054.mp4",  # Use existing standard test video
            "intent": "visual_clips",
            "user_id": f"load_test_user_{index}"
        }

        start_time = time.time()
        response = requests.post(CREATE_JOB_ENDPOINT, json=payload, timeout=10)
        submit_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            return {
                "index": index,
                "success": True,
                "job_id": result.get("job_id"),
                "submit_time": submit_time,
                "response": result
            }
        else:
            return {
                "index": index,
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "submit_time": submit_time
            }

    except Exception as e:
        return {
            "index": index,
            "success": False,
            "error": str(e),
            "submit_time": 0
        }

def check_job_status(job_id):
    """Check status van een specifieke job"""
    try:
        response = requests.get(f"{JOB_STATUS_ENDPOINT}/{job_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def monitor_jobs(job_ids, max_wait_time=300):
    """Monitor job completion status"""
    print(f"\n🔍 Monitoring {len(job_ids)} jobs (max wait: {max_wait_time}s)...")

    start_time = time.time()
    completed_jobs = []

    while len(completed_jobs) < len(job_ids) and (time.time() - start_time) < max_wait_time:
        for job_id in job_ids:
            if job_id not in completed_jobs:
                status = check_job_status(job_id)
                if status.get("status") in ["completed", "failed"]:
                    completed_jobs.append(job_id)
                    print(f"✅ Job {job_id} completed: {status.get('status')}")

        if len(completed_jobs) < len(job_ids):
            time.sleep(2)  # Wait 2 seconds before checking again

    return completed_jobs

def run_load_test(num_jobs=50, max_workers=10):
    """Run het load test met gespecificeerd aantal jobs"""
    print(f"🚀 Starting load test with {num_jobs} concurrent jobs")
    print(f"📊 Using {max_workers} concurrent threads")
    print(f"🎯 Target API: {CREATE_JOB_ENDPOINT}")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)

    # Submit alle jobs concurrent
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        print(f"📤 Submitting {num_jobs} jobs concurrent...")
        futures = [executor.submit(submit_job, i) for i in range(1, num_jobs + 1)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    submit_duration = time.time() - start_time

    # Analyze results
    successful_jobs = [r for r in results if r["success"]]
    failed_jobs = [r for r in results if not r["success"]]

    print("\n📊 SUBMISSION RESULTS:")
    print(f"✅ Successful submissions: {len(successful_jobs)}/{num_jobs}")
    print(f"❌ Failed submissions: {len(failed_jobs)}/{num_jobs}")
    print(f"⏱️ Total submission time: {submit_duration:.2f}s")
    print(f"🚀 Average submission time: {sum(r['submit_time'] for r in results)/len(results):.3f}s")

    if failed_jobs:
        print("\n❌ FAILED JOBS:")
        for job in failed_jobs[:5]:  # Show first 5 failures
            print(f"  Job {job['index']}: {job['error']}")
        if len(failed_jobs) > 5:
            print(f"  ... and {len(failed_jobs) - 5} more failures")

    # Get job IDs for monitoring
    job_ids = [job["job_id"] for job in successful_jobs if job.get("job_id")]

    if job_ids:
        print("\n📈 MONITORING PHASE:")
        completed_jobs = monitor_jobs(job_ids, max_wait_time=300)
        print(f"✅ Completed jobs: {len(completed_jobs)}/{len(job_ids)}")

    print(f"\n🏁 Load test completed at: {datetime.now().strftime('%H:%M:%S')}")

    # Return summary for further analysis
    return {
        "total_jobs": num_jobs,
        "successful_submissions": len(successful_jobs),
        "failed_submissions": len(failed_jobs),
        "submission_duration": submit_duration,
        "job_ids": job_ids,
        "completed_jobs": len(completed_jobs) if job_ids else 0
    }

def main():
    """Main entry point"""
    # Parse command line arguments
    num_jobs = 50  # Default
    if len(sys.argv) > 1:
        try:
            num_jobs = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid number of jobs. Using default: 50")

    print("🏭 AgentOS Load Test")
    print("==================")

    # Check if API is accessible
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ API not accessible: {API_BASE}")
            return 1
    except Exception as e:
        print(f"❌ Cannot reach API: {e}")
        return 1

    print(f"✅ API is accessible at {API_BASE}")

    # Run the load test
    summary = run_load_test(num_jobs)

    # Performance assessment
    success_rate = (summary["successful_submissions"] / summary["total_jobs"]) * 100

    print("\n📊 FINAL ASSESSMENT:")
    print(f"Success Rate: {success_rate:.1f}%")

    if success_rate >= 95:
        print("🎉 EXCELLENT: System handles high load very well!")
        return 0
    elif success_rate >= 80:
        print("✅ GOOD: System handles load with minor issues")
        return 0
    elif success_rate >= 60:
        print("⚠️ FAIR: System has some load handling issues")
        return 1
    else:
        print("❌ POOR: System cannot handle the load properly")
        return 1

if __name__ == "__main__":
    sys.exit(main())
