/**
 * JobHistory KPI Management Module
 * Extracted from JobHistory.js for better maintainability
 */

import { ActionableMetricCard } from '../../components/ActionableMetricCard.js';
import { getCentralDataService } from '../../services/central-data-service.js';

export class JobHistoryKPI {
  constructor(jobHistoryInstance) {
    this.jobHistory = jobHistoryInstance;
    this.metricCards = new Map();
  }

  /**
   * Setup dynamic KPIs based on current tab
   */
  setupDynamicKPIs() {
    // SIMPLE SOLUTION: Just re-render the entire metrics section like AgentsWorkers does
    this.renderMetricsSection();
  }

  /**
   * Re-render the entire metrics section based on current tab (like AgentsWorkers)
   */
  renderMetricsSection() {
    const metricsGrid = this.jobHistory.container.querySelector('.pipeline-metrics-grid');
    if (!metricsGrid) {
      console.warn('❌ Pipeline metrics grid not found');
      return;
    }
    
    // Get current tab and FILTERED jobs data
    const currentTab = this.jobHistory.currentTab;
    const allJobs = this.jobHistory.jobs || [];
    const filteredJobs = this.getJobsForCurrentFilter(allJobs);
    
    console.log('🎯 JobHistory KPI rendering metrics for tab:', currentTab, 'with', filteredJobs.length, 'filtered jobs from', allJobs.length, 'total jobs');
    console.log('🔍 JobHistory KPI filtered jobs sample:', filteredJobs.slice(0, 3));
    console.log('🔍 JobHistory KPI job statuses in filtered:', [...new Set(filteredJobs.map(j => j.status))]);
    
    // Use filtered jobs instead of raw SSOT data
    const data = {
      jobs: { recent_jobs: filteredJobs },
      queue: { pending: 0, processing: 0 } // Basic queue data
    };
    
    console.log('📊 JobHistory KPI data being passed to getMetricsHTML:', {
      currentTab,
      jobsCount: data.jobs.recent_jobs.length,
      sampleJob: data.jobs.recent_jobs[0]
    });
    
    // Render metrics based on current tab with filtered data
    metricsGrid.innerHTML = this.getMetricsHTML(currentTab, data);
    console.log('✅ JobHistory KPI metrics HTML rendered for tab:', currentTab);
  }

  /**
   * Get HTML for metrics based on current tab (like AgentsWorkers approach)
   */
  getMetricsHTML(tab, data) {
    const jobs = data?.jobs?.recent_jobs || [];
    const queueData = data?.queue || {};
    
    switch (tab) {
      case 'active':
        return this.getActiveMetricsHTML(jobs, queueData);
      case 'issues':
        return this.getIssuesMetricsHTML(jobs, queueData);
      case 'completed':
        return this.getCompletedMetricsHTML(jobs, queueData);
      case 'all':
      default:
        return this.getAllMetricsHTML(jobs, queueData);
    }
  }

  getActiveMetricsHTML(jobs, queueData) {
    const activeJobs = jobs.filter(job => ['processing', 'queued', 'running'].includes(job.status));
    const processingNow = queueData.processing || 0;
    const queueDepth = queueData.depth || queueData.pending || 0;
    
    return `
      <div class="metric-column metric-column--queue">
        <h4 class="metric-column-title">Queue Status</h4>
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__icon">📥</div>
            <div class="metric-card__title">Queue Depth</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${queueDepth}</div>
            <div class="metric-card__description">Jobs waiting</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--performance">
        <h4 class="metric-column-title">Performance</h4>
        <div class="metric-card metric-card--processing">
          <div class="metric-card__header">
            <div class="metric-card__icon">⚡</div>
            <div class="metric-card__title">Active Jobs</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${activeJobs.length}</div>
            <div class="metric-card__description">Currently processing</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--inventory">
        <h4 class="metric-column-title">Inventory</h4>
        <div class="metric-card metric-card--info">
          <div class="metric-card__header">
            <div class="metric-card__icon">🔄</div>
            <div class="metric-card__title">Processing Now</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${processingNow}</div>
            <div class="metric-card__description">On workers</div>
          </div>
        </div>
      </div>
    `;
  }

