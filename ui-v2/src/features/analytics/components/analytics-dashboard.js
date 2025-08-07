/**
 * Analytics Dashboard Component
 * Displays statistics and metrics from the database
 */

import { DatabaseService } from '../services/database-service.js';

export class AnalyticsDashboard {
  constructor(container) {
    this.container = container;
    this.databaseService = new DatabaseService();
    this.stats = null;
    this.isLoading = false;
    this.refreshInterval = null;
    this.autoRefresh = true;
    this.refreshRate = 30000; // 30 seconds
  }

  /**
   * Initialize the analytics dashboard
   */
  async init() {
    console.log('📊 Initializing Analytics Dashboard');
    
    this.render();
    await this.loadDashboardData();
    this.attachEventListeners();
    
    if (this.autoRefresh) {
      this.startAutoRefresh();
    }
  }

  /**
   * Render the dashboard interface
   */
  render() {
    this.container.innerHTML = `
      <div class="analytics-dashboard">
        <div class="dashboard-header">
          <h2>📊 Analytics Dashboard</h2>
          <div class="dashboard-controls">
            <select class="timeframe-selector" aria-label="Select timeframe">
              <option value="1h">Last Hour</option>
              <option value="24h" selected>Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>
            <button class="refresh-btn" aria-label="Refresh dashboard">
              🔄 Refresh
            </button>
            <button class="auto-refresh-btn active" aria-label="Toggle auto-refresh">
              🔄 Auto
            </button>
          </div>
        </div>
        
        <div class="dashboard-content">
          <div class="loading-indicator" style="display: none;">
            <div class="spinner"></div>
            <p>Loading analytics...</p>
          </div>
          
          <div class="error-message" style="display: none;">
            <p>❌ Failed to load analytics data</p>
            <button class="retry-btn">🔄 Retry</button>
          </div>
          
          <div class="dashboard-grid">
            <!-- System Health -->
            <div class="dashboard-card health-card">
              <div class="card-header">
                <h3>💚 System Health</h3>
                <div class="health-indicator">
                  <div class="status-dot" id="db-status"></div>
                  <span id="db-status-text">Checking...</span>
                </div>
              </div>
              <div class="card-content">
                <div class="health-metrics">
                  <div class="metric">
                    <label>Database:</label>
                    <span id="db-connection">-</span>
                  </div>
                  <div class="metric">
                    <label>Tables:</label>
                    <span id="db-tables">-</span>
                  </div>
                  <div class="metric">
                    <label>Last Check:</label>
                    <span id="health-timestamp">-</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Job Statistics -->
            <div class="dashboard-card stats-card">
              <div class="card-header">
                <h3>📈 Job Statistics</h3>
                <div class="stats-summary">
                  <span id="success-rate">-</span>
                </div>
              </div>
              <div class="card-content">
                <div class="stats-grid">
                  <div class="stat-item">
                    <div class="stat-number" id="total-jobs">-</div>
                    <div class="stat-label">Total Jobs</div>
                  </div>
                  <div class="stat-item success">
                    <div class="stat-number" id="completed-jobs">-</div>
                    <div class="stat-label">Completed</div>
                  </div>
                  <div class="stat-item processing">
                    <div class="stat-number" id="processing-jobs">-</div>
                    <div class="stat-label">Processing</div>
                  </div>
                  <div class="stat-item queued">
                    <div class="stat-number" id="queued-jobs">-</div>
                    <div class="stat-label">Queued</div>
                  </div>
                  <div class="stat-item failed">
                    <div class="stat-number" id="failed-jobs">-</div>
                    <div class="stat-label">Failed</div>
                  </div>
                  <div class="stat-item clips">
                    <div class="stat-number" id="total-clips">-</div>
                    <div class="stat-label">Total Clips</div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Performance Metrics -->
            <div class="dashboard-card performance-card">
              <div class="card-header">
                <h3>⚡ Performance</h3>
                <div class="performance-indicator">
                  <div class="performance-score" id="performance-score">-</div>
                </div>
              </div>
              <div class="card-content">
                <div class="performance-metrics">
                  <div class="metric">
                    <label>Success Rate:</label>
                    <div class="metric-value">
                      <span id="success-rate-detailed">-</span>
                      <div class="progress-bar">
                        <div class="progress-fill" id="success-progress"></div>
                      </div>
                    </div>
                  </div>
                  <div class="metric">
                    <label>Avg. Processing Time:</label>
                    <span id="avg-processing-time">-</span>
                  </div>
                  <div class="metric">
                    <label>Clips per Job:</label>
                    <span id="clips-per-job">-</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Recent Activity -->
            <div class="dashboard-card activity-card">
              <div class="card-header">
                <h3>🕐 Recent Activity</h3>
                <div class="activity-count">
                  <span id="recent-count">-</span>
                </div>
              </div>
              <div class="card-content">
                <div class="activity-list" id="recent-activity">
                  <div class="activity-item placeholder">
                    <div class="activity-icon">⏳</div>
                    <div class="activity-text">Loading recent activity...</div>
                    <div class="activity-time">-</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="dashboard-footer">
            <div class="data-source-info">
              <span>💾 Data Source: Database (Persistent)</span>
              <span id="last-updated">Last Updated: -</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Load dashboard data
   */
  async loadDashboardData() {
    this.setLoading(true);
    
    try {
      const summary = await this.databaseService.getDashboardSummary();
      
      if (summary.success) {
        this.updateHealthIndicator(summary.database);
        this.updateStats(summary.analytics);
        this.updateRecentActivity(summary.recentJobs);
        this.updateTimestamp(summary.timestamp);
        
        console.log('📊 Dashboard data loaded successfully');
      } else {
        this.showError('Failed to load dashboard data: ' + summary.error);
      }
      
    } catch (error) {
      console.error('❌ Failed to load dashboard data:', error);
      this.showError('Failed to load dashboard data');
    } finally {
      this.setLoading(false);
    }
  }

  /**
   * Update health indicator
   */
  updateHealthIndicator(healthData) {
    const statusDot = this.container.querySelector('#db-status');
    const statusText = this.container.querySelector('#db-status-text');
    const connectionSpan = this.container.querySelector('#db-connection');
    const tablesSpan = this.container.querySelector('#db-tables');
    const timestampSpan = this.container.querySelector('#health-timestamp');
    
    if (healthData.success) {
      statusDot.className = 'status-dot healthy';
      statusText.textContent = 'Healthy';
      connectionSpan.textContent = '✅ Connected';
      tablesSpan.textContent = healthData.tablesAccessible ? '✅ Accessible' : '❌ Issues';
    } else {
      statusDot.className = 'status-dot unhealthy';
      statusText.textContent = 'Unhealthy';
      connectionSpan.textContent = '❌ Failed';
      tablesSpan.textContent = '❌ Inaccessible';
    }
    
    timestampSpan.textContent = this.formatTimeAgo(new Date());
  }

  /**
   * Update statistics
   */
  updateStats(analyticsData) {
    if (!analyticsData) {
      this.showStatsError();
      return;
    }
    
    // Update stat numbers
    this.container.querySelector('#total-jobs').textContent = analyticsData.totalJobs;
    this.container.querySelector('#completed-jobs').textContent = analyticsData.completedJobs;
    this.container.querySelector('#processing-jobs').textContent = analyticsData.processingJobs;
    this.container.querySelector('#queued-jobs').textContent = analyticsData.queuedJobs;
    this.container.querySelector('#failed-jobs').textContent = analyticsData.failedJobs;
    this.container.querySelector('#total-clips').textContent = analyticsData.totalClips;
    
    // Update success rate
    const successRate = analyticsData.successRateFormatted;
    this.container.querySelector('#success-rate').textContent = successRate;
    this.container.querySelector('#success-rate-detailed').textContent = successRate;
    
    // Update progress bar
    const progressBar = this.container.querySelector('#success-progress');
    progressBar.style.width = analyticsData.successRate + '%';
    
    // Update performance score
    const performanceScore = this.calculatePerformanceScore(analyticsData);
    this.container.querySelector('#performance-score').textContent = performanceScore;
    
    // Update calculated metrics
    const clipsPerJob = analyticsData.totalJobs > 0 ? 
      Math.round((analyticsData.totalClips / analyticsData.totalJobs) * 10) / 10 : 0;
    this.container.querySelector('#clips-per-job').textContent = clipsPerJob;
    
    // Placeholder for average processing time
    this.container.querySelector('#avg-processing-time').textContent = '~10s';
  }

  /**
   * Update recent activity
   */
  updateRecentActivity(recentJobs) {
    const activityList = this.container.querySelector('#recent-activity');
    const countSpan = this.container.querySelector('#recent-count');
    
    if (!recentJobs || recentJobs.length === 0) {
      activityList.innerHTML = `
        <div class="activity-item placeholder">
          <div class="activity-icon">📝</div>
          <div class="activity-text">No recent activity</div>
          <div class="activity-time">-</div>
        </div>
      `;
      countSpan.textContent = '0';
      return;
    }
    
    countSpan.textContent = recentJobs.length;
    
    activityList.innerHTML = recentJobs.map(job => `
      <div class="activity-item">
        <div class="activity-icon">${job.statusEmoji}</div>
        <div class="activity-text">
          <div class="activity-title">${job.videoTitle}</div>
          <div class="activity-subtitle">${job.userId} • ${job.status}</div>
        </div>
        <div class="activity-time">${this.formatTimeAgo(job.createdAt)}</div>
      </div>
    `).join('');
  }

  /**
   * Calculate performance score
   */
  calculatePerformanceScore(analytics) {
    const successRate = analytics.successRate;
    const totalJobs = analytics.totalJobs;
    
    if (totalJobs === 0) return 'N/A';
    
    // Simple scoring: primarily based on success rate
    if (successRate >= 90) return 'A';
    if (successRate >= 80) return 'B';
    if (successRate >= 70) return 'C';
    if (successRate >= 60) return 'D';
    return 'F';
  }

  /**
   * Update timestamp
   */
  updateTimestamp(timestamp) {
    const lastUpdated = this.container.querySelector('#last-updated');
    lastUpdated.textContent = `Last Updated: ${this.formatDate(timestamp)}`;
  }

  /**
   * Show stats error
   */
  showStatsError() {
    const statNumbers = this.container.querySelectorAll('.stat-number');
    statNumbers.forEach(el => {
      el.textContent = 'Error';
      el.classList.add('error');
    });
  }

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // Refresh button
    this.container.querySelector('.refresh-btn').addEventListener('click', () => {
      this.loadDashboardData();
    });

    // Auto-refresh toggle
    this.container.querySelector('.auto-refresh-btn').addEventListener('click', (e) => {
      this.autoRefresh = !this.autoRefresh;
      e.target.classList.toggle('active', this.autoRefresh);
      
      if (this.autoRefresh) {
        this.startAutoRefresh();
      } else {
        this.stopAutoRefresh();
      }
    });

    // Timeframe selector
    this.container.querySelector('.timeframe-selector').addEventListener('change', (e) => {
      this.timeframe = e.target.value;
      this.loadDashboardData();
    });

    // Retry button
    this.container.addEventListener('click', (e) => {
      if (e.target.classList.contains('retry-btn')) {
        this.loadDashboardData();
      }
    });
  }

  /**
   * Start auto-refresh
   */
  startAutoRefresh() {
    this.stopAutoRefresh(); // Clear existing interval
    this.refreshInterval = setInterval(() => {
      this.loadDashboardData();
    }, this.refreshRate);
    console.log('🔄 Auto-refresh started');
  }

  /**
   * Stop auto-refresh
   */
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
      console.log('🛑 Auto-refresh stopped');
    }
  }

  /**
   * Set loading state
   */
  setLoading(isLoading) {
    this.isLoading = isLoading;
    const loadingIndicator = this.container.querySelector('.loading-indicator');
    const dashboardGrid = this.container.querySelector('.dashboard-grid');
    
    if (isLoading) {
      loadingIndicator.style.display = 'block';
      dashboardGrid.style.opacity = '0.5';
    } else {
      loadingIndicator.style.display = 'none';
      dashboardGrid.style.opacity = '1';
    }
  }

  /**
   * Show error message
   */
  showError(message) {
    const errorDiv = this.container.querySelector('.error-message');
    errorDiv.querySelector('p').textContent = `❌ ${message}`;
    errorDiv.style.display = 'block';
  }

  /**
   * Format date for display
   */
  formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }).format(date);
  }

  /**
   * Format time ago
   */
  formatTimeAgo(date) {
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  }

  /**
   * Cleanup when component is destroyed
   */
  destroy() {
    this.stopAutoRefresh();
    console.log('📊 Analytics Dashboard destroyed');
  }
}

export default AnalyticsDashboard;