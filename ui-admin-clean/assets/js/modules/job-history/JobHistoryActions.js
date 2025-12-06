/**
 * JobHistory Actions Module
 * Handles all queue management and job actions
 * Extracted from JobHistory.js for better maintainability
 */

import { actionService } from '../../../../src/services/ActionService.js';

export class JobHistoryActions {
  constructor(jobHistoryInstance) {
    this.jobHistory = jobHistoryInstance;
  }

  /**
   * Handle manual refresh of job data
   */
  async handleManualRefresh() {
    try {
      console.log('🔄 Manual refresh triggered');
      this.showActionSuccess('Refreshing job data...');
      await this.jobHistory.loadJobHistory();
    } catch (error) {
      console.error('❌ Manual refresh failed:', error);
      this.showActionError('Failed to refresh job data');
    }
  }

  /**
   * Toggle queue monitoring (pause/resume)
   */
  async handleToggleMonitoring() {
    try {
      const button = document.getElementById('toggle-monitoring');
      if (!button) return;

      const isPaused = this.jobHistory.isMonitoringPaused;
      const action = isPaused ? 'resume' : 'pause';
      
      console.log(`${action === 'pause' ? '⏸️' : '▶️'} ${action} queue monitoring`);
      
      // Show loading state
      button.disabled = true;
      button.querySelector('.btn__icon').textContent = '⏳';
      
      if (action === 'pause') {
        // Use ActionService to pause queue
        await actionService.pauseQueue('default');
        
        this.jobHistory.isMonitoringPaused = true;
        button.querySelector('.btn__icon').textContent = '▶️';
        button.innerHTML = `<span class="btn__icon">▶️</span> Resume Queue`;
        
        this.showActionSuccess('Queue processing has been paused');
        
        // Stop auto-refresh
        if (this.jobHistory.refreshTimer) {
          clearInterval(this.jobHistory.refreshTimer);
        }
        
      } else {
        // Use ActionService to resume queue
        await actionService.resumeQueue('default');
        
        this.jobHistory.isMonitoringPaused = false;
        button.querySelector('.btn__icon').textContent = '⏸️';
        button.innerHTML = `<span class="btn__icon">⏸️</span> Pause Queue`;
        
        this.showActionSuccess('Queue processing has been resumed');
        
        // Restart auto-refresh
        this.jobHistory.startAutoRefresh();
      }
      
      // Re-enable button
      button.disabled = false;
      
    } catch (error) {
      console.error('❌ Toggle monitoring failed:', error);
      this.showActionError(`Failed to ${this.jobHistory.isMonitoringPaused ? 'resume' : 'pause'} queue monitoring`);
      
      // Reset button state on error
      const button = document.getElementById('toggle-monitoring');
      if (button) {
        button.disabled = false;
        button.querySelector('.btn__icon').textContent = this.jobHistory.isMonitoringPaused ? '▶️' : '⏸️';
      }
    }
  }

  /**
   * Handle job retry action
   */
  async handleJobRetry(jobId) {
    try {
      console.log('🔄 Retrying job:', jobId);
      this.showActionProgress(`Retrying job ${jobId.substring(0, 8)}...`);
      
      // Use imported actionService instance
      
      const result = await actionService.retryJob(jobId);
      
      console.log(`✅ Job ${jobId} retry request successful:`, result);
      this.showActionSuccess(`Job ${jobId.substring(0, 8)} has been queued for retry`);
      
      // Update job status locally for immediate feedback
      const job = this.jobHistory.jobs.find(j => j.id === jobId);
      if (job) {
        job.status = 'queued';
        job.retry_count = (job.retry_count || 0) + 1;
        job.updated_at = new Date().toISOString();
      }
      
      // Re-render to show updated status
      this.jobHistory.renderCurrentView();;
      
    } catch (error) {
      console.error('❌ Job retry failed:', error);
      this.showActionError(`Failed to retry job ${jobId.substring(0, 8)}`);
    }
  }

