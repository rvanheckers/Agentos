/**
 * Main Application Entry Point
 * VibeCoder AgentOS - UI v2 met MCP Integration
 * 
 * Deze module initialiseert de gehele applicatie en koppelt de UI aan de MCP backend
 */

import { APIClient } from './adapters/api/api-client.js';
import { storeManager } from './infrastructure/state/store-manager.js';
import { NotificationService } from './shared/services/notification-service.js';
import { UploadZone } from './features/video-upload/components/upload-zone.js';
import { ProcessingPanel } from './features/processing/components/processing-panel.js';
import { ResultsGrid } from './features/results/components/results-grid.js';
// Management components moved to admin interface
import i18n, { initDOMTranslations, setLocale } from './i18n/utils/i18n.js';
import { getLogger } from './shared/services/logger.js';

class VibeCoder {
  constructor() {
    this.logger = getLogger('VibeCoder');
    this.apiClient = new APIClient();
    this.stores = storeManager;
    this.notificationService = new NotificationService();
    
    // Core user components only
    this.uploadZone = null;
    this.processingPanel = null;
    this.resultsGrid = null;
    
    this.init();
  }

  async init() {
    try {
      // 1. Wacht op API Client readiness met timeout
      this.logger.debug('Waiting for API Client initialization...');
      try {
        await Promise.race([
          this.apiClient.waitForReady(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('API Client timeout')), 3000))
        ]);
        this.logger.info('API Client ready voor component integration');
      } catch (error) {
        this.logger.warn('API Client initialization timeout, continuing with fallback mode');
      }
      
      // 2. Initialiseer i18n VERVOLGENS 
      await this.initializeI18n();
      
