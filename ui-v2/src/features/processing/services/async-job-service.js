/**
 * Async Job Service
 * Handles async video processing jobs using the new queue system
 */

import { APIClient } from '../../../adapters/api/api-client.js';

export class AsyncJobService {
  constructor(apiClient = null) {
    this.apiClient = apiClient || new APIClient();
    this.activeJobs = new Map(); // Track active jobs
    this.jobCallbacks = new Map(); // Store progress callbacks
    this.pollInterval = 2000; // 2 seconds polling
    this.maxPollTime = 300000; // 5 minutes max polling
  }

  /**
   * Submit async video processing job
   */
  async submitJob(videoInput, options = {}) {
    console.log('🚀 Submitting async job:', videoInput);
    console.log('🔍 Job options:', options);
    
    try {
      // Prepare job request - handle multiple input formats
      // videoInput can be: string (URL), object with filePath (from upload), or object with url
      let videoUrl = '';
      if (typeof videoInput === 'string') {
        videoUrl = videoInput;
      } else if (videoInput.filePath) {
        videoUrl = videoInput.filePath;  // From file upload
      } else if (videoInput.url) {
        videoUrl = videoInput.url;  // From URL input
      } else if (videoInput.path) {
        videoUrl = videoInput.path;  // Alternative format
      }
      
      console.log('🎬 Video URL to process:', videoUrl);
      console.log('📦 Video input object:', videoInput);
      console.log('🔍 VideoInput properties:', Object.keys(videoInput || {}));
      console.log('🔍 VideoInput.filePath:', videoInput?.filePath);
      console.log('🔍 VideoInput.path:', videoInput?.path);
      console.log('🔍 VideoInput.url:', videoInput?.url);
      
      const jobRequest = {
        video_url: videoUrl,
        user_id: 'anonymous',  // Use anonymous for now to avoid user lookup
        workflow_type: options.workflowType || 'default',
        intent: options.workflowType || options.intent || 'visual_clips',
        options: {
          priority: options.priority || 'normal',
          ...options
        }
      };

      console.log('📦 Sending job request:', JSON.stringify(jobRequest, null, 2));

      // Submit job to queue
      const response = await fetch(`${this.apiClient.baseUrl}/api/jobs/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(jobRequest)
      });

      if (!response.ok) {
        // Check if queue system is unavailable (503)
        if (response.status === 503) {
          console.warn('⚠️ Queue system not available, falling back to sync processing');
          return this.fallbackToSync(videoInput, options);
        }
        throw new Error(`Job submission failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Job submission failed');
      }

      console.log('✅ Job submitted successfully:', result.job_id);
      
      // Store job info
      this.activeJobs.set(result.job_id, {
        jobId: result.job_id,
        status: 'queued',
        progress: 0,
        submittedAt: new Date(),
        videoInput: videoInput,
        options: options
      });

      return {
        success: true,
        jobId: result.job_id,
        status: result.status,
        message: result.message,
        estimatedCompletion: result.estimated_completion
      };

    } catch (error) {
      console.error('❌ Async job submission failed:', error);
      
      // Try fallback to sync processing
      if (error.message.includes('Queue system not available') || 
          error.message.includes('503')) {
        console.warn('⚠️ Falling back to sync processing');
        return this.fallbackToSync(videoInput, options);
      }
      
      throw error;
    }
  }

  /**
   * Start monitoring job progress
   */
  async monitorJob(jobId, onProgress = null, onComplete = null, onError = null) {
    console.log('👁️ Starting job monitoring:', jobId);
    
    if (onProgress) {
      this.jobCallbacks.set(jobId, { onProgress, onComplete, onError });
    }

    const startTime = Date.now();
    
    const poll = async () => {
      try {
        const status = await this.getJobStatus(jobId);
        
        if (!status) {
          throw new Error('Job not found');
        }

        // Update active job info
        if (this.activeJobs.has(jobId)) {
          const jobInfo = this.activeJobs.get(jobId);
          jobInfo.status = status.status;
          jobInfo.progress = status.progress;
          jobInfo.lastUpdate = new Date();
        }

        // Call progress callback
        if (onProgress) {
          onProgress({
            jobId: jobId,
            status: status.status,
            progress: status.progress,
            message: status.message,
            currentAgent: status.current_agent,
            elapsedTime: Date.now() - startTime
          });
        }

        // Check if job is complete
        if (status.status === 'completed') {
          console.log('✅ Job completed:', jobId);
          
          // Get final results
          const clips = await this.getJobClips(jobId);
          
          if (onComplete) {
            onComplete({
              jobId: jobId,
              clips: clips.clips,
              totalClips: clips.total_clips,
              processingTime: clips.processing_time,
              workerId: clips.worker_id
            });
          }
          
          // Cleanup
          this.jobCallbacks.delete(jobId);
          return;
        }
        
        // Check if job failed
        if (status.status === 'failed') {
          console.error('❌ Job failed:', jobId, status.error_message);
          
          if (onError) {
            onError(new Error(status.error_message || 'Job processing failed'));
          }
          
          // Cleanup
          this.jobCallbacks.delete(jobId);
          return;
        }

        // Continue polling if still processing
        if (status.status === 'processing' || status.status === 'queued') {
          // Check timeout
          if (Date.now() - startTime > this.maxPollTime) {
            throw new Error('Job monitoring timeout');
          }
          
          // Schedule next poll
          setTimeout(poll, this.pollInterval);
        }

      } catch (error) {
        console.error('❌ Job monitoring error:', error);
        
        if (onError) {
          onError(error);
        }
        
        // Cleanup
        this.jobCallbacks.delete(jobId);
      }
    };

    // Start polling
    poll();
  }

