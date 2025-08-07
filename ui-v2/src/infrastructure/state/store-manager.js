/**
 * Store Manager
 * Central store management for the application
 * Provides unified access to all stores and cross-store actions
 */

import { AppStore } from './app-store.js';
import { VideoStore } from './video-store.js';
import { UIStore } from './ui-store.js';

export class StoreManager {
  constructor() {
    // Initialize all stores
    this.appStore = new AppStore();
    this.videoStore = new VideoStore();
    this.uiStore = new UIStore();
    
    // Cross-store listeners for synchronized state
    this.setupCrossStoreSync();
    
    // Make stores available globally for debugging
    if (typeof window !== 'undefined') {
      window.stores = {
        app: this.appStore,
        video: this.videoStore,
        ui: this.uiStore
      };
    }
  }

  /**
   * Setup cross-store synchronization
   */
  setupCrossStoreSync() {
    // Sync language between UI store and app store
    this.uiStore.addListener((newState, prevState) => {
      if (newState.language !== prevState.language) {
        this.appStore.setLanguage(newState.language);
      }
    });

    // Sync current step between UI store and app store
    this.uiStore.addListener((newState, prevState) => {
      if (newState.currentStep !== prevState.currentStep) {
        this.appStore.setCurrentStep(newState.currentStep);
      }
    });

    // Sync selected intent between UI store and app store
    this.uiStore.addListener((newState, prevState) => {
      if (newState.selectedIntent !== prevState.selectedIntent) {
        this.appStore.setSelectedIntent(newState.selectedIntent);
      }
    });

    // Show loading when video processing starts
    this.videoStore.addListener((newState, prevState) => {
      if (newState.isProcessing !== prevState.isProcessing) {
        if (newState.isProcessing) {
          this.uiStore.startLoading(newState.processingStage || 'Video verwerken...');
        } else {
          this.uiStore.stopLoading();
        }
      }
    });

    // Update processing progress
    this.videoStore.addListener((newState, prevState) => {
      if (newState.processingProgress !== prevState.processingProgress) {
        const message = `${this.videoStore.getProcessingStageDisplay()} (${newState.processingProgress}%)`;
        this.uiStore.setLoading(newState.isProcessing, message);
      }
    });

    // Show success notification when processing completes
    this.videoStore.addListener((newState, prevState) => {
      if (!newState.isProcessing && prevState.isProcessing && newState.clips.length > 0) {
        this.uiStore.showSuccess(
          `Video succesvol verwerkt! ${newState.clips.length} clips gegenereerd.`,
          { duration: 3000 }
        );
      }
    });

    // Show error notification when processing fails
    this.videoStore.addListener((newState, prevState) => {
      if (newState.uploadError && newState.uploadError !== prevState.uploadError) {
        this.uiStore.showError(newState.uploadError);
      }
    });
  }

  /**
   * Get all store states
   */
  getAllStates() {
    return {
      app: this.appStore.getState(),
      video: this.videoStore.getState(),
      ui: this.uiStore.getState()
    };
  }

  /**
   * Reset all stores
   */
  resetAll() {
    this.videoStore.reset();
    this.uiStore.reset();
    this.appStore.reset();
  }

  /**
   * Create a subscription to all stores
   */
  subscribe(callback) {
    const unsubscribeFunctions = [
      this.appStore.addListener(() => callback(this.getAllStates())),
      this.videoStore.addListener(() => callback(this.getAllStates())),
      this.uiStore.addListener(() => callback(this.getAllStates()))
    ];

    // Return combined unsubscribe function
    return () => {
      unsubscribeFunctions.forEach(unsub => unsub());
    };
  }

  // Convenience getters for stores
  get app() { return this.appStore; }
  get video() { return this.videoStore; }
  get ui() { return this.uiStore; }

  // High-level actions that span multiple stores

  /**
   * Handle intent selection
   */
  selectIntent(intent) {
    this.ui.setSelectedIntent(intent);
    this.ui.navigateToStep('upload');
    
    // Track analytics
    console.log(`Intent selected: ${intent}`);
  }

  /**
   * Start video upload
   */
  startVideoUpload(videoInput, method = 'file') {
    // videoInput can be a File object (legacy) or videoInput object with filePath
    // For file uploads, it should be the videoInput object from upload-zone.js
    this.video.setCurrentVideo(videoInput);
    this.ui.navigateToStep('processing');
    
    // Set processing state - the ProcessingPanel component will handle the actual processing
    this.video.setIsProcessing(true);
    
    // Processing will be started by ProcessingPanel component via ProcessingService
    console.log('📋 Video upload completed, processing will start via ProcessingPanel');
    console.log('🎬 Video input object:', videoInput);
  }

  /**
   * Handle navigation back to intent
   */
  backToIntent() {
    this.ui.navigateToStep('intent');
    this.video.reset();
  }

  /**
   * Complete processing and show results
   */
  showResults(results) {
    this.video.setProcessingResults(results);
    this.ui.navigateToStep('results');
  }

  /**
   * Handle language change
   */
  changeLanguage(language) {
    this.ui.setLanguage(language);
    
    // Trigger i18n update if available
    if (window.setLocale) {
      window.setLocale(language);
    }
    
    // Update i18n system if available
    if (window.i18n && window.i18n.setLocale) {
      window.i18n.setLocale(language);
    }
  }

  /**
   * Old simulateProcessing method removed - now handled by ProcessingService
   * Processing is now managed by ProcessingPanel component via ProcessingService
   * This provides better UX with 8+ second minimum processing time and detailed step feedback
   */

  /**
   * Debug method to log all states
   */
  logStates() {
    console.group('🏪 Store States');
    console.log('App Store:', this.appStore.getState());
    console.log('Video Store:', this.videoStore.getState());
    console.log('UI Store:', this.uiStore.getState());
    console.groupEnd();
  }
}

// Create singleton instance
export const storeManager = new StoreManager();

export default storeManager;