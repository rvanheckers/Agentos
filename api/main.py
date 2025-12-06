"""
Main FastAPI application
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables FIRST (before any other imports)
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import signal
import sys
import os

# Add current directory to path (for relative imports to work)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

from config.settings import settings
from core.logging_config import get_logger
from api.routes import websocket  # Keep WebSocket + system (for Quick Actions)

logger = get_logger("api_server")

# Import refactored routes with service layer
try:
    from api.routes import admin_ssot
    ADMIN_SSOT_AVAILABLE = True
    logger.info("Admin SSOT route loaded successfully")
except ImportError as e:
    logger.warning(f"Admin SSOT route not available: {e}")
    ADMIN_SSOT_AVAILABLE = False

try:
    from api.routes import job_refactored, queue_refactored, upload_refactored, agents_refactored, clips_refactored, admin_actions, moments, debug, files, pipeline_control
    REFACTORED_ROUTES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Refactored routes not available yet: {e}")
    REFACTORED_ROUTES_AVAILABLE = False

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="AgentOS API",
        description="AgentOS Video Processing API",
        version="1.0.0",
        debug=settings.debug
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files (only if directory exists)
    import os
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")

    # Mount io directory for video/audio files
    if os.path.exists("io"):
        app.mount("/io", StaticFiles(directory="io"), name="io")

    # Mount ui-v2 directory for frontend (including job-debug.html)
    if os.path.exists("ui-v2"):
        app.mount("/ui-v2", StaticFiles(directory="ui-v2", html=True), name="ui-v2")

    # Legacy routes DISABLED - using refactored service layer only
    # LEGACY DISABLED: app.include_router(job.router, prefix="/api/admin", tags=["admin-jobs"])
    # LEGACY DISABLED: app.include_router(user.router, prefix="/api/admin", tags=["admin-users"])
    # MOVED: system.router registration moved AFTER celery_workers to prevent conflicts
    # LEGACY DISABLED: app.include_router(files.router, prefix="/api/admin", tags=["admin-files"])
    # LEGACY DISABLED: app.include_router(upload.router, prefix="/api/admin/upload", tags=["admin-upload"])
    # LEGACY DISABLED: app.include_router(agents.router, prefix="/api/admin/agents", tags=["admin-agents"])
    # LEGACY DISABLED: app.include_router(download.router, prefix="/api/admin/download", tags=["admin-download"])
    # LEGACY DISABLED: app.include_router(workflow.router, prefix="/api/admin/workflows", tags=["admin-workflows"])

    # Keep WebSocket (not refactored yet)
    app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

    # Privacy and metadata endpoints
    try:
        from api.endpoints import metadata, privacy
        app.include_router(metadata.router, tags=['metadata'])
        app.include_router(privacy.router, tags=['privacy'])
        logger.info("Privacy and metadata endpoints registered successfully")
    except ImportError as e:
        logger.warning(f"Privacy/metadata endpoints not available: {e}")

    # UI-v2 compatibility - DISABLED to prevent duplicate routes
    # The refactored routes below already handle both /api/admin/* and /api/* patterns
    # LEGACY DISABLED: UI-v2 router removed to prevent /api/api/* duplicate prefix bug

    # ===== ADMIN SSOT ENDPOINT (ENABLED - Service Layer SSOT) =====
    # Admin SSOT route (ENABLED - CentralDataService needs this for real data)
    if ADMIN_SSOT_AVAILABLE:
        app.include_router(admin_ssot.router)
        logger.info("Admin SSOT router registered successfully")
        logger.info("STREAMLINED: Only /api/admin/ssot endpoint active - sub-endpoints disabled")
    else:
        logger.warning("Admin SSOT router not available - skipping registration")

    # Include refactored routes with service layer (parallel deployment)
    # These will gradually replace the old routes
    if REFACTORED_ROUTES_AVAILABLE:
        logger.info("Including refactored routes with service layer...")

        # ===== USER API ENDPOINTS (ENABLED - UI-v2 frontend needs these) =====

        # Jobs refactored routes (ENABLED - user workflow needs /api/jobs/create)
        app.include_router(job_refactored.router)

        # Queue refactored routes (ENABLED - user workflow needs /api/queue/stats)
        app.include_router(queue_refactored.user_router)

        # Upload refactored routes (ENABLED - needed for user video uploads)
        app.include_router(upload_refactored.user_router)

        # Job routes (ENABLED - needed for video processing workflow)
        app.include_router(job_refactored.router)
        
        # Agents routes (ENABLED - needed for agent discovery /api/agents)
        app.include_router(agents_refactored.user_router)
        
        # Clips routes (ENABLED - needed for user workflow /api/clips/recent)
        app.include_router(clips_refactored.user_router)

        # Moments routes (ENABLED - needed for user selection workflow)
        app.include_router(moments.router)

        # Pipeline Control routes (ENABLED - needed for proactive pipeline architecture)
        app.include_router(pipeline_control.router)
        logger.info("✅ Pipeline Control API registered (proactive architecture)")

        # Debug routes (ENABLED - needed for job debug viewer)
        app.include_router(debug.router)

        # Files routes (ENABLED - needed for serving debug images/videos)
        app.include_router(files.router)

        logger.info("Refactored routes registered successfully")
    else:
        logger.warning("Refactored routes not available - skipping registration")

    # ===== ADMIN API ENDPOINTS (V5 ENTERPRISE SELECTIVE ENABLE) =====
    # SSOT CLEANUP: Most admin endpoints replaced by Service Layer SSOT
    # V5 ENTERPRISE EXCEPTION: admin_actions.router ENABLED for unified action endpoint

    # app.include_router(celery_workers.admin_router)     # DISABLED: Admin UI → AdminDataManager.get_workers_data()
    # app.include_router(clips_refactored.admin_router)   # DISABLED: Admin UI → AdminDataManager.get_clips_data()
    # app.include_router(admin_dashboard.router)          # DISABLED: Admin UI → AdminDataManager.get_dashboard_data()

    # ===== V5 ENTERPRISE ACTION ENDPOINT (ENABLED) =====
    if REFACTORED_ROUTES_AVAILABLE:
        app.include_router(admin_actions.router)              # ENABLED: Admin actions endpoint

    # app.include_router(resources.router)                # DISABLED: Admin UI → AdminDataManager.get_resource_data()
    # app.include_router(system.router)                   # DISABLED: Admin UI → AdminDataManager.get_system_data()

    # ===== USER API ENDPOINTS (DISABLED - replaced by enabled endpoints above) =====
    # app.include_router(queue_refactored.admin_router)  # DISABLED: Admin uses Service Layer SSOT
    # app.include_router(agents_refactored.user_router)  # DISABLED: Service missing
    # app.include_router(analytics_refactored.user_router) # DISABLED: replaced by /api/resources/analytics
    # app.include_router(download_refactored.user_router)  # DISABLED: replaced by /api/resources/downloads
    # app.include_router(workflow_refactored.user_router)  # DISABLED: replaced by /api/resources/workflows
    # app.include_router(managers_refactored.admin_router) # DISABLED: replaced by /api/resources/managers

    logger.info("🎉 API Server configured - SSOT endpoint available")

    @app.get("/")
    async def root():
        return {"message": "AgentOS API is running"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    logger.info("FastAPI application created successfully")
    return app

app = create_app()

if __name__ == "__main__":
    # Configure server with SO_REUSEADDR to prevent port locks
    config = uvicorn.Config(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
    server = uvicorn.Server(config)

    # Proper shutdown handling
    def shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        server.should_exit = True

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Run with socket reuse
    import asyncio
    asyncio.run(server.serve())
