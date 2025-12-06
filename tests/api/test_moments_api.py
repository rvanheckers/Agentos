"""
API Integration Tests: Moments Endpoints
=========================================

Tests voor:
- GET /api/jobs/{id}/moments
- POST /api/jobs/{id}/generate-clips
"""

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.main import app
from core.database_pool import get_db_session
from core.database_manager import Job, Moment, Clip

# Mock auth dependency for testing
def mock_get_current_user():
    return {"id": "test-user-123", "is_admin": True}

# Override auth dependency
from api.services import auth_dependencies
auth_dependencies.get_current_user = mock_get_current_user

client = TestClient(app)


class TestMomentsAPI:
    """Test Moments API endpoints"""

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

    def test_get_moments_success(self):
        """
        Test: GET /api/jobs/{id}/moments returns moments
        """
        # Setup: Create job with moments
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user-123',
                video_url='test.mp4',
                phase='awaiting_selection',
                status='processing'
            )
            session.add(job)
            session.flush()

            # Create 5 moments
            for i in range(5):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 30.0,
                    end_time=(i + 1) * 30.0,
                    duration=30.0,
                    description=f'Viral moment {i}',
                    sentence_text=f'Test sentence {i}',
                    keywords=['test', f'keyword{i}'],
                    viral_score=90 - i * 5
                )
                session.add(moment)

            session.commit()

        # Test: Get moments
        response = client.get(f'/api/jobs/{job_id}/moments')

        # Verify
        assert response.status_code == 200

        data = response.json()
        assert data['job_id'] == job_id
        assert data['phase'] == 'awaiting_selection'
        assert data['total_moments'] == 5
        assert len(data['moments']) == 5

        # Check moment structure
        moment = data['moments'][0]
        assert 'id' in moment
        assert moment['moment_index'] == 0
        assert moment['start_time'] == 0.0
        assert moment['end_time'] == 30.0
        assert moment['duration'] == 30.0
        assert moment['viral_score'] == 90
        assert moment['is_selected'] == False

        print("✅ GET /moments success test PASSED")

    def test_get_moments_not_ready(self):
        """
        Test: GET /moments should fail if Phase 1 not complete
        """
        # Setup: Job in phase1_analysis (not ready yet)
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user-123',
                video_url='test.mp4',
                phase='phase1_analysis',  # Still analyzing
                status='processing'
            )
            session.add(job)
            session.commit()

        # Test: Get moments should fail
        response = client.get(f'/api/jobs/{job_id}/moments')

        # Verify error
        assert response.status_code == 400
        assert 'phase' in response.json()['detail'].lower()

        print("✅ GET /moments not ready test PASSED")

    def test_get_moments_not_found(self):
        """
        Test: GET /moments should return 404 for non-existent job
        """
        fake_job_id = str(uuid.uuid4())

        response = client.get(f'/api/jobs/{fake_job_id}/moments')

        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

        print("✅ GET /moments not found test PASSED")

    @patch('api.routes.moments.create_phase2_workflow')
    def test_generate_clips_success(self, mock_create_workflow):
        """
        Test: POST /generate-clips should trigger Phase 2
        """
        # Mock workflow
        mock_workflow = MagicMock()
        mock_create_workflow.return_value = mock_workflow

        # Setup: Job with moments in awaiting_selection phase
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user-123',
                video_url='test.mp4',
                phase='awaiting_selection',
                status='processing',
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
                    start_time=i * 10,
                    end_time=(i + 1) * 10,
                    duration=10,
                    viral_score=80
                )
                session.add(moment)
                moments.append(moment)

            session.commit()

        # Test: Select 2 moments (indices 0 and 2)
        response = client.post(
            f'/api/jobs/{job_id}/generate-clips',
            json={'selected_moments': [0, 2]}
        )

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert data['job_id'] == job_id
        assert data['selected_count'] == 2
        assert data['phase'] == 'phase2_generation'
        assert 'Generating 2 clips' in data['message']

        # Verify database updated
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            assert job.phase == 'phase2_generation'
            assert job.progress == 50

            # Verify moments marked as selected
            selected = session.query(Moment).filter(
                Moment.job_id == job_id,
                Moment.is_selected == True
            ).all()

            assert len(selected) == 2
            assert all(m.moment_index in [0, 2] for m in selected)
            assert all(m.selected_at is not None for m in selected)

        # Verify workflow was called
        assert mock_create_workflow.called
        assert mock_workflow.apply_async.called

        print("✅ POST /generate-clips success test PASSED")

    def test_generate_clips_empty_selection(self):
        """
        Test: POST /generate-clips should fail with empty selection
        """
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user-123',
                video_url='test.mp4',
                phase='awaiting_selection'
            )
            session.add(job)
            session.commit()

        # Test: Empty selection
        response = client.post(
            f'/api/jobs/{job_id}/generate-clips',
            json={'selected_moments': []}
        )

        # Verify error
        assert response.status_code == 400
        assert 'no moments selected' in response.json()['detail'].lower()

        print("✅ POST /generate-clips empty selection test PASSED")

    def test_generate_clips_invalid_indices(self):
        """
        Test: POST /generate-clips should fail with invalid moment indices
        """
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user-123',
                video_url='test.mp4',
                phase='awaiting_selection'
            )
            session.add(job)
            session.flush()

            # Create 3 moments (indices 0, 1, 2)
            for i in range(3):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 10,
                    end_time=(i + 1) * 10,
                    duration=10,
                    viral_score=70
                )
                session.add(moment)

            session.commit()

        # Test: Select invalid index 99
        response = client.post(
            f'/api/jobs/{job_id}/generate-clips',
            json={'selected_moments': [0, 99]}  # 99 doesn't exist
        )

        # Verify error
        assert response.status_code == 400
        assert 'invalid moment indices' in response.json()['detail'].lower()
        assert '99' in response.json()['detail']

        print("✅ POST /generate-clips invalid indices test PASSED")

    def test_generate_clips_wrong_phase(self):
        """
        Test: POST /generate-clips should fail if job not in awaiting_selection
        """
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user-123',
                video_url='test.mp4',
                phase='completed'  # Already completed
            )
            session.add(job)
            session.commit()

        # Test: Try to generate clips
        response = client.post(
            f'/api/jobs/{job_id}/generate-clips',
            json={'selected_moments': [0]}
        )

        # Verify error
        assert response.status_code == 400
        assert 'awaiting_selection' in response.json()['detail'].lower()

        print("✅ POST /generate-clips wrong phase test PASSED")


if __name__ == "__main__":
    """Run tests directly"""
    test = TestMomentsAPI()
    test.setup_and_teardown().__next__()

    try:
        print("\n🧪 Running Moments API Tests\n")
        print("=" * 60)

        test.test_get_moments_success()
        test.test_get_moments_not_ready()
        test.test_get_moments_not_found()
        test.test_generate_clips_success()
        test.test_generate_clips_empty_selection()
        test.test_generate_clips_invalid_indices()
        test.test_generate_clips_wrong_phase()

        print("\n" + "=" * 60)
        print("🎉 ALL API TESTS PASSED!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        list(test.setup_and_teardown())[-1]
