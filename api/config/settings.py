"""
Application settings and configuration
"""
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://agentos_user:secure_agentos_2024@localhost:5432/agentos_production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/api.log"

    # Queue
    queue_max_size: int = 1000
    worker_timeout: int = 300

    # AI Services (from .env)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Video Processing
    max_video_length: int = 3600
    max_clip_length: int = 60
    video_quality: int = 720

    # Feature Flags
    enable_real_ai: bool = False
    enable_mock_mode: bool = True
    use_mock_ai: bool = True  # New: Use mock AI responses to avoid API costs

    # 🗑️ CLEANUP CONFIGURATION - Industry Standard Retention Policies
    cleanup_enabled: bool = True
    clip_retention_days: int = 30      # Keep clips for 30 days
    job_retention_days: int = 90       # Keep job records for 90 days
    temp_retention_hours: int = 24     # Clean temp files after 24 hours
    emergency_cleanup_threshold_mb: int = 5000  # 5GB emergency threshold
    cleanup_schedule_hour: int = 2     # 2 AM daily cleanup
    disk_monitor_enabled: bool = True  # Enable hourly disk monitoring

    # Additional ports
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    websocket_port: int = 8765

    # Environment
    env: str = "development"

    # 📁 FILE MANAGEMENT - Cleanup directories
    output_dir: str = "./io/output"
    input_dir: str = "./io/input"
    temp_dir: str = "./io/temp"
    downloads_dir: str = "./io/downloads"

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env

# Global settings instance
settings = Settings()
