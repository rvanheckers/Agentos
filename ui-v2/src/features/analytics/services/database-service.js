/**
 * Database Service
 * Handles new database endpoints for job history and analytics
 */

import { APIClient } from '../../../adapters/api/api-client.js';

export class DatabaseService {
  constructor(apiClient = null) {
    this.apiClient = apiClient || new APIClient();
  }

  /**
   * Get job history from database
   */
  async getJobHistory(options = {}) {
    try {
      const params = new URLSearchParams();
      
      if (options.userId) {
        params.append('user_id', options.userId);
      }
      
      if (options.limit) {
        params.append('limit', options.limit);
      }
      
      if (options.offset) {
        params.append('offset', options.offset);
      }

      const url = `${this.apiClient.baseUrl}/api/jobs/history${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to get job history: ${response.status}`);
      }

      const data = await response.json();
      
      console.log('📚 Job history retrieved:', data.total_jobs, 'jobs');
      
      return {
        success: true,
        jobs: data.jobs,
        totalJobs: data.total_jobs,
        successRate: data.success_rate,
        avgProcessingTime: data.avg_processing_time
      };

    } catch (error) {
      console.error('❌ Failed to get job history:', error);
      return {
        success: false,
        error: error.message,
        jobs: [],
        totalJobs: 0
      };
    }
  }

  /**
   * Get analytics statistics from database
   */
  async getAnalyticsStats(timeframe = '7d') {
    try {
      const url = `${this.apiClient.baseUrl}/api/resources/analytics?timeframe=${timeframe}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to get analytics stats: ${response.status}`);
      }

      const data = await response.json();
      
      console.log('📊 Analytics stats retrieved:', data);
      
      return {
        success: true,
        stats: data,
        summary: data
      };

    } catch (error) {
      console.error('❌ Failed to get analytics stats:', error);
      return {
        success: false,
        error: error.message,
        stats: {},
        summary: {}
      };
    }
  }

  /**
   * Get detailed job information with processing steps
   */
  async getJobDetails(jobId) {
    try {
      const url = `${this.apiClient.baseUrl}/api/jobs/${jobId}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        if (response.status === 404) {
          return {
            success: false,
            error: 'Job not found',
            job: null
          };
        }
        throw new Error(`Failed to get job details: ${response.status}`);
      }

      const data = await response.json();
      
      console.log('🔍 Job details retrieved:', jobId);
      
      return {
        success: true,
        job: data.job,
        dataSource: data.data_source
      };

    } catch (error) {
      console.error('❌ Failed to get job details:', error);
      return {
        success: false,
        error: error.message,
        job: null
      };
    }
  }

  /**
   * Check database health
   */
  async checkDatabaseHealth() {
    try {
      const url = `${this.apiClient.baseUrl}/api/database/health`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Database health check failed: ${response.status}`);
      }

      const data = await response.json();
      
      console.log('💚 Database health check:', data.database_status);
      
      return {
        success: data.success,
        status: data.database_status,
        connection: data.connection,
        tablesAccessible: data.tables_accessible,
        quickStats: data.quick_stats || {}
      };

    } catch (error) {
      console.error('❌ Database health check failed:', error);
      return {
        success: false,
        status: 'unhealthy',
        connection: 'failed',
        error: error.message
      };
    }
  }

  /**
   * Format job for display
   */
  formatJobForDisplay(job) {
    return {
      id: job.id,
      shortId: job.id.substring(0, 8),
      userId: job.user_id,
      videoTitle: job.video_title || 'Untitled',
      videoUrl: job.video_url,
      status: job.status,
      statusEmoji: this.getStatusEmoji(job.status),
      progress: job.progress,
      createdAt: new Date(job.created_at),
      startedAt: job.started_at ? new Date(job.started_at) : null,
      completedAt: job.completed_at ? new Date(job.completed_at) : null,
      duration: this.calculateDuration(job.started_at, job.completed_at),
      clipsCount: job.clips_count || 0,
      errorMessage: job.error_message
    };
  }

  /**
   * Get status emoji for job status
   */
  getStatusEmoji(status) {
    const statusMap = {
      'queued': '⏳',
      'processing': '🔄',
      'completed': '✅',
      'failed': '❌',
      'cancelled': '🚫'
    };
    return statusMap[status] || '❓';
  }

  /**
   * Calculate duration between two timestamps
   */
  calculateDuration(startTime, endTime) {
    if (!startTime || !endTime) return null;
    
    const start = new Date(startTime);
    const end = new Date(endTime);
    const duration = (end - start) / 1000; // seconds
    
    if (duration < 60) {
      return `${Math.round(duration)}s`;
    } else if (duration < 3600) {
      return `${Math.round(duration / 60)}m`;
    } else {
      return `${Math.round(duration / 3600)}h`;
    }
  }

  /**
   * Format analytics data for display
   */
  formatAnalyticsData(stats) {
    return {
      totalJobs: stats.total_jobs || 0,
      completedJobs: stats.completed_jobs || 0,
      processingJobs: stats.processing_jobs || 0,
      queuedJobs: stats.queued_jobs || 0,
      failedJobs: stats.failed_jobs || 0,
      totalClips: stats.total_clips || 0,
      successRate: Math.round((stats.success_rate || 0) * 10) / 10,
      successRateFormatted: `${Math.round((stats.success_rate || 0) * 10) / 10}%`,
      avgProcessingTime: stats.avg_processing_time || 120,
      jobsLast24h: stats.jobs_last_24h || 0,
      peakHour: stats.peak_hour || '14:00',
      performanceScore: stats.performance_score || 0,
      timeframe: stats.timeframe || '7d',
      generatedAt: new Date()
    };
  }

  /**
   * Get dashboard summary data
   */
  async getDashboardSummary() {
    try {
      const [healthCheck, analytics, recentJobs] = await Promise.all([
        this.checkDatabaseHealth(),
        this.getAnalyticsStats('24h'),
        this.getJobHistory({ limit: 5 })
      ]);

      return {
        success: true,
        database: healthCheck,
        analytics: analytics.success ? this.formatAnalyticsData(analytics.stats) : null,
        recentJobs: recentJobs.success ? recentJobs.jobs.map(job => this.formatJobForDisplay(job)) : [],
        timestamp: new Date()
      };

    } catch (error) {
      console.error('❌ Failed to get dashboard summary:', error);
      return {
        success: false,
        error: error.message,
        database: { success: false },
        analytics: null,
        recentJobs: []
      };
    }
  }
}

export default DatabaseService;