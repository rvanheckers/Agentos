export class QuickActions {
  constructor(apiClient, loadDataCallback, addActivityCallback) {
    this.apiClient = apiClient;
    this.loadDataCallback = loadDataCallback;
    this.addActivityCallback = addActivityCallback;
  }

  setupEventHandlers() {
    const systemCheckBtn = document.getElementById('system-check-btn');
    if (systemCheckBtn) {
      systemCheckBtn.addEventListener('click', () => this.runSystemCheck());
    }

    const flowerDashboardBtn = document.getElementById('flower-dashboard-btn');
    if (flowerDashboardBtn) {
      flowerDashboardBtn.addEventListener('click', () => this.openFlowerDashboard());
    }

    const refreshDashboardBtn = document.getElementById('refresh-dashboard-btn');
    if (refreshDashboardBtn) {
      refreshDashboardBtn.addEventListener('click', () => this.refreshDashboard());
    }

    const viewLogsBtn = document.getElementById('view-logs-btn');
    if (viewLogsBtn) {
      viewLogsBtn.addEventListener('click', () => this.navigateToLogs());
    }

    const restartFailedBtn = document.getElementById('restart-failed-btn');
    if (restartFailedBtn) {
      restartFailedBtn.addEventListener('click', () => this.restartFailedJobs());
    }

    const exportReportBtn = document.getElementById('export-report-btn');
    if (exportReportBtn) {
      exportReportBtn.addEventListener('click', () => this.exportDailyReport());
    }

    const quickActions = document.querySelectorAll('.quick-action[data-view]');
    quickActions.forEach(action => {
      action.addEventListener('click', () => {
        const view = action.dataset.view;
        if (view) {
          window.dispatchEvent(new CustomEvent('navigate', { detail: { view } }));
        }
      });
    });
  }

  async executeButtonAction(buttonId, action, loadingText, loadingDesc) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    const originalHTML = button.innerHTML;
    
    try {
      button.disabled = true;
      button.innerHTML = `
        <div class="quick-action__icon">⏳</div>
        <div class="quick-action__title">${loadingText}</div>
        <div class="quick-action__description">${loadingDesc}</div>
      `;

      const result = await action();
      
      button.innerHTML = result.successHTML;
      setTimeout(() => this.loadDataCallback(), 1000);
      
      setTimeout(() => {
        button.disabled = false;
        button.innerHTML = originalHTML;
      }, result.resetDelay || 3000);

      return result;
    } catch (error) {
      console.error(`❌ ${buttonId} failed:`, error);
      
      button.innerHTML = `
        <div class="quick-action__icon">❌</div>
        <div class="quick-action__title">Action Failed</div>
        <div class="quick-action__description">Please try again</div>
      `;

      setTimeout(() => {
        button.disabled = false;
        button.innerHTML = originalHTML;
      }, 3000);
      
      throw error;
    }
  }

  async runSystemCheck() {
    await this.executeButtonAction('system-check-btn', async () => {
      console.log('🔍 Running system check...');
      
      // Add activity event for starting check
      if (this.addActivityCallback) {
        this.addActivityCallback({
          icon: '🔍',
          message: 'System health check initiated',
          description: 'Checking CPU, memory, disk, and service status'
        });
      }
      
      // Graceful fallback if apiClient is null
      if (!this.apiClient || !this.apiClient.triggerSystemCheck) {
        console.warn('⚠️ API client not available, using mock system check result');
        const result = {
          overall_status: 'healthy',
          checks_performed: 5,
          issues_found: 0
        };
        return {
          successHTML: `
            <div class="quick-action__icon">✅</div>
            <div class="quick-action__title">Check Complete (Mock)</div>
            <div class="quick-action__description">Status: ${result.overall_status}</div>
          `
        };
      }
      
      const result = await this.apiClient.triggerSystemCheck();
      console.log('✅ System check completed:', result);
      
      // Add completion activity event
      if (this.addActivityCallback) {
        this.addActivityCallback({
          icon: result.overall_status === 'healthy' ? '✅' : '⚠️',
          message: `System check completed - ${result.overall_status}`,
          description: `${result.checks_performed} checks performed, ${result.issues_found} issues found`
        });
      }
      
      return {
        successHTML: `
          <div class="quick-action__icon">✅</div>
          <div class="quick-action__title">Check Complete</div>
          <div class="quick-action__description">Status: ${result.overall_status}</div>
        `
      };
    }, 'Running...', 'Performing system check');
  }

  openFlowerDashboard() {
    console.log('🌸 Opening Flower dashboard...');
    const flowerUrl = 'http://localhost:5555';
    
    // Try to open in new tab
    const newWindow = window.open(flowerUrl, '_blank');
    
    if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
      // Popup blocked - show manual link
      alert(`🌸 Flower Dashboard\n\nPopup was blocked. Please open manually:\n${flowerUrl}\n\nFlower provides real-time Celery worker monitoring with detailed metrics, task history, and worker management.`);
    } else {
      console.log('✅ Flower dashboard opened in new tab');
    }
  }

  async purgeQueue() {
    const confirmed = confirm('⚠️ WARNING: This will permanently delete all pending jobs from the queue.\n\nAre you sure you want to continue?');
    if (!confirmed) return;

    await this.executeButtonAction('queue-purge-btn', async () => {
      console.log('🗑️ Purging job queue...');
      if (!this.apiClient || !this.apiClient.triggerQueuePurge) {
        console.warn('⚠️ API client not available, using mock queue purge result');
        return {
          successHTML: `
            <div class="quick-action__icon">✅</div>
            <div class="quick-action__title">Queue Purged (Mock)</div>
            <div class="quick-action__description">0 jobs removed (simulation)</div>
          `
        };
      }
      const result = await this.apiClient.triggerQueuePurge();
      console.log('✅ Queue purge completed:', result);
      
      return {
        successHTML: `
          <div class="quick-action__icon">✅</div>
          <div class="quick-action__title">Queue Purged</div>
          <div class="quick-action__description">${result.jobs_deleted} jobs removed</div>
        `
      };
    }, 'Purging...', 'Clearing queue');
  }

  async toggleMaintenance() {
    await this.executeButtonAction('maintenance-toggle-btn', async () => {
      console.log('🔧 Toggling maintenance mode...');
      if (!this.apiClient || !this.apiClient.toggleMaintenanceMode) {
        console.warn('⚠️ API client not available, using mock maintenance toggle result');
        return {
          successHTML: `
            <div class="quick-action__icon">🔧</div>
            <div class="quick-action__title">Maintenance ON (Mock)</div>
            <div class="quick-action__description">Simulation mode</div>
          `
        };
      }
      const result = await this.apiClient.toggleMaintenanceMode();
      console.log('✅ Maintenance toggle completed:', result);
      
      const icon = result.maintenance_mode ? '🔧' : '✅';
      const title = result.maintenance_mode ? 'Maintenance ON' : 'Maintenance OFF';
      const description = result.maintenance_mode ? 'New jobs blocked' : 'System accepting jobs';
      
      return {
        successHTML: `
          <div class="quick-action__icon">${icon}</div>
          <div class="quick-action__title">${title}</div>
          <div class="quick-action__description">${description}</div>
        `
      };
    }, 'Toggling...', 'Updating maintenance mode');
  }

  async restartFailedJobs() {
    await this.executeButtonAction('restart-failed-btn', async () => {
      console.log('🔄 Restarting failed jobs...');
      
      // Add activity event for restart operation
      if (this.addActivityCallback) {
        this.addActivityCallback({
          icon: '🔄',
          message: 'Restarting failed jobs',
          description: 'Scanning for failed jobs and attempting restart'
        });
      }
      
      if (!this.apiClient || !this.apiClient.restartFailedJobs) {
        console.warn('⚠️ API client not available, using mock restart result');
        return {
          successHTML: `
            <div class="quick-action__icon">✅</div>
            <div class="quick-action__title">Restart Complete (Mock)</div>
            <div class="quick-action__description">0 jobs restarted (simulation)</div>
          `
        };
      }
      const result = await this.apiClient.restartFailedJobs();
      console.log('✅ Restart failed jobs completed:', result);
      
      // Add completion activity event
      if (this.addActivityCallback) {
        this.addActivityCallback({
          icon: result.successful_restarts > 0 ? '✅' : 'ℹ️',
          message: `Restart operation completed`,
          description: `${result.successful_restarts} jobs restarted, ${result.jobs_checked || 0} jobs checked`
        });
      }
      
      return {
        successHTML: `
          <div class="quick-action__icon">✅</div>
          <div class="quick-action__title">Restart Complete</div>
          <div class="quick-action__description">${result.successful_restarts} jobs restarted</div>
        `
      };
    }, 'Restarting...', 'Processing failed jobs');
  }

  async exportDailyReport() {
    await this.executeButtonAction('export-report-btn', async () => {
      console.log('📊 Generating daily report...');
      
      // Add activity event for report generation
      if (this.addActivityCallback) {
        this.addActivityCallback({
          icon: '📊',
          message: 'Daily report generation started',
          description: 'Collecting system data and analytics'
        });
      }
      
      if (!this.apiClient || !this.apiClient.exportDailyReport) {
        console.warn('⚠️ API client not available, using mock export result');
        return {
          successHTML: `
            <div class="quick-action__icon">✅</div>
            <div class="quick-action__title">Downloaded! (Mock)</div>
            <div class="quick-action__description">mock-report.json</div>
          `,
          resetDelay: 5000
        };
      }
      const result = await this.apiClient.exportDailyReport();
      console.log('✅ Daily report generated:', result);
      
      setTimeout(() => {
        this.downloadReportFile(result);
        console.log('📋 Daily Report Downloaded:', result.report_filename);
        console.log('📊 Report contains:', result.sections_included);
        
        // Add download completion activity event
        if (this.addActivityCallback) {
          this.addActivityCallback({
            icon: '📥',
            message: `Report downloaded: ${result.report_filename}`,
            description: `Includes: ${result.sections_included.join(', ')}`
          });
        }
      }, 800);
      
      return {
        successHTML: `
          <div class="quick-action__icon">✅</div>
          <div class="quick-action__title">Downloaded!</div>
          <div class="quick-action__description">${result.report_filename}</div>
        `,
        resetDelay: 5000
      };
    }, 'Generating...', 'Creating daily report');
  }

  async refreshDashboard() {
    await this.executeButtonAction('refresh-dashboard-btn', async () => {
      console.log('🔄 Refreshing dashboard data...');
      
      // Add activity event for refresh
      if (this.addActivityCallback) {
        this.addActivityCallback({
          icon: '🔄',
          message: 'Dashboard data refresh initiated',
          description: 'Updating system metrics and activity feed'
        });
      }
      
      await this.loadDataCallback();
      console.log('✅ Dashboard data refreshed');
      
      return {
        successHTML: `
          <div class="quick-action__icon">✅</div>
          <div class="quick-action__title">Data Refreshed</div>
          <div class="quick-action__description">All metrics updated</div>
        `,
        resetDelay: 2000
      };
    }, 'Refreshing...', 'Updating all data');
  }

  navigateToLogs() {
    console.log('📜 Navigating to logs view...');
    // Navigate to logs view
    window.location.hash = 'logs';
    
    // Update the button temporarily to show action
    const button = document.getElementById('view-logs-btn');
    if (button) {
      const originalHTML = button.innerHTML;
      button.innerHTML = `
        <div class="quick-action__icon">📜</div>
        <div class="quick-action__title">Opening Logs</div>
        <div class="quick-action__description">Navigating to logs view</div>
      `;
      
      setTimeout(() => {
        button.innerHTML = originalHTML;
      }, 1500);
    }
  }

  downloadReportFile(reportData) {
    try {
      const downloadData = {
        report_metadata: {
          ...reportData.report_data.report_metadata,
          download_timestamp: new Date().toISOString(),
          file_format: "JSON",
          generated_by: "AgentOS Admin Dashboard"
        },
        report_content: reportData.report_data
      };

      const jsonString = JSON.stringify(downloadData, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      const downloadUrl = window.URL.createObjectURL(blob);
      
      const downloadLink = document.createElement('a');
      downloadLink.href = downloadUrl;
      downloadLink.download = reportData.report_filename;
      downloadLink.style.display = 'none';
      
      document.body.appendChild(downloadLink);
      downloadLink.click();
      
      document.body.removeChild(downloadLink);
      window.URL.revokeObjectURL(downloadUrl);
      
      console.log(`✅ Report downloaded: ${reportData.report_filename}`);
      console.log(`📊 File size: ${(blob.size / 1024).toFixed(2)} KB`);
      
    } catch (error) {
      console.error('❌ Download failed:', error);
      throw error;
    }
  }
}