"""
Test moments table schema and relationships

Tests for the user selection workflow database schema:
- Moment model creation
- Job <-> Moment relationships
- Moment <-> Clip relationships
- Cascade delete behavior
- Index existence
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from core.database_manager import PostgreSQLManager, Job, Moment, Clip


@pytest.fixture
def db():
    """Provide database manager instance"""
    return PostgreSQLManager()


def test_moment_model_creation(db):
    """Test creating a moment record"""
    with db.get_session() as session:
        # Create test job
        job = Job(
            user_id='test-user',
            video_url='https://example.com/test.mp4',
            status='processing'
        )
        session.add(job)
        session.flush()

        # Create moment
        moment = Moment(
            job_id=job.id,
            moment_index=0,
            start_time=6.2,
            end_time=52.1,
            duration=45.9,
            description="Test viral moment",
            sentence_text="This is a test sentence",
            keywords=["test", "moment"],
            viral_score=85,
            is_selected=False
        )
        session.add(moment)
        session.commit()

        # Validate
        assert moment.id is not None
        assert moment.job_id == job.id
        assert moment.moment_index == 0
        assert moment.start_time == 6.2
        assert moment.end_time == 52.1
        assert moment.duration == 45.9
        assert moment.description == "Test viral moment"
        assert moment.sentence_text == "This is a test sentence"
        assert moment.keywords == ["test", "moment"]
        assert moment.viral_score == 85
        assert moment.is_selected == False
        assert moment.created_at is not None

        # Cleanup
        session.delete(job)
        session.commit()


def test_job_moments_relationship(db):
    """Test Job <-> Moments relationship"""
    with db.get_session() as session:
        # Create job
        job = Job(
            user_id='test-user',
            video_url='test.mp4',
            status='processing'
        )

        # Create moments
        moment1 = Moment(
            job=job,
            moment_index=0,
            start_time=0,
            end_time=10,
            duration=10,
            viral_score=80
        )
        moment2 = Moment(
            job=job,
            moment_index=1,
            start_time=10,
            end_time=20,
            duration=10,
            viral_score=90
        )

        session.add_all([job, moment1, moment2])
        session.commit()

        # Test relationship
        assert len(job.moments) == 2
        assert job.moments[0].moment_index == 0
        assert job.moments[1].moment_index == 1
        assert moment1.job.id == job.id
        assert moment2.job.id == job.id

        # Cleanup
        session.delete(job)
        session.commit()


def test_moment_clip_relationship(db):
    """Test Moment <-> Clip relationship"""
    with db.get_session() as session:
        # Create job and moment
        job = Job(
            user_id='test',
            video_url='test.mp4',
            status='processing'
        )
        moment = Moment(
            job=job,
            moment_index=0,
            start_time=0,
            end_time=10,
            duration=10,
            viral_score=85
        )

        session.add_all([job, moment])
        session.flush()

        # Create clip linked to moment
        clip = Clip(
            job=job,
            moment=moment,
            file_path='/test/clip.mp4',
            duration=10.0
        )

        session.add(clip)
        session.commit()

        # Test relationship
        assert clip.moment_id == moment.id
        assert len(moment.clips) == 1
        assert moment.clips[0].id == clip.id

        # Cleanup
        session.delete(job)
        session.commit()


def test_cascade_delete(db):
    """Test that deleting job deletes moments"""
    with db.get_session() as session:
        # Create job and moment
        job = Job(
            user_id='test',
            video_url='test.mp4',
            status='processing'
        )
        moment = Moment(
            job=job,
            moment_index=0,
            start_time=0,
            end_time=10,
            duration=10
        )

        session.add_all([job, moment])
        session.commit()

        job_id = job.id
        moment_id = moment.id

        # Delete job
        session.delete(job)
        session.commit()

        # Verify moment is also deleted (cascade)
        deleted_moment = session.query(Moment).filter(Moment.id == moment_id).first()
        assert deleted_moment is None


def test_moment_selection_tracking(db):
    """Test moment selection tracking fields"""
    with db.get_session() as session:
        # Create job and moment
        job = Job(
            user_id='test',
            video_url='test.mp4',
            status='processing'
        )
        moment = Moment(
            job=job,
            moment_index=0,
            start_time=0,
            end_time=10,
            duration=10,
            is_selected=False
        )

        session.add_all([job, moment])
        session.commit()

        # Initially not selected
        assert moment.is_selected == False
        assert moment.selected_at is None

        # Select the moment
        moment.is_selected = True
        moment.selected_at = datetime.now(timezone.utc)
        session.commit()

        # Verify selection
        assert moment.is_selected == True
        assert moment.selected_at is not None

        # Cleanup
        session.delete(job)
        session.commit()


def test_job_phase_tracking(db):
    """Test job phase field"""
    with db.get_session() as session:
        # Create job with default phase
        job = Job(
            user_id='test',
            video_url='test.mp4',
            status='processing'
        )

        session.add(job)
        session.commit()

        # Check default phase
        assert job.phase == 'phase1_analysis'

        # Update phase
        job.phase = 'awaiting_selection'
        session.commit()

        # Verify update
        assert job.phase == 'awaiting_selection'

        # Test other phases
        job.phase = 'phase2_generation'
        session.commit()
        assert job.phase == 'phase2_generation'

        # Cleanup
        session.delete(job)
        session.commit()


def test_indexes_exist(db):
    """Verify all required indexes are created"""
    with db.engine.connect() as conn:
        # Check moments table indexes
        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'moments'
        """))
        indexes = [row[0] for row in result]

        assert 'idx_moments_job_id' in indexes
        assert 'idx_moments_is_selected' in indexes
        assert 'idx_moments_created_at' in indexes
        assert 'idx_moments_index' in indexes

        # Check jobs table phase index
        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'jobs' AND indexname = 'idx_jobs_phase'
        """))
        phase_index = result.fetchone()
        assert phase_index is not None

        # Check clips table moment_id index
        result = conn.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'clips' AND indexname = 'idx_clips_moment_id'
        """))
        moment_id_index = result.fetchone()
        assert moment_id_index is not None


