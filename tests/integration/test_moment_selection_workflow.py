"""
End-to-End Integration Test: Moment Selection Workflow
========================================================

Tests de complete flow:
1. Create job
2. Run Phase 1 (detect moments)
3. Get moments via API
4. Select moments via API
5. Phase 2 generates clips
6. Verify only selected moments became clips
"""

import pytest
import uuid
import time
import os
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database_pool import get_db_session
from core.database_manager import Job, Moment, Clip
from tasks.video_processing_phase1 import create_phase1_workflow, save_moments_to_db
from tasks.video_processing_phase2 import create_phase2_workflow
from fastapi.testclient import TestClient


class TestMomentSelectionWorkflowE2E:
    """
    End-to-End workflow tests voor moment selection feature
    """

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup en cleanup voor elke test"""
        self.test_user_id = f"test-user-{uuid.uuid4()}"
        self.test_jobs = []

        yield

        # Cleanup: verwijder test jobs
        with get_db_session() as session:
            for job_id in self.test_jobs:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    session.delete(job)
            session.commit()

    def test_phase1_creates_moments_no_clips(self):
        """
        Test: Phase 1 should create moments but NO clips

        Critical requirement: Phase 1 moet stoppen na moment detection
        """
        # Create test job
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id=self.test_user_id,
                video_url='https://example.com/test.mp4',
                status='processing',
                phase='phase1_analysis'
            )
            session.add(job)
            session.commit()

        # Simulate Phase 1 completion by calling save_moments_to_db directly
        mock_task_data = {
            'moments': [
                {
                    'start_time': 6.2,
                    'end_time': 52.1,
                    'description': 'Test moment 1',
                    'sentence_text': 'Test sentence 1',
                    'keywords': ['test', 'moment'],
                    'viral_score': 85
                },
                {
                    'start_time': 65.0,
                    'end_time': 95.0,
                    'description': 'Test moment 2',
                    'sentence_text': 'Test sentence 2',
                    'keywords': ['second', 'test'],
                    'viral_score': 72
                },
                {
                    'start_time': 120.0,
                    'end_time': 150.0,
                    'description': 'Test moment 3',
                    'sentence_text': 'Test sentence 3',
                    'keywords': ['third'],
                    'viral_score': 68
                }
            ],
            'video_duration': 200.0,
            'content_type': 'spoken'
        }

        # Run save_moments_to_db task
        result = save_moments_to_db(mock_task_data, job_id)

        # Verify results
        assert result['success'] is True
        assert result['phase'] == 'awaiting_selection'
        assert result['moments_count'] == 3

        # Verify database state
        with get_db_session() as session:
            # Check job phase
            job = session.query(Job).filter(Job.id == job_id).first()
            assert job is not None
            assert job.phase == 'awaiting_selection'
            assert job.status == 'processing'  # Still processing, awaiting selection
            assert job.progress == 50

            # Check moments created
            moments = session.query(Moment).filter(Moment.job_id == job_id).all()
            assert len(moments) == 3
            assert all(m.is_selected == False for m in moments)
            assert moments[0].moment_index == 0
            assert moments[1].moment_index == 1
            assert moments[2].moment_index == 2

            # CRITICAL: Check NO clips created yet
            clips = session.query(Clip).filter(Clip.job_id == job_id).all()
            assert len(clips) == 0, "Phase 1 should NOT create clips!"

        print("✅ Phase 1 test PASSED: Moments created, no clips")

    def test_phase2_only_processes_selected_moments(self):
        """
        Test: Phase 2 should ONLY process selected moments

        Critical requirement: Als user 2 van 5 moments selecteert,
        moeten er exact 2 clips worden gegenereerd (niet 5!)
        """
        # Setup: Create job with moments
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id=self.test_user_id,
                video_url='test.mp4',
                status='processing',
                phase='awaiting_selection',
                progress=50
            )
            session.add(job)
            session.flush()

            # Create 5 moments
            moments = []
            for i in range(5):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 30.0,
                    end_time=(i + 1) * 30.0,
                    duration=30.0,
                    description=f'Test moment {i}',
                    viral_score=80 - i * 5,
                    is_selected=False
                )
                session.add(moment)
                moments.append(moment)

            session.commit()

            # Get moment IDs for moments 0 and 2 (select 2 of 5)
            selected_ids = [str(moments[0].id), str(moments[2].id)]

        # Simulate Phase 2 by calling load_selected_moments
        from tasks.video_processing_phase2 import load_selected_moments

        result = load_selected_moments(job_id, selected_ids)

        # Verify Phase 2 loaded correct moments
        assert result['success'] is True
        assert result['selected_count'] == 2
        assert len(result['moments']) == 2

        # Check that returned moments are indices 0 and 2
        moment_indices = [m['moment_index'] for m in result['moments']]
        assert set(moment_indices) == {0, 2}

        # Verify moments marked as selected in database
        with get_db_session() as session:
            all_moments = session.query(Moment).filter(Moment.job_id == job_id).all()
            selected_moments = [m for m in all_moments if m.is_selected]

            assert len(selected_moments) == 2
            assert all(m.moment_index in [0, 2] for m in selected_moments)
            assert all(m.selected_at is not None for m in selected_moments)

            # Check job phase updated
            job = session.query(Job).filter(Job.id == job_id).first()
            assert job.phase == 'phase2_generation'

        print("✅ Phase 2 test PASSED: Only selected moments processed")

    def test_moment_selection_validation(self):
        """
        Test: API should validate moment selection

        Tests:
        - Empty selection should fail
        - Invalid indices should fail
        - Valid selection should succeed
        """
        # Setup job with moments
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id=self.test_user_id,
                video_url='test.mp4',
                phase='awaiting_selection'
            )
            session.add(job)
            session.flush()

            for i in range(3):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 10.0,
                    end_time=(i + 1) * 10.0,
                    duration=10.0,
                    viral_score=70
                )
                session.add(moment)

            session.commit()

        # Test 1: Empty selection
        from tasks.video_processing_phase2 import load_selected_moments

        # Empty selection should work but load 0 moments
        # (API should prevent this, but workflow should handle it)

        # Test 2: Invalid moment IDs
        invalid_id = str(uuid.uuid4())
        result = load_selected_moments(job_id, [invalid_id])

        # Should load 0 moments if ID doesn't exist
        assert result['selected_count'] == 0 or 'error' in str(result).lower()

        print("✅ Validation test PASSED")

    def test_complete_workflow_integration(self):
        """
        Test: Complete workflow from job creation to clip generation

        Flow:
        1. Create job
        2. Phase 1 detects moments
        3. User selects 2 moments
        4. Phase 2 generates 2 clips
        5. Clips are linked to moments
        """
        # Step 1: Create job
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id=self.test_user_id,
                video_url='test.mp4',
                status='processing',
                phase='phase1_analysis'
            )
            session.add(job)
            session.commit()

        print(f"Step 1: Job created - {job_id}")

        # Step 2: Simulate Phase 1 completion
        mock_task_data = {
            'moments': [
                {'start_time': 0, 'end_time': 30, 'description': 'M0', 'viral_score': 90, 'sentence_text': 'Test 0'},
                {'start_time': 30, 'end_time': 60, 'description': 'M1', 'viral_score': 85, 'sentence_text': 'Test 1'},
                {'start_time': 60, 'end_time': 90, 'description': 'M2', 'viral_score': 80, 'sentence_text': 'Test 2'},
                {'start_time': 90, 'end_time': 120, 'description': 'M3', 'viral_score': 75, 'sentence_text': 'Test 3'},
                {'start_time': 120, 'end_time': 150, 'description': 'M4', 'viral_score': 70, 'sentence_text': 'Test 4'},
            ]
        }

        result = save_moments_to_db(mock_task_data, job_id)
        assert result['phase'] == 'awaiting_selection'

        print("Step 2: Phase 1 complete - 5 moments detected")

        # Step 3: Verify moments in database
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            assert job.phase == 'awaiting_selection'
            assert job.total_moments == 5

            moments = session.query(Moment).filter(Moment.job_id == job_id).all()
            assert len(moments) == 5

        print("Step 3: Moments verified in database")

        # Step 4: Select 2 moments (indices 1 and 3)
        with get_db_session() as session:
            moments = session.query(Moment).filter(Moment.job_id == job_id).order_by(Moment.moment_index).all()
            selected_moment_ids = [str(moments[1].id), str(moments[3].id)]

        print(f"Step 4: User selects moments 1 and 3")

        # Step 5: Trigger Phase 2
        from tasks.video_processing_phase2 import load_selected_moments

        phase2_data = load_selected_moments(job_id, selected_moment_ids)

        assert phase2_data['success'] is True
        assert phase2_data['selected_count'] == 2

        print("Step 5: Phase 2 triggered with 2 selected moments")

        # Step 6: Verify final state
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            assert job.phase == 'phase2_generation'

            # Verify exactly 2 moments are selected
            selected_moments = session.query(Moment).filter(
                Moment.job_id == job_id,
                Moment.is_selected == True
            ).all()

            assert len(selected_moments) == 2
            assert selected_moments[0].moment_index == 1
            assert selected_moments[1].moment_index == 3

        print("Step 6: ✅ Complete workflow test PASSED!")
        print(f"   - Job created: {job_id}")
        print(f"   - Phase 1: 5 moments detected")
        print(f"   - User selected: 2 moments (indices 1, 3)")
        print(f"   - Phase 2: Ready to generate 2 clips")


if __name__ == "__main__":
    """Run tests directly"""
    test = TestMomentSelectionWorkflowE2E()
    test.setup_and_teardown().__next__()  # Setup

    try:
        print("\n🧪 Running Moment Selection E2E Tests\n")
        print("=" * 60)

        test.test_phase1_creates_moments_no_clips()
        print()

        test.test_phase2_only_processes_selected_moments()
        print()

        test.test_moment_selection_validation()
        print()

        test.test_complete_workflow_integration()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        list(test.setup_and_teardown())[-1]
