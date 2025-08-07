/**
 * Application State Management
 * Simple state store voor UI v2 applicatie
 */

export class AppStore {
  constructor() {
    this.state = {
      selectedIntent: null,
      currentStep: 'intent',
      processingSession: null,
      uploadedFile: null,
      processingResults: null,
      mcpStatus: {
        available: false,
        connected: false
      },
      user: {
        language: 'nl',
        preferences: {}
      }
    };
    
    this.listeners = new Set();
    this.loadFromStorage();
  }

  /**
   * Krijg huidige state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Update state
   */
  setState(updates) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };
    
    // Persist belangrijke state
    this.saveToStorage();
    
    // Notify listeners
    this.notifyListeners(prevState, this.state);
  }

  /**
   * Set selected intent
   */
  setSelectedIntent(intent) {
    this.setState({ selectedIntent: intent });
  }

  /**
   * Set current step
   */
  setCurrentStep(step) {
    this.setState({ currentStep: step });
  }

  /**
   * Set processing session
   */
  setProcessingSession(session) {
    this.setState({ processingSession: session });
  }

  /**
   * Set uploaded file
   */
  setUploadedFile(file) {
    this.setState({ uploadedFile: file });
  }

  /**
   * Set processing results
   */
  setProcessingResults(results) {
    this.setState({ processingResults: results });
  }

  /**
   * Set MCP status
   */
  setMCPStatus(status) {
    this.setState({ 
      mcpStatus: { ...this.state.mcpStatus, ...status }
    });
  }

  /**
   * Set user language
   */
  setLanguage(language) {
    this.setState({
      user: { ...this.state.user, language }
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
   * Notify all listeners
   */
  notifyListeners(prevState, newState) {
    this.listeners.forEach(callback => {
      try {
        callback(newState, prevState);
      } catch (error) {
        console.error('State listener error:', error);
      }
    });
  }

  /**
   * Reset state
   */
  reset() {
    this.setState({
      selectedIntent: null,
      currentStep: 'intent',
      processingSession: null,
      uploadedFile: null,
      processingResults: null
    });
  }

  /**
   * Load state from localStorage
   */
  loadFromStorage() {
    try {
      const saved = localStorage.getItem('vibecoder-state');
      if (saved) {
        const parsed = JSON.parse(saved);
        
        // Alleen bepaalde keys laden
        const persistentKeys = ['user'];
        persistentKeys.forEach(key => {
          if (parsed[key]) {
            this.state[key] = { ...this.state[key], ...parsed[key] };
          }
        });
      }
    } catch (error) {
      console.warn('Could not load state from storage:', error);
    }
  }

  /**
   * Save state to localStorage
   */
  saveToStorage() {
    try {
      // Alleen bepaalde keys opslaan
      const toSave = {
        user: this.state.user
      };
      
      localStorage.setItem('vibecoder-state', JSON.stringify(toSave));
    } catch (error) {
      console.warn('Could not save state to storage:', error);
    }
  }
}

export default AppStore;