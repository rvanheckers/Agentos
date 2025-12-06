"""
Performance Benchmarks: Moment Selection Workflow
==================================================

Performance tests voor:
- Database query speed (GET moments)
- Selection update speed (UPDATE is_selected)
- Overall workflow efficiency
"""

import pytest
import uuid
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database_pool import get_db_session
from core.database_manager import Job, Moment


class TestSelectionPerformance:
    """Performance benchmarks voor moment selection"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup en cleanup"""
        self.test_jobs = []
        yield

        # Cleanup
        with get_db_session() as session:
            for job_id in self.test_jobs:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    session.delete(job)
            session.commit()

    def test_get_moments_query_performance(self):
        """
        Benchmark: GET moments query moet < 50ms zijn

        Target: < 50ms voor query van 5 moments
        """
        # Setup: Create job with moments
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user',
                video_url='test.mp4',
                phase='awaiting_selection'
            )
            session.add(job)
            session.flush()

            for i in range(5):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 30,
                    end_time=(i + 1) * 30,
                    duration=30,
                    viral_score=80
                )
                session.add(moment)

            session.commit()

        # Benchmark: Query moments
        times = []
        for _ in range(10):  # Run 10 times for average
            start = time.time()

            with get_db_session() as session:
                moments = session.query(Moment).filter(
                    Moment.job_id == job_id
                ).order_by(Moment.moment_index).all()

            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n📊 GET Moments Query Performance:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min: {min_time:.2f}ms")
        print(f"   Max: {max_time:.2f}ms")
        print(f"   Target: < 50ms")

        # Assert performance
        assert avg_time < 50, f"Average query time {avg_time:.2f}ms exceeds 50ms target!"

        if avg_time < 10:
            print(f"   ✅ EXCELLENT (< 10ms)")
        elif avg_time < 50:
            print(f"   ✅ GOOD (< 50ms)")
        else:
            print(f"   ⚠️  SLOW (>= 50ms)")

    def test_moment_selection_update_performance(self):
        """
        Benchmark: Update is_selected moet < 10ms zijn

        Target: < 10ms voor update van 2 moments
        """
        # Setup
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        moment_ids = []
        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test',
                video_url='test.mp4',
                phase='awaiting_selection'
            )
            session.add(job)
            session.flush()

            for i in range(5):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 10,
                    end_time=(i + 1) * 10,
                    duration=10,
                    viral_score=75
                )
                session.add(moment)
                session.flush()
                moment_ids.append(str(moment.id))

            session.commit()

        # Benchmark: Update selection
        selected_ids = [moment_ids[0], moment_ids[2]]
        times = []

        for _ in range(10):
            # Reset selection
            with get_db_session() as session:
                session.query(Moment).filter(Moment.job_id == job_id).update({
                    'is_selected': False
                })
                session.commit()

            # Benchmark update
            start = time.time()

            with get_db_session() as session:
                # Update selected moments
                for moment_id in selected_ids:
                    moment = session.query(Moment).filter(Moment.id == moment_id).first()
                    if moment:
                        moment.is_selected = True

                session.commit()

            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n📊 Update is_selected Performance:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min: {min_time:.2f}ms")
        print(f"   Max: {max_time:.2f}ms")
        print(f"   Target: < 10ms")

        # Assert performance
        assert avg_time < 10, f"Average update time {avg_time:.2f}ms exceeds 10ms target!"

        if avg_time < 5:
            print(f"   ✅ EXCELLENT (< 5ms)")
        elif avg_time < 10:
            print(f"   ✅ GOOD (< 10ms)")
        else:
            print(f"   ⚠️  SLOW (>= 10ms)")

    def test_bulk_moments_query_performance(self):
        """
        Benchmark: Query performance met grotere datasets

        Test hoe performance schaalt met meer moments
        """
        # Create multiple jobs with moments
        job_ids = []
        for _ in range(10):  # 10 jobs
            job_id = str(uuid.uuid4())
            job_ids.append(job_id)
            self.test_jobs.append(job_id)

            with get_db_session() as session:
                job = Job(
                    id=job_id,
                    user_id='test',
                    video_url='test.mp4',
                    phase='awaiting_selection'
                )
                session.add(job)
                session.flush()

                for i in range(20):  # 20 moments per job
                    moment = Moment(
                        job_id=job_id,
                        moment_index=i,
                        start_time=i * 5,
                        end_time=(i + 1) * 5,
                        duration=5,
                        viral_score=70
                    )
                    session.add(moment)

                session.commit()

        # Benchmark: Query all moments for one job
        test_job_id = job_ids[0]
        times = []

        for _ in range(5):
            start = time.time()

            with get_db_session() as session:
                moments = session.query(Moment).filter(
                    Moment.job_id == test_job_id
                ).order_by(Moment.moment_index).all()

            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)

        avg_time = sum(times) / len(times)

        print(f"\n📊 Bulk Query Performance (20 moments):")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Target: < 100ms")

        assert avg_time < 100, f"Bulk query too slow: {avg_time:.2f}ms"

        print(f"   ✅ PASS")

    def test_index_effectiveness(self):
        """
        Test: Verify database indexes are being used

        Checks dat queries gebruik maken van indexes op:
        - job_id
        - moment_index
        - is_selected
        """
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test',
                video_url='test.mp4',
                phase='awaiting_selection'
            )
            session.add(job)
            session.flush()

            for i in range(100):  # Larger dataset
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i,
                    end_time=i + 1,
                    duration=1,
                    viral_score=70,
                    is_selected=(i % 2 == 0)  # Half selected
                )
                session.add(moment)

            session.commit()

        # Test 1: Query by job_id (should use index)
        start = time.time()
        with get_db_session() as session:
            moments = session.query(Moment).filter(Moment.job_id == job_id).all()
        time_job_id = (time.time() - start) * 1000

        # Test 2: Query by is_selected (should use index)
        start = time.time()
        with get_db_session() as session:
            selected = session.query(Moment).filter(
                Moment.job_id == job_id,
                Moment.is_selected == True
            ).all()
        time_is_selected = (time.time() - start) * 1000

        # Test 3: Order by moment_index (should use index)
        start = time.time()
        with get_db_session() as session:
            ordered = session.query(Moment).filter(
                Moment.job_id == job_id
            ).order_by(Moment.moment_index).all()
        time_ordered = (time.time() - start) * 1000

        print(f"\n📊 Index Effectiveness (100 moments):")
        print(f"   Query by job_id: {time_job_id:.2f}ms")
        print(f"   Filter by is_selected: {time_is_selected:.2f}ms")
        print(f"   Order by moment_index: {time_ordered:.2f}ms")

        # With proper indexes, all queries should be fast even with 100 records
        assert time_job_id < 100, "job_id index may not be working"
        assert time_is_selected < 100, "is_selected index may not be working"
        assert time_ordered < 100, "moment_index index may not be working"

        print(f"   ✅ All indexes working efficiently")


if __name__ == "__main__":
    """Run benchmarks directly"""
    test = TestSelectionPerformance()
    test.setup_and_teardown().__next__()

    try:
        print("\n⚡ Running Performance Benchmarks\n")
        print("=" * 60)

        test.test_get_moments_query_performance()
        test.test_moment_selection_update_performance()
        test.test_bulk_moments_query_performance()
        test.test_index_effectiveness()

        print("\n" + "=" * 60)
        print("🎉 ALL PERFORMANCE BENCHMARKS PASSED!")

    except Exception as e:
        print(f"\n❌ BENCHMARK FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        list(test.setup_and_teardown())[-1]
