/**
 * Analytics Dashboard View Controller - Refactored Version
 * Main controller that orchestrates analytics modules
 */

import { SmartFilter } from '../components/SmartFilter.js';
import { getFilterPresets, getFilterTypes } from '../config/filterPresets.js';
import { getCentralDataService } from '../services/central-data-service.js';
import { ActionableMetricCard } from '../components/ActionableMetricCard.js';
import { AnalyticsHelpProvider } from '../help-providers/AnalyticsHelpProvider.js';

// Import new modular components
import { AnalyticsCharts } from '../modules/analytics/AnalyticsCharts.js';
import { AnalyticsCalculations } from '../modules/analytics/AnalyticsCalculations.js';
import { AnalyticsRenderers } from '../modules/analytics/AnalyticsRenderers.js';

export class Analytics {
  constructor(apiClient, container) {
    this.apiClient = apiClient;
    this.container = container;
    this.centralDataService = getCentralDataService(apiClient);
    this.subscriptionId = null;
    this.smartFilter = null;
    this.analyticsData = {};
    this.currentFilter = {};
    this.metricCards = new Map();
    this.actionService = null;
    this.helpProvider = AnalyticsHelpProvider;
    this.currentTab = 'performance';
    this.currentTimeframe = '24h';
    
    // Initialize modular components
    this.charts = new AnalyticsCharts();
    this.calculations = new AnalyticsCalculations();
    this.renderers = new AnalyticsRenderers(container, this.charts, this.calculations);
  }

  async init() {
    // Initialize ActionService for actionable metrics
    await this.initializeActionService();
    
    this.render();
    this.setupSmartFilter();
    this.setupEventListeners();
    
    // Initialize actionable metrics after DOM is ready
    setTimeout(() => {
      this.initializeActionableMetrics();
    }, 100);
    
    // Subscribe to central data service
    this.subscriptionId = this.centralDataService.subscribe('Analytics', async (data) => {
      await this.updateAnalytics(data);
    });
    
    // Start central service if not running
    if (!this.centralDataService.getStatus().isRunning) {
      this.centralDataService.start();
    } else {
      // If service is already running, get initial data immediately
      setTimeout(async () => {
        const data = this.centralDataService.getCurrentData();
        if (data) {
          await this.updateAnalytics(data);
        }
      }, 200);
    }
    
    // Make analytics instance globally available for help system
    if (typeof window !== 'undefined') {
      window.analytics = this;
    }

    // Register analytics help provider
    this.registerHelpProvider();
  }

  render() {
    this.container.innerHTML = `
      <div class="analytics-view">
        <div class="page-header">
          <h1 class="page-header__title">
            <span class="page-header__icon">📊</span>
            Processing Analytics
          </h1>
          <p class="page-header__description">
            Comprehensive performance metrics and insights for video processing workflows
          </p>
        </div>

        <!-- Actionable Analytics KPIs -->
        <div class="analytics-kpis" id="analyticsKPIs">
          <div class="kpi-card kpi-card--actionable" id="slaComplianceCard"></div>
          <div class="kpi-card kpi-card--actionable" id="responseTimeCard"></div>
          <div class="kpi-card kpi-card--actionable" id="dailyVolumeCard"></div>
          <div class="kpi-card kpi-card--actionable" id="systemHealthCard"></div>
        </div>

        <!-- Smart Filter Component -->
        <div id="smartFilterContainer"></div>

        <!-- Analytics Tabs Content - Dynamic Content Based on Filter -->
        <div class="analytics-content" id="analyticsContent">
          <!-- Content will be dynamically rendered based on selected tab -->
        </div>

        <!-- Detailed Reports Section -->
        <div class="analytics-reports">
          <div class="analytics-card analytics-card--full">
            <div class="analytics-card__header">
              <h3 class="analytics-card__title">📋 Detailed Performance Reports</h3>
              <div class="analytics-card__actions">
                <button class="btn btn-sm btn-outline" id="generateReport">
                  <i class="icon-download"></i> Generate Report
                </button>
                <button class="btn btn-sm btn-outline" id="exportData">
                  <i class="icon-export"></i> Export Data
                </button>
              </div>
            </div>
            <div class="analytics-card__content" id="detailedReports">
              <!-- Reports will be rendered here -->
            </div>
          </div>
        </div>
      </div>
    `;
  }

  setupSmartFilter() {
    const filterContainer = document.getElementById('smartFilterContainer');
    if (filterContainer) {
      this.smartFilter = new SmartFilter({
        container: filterContainer,
        presets: getFilterPresets('analytics'),
        filterTypes: getFilterTypes(),
        onFilterChange: this.handleFilterChange.bind(this),
        defaultView: 'presets'
      });
    }
  }

