/**
 * Job History Component
 * Displays job history from database with filtering and details
 */

import { DatabaseService } from '../services/database-service.js';

export class JobHistory {
  constructor(container) {
    this.container = container;
    this.databaseService = new DatabaseService();
    this.jobs = [];
    this.isLoading = false;
    this.selectedJob = null;
    this.filters = {
      limit: 20,
      status: 'all',
      userId: null
    };
  }

  /**
   * Initialize the job history component
   */
  async init() {
    console.log('📚 Initializing Job History component');
    
    this.render();
    await this.loadJobs();
    this.attachEventListeners();
  }

  /**
   * Render the job history interface
   */
  render() {
    this.container.innerHTML = `
      <div class="job-history">
        <div class="job-history-header">
          <h2>📚 Job History</h2>
          <div class="job-history-controls">
            <select class="filter-status" aria-label="Filter by status">
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="processing">Processing</option>
              <option value="queued">Queued</option>
            </select>
            <select class="filter-limit" aria-label="Number of jobs to show">
              <option value="10">10 jobs</option>
              <option value="20" selected>20 jobs</option>
              <option value="50">50 jobs</option>
              <option value="100">100 jobs</option>
            </select>
            <button class="refresh-btn" aria-label="Refresh job history">
              🔄 Refresh
            </button>
          </div>
        </div>
        
        <div class="job-history-content">
          <div class="job-list">
            <div class="loading-indicator" style="display: none;">
              <div class="spinner"></div>
              <p>Loading jobs...</p>
            </div>
            
            <div class="job-table">
              <table>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Job ID</th>
                    <th>Video Title</th>
                    <th>User</th>
                    <th>Created</th>
                    <th>Duration</th>
                    <th>Clips</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody class="job-table-body">
                  <!-- Jobs will be populated here -->
                </tbody>
              </table>
            </div>
          </div>
          
          <div class="job-details" style="display: none;">
            <div class="job-details-header">
              <h3>Job Details</h3>
              <button class="close-details-btn" aria-label="Close details">✕</button>
            </div>
            <div class="job-details-content">
              <!-- Job details will be populated here -->
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Load jobs from database
   */
  async loadJobs() {
    this.setLoading(true);
    
    try {
      const result = await this.databaseService.getJobHistory({
        limit: this.filters.limit,
        userId: this.filters.userId
      });
      
      if (result.success) {
        this.jobs = result.jobs.map(job => this.databaseService.formatJobForDisplay(job));
        this.renderJobs();
        console.log('📚 Loaded', this.jobs.length, 'jobs');
      } else {
        this.showError('Failed to load job history: ' + result.error);
      }
      
    } catch (error) {
      console.error('❌ Failed to load jobs:', error);
      this.showError('Failed to load job history');
    } finally {
      this.setLoading(false);
    }
  }

  /**
   * Render jobs in the table
   */
  renderJobs() {
    const tableBody = this.container.querySelector('.job-table-body');
    
    if (this.jobs.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="8" class="no-jobs">
            <div class="empty-state">
              <p>📝 No jobs found</p>
              <p>Jobs will appear here after you process some videos</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    // Filter jobs based on status
    const filteredJobs = this.filters.status === 'all' 
      ? this.jobs 
      : this.jobs.filter(job => job.status === this.filters.status);

    tableBody.innerHTML = filteredJobs.map(job => `
      <tr class="job-row" data-job-id="${job.id}">
        <td class="job-status">
          <span class="status-badge status-${job.status}">
            ${job.statusEmoji} ${job.status}
          </span>
        </td>
        <td class="job-id">
          <code>${job.shortId}</code>
        </td>
        <td class="job-title">
          <div class="video-title">
            ${job.videoTitle || 'Untitled'}
          </div>
          <div class="video-url">
            <a href="${job.videoUrl}" target="_blank" rel="noopener">
              ${this.truncateUrl(job.videoUrl)}
            </a>
          </div>
        </td>
        <td class="job-user">
          ${job.userId}
        </td>
        <td class="job-created">
          <div class="date-time">
            ${this.formatDate(job.createdAt)}
          </div>
          <div class="time-ago">
            ${this.formatTimeAgo(job.createdAt)}
          </div>
        </td>
        <td class="job-duration">
          ${job.duration || '-'}
        </td>
        <td class="job-clips">
          <span class="clip-count">
            🎬 ${job.clipsCount}
          </span>
        </td>
        <td class="job-actions">
          <button class="view-details-btn" data-job-id="${job.id}">
            👁️ Details
          </button>
        </td>
      </tr>
    `).join('');
  }

  /**
   * Show job details in sidebar
   */
  async showJobDetails(jobId) {
    this.selectedJob = jobId;
    const detailsPanel = this.container.querySelector('.job-details');
    const detailsContent = this.container.querySelector('.job-details-content');
    
    // Show loading in details panel
    detailsContent.innerHTML = `
      <div class="loading-indicator">
        <div class="spinner"></div>
        <p>Loading job details...</p>
      </div>
    `;
    
    detailsPanel.style.display = 'block';
    
    try {
      const result = await this.databaseService.getJobDetails(jobId);
      
      if (result.success) {
        this.renderJobDetails(result.job);
      } else {
        detailsContent.innerHTML = `
          <div class="error-message">
            <p>❌ Failed to load job details</p>
            <p>${result.error}</p>
          </div>
        `;
      }
      
    } catch (error) {
      console.error('❌ Failed to load job details:', error);
      detailsContent.innerHTML = `
        <div class="error-message">
          <p>❌ Failed to load job details</p>
          <p>${error.message}</p>
        </div>
      `;
    }
  }

  /**
   * Render job details in sidebar
   */
  renderJobDetails(job) {
    const detailsContent = this.container.querySelector('.job-details-content');
    const formattedJob = this.databaseService.formatJobForDisplay(job);
    
    detailsContent.innerHTML = `
      <div class="job-details-info">
        <div class="detail-section">
          <h4>📋 Job Information</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Job ID:</label>
              <code>${formattedJob.id}</code>
            </div>
            <div class="detail-item">
              <label>Status:</label>
              <span class="status-badge status-${formattedJob.status}">
                ${formattedJob.statusEmoji} ${formattedJob.status}
              </span>
            </div>
            <div class="detail-item">
              <label>Progress:</label>
              <div class="progress-bar">
                <div class="progress-fill" style="width: ${formattedJob.progress}%"></div>
                <span class="progress-text">${formattedJob.progress}%</span>
              </div>
            </div>
            <div class="detail-item">
              <label>User:</label>
              <span>${formattedJob.userId}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>🎬 Video Information</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Title:</label>
              <span>${formattedJob.videoTitle}</span>
            </div>
            <div class="detail-item">
              <label>URL:</label>
              <a href="${formattedJob.videoUrl}" target="_blank" rel="noopener">
                ${this.truncateUrl(formattedJob.videoUrl)}
              </a>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>⏱️ Timing</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Created:</label>
              <span>${this.formatDate(formattedJob.createdAt)}</span>
            </div>
            <div class="detail-item">
              <label>Started:</label>
              <span>${formattedJob.startedAt ? this.formatDate(formattedJob.startedAt) : 'Not started'}</span>
            </div>
            <div class="detail-item">
              <label>Completed:</label>
              <span>${formattedJob.completedAt ? this.formatDate(formattedJob.completedAt) : 'Not completed'}</span>
            </div>
            <div class="detail-item">
              <label>Duration:</label>
              <span>${formattedJob.duration || 'N/A'}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>🎯 Results</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Clips Generated:</label>
              <span>🎬 ${formattedJob.clipsCount}</span>
            </div>
            ${formattedJob.errorMessage ? `
              <div class="detail-item">
                <label>Error:</label>
                <div class="error-message">${formattedJob.errorMessage}</div>
              </div>
            ` : ''}
          </div>
        </div>
        
        <div class="detail-section">
          <h4>📊 Data Source</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Source:</label>
              <span>💾 Database (Persistent)</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // Refresh button
    this.container.querySelector('.refresh-btn').addEventListener('click', () => {
      this.loadJobs();
    });

    // Status filter
    this.container.querySelector('.filter-status').addEventListener('change', (e) => {
      this.filters.status = e.target.value;
      this.renderJobs();
    });

    // Limit filter
    this.container.querySelector('.filter-limit').addEventListener('change', (e) => {
      this.filters.limit = parseInt(e.target.value);
      this.loadJobs();
    });

    // View details buttons
    this.container.addEventListener('click', (e) => {
      if (e.target.classList.contains('view-details-btn')) {
        const jobId = e.target.dataset.jobId;
        this.showJobDetails(jobId);
      }
    });

    // Close details button
    this.container.querySelector('.close-details-btn').addEventListener('click', () => {
      this.container.querySelector('.job-details').style.display = 'none';
      this.selectedJob = null;
    });
  }

  /**
   * Set loading state
   */
  setLoading(isLoading) {
    this.isLoading = isLoading;
    const loadingIndicator = this.container.querySelector('.loading-indicator');
    const jobTable = this.container.querySelector('.job-table');
    
    if (isLoading) {
      loadingIndicator.style.display = 'block';
      jobTable.style.opacity = '0.5';
    } else {
      loadingIndicator.style.display = 'none';
      jobTable.style.opacity = '1';
    }
  }

  /**
   * Show error message
   */
  showError(message) {
    const tableBody = this.container.querySelector('.job-table-body');
    tableBody.innerHTML = `
      <tr>
        <td colspan="8" class="error-state">
          <div class="error-message">
            <p>❌ ${message}</p>
            <button class="retry-btn" onclick="this.closest('.job-history').dispatchEvent(new CustomEvent('retry'))">
              🔄 Retry
            </button>
          </div>
        </td>
      </tr>
    `;
  }

  /**
   * Format date for display
   */
  formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
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
   * Truncate URL for display
   */
  truncateUrl(url) {
    if (!url || typeof url !== 'string') {
      return 'N/A';
    }
    if (url.length > 50) {
      return url.substring(0, 47) + '...';
    }
    return url;
  }
}

export default JobHistory;