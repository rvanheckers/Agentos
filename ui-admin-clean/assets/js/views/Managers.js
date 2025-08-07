/**
 * Managers Performance Monitoring View - Service Layer SSOT Architecture
 * 
 * PERFORMANCE MONITORING: Real-time service layer performance tracking
 * ARCHITECTUUR: Direct AdminDataManager calls, geen HTTP overhead
 * 
 * Functionaliteiten:
 * - Service layer performance monitoring (JobsService, QueueService, etc.)
 * - Real-time health indicators per manager
 * - Response time tracking & trends
 * - System resource usage monitoring
 * - Manager-specific detailed metrics
 * 
 * Created: 2 Augustus 2025
 * Pattern: Service Layer SSOT + Performance Monitoring
 */

import { getCentralDataService } from '../services/central-data-service.js';
import { SmartFilter } from '../components/SmartFilter.js';
import { HelpService } from '../services/HelpService.js';
import { HelpPanel } from '../components/HelpPanel.js';
import { ManagersHelpProvider } from '../help-providers/ManagersHelpProvider.js';

export class ManagersView {
  constructor() {
    this.centralDataService = getCentralDataService();
    this.subscriptionId = null;
    this.container = null;
    this.smartFilter = null;
    
    // Performance monitoring state
    this.managerMetrics = new Map();
    this.refreshRate = 10000; // 10 seconds for performance data
    this.refreshTimer = null;
    this.refreshCountdown = 10;
    this.countdownTimer = null;
    
    // Help system
    this.helpPanel = null;
    
    // Manager definitions based on services/README.md
    this.managers = [
      { id: 'admin_data', name: 'AdminDataManager', service: 'AdminDataManager', description: 'Real-time data aggregation hub - coordinates WebSocket + HTTP data flows' },
      { id: 'jobs', name: 'JobsService', service: 'JobsService', description: 'Orchestrates automation tasks, job lifecycle management, and status tracking' },
      { id: 'queue', name: 'QueueService', service: 'QueueService', description: 'Manages Celery task queues, worker coordination, and job distribution' },
      { id: 'agents', name: 'AgentsService', service: 'AgentsService', description: 'Controls AI agents execution, status monitoring, and configuration' },
      { id: 'analytics', name: 'AnalyticsService', service: 'AnalyticsService', description: 'Provides performance metrics, reporting, and system analytics' },
      { id: 'database', name: 'DatabaseManager', service: 'DatabaseManager', description: 'Handles all PostgreSQL operations, connection pooling, and queries' }
    ];
    
    console.log('🏢 Managers Performance View initialized - Service Layer SSOT pattern');
  }

  async init(container) {
    this.container = container;
    
    // Make globally accessible EARLY for onclick handlers
    window.managersView = this;
    console.log('🔧 Global managersView set:', window.managersView);
    
    this.render();
    this.setupSmartFilter();
    this.setupEventListeners();
    this.setupHelpSystem();
    
    // Subscribe to AdminDataManager for system health data
    this.subscriptionId = this.centralDataService.subscribe('Managers', (data) => {
      this.updateFromServiceLayer(data);
    });
    
    // Start central service if not running
    if (!this.centralDataService.getStatus().isRunning) {
      this.centralDataService.start();
    }
    
    // Load initial performance data
    await this.loadInitialData();
    
    // Start performance monitoring
    this.startPerformanceMonitoring();
    
    console.log('✅ Managers Performance View initialized successfully');
  }

  render() {
    this.container.innerHTML = `
      <div class="managers-performance-view">
        <!-- Page Header -->
        <div class="page-header">
          <div class="page-header__content">
            <h1 class="page-header__title">
              🏢 Business Service Layers
              <button class="help-icon" data-section="diagnostics">🩺</button>
            </h1>
            <p class="page-header__description">
              Monitor the core business logic services that power your automation framework - real-time health and performance tracking
            </p>
          </div>
          <div class="page-header__actions">
            <div class="refresh-indicator">
              <span class="refresh-icon">🔄</span>
              Auto-refresh: <span id="refresh-countdown">10</span>s
            </div>
            <button class="btn btn-secondary" id="manual-refresh">
              <span class="btn__icon">🔄</span>
              Refresh Now
            </button>
            <button class="btn btn-primary" id="toggle-monitoring">
              <span class="btn__icon">⏸️</span>
              Pause Monitoring
            </button>
          </div>
        </div>

        <!-- SmartFilter Container -->
        <div class="smartfilter-section">
          <div class="smartfilter-header">
            <h3 class="section-title">
              🔍 Smart Filters
              <button class="help-icon" data-section="smartfilter">❓</button>
            </h3>
          </div>
          <div id="smart-filter-container"></div>
        </div>

        <!-- System Overview Metrics -->
        <div class="system-overview">
          <h3 class="section-title">
            📊 System Overview
            <button class="help-icon" data-section="system_overview">❓</button>
          </h3>
          <div class="overview-metrics">
            <div id="total-managers-card"></div>
            <div id="healthy-managers-card"></div>
            <div id="avg-response-card"></div>
            <div id="system-load-card"></div>
          </div>
        </div>

        <!-- Managers Performance Grid -->
        <div class="managers-section">
          <h3 class="section-title">
            🏢 Core Business Services
            <button class="help-icon" data-section="business_services">❓</button>
          </h3>
          <div class="managers-grid" id="managers-grid">
            <div class="loading-state">
              <div class="loading-spinner"></div>
              <p>Loading manager performance data...</p>
            </div>
          </div>
        </div>

        <!-- Compact Details & Alerts Section -->
        <div class="bottom-section">
          <!-- Service Trends - Compact -->
          <div class="detailed-section compact">
            <div class="compact-header">
              <h4>📊 Service Trends</h4>
              <div class="compact-controls">
                <select id="trend-timeframe" class="compact-select">
                  <option value="5m">Last 5min</option>
                  <option value="1h">Last Hour</option>
                  <option value="24h">Last 24h</option>
                </select>
                <button class="btn-compact" id="refresh-trends">Refresh</button>
              </div>
            </div>
            <div id="detailed-content" class="compact-content">
              <div class="trends-overview">
                <div class="trend-item">
                  <span class="trend-label">Avg Response:</span>
                  <span class="trend-value" id="avg-response">--ms</span>
                  <span class="trend-change improving" id="response-trend">↗ +5%</span>
                </div>
                <div class="trend-item">
                  <span class="trend-label">System Load:</span>
                  <span class="trend-value" id="system-load">--%</span>
                  <span class="trend-change stable" id="load-trend">→ 0%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Performance Alerts - Compact -->
          <div class="alerts-section compact" id="performance-alerts" style="display: none;">
            <div class="compact-header">
              <h4>⚠️ Active Issues</h4>
            </div>
            <div id="alerts-content" class="compact-alerts">
              <!-- Dynamic alerts content -->
            </div>
          </div>
        </div>
      </div>
    `;
  }

