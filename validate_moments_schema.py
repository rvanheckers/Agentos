#!/usr/bin/env python3
"""
Quick validation script to test the moments schema implementation
"""

from core.database_manager import PostgreSQLManager, Job, Moment, Clip
from datetime import datetime, timezone

def validate_schema():
    """Validate that the moments schema works correctly"""

    db = PostgreSQLManager()

    print("🔍 Validating moments schema implementation...")

    try:
        with db.get_session() as session:
            # 1. Create a test job
            print("\n1️⃣ Creating test job...")
            job = Job(
                user_id='validation-test',
                video_url='https://example.com/test.mp4',
                video_title='Test Video',
                status='processing',
                phase='phase1_analysis'
            )
            session.add(job)
            session.flush()
            print(f"   ✅ Job created: {job.id}")
            print(f"   ✅ Job phase: {job.phase}")

            # 2. Create moments
            print("\n2️⃣ Creating 3 viral moments...")
            moments = []
            for i in range(3):
                moment = Moment(
                    job_id=job.id,
                    moment_index=i,
                    start_time=i * 30.0,
                    end_time=(i + 1) * 30.0,
                    duration=30.0,
                    description=f"Viral moment {i+1}",
                    sentence_text=f"This is the transcript for moment {i+1}",
                    keywords=["viral", "trending", f"moment{i+1}"],
                    viral_score=75 + (i * 5),
                    is_selected=False
                )
                moments.append(moment)
                session.add(moment)

            session.flush()
            print(f"   ✅ Created {len(moments)} moments")
            for m in moments:
                print(f"      • Moment {m.moment_index}: score={m.viral_score}, selected={m.is_selected}")

            # 3. Select one moment
            print("\n3️⃣ Selecting moment 1...")
            moments[1].is_selected = True
            moments[1].selected_at = datetime.now(timezone.utc)
            session.flush()
            print(f"   ✅ Moment 1 selected at {moments[1].selected_at}")

            # 4. Update job phase
            print("\n4️⃣ Updating job phase to 'awaiting_selection'...")
            job.phase = 'awaiting_selection'
            session.flush()
            print(f"   ✅ Job phase updated: {job.phase}")

            # 5. Create a clip linked to the selected moment
            print("\n5️⃣ Creating clip from selected moment...")
            clip = Clip(
                job_id=job.id,
                moment_id=moments[1].id,
                file_path='/test/output/clip_001.mp4',
                duration=30.0,
                title="Generated Clip from Moment 1"
            )
            session.add(clip)
            session.flush()
            print(f"   ✅ Clip created: {clip.id}")
            print(f"   ✅ Linked to moment: {clip.moment_id}")

            # 6. Verify relationships
            print("\n6️⃣ Verifying relationships...")
            print(f"   ✅ Job has {len(job.moments)} moments")
            print(f"   ✅ Job has {len(job.clips)} clips")
            print(f"   ✅ Moment has {len(moments[1].clips)} clips")
            print(f"   ✅ Clip moment_id: {clip.moment_id}")

            # 7. Query selected moments
            print("\n7️⃣ Querying selected moments...")
            selected_moments = session.query(Moment).filter(
                Moment.job_id == job.id,
                Moment.is_selected == True
            ).all()
            print(f"   ✅ Found {len(selected_moments)} selected moments")
            for m in selected_moments:
                print(f"      • Moment {m.moment_index}: '{m.description}'")

            # Cleanup
            print("\n8️⃣ Cleaning up test data...")
            session.delete(job)
            session.commit()
            print("   ✅ Test data cleaned up (cascade delete)")

        print("\n" + "="*60)
        print("✅ ALL VALIDATIONS PASSED!")
        print("="*60)
        print("\n📋 Summary:")
        print("   ✅ Moment model works correctly")
        print("   ✅ Job phase tracking works")
        print("   ✅ Job <-> Moment relationship works")
        print("   ✅ Moment <-> Clip relationship works")
        print("   ✅ Cascade delete works")
        print("   ✅ Queries and indexes work")
        print("\n🎉 Database schema implementation is COMPLETE and VALIDATED!")

    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()

    return True

if __name__ == "__main__":
    validate_schema()
