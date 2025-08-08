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
    this.selectedJob = null;
    this.smartFilter = null;
    this.helpPanel = null;
    
    // Auto-refresh state
    this.refreshTimer = null;
    this.countdownTimer = null;
    this.refreshCountdown = 30;
    this.isMonitoringPaused = false;
  }

  async init() {
    // Make globally accessible EARLY for onclick handlers
    window.jobHistory = this;
    console.log('🔧 Global jobHistory set:', window.jobHistory);
    
    this.render();
    this.setupHelpSystem();
    this.setupSmartFilter();
    this.setupPaginationListeners();
    await this.loadJobHistory();
    this.setupEventListeners();
    
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
          </div>
          <div id="smartFilterContainer"></div>
        </div>

        <!-- Jobs Overview Metrics -->
        <div class="jobs-overview">
          <h3 class="section-title">
            📊 Pipeline Overview
            <button class="help-icon" data-section="pipeline_metrics">❓</button>
          </h3>
          <div class="overview-metrics">
            <div id="total-jobs-card"></div>
            <div id="active-jobs-card"></div>
            <div id="success-rate-card"></div>
            <div id="avg-processing-card"></div>
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

        <!-- Compact Bottom Section -->
        <div class="bottom-section">
          <!-- Queue Analytics - Compact -->
          <div class="queue-analytics compact">
            <div class="compact-header">
              <h4>📊 Queue Analytics</h4>
              <div class="compact-controls">
                <select id="analytics-timeframe" class="compact-select">
                  <option value="1h">Last Hour</option>
                  <option value="6h">Last 6h</option>
                  <option value="24h">Last 24h</option>
                </select>
                <button class="btn-compact" id="refresh-analytics">Refresh</button>
              </div>
            </div>
            <div id="analytics-content" class="compact-content">
              <div class="analytics-overview">
                <div class="analytics-item">
                  <span class="analytics-label">Processing Rate:</span>
                  <span class="analytics-value" id="processing-rate">--/min</span>
                  <span class="analytics-change improving" id="rate-trend">↗ +12%</span>
                </div>
                <div class="analytics-item">
                  <span class="analytics-label">Queue Depth:</span>
                  <span class="analytics-value" id="queue-depth">-- jobs</span>
                  <span class="analytics-change stable" id="depth-trend">→ 0%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Worker Health - Compact -->
          <div class="worker-health compact">
            <div class="compact-header">
              <h4>⚙️ Worker Health</h4>
              <div class="compact-controls">
                <button class="btn-compact" id="refresh-workers">Status</button>
              </div>
            </div>
            <div id="worker-content" class="compact-content">
              <div class="worker-overview">
                <div class="worker-item">
                  <span class="worker-label">Active Workers:</span>
                  <span class="worker-value" id="active-workers">5/5</span>
                  <span class="worker-status healthy" id="worker-health">🟢</span>
                </div>
                <div class="worker-item">
                  <span class="worker-label">Avg Load:</span>
                  <span class="worker-value" id="worker-load">--%</span>
                  <span class="worker-status" id="load-status">🟡</span>
                </div>
              </div>
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
      
      // Refresh analytics button
      if (e.target.closest('#refresh-analytics')) {
        this.updateQueueAnalytics();
      }
      
      // Refresh workers button
      if (e.target.closest('#refresh-workers')) {
        this.updateWorkerHealth();
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
    const dashboardData = ssotData.dashboard || {};
    const jobs = dashboardData.jobs?.recent_jobs || [];
    const queueData = dashboardData.queue || {};
    const recentActivity = dashboardData.recent_activity || [];
    
    // Process job data
    this.historyData = {
      jobs: jobs,
      total: jobs.length,
      stats: queueData,
      activity: recentActivity,
      lastUpdated: new Date().toISOString(),
      source: 'ssot'
    };
    
    // Enterprise job enrichment with pipeline data
    this.enrichJobsWithPipelineData(this.historyData.jobs).then(enrichedJobs => {
      this.jobs = enrichedJobs;
      this.totalJobs = this.historyData.total;
      
      // Calculate enterprise analytics
      this.calculateHistoryAnalytics();
      
      // Update UI with enterprise data
      this.updateOverviewMetrics();
      
      // Update filter results count
      if (this.smartFilter) {
        this.smartFilter.updateResultsCount(this.jobs.length, this.totalJobs);
      }
      
      // Render current view with enterprise features
      this.renderCurrentView();
      this.updatePagination();
      
      // Cache data for offline access
      this.cacheHistoryData();

      console.log(`✅ SSOT job history loaded: ${this.jobs.length} jobs with pipeline data`);
    });
  }

  // Enterprise fallback methods
  getFallbackJobHistory() {
    // Generate realistic mock jobs for demonstration when APIs are unavailable
    const mockJobs = this.generateMockJobs(12);
    
    return {
      jobs: mockJobs,
      total: mockJobs.length,
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
        this.jobs = this.historyData.jobs || [];
        this.totalJobs = this.historyData.total || 0;
        this.updateOverviewMetrics();
        this.renderCurrentView();
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
    
    // Apply filter and re-render
    this.renderCurrentView();
    this.updateOverviewMetrics();
    
    // Update results count
    const filteredJobs = this.getFilteredJobs();
    if (this.smartFilter) {
      this.smartFilter.updateResultsCount(filteredJobs.length, (this.jobs || []).length);
    }
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
    const totalJobs = this.jobs.length;
    const activeJobs = this.jobs.filter(job => ['queued', 'processing', 'running'].includes(job.status)).length;
    const completedJobs = this.jobs.filter(job => job.status === 'completed').length;
    const successRate = totalJobs > 0 ? Math.round((completedJobs / totalJobs) * 100) : 0;
    
    // Calculate average processing time from completed jobs
    const completedJobsWithTime = this.jobs.filter(job => 
      job.status === 'completed' && job.performance_metrics?.total_duration
    );
    const avgProcessingTime = completedJobsWithTime.length > 0 
      ? Math.round(completedJobsWithTime.reduce((sum, job) => sum + job.performance_metrics.total_duration, 0) / completedJobsWithTime.length)
      : 0;

    // Total Jobs
    this.createMetricCard('total-jobs-card', {
      title: 'Total Jobs',
      value: totalJobs.toString(),
      description: 'In processing pipeline',
      status: 'neutral',
      icon: '📋'
    });

    // Active Jobs
    this.createMetricCard('active-jobs-card', {
      title: 'Active Jobs',
      value: activeJobs.toString(),
      description: `${activeJobs} currently processing`,
      status: activeJobs > 10 ? 'warning' : 'good',
      icon: '⚡'
    });

    // Success Rate
    this.createMetricCard('success-rate-card', {
      title: 'Success Rate',
      value: `${successRate}%`,
      description: 'Pipeline reliability',
      status: successRate > 90 ? 'good' : (successRate > 70 ? 'warning' : 'danger'),
      icon: '🎯'
    });

    // Average Processing Time
    this.createMetricCard('avg-processing-card', {
      title: 'Avg Processing',
      value: `${avgProcessingTime}s`,
      description: 'Per job completion',
      status: avgProcessingTime < 120 ? 'good' : (avgProcessingTime < 300 ? 'warning' : 'danger'),
      icon: '⏱️'
    });

    // Update queue analytics
    this.updateQueueAnalytics();
    
    // Update worker health
    this.updateWorkerHealth();
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

  updateQueueAnalytics() {
    // Mock queue analytics - would be real data from /api/queue/analytics
    const processingRate = Math.round(15 + Math.random() * 10); // jobs per minute
    const queueDepth = Math.round(5 + Math.random() * 15); // waiting jobs
    
    const processingRateEl = document.getElementById('processing-rate');
    const queueDepthEl = document.getElementById('queue-depth');
    
    if (processingRateEl) processingRateEl.textContent = `${processingRate}/min`;
    if (queueDepthEl) queueDepthEl.textContent = `${queueDepth} jobs`;
    
    // Mock trends
    const rateTrend = processingRate > 20 ? 'improving' : processingRate < 15 ? 'degrading' : 'stable';
    const depthTrend = queueDepth < 10 ? 'improving' : queueDepth > 20 ? 'degrading' : 'stable';
    
    const rateTrendEl = document.getElementById('rate-trend');
    const depthTrendEl = document.getElementById('depth-trend');
    
    if (rateTrendEl) {
      const rateChange = rateTrend === 'improving' ? '↗ +12%' : 
                        rateTrend === 'degrading' ? '↘ -8%' : '→ +2%';
      rateTrendEl.textContent = rateChange;
      rateTrendEl.className = `analytics-change ${rateTrend}`;
    }
    
    if (depthTrendEl) {
      const depthChange = depthTrend === 'improving' ? '↗ -15%' : 
                         depthTrend === 'degrading' ? '↘ +25%' : '→ 0%';
      depthTrendEl.textContent = depthChange;
      depthTrendEl.className = `analytics-change ${depthTrend}`;
    }
  }

  updateWorkerHealth() {
    // Mock worker health - would be real data from /api/workers/health
    const activeWorkers = 5;
    const totalWorkers = 5;
    const avgLoad = Math.round(45 + Math.random() * 30); // CPU load percentage
    
    const activeWorkersEl = document.getElementById('active-workers');
    const workerLoadEl = document.getElementById('worker-load');
    
    if (activeWorkersEl) activeWorkersEl.textContent = `${activeWorkers}/${totalWorkers}`;
    if (workerLoadEl) workerLoadEl.textContent = `${avgLoad}%`;
    
    // Update health indicators
    const workerHealthEl = document.getElementById('worker-health');
    const loadStatusEl = document.getElementById('load-status');
    
    if (workerHealthEl) {
      const isHealthy = activeWorkers === totalWorkers;
      workerHealthEl.textContent = isHealthy ? '🟢' : '🔴';
      workerHealthEl.className = `worker-status ${isHealthy ? 'healthy' : 'warning'}`;
    }
    
    if (loadStatusEl) {
      const loadStatus = avgLoad < 70 ? 'healthy' : avgLoad < 85 ? 'warning' : 'danger';
      const loadIcon = loadStatus === 'healthy' ? '🟢' : 
                      loadStatus === 'warning' ? '🟡' : '🔴';
      loadStatusEl.textContent = loadIcon;
      loadStatusEl.className = `worker-status ${loadStatus}`;
    }
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
      this.showTemporaryNotification('Refreshing job data...', 'info');
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
    // Create temporary success notification
    this.showTemporaryNotification(message, 'success');
  }

  showActionError(message) {
    console.error(`❌ ${message}`);
    // Create temporary error notification
    this.showTemporaryNotification(message, 'error');
  }

  showTemporaryNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `action-notification action-notification--${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <span class="notification-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
        <span class="notification-message">${message}</span>
      </div>
    `;

    // Add to page header actions
    const headerActions = document.querySelector('.page-header__actions');
    if (headerActions) {
      headerActions.appendChild(notification);
    }

    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 3000);

    // Add CSS if not already added
    if (!document.getElementById('action-notifications-css')) {
      const style = document.createElement('style');
      style.id = 'action-notifications-css';
      style.textContent = `
        .action-notification {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 1000;
          padding: 0.75rem 1rem;
          border-radius: 6px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          animation: slideInRight 0.3s ease-out;
        }
        .action-notification--success {
          background: #d4edda;
          color: #155724;
          border: 1px solid #c3e6cb;
        }
        .action-notification--error {
          background: #f8d7da;
          color: #721c24;
          border: 1px solid #f5c6cb;
        }
        .action-notification--info {
          background: #d1ecf1;
          color: #0c5460;
          border: 1px solid #bee5eb;
        }
        .notification-content {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .notification-icon {
          font-size: 1rem;
        }
        .notification-message {
          font-size: 0.9rem;
          font-weight: 500;
        }
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        .action-btn--loading {
          opacity: 0.7;
          cursor: not-allowed;
        }
      `;
      document.head.appendChild(style);
    }
  }

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
}