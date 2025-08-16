// EMERGENCY SCRIPT: Stop alle auto-refresh mechanismen
// Open browser console en plak dit in om auto-refresh te stoppen

console.log('🛑 STOPPING ALL AUTO-REFRESH MECHANISMS...');

// Stop alle intervals - safe deterministic pattern
// Create a no-op timeout to get current highest ID
let highestTimeoutId = setTimeout(function() {}, 0);
// Convert to integer to ensure proper bounds handling
highestTimeoutId = parseInt(highestTimeoutId, 10);
// Clear the probe timeout immediately
clearTimeout(highestTimeoutId);

// Iterate downward from highest ID to zero clearing all timeouts and intervals
for (let i = highestTimeoutId; i >= 0; i--) {
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
    
    // Complete WebSocket mock implementation
    window.WebSocket = function(url, protocols) {
        console.log('🚫 WebSocket creation blocked for URL:', url);
        
        // WebSocket readyState constants (as per WebSocket API specification)
        const CONNECTING = 0;
        const OPEN = 1;
        const CLOSING = 2;
        const CLOSED = 3;
        
        // Create mock WebSocket instance with full API compatibility
        const mockWebSocket = {
            // Standard WebSocket properties
            url: url,
            protocol: Array.isArray(protocols) ? protocols[0] || '' : protocols || '',
            readyState: CLOSED, // Start as CLOSED since we're blocking
            bufferedAmount: 0,
            extensions: '',
            binaryType: 'blob',
            
            // WebSocket constants (attached to instance)
            CONNECTING: CONNECTING,
            OPEN: OPEN,
            CLOSING: CLOSING,
            CLOSED: CLOSED,
            
            // Event handlers (default to no-ops)
            onopen: null,
            onmessage: null,
            onerror: null,
            onclose: null,
            
            // Methods
            send: function(data) {
                console.log('🚫 WebSocket send() blocked, data:', data);
                // Silently ignore - don't queue messages since we're intentionally blocking
            },
            
            close: function(code = 1000, reason = 'Connection closed by mock') {
                if (this.readyState === CLOSED || this.readyState === CLOSING) {
                    return; // Already closed/closing
                }
                
                console.log('🚫 WebSocket close() called, code:', code, 'reason:', reason);
                this.readyState = CLOSED;
                
                // Call onclose handler if it exists
                if (typeof this.onclose === 'function') {
                    try {
                        this.onclose({
                            type: 'close',
                            code: code,
                            reason: reason,
                            wasClean: true,
                            target: this
                        });
                    } catch (e) {
                        console.warn('🚫 WebSocket onclose handler error:', e);
                    }
                }
            },
            
            // EventTarget methods for addEventListener/removeEventListener compatibility
            addEventListener: function(type, listener, options) {
                console.log(`🚫 WebSocket addEventListener(${type}) blocked`);
                // No-op - don't actually register listeners
            },
            
            removeEventListener: function(type, listener, options) {
                console.log(`🚫 WebSocket removeEventListener(${type}) blocked`);
                // No-op
            },
            
            dispatchEvent: function(event) {
                console.log('🚫 WebSocket dispatchEvent blocked:', event.type);
                return false;
            }
        };
        
        // Simulate immediate close event (async to match real WebSocket behavior)
        setTimeout(() => {
            if (typeof mockWebSocket.onclose === 'function') {
                try {
                    mockWebSocket.onclose({
                        type: 'close',
                        code: 1006, // Abnormal closure
                        reason: 'WebSocket blocked by debug script',
                        wasClean: false,
                        target: mockWebSocket
                    });
                } catch (e) {
                    console.warn('🚫 WebSocket mock onclose error:', e);
                }
            }
        }, 0);
        
        return mockWebSocket;
    };
    
    // Copy static constants to constructor function
    window.WebSocket.CONNECTING = 0;
    window.WebSocket.OPEN = 1;
    window.WebSocket.CLOSING = 2;
    window.WebSocket.CLOSED = 3;
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
        let targetElement = null;
        let newValue = null;
        
        // Check if target is an element node (nodeType 1) or text node (nodeType 3)
        if (mutation.target.nodeType === Node.ELEMENT_NODE) {
            // Element node - check classList directly
            if (mutation.target.classList && mutation.target.classList.contains('metric-card__description')) {
                targetElement = mutation.target;
                newValue = mutation.target.textContent;
            }
        } else if (mutation.target.nodeType === Node.TEXT_NODE) {
            // Text node - check parentElement for the class
            const parentElement = mutation.target.parentElement;
            if (parentElement && parentElement.classList && parentElement.classList.contains('metric-card__description')) {
                targetElement = parentElement;
                newValue = parentElement.textContent;
            }
        }
        
        // Log if we found a metric card change
        if (targetElement) {
            console.log('⚠️ Metric card changed!', {
                oldValue: mutation.oldValue,
                newValue: newValue,
                targetType: mutation.target.nodeType === Node.ELEMENT_NODE ? 'element' : 'text',
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