/**
 * JobHistory Filter Module
 * Handles filtering, pagination, and search logic
 * Extracted from JobHistory.js for better maintainability
 */

import { SmartFilter } from '../../components/SmartFilter.js';
import { getFilterPresets, getFilterTypes } from '../../config/filterPresets.js';

export class JobHistoryFilter {
  constructor(jobHistoryInstance) {
    this.jobHistory = jobHistoryInstance;
    this.smartFilter = null;
    this.currentFilter = {};
  }

  /**
   * Setup smart filter component - copied from backup
   */
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
        defaultFilter: 'all',
        onFilterChange: (filter) => this.jobHistory.handleFilterChange(filter)
      });

      this.smartFilter.init(container);
      console.log('✅ SmartFilter initialized successfully for Jobs view');
      console.log('🔍 SmartFilter default filter after init:', this.smartFilter.getCurrentFilter());
      console.log('🔍 SmartFilter currentTab should be:', this.jobHistory.currentTab);
    } catch (error) {
      console.error('❌ Failed to setup SmartFilter:', error);
    }
  }

  /**
   * Setup timeframe filter dropdown
   */
  setupTimeframeFilter() {
    const timeframeSelect = document.getElementById('timeframe-select');
    if (!timeframeSelect) {
      console.warn('Timeframe select not found');
      return;
    }

    timeframeSelect.addEventListener('change', (e) => {
      const newTimeframe = e.target.value;
      if (newTimeframe !== this.jobHistory.currentTimeframe) {
        console.log(`🕒 Timeframe changed: ${this.jobHistory.currentTimeframe} → ${newTimeframe}`);
        
        this.jobHistory.currentTimeframe = newTimeframe;
        
        // Apply new timeframe filter
        this.applyCurrentFilters();
        
        // Show notification
        this.showTimeframeChangedNotification(this.jobHistory.currentTimeframe);
      }
    });
  }

  /**
   * Show timeframe changed notification
   */
  showTimeframeChangedNotification(timeframe) {
    const timeframeMap = {
      'hour': 'Last Hour',
      'today': 'Today', 
      'week': 'This Week',
      'month': 'This Month',
      'all': 'All Time'
    };

    const notification = document.createElement('div');
    notification.className = 'timeframe-notification';
    notification.innerHTML = `
      <div class="notification-content">
        <span class="notification-icon">🕒</span>
        <span class="notification-message">Showing jobs from: ${timeframeMap[timeframe] || timeframe}</span>
        <button class="notification-dismiss" onclick="this.parentElement.parentElement.remove()">×</button>
      </div>
    `;

    // Add to page
    const container = document.querySelector('.job-history-container') || document.body;
    container.appendChild(notification);

    // Auto-remove after delay
    setTimeout(() => {
      if (document.body.contains(notification)) {
        notification.remove();
      }
    }, 3000);
  }

  /**
   * Setup pagination event listeners
   */
  setupPaginationListeners() {
    document.addEventListener('click', (e) => {
      // Handle pagination button clicks
      if (e.target.classList.contains('pagination-btn') && e.target.dataset.page) {
        const page = parseInt(e.target.dataset.page);
        if (page && page !== this.jobHistory.currentPage) {
          this.jobHistory.currentPage = page;
          this.jobHistory.renderCurrentView(); // Re-render with new page
        }
      }

      // Handle "Go to page" button
      if (e.target.classList.contains('pagination-btn--go')) {
        const input = e.target.parentElement.querySelector('.page-input');
        const page = parseInt(input.value);
        const totalPages = Math.ceil(this.getFilteredJobs().length / this.jobHistory.itemsPerPage);
        
        if (page && page >= 1 && page <= totalPages && page !== this.jobHistory.currentPage) {
          this.jobHistory.currentPage = page;
          this.jobHistory.renderCurrentView();
        }
      }
    });

    // Handle Enter key in page input
    document.addEventListener('keydown', (e) => {
      if (e.target.classList.contains('page-input') && e.key === 'Enter') {
        const page = parseInt(e.target.value);
        const totalPages = Math.ceil(this.getFilteredJobs().length / this.jobHistory.itemsPerPage);
        
        if (page && page >= 1 && page <= totalPages && page !== this.jobHistory.currentPage) {
          this.jobHistory.currentPage = page;
          this.jobHistory.renderCurrentView();
        }
      }
    });
  }

  /**
   * Handle filter changes from SmartFilter
   */
  async handleFilterChange(filter) {
    console.log('🔍 Filter changed:', filter);
    
    this.currentFilter = filter;
    
    // Reset to first page when filter changes
    this.jobHistory.currentPage = 1;
    
    // Update KPIs based on new filter context
    this.jobHistory.setupDynamicKPIs();
    
    // Re-render with new filter
    console.log('🔄 About to call renderCurrentView from filter');
    this.jobHistory.renderCurrentView();
    
    // Update job stats based on filtered results
    const filteredJobs = this.getFilteredJobs();
    console.log(`📊 Filter applied - showing ${filteredJobs.length} of ${this.jobHistory.jobs?.length || 0} jobs`);
    console.log('🔍 Current filter:', this.currentFilter);
    console.log('🔍 All jobs:', this.jobHistory.jobs?.length || 0);
    console.log('🔍 Sample job:', this.jobHistory.jobs?.[0]);
  }

  /**
   * Get filtered jobs based on current filters - copied from backup
   */
  getFilteredJobs() {
    // Return all jobs if no filter is set
    if (!this.jobHistory.currentFilter || this.jobHistory.currentFilter.status === 'all') {
      return this.jobHistory.jobs || [];
    }
    
    return (this.jobHistory.jobs || []).filter(job => {
      const filter = this.jobHistory.currentFilter;
      
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

  /**
   * Filter jobs by timeframe
   */
  filterJobsByTimeframe(jobs) {
    if (this.jobHistory.currentTimeframe === 'all') {
      return jobs;
    }

    const now = new Date();
    let cutoffDate;

    switch (this.jobHistory.currentTimeframe) {
      case 'hour':
        cutoffDate = new Date(now.getTime() - (60 * 60 * 1000));
        break;
      case 'today':
        cutoffDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case 'week':
        cutoffDate = new Date(now.getTime() - (7 * 24 * 60 * 60 * 1000));
        break;
      case 'month':
        cutoffDate = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
      default:
        return jobs;
    }

    return jobs.filter(job => {
      const jobDate = new Date(job.created_at || job.timestamp);
      return jobDate >= cutoffDate;
    });
  }

  /**
   * Apply SmartFilter filters to jobs
   */
  applySmartFilters(jobs, filters) {
    let filtered = [...jobs];

    // Text search filter
    if (filters.search && filters.search.trim()) {
      const searchTerm = filters.search.toLowerCase().trim();
      filtered = filtered.filter(job => {
        return (
          (job.id && job.id.toLowerCase().includes(searchTerm)) ||
          (job.user_id && job.user_id.toLowerCase().includes(searchTerm)) ||
          (job.status && job.status.toLowerCase().includes(searchTerm)) ||
          (job.video_title && job.video_title.toLowerCase().includes(searchTerm)) ||
          (job.current_step && job.current_step.toLowerCase().includes(searchTerm)) ||
          (job.error_message && job.error_message.toLowerCase().includes(searchTerm))
        );
      });
    }

    // Status filter
    if (filters.status && filters.status.length > 0) {
      filtered = filtered.filter(job => 
        filters.status.includes(job.status)
      );
    }

    // Priority filter
    if (filters.priority && filters.priority.length > 0) {
      filtered = filtered.filter(job => 
        filters.priority.includes(job.priority || 'medium')
      );
    }

    // User filter
    if (filters.user_id && filters.user_id.length > 0) {
      filtered = filtered.filter(job => 
        filters.user_id.includes(job.user_id)
      );
    }

    // Duration filter
    if (filters.duration) {
      filtered = filtered.filter(job => {
        const duration = job.performance_metrics?.total_duration || job.duration || 0;
        
        if (filters.duration.min !== undefined && duration < filters.duration.min) {
          return false;
        }
        
        if (filters.duration.max !== undefined && duration > filters.duration.max) {
          return false;
        }
        
        return true;
      });
    }

    // Progress filter
    if (filters.progress) {
      filtered = filtered.filter(job => {
        const progress = job.progress || 0;
        
        if (filters.progress.min !== undefined && progress < filters.progress.min) {
          return false;
        }
        
        if (filters.progress.max !== undefined && progress > filters.progress.max) {
          return false;
        }
        
        return true;
      });
    }

    // Date range filter
    if (filters.date_range) {
      filtered = filtered.filter(job => {
        const jobDate = new Date(job.created_at || job.timestamp);
        
        if (filters.date_range.start) {
          const startDate = new Date(filters.date_range.start);
          if (jobDate < startDate) return false;
        }
        
        if (filters.date_range.end) {
          const endDate = new Date(filters.date_range.end);
          if (jobDate > endDate) return false;
        }
        
        return true;
      });
    }

    // Worker ID filter
    if (filters.worker_id && filters.worker_id.length > 0) {
      filtered = filtered.filter(job => 
        filters.worker_id.includes(job.worker_id)
      );
    }

    // Retry count filter
    if (filters.retry_count !== undefined) {
      filtered = filtered.filter(job => 
        (job.retry_count || 0) >= filters.retry_count
      );
    }

    // Has error filter
    if (filters.has_error === true) {
      filtered = filtered.filter(job => 
        job.error_message && job.error_message.trim().length > 0
      );
    } else if (filters.has_error === false) {
      filtered = filtered.filter(job => 
        !job.error_message || job.error_message.trim().length === 0
      );
    }

    return filtered;
  }

  /**
   * Apply current filters and refresh view
   */
  applyCurrentFilters() {
    console.log('🔄 applyCurrentFilters called from JobHistoryFilter');
    // Call the main JobHistory applyCurrentFilters which handles timeframe filtering
    this.jobHistory.applyCurrentFilters();
  }

  /**
   * Clear all filters
   */
  clearAllFilters() {
    this.currentFilter = {};
    this.jobHistory.currentTimeframe = 'today';
    this.jobHistory.currentPage = 1;
    
    // Reset SmartFilter
    if (this.smartFilter) {
      this.smartFilter.clearFilters();
    }
    
    // Reset timeframe dropdown
    const timeframeSelect = document.getElementById('timeframe-select');
    if (timeframeSelect) {
      timeframeSelect.value = 'today';
    }
    
    // Re-render
    this.jobHistory.renderCurrentView();
  }

  /**
   * Apply preset filter
   */
  applyPresetFilter(presetId) {
    if (this.smartFilter) {
      this.smartFilter.applyPreset(presetId);
    }
  }

  /**
   * Get current filter state
   */
  getCurrentFilter() {
    return {
      ...this.currentFilter,
      timeframe: this.jobHistory.currentTimeframe,
      page: this.jobHistory.currentPage
    };
  }

  /**
   * Set filter from external source
   */
  setFilter(filter) {
    this.currentFilter = filter.filters || {};
    this.jobHistory.currentTimeframe = filter.timeframe || 'today';
    this.jobHistory.currentPage = filter.page || 1;
    
    // Update UI components
    if (this.smartFilter) {
      this.smartFilter.setFilter(this.currentFilter);
    }
    
    const timeframeSelect = document.getElementById('timeframe-select');
    if (timeframeSelect) {
      timeframeSelect.value = this.jobHistory.currentTimeframe;
    }
    
    // Re-render
    this.jobHistory.renderCurrentView();
  }

  /**
   * Get filter statistics
   */
  getFilterStats() {
    const allJobs = this.jobHistory.jobs || [];
    const filteredJobs = this.getFilteredJobs();
    
    return {
      total: allJobs.length,
      filtered: filteredJobs.length,
      percentage: allJobs.length > 0 ? Math.round((filteredJobs.length / allJobs.length) * 100) : 0,
      timeframe: this.jobHistory.currentTimeframe,
      hasActiveFilters: Object.keys(this.currentFilter).length > 0
    };
  }

  /**
   * Export current filter settings
   */
  exportFilterSettings() {
    return {
      version: '1.0',
      timestamp: new Date().toISOString(),
      filters: this.currentFilter,
      timeframe: this.jobHistory.currentTimeframe,
      settings: {
        itemsPerPage: this.jobHistory.itemsPerPage,
        currentPage: this.jobHistory.currentPage
      }
    };
  }

  /**
   * Import filter settings
   */
  importFilterSettings(settings) {
    try {
      if (settings.version === '1.0') {
        this.setFilter({
          filters: settings.filters || {},
          timeframe: settings.timeframe || 'today',
          page: settings.settings?.currentPage || 1
        });
        
        if (settings.settings?.itemsPerPage) {
          this.jobHistory.itemsPerPage = settings.settings.itemsPerPage;
        }
        
        return true;
      }
    } catch (error) {
      console.error('Failed to import filter settings:', error);
    }
    
    return false;
  }

  /**
   * Get available filter options based on current data
   */
  getAvailableFilterOptions() {
    const jobs = this.jobHistory.jobs || [];
    
    const options = {
      statuses: [...new Set(jobs.map(job => job.status).filter(Boolean))],
      users: [...new Set(jobs.map(job => job.user_id).filter(Boolean))],
      workers: [...new Set(jobs.map(job => job.worker_id).filter(Boolean))],
      priorities: [...new Set(jobs.map(job => job.priority || 'medium'))],
      steps: [...new Set(jobs.map(job => job.current_step).filter(Boolean))]
    };
    
    return options;
  }

  /**
   * Get smart filter suggestions based on current data
   */
  getFilterSuggestions() {
    const jobs = this.jobHistory.jobs || [];
    const suggestions = [];
    
    // Suggest failed jobs if any exist
    const failedCount = jobs.filter(job => job.status === 'failed').length;
    if (failedCount > 0) {
      suggestions.push({
        id: 'failed_jobs',
        label: `Show ${failedCount} failed jobs`,
        filter: { status: ['failed'] },
        icon: '❌'
      });
    }
    
    // Suggest long running jobs
    const longRunning = jobs.filter(job => {
      const duration = job.performance_metrics?.total_duration || job.duration || 0;
      return duration > 300 && job.status === 'processing'; // 5+ minutes
    }).length;
    
    if (longRunning > 0) {
      suggestions.push({
        id: 'long_running',
        label: `Show ${longRunning} long running jobs`,
        filter: { duration: { min: 300 }, status: ['processing'] },
        icon: '⏱️'
      });
    }
    
    // Suggest high priority jobs
    const highPriority = jobs.filter(job => job.priority === 'high').length;
    if (highPriority > 0) {
      suggestions.push({
        id: 'high_priority',
        label: `Show ${highPriority} high priority jobs`,
        filter: { priority: ['high'] },
        icon: '🔴'
      });
    }
    
    return suggestions;
  }

  /**
   * Destroy filter components and cleanup
   */
  destroy() {
    if (this.smartFilter) {
      this.smartFilter.destroy();
      this.smartFilter = null;
    }
    
    this.currentFilter = {};
  }
}