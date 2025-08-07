/**
 * UI State Management
 * Handles all user interface state: navigation, modals, notifications, preferences
 */

export class UIStore {
  constructor() {
    this.state = {
      // Navigation
      currentStep: 'intent',
      selectedIntent: null,
      navigationHistory: [],
      
      // Modals & Overlays
      activeModal: null,
      helpModalOpen: false,
      settingsModalOpen: false,
      
      // Notifications
      notifications: [],
      notificationQueue: [],
      
      // User preferences
      language: 'nl',
      theme: 'light',
      autoplay: true,
      showAdvancedOptions: false,
      
      // UI State
      isLoading: false,
      loadingMessage: '',
      sidebarOpen: false,
      
      // Form state
      uploadZoneActive: false,
      dragOverActive: false,
      
      // Error state
      lastError: null,
      errorContext: null,
      
      // Feature flags
      features: {
        betaFeatures: false,
        advancedMode: false,
        debugMode: false
      }
    };
    
    this.listeners = new Set();
    this.loadFromStorage();
  }

  /**
   * Get current state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Update state with partial updates
   */
  setState(updates) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };
    this.saveToStorage();
    this.notifyListeners(prevState, this.state);
  }

  // Navigation Methods
  
  /**
   * Navigate to a specific step
   */
  navigateToStep(step) {
    const currentStep = this.state.currentStep;
    
    // If navigating to intent from results/processing, trigger full reset
    if (step === 'intent' && (currentStep === 'results' || currentStep === 'processing')) {
      this.resetForNewSession();
      return;
    }
    
    // Add to history if it's a real navigation
    if (currentStep !== step) {
      const history = [...this.state.navigationHistory, currentStep];
      this.setState({
        currentStep: step,
        navigationHistory: history.slice(-10) // Keep last 10 steps
      });
    }
  }
  
  /**
   * Reset for new session - clears all state for fresh start
   */
  resetForNewSession() {
    console.log('🔄 Resetting all stores for new session');
    
    // Reset this store first
    this.setState({
      currentStep: 'intent',
      selectedIntent: null,
      navigationHistory: [],
      activeModal: null,
      helpModalOpen: false,
      settingsModalOpen: false,
      notifications: [],
      isLoading: false,
      loadingMessage: '',
      uploadZoneActive: false,
      dragOverActive: false,
      lastError: null,
      errorContext: null
    });
    
    // Also reset video store if store manager is available
    if (typeof window !== 'undefined' && window.stores && window.stores.video) {
      window.stores.video.reset();
    }
  }

  /**
   * Go back to previous step
   */
  navigateBack() {
    const history = [...this.state.navigationHistory];
    if (history.length > 0) {
      const previousStep = history.pop();
      this.setState({
        currentStep: previousStep,
        navigationHistory: history
      });
      return previousStep;
    }
    return null;
  }

  /**
   * Set selected intent
   */
  setSelectedIntent(intent) {
    this.setState({ selectedIntent: intent });
  }

  // Modal Methods

  /**
   * Open modal
   */
  openModal(modalType, data = null) {
    this.setState({
      activeModal: modalType,
      [`${modalType}ModalOpen`]: true,
      modalData: data
    });
  }

  /**
   * Close modal
   */
  closeModal(modalType = null) {
    const updates = { activeModal: null };
    
    if (modalType) {
      updates[`${modalType}ModalOpen`] = false;
    } else {
      // Close all modals
      updates.helpModalOpen = false;
      updates.settingsModalOpen = false;
    }
    
    this.setState(updates);
  }

  // Notification Methods

  /**
   * Add notification
   */
  addNotification(notification) {
    const id = Date.now() + Math.random();
    const newNotification = {
      id,
      type: 'info',
      autoClose: true,
      duration: 5000,
      ...notification,
      timestamp: Date.now()
    };
    
    const notifications = [...this.state.notifications, newNotification];
    this.setState({ notifications });
    
    // Auto remove if enabled
    if (newNotification.autoClose) {
      setTimeout(() => {
        this.removeNotification(id);
      }, newNotification.duration);
    }
    
    return id;
  }

  /**
   * Remove notification
   */
  removeNotification(id) {
    const notifications = this.state.notifications.filter(n => n.id !== id);
    this.setState({ notifications });
  }

  /**
   * Clear all notifications
   */
  clearNotifications() {
    this.setState({ notifications: [] });
  }

  /**
   * Show success notification
   */
  showSuccess(message, options = {}) {
    return this.addNotification({
      type: 'success',
      message,
      ...options
    });
  }

  /**
   * Show error notification
   */
  showError(message, options = {}) {
    return this.addNotification({
      type: 'error',
      message,
      autoClose: false,
      ...options
    });
  }

  /**
   * Show warning notification
   */
  showWarning(message, options = {}) {
    return this.addNotification({
      type: 'warning',
      message,
      ...options
    });
  }

  /**
   * Show info notification
   */
  showInfo(message, options = {}) {
    return this.addNotification({
      type: 'info',
      message,
      ...options
    });
  }

  // Loading Methods

  /**
   * Set loading state
   */
  setLoading(isLoading, message = '') {
    this.setState({
      isLoading,
      loadingMessage: message
    });
  }

  /**
   * Start loading with message
   */
  startLoading(message = 'Laden...') {
    this.setLoading(true, message);
  }

  /**
   * Stop loading
   */
  stopLoading() {
    this.setLoading(false, '');
  }

  // Preference Methods

  /**
   * Set language
   */
  setLanguage(language) {
    this.setState({ language });
  }

  /**
   * Set theme
   */
  setTheme(theme) {
    this.setState({ theme });
    document.documentElement.setAttribute('data-theme', theme);
  }

  /**
   * Toggle feature
   */
  toggleFeature(featureName) {
    const features = {
      ...this.state.features,
      [featureName]: !this.state.features[featureName]
    };
    this.setState({ features });
  }

  /**
   * Update preferences
   */
  updatePreferences(preferences) {
    this.setState({ ...preferences });
  }

  // Error Methods

  /**
   * Set error state
   */
  setError(error, context = null) {
    this.setState({
      lastError: error,
      errorContext: context
    });
    
    // Also show as notification
    this.showError(error.message || error, { context });
  }

  /**
   * Clear error state
   */
  clearError() {
    this.setState({
      lastError: null,
      errorContext: null
    });
  }

  // UI Interaction Methods

  /**
   * Set upload zone state
   */
  setUploadZoneActive(active) {
    this.setState({ uploadZoneActive: active });
  }

  /**
   * Set drag over state
   */
  setDragOverActive(active) {
    this.setState({ dragOverActive: active });
  }

  /**
   * Toggle sidebar
   */
  toggleSidebar() {
    this.setState({ sidebarOpen: !this.state.sidebarOpen });
  }

  // Storage Methods

  /**
   * Load state from localStorage
   */
  loadFromStorage() {
    try {
      const saved = localStorage.getItem('vibecoder-ui-state');
      if (saved) {
        const parsed = JSON.parse(saved);
        
        // Only load persistent preferences
        const persistentKeys = ['language', 'theme', 'autoplay', 'showAdvancedOptions', 'features'];
        persistentKeys.forEach(key => {
          if (parsed[key] !== undefined) {
            this.state[key] = parsed[key];
          }
        });
        
        // Apply theme immediately
        if (this.state.theme) {
          document.documentElement.setAttribute('data-theme', this.state.theme);
        }
      }
    } catch (error) {
      console.warn('Could not load UI state from storage:', error);
    }
  }

  /**
   * Save state to localStorage
   */
  saveToStorage() {
    try {
      // Only save persistent state
      const toSave = {
        language: this.state.language,
        theme: this.state.theme,
        autoplay: this.state.autoplay,
        showAdvancedOptions: this.state.showAdvancedOptions,
        features: this.state.features
      };
      
      localStorage.setItem('vibecoder-ui-state', JSON.stringify(toSave));
    } catch (error) {
      console.warn('Could not save UI state to storage:', error);
    }
  }

  /**
   * Reset UI state (except preferences)
   */
  reset() {
    this.setState({
      currentStep: 'intent',
      selectedIntent: null,
      navigationHistory: [],
      activeModal: null,
      helpModalOpen: false,
      settingsModalOpen: false,
      notifications: [],
      isLoading: false,
      loadingMessage: '',
      uploadZoneActive: false,
      dragOverActive: false,
      lastError: null,
      errorContext: null
    });
  }

  /**
   * Add state listener
   */
  addListener(callback) {
    this.listeners.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(callback);
    };
  }

  /**
   * Notify all listeners of state changes
   */
  notifyListeners(prevState, newState) {
    this.listeners.forEach(callback => {
      try {
        callback(newState, prevState);
      } catch (error) {
        console.error('UIStore listener error:', error);
      }
    });
  }

  /**
   * Get current step display name
   */
  getCurrentStepDisplay() {
    const stepNames = {
      'intent': 'Intentie selectie',
      'upload': 'Video uploaden',
      'processing': 'Video verwerken',
      'results': 'Resultaten bekijken'
    };
    return stepNames[this.state.currentStep] || this.state.currentStep;
  }
}

export default UIStore;