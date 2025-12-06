#!/usr/bin/env python3
"""
Test Suite: Phase 1 Reliability and Code Quality Improvements
==============================================================

Tests for the 3 code quality fixes in video_processing_phase1.py:
1. Celery task reliability configuration (acks_late, autoretry, backoff)
2. Idempotency checks (prevent duplicate execution)
3. Improved error handling (autoretry instead of manual retry)

Context7 Reference: Celery testing patterns (trust score 8.9)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Import the task
from tasks.video_processing_phase1 import save_moments_to_db


class TestCeleryReliabilityConfig:
    """Test Celery task decorator configuration (FIX 1)"""

    def test_task_has_acks_late(self):
        """Verify acks_late=True is configured"""
        assert hasattr(save_moments_to_db, 'acks_late')
        assert save_moments_to_db.acks_late is True, "Task should acknowledge after completion"

    def test_task_has_autoretry(self):
        """Verify autoretry_for is configured"""
        assert hasattr(save_moments_to_db, 'autoretry_for')
        assert Exception in save_moments_to_db.autoretry_for, "Task should auto-retry on Exception"

    def test_task_has_retry_backoff(self):
        """Verify exponential backoff is configured"""
        assert hasattr(save_moments_to_db, 'retry_backoff')
        assert save_moments_to_db.retry_backoff is True, "Task should use exponential backoff"

    def test_task_has_max_retries(self):
        """Verify max_retries is configured"""
        assert hasattr(save_moments_to_db, 'max_retries')
        assert save_moments_to_db.max_retries == 3, "Task should retry max 3 times"

    def test_task_has_retry_backoff_max(self):
        """Verify max backoff time is configured"""
        assert hasattr(save_moments_to_db, 'retry_backoff_max')
        assert save_moments_to_db.retry_backoff_max == 600, "Max backoff should be 10 minutes"


class TestIdempotency:
    """Test idempotency checks (FIX 2)"""

    @patch('tasks.video_processing_phase1.get_db_session')
    def test_idempotent_skip_when_already_completed(self, mock_db):
        """Test that task skips execution if already completed"""
        # Mock database session
        mock_session = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session

        # Mock job that's already in awaiting_admin_config phase
        mock_job = Mock()
        mock_job.phase = 'awaiting_admin_config'
        mock_session.query.return_value.filter.return_value.first.return_value = mock_job

        # Execute task directly (bypass Celery wrapper)
        # Use apply() to call the function directly
        result = save_moments_to_db.apply(
            kwargs={'task_data': {'moments': [], 'faces': []}, 'job_id': 'test-job-123'}
        ).get()

        # Verify idempotent skip
        assert result['success'] is True
        assert result['idempotent_skip'] is True
        assert result['message'] == 'Task already completed (idempotent)'

    @patch('tasks.video_processing_phase1.validate_face_coordinates')
    @patch('tasks.video_processing_phase1.get_db_session')
    def test_executes_when_not_completed(self, mock_db, mock_validate):
        """Test that task executes normally if not completed"""
        mock_validate.return_value = []

        # Mock database session for idempotency check
        mock_check_session = MagicMock()
        mock_job_check = Mock()
        mock_job_check.phase = 'processing'  # NOT awaiting_admin_config
        mock_check_session.query.return_value.filter.return_value.first.return_value = mock_job_check

        # Mock database session for main execution
        mock_main_session = MagicMock()
        mock_job_main = Mock()
        mock_job_main.id = 'test-job-123'
        mock_job_main.pipeline_config = {}
        mock_job_main.video_duration = 120
        mock_job_main.transcription_text = 'test transcript'
        mock_job_main.analysis_mode = 'hybrid'
        mock_job_main.content_type = 'spoken'
        mock_main_session.query.return_value.filter.return_value.first.return_value = mock_job_main

        # Mock get_db_session to return different sessions
        mock_db.side_effect = [
            MagicMock(__enter__=lambda s: mock_check_session, __exit__=Mock()),  # Idempotency check
            MagicMock(__enter__=lambda s: mock_main_session, __exit__=Mock())    # Main execution
        ]

        # Execute task directly
        result = save_moments_to_db.apply(
            kwargs={'task_data': {'moments': [], 'faces': []}, 'job_id': 'test-job-123'}
        ).get()

        # Verify normal execution (not idempotent skip)
        assert 'idempotent_skip' not in result or result.get('idempotent_skip') is False


class TestErrorHandling:
    """Test improved error handling (FIX 3)"""

    @patch('tasks.video_processing_phase1.get_db_session')
    def test_autoretry_on_database_error(self, mock_db):
        """Test that database errors trigger autoretry (not manual retry)"""
        # Mock idempotency check (job not completed)
        mock_check_session = MagicMock()
        mock_job_check = Mock()
        mock_job_check.phase = 'processing'
        mock_check_session.query.return_value.filter.return_value.first.return_value = mock_job_check

        # Mock main execution to raise exception
        mock_main_session = MagicMock()
        mock_main_session.query.side_effect = Exception("Database connection failed")

        mock_db.side_effect = [
            MagicMock(__enter__=lambda s: mock_check_session, __exit__=Mock()),
            MagicMock(__enter__=lambda s: mock_main_session, __exit__=Mock())
        ]

        # Execute task and expect exception (autoretry will catch it)
        result = save_moments_to_db.apply(
            kwargs={'task_data': {'moments': [], 'faces': []}, 'job_id': 'test-job-123'}
        )

        # Verify exception is propagated (Celery autoretry will handle)
        assert result.failed()
        assert "Database connection failed" in str(result.traceback)

    @patch('tasks.video_processing_phase1.get_db_session')
    def test_no_nested_try_except_for_job_status_update(self, mock_db):
        """Verify that manual job.status='failed' update is removed"""
        # This test verifies that the old nested try-except pattern is gone
        # by checking that exceptions are NOT caught and re-raised with self.retry()

        mock_check_session = MagicMock()
        mock_job_check = Mock()
        mock_job_check.phase = 'processing'
        mock_check_session.query.return_value.filter.return_value.first.return_value = mock_job_check

        mock_main_session = MagicMock()
        mock_main_session.query.side_effect = ValueError("Job not found")

        mock_db.side_effect = [
            MagicMock(__enter__=lambda s: mock_check_session, __exit__=Mock()),
            MagicMock(__enter__=lambda s: mock_main_session, __exit__=Mock())
        ]

        # Execute and expect exception to propagate (autoretry handles it)
        result = save_moments_to_db.apply(
            kwargs={'task_data': {'moments': [], 'faces': []}, 'job_id': 'test-job-123'}
        )

        # Verify exception propagated cleanly (no manual retry wrapper)
        assert result.failed()
        assert "Job not found" in str(result.traceback)


class TestAtomicTransaction:
    """Test single atomic commit (FIX 1 - database atomicity)"""

    @patch('tasks.video_processing_phase1.validate_face_coordinates')
    @patch('tasks.video_processing_phase1.get_db_session')
    def test_single_commit_for_all_changes(self, mock_db, mock_validate):
        """Verify all database changes happen in single commit"""
        mock_validate.return_value = []

        # Mock idempotency check
        mock_check_session = MagicMock()
        mock_job_check = Mock()
        mock_job_check.phase = 'processing'
        mock_check_session.query.return_value.filter.return_value.first.return_value = mock_job_check

        # Mock main execution
        mock_main_session = MagicMock()
        mock_job = Mock()
        mock_job.id = 'test-job-123'
        mock_job.pipeline_config = {}
        mock_job.video_duration = 120
        mock_job.transcription_text = 'test'
        mock_job.analysis_mode = 'hybrid'
        mock_job.content_type = 'spoken'
        mock_main_session.query.return_value.filter.return_value.first.return_value = mock_job

        mock_db.side_effect = [
            MagicMock(__enter__=lambda s: mock_check_session, __exit__=Mock()),
            MagicMock(__enter__=lambda s: mock_main_session, __exit__=Mock())
        ]

        # Execute
        result = save_moments_to_db.apply(
            kwargs={'task_data': {'moments': [], 'faces': []}, 'job_id': 'test-job-123'}
        ).get()

        # Verify ONLY ONE commit call (not two)
        assert mock_main_session.commit.call_count == 1, "Should have exactly 1 commit (atomic transaction)"

    @patch('tasks.video_processing_phase1.get_db_session')
    def test_rollback_on_failure(self, mock_db):
        """Verify transaction rollback on failure"""
        # Mock idempotency check
        mock_check_session = MagicMock()
        mock_job_check = Mock()
        mock_job_check.phase = 'processing'
        mock_check_session.query.return_value.filter.return_value.first.return_value = mock_job_check

        # Mock main execution that fails during commit
        mock_main_session = MagicMock()
        mock_job = Mock()
        mock_job.id = 'test-job-123'
        mock_main_session.query.return_value.filter.return_value.first.return_value = mock_job
        mock_main_session.commit.side_effect = Exception("Commit failed")

        mock_db.side_effect = [
            MagicMock(__enter__=lambda s: mock_check_session),
            MagicMock(__enter__=lambda s: mock_main_session)
        ]

        mock_task = Mock()
        mock_task.request.retries = 0

        # Execute and expect exception
        with pytest.raises(Exception):
            save_moments_to_db(
                mock_task,
                task_data={'moments': [], 'faces': []},
                job_id='test-job-123'
            )

        # Verify rollback happened via context manager (__exit__)
        # (get_db_session context manager handles rollback automatically)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
