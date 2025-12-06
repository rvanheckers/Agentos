"""
Workflow Separation Tests: Phase 1 vs Phase 2
==============================================

Tests verificatie dat Phase 1 en Phase 2 correct gescheiden zijn:
- Phase 1 stopt na moment detection (geen clips)
- Phase 2 verwerkt alleen geselecteerde moments
"""

import pytest
import uuid
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database_pool import get_db_session
from core.database_manager import Job, Moment, Clip
from tasks.video_processing_phase1 import save_moments_to_db
from tasks.video_processing_phase2 import load_selected_moments, finalize_phase2


class TestPhaseSeparation:
    """Test dat Phase 1 en Phase 2 onafhankelijk werken"""

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

    def test_phase1_independence(self):
        """
        Test: Phase 1 moet volledig onafhankelijk werken

        Verificaties:
        - Kan draaien zonder Phase 2 dependencies
        - Stopt bij juiste punt (na moment detection)
        - Genereert geen clips
        - Zet job.phase correct
        """
        # Setup job
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user',
                video_url='test.mp4',
                phase='phase1_analysis',
                status='processing'
            )
            session.add(job)
            session.commit()

        # Run Phase 1 save_moments task
        mock_moments_data = {
            'moments': [
                {'start_time': 0, 'end_time': 30, 'description': 'M1', 'viral_score': 80, 'sentence_text': 'Test'},
                {'start_time': 30, 'end_time': 60, 'description': 'M2', 'viral_score': 75, 'sentence_text': 'Test'},
                {'start_time': 60, 'end_time': 90, 'description': 'M3', 'viral_score': 70, 'sentence_text': 'Test'},
            ]
        }

        result = save_moments_to_db(mock_moments_data, job_id)

        # Verify Phase 1 output
        assert result['success'] is True
        assert result['phase'] == 'awaiting_selection'
        assert result['moments_count'] == 3

        # Verify database state
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            # Job should be awaiting selection
            assert job.phase == 'awaiting_selection'
            assert job.status == 'processing'  # Still processing (awaiting user)
            assert job.progress == 50

            # Moments should exist
            moments = session.query(Moment).filter(Moment.job_id == job_id).all()
            assert len(moments) == 3
            assert all(not m.is_selected for m in moments)

            # NO clips should exist yet
            clips = session.query(Clip).filter(Clip.job_id == job_id).all()
            assert len(clips) == 0, "Phase 1 should NOT generate clips!"

        print("✅ Phase 1 independence test PASSED")

    def test_phase2_independence(self):
        """
        Test: Phase 2 moet onafhankelijk van Phase 1 kunnen draaien

        Verificaties:
        - Kan starten met bestaande moments
        - Verwerkt alleen geselecteerde moments
        - Werkt met subset van moments
        """
        # Setup: Job with pre-existing moments
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        moment_ids = []
        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test-user',
                video_url='test.mp4',
                phase='awaiting_selection',
                status='processing',
                progress=50
            )
            session.add(job)
            session.flush()

            # Create 5 moments
            for i in range(5):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 20,
                    end_time=(i + 1) * 20,
                    duration=20,
                    viral_score=85 - i * 3,
                    sentence_text=f'Moment {i}'
                )
                session.add(moment)
                session.flush()
                moment_ids.append(str(moment.id))

            session.commit()

        # Run Phase 2 with selection (moments 0, 2, 4)
        selected_ids = [moment_ids[0], moment_ids[2], moment_ids[4]]

        result = load_selected_moments(job_id, selected_ids)

        # Verify Phase 2 loaded correct moments
        assert result['success'] is True
        assert result['selected_count'] == 3
        assert len(result['moments']) == 3

        # Verify only selected moments are marked
        with get_db_session() as session:
            all_moments = session.query(Moment).filter(Moment.job_id == job_id).all()
            selected = [m for m in all_moments if m.is_selected]

            assert len(selected) == 3
            assert set(m.moment_index for m in selected) == {0, 2, 4}

        print("✅ Phase 2 independence test PASSED")

    def test_phase_separation_no_leakage(self):
        """
        Test: Phase 1 en Phase 2 mogen geen data lekken tussen elkaar

        Verificaties:
        - Phase 1 wijzigt geen Phase 2 data
        - Phase 2 wijzigt geen Phase 1 data
        - Elke phase heeft eigen verantwoordelijkheden
        """
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        # Create job
        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test',
                video_url='test.mp4',
                phase='phase1_analysis'
            )
            session.add(job)
            session.commit()

        # Run Phase 1
        moments_data = {
            'moments': [
                {'start_time': 0, 'end_time': 10, 'description': 'M', 'viral_score': 80, 'sentence_text': 'T'}
            ],
            'extra_phase1_data': 'should_not_affect_phase2'
        }

        phase1_result = save_moments_to_db(moments_data, job_id)

        # Verify Phase 1 didn't touch is_selected
        with get_db_session() as session:
            moment = session.query(Moment).filter(Moment.job_id == job_id).first()
            assert moment.is_selected == False
            assert moment.selected_at is None
            moment_id = str(moment.id)

        # Run Phase 2
        phase2_result = load_selected_moments(job_id, [moment_id])

        # Verify Phase 2 only modified selection fields
        with get_db_session() as session:
            moment = session.query(Moment).filter(Moment.id == moment_id).first()

            # Phase 2 should modify these
            assert moment.is_selected == True
            assert moment.selected_at is not None

            # Phase 2 should NOT modify these (Phase 1 data)
            assert moment.start_time == 0
            assert moment.end_time == 10
            assert moment.description == 'M'

        print("✅ Phase separation no leakage test PASSED")

    def test_clip_moment_linking(self):
        """
        Test: Clips moeten correct gelinkt worden aan moments via moment_id

        Verificaties:
        - finalize_phase2 linkt clips aan moments
        - moment_id foreign key werkt
        - Alleen clips van geselecteerde moments hebben moment_id
        """
        job_id = str(uuid.uuid4())
        self.test_jobs.append(job_id)

        # Setup job with moments
        with get_db_session() as session:
            job = Job(
                id=job_id,
                user_id='test',
                video_url='test.mp4',
                phase='phase2_generation'
            )
            session.add(job)
            session.flush()

            moments = []
            for i in range(2):
                moment = Moment(
                    job_id=job_id,
                    moment_index=i,
                    start_time=i * 10,
                    end_time=(i + 1) * 10,
                    duration=10,
                    viral_score=80,
                    is_selected=True
                )
                session.add(moment)
                session.flush()
                moments.append(moment)

            # Create clips (simulating cut_videos output)
            clips = []
            for i, moment in enumerate(moments):
                clip = Clip(
                    job_id=job_id,
                    file_path=f'/test/clip_{i}.mp4',
                    duration=10.0
                )
                session.add(clip)
                session.flush()
                clips.append(clip)

            session.commit()

            moment_ids = [str(m.id) for m in moments]
            clip_paths = [c.file_path for c in clips]

        # Simulate finalize_phase2
        task_data = {
            'cut_videos': [
                {'path': clip_paths[0]},
                {'path': clip_paths[1]}
            ],
            'moments': [
                {'moment_id': moment_ids[0], 'moment_index': 0},
                {'moment_id': moment_ids[1], 'moment_index': 1}
            ]
        }

        result = finalize_phase2(task_data, job_id)

        # Verify clips are linked
        with get_db_session() as session:
            clips = session.query(Clip).filter(Clip.job_id == job_id).all()

            assert len(clips) == 2
            assert all(c.moment_id is not None for c in clips)

            # Verify each clip links to correct moment
            for clip in clips:
                moment = session.query(Moment).filter(Moment.id == clip.moment_id).first()
                assert moment is not None
                assert moment.job_id == job_id

        print("✅ Clip-moment linking test PASSED")


if __name__ == "__main__":
    """Run tests directly"""
    test = TestPhaseSeparation()
    test.setup_and_teardown().__next__()

    try:
        print("\n🧪 Running Workflow Separation Tests\n")
        print("=" * 60)

        test.test_phase1_independence()
        test.test_phase2_independence()
        test.test_phase_separation_no_leakage()
        test.test_clip_moment_linking()

        print("\n" + "=" * 60)
        print("🎉 ALL WORKFLOW TESTS PASSED!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        list(test.setup_and_teardown())[-1]
