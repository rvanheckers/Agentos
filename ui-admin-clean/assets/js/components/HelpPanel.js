/**
 * HelpPanel - Smart Context Panel Component
 * 
 * Responsive help panel component dat contextual help toont.
 * Gebaseerd op Netflix/AWS Console design patterns.
 * 
 * Features:
 * - Responsive panel design (slides in from right)
 * - User level toggle (beginner/intermediate)
 * - Component-specific help content
 * - Mobile-friendly touch interactions
 * - Zero coupling met bestaande views
 * 
 * Created: 4 Augustus 2025
 * Pattern: Smart Context Panel + Component Architecture
 */

import { HelpService } from '../services/HelpService.js';

export class HelpPanel {
  constructor(viewId, options = {}) {
    this.viewId = viewId;
    this.options = {
      position: 'right',           // 'right' | 'left'
      width: '380px',             // Panel width
      showUserLevelToggle: true,  // Show beginner/intermediate toggle
      autoClose: false,           // Auto-close na X seconden
      ...options
    };
    
    this.isVisible = false;
    this.currentComponent = null;
    this.container = null;
    
    // Bind methods
    this.handleLevelChange = this.handleLevelChange.bind(this);
    this.handleKeyboard = this.handleKeyboard.bind(this);
    this.handleClickOutside = this.handleClickOutside.bind(this);
    
    this.init();
  }
  
  /**
   * Initialize help panel
   */
  init() {
    this.createPanel();
    this.attachEventListeners();
    
    console.log(`🆘 HelpPanel initialized for view '${this.viewId}'`);
  }
  
  /**
   * Create help panel DOM structure
   */
  createPanel() {
    // Remove existing panel if any
    this.destroy();
    
    // Create panel container
    this.container = document.createElement('div');
    this.container.className = 'help-panel';
    
    // Create panel content
    this.container.innerHTML = this.getPanelHTML();
    
    // Append to body
    document.body.appendChild(this.container);
    
    // Setup internal event listeners
    this.setupInternalEvents();
  }
  
  /**
   * Get panel HTML structure
   */
  getPanelHTML() {
    const userLevel = HelpService.getUserLevel();
    
    return `
      <div class="help-panel__header">
        <div class="help-panel__title">
          <h2>💡 AgentOS Help</h2>
          <button class="help-panel__close" aria-label="Close help">✕</button>
        </div>
        
        ${this.options.showUserLevelToggle ? `
          <div class="help-panel__level-toggle">
            <span class="help-panel__level-label">Experience Level:</span>
            <div class="help-panel__toggle-buttons">
              <button class="help-panel__level-btn ${userLevel === 'beginner' ? 'active' : ''}" 
                      data-level="beginner">
                👋 Beginner
              </button>
              <button class="help-panel__level-btn ${userLevel === 'intermediate' ? 'active' : ''}" 
                      data-level="intermediate">
                🔧 Intermediate
              </button>
            </div>
          </div>
        ` : ''}
      </div>
      
      <div class="help-panel__content">
        <div class="help-panel__loading">
          <div class="help-panel__spinner"></div>
          <p>Loading help content...</p>
        </div>
      </div>
    `;
  }
  