def test_multiple_moments_per_job(db):
    """Test creating multiple moments for a single job"""
    with db.get_session() as session:
        # Create job
        job = Job(
            user_id='test',
            video_url='test.mp4',
            status='processing'
        )

        # Create 5 moments
        moments = []
        for i in range(5):
            moment = Moment(
                job=job,
                moment_index=i,
                start_time=i * 10,
                end_time=(i + 1) * 10,
                duration=10,
                viral_score=70 + i * 5
            )
            moments.append(moment)

        session.add(job)
        session.add_all(moments)
        session.commit()

        # Verify
        assert len(job.moments) == 5
        for i, moment in enumerate(job.moments):
            assert moment.moment_index == i
            assert moment.viral_score == 70 + i * 5

        # Cleanup
        session.delete(job)
        session.commit()


def test_moment_set_null_on_clip(db):
    """Test that deleting moment sets clip.moment_id to NULL (not cascade delete clip)"""
    with db.get_session() as session:
        # Create job, moment, and clip
        job = Job(
            user_id='test',
            video_url='test.mp4',
            status='processing'
        )
        moment = Moment(
            job=job,
            moment_index=0,
            start_time=0,
            end_time=10,
            duration=10
        )
        clip = Clip(
            job=job,
            moment=moment,
            file_path='/test/clip.mp4'
        )

        session.add_all([job, moment, clip])
        session.commit()

        clip_id = clip.id

        # Delete moment
        session.delete(moment)
        session.commit()

        # Verify clip still exists but moment_id is NULL
        existing_clip = session.query(Clip).filter(Clip.id == clip_id).first()
        assert existing_clip is not None
        assert existing_clip.moment_id is None

        # Cleanup
        session.delete(job)
        session.commit()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
