# Real Monitoring Data Integration Plan
**Status: 📋 PLANNING**  
**Datum: 8 Augustus 2025**  
**Doel: Vervang test data met echte Grafana/Celery/Prometheus metrics**

## 🎯 Het Probleem

**Momenteel:** AgentOS dashboard gebruikt **test data** voor mooie cijfers  
**Gewenst:** Echte metrics uit jullie **Grafana + Celery + Prometheus** stack

## 📊 Huidige Test Data vs Gewenste Echte Data

### **Queue Analytics (Fake → Real)**
```javascript
// ❌ HUIDIGE TEST DATA
"Processing Rate: 17/min → +2%"  // analytics_service.py - fake berekening
"Queue Depth: 8 jobs ↗ -15%"    // queue_service.py - fake trend data
```

```javascript  
// ✅ ECHTE DATA BRONNEN
"Processing Rate: 23/min → +5%"  // Grafana: sum(rate(jobs_completed[1m]))
"Queue Depth: 12 jobs ↗ -8%"    // Celery: celery inspect active_queues()
```

### **Worker Health (Mix → Real)**
```javascript
// 🔄 GEDEELTELIJK ECHT 
"Active Workers: 5/5" ✅         // Celery inspect - ECHT
"Avg Load: 74% 🟡"   ❌         // Fake percentage - NEEM PROMETHEUS
```

## 🔧 Integration Plan per Component

### **1. Grafana API Integration**
**Doel:** Vervang `AnalyticsService` fake metrics

**Huidige locatie:** `/services/analytics_service.py`
```python
# ❌ FAKE DATA
def get_performance_metrics(self, time_range="24h"):
    return {
        "processing_rate": 17.3,  # FAKE
        "success_rate": 94.2,     # FAKE
        "avg_duration": 125.5     # FAKE
    }
```

**Nieuwe implementatie:**
```python
# ✅ ECHTE GRAFANA DATA  
import requests

def get_performance_metrics(self, time_range="24h"):
    grafana_query = {
        "query": "sum(rate(agentos_jobs_completed_total[1m]))",
        "start": f"-{time_range}",
        "step": "1m"
    }
    
    response = requests.post(
        f"{GRAFANA_URL}/api/v1/query_range",
        json=grafana_query,
        headers={"Authorization": f"Bearer {GRAFANA_TOKEN}"}
    )
    
    return {
        "processing_rate": calculate_rate_from_prometheus(response.json()),
        "success_rate": get_success_rate_from_grafana(time_range),
        "avg_duration": get_avg_duration_from_grafana(time_range)
    }
```

### **2. Celery Monitoring Integration** 
**Doel:** Echte worker stats uit Celery

**Huidige locatie:** `/services/queue_service.py`
```python
# ❌ FAKE WORKER DATA
def get_workers_status(self):
    return [
        {"id": "worker-1", "status": "active", "load": 74},  # FAKE
        {"id": "worker-2", "status": "active", "load": 82},  # FAKE
    ]
```

**Nieuwe implementatie:**
```python  
# ✅ ECHTE CELERY DATA
from celery import Celery

def get_workers_status(self):
    app = Celery('agentos')
    inspect = app.control.inspect()
    
    # Echte Celery worker data
    active_workers = inspect.active()      # Actieve jobs per worker  
    stats = inspect.stats()                # Worker statistieken
    registered = inspect.registered()      # Geregistreerde tasks
    
    workers = []
    for worker_name, worker_stats in stats.items():
        workers.append({
            "id": worker_name,
            "status": "active" if worker_name in active_workers else "idle",
            "load": calculate_worker_load(worker_stats),     # ECHTE berekening
            "active_jobs": len(active_workers.get(worker_name, [])),
            "memory_usage": worker_stats.get('rusage', {}).get('maxrss', 0),
            "cpu_time": worker_stats.get('rusage', {}).get('utime', 0)
        })
    
    return workers
```

### **3. Prometheus Metrics Integration**
**Doel:** System health uit Prometheus

**Huidige locatie:** `/services/admin_data_manager.py`
```python
# ❌ FAKE SYSTEM HEALTH
def _get_system_health(self):
    return {
        "cpu_usage": 23.1,    # FAKE
        "memory_usage": 67.8, # FAKE  
        "disk_usage": 45.2    # FAKE
    }
```