  setupSmartFilter() {
    try {
      const container = document.getElementById('smart-filter-container');
      if (!container) {
        console.warn('⚠️ SmartFilter container not found, skipping setup');
        return;
      }

      this.smartFilter = new SmartFilter({
        presets: {
          'all': {
            label: 'All Services',
            icon: '📊',
            badge: 'Default',
            filter: {
              view: 'all',
              layout: 'grid',
              highlight: 'none',
              details: 'summary',
              status: 'all'
            }
          },
          'issues': {
            label: 'Issues Only',
            icon: '⚠️',
            filter: {
              view: 'issues',
              layout: 'priority',
              highlight: 'negative',
              details: 'expanded',
              status: ['warning', 'error'],
              errorRate: '>5'
            }
          },
          'performance': {
            label: 'Performance Focus',
            icon: '⚡',
            filter: {
              view: 'performance',
              layout: 'timeline',
              highlight: 'performance',
              details: 'latency',
              status: 'all'
            }
          }
        },
        // Simplified - only Quick Filters, no complex dropdowns needed for 6 services
        filterTypes: {},
        defaultFilter: 'all',
        onFilterChange: (filter) => this.handleFilterChange(filter)
      });

      this.smartFilter.init(container);
      console.log('✅ SmartFilter initialized successfully for Managers view');
    } catch (error) {
      console.error('❌ Failed to setup SmartFilter:', error);
    }
  }

  handleFilterChange(filter) {
    console.log('🔍 Managers filter changed:', filter);
    console.log('📊 Current metrics before filter:', this.managerMetrics.size, 'services');
    
    // Update current filter - store the complete filter object including preset data
    this.currentFilter = filter;
    
    // Apply filter to performance data
    this.applyCurrentFilter();
  }

  applyCurrentFilter() {
    // Get all manager metrics
    const allMetrics = Array.from(this.managerMetrics.values());
    console.log('🔄 Applying filter to', allMetrics.length, 'services');
    console.log('🎯 Filter criteria:', this.currentFilter);
    
    // Apply filters based on current filter criteria
    let filteredMetrics = allMetrics;
    
    if (this.currentFilter) {
      // Use the filter data directly from currentFilter (includes preset criteria)
      const filter = this.currentFilter;
      
      filteredMetrics = allMetrics.filter(metrics => {
        // Status filter
        if (filter.status && filter.status !== 'all') {
          if (Array.isArray(filter.status)) {
            if (!filter.status.includes(metrics.status)) return false;
          } else {
            if (metrics.status !== filter.status) return false;
          }
        }
        
        // Response time filter
        if (filter.responseTime) {
          const operator = filter.responseTime.charAt(0);
          const value = parseInt(filter.responseTime.slice(1));
          
          if (operator === '>' && metrics.responseTime <= value) return false;
          if (operator === '<' && metrics.responseTime >= value) return false;
        }
        
        // Error rate filter
        if (filter.errorRate) {
          const operator = filter.errorRate.charAt(0);
          const value = parseFloat(filter.errorRate.slice(1));
          
          if (operator === '>' && metrics.errorRate <= value) return false;
          if (operator === '<' && metrics.errorRate >= value) return false;
        }
        
        // CPU usage filter
        if (filter.cpuUsage) {
          const operator = filter.cpuUsage.charAt(0);
          const value = parseInt(filter.cpuUsage.slice(1));
          
          if (operator === '>' && metrics.cpuUsage <= value) return false;
          if (operator === '<' && metrics.cpuUsage >= value) return false;
        }
        
        // Memory usage filter
        if (filter.memoryUsage) {
          const operator = filter.memoryUsage.charAt(0);
          const value = parseInt(filter.memoryUsage.slice(1));
          
          if (operator === '>' && metrics.memoryUsage <= value) return false;
          if (operator === '<' && metrics.memoryUsage >= value) return false;
        }
        
        return true;
      });
    }
    
    // Store filtered metrics for rendering
    this.filteredMetrics = filteredMetrics;
    
    console.log('✅ Filter result:', filteredMetrics.length, 'services match filter');
    
    // Update results count
    const resultsCount = document.getElementById('resultsCount');
    if (resultsCount) {
      resultsCount.textContent = `${filteredMetrics.length} of ${allMetrics.length} services`;
    }
    
    // Re-render with filtered data
    this.updateOverviewMetrics();
    this.renderFilteredManagersGrid();
    this.updateDetailedSection(); // Show/hide detailed section based on context
  }

  setupEventListeners() {
    // Manual refresh button
    document.getElementById('manual-refresh')?.addEventListener('click', () => {
      this.refreshPerformanceData();
    });

    // Toggle monitoring
    document.getElementById('toggle-monitoring')?.addEventListener('click', () => {
      this.toggleMonitoring();
    });

    // Manager selector for detailed view
    document.getElementById('manager-selector')?.addEventListener('change', (e) => {
      if (e.target.value) {
        this.showManagerDetails(e.target.value);
      }
    });

    // View details button
    document.getElementById('view-details')?.addEventListener('click', () => {
      const selectedManager = document.getElementById('manager-selector').value;
      if (selectedManager) {
        this.showManagerDetails(selectedManager);
      }
    });
  }

