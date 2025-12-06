#!/usr/bin/env python3
"""
Test Script - Debug Viewer Integration
=======================================

Test script om te verifi\u00ebren dat de debug viewer integration werkt.
Run dit om te checken of alle pieces samenwerken.

Usage:
    python3 test_debug_integration.py
"""
import sys
import os
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents2.shared.utils import debug_wrapper
from core.database_manager import PostgreSQLManager, Job


def test_wrapper_basic():
    """Test basic wrapper functionality"""
    print("\n🧪 Test 1: Basic Wrapper Test")
    print("=" * 50)

    # Create test job in database
    db = PostgreSQLManager()
    test_job_id = str(uuid.uuid4())

    with db.get_session() as session:
        job = Job(
            id=test_job_id,
            user_id="test-user",
            video_url="https://test.com/video.mp4",
            status="processing",
            phase="phase1_analysis"
        )
        session.add(job)
        session.commit()

    print(f"✅ Created test job: {test_job_id}")

    # Test save_step_output directly
    from agents2.shared.utils.video_helpers import save_step_output

    save_step_output(test_job_id, "download_video", "in_progress")
    print("✅ Logged 'in_progress' status")

    save_step_output(
        test_job_id,
        "download_video",
        "success",
        output={
            "video_path": "/io/test.mp4",
            "duration": 120.5,
            "resolution": "1920x1080"
        }
    )
    print("✅ Logged 'success' status with output")

    # Verify in database
    with db.get_session() as session:
        job = session.query(Job).filter(Job.id == test_job_id).first()
        if job and job.step_outputs:
            print(f"✅ Database contains step_outputs: {list(job.step_outputs.keys())}")
            print(f"   Status: {job.step_outputs.get('download_video', {}).get('status')}")
        else:
            print("❌ No step_outputs found in database")

    return test_job_id


def test_wrapper_with_mock_agent():
    """Test wrapper with a mock agent"""
    print("\n🧪 Test 2: Wrapper with Mock Agent")
    print("=" * 50)

    # Create test job
    db = PostgreSQLManager()
    test_job_id = str(uuid.uuid4())

    with db.get_session() as session:
        job = Job(
            id=test_job_id,
            user_id="test-user",
            video_url="https://test.com/video2.mp4",
            status="processing",
            phase="phase1_analysis"
        )
        session.add(job)
        session.commit()

    print(f"✅ Created test job: {test_job_id}")

    # Mock agent
    class MockAgent:
        def process(self, input_data):
            print(f"   Mock agent processing: {input_data}")
            return {
                "success": True,
                "video_path": "/io/mock_video.mp4",
                "duration": 300.0,
                "title": "Mock Video"
            }

    # Execute with wrapper
    agent = MockAgent()
    result = debug_wrapper.execute_agent(
        job_id=test_job_id,
        step_name="download_video",
        agent_callable=agent.process,
        agent_input={"url": "https://test.com/video2.mp4"},
        extract_debug_output=lambda r: {
            "video_path": r.get("video_path"),
            "duration": r.get("duration"),
            "title": r.get("title")
        },
        auto_generate_thumbnail=False  # Skip thumbnail for test
    )

    print(f"✅ Agent executed: success={result.get('success')}")

    # Verify in database
    with db.get_session() as session:
        job = session.query(Job).filter(Job.id == test_job_id).first()
        if job and job.step_outputs and "download_video" in job.step_outputs:
            step_data = job.step_outputs["download_video"]
            print(f"✅ Step logged: status={step_data.get('status')}")
            print(f"   Output: {step_data.get('output')}")
        else:
            print("❌ Step not logged correctly")

    return test_job_id


def test_api_endpoint(job_id: str):
    """Test if API endpoint returns debug data"""
    print("\n🧪 Test 3: API Endpoint Test")
    print("=" * 50)

    try:
        import requests

        url = f"http://localhost:8001/api/jobs/{job_id}/debug"
        print(f"   Testing: {url}")

        # Note: This requires API to be running and authentication
        print("⚠️  Skipping API test (requires running server + auth)")
        print("   To test manually:")
        print(f"   curl http://localhost:8001/api/jobs/{job_id}/debug")

    except ImportError:
        print("⚠️  requests library not available, skipping API test")


def test_helper_functions():
    """Test helper functions work correctly"""
    print("\n🧪 Test 4: Helper Functions Test")
    print("=" * 50)

    # Test with sample video if exists
    test_video_path = "./io/input/test.mp4"

    if not os.path.exists(test_video_path):
        print("⚠️  No test video found, skipping helper tests")
        print(f"   Create a test video at: {test_video_path}")
        return

    from agents2.shared.utils.video_helpers import (
        generate_thumbnail,
        get_duration,
        get_resolution
    )

    # Test get_duration
    try:
        duration = get_duration(test_video_path)
        print(f"✅ get_duration() works: {duration}s")
    except Exception as e:
        print(f"❌ get_duration() failed: {e}")

    # Test get_resolution
    try:
        resolution = get_resolution(test_video_path)
        print(f"✅ get_resolution() works: {resolution}")
    except Exception as e:
        print(f"❌ get_resolution() failed: {e}")

    # Test generate_thumbnail
    try:
        thumbnail = generate_thumbnail(test_video_path, timestamp=1.0)
        if thumbnail and os.path.exists(thumbnail):
            print(f"✅ generate_thumbnail() works: {thumbnail}")
        else:
            print("❌ generate_thumbnail() returned no path")
    except Exception as e:
        print(f"❌ generate_thumbnail() failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  Job Debug Viewer Integration Tests")
    print("="*60)

    try:
        # Test 1: Basic wrapper
        job_id_1 = test_wrapper_basic()

        # Test 2: Wrapper with mock agent
        job_id_2 = test_wrapper_with_mock_agent()

        # Test 3: API endpoint (requires running server)
        test_api_endpoint(job_id_1)

        # Test 4: Helper functions
        test_helper_functions()

        print("\n" + "="*60)
        print("  Test Summary")
        print("="*60)
        print("✅ All tests completed!")
        print("\n📊 Next Steps:")
        print(f"   1. Start API: python3 -m api.main")
        print(f"   2. Open debug viewer:")
        print(f"      http://localhost:8001/ui-v2/job-debug.html?job={job_id_1}")
        print(f"   3. Verify steps appear in UI")
        print("\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
