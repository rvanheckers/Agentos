/**
 * Performance Dashboard Component
 * 
 * Real-time monitoring van AgentOS performance en agent metrics
 */

export class PerformanceDashboard {
  constructor() {
    this.element = null;
    this.apiClient = null;
    this.refreshInterval = null;
    this.isVisible = false;
    this.metrics = {
      agents: {},
      system: {},
      workflows: {}
    };
  }

  async init(apiClient) {
    this.apiClient = apiClient;
    this.createElement();
    await this.loadInitialData();
    this.startAutoRefresh();
  }

  createElement() {
    this.element = document.createElement('div');
    this.element.className = 'performance-dashboard';
    this.element.innerHTML = `
      <div class="dashboard-header">
        <h2>🚀 AgentOS Performance Dashboard</h2>
        <div class="dashboard-controls">
          <button class="refresh-btn" onclick="performanceDashboard.refresh()">
            🔄 Refresh
          </button>
          <button class="toggle-auto-refresh" onclick="performanceDashboard.toggleAutoRefresh()">
            ⏸️ Auto-refresh
          </button>
        </div>
      </div>

      <div class="dashboard-grid">
        <!-- System Overview -->
        <div class="metric-card system-overview">
          <h3>🎯 System Overview</h3>
          <div class="metric-grid">
            <div class="metric">
              <span class="metric-label">API Status</span>
              <span class="metric-value" id="api-status">🔄 Checking...</span>
            </div>
            <div class="metric">
              <span class="metric-label">Active Agents</span>
              <span class="metric-value" id="active-agents">-</span>
            </div>
            <div class="metric">
              <span class="metric-label">Total Requests</span>
              <span class="metric-value" id="total-requests">-</span>
            </div>
            <div class="metric">
              <span class="metric-label">Success Rate</span>
              <span class="metric-value" id="success-rate">-</span>
            </div>
          </div>
        </div>

        <!-- Agent Performance -->
        <div class="metric-card agent-performance">
          <h3>🤖 Agent Performance</h3>
          <div id="agent-metrics">
            <div class="loading">Loading agent metrics...</div>
          </div>
        </div>

        <!-- MCP Context -->
        <div class="metric-card mcp-context">
          <h3>🔗 MCP Context</h3>
          <div class="metric-grid">
            <div class="metric">
              <span class="metric-label">MCP Available</span>
              <span class="metric-value" id="mcp-status">🔄 Checking...</span>
            </div>
            <div class="metric">
              <span class="metric-label">Active Sessions</span>
              <span class="metric-value" id="active-sessions">-</span>
            </div>
            <div class="metric">
              <span class="metric-label">Context Sharing</span>
              <span class="metric-value" id="context-sharing">-</span>
            </div>
            <div class="metric">
              <span class="metric-label">Avg. Chain Length</span>
              <span class="metric-value" id="avg-chain-length">-</span>
            </div>
          </div>
        </div>

        <!-- Recent Activity -->
        <div class="metric-card recent-activity">
          <h3>📊 Recent Activity</h3>
          <div id="activity-log">
            <div class="loading">Loading recent activity...</div>
          </div>
        </div>

        <!-- Performance Trends -->
        <div class="metric-card performance-trends">
          <h3>📈 Performance Trends</h3>
          <div id="trends-chart">
            <div class="trend-item">
              <span class="trend-label">Avg Response Time</span>
              <div class="trend-bar">
                <div class="trend-fill" style="width: 0%" id="avg-response-trend"></div>
              </div>
              <span class="trend-value" id="avg-response-value">-</span>
            </div>
            <div class="trend-item">
              <span class="trend-label">Throughput</span>
              <div class="trend-bar">
                <div class="trend-fill" style="width: 0%" id="throughput-trend"></div>
              </div>
              <span class="trend-value" id="throughput-value">-</span>
            </div>
            <div class="trend-item">
              <span class="trend-label">Error Rate</span>
              <div class="trend-bar error">
                <div class="trend-fill" style="width: 0%" id="error-rate-trend"></div>
              </div>
              <span class="trend-value" id="error-rate-value">-</span>
            </div>
          </div>
        </div>

        <!-- Third-party Integration -->
        <div class="metric-card third-party">
          <h3>🌐 Third-party Integration</h3>
          <div id="third-party-metrics">
            <div class="loading">Loading integration metrics...</div>
          </div>
        </div>
      </div>

      <style>
        .performance-dashboard {
          padding: 20px;
          background: var(--gray-50);
          min-height: 100vh;
        }

        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
          padding-bottom: 16px;
          border-bottom: 2px solid var(--primary-500);
        }

        .dashboard-header h2 {
          margin: 0;
          color: var(--gray-900);
        }

        .dashboard-controls {
          display: flex;
          gap: 12px;
        }

        .dashboard-controls button {
          padding: 8px 16px;
          border: none;
          border-radius: 6px;
          background: var(--primary-500);
          color: white;
          cursor: pointer;
          font-size: 14px;
          transition: background-color 0.2s;
        }

        .dashboard-controls button:hover {
          background: var(--primary-600);
        }

        .dashboard-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 20px;
        }

        .metric-card {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          border: 1px solid var(--gray-300);
        }

        .metric-card h3 {
          margin: 0 0 16px 0;
          color: var(--gray-900);
          font-size: 16px;
          font-weight: 600;
        }

        .metric-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .metric {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .metric-label {
          font-size: 12px;
          color: var(--gray-500);
          font-weight: 500;
        }

        .metric-value {
          font-size: 18px;
          font-weight: 600;
          color: var(--gray-900);
        }

        .loading {
          text-align: center;
          color: var(--gray-500);
          font-style: italic;
          padding: 20px;
        }

        .agent-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid var(--gray-200);
        }

        .agent-name {
          font-weight: 500;
          color: var(--gray-900);
        }

        .agent-stats {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: var(--gray-500);
        }

        .activity-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 0;
          font-size: 14px;
        }

        .activity-time {
          color: var(--gray-500);
          font-size: 12px;
        }

        .trend-item {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }

        .trend-label {
          min-width: 100px;
          font-size: 12px;
          color: var(--gray-500);
        }

        .trend-bar {
          flex: 1;
          height: 8px;
          background: var(--gray-200);
          border-radius: 4px;
          overflow: hidden;
        }

        .trend-fill {
          height: 100%;
          background: var(--success-500);
          transition: width 0.3s ease;
        }

        .trend-bar.error .trend-fill {
          background: var(--danger-500);
        }

        .trend-value {
          min-width: 60px;
          text-align: right;
          font-size: 12px;
          font-weight: 600;
          color: var(--gray-900);
        }

        .status-indicator {
          display: inline-block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-right: 6px;
        }

        .status-success {
          background: var(--success-500);
        }

        .status-warning {
          background: var(--warning-500);
        }

        .status-error {
          background: var(--danger-500);
        }
      </style>
    `;

    // Make dashboard available globally for button clicks
    window.performanceDashboard = this;
  }