  /**
   * Handle job cancellation
   */
  async handleJobCancel(jobId) {
    try {
      // Confirmation dialog
      const confirmed = confirm(`Are you sure you want to cancel job ${jobId.substring(0, 8)}?`);
      if (!confirmed) return;
      
      console.log('❌ Cancelling job:', jobId);
      this.showActionProgress(`Cancelling job ${jobId.substring(0, 8)}...`);
      
      // Import and use ActionService
      const ActionService = (await import('/ui-admin-clean/src/services/ActionService.js')).default;
      const actionService = new ActionService();
      
      const result = await actionService.cancelJob(jobId);
      
      console.log(`✅ Job ${jobId} cancel request successful:`, result);
      this.showActionSuccess(`Job ${jobId.substring(0, 8)} cancelled`);
      
      // Update job status locally
      const job = this.jobHistory.jobs.find(j => j.id === jobId);
      if (job) {
        job.status = 'cancelled';
        job.updated_at = new Date().toISOString();
      }
      
      // Re-render to show updated status
      this.jobHistory.renderCurrentView();
      
    } catch (error) {
      console.error('❌ Job cancellation failed:', error);
      this.showActionError(`Failed to cancel job ${jobId.substring(0, 8)}`);
    }
  }

  /**
   * Handle delete job action
   */
  async handleJobDelete(jobId) {
    try {
      // Confirmation dialog
      const confirmed = confirm(`Are you sure you want to delete job ${jobId.substring(0, 8)}? This cannot be undone.`);
      if (!confirmed) return;
      
      console.log('🗑️ Deleting job:', jobId);
      this.showActionProgress(`Deleting job ${jobId.substring(0, 8)}...`);
      
      const response = await this.jobHistory.apiClient.delete(`/api/jobs/${jobId}`);
      
      if (response.success) {
        this.showActionSuccess(`Job ${jobId.substring(0, 8)} deleted`);
        
        // Refresh job list
        await this.jobHistory.loadJobHistory();
      } else {
        this.showActionError(`Failed to delete job: ${response.message}`);
      }
      
    } catch (error) {
      console.error('❌ Job deletion failed:', error);
      this.showActionError(`Failed to delete job ${jobId.substring(0, 8)}`);
    }
  }

  /**
   * Handle bulk job actions
   */
  async handleBulkJobAction(action, jobIds) {
    try {
      const jobCount = jobIds.length;
      console.log(`🔄 Bulk ${action} for ${jobCount} jobs:`, jobIds);
      
      this.showActionProgress(`${action} ${jobCount} jobs...`);
      
      const promises = jobIds.map(jobId => {
        switch (action) {
          case 'retry':
            return this.jobHistory.apiClient.post('/api/admin/action', {
              action: 'retry_job',
              job_id: jobId
            });
          case 'cancel':
            return this.jobHistory.apiClient.post('/api/admin/action', {
              action: 'cancel_job',
              job_id: jobId
            });
          case 'delete':
            return this.jobHistory.apiClient.delete(`/api/jobs/${jobId}`);
          default:
            throw new Error(`Unknown bulk action: ${action}`);
        }
      });
      
      const results = await Promise.allSettled(promises);
      
      // Count successes and failures
      const successes = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
      const failures = jobCount - successes;
      
      if (failures === 0) {
        this.showActionSuccess(`All ${jobCount} jobs ${action}ed successfully`);
      } else if (successes === 0) {
        this.showActionError(`Failed to ${action} all ${jobCount} jobs`);
      } else {
        this.showActionWarning(`${successes} jobs ${action}ed, ${failures} failed`);
      }
      
      // Refresh job list
      await this.jobHistory.loadJobHistory();
      
    } catch (error) {
      console.error(`❌ Bulk ${action} failed:`, error);
      this.showActionError(`Failed to ${action} selected jobs`);
    }
  }

  /**
   * Handle clear queue action
   */
  async handleClearQueue() {
    try {
      // Confirmation dialog
      const confirmed = confirm('Are you sure you want to clear the entire queue? This will cancel all pending jobs.');
      if (!confirmed) return;
      
      console.log('🧹 Clearing queue');
      this.showActionProgress('Clearing queue...');
      
      const response = await this.jobHistory.apiClient.post('/api/admin/action', {
        action: 'clear_queue'
      });
      
      if (response.success) {
        this.showActionSuccess('Queue cleared successfully');
        
        // Refresh job list
        await this.jobHistory.loadJobHistory();
      } else {
        this.showActionError(`Failed to clear queue: ${response.message}`);
      }
      
    } catch (error) {
      console.error('❌ Clear queue failed:', error);
      this.showActionError('Failed to clear queue');
    }
  }