  /**
   * Setup internal event listeners
   */
  setupInternalEvents() {
    // Close button
    const closeBtn = this.container.querySelector('.help-panel__close');
    closeBtn?.addEventListener('click', () => this.hide());
    
    // User level toggle buttons
    const levelButtons = this.container.querySelectorAll('.help-panel__level-btn');
    levelButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const level = e.target.dataset.level;
        HelpService.setUserLevel(level);
        this.updateLevelButtons(level);
        this.refreshContent();
      });
    });
  }
  
  /**
   * Attach global event listeners
   */
  attachEventListeners() {
    // Listen voor user level changes
    window.addEventListener('helpLevelChanged', this.handleLevelChange);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', this.handleKeyboard);
    
    // Click outside to close (re-enabled)
    document.addEventListener('click', this.handleClickOutside);
  }
  
  /**
   * Handle user level change event
   */
  handleLevelChange(event) {
    const newLevel = event.detail.level;
    this.updateLevelButtons(newLevel);
    if (this.isVisible) {
      this.refreshContent();
    }
  }
  
  /**
   * Handle keyboard shortcuts
   */
  handleKeyboard(event) {
    // ESC to close
    if (event.key === 'Escape' && this.isVisible) {
      this.hide();
    }
    
    // Ctrl+H / Cmd+H to toggle
    if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
      event.preventDefault();
      this.toggle();
    }
  }
  
  /**
   * Handle click outside panel
   */
  handleClickOutside(event) {
    if (this.isVisible && !this.container.contains(event.target)) {
      // Check if click was on help toggle button or any button element
      const helpToggle = document.querySelector('.help-toggle, [data-help-toggle]');
      if (helpToggle && (helpToggle.contains(event.target) || helpToggle === event.target)) {
        return; // Don't close if clicking toggle button
      }
      
      // Also check if clicking on any button (prevent accidental closes)
      if (event.target.closest('button')) {
        return;
      }
      
      // Add delay to prevent immediate close on show
      setTimeout(() => {
        if (this.isVisible) {
          this.hide();
        }
      }, 100);
    }
  }
  
  /**
   * Update level toggle buttons
   */
  updateLevelButtons(activeLevel) {
    const buttons = this.container.querySelectorAll('.help-panel__level-btn');
    buttons.forEach(btn => {
      const isActive = btn.dataset.level === activeLevel;
      btn.classList.toggle('active', isActive);
    });
  }
  
  /**
   * Show help panel
   * @param {string} componentId - Optional specific component help
   */
  show(componentId = null) {
    if (this.isVisible) return;
    
    this.currentComponent = componentId;
    this.isVisible = true;
    
    // Set help service context
    HelpService.setCurrentView(this.viewId);
    
    // Load content
    this.loadContent(componentId);
    
    // Animate in (CSS transition)
    requestAnimationFrame(() => {
      this.container.classList.add('help-panel--visible');
    });
    
    // Add body class voor styling adjustments
    document.body.classList.add('help-panel-open');
    
    console.log(`🆘 HelpPanel shown for ${componentId || 'view-level'} help`);
  }
  
  /**
   * Hide help panel
   */
  hide() {
    if (!this.isVisible) return;
    
    this.isVisible = false;
    
    // Animate out (CSS transition)
    this.container.classList.remove('help-panel--visible');
    
    // Remove body class
    document.body.classList.remove('help-panel-open');
    
    console.log('🆘 HelpPanel hidden');
  }
  
  /**
   * Toggle help panel visibility
   * @param {string} componentId - Optional specific component help
   */
  toggle(componentId = null) {
    if (this.isVisible) {
      this.hide();
    } else {
      this.show(componentId);
    }
  }
  
  /**
   * Load help content
   * @param {string} componentId - Optional specific component
   */
  loadContent(componentId = null) {
    const contentContainer = this.container.querySelector('.help-panel__content');
    
    // Show loading state
    contentContainer.innerHTML = `
      <div class="help-panel__loading">
        <div class="help-panel__spinner"></div>
        <p>Loading help content...</p>
      </div>
    `;
    
    // Get help content
    setTimeout(() => {
      const helpData = HelpService.getContextualHelp(componentId);
      
      if (!helpData) {
        contentContainer.innerHTML = this.getNoHelpHTML();
        return;
      }
      
      contentContainer.innerHTML = this.renderHelpContent(helpData, componentId);
    }, 300); // Small delay for UX
  }
  
  /**
   * Refresh current content
   */
  refreshContent() {
    this.loadContent(this.currentComponent);
  }
  
  /**
   * Render help content HTML
   * @param {object} helpData - Help data object
   * @param {string} componentId - Component identifier
   */
  renderHelpContent(helpData, componentId) {
    const userLevel = HelpService.getUserLevel();
    
    if (componentId && helpData[componentId]) {
      // Specific component help
      return this.renderComponentHelp(helpData[componentId], componentId);
    } else {
      // View-level help (all components)
      return this.renderViewHelp(helpData);
    }
  }
  
  /**
   * Render specific component help
   * @param {object} componentHelp - Component help data
   * @param {string} componentId - Component identifier
   */
  renderComponentHelp(componentHelp, componentId) {
    const userLevel = HelpService.getUserLevel();
    const helpContent = componentHelp[userLevel];
    
    if (!helpContent) {
      return this.getNoHelpHTML(`No ${userLevel} help available for this component.`);
    }
    
    return `
      <div class="help-panel__component-help">
        <h3 class="help-panel__component-title">${helpContent.title}</h3>
        
        <div class="help-panel__practical">
          <h4>💡 What does this do?</h4>
          <p>${helpContent.praktisch}</p>
        </div>
        
        ${helpContent.technisch ? `
          <div class="help-panel__technical">
            <h4>🔧 Technical Details</h4>
            <p><strong>${helpContent.technisch}</strong></p>
          </div>
        ` : ''}
        
        ${helpContent.wat_te_doen ? `
          <div class="help-panel__actions">
            <h4>✅ What can you do?</h4>
            <ul>
              ${helpContent.wat_te_doen.map(action => `<li>${action}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        
        ${helpContent.metrics ? `
          <div class="help-panel__metrics">
            <h4>📊 Performance Metrics</h4>
            <ul>
              ${helpContent.metrics.map(metric => `<li>${metric}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        
        ${helpContent.scenarios ? `
          <div class="help-panel__scenarios">
            <h4>🔍 Veelvoorkomende Situaties</h4>
            ${helpContent.scenarios.map(scenario => `
              <div class="scenario-card">
                <h5>❗ ${scenario.symptoom}</h5>
                <div class="scenario-section">
                  <h6>🔎 Diagnose:</h6>
                  <ul>
                    ${scenario.diagnose.map(item => `<li>${item}</li>`).join('')}
                  </ul>
                </div>
                <div class="scenario-section">
                  <h6>⚡ Acties:</h6>
                  <ul>
                    ${scenario.acties.map(item => `<li>${item}</li>`).join('')}
                  </ul>
                </div>
              </div>
            `).join('')}
          </div>
        ` : ''}
        
        ${helpContent.workflows ? `
          <div class="help-panel__workflows">
            <h4>⚙️ Workflows</h4>
            ${helpContent.workflows.map(workflow => `
              <div class="workflow-card">
                <h5>📋 ${workflow.naam}</h5>
                <ol>
                  ${workflow.stappen.map(stap => `<li>${stap}</li>`).join('')}
                </ol>
              </div>
            `).join('')}
          </div>
        ` : ''}
        
        ${helpContent.use_cases ? `
          <div class="help-panel__use-cases">
            <h4>💡 Praktische Voorbeelden</h4>
            <ul>
              ${helpContent.use_cases.map(useCase => `<li>${useCase}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        
        ${helpContent.diagnostische_tips ? `
          <div class="help-panel__diagnostic-tips">
            <h4>🔍 Diagnostische Tips</h4>
            <ul>
              ${helpContent.diagnostische_tips.map(tip => `<li>${tip}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        
        ${helpContent.diagnostic_workflows ? `
          <div class="help-panel__diagnostic-workflows">
            <h4>🔬 Diagnostische Workflows</h4>
            ${helpContent.diagnostic_workflows.map(workflow => `
              <div class="diagnostic-workflow-card">
                <h5>🎯 ${workflow.scenario}</h5>
                <ol>
                  ${workflow.stappen.map(stap => `<li>${stap}</li>`).join('')}
                </ol>
              </div>
            `).join('')}
          </div>
        ` : ''}
        
        ${helpContent.metrics_interpretation ? `
          <div class="help-panel__metrics-interpretation">
            <h4>📏 Metrics Interpretatie</h4>
            <ul>
              ${helpContent.metrics_interpretation.map(interpretation => `<li>${interpretation}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;
  }
  
  /**
   * Render view-level help (all components)
   * @param {object} helpData - All help data
   */
  renderViewHelp(helpData) {
    const components = Object.keys(helpData);
    const userLevel = HelpService.getUserLevel();
    
    return `
      <div class="help-panel__view-help">
        <div class="help-panel__intro">
          <h3>Service Managers Overview</h3>
          <p>Click any service below voor detailed help, or use the 💡 toggle to switch between experience levels.</p>
        </div>
        
        <div class="help-panel__components-list">
          ${components.map(componentId => {
            const component = helpData[componentId];
            const content = component[userLevel];
            if (!content) return '';
            
            return `
              <div class="help-panel__component-card" data-component="${componentId}">
                <h4 class="help-panel__card-title">${content.title}</h4>
                <p class="help-panel__card-summary">${content.praktisch.substring(0, 120)}...</p>
                <button class="help-panel__card-button" onclick="helpPanel.show('${componentId}')">
                  Show Details →
                </button>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }
  
  /**
   * Get no help available HTML
   * @param {string} message - Custom message
   */
  getNoHelpHTML(message = 'No help content available for this view.') {
    return `
      <div class="help-panel__no-help">
        <div class="help-panel__no-help-icon">❓</div>
        <h3>Help Not Available</h3>
        <p>${message}</p>
        <p>Please check that help content is properly registered voor this view.</p>
      </div>
    `;
  }
  
  /**
   * Destroy help panel
   */
  destroy() {
    // Remove event listeners
    window.removeEventListener('helpLevelChanged', this.handleLevelChange);
    document.removeEventListener('keydown', this.handleKeyboard);
    document.removeEventListener('click', this.handleClickOutside);
    
    // Remove DOM element
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    
    // Remove body class
    document.body.classList.remove('help-panel-open');
    
    console.log('🆘 HelpPanel destroyed');
  }
}

export default HelpPanel;