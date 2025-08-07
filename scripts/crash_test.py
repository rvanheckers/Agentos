#!/usr/bin/env python3
"""
Worker Crash Recovery Test
==========================

Start jobs, kill a worker mid-processing, see recovery behavior.
"""

import requests
import time
import subprocess
import signal
import os
import sys

def start_jobs_async(num_jobs=50):
    """Start jobs zonder te wachten op completion"""
    print(f"🚀 Starting {num_jobs} jobs async...")
    
    jobs = []
    for i in range(num_jobs):
        payload = {
            "video_url": f"./io/input/crash_test_{i}.mp4",
            "intent": "visual_clips", 
            "user_id": "crash_test_user"
        }
        
        response = requests.post("http://localhost:8001/api/jobs/create", json=payload)
        if response.status_code == 200:
            job_id = response.json().get("job_id")
            jobs.append(job_id)
            print(f"✅ Job {i+1}/{num_jobs} created: {job_id}")
        else:
            print(f"❌ Job {i+1} failed")
    
    return jobs

def get_worker_pids():
    """Get alle celery worker PIDs"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        worker_pids = []
        for line in lines:
            if 'celery' in line and 'worker' in line and 'python3' in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = int(parts[1])
                    worker_pids.append(pid)
        
        return worker_pids
    except Exception as e:
        print(f"❌ Error getting worker PIDs: {e}")
        return []

def kill_random_worker():
    """Kill een random worker"""
    pids = get_worker_pids()
    if not pids:
        print("❌ No workers found to kill")
        return None
    
    import random
    victim_pid = random.choice(pids)
    
    try:
        print(f"💀 Killing worker PID {victim_pid}")
        os.kill(victim_pid, signal.SIGTERM)
        time.sleep(2)
        
        # Check if it's really dead
        try:
            os.kill(victim_pid, 0)  # Check if process exists
            print(f"⚠️ Worker {victim_pid} still alive, force killing...")
            os.kill(victim_pid, signal.SIGKILL)
        except ProcessLookupError:
            print(f"✅ Worker {victim_pid} successfully killed")
        
        return victim_pid
    except Exception as e:
        print(f"❌ Failed to kill worker {victim_pid}: {e}")
        return None

def check_jobs_status(job_ids):
    """Check status van alle jobs"""
    completed = 0
    failed = 0
    processing = 0
    
    for job_id in job_ids:
        try:
            response = requests.get(f"http://localhost:8001/api/jobs/{job_id}")
            if response.status_code == 200:
                status = response.json().get("status", "unknown")
                if status == "completed":
                    completed += 1
                elif status == "failed":
                    failed += 1
                else:
                    processing += 1
        except:
            failed += 1
    
    return completed, failed, processing

def main():
    print("💥 Worker Crash Recovery Test")
    print("=============================")
    
    # Start met baseline worker count
    initial_pids = get_worker_pids()
    print(f"🏭 Initial workers: {len(initial_pids)} processes")
    
    # Start jobs
    job_ids = start_jobs_async(40)
    print(f"📊 Started {len(job_ids)} jobs")
    
    # Wait a bit for jobs to start processing
    print("⏳ Waiting 3 seconds for jobs to start processing...")
    time.sleep(3)
    
    # Kill a worker
    killed_pid = kill_random_worker()
    
    if killed_pid:
        print(f"💀 Killed worker {killed_pid}")
        
        # Check remaining workers
        remaining_pids = get_worker_pids()
        print(f"🏭 Remaining workers: {len(remaining_pids)} processes")
        
        # Monitor job progress
        print("📊 Monitoring job recovery...")
        
        for i in range(30):  # Monitor for 30 seconds
            completed, failed, processing = check_jobs_status(job_ids)
            print(f"Status: ✅{completed} ❌{failed} 🔄{processing}")
            
            if completed + failed == len(job_ids):
                print("🏁 All jobs completed!")
                break
                
            time.sleep(1)
        
        # Final status
        completed, failed, processing = check_jobs_status(job_ids)
        success_rate = (completed / len(job_ids)) * 100
        
        print(f"\n📊 CRASH RECOVERY RESULTS:")
        print(f"✅ Completed: {completed}/{len(job_ids)}")
        print(f"❌ Failed: {failed}/{len(job_ids)}")
        print(f"🔄 Still processing: {processing}/{len(job_ids)}")
        print(f"🎯 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: System recovered very well from worker crash!")
        elif success_rate >= 70:
            print("✅ GOOD: System handled worker crash reasonably well")
        else:
            print("⚠️ POOR: Worker crash caused significant job failures")
    
    else:
        print("❌ Could not kill a worker for testing")

if __name__ == "__main__":
    main()