# Debug Tools Collection

**Created during: Dashboard "0/5 completed today" → "1/5 completed today" fix**  
**Date: 11 Augustus 2025**

## 🎯 Purpose
These tools were created to debug discrepancies between what the backend calculates, what the API sends, and what the frontend displays.

## 📁 Tools Included

### 1. `ui-data-validator.html`
**Real-time UI vs API comparison tool**
- Open in browser alongside your dashboard
- Captures exact UI display values
- Compares with live API responses
- Shows discrepancies in real-time

**Usage:** Open `http://localhost:8080/ui-data-validator.html` in new browser tab

### 2. `debug-dashboard.html` 
**Interactive dashboard debugger**
- Step-by-step data flow analysis
- Cache inspection
- Performance metrics
- Visual discrepancy highlighting

**Usage:** Load alongside dashboard for detailed analysis

### 3. `STOP_AUTO_REFRESH.js`
**Disable auto-refresh for testing**
- Stops CentralDataService polling
- Blocks WebSocket updates
- Freezes UI state for inspection
- Prevents test data from being overwritten

**Usage:** Paste in browser console to stop all auto-refreshes

### 4. `MANUAL_TEST_DASHBOARD.js`
**Manual testing functions**
- `captureUI()` - Show current UI state
- `fetchAPI()` - Get current API data  
- `compareUIAPI()` - Compare UI vs API
- `updateJobsCard(completed, total, rate)` - Manually update jobs card

**Usage:** Paste in browser console for manual testing functions

### 5. `validate_dashboard_data.py`
**Complete backend-to-API validation script**
- Tests database layer
- Tests service layer
- Tests API layer
- Generates detailed reports

**Usage:** `python3 validate_dashboard_data.py`

## 🔧 When to Use These Tools

### For Similar Data Discrepancy Problems:
1. **Run Python validator** - find which layer is wrong
2. **Use STOP_AUTO_REFRESH.js** - prevent interference  
3. **Use ui-data-validator.html** - compare UI vs API real-time
4. **Use manual test functions** - test specific values

### For New Metric Issues:
1. Check if new metric appears in all layers
2. Verify cache structure includes new fields
3. Test data transformations
4. Validate UI rendering

## 💡 Lessons Learned from This Debug Session

### The Problem:
- Dashboard showed "0/5 completed today" 
- Should have shown "1/5 completed today"

### Root Cause:
- Backend: QueueService counted ALL completed jobs (not just today)
- Frontend: Looked for `jobs.completed` instead of `queue.completed_today`
- Cache: Auto-refresh kept overwriting fixes during testing

### The Fix:
1. **Backend:** Changed QueueService to only count today's jobs
2. **Frontend:** Modified Dashboard.js to use queue.completed_today  
3. **Testing:** Used these debug tools to validate each layer

## 🗂️ Keep These Tools Because:

✅ **Reusable** - Same patterns apply to other metrics  
✅ **Time-saving** - No need to recreate debug infrastructure  
✅ **Educational** - Show complete data flow understanding  
✅ **Professional** - Systematic approach to debugging  

## 🧹 Cleanup Recommendation

**Keep in `/tools/debug/` folder:**
- Ready for future metric issues
- Reference for data flow debugging
- Training material for team members
- Documentation of debugging methodology

**Don't delete** - these tools represent significant debugging infrastructure that took time to build and will be useful again.