  /**
   * Get job status from API
   */
  async getJobStatus(jobId) {
    try {
      const response = await fetch(`${this.apiClient.baseUrl}/api/jobs/${jobId}/status`);
      
      if (!response.ok) {
        if (response.status === 404) {
          return null; // Job not found
        }
        throw new Error(`Failed to get job status: ${response.status}`);
      }

      return await response.json();
      
    } catch (error) {
      console.error(`❌ Failed to get status for job ${jobId}:`, error);
      throw error;
    }
  }

  /**
   * Get job clips (results) from API
   */
  async getJobClips(jobId) {
    try {
      const response = await fetch(`${this.apiClient.baseUrl}/api/jobs/${jobId}/clips`);
      
      if (!response.ok) {
        throw new Error(`Failed to get job clips: ${response.status}`);
      }

      return await response.json();
      
    } catch (error) {
      console.error(`❌ Failed to get clips for job ${jobId}:`, error);
      throw error;
    }
  }

  /**
   * Download specific clip
   */
  async downloadClip(jobId, clipId, filename = null) {
    try {
      const response = await fetch(`${this.apiClient.baseUrl}/api/download/clip/${jobId}/${clipId}`);
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }

      // Get filename from response headers or use provided name
      const contentDisposition = response.headers.get('Content-Disposition');
      let downloadFilename = filename;
      
      if (!downloadFilename && contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          downloadFilename = filenameMatch[1];
        }
      }
      
      if (!downloadFilename) {
        downloadFilename = `clip_${clipId}.mp4`;
      }

      // Create download blob
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      // Trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadFilename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      console.log('✅ Clip downloaded:', downloadFilename);
      
      return {
        success: true,
        filename: downloadFilename,
        size: blob.size
      };

    } catch (error) {
      console.error(`❌ Failed to download clip ${clipId}:`, error);
      throw error;
    }
  }

  /**
   * Fallback to sync processing when queue is unavailable
   */
  async fallbackToSync(videoInput, options = {}) {
    console.log('🔄 Using sync processing fallback');
    
    try {
      // Use existing workflow endpoint for sync processing
      const response = await fetch(`${this.apiClient.baseUrl}/api/workflows/youtube-to-tiktok`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          youtube_url: typeof videoInput === 'string' ? videoInput : (videoInput.filePath || videoInput.url || videoInput.path || videoInput),
          target_duration: options.targetDuration || 60,
          voice_preference: options.voicePreference || 'female_professional',
          target_audience: options.targetAudience || 'general'
        })
      });

      if (!response.ok) {
        throw new Error(`Sync processing failed: ${response.status}`);
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Sync processing failed');
      }

      // Convert sync result to async-like format
      return {
        success: true,
        jobId: `sync_${Date.now()}`,
        status: 'completed',
        syncMode: true,
        result: result,
        clips: this.convertSyncResultToClips(result),
        message: 'Processed synchronously (queue system unavailable)'
      };

    } catch (error) {
      console.error('❌ Sync fallback failed:', error);
      throw error;
    }
  }

  /**
   * Convert sync workflow result to async clip format
   */
  convertSyncResultToClips(syncResult) {
    const clips = [];
    
    // Extract clips from sync result
    if (syncResult.final_deliverables) {
      clips.push({
        clip_id: 1,
        type: 'main_video',
        title: 'Processed Video',
        file_path: syncResult.final_deliverables.video_path,
        platform: 'general',
        description: 'Main processed video',
        download_url: '#sync' // Special marker for sync mode
      });
    }

    return {
      clips: clips,
      total_clips: clips.length,
      processing_time: syncResult.total_processing_time,
      sync_mode: true
    };
  }

  /**
   * Get queue statistics
   */
  async getQueueStats() {
    try {
      const response = await fetch(`${this.apiClient.baseUrl}/api/queue/stats`);
      
      if (!response.ok) {
        return { available: false };
      }

      return await response.json();
      
    } catch (error) {
      console.warn('❌ Failed to get queue stats:', error);
      return { available: false };
    }
  }

  /**
   * Get all active jobs for current session
   */
  getActiveJobs() {
    return Array.from(this.activeJobs.values());
  }

  /**
   * Cancel job monitoring (doesn't cancel the actual job)
   */
  stopMonitoring(jobId) {
    this.jobCallbacks.delete(jobId);
    console.log('🛑 Stopped monitoring job:', jobId);
  }

  /**
   * Clear completed jobs from memory
   */
  clearCompletedJobs() {
    const active = [];
    for (const [jobId, jobInfo] of this.activeJobs.entries()) {
      if (jobInfo.status === 'completed' || jobInfo.status === 'failed') {
        this.activeJobs.delete(jobId);
      } else {
        active.push(jobId);
      }
    }
    console.log(`🧹 Cleared completed jobs, ${active.length} still active`);
    return active;
  }
}

export default AsyncJobService;