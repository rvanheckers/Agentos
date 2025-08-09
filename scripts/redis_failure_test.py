#!/usr/bin/env python3
"""
Redis Failure Test
==================

Test what happens when Redis goes down during job processing.
"""

import requests
import time
import subprocess
import sys

def stop_redis():
    """Stop Redis server"""
    try:
        print("🛑 Stopping Redis server...")
        subprocess.run(['redis-cli', 'shutdown'], capture_output=True, text=True)
        time.sleep(2)
        return True
    except Exception as e:
        print(f"❌ Failed to stop Redis: {e}")
        return False

def start_redis():
    """Start Redis server"""
    try:
        print("🚀 Starting Redis server...")
        subprocess.run(['redis-server', '--daemonize', 'yes', '--port', '6379'], check=True)
        time.sleep(3)
        return True
    except Exception as e:
        print(f"❌ Failed to start Redis: {e}")
        return False

def check_redis():
    """Check if Redis is running"""
    try:
        result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True)
        return result.stdout.strip() == 'PONG'
    except Exception:
        return False

def submit_job():
    """Submit a single job"""
    try:
        payload = {
            "video_url": "./io/input/redis_test.mp4",
            "intent": "visual_clips",
            "user_id": "redis_test_user"
        }

        response = requests.post("http://localhost:8001/api/jobs/create", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json().get("job_id")
        else:
            return None
    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return None

def main():
    print("💥 Redis Failure Recovery Test")
    print("==============================")

    # Check initial Redis status
    if not check_redis():
        print("❌ Redis is not running initially")
        return 1

    print("✅ Redis is running initially")

    # Submit some jobs before Redis failure
    print("📤 Submitting jobs before Redis failure...")
    pre_jobs = []
    for i in range(5):
        job_id = submit_job()
        if job_id:
            pre_jobs.append(job_id)
            print(f"✅ Pre-failure job {i+1}: {job_id}")

    time.sleep(2)

    # Stop Redis
    if not stop_redis():
        return 1

    print("🛑 Redis stopped")

    # Try to submit jobs while Redis is down
    print("📤 Trying to submit jobs while Redis is down...")
    failed_jobs = 0
    for i in range(3):
        job_id = submit_job()
        if not job_id:
            failed_jobs += 1
            print(f"❌ Job {i+1} failed (expected)")
        else:
            print(f"😱 Job {i+1} unexpectedly succeeded: {job_id}")

    # Restart Redis
    if not start_redis():
        return 1

    print("🚀 Redis restarted")

    # Submit jobs after Redis restart
    print("📤 Submitting jobs after Redis restart...")
    post_jobs = []
    for i in range(5):
        job_id = submit_job()
        if job_id:
            post_jobs.append(job_id)
            print(f"✅ Post-restart job {i+1}: {job_id}")

    # Check if system recovered
    recovery_success = len(post_jobs) == 5

    print("\n📊 REDIS FAILURE TEST RESULTS:")
    print(f"✅ Pre-failure jobs: {len(pre_jobs)}/5")
    print(f"❌ Failed during downtime: {failed_jobs}/3 (expected)")
    print(f"🔄 Post-restart jobs: {len(post_jobs)}/5")

    if recovery_success:
        print("🎉 EXCELLENT: System recovered completely after Redis restart!")
        return 0
    else:
        print("⚠️ PARTIAL: System had issues recovering from Redis failure")
        return 1

if __name__ == "__main__":
    sys.exit(main())
