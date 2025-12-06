/**
 * AnalyticsRenderers Module  
 * Handles all tab content rendering and UI updates for Analytics dashboard
 */

export class AnalyticsRenderers {
  constructor(container, charts, calculations) {
    this.container = container;
    this.charts = charts;
    this.calculations = calculations;
  }

  /**
   * Render Performance Metrics Tab
   */
  renderPerformanceMetricsTab(data) {
    console.log('📊 Rendering Performance Metrics Tab');
    const content = this.container.querySelector('#analyticsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">📊 Performance Metrics</h2>
        <div class="tab-filters">
          <select class="filter-select" id="performanceTimeRange">
            <option value="1h">Last Hour</option>
            <option value="24h" selected>Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
      </div>
      
      <div class="analytics-grid analytics-grid--2x2">
        <!-- Response Time Trends -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">⚡ Response Time Trends</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="responseTimeChart"></canvas>
          </div>
        </div>
        
        <!-- SLA Compliance -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🎯 SLA Compliance</h3>
            <div class="analytics-card__subtitle">Target: 99.5%</div>
          </div>
          <div class="analytics-card__content">
            <canvas id="slaComplianceChart"></canvas>
          </div>
        </div>
        
        <!-- Throughput Analysis -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📈 Throughput Analysis</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="throughputChart"></canvas>
          </div>
        </div>
        
        <!-- Performance Heatmap -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🔥 Performance Heatmap</h3>
          </div>
          <div class="analytics-card__content">
            <div id="performanceHeatmap" class="heatmap-container">
              ${this.renderPerformanceHeatmap(data)}
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Render charts after DOM is ready
    setTimeout(() => {
      this.charts.renderResponseTimeChart(data);
      this.charts.renderSLAComplianceChart(data);
      this.charts.renderThroughputChart(data);
    }, 100);
  }

  /**
   * Render Usage Statistics Tab
   */
  renderUsageStatisticsTab(data) {
    console.log('📈 Rendering Usage Statistics Tab');
    const content = this.container.querySelector('#analyticsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">📈 Usage Statistics</h2>
        <div class="tab-filters">
          <select class="filter-select" id="usageUserSegment">
            <option value="all" selected>All Users</option>
            <option value="premium">Premium Users</option>
            <option value="free">Free Users</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
      </div>
      
      <div class="analytics-grid analytics-grid--2x2">
        <!-- Daily Active Jobs -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📊 Daily Active Jobs</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="dailyJobsChart"></canvas>
          </div>
        </div>
        
        <!-- User Activity -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">👥 User Activity</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="userActivityChart"></canvas>
          </div>
        </div>
        
        <!-- Popular Job Types -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🎭 Popular Job Types</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="jobTypesChart"></canvas>
          </div>
        </div>
        
        <!-- Peak Hours Analysis -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🕐 Peak Hours Analysis</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="peakHoursChart"></canvas>
          </div>
        </div>
      </div>
    `;
    
    setTimeout(() => {
      this.charts.renderDailyJobsChart(data);
      this.charts.renderUserActivityChart(data);
      this.charts.renderJobTypesChart(data);
      this.charts.renderPeakHoursChart(data);
    }, 100);
  }

  /**
   * Render Error Trends Tab
   */
  renderErrorTrendsTab(data) {
    console.log('📉 Rendering Error Trends Tab');
    const content = this.container.querySelector('#analyticsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">📉 Error Trends</h2>
        <div class="tab-filters">
          <select class="filter-select" id="errorSeverity">
            <option value="all" selected>All Severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </div>
      </div>
      
      <div class="analytics-grid analytics-grid--2x2">
        <!-- Error Rate Over Time -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📈 Error Rate Over Time</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="errorRateChart"></canvas>
          </div>
        </div>
        
        <!-- Error Types Breakdown -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🔍 Error Types Breakdown</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="errorTypesChart"></canvas>
          </div>
        </div>
        
        <!-- MTTR Trends -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">⏱️ MTTR Trends</h3>
            <div class="analytics-card__subtitle">Mean Time To Recovery</div>
          </div>
          <div class="analytics-card__content">
            <canvas id="mttrChart"></canvas>
          </div>
        </div>
        
        <!-- Failure Root Causes -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🔧 Failure Root Causes</h3>
          </div>
          <div class="analytics-card__content">
            <div id="rootCausesChart" class="root-causes-container">
              ${this.renderRootCausesChart(data)}
            </div>
          </div>
        </div>
      </div>
    `;
    
    setTimeout(() => {
      this.charts.renderErrorRateChart(data);
      this.charts.renderErrorTypesChart(data);
      this.charts.renderMTTRChart(data);
    }, 100);
  }

  /**
   * Render Capacity Planning Tab
   */
  renderCapacityPlanningTab(data) {
    console.log('🔮 Rendering Capacity Planning Tab');
    const content = this.container.querySelector('#analyticsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">🔮 Capacity Planning</h2>
        <div class="tab-filters">
          <select class="filter-select" id="capacityProjection">
            <option value="1w">1 Week</option>
            <option value="1m" selected>1 Month</option>
            <option value="3m">3 Months</option>
            <option value="6m">6 Months</option>
          </select>
        </div>
      </div>
      
      <div class="analytics-grid analytics-grid--2x2">
        <!-- Resource Utilization -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">💻 Resource Utilization</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="resourceUtilChart"></canvas>
          </div>
        </div>
        
        <!-- Queue Depth Trends -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📦 Queue Depth Trends</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="queueDepthChart"></canvas>
          </div>
        </div>
        
        <!-- Worker Load Distribution -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">⚙️ Worker Load Distribution</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="workerLoadChart"></canvas>
          </div>
        </div>
        
        <!-- Forecasting -->
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📊 Load Forecasting</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="forecastingChart"></canvas>
          </div>
        </div>
      </div>
      
      <!-- Capacity Metrics Detail -->
      <div class="analytics-card analytics-card--full">
        <div class="analytics-card__header">
          <h3 class="analytics-card__title">📋 Capacity Metrics Detail</h3>
        </div>
        <div class="analytics-card__content">
          ${this.renderCapacityMetrics(data)}
        </div>
      </div>
    `;
    
    setTimeout(() => {
      this.charts.renderResourceUtilChart(data);
      this.charts.renderQueueDepthChart(data);
      this.charts.renderWorkerLoadChart(data);
      this.charts.renderForecastingChart(data);
    }, 100);
  }

  /**
   * Update KPIs based on current tab
   */
  updateKPIs(tab, data) {
    const kpiContainer = this.container.querySelector('#analyticsKPIs');
    if (!kpiContainer) return;
    
    let kpis = [];
    
    switch(tab) {
      case 'performance':
        kpis = this.calculations.getPerformanceKPIs(data);
        break;
      case 'usage':
        kpis = this.calculations.getUsageKPIs(data);
        break;
      case 'errors':
        kpis = this.calculations.getErrorKPIs(data);
        break;
      case 'capacity':
        kpis = this.calculations.getCapacityKPIs(data);
        break;
      default:
        kpis = this.calculations.getPerformanceKPIs(data);
    }
    
    // Render KPIs to their containers
    kpis.forEach((kpi, index) => {
      const cardElement = kpiContainer.children[index];
      if (cardElement && kpi) {
        this.renderKPICard(cardElement, kpi);
      }
    });
  }

  /**
   * Render individual KPI card
   */
  renderKPICard(element, kpi) {
    element.innerHTML = `
      <div class="kpi-card__icon">${kpi.icon}</div>
      <div class="kpi-card__content">
        <div class="kpi-card__title">${kpi.title}</div>
        <div class="kpi-card__value kpi-card__value--${kpi.status}">
          ${kpi.value}
        </div>
        <div class="kpi-card__meta">
          <span class="kpi-card__target">Target: ${kpi.target}</span>
          <span class="kpi-card__trend">${kpi.trend}</span>
        </div>
        ${kpi.actions ? `
          <div class="kpi-card__actions">
            ${kpi.actions.map(action => `
              <button class="kpi-action-btn" data-action="${action.action}">
                ${action.label}
              </button>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  /**
   * Render performance heatmap
   */
  renderPerformanceHeatmap(data) {
    const hours = Array.from({length: 24}, (_, i) => i);
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    
    let heatmapHTML = '<div class="heatmap-grid">';
    
    // Header row with hours
    heatmapHTML += '<div class="heatmap-row heatmap-header">';
    heatmapHTML += '<div class="heatmap-cell"></div>';
    hours.forEach(hour => {
      heatmapHTML += `<div class="heatmap-cell">${hour}</div>`;
    });
    heatmapHTML += '</div>';
    
    // Data rows
    days.forEach(day => {
      heatmapHTML += '<div class="heatmap-row">';
      heatmapHTML += `<div class="heatmap-cell heatmap-label">${day}</div>`;
      
      hours.forEach(hour => {
        const intensity = Math.random(); // Replace with actual data
        const className = this.getHeatmapClass(intensity);
        heatmapHTML += `<div class="heatmap-cell heatmap-data ${className}" 
                            data-day="${day}" data-hour="${hour}" 
                            title="${day} ${hour}:00 - ${Math.round(intensity * 100)}%"></div>`;
      });
      
      heatmapHTML += '</div>';
    });
    
    heatmapHTML += '</div>';
    return heatmapHTML;
  }

  /**
   * Get heatmap class based on intensity
   */
  getHeatmapClass(intensity) {
    if (intensity > 0.8) return 'heatmap-high';
    if (intensity > 0.6) return 'heatmap-medium-high';
    if (intensity > 0.4) return 'heatmap-medium';
    if (intensity > 0.2) return 'heatmap-low';
    return 'heatmap-very-low';
  }

  /**
   * Render peak hours analysis
   */
  renderPeakHours(data) {
    const peakHours = data.peak_hours || [
      { hour: '09:00', jobs: 450 },
      { hour: '14:00', jobs: 520 },
      { hour: '16:00', jobs: 480 }
    ];
    
    return `
      <div class="peak-hours-list">
        ${peakHours.map((peak, index) => `
          <div class="peak-hour-item">
            <span class="peak-rank">#${index + 1}</span>
            <span class="peak-time">${peak.hour}</span>
            <span class="peak-volume">${peak.jobs} jobs</span>
            <div class="peak-bar" style="width: ${(peak.jobs / 600) * 100}%"></div>
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Render popular intents list
   */
  renderPopularIntents(data) {
    const intents = data.popular_intents || [
      { name: 'video_processing', count: 450, percentage: 35 },
      { name: 'transcoding', count: 320, percentage: 25 },
      { name: 'thumbnail_generation', count: 260, percentage: 20 }
    ];
    
    return `
      <div class="intents-list">
        ${intents.map(intent => `
          <div class="intent-item">
            <div class="intent-header">
              <span class="intent-name">${intent.name}</span>
              <span class="intent-count">${intent.count}</span>
            </div>
            <div class="intent-progress">
              <div class="intent-progress-bar" style="width: ${intent.percentage}%"></div>
            </div>
            <span class="intent-percentage">${intent.percentage}%</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Render error analysis
   */
  renderErrorAnalysis(data) {
    const errors = data.recent_errors || [];
    
    return `
      <div class="error-analysis">
        <div class="error-summary">
          <div class="error-stat">
            <span class="error-stat-label">Total Errors</span>
            <span class="error-stat-value">${data.job_metrics?.failed || 0}</span>
          </div>
          <div class="error-stat">
            <span class="error-stat-label">Error Rate</span>
            <span class="error-stat-value">${((data.job_metrics?.failed || 0) / Math.max(data.job_metrics?.total || 1, 1) * 100).toFixed(1)}%</span>
          </div>
        </div>
        ${errors.length > 0 ? `
          <div class="recent-errors">
            <h4>Recent Errors</h4>
            ${errors.slice(0, 5).map(error => `
              <div class="error-item">
                <span class="error-time">${error.time}</span>
                <span class="error-type">${error.type}</span>
                <span class="error-message">${error.message}</span>
              </div>
            `).join('')}
          </div>
        ` : '<p class="no-errors">No recent errors</p>'}
      </div>
    `;
  }

  /**
   * Render capacity metrics detail
   */
  renderCapacityMetrics(data) {
    const systemHealth = data.system_health || {};
    const queueStatus = data.queue_status || {};
    
    const metrics = [
      {
        name: 'CPU Usage',
        current: systemHealth.cpu_usage || 0,
        threshold: 80,
        unit: '%',
        icon: '💻'
      },
      {
        name: 'Memory Usage',
        current: systemHealth.memory_usage || 0,
        threshold: 85,
        unit: '%',
        icon: '🧠'
      },
      {
        name: 'Storage Used',
        current: 450,
        threshold: 1000,
        unit: 'GB',
        icon: '💾'
      },
      {
        name: 'Queue Depth',
        current: queueStatus.total_queued || 0,
        threshold: 100,
        unit: 'jobs',
        icon: '📦'
      },
      {
        name: 'Active Workers',
        current: systemHealth.active_workers || 0,
        threshold: systemHealth.total_workers || 10,
        unit: 'workers',
        icon: '⚙️'
      }
    ];
    
    return `
      <div class="capacity-metrics-grid">
        ${metrics.map(metric => {
          const percentage = (metric.current / metric.threshold) * 100;
          const statusClass = this.calculations.getCapacityStatusClass(percentage, metric.threshold);
          const statusIcon = this.calculations.getCapacityStatusIcon(statusClass);
          
          return `
            <div class="capacity-metric capacity-metric--${statusClass}">
              <div class="capacity-metric__header">
                <span class="capacity-metric__icon">${metric.icon}</span>
                <span class="capacity-metric__name">${metric.name}</span>
                <span class="capacity-metric__status">${statusIcon}</span>
              </div>
              <div class="capacity-metric__value">
                ${this.calculations.formatCapacityValue(metric.current, metric.unit)}
                <span class="capacity-metric__threshold">/ ${this.calculations.formatCapacityValue(metric.threshold, metric.unit)}</span>
              </div>
              <div class="capacity-metric__progress">
                <div class="capacity-metric__progress-bar" style="width: ${Math.min(percentage, 100)}%"></div>
              </div>
              <div class="capacity-metric__recommendation">
                ${this.calculations.getCapacityRecommendation(statusClass, metric.name)}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  /**
   * Render root causes chart
   */
  renderRootCausesChart(data) {
    const rootCauses = [
      { cause: 'Network Timeout', count: 45, percentage: 35 },
      { cause: 'Invalid Input', count: 32, percentage: 25 },
      { cause: 'Resource Limit', count: 26, percentage: 20 },
      { cause: 'Processing Error', count: 19, percentage: 15 },
      { cause: 'Other', count: 6, percentage: 5 }
    ];
    
    return `
      <div class="root-causes-chart">
        ${rootCauses.map(cause => `
          <div class="root-cause-item">
            <div class="root-cause-header">
              <span class="root-cause-name">${cause.cause}</span>
              <span class="root-cause-count">${cause.count} errors</span>
            </div>
            <div class="root-cause-bar-container">
              <div class="root-cause-bar" style="width: ${cause.percentage}%">
                <span class="root-cause-percentage">${cause.percentage}%</span>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Render detailed reports section
   */
  renderDetailedReports(data) {
    return `
      <div class="detailed-reports">
        <div class="report-actions">
          <button class="btn btn-primary" id="generateReport">
            <i class="icon-download"></i> Generate Report
          </button>
          <button class="btn btn-secondary" id="scheduleReport">
            <i class="icon-calendar"></i> Schedule Report
          </button>
          <button class="btn btn-secondary" id="exportData">
            <i class="icon-export"></i> Export Data
          </button>
        </div>
        
        <div class="recent-reports">
          <h4>Recent Reports</h4>
          <div class="reports-list">
            <div class="report-item">
              <span class="report-date">2024-01-15</span>
              <span class="report-type">Weekly Performance</span>
              <a href="#" class="report-download">Download</a>
            </div>
            <div class="report-item">
              <span class="report-date">2024-01-08</span>
              <span class="report-type">Monthly Analytics</span>
              <a href="#" class="report-download">Download</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Export performance data
   */
  exportPerformanceData(data) {
    const exportData = {
      timestamp: new Date().toISOString(),
      performance_metrics: {
        sla_compliance: this.calculations.calculateSLACompliance(data.job_metrics?.success_rate || 95),
        avg_response_time: data.performance_metrics?.avg_response_time || 0,
        throughput: data.job_metrics?.total || 0,
        success_rate: data.job_metrics?.success_rate || 0
      },
      job_metrics: data.job_metrics || {},
      system_health: data.system_health || {},
      trends: {
        throughput: this.calculations.calculateThroughputTrend(data.job_metrics || {})
      }
    };
    
    this.downloadAsJSON(exportData, 'performance-metrics.json');
  }

  /**
   * Generate detailed analytics report
   */
  generateDetailedReport(data) {
    const report = {
      metadata: {
        generated_at: new Date().toISOString(),
        report_type: 'comprehensive_analytics',
        period: {
          start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          end: new Date().toISOString()
        }
      },
      summary: {
        overall_health: this.getOverallSystemStatus(data),
        key_metrics: {
          total_jobs: data.job_metrics?.total || 0,
          success_rate: data.job_metrics?.success_rate || 0,
          avg_response_time: data.performance_metrics?.avg_response_time || 0,
          system_load: this.calculations.calculateSystemLoadScore(
            data.system_health || {},
            data.queue_status || {}
          )
        }
      },
      kpis: {
        performance: this.calculations.getPerformanceKPIs(data),
        usage: this.calculations.getUsageKPIs(data),
        errors: this.calculations.getErrorKPIs(data),
        capacity: this.calculations.getCapacityKPIs(data)
      },
      findings: this.calculations.generateKeyFindings(data),
      recommendations: this.calculations.generateRecommendations(data),
      raw_data: data
    };
    
    this.downloadAsJSON(report, `analytics-report-${Date.now()}.json`);
    return report;
  }

  /**
   * Export all analytics data
   */
  exportAllData(data) {
    const exportPackage = {
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      data_sources: this.getAvailableDataSources(data),
      completeness: this.calculations.calculateDataCompleteness(data),
      full_data: data,
      calculated_metrics: {
        enterprise_kpis: this.calculations.calculateEnterpriseKPIs(data),
        performance_kpis: this.calculations.getPerformanceKPIs(data),
        usage_kpis: this.calculations.getUsageKPIs(data),
        error_kpis: this.calculations.getErrorKPIs(data),
        capacity_kpis: this.calculations.getCapacityKPIs(data)
      }
    };
    
    this.downloadAsJSON(exportPackage, `analytics-export-${Date.now()}.json`);
  }

  /**
   * Download data as JSON file
   */
  downloadAsJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json'
    });
    
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    
    document.body.appendChild(link);
    link.click();
    
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    this.showToast(`Report downloaded: ${filename}`, 'success');
  }

  /**
   * Get overall system status
   */
  getOverallSystemStatus(data) {
    const healthScore = this.calculations.calculateSystemLoadScore(
      data.system_health || {},
      data.queue_status || {}
    );
    
    if (healthScore >= 80) return 'healthy';
    if (healthScore >= 60) return 'moderate';
    return 'critical';
  }

  /**
   * Get available data sources
   */
  getAvailableDataSources(data) {
    return Object.keys(data).filter(key => 
      data[key] !== null && data[key] !== undefined
    );
  }

  /**
   * Show error message
   */
  showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'analytics-error';
    errorDiv.textContent = message;
    this.container.prepend(errorDiv);
    
    setTimeout(() => errorDiv.remove(), 5000);
  }

  /**
   * Show toast notification
   */
  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
      <div class="toast__content">
        <span class="toast__message">${message}</span>
        <button class="toast__close">&times;</button>
      </div>
    `;
    
    document.body.appendChild(toast);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
      toast.classList.add('toast--fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 5000);
    
    // Manual dismiss
    toast.querySelector('.toast__close').addEventListener('click', () => {
      toast.remove();
    });
  }
}