  async loadInitialData() {
    try {
      // Load system health
      await this.updateSystemMetrics();
      
      // Load agent metrics
      await this.updateAgentMetrics();
      
      // Load MCP status
      await this.updateMCPMetrics();
      
      // Load recent activity
      await this.updateActivityLog();
      
      // Load performance trends
      await this.updatePerformanceTrends();
      
      // Load third-party metrics
      await this.updateThirdPartyMetrics();
      
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  }

  async updateSystemMetrics() {
    try {
      const response = await fetch('http://localhost:8001/health');
      const health = await response.json();
      
      document.getElementById('api-status').innerHTML = 
        `<span class="status-indicator status-success"></span>✅ ${health.status}`;
      
      // Mock additional system metrics
      document.getElementById('active-agents').textContent = '12';
      document.getElementById('total-requests').textContent = '1,247';
      document.getElementById('success-rate').textContent = '98.3%';
      
    } catch (error) {
      document.getElementById('api-status').innerHTML = 
        `<span class="status-indicator status-error"></span>❌ Offline`;
    }
  }

  async updateAgentMetrics() {
    const agentContainer = document.getElementById('agent-metrics');
    
    // Mock agent performance data
    const agents = [
      { name: 'script_generator', calls: 156, avgTime: '0.08s', success: '99.2%' },
      { name: 'moment_detector', calls: 89, avgTime: '0.12s', success: '97.8%' },
      { name: 'external_ai_enhancer', calls: 23, avgTime: '0.45s', success: '95.7%' },
      { name: 'audio_transcriber', calls: 67, avgTime: '2.34s', success: '98.5%' },
      { name: 'video_cutter', calls: 45, avgTime: '1.23s', success: '100%' }
    ];
    
    agentContainer.innerHTML = agents.map(agent => `
      <div class="agent-item">
        <span class="agent-name">${agent.name}</span>
        <div class="agent-stats">
          <span>${agent.calls} calls</span>
          <span>${agent.avgTime}</span>
          <span style="color: var(--success-500)">${agent.success}</span>
        </div>
      </div>
    `).join('');
  }

  async updateMCPMetrics() {
    // Mock MCP metrics
    document.getElementById('mcp-status').innerHTML = 
      `<span class="status-indicator status-success"></span>✅ Available`;
    document.getElementById('active-sessions').textContent = '8';
    document.getElementById('context-sharing').textContent = '94.2%';
    document.getElementById('avg-chain-length').textContent = '2.3';
  }

  async updateActivityLog() {
    const activityContainer = document.getElementById('activity-log');
    
    // Mock recent activity
    const activities = [
      { action: 'script_generator executed', time: '2 min ago' },
      { action: 'external_ai_enhancer completed', time: '5 min ago' },
      { action: 'MCP session started', time: '8 min ago' },
      { action: 'moment_detector processed', time: '12 min ago' },
      { action: 'Video upload completed', time: '15 min ago' }
    ];
    
    activityContainer.innerHTML = activities.map(activity => `
      <div class="activity-item">
        <span>${activity.action}</span>
        <span class="activity-time">${activity.time}</span>
      </div>
    `).join('');
  }

  async updatePerformanceTrends() {
    // Mock performance trends
    document.getElementById('avg-response-trend').style.width = '75%';
    document.getElementById('avg-response-value').textContent = '0.8s';
    
    document.getElementById('throughput-trend').style.width = '85%';
    document.getElementById('throughput-value').textContent = '34/min';
    
    document.getElementById('error-rate-trend').style.width = '5%';
    document.getElementById('error-rate-value').textContent = '1.2%';
  }

  async updateThirdPartyMetrics() {
    const thirdPartyContainer = document.getElementById('third-party-metrics');
    
    // Mock third-party integration metrics
    thirdPartyContainer.innerHTML = `
      <div class="metric-grid">
        <div class="metric">
          <span class="metric-label">External Agents</span>
          <span class="metric-value">3</span>
        </div>
        <div class="metric">
          <span class="metric-label">API Calls</span>
          <span class="metric-value">127</span>
        </div>
        <div class="metric">
          <span class="metric-label">Total Cost</span>
          <span class="metric-value">$2.54</span>
        </div>
        <div class="metric">
          <span class="metric-label">Avg. Latency</span>
          <span class="metric-value">0.45s</span>
        </div>
      </div>
    `;
  }

  startAutoRefresh() {
    this.refreshInterval = setInterval(() => {
      this.refresh();
    }, 30000); // Refresh every 30 seconds
  }

  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  toggleAutoRefresh() {
    const button = document.querySelector('.toggle-auto-refresh');
    
    if (this.refreshInterval) {
      this.stopAutoRefresh();
      button.textContent = '▶️ Auto-refresh';
    } else {
      this.startAutoRefresh();
      button.textContent = '⏸️ Auto-refresh';
    }
  }

  async refresh() {
    console.log('🔄 Refreshing dashboard metrics...');
    await this.loadInitialData();
    
    // Show refresh feedback
    const button = document.querySelector('.refresh-btn');
    const originalText = button.textContent;
    button.textContent = '✅ Refreshed';
    
    setTimeout(() => {
      button.textContent = originalText;
    }, 1000);
  }

  show() {
    if (this.element) {
      this.element.style.display = 'block';
      this.isVisible = true;
      this.refresh();
    }
  }

  hide() {
    if (this.element) {
      this.element.style.display = 'none';
      this.isVisible = false;
    }
  }

  destroy() {
    this.stopAutoRefresh();
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    window.performanceDashboard = null;
  }
}