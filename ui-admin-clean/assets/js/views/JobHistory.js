/**
 * Job History View Controller (REFACTORED)
 * Main coordinator for job history functionality
 * 
 * ARCHITECTURE: This file now acts as a coordinator that delegates to specialized modules:
 * - JobHistoryKPI: KPI system and metric cards
 * - JobHistoryActions: Queue management and job actions  
 * - JobHistoryUtils: Utility functions and helpers
 */

import { SmartFilter } from '../components/SmartFilter.js';
import { getFilterPresets, getFilterTypes } from '../config/filterPresets.js';
import { getCentralDataService } from '../services/central-data-service.js';
import { HelpService } from '../services/HelpService.js';
import { HelpPanel } from '../components/HelpPanel.js';
import { JobsQueueHelpProvider } from '../help-providers/JobsQueueHelpProvider.js';
import { ActionableMetricCard } from '../components/ActionableMetricCard.js';

// 🆕 REFACTORED: Import specialized modules
import { JobHistoryKPI } from '../modules/job-history/JobHistoryKPI.js';
import { JobHistoryActions } from '../modules/job-history/JobHistoryActions.js';
import { JobHistoryUtils } from '../modules/job-history/JobHistoryUtils.js';
import { JobHistoryRendering } from '../modules/job-history/JobHistoryRendering.js';
import { JobHistoryFilter } from '../modules/job-history/JobHistoryFilter.js';
import { JobHistoryData } from '../modules/job-history/JobHistoryData.js';

export class JobHistory {
  constructor(apiClient, container) {
    this.apiClient = apiClient;
    this.container = container;
    this.centralDataService = getCentralDataService(apiClient); // FIX: Use same service as Dashboard
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
    this.currentTab = 'all'; // Default tab matches SmartFilter defaultFilter
    
    // Subscription ID for CentralDataService
    this.subscriptionId = null;
    
    // 🆕 REFACTORED: Initialize specialized modules
    this.kpiManager = new JobHistoryKPI(this);
    this.actionsManager = new JobHistoryActions(this);
    this.utils = JobHistoryUtils; // Static utility class
    this.renderer = new JobHistoryRendering(this);
    this.filterManager = new JobHistoryFilter(this);
    this.dataManager = new JobHistoryData(this);
  }