  /**
   * Setup help system for Managers view
   */
  setupHelpSystem() {
    try {
      // Register help provider
      HelpService.registerProvider('managers', ManagersHelpProvider);
      
      // Create help panel
      this.helpPanel = new HelpPanel('managers', {
        position: 'right',
        width: '380px',
        showUserLevelToggle: true
      });
      
      // Setup help icon click handlers (contextual help)
      document.addEventListener('click', (event) => {
        const helpIcon = event.target.closest('.help-icon');
        if (!helpIcon) return;
        
        event.preventDefault();
        event.stopPropagation();
        
        // Get context from data attributes
        const serviceId = helpIcon.getAttribute('data-service');
        const metricId = helpIcon.getAttribute('data-metric');
        const sectionId = helpIcon.getAttribute('data-section');
        
        // Determine help context
        let helpContext = null;
        if (serviceId) {
          helpContext = serviceId;
        } else if (metricId) {
          helpContext = metricId;
        } else if (sectionId) {
          helpContext = sectionId;
        }
        
        // Show contextual help
        this.helpPanel.show(helpContext);
        
        console.log(`🆘 Contextual help shown for: ${helpContext}`);
      });
      
      // Make help panel globally accessible for onclick handlers
      window.helpPanel = this.helpPanel;
      
      console.log('🆘 Help system initialized for Managers view');
      
    } catch (error) {
      console.error('❌ Error setting up help system:', error);
    }
  }

  async loadInitialData() {
    try {
      // Generate initial performance data
      this.generatePerformanceMetrics();
      this.updateOverviewMetrics();
      this.renderManagersGrid();
      
    } catch (error) {
      console.error('❌ Error loading initial performance data:', error);
      this.showError('Failed to load performance data');
    }
  }

  updateFromServiceLayer(centralData) {
    try {
      if (centralData.error) {
        console.warn('⚠️ Service layer error:', centralData.message);
        return;
      }

      console.log('🔄 Updating managers performance from service layer...');
      
      // Extract system health data for performance correlation
      const systemData = centralData.dashboard?.success ? centralData.dashboard.data : null;
      
      if (systemData) {
        this.correlateSystemHealth(systemData);
      }
      
    } catch (error) {
      console.error('❌ Failed to update from service layer:', error);
    }
  }

  generatePerformanceMetrics() {
    // TEMPORARY: Using consistent mock data until real API endpoints are connected
    // TODO: Connect to /api/admin/managers/status and /api/admin/managers/*/metrics
    
    // Fixed seed based on manager ID to prevent flickering
    this.managers.forEach(manager => {
      const baseResponseTime = this.getBaseResponseTime(manager.id);
      
      // Use existing metrics if available (prevent flickering)
      const existingMetrics = this.managerMetrics.get(manager.id);
      
      // Only update certain values that should change
      const metrics = {
        id: manager.id,
        name: manager.name,
        service: manager.service,
        status: existingMetrics?.status || 'healthy',
        responseTime: existingMetrics?.responseTime || baseResponseTime,
        successRate: existingMetrics?.successRate || 98.5,
        requestsPerMinute: existingMetrics?.requestsPerMinute || this.getFixedRequests(manager.id),
        cpuUsage: existingMetrics?.cpuUsage || this.getFixedCPU(manager.id),
        memoryUsage: existingMetrics?.memoryUsage || this.getFixedMemory(manager.id),
        errorRate: existingMetrics?.errorRate || 0.5,
        lastUpdated: new Date().toISOString(),
        trend: existingMetrics?.trend || 'stable'
      };
      
      // Small variations to show it's "live" without flickering
      if (existingMetrics) {
        metrics.responseTime = Math.round(baseResponseTime + (Math.random() * 10 - 5)); // ±5ms variation
        metrics.requestsPerMinute = Math.round(metrics.requestsPerMinute + (Math.random() * 4 - 2)); // ±2 variation
      }
      
      this.managerMetrics.set(manager.id, metrics);
    });
  }
  
  getFixedRequests(managerId) {
    const baseRequests = {
      'admin_data': 25,
      'jobs': 45,
      'queue': 35,
      'agents': 20,
      'analytics': 15,
      'database': 60
    };
    return baseRequests[managerId] || 20;
  }
  
  getFixedCPU(managerId) {
    const baseCPU = {
      'admin_data': 22,
      'jobs': 85,       // High CPU for testing high-load filter
      'queue': 18,
      'agents': 25,
      'analytics': 92,  // High CPU for testing high-load filter
      'database': 15
    };
    return baseCPU[managerId] || 20;
  }
  
  getFixedMemory(managerId) {
    const baseMemory = {
      'admin_data': 45,
      'jobs': 35,
      'queue': 25,
      'agents': 30,
      'analytics': 40,
      'database': 50
    };
    return baseMemory[managerId] || 30;
  }

  getBaseResponseTime(managerId) {
    // Base response times with more realistic variation for testing filters
    const baseTimes = {
      'admin_data': 185,  // AdminDataManager aggregates all data (target: <300ms)
      'jobs': 550,        // JobsService can be slow with complex jobs (for testing slow filter)
      'queue': 45,        // QueueService handles Celery operations
      'agents': 750,      // AgentsService can be slow with AI calls (for testing slow filter)  
      'analytics': 140,   // AnalyticsService performs metric calculations
      'database': 35      // DatabaseManager direct PostgreSQL operations
    };
    return baseTimes[managerId] || 75;
  }

  generateHealthStatus() {
    const rand = Math.random();
    if (rand > 0.9) return 'warning';
    if (rand > 0.98) return 'error';
    return 'healthy';
  }

