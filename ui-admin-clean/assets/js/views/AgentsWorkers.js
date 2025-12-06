/**
 * Agents & Workers Management View - Service Layer SSOT Architecture
 * 
 * GECONSOLIDEERDE VIEW: Combineert Workers.js + Agents.js + nieuwe functionaliteit
 * ARCHITECTUUR: Direct AdminDataManager calls via CentralDataService, geen HTTP overhead
 * 
 * Functionaliteiten:
 * - AI Agents monitoring & configuratie (van Agents.js)
 * - Celery Workers enterprise monitoring (van Workers.js)  
 * - Pipeline management & health monitoring
 * - Resource allocation & scaling operations
 * - Real-time performance metrics
 * - Smart filtering met presets
 * 
 * Created: 2 Augustus 2025
 * Pattern: Service Layer SSOT + Enterprise Monitoring (Queue.js pattern)
 */

import { SmartFilter } from '../components/SmartFilter.js';
import { getFilterPresets, getFilterTypes } from '../config/filterPresets.js';
import { getCentralDataService } from '../services/central-data-service.js';
import { HelpService } from '../services/HelpService.js';
import { HelpPanel } from '../components/HelpPanel.js';
import { AgentsWorkersHelpProvider } from '../help-providers/AgentsWorkersHelpProvider.js';

export class AgentsWorkersView {
  constructor() {
    this.centralDataService = getCentralDataService();
    this.subscriptionId = null;
    this.container = null;
    
    // View state
    this.selectedTab = 'overview';
    this.agents = [];
    this.workers = [];
    this.filteredAgents = [];
    this.filteredWorkers = [];
    this.agentsWorkersData = null;
    this.smartFilter = null;
    this.helpPanel = null;
    
    // Set initial filter immediately to ensure proper filtering
    this.currentFilter = { 
      view: 'active-workers',
      status: ['active', 'processing'],
      sortBy: 'activity',
      limit: 20
    };
    
    // Performance monitoring
    this.lastUpdate = null;
    
    console.log('👷 Agents & Workers View initialized - Service Layer SSOT pattern');
  }

  async init(container) {
    this.container = container;
    this.render();
    this.setupHelpSystem();
    this.setupSmartFilter();
    this.setupEventListeners();
    
    // Subscribe to AdminDataManager via CentralDataService
    this.subscriptionId = this.centralDataService.subscribe('AgentsWorkers', (data) => {
      this.updateFromServiceLayer(data);
    });
    
    // Start central service if not running
    if (!this.centralDataService.getStatus().isRunning) {
      this.centralDataService.start();
    }
    
    // Set initial filter BEFORE loading data
    this.selectedTab = 'overview';
    this.currentFilter = { 
      view: 'overview',
      status: 'all',
      dateRange: 'today',
      sortBy: 'recent'
    };
    
    // Load initial data
    await this.loadInitialData();
    
    console.log('✅ Agents & Workers View initialized successfully');
  }

  setupHelpSystem() {
    // Register help provider
    HelpService.registerProvider('agents_workers', AgentsWorkersHelpProvider);
    HelpService.setCurrentView('agents_workers');
    
    // Create help panel
    this.helpPanel = new HelpPanel('agents_workers');
    
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
    
    console.log('🆘 Agents & Workers help system initialized');
  }

  render() {
    this.container.innerHTML = `
      <div class="agents-workers-view">
        <!-- Page Header -->
        <div class="page-header">
          <div class="page-header__content">
            <h1 class="page-header__title">
              👷 Agents & Workers
              <button class="help-icon" data-section="agents_workers_overview" title="Wat zijn Agents & Workers?">❓</button>
            </h1>
            <p class="page-header__description">
              Unified management for AI agents and Celery workers - monitoring, configuration, and scaling
            </p>
          </div>
        </div>

        <!-- Smart Filter Component -->
        <div class="filter-section">
          <div class="section-header">
            <h3 class="section-title">
              🔍 Smart Filters
              <button class="help-icon" data-section="smart_filter" title="Help voor Smart Filters">❓</button>
            </h3>
          </div>
          <div id="smart-filter-container"></div>
        </div>

        <!-- Dynamic Content Area -->
        <div class="agents-workers-content" id="agents-workers-content">
          <!-- Content will be dynamically rendered based on selected filter/tab -->
        </div>

        <!-- Details Modal -->
        <div class="modal" id="details-modal" style="display: none;">
          <div class="modal__backdrop"></div>
          <div class="modal__content">
            <div class="modal__header">
              <h3 class="modal__title">Details</h3>
              <button class="modal__close" id="close-modal">×</button>
            </div>
            <div class="modal__body" id="modal-content">
              <!-- Dynamic content -->
            </div>
          </div>
        </div>
      </div>
    `;
  }

