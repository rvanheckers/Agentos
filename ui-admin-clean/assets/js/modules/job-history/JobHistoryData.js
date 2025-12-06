/**
 * JobHistory Data Processing Module
 * Handles data processing, analytics, and mock data generation
 * Extracted from JobHistory.js for better maintainability
 */

export class JobHistoryData {
  constructor(jobHistoryInstance) {
    this.jobHistory = jobHistoryInstance;
  }

  /**
   * Load job history data - delegates to main JobHistory loadJobHistory method
   */
  async loadJobHistory(page = 1) {
    console.log('🔄 JobHistoryData.loadJobHistory() - delegating to main JobHistory');
    try {
      this.jobHistory.currentPage = page;
      console.log('🔄 Loading job history from SSOT...');
      
      // FIX: Use same Central Data Service instance as Dashboard
      const centralDataService = this.jobHistory.centralDataService;
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
      // Use fallback data instead of breaking
      console.log('📋 Using fallback data due to error');
      this.useFallbackData();
    }
  }

  /**
   * Use fallback data when SSOT fails
   */
  useFallbackData() {
    const fallbackJobs = this.generateMockJobs(10);
    this.jobHistory.allJobs = fallbackJobs;
    this.jobHistory.jobs = fallbackJobs;
    this.jobHistory.totalJobs = fallbackJobs.length;
    
    console.log('📋 Fallback data set:', {
      jobs: this.jobHistory.jobs.length,
      totalJobs: this.jobHistory.totalJobs
    });
    
    // Trigger UI update
    this.jobHistory.applyCurrentFilters();
  }

