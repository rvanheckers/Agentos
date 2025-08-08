# 🧪 Jobs & Queue Testing Scripts

**Directory Purpose:** Dedicated testing scripts voor Jobs & Queue management functionality

**Created:** 3 Augustus 2025  
**Project:** AgentOS Admin UI - Jobs & Queue Testing

---

## 📁 **Test Scripts Overview**

### **🔍 API Testing**
- `test-ssot-api.sh` - Test SSOT endpoint voor jobs & queue data
- `test-jobs-api.sh` - Test alle job-related API endpoints
- `test-queue-api.sh` - Test queue status en worker endpoints

### **🎯 UI Testing**  
- `test-queue-ui.html` - Direct HTML test voor Queue view functionality
- `test-filter-presets.js` - Test SmartFilter presets voor queue
- `test-bulk-actions.js` - Test bulk job selection en actions

### **📊 Data Testing**
- `test-job-data-parsing.js` - Test job data parsing van SSOT API
- `test-queue-stats.js` - Test queue statistics berekeningen
- `test-real-vs-mock.js` - Vergelijk echte data vs mock data

### **🚀 Performance Testing**
- `test-queue-load.js` - Load testing met veel jobs
- `test-filter-performance.js` - Performance van filtering bij grote datasets
- `benchmark-queue-rendering.js` - Benchmark UI rendering performance

### **⚙️ Integration Testing**
- `test-full-workflow.sh` - End-to-end test van job creation tot completion
- `test-websocket-updates.js` - Test real-time updates via WebSocket
- `test-celery-integration.js` - Test Celery worker integration

---

## 🎯 **Quick Test Commands**

```bash
# API Tests
./test-ssot-api.sh
./test-jobs-api.sh  
./test-queue-api.sh

# UI Tests (open in browser)
open test-queue-ui.html

# Data Tests  
node test-job-data-parsing.js
node test-queue-stats.js

# Performance Tests
node test-queue-load.js
node benchmark-queue-rendering.js

# Integration Tests
./test-full-workflow.sh
node test-websocket-updates.js
```

---

## 📋 **Test Checklist**

### **✅ Core Functionality**
- [ ] SSOT API levert correcte jobs data
- [ ] Queue statistics kloppen met echte data  
- [ ] SmartFilter tabs werken (Live Queue, Job History, Performance, Alerts)
- [ ] Jobs table toont correcte data
- [ ] Status badges tonen juiste kleuren/iconen

### **✅ Interactive Features**
- [ ] Bulk selection (checkboxes) werkt
- [ ] Bulk actions toolbar verschijnt/verdwijnt
- [ ] Individual job actions (view, retry, cancel) werken
- [ ] Search & filtering responsive
- [ ] Pagination werkt bij grote datasets

### **✅ Real-time Updates** 
- [ ] Auto-refresh via CentralDataService
- [ ] Job status updates in real-time
- [ ] Queue statistics updaten automatisch
- [ ] No memory leaks bij continuous updates

### **✅ Error Handling**
- [ ] Graceful fallback bij API failures
- [ ] User feedback bij errors
- [ ] No console errors
- [ ] Recovery na connection loss

---

## 🔧 **Development Usage**

```bash
# Run all API tests
find . -name "test-*-api.sh" -exec {} \;

# Run all JS tests  
find . -name "test-*.js" -exec node {} \;

# Run specific test category
./test-jobs-api.sh && node test-job-data-parsing.js

# Performance benchmark
node benchmark-queue-rendering.js
```

---

## 📊 **Expected Results**

### **API Tests**
- SSOT endpoint: 200 OK met jobs & queue data
- Jobs API: CRUD operations werken
- Queue API: Status en worker info correct

### **UI Tests**
- Tab switching < 500ms
- Filter responses < 200ms  
- Bulk operations responsive
- No visual glitches

### **Data Tests**
- Job parsing: 100% accuracy
- Queue stats: Match echte data
- Mock vs real: Consistent structure

### **Performance Tests**
- 1000+ jobs: < 2s render time
- Filter 500+ jobs: < 300ms
- Memory usage stable

---

**Note:** Deze test scripts zijn specifiek voor Jobs & Queue functionality en gebruiken de echte AgentOS API endpoints en database.