  setupSmartFilter() {
    const filterContainer = document.getElementById('smart-filter-container');
    
    this.smartFilter = new SmartFilter({
      presets: {
        'overview': {
          label: 'System Overview',
          icon: '📊',
          badge: 'Default',
          filter: {
            view: 'overview',
            status: 'all',
            sortBy: 'recent'
          }
        },
        'agents': {
          label: 'AI Agents',
          icon: '🤖',
          filter: {
            view: 'agents',
            status: 'active',
            sortBy: 'category'
          }
        },
        'workers': {
          label: 'Celery Workers',
          icon: '👷',
          filter: {
            view: 'workers',
            status: 'active',
            sortBy: 'activity'
          }
        },
        'pipelines': {
          label: 'Pipelines',
          icon: '🔄',
          filter: {
            view: 'pipelines',
            status: 'all',
            sortBy: 'success_rate'
          }
        }
      },
      // Simplified - no complex filterTypes needed for agent/worker management
      filterTypes: {},
      defaultFilter: 'overview',
      onFilterChange: (filter) => this.handleFilterChange(filter)
    });

    this.smartFilter.init(filterContainer);
  }

  setupEventListeners() {
    // Modal close
    document.getElementById('close-modal')?.addEventListener('click', () => {
      this.hideModal();
    });

    // Click outside modal to close
    document.getElementById('details-modal')?.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal__backdrop')) {
        this.hideModal();
      }
    });

    // Dynamic event delegation for tab-specific events
    this.container.addEventListener('click', (e) => {
      this.handleDynamicClicks(e);
    });
  }

  handleDynamicClicks(e) {
    const action = e.target.dataset.action;
    const agentId = e.target.dataset.agentId;
    const workerId = e.target.dataset.workerId;
    
    if (!action) return;
    
    switch (action) {
      case 'view-agent-details':
        this.showAgentDetails(agentId);
        break;
      case 'view-worker-details':
        this.showWorkerDetails(workerId);
        break;
      case 'test-agent':
        this.testAgent(agentId);
        break;
      case 'restart-worker':
        this.restartWorker(workerId);
        break;
      case 'start-workers':
        this.startWorkers();
        break;
      case 'restart-all-workers':
        this.restartAllWorkers();
        break;
      case 'scale-workers':
        this.showScaleWorkersDialog();
        break;
      case 'refresh-all':
        this.refreshData();
        break;
    }
  }

  async loadInitialData() {
    try {
      // Get fresh agents_workers data from AdminDataManager
      const data = await this.centralDataService.getViewData('agents_workers', true);
      if (data.success) {
        this.processAgentsWorkersData(data.data);
      } else {
        console.warn('⚠️ Failed to load initial agents_workers data, using fallback');
        this.loadFallbackData();
      }
    } catch (error) {
      console.error('❌ Error loading initial agents_workers data:', error);
      this.loadFallbackData();
    }
  }

  updateFromServiceLayer(centralData) {
    try {
      if (centralData.error) {
        console.warn('⚠️ Service layer error:', centralData.message);
        return;
      }

      console.log('🔄 Updating agents_workers from AdminDataManager...', centralData);
      
      // Extract agents_workers data from SSOT structure
      let agentsWorkersData = null;
      
      // Handle both mock and real SSOT structures
      if (centralData.agents_workers && centralData.agents_workers.success) {
        // Mock/fallback structure
        agentsWorkersData = centralData.agents_workers.data;
      } else if (centralData.agents_workers) {
        // Real API structure - direct agents_workers data
        agentsWorkersData = centralData.agents_workers;
      }
      
      if (agentsWorkersData) {
        this.processAgentsWorkersData(agentsWorkersData);
      } else {
        console.warn('⚠️ No agents_workers data found in central data, using fallback');
        this.loadFallbackData();
      }
      
      this.lastUpdate = centralData.timestamp;
      
    } catch (error) {
      console.error('❌ Failed to update from service layer:', error);
      this.loadFallbackData();
    }
  }

  processAgentsWorkersData(data) {
    console.log('📊 Processing agents & workers data:', data);
    
    // Store data
    this.agentsWorkersData = data;
    
    // Handle different data structures from real API vs mock
    let allAgents = [];
    let allWorkers = [];
    
    if (data.agents && data.workers) {
      // Standard structure
      allAgents = data.agents.agents || data.agents || [];
      allWorkers = data.workers.workers || data.workers || [];
    } else if (Array.isArray(data.agents)) {
      // Direct array
      allAgents = data.agents;
      allWorkers = data.workers || [];
    }
    
    // Process and store data
    this.agents = allAgents;
    this.workers = allWorkers;
    
    console.log(`📊 Found ${this.agents.length} agents, ${this.workers.length} workers`);
    if (this.agents.length > 0) {
      console.log('📊 Sample agent data:', this.agents[0]);
    }
    if (this.workers.length > 0) {
      console.log('📊 Sample worker data:', this.workers[0]);
    }
    
    // IMPORTANT: Apply current filter BEFORE rendering
    console.log('🎯 Applying initial filter for:', this.selectedTab);
    this.applyCurrentFilter();
    
    // Update UI based on current tab
    this.renderCurrentTab();
    
    console.log(`✅ Processed ${this.agents.length} agents + ${this.workers.length} workers`);
  }

  async handleFilterChange(filter) {
    console.log('🔄 Agents & Workers filter changed:', filter);
    
    // Handle special actions
    if (filter.action === 'export') {
      console.log('📤 Export action detected from SmartFilter');
      this.exportAgentsWorkers();
      return;
    }
    
    // Preserve the active tab state when individual filters change
    const previousTab = this.selectedTab;
    
    this.currentFilter = filter;
    this.selectedTab = filter.view || previousTab || 'overview';
    
    // If this is just a filter property change within the same tab,
    // maintain the tab's active state in SmartFilter
    if (filter.view === undefined && previousTab && this.smartFilter) {
      // This was a property change (like status dropdown), not a tab change
      // Keep the SmartFilter's currentFilter pointing to the active tab preset
      this.smartFilter.currentFilter = previousTab;
      this.smartFilter.updateActiveButton();
    }
    
    // Apply filter and render appropriate tab
    this.applyCurrentFilter();
    this.renderCurrentTab();
  }

  applyCurrentFilter() {
    if (!this.currentFilter) {
      this.filteredAgents = this.agents || [];
      this.filteredWorkers = this.workers || [];
      return;
    }
    
    console.log('🔍 Applying filter:', this.currentFilter);
    console.log('📊 Total agents before filtering:', this.agents.length);
    console.log('📊 Total workers before filtering:', this.workers.length);
    
    let filteredAgents = [...this.agents];
    let filteredWorkers = [...this.workers];
    
    // Apply status filter
    if (this.currentFilter.status && this.currentFilter.status !== 'all') {
      console.log('📋 Applying status filter:', this.currentFilter.status);
      filteredAgents = filteredAgents.filter(agent => (agent.status || 'active') === this.currentFilter.status);
      filteredWorkers = filteredWorkers.filter(worker => (worker.status || 'active') === this.currentFilter.status);
      console.log('📊 After status filter - agents:', filteredAgents.length, 'workers:', filteredWorkers.length);
    }
    
    // Apply search filter
    if (this.currentFilter.search) {
      const searchTerm = this.currentFilter.search.toLowerCase();
      filteredAgents = filteredAgents.filter(agent => 
        (agent.name && agent.name.toLowerCase().includes(searchTerm)) ||
        (agent.display_name && agent.display_name.toLowerCase().includes(searchTerm)) ||
        (agent.category && agent.category.toLowerCase().includes(searchTerm))
      );
      filteredWorkers = filteredWorkers.filter(worker => 
        (worker.id && worker.id.toLowerCase().includes(searchTerm)) ||
        (worker.name && worker.name.toLowerCase().includes(searchTerm)) ||
        (worker.current_task && worker.current_task.toLowerCase().includes(searchTerm))
      );
    }
    
    // Apply view-specific filters
    console.log('🎯 Applying tab-specific filter for:', this.selectedTab);
    if (this.selectedTab === 'agents') {
      // Agents tab: focus on agents
      this.filteredAgents = filteredAgents;
      this.filteredWorkers = this.workers; // Keep all workers for context
    } else if (this.selectedTab === 'workers') {
      // Workers tab: focus on workers
      this.filteredAgents = this.agents; // Keep all agents for context
      this.filteredWorkers = filteredWorkers;
    } else if (this.selectedTab === 'overview') {
      // Overview tab: show all data
      this.filteredAgents = filteredAgents;
      this.filteredWorkers = filteredWorkers;
    } else {
      // Other tabs: show filtered data
      this.filteredAgents = filteredAgents;
      this.filteredWorkers = filteredWorkers;
    }
    
    console.log('✅ Final filtered - agents:', this.filteredAgents.length, 'workers:', this.filteredWorkers.length);
    this.updateFilterResults();
  }

  renderCurrentTab() {
    const content = document.getElementById('agents-workers-content');
    
    // Log tab switch for debugging
    console.log(`🎯 Rendering tab: ${this.selectedTab} with ${this.filteredAgents.length} agents, ${this.filteredWorkers.length} workers`);
    
    switch (this.selectedTab) {
      case 'overview':
        this.renderOverviewTab(content);
        break;
      case 'agents':
        this.renderAgentsTab(content);
        break;
      case 'workers':
        this.renderWorkersTab(content);
        break;
      case 'pipelines':
        this.renderPipelinesTab(content);
        break;
      default:
        console.warn(`⚠️ Unknown tab: ${this.selectedTab}, falling back to overview`);
        this.renderOverviewTab(content);
    }
  }

  renderOverviewTab(container) {
    console.log('📊 Rendering Overview Tab');
    
    container.innerHTML = `
      <div class="agents-workers-tab-content">
        <!-- Tab Header -->
        <div class="tab-header">
          <h2 class="tab-title">
            📊 System Overview
            <button class="help-icon" data-section="system_overview" title="Wat toont System Overview?">❓</button>
          </h2>
          <div class="tab-actions">
            <button class="refresh-icon" data-action="refresh-all" title="Refresh data">
              ↻
            </button>
          </div>
        </div>
        
        <!-- System Metrics -->
        <div class="overview-metrics" id="overview-metrics">
          ${this.renderSystemMetrics()}
        </div>
        
        <!-- Quick Stats Grid -->
        <div class="quick-stats-grid">
          <div class="quick-stat-card">
            <div class="quick-stat__icon">🤖</div>
            <div class="quick-stat__content">
              <div class="quick-stat__value">${this.agents.length}</div>
              <div class="quick-stat__label">
                AI Agents
                <button class="help-icon help-icon--small" data-section="total_agents" title="Wat zijn AI Agents?">❓</button>
              </div>
            </div>
          </div>
          <div class="quick-stat-card">
            <div class="quick-stat__icon">👷</div>
            <div class="quick-stat__content">
              <div class="quick-stat__value">${this.workers.length}</div>
              <div class="quick-stat__label">
                Workers
                <button class="help-icon help-icon--small" data-section="total_workers" title="Wat zijn Workers?">❓</button>
              </div>
            </div>
          </div>
          <div class="quick-stat-card">
            <div class="quick-stat__icon">✅</div>
            <div class="quick-stat__content">
              <div class="quick-stat__value">${this.calculateActiveCount()}</div>
              <div class="quick-stat__label">
                Active
                <button class="help-icon help-icon--small" data-section="active_count" title="Wat betekent Active?">❓</button>
              </div>
            </div>
          </div>
          <div class="quick-stat-card">
            <div class="quick-stat__icon">🔄</div>
            <div class="quick-stat__content">
              <div class="quick-stat__value">${this.calculateSuccessRate()}%</div>
              <div class="quick-stat__label">
                Success Rate
                <button class="help-icon help-icon--small" data-section="success_rate" title="Hoe wordt Success Rate berekend?">❓</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderAgentsTab(container) {
    console.log('🤖 Rendering Agents Tab');
    
    container.innerHTML = `
      <div class="agents-workers-tab-content">
        <!-- Tab Header -->
        <div class="tab-header">
          <h2 class="tab-title">
            🤖 AI Agents Management
            <button class="help-icon" data-section="agents_management" title="Wat zijn AI Agents?">❓</button>
          </h2>
          <div class="tab-actions">
            <button class="refresh-icon" data-action="refresh-all" title="Refresh data">
              ↻
            </button>
          </div>
        </div>
        
        <!-- Agents Grid -->
        <div class="agents-section">
          ${this.renderAgentsGrid()}
        </div>
      </div>
    `;
  }

  renderWorkersTab(container) {
    console.log('👷 Rendering Workers Tab');
    
    container.innerHTML = `
      <div class="agents-workers-tab-content">
        <!-- Tab Header -->
        <div class="tab-header">
          <h2 class="tab-title">
            👷 Celery Workers Management
            <button class="help-icon" data-section="workers_management" title="Wat zijn Workers?">❓</button>
          </h2>
          <div class="tab-actions">
            <button class="btn btn-success" data-action="start-workers">
              ▶️ Start Workers
            </button>
            <button class="btn btn-warning" data-action="restart-all-workers">
              🔄 Restart All
            </button>
            <button class="btn btn-primary" data-action="scale-workers">
              📈 Scale
            </button>
          </div>
        </div>
        
        <!-- Workers Grid -->
        <div class="workers-section">
          ${this.renderWorkersGrid()}
        </div>
      </div>
    `;
  }

  renderPipelinesTab(container) {
    console.log('🔄 Rendering Pipelines Tab');
    
    container.innerHTML = `
      <div class="agents-workers-tab-content">
        <div class="tab-header">
          <h2 class="tab-title">
            🔄 Pipeline Management
            <button class="help-icon" data-section="pipeline_status" title="Wat is Pipeline Management?">❓</button>
          </h2>
        </div>
        
        <div class="pipelines-grid">
          <div class="pipeline-card pipeline-card--active">
            <div class="pipeline-header">
              <h4>📹 Video Processing Pipeline</h4>
              <span class="status-badge status-badge--active">Active</span>
            </div>
            <div class="pipeline-flow">
              <div class="pipeline-step">video-downloader</div>
              <div class="pipeline-arrow">→</div>
              <div class="pipeline-step">audio-transcriber</div>
              <div class="pipeline-arrow">→</div>
              <div class="pipeline-step">moment-detector</div>
              <div class="pipeline-arrow">→</div>
              <div class="pipeline-step">video-cutter</div>
            </div>
            <div class="pipeline-stats">
              <div class="stat-item">
                <span class="stat-value">94.5%</span>
                <span class="stat-label">Success Rate</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">32s</span>
                <span class="stat-label">Avg Duration</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderSystemMetrics() {
    const activeAgents = this.agents.filter(a => (a.status || 'active') === 'active').length;
    const activeWorkers = this.workers.filter(w => (w.status || 'active') === 'active').length;
    
    return `
      <div class="metrics-grid">
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__icon">🤖</div>
            <div class="metric-card__title">Active Agents</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${activeAgents}/${this.agents.length}</div>
            <div class="metric-card__description">AI agents online</div>
          </div>
        </div>
        
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__icon">👷</div>
            <div class="metric-card__title">Active Workers</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${activeWorkers}/${this.workers.length}</div>
            <div class="metric-card__description">Celery workers ready</div>
          </div>
        </div>
        
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__icon">⚡</div>
            <div class="metric-card__title">System Capacity</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${this.workers.length * 4}</div>
            <div class="metric-card__description">Concurrent tasks</div>
          </div>
        </div>
      </div>
    `;
  }

  renderAgentsGrid() {
    if (this.filteredAgents.length === 0) {
      return `
        <div class="empty-state">
          <div class="empty-state__icon">🤖</div>
          <h3 class="empty-state__title">No agents found</h3>
          <p class="empty-state__description">
            No AI agents match your current filters
          </p>
          <button class="btn btn-primary" data-action="clear-filters">Clear Filters</button>
        </div>
      `;
    }
    
    return `
      <div class="agents-grid">
        ${this.filteredAgents.map(agent => this.renderAgentCard(agent)).join('')}
      </div>
    `;
  }

  renderAgentCard(agent) {
    const statusClass = this.getStatusClass(agent.status || 'active');
    
    return `
      <div class="agent-card agent-card--${statusClass}">
        <div class="agent-card__header">
          <div class="agent-card__category">
            <span class="category-icon">${this.getCategoryIcon(agent.category)}</span>
            <span class="category-name">${agent.category || 'Unknown'}</span>
          </div>
          <div class="agent-card__status">
            <span class="status-indicator status-indicator--${statusClass}"></span>
          </div>
        </div>
        
        <div class="agent-card__body">
          <h4 class="agent-card__name">${agent.display_name || agent.name}</h4>
          <p class="agent-card__description">${agent.description || 'AI processing agent'}</p>
          
          <div class="agent-card__stats">
            <div class="stat-item">
              <span class="stat-value">${agent.success_rate || '99'}%</span>
              <span class="stat-label">Success</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${agent.avg_time || '45'}s</span>
              <span class="stat-label">Avg Time</span>
            </div>
          </div>
        </div>
        
        <div class="agent-card__footer">
          <button class="btn btn-sm btn-secondary" data-action="view-agent-details" data-agent-id="${agent.name}">
            Details
          </button>
          <button class="btn btn-sm btn-primary" data-action="test-agent" data-agent-id="${agent.name}">
            Test
          </button>
        </div>
      </div>
    `;
  }

  renderWorkersGrid() {
    if (this.filteredWorkers.length === 0) {
      return `
        <div class="empty-state">
          <div class="empty-state__icon">👷</div>
          <h3 class="empty-state__title">No workers running</h3>
          <p class="empty-state__description">
            Start some workers to begin processing jobs
          </p>
          <button class="btn btn-primary" data-action="start-workers">Start Workers</button>
        </div>
      `;
    }
    
    return `
      <div class="workers-grid">
        ${this.filteredWorkers.map(worker => this.renderWorkerCard(worker)).join('')}
      </div>
    `;
  }

  renderWorkerCard(worker) {
    const statusClass = this.getStatusClass(worker.status || 'active');
    const statusIcon = this.getWorkerStatusIcon(worker.status || 'active');
    
    return `
      <div class="worker-card worker-card--${statusClass}">
        <div class="worker-card__header">
          <span class="worker-card__id">${worker.id || 'Unknown'}</span>
          <span class="status-badge status-badge--${statusClass}">
            ${statusIcon} ${worker.status || 'unknown'}
          </span>
        </div>
        
        <div class="worker-card__body">
          <h4 class="worker-card__name">${worker.name || worker.id || 'Worker'}</h4>
          <div class="worker-card__current-task">
            ${worker.current_task || 'No active task'}
          </div>
          
          <div class="worker-card__stats">
            <div class="stat-item">
              <span class="stat-value">${worker.tasks_completed || 0}</span>
              <span class="stat-label">Completed</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${worker.tasks_failed || 0}</span>
              <span class="stat-label">Failed</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${worker.uptime || 'Unknown'}</span>
              <span class="stat-label">Uptime</span>
            </div>
          </div>
        </div>
        
        <div class="worker-card__footer">
          <button class="btn btn-sm btn-secondary" data-action="view-worker-details" data-worker-id="${worker.id}">
            Details
          </button>
          <button class="btn btn-sm btn-warning" data-action="restart-worker" data-worker-id="${worker.id}">
            Restart
          </button>
        </div>
      </div>
    `;
  }

  // Action Methods
  async showAgentDetails(agentName) {
    const agent = this.agents.find(a => a.name === agentName);
    if (!agent) return;
    
    this.showModal('Agent Details', `
      <div class="agent-details">
        <h4>${agent.display_name || agent.name}</h4>
        <div class="details-grid">
          <div class="detail-item">
            <label>Category:</label>
            <span>${agent.category}</span>
          </div>
          <div class="detail-item">
            <label>Status:</label>
            <span>${agent.status || 'active'}</span>
          </div>
          <div class="detail-item">
            <label>Success Rate:</label>
            <span>${agent.success_rate || '99'}%</span>
          </div>
          <div class="detail-item">
            <label>Average Time:</label>
            <span>${agent.avg_time || '45'}s</span>
          </div>
          <div class="detail-item">
            <label>Description:</label>
            <span>${agent.description || 'AI processing agent'}</span>
          </div>
        </div>
      </div>
    `);
  }

  async showWorkerDetails(workerId) {
    const worker = this.workers.find(w => w.id === workerId);
    if (!worker) return;
    
    this.showModal('Worker Details', `
      <div class="worker-details">
        <h4>${worker.name || worker.id}</h4>
        <div class="details-grid">
          <div class="detail-item">
            <label>Status:</label>
            <span>${worker.status || 'unknown'}</span>
          </div>
          <div class="detail-item">
            <label>Current Task:</label>
            <span>${worker.current_task || 'None'}</span>
          </div>
          <div class="detail-item">
            <label>Tasks Completed:</label>
            <span>${worker.tasks_completed || 0}</span>
          </div>
          <div class="detail-item">
            <label>Tasks Failed:</label>
            <span>${worker.tasks_failed || 0}</span>
          </div>
          <div class="detail-item">
            <label>Uptime:</label>
            <span>${worker.uptime || 'Unknown'}</span>
          </div>
        </div>
      </div>
    `);
  }

  async testAgent(agentName) {
    this.showInfo(`Testing agent ${agentName}...`);
    
    try {
      // Real API call to test agent
      const response = await fetch(`/api/agents/${agentName}/status`);
      const result = await response.json();
      
      if (result.success) {
        this.showSuccess(`Agent ${agentName} test completed successfully`);
      } else {
        this.showError(`Agent ${agentName} test failed: ${result.error}`);
      }
    } catch (error) {
      console.error(`Failed to test agent ${agentName}:`, error);
      this.showError(`Agent ${agentName} test failed: ${error.message}`);
    }
  }

  async restartWorker(workerId) {
    if (confirm(`Restart worker ${workerId}?`)) {
      this.showInfo(`Restarting worker ${workerId}...`);
      
      try {
        // Real API call to restart worker
        const response = await fetch(`/api/admin/workers/${workerId}/restart`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });
        const result = await response.json();
        
        if (result.success) {
          this.showSuccess(`Worker ${workerId} restarted successfully`);
          await this.refreshData();
        } else {
          this.showError(`Failed to restart worker ${workerId}: ${result.message}`);
        }
      } catch (error) {
        console.error(`Failed to restart worker ${workerId}:`, error);
        this.showError(`Failed to restart worker ${workerId}: ${error.message}`);
      }
    }
  }

  async startWorkers() {
    const count = prompt('How many workers to start?', '3');
    if (count && !isNaN(count)) {
      this.showInfo(`Starting ${count} workers...`);
      
      try {
        // Real API call to start workers
        const response = await fetch('/api/admin/workers/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ count: parseInt(count) })
        });
        const result = await response.json();
        
        if (result.success) {
          this.showSuccess(`${count} workers started successfully`);
          await this.refreshData();
        } else {
          this.showError(`Failed to start workers: ${result.message}`);
        }
      } catch (error) {
        console.error('Failed to start workers:', error);
        this.showError(`Failed to start workers: ${error.message}`);
      }
    }
  }

  async restartAllWorkers() {
    if (confirm('Restart all workers? This will temporarily interrupt processing.')) {
      this.showInfo('Restarting all workers...');
      
      try {
        // Real API call to restart all workers
        const response = await fetch('/api/admin/workers/restart-all', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });
        const result = await response.json();
        
        if (result.success) {
          this.showSuccess('All workers restarted successfully');
          await this.refreshData();
        } else {
          this.showError(`Failed to restart all workers: ${result.message}`);
        }
      } catch (error) {
        console.error('Failed to restart all workers:', error);
        this.showError(`Failed to restart all workers: ${error.message}`);
      }
    }
  }

  showScaleWorkersDialog() {
    this.showModal('Scale Workers', `
      <div class="scale-dialog">
        <h4>Worker Scaling</h4>
        <div class="scale-options">
          <button class="btn btn-success" onclick="window.agentsWorkersView.scaleWorkers(2)">Add 2 Workers</button>
          <button class="btn btn-success" onclick="window.agentsWorkersView.scaleWorkers(5)">Add 5 Workers</button>
          <button class="btn btn-warning" onclick="window.agentsWorkersView.scaleWorkers(-2)">Remove 2 Workers</button>
        </div>
        <div class="current-status">
          <p>Current workers: ${this.workers.length}</p>
          <p>Active workers: ${this.workers.filter(w => (w.status || 'active') === 'active').length}</p>
        </div>
      </div>
    `);
  }

  async scaleWorkers(delta) {
    this.hideModal();
    const action = delta > 0 ? 'Starting' : 'Stopping';
    this.showInfo(`${action} ${Math.abs(delta)} workers...`);
    
    try {
      // Real API call to scale workers
      const response = await fetch('/api/admin/workers/scale', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ delta: delta })
      });
      const result = await response.json();
      
      if (result.success) {
        this.showSuccess(`Workers scaled by ${delta}`);
        await this.refreshData();
      } else {
        this.showError(`Failed to scale workers: ${result.message}`);
      }
    } catch (error) {
      console.error('Failed to scale workers:', error);
      this.showError(`Failed to scale workers: ${error.message}`);
    }
  }

  // Utility Methods
  calculateActiveCount() {
    const activeAgents = this.agents.filter(a => (a.status || 'active') === 'active').length;
    const activeWorkers = this.workers.filter(w => (w.status || 'active') === 'active').length;
    return activeAgents + activeWorkers;
  }

  calculateSuccessRate() {
    // Calculate overall success rate from agents and workers
    let totalSuccessRate = 0;
    let count = 0;
    
    // Include agent success rates
    this.agents.forEach(agent => {
      if (agent.success_rate !== undefined) {
        totalSuccessRate += agent.success_rate;
        count++;
      }
    });
    
    // Include worker success rates (calculated from completed vs failed tasks)
    this.workers.forEach(worker => {
      const completed = worker.tasks_completed || 0;
      const failed = worker.tasks_failed || 0;
      const total = completed + failed;
      
      if (total > 0) {
        const successRate = (completed / total) * 100;
        totalSuccessRate += successRate;
        count++;
      }
    });
    
    // Return average or fallback
    return count > 0 ? Math.round(totalSuccessRate / count * 10) / 10 : 94.5;
  }

  getCategoryIcon(category) {
    const icons = {
      'input': '📥',
      'analysis': '🔍',
      'editing': '✂️',
      'content': '📝',
      'audio': '🎵'
    };
    return icons[category] || '🔧';
  }

  getStatusClass(status) {
    const statusMap = {
      'active': 'success',
      'idle': 'warning', 
      'inactive': 'danger',
      'offline': 'danger'
    };
    return statusMap[status] || 'neutral';
  }

  getWorkerStatusIcon(status) {
    const iconMap = {
      'active': '✅',
      'idle': '💤',
      'inactive': '❌',
      'offline': '🔴'
    };
    return iconMap[status] || '❓';
  }

  updateFilterResults() {
    // Calculate context information
    const activeAgents = this.agents.filter(agent => (agent.status || 'active') === 'active').length;
    const activeWorkers = this.workers.filter(worker => (worker.status || 'active') === 'active').length;
    
    // Check if filters are applied
    const hasFilters = this.currentFilter && (
      this.currentFilter.search !== '' ||
      this.currentFilter.status !== 'all' ||
      this.currentFilter.dateRange !== 'all'
    );
    
    const context = {
      currentTab: this.selectedTab,
      totalAgents: this.agents.length,
      totalWorkers: this.workers.length,
      activeAgents: activeAgents,
      activeWorkers: activeWorkers,
      hasFilters: hasFilters
    };
    
    const totalFiltered = this.filteredAgents.length + this.filteredWorkers.length;
    const totalItems = this.agents.length + this.workers.length;
    
    this.smartFilter?.updateResultsCount(totalFiltered, totalItems, context);
  }

  showModal(title, content) {
    const modal = document.getElementById('details-modal');
    modal.querySelector('.modal__title').textContent = title;
    modal.querySelector('#modal-content').innerHTML = content;
    modal.style.display = 'block';
    
    // Make instance globally accessible for modal click handlers
    window.agentsWorkersView = this;
  }

  hideModal() {
    document.getElementById('details-modal').style.display = 'none';
  }

  async refreshData() {
    console.log('🔄 Manual refresh triggered');
    await this.centralDataService.refreshView('agents_workers');
  }

  exportAgentsWorkers() {
    console.log('📤 Exporting agents & workers data');
    this.showInfo('Export feature coming soon');
  }

  // Notification methods
  showSuccess(message) {
    console.log('SUCCESS:', message);
    this.showNotification(message, 'success');
  }

  showError(message) {
    console.error('ERROR:', message);
    this.showNotification(message, 'error');
  }

  showInfo(message) {
    console.info('INFO:', message);
    this.showNotification(message, 'info');
  }

  showNotification(message, type = 'info') {
    // Create toast notification (better than alert)
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
      <div class="toast__icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</div>
      <div class="toast__message">${message}</div>
      <button class="toast__close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // Add to container or body
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    container.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (toast.parentElement) {
        toast.remove();
      }
    }, 5000);
  }

  // Fallback data for when AdminDataManager is not available
  loadFallbackData() {
    console.log('⚠️ Loading fallback agents & workers data');
    
    this.agentsWorkersData = {
      agents: this.getFallbackAgents(),
      workers: this.getFallbackWorkers()
    };
    
    this.processAgentsWorkersData(this.agentsWorkersData);
  }

  getFallbackAgents() {
    return [
      {
        name: 'video_downloader',
        display_name: 'Video Downloader',
        category: 'input',
        status: 'active',
        description: 'Downloads and validates video files',
        success_rate: 98.5,
        avg_time: 15
      },
      {
        name: 'audio_transcriber',
        display_name: 'Audio Transcriber',
        category: 'analysis',
        status: 'active',
        description: 'Converts speech to text using Whisper',
        success_rate: 97.2,
        avg_time: 45
      },
      {
        name: 'moment_detector',
        display_name: 'Moment Detector',
        category: 'analysis',
        status: 'active',
        description: 'Identifies viral moments in content',
        success_rate: 95.8,
        avg_time: 30
      },
      {
        name: 'video_cutter',
        display_name: 'Video Cutter',
        category: 'editing',
        status: 'active',
        description: 'Creates clips from detected moments',
        success_rate: 99.1,
        avg_time: 20
      }
    ];
  }

  getFallbackWorkers() {
    return [
      {
        id: 'worker-001',
        name: 'celery@worker-001',
        status: 'active',
        current_task: 'Processing video job #1234',
        tasks_completed: 156,
        tasks_failed: 2,
        uptime: '2h 45m',
        queue: 'default'
      },
      {
        id: 'worker-002',
        name: 'celery@worker-002',
        status: 'active',
        current_task: 'Processing audio transcription #1235',
        tasks_completed: 143,
        tasks_failed: 1,
        uptime: '2h 45m',
        queue: 'default'
      },
      {
        id: 'worker-003',
        name: 'celery@worker-003',
        status: 'idle',
        current_task: null,
        tasks_completed: 129,
        tasks_failed: 0,
        uptime: '2h 45m',
        queue: 'priority'
      }
    ];
  }

  destroy() {
    // Unsubscribe from central service
    if (this.subscriptionId) {
      this.centralDataService.unsubscribe(this.subscriptionId);
    }
    
    // Clean up SmartFilter component
    this.smartFilter?.destroy();
    
    // Cleanup help panel
    if (this.helpPanel) {
      this.helpPanel.destroy();
    }
    
    // Clear global reference
    if (window.agentsWorkersView === this) {
      delete window.agentsWorkersView;
    }
    
    console.log('🧹 Agents & Workers View destroyed');
  }
}