  setupEventListeners() {
    // Tab switching handled by smart filter
    
    // Report generation
    const generateBtn = document.getElementById('generateReport');
    if (generateBtn) {
      generateBtn.addEventListener('click', () => {
        this.renderers.generateDetailedReport(this.analyticsData);
      });
    }
    
    // Data export
    const exportBtn = document.getElementById('exportData');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        this.renderers.exportAllData(this.analyticsData);
      });
    }
    
    // Refresh data
    document.addEventListener('analytics:refresh', () => {
      this.refreshData();
    });
  }

  async updateAnalytics(centralData) {
    try {
      if (centralData.error) {
        console.error('Analytics data error:', centralData.error);
        this.renderers.showError('Failed to load analytics data. Using cached data.');
        this.analyticsData = this.loadCachedData() || this.getFallbackAnalytics();
      } else {
        // Process and enrich the data
        this.analyticsData = {
          ...centralData,
          job_metrics: centralData.job_metrics || this.getFallbackJobsToday(),
          system_health: centralData.system_health || this.getFallbackSystemHealth(),
          queue_status: centralData.queue_status || this.getFallbackQueueStatus(),
          performance_metrics: centralData.performance_metrics || {},
          worker_status: centralData.worker_status || {},
          timestamp: new Date().toISOString()
        };
        
        // Calculate enterprise KPIs
        this.analyticsData.kpis = this.calculations.calculateEnterpriseKPIs(this.analyticsData);
        
        // Cache the data
        this.cacheAnalyticsData(this.analyticsData);
      }
      
      // Update visualizations based on current filter
      this.updateVisualizationsForCurrentFilter();
      
      // Update KPIs
      this.renderers.updateKPIs(this.currentTab, this.analyticsData);
      
      // Update actionable metrics (only if already initialized)
      if (this.metricCards.size > 0) {
        this.updateActionableMetrics();
      }
      
    } catch (error) {
      console.error('Error updating analytics:', error);
      this.renderers.showError('An error occurred while updating analytics');
    }
  }

  updateVisualizationsForCurrentFilter() {
    // Ensure DOM is ready before rendering
    const contentContainer = this.container.querySelector('#analyticsContent');
    if (!contentContainer) {
      console.warn('Analytics content container not found, retrying...');
      setTimeout(() => this.updateVisualizationsForCurrentFilter(), 100);
      return;
    }
    
    if (this.currentFilter.metric) {
      switch(this.currentFilter.metric) {
        case 'performance':
          this.renderers.renderPerformanceMetricsTab(this.analyticsData);
          break;
        case 'usage':
          this.renderers.renderUsageStatisticsTab(this.analyticsData);
          break;
        case 'errors':
          this.renderers.renderErrorTrendsTab(this.analyticsData);
          break;
        case 'capacity':
          this.renderers.renderCapacityPlanningTab(this.analyticsData);
          break;
        default:
          this.renderers.renderPerformanceMetricsTab(this.analyticsData);
      }
    } else {
      // Default to performance tab
      this.renderers.renderPerformanceMetricsTab(this.analyticsData);
    }
    
    // Update detailed reports section
    setTimeout(() => {
      const reportsContainer = document.getElementById('detailedReports');
      if (reportsContainer) {
        reportsContainer.innerHTML = this.renderers.renderDetailedReports(this.analyticsData);
      }
    }, 50);
  }

  // Fallback data methods
  getFallbackAnalytics() {
    return {
      job_metrics: this.getFallbackJobsToday(),
      system_health: this.getFallbackSystemHealth(),
      queue_status: this.getFallbackQueueStatus(),
      performance_metrics: {},
      worker_status: {}
    };
  }

  getFallbackSystemHealth() {
    return {
      cpu_usage: 65,
      memory_usage: 72,
      active_workers: 8,
      total_workers: 10
    };
  }

  getFallbackQueueStatus() {
    return {
      total_queued: 45,
      by_priority: { high: 5, normal: 30, low: 10 }
    };
  }

  getFallbackJobsToday() {
    return {
      total: 1234,
      completed: 1150,
      failed: 34,
      processing: 25,
      queued: 25,
      success_rate: 97.1
    };
  }

  loadCachedData() {
    const cached = localStorage.getItem('analytics_cache');
    if (cached) {
      try {
        return JSON.parse(cached);
      } catch (e) {
        return null;
      }
    }
    return null;
  }

  async handleFilterChange(filter) {
    this.currentFilter = filter;
    
    // Update current tab based on filter metric
    if (filter.metric) {
      this.currentTab = filter.metric;
    }
    
    // Update timeframe if specified
    if (filter.timeframe) {
      this.currentTimeframe = filter.timeframe;
    }
    
    // Re-render the appropriate tab
    this.updateVisualizationsForCurrentFilter();
    
    // Update KPIs for new tab
    this.renderers.updateKPIs(this.currentTab, this.analyticsData);
  }

  cacheAnalyticsData(data) {
    try {
      const cacheData = {
        ...data,
        cached_at: new Date().toISOString()
      };
      localStorage.setItem('analytics_cache', JSON.stringify(cacheData));
    } catch (e) {
      console.warn('Failed to cache analytics data:', e);
    }
  }

  refreshAllCharts() {
    this.charts.refreshAllCharts();
  }

  async refreshData() {
    // Force refresh from central data service
    if (this.centralDataService) {
      const data = this.centralDataService.getCurrentData();
      if (data) {
        await this.updateAnalytics(data);
      }
    }
  }

  async initializeActionService() {
    try {
      const { actionService } = await import('../../../src/services/ActionService.js');
      this.actionService = actionService;
      
      // ActionService is available but doesn't have event listeners
      // We'll handle action results in the handleMetricAction method
      console.log('✅ ActionService initialized');
    } catch (error) {
      console.warn('ActionService not available:', error);
    }
  }

  initializeActionableMetrics() {
    this.setupActionableKPIs();
  }

  setupActionableKPIs() {
    const kpiConfigs = this.getKPIConfigsForTab(this.currentTab);
    
    kpiConfigs.forEach((config, index) => {
      const container = document.querySelector(`#analyticsKPIs > div:nth-child(${index + 1})`);
      if (container && config) {
        try {
          const card = new ActionableMetricCard(container, {
            title: config.title,
            value: config.value,
            icon: config.icon,
            status: config.status,
            thresholds: config.thresholds,
            actions: config.actions || [],
            onActionClick: this.handleMetricAction.bind(this),
            onThresholdCross: this.handleThresholdCross.bind(this)
          });
          
          this.metricCards.set(config.id, card);
        } catch (error) {
          console.warn(`Failed to create ActionableMetricCard for ${config.id}:`, error);
          // Fallback: render basic KPI card
          this.renderers.renderKPICard(container, config);
        }
      }
    });
  }

  updateActionableMetrics() {
    const kpis = this.getKPIConfigsForTab(this.currentTab);
    
    kpis.forEach(kpi => {
      const card = this.metricCards.get(kpi.id);
      if (card) {
        card.update(kpi);
      }
    });
  }

  getKPIConfigsForTab(tab) {
    switch(tab) {
      case 'performance':
        return this.calculations.getPerformanceKPIs(this.analyticsData);
      case 'usage':
        return this.calculations.getUsageKPIs(this.analyticsData);
      case 'errors':
        return this.calculations.getErrorKPIs(this.analyticsData);
      case 'capacity':
        return this.calculations.getCapacityKPIs(this.analyticsData);
      default:
        return this.calculations.getPerformanceKPIs(this.analyticsData);
    }
  }

  async handleMetricAction({ action, params, button }) {
    if (!this.actionService) {
      this.renderers.showToast('Action service not available', 'warning');
      return;
    }
    
    try {
      button.disabled = true;
      button.textContent = 'Processing...';
      
      const result = await this.actionService.execute(action, params);
      this.showActionResult(result, action);
      
    } catch (error) {
      this.renderers.showToast(`Action failed: ${error.message}`, 'error');
    } finally {
      button.disabled = false;
      button.textContent = button.dataset.originalText || 'Execute';
    }
  }

  handleThresholdCross({ metric, oldStatus, newStatus, value, thresholds }) {
    if (newStatus === 'danger' && oldStatus !== 'danger') {
      this.showCriticalAlert(metric, value);
    }
    
    // Log threshold crossing for monitoring
    console.warn(`Threshold crossed for ${metric}:`, {
      oldStatus,
      newStatus,
      value,
      thresholds
    });
  }


  showActionResult(result, action) {
    const message = result.message || `Action ${action} completed`;
    const type = result.success ? 'success' : 'warning';
    this.renderers.showToast(message, type);
  }

  showCriticalAlert(metric, value) {
    const alert = `⚠️ Critical threshold reached for ${metric}: ${value}`;
    this.renderers.showToast(alert, 'error');
  }

  async registerHelpProvider() {
    if (window.HelpSystem && this.helpProvider) {
      try {
        const helpSystem = window.HelpSystem.getInstance();
        await helpSystem.registerProvider('analytics', this.helpProvider);
        console.log('✅ Analytics help provider registered');
      } catch (error) {
        console.warn('Could not register analytics help provider:', error);
      }
    }
  }

  destroy() {
    // Unsubscribe from central data service
    if (this.subscriptionId && this.centralDataService) {
      this.centralDataService.unsubscribe(this.subscriptionId);
    }
    
    // Destroy all charts
    this.charts.destroyAllCharts();
    
    // Clear metric cards
    this.metricCards.forEach(card => card.destroy && card.destroy());
    this.metricCards.clear();
    
    // Clean up smart filter
    if (this.smartFilter) {
      this.smartFilter.destroy && this.smartFilter.destroy();
    }
    
    // Clear global reference
    if (typeof window !== 'undefined') {
      delete window.analytics;
    }
  }
}