  async init() {
    // Make globally accessible EARLY for onclick handlers
    window.jobHistory = this;
    console.log('🔧 Global jobHistory set:', window.jobHistory);
    
    this.renderer.render();
    this.setupHelpSystem();
    
    // 🆕 REFACTORED: Setup SmartFilter via filter manager
    this.filterManager.setupSmartFilter();
    this.filterManager.setupTimeframeFilter();
    this.filterManager.setupPaginationListeners();
    
    // 🆕 REFACTORED: Initialize KPI system via dedicated module AFTER SmartFilter setup
    this.kpiManager.setupDynamicKPIs();
    
    // Subscribe to CentralDataService for real-time updates (like other views)
    this.subscriptionId = this.centralDataService.subscribe('JobHistory', (data) => {
      console.log('🔔 JobHistory received data update:', data);
      this.updateFromCentralData(data);
    });
    
    // FIX: Ensure central data service is started like Dashboard does
    if (!this.centralDataService.getStatus().isRunning) {
      this.centralDataService.start();
    } else {
      // Service is already running - force fresh fetch
      console.log('📊 Service already running, forcing fresh fetch for Jobs view');
      await this.centralDataService.refresh();
    }
    
    await this.dataManager.loadJobHistory();
    this.setupEventListeners();
    
    // 🔥 FIX: Sync currentTab with SmartFilter state after initialization
    console.log('🔄 About to sync currentTab with filter. Current state:', {
      currentTab: this.currentTab,
      hasFilterManager: !!this.filterManager,
      hasSmartFilter: !!this.filterManager?.smartFilter
    });
    this.syncCurrentTabWithFilter();
    
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
          this.dataManager.processSSotData(ssotData);
          return;
        }
      }
      
      // Fallback: Direct SSOT API call
      console.log('🔄 Fallback: Direct SSOT API call');
      const response = await fetch('http://localhost:8001/api/admin/ssot');
      const ssotData = await response.json();
      this.dataManager.processSSotData(ssotData);
      
    } catch (error) {
      console.error('❌ Critical job history failure:', error);
      this.showError('Job history service temporarily unavailable. Showing cached data.');
      this.loadCachedHistoryData();
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


  mapFilterToTab(filter) {
    // Map SmartFilter selection to tab names
    if (!filter) return 'active'; // Default to active view
    
    // 🔥 FIX: Handle filter.preset (primary) and filter.view (fallback)
    const preset = filter.preset || filter.view;
    if (preset) {
      switch (preset) {
        case 'active': return 'active';
        case 'issues': return 'issues';
        case 'completed': return 'completed';
        case 'all': return 'all';
        default: return preset;
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
    return this.filterManager.getFilteredJobs();
  }

  /**
   * 🔥 NEW: Sync currentTab with SmartFilter state
   */
  syncCurrentTabWithFilter() {
    try {
      // Get current filter from SmartFilter
      const smartFilter = this.filterManager?.smartFilter;
      const currentFilter = smartFilter?.getCurrentFilter() || this.currentFilter;
      
      console.log('🔍 syncCurrentTabWithFilter debug:', {
        hasSmartFilter: !!smartFilter,
        currentFilter: currentFilter,
        currentTabBefore: this.currentTab
      });
      
      if (currentFilter) {
        // Map current filter to tab
        const mappedTab = this.mapFilterToTab(currentFilter);
        this.currentTab = mappedTab;
        
        console.log('🔄 Synced currentTab with filter:', {
          filterPreset: currentFilter.preset || currentFilter.view,
          mappedTab: mappedTab,
          currentTab: this.currentTab
        });
      } else {
        // 🔥 FIX: If no filter found but we expect 'all', force it
        console.log('🔄 No current filter found, forcing default to all tab');
        this.currentTab = 'all';
        
        // Try to force SmartFilter to select 'all' preset
        if (smartFilter && smartFilter.applyPreset) {
          console.log('🔧 Forcing SmartFilter to select all preset');
          smartFilter.applyPreset('all');
        }
      }
      
      // 🔥 FIX: Always force immediate KPI update with correct tab
      if (this.kpiManager) {
        console.log('🔄 Triggering immediate KPI update for synced tab:', this.currentTab);
        this.kpiManager.currentTab = this.currentTab;
        if (this.jobs && this.jobs.length > 0) {
          this.kpiManager.renderMetricsSection();
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to sync currentTab with filter:', error);
    }
  }

  // Handle filter changes from SmartFilter 
  handleFilterChange(filter) {
    console.log('🔍 Jobs filter changed:', filter);
    console.log('🔍 Filter change stack trace:', new Error().stack.split('\n').slice(1, 4));
    this.currentFilter = filter;
    this.currentPage = 1; // Reset to first page when filter changes
    
    // Update current tab for KPI switching (map filter to tab)
    this.currentTab = this.mapFilterToTab(filter);
    
    // 🔥 FIX: Update Pipeline Overview metrics for new filter with delay
    if (this.kpiManager && this.jobs && this.jobs.length > 0) {
      console.log('📊 Scheduling Pipeline Overview update for filter:', filter.preset);
      
      // Use delayed approach for consistency
      setTimeout(() => {
        console.log('⏰ Executing delayed Pipeline Overview update for filter change...');
        this.kpiManager.currentTab = this.currentTab;
        this.kpiManager.updatePipelineOverview(this.jobs);
        this.kpiManager.renderMetricsSection();
        console.log('✅ Delayed Pipeline Overview update for filter change completed');
      }, 100); // Short delay for filter changes
    }
    
    // Update the dynamic KPIs for the new tab
    this.setupDynamicKPIs();
    
    // Apply filter and re-render
    this.renderCurrentView();
    
    // Update results count
    const filteredJobs = this.getFilteredJobs();
    if (this.filterManager && this.filterManager.smartFilter) {
      this.filterManager.smartFilter.updateResultsCount?.(filteredJobs.length, (this.jobs || []).length);
    }
  }

  applyCurrentFilters() {
    // Apply timeframe filtering to complete dataset - COPIED FROM BACKUP
    this.jobs = this.filterJobsByTimeframe(this.allJobs);
    this.totalJobs = this.jobs.length;
    
    console.log(`📅 Filters applied: ${this.allJobs.length} → ${this.jobs.length} jobs (timeframe: ${this.currentTimeframe})`);
    
    // Update UI components
    this.updateOverviewMetrics();
    this.renderCurrentView();
    this.updatePagination();
    
    // Update smart filter results (guard against null)
    if (this.filterManager && this.filterManager.smartFilter) {
      this.filterManager.smartFilter.updateResultsCount?.(this.jobs.length, this.allJobs.length);
    }
  }

  filterJobsByTimeframe(jobs) {
    return this.dataManager.filterJobsByTimeframe(jobs);
  }

  updateOverviewMetrics() {
    // Update KPIs
    this.setupDynamicKPIs();
  }

  updatePagination() {
    // Reset to page 1 when filters change
    this.currentPage = 1;
  }

  // Enterprise pipeline enrichment - copied from backup  
  async enrichJobsWithPipelineData(jobs) {
    return Promise.all(jobs.map(async (job) => {
      try {
        // Load pipeline steps for each job
        const pipelineSteps = await this.loadJobPipelineSteps(job.id);
        
        return {
          ...job,
          // Enterprise pipeline enrichment
          pipeline_steps: pipelineSteps,
          pipeline_status: this.dataManager.calculatePipelineStatus(pipelineSteps),
          duration_breakdown: this.dataManager.calculateDurationBreakdown(pipelineSteps),
          performance_metrics: this.dataManager.calculatePerformanceMetrics(pipelineSteps),
          resource_utilization: this.dataManager.calculateResourceUtilization(pipelineSteps)
        };
      } catch (error) {
        console.warn(`Failed to enrich pipeline data for job ${job.id}:`, error);
        return {
          ...job,
          pipeline_steps: this.dataManager.getMockPipelineSteps(job),
          pipeline_status: 'unknown'
        };
      }
    }));
  }

  async loadJobPipelineSteps(jobId) {
    // All pipeline data comes from SSOT now - no separate API calls needed
    return this.dataManager.getMockPipelineSteps({ id: jobId });
  }

  // Delegate analytics calculation to data manager  
  calculateHistoryAnalytics() {
    if (this.dataManager.calculateHistoryAnalytics) {
      this.dataManager.calculateHistoryAnalytics();
    }
  }

  // Cache history data - copied from backup
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
    console.log('🎯 JobHistory.renderCurrentView() called');
    console.log('🎯 this.renderer exists:', !!this.renderer);
    this.renderer.renderCurrentView();
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

  // =============================================================================

  /**
   * Delegate KPI setup to specialized module
   */
  setupDynamicKPIs() {
    return this.kpiManager.setupDynamicKPIs();
  }

  /**
   * Delegate KPI updates to specialized module
   */
  updateKPIs() {
    return this.kpiManager.updateKPIs();
  }

  /**
   * Get metric cards from KPI manager
   */
  getMetricCards() {
    return this.kpiManager.getMetricCards();
  }

  // =============================================================================
  // ACTION DELEGATION METHODS
  // =============================================================================

  /**
   * Delegate manual refresh to actions module
   */
  async handleManualRefresh() {
    return this.actionsManager.handleManualRefresh();
  }

  /**
   * Delegate monitoring toggle to actions module
   */
  async handleToggleMonitoring() {
    return this.actionsManager.handleToggleMonitoring();
  }

  /**
   * Delegate job retry to actions module
   */
  async handleJobRetry(jobId) {
    return this.actionsManager.handleJobRetry(jobId);
  }

  /**
   * Delegate job cancellation to actions module
   */
  async handleJobCancel(jobId) {
    return this.actionsManager.handleJobCancel(jobId);
  }

  /**
   * Delegate job deletion to actions module
   */
  async handleJobDelete(jobId) {
    return this.actionsManager.handleJobDelete(jobId);
  }

  /**
   * Delegate bulk actions to actions module
   */
  async handleBulkJobAction(action, jobIds) {
    return this.actionsManager.handleBulkJobAction(action, jobIds);
  }

  /**
   * Delegate export to actions module
   */
  async handleExportJobs(jobs = null) {
    return this.actionsManager.handleExportJobs(jobs);
  }

  // =============================================================================
  // UTILITY DELEGATION METHODS
  // =============================================================================

  /**
   * Delegate date filtering to utils
   */
  filterJobsByDate(jobs, period) {
    return this.utils.filterJobsByDate(jobs, period);
  }

  /**
   * Delegate status filtering to utils
   */
  filterJobsByStatus(jobs, status) {
    return this.utils.filterJobsByStatus(jobs, status);
  }

  /**
   * Delegate duration formatting to utils
   */
  formatDuration(seconds) {
    return this.utils.formatDuration(seconds);
  }

  /**
   * Delegate file size formatting to utils
   */
  formatFileSize(bytes) {
    return this.utils.formatFileSize(bytes);
  }

  /**
   * Delegate relative time formatting to utils
   */
  formatRelativeTime(timestamp) {
    return this.utils.formatRelativeTime(timestamp);
  }

  /**
   * Delegate status display to utils
   */
  getStatusDisplay(status) {
    return this.utils.getStatusDisplay(status);
  }

  /**
   * Delegate progress display to utils
   */
  getProgressDisplay(progress, status) {
    return this.utils.getProgressDisplay(progress, status);
  }

  /**
   * Handle updates from CentralDataService (like other views do)
   */
  updateFromCentralData(centralData) {
    try {
      if (centralData.error) {
        console.warn('⚠️ JobHistory service layer error:', centralData.message);
        return;
      }

      console.log('🔄 JobHistory updating from CentralDataService...');
      console.log('📊 JobHistory current state before update:', {
        currentTab: this.currentTab,
        jobsCount: this.jobs?.length || 0,
        hasKpiManager: !!this.kpiManager
      });
      
      // Process SSOT data if available
      if (centralData) {
        this.dataManager.processSSotData(centralData);
        
        console.log('📊 JobHistory state after processSSotData:', {
          currentTab: this.currentTab,
          jobsCount: this.jobs?.length || 0,
          hasJobs: !!(this.jobs && this.jobs.length > 0)
        });
        
        // 🔥 FIX: Update KPI Manager with current jobs data - with delay like initial load
        if (this.kpiManager && this.jobs && this.jobs.length > 0) {
          console.log('📊 JobHistory scheduling delayed KPI Manager update with', this.jobs.length, 'jobs for tab:', this.currentTab);
          
          // Use same delayed approach as initial load
          setTimeout(() => {
            console.log('⏰ JobHistory executing delayed KPI Manager update from central data...');
            // Set current tab for KPI calculations
            this.currentTab = this.currentTab || 'all';
            this.kpiManager.currentTab = this.currentTab;
            console.log('🎯 JobHistory KPI update - currentTab set to:', this.currentTab);
            this.kpiManager.updateKPIs(this.jobs);
            // Force render Pipeline Overview metrics
            this.kpiManager.renderMetricsSection();
            console.log('✅ JobHistory delayed KPI Manager update from central data completed for tab:', this.currentTab);
          }, 300); // Shorter delay for real-time updates
        } else {
          console.warn('⚠️ JobHistory KPI update skipped:', {
            hasKpiManager: !!this.kpiManager,
            hasJobs: !!(this.jobs && this.jobs.length > 0),
            jobsLength: this.jobs?.length || 0
          });
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to update JobHistory from central data:', error);
    }
  }

  /**
   * Handle job actions (retry, cancel, etc)
   */
  async handleJobAction(action, jobId) {
    if (action === 'retry') {
      return this.handleJobRetry(jobId);
    } else if (action === 'cancel') {
      return this.handleJobCancel(jobId);
    } else {
      console.warn(`Unknown job action: ${action}`);
    }
  }

  /**
   * Show job details modal
   */
  async showJobDetails(jobId) {
    try {
      console.log(`👁️ Loading job details for ${jobId}...`);
      const jobDetails = await this.apiClient.getJobDetails(jobId);
      this.openJobDetailsModal(jobDetails);
    } catch (error) {
      console.error(`❌ Failed to load job details for ${jobId}:`, error);
      this.showError('Failed to load job details.');
    }
  }

  /**
   * Open job details modal
   */
  openJobDetailsModal(job) {
    // TODO: Implement proper modal component for job details
    // For now, show detailed alert like working backup
    const details = `Job Details:

ID: ${job.id}
Status: ${job.status}
Type: ${job.type || 'N/A'}
Created: ${job.created_at}
Updated: ${job.updated_at}
Progress: ${job.progress || 0}%
User: ${job.user_id}

Full details logged to console.`;
    
    console.log('📋 Job Details:', job);
    alert(details);
  }

  /**
   * Show error notification
   */
  showError(message) {
    console.error(message);
    // TODO: Implement proper error notification
  }

  /**
   * Cleanup method for JobHistory view
   */
  destroy() {
    // Unsubscribe from central data service
    if (this.subscriptionId) {
      this.centralDataService.unsubscribe(this.subscriptionId);
    }
    
    // Clear timers
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
    
    // Clean up modules
    if (this.filterManager) {
      this.filterManager.destroy();
    }
    
    // Clear global reference
    if (window.jobHistory === this) {
      delete window.jobHistory;
    }
    
    console.log('🧹 JobHistory View destroyed');
  }

}