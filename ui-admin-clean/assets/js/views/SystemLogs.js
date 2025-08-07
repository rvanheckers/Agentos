/**
 * System Logs View Controller
 * Real-time log monitoring with advanced filtering and search capabilities
 */

import { SmartFilter } from '../components/SmartFilter.js';
import { getFilterPresets, getFilterTypes } from '../config/filterPresets.js';
import { getCentralDataService } from '../services/central-data-service.js';

export class SystemLogs {
  constructor(apiClient, container) {
    this.apiClient = apiClient;
    this.container = container;
    this.centralDataService = getCentralDataService(apiClient);
    this.subscriptionId = null;
    this.smartFilter = null;
    this.logs = [];
    this.categories = {};
    this.currentCategory = 'all';
    this.currentFilter = {};
    this.autoRefresh = true;
    this.isStreaming = false;
    this.maxLogs = 1000; // Maximum logs to keep in memory
  }

  async init() {
    this.render();
    this.setupSmartFilter();
    
    // Render default tab (live logs)
    this.renderLiveLogsTab();
    
    await this.loadSystemLogs();
    this.setupEventListeners();
    this.startAutoRefresh();
    
    // Fix voor ongewenste terminal/console elementen
    this.removeUnwantedElements();
  }

  render() {
    this.container.innerHTML = `
      <div class="analytics-view">
        <div class="page-header">
          <h1 class="page-header__title">
            <span class="page-header__icon">🔍</span>
            Logs & Debug
          </h1>
          <p class="page-header__description">
            Real-time log monitoring and debugging interface with advanced filtering capabilities
          </p>
        </div>

        <!-- Quick Statistics KPIs -->
        <div class="analytics-kpis" id="logsKPIs">
          <div class="kpi-card kpi-card--primary">
            <div class="kpi-card__icon">🔴</div>
            <div class="kpi-card__content">
              <div class="kpi-card__value" id="errorCount">-</div>
              <div class="kpi-card__label">Errors</div>
              <div class="kpi-card__sublabel">System Errors</div>
              <div class="kpi-card__trend" id="errorTrend">-</div>
            </div>
          </div>
          <div class="kpi-card kpi-card--secondary">
            <div class="kpi-card__icon">🟡</div>
            <div class="kpi-card__content">
              <div class="kpi-card__value" id="warningCount">-</div>
              <div class="kpi-card__label">Warnings</div>
              <div class="kpi-card__sublabel">System Warnings</div>
              <div class="kpi-card__trend" id="warningTrend">-</div>
            </div>
          </div>
          <div class="kpi-card kpi-card--tertiary">
            <div class="kpi-card__icon">🔵</div>
            <div class="kpi-card__content">
              <div class="kpi-card__value" id="infoCount">-</div>
              <div class="kpi-card__label">Info Logs</div>
              <div class="kpi-card__sublabel">Information Messages</div>
              <div class="kpi-card__trend" id="infoTrend">-</div>
            </div>
          </div>
          <div class="kpi-card kpi-card--quaternary">
            <div class="kpi-card__icon">📊</div>
            <div class="kpi-card__content">
              <div class="kpi-card__value" id="totalCount">-</div>
              <div class="kpi-card__label">Total</div>
              <div class="kpi-card__sublabel">All Log Entries</div>
              <div class="kpi-card__trend" id="totalTrend">-</div>
            </div>
          </div>
        </div>

        <!-- Smart Filter Component -->
        <div id="smartFilterContainer"></div>

        <!-- Logs Content Tabs -->
        <div class="analytics-content" id="logsContent">
          <!-- Content will be dynamically rendered based on selected tab -->
        </div>

        <!-- Detailed Log Analysis Section -->
        <div class="analytics-reports">
          <div class="analytics-card analytics-card--full">
            <div class="analytics-card__header">
              <h3 class="analytics-card__title">📋 Log Analysis & Tools</h3>
              <div class="analytics-card__actions">
                <button class="btn btn-sm btn-outline" id="refreshBtn">
                  🔄 Refresh
                </button>
                <button class="btn btn-sm btn-outline" id="clearLogsBtn">
                  🗑️ Clear
                </button>
                <button class="btn btn-sm btn-outline" id="exportLogsBtn">
                  📤 Export
                </button>
              </div>
            </div>
            <div class="analytics-card__content">
              <div id="detailedLogs" class="detailed-logs">
                <!-- Detailed logs table will be rendered here -->
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  setupSmartFilter() {
    const filterContainer = this.container.querySelector('#smartFilterContainer');
    
    this.smartFilter = new SmartFilter({
      filterTypes: getFilterTypes('logs'),
      presets: getFilterPresets('logs'),
      defaultFilter: 'errors-warnings',
      onFilterChange: (filter) => this.handleFilterChange(filter)
    });

    this.smartFilter.init(filterContainer);
  }

  setupEventListeners() {
    // =================================================================
    // HEADER ACTIONS
    // =================================================================
    
    // Refresh button
    this.container.querySelector('#refreshBtn')?.addEventListener('click', () => {
      this.loadSystemLogs();
    });

    // Clear logs button
    this.container.querySelector('#clearLogsBtn')?.addEventListener('click', () => {
      this.clearLogs();
    });

    // Export logs button
    this.container.querySelector('#exportLogsBtn')?.addEventListener('click', () => {
      this.exportLogs();
    });

    // =================================================================
    // LEFT PANEL CONTROLS
    // =================================================================

    // Auto-refresh toggle
    this.container.querySelector('#autoRefreshToggle')?.addEventListener('change', (e) => {
      this.autoRefresh = e.target.checked;
      if (this.autoRefresh) {
        this.startAutoRefresh();
      } else {
        this.stopAutoRefresh();
      }
    });

    // Follow logs toggle
    this.container.querySelector('#followLogsToggle')?.addEventListener('change', (e) => {
      this.isStreaming = e.target.checked;
      if (this.isStreaming) {
        this.scrollToBottom();
      }
    });

    // Lines select
    this.container.querySelector('#linesSelect')?.addEventListener('change', () => {
      this.loadSystemLogs();
    });

    // Log entry click for details
    this.container.addEventListener('click', (e) => {
      if (e.target && e.target.closest && e.target.closest('.log-entry')) {
        this.showLogDetails(e.target.closest('.log-entry'));
      }
    });

    // =================================================================
    // TAB CONTENT EVENT LISTENERS (handled by SmartFilter now)
    // =================================================================

    // =================================================================
    // DYNAMIC TAB EVENT LISTENERS (set up in individual tab render methods)
    // =================================================================

    // =================================================================
    // TOOLS TAB ACTIONS
    // =================================================================

    // Debug tools
    this.container.querySelector('#downloadLogfile')?.addEventListener('click', () => {
      this.downloadFullLogfile();
    });

    this.container.querySelector('#clearAllLogs')?.addEventListener('click', () => {
      this.clearAllLogs();
    });

    this.container.querySelector('#systemDiagnostics')?.addEventListener('click', () => {
      this.runSystemDiagnostics();
    });

    this.container.querySelector('#exportAnalytics')?.addEventListener('click', () => {
      this.exportAnalytics();
    });

    this.container.querySelector('#restartLogging')?.addEventListener('click', () => {
      this.restartLoggingService();
    });

    // Note: Panel splitter removed in new layout - using analytics-style tabs instead
  }

  async loadSystemLogs() {
    try {
      const linesSelect = this.container.querySelector('#linesSelect');
      const lines = parseInt(linesSelect?.value || '100');
      
      // Build filter parameters
      const category = this.buildCategoryFilter();
      
      const response = await this.apiClient.getSystemLogs(category, lines);
      
      this.logs = response.logs || [];
      this.categories = response.categories || {};
      this.currentCategory = response.current_category || 'all';
      
      // Update statistics
      this.updateStatistics();
      
      // Update filter results count
      if (this.smartFilter) {
        this.smartFilter.updateResultsCount(this.logs.length, response.total_entries || this.logs.length);
      }
      
      // Render logs
      this.renderLogs();
      
      // Update status
      this.updateStatus('Connected', 'success');
      
      console.log(`✅ Loaded ${this.logs.length} log entries`);
      
    } catch (error) {
      console.error('❌ Failed to load system logs:', error);
      this.updateStatus('Connection Error', 'error');
      this.showError('Failed to load system logs. Please try again.');
    }
  }

  buildCategoryFilter() {
    if (this.currentFilter.level && this.currentFilter.level !== 'all') {
      return this.currentFilter.level;
    }
    if (this.currentFilter.source && this.currentFilter.source !== 'all') {
      return this.currentFilter.source;
    }
    return 'all';
  }

  async handleFilterChange(filter) {
    console.log('🔍 Logs filter changed:', filter);
    this.currentFilter = filter;
    
    // Switch tab content based on filter
    switch(filter.metric) {
      case 'live-logs':
        this.renderLiveLogsTab();
        break;
      case 'search':
        this.renderSearchTab();
        break;
      case 'analysis':
        this.renderAnalysisTab();
        break;
      case 'tools':
        this.renderToolsTab();
        break;
      default:
        this.renderLiveLogsTab(); // Default to live logs
    }
    
    await this.loadSystemLogs();
  }

  renderLiveLogsTab() {
    console.log('📋 Rendering Live Logs Tab');
    const content = this.container.querySelector('#logsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">📋 Live System Logs</h2>
        <div class="tab-filters">
          <label class="control-toggle">
            <input type="checkbox" id="autoRefreshToggle" checked>
            <span>Auto-refresh</span>
          </label>
          <label class="control-toggle">
            <input type="checkbox" id="followLogsToggle">
            <span>Follow</span>
          </label>
          <select class="filter-select" id="linesSelect">
            <option value="50">50 lines</option>
            <option value="100" selected>100 lines</option>
            <option value="200">200 lines</option>
            <option value="500">500 lines</option>
            <option value="1000">1000 lines</option>
          </select>
        </div>
      </div>
      
      <div class="analytics-grid analytics-grid--full">
        <div class="analytics-card analytics-card--full">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📊 Log Stream</h3>
            <div class="analytics-card__subtitle">
              <span class="logs-status" id="logsStatus">
                <span class="logs-status-indicator"></span>
                Loading...
              </span>
            </div>
          </div>
          <div class="analytics-card__content">
            <div class="logs-content" id="logsContentStream">
              <!-- Log entries will be rendered here -->
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Setup event listeners for live logs tab
    this.setupLiveLogsEventListeners();
  }

  renderSearchTab() {
    console.log('🔍 Rendering Search Tab');
    const content = this.container.querySelector('#logsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">🔍 Advanced Search</h2>
        <div class="tab-filters">
          <input type="text" class="search-input" id="searchInput" placeholder="Search logs...">
          <button class="btn btn-primary" id="searchBtn">Search</button>
        </div>
      </div>
      
      <div class="analytics-grid analytics-grid--2x1">
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🎯 Search Options</h3>
          </div>
          <div class="analytics-card__content">
            <div class="search-options">
              <label class="search-option">
                <input type="checkbox" id="regexSearch">
                <span>Regular Expression</span>
              </label>
              <label class="search-option">
                <input type="checkbox" id="caseSensitiveSearch">
                <span>Case Sensitive</span>
              </label>
              <label class="search-option">
                <input type="checkbox" id="wholeWordSearch">
                <span>Whole Words Only</span>
              </label>
            </div>
            <div class="search-results">
              <div class="search-results__summary" id="searchResults">No active search</div>
            </div>
          </div>
        </div>
        
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📋 Search Results</h3>
          </div>
          <div class="analytics-card__content">
            <div id="searchResultsContent" class="search-results-content">
              <!-- Search results will be rendered here -->
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderAnalysisTab() {
    console.log('📊 Rendering Analysis Tab');
    const content = this.container.querySelector('#logsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">📊 Log Analysis</h2>
        <div class="tab-filters">
          <select class="filter-select" id="analysisTimeRange">
            <option value="1h">Last Hour</option>
            <option value="24h" selected>Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
      </div>
      
      <div class="analytics-grid analytics-grid--2x2">
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📈 Error Rate Trends</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="errorTrendChart"></canvas>
          </div>
        </div>
        
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🔍 Log Level Distribution</h3>
          </div>
          <div class="analytics-card__content">
            <canvas id="logLevelChart"></canvas>
          </div>
        </div>
        
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🕒 Activity Heatmap</h3>
          </div>
          <div class="analytics-card__content">
            <div id="activityHeatmap" class="heatmap-container">
              <!-- Activity heatmap will be rendered here -->
            </div>
          </div>
        </div>
        
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📋 Top Error Sources</h3>
          </div>
          <div class="analytics-card__content">
            <div id="topErrorSources" class="top-sources-list">
              <!-- Top error sources will be rendered here -->
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Render charts after DOM is ready
    setTimeout(() => {
      this.renderErrorTrendChart();
      this.renderLogLevelChart();
      this.renderActivityHeatmap();
      this.renderTopErrorSources();
    }, 100);
  }

  renderToolsTab() {
    console.log('🛠️ Rendering Tools Tab');
    const content = this.container.querySelector('#logsContent');
    
    content.innerHTML = `
      <div class="analytics-tab-header">
        <h2 class="tab-title">🛠️ Log Management Tools</h2>
      </div>
      
      <div class="analytics-grid analytics-grid--2x2">
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">📥 Export & Download</h3>
          </div>
          <div class="analytics-card__content">
            <div class="debug-actions">
              <button class="debug-action" id="downloadLogfile">
                <span class="debug-action__icon">📥</span>
                <span class="debug-action__label">Download Full Logfile</span>
              </button>
              
              <button class="debug-action" id="exportAnalytics">
                <span class="debug-action__icon">📊</span>
                <span class="debug-action__label">Export Analytics</span>
              </button>
            </div>
          </div>
        </div>
        
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🗑️ Cleanup Tools</h3>
          </div>
          <div class="analytics-card__content">
            <div class="debug-actions">
              <button class="debug-action" id="clearAllLogs">
                <span class="debug-action__icon">🗑️</span>
                <span class="debug-action__label">Clear All Logs</span>
              </button>
            </div>
          </div>
        </div>
        
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">🏥 System Diagnostics</h3>
          </div>
          <div class="analytics-card__content">
            <div class="debug-actions">
              <button class="debug-action" id="systemDiagnostics">
                <span class="debug-action__icon">🏥</span>
                <span class="debug-action__label">Run System Diagnostics</span>
              </button>
              
              <button class="debug-action" id="restartLogging">
                <span class="debug-action__icon">🔄</span>
                <span class="debug-action__label">Restart Logging Service</span>
              </button>
            </div>
          </div>
        </div>
        
        <div class="analytics-card">
          <div class="analytics-card__header">
            <h3 class="analytics-card__title">ℹ️ System Information</h3>
          </div>
          <div class="analytics-card__content">
            <div class="system-info">
              <div class="info-item">
                <span class="info-label">Log Retention:</span>
                <span class="info-value">7 days</span>
              </div>
              <div class="info-item">
                <span class="info-label">Log Size:</span>
                <span class="info-value" id="logSize">-</span>
              </div>
              <div class="info-item">
                <span class="info-label">Oldest Entry:</span>
                <span class="info-value" id="oldestEntry">-</span>
              </div>
              <div class="info-item">
                <span class="info-label">Log Format:</span>
                <span class="info-value">JSON + Text</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderLogs() {
    // Use the correct target based on current tab
    const logsContentStream = this.container.querySelector('#logsContentStream');
    const detailedLogs = this.container.querySelector('#detailedLogs');
    
    // Determine target container
    const targetContainer = logsContentStream || detailedLogs;
    
    if (!targetContainer) {
      console.warn('No logs container found, rendering live logs tab first');
      this.renderLiveLogsTab();
      return;
    }

    if (!this.logs || this.logs.length === 0) {
      targetContainer.innerHTML = `
        <div class="logs-empty">
          <div class="logs-empty__icon">📋</div>
          <div class="logs-empty__title">No logs found</div>
          <div class="logs-empty__description">
            Try adjusting your filters or check back later
          </div>
        </div>
      `;
      return;
    }

    // Filter logs based on current filter
    const filteredLogs = this.filterLogs(this.logs);

    if (logsContentStream) {
      // Terminal-style rendering for live logs
      targetContainer.innerHTML = filteredLogs.map(log => this.renderLogEntry(log)).join('');
      
      // Auto-scroll if following logs
      if (this.isStreaming) {
        this.scrollToBottom();
      }
    } else if (detailedLogs) {
      // Table-style rendering for detailed view
      this.renderDetailedLogsTable(filteredLogs, targetContainer);
    }
  }

  filterLogs(logs) {
    return logs.filter(log => {
      // Level filter
      if (this.currentFilter.level && this.currentFilter.level !== 'all') {
        if (log.level?.toLowerCase() !== this.currentFilter.level.toLowerCase()) {
          return false;
        }
      }

      // Source filter
      if (this.currentFilter.source && this.currentFilter.source !== 'all') {
        if (log.source?.toLowerCase() !== this.currentFilter.source.toLowerCase()) {
          return false;
        }
      }

      // Search filter
      if (this.currentFilter.search) {
        const searchTerm = this.currentFilter.search.toLowerCase();
        const searchableText = `${log.message} ${log.source} ${log.category}`.toLowerCase();
        if (!searchableText.includes(searchTerm)) {
          return false;
        }
      }

      return true;
    });
  }

  removeUnwantedElements() {
    // Verwijder ongewenste terminal/console elementen
    setTimeout(() => {
      const unwantedSelectors = [
        '.terminal',
        '.xterm',
        '.console',
        '[class*="terminal"]',
        '[class*="console"]',
        'iframe',
        'object',
        'embed'
      ];
      
      unwantedSelectors.forEach(selector => {
        const elements = document.querySelectorAll(`body > ${selector}`);
        elements.forEach(el => {
          if (el && el.closest && !el.closest('.system-logs-view')) {
            console.warn('Removing unwanted element:', el);
            el.remove();
          }
        });
      });
    }, 1000);
  }

  renderLogEntry(log) {
    const level = log.level?.toLowerCase() || 'info';
    const timestamp = this.formatTimestamp(log.timestamp);
    const icon = this.getLevelIcon(level);
    const message = this.escapeHtml(log.message || 'No message');
    const source = log.source || 'system';

    return `
      <div class="log-entry log-entry--${level}" data-log-id="${log.id || Math.random()}">
        <div class="log-entry__timestamp">${timestamp}</div>
        <div class="log-entry__level">
          <span class="log-level-badge log-level-badge--${level}">
            ${icon} ${level.toUpperCase()}
          </span>
        </div>
        <div class="log-entry__source">${source}</div>
        <div class="log-entry__message">${message}</div>
        ${log.context ? `
          <div class="log-entry__context">
            <details>
              <summary>Context</summary>
              <pre>${JSON.stringify(log.context, null, 2)}</pre>
            </details>
          </div>
        ` : ''}
      </div>
    `;
  }

  updateStatistics() {
    const stats = this.calculateLogStatistics();
    
    // Update KPI values
    const errorCountEl = document.getElementById('errorCount');
    const warningCountEl = document.getElementById('warningCount');
    const infoCountEl = document.getElementById('infoCount');
    const totalCountEl = document.getElementById('totalCount');
    
    if (errorCountEl) errorCountEl.textContent = stats.errors.toLocaleString();
    if (warningCountEl) warningCountEl.textContent = stats.warnings.toLocaleString();
    if (infoCountEl) infoCountEl.textContent = stats.info.toLocaleString();
    if (totalCountEl) totalCountEl.textContent = stats.total.toLocaleString();
    
    // Update trend indicators
    this.updateTrendIndicators(stats);
  }
  
  updateTrendIndicators(stats) {
    const errorTrendEl = document.getElementById('errorTrend');
    const warningTrendEl = document.getElementById('warningTrend');
    const infoTrendEl = document.getElementById('infoTrend');
    const totalTrendEl = document.getElementById('totalTrend');
    
    // Calculate trends (mock data for now)
    const errorTrend = stats.errors > 0 ? '↗ Critical' : '→ Normal';
    const warningTrend = stats.warnings > 10 ? '↗ High' : '→ Normal';
    const infoTrend = stats.info > 50 ? '↗ Active' : '→ Quiet';
    const totalTrend = stats.total > 100 ? '↗ Busy' : '→ Normal';
    
    if (errorTrendEl) errorTrendEl.textContent = errorTrend;
    if (warningTrendEl) warningTrendEl.textContent = warningTrend;
    if (infoTrendEl) infoTrendEl.textContent = infoTrend;
    if (totalTrendEl) totalTrendEl.textContent = totalTrend;
  }

  calculateLogStatistics() {
    const filteredLogs = this.filterLogs(this.logs);
    
    const errors = filteredLogs.filter(log => log.level?.toLowerCase() === 'error').length;
    const warnings = filteredLogs.filter(log => log.level?.toLowerCase() === 'warning').length;
    const info = filteredLogs.filter(log => log.level?.toLowerCase() === 'info').length;
    const total = filteredLogs.length;

    return { errors, warnings, info, total };
  }

  updateStatus(status, type = 'info') {
    const statusEl = this.container.querySelector('#logsStatus');
    const indicator = statusEl.querySelector('.logs-status-indicator');
    
    statusEl.className = `logs-header__status logs-status--${type}`;
    indicator.className = `logs-status-indicator logs-status-indicator--${type}`;
    statusEl.innerHTML = `<span class="logs-status-indicator logs-status-indicator--${type}"></span>${status}`;
  }

  clearLogs() {
    const confirmed = confirm('Are you sure you want to clear all displayed logs? This action cannot be undone.');
    if (confirmed) {
      this.logs = [];
      this.renderLogs();
      this.updateStatistics();
      console.log('🗑️ Logs cleared');
    }
  }

  exportLogs() {
    const filteredLogs = this.filterLogs(this.logs);
    const csv = this.convertLogsToCSV(filteredLogs);
    this.downloadCSV(csv, `system-logs-${new Date().toISOString().split('T')[0]}.csv`);
  }

  convertLogsToCSV(logs) {
    const headers = ['Timestamp', 'Level', 'Source', 'Message'];
    const csvRows = [headers.join(',')];

    logs.forEach(log => {
      const row = [
        log.timestamp || '',
        log.level || '',
        log.source || '',
        `"${(log.message || '').replace(/"/g, '""')}"` // Escape quotes
      ];
      csvRows.push(row.join(','));
    });

    return csvRows.join('\n');
  }

  downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  showLogDetails(logId) {
    const logData = this.logs.find(log => (log.id || Math.random().toString()) === logId);
    
    if (!logData) {
      console.warn('Log data not found for ID:', logId);
      return;
    }

    // Create a modal or alert for log details in the new layout
    alert(`Log Details:
    
Timestamp: ${this.formatTimestamp(logData.timestamp)}
Level: ${(logData.level || 'INFO').toUpperCase()}
Source: ${logData.source || 'system'}
Message: ${logData.message || 'No message'}
${logData.context ? `\nContext: ${JSON.stringify(logData.context, null, 2)}` : ''}
${logData.stack_trace ? `\nStack Trace: ${logData.stack_trace}` : ''}`);
  }

  scrollToBottom() {
    const logsContent = this.container.querySelector('#logsContentStream');
    if (logsContent) {
      logsContent.scrollTop = logsContent.scrollHeight;
    }
  }

  // Utility Methods
  getLevelIcon(level) {
    const icons = {
      'error': '🔴',
      'warning': '🟡',
      'info': '🔵',
      'debug': '⚪',
      'success': '🟢'
    };
    return icons[level] || '📋';
  }

  formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  showError(message) {
    console.error(message);
    // TODO: Implement proper error notification system
  }

  updateLogsFromCentralData(logsData) {
    if (logsData && this.autoRefresh) {
      this.logs = logsData.logs || [];
      this.categories = logsData.categories || {};
      this.currentCategory = logsData.current_category || 'all';
      
      this.updateStatistics();
      this.renderLogs();
      this.updateStatus('Connected', 'success');
    }
  }

  startAutoRefresh() {
    // Timer removed - using central data service instead
    this.subscriptionId = this.centralDataService.subscribe('SystemLogs', async (data) => {
      if (data.systemLogs) {
        this.updateLogsFromCentralData(data.systemLogs);
      }
    });
  }

  stopAutoRefresh() {
    if (this.subscriptionId) {
      this.centralDataService.unsubscribe(this.subscriptionId);
      this.subscriptionId = null;
    }
  }

  // =================================================================
  // REMOVED: OLD SPLIT PANEL FUNCTIONALITY
  // Now using analytics-style tabs managed by SmartFilter component
  // =================================================================

  // =================================================================
  // SEARCH FUNCTIONALITY (simplified for new layout)
  // =================================================================

  performSearch(searchTerm) {
    if (!searchTerm.trim()) {
      console.log('🔍 Search cleared');
      return;
    }

    console.log('🔍 Searching for:', searchTerm);
    // TODO: Implement search in the new layout
    // This will be handled by the Search tab when it's active
  }

  // =================================================================
  // ANALYSIS FUNCTIONALITY (handled in individual tab methods now)
  // =================================================================

  // =================================================================
  // TOOLS FUNCTIONALITY
  // =================================================================

  async downloadFullLogfile() {
    try {
      const response = await this.apiClient.request('/api/admin/logs/download');
      const blob = new Blob([response], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `full-system-logs-${new Date().toISOString().split('T')[0]}.log`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download logfile:', error);
      alert('Failed to download logfile');
    }
  }

  async clearAllLogs() {
    if (!confirm('⚠️ This will permanently delete ALL system logs. This action cannot be undone. Continue?')) {
      return;
    }
    
    try {
      await this.apiClient.request('/api/admin/logs/clear', { method: 'POST' });
      this.logs = [];
      this.renderLogs();
      this.updateStatistics();
      alert('✅ All logs cleared successfully');
    } catch (error) {
      console.error('Failed to clear logs:', error);
      alert('❌ Failed to clear logs');
    }
  }

  async runSystemDiagnostics() {
    try {
      const diagnostics = await this.apiClient.request('/api/admin/diagnostics');
      console.log('System Diagnostics:', diagnostics);
      alert(`System Diagnostics Complete:\n\n${JSON.stringify(diagnostics, null, 2)}`);
    } catch (error) {
      console.error('Failed to run diagnostics:', error);
      alert('❌ Failed to run system diagnostics');
    }
  }

  async exportAnalytics() {
    try {
      const analytics = await this.apiClient.request('/api/admin/logs/analytics');
      const csv = this.convertLogsToCSV(analytics.data || []);
      this.downloadCSV(csv, `log-analytics-${new Date().toISOString().split('T')[0]}.csv`);
    } catch (error) {
      console.error('Failed to export analytics:', error);
      alert('❌ Failed to export analytics');
    }
  }

  async restartLoggingService() {
    if (!confirm('🔄 This will restart the logging service. Continue?')) {
      return;
    }
    
    try {
      await this.apiClient.request('/api/admin/services/logging/restart', { method: 'POST' });
      alert('✅ Logging service restarted successfully');
      this.loadSystemLogs();
    } catch (error) {
      console.error('Failed to restart logging service:', error);
      alert('❌ Failed to restart logging service');
    }
  }

  updateSystemInfo() {
    // Mock system information - would be populated from real API
    const logSizeEl = this.container.querySelector('#logSize');
    const oldestEntryEl = this.container.querySelector('#oldestEntry');
    
    if (logSizeEl) logSizeEl.textContent = '245 MB';
    if (oldestEntryEl) oldestEntryEl.textContent = '7 days ago';
  }

  // =================================================================
  // NEW HELPER METHODS FOR UPDATED LAYOUT
  // =================================================================

  renderDetailedLogsTable(logs, container) {
    if (!logs || logs.length === 0) {
      container.innerHTML = `
        <div class="logs-empty">
          <div class="logs-empty__icon">📋</div>
          <div class="logs-empty__title">No logs found</div>
          <div class="logs-empty__description">
            Try adjusting your filters or check back later
          </div>
        </div>
      `;
      return;
    }

    const tableHTML = `
      <div class="logs-table-container">
        <table class="logs-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Level</th>
              <th>Source</th>
              <th>Message</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${logs.map(log => `
              <tr class="log-row log-row--${log.level?.toLowerCase() || 'info'}">
                <td class="log-timestamp">${this.formatTimestamp(log.timestamp)}</td>
                <td class="log-level">
                  <span class="log-level-badge log-level-badge--${log.level?.toLowerCase() || 'info'}">
                    ${this.getLevelIcon(log.level?.toLowerCase() || 'info')} ${(log.level || 'INFO').toUpperCase()}
                  </span>
                </td>
                <td class="log-source">${log.source || 'system'}</td>
                <td class="log-message">${this.escapeHtml(log.message || 'No message')}</td>
                <td class="log-actions">
                  <button class="btn btn-xs btn-ghost" onclick="this.showLogDetails('${log.id || Math.random()}')">Details</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    container.innerHTML = tableHTML;
  }

  setupLiveLogsEventListeners() {
    // Auto-refresh toggle
    const autoRefreshToggle = this.container.querySelector('#autoRefreshToggle');
    if (autoRefreshToggle) {
      autoRefreshToggle.addEventListener('change', (e) => {
        this.autoRefresh = e.target.checked;
        if (this.autoRefresh) {
          this.startAutoRefresh();
        } else {
          this.stopAutoRefresh();
        }
      });
    }

    // Follow logs toggle
    const followLogsToggle = this.container.querySelector('#followLogsToggle');
    if (followLogsToggle) {
      followLogsToggle.addEventListener('change', (e) => {
        this.isStreaming = e.target.checked;
        if (this.isStreaming) {
          this.scrollToBottom();
        }
      });
    }

    // Lines select
    const linesSelect = this.container.querySelector('#linesSelect');
    if (linesSelect) {
      linesSelect.addEventListener('change', () => {
        this.loadSystemLogs();
      });
    }
  }

  renderErrorTrendChart() {
    const canvas = this.container.querySelector('#errorTrendChart');
    if (!canvas) return;

    // Set proper canvas dimensions
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    canvas.width = rect.width * dpr;
    canvas.height = 250 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '250px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    
    // Clear canvas and draw simple chart
    ctx.clearRect(0, 0, rect.width, 250);
    
    // Mock data for error trend
    const data = [2, 5, 3, 8, 1, 4, 7, 2, 1, 3];
    const maxValue = Math.max(...data);
    const padding = 20;
    const chartWidth = rect.width - 2 * padding;
    const chartHeight = 250 - 2 * padding;
    
    // Draw grid lines
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    
    for (let i = 0; i <= 4; i++) {
      const y = padding + (i * chartHeight / 4);
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(padding + chartWidth, y);
      ctx.stroke();
    }
    
    // Draw data line
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 3;
    ctx.beginPath();
    
    data.forEach((value, index) => {
      const x = padding + (index * chartWidth / (data.length - 1));
      const y = padding + chartHeight - (value / maxValue * chartHeight);
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    
    ctx.stroke();
    
    // Draw data points
    ctx.fillStyle = '#ef4444';
    data.forEach((value, index) => {
      const x = padding + (index * chartWidth / (data.length - 1));
      const y = padding + chartHeight - (value / maxValue * chartHeight);
      
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fill();
    });
  }

  renderLogLevelChart() {
    const canvas = this.container.querySelector('#logLevelChart');
    if (!canvas) return;

    // Set proper canvas dimensions
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    canvas.width = rect.width * dpr;
    canvas.height = 250 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '250px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    
    const stats = this.calculateLogStatistics();
    
    // Clear canvas
    ctx.clearRect(0, 0, rect.width, 250);
    
    // Simple pie chart with proper sizing
    const total = stats.total || 1;
    const centerX = rect.width / 2;
    const centerY = 250 / 2;
    const radius = Math.min(centerX, centerY) - 40;
    
    let currentAngle = 0;
    const colors = ['#ef4444', '#f59e0b', '#3b82f6', '#6b7280'];
    const labels = ['Errors', 'Warnings', 'Info', 'Debug'];
    const data = [stats.errors, stats.warnings, stats.info, stats.total - stats.errors - stats.warnings - stats.info];
    
    // Draw pie slices
    data.forEach((value, index) => {
      if (value > 0) {
        const sliceAngle = (value / total) * 2 * Math.PI;
        
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
        ctx.closePath();
        ctx.fillStyle = colors[index];
        ctx.fill();
        
        // Add stroke
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        currentAngle += sliceAngle;
      }
    });
    
    // Draw center hole for donut effect
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.5, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    
    // Add center text
    ctx.fillStyle = '#374151';
    ctx.font = 'bold 16px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(total.toString(), centerX, centerY - 5);
    
    ctx.fillStyle = '#6B7280';
    ctx.font = '12px Inter, sans-serif';
    ctx.fillText('Total Logs', centerX, centerY + 15);
  }

  renderActivityHeatmap() {
    const container = this.container.querySelector('#activityHeatmap');
    if (!container) return;

    container.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <div style="font-size: 48px; margin-bottom: 8px;">🕒</div>
        <div style="font-weight: 600;">Activity Heatmap</div>
        <div style="font-size: 14px; margin-top: 4px;">24-hour activity visualization</div>
      </div>
    `;
  }

  renderTopErrorSources() {
    const container = this.container.querySelector('#topErrorSources');
    if (!container) return;

    const sources = [
      { source: 'API Server', count: 23 },
      { source: 'Worker Process', count: 12 },
      { source: 'Database', count: 8 },
      { source: 'WebSocket', count: 5 }
    ];

    container.innerHTML = sources.map((source, index) => `
      <div class="source-item">
        <div class="source-rank">#${index + 1}</div>
        <div class="source-name">${source.source}</div>
        <div class="source-count">${source.count}</div>
      </div>
    `).join('');
  }

  destroy() {
    this.stopAutoRefresh();
    if (this.smartFilter) {
      this.smartFilter.destroy();
    }
  }
}