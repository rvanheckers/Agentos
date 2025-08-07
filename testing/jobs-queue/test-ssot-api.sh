#!/bin/bash

# 🧪 SSOT API Test Script
# Tests the Single Source of Truth endpoint for Jobs & Queue data

echo "🔍 Testing SSOT API Endpoint for Jobs & Queue..."
echo "================================================"

# Test SSOT endpoint
echo "📡 Testing /api/admin/ssot endpoint..."
RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" http://localhost:8001/api/admin/ssot)
HTTP_STATUS=$(echo $RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
BODY=$(echo $RESPONSE | sed -e 's/HTTPSTATUS\:.*//g')

if [ $HTTP_STATUS -eq 200 ]; then
    echo "✅ SSOT API: HTTP 200 OK"
    
    # Parse and validate JSON structure
    echo "$BODY" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('✅ JSON: Valid structure')
    
    # Check dashboard section
    if 'dashboard' in data:
        dashboard = data['dashboard']
        print('✅ Dashboard section: Present')
        
        # Check jobs section
        if 'jobs' in dashboard:
            jobs = dashboard['jobs']
            recent_jobs = jobs.get('recent_jobs', [])
            print(f'✅ Recent jobs: Found {len(recent_jobs)} jobs')
            
            if recent_jobs:
                job = recent_jobs[0]
                required_fields = ['id', 'status', 'created_at', 'progress']
                missing = [f for f in required_fields if f not in job]
                if not missing:
                    print('✅ Job structure: All required fields present')
                else:
                    print(f'❌ Job structure: Missing fields {missing}')
        else:
            print('❌ Dashboard: Missing jobs section')
            
        # Check queue section  
        if 'queue' in dashboard:
            queue = dashboard['queue']
            required_fields = ['pending', 'processing', 'completed_today', 'failed_today']
            missing = [f for f in required_fields if f not in queue]
            if not missing:
                print('✅ Queue structure: All required fields present')
                print(f'📊 Queue stats: {queue[\"pending\"]} pending, {queue[\"processing\"]} processing')
            else:
                print(f'❌ Queue structure: Missing fields {missing}')
        else:
            print('❌ Dashboard: Missing queue section')
    else:
        print('❌ SSOT: Missing dashboard section')
        
    # Check queue detail section
    if 'queue' in data:
        queue_detail = data['queue']
        print('✅ Queue detail section: Present')
        
        if 'job_history' in queue_detail:
            job_history = queue_detail['job_history']
            print(f'✅ Job history: Found {len(job_history)} historical jobs')
        else:
            print('❌ Queue detail: Missing job_history')
    else:
        print('❌ SSOT: Missing queue detail section')
        
except json.JSONDecodeError as e:
    print(f'❌ JSON: Invalid structure - {e}')
except Exception as e:
    print(f'❌ Error: {e}')
"
else
    echo "❌ SSOT API: HTTP $HTTP_STATUS"
    echo "Response: $BODY"
fi

echo ""
echo "🔍 Testing specific queue endpoints..."

# Test jobs today endpoint
echo "📡 Testing /api/jobs/today endpoint..."
RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" http://localhost:8001/api/jobs/today)
HTTP_STATUS=$(echo $RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

if [ $HTTP_STATUS -eq 200 ]; then
    echo "✅ Jobs Today API: HTTP 200 OK"
else
    echo "❌ Jobs Today API: HTTP $HTTP_STATUS"
fi

# Test queue status endpoint  
echo "📡 Testing /api/queue/status endpoint..."
RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" http://localhost:8001/api/queue/status)
HTTP_STATUS=$(echo $RESPONSE | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

if [ $HTTP_STATUS -eq 200 ]; then
    echo "✅ Queue Status API: HTTP 200 OK"
else
    echo "❌ Queue Status API: HTTP $HTTP_STATUS"
fi

echo ""
echo "🎯 SSOT API Test Complete"
echo "========================"