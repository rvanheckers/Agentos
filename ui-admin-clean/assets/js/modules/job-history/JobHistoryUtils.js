/**
 * JobHistory Utilities Module
 * Helper functions and utilities for job history management
 * Extracted from JobHistory.js for better maintainability
 */

export class JobHistoryUtils {
  constructor() {
    // Static utility class
  }

  /**
   * Filter jobs by date period
   */
  static filterJobsByDate(jobs, period) {
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
        console.warn('Job has unexpected date type:', typeof dateValue, 'value:', dateValue, 'for job:', job.id || 'unknown');
        return false;
      }
      
      // Compare dates
      return jobDate >= filterDate;
    });
  }

  /**
   * Filter jobs by status
   */
  static filterJobsByStatus(jobs, status) {
    if (!jobs || jobs.length === 0) return [];
    if (!status || status === 'all') return jobs;
    
    return jobs.filter(job => job.status === status);
  }

  /**
   * Calculate average wait time for jobs
   */
  static calculateAvgWaitTime(jobs) {
    if (!jobs || jobs.length === 0) return 0;
    
    const waitTimes = jobs
      .filter(job => job.created_at && job.started_at)
      .map(job => {
        const created = new Date(job.created_at);
        const started = new Date(job.started_at);
        return started - created;
      })
      .filter(time => time > 0); // Only positive wait times
    
    if (waitTimes.length === 0) return 0;
    
    const avgWaitTimeMs = waitTimes.reduce((sum, time) => sum + time, 0) / waitTimes.length;
    return Math.round(avgWaitTimeMs / 1000); // Convert to seconds
  }

  /**
   * Calculate average processing time for completed jobs
   */
  static calculateAvgProcessingTime(jobs) {
    if (!jobs || jobs.length === 0) return 0;
    
    const processingTimes = jobs
      .filter(job => job.status === 'completed' && job.started_at && job.completed_at)
      .map(job => {
        const started = new Date(job.started_at);
        const completed = new Date(job.completed_at);
        return completed - started;
      })
      .filter(time => time > 0); // Only positive processing times
    
    if (processingTimes.length === 0) return 0;
    
    const avgProcessingTimeMs = processingTimes.reduce((sum, time) => sum + time, 0) / processingTimes.length;
    return Math.round(avgProcessingTimeMs / 1000); // Convert to seconds
  }

  /**
   * Format duration in a human-readable way
   */
  static formatDuration(seconds) {
    if (!seconds || seconds < 0) return '0s';
    
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return remainingSeconds > 0 ? `${minutes}m ${Math.round(remainingSeconds)}s` : `${minutes}m`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const remainingMinutes = Math.floor((seconds % 3600) / 60);
      return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
    }
  }

  /**
   * Format file size in human-readable way
   */
  static formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const base = 1024;
    const exp = Math.floor(Math.log(bytes) / Math.log(base));
    const size = bytes / Math.pow(base, exp);
    
    return `${size.toFixed(1)} ${units[exp]}`;
  }

  /**
   * Format timestamp in relative time (e.g., "2 hours ago")
   */
  static formatRelativeTime(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now - date;
    
    if (isNaN(date.getTime())) return 'Invalid date';
    
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSeconds < 60) {
      return 'Just now';
    } else if (diffMinutes < 60) {
      return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString();
    }
  }

  /**
   * Format absolute timestamp
   */
  static formatAbsoluteTime(timestamp, options = {}) {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'Invalid date';
    
    const defaultOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...options
    };
    
    return date.toLocaleDateString('en-US', defaultOptions);
  }

  /**
   * Get status display properties
   */
  static getStatusDisplay(status) {
    const statusMap = {
      'pending': { 
        label: 'Pending', 
        class: 'status--pending', 
        icon: '⏳', 
        color: '#fbbf24' 
      },
      'queued': { 
        label: 'Queued', 
        class: 'status--queued', 
        icon: '📋', 
        color: '#60a5fa' 
      },
      'processing': { 
        label: 'Processing', 
        class: 'status--processing', 
        icon: '⚡', 
        color: '#34d399' 
      },
      'running': { 
        label: 'Running', 
        class: 'status--running', 
        icon: '🔄', 
        color: '#34d399' 
      },
      'completed': { 
        label: 'Completed', 
        class: 'status--completed', 
        icon: '✅', 
        color: '#10b981' 
      },
      'failed': { 
        label: 'Failed', 
        class: 'status--failed', 
        icon: '❌', 
        color: '#ef4444' 
      },
      'cancelled': { 
        label: 'Cancelled', 
        class: 'status--cancelled', 
        icon: '🚫', 
        color: '#6b7280' 
      }
    };
    
    return statusMap[status] || { 
      label: status || 'Unknown', 
      class: 'status--unknown', 
      icon: '❓', 
      color: '#6b7280' 
    };
  }

  /**
   * Get progress bar properties
   */
  static getProgressDisplay(progress, status) {
    const numericProgress = Math.max(0, Math.min(100, Number(progress) || 0));
    
    let progressClass = 'progress--normal';
    let progressColor = '#3b82f6';
    
    if (status === 'failed') {
      progressClass = 'progress--error';
      progressColor = '#ef4444';
    } else if (status === 'completed') {
      progressClass = 'progress--success';
      progressColor = '#10b981';
    } else if (status === 'cancelled') {
      progressClass = 'progress--cancelled';
      progressColor = '#6b7280';
    }
    
    return {
      percentage: numericProgress,
      class: progressClass,
      color: progressColor,
      label: `${numericProgress}%`
    };
  }

  /**
   * Truncate text with ellipsis
   */
  static truncateText(text, maxLength = 50) {
    if (!text || text.length <= maxLength) return text || '';
    return text.substring(0, maxLength - 3) + '...';
  }

  /**
   * Escape HTML to prevent XSS
   */
  static escapeHtml(text) {
    if (!text) return '';
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Generate unique ID
   */
  static generateId(prefix = 'id') {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Debounce function
   */
  static debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * Throttle function
   */
  static throttle(func, limit) {
    let inThrottle;
    return function(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }

  /**
   * Deep clone object
   */
  static deepClone(obj) {
    if (obj === null || typeof obj !== "object") return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => this.deepClone(item));
    if (typeof obj === "object") {
      const clonedObj = {};
      for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
          clonedObj[key] = this.deepClone(obj[key]);
        }
      }
      return clonedObj;
    }
  }

  /**
   * Validate job object structure
   */
  static validateJob(job) {
    const errors = [];
    
    if (!job) {
      errors.push('Job object is null or undefined');
      return errors;
    }
    
    if (!job.id) errors.push('Missing job ID');
    if (!job.status) errors.push('Missing job status');
    if (!job.created_at) errors.push('Missing creation timestamp');
    
    // Validate status
    const validStatuses = ['pending', 'queued', 'processing', 'running', 'completed', 'failed', 'cancelled'];
    if (job.status && !validStatuses.includes(job.status)) {
      errors.push(`Invalid status: ${job.status}`);
    }
    
    // Validate progress
    if (job.progress !== undefined && (job.progress < 0 || job.progress > 100)) {
      errors.push(`Invalid progress: ${job.progress} (must be 0-100)`);
    }
    
    return errors;
  }

  /**
   * Sort jobs by various criteria
   */
  static sortJobs(jobs, sortBy = 'created_at', sortOrder = 'desc') {
    if (!jobs || jobs.length === 0) return [];
    
    const sortedJobs = [...jobs].sort((a, b) => {
      let aValue, bValue;
      
      switch (sortBy) {
        case 'created_at':
        case 'updated_at':
        case 'started_at':
        case 'completed_at':
          aValue = a[sortBy] ? new Date(a[sortBy]).getTime() : 0;
          bValue = b[sortBy] ? new Date(b[sortBy]).getTime() : 0;
          break;
        case 'progress':
          aValue = Number(a.progress) || 0;
          bValue = Number(b.progress) || 0;
          break;
        case 'status':
          // Sort by status priority
          const statusPriority = {
            'processing': 1, 'running': 2, 'queued': 3, 'pending': 4,
            'failed': 5, 'cancelled': 6, 'completed': 7
          };
          aValue = statusPriority[a.status] || 99;
          bValue = statusPriority[b.status] || 99;
          break;
        default:
          aValue = a[sortBy] || '';
          bValue = b[sortBy] || '';
      }
      
      if (aValue === bValue) return 0;
      
      const comparison = aValue < bValue ? -1 : 1;
      return sortOrder === 'asc' ? comparison : -comparison;
    });
    
    return sortedJobs;
  }

  /**
   * Group jobs by criteria
   */
  static groupJobs(jobs, groupBy = 'status') {
    if (!jobs || jobs.length === 0) return {};
    
    return jobs.reduce((groups, job) => {
      let key;
      
      switch (groupBy) {
        case 'status':
          key = job.status || 'unknown';
          break;
        case 'user':
          key = job.user_id || 'unknown';
          break;
        case 'date':
          const date = job.created_at ? new Date(job.created_at).toDateString() : 'unknown';
          key = date;
          break;
        case 'worker':
          key = job.worker_id || 'unassigned';
          break;
        default:
          key = job[groupBy] || 'unknown';
      }
      
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(job);
      
      return groups;
    }, {});
  }
}