**Nieuwe implementatie:**
```python
# ✅ ECHTE PROMETHEUS DATA
def _get_system_health(self):
    prometheus_queries = {
        "cpu_usage": "100 - (avg(irate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)",
        "memory_usage": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",  
        "disk_usage": "(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100"
    }
    
    metrics = {}
    for metric_name, query in prometheus_queries.items():
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query}
        )
        metrics[metric_name] = extract_prometheus_value(response.json())
    
    return metrics
```

### **4. Redis Queue Stats Integration**
**Doel:** Echte queue depth en trends

```python
# ✅ ECHTE REDIS QUEUE DATA
import redis

def get_real_queue_stats(self):
    r = redis.Redis(host='localhost', port=6379)
    
    # Echte queue metrics
    queues = ['default', 'high_priority', 'low_priority'] 
    total_pending = sum(r.llen(f"celery:{queue}") for queue in queues)
    
    # Trend berekening uit historische Redis data
    historical_depths = r.lrange("queue_depth_history", 0, 60)  # Last hour
    trend = calculate_trend_percentage(historical_depths)
    
    return {
        "queue_depth": total_pending,
        "trend_percentage": trend,
        "queues_breakdown": {queue: r.llen(f"celery:{queue}") for queue in queues}
    }
```

## 🛠️ Implementatie Steps

### **Step 1: Environment Setup**
```bash
# Voeg environment variabelen toe
export GRAFANA_URL="http://localhost:3000"
export GRAFANA_TOKEN="your_grafana_api_token"  
export PROMETHEUS_URL="http://localhost:9090"
```

### **Step 2: New Service Creation** 
```python
# Nieuwe service: /services/real_monitoring_service.py
class RealMonitoringService:
    """
    Centrale service voor het ophalen van echte monitoring data
    uit Grafana, Prometheus, en Celery
    """
    
    def get_grafana_metrics(self, time_range): pass
    def get_prometheus_metrics(self, queries): pass  
    def get_celery_worker_stats(self): pass
    def get_redis_queue_stats(self): pass
```

### **Step 3: Service Updates**
1. **analytics_service.py** → gebruik RealMonitoringService
2. **queue_service.py** → gebruik echte Celery data
3. **admin_data_manager.py** → gebruik Prometheus metrics

### **Step 4: Configuration**
```python
# /config/monitoring_config.py
MONITORING_CONFIG = {
    "grafana": {
        "url": os.getenv("GRAFANA_URL"),
        "token": os.getenv("GRAFANA_TOKEN"),
        "dashboard_id": "agentos-main"
    },
    "prometheus": {
        "url": os.getenv("PROMETHEUS_URL"), 
        "queries": {
            "job_completion_rate": "sum(rate(agentos_jobs_completed_total[1m]))",
            "error_rate": "sum(rate(agentos_jobs_failed_total[1m]))"
        }
    },
    "celery": {
        "broker_url": os.getenv("CELERY_BROKER_URL"),
        "inspect_timeout": 5.0
    }
}
```

## 🎯 Expected Results

### **Voor (Test Data)**
```
📊 Processing Rate: 17/min → +2%    [FAKE]
⚙️ Active Workers: 5/5 🟢           [GEDEELTELIJK ECHT]
💾 Memory Usage: 67.8%              [FAKE]
```

### **Na (Real Data)**  
```
📊 Processing Rate: 23/min → +5%    [GRAFANA REAL-TIME]
⚙️ Active Workers: 3/5 🟡           [CELERY INSPECT]  
💾 Memory Usage: 82.3%              [PROMETHEUS NODE_EXPORTER]
```

## 📋 Implementation Checklist

- [ ] **Environment setup** (Grafana token, Prometheus URL)
- [ ] **RealMonitoringService creation**
- [ ] **Grafana API integration**
- [ ] **Celery inspect integration** 
- [ ] **Prometheus queries setup**
- [ ] **Redis queue stats**
- [ ] **Update analytics_service.py**
- [ ] **Update queue_service.py**
- [ ] **Update admin_data_manager.py**
- [ ] **Test real data flow**
- [ ] **Remove all fake data generators**

## 💡 Benefits

✅ **100% authentic dashboards**  
✅ **Real performance insights**  
✅ **Accurate capacity planning**  
✅ **Production-grade monitoring**  
✅ **No more "movie props" data**

---

**Ready to implement real monitoring data integration?** 🚀  
**Let's replace fake data with real production insights!**