  generateTrend() {
    const trends = ['improving', 'stable', 'degrading'];
    const weights = [0.3, 0.6, 0.1]; // Mostly stable, some improving
    
    const rand = Math.random();
    let cumulative = 0;
    
    for (let i = 0; i < trends.length; i++) {
      cumulative += weights[i];
      if (rand <= cumulative) {
        return trends[i];
      }
    }
    return 'stable';
  }

  updateOverviewMetrics() {
    const metricsArray = Array.from(this.managerMetrics.values());
    const healthyCount = metricsArray.filter(m => m.status === 'healthy').length;
    const avgResponseTime = Math.round(
      metricsArray.reduce((sum, m) => sum + m.responseTime, 0) / metricsArray.length
    );
    const avgCpuUsage = Math.round(
      metricsArray.reduce((sum, m) => sum + m.cpuUsage, 0) / metricsArray.length
    );

    // Total Managers
    this.createMetricCard('total-managers-card', {
      title: 'Total Managers',
      value: this.managers.length.toString(),
      description: 'Active service managers',
      status: 'neutral',
      icon: '🏢'
    });

    // Healthy Managers
    this.createMetricCard('healthy-managers-card', {
      title: 'Healthy Managers',
      value: `${healthyCount}/${this.managers.length}`,
      description: `${Math.round((healthyCount/this.managers.length)*100)}% healthy`,
      status: healthyCount === this.managers.length ? 'good' : 'warning',
      icon: '💚'
    });

    // Average Response Time
    this.createMetricCard('avg-response-card', {
      title: 'Avg Response Time',
      value: `${avgResponseTime}ms`,
      description: 'Across all managers',
      status: avgResponseTime < 100 ? 'good' : (avgResponseTime < 200 ? 'warning' : 'danger'),
      icon: '⚡'
    });

    // System Load
    this.createMetricCard('system-load-card', {
      title: 'System Load',
      value: `${avgCpuUsage}%`,
      description: 'Average CPU usage',
      status: avgCpuUsage < 60 ? 'good' : (avgCpuUsage < 80 ? 'warning' : 'danger'),
      icon: '📊'
    });
  }

