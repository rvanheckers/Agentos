/**
 * ActionableMetricCard Component - Enhanced MetricCard met Actions & Thresholds
 * 
 * Extends MetricCard met actionable intelligence features:
 * - Threshold-based visual indicators en status changes
 * - Direct action buttons voor operational responses
 * - Smart recommendations based on metric values
 * - Integration met unified ActionService
 * 
 * Used in: Analytics view redesign voor operational intelligence
 * Based on: ANALYTICS_REDESIGN_ASSESSMENT.md actionable metrics pattern
 * 
 * Created: 11 Augustus 2025
 */

import { MetricCard } from './MetricCard.js';

export class ActionableMetricCard extends MetricCard {
  constructor(container, options = {}) {
    const defaultOptions = {
      title: 'Metric',
      value: '0',
      description: '',
      status: 'good',
      icon: '📊',
      helpId: null,
      
      // Actionable features
      actions: [],           // Array of action objects: [{label, action, params, icon, enabled}]
      thresholds: null,      // {warning: value, critical: value}
      currentValue: 0,       // Numeric value voor threshold comparison
      contextualActions: {}, // {warning: [...actions], critical: [...actions]}
      showThresholdBar: false, // Visual threshold indicator
      trend: null,           // Trend data: {direction: 'up'|'down'|'stable', percentage: number}
      recommendations: [],   // Smart recommendations array
      
      // Callbacks
      onActionClick: null,   // Callback when action button clicked
      onThresholdCross: null // Callback when threshold crossed
    };
    
    super(container, { ...defaultOptions, ...options });
    
    this.actionService = window.actionService || null;
    this.setupEventListeners();
    this.evaluateThresholds();
  }

  render() {
    // Determine status based on thresholds if configured
    if (this.options.thresholds && typeof this.options.currentValue === 'number') {
      this.options.status = this.getThresholdStatus(this.options.currentValue);
    }
    
    this.container.className = `metric-card metric-card--actionable metric-card--${this.options.status}`;
    
    // Help icon
    const helpIcon = this.options.helpId 
      ? `<button class="help-icon" data-service="${this.options.helpId}" title="Help voor ${this.options.title}">❓</button>`
      : '';
    
    // Trend indicator
    const trendIndicator = this.options.trend 
      ? this.renderTrendIndicator()
      : '';
    
    // Threshold bar
    const thresholdBar = this.options.showThresholdBar && this.options.thresholds
      ? this.renderThresholdBar()
      : '';
    
    // Actions section
    const actionsSection = this.options.actions.length > 0 || this.hasContextualActions()
      ? this.renderActionsSection()
      : '';
    
    // Recommendations
    const recommendationsSection = this.options.recommendations.length > 0
      ? this.renderRecommendationsSection()
      : '';

    this.container.innerHTML = `
      <div class="metric-card__header">
        <div class="metric-card__title-row">
          <div class="metric-card__title">
            ${this.options.icon} ${this.options.title}
            ${helpIcon}
          </div>
          <div class="metric-card__status metric-card__status--${this.options.status}">
            ${this.getStatusLabel()}
          </div>
        </div>
        <div class="metric-card__value-row">
          <div class="metric-card__value">${this.options.value}</div>
          ${trendIndicator}
        </div>
      </div>
      
      <div class="metric-card__content">
        <div class="metric-card__description">${this.options.description}</div>
        ${thresholdBar}
        ${recommendationsSection}
      </div>
      
      ${actionsSection}
    `;
    
    // Re-setup event listeners after render
    this.setupEventListeners();
  }

  renderTrendIndicator() {
    const { direction, percentage } = this.options.trend;
    const trendIcon = {
      up: '↗️',
      down: '↘️', 
      stable: '→'
    };
    
    const trendColor = {
      up: 'trend--positive',
      down: 'trend--negative',
      stable: 'trend--neutral'
    };
    
    return `
      <div class="metric-card__trend ${trendColor[direction]}">
        ${trendIcon[direction]} ${percentage}%
      </div>
    `;
  }