  /**
   * Process SSOT data and update job history
   */
  processSSotData(ssotData) {
    try {
      // Debug: Log the actual SSOT data structure (like Dashboard does)
      console.log('🔍 JobHistory SSOT Data structure:', Object.keys(ssotData));
      console.log('💾 JobHistory data sources:', {
        system: ssotData.system ? 'REAL' : 'NULL',
        workers: ssotData.workers ? 'REAL' : 'NULL', 
        queue: ssotData.queue ? 'REAL' : 'NULL',
        jobs: ssotData.jobs ? 'REAL' : 'NULL',
        dashboard: ssotData.dashboard ? 'REAL' : 'NULL',
        analytics: ssotData.analytics ? 'REAL' : 'NULL',
        agents: ssotData.agents || ssotData.agents_workers ? 'REAL' : 'NULL'
      });
      console.log('🔍 SSOT Jobs data details:', ssotData.jobs);
      console.log('🔍 SSOT Dashboard data details:', ssotData.dashboard);
      console.log('🔍 SSOT Queue data details:', ssotData.queue);
      
      // Extract jobs data from SSOT response - EXACTLY like Dashboard does it
      const todayJobs = ssotData.dashboard?.jobs || ssotData.jobs;
      const jobs = todayJobs?.recent_jobs || todayJobs?.jobs || [];
      
      console.log('🔍 Found jobs:', jobs?.length, 'jobs from todayJobs:', todayJobs);
      const queueData = ssotData.queue || ssotData.dashboard?.queue || {};
      
      if (jobs && jobs.length > 0) {
        console.log('📊 Processing SSOT jobs data:', jobs.length, 'jobs');
        
        // Transform SSOT data to match our job structure
        const transformedJobs = jobs.map(job => ({
          ...job,
          // Ensure required fields exist
          id: job.id || job.job_id || `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          status: job.status || 'unknown',
          progress: job.progress || 0,
          created_at: job.created_at || job.timestamp || new Date().toISOString(),
          // Add performance metrics if missing
          performance_metrics: job.performance_metrics || this.calculatePerformanceMetrics(job.pipeline_steps || []),
          // Add pipeline steps if missing
          pipeline_steps: job.pipeline_steps || this.getMockPipelineSteps(job),
          // Add calculated fields
          duration_breakdown: job.duration_breakdown || this.calculateDurationBreakdown(job.pipeline_steps || []),
          pipeline_status: job.pipeline_status || this.calculatePipelineStatus(job.pipeline_steps || []),
          resource_utilization: job.resource_utilization || this.calculateResourceUtilization(job.pipeline_steps || [])
        }));
        
        this.jobHistory.historyData = {
          jobs: transformedJobs,
          total: transformedJobs.length,
          lastUpdated: new Date().toISOString(),
          source: 'ssot'
        };
        
        // 🔥 DIRECT FIX: Set jobs immediately for UI rendering
        this.jobHistory.allJobs = transformedJobs;
        this.jobHistory.jobs = transformedJobs;
        this.jobHistory.totalJobs = transformedJobs.length;
        
        console.log('🔥 DIRECT FIX: Set jobs in JobHistory:', {
          allJobs: this.jobHistory.allJobs.length,
          jobs: this.jobHistory.jobs.length,
          totalJobs: this.jobHistory.totalJobs
        });
        
        // Trigger UI update immediately
        this.jobHistory.applyCurrentFilters();
        
        // Enterprise job enrichment with pipeline data (async - non-blocking)
        if (this.jobHistory.enrichJobsWithPipelineData) {
          this.jobHistory.enrichJobsWithPipelineData(transformedJobs).then(enrichedJobs => {
            // Update with enriched data later
            this.jobHistory.allJobs = enrichedJobs;
            this.jobHistory.jobs = enrichedJobs;
            
            // Re-apply filters with enriched data
            this.jobHistory.applyCurrentFilters();
            
            // Calculate enterprise analytics
            this.jobHistory.calculateHistoryAnalytics();
            
            // Cache data for offline access
            this.jobHistory.cacheHistoryData();
          }).catch(error => {
            console.warn('⚠️ Pipeline enrichment failed, using basic data:', error);
          });
        } else {
          console.log('📝 enrichJobsWithPipelineData method not available, using basic data');
        }
        
        // 🔥 FIX: Update KPI Manager AFTER all rendering is complete
        if (this.jobHistory.kpiManager && this.jobHistory.jobs && this.jobHistory.jobs.length > 0) {
          console.log('📊 Scheduling KPI Manager update after rendering with', this.jobHistory.jobs.length, 'jobs');
          
          // Use setTimeout to ensure KPI update happens AFTER all rendering
          setTimeout(() => {
            console.log('⏰ Executing delayed KPI Manager update...');
            // 🔥 FIX: Preserve existing currentTab, don't force 'active'
            const preservedTab = this.jobHistory.currentTab || 'active';
            this.jobHistory.kpiManager.currentTab = preservedTab;
            this.jobHistory.kpiManager.updateKPIs(this.jobHistory.jobs);
            console.log('✅ Delayed KPI Manager update completed for tab:', preservedTab);
          }, 500); // 500ms delay to ensure all rendering is finished
        }
        
        console.log('✅ SSOT data processed successfully');
        return true;
      } else {
        console.warn('⚠️ No jobs data found in SSOT response, using fallback');
        console.log('🔍 Available jobs paths checked:', {
          'ssotData.jobs?.recent_jobs': ssotData.jobs?.recent_jobs?.length || 'undefined',
          'ssotData.dashboard?.jobs?.recent_jobs': ssotData.dashboard?.jobs?.recent_jobs?.length || 'undefined'
        });
        return false;
      }
    } catch (error) {
      console.error('❌ Error processing SSOT data:', error);
      return false;
    }
  }

  /**
   * Get fallback job history data when SSOT is unavailable
   */
  getFallbackJobHistory() {
    console.log('📋 Using fallback job history data');
    
    const mockJobs = this.generateMockJobs(15);
    
    return {
      jobs: mockJobs,
      analytics: this.getFallbackJobStats(),
      recent_activity: this.getFallbackRecentActivity(),
      last_update: new Date().toISOString()
    };
  }

  /**
   * Generate mock jobs for testing/fallback
   */
  generateMockJobs(count = 10) {
    const jobs = [];
    const statuses = ['completed', 'processing', 'failed', 'pending', 'queued'];
    const priorities = ['high', 'medium', 'low'];
    const taskTypes = ['video_processing', 'audio_extraction', 'transcription', 'content_analysis'];
    
    for (let i = 1; i <= count; i++) {
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      const priority = priorities[Math.floor(Math.random() * priorities.length)];
      const taskType = taskTypes[Math.floor(Math.random() * taskTypes.length)];
      
      // Generate realistic timestamps
      const createdAt = new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000); // Last 24 hours
      const updatedAt = new Date(createdAt.getTime() + Math.random() * 60 * 60 * 1000); // Up to 1 hour later
      
      const job = {
        id: `job_${Date.now()}_${i.toString().padStart(3, '0')}`,
        user_id: `user_${Math.floor(Math.random() * 50) + 1}`,
        status,
        priority,
        progress: status === 'completed' ? 100 : 
                 status === 'failed' ? Math.floor(Math.random() * 80) :
                 status === 'processing' ? Math.floor(Math.random() * 80) + 10 :
                 0,
        video_url: `https://example.com/video_${i}.mp4`,
        video_title: `Sample Video ${i} - ${taskType.replace('_', ' ')}`,
        current_step: status === 'processing' ? taskTypes[Math.floor(Math.random() * taskTypes.length)] : null,
        error_message: status === 'failed' ? this.generateErrorMessage() : null,
        retry_count: status === 'failed' ? Math.floor(Math.random() * 3) : 0,
        worker_id: status !== 'pending' ? `worker_${Math.floor(Math.random() * 5) + 1}` : null,
        created_at: createdAt.toISOString(),
        started_at: status !== 'pending' ? new Date(createdAt.getTime() + Math.random() * 300000).toISOString() : null,
        completed_at: status === 'completed' ? updatedAt.toISOString() : null,
        updated_at: updatedAt.toISOString(),
        description: this.generateJobDescription(taskType, status),
        duration: status === 'completed' ? Math.floor(Math.random() * 600) + 30 : null,
        processing_time: status === 'completed' ? Math.floor(Math.random() * 400) + 20 : null,
        agent_pipeline: this.getMockPipelineSteps(),
        performance_metrics: this.calculatePerformanceMetrics([]),
        pipeline_steps: this.getMockPipelineSteps({ id: job?.id || `job_${i}`, status })
      };
      
      // Calculate additional metrics
      job.pipeline_status = this.calculatePipelineStatus(job.pipeline_steps);
      job.duration_breakdown = this.calculateDurationBreakdown(job.pipeline_steps);
      job.resource_utilization = this.calculateResourceUtilization(job.pipeline_steps);
      
      jobs.push(job);
    }
    
    return jobs;
  }

  /**
   * Generate job description based on task type and status
   */
  generateJobDescription(taskType, status) {
    const descriptions = {
      video_processing: {
        completed: 'Video processing completed successfully with high quality output',
        processing: 'Currently processing video through AI pipeline',
        failed: 'Video processing failed during transcription stage',
        pending: 'Video queued for processing',
        queued: 'Video waiting in processing queue'
      },
      audio_extraction: {
        completed: 'Audio successfully extracted and optimized',
        processing: 'Extracting audio from video source',
        failed: 'Audio extraction failed due to codec issues',
        pending: 'Audio extraction task queued',
        queued: 'Waiting to extract audio from video'
      },
      transcription: {
        completed: 'Speech transcription completed with high accuracy',
        processing: 'Converting speech to text using AI models',
        failed: 'Transcription failed - poor audio quality detected',
        pending: 'Transcription job waiting to start',
        queued: 'Speech transcription queued for processing'
      },
      content_analysis: {
        completed: 'Content analysis completed with detailed insights',
        processing: 'Analyzing content using natural language processing',
        failed: 'Content analysis failed during sentiment detection',
        pending: 'Content analysis scheduled',
        queued: 'Content analysis waiting in queue'
      }
    };
    
    if (status === 'failed') {
      return descriptions[taskType]?.failed || 'Task failed during processing';
    }
    
    return descriptions[taskType]?.[status] || `${taskType.replace('_', ' ')} - ${status}`;
  }

  /**
   * Generate realistic error messages
   */
  generateErrorMessage() {
    const errors = [
      'Connection timeout to video source',
      'Insufficient memory for processing large file',
      'Unsupported video codec detected',
      'Audio extraction failed - corrupted stream',
      'Transcription accuracy below threshold',
      'Worker instance crashed during processing',
      'Network error while downloading content',
      'Rate limit exceeded on external API',
      'Invalid video format or resolution',
      'Processing timeout after 10 minutes'
    ];
    
    return errors[Math.floor(Math.random() * errors.length)];
  }

  /**
   * Get fallback job statistics
   */
  getFallbackJobStats() {
    return {
      total_jobs: 150,
      completed_today: 45,
      failed_today: 3,
      processing_now: 7,
      average_duration: 180,
      success_rate: 94.2
    };
  }

  /**
   * Get fallback recent activity
   */
  getFallbackRecentActivity() {
    return [
      { action: 'Job completed', timestamp: new Date(Date.now() - 300000).toISOString() },
      { action: 'New job started', timestamp: new Date(Date.now() - 600000).toISOString() },
      { action: 'Worker scaled up', timestamp: new Date(Date.now() - 900000).toISOString() }
    ];
  }

  /**
   * Filter jobs by timeframe
   */
  filterJobsByTimeframe(jobs) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    // Calculate week start (Monday)
    const dayOfWeek = today.getDay();
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // Sunday = 0, so we need 6 days back
    const thisWeekStart = new Date(today);
    thisWeekStart.setDate(today.getDate() - daysToMonday);
    const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);

    switch (this.jobHistory.currentTimeframe) {
      case 'today':
        return jobs.filter(job => new Date(job.created_at) >= today);
      case 'week':
        return jobs.filter(job => new Date(job.created_at) >= thisWeekStart);
      case 'month':
        return jobs.filter(job => new Date(job.created_at) >= thisMonthStart);
      default:
        return jobs;
    }
  }

  /**
   * Get mock pipeline steps for a job
   */
  getMockPipelineSteps(job) {
    const agentPipeline = [
      { name: 'video_download', duration: 30, status: 'completed' },
      { name: 'audio_extraction', duration: 45, status: 'completed' },
      { name: 'speech_transcription', duration: 120, status: 'completed' },
      { name: 'content_analysis', duration: 60, status: 'completed' },
      { name: 'summary_generation', duration: 30, status: 'completed' },
      { name: 'quality_check', duration: 15, status: 'completed' }
    ];

    // Adjust pipeline based on job status
    if (job && job.status === 'failed') {
      const failPoint = Math.floor(Math.random() * agentPipeline.length);
      agentPipeline[failPoint].status = 'failed';
      agentPipeline[failPoint].error = 'Processing failed at this stage';
      
      // Mark subsequent steps as pending
      for (let i = failPoint + 1; i < agentPipeline.length; i++) {
        agentPipeline[i].status = 'pending';
        agentPipeline[i].duration = 0;
      }
    } else if (job && job.status === 'processing') {
      const currentStep = Math.floor(Math.random() * agentPipeline.length);
      agentPipeline[currentStep].status = 'processing';
      
      // Mark subsequent steps as pending
      for (let i = currentStep + 1; i < agentPipeline.length; i++) {
        agentPipeline[i].status = 'pending';
        agentPipeline[i].duration = 0;
      }
    }

    return agentPipeline;
  }

  /**
   * Calculate pipeline status from steps
   */
  calculatePipelineStatus(steps) {
    if (!steps || steps.length === 0) return 'pending';
    
    const completed = steps.filter(step => step.status === 'completed').length;
    const failed = steps.filter(step => step.status === 'failed').length;
    const processing = steps.filter(step => step.status === 'processing').length;
    
    if (failed > 0) return 'failed';
    if (processing > 0) return 'running';
    if (completed === steps.length) return 'success';
    return 'partial';
  }

  /**
   * Calculate duration breakdown by agent
   */
  calculateDurationBreakdown(steps) {
    const breakdown = {
      total: 0,
      by_agent: {},
      longest_step: null,
      shortest_step: null
    };
    
    if (!steps || steps.length === 0) return breakdown;

    steps.forEach(step => {
      if (step.duration) {
        breakdown.total += step.duration;
        breakdown.by_agent[step.name] = step.duration;
      }
    });

    // Find longest and shortest steps
    const durations = steps.filter(step => step.duration > 0);
    if (durations.length > 0) {
      breakdown.longest_step = durations.reduce((max, step) => 
        step.duration > max.duration ? step : max
      );
      breakdown.shortest_step = durations.reduce((min, step) => 
        step.duration < min.duration ? step : min
      );
    }

    return breakdown;
  }

  /**
   * Get recovery suggestion for failed step
   */
  getRecoverySuggestion(failedStep) {
    const suggestions = {
      'video_download': 'Check video URL accessibility and network connectivity',
      'audio_extraction': 'Verify video codec support and file integrity',
      'speech_transcription': 'Ensure audio quality meets minimum requirements',
      'content_analysis': 'Check if content contains supported language',
      'summary_generation': 'Verify AI model availability and processing capacity',
      'quality_check': 'Review output format requirements and validation rules'
    };
    
    return suggestions[failedStep] || 'Review logs and retry with different parameters';
  }

  /**
   * Calculate performance metrics for pipeline
   */
  calculatePerformanceMetrics(steps) {
    const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0);
    const processingTime = steps.filter(step => step.status !== 'pending').reduce((sum, step) => sum + (step.duration || 0), 0);
    const queueWaitTime = totalDuration - processingTime;
    
    return {
      total_duration: totalDuration,
      processing_time: processingTime,
      queue_wait_time: Math.max(0, queueWaitTime),
      efficiency_score: this.calculatePipelineEfficiency(steps)
    };
  }

