// MANUAL DASHBOARD TESTER
// Open browser console en plak dit in om handmatig te testen

console.log('🧪 MANUAL DASHBOARD TESTER ACTIVATED');

// Configuration: API Base URL with environment-aware fallbacks
function getAPIBaseURL() {
    // Priority order for API URL detection:
    // 1. Build-time environment variable (if available)
    // 2. Runtime configuration window variable
    // 3. Derive from current window location 
    // 4. Development fallback
    
    if (typeof process !== 'undefined' && process.env && process.env.API_BASE_URL) {
        return { url: process.env.API_BASE_URL, source: 'Environment Variable' };
    }
    
    if (typeof window !== 'undefined' && window.AGENTOS_CONFIG && window.AGENTOS_CONFIG.API_BASE_URL) {
        return { url: window.AGENTOS_CONFIG.API_BASE_URL, source: 'Runtime Config' };
    }
    
    if (typeof window !== 'undefined' && window.location) {
        // Use current origin but switch to API port (8001)
        const currentOrigin = window.location.origin;
        if (currentOrigin.includes('localhost') || currentOrigin.includes('127.0.0.1')) {
            return { url: currentOrigin.replace(':8080', ':8001').replace(':3000', ':8001'), source: 'Derived from Location' };
        }
        // For production environments, assume API is on same origin with /api prefix
        return { url: currentOrigin, source: 'Production Origin' };
    }
    
    // Development fallback
    return { url: 'http://localhost:8001', source: 'Development Fallback' };
}

const { url: API_BASE_URL, source: API_SOURCE } = getAPIBaseURL();
console.log('🔧 API Configuration:', {
    API_BASE_URL,
    Detection_Method: API_SOURCE,
    Environment: (typeof process !== 'undefined' && process.release && process.release.name === 'node') ? 'Node.js' : 'Browser'
});

// Functie om exact te zien wat er in de UI staat
function captureCurrentUIState() {
    const metrics = Array.from(document.querySelectorAll('.metric-card')).map(card => {
        // Updated selectors to match new HTML structure
        const titleElement = card.querySelector('.metric-card__title');
        // Remove help icon from title text if present
        const titleText = titleElement ? titleElement.textContent?.replace('❓', '').trim() : null;
        
        return {
            title: titleText,
            value: card.querySelector('.metric-card__value')?.textContent?.trim(), 
            description: card.querySelector('.metric-card__description')?.textContent?.trim(),
            status: card.querySelector('.metric-card__status')?.textContent?.trim()
        };
    });
    
    console.table(metrics);
    
    // Focus op Today's Jobs card
    const jobsCard = metrics.find(m => m.title?.includes('Today\'s Jobs') || m.title?.includes('Jobs'));
    if (jobsCard) {
        console.log('🎯 JOBS CARD ANALYSIS:');
        console.log('Title:', jobsCard.title);
        console.log('Value:', jobsCard.value);  
        console.log('Description:', jobsCard.description);
        
        // Extract completion data
        const match = jobsCard.description?.match(/(\d+)% success \((\d+)\/(\d+) completed today\)/);
        if (match) {
            console.log('📊 EXTRACTED DATA:');
            console.log('  Success Rate:', match[1] + '%');
            console.log('  Completed Today:', match[2]);
            console.log('  Total Today:', match[3]);
            
            return {
                successRate: parseInt(match[1]),
                completedToday: parseInt(match[2]),
                totalToday: parseInt(match[3]),
                rawDescription: jobsCard.description
            };
        }
    }
    
    return metrics;
}