  renderThresholdBar() {
    const { warning, critical } = this.options.thresholds;
    const currentValue = this.options.currentValue;
    const maxValue = Math.max(critical * 1.2, currentValue * 1.1);
    
    const warningPos = (warning / maxValue) * 100;
    const criticalPos = (critical / maxValue) * 100;
    const currentPos = Math.min((currentValue / maxValue) * 100, 100);
    
    return `
      <div class="metric-card__threshold-bar">
        <div class="threshold-bar__track">
          <div class="threshold-indicator threshold-indicator--warning" style="left: ${warningPos}%" title="Warning: ${warning}"></div>
          <div class="threshold-indicator threshold-indicator--critical" style="left: ${criticalPos}%" title="Critical: ${critical}"></div>
          <div class="threshold-current" style="left: ${currentPos}%" title="Current: ${currentValue}"></div>
        </div>
        <div class="threshold-bar__labels">
          <span class="threshold-label threshold-label--good">Good</span>
          <span class="threshold-label threshold-label--warning">Warning</span>
          <span class="threshold-label threshold-label--critical">Critical</span>
        </div>
      </div>
    `;
  }

  renderActionsSection() {
    const baseActions = this.options.actions || [];
    const contextualActions = this.getContextualActions();
    const allActions = [...baseActions, ...contextualActions];
    
    if (allActions.length === 0) return '';
    
    const actionButtons = allActions
      .filter(action => action.enabled !== false)
      .map(action => this.renderActionButton(action))
      .join('');
    
    return `
      <div class="metric-card__actions">
        <div class="action-buttons">
          ${actionButtons}
        </div>
      </div>
    `;
  }

  renderActionButton(action) {
    const priorityClass = action.priority ? `btn--${action.priority}` : '';
    const iconDisplay = action.icon || '⚡';
    const disabledAttr = action.enabled === false ? 'disabled' : '';
    const confirmAttr = action.confirm ? 'data-confirm="true"' : '';
    
    // Create helpful tooltip text
    const tooltipText = this.getActionTooltip(action);
    
    return `
      <button 
        class="btn btn-sm btn-action ${priorityClass}" 
        data-action="${action.action}"
        data-params="${action.params ? JSON.stringify(action.params).replace(/"/g, '&quot;') : '{}'}"
        ${confirmAttr}
        ${disabledAttr}
        title="${tooltipText}"
      >
        ${iconDisplay} ${action.label}
      </button>
    `;
  }

  getActionTooltip(action) {
    const tooltips = {
      // Analytics actions
      'analytics.drill_down': 'Deep dive into detailed data and statistics',
      'analytics.generate_report': 'Generate comprehensive PDF report with recommendations',
      'analytics.capacity_analysis': 'Analyze capacity trends and scaling needs',
      
      // System actions  
      'system.performance_tune': 'Automatically optimize system performance settings',
      'system.health_check': 'Run comprehensive system health diagnostics',
      'system.emergency_report': 'Generate emergency incident report and alerts',
      'system.auto_optimize': 'Apply automated system optimizations',
      'system.auto_fix': 'Attempt automatic issue resolution',
      'system.fix_timeout': 'Fix API timeout configuration',
      'system.optimize_recovery': 'Improve mean time to recovery processes',
      'system.clear_cache': 'Clear system caches to free memory',
      'system.load_test': 'Perform system load testing',
      
      // Worker actions
      'worker.auto_scale': 'Automatically scale worker pool based on load',
      'worker.optimize': 'Optimize worker distribution and performance',
      'worker.scale_up': 'Add more workers to handle increased load',
      
      // Job actions
      'job.bulk_retry': 'Retry all failed jobs that can be retried',
      
      // Queue actions
      'queue.process_priority': 'Process high-priority jobs first'
    };
    
    return tooltips[action.action] || `Execute ${action.label.toLowerCase()} action`;
  }

