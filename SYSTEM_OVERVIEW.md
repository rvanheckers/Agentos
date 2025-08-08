# 🚀 AgentOS System Overview & Access Points

**Last Updated:** 30 Juli 2025  
**Project Version:** v2.7.0 (Enhanced Admin Interface + Working Video Generation)  
**WSL IP Address:** 172.30.108.252

---

## 🌐 **Service Access Points**

### **Main Application Services**
- **Frontend UI**: http://localhost:8000/ui-v2/
- **Enhanced Admin Dashboard**: http://localhost:8004/ (v2.7.0 - Activity Monitoring + Framework Management)
- **API Server**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **WebSocket**: ws://localhost:8765

### **Celery & Task Management**
- **Celery Flower Dashboard**: http://localhost:5555 (Real-time worker monitoring)
- **Admin UI Celery Tab**: http://localhost:8004 → Celery Flower (integrated)
- **Redis Commander**: http://localhost:8081 (if enabled)

### **Database & Monitoring**
- **PgAdmin (PostgreSQL Management)**: http://172.30.108.252:5050
  - Login: `admin@example.com` / `admin123`
- **Grafana (Performance Monitoring)**: http://172.30.108.252:3000
  - Login: `admin` / `admin123`
- **Prometheus (Metrics)**: http://172.30.108.252:9090

---

## 📁 **Directory Structure**

### **Root Level**
```
AgentOS/
├── 📄 README.md                    # Framework documentation
├── 📄 CLAUDE.md                    # Development notes
├── 📄 SYSTEM_OVERVIEW.md           # This file
├── 🔧 Makefile                     # Build commands
├── 📦 requirements.txt             # Python dependencies
├── 🛠️ backup.sh                   # Backup utility
└── ⚙️ logging_config.json         # Logging configuration
```

### **Core Framework**
```
core/
├── database_manager.py             # PostgreSQL ORM & connection pooling
├── logging_config.py               # Centralized logging system
└── celery_app.py                   # Celery task queue configuration
```

### **Development Tools**
```
tools/
└── postgresql_inspector.py         # Database inspection tool
```

### **Configuration**
```
config/
└── docker-compose.postgresql.yml   # PostgreSQL monitoring stack
```

### **Application Modules**
```
api/                                # FastAPI backend (31 endpoints - 61% REDUCED!)
├── config/settings.py              # Application settings
├── routes/                         # Enterprise API routes (cleaned up)
├── services/                       # Business logic services
└── main.py                         # FastAPI application

services/                           # Service layer managers
├── jobs_service.py                 # Job management
├── agents_service.py               # Agent orchestration
├── queue_service.py                # Queue management
├── upload_service.py               # File handling
└── analytics_service.py            # Analytics & reporting

tasks/                              # Celery tasks
├── video_processing.py             # Video pipeline tasks
└── maintenance.py                  # System maintenance tasks

agents2/                            # AI Agent implementations
├── video_downloader.py             # Multi-platform download
├── audio_transcriber.py            # Speech-to-text
├── moment_detector.py              # Viral moment detection
├── face_detector.py                # Face tracking
├── intelligent_cropper.py          # Smart cropping
├── video_cutter.py                 # Video cutting
└── (7 more agents...)              # Content generation agents
```

### **User Interfaces**
```
ui-v2/                              # Main user interface (Vite)
├── src/features/                   # Feature modules
├── src/shared/                     # Shared components
└── index.html                      # Entry point

ui-admin-clean/                     # Enhanced admin interface (v2.7.0)
├── assets/js/views/                # Activity Monitoring + Framework Management views
│   ├── Dashboard.js                # Real-time dashboard with 6 integrated endpoints
│   ├── AgentsWorkers.js            # Combined agents/workers management
│   ├── Jobs.js                     # Job monitoring
│   └── Analytics.js                # Performance analytics
├── assets/js/modules/              # Reusable modules
│   ├── ActivityFeed.js             # Real-time activity tracking
│   └── QuickActions.js             # Navigation quick actions
├── assets/css/                     # Styling system
└── index.html                      # Admin entry point
```

### **Data & Storage**
```
io/                                 # File system storage
├── input/                          # Upload staging
├── output/                         # Generated content
├── temp/                           # Temporary files
└── downloads/                      # Download cache

logs/                               # Application logs
├── agentos.log                     # Main application log
├── celery.log                      # Celery worker logs
├── api.log                         # API server logs
├── websocket.log                   # WebSocket logs
└── errors.log                      # Error logs only

monitoring/                         # Monitoring configuration
├── grafana/dashboards/             # Grafana dashboard configs
├── prometheus.yml                  # Prometheus configuration
└── postgres_queries.yaml          # PostgreSQL monitoring queries
```

---

## 🔧 **Development Commands**

### **Service Management**
```bash
# Start all services
make start

# Development mode with auto-reload
make dev-start

# Stop all services cleanly
make stop

# Check service status
make status

# View live logs
make dev-logs
```

### **Enhanced Celery Commands (v2.7.0)**
```bash
# Production worker management (Enhanced concurrency)
make celery-worker-start-multi    # Start 5 workers × 4 concurrency = 20 parallel tasks
make celery-worker-stop          # Stop all workers gracefully
make celery-status               # Check worker status

# Individual Celery commands
celery -A core.celery_app worker --loglevel=info --concurrency=4  # Start worker with 4 concurrent tasks
celery -A core.celery_app flower                                  # Monitor workers (Flower dashboard)
celery -A core.celery_app status                                  # Check worker status
celery -A core.celery_app purge                                   # Clear all tasks
```

