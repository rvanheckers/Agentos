/**
 * Dashboard View Controller
 * Manages dashboard page logic and data
 */

import { TimeManager } from '../modules/TimeManager.js';
import { ActivityFeed } from '../modules/ActivityFeed.js';
import { QuickActions } from '../modules/QuickActions.js';
import { MetricManager } from '../modules/MetricManager.js';
import { getCentralDataService } from '../services/central-data-service.js';
import { HelpService } from '../services/HelpService.js';
import { HelpPanel } from '../components/HelpPanel.js';
import { DashboardHelpProvider } from '../help-providers/DashboardHelpProvider.js';

export class Dashboard {
  constructor(apiClient, container) {
    this.apiClient = apiClient;
    this.container = container;
    this.centralDataService = getCentralDataService(apiClient);
    this.subscriptionId = null;
    
    this.timeManager = new TimeManager();
    this.activityFeed = new ActivityFeed();
    this.quickActions = new QuickActions(apiClient, () => this.refreshData(), (event) => this.addActivityEvent(event));
    this.metricManager = new MetricManager();
    this.helpPanel = null;
  }

  async init() {
    this.render();
    this.setupHelpSystem();
    this.metricManager.setupMetricCards();
    this.quickActions.setupEventHandlers();
    
    // Subscribe to central data service instead of polling
    this.subscriptionId = this.centralDataService.subscribe('Dashboard', async (data) => {
      await this.updateDashboard(data);
    });
    
    // Start central data service if not running  
    if (!this.centralDataService.getStatus().isRunning) {
      this.centralDataService.start();
    } else {
      // Service is already running - FORCE fresh fetch on navigation return
      console.log('📊 Service already running, forcing fresh fetch for navigation consistency');
      await this.centralDataService.refresh();
    }
    
    this.timeManager.startTimeUpdates();
  }