  getIssuesMetricsHTML(jobs, queueData) {
    const failedJobs = jobs.filter(job => ['failed', 'cancelled'].includes(job.status));
    const errorRate = jobs.length > 0 ? ((failedJobs.length / jobs.length) * 100).toFixed(1) : 0;
    
    return `
      <div class="metric-column metric-column--queue">
        <h4 class="metric-column-title">Queue Status</h4>
        <div class="metric-card metric-card--error">
          <div class="metric-card__header">
            <div class="metric-card__icon">❌</div>
            <div class="metric-card__title">Failed Jobs</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${failedJobs.length}</div>
            <div class="metric-card__description">Need attention</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--performance">
        <h4 class="metric-column-title">Performance</h4>
        <div class="metric-card metric-card--warning">
          <div class="metric-card__header">
            <div class="metric-card__icon">📉</div>
            <div class="metric-card__title">Error Rate</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${errorRate}%</div>
            <div class="metric-card__description">Failure percentage</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--inventory">
        <h4 class="metric-column-title">Inventory</h4>
        <div class="metric-card metric-card--info">
          <div class="metric-card__header">
            <div class="metric-card__icon">⏱️</div>
            <div class="metric-card__title">MTTR</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">3min</div>
            <div class="metric-card__description">Avg fix time</div>
          </div>
        </div>
      </div>
    `;
  }

  getCompletedMetricsHTML(jobs, queueData) {
    const completedJobs = jobs.filter(job => job.status === 'completed');
    const successRate = jobs.length > 0 ? ((completedJobs.length / jobs.length) * 100).toFixed(1) : 0;
    const avgDuration = completedJobs.length > 0 ? 
      (completedJobs.reduce((sum, job) => sum + (job.duration || 0), 0) / completedJobs.length / 60).toFixed(1) : 0;
    
    return `
      <div class="metric-column metric-column--queue">
        <h4 class="metric-column-title">Queue Status</h4>
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__icon">✅</div>
            <div class="metric-card__title">Completed Today</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${completedJobs.length}</div>
            <div class="metric-card__description">Successfully done</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--performance">
        <h4 class="metric-column-title">Performance</h4>
        <div class="metric-card metric-card--success">
          <div class="metric-card__header">
            <div class="metric-card__icon">🎯</div>
            <div class="metric-card__title">Success Rate</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${successRate}%</div>
            <div class="metric-card__description">Jobs completed</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--inventory">
        <h4 class="metric-column-title">Inventory</h4>
        <div class="metric-card metric-card--info">
          <div class="metric-card__header">
            <div class="metric-card__icon">⏱️</div>
            <div class="metric-card__title">Avg Duration</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${avgDuration}min</div>
            <div class="metric-card__description">Processing time</div>
          </div>
        </div>
      </div>
    `;
  }