      // 3. Dan pas DOM setup met volledig geïntegreerde services
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.setupApp());
      } else {
        this.setupApp();
      }
    } catch (error) {
      console.error('Fout bij initialisatie:', error);
      this.notificationService.showError('Fout bij laden van applicatie');
    }
  }

  setupApp() {
    console.log('🚀 DEBUG: setupApp() called - starting component initialization');
    // Initialiseer alle componenten
    this.setupEventListeners();
    this.setupIntentSelection();
    this.setupLanguageSwitcher();
    this.setupHelpSystem();
    
    // Setup clean components
    this.setupComponents();
    
    // Setup store listeners
    this.setupStoreListeners();
    
    // Force DOM translations update als i18n al klaar is
    if (i18n.translations.has('nl')) {
      initDOMTranslations();
      console.log('🔄 DOM translations geforceerd na setup');
    }
    
    // Test MCP connectie
    this.testMCPConnection();
    
    // Clear any previous video processing results
    this.stores.video.reset();
    
    // Ensure we start on the intent step
    this.stores.ui.navigateToStep('intent');
    
    // Load existing clips on startup (without auto-navigation)
    this.loadExistingClips();
    
    console.log('✅ VibeCoder AgentOS UI v2 geladen met Clean Components');
  }

  async initializeI18n() {
    try {
      // Wacht tot i18n de Nederlandse vertalingen heeft geladen
      await i18n.loadLocale('nl');
      
      // Debug: controleer of vertalingen zijn geladen
      console.log('🔍 i18n Debug:', {
        currentLocale: i18n.currentLocale,
        hasTranslations: i18n.translations.has('nl'),
        testTranslation: i18n.t('common.help')
      });
      
      // Update alle DOM elementen met vertalingen
      initDOMTranslations();
      
      console.log('✅ i18n geïnitialiseerd met Nederlandse vertalingen');
    } catch (error) {
      console.warn('⚠️ i18n initialisatie gefaald:', error);
    }
  }


  setupComponents() {
    // Initialize Upload Zone Component with API client dependency injection
    const uploadSection = document.getElementById('stepUpload');
    if (uploadSection) {
      console.log('🔍 MAIN.JS: About to create UploadZone');
      console.log('🔍 MAIN.JS: this.apiClient exists:', !!this.apiClient);
      console.log('🔍 MAIN.JS: this.apiClient.baseUrl:', this.apiClient?.baseUrl);
      
      this.uploadZone = new UploadZone(uploadSection, {
        apiClient: this.apiClient,
        stores: this.stores
      });
      console.log('✅ UploadZone component initialized with API client');
    }
    
    // Initialize Processing Panel Component with API client dependency injection
    const processingSection = document.getElementById('stepProcessing');
    if (processingSection) {
      this.processingPanel = new ProcessingPanel(processingSection, {
        apiClient: this.apiClient,
        stores: this.stores
      });
      console.log('✅ ProcessingPanel component initialized with API client (hybrid async/sync)');
    }
    
    // Initialize Results Grid Component with API client dependency injection
    const resultsSection = document.getElementById('stepResults');
    if (resultsSection) {
      this.resultsGrid = new ResultsGrid(resultsSection, {
        apiClient: this.apiClient,
        stores: this.stores
      });
      console.log('✅ ResultsGrid component initialized with API client');
    }
    
    console.log('✅ Core components initialized - focused user interface');
  }

  // Navigation removed - single focused interface

  setupStoreListeners() {
    // Listen to UI store changes for step navigation
    this.stores.ui.addListener((newState, prevState) => {
      if (newState.currentStep !== prevState.currentStep) {
        this.updateStepVisibility(newState.currentStep);
      }
    });

    // Listen to video store changes for results display
    this.stores.video.addListener((newState, prevState) => {
      if (newState.processingResults && !prevState.processingResults) {
        // Results are now handled by ResultsGrid component via its own store listeners
        console.log('📊 Results available, ResultsGrid will handle display');
      }
    });

    // Debug logging with deduplication
    let lastLoggedState = null;
    this.stores.subscribe((states) => {
      const currentState = {
        currentStep: states.ui.currentStep,
        selectedIntent: states.ui.selectedIntent,
        isProcessing: states.video.isProcessing,
        processingProgress: states.video.processingProgress
      };
      
      // Only log if state actually changed
      const stateString = JSON.stringify(currentState);
      if (stateString !== lastLoggedState) {
        console.log('🏪 Store state changed:', currentState);
        lastLoggedState = stateString;
      }
    });
  }

  setupEventListeners() {
    console.log('🔧 DEBUG: setupEventListeners called');
    
    // Intent selectie
    const intentCards = document.querySelectorAll('.intent-card');
    console.log('🔧 DEBUG: Found intent cards:', intentCards.length);
    
    if (intentCards.length === 0) {
      console.error('❌ DEBUG: No intent cards found! DOM not ready?');
      console.error('❌ DEBUG: Document readyState:', document.readyState);
      console.error('❌ DEBUG: Body innerHTML length:', document.body.innerHTML.length);
      return;
    }
    
    intentCards.forEach((card, index) => {
      console.log(`🔧 DEBUG: Setting up card ${index}:`, card.dataset.intent);
      card.addEventListener('click', (e) => {
        console.log('🔧 DEBUG: Intent card clicked!', card.dataset.intent);
        this.handleIntentSelection(e);
      });
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.handleIntentSelection(e);
        }
      });
    });

    // Navigatie
    document.getElementById('backToIntent')?.addEventListener('click', () => {
      this.stores.backToIntent();
    });

    // Upload handling - now managed by UploadZone component
    // OLD CODE REMOVED: this.setupFileUpload();
    // OLD CODE REMOVED: this.setupUrlUpload();

    // Help modal
    document.getElementById('helpButton')?.addEventListener('click', () => {
      this.showHelpModal();
    });
    
    document.getElementById('closeHelpModal')?.addEventListener('click', () => {
      this.hideHelpModal();
    });
  }

  setupIntentSelection() {
    const intentCards = document.querySelectorAll('.intent-card');
    
    intentCards.forEach(card => {
      card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-2px)';
      });
      
      card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0)';
      });
    });
  }

  handleIntentSelection(event) {
    const card = event.currentTarget;
    const intent = card.dataset.intent;
    
    // Use store manager for intent selection
    this.stores.selectIntent(intent);
    
    // Update UI teksten
    document.getElementById('selectedIntentTitle').textContent = 
      this.getIntentDisplayName(intent);
    document.getElementById('processingIntentTitle').textContent = 
      this.getIntentDisplayName(intent);
    document.getElementById('resultsIntentTitle').textContent = 
      this.getIntentDisplayName(intent);
    
    // Update upload tip gebaseerd op intent
    this.updateUploadTip(intent);
  }

  getIntentDisplayName(intent) {
    const intentMap = {
      'short_clips': 'intent.short_clips.title',
      'key_moments': 'intent.key_moments.title', 
      'smart_summary': 'intent.smart_summary.title'
    };
    const i18nKey = intentMap[intent];
    return i18nKey ? i18n.t(i18nKey) : intent;
  }

  updateUploadTip(intent) {
    const tipKey = `intent.tips.${intent}`;
    const tipText = i18n.t(tipKey) || i18n.t('intent.tips.short_clips');
    
    document.getElementById('uploadTip').textContent = tipText;
  }

  // REMOVED: OLD UPLOAD SETUP METHODS
  // setupFileUpload() and setupUrlUpload() - now handled by UploadZone component
  // The UploadZone component manages all upload-related DOM interactions

  // REMOVED: OLD UPLOAD METHODS - Now handled by UploadZone component
  // - validateFile() → FileValidator service
  // - handleFileUpload() → UploadZone.handleFileUpload()
  // - handleUrlUpload() → UploadZone.handleUrlUpload()
  // See: src/features/video-upload/ for new implementation

  handleProcessingComplete(result) {
    if (result.success) {
      // Results are now handled by ResultsGrid component via store listeners
      this.stores.video.setProcessingResults(result.data);
      this.showStep('results');
    } else {
      this.notificationService.showError(result.error || 'Fout bij verwerken');
      this.showStep('upload');
    }
  }

  /**
   * Expert-level method: Process video with intent using agent configuration
   * This is the main entry point for video processing workflows
   */
  async processVideoWithIntent(videoInput, intent, options = {}) {
    try {
      console.log(`🎯 Starting ${intent} workflow with expert-level agent routing`);
      
      // Update UI state
      this.stores.ui.navigateToStep('processing');
      this.stores.video.setIsProcessing(true);
      this.stores.video.updateProcessingProgress(0);
      
      // Use API client with agent configuration for intelligent routing
      const result = await this.apiClient.processWithIntent(videoInput, intent, {
        ...options,
        ui_context: true,
        progress_callback: (progress) => {
          this.stores.video.setProcessingProgress(progress.percentage || 0);
          this.stores.video.setProcessingStatus(progress.message || 'Processing...');
        }
      });
      
      // Process completed successfully
      this.handleProcessingComplete({
        success: true,
        data: result
      });
      
      return result;
      
    } catch (error) {
      console.error('❌ Video processing workflow failed:', error);
      
      this.stores.video.setIsProcessing(false);
      this.stores.video.updateProcessingProgress(0);
      this.stores.video.setProcessingError(error.message);
      
      this.handleProcessingComplete({
        success: false,
        error: error.message
      });
      
      throw error;
    }
  }

  /**
   * Get available processing intents from agent configuration
   */
  getAvailableIntents() {
    if (!this.apiClient?.agentConfig) {
      console.warn('⚠️ Agent configuration not available yet');
      return ['short_clips', 'key_moments', 'smart_summary']; // fallback
    }
    
    return this.apiClient.getAvailableIntents();
  }

  /**
   * Check if intent workflow is available
   */
  async isIntentAvailable(intent) {
    if (!this.apiClient) {
      return { available: false, reason: 'API client not ready' };
    }
    
    return await this.apiClient.isIntentAvailable(intent);
  }

  // REMOVED: displayResults() and downloadClip() - now handled by ResultsGrid component
  // Results display logic moved to: src/features/results/components/results-grid.js
  // Download logic moved to: src/features/results/services/download-manager.js

  setupLanguageSwitcher() {
    const languageSelect = document.getElementById('languageSelect');
    if (!languageSelect) return;

    // Zet de selector op de huidige taal
    languageSelect.value = i18n.currentLocale || 'nl';

    languageSelect.addEventListener('change', async (e) => {
      console.log(`🔄 Switching to ${e.target.value}...`);
      
      try {
        // Switch i18n locale first
        await i18n.setLocale(e.target.value);
        
        // Update DOM translations
        initDOMTranslations();
        
        // Force update URL placeholder
        this.updateUrlPlaceholder();
        
        // Update intent titles if they're set
        this.updateIntentTitlesForLanguage();
        
        // Use store manager for language change
        this.stores.changeLanguage(e.target.value);
        console.log(`✅ Language switched to ${e.target.value}`);
      } catch (error) {
        console.error(`❌ Failed to switch to ${e.target.value}:`, error);
        this.stores.ui.showError('Fout bij wisselen van taal');
      }
    });
    
    // Set initial placeholder
    this.updateUrlPlaceholder();
  }

  updateUrlPlaceholder() {
    const urlInput = document.getElementById('urlInput');
    if (urlInput) {
      urlInput.placeholder = i18n.t('upload.url_placeholder');
    }
  }

  updateIntentTitlesForLanguage() {
    // Update intent titles if an intent is already selected
    const selectedIntent = this.stores.ui.getState().selectedIntent;
    if (selectedIntent) {
      const displayName = this.getIntentDisplayName(selectedIntent);
      
      // Update all intent title elements
      const selectedIntentTitle = document.getElementById('selectedIntentTitle');
      const processingIntentTitle = document.getElementById('processingIntentTitle');
      const resultsIntentTitle = document.getElementById('resultsIntentTitle');
      
      if (selectedIntentTitle) selectedIntentTitle.textContent = displayName;
      if (processingIntentTitle) processingIntentTitle.textContent = displayName;
      if (resultsIntentTitle) resultsIntentTitle.textContent = displayName;
      
      // Update upload tip
      this.updateUploadTip(selectedIntent);
    }
  }

  setupHelpSystem() {
    // Help content laden
    this.loadHelpContent();
  }

  async loadHelpContent() {
    try {
      const response = await fetch('./docs/help.json');
      if (response.ok) {
        this.helpContent = await response.json();
        console.log('✅ Help content loaded');
      }
    } catch (error) {
      console.warn('Help content niet geladen:', error);
      // Fallback help content
      this.helpContent = {
        nl: { welcome: { title: "Help", description: "Video processor help" } }
      };
    }
  }

  showHelpModal() {
    document.getElementById('helpModal').classList.remove('hidden');
  }

  hideHelpModal() {
    document.getElementById('helpModal').classList.add('hidden');
  }

  showStep(stepName) {
    // Use store for navigation
    this.stores.ui.navigateToStep(stepName);
    
    // Update DOM immediately
    this.updateStepVisibility(stepName);
  }

  updateStepVisibility(stepName) {
    console.log(`🔄 Updating step visibility to: ${stepName}`);
    
    // Verberg alle stappen
    document.querySelectorAll('.step').forEach(step => {
      step.classList.remove('active');
      step.classList.add('hidden');
    });
    
    // Toon gewenste stap
    const targetStep = document.getElementById(`step${stepName.charAt(0).toUpperCase() + stepName.slice(1)}`);
    if (targetStep) {
      targetStep.classList.remove('hidden');
      targetStep.classList.add('active');
      console.log(`✅ Showing step: ${stepName}`);
      
      // CRITICAL FIX: Always scroll to top when showing results step
      if (stepName === 'results') {
        // Multiple scroll attempts to ensure it works regardless of timing
        const forceScrollToTop = () => {
          window.scrollTo({ top: 0, behavior: 'instant' });
          console.log('🔝 Forced scroll to top for results page');
        };
        
        // Immediate scroll
        forceScrollToTop();
        
        // Backup scrolls at different intervals to catch DOM rendering delays
        setTimeout(forceScrollToTop, 50);
        setTimeout(forceScrollToTop, 150);
        setTimeout(forceScrollToTop, 300);
        
        // Extra verification after longer delay
        setTimeout(() => {
          if (window.pageYOffset > 50) {
            console.log('🚨 Scroll position still wrong, forcing final correction');
            forceScrollToTop();
          }
          
        }, 500);
      }
      
      // Special handling for upload step after processing completion
      if (stepName === 'upload') {
        console.log('🔧 Special handling for upload step - ensuring upload zone is functional');
        
        // Give upload zone component time to reset, then force visibility fix
        setTimeout(() => {
          // Force remove hidden class if it's still there
          if (targetStep.classList.contains('hidden')) {
            console.log('🚨 Upload step still hidden after timeout, force fixing...');
            targetStep.classList.remove('hidden');
            targetStep.classList.add('active');
          }
          
          // Trigger upload zone diagnostic and auto-fix
          if (window.uploadZone) {
            console.log('🔧 Running upload zone auto-check after step visibility update');
            window.uploadZone.autoCheck();
          }
        }, 200);
      }
    } else {
      console.error(`❌ Step not found: step${stepName.charAt(0).toUpperCase() + stepName.slice(1)}`);
    }
  }

  async testMCPConnection() {
    try {
      const status = await this.apiClient.getStatus();
      console.log('🔗 MCP Connection Status:', status);
      
      if (status.mcp_available) {
        console.log('✅ MCP Backend verbonden');
        
        // Test agent discovery
        try {
          const agentSummary = this.apiClient.getAgentConfigSummary();
          console.log('🤖 Agent Configuration Summary:', agentSummary);
        } catch (error) {
          console.warn('⚠️ Agent discovery test failed:', error);
        }
      } else {
        console.log('⚠️ MCP Backend not available, using fallback');
      }
    } catch (error) {
      console.warn('MCP connection test failed:', error);
    }
  }

  // Load existing clips from backend (but don't auto-navigate)
  async loadExistingClips() {
    try {
      console.log('🔍 Loading existing clips from backend...');
      const result = await this.apiClient.getExistingClips(10);
      
      if (result.success && result.clips.length > 0) {
        console.log(`✅ Found ${result.clips.length} existing clips`);
        
        // Store clips for later access but don't auto-navigate
        this.existingClips = result.clips;
        
        // Add a button or indicator to show existing clips if needed
        this.addExistingClipsIndicator(result.clips.length);
        
        console.log('✅ Existing clips loaded (available for later access)');
      } else {
        console.log('📭 No existing clips found');
      }
    } catch (error) {
      console.warn('⚠️ Failed to load existing clips:', error);
    }
  }

  // Add indicator for existing clips without disrupting user flow
  addExistingClipsIndicator(clipCount) {
    // Add a small indicator in the header or somewhere non-intrusive
    const header = document.querySelector('.app-header .header-right');
    if (header && clipCount > 0) {
      const indicator = document.createElement('div');
      indicator.className = 'existing-clips-indicator';
      indicator.innerHTML = `
        <button class="btn-secondary" id="showExistingClips" title="Show ${clipCount} existing clips">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 4a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V4z"/>
            <path d="M6 8l2 2 4-4" stroke="white" stroke-width="2" fill="none"/>
          </svg>
          ${clipCount}
        </button>
      `;
      header.appendChild(indicator);
      
      // Add click handler to show existing clips
      document.getElementById('showExistingClips').addEventListener('click', () => {
        this.showExistingClips();
      });
    }
  }

  // Show existing clips when user explicitly requests it
  showExistingClips() {
    if (this.existingClips && this.existingClips.length > 0) {
      const mockResults = {
        clips: this.existingClips,
        analysis: {
          totalDuration: this.existingClips.length * 30,
          confidence: 0.95,
          intent: 'existing_clips'
        },
        output_files: this.existingClips
      };
      
      // Set results in store and navigate
      this.stores.video.setProcessingResults(mockResults);
      this.stores.ui.navigateToStep('results');
      
      console.log('✅ Showing existing clips on user request');
    }
  }


  // Development helper: Simulate processing results for testing
  simulateResults(clipCount = 3) {
    console.log('🎬 Simulating results with', clipCount, 'clips');
    
    const mockClips = [];
    for (let i = 0; i < clipCount; i++) {
      mockClips.push({
        url: `https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_${i + 1}mb.mp4`,
        name: `generated_clip_${i + 1}.mp4`,
        description: `AI heeft dit segment geïdentificeerd als ${['perfect moment', 'hoogtepunt', 'geweldige actie'][i] || 'interessant deel'}`,
        aiScore: (7.5 + Math.random() * 2.5).toFixed(1),
        duration: Math.floor(20 + Math.random() * 40),
        type: ['best_moment', 'emotional_peak', 'action_scene'][i] || 'highlight'
      });
    }

    const mockResults = {
      clips: mockClips,
      analysis: {
        totalDuration: mockClips.reduce((sum, clip) => sum + clip.duration, 0),
        confidence: 0.85 + Math.random() * 0.15,
        intent: this.stores.ui.getState().selectedIntent || 'short_clips'
      }
    };

    // Set results in store (triggers ResultsGrid display)
    this.stores.video.setProcessingResults(mockResults);
    
    // Navigate to results step
    this.showStep('results');
    
    return mockResults;
  }
}

// Initialiseer applicatie
const vibeCoder = new VibeCoder();

// Maak globaal beschikbaar voor debugging
window.vibeCoder = vibeCoder;
window.stores = vibeCoder.stores;
window.i18n = i18n;
window.setLocale = setLocale;

export default vibeCoder;