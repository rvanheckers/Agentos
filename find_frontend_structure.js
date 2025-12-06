// BROWSER CONSOLE - Find correct frontend structure
console.log('🔍 FINDING FRONTEND STRUCTURE');

// Check all possible window properties
console.log('📋 Window properties:');
Object.keys(window).filter(key => key.includes('app') || key.includes('store') || key.includes('video')).forEach(key => {
  console.log(`  - ${key}:`, window[key]);
});

// Check common patterns
console.log('\n🎯 CHECKING COMMON PATTERNS:');

// Pattern 1: Direct store objects
if (window.videoStore) {
  console.log('✅ Found window.videoStore');
  const state = window.videoStore.getState();
  console.log('  State:', state);
}

// Pattern 2: App with stores
if (window.App) {
  console.log('✅ Found window.App');
  console.log('  App:', window.App);
  if (window.App.stores) {
    console.log('  App.stores:', window.App.stores);
  }
}

// Pattern 3: Global app variable
if (window.application) {
  console.log('✅ Found window.application');
}

// Pattern 4: Check for Vue/React instances
if (window.__VUE__) {
  console.log('✅ Vue app detected');
}

if (window.React) {
  console.log('✅ React detected');  
}

// Pattern 5: Check for custom app names
['agentos', 'agentOS', 'AgentOS', 'main', 'MainApp'].forEach(name => {
  if (window[name]) {
    console.log(`✅ Found window.${name}:`, window[name]);
  }
});

// Pattern 6: Look for results/metadata functions
console.log('\n🔍 LOOKING FOR METADATA FUNCTIONS:');
Object.keys(window).forEach(key => {
  if (typeof window[key] === 'object' && window[key] && window[key].toggleMetadataDetails) {
    console.log(`✅ Found toggleMetadataDetails in window.${key}`);
  }
});

// Pattern 7: Look for DOM elements with data
console.log('\n📋 DOM INSPECTION:');
const resultsEl = document.querySelector('#stepResults') || document.querySelector('.results') || document.querySelector('[data-step="results"]');
if (resultsEl) {
  console.log('✅ Found results element:', resultsEl);
  console.log('  Data attributes:', resultsEl.dataset);
}

// Pattern 8: Test direct metadata trigger
console.log('\n🧪 TESTING DIRECT METADATA TRIGGER:');
const infoBtn = document.getElementById('infoFloatBtn');
if (infoBtn) {
  console.log('✅ Found info button:', infoBtn);
  console.log('  Clicking to trigger metadata...');
  
  // Inject test data first
  window.testResults = {
    jobId: '6e446628-53df-46a9-825d-a3aef6e9bb8f',
    analysis_mode: 'viral_ai',
    keywords: ['test', 'metadata'],
    viral_score: 85,
    clips: []
  };
  
  infoBtn.click();
} else {
  console.log('❌ Info button not found');
}

console.log('\n🏁 STRUCTURE DISCOVERY COMPLETE');