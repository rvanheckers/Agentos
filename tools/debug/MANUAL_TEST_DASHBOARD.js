// MANUAL DASHBOARD TESTER
// Open browser console en plak dit in om handmatig te testen

console.log('🧪 MANUAL DASHBOARD TESTER ACTIVATED');

// Functie om exact te zien wat er in de UI staat
function captureCurrentUIState() {
    const metrics = Array.from(document.querySelectorAll('.metric-card')).map(card => {
        return {
            title: card.querySelector('.metric-card__title')?.textContent?.trim(),
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

// Functie om API data op te halen
async function fetchCurrentAPIData() {
    try {
        console.log('📡 Fetching API data...');
        const response = await fetch('http://localhost:8001/api/admin/ssot');
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
        console.error('❌ API fetch failed:', error);
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
    const jobsCard = Array.from(document.querySelectorAll('.metric-card')).find(card => 
        card.querySelector('.metric-card__title')?.textContent?.includes('Jobs')
    );
    
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