### **Database Commands**
```bash
# Inspect PostgreSQL database
python3 tools/postgresql_inspector.py

# Test database connection
python3 -c "from core.database_manager import PostgreSQLManager; pg = PostgreSQLManager(); print('✅ Connected')"
```

### **Docker Stack Management**
```bash
# Start PostgreSQL monitoring stack
docker-compose -f config/docker-compose.postgresql.yml up -d

# Check container status
docker ps

# View container logs
docker logs agentos-postgresql
```

---

## 📊 **Database Information**

### **PostgreSQL Connection**
- **Host**: localhost
- **Port**: 5432
- **Database**: agentos_production
- **User**: agentos_user
- **Connection Pool**: 20 base + 30 overflow connections

### **Tables & Schema**
```sql
-- Core application tables
jobs                    -- Automation job tracking
users                   -- User accounts and credits
clips                   -- Generated content results
processing_steps        -- Agent execution audit trail

-- System tables
system_events          -- Performance monitoring (SSOT)
system_config          -- Configuration management
system_logs            -- Structured application logs
```

### **Key Indexes**
- Primary keys on all tables
- Job status + created_at composite index
- User ID foreign key indexes
- Processing step job_id index

---

## 🚀 **Quick Start Testing**

### **1. Verify Core System**
```bash
# Test imports
python3 -c "from core.database_manager import PostgreSQLManager; print('✅ Core imports work')"

# Test database connection
python3 -c "from core.database_manager import PostgreSQLManager; pg = PostgreSQLManager(); print('✅ PostgreSQL connected')"

# Test API
curl http://localhost:8001/health
```

### **2. Test Monitoring Stack**
```bash
# Check containers
docker ps

# Test database inspector
python3 tools/postgresql_inspector.py
```

### **3. Access Dashboards**
- Open PgAdmin: http://172.30.108.252:5050
- Open Grafana: http://172.30.108.252:3000
- Check API docs: http://localhost:8001/docs

---

## 🔑 **Credentials & Access**

### **Database Access**
- **PostgreSQL**: agentos_user / secure_agentos_2024
- **PgAdmin**: admin@example.com / admin123

### **Monitoring Access**
- **Grafana**: admin / admin123
- **Prometheus**: No authentication required

### **Application Access**
- **API**: No authentication in development
- **Admin UI**: No authentication in development

---

## 🛠️ **Troubleshooting**

### **Common Issues**
```bash
# Port conflicts
make kill-ports

# Container issues
docker-compose -f config/docker-compose.postgresql.yml restart

# Import errors after restructure
python3 -c "import sys; sys.path.append('.'); from core.database_manager import PostgreSQLManager"

# Database connection test
python3 tools/postgresql_inspector.py
```

### **Service Health Checks**
```bash
# Check all services
make status

# Test specific components
curl http://localhost:8001/health      # API health
curl http://localhost:8004/            # Admin UI
curl http://172.30.108.252:5050/login  # PgAdmin
```

---

## 🎉 **SUCCESS: Endpoint Cleanup Project - COMPLETED!**

### **🏆 MAJOR ACHIEVEMENT: 80 → 31 Endpoints (61% Reduction!)**

**📍 Complete Documentation & Results:**
```bash
/endpoint-monitoring/
├── ENDPOINT_CLEANUP_PLAN.md      # Implementation plan (COMPLETED)
├── run_endpoint_check.py         # Progress monitoring (31 endpoints)
├── data/endpoint_report.json     # Final health report: HEALTHY
└── docs/endpoints/
    ├── ENDPOINT_GOVERNANCE.md    # Updated governance rules
    └── QUICK_REFERENCE.md        # New enterprise architecture
```

**🎯 Three-Phase Cleanup COMPLETED:**
✅ **Phase 1**: Quick Wins - Removed 11 duplicate admin endpoints (80→69)
✅ **Phase 2**: Enterprise Patterns - Added aggregated endpoints (69→79)  
✅ **Phase 3**: Resource Architecture - Modern REST patterns (79→31)

**Current Status:**
```bash
cd endpoint-monitoring
python3 run_endpoint_check.py    # Status: 🟢 HEALTHY (31/80 used)
```

---

## 🎯 **Architecture Summary**

**AgentOS v2.7.0** is a distributed AI agent framework with:

- **🏗️ Core Framework**: PostgreSQL + Enhanced Celery (4×5=20 concurrent tasks) + FastAPI
- **🤖 Agent System**: 13 pluggable AI agents with working video generation pipeline
- **🎛️ Enhanced Admin Interface**: Activity Monitoring + Framework Management with real-time updates
- **📊 Dual Monitoring**: Grafana + Prometheus stack + live admin dashboard
- **🔄 Advanced Task Processing**: 5 workers × 4 concurrency for high-throughput processing
- **🌐 Multi-UI**: Framework supports multiple specialized interfaces
- **📈 Production Ready**: Connection pooling, graceful shutdown, comprehensive monitoring
- **⚡ Real-time Features**: Live activity feeds, WebSocket updates, immediate action feedback

**Perfect foundation for building automation workflows beyond just video processing!** 🚀

### **🎉 Latest Achievements (v2.7.0)**
- ✅ **Working Video Generation**: End-to-end pipeline produces real MP4 clips
- ✅ **Enterprise API Architecture**: 61% endpoint reduction (80→31) with Resource patterns
- ✅ **Improved Concurrency**: 4× performance boost (5 workers × 4 tasks = 20 parallel)
- ✅ **Live Activity Tracking**: Real-time updates when performing system actions
- ✅ **Unified Management**: Combined agent/worker views with tabbed interface
- 🎯 **Health Status**: From "CAUTION" to "HEALTHY" - 49 endpoints headroom for growth!