// Simple retry wrapper for fetch
async function fetchWithRetry(url, options = {}, maxRetries = 2) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const response = await fetch(url, options);
            return response;
        } catch (error) {
            if (attempt === maxRetries) throw error;
            
            const delay = Math.min(1000 * attempt, 3000); // 1s, 2s, then 3s max
            console.warn(`🔄 Retry attempt ${attempt}/${maxRetries} in ${delay}ms:`, error.message);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

// Functie om API data op te halen
async function fetchCurrentAPIData() {
    try {
        const apiUrl = `${API_BASE_URL}/api/admin/ssot`;
        console.log('📡 Fetching API data from:', apiUrl);
        
        const response = await fetchWithRetry(apiUrl);
        
        if (!response.ok) {
            console.error('❌ API HTTP error:', {
                status: response.status,
                statusText: response.statusText,
                url: response.url,
                headers: Object.fromEntries(response.headers.entries())
            });
            return null;
        }
        
        const data = await response.json();
        
        const queue = data.dashboard?.queue || {};
        const jobs = data.dashboard?.jobs || {};
        
        console.log('🔌 API RESPONSE:');
        console.log('  queue.completed_today:', queue.completed_today);
        console.log('  queue.failed_today:', queue.failed_today);
        console.log('  jobs.total_today:', jobs.total_today);
        console.log('  jobs.success_rate:', jobs.success_rate);
        
        return { queue, jobs };
    } catch (error) {
        // Detect CORS and network-specific issues
        const errorName = error?.name || '';
        const errorMessage = error?.message || '';
        
        if (errorName === 'TypeError' && 
            /Failed to fetch|NetworkError|CORS|Cross-Origin/i.test(errorMessage)) {
            
            console.error('❌ API fetch failed — mogelijke CORS/netwerk issue:', {
                name: errorName,
                message: errorMessage,
                apiUrl: `${API_BASE_URL}/api/admin/ssot`,
                suggestion: 'Check if API server is running en CORS is configured'
            });
            
        } else if (errorName === 'SyntaxError' && /JSON/i.test(errorMessage)) {
            
            console.error('❌ API returned invalid JSON:', {
                name: errorName,
                message: errorMessage,
                suggestion: 'Check server response format'
            });
            
        } else {
            
            console.error('❌ API fetch failed:', {
                name: errorName,
                message: errorMessage,
                stack: error?.stack,
                suggestion: 'Check console voor details'
            });
        }
        
        return null;
    }
}

// Functie om volledige vergelijking te doen
async function compareUIvsAPI() {
    console.log('\n' + '='.repeat(60));
    console.log('🔍 COMPARING UI vs API DATA');
    console.log('='.repeat(60));
    
    const uiData = captureCurrentUIState();
    const apiData = await fetchCurrentAPIData();
    
    if (!apiData) return;
    
    console.log('\n📊 COMPARISON RESULTS:');
    console.table([
        {
            Source: 'UI Shows',
            CompletedToday: uiData?.completedToday || '?',
            TotalToday: uiData?.totalToday || '?',
            SuccessRate: (uiData?.successRate || '?') + '%'
        },
        {
            Source: 'API Sends',
            CompletedToday: apiData.queue.completed_today || '?',
            TotalToday: apiData.jobs.total_today || '?',
            SuccessRate: (apiData.jobs.success_rate || '?') + '%'
        }
    ]);
    
    // Check for mismatches
    const mismatches = [];
    if (uiData?.completedToday !== apiData.queue.completed_today) {
        mismatches.push(`Completed Today: UI shows ${uiData?.completedToday}, API sends ${apiData.queue.completed_today}`);
    }
    
    if (mismatches.length > 0) {
        console.log('\n❌ MISMATCHES FOUND:');
        mismatches.forEach((m, i) => console.log(`  ${i+1}. ${m}`));
    } else {
        console.log('\n✅ All data matches!');
    }
    
    return { uiData, apiData, mismatches };
}

// Functie om de Jobs card handmatig te updaten (voor testing)
function manualUpdateJobsCard(completedToday, totalToday, successRate) {
    const jobsCard = Array.from(document.querySelectorAll('.metric-card')).find(card => {
        const titleText = card.querySelector('.metric-card__title')?.textContent?.replace('❓', '').trim();
        return titleText?.includes('Jobs');
    });
    
    if (jobsCard) {
        const descElement = jobsCard.querySelector('.metric-card__description');
        const valueElement = jobsCard.querySelector('.metric-card__value');
        
        if (descElement && valueElement) {
            valueElement.textContent = totalToday.toString();
            descElement.textContent = `${successRate}% success (${completedToday}/${totalToday} completed today)`;
            
            console.log('✏️ MANUALLY UPDATED Jobs Card:');
            console.log(`  Value: ${totalToday}`);
            console.log(`  Description: ${successRate}% success (${completedToday}/${totalToday} completed today)`);
        }
    }
}

// Maak functies globaal beschikbaar
window.captureUI = captureCurrentUIState;
window.fetchAPI = fetchCurrentAPIData;
window.compareUIAPI = compareUIvsAPI;
window.updateJobsCard = manualUpdateJobsCard;

console.log('\n🎮 AVAILABLE COMMANDS:');
console.log('  captureUI()     - Show current UI state');
console.log('  fetchAPI()      - Get current API data');
console.log('  compareUIAPI()  - Compare UI vs API');
console.log('  updateJobsCard(completed, total, rate) - Manually update jobs card');

console.log('\n🚀 Ready for testing! Try: compareUIAPI()');