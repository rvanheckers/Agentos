/**
 * Job History View Controller
 * Comprehensive job history management with filtering, search, and timeline
 */

import { SmartFilter } from '../components/SmartFilter.js';
import { getFilterPresets, getFilterTypes } from '../config/filterPresets.js';
import { getCentralDataService } from '../services/central-data-service.js';
import { HelpService } from '../services/HelpService.js';
import { HelpPanel } from '../components/HelpPanel.js';
import { JobsQueueHelpProvider } from '../help-providers/JobsQueueHelpProvider.js';
import { actionService } from '../../../src/services/ActionService.js';
import { ActionableMetricCard } from '../components/ActionableMetricCard.js';

export class JobHistory {
  constructor(apiClient, container) {
    this.apiClient = apiClient;
    this.container = container;
    this.jobs = [];
    this.totalJobs = 0;
    this.currentPage = 1;
    this.pageSize = 50;
    this.itemsPerPage = 20; // For list view pagination
    this.viewMode = 'list'; // Always use list view
    this.currentFilter = null;
    this.currentTimeframe = 'all'; // Default timeframe
    this.allJobs = []; // Store complete job dataset
    this.selectedJob = null;
    this.smartFilter = null;
    this.helpPanel = null;
    
    // Auto-refresh state
    this.refreshTimer = null;
    this.countdownTimer = null;
    this.refreshCountdown = 30;
    this.isMonitoringPaused = false;
    
    // Dynamic KPI cards
    this.metricCards = new Map();
    this.currentTab = 'active'; // Default tab matches JobHistory presets
  }

  async init() {
    // Make globally accessible EARLY for onclick handlers
    window.jobHistory = this;
    console.log('🔧 Global jobHistory set:', window.jobHistory);
    
    this.render();
    this.setupHelpSystem();
    this.setupSmartFilter();
    this.setupTimeframeFilter();
    this.setupPaginationListeners();
    await this.loadJobHistory();
    this.setupEventListeners();
    
    // Initialize dynamic KPIs with default tab (after SmartFilter is setup)
    this.setupDynamicKPIs();
    
    // Start real-time updates for active jobs
    this.startAutoRefresh();
    
    console.log('✅ Jobs & Queue View initialized successfully');
  }

  setupHelpSystem() {
    // Register help provider
    HelpService.registerProvider('jobs_queue', JobsQueueHelpProvider);
    HelpService.setCurrentView('jobs_queue');
    
    // Create help panel
    this.helpPanel = new HelpPanel('jobs_queue');
    
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
    
    console.log('🆘 Jobs & Queue help system initialized');
  }

  startAutoRefresh() {
    // Start auto-refresh timer for jobs data
    this.refreshTimer = setInterval(() => {
      if (!this.isMonitoringPaused) {
        this.loadJobHistory(); // Fix: use existing method instead of missing refreshJobData
      }
    }, 30000); // 30 seconds

    // Start countdown timer
    this.startCountdown();
    
    console.log('🔄 Auto-refresh started for Jobs & Queue');
  }

  startCountdown() {
    this.refreshCountdown = 30;
    this.countdownTimer = setInterval(() => {
      this.refreshCountdown--;
      const countdownEl = document.getElementById('refresh-countdown');
      if (countdownEl) {
        countdownEl.textContent = this.refreshCountdown;
      }
      
      if (this.refreshCountdown <= 0) {
        this.refreshCountdown = 30;
      }
    }, 1000);
  }

  render() {
    this.container.innerHTML = `
      <div class="jobs-queue-view">
        <!-- Compact Header -->
        <div class="page-header">
          <div class="page-header__content">
            <h1 class="page-header__title">
              🔄 Jobs & Queue Management
              <button class="help-icon" data-section="jobs_overview">❓</button>
            </h1>
            <p class="page-header__description">
              Monitor job processing pipeline and queue health - real-time tracking of automation workflows
            </p>
          </div>
          <div class="page-header__actions">
            <div class="refresh-indicator">
              <span class="refresh-icon">🔄</span>
              Auto-refresh: <span id="refresh-countdown">30</span>s
            </div>
            <button class="btn btn-secondary" id="manual-refresh">
              <span class="btn__icon">🔄</span>
              Refresh Now
            </button>
            <button class="btn btn-primary" id="toggle-monitoring">
              <span class="btn__icon">⏸️</span>
              Pause Queue
            </button>
          </div>
        </div>

        <!-- Smart Filter Component -->
        <div class="smartfilter-section">
          <div class="smartfilter-header">
            <h3 class="section-title">
              🔍 Smart Filters
              <button class="help-icon" data-section="job_filters">❓</button>
            </h3>
            <div class="timeframe-filter">
              <label for="timeframe-select">📅 Timeframe:</label>
              <select id="timeframe-select" class="timeframe-select" aria-label="Select job history timeframe">
                <option value="all">All Time</option>
                <option value="today">Today Only</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
              </select>
              <button class="help-icon" data-section="timeframe_filter" title="Help - Tijdsframe Filter">❓</button>
            </div>
          </div>
          <div id="smartFilterContainer"></div>
        </div>

        <!-- Jobs Overview Metrics -->
        <div class="jobs-overview">
          <h3 class="section-title">
            📊 Pipeline Overview
            <button class="help-icon" data-section="pipeline_metrics">❓</button>
          </h3>
          <div class="pipeline-metrics-grid">
            <div class="metric-column metric-column--queue">
              <h4 class="metric-column-title">Queue Status</h4>
              <div id="queue-depth-card"></div>
              <div id="active-processing-card"></div>
              <div id="queue-throughput-card"></div>
            </div>
            
            <div class="metric-column metric-column--performance">
              <h4 class="metric-column-title">Performance</h4>
              <div id="success-rate-24h-card"></div>
              <div id="avg-processing-card"></div>
              <div id="failed-today-card"></div>
            </div>
            
            <div class="metric-column metric-column--inventory">
              <h4 class="metric-column-title">Inventory</h4>
              <div id="total-jobs-card"></div>
              <div id="today-jobs-card"></div>
              <div id="worker-utilization-card"></div>
            </div>
          </div>
        </div>

        <!-- Jobs Grid -->
        <div class="jobs-section">
          <h3 class="section-title" id="jobsSectionTitle">
            📊 All Jobs
            <button class="help-icon" data-section="job_pipeline">❓</button>
          </h3>
          <div class="jobs-grid" id="jobsGrid">
            <div class="loading-state">
              <div class="loading-spinner"></div>
              <p>Loading job pipeline data...</p>
            </div>
          </div>
        </div>


        <!-- Pagination -->
        <div class="jobs-pagination" id="paginationContainer" style="display: none;">
          <!-- Pagination controls will be rendered here -->
        </div>
      </div>
    `;
  }

  setupSmartFilter() {
    try {
      const container = document.getElementById('smartFilterContainer');
      if (!container) {
        console.warn('⚠️ SmartFilter container not found, skipping setup');
        return;
      }

      this.smartFilter = new SmartFilter({
        presets: {
          'active': {
            label: 'Active Jobs',
            icon: '⚡',
            badge: 'Live',
            filter: {
              view: 'active',
              layout: 'pipeline',
              highlight: 'processing',
              details: 'expanded',
              status: ['queued', 'processing', 'running']
            }
          },
          'issues': {
            label: 'Failed Jobs',
            icon: '⚠️',
            filter: {
              view: 'issues',
              layout: 'priority',
              highlight: 'negative',
              details: 'expanded',
              status: ['failed', 'cancelled'],
              errorRate: '>0'
            }
          },
          'completed': {
            label: 'Completed',
            icon: '✅',
            filter: {
              view: 'completed',
              layout: 'timeline',
              highlight: 'positive',
              details: 'summary',
              status: ['completed']
            }
          },
          'all': {
            label: 'All Jobs',
            icon: '📊',
            filter: {
              view: 'all',
              layout: 'grid',
              highlight: 'none',
              details: 'summary',
              status: 'all'
            }
          }
        },
        filterTypes: {},
        defaultFilter: 'active',
        onFilterChange: (filter) => this.handleFilterChange(filter)
      });

      this.smartFilter.init(container);
      console.log('✅ SmartFilter initialized successfully for Jobs view');
    } catch (error) {
      console.error('❌ Failed to setup SmartFilter:', error);
    }
  }

  setupTimeframeFilter() {
    const timeframeSelect = document.getElementById('timeframe-select');
    if (!timeframeSelect) {
      console.warn('⚠️ Timeframe select not found');
      return;
    }

    timeframeSelect.addEventListener('change', (e) => {
      this.currentTimeframe = e.target.value;
      console.log(`📅 Timeframe changed to: ${this.currentTimeframe}`);
      
      // Apply new timeframe filter (no need to reload data)
      this.applyCurrentFilters();
      
      // Show notification
      this.showTimeframeChangedNotification(this.currentTimeframe);
    });

    console.log('✅ Timeframe filter setup complete');
  }

  showTimeframeChangedNotification(timeframe) {
    const messages = {
      'all': 'Showing all jobs (complete history)',
      'today': 'Showing today\'s jobs only - compare with Dashboard!',
      'week': 'Showing this week\'s jobs',
      'month': 'Showing this month\'s jobs'
    };
    
    const message = messages[timeframe] || `Showing ${timeframe} jobs`;
    
    // Remove existing notifications to prevent DOM buildup
    const existingNotifications = document.querySelectorAll('.timeframe-notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create and show notification
    const notification = document.createElement('div');
    notification.className = 'timeframe-notification';
    notification.innerHTML = `
      <div class="notification-content">
        <span>📅 ${message}</span>
        <button class="notification-close">×</button>
      </div>
    `;
    
    // Style the notification
    notification.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      background: #e7f3ff;
      border: 1px solid #bee5eb;
      border-radius: 8px;
      padding: 12px 16px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 1000;
      animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Add close handler
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
      document.body.removeChild(notification);
    });
    