  /**
   * Export jobs to CSV
   */
  async handleExportJobs(jobs = null) {
    try {
      console.log('📊 Exporting jobs to CSV');
      this.showActionProgress('Generating CSV export...');
      
      // Use provided jobs or current job list
      const jobsToExport = jobs || this.jobHistory.jobs;
      
      if (!jobsToExport || jobsToExport.length === 0) {
        this.showActionWarning('No jobs to export');
        return;
      }
      
      // Generate CSV content
      const csvContent = this.generateJobsCSV(jobsToExport);
      
      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      
      link.setAttribute('href', url);
      link.setAttribute('download', `job_history_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      this.showActionSuccess(`Exported ${jobsToExport.length} jobs to CSV`);
      
    } catch (error) {
      console.error('❌ Export jobs failed:', error);
      this.showActionError('Failed to export jobs');
    }
  }

  /**
   * Generate CSV content from jobs array
   */
  generateJobsCSV(jobs) {
    const headers = [
      'Job ID',
      'User ID', 
      'Status',
      'Progress',
      'Video URL',
      'Video Title',
      'Current Step',
      'Error Message',
      'Retry Count',
      'Worker ID',
      'Created At',
      'Started At',
      'Completed At',
      'Updated At'
    ];
    
    const csvRows = [headers.join(',')];
    
    jobs.forEach(job => {
      const row = [
        `"${job.id || ''}"`,
        `"${job.user_id || ''}"`,
        `"${job.status || ''}"`,
        `"${job.progress || 0}"`,
        `"${job.video_url || ''}"`,
        `"${job.video_title || ''}"`,
        `"${job.current_step || ''}"`,
        `"${job.error_message || ''}"`,
        `"${job.retry_count || 0}"`,
        `"${job.worker_id || ''}"`,
        `"${job.created_at || ''}"`,
        `"${job.started_at || ''}"`,
        `"${job.completed_at || ''}"`,
        `"${job.updated_at || ''}"`
      ];
      csvRows.push(row.join(','));
    });
    
    return csvRows.join('\n');
  }

  // =============================================================================
  // ACTION FEEDBACK METHODS
  // =============================================================================

  /**
   * Show action success message
   */
  showActionSuccess(message) {
    this.showActionMessage(message, 'success', '✅');
  }

  /**
   * Show action error message
   */
  showActionError(message) {
    this.showActionMessage(message, 'error', '❌');
  }

  /**
   * Show action warning message
   */
  showActionWarning(message) {
    this.showActionMessage(message, 'warning', '⚠️');
  }

  /**
   * Show action progress message
   */
  showActionProgress(message) {
    this.showActionMessage(message, 'progress', '⏳');
  }

  /**
   * Show generic action message with type and icon
   */
  showActionMessage(message, type = 'info', icon = 'ℹ️') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `action-notification action-notification--${type}`;
    notification.innerHTML = `
      <div class="action-notification__content">
        <span class="action-notification__icon">${icon}</span>
        <span class="action-notification__message">${message}</span>
        <button class="action-notification__dismiss" onclick="this.parentElement.parentElement.remove()">×</button>
      </div>
    `;
    
    // Add to page
    const container = document.querySelector('.job-history-container') || document.body;
    container.appendChild(notification);
    
    // Auto-remove after delay (except progress messages)
    if (type !== 'progress') {
      const delay = type === 'error' ? 7000 : 4000; // Errors stay longer
      setTimeout(() => {
        if (notification.parentElement) {
          notification.remove();
        }
      }, delay);
    }
    
    // Remove any existing progress messages if this is not progress
    if (type !== 'progress') {
      const existingProgress = container.querySelectorAll('.action-notification--progress');
      existingProgress.forEach(el => el.remove());
    }
  }
}