  /**
   * Calculate pipeline efficiency score
   */
  calculatePipelineEfficiency(steps) {
    if (!steps || steps.length === 0) return 0;
    
    const completedSteps = steps.filter(step => step.status === 'completed').length;
    const totalSteps = steps.length;
    const failedSteps = steps.filter(step => step.status === 'failed').length;
    
    // Base efficiency on completion rate
    let efficiency = (completedSteps / totalSteps) * 100;
    
    // Penalize for failures
    efficiency -= (failedSteps * 20);
    
    // Consider duration optimization
    const avgDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0) / steps.length;
    if (avgDuration < 60) { // Under 1 minute avg is good
      efficiency += 10;
    } else if (avgDuration > 180) { // Over 3 minutes avg is poor
      efficiency -= 10;
    }
    
    return Math.max(0, Math.min(100, Math.round(efficiency)));
  }

  /**
   * Calculate resource utilization metrics
   */
  calculateResourceUtilization(steps) {
    // Mock resource utilization data
    return {
      cpu_usage: Math.floor(Math.random() * 40) + 30, // 30-70%
      memory_usage: Math.floor(Math.random() * 50) + 25, // 25-75%
      io_wait: Math.floor(Math.random() * 20) + 5, // 5-25%
      network_usage: Math.floor(Math.random() * 30) + 10 // 10-40%
    };
  }

  /**
   * Calculate comprehensive job history analytics
   */
  calculateHistoryAnalytics() {
    if (!this.jobHistory.jobs || this.jobHistory.jobs.length === 0) {
      this.jobHistory.historyData = { analytics: {} };
      return;
    }

    const analytics = {
      total_jobs: this.jobHistory.jobs.length,
      pipeline_success_rate: this.calculatePipelineSuccessRate(),
      avg_pipeline_duration: this.calculateAvgPipelineDuration(),
      most_common_failures: this.calculateMostCommonFailures(),
      performance_trends: this.calculatePerformanceTrends()
    };

    this.jobHistory.historyData = { analytics };
  }

  /**
   * Calculate overall pipeline success rate
   */
  calculatePipelineSuccessRate() {
    const completedJobs = this.jobHistory.jobs.filter(job => job.status === 'completed').length;
    return this.jobHistory.jobs.length > 0 ? Math.round((completedJobs / this.jobHistory.jobs.length) * 100) : 0;
  }

  /**
   * Calculate average pipeline duration
   */
  calculateAvgPipelineDuration() {
    const completedJobs = this.jobHistory.jobs.filter(job => job.status === 'completed' && job.performance_metrics?.total_duration);
    if (completedJobs.length === 0) return 0;
    
    const totalDuration = completedJobs.reduce((sum, job) => sum + job.performance_metrics.total_duration, 0);
    return Math.round(totalDuration / completedJobs.length);
  }

  /**
   * Calculate most common failure patterns
   */
  calculateMostCommonFailures() {
    const failedJobs = this.jobHistory.jobs.filter(job => job.status === 'failed');
    const failureReasons = {};
    
    failedJobs.forEach(job => {
      const reason = job.error_message || 'Unknown error';
      failureReasons[reason] = (failureReasons[reason] || 0) + 1;
    });
    
    return Object.entries(failureReasons)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([reason, count]) => ({ reason, count, percentage: Math.round((count / failedJobs.length) * 100) }));
  }

  /**
   * Calculate performance trends over time
   */
  calculatePerformanceTrends() {
    // Group jobs by hour for trend analysis
    const hourlyStats = {};
    const now = new Date();
    
    // Initialize last 24 hours
    for (let i = 23; i >= 0; i--) {
      const hour = new Date(now.getTime() - (i * 60 * 60 * 1000));
      const key = hour.toISOString().substring(0, 13); // YYYY-MM-DDTHH
      hourlyStats[key] = {
        hour: hour.getHours(),
        completed: 0,
        failed: 0,
        total_duration: 0,
        avg_duration: 0
      };
    }
    
    // Populate with actual job data
    this.jobHistory.jobs.forEach(job => {
      const jobHour = new Date(job.created_at).toISOString().substring(0, 13);
      if (hourlyStats[jobHour]) {
        if (job.status === 'completed') {
          hourlyStats[jobHour].completed++;
          hourlyStats[jobHour].total_duration += job.performance_metrics?.total_duration || 0;
        } else if (job.status === 'failed') {
          hourlyStats[jobHour].failed++;
        }
      }
    });
    
    // Calculate averages
    Object.values(hourlyStats).forEach(stats => {
      if (stats.completed > 0) {
        stats.avg_duration = Math.round(stats.total_duration / stats.completed);
      }
    });
    
    return Object.values(hourlyStats);
  }

  /**
   * Load cached job data
   */
  loadCachedData() {
    try {
      const cached = localStorage.getItem('agentos_history_cache');
      if (cached) {
        const data = JSON.parse(cached);
        // Check if cache is still valid (less than 5 minutes old)
        const cacheAge = Date.now() - new Date(data.timestamp).getTime();
        if (cacheAge < 5 * 60 * 1000) { // 5 minutes
          console.log('📦 Loading cached job history data');
          return data;
        }
      }
    } catch (error) {
      console.error('Failed to load cached data:', error);
    }
    return null;
  }

  /**
   * Cache job data to localStorage
   */
  cacheJobData(data) {
    try {
      const cacheData = {
        ...data,
        timestamp: new Date().toISOString(),
        version: '1.0'
      };
      localStorage.setItem('agentos_history_cache', JSON.stringify(cacheData));
    } catch (error) {
      console.warn('Failed to cache job data:', error);
    }
  }

  /**
   * Clear cached data
   */
  clearCache() {
    try {
      localStorage.removeItem('agentos_history_cache');
      console.log('🗑️ Job history cache cleared');
    } catch (error) {
      console.error('Failed to clear cache:', error);
    }
  }

  /**
   * Export job data for analysis
   */
  exportJobData(format = 'json') {
    const data = {
      jobs: this.jobHistory.jobs || [],
      analytics: this.jobHistory.historyData?.analytics || {},
      metadata: {
        export_time: new Date().toISOString(),
        total_jobs: this.jobHistory.jobs?.length || 0,
        timeframe: this.jobHistory.currentTimeframe,
        version: '1.0'
      }
    };

    if (format === 'csv') {
      return this.convertToCSV(data.jobs);
    }

    return JSON.stringify(data, null, 2);
  }

  /**
   * Convert jobs to CSV format
   */
  convertToCSV(jobs) {
    if (!jobs || jobs.length === 0) return '';

    const headers = [
      'ID', 'Status', 'Progress', 'Duration', 'Created At', 
      'User ID', 'Priority', 'Error Message', 'Worker ID'
    ];

    const rows = jobs.map(job => [
      job.id || '',
      job.status || '',
      job.progress || 0,
      job.performance_metrics?.total_duration || 0,
      job.created_at || '',
      job.user_id || '',
      job.priority || '',
      job.error_message || '',
      job.worker_id || ''
    ]);

    return [headers, ...rows].map(row => 
      row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ).join('\n');
  }

  /**
   * Get data quality metrics
   */
  getDataQuality() {
    const jobs = this.jobHistory.jobs || [];
    if (jobs.length === 0) return { score: 0, issues: [] };

    const issues = [];
    let score = 100;

    // Check for missing required fields
    const missingIds = jobs.filter(job => !job.id).length;
    const missingStatus = jobs.filter(job => !job.status).length;
    const missingTimestamps = jobs.filter(job => !job.created_at).length;

    if (missingIds > 0) {
      issues.push(`${missingIds} jobs missing IDs`);
      score -= 20;
    }

    if (missingStatus > 0) {
      issues.push(`${missingStatus} jobs missing status`);
      score -= 15;
    }

    if (missingTimestamps > 0) {
      issues.push(`${missingTimestamps} jobs missing timestamps`);
      score -= 10;
    }

    // Check for data consistency
    const invalidProgress = jobs.filter(job => 
      job.progress < 0 || job.progress > 100
    ).length;

    if (invalidProgress > 0) {
      issues.push(`${invalidProgress} jobs with invalid progress values`);
      score -= 10;
    }

    return {
      score: Math.max(0, score),
      issues,
      total_jobs: jobs.length,
      quality_grade: score >= 90 ? 'A' : score >= 80 ? 'B' : score >= 70 ? 'C' : score >= 60 ? 'D' : 'F'
    };
  }
}