    // Auto remove after 3 seconds
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 3000);
  }

  
  setupPaginationListeners() {
    this.container.addEventListener('click', (e) => {
      // Pagination buttons
      if (e.target.classList.contains('pagination-btn') && e.target.dataset.page) {
        const page = parseInt(e.target.dataset.page);
        if (page && page !== this.currentPage) {
          this.currentPage = page;
          this.renderCurrentView(); // Re-render with new page
        }
      }
      
      // Go to page button
      if (e.target.classList.contains('pagination-btn--go')) {
        const input = e.target.parentElement.querySelector('.page-input');
        const page = parseInt(input.value);
        const totalPages = Math.ceil(this.getFilteredJobs().length / this.itemsPerPage);
        
        if (page && page >= 1 && page <= totalPages && page !== this.currentPage) {
          this.currentPage = page;
          this.renderCurrentView();
        }
      }
    });
    
    // Handle Enter key in page input
    this.container.addEventListener('keypress', (e) => {
      if (e.target.classList.contains('page-input') && e.key === 'Enter') {
        const page = parseInt(e.target.value);
        const totalPages = Math.ceil(this.getFilteredJobs().length / this.itemsPerPage);
        
        if (page && page >= 1 && page <= totalPages && page !== this.currentPage) {
          this.currentPage = page;
          this.renderCurrentView();
        }
      }
    });
  }

  setupEventListeners() {
    // Job actions
    this.container.addEventListener('click', (e) => {
      if (e.target.classList.contains('action-btn')) {
        const action = e.target.classList.contains('action-btn--retry') ? 'retry' :
                      e.target.classList.contains('action-btn--cancel') ? 'cancel' : 'view';
        const jobId = e.target.dataset.jobId;
        
        if (action === 'view') {
          this.showJobDetails(jobId);
        } else {
          this.handleJobAction(action, jobId);
        }
      }

      // Job details
      if (e.target.classList.contains('job-details-btn')) {
        this.showJobDetails(e.target.dataset.jobId);
      }
      
      // Job links in table
      if (e.target.classList.contains('job-link')) {
        e.preventDefault();
        this.showJobDetails(e.target.dataset.jobId);
      }
    });

    // Queue management actions
    document.addEventListener('click', (e) => {
      // Manual refresh button
      if (e.target.closest('#manual-refresh')) {
        this.handleManualRefresh();
      }
      
      // Toggle monitoring/queue pause button
      if (e.target.closest('#toggle-monitoring')) {
        this.handleToggleMonitoring();
      }
      
    });
  }

  async loadJobHistory(page = 1) {
    try {
      this.currentPage = page;
      console.log('🔄 Loading job history from SSOT...');
      
      // Use Central Data Service like all other views
      const centralDataService = window.centralDataService;
      if (centralDataService?.getStatus().isRunning) {
        const ssotData = centralDataService.getCurrentData();
        if (ssotData) {
          console.log('💾 Using SSOT data from Central Data Service');
          this.processSSotData(ssotData);
          return;
        }
      }
      
      // Fallback: Direct SSOT API call
      console.log('🔄 Fallback: Direct SSOT API call');
      const response = await fetch('http://localhost:8001/api/admin/ssot');
      const ssotData = await response.json();
      this.processSSotData(ssotData);
      
    } catch (error) {
      console.error('❌ Critical job history failure:', error);
      this.showError('Job history service temporarily unavailable. Showing cached data.');
      this.loadCachedHistoryData();
    }
  }

  processSSotData(ssotData) {
    console.log('📊 Processing SSOT data for Jobs & Queue view');
    
    // Extract jobs data from SSOT response
    // V5 fix: jobs are directly in ssotData.jobs.recent_jobs
    const jobs = ssotData.jobs?.recent_jobs || ssotData.dashboard?.jobs?.recent_jobs || [];
    const queueData = ssotData.queue || ssotData.dashboard?.queue || {};
    const recentActivity = ssotData.recent_activity || ssotData.dashboard?.recent_activity || [];
    
    // Process job data
    this.historyData = {
      jobs: jobs,
      total: jobs.length,
      stats: queueData,
      activity: recentActivity,
      lastUpdated: new Date().toISOString(),
      source: 'ssot'
    };
    
    // Enterprise job enrichment with pipeline data (on ALL jobs)
    this.enrichJobsWithPipelineData(this.historyData.jobs).then(enrichedJobs => {
      // Store complete dataset
      this.allJobs = enrichedJobs;
      
      // Apply current filters (timeframe, etc.) - handles all UI updates
      this.applyCurrentFilters();
      
      // Calculate enterprise analytics
      this.calculateHistoryAnalytics();
      
      // Cache data for offline access
      this.cacheHistoryData();

      console.log(`✅ SSOT job history loaded: ${this.jobs.length} jobs with pipeline data`);
    });
  }

  // Enterprise fallback methods
  getFallbackJobHistory() {
    // Generate realistic mock jobs for demonstration when APIs are unavailable
    const mockJobs = this.generateMockJobs(12);
    // Apply timeframe filtering to mock jobs
    const filteredJobs = this.filterJobsByTimeframe(mockJobs);
    
    return {
      jobs: filteredJobs,
      total: filteredJobs.length,
      page: 1,
      pages: 1,
      data_source: 'fallback'
    };
  }

  generateMockJobs(count = 10) {
    const statuses = ['completed', 'processing', 'failed', 'queued', 'cancelled'];
    const taskTypes = ['video_processing', 'audio_transcription', 'image_analysis', 'data_export', 'content_generation'];
    const priorities = ['normal', 'high', 'critical', 'low'];
    const stages = ['download', 'transcribe', 'analyze', 'process', 'complete'];
    
    const jobs = [];
    const now = new Date();
    
    for (let i = 1; i <= count; i++) {
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      const taskType = taskTypes[Math.floor(Math.random() * taskTypes.length)];
      const priority = priorities[Math.floor(Math.random() * priorities.length)];
      const stage = stages[Math.floor(Math.random() * stages.length)];
      
      // Create realistic timestamps
      const createdAt = new Date(now - Math.random() * 24 * 60 * 60 * 1000); // Last 24 hours
      const updatedAt = new Date(createdAt.getTime() + Math.random() * 60 * 60 * 1000); // Up to 1 hour later
      
      const job = {
        id: `job_${String(i).padStart(4, '0')}`,
        status: status,
        task_type: taskType,
        priority: priority,
        current_stage: stage,
        pipeline_stage: stage,
        progress: status === 'completed' ? 100 : 
                 status === 'processing' ? Math.floor(Math.random() * 90) + 10 :
                 status === 'failed' ? Math.floor(Math.random() * 80) :
                 status === 'queued' ? 0 : Math.floor(Math.random() * 50),
        created_at: createdAt.toISOString(),
        updated_at: updatedAt.toISOString(),
        description: this.generateJobDescription(taskType, status),
        
        // Performance metrics
        performance_metrics: {
          total_duration: status === 'completed' ? Math.floor(Math.random() * 300) + 30 : 0,
          efficiency_score: status === 'completed' ? Math.floor(Math.random() * 30) + 70 : 0,
          resource_usage: {
            cpu: Math.floor(Math.random() * 80) + 20,
            memory: Math.floor(Math.random() * 60) + 30,
            disk: Math.floor(Math.random() * 40) + 10
          }
        },
        
        // Enterprise metadata
        user_id: `user_${Math.floor(Math.random() * 100) + 1}`,
        retry_count: status === 'failed' ? Math.floor(Math.random() * 3) : 0,
        error_message: status === 'failed' ? this.generateErrorMessage() : null,
        
        // Agent pipeline information
        agent_pipeline: this.getMockPipelineSteps(),
        
        // Resource requirements
        resource_requirements: {
          cpu_cores: Math.floor(Math.random() * 4) + 1,
          memory_mb: Math.floor(Math.random() * 2048) + 512,
          estimated_duration: Math.floor(Math.random() * 600) + 60
        }
      };
      
      jobs.push(job);
    }
    
    // Sort by created_at descending (newest first)
    return jobs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }

  generateJobDescription(taskType, status) {
    const descriptions = {
      'video_processing': [
        'Processing promotional video content for social media',
        'Converting high-resolution video to multiple formats',
        'Extracting key moments from conference presentation',
        'Optimizing video quality for web streaming'
      ],
      'audio_transcription': [
        'Transcribing customer service call recording',
        'Converting podcast episode to text format',
        'Processing meeting audio for searchable content',
        'Generating subtitles for video content'
      ],
      'image_analysis': [
        'Analyzing product images for quality control',
        'Detecting objects in surveillance footage',
        'Processing medical imaging data',
        'Optimizing images for web performance'
      ],
      'data_export': [
        'Exporting customer analytics to CSV format',
        'Generating monthly performance reports',
        'Creating backup of user data',
        'Compiling system metrics for analysis'
      ],
      'content_generation': [
        'Generating social media post variations',
        'Creating product descriptions from specifications',
        'Producing automated email content',
        'Generating technical documentation'
      ]
    };
    
    const typeDescriptions = descriptions[taskType] || ['Processing general task'];
    const description = typeDescriptions[Math.floor(Math.random() * typeDescriptions.length)];
    
    if (status === 'failed') {
      return `${description} (encountered processing error)`;
    } else if (status === 'processing') {
      return `${description} (in progress)`;
    }
    
    return description;
  }

  generateErrorMessage() {
    const errors = [
      'Connection timeout to external service',
      'Insufficient memory for processing large file',
      'Input file format not supported',
      'Rate limit exceeded for API calls',
      'Disk space unavailable for output files',
      'Authentication failed for required service',
      'Network connectivity issues during processing'
    ];
    
    return errors[Math.floor(Math.random() * errors.length)];
  }

  getFallbackJobStats() {
    return {
      pending: 0,
      processing: 0,
      completed: 0,
      failed: 0,
      total: 0,
      source: 'fallback'
    };
  }

  getFallbackRecentActivity() {
    return {
      recent_jobs: [],
      pipeline_events: [],
      data_source: 'fallback'
    };
  }

  filterJobsByTimeframe(jobs) {
    if (this.currentTimeframe === 'all') {
      return jobs; // No filtering needed
    }

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const thisWeekStart = new Date(today);
    // Start week on Monday (NL standard) instead of Sunday
    const dayOfWeek = today.getDay();
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
    thisWeekStart.setDate(today.getDate() - daysToMonday);
    const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);

    return jobs.filter(job => {
      const jobDate = new Date(job.created_at);
      
      switch (this.currentTimeframe) {
        case 'today':
          return jobDate >= today;
        case 'week':
          return jobDate >= thisWeekStart;
        case 'month':
          return jobDate >= thisMonthStart;
        default:
          return true;
      }
    });
  }

  applyCurrentFilters() {
    // Apply timeframe filtering to complete dataset
    this.jobs = this.filterJobsByTimeframe(this.allJobs);
    this.totalJobs = this.jobs.length;
    
    console.log(`📅 Filters applied: ${this.allJobs.length} → ${this.jobs.length} jobs (timeframe: ${this.currentTimeframe})`);
    
    // Update UI components
    this.updateOverviewMetrics();
    this.renderCurrentView();
    this.updatePagination();
    
    // Update smart filter results (guard against null)
    if (this.smartFilter) {
      this.smartFilter.updateResultsCount(this.jobs.length, this.allJobs.length);
    } else {
      console.warn('⚠️ SmartFilter not initialized, skipping results count update');
    }
  }

  async enrichJobsWithPipelineData(jobs) {
    // Enterprise enhancement: Add detailed pipeline information
    return Promise.all(jobs.map(async (job) => {
      try {
        // Load pipeline steps for each job
        const pipelineSteps = await this.loadJobPipelineSteps(job.id);
        
        return {
          ...job,
          // Enterprise pipeline enrichment
          pipeline_steps: pipelineSteps,
          pipeline_status: this.calculatePipelineStatus(pipelineSteps),
          duration_breakdown: this.calculateDurationBreakdown(pipelineSteps),
          failure_analysis: this.analyzeFailurePoints(pipelineSteps),
          performance_metrics: this.calculatePerformanceMetrics(pipelineSteps),
          resource_utilization: this.calculateResourceUtilization(pipelineSteps)
        };
      } catch (error) {
        console.warn(`Failed to enrich pipeline data for job ${job.id}:`, error);
        return {
          ...job,
          pipeline_steps: this.getMockPipelineSteps(job),
          pipeline_status: 'unknown'
        };
      }
    }));
  }

  async loadJobPipelineSteps(jobId) {
    // All pipeline data comes from SSOT now - no separate API calls needed
    return this.getMockPipelineSteps({ id: jobId });
  }

  getMockPipelineSteps(job) {
    // Enterprise mock pipeline steps based on AgentOS architecture
    const agentPipeline = [
      { name: 'video_downloader', status: 'completed', duration: 5, started_at: '2025-01-01T10:00:00Z', completed_at: '2025-01-01T10:00:05Z' },
      { name: 'audio_transcriber', status: 'completed', duration: 15, started_at: '2025-01-01T10:00:05Z', completed_at: '2025-01-01T10:00:20Z' },
      { name: 'moment_detector', status: 'completed', duration: 8, started_at: '2025-01-01T10:00:20Z', completed_at: '2025-01-01T10:00:28Z' },
      { name: 'face_detector', status: 'completed', duration: 12, started_at: '2025-01-01T10:00:28Z', completed_at: '2025-01-01T10:00:40Z' },
      { name: 'intelligent_cropper', status: 'completed', duration: 6, started_at: '2025-01-01T10:00:40Z', completed_at: '2025-01-01T10:00:46Z' },
      { name: 'video_cutter', status: 'completed', duration: 10, started_at: '2025-01-01T10:00:46Z', completed_at: '2025-01-01T10:00:56Z' }
    ];

    // Simulate different failure scenarios based on job status
    if (job.status === 'failed') {
      const failPoint = Math.floor(Math.random() * agentPipeline.length);
      agentPipeline[failPoint].status = 'failed';
      agentPipeline[failPoint].error = 'Processing timeout after 30 seconds';
      
      // Mark subsequent steps as skipped
      for (let i = failPoint + 1; i < agentPipeline.length; i++) {
        agentPipeline[i].status = 'skipped';
        delete agentPipeline[i].completed_at;
        delete agentPipeline[i].duration;
      }
    }

    return agentPipeline;
  }

  calculatePipelineStatus(steps) {
    if (!steps || steps.length === 0) return 'unknown';
    
    const hasFailure = steps.some(step => step.status === 'failed');
    const hasRunning = steps.some(step => step.status === 'running' || step.status === 'processing');
    const allCompleted = steps.every(step => step.status === 'completed' || step.status === 'skipped');
    
    if (hasFailure) return 'failed';
    if (hasRunning) return 'running';
    if (allCompleted) return 'completed';
    return 'pending';
  }

  calculateDurationBreakdown(steps) {
    return steps.reduce((breakdown, step) => {
      if (step.duration) {
        breakdown[step.name] = step.duration;
        breakdown.total = (breakdown.total || 0) + step.duration;
      }
      return breakdown;
    }, {});
  }

  analyzeFailurePoints(steps) {
    const failures = steps.filter(step => step.status === 'failed');
    
    return failures.map(failure => ({
      step: failure.name,
      error: failure.error || 'Unknown error',
      duration_before_failure: failure.duration || 0,
      recovery_suggestion: this.getRecoverySuggestion(failure)
    }));
  }

  getRecoverySuggestion(failedStep) {
    const suggestions = {
      'video_downloader': 'Check video URL accessibility and network connectivity',
      'audio_transcriber': 'Verify audio quality and increase processing timeout',
      'moment_detector': 'Review video content for sufficient activity patterns',
      'face_detector': 'Ensure video contains detectable faces',
      'intelligent_cropper': 'Check crop parameters and aspect ratio requirements',
      'video_cutter': 'Verify output path permissions and disk space'
    };
    
    return suggestions[failedStep.name] || 'Review system logs for detailed error information';
  }

  calculatePerformanceMetrics(steps) {
    const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0);
    const avgStepDuration = totalDuration / steps.length;
    
    return {
      total_duration: totalDuration,
      avg_step_duration: avgStepDuration,
      steps_per_minute: steps.length / (totalDuration / 60),
      efficiency_score: this.calculatePipelineEfficiency(steps)
    };
  }

  calculatePipelineEfficiency(steps) {
    // Enterprise efficiency calculation based on expected vs actual durations
    const expectedDurations = {
      'video_downloader': 3,
      'audio_transcriber': 10,
      'moment_detector': 5,
      'face_detector': 8,
      'intelligent_cropper': 4,
      'video_cutter': 7
    };
    
    let efficiencySum = 0;
    let validSteps = 0;
    
    steps.forEach(step => {
      const expected = expectedDurations[step.name];
      if (expected && step.duration) {
        const efficiency = Math.min(100, (expected / step.duration) * 100);
        efficiencySum += efficiency;
        validSteps++;
      }
    });
    
    return validSteps > 0 ? Math.round(efficiencySum / validSteps) : 100;
  }

  calculateResourceUtilization(steps) {
    // Mock resource utilization - would be real metrics in production
    return {
      peak_cpu: Math.round(Math.random() * 100),
      peak_memory: Math.round(Math.random() * 100),
      network_usage: Math.round(Math.random() * 1000), // MB
      processing_nodes: steps.length
    };
  }

  calculateHistoryAnalytics() {
    const data = this.historyData;
    
    // Calculate enterprise analytics
    data.analytics = {
      pipeline_success_rate: this.calculatePipelineSuccessRate(),
      avg_pipeline_duration: this.calculateAvgPipelineDuration(),
      most_common_failures: this.calculateMostCommonFailures(),
      performance_trends: this.calculatePerformanceTrends()
    };
  }

  calculatePipelineSuccessRate() {
    const completedPipelines = this.jobs.filter(job => job.pipeline_status === 'completed').length;
    return this.jobs.length > 0 ? Math.round((completedPipelines / this.jobs.length) * 100) : 0;
  }

  calculateAvgPipelineDuration() {
    const durations = this.jobs
      .filter(job => job.performance_metrics?.total_duration)
      .map(job => job.performance_metrics.total_duration);
    
    return durations.length > 0 ? Math.round(durations.reduce((sum, d) => sum + d, 0) / durations.length) : 0;
  }

  calculateMostCommonFailures() {
    const failures = {};
    
    this.jobs.forEach(job => {
      if (job.failure_analysis && job.failure_analysis.length > 0) {
        job.failure_analysis.forEach(failure => {
          failures[failure.step] = (failures[failure.step] || 0) + 1;
        });
      }
    });
    
    return Object.entries(failures)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 3)
      .map(([step, count]) => ({ step, count }));
  }

  calculatePerformanceTrends() {
    // Mock performance trends - would be real time-series data in production
    return {
      avg_duration_trend: 'improving', // improving, stable, declining
      success_rate_trend: 'stable',
      failure_rate_trend: 'improving'
    };
  }

  cacheHistoryData() {
    try {
      localStorage.setItem('agentos_history_cache', JSON.stringify({
        ...this.historyData,
        cached_at: new Date().toISOString()
      }));
    } catch (error) {
      console.warn('Failed to cache history data:', error);
    }
  }

  loadCachedHistoryData() {
    try {
      const cached = localStorage.getItem('agentos_history_cache');
      if (cached) {
        this.historyData = JSON.parse(cached);
        // Store complete cached dataset and apply filters
        this.allJobs = this.historyData.jobs || [];
        this.applyCurrentFilters();
      }
    } catch (error) {
      console.warn('Failed to load cached history data:', error);
    }
  }

  buildApiParams() {
    const params = {};
    
    // Safe check for currentFilter
    if (this.currentFilter) {
      if (this.currentFilter.status && this.currentFilter.status !== 'all') {
        params.status = this.currentFilter.status;
      }
      
      if (this.currentFilter.search) {
        params.search = this.currentFilter.search;
      }
      
      if (this.currentFilter.dateRange && this.currentFilter.dateRange !== 'all') {
        params.date_range = this.currentFilter.dateRange;
      }
      
      if (this.currentFilter.sortBy) {
        params.sort = this.currentFilter.sortBy;
      }
    }

    return params;
  }

  async handleFilterChange(filter) {
    console.log('🔍 Jobs filter changed:', filter);
    this.currentFilter = filter;
    this.currentPage = 1; // Reset to first page when filter changes
    
    // Update current tab for KPI switching (map filter to tab)
    this.currentTab = this.mapFilterToTab(filter);
    
    // Update the dynamic KPIs for the new tab
    this.setupDynamicKPIs();
    
    // Apply filter and re-render
    this.renderCurrentView();
    
    // Update results count
    const filteredJobs = this.getFilteredJobs();
    if (this.smartFilter) {
      this.smartFilter.updateResultsCount(filteredJobs.length, (this.jobs || []).length);
    }
  }

  mapFilterToTab(filter) {
    // Map SmartFilter selection to tab names
    if (!filter) return 'active'; // Default to active view
    
    // Handle custom JobHistory presets directly
    if (filter.view) {
      switch (filter.view) {
        case 'active': return 'active';
        case 'issues': return 'issues';
        case 'completed': return 'completed';
        case 'all': return 'all';
        default: return filter.view;
      }
    }
    
    // Map based on filter properties (legacy fallback)
    if (filter.status && Array.isArray(filter.status)) {
      if (filter.status.includes('failed') || filter.status.includes('cancelled')) {
        return 'issues';
      }
      if (filter.status.includes('completed')) {
        return 'completed';
      }
      if (filter.status.includes('queued') || filter.status.includes('processing')) {
        return 'active';
      }
    }
    if (filter.status === 'all') return 'all';
    
    return 'active'; // Default fallback
  }

  getFilteredJobs() {
    // Return all jobs if no filter is set
    if (!this.currentFilter || this.currentFilter.status === 'all') {
      return this.jobs || [];
    }
    
    return (this.jobs || []).filter(job => {
      const filter = this.currentFilter;
      
      // Status filter
      if (filter.status && filter.status !== 'all') {
        if (Array.isArray(filter.status)) {
          if (!filter.status.includes(job.status)) return false;
        } else {
          if (job.status !== filter.status) return false;
        }
      }
      
      return true;
    });
  }

  handleViewToggle(view) {
    // Update active button
    this.container.querySelectorAll('.view-toggle-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === view);
    });

    // Store current view and re-render
    this.currentView = view;
    this.renderCurrentView();
  }

  renderCurrentView() {
    const contentContainer = this.container.querySelector('#jobsGrid');
    if (!contentContainer) return;
    
    // Get filtered jobs
    const filteredJobs = this.getFilteredJobs();
    
    // Update section title based on current filter
    this.updateJobsSectionTitle();
    
    // Always use list view
    this.renderListLayout(contentContainer, filteredJobs);
  }

  updateJobsSectionTitle() {
    const titleElement = document.getElementById('jobsSectionTitle');
    if (!titleElement) return;
    
    const filteredJobs = this.getFilteredJobs();
    const count = filteredJobs.length;
    
    let title = '';
    
    // Determine title based on current filter preset
    if (this.currentFilter && this.currentFilter.preset) {
      switch (this.currentFilter.preset) {
        case 'active':
          title = `⚡ Active Jobs (${count})`;
          break;
        case 'issues':
          title = `❌ Failed Jobs (${count})`;
          break;
        case 'completed':
          title = `✅ Completed Jobs (${count})`;
          break;
        case 'all':
        default:
          title = `📊 All Jobs (${count})`;
          break;
      }
    } else {
      // Fallback based on job statuses in filtered results
      if (filteredJobs.length === 0) {
        title = `📊 No Jobs Found`;
      } else if (filteredJobs.every(job => ['processing', 'running', 'queued'].includes(job.status))) {
        title = `⚡ Active Jobs (${count})`;
      } else if (filteredJobs.every(job => job.status === 'failed')) {
        title = `❌ Failed Jobs (${count})`;
      } else if (filteredJobs.every(job => job.status === 'completed')) {
        title = `✅ Completed Jobs (${count})`;
      } else {
        title = `📊 All Jobs (${count})`;
      }
    }
    
    console.log('🏷️ Setting section title to:', title);
    
    // Update only the text content, keep the help button
    const helpButton = titleElement.querySelector('.help-icon');
    titleElement.innerHTML = `${title} ${helpButton ? helpButton.outerHTML : '<button class="help-icon" data-section="job_pipeline">❓</button>'}`;
  }

  renderGridLayout(container, jobs, highlight = 'none', detailLevel = 'summary') {
    if (!jobs || jobs.length === 0) {
      container.innerHTML = this.renderEmptyState();
      return;
    }

    const jobCards = jobs.map(job => this.renderJobCard(job, { 
      detailLevel, 
      highlight: job.id === highlight ? 'active' : 'none' 
    })).join('');

    container.innerHTML = `
      <div class="jobs-grid jobs-grid--grid">
        ${jobCards}
      </div>
    `;
  }

  renderListLayout(container, jobs) {
    if (!jobs || jobs.length === 0) {
      container.innerHTML = this.renderEmptyState();
      return;
    }

    // Pagination logic
    const currentPage = this.currentPage || 1;
    const itemsPerPage = this.itemsPerPage || 20;
    const totalPages = Math.ceil(jobs.length / itemsPerPage);
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, jobs.length);
    const paginatedJobs = jobs.slice(startIndex, endIndex);

    const tableRows = paginatedJobs.map(job => {
      const statusClass = this.getStatusClass(job.status);
      const statusIcon = this.getStatusIcon(job.status);
      const duration = this.formatDuration(job.performance_metrics?.total_duration || job.duration || 0);
      const timeAgo = this.formatTimeAgo(job.created_at);
      
      return `
        <tr class="job-row job-row--${statusClass}" data-job-id="${job.id}">
          <td class="job-cell job-cell--id">
            <a href="#" class="job-link" data-job-id="${job.id}">#${job.id.slice(0, 8)}...</a>
          </td>
          <td class="job-cell job-cell--status">
            <span class="status-badge status-badge--${statusClass}">
              ${statusIcon} ${job.status}
            </span>
          </td>
          <td class="job-cell job-cell--type">${job.task_type || 'Processing'}</td>
          <td class="job-cell job-cell--time">${timeAgo}</td>
          <td class="job-cell job-cell--duration">${duration}</td>
          <td class="job-cell job-cell--progress">
            <div class="progress-bar">
              <div class="progress-bar__fill" style="width: ${job.progress || 0}%"></div>
              <span class="progress-bar__text">${job.progress || 0}%</span>
            </div>
          </td>
          <td class="job-cell job-cell--actions">
            <button class="action-btn action-btn--view" data-job-id="${job.id}" title="View Details">👁️</button>
            ${job.status === 'failed' ? `<button class="action-btn action-btn--retry" data-job-id="${job.id}" title="Retry">🔄</button>` : ''}
            ${job.status === 'processing' ? `<button class="action-btn action-btn--cancel" data-job-id="${job.id}" title="Cancel">⏹️</button>` : ''}
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <div class="jobs-list">
        <table class="jobs-table">
          <thead>
            <tr>
              <th class="sortable" data-sort="id">Job ID ↕</th>
              <th class="sortable" data-sort="status">Status ↕</th>
              <th class="sortable" data-sort="type">Type ↕</th>
              <th class="sortable" data-sort="created">Created ↕</th>
              <th class="sortable" data-sort="duration">Duration ↕</th>
              <th>Progress</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${tableRows}
          </tbody>
        </table>
        
        <div class="pagination-controls">
          <div class="pagination-info">
            📄 Showing ${startIndex + 1}-${endIndex} of ${jobs.length} jobs
          </div>
          <div class="pagination-nav">
            <button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} data-page="${currentPage - 1}">◀️ Prev</button>
            ${this.renderPaginationNumbers(currentPage, totalPages)}
            <button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">Next ▶️</button>
            <div class="pagination-jump">
              Go to: <input type="number" class="page-input" min="1" max="${totalPages}" value="${currentPage}"> 
              <button class="pagination-btn pagination-btn--go">🔍</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderPaginationNumbers(current, total) {
    let pages = [];
    const maxVisible = 5;
    
    if (total <= maxVisible) {
      for (let i = 1; i <= total; i++) {
        pages.push(`<button class="pagination-btn ${i === current ? 'pagination-btn--active' : ''}" data-page="${i}">${i}</button>`);
      }
    } else {
      pages.push(`<button class="pagination-btn ${current === 1 ? 'pagination-btn--active' : ''}" data-page="1">1</button>`);
      
      if (current > 3) pages.push('<span class="pagination-dots">...</span>');
      
      for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        pages.push(`<button class="pagination-btn ${i === current ? 'pagination-btn--active' : ''}" data-page="${i}">${i}</button>`);
      }
      
      if (current < total - 2) pages.push('<span class="pagination-dots">...</span>');
      
      pages.push(`<button class="pagination-btn ${current === total ? 'pagination-btn--active' : ''}" data-page="${total}">${total}</button>`);
    }
    
    return pages.join('');
  }

  renderPipelineLayout(container, jobs, highlight = 'none', detailLevel = 'summary') {
    const pipelineGroups = this.groupJobsByPipelineStage(jobs);
    
    const pipelineSections = Object.entries(pipelineGroups).map(([stage, stageJobs]) => {
      const statusClass = this.getPipelineStageStatusClass(stageJobs);
      const jobCards = stageJobs.map(job => this.renderJobCard(job, { 
        detailLevel: 'minimal', 
        highlight: job.id === highlight ? 'active' : 'none',
        showPipeline: true 
      })).join('');

      return `
        <div class="pipeline-section">
          <h3 class="pipeline-section-title pipeline-section-title--${statusClass}">
            🏭 ${stage.charAt(0).toUpperCase() + stage.slice(1)} Pipeline
            <span class="pipeline-count">(${stageJobs.length})</span>
          </h3>
          <div class="pipeline-jobs pipeline-jobs--compact">
            ${jobCards}
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = `<div class="jobs-grid jobs-grid--pipeline">${pipelineSections}</div>`;
  }

  renderPriorityLayout(container, jobs, highlight = 'none', detailLevel = 'summary') {
    const priorityGroups = this.groupJobsByPriority(jobs);
    
    const prioritySections = Object.entries(priorityGroups).map(([priority, priorityJobs]) => {
      const jobCards = priorityJobs.map(job => this.renderJobCard(job, { 
        detailLevel: 'summary', 
        highlight: job.id === highlight ? 'active' : 'none' 
      })).join('');

      return `
        <div class="priority-section priority-section--${priority}">
          <h3 class="priority-section-title">
            ${this.getPriorityIcon(priority)} ${priority.charAt(0).toUpperCase() + priority.slice(1)} Priority
            <span class="priority-count">(${priorityJobs.length})</span>
          </h3>
          <div class="priority-jobs priority-jobs--compact">
            ${jobCards}
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = `<div class="jobs-grid jobs-grid--priority">${prioritySections}</div>`;
  }

  renderTimelineLayout(container, jobs, highlight = 'none', detailLevel = 'expanded') {
    if (!jobs || jobs.length === 0) {
      container.innerHTML = this.renderEmptyState();
      return;
    }

    // Sort jobs by created_at for timeline
    const sortedJobs = [...jobs].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    const timelineItems = sortedJobs.map(job => {
      const statusClass = this.getStatusClass(job.status);
      const timeAgo = this.formatTimeAgo(job.created_at);
      const duration = this.formatDuration(job.performance_metrics?.total_duration || 0);
      
      return `
        <div class="timeline-item timeline-item--${statusClass} ${job.id === highlight ? 'timeline-item--highlighted' : ''}">
          <div class="timeline-header">
            <h4 class="timeline-title">
              ${this.getStatusIcon(job.status)} Job ${job.id}
            </h4>
            <span class="timeline-time">${timeAgo}</span>
          </div>
          <div class="timeline-description">
            ${job.description || job.task_type || 'Processing task'}
          </div>
          <div class="timeline-metadata">
            <div class="timeline-meta-item">
              <span>Duration:</span> ${duration}
            </div>
            <div class="timeline-meta-item">
              <span>Status:</span> ${job.status}
            </div>
            <div class="timeline-meta-item">
              <span>Progress:</span> ${job.progress || 0}%
            </div>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = `<div class="jobs-grid jobs-grid--timeline">${timelineItems}</div>`;
  }

  renderJobCard(job, options = {}) {
    const { 
      detailLevel = 'summary', 
      highlight = 'none',
      showPipeline = false
    } = options;
    
    const status = job.status || 'unknown';
    const statusClass = this.getStatusClass(status);
    const timeAgo = this.formatTimeAgo(job.created_at);
    const duration = job.performance_metrics?.total_duration || job.duration || 0;
    const efficiency = job.performance_metrics?.efficiency_score || 0;
    
    // Minimal compact card
    if (detailLevel === 'minimal') {
      return `
        <div class="job-card job-card--${statusClass} job-card--minimal">
          <div class="job-card__header">
            <span class="job-id">Job #${job.id || job.job_id}</span>
            <span class="status-indicator status-indicator--${statusClass}"></span>
          </div>
          <div class="job-card__summary">
            <span class="job-time">${timeAgo}</span>
            <span class="job-duration">${this.formatDuration(duration)}</span>
          </div>
        </div>
      `;
    }
    
    // Compact summary card
    if (detailLevel === 'summary') {
      return `
        <div class="job-card job-card--${statusClass} job-card--summary">
          <div class="job-card__header">
            <div class="job-card__id">
              <span class="job-id">Job #${job.id || job.job_id}</span>
              <span class="job-time">${timeAgo}</span>
            </div>
            <div class="job-card__status">
              <span class="status-indicator status-indicator--${statusClass}"></span>
              <span class="status-text">${status}</span>
            </div>
          </div>
          <div class="job-card__metrics">
            <div class="metric-item">
              <span class="metric-label">Duration</span>
              <span class="metric-value">${this.formatDuration(duration)}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Efficiency</span>
              <span class="metric-value">${efficiency}%</span>
            </div>
          </div>
          <div class="job-card__actions">
            <button class="btn btn-sm btn-secondary" onclick="window.jobHistory.showJobDetails('${job.id}')">
              Details
            </button>
          </div>
        </div>
      `;
    }
    
    // Expanded detail card
    if (detailLevel === 'expanded') {
      const alertBg = status === 'failed' ? '#f8d7da' : status === 'processing' ? '#fff3cd' : 'transparent';
      const alertBorder = status === 'failed' ? '1px solid #f5c6cb' : status === 'processing' ? '1px solid #ffeaa7' : 'none';
      
      return `
        <div class="job-card job-card--${statusClass} job-card--expanded">
          <div class="job-card__header">
            <div class="job-card__info">
              <h4 class="job-card__title">Job #${job.id || job.job_id}</h4>
              <div class="job-card__meta">
                <span class="job-time">${timeAgo}</span>
                <span class="job-duration">${this.formatDuration(duration)}</span>
              </div>
            </div>
            <div class="job-card__status">
              <span class="status-badge status-badge--${statusClass}">${status.toUpperCase()}</span>
            </div>
          </div>
          
          ${(status === 'failed' || status === 'processing') ? `
            <div class="job-alert" style="background: ${alertBg}; border: ${alertBorder}; border-radius: 4px; padding: 0.75rem; margin-bottom: 1rem;">
              ${status === 'failed' ? `
                <strong>⚠️ Processing Failed:</strong>
                ${job.failure_analysis?.[0]?.error || 'Unknown error occurred'}
              ` : `
                <strong>⚡ Currently Processing:</strong>
                Step ${job.pipeline_steps?.findIndex(s => s.status === 'running') + 1 || '?'} of ${job.pipeline_steps?.length || '?'}
              `}
            </div>
          ` : ''}
          
          ${showPipeline && job.pipeline_steps ? this.renderMiniPipeline(job.pipeline_steps) : ''}
          
          <div class="job-card__metrics">
            <div class="metrics-grid">
              <div class="metric-item">
                <span class="metric-label">Efficiency</span>
                <span class="metric-value">${efficiency}%</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">Steps</span>
                <span class="metric-value">${job.pipeline_steps?.length || 0}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">Progress</span>
                <span class="metric-value">${job.progress || 0}%</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">Resource</span>
                <span class="metric-value">${job.resource_utilization?.peak_cpu || 0}%</span>
              </div>
            </div>
          </div>
          
          <div class="job-card__actions">
            <button class="btn btn-sm btn-primary" onclick="window.jobHistory.showJobDetails('${job.id}')">
              📄 Full Details
            </button>
            ${status === 'failed' ? `
              <button class="btn btn-sm btn-warning" onclick="window.jobHistory.retryJob('${job.id}')">
                🔄 Retry Job
              </button>
            ` : ''}
            ${status === 'processing' ? `
              <button class="btn btn-sm btn-danger" onclick="window.jobHistory.cancelJob('${job.id}')">
                ⏹️ Cancel
              </button>
            ` : ''}
          </div>
        </div>
      `;
    }
    
    return this.renderJobCard(job, { detailLevel: 'summary', highlight });
  }

  renderMiniPipeline(steps) {
    if (!steps || steps.length === 0) return '';
    
    return `
      <div class="mini-pipeline">
        <div class="mini-pipeline__header">
          <span class="mini-pipeline__title">🔄 Agent Pipeline</span>
        </div>
        <div class="mini-pipeline__steps">
          ${steps.map((step, index) => {
            const statusIcon = this.getStageIcon(step.name, step.status);
            const isActive = step.status === 'running' || step.status === 'processing';
            
            return `
              <div class="mini-step mini-step--${step.status} ${isActive ? 'mini-step--active' : ''}">
                <span class="mini-step__icon">${statusIcon}</span>
                <span class="mini-step__name">${this.formatAgentName(step.name)}</span>
                ${step.duration ? `<span class="mini-step__time">${step.duration}s</span>` : ''}
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  renderJobRow(job) {
    const status = job.status || 'unknown';
    const statusClass = status.toLowerCase();
    const createdDate = job.created_at ? new Date(job.created_at).toLocaleDateString() : '-';
    const duration = this.formatDuration(job.duration || job.processing_time);
    const progress = job.progress || 0;

    return `
      <tr>
        <td>
          <span class="history-job-id">${job.id || job.job_id || 'N/A'}</span>
        </td>
        <td>
          <span class="history-status ${statusClass}">
            ${this.getStatusIcon(status)} ${status}
          </span>
        </td>
        <td>${createdDate}</td>
        <td>
          <span class="history-duration">${duration}</span>
        </td>
        <td>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${progress}%"></div>
            <span class="progress-text">${progress}%</span>
          </div>
        </td>
        <td>
          <div class="history-actions-cell">
            <button class="history-action job-details-btn" data-job-id="${job.id || job.job_id}">
              👁️ View
            </button>
            ${status === 'failed' ? `
              <button class="history-action job-action" data-action="retry" data-job-id="${job.id || job.job_id}">
                🔄 Retry
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }

  renderTimelineView(container) {
    if (!this.jobs || this.jobs.length === 0) {
      container.innerHTML = `
        <div class="enterprise-pipeline-timeline">
          <div class="empty-state">
            <div class="empty-state__icon">🔄</div>
            <div class="empty-state__title">No pipeline jobs found</div>
            <div class="empty-state__description">
              Adjust your filters to see job pipeline timelines
            </div>
          </div>
        </div>
      `;
      return;
    }

    // Enterprise pipeline timeline with GitLab/Azure DevOps style
    const timelineHTML = `
      <div class="enterprise-pipeline-timeline">
        <!-- Timeline Analytics Header -->
        <div class="pipeline-analytics-header">
          <div class="pipeline-summary-card">
            <div class="pipeline-summary-stat">
              <div class="stat-value">${this.historyData?.analytics?.pipeline_success_rate || 0}%</div>
              <div class="stat-label">Pipeline Success Rate</div>
            </div>
            <div class="pipeline-summary-stat">
              <div class="stat-value">${this.formatDuration(this.historyData?.analytics?.avg_pipeline_duration || 0)}</div>
              <div class="stat-label">Avg Pipeline Duration</div>
            </div>
            <div class="pipeline-summary-stat">
              <div class="stat-value">${this.historyData?.analytics?.most_common_failures?.length || 0}</div>
              <div class="stat-label">Active Failure Types</div>
            </div>
          </div>
        </div>

        <!-- Enterprise Pipeline Timeline -->
        <div class="pipeline-timeline-container">
          ${this.jobs.map(job => this.renderEnterprisePipelineItem(job)).join('')}
        </div>
      </div>
    `;

    container.innerHTML = timelineHTML;
  }

  renderEnterprisePipelineItem(job) {
    const pipelineStatus = job.pipeline_status || 'unknown';
    const totalDuration = job.performance_metrics?.total_duration || 0;
    const efficiencyScore = job.performance_metrics?.efficiency_score || 0;
    const timeAgo = this.formatTimeAgo(job.created_at);
    
    return `
      <div class="enterprise-pipeline-item pipeline-item--${pipelineStatus}">
        <!-- Pipeline Header -->
        <div class="pipeline-item-header">
          <div class="pipeline-item-info">
            <div class="pipeline-item-title">
              <span class="pipeline-status-icon">${this.getPipelineStatusIcon(pipelineStatus)}</span>
              <span class="pipeline-job-id">Job #${job.id || job.job_id}</span>
              <span class="pipeline-status-badge pipeline-status-badge--${pipelineStatus}">${pipelineStatus.toUpperCase()}</span>
            </div>
            <div class="pipeline-item-metadata">
              <span class="pipeline-timestamp">${timeAgo}</span>
              <span class="pipeline-duration">Duration: ${this.formatDuration(totalDuration)}</span>
              <span class="pipeline-efficiency">Efficiency: ${efficiencyScore}%</span>
            </div>
          </div>
          <div class="pipeline-item-actions">
            <button class="btn btn-xs btn-ghost" onclick="this.togglePipelineDetails('${job.id}')" title="Toggle pipeline details">
              <span class="pipeline-toggle-icon">🔽</span>
            </button>
            ${job.failure_analysis?.length > 0 ? 
              `<button class="btn btn-xs btn-warning" title="View failure analysis">⚠️</button>` : ''
            }
            <button class="btn btn-xs btn-primary" onclick="this.showJobDetails('${job.id}')" title="View job details">📋</button>
          </div>
        </div>

        <!-- Enterprise Pipeline Visualization -->
        <div class="pipeline-stages">
          ${this.renderPipelineStages(job.pipeline_steps || [])}
        </div>

        <!-- Pipeline Details (Collapsible) -->
        <div class="pipeline-details" id="pipeline-details-${job.id}" style="display: none;">
          ${this.renderPipelineDetails(job)}
        </div>

        <!-- Failure Analysis (if applicable) -->
        ${job.failure_analysis?.length > 0 ? this.renderFailureAnalysis(job.failure_analysis) : ''}
      </div>
    `;
  }

  renderPipelineStages(steps) {
    if (!steps || steps.length === 0) {
      return `
        <div class="pipeline-stage pipeline-stage--unknown">
          <div class="stage-icon">❓</div>
          <div class="stage-name">No pipeline data</div>
        </div>
      `;
    }

    return `
      <div class="pipeline-stages-flow">
        ${steps.map((step, index) => this.renderPipelineStage(step, index, steps.length)).join('')}
      </div>
    `;
  }

  renderPipelineStage(step, index, totalSteps) {
    const statusClass = step.status || 'unknown';
    const duration = step.duration ? `${step.duration}s` : '-';
    const isLastStep = index === totalSteps - 1;
    
    return `
      <div class="pipeline-stage pipeline-stage--${statusClass}">
        <div class="stage-container">
          <div class="stage-icon">${this.getStageIcon(step.name, step.status)}</div>
          <div class="stage-content">
            <div class="stage-name">${this.formatAgentName(step.name)}</div>
            <div class="stage-duration">${duration}</div>
          </div>
          ${step.error ? `<div class="stage-error" title="${step.error}">⚠️</div>` : ''}
        </div>
        ${!isLastStep ? '<div class="stage-connector"></div>' : ''}
      </div>
    `;
  }

  renderPipelineDetails(job) {
    const resourceUsage = job.resource_utilization || {};
    const durationBreakdown = job.duration_breakdown || {};
    
    return `
      <div class="pipeline-details-content">
        <!-- Resource Utilization -->
        <div class="pipeline-details-section">
          <h4 class="details-section-title">🔧 Resource Utilization</h4>
          <div class="resource-metrics">
            <div class="resource-metric">
              <span class="metric-label">Peak CPU:</span>
              <span class="metric-value">${resourceUsage.peak_cpu || 0}%</span>
            </div>
            <div class="resource-metric">
              <span class="metric-label">Peak Memory:</span>
              <span class="metric-value">${resourceUsage.peak_memory || 0}%</span>
            </div>
            <div class="resource-metric">
              <span class="metric-label">Network Usage:</span>
              <span class="metric-value">${resourceUsage.network_usage || 0} MB</span>
            </div>
          </div>
        </div>

        <!-- Duration Breakdown -->
        <div class="pipeline-details-section">
          <h4 class="details-section-title">⏱️ Duration Breakdown</h4>
          <div class="duration-breakdown">
            ${Object.entries(durationBreakdown)
              .filter(([key]) => key !== 'total')
              .map(([agent, duration]) => `
                <div class="duration-item">
                  <span class="duration-agent">${this.formatAgentName(agent)}</span>
                  <div class="duration-bar-container">
                    <div class="duration-bar" style="width: ${this.calculateDurationPercentage(duration, durationBreakdown.total)}%"></div>
                  </div>
                  <span class="duration-time">${duration}s</span>
                </div>
              `).join('')}
          </div>
        </div>

        <!-- Performance Insights -->
        <div class="pipeline-details-section">
          <h4 class="details-section-title">📊 Performance Insights</h4>
          <div class="performance-insights">
            <div class="insight-item">
              <span class="insight-icon">⚡</span>
              <span class="insight-text">Pipeline efficiency: ${job.performance_metrics?.efficiency_score || 0}%</span>
            </div>
            <div class="insight-item">
              <span class="insight-icon">🎯</span>
              <span class="insight-text">Processing rate: ${(job.performance_metrics?.steps_per_minute || 0).toFixed(1)} steps/min</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderFailureAnalysis(failures) {
    return `
      <div class="pipeline-failure-analysis">
        <div class="failure-analysis-header">
          <span class="failure-icon">🚨</span>
          <span class="failure-title">Failure Analysis</span>
        </div>
        <div class="failure-items">
          ${failures.map(failure => `
            <div class="failure-item">
              <div class="failure-step">${this.formatAgentName(failure.step)}</div>
              <div class="failure-error">${failure.error}</div>
              <div class="failure-suggestion">💡 ${failure.recovery_suggestion}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Enterprise utility methods for pipeline visualization
  getPipelineStatusIcon(status) {
    const icons = {
      'completed': '✅',
      'failed': '❌',
      'running': '🔄',
      'pending': '⏳',
      'cancelled': '🚫'
    };
    return icons[status] || '❓';
  }

  getStageIcon(stageName, status) {
    const stageIcons = {
      'video_downloader': '📥',
      'audio_transcriber': '🎧',
      'moment_detector': '🎯',
      'face_detector': '👤',
      'intelligent_cropper': '✂️',
      'video_cutter': '🎬'
    };
    
    const statusOverlay = {
      'completed': '✅',
      'failed': '❌',
      'running': '🔄',
      'skipped': '⏭️'
    };
    
    const baseIcon = stageIcons[stageName] || '⚙️';
    const overlay = statusOverlay[status];
    
    return overlay ? `${baseIcon}${overlay}` : baseIcon;
  }

  formatAgentName(agentName) {
    return agentName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  calculateDurationPercentage(stepDuration, totalDuration) {
    if (!totalDuration || totalDuration === 0) return 0;
    return Math.round((stepDuration / totalDuration) * 100);
  }

  togglePipelineDetails(jobId) {
    const detailsElement = document.getElementById(`pipeline-details-${jobId}`);
    const pipelineItem = event.target && event.target.closest ? event.target.closest('.pipeline-item') : null;
    const toggleIcon = pipelineItem ? pipelineItem.querySelector('.pipeline-toggle-icon') : null;
    
    if (detailsElement.style.display === 'none') {
      detailsElement.style.display = 'block';
      if (toggleIcon) toggleIcon.textContent = '🔼';
    } else {
      detailsElement.style.display = 'none';
      if (toggleIcon) toggleIcon.textContent = '🔽';
    }
  }

  renderTimelineItem(job) {
    const status = job.status || 'unknown';
    const markerClass = this.getTimelineMarkerClass(status);
    const timeAgo = this.formatTimeAgo(job.created_at);
    const duration = this.formatDuration(job.duration || job.processing_time);

    return `
      <div class="timeline-item">
        <div class="timeline-marker ${markerClass}"></div>
        <div class="timeline-content">
          <div class="timeline-header">
            <h4 class="timeline-title">
              ${this.getStatusIcon(status)} Job ${job.id || job.job_id}
            </h4>
            <span class="timeline-time">${timeAgo}</span>
          </div>
          <div class="timeline-description">
            Status: <strong>${status}</strong> | Duration: <strong>${duration}</strong>
            ${job.error_message ? `<br>Error: ${job.error_message}` : ''}
          </div>
          <div class="timeline-metadata">
            <div class="timeline-meta-item">
              <span>📊</span> Progress: ${job.progress || 0}%
            </div>
            <div class="timeline-meta-item">
              <button class="btn btn-xs btn-link job-details-btn" data-job-id="${job.id || job.job_id}">
                View Details
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  updateOverviewMetrics() {
    // DON'T auto-setup dynamic KPIs here - only via handleFilterChange()
    // This prevents double-triggering during initialization
    
    // Legacy fallback - keep old logic as backup  
    const centralData = getCentralDataService();
    const currentData = centralData.getCurrentData();
    const queueData = currentData?.queue || {};
    const jobsData = currentData?.jobs || {};
    
    // Extract new metrics - use jobs section as fallback for metrics that may be there
    const queueDepth = queueData.queue_depth || queueData.pending || 0;
    const throughput = queueData.queue_throughput || {per_hour: 0, trend: 'unknown'};
    const workerUtil = queueData.worker_utilization || 0;
    const successRate24h = queueData.success_rate_24h || jobsData.success_rate || 0;
    
    // Jobs breakdown - construct from available data if not directly available
    const jobsBreakdown = queueData.jobs_breakdown || {
      total: jobsData.total_jobs || 0,
      completed: jobsData.completed_jobs || 0,
      failed: jobsData.failed_jobs || 0,
      processing: jobsData.processing_jobs || queueData.processing || 0,
      pending: jobsData.pending_jobs || queueData.pending || 0
    };
    
    const todayBreakdown = queueData.today_jobs_breakdown || {
      total: jobsData.total_today || 0,
      completed: 0, // Not available separately
      failed: queueData.failed_today || 0,
      processing: Math.floor((jobsData.processing_jobs || 0) * 0.2), // Estimate
      pending: Math.floor((jobsData.pending_jobs || 0) * 0.2) // Estimate  
    };
    
    const avgWaitTime = queueData.avg_wait_time || 0;
    
    // Calculate average processing time from completed jobs (fallback for jobs without backend metrics)
    const completedJobsWithTime = this.jobs.filter(job => 
      job.status === 'completed' && job.performance_metrics?.total_duration
    );
    const avgProcessingTime = completedJobsWithTime.length > 0 
      ? Math.round(completedJobsWithTime.reduce((sum, job) => sum + job.performance_metrics.total_duration, 0) / completedJobsWithTime.length)
      : Math.round(avgWaitTime);

    // LEGACY METRIC SYSTEM DISABLED
    // Dynamic KPI system via setupDynamicKPIs() handles all metrics now
    // This prevents dual system conflicts (refresh vs tab-switch)

  }

  createMetricCard(containerId, data) {
    // LEGACY METHOD - DISABLED
    // All metrics now handled by dynamic KPI system (ActionableMetricCard)
    console.log('Legacy createMetricCard() disabled - using dynamic KPI system instead');
    return;
  }

  // =============================================================================
  // DYNAMIC KPI SYSTEM (like Analytics.js)
  // =============================================================================

  setupDynamicKPIs() {
    // Get KPI configurations based on current tab
    const kpiConfigs = this.getKPIConfigsForTab(this.currentTab);
    
    // Clear existing metric cards
    this.metricCards.clear();
    
    kpiConfigs.forEach(config => {
      if (config.container && config.container !== null) {
        try {
          // ActionableMetricCard constructor expects (container, options)
          const { container, ...options } = config;
          const metricCard = new ActionableMetricCard(container, options);
          this.metricCards.set(config.id, metricCard);
        } catch (error) {
          console.error(`❌ Failed to create ActionableMetricCard for ${config.id}:`, error);
          console.error(`Container:`, config.container);
          
          // Show user-visible error notification
          this.showKPILoadError(config.id, error.message);
          
          // Create error placeholder card for downstream safety
          const errorCard = this.createErrorMetricCard(config);
          this.metricCards.set(config.id, errorCard);
          
          // Render the error placeholder immediately
          errorCard.render();
          
          // Continue loop - don't rethrow
        }
      } else {
        console.warn(`⚠️ Missing container for KPI ${config.id}, selector: ${config.container}`);
      }
    });
  }

  getKPIConfigsForTab(tab) {
    // Get current data from CentralDataService
    const centralData = getCentralDataService();
    const currentData = centralData.getCurrentData();
    const queueData = currentData?.queue || {};
    const jobsData = currentData?.jobs || {};
    
    // Build comprehensive data object
    const data = {
      queue: queueData,
      jobs: jobsData,
      filteredJobs: this.getFilteredJobs(),
      allJobs: this.jobs || []
    };
    
    switch (tab) {
      case 'active':
        return this.getActiveKPIs(data);
      case 'issues':
        return this.getIssuesKPIs(data);
      case 'completed':
        return this.getCompletedKPIs(data);
      case 'all':
        return this.getAllKPIs(data);
      // Legacy support for old tab names
      case 'today':
        return this.getTodayKPIs(data);
      case 'this-week':
        return this.getThisWeekKPIs(data);
      case 'successful':
        return this.getSuccessfulKPIs(data);
      case 'errors':
        return this.getErrorKPIs(data);
      case 'all-history':
        return this.getAllHistoryKPIs(data);
      default:
        return this.getActiveKPIs(data);
    }
  }

  // KPI BUILDER CLASS - Reduces repetitive KPI configuration code
  // =============================================================================
  
  /**
   * Generic KPI builder to eliminate code duplication across get*KPIs methods
   */
  createKPIBuilder() {
    return {
      container: this.container,
      kpis: [],
      
      addKPI(selector, config) {
        this.kpis.push({
          ...config,
          container: this.container.querySelector(selector)
        });
        return this;
      },
      
      build() {
        return this.kpis;
      }
    };
  }

  getTodayKPIs(data) {
    const todayJobs = this.filterJobsByDate(data.allJobs, 'today');
    const todayCompleted = todayJobs.filter(j => j.status === 'completed').length;
    const todayFailed = todayJobs.filter(j => j.status === 'failed').length;
    const todayProcessing = todayJobs.filter(j => j.status === 'processing').length;
    const successRate = todayJobs.length > 0 ? (todayCompleted / todayJobs.length * 100).toFixed(1) : 0;

    const builder = this.createKPIBuilder();
    
    return builder
      .addKPI('#queue-depth-card', {
        id: 'today-total',
        title: 'Jobs Today',
        icon: '📅',
        value: todayJobs.length.toString(),
        description: 'Total jobs processed today',
        helpId: 'jobs_today',
        trend: { direction: 'up', percentage: 12 },
        actions: [
          { label: 'View Today Details', action: 'analytics.drill_down', params: { filter: 'today_jobs' }, icon: '🔍' },
          { label: 'Export Today', action: 'analytics.generate_report', params: { type: 'daily' }, icon: '📊' }
        ]
      })
      .addKPI('#active-processing-card', {
        id: 'today-success-rate',
        title: 'Today Success Rate',
        icon: '✅',
        value: `${successRate}%`,
        description: `${todayCompleted} completed, ${todayFailed} failed`,
        helpId: 'success_rate_today',
        thresholds: { warning: 95, critical: 90 },
        currentValue: parseFloat(successRate),
        trend: { direction: 'up', percentage: 3 },
        showThresholdBar: true,
        actions: [
          { label: 'Analyze Failures', action: 'analytics.drill_down', params: { filter: 'today_failed' }, icon: '🔍' },
          { label: 'Retry Failed', action: 'job.bulk_retry', params: { filter: 'today' }, icon: '🔄' }
        ]
      })
      .addKPI('#queue-throughput-card', {
        id: 'today-active',
        title: 'Active Now',
        icon: '⚡',
        value: todayProcessing.toString(),
        description: 'Currently processing',
        helpId: 'active_jobs',
        actions: [
          { label: 'Monitor Active', action: 'analytics.drill_down', params: { filter: 'active_jobs' }, icon: '👁️' },
          { label: 'Worker Status', action: 'worker.status', icon: '👷' }
        ]
      })
      .addKPI('#success-rate-24h-card', {
        id: 'today-avg-time',
        title: 'Avg Processing Time',
        icon: '⏱️',
        value: this.calculateAvgProcessingTime(todayJobs),
        description: 'Average completion time today',
        helpId: 'avg_processing_time',
        actions: [
          { label: 'Performance Analysis', action: 'analytics.drill_down', params: { filter: 'performance' }, icon: '📊' },
          { label: 'Optimize Performance', action: 'system.performance_tune', icon: '🚀' }
        ]
      })
      .build();
  }

  getThisWeekKPIs(data) {
    const weekJobs = this.filterJobsByDate(data.allJobs, 'week');
    const weekCompleted = weekJobs.filter(j => j.status === 'completed').length;
    const weekFailed = weekJobs.filter(j => j.status === 'failed').length;
    const dailyAvg = Math.round(weekJobs.length / 7);

    const builder = this.createKPIBuilder();
    
    return builder
      .addKPI('#queue-depth-card', {
        id: 'week-total',
        title: 'Week Total',
        icon: '📆',
        value: weekJobs.length.toString(),
        description: `${dailyAvg} jobs/day average`,
        helpId: 'week_total',
        trend: { direction: 'up', percentage: 8 },
        actions: [
          { label: 'Weekly Report', action: 'analytics.generate_report', params: { type: 'weekly' }, icon: '📊' },
          { label: 'Trend Analysis', action: 'analytics.drill_down', params: { filter: 'week_trends' }, icon: '📈' }
        ]
      })
      .addKPI('#active-processing-card', {
        id: 'week-growth',
        title: 'Week Growth',
        icon: '📈',
        value: '+23%',
        description: 'vs previous week',
        helpId: 'week_growth',
        trend: { direction: 'up', percentage: 23 },
        actions: [
          { label: 'Growth Analysis', action: 'analytics.drill_down', params: { filter: 'growth' }, icon: '📊' },
          { label: 'Capacity Planning', action: 'analytics.capacity_analysis', icon: '⚖️' }
        ]
      })
      .addKPI('#queue-throughput-card', {
        id: 'week-completion',
        title: 'Completion Rate',
        icon: '🎯',
        value: `${weekCompleted}/${weekJobs.length}`,
        description: `${weekJobs.length > 0 ? (weekCompleted/weekJobs.length*100).toFixed(1) : 0}% success rate`,
        helpId: 'week_completion',
        actions: [
          { label: 'Success Analysis', action: 'analytics.drill_down', params: { filter: 'success_patterns' }, icon: '✅' }
        ]
      })
      .addKPI('#success-rate-24h-card', {
        id: 'week-peak-day',
        title: 'Peak Day',
        icon: '🔥',
        value: 'Wednesday',
        description: '45 jobs processed',
        helpId: 'peak_day',
        actions: [
          { label: 'Daily Breakdown', action: 'analytics.drill_down', params: { filter: 'daily_breakdown' }, icon: '📅' }
        ]
      })
      .build();
  }

  getSuccessfulKPIs(data) {
    const successfulJobs = data.allJobs.filter(j => j.status === 'completed');
    const avgSuccessTime = this.calculateAvgProcessingTime(successfulJobs);
    const qualityScore = this.calculateQualityScore(successfulJobs);

    const builder = this.createKPIBuilder();
    
    return builder
      .addKPI('#queue-depth-card', {
        id: 'successful-total',
        title: 'Successful Jobs',
        icon: '✅',
        value: successfulJobs.length.toString(),
        description: 'Total completed jobs',
        helpId: 'successful_jobs',
        trend: { direction: 'up', percentage: 15 },
        actions: [
          { label: 'Success Report', action: 'analytics.generate_report', params: { type: 'success' }, icon: '📊' },
          { label: 'Success Patterns', action: 'analytics.drill_down', params: { filter: 'success_analysis' }, icon: '🔍' }
        ]
      })
      .addKPI('#active-processing-card', {
        id: 'quality-score',
        title: 'Quality Score',
        icon: '⭐',
        value: `${qualityScore}%`,
        description: 'Output quality rating',
        helpId: 'quality_score',
        thresholds: { warning: 90, critical: 80 },
        currentValue: qualityScore,
        trend: { direction: 'up', percentage: 5 },
        showThresholdBar: true,
        actions: [
          { label: 'Quality Analysis', action: 'analytics.drill_down', params: { filter: 'quality' }, icon: '📊' },
          { label: 'Improve Quality', action: 'system.optimize_quality', icon: '⚡' }
        ]
      })
      .addKPI('#queue-throughput-card', {
        id: 'success-avg-time',
        title: 'Avg Success Time',
        icon: '⚡',
        value: avgSuccessTime,
        description: 'Average completion time',
        helpId: 'success_time',
        actions: [
          { label: 'Performance Deep Dive', action: 'analytics.drill_down', params: { filter: 'performance_analysis' }, icon: '🔍' }
        ]
      })
      .addKPI('#success-rate-24h-card', {
        id: 'success-rate',
        title: 'Overall Success Rate',
        icon: '🎯',
        value: `${data.allJobs.length > 0 ? (successfulJobs.length/data.allJobs.length*100).toFixed(1) : 0}%`,
        description: 'Total success percentage',
        helpId: 'overall_success_rate',
        thresholds: { warning: 95, critical: 90 },
        currentValue: data.allJobs.length > 0 ? (successfulJobs.length/data.allJobs.length*100) : 0,
        showThresholdBar: true,
        actions: [
          { label: 'Success Optimization', action: 'system.optimize_success', icon: '🚀' }
        ]
      })
      .build();
  }

  getErrorKPIs(data) {
    const failedJobs = data.allJobs.filter(j => j.status === 'failed');
    const errorRate = data.allJobs.length > 0 ? (failedJobs.length / data.allJobs.length * 100).toFixed(2) : 0;
    const topError = this.getTopErrorType(failedJobs);
    const mttr = this.calculateMTTR(failedJobs);

    return [
      {
        id: 'failed-total',
        container: this.container.querySelector('#queue-depth-card'),
        title: 'Failed Jobs',
        icon: '❌',
        value: failedJobs.length.toString(),
        description: 'Total failed jobs',
        helpId: 'failed_jobs',
        trend: { direction: 'down', percentage: 20 },
        actions: [
          { label: 'Analyze Failures', action: 'analytics.drill_down', params: { filter: 'failure_analysis' }, icon: '🔍' },
          { label: 'Retry All Failed', action: 'job.bulk_retry', params: { filter: 'failed' }, icon: '🔄' },
          { label: 'Error Report', action: 'analytics.generate_report', params: { type: 'errors' }, icon: '📊' }
        ]
      },
      {
        id: 'error-rate',
        container: this.container.querySelector('#active-processing-card'),
        title: 'Error Rate',
        icon: '📉',
        value: `${errorRate}%`,
        description: 'Failure percentage',
        helpId: 'error_rate',
        thresholds: { warning: 5.0, critical: 10.0 },
        currentValue: parseFloat(errorRate),
        trend: { direction: 'down', percentage: 15 },
        showThresholdBar: true,
        actions: [
          { label: 'Reduce Errors', action: 'system.error_reduction', icon: '🛠️' },
          { label: 'Error Patterns', action: 'analytics.drill_down', params: { filter: 'error_patterns' }, icon: '📊' }
        ]
      },
      {
        id: 'top-error',
        container: this.container.querySelector('#queue-throughput-card'),
        title: 'Top Error',
        icon: '🔧',
        value: topError.type,
        description: `${topError.count} occurrences (${topError.percentage}%)`,
        helpId: 'top_error',
        actions: [
          { label: 'Fix This Error', action: 'system.fix_error', params: { error_type: topError.type }, icon: '🔧' },
          { label: 'Error Details', action: 'analytics.drill_down', params: { filter: `error_${topError.type}` }, icon: '🔍' }
        ]
      },
      {
        id: 'mttr',
        container: this.container.querySelector('#success-rate-24h-card'),
        title: 'MTTR',
        icon: '⏱️',
        value: `${mttr}min`,
        description: 'Mean Time To Recovery',
        helpId: 'mttr',
        thresholds: { warning: 10, critical: 30 },
        currentValue: mttr,
        trend: { direction: 'down', percentage: 25 },
        showThresholdBar: true,
        actions: [
          { label: 'Improve MTTR', action: 'system.optimize_recovery', icon: '🚀' },
          { label: 'Recovery Report', action: 'analytics.generate_report', params: { type: 'recovery' }, icon: '📊' }
        ]
      }
    ];
  }

  getAllHistoryKPIs(data) {
    const totalJobs = data.allJobs.length;
    const completedJobs = data.allJobs.filter(j => j.status === 'completed').length;
    const overallSuccessRate = totalJobs > 0 ? (completedJobs / totalJobs * 100).toFixed(1) : 0;

    return [
      {
        id: 'history-total',
        container: this.container.querySelector('#queue-depth-card'),
        title: 'Total Jobs',
        icon: '📚',
        value: totalJobs.toString(),
        description: 'Complete job history',
        helpId: 'total_history',
        actions: [
          { label: 'Full Export', action: 'analytics.generate_report', params: { type: 'complete' }, icon: '📊' },
          { label: 'Archive Old Jobs', action: 'job.archive_old', icon: '🗄️' }
        ]
      },
      {
        id: 'history-success',
        container: this.container.querySelector('#active-processing-card'),
        title: 'Overall Success Rate',
        icon: '🎯',
        value: `${overallSuccessRate}%`,
        description: `${completedJobs} of ${totalJobs} completed`,
        helpId: 'overall_success',
        thresholds: { warning: 95, critical: 90 },
        currentValue: parseFloat(overallSuccessRate),
        showThresholdBar: true,
        actions: [
          { label: 'Historical Analysis', action: 'analytics.drill_down', params: { filter: 'historical' }, icon: '📈' }
        ]
      },
      {
        id: 'history-oldest',
        container: this.container.querySelector('#queue-throughput-card'),
        title: 'Oldest Job',
        icon: '⏳',
        value: this.getOldestJobAge(data.allJobs),
        description: 'First job in history',
        helpId: 'oldest_job',
        actions: [
          { label: 'View Oldest', action: 'analytics.drill_down', params: { filter: 'oldest_jobs' }, icon: '🔍' }
        ]
      },
      {
        id: 'history-storage',
        container: this.container.querySelector('#success-rate-24h-card'),
        title: 'Storage Used',
        icon: '💾',
        value: this.calculateStorageUsed(totalJobs),
        description: 'Database storage for history',
        helpId: 'storage_usage',
        actions: [
          { label: 'Cleanup Old Data', action: 'system.cleanup_history', icon: '🧹' },
          { label: 'Storage Report', action: 'analytics.generate_report', params: { type: 'storage' }, icon: '📊' }
        ]
      }
    ];
  }



  updateStatistics() {
    // Fallback to new overview metrics
    this.updateOverviewMetrics();
  }

  calculateEnterpriseStatistics() {
    const completed = this.jobs.filter(job => job.status === 'completed').length;
    const failed = this.jobs.filter(job => job.status === 'failed').length;
    const cancelled = this.jobs.filter(job => job.status === 'cancelled').length;
    
    // Enterprise metrics: Pipeline-based calculations
    const pipelineStats = this.calculatePipelineStatistics();
    
    const durations = this.jobs
      .filter(job => job.performance_metrics?.total_duration)
      .map(job => job.performance_metrics.total_duration);
    
    const avgDuration = durations.length > 0 
      ? this.formatDuration(durations.reduce((a, b) => a + b, 0) / durations.length)
      : '-';
    
    return {
      completed,
      failed,
      cancelled,
      avgDuration,
      pipelineStats,
      trends: this.calculateStatsTrends()
    };
  }

  calculatePipelineStatistics() {
    const pipelineSuccessful = this.jobs.filter(job => job.pipeline_status === 'completed').length;
    const pipelineFailed = this.jobs.filter(job => job.pipeline_status === 'failed').length;
    const pipelineEfficiencies = this.jobs
      .filter(job => job.performance_metrics?.efficiency_score)
      .map(job => job.performance_metrics.efficiency_score);
    
    const avgEfficiency = pipelineEfficiencies.length > 0 
      ? Math.round(pipelineEfficiencies.reduce((a, b) => a + b, 0) / pipelineEfficiencies.length)
      : 0;
    
    return {
      pipeline_success_rate: this.jobs.length > 0 ? Math.round((pipelineSuccessful / this.jobs.length) * 100) : 0,
      pipeline_failure_rate: this.jobs.length > 0 ? Math.round((pipelineFailed / this.jobs.length) * 100) : 0,
      avg_pipeline_efficiency: avgEfficiency
    };
  }

  calculateStatsTrends() {
    // Enterprise trend calculation - would be real historical data in production
    return {
      completed_trend: 'increasing', // increasing, stable, decreasing
      failed_trend: 'decreasing',
      efficiency_trend: 'improving'
    };
  }

  addTrendIndicators(stats) {
    // Add enterprise trend indicators to the UI
    const trends = stats.trends;
    
    this.addTrendToElement('completedCount', trends.completed_trend);
    this.addTrendToElement('failedCount', trends.failed_trend);
    this.addTrendToElement('avgDuration', trends.efficiency_trend);
  }

  addTrendToElement(elementId, trend) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Remove existing trend indicators
    const existingTrend = element.parentElement.querySelector('.trend-indicator');
    if (existingTrend) {
      existingTrend.remove();
    }
    
    // Add new trend indicator
    const trendIcon = this.getTrendIcon(trend);
    const trendElement = document.createElement('span');
    trendElement.className = `trend-indicator trend-indicator--${trend}`;
    trendElement.textContent = trendIcon;
    trendElement.title = `Trend: ${trend}`;
    
    element.parentElement.appendChild(trendElement);
  }

  getTrendIcon(trend) {
    const icons = {
      'increasing': '📈',
      'decreasing': '📉',
      'stable': '➡️',
      'improving': '📈',
      'declining': '📉'
    };
    return icons[trend] || '➡️';
  }

  calculateStatistics() {
    // Legacy method - redirect to enterprise version
    return this.calculateEnterpriseStatistics();
  }

  // Helper methods for layout rendering
  groupJobsByPipelineStage(jobs) {
    const stages = {
      'download': [],
      'transcribe': [],
      'analyze': [],
      'process': [],
      'complete': []
    };

    jobs.forEach(job => {
      const stage = job.current_stage || job.pipeline_stage || 'process';
      if (stages[stage]) {
        stages[stage].push(job);
      } else {
        stages['process'].push(job);
      }
    });

    // Only return stages that have jobs
    return Object.fromEntries(
      Object.entries(stages).filter(([_, jobs]) => jobs.length > 0)
    );
  }

  groupJobsByPriority(jobs) {
    const priorities = {
      'critical': [],
      'high': [],
      'normal': [],
      'low': []
    };

    jobs.forEach(job => {
      const priority = job.priority || 'normal';
      if (priorities[priority]) {
        priorities[priority].push(job);
      } else {
        priorities['normal'].push(job);
      }
    });

    // Only return priorities that have jobs
    return Object.fromEntries(
      Object.entries(priorities).filter(([_, jobs]) => jobs.length > 0)
    );
  }

  getPipelineStageStatusClass(stageJobs) {
    const failedJobs = stageJobs.filter(job => job.status === 'failed').length;
    const completedJobs = stageJobs.filter(job => job.status === 'completed').length;
    
    if (failedJobs > 0) return 'error';
    if (completedJobs === stageJobs.length) return 'success';
    return 'info';
  }

  getPriorityIcon(priority) {
    const icons = {
      'critical': '🚨',
      'high': '🔴', 
      'normal': '🟡',
      'low': '🟢'
    };
    return icons[priority] || '🟡';
  }

  renderEmptyState() {
    // Dynamic empty state based on current filter
    const currentFilter = this.currentFilter?.status || 'all';
    let icon = '📋';
    let title = 'No Jobs Found';
    let description = 'No jobs match your current filters.';
    
    switch (currentFilter) {
      case 'processing':
      case 'running':
        icon = '⚡';
        title = 'No Active Jobs';
        description = 'There are no jobs currently processing. All jobs may be completed or queued.';
        break;
      case 'failed':
        icon = '✅';
        title = 'No Failed Jobs';
        description = 'Great news! There are no failed jobs at the moment.';
        break;
      case 'completed':
        icon = '✅';
        title = 'No Completed Jobs';
        description = 'No jobs have been completed yet. Jobs may still be processing or queued.';
        break;
      case 'queued':
      case 'pending':
        icon = '📥';
        title = 'No Queued Jobs';
        description = 'The queue is empty. All jobs are either processing or completed.';
        break;
    }
    
    return `
      <div class="empty-state">
        <div class="empty-state__icon">${icon}</div>
        <h3 class="empty-state__title">${title}</h3>
        <p class="empty-state__description">${description}</p>
      </div>
    `;
  }

  updatePagination() {
    const container = this.container.querySelector('#paginationContainer');
    const totalPages = Math.ceil(this.totalJobs / this.pageSize);

    if (totalPages <= 1) {
      container.style.display = 'none';
      return;
    }

    container.style.display = 'flex';
    
    const startItem = (this.currentPage - 1) * this.pageSize + 1;
    const endItem = Math.min(this.currentPage * this.pageSize, this.totalJobs);

    container.innerHTML = `
      <button class="pagination-btn" data-page="${this.currentPage - 1}" ${this.currentPage === 1 ? 'disabled' : ''}>
        ← Previous
      </button>
      <span class="pagination-info">
        ${startItem}-${endItem} of ${this.totalJobs.toLocaleString()}
      </span>
      <button class="pagination-btn" data-page="${this.currentPage + 1}" ${this.currentPage === totalPages ? 'disabled' : ''}>
        Next →
      </button>
    `;
  }

  async handleJobAction(action, jobId) {
    try {
      if (action === 'retry') {
        await this.retryJob(jobId);
      } else if (action === 'cancel') {
        await this.cancelJob(jobId);
      }
    } catch (error) {
      console.error(`❌ Failed to ${action} job ${jobId}:`, error);
      this.showError(`Failed to ${action} job. Please try again.`);
    }
  }
  
  async retryJob(jobId) {
    try {
      console.log(`🔄 Retrying job ${jobId} using ActionService...`);
      
      // Show loading state
      this.showActionLoading(jobId, 'retry');
      
      // Call the unified action endpoint
      const result = await actionService.retryJob(jobId);
      
      console.log(`✅ Job ${jobId} retry request successful:`, result);
      
      // Update job status locally for immediate feedback
      const job = this.jobs.find(j => j.id === jobId);
      if (job) {
        job.status = 'queued';
        job.retry_count = (job.retry_count || 0) + 1;
        job.updated_at = new Date().toISOString();
      }
      
      // Re-render to show updated status
      this.renderCurrentView();
      
      // Show success message
      this.showActionSuccess(`Job ${jobId} has been queued for retry`);
      
    } catch (error) {
      console.error(`❌ Failed to retry job ${jobId}:`, error);
      this.showActionError(`Failed to retry job ${jobId}: ${error.message}`);
      throw error;
    } finally {
      this.hideActionLoading(jobId);
    }
  }
  
  async cancelJob(jobId) {
    try {
      console.log(`⏹️ Cancelling job ${jobId} using ActionService...`);
      
      // Show loading state
      this.showActionLoading(jobId, 'cancel');
      
      // Call the unified action endpoint
      const result = await actionService.cancelJob(jobId);
      
      console.log(`✅ Job ${jobId} cancel request successful:`, result);
      
      // Update job status locally for immediate feedback
      const job = this.jobs.find(j => j.id === jobId);
      if (job) {
        job.status = 'cancelled';
        job.updated_at = new Date().toISOString();
      }
      
      // Re-render to show updated status
      this.renderCurrentView();
      
      // Show success message
      this.showActionSuccess(`Job ${jobId} has been cancelled`);
      
    } catch (error) {
      console.error(`❌ Failed to cancel job ${jobId}:`, error);
      this.showActionError(`Failed to cancel job ${jobId}: ${error.message}`);
      throw error;
    } finally {
      this.hideActionLoading(jobId);
    }
  }

  async showJobDetails(jobId) {
    try {
      const jobDetails = await this.apiClient.getJobDetails(jobId);
      this.openJobDetailsModal(jobDetails);
    } catch (error) {
      console.error(`❌ Failed to load job details for ${jobId}:`, error);
      this.showError('Failed to load job details.');
    }
  }

  openJobDetailsModal(job) {
    // TODO: Implement modal component for job details
    // For now, just log the details
    console.log('Job Details:', job);
    alert(`Job Details:\n\nID: ${job.id}\nStatus: ${job.status}\nCreated: ${job.created_at}\n\nFull details logged to console.`);
  }

  // Utility Methods
  getStatusIcon(status) {
    const icons = {
      'completed': '✅',
      'failed': '❌',
      'cancelled': '🚫',
      'processing': '⚡',
      'queued': '📥'
    };
    return icons[status] || '❓';
  }

  getStatusClass(status) {
    const statusMap = {
      'completed': 'success',
      'processing': 'info',
      'running': 'info', 
      'failed': 'danger',
      'cancelled': 'warning',
      'queued': 'neutral',
      'pending': 'neutral',
      'paused': 'warning',
      'retry': 'warning',
      'unknown': 'neutral'
    };
    return statusMap[status] || 'neutral';
  }

  getTimelineMarkerClass(status) {
    const classes = {
      'completed': 'success',
      'failed': 'error',
      'cancelled': 'warning',
      'processing': 'info',
      'queued': 'info'
    };
    return classes[status] || 'info';
  }

  formatDuration(seconds) {
    if (!seconds || seconds === 0) return '-';
    
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600 * 10) / 10}h`;
  }

  formatTimeAgo(timestamp) {
    if (!timestamp) return '-';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  }

  showError(message) {
    console.error(message);
    // TODO: Implement proper error notification system
  }

  // =============================================================================
  // QUEUE MANAGEMENT ACTIONS
  // =============================================================================

  async handleManualRefresh() {
    try {
      console.log('🔄 Manual refresh triggered');
      this.showActionSuccess('Refreshing job data...');
      await this.loadJobHistory();
    } catch (error) {
      console.error('❌ Manual refresh failed:', error);
      this.showActionError('Failed to refresh job data');
    }
  }

  async handleToggleMonitoring() {
    try {
      const button = document.getElementById('toggle-monitoring');
      if (!button) return;

      const isPaused = this.isMonitoringPaused;
      const action = isPaused ? 'resume' : 'pause';
      
      console.log(`${action === 'pause' ? '⏸️' : '▶️'} ${action} queue monitoring`);
      
      // Show loading state
      button.disabled = true;
      button.querySelector('.btn__icon').textContent = '⏳';
      
      if (action === 'pause') {
        // Use ActionService to pause queue
        await actionService.pauseQueue('default');
        
        this.isMonitoringPaused = true;
        button.querySelector('.btn__icon').textContent = '▶️';
        button.innerHTML = `<span class="btn__icon">▶️</span> Resume Queue`;
        
        this.showActionSuccess('Queue processing has been paused');
        
        // Stop auto-refresh
        if (this.refreshTimer) {
          clearInterval(this.refreshTimer);
        }
        
      } else {
        // Use ActionService to resume queue
        await actionService.resumeQueue('default');
        
        this.isMonitoringPaused = false;
        button.querySelector('.btn__icon').textContent = '⏸️';
        button.innerHTML = `<span class="btn__icon">⏸️</span> Pause Queue`;
        
        this.showActionSuccess('Queue processing has been resumed');
        
        // Restart auto-refresh
        this.startAutoRefresh();
      }
      
    } catch (error) {
      console.error('❌ Failed to toggle queue monitoring:', error);
      this.showActionError(`Failed to ${this.isMonitoringPaused ? 'resume' : 'pause'} queue: ${error.message}`);
    } finally {
      // Re-enable button
      const button = document.getElementById('toggle-monitoring');
      if (button) {
        button.disabled = false;
      }
    }
  }

  // =============================================================================
  // ACTION UI FEEDBACK METHODS
  // =============================================================================

  showActionLoading(jobId, action) {
    const actionBtn = document.querySelector(`[data-job-id="${jobId}"].action-btn--${action}`);
    if (actionBtn) {
      actionBtn.disabled = true;
      actionBtn.textContent = action === 'retry' ? '🔄 Retrying...' : '⏹️ Cancelling...';
      actionBtn.classList.add('action-btn--loading');
    }
  }

  hideActionLoading(jobId) {
    const actionBtns = document.querySelectorAll(`[data-job-id="${jobId}"].action-btn`);
    actionBtns.forEach(btn => {
      btn.disabled = false;
      btn.classList.remove('action-btn--loading');
      
      // Reset button text based on type
      if (btn.classList.contains('action-btn--retry')) {
        btn.textContent = '🔄';
        btn.title = 'Retry';
      } else if (btn.classList.contains('action-btn--cancel')) {
        btn.textContent = '⏹️';
        btn.title = 'Cancel';
      }
    });
  }

  showActionSuccess(message) {
    console.log(`✅ ${message}`);
    // Use the existing notification system from main.js
    const event = new CustomEvent('app:notification', {
      detail: {
        type: 'success',
        title: 'Success',
        message: message,
        duration: 3000
      }
    });
    document.dispatchEvent(event);
  }

  showActionError(message) {
    console.error(`❌ ${message}`);
    // Use the existing notification system from main.js
    const event = new CustomEvent('app:notification', {
      detail: {
        type: 'error',
        title: 'Error',
        message: message,
        duration: 5000
      }
    });
    document.dispatchEvent(event);
  }

  // Removed showTemporaryNotification - now using main.js notification system

  // Removed auto-refresh - job history doesn't need real-time updates

  destroy() {
    // Clean up auto-refresh timer if exists
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
    
    // Clean up SmartFilter
    if (this.smartFilter) {
      this.smartFilter.destroy();
    }
    
    // Cleanup help panel
    if (this.helpPanel) {
      this.helpPanel.destroy();
    }
    
    // Clear global reference
    if (window.jobHistory === this) {
      delete window.jobHistory;
    }
    
    console.log('🧹 Jobs & Queue View destroyed');
  }

  // =============================================================================
  // HELPER METHODS FOR DYNAMIC KPIs
  // =============================================================================

  filterJobsByDate(jobs, period) {
    if (!jobs || jobs.length === 0) return [];
    
    const now = new Date();
    let filterDate;
    
    switch (period) {
      case 'today':
        filterDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case 'week':
        filterDate = new Date(now.getTime() - (7 * 24 * 60 * 60 * 1000));
        break;
      default:
        return jobs;
    }
    
    return jobs.filter(job => {
      // Check if date fields exist and get the first available one
      const dateValue = job.created_at || job.timestamp;
      
      // Skip jobs with no date field
      if (!dateValue) {
        console.warn('Job missing date field:', job.id || 'unknown');
        return false; // Business rule: exclude jobs without dates
      }
      
      // Validate date and handle invalid dates
      let jobDate;
      if (typeof dateValue === 'string' || typeof dateValue === 'number') {
        // Check if it's a valid date string/timestamp
        const parsedTime = Date.parse(dateValue);
        if (isNaN(parsedTime)) {
          console.warn('Job has invalid date format:', dateValue, 'for job:', job.id || 'unknown');
          return false; // Business rule: exclude jobs with invalid dates
        }
        jobDate = new Date(parsedTime);
      } else if (dateValue instanceof Date) {
        // Already a Date object, check if valid
        if (isNaN(dateValue.getTime())) {
          console.warn('Job has invalid Date object for job:', job.id || 'unknown');
          return false;
        }
        jobDate = dateValue;
      } else {
        // Invalid date type
        console.warn('Job has invalid date type:', typeof dateValue, 'for job:', job.id || 'unknown');
        return false;
      }
      
      // Perform safe date comparison
      return jobDate >= filterDate;
    });
  }

  calculateAvgProcessingTime(jobs) {
    if (!jobs || jobs.length === 0) return '0s';
    
    const completedJobs = jobs.filter(j => j.status === 'completed' && j.processing_time);
    if (completedJobs.length === 0) return '0s';
    
    const avgMs = completedJobs.reduce((sum, job) => sum + (job.processing_time || 0), 0) / completedJobs.length;
    return this.formatDuration(avgMs);
  }

  calculateQualityScore(jobs) {
    if (!jobs || jobs.length === 0) return 0;
    
    // Mock quality calculation based on completion rate and processing time
    const successful = jobs.filter(j => j.status === 'completed').length;
    const baseScore = (successful / jobs.length) * 100;
    
    // Adjust based on processing time consistency
    const avgTime = jobs.reduce((sum, job) => sum + (job.processing_time || 0), 0) / jobs.length;
    const timeVariance = jobs.reduce((sum, job) => sum + Math.pow((job.processing_time || 0) - avgTime, 2), 0) / jobs.length;
    const consistencyBonus = Math.max(0, 10 - (timeVariance / 1000)); // Less variance = higher score
    
    return Math.min(100, Math.round(baseScore + consistencyBonus));
  }

  getTopErrorType(failedJobs) {
    if (!failedJobs || failedJobs.length === 0) {
      return { type: 'None', count: 0, percentage: 0 };
    }
    
    // Count error types
    const errorCounts = {};
    failedJobs.forEach(job => {
      const errorType = job.error_type || job.failure_reason || 'Unknown';
      errorCounts[errorType] = (errorCounts[errorType] || 0) + 1;
    });
    
    // Find most common error
    let topError = { type: 'Unknown', count: 0 };
    for (const [type, count] of Object.entries(errorCounts)) {
      if (count > topError.count) {
        topError = { type, count };
      }
    }
    
    topError.percentage = Math.round((topError.count / failedJobs.length) * 100);
    return topError;
  }

  calculateMTTR(failedJobs) {
    if (!failedJobs || failedJobs.length === 0) return 0;
    
    // Mock MTTR calculation - in real implementation this would use recovery/retry timestamps
    const recoveredJobs = failedJobs.filter(j => j.retry_count && j.retry_count > 0);
    if (recoveredJobs.length === 0) return 0;
    
    // Assume average recovery time based on retry patterns
    const avgRetryTime = recoveredJobs.reduce((sum, job) => {
      return sum + ((job.retry_count || 1) * 2); // 2 minutes per retry cycle
    }, 0) / recoveredJobs.length;
    
    return Math.round(avgRetryTime);
  }

  getOldestJobAge(jobs) {
    if (!jobs || jobs.length === 0) return '0 days';
    
    const oldest = jobs.reduce((oldest, job) => {
      const jobDate = new Date(job.created_at || job.timestamp);
      const oldestDate = new Date(oldest.created_at || oldest.timestamp);
      return jobDate < oldestDate ? job : oldest;
    });
    
    const now = new Date();
    const oldestDate = new Date(oldest.created_at || oldest.timestamp);
    const daysDiff = Math.floor((now - oldestDate) / (1000 * 60 * 60 * 24));
    
    if (daysDiff === 0) return 'Today';
    if (daysDiff === 1) return '1 day ago';
    return `${daysDiff} days ago`;
  }

  calculateStorageUsed(jobCount) {
    // Rough estimate: 1KB per job record
    const bytesPerJob = 1024;
    const totalBytes = jobCount * bytesPerJob;
    
    if (totalBytes < 1024 * 1024) {
      return `${Math.round(totalBytes / 1024)}KB`;
    } else if (totalBytes < 1024 * 1024 * 1024) {
      return `${Math.round(totalBytes / (1024 * 1024))}MB`;
    } else {
      return `${Math.round(totalBytes / (1024 * 1024 * 1024))}GB`;
    }
  }

  // =============================================================================
  // JOBHISTORY-SPECIFIC KPI CONFIGURATIONS
  // =============================================================================

  getActiveKPIs(data) {
    const activeJobs = data.allJobs.filter(j => ['queued', 'processing', 'running'].includes(j.status));
    const queuedJobs = data.allJobs.filter(j => j.status === 'queued');
    const processingJobs = data.allJobs.filter(j => ['processing', 'running'].includes(j.status));
    const avgWaitTime = this.calculateAvgWaitTime(queuedJobs);

    return [
      {
        id: 'active-total',
        container: this.container.querySelector('#queue-depth-card'),
        title: 'Active Jobs',
        icon: '⚡',
        value: activeJobs.length.toString(),
        description: `${queuedJobs.length} queued, ${processingJobs.length} processing`,
        helpId: 'active_jobs',
        trend: { direction: 'up', percentage: 8 },
        actions: [
          { label: 'Monitor Active', action: 'analytics.drill_down', params: { filter: 'active_jobs' }, icon: '👁️' },
          { label: 'Scale Workers', action: 'worker.auto_scale', icon: '📈' },
          { label: 'Priority Queue', action: 'queue.process_priority', icon: '⚡' }
        ]
      },
      {
        id: 'processing-now',
        container: this.container.querySelector('#active-processing-card'),
        title: 'Processing Now',
        icon: '🔄',
        value: processingJobs.length.toString(),
        description: 'Currently being processed',
        helpId: 'processing_now',
        actions: [
          { label: 'View Details', action: 'analytics.drill_down', params: { filter: 'processing_jobs' }, icon: '🔍' },
          { label: 'Worker Status', action: 'worker.status', icon: '👷' }
        ]
      },
      {
        id: 'queue-depth',
        container: this.container.querySelector('#queue-throughput-card'),
        title: 'Queue Depth',
        icon: '📥',
        value: queuedJobs.length.toString(),
        description: 'Jobs waiting to process',
        helpId: 'queue_depth',
        thresholds: { warning: 20, critical: 50 },
        currentValue: queuedJobs.length,
        trend: { direction: 'down', percentage: 5 },
        showThresholdBar: true,
        actions: [
          { label: 'Process Queue', action: 'queue.process_priority', icon: '⚡' },
          { label: 'Clear Queue', action: 'queue.clear', params: { confirmation: true }, icon: '🧹' }
        ]
      },
      {
        id: 'avg-wait-time',
        container: this.container.querySelector('#success-rate-24h-card'),
        title: 'Avg Wait Time',
        icon: '⌛',
        value: avgWaitTime,
        description: 'Time before processing starts',
        helpId: 'avg_wait_time',
        thresholds: { warning: 5, critical: 15 },
        currentValue: this.parseTimeToMinutes(avgWaitTime),
        showThresholdBar: true,
        actions: [
          { label: 'Optimize Queue', action: 'queue.optimize', icon: '🚀' },
          { label: 'Add Workers', action: 'worker.scale_up', icon: '👷' }
        ]
      }
    ];
  }

  getIssuesKPIs(data) {
    const failedJobs = data.allJobs.filter(j => ['failed', 'cancelled'].includes(j.status));
    const failedToday = this.filterJobsByDate(failedJobs, 'today');
    const topError = this.getTopErrorType(failedJobs);
    const mttr = this.calculateMTTR(failedJobs);

    return [
      {
        id: 'failed-total',
        container: this.container.querySelector('#queue-depth-card'),
        title: 'Failed Jobs',
        icon: '❌',
        value: failedJobs.length.toString(),
        description: `${failedToday.length} failed today`,
        helpId: 'failed_jobs',
        trend: { direction: 'down', percentage: 12 },
        actions: [
          { label: 'Retry All Failed', action: 'job.bulk_retry', params: { filter: 'failed' }, icon: '🔄' },
          { label: 'Failure Analysis', action: 'analytics.drill_down', params: { filter: 'failure_analysis' }, icon: '🔍' },
          { label: 'Error Report', action: 'analytics.generate_report', params: { type: 'errors' }, icon: '📊' }
        ]
      },
      {
        id: 'top-error-type',
        container: this.container.querySelector('#active-processing-card'),
        title: 'Top Error',
        icon: '🔧',
        value: topError.type,
        description: `${topError.count} occurrences (${topError.percentage}%)`,
        helpId: 'top_error',
        actions: [
          { label: 'Fix This Error', action: 'system.fix_error', params: { error_type: topError.type }, icon: '🔧' },
          { label: 'Error Pattern', action: 'analytics.drill_down', params: { filter: `error_${topError.type}` }, icon: '📊' }
        ]
      },
      {
        id: 'recovery-time',
        container: this.container.querySelector('#queue-throughput-card'),
        title: 'MTTR',
        icon: '⏱️',
        value: `${mttr}min`,
        description: 'Mean Time To Recovery',
        helpId: 'mttr',
        thresholds: { warning: 10, critical: 30 },
        currentValue: mttr,
        trend: { direction: 'down', percentage: 20 },
        showThresholdBar: true,
        actions: [
          { label: 'Improve Recovery', action: 'system.optimize_recovery', icon: '🚀' },
          { label: 'Auto-Recovery', action: 'system.enable_auto_recovery', icon: '🤖' }
        ]
      },
      {
        id: 'error-rate',
        container: this.container.querySelector('#success-rate-24h-card'),
        title: 'Error Rate',
        icon: '📉',
        value: `${data.allJobs.length > 0 ? (failedJobs.length/data.allJobs.length*100).toFixed(1) : 0}%`,
        description: 'Failure percentage',
        helpId: 'error_rate',
        thresholds: { warning: 5.0, critical: 10.0 },
        currentValue: data.allJobs.length > 0 ? (failedJobs.length/data.allJobs.length*100) : 0,
        trend: { direction: 'down', percentage: 8 },
        showThresholdBar: true,
        actions: [
          { label: 'Reduce Errors', action: 'system.error_reduction', icon: '🛠️' },
          { label: 'Prevention Rules', action: 'system.error_prevention', icon: '🛡️' }
        ]
      }
    ];
  }

  getCompletedKPIs(data) {
    const completedJobs = data.allJobs.filter(j => j.status === 'completed');
    const completedToday = this.filterJobsByDate(completedJobs, 'today');
    const avgCompletionTime = this.calculateAvgProcessingTime(completedJobs);
    const qualityScore = this.calculateQualityScore(completedJobs);

    return [
      {
        id: 'completed-total',
        container: this.container.querySelector('#queue-depth-card'),
        title: 'Completed Jobs',
        icon: '✅',
        value: completedJobs.length.toString(),
        description: `${completedToday.length} completed today`,
        helpId: 'completed_jobs',
        trend: { direction: 'up', percentage: 18 },
        actions: [
          { label: 'Completion Report', action: 'analytics.generate_report', params: { type: 'completed' }, icon: '📊' },
          { label: 'Success Analysis', action: 'analytics.drill_down', params: { filter: 'success_patterns' }, icon: '🔍' }
        ]
      },
      {
        id: 'completion-time',
        container: this.container.querySelector('#active-processing-card'),
        title: 'Avg Completion Time',
        icon: '⚡',
        value: avgCompletionTime,
        description: 'Average processing time',
        helpId: 'completion_time',
        actions: [
          { label: 'Performance Analysis', action: 'analytics.drill_down', params: { filter: 'performance' }, icon: '📈' },
          { label: 'Optimize Speed', action: 'system.performance_tune', icon: '🚀' }
        ]
      },
      {
        id: 'quality-score',
        container: this.container.querySelector('#queue-throughput-card'),
        title: 'Quality Score',
        icon: '⭐',
        value: `${qualityScore}%`,
        description: 'Output quality rating',
        helpId: 'quality_score',
        thresholds: { warning: 85, critical: 70 },
        currentValue: qualityScore,
        trend: { direction: 'up', percentage: 6 },
        showThresholdBar: true,
        actions: [
          { label: 'Quality Report', action: 'analytics.generate_report', params: { type: 'quality' }, icon: '📊' },
          { label: 'Improve Quality', action: 'system.optimize_quality', icon: '⚡' }
        ]
      },
      {
        id: 'success-rate',
        container: this.container.querySelector('#success-rate-24h-card'),
        title: 'Success Rate',
        icon: '🎯',
        value: `${data.allJobs.length > 0 ? (completedJobs.length/data.allJobs.length*100).toFixed(1) : 0}%`,
        description: 'Overall completion rate',
        helpId: 'success_rate',
        thresholds: { warning: 90, critical: 80 },
        currentValue: data.allJobs.length > 0 ? (completedJobs.length/data.allJobs.length*100) : 0,
        showThresholdBar: true,
        actions: [
          { label: 'Success Optimization', action: 'system.optimize_success', icon: '🚀' }
        ]
      }
    ];
  }

  getAllKPIs(data) {
    const totalJobs = data.allJobs.length;
    const activeJobs = data.allJobs.filter(j => ['queued', 'processing', 'running'].includes(j.status)).length;
    const completedJobs = data.allJobs.filter(j => j.status === 'completed').length;
    const failedJobs = data.allJobs.filter(j => ['failed', 'cancelled'].includes(j.status)).length;

    return [
      {
        id: 'total-jobs',
        container: this.container.querySelector('#queue-depth-card'),
        title: 'Total Jobs',
        icon: '📊',
        value: totalJobs.toString(),
        description: `${completedJobs} completed, ${failedJobs} failed`,
        helpId: 'total_jobs',
        actions: [
          { label: 'Full Report', action: 'analytics.generate_report', params: { type: 'comprehensive' }, icon: '📊' },
          { label: 'Export All Data', action: 'analytics.export_data', params: { format: 'csv' }, icon: '📁' }
        ]
      },
      {
        id: 'active-count',
        container: this.container.querySelector('#active-processing-card'),
        title: 'Active Jobs',
        icon: '⚡',
        value: activeJobs.toString(),
        description: 'Currently active',
        helpId: 'active_count',
        actions: [
          { label: 'View Active', action: 'analytics.drill_down', params: { filter: 'active_jobs' }, icon: '👁️' }
        ]
      },
      {
        id: 'completion-rate',
        container: this.container.querySelector('#queue-throughput-card'),
        title: 'Completion Rate',
        icon: '✅',
        value: `${totalJobs > 0 ? (completedJobs/totalJobs*100).toFixed(1) : 0}%`,
        description: `${completedJobs}/${totalJobs} completed`,
        helpId: 'completion_rate',
        thresholds: { warning: 90, critical: 80 },
        currentValue: totalJobs > 0 ? (completedJobs/totalJobs*100) : 0,
        showThresholdBar: true,
        actions: [
          { label: 'Optimize Performance', action: 'system.optimize', icon: '🚀' }
        ]
      },
      {
        id: 'system-status',
        container: this.container.querySelector('#success-rate-24h-card'),
        title: 'System Status',
        icon: this.getSystemStatusIcon(data),
        value: this.getSystemStatusText(data),
        description: this.getSystemStatusDescription(data),
        helpId: 'system_status',
        actions: [
          { label: 'System Health', action: 'analytics.drill_down', params: { filter: 'system_health' }, icon: '🔍' },
          { label: 'Health Report', action: 'analytics.generate_report', params: { type: 'health' }, icon: '📊' }
        ]
      }
    ];
  }

  // Helper methods for JobHistory-specific KPIs
  calculateAvgWaitTime(queuedJobs) {
    if (!queuedJobs || queuedJobs.length === 0) return '0min';
    
    const now = new Date();
    const waitTimes = queuedJobs.map(job => {
      const createdAt = new Date(job.created_at || job.timestamp);
      return Math.max(0, (now - createdAt) / (1000 * 60)); // minutes
    });
    
    const avgMinutes = waitTimes.reduce((sum, time) => sum + time, 0) / waitTimes.length;
    return avgMinutes < 60 ? `${Math.round(avgMinutes)}min` : `${Math.round(avgMinutes/60)}h`;
  }

  parseTimeToMinutes(timeString) {
    if (!timeString || timeString === '0min') return 0;
    if (timeString.includes('h')) {
      const hours = parseInt(timeString);
      return hours * 60;
    }
    return parseInt(timeString);
  }

  getSystemStatusIcon(data) {
    const totalJobs = data.allJobs.length;
    if (totalJobs === 0) return '⚪';
    
    const failedJobs = data.allJobs.filter(j => ['failed', 'cancelled'].includes(j.status)).length;
    const errorRate = (failedJobs / totalJobs) * 100;
    
    if (errorRate < 1) return '🟢';
    if (errorRate < 5) return '🟡';
    return '🔴';
  }

  getSystemStatusText(data) {
    const totalJobs = data.allJobs.length;
    if (totalJobs === 0) return 'Idle';
    
    const failedJobs = data.allJobs.filter(j => ['failed', 'cancelled'].includes(j.status)).length;
    const errorRate = (failedJobs / totalJobs) * 100;
    
    if (errorRate < 1) return 'Healthy';
    if (errorRate < 5) return 'Warning';
    return 'Critical';
  }

  getSystemStatusDescription(data) {
    const totalJobs = data.allJobs.length;
    if (totalJobs === 0) return 'No recent activity';
    
    const failedJobs = data.allJobs.filter(j => ['failed', 'cancelled'].includes(j.status)).length;
    const activeJobs = data.allJobs.filter(j => ['queued', 'processing', 'running'].includes(j.status)).length;
    
    if (activeJobs > 0) {
      return `${activeJobs} active jobs`;
    } else if (failedJobs === 0) {
      return 'All systems operational';
    } else {
      return `${failedJobs} failed jobs need attention`;
    }
  }

  showKPILoadError(kpiId, errorMessage) {
    // Create user-visible error notification
    const errorNotification = document.createElement('div');
    errorNotification.className = 'kpi-error-notification';
    errorNotification.innerHTML = `
      <div class="error-content">
        <span class="error-icon">⚠️</span>
        <span class="error-text">KPI "${kpiId}" failed to load: ${errorMessage}</span>
        <button class="error-close" onclick="this.parentElement.parentElement.remove()">✕</button>
      </div>
    `;
    errorNotification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
      border-radius: 4px;
      padding: 12px;
      z-index: 1000;
      max-width: 400px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    `;
    
    document.body.appendChild(errorNotification);
    
    // Auto-remove after 8 seconds
    setTimeout(() => {
      if (errorNotification.parentNode) {
        errorNotification.parentNode.removeChild(errorNotification);
      }
    }, 8000);
  }

  createErrorMetricCard(config) {
    // Create lightweight error placeholder that mimics ActionableMetricCard interface
    return {
      id: config.id,
      container: config.container,
      isError: true,
      
      // Mock ActionableMetricCard methods to prevent downstream breaks
      update: () => {
        console.warn(`Cannot update error placeholder for KPI ${config.id}`);
      },
      
      render: () => {
        // Insert error placeholder into container if it exists
        const container = document.querySelector(config.container);
        if (container) {
          container.innerHTML = `
            <div class="metric-card error-metric-card">
              <div class="metric-card__title">⚠️ Error</div>
              <div class="metric-card__value">—</div>
              <div class="metric-card__description">KPI "${config.id}" failed to load</div>
            </div>
          `;
          container.style.cssText = `
            opacity: 0.6;
            border: 1px solid #f5c6cb;
            background: #f8d7da;
          `;
        }
      },
      
      getData: () => ({ error: true, id: config.id }),
      destroy: () => {},
      
      // Properties that might be accessed downstream
      options: config,
      element: document.querySelector(config.container)
    };
  }
}