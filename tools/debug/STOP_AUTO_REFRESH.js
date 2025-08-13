// EMERGENCY SCRIPT: Stop alle auto-refresh mechanismen
// Open browser console en plak dit in om auto-refresh te stoppen

console.log('🛑 STOPPING ALL AUTO-REFRESH MECHANISMS...');

// Stop alle intervals
let highestTimeoutId = setTimeout(";");
for (let i = 0; i < highestTimeoutId; i++) {
    clearTimeout(i);
    clearInterval(i);
}

// Stop WebSocket verbindingen
if (window.centralDataService) {
    try {
        window.centralDataService.stop();
        console.log('✅ CentralDataService stopped');
    } catch (e) {
        console.log('CentralDataService stop failed:', e);
    }
}

// Stop alle WebSocket verbindingen
if (window.WebSocket) {
    const originalWebSocket = window.WebSocket;
    window.WebSocket = function() {
        console.log('🚫 WebSocket creation blocked');
        return { close: () => {}, send: () => {} };
    };
}

// Stop fetch calls naar admin endpoints
const originalFetch = window.fetch;
window.fetch = function(url, options) {
    if (url.includes('/api/admin/ssot')) {
        console.log('🚫 Blocked auto-refresh API call to:', url);
        return Promise.resolve({
            json: () => Promise.resolve({ blocked: true, timestamp: new Date().toISOString() })
        });
    }
    return originalFetch.call(this, url, options);
};

// Stop alle setTimeout/setInterval voor dashboard
const originalSetTimeout = window.setTimeout;
const originalSetInterval = window.setInterval;

window.setTimeout = function(callback, delay) {
    const stack = new Error().stack;
    if (stack.includes('dashboard') || stack.includes('central-data') || stack.includes('refresh')) {
        console.log('🚫 Blocked setTimeout for dashboard refresh');
        return 0;
    }
    return originalSetTimeout.call(this, callback, delay);
};

window.setInterval = function(callback, delay) {
    const stack = new Error().stack;
    if (stack.includes('dashboard') || stack.includes('central-data') || stack.includes('refresh')) {
        console.log('🚫 Blocked setInterval for dashboard refresh');
        return 0;
    }
    return originalSetInterval.call(this, callback, delay);
};

// Forceer UI state te bewaren
const UI_STATE = {
    timestamp: new Date().toISOString(),
    metrics: Array.from(document.querySelectorAll('.metric-card')).map(card => ({
        title: card.querySelector('.metric-card__title')?.textContent,
        value: card.querySelector('.metric-card__value')?.textContent,
        description: card.querySelector('.metric-card__description')?.textContent
    }))
};

console.log('💾 Current UI state preserved:', UI_STATE);

// Monitor voor changes en log ze
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.target.classList && mutation.target.classList.contains('metric-card__description')) {
            console.log('⚠️ Metric card changed!', {
                oldValue: mutation.oldValue,
                newValue: mutation.target.textContent,
                timestamp: new Date().toISOString()
            });
        }
    });
});

observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true,
    characterDataOldValue: true
});

console.log('🔍 UI change monitor activated');
console.log('✅ Auto-refresh stopped! UI should now be stable for testing.');