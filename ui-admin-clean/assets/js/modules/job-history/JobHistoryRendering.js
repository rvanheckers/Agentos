/**
 * JobHistory Rendering Module
 * Handles all rendering methods for different job views
 * Extracted from JobHistory.js for better maintainability
 */

export class JobHistoryRendering {
  constructor(jobHistoryInstance) {
    this.jobHistory = jobHistoryInstance;
  }

  /**
   * Main render method - renders the complete JobHistory view
   */
  render() {
    this.jobHistory.container.innerHTML = `
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

  /**
   * Render empty state when no jobs found
   */
  renderEmptyState() {
    return `
      <div class="empty-state">
        <div class="empty-state__icon">📋</div>
        <h3 class="empty-state__title">No Jobs Found</h3>
        <p class="empty-state__description">
          No jobs match your current filters. Try adjusting your search criteria.
        </p>
      </div>
    `;
  }

  /**
   * Render current view based on active tab - copied from backup
   */
  renderCurrentView() {
    try {
      const contentContainer = this.jobHistory.container.querySelector('#jobsGrid');
      if (!contentContainer) {
        console.warn('❌ #jobsGrid container not found!');
        return;
      }

      const filteredJobs = this.jobHistory.getFilteredJobs();
      console.log('🎨 About to render', filteredJobs.length, 'jobs');
      
      // Update section title based on current filter
      this.jobHistory.updateJobsSectionTitle();
      
      // Always use list view
      console.log('🎨 About to call renderListLayout with container:', contentContainer, 'and', filteredJobs.length, 'jobs');
      this.renderListLayout(contentContainer, filteredJobs);
      console.log('🎨 renderListLayout call FINISHED');
    } catch (error) {
      console.error('❌ renderCurrentView error:', error);
      console.error('❌ Error stack:', error.stack);
    }
  }

  /**
   * Render list layout for jobs - copied from backup
   */
  renderListLayout(container, jobs) {
    console.log('🎨 ===== renderListLayout START =====');
    console.log('🎨 Container:', container);
    console.log('🎨 Jobs:', jobs?.length);
    
    try {
    
    if (!jobs || jobs.length === 0) {
      console.log('🎨 No jobs - rendering empty state');
      container.innerHTML = this.renderEmptyState();
      return;
    }
    
    console.log('🎨 About to process', jobs.length, 'jobs');
    
    // CRITICAL FIX: Clear container first!
    console.log('🎨 Clearing container first...');
    container.innerHTML = '';
    console.log('🎨 Container cleared successfully');

    // Pagination logic
    const currentPage = this.jobHistory.currentPage || 1;
    const itemsPerPage = this.jobHistory.itemsPerPage || 20;
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

    const html = `
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
    
    console.log('🎨 About to set innerHTML...');
    container.innerHTML = html;
    console.log('🎨 innerHTML set successfully');
    
    // Fix positioning and visibility issues
    container.style.cssText = `
      display: block !important;
      visibility: visible !important;
      position: static !important;
      width: 100% !important;
      min-height: 200px !important;
      background: transparent !important;
      z-index: auto !important;
    `;
    console.log('🎨 Styles applied successfully');
    console.log('🎨 ===== renderListLayout COMPLETE =====');
    
    } catch (error) {
      console.error('❌ renderListLayout error:', error);
      console.error('❌ Error stack:', error.stack);
      container.innerHTML = '<div class="error">Rendering failed: ' + error.message + '</div>';
    }
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
      if (total > 1) pages.push(`<button class="pagination-btn ${current === total ? 'pagination-btn--active' : ''}" data-page="${total}">${total}</button>`);
    }
    
    return pages.join('');
  }

  getStatusClass(status) {
    const statusMap = {
      'completed': 'success',
      'processing': 'warning', 
      'running': 'warning',
      'queued': 'info',
      'pending': 'info',
      'failed': 'error',
      'cancelled': 'error'
    };
    return statusMap[status] || 'default';
  }

  getStatusIcon(status) {
    const iconMap = {
      'completed': '✅',
      'processing': '⚡',
      'running': '🔄',
      'queued': '⏳',
      'pending': '⏳',
      'failed': '❌',
      'cancelled': '🚫'
    };
    return iconMap[status] || '❔';
  }

  formatDuration(seconds) {
    if (!seconds || seconds === 0) return '-';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes === 0) {
      return `${remainingSeconds}s`;
    } else if (minutes < 60) {
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;
      return `${hours}h ${remainingMinutes}m`;
    }
  }

  formatTimeAgo(timestamp) {
    if (!timestamp) return '-';
    
    const now = new Date();
    const jobTime = new Date(timestamp);
    const diffMs = now - jobTime;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  /**
   * Render grid layout for jobs
   */
  renderGridLayout(container, jobs, highlight = 'none', detailLevel = 'summary') {
    if (!jobs || jobs.length === 0) {
      container.innerHTML = this.renderEmptyState();
      return;
    }

    const jobCards = jobs.map(job => this.renderJobCard(job, { 
      detailLevel, 
      highlight: highlight === job.id ? 'highlight' : 'none' 
    })).join('');

    container.innerHTML = `
      <div class="job-grid">
        ${jobCards}
      </div>
    `;
  }

  /**
   * Render list layout for jobs with pagination
   */
}