  createMetricCard(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="metric-card metric-card--${data.status}">
        <div class="metric-card__header">
          <div class="metric-card__icon">${data.icon}</div>
          <div class="metric-card__title">${data.title}</div>
        </div>
        <div class="metric-card__content">
          <div class="metric-card__value">${data.value}</div>
          <div class="metric-card__description">${data.description}</div>
        </div>
      </div>
    `;
  }

  renderManagersGrid() {
    const grid = document.getElementById('managers-grid');
    if (!grid) return;

    const metricsArray = Array.from(this.managerMetrics.values());
    
    grid.innerHTML = metricsArray.map(metrics => this.renderManagerCard(metrics)).join('');
  }

  renderFilteredManagersGrid() {
    const grid = document.getElementById('managers-grid');
    if (!grid) return;

    // Get layout and display preferences from current filter
    const layout = this.currentFilter?.layout || 'grid';
    const highlight = this.currentFilter?.highlight || 'none';
    const details = this.currentFilter?.details || 'summary';
    
    // Use all metrics but apply visual filtering based on filter criteria
    const allMetrics = Array.from(this.managerMetrics.values());
    const filteredMetrics = this.filteredMetrics || allMetrics;
    
    // Apply layout-specific rendering
    switch (layout) {
      case 'grid':
        this.renderGridLayout(grid, allMetrics, filteredMetrics, highlight, details);
        break;
      case 'priority':
        this.renderPriorityLayout(grid, allMetrics, filteredMetrics, highlight, details);
        break;
      case 'timeline':
        this.renderTimelineLayout(grid, allMetrics, filteredMetrics, highlight, details);
        break;
      default:
        this.renderGridLayout(grid, allMetrics, filteredMetrics, highlight, details);
    }
  }

  renderManagerCard(metrics, options = {}) {
    const { 
      cardClass = '', 
      detailLevel = 'summary', 
      isHighlighted = true 
    } = options;
    
    const statusClass = this.getStatusClass(metrics.status);
    const trendIcon = this.getTrendIcon(metrics.trend);
    const trendClass = this.getTrendClass(metrics.trend);
    
    // Find manager description
    const manager = this.managers.find(m => m.id === metrics.id);
    const description = manager?.description || 'Service layer manager';
    
    // Apply detail level variations
    if (detailLevel === 'minimal') {
      return `
        <div class="manager-card manager-card--${statusClass}" style="padding: 0.5rem; ${cardClass}">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
            <h4 style="margin: 0; font-size: 0.9rem;">${metrics.name}</h4>
            <span class="status-indicator status-indicator--${statusClass}"></span>
          </div>
          <div style="font-size: 0.8rem; color: #6c757d;">
            ${metrics.responseTime}ms | ${metrics.cpuUsage}%
          </div>
        </div>
      `;
    }
    
    if (detailLevel === 'expanded') {
      const alertBg = metrics.status !== 'healthy' ? '#f8d7da' : 'transparent';
      const alertBorder = metrics.status !== 'healthy' ? '1px solid #f5c6cb' : 'none';
      const alertText = metrics.status !== 'healthy' ? '#721c24' : 'transparent';
      
      return `
        <div class="manager-card manager-card--${statusClass}" style="padding: 1.5rem; ${cardClass}">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
              <h4 style="margin: 0; margin-bottom: 0.25rem;">${metrics.name}</h4>
              <span style="background: ${metrics.status === 'healthy' ? '#d4edda' : '#f8d7da'}; color: ${metrics.status === 'healthy' ? '#155724' : '#721c24'}; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">${metrics.status}</span>
            </div>
            <button class="help-icon" data-service="${manager.id}">❓</button>
          </div>
          
          ${metrics.status !== 'healthy' ? `
            <div style="background: ${alertBg}; border: ${alertBorder}; border-radius: 4px; padding: 0.75rem; margin-bottom: 1rem; color: ${alertText};">
              <strong>Issue Detected:</strong> 
              ${metrics.errorRate > 5 ? `High error rate: ${metrics.errorRate.toFixed(1)}% ` : ''}
              ${metrics.responseTime > 500 ? `Slow response: ${metrics.responseTime}ms ` : ''}
              ${metrics.cpuUsage > 80 ? `High CPU: ${metrics.cpuUsage}% ` : ''}
            </div>
          ` : ''}
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
            <div>
              <span style="font-size: 0.8rem; color: #6c757d; display: block;">Response Time</span>
              <span style="font-size: 1.25rem; font-weight: 600; color: ${metrics.responseTime > 500 ? '#dc3545' : '#28a745'};">${metrics.responseTime}ms</span>
            </div>
            <div>
              <span style="font-size: 0.8rem; color: #6c757d; display: block;">Success Rate</span>
              <span style="font-size: 1.25rem; font-weight: 600;">${metrics.successRate.toFixed(1)}%</span>
            </div>
            <div>
              <span style="font-size: 0.8rem; color: #6c757d; display: block;">Error Rate</span>
              <span style="font-size: 1.25rem; font-weight: 600; color: ${metrics.errorRate > 5 ? '#dc3545' : '#28a745'};">${metrics.errorRate.toFixed(1)}%</span>
            </div>
            <div>
              <span style="font-size: 0.8rem; color: #6c757d; display: block;">CPU Usage</span>
              <span style="font-size: 1.25rem; font-weight: 600; color: ${metrics.cpuUsage > 80 ? '#dc3545' : '#28a745'};">${metrics.cpuUsage}%</span>
            </div>
          </div>
          
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-sm btn-primary" onclick="window.managersView.showManagerDetails('${metrics.id}')">
              View Details
            </button>
            ${metrics.status !== 'healthy' ? `
              <button class="btn btn-sm btn-warning" onclick="window.managersView.troubleshootService('${metrics.id}')">
                Troubleshoot
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }

    // Default summary view
    return `
      <div class="manager-card manager-card--${statusClass} ${cardClass}">
        <div class="manager-card__header">
          <div class="manager-card__title">
            <h4>${metrics.name}</h4>
          </div>
          <div class="manager-card__actions">
            <button class="help-icon" data-service="${manager.id}">
              ❓
            </button>
            <div class="manager-card__status">
              <span class="status-indicator status-indicator--${statusClass}"></span>
              <span class="status-text">${metrics.status}</span>
            </div>
          </div>
        </div>
        
        <div class="manager-card__description">
          <p>${description}</p>
        </div>
        
        <div class="manager-card__metrics">
          <div class="metric-row">
            <div class="metric-item">
              <span class="metric-label">Response Time</span>
              <span class="metric-value">${metrics.responseTime}ms</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Success Rate</span>
              <span class="metric-value">${metrics.successRate.toFixed(1)}%</span>
            </div>
          </div>
          
          <div class="metric-row">
            <div class="metric-item">
              <span class="metric-label">Requests/min</span>
              <span class="metric-value">${metrics.requestsPerMinute}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">CPU Usage</span>
              <span class="metric-value">${metrics.cpuUsage}%</span>
            </div>
          </div>
        </div>
        
        <div class="manager-card__footer">
          <div class="trend-indicator trend-indicator--${trendClass}">
            <span class="trend-icon">${trendIcon}</span>
            <span class="trend-text">${metrics.trend}</span>
          </div>
          <button class="btn btn-sm btn-secondary" onclick="window.managersView.showManagerDetails('${metrics.id}')">
            Details
          </button>
        </div>
      </div>
    `;
  }

  renderGridLayout(grid, allMetrics, filteredMetrics, highlight, details) {
    // Standard grid layout with highlighting
    const filteredIds = new Set(filteredMetrics.map(m => m.id));
    
    grid.className = 'managers-grid managers-grid--grid';
    grid.innerHTML = allMetrics.map(metrics => {
      const isFiltered = filteredIds.has(metrics.id);
      const cardClass = this.getCardHighlightClass(metrics, isFiltered, highlight);
      
      return this.renderManagerCard(metrics, {
        cardClass,
        detailLevel: details,
        isHighlighted: isFiltered
      });
    }).join('');
  }

  renderPriorityLayout(grid, allMetrics, filteredMetrics, highlight, details) {
    // Issues first, larger cards for problems
    const issues = filteredMetrics.filter(m => m.status !== 'healthy');
    const healthy = allMetrics.filter(m => m.status === 'healthy');
    
    grid.className = 'managers-grid'; // Use existing CSS
    
    const issuesHtml = issues.length > 0 ? `
      <div style="margin-bottom: 2rem;">
        <h3 style="color: #dc3545; margin-bottom: 1rem; display: flex; align-items: center;">
          <span style="margin-right: 0.5rem;">⚠️</span>
          Services Requiring Attention (${issues.length})
        </h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 1rem;">
          ${issues.map(metrics => this.renderManagerCard(metrics, {
            cardClass: '',
            detailLevel: 'expanded',
            isHighlighted: true
          })).join('')}
        </div>
      </div>
    ` : '';
    
    const healthyHtml = `
      <div>
        <h3 style="color: #28a745; margin-bottom: 1rem; display: flex; align-items: center;">
          <span style="margin-right: 0.5rem;">✅</span>
          Healthy Services (${healthy.length})
        </h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.5rem;">
          ${healthy.map(metrics => this.renderManagerCard(metrics, {
            cardClass: '',
            detailLevel: 'minimal',
            isHighlighted: false
          })).join('')}
        </div>
      </div>
    `;
    
    grid.innerHTML = issuesHtml + healthyHtml;
  }

  renderTimelineLayout(grid, allMetrics, filteredMetrics, highlight, details) {
    // Timeline view focused on response times
    const sortedMetrics = [...allMetrics].sort((a, b) => b.responseTime - a.responseTime);
    const maxResponseTime = Math.max(...sortedMetrics.map(m => m.responseTime));
    
    grid.className = 'managers-grid';
    grid.innerHTML = `
      <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px;">
        <h3 style="margin-bottom: 1rem; color: #495057;">🐌 Response Time Timeline</h3>
        <div style="display: flex; justify-content: space-between; margin-bottom: 1rem; font-size: 0.8rem; color: #6c757d;">
          <span>0ms</span>
          <span>${Math.round(maxResponseTime/2)}ms</span>
          <span>${maxResponseTime}ms (slowest)</span>
        </div>
        <div style="space-y: 0.5rem;">
          ${sortedMetrics.map(metrics => this.renderTimelineItem(metrics, maxResponseTime, filteredMetrics)).join('')}
        </div>
      </div>
    `;
  }

  renderResourceLayout(grid, allMetrics, filteredMetrics, highlight, details) {
    // Resource usage visualization
    grid.className = 'managers-grid';
    
    const resourceHtml = allMetrics.map(metrics => {
      const isHighLoad = metrics.cpuUsage > 80 || metrics.memoryUsage > 80;
      const isFiltered = filteredMetrics.some(f => f.id === metrics.id);
      const cardBg = isHighLoad ? '#ffeaa7' : '#f8f9fa';
      const cardBorder = isHighLoad ? '2px solid #e17055' : '1px solid #dee2e6';
      const opacity = isFiltered ? '1.0' : '0.6';
      
      return `
        <div style="background: ${cardBg}; border: ${cardBorder}; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; opacity: ${opacity};">
          <h4 style="margin-bottom: 0.5rem;">${metrics.name}</h4>
          <div style="margin-bottom: 1rem;">
            <div style="margin-bottom: 0.5rem;">
              <label style="font-size: 0.8rem; color: #6c757d; margin-bottom: 0.25rem; display: block;">CPU</label>
              <div style="background: #e9ecef; height: 20px; border-radius: 10px; position: relative;">
                <div style="background: ${metrics.cpuUsage > 80 ? '#dc3545' : '#28a745'}; height: 100%; width: ${metrics.cpuUsage}%; border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                  <span style="color: white; font-size: 0.75rem; font-weight: 600;">${metrics.cpuUsage}%</span>
                </div>
              </div>
            </div>
            <div>
              <label style="font-size: 0.8rem; color: #6c757d; margin-bottom: 0.25rem; display: block;">Memory</label>
              <div style="background: #e9ecef; height: 20px; border-radius: 10px; position: relative;">
                <div style="background: ${metrics.memoryUsage > 80 ? '#dc3545' : '#17a2b8'}; height: 100%; width: ${metrics.memoryUsage}%; border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                  <span style="color: white; font-size: 0.75rem; font-weight: 600;">${metrics.memoryUsage}%</span>
                </div>
              </div>
            </div>
          </div>
          <div style="font-size: 0.8rem; color: #6c757d;">
            Response: ${metrics.responseTime}ms | Requests: ${metrics.requestsPerMinute}/min
          </div>
        </div>
      `;
    }).join('');
    
    grid.innerHTML = `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">${resourceHtml}</div>`;
  }

  renderTimelineItem(metrics, maxTime, filteredMetrics) {
    const percentage = (metrics.responseTime / maxTime) * 100;
    const isFiltered = filteredMetrics.some(f => f.id === metrics.id);
    const barColor = metrics.responseTime > 500 ? '#dc3545' : 
                     metrics.responseTime > 200 ? '#ffc107' : 
                     '#28a745';
    const opacity = isFiltered ? '1.0' : '0.5';
    
    return `
      <div style="display: flex; align-items: center; margin-bottom: 0.5rem; opacity: ${opacity};">
        <div style="width: 150px; font-size: 0.9rem; font-weight: 500;">${metrics.name}</div>
        <div style="flex: 1; background: #e9ecef; height: 24px; border-radius: 4px; position: relative; margin-left: 1rem;">
          <div style="background: ${barColor}; height: 100%; width: ${percentage}%; border-radius: 4px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px;">
            <span style="color: white; font-size: 0.8rem; font-weight: 600;">${metrics.responseTime}ms</span>
          </div>
        </div>
      </div>
    `;
  }

  getCardHighlightClass(metrics, isFiltered, highlight) {
    // Use inline styles instead of CSS classes for now
    if (!isFiltered && highlight !== 'none') {
      return 'opacity: 0.5;';
    }
    
    switch (highlight) {
      case 'positive':
        return metrics.status === 'healthy' ? 'border-left: 4px solid #28a745;' : 'opacity: 0.5;';
      case 'negative':
        return metrics.status !== 'healthy' ? 'border-left: 4px solid #dc3545;' : 'opacity: 0.5;';
      case 'performance':
        return metrics.responseTime > 500 ? 'border-left: 4px solid #ffc107;' : '';
      case 'resources':
        return (metrics.cpuUsage > 80 || metrics.memoryUsage > 80) ? 'border-left: 4px solid #e17055;' : '';
      default:
        return '';
    }
  }

  showManagerDetails(managerId) {
    const metrics = this.managerMetrics.get(managerId);
    if (!metrics) return;

    const detailsContent = document.getElementById('detailed-content');
    if (!detailsContent) return;

    detailsContent.innerHTML = `
      <div class="compact-details">
        <div class="compact-metrics">
          <div class="metric-group">
            <div class="metric-pair">
              <span class="label">Response:</span>
              <span class="value ${metrics.responseTime > 500 ? 'warning' : ''}">${metrics.responseTime}ms</span>
            </div>
            <div class="metric-pair">
              <span class="label">Success:</span>
              <span class="value">${metrics.successRate.toFixed(1)}%</span>
            </div>
            <div class="metric-pair">
              <span class="label">CPU:</span>
              <span class="value ${metrics.cpuUsage > 80 ? 'warning' : ''}">${metrics.cpuUsage}%</span>
            </div>
            <div class="metric-pair">
              <span class="label">Status:</span>
              <span class="value status-${metrics.status}">${metrics.status}</span>
            </div>
          </div>
          <div class="compact-actions">
            <button class="btn-micro" onclick="window.managersView.refreshManagerMetrics('${managerId}')">🔄</button>
            <button class="btn-micro" onclick="window.managersView.exportManagerReport('${managerId}')">📊</button>
          </div>
        </div>
      </div>
    `;
  }

  startPerformanceMonitoring() {
    // Start auto-refresh timer
    this.refreshTimer = setInterval(() => {
      this.refreshPerformanceData();
    }, this.refreshRate);

    // Start countdown timer
    this.startCountdown();
    
    console.log('🔄 Performance monitoring started');
  }

  startCountdown() {
    this.refreshCountdown = 10;
    this.countdownTimer = setInterval(() => {
      this.refreshCountdown--;
      const countdownEl = document.getElementById('refresh-countdown');
      if (countdownEl) {
        countdownEl.textContent = this.refreshCountdown;
      }
      
      if (this.refreshCountdown <= 0) {
        this.refreshCountdown = 10;
      }
    }, 1000);
  }

  refreshPerformanceData() {
    console.log('🔄 Refreshing performance data...');
    
    // Simulate performance data updates
    this.generatePerformanceMetrics();
    this.updateOverviewMetrics();
    
    // Re-apply current filter instead of default grid
    if (this.currentFilter) {
      this.applyCurrentFilter();
    } else {
      this.renderManagersGrid();
    }
    
    this.checkPerformanceAlerts();
    
    console.log('✅ Performance data refreshed with filter preserved');
  }

  checkPerformanceAlerts() {
    const alerts = [];
    
    // Context-aware alert filtering based on current filter view
    const currentView = this.currentFilter?.view || 'all';
    
    this.managerMetrics.forEach((metrics, managerId) => {
      // Performance alerts (for performance context)
      if (metrics.responseTime > 500 && (currentView === 'issues' || currentView === 'performance')) {
        alerts.push({
          type: 'warning',
          manager: metrics.name,
          message: `High response time: ${metrics.responseTime}ms`
        });
      }
      
      // Error rate alerts (for issues context)
      if (metrics.errorRate > 2 && (currentView === 'issues')) {
        alerts.push({
          type: 'error',
          manager: metrics.name,
          message: `High error rate: ${metrics.errorRate.toFixed(1)}%`
        });
      }
      
      // Resource alerts (for issues context only)
      if (metrics.cpuUsage > 85 && currentView === 'issues') {
        alerts.push({
          type: 'warning',
          manager: metrics.name,
          message: `High CPU usage: ${metrics.cpuUsage}%`
        });
      }
      
      if (metrics.memoryUsage > 85 && currentView === 'issues') {
        alerts.push({
          type: 'warning',
          manager: metrics.name,
          message: `High memory usage: ${metrics.memoryUsage}%`
        });
      }
    });
    
    this.updatePerformanceAlerts(alerts, currentView);
  }

  updatePerformanceAlerts(alerts, currentView) {
    const alertsSection = document.getElementById('performance-alerts');
    const alertsContent = document.getElementById('alerts-content');
    
    // Context-aware alert display
    const shouldShowAlerts = ['issues', 'performance'].includes(currentView) && alerts.length > 0;
    
    if (shouldShowAlerts) {
      alertsSection.style.display = 'block';
      
      // Context-specific alert title
      const alertTitle = {
        'issues': '⚠️ Service Issues Detected',
        'performance': '⚡ Performance Alerts'
      }[currentView] || '⚠️ Performance Alerts';
      
      // Update section title
      const titleElement = alertsSection.querySelector('.section-title');
      if (titleElement) {
        titleElement.textContent = alertTitle;
      }
      
      alertsContent.innerHTML = alerts.map(alert => `
        <div class="compact-alert ${alert.type}">
          <span class="alert-icon">${alert.type === 'error' ? '🔴' : '🟡'}</span>
          <span class="alert-service">${alert.manager}</span>
          <span class="alert-message">${alert.message}</span>
        </div>
      `).join('');
    } else {
      alertsSection.style.display = 'none';
    }
    
    console.log(`🚨 Alerts: ${alerts.length} alerts for view "${currentView}", display: ${shouldShowAlerts}`);
  }

  toggleMonitoring() {
    const button = document.getElementById('toggle-monitoring');
    
    if (this.refreshTimer) {
      // Stop monitoring
      clearInterval(this.refreshTimer);
      clearInterval(this.countdownTimer);
      this.refreshTimer = null;
      this.countdownTimer = null;
      
      button.innerHTML = '<span class="btn__icon">▶️</span> Resume Monitoring';
      console.log('⏸️ Performance monitoring paused');
    } else {
      // Start monitoring
      this.startPerformanceMonitoring();
      button.innerHTML = '<span class="btn__icon">⏸️</span> Pause Monitoring';
      console.log('▶️ Performance monitoring resumed');
    }
  }

  correlateSystemHealth(systemData) {
    // Correlate system health with manager performance
    if (systemData.system && systemData.system.cpu_usage) {
      const systemCpu = systemData.system.cpu_usage;
      
      // Adjust manager metrics based on system load
      this.managerMetrics.forEach((metrics, managerId) => {
        if (systemCpu > 80) {
          metrics.responseTime = Math.round(metrics.responseTime * 1.2);
          metrics.cpuUsage = Math.min(95, metrics.cpuUsage * 1.1);
        }
      });
    }
  }

  // Action Methods
  async refreshManagerMetrics(managerId) {
    console.log(`🔄 Refreshing metrics for ${managerId}`);
    
    // Regenerate metrics for specific manager
    const manager = this.managers.find(m => m.id === managerId);
    if (manager) {
      const baseResponseTime = this.getBaseResponseTime(managerId);
      const variation = 0.8 + (Math.random() * 0.4);
      
      const updatedMetrics = {
        ...this.managerMetrics.get(managerId),
        responseTime: Math.round(baseResponseTime * variation),
        successRate: 95 + (Math.random() * 5),
        requestsPerMinute: Math.round(10 + (Math.random() * 50)),
        cpuUsage: Math.round(15 + (Math.random() * 25)),
        memoryUsage: Math.round(20 + (Math.random() * 30)),
        errorRate: Math.random() * 2,
        lastUpdated: new Date().toISOString(),
        trend: this.generateTrend()
      };
      
      this.managerMetrics.set(managerId, updatedMetrics);
      this.showManagerDetails(managerId);
      this.renderManagersGrid();
    }
  }

  async exportManagerReport(managerId) {
    const metrics = this.managerMetrics.get(managerId);
    if (!metrics) return;
    
    const report = {
      manager: metrics.name,
      service: metrics.service,
      timestamp: new Date().toISOString(),
      metrics: {
        responseTime: metrics.responseTime,
        successRate: metrics.successRate,
        errorRate: metrics.errorRate,
        requestsPerMinute: metrics.requestsPerMinute,
        cpuUsage: metrics.cpuUsage,
        memoryUsage: metrics.memoryUsage,
        status: metrics.status,
        trend: metrics.trend
      }
    };
    
    const reportJson = JSON.stringify(report, null, 2);
    const blob = new Blob([reportJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `${metrics.name}_performance_report_${Date.now()}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
    
    this.showSuccess(`Performance report exported for ${metrics.name}`);
  }

  updateDetailedSection() {
    // Show/hide Service Trends based on current filter context
    const detailedSection = document.querySelector('.detailed-section');
    if (!detailedSection) return;
    
    const currentView = this.currentFilter?.view || 'all';
    
    // Show trends for 'all' and 'performance' views, hide for 'issues' view
    const shouldShow = ['all', 'performance'].includes(currentView);
    
    detailedSection.style.display = shouldShow ? 'block' : 'none';
    
    // Update trends data if visible
    if (shouldShow) {
      this.updateTrendsData();
    }
    
    console.log(`📊 Service trends ${shouldShow ? 'shown' : 'hidden'} for view: ${currentView}`);
  }

  updateTrendsData() {
    // Calculate real trends from current metrics
    const metricsArray = Array.from(this.managerMetrics.values());
    
    if (metricsArray.length === 0) return;
    
    const avgResponse = Math.round(
      metricsArray.reduce((sum, m) => sum + m.responseTime, 0) / metricsArray.length
    );
    
    const avgLoad = Math.round(
      metricsArray.reduce((sum, m) => sum + m.cpuUsage, 0) / metricsArray.length
    );
    
    // Mock trend changes (in real app, compare with historical data)
    const responseTrend = avgResponse < 300 ? 'improving' : avgResponse > 600 ? 'degrading' : 'stable';
    const loadTrend = avgLoad < 50 ? 'improving' : avgLoad > 80 ? 'degrading' : 'stable';
    
    const responseChange = responseTrend === 'improving' ? '↗ +8%' : 
                          responseTrend === 'degrading' ? '↘ -12%' : '→ 0%';
    const loadChange = loadTrend === 'improving' ? '↗ +5%' : 
                      loadTrend === 'degrading' ? '↘ -15%' : '→ +2%';
    
    // Update UI
    document.getElementById('avg-response').textContent = `${avgResponse}ms`;
    document.getElementById('system-load').textContent = `${avgLoad}%`;
    
    const responseTrendEl = document.getElementById('response-trend');
    const loadTrendEl = document.getElementById('load-trend');
    
    if (responseTrendEl) {
      responseTrendEl.textContent = responseChange;
      responseTrendEl.className = `trend-change ${responseTrend}`;
    }
    
    if (loadTrendEl) {
      loadTrendEl.textContent = loadChange;
      loadTrendEl.className = `trend-change ${loadTrend}`;
    }
  }

  // Utility Methods
  getStatusClass(status) {
    const statusMap = {
      'healthy': 'success',
      'warning': 'warning',
      'error': 'danger'
    };
    return statusMap[status] || 'neutral';
  }

  getTrendIcon(trend) {
    const iconMap = {
      'improving': '📈',
      'stable': '➡️',
      'degrading': '📉'
    };
    return iconMap[trend] || '➡️';
  }

  getTrendClass(trend) {
    const classMap = {
      'improving': 'success',
      'stable': 'neutral',
      'degrading': 'warning'
    };
    return classMap[trend] || 'neutral';
  }

  formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleTimeString();
  }
  

  // Notification methods
  showSuccess(message) {
    console.log('SUCCESS:', message);
    alert(`✅ ${message}`);
  }

  showError(message) {
    console.error('ERROR:', message);
    alert(`❌ ${message}`);
  }

  destroy() {
    // Stop monitoring timers
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
    
    // Cleanup SmartFilter
    if (this.smartFilter) {
      this.smartFilter.destroy();
      this.smartFilter = null;
    }
    
    // Cleanup Help Panel
    if (this.helpPanel) {
      this.helpPanel.destroy();
      this.helpPanel = null;
    }
    
    // Unsubscribe from central service
    if (this.subscriptionId) {
      this.centralDataService.unsubscribe(this.subscriptionId);
    }
    
    // Clear global reference
    if (window.managersView === this) {
      delete window.managersView;
    }
    
    console.log('🧹 Managers Performance View destroyed');
  }
}

// Make instance globally accessible for onclick handlers
window.managersView = null;

export function initManagersView(container) {
  if (!window.managersView) {
    window.managersView = new ManagersView();
  }
  return window.managersView.init(container);
}