/**
 * HelpService - Registry Pattern voor Contextual Help System
 * 
 * Zero-coupling modulair help system gebaseerd op Netflix/AWS Console patterns.
 * Elke view kan help providers registreren zonder dependencies.
 * 
 * Features:
 * - Registry pattern voor help providers
 * - Auto-context detection
 * - User level support (beginner/intermediate)
 * - Service layer pattern
 * 
 * Created: 4 Augustus 2025
 * Architecture: Smart Context Panel + Registry Pattern
 */

export class HelpService {
  static #providers = new Map();
  static #currentView = null;
  static #userLevel = 'beginner'; // 'beginner' | 'intermediate'
  
  /**
   * Register help provider voor een view
   * @param {string} viewId - View identifier (e.g., 'managers', 'dashboard')
   * @param {object} provider - Help provider object met getHelp() method
   */
  static registerProvider(viewId, provider) {
    if (!viewId || !provider) {
      console.error('HelpService: Invalid viewId or provider');
      return;
    }
    
    if (typeof provider.getHelp !== 'function') {
      console.error('HelpService: Provider must have getHelp() method');
      return;
    }
    
    this.#providers.set(viewId, provider);
    console.log(`🆘 HelpService: Registered provider for view '${viewId}'`);
  }
  
  /**
   * Set current active view voor context awareness
   * @param {string} viewId - Currently active view
   */
  static setCurrentView(viewId) {
    this.#currentView = viewId;
    console.log(`🎯 HelpService: Context set to view '${viewId}'`);
  }
  
  /**
   * Get contextual help voor specific component
   * @param {string} componentId - Component identifier (optional, defaults to view-level help)
   * @param {string} viewId - View identifier (optional, uses current view)
   * @returns {object|null} Help content object
   */
  static getContextualHelp(componentId = null, viewId = null) {
    const targetView = viewId || this.#currentView;
    
    if (!targetView) {
      console.warn('HelpService: No view context set');
      return null;
    }
    
    const provider = this.#providers.get(targetView);
    if (!provider) {
      console.warn(`HelpService: No provider registered for view '${targetView}'`);
      return null;
    }
    
    try {
      const helpData = provider.getHelp(componentId);
      return helpData;
    } catch (error) {
      console.error(`HelpService: Error getting help for '${componentId}':`, error);
      return null;
    }
  }
  
  /**
   * Get all available help topics voor current view
   * @param {string} viewId - View identifier (optional, uses current view)
   * @returns {object|null} All help topics
   */
  static getAllHelp(viewId = null) {
    return this.getContextualHelp(null, viewId);
  }
  
  /**
   * Set user experience level
   * @param {string} level - 'beginner' | 'intermediate'
   */
  static setUserLevel(level) {
    if (!['beginner', 'intermediate'].includes(level)) {
      console.error('HelpService: Invalid user level. Use "beginner" or "intermediate"');
      return;
    }
    
    this.#userLevel = level;
    console.log(`👤 HelpService: User level set to '${level}'`);
    
    // Trigger refresh als help panel open is
    this.#notifyLevelChange();
  }
  
  /**
   * Get current user level
   * @returns {string} Current user level
   */
  static getUserLevel() {
    return this.#userLevel;
  }
  
  /**
   * Check if help is available voor specific component
   * @param {string} componentId - Component identifier
   * @param {string} viewId - View identifier (optional)
   * @returns {boolean} True if help is available
   */
  static hasHelp(componentId, viewId = null) {
    const help = this.getContextualHelp(componentId, viewId);
    return help !== null && help[this.#userLevel] !== undefined;
  }
  
  /**
   * Get registered views (for debugging)
   * @returns {string[]} Array of registered view IDs
   */
  static getRegisteredViews() {
    return Array.from(this.#providers.keys());
  }
  
  /**
   * Clear all providers (for testing)
   */
  static clearProviders() {
    this.#providers.clear();
    this.#currentView = null;
    console.log('🧹 HelpService: All providers cleared');
  }
  
  /**
   * Notify subscribers about user level change
   * @private
   */
  static #notifyLevelChange() {
    const event = new CustomEvent('helpLevelChanged', {
      detail: { level: this.#userLevel }
    });
    window.dispatchEvent(event);
  }
  
  /**
   * Initialize help service met localStorage support
   */
  static initialize() {
    // Load user level from localStorage
    const savedLevel = localStorage.getItem('agentOS_helpLevel');
    if (savedLevel && ['beginner', 'intermediate'].includes(savedLevel)) {
      this.#userLevel = savedLevel;
    }
    
    console.log('🆘 HelpService initialized:', {
      userLevel: this.#userLevel,
      providers: this.getRegisteredViews()
    });
  }
  
  /**
   * Save user level to localStorage
   * @private
   */
  static #saveUserLevel() {
    localStorage.setItem('agentOS_helpLevel', this.#userLevel);
  }
  
  // Override setUserLevel to include persistence
  static setUserLevel(level) {
    if (!['beginner', 'intermediate'].includes(level)) {
      console.error('HelpService: Invalid user level. Use "beginner" or "intermediate"');
      return;
    }
    
    this.#userLevel = level;
    this.#saveUserLevel();
    console.log(`👤 HelpService: User level set to '${level}' (saved)`);
    
    this.#notifyLevelChange();
  }
}

// Auto-initialize when module loads
HelpService.initialize();

// Export voor gebruik in andere modules
export default HelpService;