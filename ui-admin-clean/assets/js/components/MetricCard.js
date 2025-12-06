/**
 * Metric Card Component
 * Reusable metric display component
 */

export class MetricCard {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      title: 'Metric',
      value: '0',
      description: '',
      status: 'good',
      icon: '📊',
      helpId: null,  // Help context ID for help system
      ...options
    };
    
    this.render();
  }

  render() {
    this.container.className = `metric-card metric-card--${this.options.status}`;
    
    // Add help icon if helpId is provided
    const helpIcon = this.options.helpId 
      ? `<button class="help-icon" data-service="${this.options.helpId}" title="Help voor ${this.options.title}">❓</button>`
      : '';
    
    this.container.innerHTML = `
      <div class="metric-card__header">
        <div class="metric-card__title">
          ${this.options.title}
          ${helpIcon}
        </div>
        <div class="metric-card__status metric-card__status--${this.options.status}">
          ${this.options.status}
        </div>
      </div>
      <div class="metric-card__value">${this.options.value}</div>
      <div class="metric-card__description">${this.options.description}</div>
    `;
  }

  update(newOptions) {
    this.options = { ...this.options, ...newOptions };
    this.render();
  }

  setValue(value) {
    this.update({ value });
  }

  setStatus(status) {
    this.update({ status });
  }
}