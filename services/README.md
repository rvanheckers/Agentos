# Service Layers (Managers) - Business Logic Middleware

## Data-efficiency engines voor AgentOS – nu met performance monitoring

In de **Admin UI** worden deze service layers **"Managers"** genoemd voor performance monitoring.

## Architectuur Principe

**"2 deuren naar 1 kamer"** - Admin & user endpoints delen dezelfde service layer business logic voor maximale data efficiency en code hergebruik.

```text
Admin UI View → API Endpoint → Service Layer → Database
User API Call → API Endpoint → Service Layer → Database
                    ↑              ↑
               Clean Routes   Shared Logic
```

## Huidige Service Layers (Managers)

### Core Services/Managers
- **`jobs_service.py`** - **Jobs Manager** - Job management, analytics, retry logic  
- **`agents_service.py`** - **Agents Manager** - Agent lifecycle, status, configuratie
- **`workers_service.py`** - **Workers Manager** - Worker status, discovery, monitoring
- **`queue_service.py`** - **Queue Manager** - Queue management, prioritering
- **`upload_service.py`** - **Upload Manager** - File handling, processing
- **`analytics_service.py`** - **Analytics Manager** - Usage statistics, reporting

### 🏢 Managers Performance Monitoring
**NEW**: Real-time performance monitoring via `/api/admin/managers/*` endpoints:
- **Health status** per manager
- **Response time** tracking  
- **Success/error rates**
- **System resource usage**
- **Method-level performance**

## Admin UI Mapping

Service layers ondersteunen **meerdere admin views** via gedeelde business logic:

- **📊 Dashboard** = Combinatie van alle services
- **👷 Workers** = workers_service.py (Workers Manager)
- **📋 Job Queue** = jobs_service.py + queue_service.py (Jobs + Queue Managers)
- **📈 Analytics** = analytics_service.py (Analytics Manager)
- **🏢 Managers Performance** = **NEW** - Monitoring van alle managers
- **🎛️ System Controls** = System management endpoints

## Refactor + Managers Resultaat

**Voor**: 170 endpoints met duplicated logic  
**Na**: 64 endpoints + 6 service layers + performance monitoring  
**Voordeel**: Geen data duplicatie, consistent format, onderhoudsbaar + real-time monitoring

### **🎯 Current Status (2025-07-26):**
- ✅ **64 total endpoints** (was 170 → -62% reduction)
- ✅ **6 service layers** (managers) fully operational
- ✅ **3 monitoring endpoints** for real-time performance tracking
- ✅ **0 duplicates** - Clean architecture achieved
- ✅ **Admin UI integration** - Managers view for performance monitoring

## Principle

Elke service layer is een **domein expert** (manager) die weet hoe zijn deel van het systeem werkt, zodat endpoints simpel blijven en alleen hoeven te zeggen "doe X" zonder te weten hoe X werkt.

## 🏢 Managers Monitoring Usage

**Admin UI Performance View:**
```javascript
// Access via admin UI: Navigation → Monitoring → Managers Performance
// Real-time monitoring dashboard shows:
// - Overall health of all 6 managers
// - Individual response times and success rates  
// - System resource usage per manager
// - Method-level performance details
```

**API Endpoints:**
```bash
# Overall managers health
GET /api/admin/managers/status

# Detailed metrics for specific manager
GET /api/admin/managers/jobs/metrics
GET /api/admin/managers/workers/metrics  

# Dashboard summary for admin UI
GET /api/admin/managers/performance-summary
```

**Available Managers:**
- `jobs` - Job creation, status, analytics
- `agents` - Agent lifecycle and execution
- `workers` - Worker processes and monitoring  
- `queue` - Job queue management
- `upload` - File upload handling
- `analytics` - Usage statistics and reporting