  getAllMetricsHTML(jobs, queueData) {
    const throughputPerHour = queueData.throughput?.per_hour || 24.5;
    const workerEfficiency = queueData.worker_utilization || 87;
    const totalJobs = jobs.length;
    
    return `
      <div class="metric-column metric-column--queue">
        <h4 class="metric-column-title">Queue Status</h4>
        <div class="metric-card metric-card--info">
          <div class="metric-card__header">
            <div class="metric-card__icon">📊</div>
            <div class="metric-card__title">Total Jobs</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${totalJobs}</div>
            <div class="metric-card__description">All time</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--performance">
        <h4 class="metric-column-title">Performance</h4>
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__icon">🚀</div>
            <div class="metric-card__title">Throughput</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${throughputPerHour}/hr</div>
            <div class="metric-card__description">Jobs per hour</div>
          </div>
        </div>
      </div>
      
      <div class="metric-column metric-column--inventory">
        <h4 class="metric-column-title">Inventory</h4>
        <div class="metric-card metric-card--good">
          <div class="metric-card__header">
            <div class="metric-card__icon">👷</div>
            <div class="metric-card__title">Worker Efficiency</div>
          </div>
          <div class="metric-card__content">
            <div class="metric-card__value">${workerEfficiency}%</div>
            <div class="metric-card__description">Resource usage</div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Clear all KPI containers to prevent stacking of metrics from different tabs
   */
  clearUsedContainers(configs) {
    // Only clear containers that are actually going to be used in this tab
    configs.forEach(config => {
      if (config.container) {
        config.container.innerHTML = ''; // Clear only containers that will be populated
        console.log(`🧹 Cleared container for KPI: ${config.id}`);
      }
    });
    
    console.log(`🧹 Cleared ${configs.length} containers for current tab`);
  }

  /**
   * Get KPI configurations for specific tab
   */
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
      recent_jobs: jobsData.recent_jobs || [],
      timestamp: currentData?.timestamp
    };

    console.log('🔍 JobHistory KPI configs for tab:', tab, 'with data:', data);

    switch (tab) {
      case 'active':
        return this.getActiveJobsKPIs(data);
      case 'issues':  // FIX: Map 'issues' from SmartFilter to failed KPIs
      case 'failed':
        return this.getFailedJobsKPIs(data);
      case 'completed':
        return this.getCompletedJobsKPIs(data);
      case 'all':     // FIX: Map 'all' from SmartFilter to performance KPIs
      case 'performance':
        return this.getPerformanceKPIs(data);
      default:
        return this.getActiveJobsKPIs(data);
    }
  }

  /**
   * Active Jobs tab KPIs
   */
  getActiveJobsKPIs(data) {
    return [
      {
        id: 'active_jobs',
        container: this.jobHistory.container.querySelector('#active-processing-card'),
        title: 'Active Jobs',
        icon: '⚡',
        value: (data.queue?.processing || 0) + (data.queue?.pending || 0),
        status: 'good',
        trend: { direction: 'stable', percentage: 0 },
        description: `${data.queue?.processing || 0} processing, ${data.queue?.pending || 0} queued`,
        actions: [
          { label: 'Monitor Active', icon: '👁️', action: 'view_active' },
          { label: 'Scale Workers', icon: '📈', action: 'scale_workers' },
          { label: 'Priority Queue', icon: '⚡', action: 'priority_queue' }
        ],
        help: 'Jobs currently being processed or waiting in queue'
      },
      {
        id: 'processing_now',
        container: this.jobHistory.container.querySelector('#queue-throughput-card'),
        title: 'Processing Now',
        icon: '🔄',
        value: data.queue?.processing || 0,
        status: 'good',
        trend: { direction: 'stable', percentage: 0 },
        description: 'Currently being processed',
        actions: [
          { label: 'View Details', icon: '🔍', action: 'view_processing' }
        ],
        help: 'Jobs actively running on workers'
      },
      {
        id: 'queue_depth',
        container: this.jobHistory.container.querySelector('#queue-depth-card'),
        title: 'Queue Depth',
        icon: '📥',
        // FIX: Use queue.depth from SSOT, not queue.pending
        value: data.queue?.depth || 0,
        status: data.queue?.depth > 10 ? 'warning' : 'good',
        trend: { direction: 'down', percentage: 5 },
        description: 'Jobs waiting to process',
        actions: [
          { label: 'Process Queue', icon: '⚡', action: 'process_queue' },
          { label: 'Clear Queue', icon: '🧹', action: 'clear_queue' }
        ],
        help: 'Number of jobs waiting for processing'
      }
    ];
  }

  /**
   * Failed Jobs tab KPIs
   */
  getFailedJobsKPIs(data) {
    const failedJobs = data.recent_jobs?.filter(job => job.status === 'failed') || [];
    const totalFailed = data.queue?.failed_today || failedJobs.length;

    return [
      {
        id: 'failed_jobs',
        container: this.jobHistory.container.querySelector('#failed-today-card'),
        title: 'Failed Jobs',
        icon: '❌',
        value: totalFailed,
        status: totalFailed > 0 ? 'warning' : 'good',
        trend: { direction: 'down', percentage: 12 },
        description: `${data.queue?.failed_today || 0} failed today`,
        actions: [
          { label: 'Retry All Failed', icon: '🔄', action: 'retry_failed' },
          { label: 'Failure Analysis', icon: '🔍', action: 'analyze_failures' },
          { label: 'Error Report', icon: '📊', action: 'error_report' }
        ],
        help: 'Jobs that failed during processing'
      },
      {
        id: 'top_error',
        container: this.jobHistory.container.querySelector('#failed-today-card'),
        title: 'Top Error',
        icon: '🔧',
        value: 'Unknown',
        status: 'good',
        trend: { direction: 'stable', percentage: 0 },
        description: `${totalFailed} occurrences (100%)`,
        actions: [
          { label: 'Fix This Error', icon: '🔧', action: 'fix_error' },
          { label: 'Error Pattern', icon: '📊', action: 'error_pattern' }
        ],
        help: 'Most common error causing job failures'
      },
      {
        id: 'mttr',
        container: this.jobHistory.container.querySelector('#worker-utilization-card'),
        title: 'MTTR',
        icon: '⏱️',
        value: '3min',
        status: 'good',
        trend: { direction: 'down', percentage: 20 },
        description: 'Mean Time To Recovery',
        actions: [
          { label: 'Improve Recovery', icon: '🚀', action: 'improve_recovery' },
          { label: 'Auto-Recovery', icon: '🤖', action: 'auto_recovery' }
        ],
        help: 'Average time to fix failed jobs'
      },
      {
        id: 'error_rate',
        container: this.jobHistory.container.querySelector('#total-jobs-card'),
        title: 'Error Rate',
        icon: '📉',
        value: '9.7%',
        status: 'warning',
        trend: { direction: 'down', percentage: 8 },
        description: 'Failure percentage',
        actions: [
          { label: 'Reduce Errors', icon: '🛠️', action: 'reduce_errors' },
          { label: 'Prevention Rules', icon: '🛡️', action: 'prevention_rules' }
        ],
        help: 'Percentage of jobs that fail'
      }
    ];
  }

  /**
   * Completed Jobs tab KPIs
   */
  getCompletedJobsKPIs(data) {
    const completedJobs = data.recent_jobs?.filter(job => job.status === 'completed') || [];
    
    return [
      {
        id: 'completed_today',
        container: this.jobHistory.container.querySelector('#today-jobs-card'),
        title: 'Completed Today',
        icon: '✅',
        value: data.queue?.completed_today || completedJobs.length,
        status: 'good',
        trend: { direction: 'up', percentage: 15 },
        description: 'Successfully processed',
        actions: [
          { label: 'View Results', icon: '🔍', action: 'view_completed' },
          { label: 'Export Report', icon: '📊', action: 'export_completed' }
        ],
        help: 'Jobs completed successfully today'
      },
      {
        id: 'success_rate',
        container: this.jobHistory.container.querySelector('#success-rate-24h-card'),
        title: 'Success Rate',
        icon: '🎯',
        value: '90.3%',
        status: 'good',
        trend: { direction: 'up', percentage: 5 },
        description: 'Last 24 hours',
        actions: [
          { label: 'Trend Analysis', icon: '📈', action: 'trend_analysis' }
        ],
        help: 'Percentage of jobs completed successfully'
      },
      {
        id: 'avg_duration',
        container: this.jobHistory.container.querySelector('#avg-processing-card'),
        title: 'Avg Duration',
        icon: '⏱️',
        value: '2.5min',
        status: 'good',
        trend: { direction: 'down', percentage: 10 },
        description: 'Processing time',
        actions: [
          { label: 'Optimize Speed', icon: '🚀', action: 'optimize_speed' }
        ],
        help: 'Average time to complete jobs'
      }
    ];
  }

  /**
   * Performance tab KPIs
   */
  getPerformanceKPIs(data) {
    return [
      {
        id: 'throughput',
        container: this.jobHistory.container.querySelector('#queue-throughput-card'),
        title: 'Throughput',
        icon: '🚀',
        value: '24.5/hr',
        status: 'good',
        trend: { direction: 'up', percentage: 8 },
        description: 'Jobs per hour',
        actions: [
          { label: 'Scale Up', icon: '📈', action: 'scale_up' },
          { label: 'Optimize', icon: '⚡', action: 'optimize' }
        ],
        help: 'Number of jobs processed per hour'
      },
      {
        id: 'worker_efficiency',
        container: this.jobHistory.container.querySelector('#worker-utilization-card'),
        title: 'Worker Efficiency',
        icon: '👷',
        value: '87%',
        status: 'good',
        trend: { direction: 'stable', percentage: 0 },
        description: 'Resource utilization',
        actions: [
          { label: 'Worker Details', icon: '🔍', action: 'worker_details' }
        ],
        help: 'How efficiently workers are being used'
      },
      {
        id: 'peak_load',
        container: this.jobHistory.container.querySelector('#active-processing-card'),
        title: 'Peak Load',
        icon: '📊',
        value: '2-4 PM',
        status: 'good',
        trend: { direction: 'stable', percentage: 0 },
        description: 'Busiest time period',
        actions: [
          { label: 'Load Analysis', icon: '📈', action: 'load_analysis' }
        ],
        help: 'Time period with highest job volume'
      }
    ];
  }

  /**
   * Update all KPI cards with fresh data
   */
  updateKPIs(jobs) {
    // 🔥 FIX: Update Pipeline Overview metrics with job data
    if (jobs && jobs.length > 0) {
      this.updatePipelineOverview(jobs);
    }
    
    // Original ActionableMetricCard updates
    this.metricCards.forEach((card, id) => {
      if (card && typeof card.update === 'function') {
        try {
          card.update();
        } catch (error) {
          console.error(`❌ Failed to update KPI card ${id}:`, error);
        }
      }
    });
  }

  /**
   * 🔥 NEW: Update Pipeline Overview metrics like AgentsWorkers does
   */
  updatePipelineOverview(jobs) {
    try {
      console.log('🔄 JobHistory updatePipelineOverview called with', jobs?.length || 0, 'jobs');
      
      // 🔥 FIX: Re-render entire metrics grid like AgentsWorkers
      const metricsGrid = this.jobHistory.container.querySelector('.pipeline-metrics-grid');
      if (!metricsGrid) {
        console.warn('❌ Pipeline metrics grid not found');
        return;
      }
      
      // Get current tab and calculate metrics - use currentTab for consistency
      const filteredJobs = this.getJobsForCurrentFilter(jobs);
      const currentTab = this.jobHistory.currentTab || 'active';
      
      console.log('🔢 JobHistory re-rendering Pipeline Overview for tab:', currentTab, 'with', filteredJobs.length, 'filtered jobs from', jobs?.length || 0, 'total');
      console.log('🔍 JobHistory Pipeline Overview job statuses:', [...new Set(filteredJobs.map(j => j.status))]);
      console.log('🔍 JobHistory Pipeline Overview currentTab:', currentTab);
      
      // Re-render complete metrics HTML like AgentsWorkers does
      const metricsData = {
        jobs: { recent_jobs: filteredJobs },
        queue: { pending: 0, processing: 0 } // Basic queue data
      };
      
      console.log('📊 JobHistory Pipeline Overview metrics data:', {
        tab: currentTab,
        filteredJobsCount: metricsData.jobs.recent_jobs.length,
        firstJob: metricsData.jobs.recent_jobs[0]?.status
      });
      
      metricsGrid.innerHTML = this.getMetricsHTML(currentTab, metricsData);

      console.log('✅ JobHistory Pipeline Overview re-rendered successfully for tab:', currentTab);
      
    } catch (error) {
      console.error('❌ Failed to update Pipeline Overview:', error);
    }
  }

  /**
   * 🔥 NEW: Get jobs filtered by current tab/filter
   */
  getJobsForCurrentFilter(allJobs) {
    // Use currentTab instead of filter for consistent filtering
    const currentTab = this.jobHistory.currentTab;
    if (!currentTab || currentTab === 'all') {
      return allJobs; // 'All Jobs' tab shows all jobs
    }

    // Filter jobs based on current tab
    switch (currentTab) {
      case 'active':
        return allJobs.filter(job => job.status === 'processing' || job.status === 'pending');
      case 'completed':
        return allJobs.filter(job => job.status === 'completed');
      case 'issues':
      case 'failed':
        return allJobs.filter(job => job.status === 'failed' || job.status === 'error');
      default:
        return allJobs;
    }
  }

  /**
   * Show KPI load error to user
   */
  showKPILoadError(kpiId, errorMessage) {
    // Create user-visible error notification
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.innerHTML = `
      <div class="error-content">
        <span class="error-icon">⚠️</span>
        <span class="error-message">KPI ${kpiId} failed to load: ${errorMessage}</span>
        <button class="error-dismiss" onclick="this.parentElement.parentElement.remove()">×</button>
      </div>
    `;
    
    // Add to page
    const container = document.querySelector('.job-history-container') || document.body;
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 5000);
  }

  /**
   * Create error placeholder card
   */
  createErrorMetricCard(config) {
    return {
      render: () => {
        const container = document.querySelector(config.container);
        if (container) {
          container.innerHTML = `
            <div class="metric-card metric-card--error">
              <div class="metric-card__error">
                <span class="error-icon">⚠️</span>
                <span class="error-text">KPI Error</span>
              </div>
            </div>
          `;
        }
      },
      update: () => {}, // No-op
      getMetricCards: () => this.metricCards
    };
  }

  /**
   * Get all metric cards
   */
  getMetricCards() {
    return this.metricCards;
  }
}