  renderRecommendationsSection() {
    const recommendations = this.options.recommendations
      .filter(rec => rec.priority === 'high' || rec.category === 'performance')
      .slice(0, 2); // Show max 2 recommendations
    
    if (recommendations.length === 0) return '';
    
    const recItems = recommendations.map(rec => `
      <div class="recommendation-item">
        <div class="recommendation-content">
          <strong>💡 ${rec.title}:</strong> ${rec.description}
        </div>
        ${rec.actions && rec.actions.length > 0 ? `
          <div class="recommendation-actions">
            ${rec.actions.map(action => `
              <button class="btn btn-xs btn-success" 
                      data-action="${action.action}"
                      data-params="${JSON.stringify(action.params || {}).replace(/"/g, '&quot;')}">
                ${action.label}
              </button>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `).join('');
    
    return `
      <div class="metric-card__recommendations">
        ${recItems}
      </div>
    `;
  }

  getThresholdStatus(value) {
    if (!this.options.thresholds) return this.options.status;
    
    const { warning, critical } = this.options.thresholds;
    
    if (value >= critical) return 'critical';
    if (value >= warning) return 'warning';
    return 'good';
  }

  getStatusLabel() {
    const labels = {
      good: 'Good',
      warning: 'Warning', 
      critical: 'Critical'
    };
    return labels[this.options.status] || this.options.status;
  }

  getContextualActions() {
    if (!this.options.contextualActions || !this.options.thresholds) return [];
    
    const status = this.getThresholdStatus(this.options.currentValue);
    return this.options.contextualActions[status] || [];
  }

  hasContextualActions() {
    const contextualActions = this.getContextualActions();
    return contextualActions.length > 0;
  }

  evaluateThresholds() {
    if (!this.options.thresholds || typeof this.options.currentValue !== 'number') return;
    
    const oldStatus = this.options.status;
    const newStatus = this.getThresholdStatus(this.options.currentValue);
    
    if (oldStatus !== newStatus && this.options.onThresholdCross) {
      this.options.onThresholdCross({
        metric: this.options.title,
        oldStatus,
        newStatus,
        value: this.options.currentValue,
        thresholds: this.options.thresholds
      });
    }
  }

  setupEventListeners() {
    // Defensive check: ensure container exists and has addEventListener
    if (!this.container || typeof this.container.addEventListener !== 'function') {
      console.error('ActionableMetricCard: Invalid container', this.container);
      return;
    }
    
    // Action button clicks
    this.container.addEventListener('click', (e) => {
      const actionButton = e.target.closest('[data-action]');
      if (!actionButton) return;
      
      e.preventDefault();
      this.handleActionClick(actionButton);
    });
  }

  async handleActionClick(button) {
    const action = button.dataset.action;
    const params = button.dataset.params ? JSON.parse(button.dataset.params) : {};
    const needsConfirm = button.dataset.confirm === 'true';
    
    // Confirmation dialog for destructive actions
    if (needsConfirm) {
      const confirmed = confirm(`Are you sure you want to execute: ${action}?`);
      if (!confirmed) return;
    }
    
    // Disable button during action
    button.disabled = true;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Processing...';
    
    try {
      // Custom callback heeft priority
      if (this.options.onActionClick) {
        await this.options.onActionClick({ action, params, button });
        return;
      }
      
      // Use ActionService if available
      if (this.actionService && typeof this.actionService.execute === 'function') {
        const result = await this.actionService.execute(action, params);
        this.showActionResult(result, button);
      } else {
        console.warn('ActionService not available, action not executed:', action);
        this.showActionError('ActionService not available', button);
      }
    } catch (error) {
      console.error('Action execution failed:', error);
      this.showActionError(error.message, button);
    } finally {
      // Re-enable button
      button.disabled = false;
      button.innerHTML = originalText;
    }
  }

  showActionResult(result, button) {
    if (result.success) {
      this.showToast(`✅ Action completed: ${result.message || 'Success'}`, 'success');
    } else {
      this.showToast(`❌ Action failed: ${result.error || 'Unknown error'}`, 'error');
    }
  }

  showActionError(message, button) {
    this.showToast(`❌ ${message}`, 'error');
  }

  showToast(message, type = 'info') {
    // Simple toast notification - could be enhanced with proper toast system
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed; 
      top: 20px; 
      right: 20px; 
      padding: 12px 16px;
      background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
      color: white;
      border-radius: 8px;
      z-index: 9999;
      animation: slideInRight 0.3s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.animation = 'slideOutRight 0.3s ease-in';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Enhanced update method voor actionable features
  update(newOptions) {
    const oldValue = this.options.currentValue;
    super.update(newOptions);
    
    // Re-evaluate thresholds if value changed
    if (oldValue !== this.options.currentValue) {
      this.evaluateThresholds();
    }
  }

  // Set numeric value en update thresholds
  setCurrentValue(value) {
    this.update({ 
      currentValue: value,
      value: typeof value === 'number' ? value.toLocaleString() : value 
    });
  }

  // Add/update actions
  setActions(actions) {
    this.update({ actions });
  }

  // Add/update recommendations
  setRecommendations(recommendations) {
    this.update({ recommendations });
  }

  // Configure thresholds
  setThresholds(thresholds) {
    this.update({ thresholds, showThresholdBar: true });
  }
}