  render() {
    this.container.innerHTML = `
      <div class="dashboard">
        <div class="page-header">
          <h1 class="page-header__title">
            System Dashboard
            <button class="help-icon" data-section="dashboard_overview" title="Wat is System Dashboard?">❓</button>
          </h1>
          <p class="page-header__description">Real-time monitoring of AgentOS video processing system</p>
        </div>

        <div class="metrics-grid">
          <div id="system-health-card"></div>
          <div id="workers-card"></div>
          <div id="queue-card"></div>
          <div id="jobs-card"></div>
          <div id="active-agents-card"></div>
        </div>

        <div class="dashboard-grid">
          <div class="dashboard__section dashboard__section--activity">
            <h2 class="dashboard__section-title">
              <span class="dashboard__section-icon">⚡</span>
              Recent Activity
              <button class="help-icon" data-section="recent_activity" title="Wat betekent Recent Activity?">❓</button>
            </h2>
            <div id="activity-feed" class="activity-feed">
              <div class="activity-item">
                <div class="activity-item__icon">📊</div>
                <div class="activity-item__content">
                  <div class="activity-item__title">Loading recent activity...</div>
                  <div class="activity-item__description">Fetching latest system events</div>
                  <div class="activity-item__time">Just now</div>
                </div>
              </div>
            </div>
          </div>

          <div class="dashboard__section dashboard__section--actions">
            <h2 class="dashboard__section-title">
              <span class="dashboard__section-icon">🚀</span>
              Quick Actions
              <button class="help-icon" data-section="quick_actions" title="Wat doen Quick Actions?">❓</button>
            </h2>
          <div class="quick-actions">
            <button class="quick-action" id="system-check-btn" title="Run comprehensive system health check">
              <div class="quick-action__icon">🔍</div>
              <div class="quick-action__title">System Check</div>
              <div class="quick-action__description">Run comprehensive system health check</div>
            </button>
            <button class="quick-action" id="flower-dashboard-btn" title="Open Celery monitoring dashboard">
              <div class="quick-action__icon">🌸</div>
              <div class="quick-action__title">Flower Dashboard</div>
              <div class="quick-action__description">Open Celery monitoring (localhost:5555)</div>
            </button>
            <button class="quick-action" id="restart-failed-btn" title="Restart failed jobs from today">
              <div class="quick-action__icon">🔄</div>
              <div class="quick-action__title">Restart Failed</div>
              <div class="quick-action__description">Restart failed jobs from today</div>
            </button>
            <button class="quick-action" id="export-report-btn" title="Generate and export daily system report">
              <div class="quick-action__icon">📊</div>
              <div class="quick-action__title">Daily Report</div>
              <div class="quick-action__description">Generate and export daily report</div>
            </button>
            <button class="quick-action" id="refresh-dashboard-btn" title="Refresh all dashboard data">
              <div class="quick-action__icon">🔄</div>
              <div class="quick-action__title">Refresh Data</div>
              <div class="quick-action__description">Reload all dashboard metrics</div>
            </button>
            <button class="quick-action" id="view-logs-btn" title="View recent system logs">
              <div class="quick-action__icon">📜</div>
              <div class="quick-action__title">View Logs</div>
              <div class="quick-action__description">Open logs and diagnostics</div>
            </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }



  /**
   * Update dashboard with data from central service
   * Replaces the old loadData() method that made 6+ API calls
   */
  async updateDashboard(centralData) {
    try {
      if (centralData.error) {
        console.warn('⚠️ Central data service error:', centralData.message);
        this.showError('Failed to load dashboard data');
        return;
      }

      // V4 ARCHITECTURE: Handle complete AdminDataManager response structure
      // API returns complete nested structure from AdminDataManager: {dashboard: {...}, agents_workers: {...}, analytics: {...}}
      const hasCompleteStructure = centralData.dashboard && centralData.agents_workers;
      const hasLegacyFlatStructure = centralData.workers && centralData.jobs && centralData.queue;
      
      if (!hasCompleteStructure && !hasLegacyFlatStructure) {
        console.log('⏭️ Skipping dashboard update - no recognizable data format in event');
        return;
      }

      // Update system status indicator based on SSOT data
      const systemData = hasCompleteStructure ? centralData.dashboard?.system : (hasLegacyFlatStructure ? centralData.system : null);
      if (systemData && window.adminApp) {
        const websocketStatus = systemData.websocket_status;
        const statusData = {
          connectionMode: websocketStatus === 'healthy' ? 'websocket' : 'polling',
          timestamp: centralData.timestamp,
          reconnectAttempts: 0,
          websocketConnected: websocketStatus === 'healthy'
        };
        
        if (window.adminApp.updateConnectionStatus) {
          window.adminApp.updateConnectionStatus(statusData);
        }
      }

      console.log('📊 Updating dashboard from central data service...');
      
      // V4 ARCHITECTURE: Extract data from complete AdminDataManager response
      const systemHealth = hasCompleteStructure ? centralData.dashboard?.system : centralData.system;
      const workersDetails = hasCompleteStructure ? centralData.dashboard?.workers : centralData.workers;
      const queueStatus = hasCompleteStructure ? centralData.dashboard?.queue : centralData.queue;
      const todayJobs = hasCompleteStructure ? centralData.dashboard?.jobs : centralData.jobs;
      const analytics = centralData.analytics;
      const agents = centralData.agents_workers || centralData.agents;
      
      console.log('💾 Dashboard data sources:', {
        systemHealth: systemHealth ? 'REAL' : 'NULL',
        workers: workersDetails ? 'REAL' : 'NULL', 
        queue: queueStatus ? 'REAL' : 'NULL',
        jobs: todayJobs ? 'REAL' : 'NULL',
        analytics: analytics ? 'REAL' : 'NULL',
        agents: agents ? 'REAL' : 'NULL'
      });

      // Transform system health data to expected format
      const transformedSystemHealth = this.transformSystemHealthData(systemHealth, centralData.system_control);
      const fallbackSystemHealth = transformedSystemHealth || { 
        status: 'unknown', uptime: 'N/A', cpu_usage: 0, memory_usage: 0, disk_usage: 0 
      };
      
      // Transform workers data from API format to MetricManager expected format
      const fallbackWorkers = this.transformWorkersData(workersDetails);
      
      // Transform queue data to ensure expected format
      const fallbackQueue = this.transformQueueData(queueStatus);
      
      // Transform jobs data to ensure expected format
      // FIX: Pass queue data to get completed_today and failed_today  
      const fallbackJobs = this.transformJobsData(todayJobs, queueStatus);
      
      // Transform agents data for Active Agents metric card
      const fallbackAgents = this.transformAgentsData(agents);

      console.log('✅ Dashboard updated from central service:', {
        system: fallbackSystemHealth.status,
        workers: fallbackWorkers.total || 0,
        agents: fallbackAgents.total || 0,
        queue: fallbackQueue.total || 0,
        jobs_today: fallbackJobs.total || 0,
        timestamp: centralData.timestamp
      });

      // Log transformed data structures being passed to MetricManager
      console.log('📊 Transformed data structures for MetricManager:', {
        workers: {
          hasWorkersArray: Array.isArray(fallbackWorkers.workers),
          workersCount: fallbackWorkers.workers?.length || 0,
          total: fallbackWorkers.total,
          active: fallbackWorkers.active
        },
        queue: {
          pending: fallbackQueue.pending,
          processing: fallbackQueue.processing,
          total: fallbackQueue.total
        },
        jobs: {
          completed: fallbackJobs.completed,
          failed: fallbackJobs.failed,
          total: fallbackJobs.total,
          hasJobsArray: Array.isArray(fallbackJobs.jobs)
        }
      });

      // Update all metric cards
      this.metricManager.updateSystemHealth(fallbackSystemHealth);
      this.metricManager.updateWorkers(fallbackWorkers);
      this.metricManager.updateQueue(fallbackQueue);
      this.metricManager.updateJobs(fallbackJobs);
      
      // Update pipeline tools metric from worker queues (now renamed to Worker Queues)
      const pipelineTools = this.extractPipelineTools(fallbackWorkers);
      this.updateAgentsMetric(pipelineTools);
      
      // Update Active Agents metric from actual agents data
      this.metricManager.updateActiveAgents(fallbackAgents);
      
      // Build and update activity feed
      const recentActivity = await this.buildRecentActivity(fallbackJobs, fallbackWorkers, fallbackSystemHealth);
      this.activityFeed.updateActivity(recentActivity);

    } catch (error) {
      console.error('❌ Failed to update dashboard:', error);
      this.showError('Failed to update dashboard data');
    }
  }

  async buildRecentActivity(todayJobs, workersDetails, systemHealth) {
    const events = [];
    const now = new Date();

    // Always add system startup/health event
    events.push({
      id: 'system-health',
      type: 'system',
      message: `System ${systemHealth.status} - CPU: ${systemHealth.cpu_usage}%, Memory: ${systemHealth.memory_usage}%`,
      timestamp: systemHealth.last_check || now.toISOString(),
      status: systemHealth.status,
      icon: systemHealth.status === 'healthy' ? '💚' : '⚠️'
    });

    // Add worker activity
    if (workersDetails.workers && workersDetails.workers.length > 0) {
      const activeWorkers = workersDetails.workers.filter(w => w.status === 'active');
      events.push({
        id: 'workers-status',
        type: 'system',
        message: activeWorkers.length > 0 
          ? `${activeWorkers.length} worker(s) active and ready`
          : `${workersDetails.workers.length} worker(s) idle`,
        timestamp: workersDetails.workers[0].last_heartbeat || now.toISOString(),
        status: activeWorkers.length > 0 ? 'active' : 'idle',
        icon: activeWorkers.length > 0 ? '👷' : '💤'
      });
    } else {
      // No workers found
      events.push({
        id: 'workers-none',
        type: 'system',
        message: 'No workers detected - system ready to scale',
        timestamp: now.toISOString(),
        status: 'ready',
        icon: '⚡'
      });
    }

    // Add recent jobs activity if available
    if (todayJobs.jobs && todayJobs.jobs.length > 0) {
      todayJobs.jobs.slice(0, 2).forEach(job => {
        events.push({
          id: `job-${job.id}`,
          type: 'job',
          message: `Job ${job.id.substring(0, 8)} ${job.status}`,
          timestamp: job.updated_at || job.created_at,
          status: job.status,
          icon: this.getJobIcon(job.status)
        });
      });
    } else {
      // No jobs today
      events.push({
        id: 'jobs-none',
        type: 'system',
        message: 'No jobs processed today - system ready for work',
        timestamp: now.toISOString(),
        status: 'ready',
        icon: '📋'
      });
    }

    // Add dashboard startup event
    events.push({
      id: 'dashboard-loaded',
      type: 'system',
      message: 'Dashboard loaded and monitoring active',
      timestamp: now.toISOString(),
      status: 'info',
      icon: '📊'
    });

    // Sort by timestamp (newest first)
    events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    return {
      total: events.length,
      events: events.slice(0, 5)
    };
  }

  getJobIcon(status) {
    const icons = {
      'completed': '✅',
      'processing': '⚡',
      'pending': '⏳',
      'failed': '❌',
      'queued': '📋'
    };
    return icons[status] || '📄';
  }

  transformSystemHealthData(systemHealth, systemControl) {
    try {
      console.log('🔍 transformSystemHealthData inputs:', {
        systemHealth: systemHealth,
        systemControl: systemControl ? 'present' : 'missing'
      });
      
      // Combine dashboard system health + system control uptime data
      if (!systemHealth && !systemControl) return null;
      
      // Get overall system status from service statuses
      let overallStatus = 'healthy';
      if (systemHealth) {
        const services = ['api_status', 'database_status', 'redis_status', 'websocket_status'];
        const unhealthyServices = services.filter(service => 
          systemHealth[service] && systemHealth[service] !== 'healthy'
        );
        if (unhealthyServices.length > 0) {
          overallStatus = 'degraded';
        }
      }
      
      // Get uptime from system health data (industry standard backend calculation)
      let uptime = systemHealth?.uptime || 'N/A';
      
      return {
        status: overallStatus,
        uptime: uptime,
        cpu_usage: systemHealth?.cpu_usage || 0,
        memory_usage: systemHealth?.memory_usage || 0,
        disk_usage: systemHealth?.disk_usage || 0,
        services: {
          api: systemHealth?.api_status || 'unknown',
          database: systemHealth?.database_status || 'unknown', 
          redis: systemHealth?.redis_status || 'unknown',
          websocket: systemHealth?.websocket_status || 'unknown'
        }
      };
      
    } catch (error) {
      console.error('Failed to transform system health data:', error);
      return null;
    }
  }

  transformWorkersData(workersDetails) {
    try {
      console.log('🔍 transformWorkersData input:', workersDetails);
      
      // If no workers data, return default structure
      if (!workersDetails) {
        return { 
          workers: [], 
          total: 0, 
          active: 0, 
          idle: 0,
          details: [] // Keep details for extractPipelineTools compatibility
        };
      }
      
      // Transform API format to MetricManager expected format
      // API format: {total: 1, active: 1, details: [...]}
      // MetricManager expects: {workers: [...], total: 1, active: 1}
      
      const workers = workersDetails.details || [];
      const total = workersDetails.total || 0;
      const active = workersDetails.active || 0;
      const idle = total - active;
      
      return {
        workers: workers,          // Array for MetricManager.updateWorkers()
        details: workers,          // Array for extractPipelineTools() 
        total: total,
        active: active,
        idle: idle,
        is_mock_data: workersDetails.is_mock_data || false
      };
      
    } catch (error) {
      console.error('Failed to transform workers data:', error);
      return { 
        workers: [], 
        total: 0, 
        active: 0, 
        idle: 0,
        details: []
      };
    }
  }

  transformQueueData(queueStatus) {
    try {
      console.log('🔍 transformQueueData input:', queueStatus);
      
      // If no queue data, return default structure
      if (!queueStatus) {
        return { 
          pending: 0, 
          processing: 0, 
          completed: 0, 
          failed: 0, 
          total: 0,
          is_mock_data: false
        };
      }
      
      // Ensure all required fields exist with proper defaults
      return {
        pending: queueStatus.pending || 0,
        processing: queueStatus.processing || 0,
        completed: queueStatus.completed || 0,
        failed: queueStatus.failed || 0,
        total: queueStatus.total || 0,
        is_mock_data: queueStatus.is_mock_data || false
      };
      
    } catch (error) {
      console.error('Failed to transform queue data:', error);
      return { 
        pending: 0, 
        processing: 0, 
        completed: 0, 
        failed: 0, 
        total: 0,
        is_mock_data: false
      };
    }
  }

  transformJobsData(todayJobs, queueData) {
    try {
      console.log('🔍 transformJobsData input:', todayJobs, 'queue:', queueData);
      
      // If no jobs data, return default structure
      if (!todayJobs) {
        return { 
          completed: 0, 
          processing: 0, 
          pending: 0, 
          failed: 0, 
          total: 0, 
          jobs: [],
          is_mock_data: false
        };
      }
      
      // Calculate status counts from recent_jobs array
      const recentJobs = todayJobs.recent_jobs || todayJobs.jobs || [];
      const statusCounts = recentJobs.reduce((counts, job) => {
        const status = job.status;
        counts[status] = (counts[status] || 0) + 1;
        return counts;
      }, {});
      
      // Combine both approaches: use queue data when available, fallback to calculated counts
      return {
        completed: queueData?.completed_today || statusCounts.completed || todayJobs.completed || 0,
        processing: statusCounts.processing || todayJobs.processing || 0,
        pending: statusCounts.queued || statusCounts.pending || todayJobs.pending || 0,
        failed: queueData?.failed_today || statusCounts.failed || todayJobs.failed || 0,
        cancelled: statusCounts.cancelled || 0,
        total: todayJobs.total_today || todayJobs.total || 0,  // CRITICAL FIX: Use total_today from API
        jobs: recentJobs,   // CRITICAL FIX: Use recent_jobs from API
        success_rate: todayJobs.success_rate,  // CRITICAL FIX: Pass through API success_rate
        is_mock_data: todayJobs.is_mock_data || false
      };
      
    } catch (error) {
      console.error('Failed to transform jobs data:', error);
      return { 
        completed: 0, 
        processing: 0, 
        pending: 0, 
        failed: 0, 
        total: 0, 
        jobs: [],
        is_mock_data: false
      };
    }
  }

  transformAgentsData(agents) {
    try {
      console.log('🔍 transformAgentsData input structure:', {
        hasAgents: 'agents' in agents,
        agentsType: typeof agents.agents,
        hasStatus: agents.agents && 'status' in agents.agents,
        topLevelKeys: Object.keys(agents)
      });
      
      // If no agents data, return default structure  
      if (!agents || agents.error) {
        return {
          agents: [],
          total_agents: 0,
          active_agents: 0,
          categories: [],
          error: agents?.error || null
        };
      }
      
      // Handle API response structure: agents.agents.status.agents[]
      let agentsList = [];
      let totalAgents = 0;
      let activeAgents = 0;
      
      if (agents.agents && agents.agents.status && Array.isArray(agents.agents.status.agents)) {
        // Correct API structure: agents_workers.agents.status.agents[]
        agentsList = agents.agents.status.agents;
        totalAgents = agents.agents.status.total_agents || agentsList.length;
        activeAgents = agents.agents.status.active_agents || agentsList.filter(a => a.status === 'running' || a.availability === 'available').length;
        
        console.log('🔍 Found agents via agents.agents.status.agents:', agentsList.length);
      } else if (agents.agents && Array.isArray(agents.agents)) {
        // Fallback: direct agents array
        agentsList = agents.agents;
        totalAgents = agentsList.length;
        activeAgents = agentsList.filter(a => a.status === 'running' || a.availability === 'available').length;
        
        console.log('🔍 Found agents via direct agents.agents:', agentsList.length);
      } else {
        console.log('🔍 No agents found - checking structure:', agents);
        agentsList = [];
        totalAgents = 0;
        activeAgents = 0;
      }
      
      // Extract unique categories
      const categories = [...new Set(agentsList.map(agent => agent.category))];
      
      console.log('🔍 Transformed agents result:', {
        totalAgents,
        activeAgents,
        categories: categories.length
      });
      
      return {
        agents: agentsList,
        total_agents: totalAgents,
        active_agents: activeAgents,
        categories: categories,
        error: null
      };
      
    } catch (error) {
      console.error('Failed to transform agents data:', error);
      return {
        agents: [],
        total_agents: 0, 
        active_agents: 0,
        categories: [],
        error: error.message
      };
    }
  }

  extractPipelineTools(workersData) {
    // Extract pipeline tools from worker queue information
    try {
      const tools = [];
      const uniqueQueues = new Set();
      
      if (workersData && workersData.details) {
        workersData.details.forEach(worker => {
          if (worker.queues) {
            worker.queues.forEach(queue => uniqueQueues.add(queue));
          }
        });
      }
      
      // Convert queue names to pipeline categories (not individual steps)
      const queueToCategory = {
        'video_processing': 'Video Processing',
        'transcription': 'Audio Processing', 
        'ai_analysis': 'AI Analysis',
        'file_operations': 'File Management'
      };
      
      uniqueQueues.forEach(queue => {
        const categoryName = queueToCategory[queue] || queue;
        tools.push({
          name: categoryName,
          status: 'active',
          queue: queue
        });
      });
      
      return {
        agents: tools,
        categories: [...uniqueQueues].length,
        total: tools.length
      };
      
    } catch (error) {
      console.error('Failed to extract pipeline tools:', error);
      return { agents: [], categories: 0, total: 0 };
    }
  }

  updateAgentsMetric(agents) {
    // Add pipeline tools metric to dashboard if not already present
    const agentsCard = document.getElementById('agents-card');
    if (!agentsCard) {
      // Create pipeline tools metric card dynamically
      const metricsGrid = document.querySelector('.metrics-grid');
      const agentCardHtml = '<div id="agents-card"></div>';
      metricsGrid.insertAdjacentHTML('beforeend', agentCardHtml);
    }
    
    // Update pipeline tools card
    const card = document.getElementById('agents-card');
    if (card) {
      const toolCount = agents.agents ? agents.agents.length : 0;
      const categories = agents.categories || 0; // categories is already a number, not array
      
      // Get pipeline tools description
      const toolsList = agents.agents && agents.agents.length > 0 
        ? agents.agents.map(tool => tool.name).join(', ')
        : 'No Pipeline';
      
      card.innerHTML = `
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__title">
              Worker Queues
              <button class="help-icon" data-service="worker_queues" title="Help voor Worker Queues">❓</button>
            </div>
            <div class="metric-card__status metric-card__status--good">
              good
            </div>
          </div>
          <div class="metric-card__value">${toolCount}</div>
          <div class="metric-card__description">${toolsList} (${categories} active queues)</div>
        </div>
      `;
    }
  }

  addActivityEvent(event) {
    // Add a new activity event to the feed
    const feed = document.getElementById('activity-feed');
    if (!feed) return;

    const eventHtml = `
      <div class="activity-item activity-item--new">
        <div class="activity-item__icon">${event.icon}</div>
        <div class="activity-item__content">
          <div class="activity-item__title">${event.message}</div>
          <div class="activity-item__description">${event.description}</div>
          <div class="activity-item__time">Just now</div>
        </div>
      </div>
    `;

    // Insert at the top of the feed
    feed.insertAdjacentHTML('afterbegin', eventHtml);

    // Remove oldest items if we have more than 5
    const items = feed.querySelectorAll('.activity-item');
    if (items.length > 5) {
      items[items.length - 1].remove();
    }

    // Remove the 'new' class after animation
    setTimeout(() => {
      const newItem = feed.querySelector('.activity-item--new');
      if (newItem) {
        newItem.classList.remove('activity-item--new');
      }
    }, 2000);
  }



  showError(message) {
    console.error(message);
  }

  // Manual refresh method for refresh button
  async refreshData() {
    console.log('🔄 Manual dashboard refresh triggered');
    await this.centralDataService.refresh();
  }

  setupHelpSystem() {
    // Register help provider
    HelpService.registerProvider('dashboard', DashboardHelpProvider);
    HelpService.setCurrentView('dashboard');
    
    // Create help panel
    this.helpPanel = new HelpPanel('dashboard');
    
    // Setup help icon click handlers
    document.addEventListener('click', (event) => {
      const helpIcon = event.target.closest('.help-icon');
      if (!helpIcon) return;
      
      const serviceId = helpIcon.getAttribute('data-service');
      const sectionId = helpIcon.getAttribute('data-section');
      const helpContext = serviceId || sectionId;
      
      console.log(`🆘 Help requested for context: ${helpContext}`);
      this.helpPanel.show(helpContext);
    });
    
    console.log('🆘 Dashboard help system initialized');
  }

  destroy() {
    // Unsubscribe from central data service
    if (this.subscriptionId) {
      this.centralDataService.unsubscribe(this.subscriptionId);
    }
    this.timeManager.stopTimeUpdates();
    
    // Cleanup help panel
    if (this.helpPanel) {
      this.helpPanel.destroy();
    }
  }
}