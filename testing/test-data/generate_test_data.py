#!/usr/bin/env python3
"""
Test Data Generator voor AgentOS
===============================

Dit script genereert realistische test data voor alle database tabellen:
- Jobs met verschillende statussen
- Clips met bijbehorende metadata
- Processing steps voor elke job
- System events
- System config items

Usage:
    python generate_test_data.py [--jobs N] [--events N] [--clean]
    
Arguments:
    --jobs N    : Aantal jobs om te genereren (default: 50)
    --events N  : Aantal system events om te genereren (default: 200)
    --clean     : Verwijder eerst alle bestaande data
"""

import sys
import os
import argparse
import logging
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import json

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from core.database_manager import PostgreSQLManager, Job, Clip, ProcessingStep, SystemEvent, SystemConfig

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestDataGenerator:
    """Generator voor realistische test data"""
    
    def __init__(self, db_manager: PostgreSQLManager):
        self.db = db_manager
        self.video_titles = [
            "TikTok Dance Challenge Compilation",
            "Epic Gaming Moments Montage", 
            "Street Food Tour Bangkok",
            "Unboxing Latest iPhone",
            "Morning Workout Routine",
            "Cooking Pasta from Scratch",
            "City Skyline Timelapse",
            "Pet Tricks and Funny Moments",
            "DIY Home Renovation",
            "Music Festival Highlights",
            "Beach Sunset Photography",
            "Tech Review: New Laptop",
            "Travel Vlog: Paris Adventure",
            "Recipe: Homemade Pizza",
            "Fitness Transformation",
            "Art Tutorial: Watercolor",
            "Comedy Sketch Performance",
            "Nature Documentary Clips",
            "Fashion Haul Spring 2024",
            "Car Review: Electric Vehicle"
        ]
        
        self.processing_steps = [
            "video_download",
            "video_analysis", 
            "moment_detection",
            "face_detection",
            "intelligent_cropping",
            "video_cutting",
            "thumbnail_generation",
            "audio_transcription",
            "social_post_generation",
            "visual_effects",
            "voiceover_creation",
            "final_rendering"
        ]
        
        self.user_ids = [
            "user_001_demo",
            "user_002_beta",
            "user_003_premium", 
            "user_004_basic",
            "user_005_trial",
            "user_006_enterprise",
            "user_007_creator",
            "user_008_business",
            "user_009_student",
            "user_010_admin"
        ]
        
        self.video_urls = [
            "https://example.com/videos/tiktok_dance_001.mp4",
            "https://example.com/videos/gaming_montage_002.mp4",
            "https://example.com/videos/food_tour_003.mp4",
            "https://example.com/videos/unboxing_004.mp4",
            "https://example.com/videos/workout_005.mp4",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://vimeo.com/123456789",
            "https://example.com/videos/cooking_pasta.mp4",
            "https://example.com/videos/timelapse_city.mp4",
            "https://example.com/videos/pet_tricks.mp4"
        ]
        
        self.event_types = [
            "job_created", "job_started", "job_completed", "job_failed",
            "agent_started", "agent_stopped", "agent_error",
            "system_startup", "system_shutdown", "system_error",
            "database_connection", "database_error", "database_backup",
            "api_request", "api_error", "websocket_connection",
            "file_upload", "file_download", "file_error",
            "cleanup_started", "cleanup_completed", "disk_space_warning"
        ]
        
        self.components = [
            "job_processor", "video_downloader", "moment_detector",
            "face_detector", "intelligent_cropper", "video_cutter",
            "thumbnail_generator", "audio_transcriber", "social_post_generator",
            "visual_effects", "voiceover_creator", "database_manager",
            "api_server", "websocket_server", "cleanup_service",
            "file_manager", "queue_manager", "admin_ui"
        ]

    def clean_database(self):
        """Verwijder alle bestaande test data"""
        logger.info("🧹 Cleaning existing data...")
        try:
            with self.db.get_session() as session:
                # Delete in correct order (foreign key constraints)
                session.query(ProcessingStep).delete()
                session.query(Clip).delete() 
                session.query(Job).delete()
                session.query(SystemEvent).delete()
                # Keep SystemConfig as it contains important settings
                session.commit()
                logger.info("✅ Database cleaned successfully")
        except Exception as e:
            logger.error(f"❌ Failed to clean database: {e}")
            raise

    def generate_jobs(self, count: int = 50) -> List[str]:
        """Genereer test jobs met realistische data"""
        logger.info(f"📋 Generating {count} test jobs...")
        job_ids = []
        
        try:
            with self.db.get_session() as session:
                for i in range(count):
                    # Create realistic timestamps
                    created_at = datetime.now(timezone.utc) - timedelta(
                        days=random.randint(0, 30),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                    
                    # Determine job status with realistic distribution
                    status_weights = {
                        'completed': 60,  # 60% completed
                        'failed': 15,     # 15% failed  
                        'processing': 10, # 10% processing
                        'pending': 15     # 15% pending
                    }
                    status = random.choices(
                        list(status_weights.keys()),
                        weights=list(status_weights.values())
                    )[0]
                    
                    # Set timestamps based on status
                    started_at = None
                    completed_at = None
                    progress = 0
                    error_message = None
                    
                    if status in ['processing', 'completed', 'failed']:
                        started_at = created_at + timedelta(minutes=random.randint(1, 30))
                        progress = random.randint(10, 100)
                        
                    if status in ['completed', 'failed']:
                        completed_at = started_at + timedelta(minutes=random.randint(5, 120))
                        progress = 100 if status == 'completed' else random.randint(30, 80)
                        
                    if status == 'failed':
                        error_messages = [
                            "Video download failed: Connection timeout",
                            "Face detection error: No faces found in video",
                            "Video format not supported: codec not available",
                            "Insufficient disk space for processing",
                            "AI service temporarily unavailable",
                            "Video duration exceeds maximum limit",
                            "Audio extraction failed: corrupted file",
                            "Thumbnail generation timeout"
                        ]
                        error_message = random.choice(error_messages)
                    
                    job = Job(
                        id=uuid.uuid4(),
                        user_id=random.choice(self.user_ids),
                        video_url=random.choice(self.video_urls),
                        video_title=random.choice(self.video_titles),
                        status=status,
                        progress=progress,
                        current_step=random.choice(self.processing_steps) if status == 'processing' else None,
                        error_message=error_message,
                        created_at=created_at,
                        started_at=started_at, 
                        completed_at=completed_at,
                        priority=random.randint(1, 10),
                        retry_count=random.randint(0, 3) if status == 'failed' else 0,
                        worker_id=f"worker-{random.randint(1, 5)}" if started_at else None
                    )
                    
                    session.add(job)
                    job_ids.append(str(job.id))
                    
                session.commit()
                logger.info(f"✅ Generated {count} jobs successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to generate jobs: {e}")
            raise
            
        return job_ids

    def generate_clips(self, job_ids: List[str]):
        """Genereer clips voor completed jobs"""
        logger.info("🎬 Generating clips for completed jobs...")
        
        try:
            with self.db.get_session() as session:
                completed_jobs = session.query(Job).filter(Job.status == 'completed').all()
                clip_count = 0
                
                for job in completed_jobs:
                    # Generate 1-5 clips per completed job
                    num_clips = random.randint(1, 5)
                    
                    for clip_num in range(1, num_clips + 1):
                        clip = Clip(
                            id=uuid.uuid4(),
                            job_id=job.id,
                            clip_number=clip_num,
                            file_path=f"./io/output/{job.id}/clip_{clip_num}.mp4",
                            duration=round(random.uniform(10.0, 60.0), 2),
                            title=f"{job.video_title} - Clip {clip_num}",
                            description=f"Auto-generated clip {clip_num} from {job.video_title}",
                            tags="auto-generated,viral,trending,short-form",
                            created_at=job.completed_at or job.created_at,
                            file_size=random.randint(1024*1024, 50*1024*1024),  # 1MB - 50MB
                            thumbnail_path=f"./io/output/{job.id}/clip_{clip_num}_thumb.jpg"
                        )
                        
                        session.add(clip)
                        clip_count += 1
                
                session.commit()
                logger.info(f"✅ Generated {clip_count} clips successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to generate clips: {e}")
            raise

    def generate_processing_steps(self, job_ids: List[str]):
        """Genereer processing steps voor alle jobs"""
        logger.info("⚙️ Generating processing steps...")
        
        try:
            with self.db.get_session() as session:
                all_jobs = session.query(Job).all()
                step_count = 0
                
                for job in all_jobs:
                    # Skip pending jobs (no steps started yet)
                    if job.status == 'pending':
                        continue
                        
                    # Determine how many steps to generate based on job status
                    if job.status == 'processing':
                        # Partial completion
                        num_steps = random.randint(3, 8)
                    elif job.status == 'completed':
                        # All steps completed
                        num_steps = len(self.processing_steps)
                    else:  # failed
                        # Failed partway through
                        num_steps = random.randint(1, 6)
                    
                    step_start_time = job.started_at or job.created_at
                    
                    for i, step_name in enumerate(self.processing_steps[:num_steps]):
                        # Calculate step timing
                        step_started = step_start_time + timedelta(
                            minutes=i * random.randint(2, 10)
                        )
                        
                        # Determine step status
                        if job.status == 'completed':
                            step_status = 'completed'
                            step_completed = step_started + timedelta(
                                minutes=random.randint(1, 15)
                            )
                            duration = (step_completed - step_started).total_seconds()
                        elif job.status == 'processing' and i < num_steps - 1:
                            step_status = 'completed'
                            step_completed = step_started + timedelta(
                                minutes=random.randint(1, 15)
                            )
                            duration = (step_completed - step_started).total_seconds()
                        elif job.status == 'processing' and i == num_steps - 1:
                            step_status = 'processing'
                            step_completed = None
                            duration = None
                        else:  # failed job
                            if i < num_steps - 1:
                                step_status = 'completed'
                                step_completed = step_started + timedelta(
                                    minutes=random.randint(1, 15)
                                )
                                duration = (step_completed - step_started).total_seconds()
                            else:  # last step failed
                                step_status = 'failed'
                                step_completed = step_started + timedelta(
                                    minutes=random.randint(1, 10)
                                )
                                duration = (step_completed - step_started).total_seconds()
                        
                        # Generate realistic agent output
                        agent_outputs = {
                            'video_download': f"Downloaded video: {random.randint(10, 100)}MB, Duration: {random.randint(30, 300)}s",
                            'video_analysis': f"Detected {random.randint(5, 20)} scenes, {random.randint(50, 200)} frames analyzed",
                            'moment_detection': f"Found {random.randint(3, 12)} key moments with confidence > 0.8",
                            'face_detection': f"Detected {random.randint(0, 5)} faces in {random.randint(10, 80)}% of frames",
                            'intelligent_cropping': f"Applied smart crop to {random.randint(60, 100)}% of content",
                            'video_cutting': f"Generated {random.randint(2, 6)} clips with total duration {random.randint(60, 300)}s",
                            'thumbnail_generation': f"Created {random.randint(3, 10)} thumbnails at various timestamps",
                            'audio_transcription': f"Transcribed {random.randint(50, 500)} words with {random.randint(85, 98)}% accuracy",
                            'social_post_generation': f"Generated {random.randint(3, 8)} social media captions",
                            'visual_effects': f"Applied {random.randint(2, 6)} visual filters and transitions",
                            'voiceover_creation': f"Generated {random.randint(30, 120)}s of AI voiceover",
                            'final_rendering': f"Rendered {random.randint(2, 5)} final videos in {random.randint(720, 1080)}p"
                        }
                        
                        processing_step = ProcessingStep(
                            id=uuid.uuid4(),
                            job_id=job.id,
                            step_name=step_name,
                            status=step_status,
                            started_at=step_started,
                            completed_at=step_completed,
                            duration_seconds=duration,
                            agent_output=agent_outputs.get(step_name, f"{step_name} completed successfully"),
                            error_message=job.error_message if step_status == 'failed' else None,
                            metadata_json=json.dumps({
                                "step_index": i,
                                "total_steps": num_steps,
                                "worker_id": job.worker_id,
                                "processing_time": duration
                            })
                        )
                        
                        session.add(processing_step)
                        step_count += 1
                        
                        # Update step_start_time for next step
                        if step_completed:
                            step_start_time = step_completed
                
                session.commit()
                logger.info(f"✅ Generated {step_count} processing steps successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to generate processing steps: {e}")
            raise

    def generate_system_events(self, count: int = 200):
        """Genereer system events"""
        logger.info(f"📝 Generating {count} system events...")
        
        try:
            with self.db.get_session() as session:
                for i in range(count):
                    # Create realistic timestamps (last 30 days)
                    created_at = datetime.now(timezone.utc) - timedelta(
                        days=random.randint(0, 30),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )
                    
                    event_type = random.choice(self.event_types)
                    component = random.choice(self.components)
                    
                    # Generate realistic messages based on event type
                    messages = {
                        'job_created': f"New job created by {random.choice(self.user_ids)}",
                        'job_started': f"Job processing started on worker-{random.randint(1, 5)}",
                        'job_completed': f"Job completed successfully in {random.randint(60, 1800)}s",
                        'job_failed': f"Job failed: {random.choice(['timeout', 'invalid_format', 'api_error', 'disk_full'])}",
                        'agent_started': f"Agent {component} started successfully",
                        'agent_stopped': f"Agent {component} stopped gracefully",
                        'agent_error': f"Agent {component} encountered error and restarted",
                        'system_startup': "AgentOS system started successfully",
                        'system_shutdown': "AgentOS system shutdown initiated",
                        'system_error': f"System error in {component}: memory usage high",
                        'database_connection': "Database connection established",
                        'database_error': "Database connection timeout, retrying...",
                        'database_backup': f"Database backup completed: {random.randint(100, 500)}MB",
                        'api_request': f"API request processed: {random.choice(['GET', 'POST', 'PUT', 'DELETE'])} /api/v1/{random.choice(['jobs', 'clips', 'users', 'analytics'])}",
                        'api_error': f"API error: {random.choice(['400 Bad Request', '401 Unauthorized', '500 Internal Error', '503 Service Unavailable'])}",
                        'websocket_connection': f"WebSocket client connected from {random.choice(['192.168.1.', '10.0.0.', '172.16.0.'])}{random.randint(1, 255)}",
                        'file_upload': f"File uploaded: {random.randint(5, 500)}MB video file",
                        'file_download': f"File downloaded: clip_{random.randint(1, 1000)}.mp4",
                        'file_error': "File operation failed: insufficient disk space",
                        'cleanup_started': "Automated cleanup process started",
                        'cleanup_completed': f"Cleanup completed: removed {random.randint(5, 50)} old files ({random.randint(100, 2000)}MB freed)",
                        'disk_space_warning': f"Disk space warning: {random.randint(80, 95)}% full"
                    }
                    
                    # Determine severity based on event type
                    severities = {
                        'error': ['job_failed', 'agent_error', 'system_error', 'database_error', 'api_error', 'file_error'],
                        'warning': ['disk_space_warning', 'database_connection'],
                        'info': ['job_created', 'job_started', 'job_completed', 'agent_started', 'agent_stopped', 
                                'system_startup', 'database_backup', 'api_request', 'websocket_connection',
                                'file_upload', 'file_download', 'cleanup_started', 'cleanup_completed'],
                        'critical': ['system_shutdown']
                    }
                    
                    severity = 'info'  # default
                    for sev, event_types in severities.items():
                        if event_type in event_types:
                            severity = sev
                            break
                    
                    # Generate metadata
                    metadata = {
                        "event_id": f"evt_{i+1:06d}",
                        "source_component": component,
                        "timestamp_ms": int(created_at.timestamp() * 1000),
                        "session_id": str(uuid.uuid4())[:8]
                    }
                    
                    # Add specific metadata based on event type
                    if 'job_' in event_type:
                        metadata["job_id"] = str(uuid.uuid4())
                        metadata["user_id"] = random.choice(self.user_ids)
                    elif 'api_' in event_type:
                        metadata["response_time_ms"] = random.randint(50, 2000)
                        metadata["user_agent"] = random.choice(["AgentOS-UI/1.0", "Chrome/91.0", "Firefox/89.0"])
                    elif 'database_' in event_type:
                        metadata["connection_pool_size"] = random.randint(10, 50)
                        metadata["active_connections"] = random.randint(5, 25)
                    
                    system_event = SystemEvent(
                        id=uuid.uuid4(),
                        event_type=event_type,
                        message=messages.get(event_type, f"System event: {event_type}"),
                        severity=severity,
                        component=component,
                        metadata_json=json.dumps(metadata),
                        created_at=created_at
                    )
                    
                    session.add(system_event)
                
                session.commit()
                logger.info(f"✅ Generated {count} system events successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to generate system events: {e}")
            raise

    def generate_system_config(self):
        """Genereer system configuration entries"""
        logger.info("⚙️ Generating system configuration...")
        
        config_items = [
            {
                "key": "max_concurrent_jobs",
                "value": "10",
                "description": "Maximum number of jobs that can be processed simultaneously",
                "is_editable": True
            },
            {
                "key": "default_video_quality", 
                "value": "720",
                "description": "Default video quality for processing (480, 720, 1080)",
                "is_editable": True
            },
            {
                "key": "ai_service_timeout",
                "value": "300",
                "description": "Timeout for AI service requests in seconds",
                "is_editable": True
            },
            {
                "key": "cleanup_retention_days",
                "value": "30", 
                "description": "Number of days to retain completed job files",
                "is_editable": True
            },
            {
                "key": "enable_notifications",
                "value": "true",
                "description": "Enable system notifications for job completion",
                "is_editable": True
            },
            {
                "key": "max_upload_size_mb",
                "value": "500",
                "description": "Maximum file size for video uploads in MB",
                "is_editable": True
            },
            {
                "key": "system_version",
                "value": "1.2.3",
                "description": "Current AgentOS version",
                "is_editable": False
            },
            {
                "key": "database_version",
                "value": "2.1.0",
                "description": "Database schema version",
                "is_editable": False
            },
            {
                "key": "api_rate_limit",
                "value": "100",
                "description": "API requests per minute per user",
                "is_editable": True
            },
            {
                "key": "worker_health_check_interval",
                "value": "60",
                "description": "Worker health check interval in seconds",
                "is_editable": True
            }
        ]
        
        try:
            with self.db.get_session() as session:
                # Clear existing config
                session.query(SystemConfig).delete()
                
                for item in config_items:
                    config = SystemConfig(
                        id=uuid.uuid4(),
                        key=item["key"],
                        value=item["value"],
                        description=item["description"],
                        is_editable=item["is_editable"],
                        updated_at=datetime.now(timezone.utc),
                        updated_by="system_init"
                    )
                    session.add(config)
                
                session.commit()
                logger.info(f"✅ Generated {len(config_items)} system config items successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to generate system config: {e}")
            raise

    def print_summary(self):
        """Print summary of generated data"""
        logger.info("📊 Data Generation Summary:")
        try:
            stats = self.db.get_stats()
            
            print(f"""
            ┌─────────────────────────────────────┐
            │           Test Data Summary         │
            ├─────────────────────────────────────┤
            │ Jobs:              {stats['total_jobs']:>10} │
            │ - Pending:         {stats['pending_jobs']:>10} │
            │ - Processing:      {stats['processing_jobs']:>10} │
            │ - Completed:       {stats['completed_jobs']:>10} │
            │ - Failed:          {stats['failed_jobs']:>10} │
            │                                     │
            │ Clips:             {stats['total_clips']:>10} │
            │ Processing Steps:  {stats['total_processing_steps']:>10} │
            │ System Events:     {stats['total_system_events']:>10} │
            │                                     │
            │ Success Rate:      {stats['success_rate']:>9.1f}% │
            │ Recent Activity:   {stats['recent_jobs_24h']:>10} │
            └─────────────────────────────────────┘
            """)
            
        except Exception as e:
            logger.error(f"❌ Failed to get summary: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate test data for AgentOS')
    parser.add_argument('--jobs', type=int, default=50, help='Number of jobs to generate')
    parser.add_argument('--events', type=int, default=200, help='Number of system events to generate')
    parser.add_argument('--clean', action='store_true', help='Clean existing data first')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting AgentOS Test Data Generation")
    logger.info(f"Configuration: {args.jobs} jobs, {args.events} events, clean={args.clean}")
    
    try:
        # Initialize database manager
        db_manager = PostgreSQLManager()
        
        # Create tables if they don't exist
        db_manager.create_tables()
        
        # Initialize generator
        generator = TestDataGenerator(db_manager)
        
        # Clean database if requested
        if args.clean:
            generator.clean_database()
        
        # Generate test data
        logger.info("📦 Generating test data...")
        
        # 1. Generate jobs
        job_ids = generator.generate_jobs(args.jobs)
        
        # 2. Generate clips for completed jobs
        generator.generate_clips(job_ids)
        
        # 3. Generate processing steps
        generator.generate_processing_steps(job_ids)
        
        # 4. Generate system events
        generator.generate_system_events(args.events)
        
        # 5. Generate system config
        generator.generate_system_config()
        
        # Print summary
        generator.print_summary()
        
        logger.info("✅ Test data generation completed successfully!")
        logger.info("🎯 You can now test the admin UI with realistic data")
        
    except KeyboardInterrupt:
        logger.warning("⚠️ Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Close database connections
        try:
            db_manager.close()
        except:
            pass

if __name__ == "__main__":
    main()