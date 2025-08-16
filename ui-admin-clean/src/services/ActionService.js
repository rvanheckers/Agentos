/**
 * Enterprise Action Service
 * Single service for all admin actions using the unified action endpoint
 */

// Browser-compatible UUID generator (no external dependencies)
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

class ActionService {
  constructor() {
    // Configurable API base URL with environment-aware fallbacks
    this.baseUrl = this._getApiBaseUrl() + '/api/admin/action';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
  }

  /**
   * Get API base URL with environment detection
   * Priority: window.AGENTOS_CONFIG > location origin port mapping > localhost fallback
   */
  _getApiBaseUrl() {
    // 1. Check for runtime configuration
    if (typeof window !== 'undefined' && window.AGENTOS_CONFIG && window.AGENTOS_CONFIG.API_BASE_URL) {
      return window.AGENTOS_CONFIG.API_BASE_URL;
    }
    
    // 2. Derive from current location for development/production
    if (typeof window !== 'undefined' && window.location) {
      const currentOrigin = window.location.origin;
      
      // Development: map UI ports to API port
      if (currentOrigin.includes('localhost') || currentOrigin.includes('127.0.0.1')) {
        return currentOrigin.replace(':8080', ':8001').replace(':8004', ':8001').replace(':3000', ':8001');
      }
      
      // Production/staging: assume API on same origin
      return currentOrigin;
    }
    
    // 3. Fallback for development
    return 'http://localhost:8001';
  }

  /**
   * Generate trace ID for request tracking
   */
  generateTraceId() {
    return generateUUID();
  }

  /**
   * Execute any admin action
   * @param {string} action - Action type (e.g., 'job.retry', 'queue.clear')
   * @param {Object} payload - Action-specific payload
   * @param {Object} options - Additional options (idempotencyKey, traceId)
   * @returns {Promise<Object>} Action result
   */
  async execute(action, payload = {}, options = {}) {
    const traceId = options.traceId || this.generateTraceId();
    
    const headers = {
      ...this.defaultHeaders,
      'X-Trace-Id': traceId
    };

    // Add idempotency key if provided
    if (options.idempotencyKey) {
      headers['X-Idempotency-Key'] = options.idempotencyKey;
    }

    const request = {
      action: action,
      payload: payload
    };

    try {
      console.log(`🚀 Executing action: ${action}`, { traceId, payload });
      
      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(request)
      });

      const responseData = await response.json();

      if (!response.ok) {
        const error = new Error(responseData.detail || `Action failed: ${action}`);
        error.status = response.status;
        error.traceId = traceId;
        error.action = action;
        throw error;
      }

      console.log(`✅ Action completed: ${action}`, { 
        traceId, 
        duration: responseData.duration_ms,
        success: responseData.success 
      });

      return {
        success: responseData.success,
        result: responseData.result,
        traceId: responseData.trace_id,
        timestamp: responseData.timestamp,
        duration: responseData.duration_ms
      };

    } catch (error) {
      console.error(`❌ Action failed: ${action}`, { 
        traceId, 
        error: error.message,
        status: error.status 
      });
      
      // Re-throw with additional context
      error.traceId = traceId;
      error.action = action;
      throw error;
    }
  }

  // =============================================================================
  // JOB ACTIONS
  // =============================================================================

  /**
   * Retry a failed job
   */
  async retryJob(jobId, options = {}) {
    return this.execute('job.retry', { job_id: jobId }, {
      ...options
      // TODO: Re-enable idempotency key after backend fix (target: Sprint 2025-08-15)
      // Issue: Backend idempotency service causing 500 errors on job actions
      // Mitigation: UI should disable buttons during request to prevent double-submit
      // idempotencyKey: options.idempotencyKey || `retry-job-${jobId}-${Date.now()}`
    });
  }

  /**
   * Cancel a running job
   */
  async cancelJob(jobId, options = {}) {
    return this.execute('job.cancel', { job_id: jobId }, {
      ...options
      // TODO: Re-enable idempotency key after backend fix (target: Sprint 2025-08-15)
      // Issue: Backend idempotency service causing 500 errors on job actions
      // Mitigation: UI should disable buttons during request to prevent double-submit
      // idempotencyKey: options.idempotencyKey || `cancel-job-${jobId}-${Date.now()}`
    });
  }

  /**
   * Delete a job (admin only)
   */
  async deleteJob(jobId, options = {}) {
    return this.execute('job.delete', { job_id: jobId }, {
      ...options
      // TODO: Re-enable idempotency key after backend fix (target: Sprint 2025-08-15)
      // Issue: Backend idempotency service causing 500 errors on job actions
      // Mitigation: UI should disable buttons during request to prevent double-submit
      // idempotencyKey: options.idempotencyKey || `delete-job-${jobId}-${Date.now()}`
    });
  }

  /**
   * Change job priority
   */
  async changeJobPriority(jobId, priority, options = {}) {
    return this.execute('job.priority', { job_id: jobId, priority }, options);
  }

  // =============================================================================
  // QUEUE ACTIONS
  // =============================================================================

  /**
   * Clear all jobs from queue (admin only)
   */
  async clearQueue(queueName = 'default', options = {}) {
    return this.execute('queue.clear', { queue_name: queueName }, {
      ...options,
      idempotencyKey: options.idempotencyKey || `clear-queue-${queueName}-${Date.now()}`
    });
  }

  /**
   * Pause queue processing
   */
  async pauseQueue(queueName = 'default', options = {}) {
    return this.execute('queue.pause', { queue_name: queueName }, options);
  }

  /**
   * Resume queue processing
   */
  async resumeQueue(queueName = 'default', options = {}) {
    return this.execute('queue.resume', { queue_name: queueName }, options);
  }

  /**
   * Drain queue (wait for current jobs to finish, don't start new ones)
   */
  async drainQueue(queueName = 'default', options = {}) {
    return this.execute('queue.drain', { queue_name: queueName }, options);
  }

  // =============================================================================
  // WORKER ACTIONS  
  // =============================================================================

  /**
   * Restart workers
   */
  async restartWorkers(options = {}) {
    return this.execute('worker.restart', {}, {
      ...options,
      idempotencyKey: options.idempotencyKey || `restart-workers-${Date.now()}`
    });
  }

  /**
   * Scale workers up or down
   */
  async scaleWorkers(count, options = {}) {
    return this.execute('worker.scale', { worker_count: count }, options);
  }

  /**
   * Pause worker processing
   */
  async pauseWorkers(options = {}) {
    return this.execute('worker.pause', {}, options);
  }

  /**
   * Resume worker processing
   */
  async resumeWorkers(options = {}) {
    return this.execute('worker.resume', {}, options);
  }

  // =============================================================================
  // SYSTEM ACTIONS
  // =============================================================================

  /**
   * Create system backup (admin only)
   */
  async createBackup(options = {}) {
    return this.execute('system.backup', {}, {
      ...options,
      idempotencyKey: options.idempotencyKey || `backup-${Date.now()}`
    });
  }

  /**
   * Enter maintenance mode (admin only)
   */
  async enterMaintenanceMode(reason = 'Scheduled maintenance', options = {}) {
    return this.execute('system.maintenance', { 
      action: 'enter',
      reason: reason 
    }, options);
  }

  /**
   * Exit maintenance mode (admin only)
   */
  async exitMaintenanceMode(options = {}) {
    return this.execute('system.maintenance', { 
      action: 'exit'
    }, options);
  }

  // =============================================================================
  // CACHE ACTIONS
  // =============================================================================

  /**
   * Clear system cache
   */
  async clearCache(cacheType = 'all', options = {}) {
    return this.execute('cache.clear', { cache_type: cacheType }, options);
  }

  /**
   * Warm cache with fresh data
   */
  async warmCache(cacheType = 'all', options = {}) {
    return this.execute('cache.warm', { cache_type: cacheType }, options);
  }

  // =============================================================================
  // ANALYTICS ACTIONS
  // =============================================================================

  /**
   * Drill down into analytics data
   */
  async analyticsDrillDown(filter = {}, options = {}) {
    return this.execute('analytics.drill_down', { filter }, options);
  }

  /**
   * Generate analytics report
   */
  async generateAnalyticsReport(type, format = 'pdf', options = {}) {
    return this.execute('analytics.generate_report', { 
      type, 
      format,
      timestamp: new Date().toISOString()
    }, options);
  }

  /**
   * Performance tuning automation
   */
  async performanceTune(targets = [], options = {}) {
    return this.execute('system.performance_tune', { targets }, options);
  }

  /**
   * Auto-scale workers based on metrics
   */
  async autoScale(immediate = false, options = {}) {
    return this.execute('worker.auto_scale', { immediate }, options);
  }

  /**
   * Scale workers up
   */
  async scaleUp(factor = 1, options = {}) {
    return this.execute('worker.scale_up', { factor }, options);
  }

  /**
   * Optimize worker allocation
   */
  async optimizeWorkers(options = {}) {
    return this.execute('worker.optimize', {}, options);
  }

  /**
   * Process high-priority queue items
   */
  async processPriorityQueue(options = {}) {
    return this.execute('queue.process_priority', {}, options);
  }

  /**
   * Optimize recovery processes
   */
  async optimizeRecovery(options = {}) {
    return this.execute('system.optimize_recovery', {}, options);
  }

  // =============================================================================
  // BATCH ACTIONS
  // =============================================================================

  /**
   * Execute multiple actions in sequence
   * @param {Array} actions - Array of {action, payload, options} objects
   * @returns {Promise<Array>} Results array
   */
  async executeBatch(actions) {
    const results = [];
    const batchId = generateUUID();
    
    console.log(`🔄 Executing batch of ${actions.length} actions`, { batchId });

    for (const [index, { action, payload, options = {} }] of actions.entries()) {
      try {
        const result = await this.execute(action, payload, {
          ...options,
          traceId: `${batchId}-${index}`
        });
        results.push({ success: true, result, action, index });
      } catch (error) {
        console.error(`Batch action ${index} failed:`, error);
        results.push({ 
          success: false, 
          error: error.message, 
          action, 
          index,
          traceId: error.traceId 
        });
        
        // Stop on first failure unless continueOnError is set
        if (!options.continueOnError) {
          break;
        }
      }
    }

    console.log(`✅ Batch completed: ${results.filter(r => r.success).length}/${actions.length} succeeded`);
    return results;
  }

  // =============================================================================
  // ERROR HANDLING UTILITIES
  // =============================================================================

  /**
   * Check if error is retryable
   */
  isRetryableError(error) {
    if (!error.status) return false;
    
    // Retry on server errors, rate limits, and timeouts
    return [500, 502, 503, 504, 429].includes(error.status);
  }

  /**
   * Execute with automatic retry
   */
  async executeWithRetry(action, payload = {}, options = {}, maxRetries = 3) {
    let lastError;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await this.execute(action, payload, options);
      } catch (error) {
        lastError = error;
        
        if (!this.isRetryableError(error) || attempt === maxRetries) {
          throw error;
        }
        
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000); // Exponential backoff
        console.warn(`Retry attempt ${attempt}/${maxRetries} for ${action} in ${delay}ms`, {
          error: error.message,
          traceId: error.traceId
        });
        
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    throw lastError;
  }

  // =============================================================================
  // STATUS AND MONITORING
  // =============================================================================

  /**
   * Get action execution status (if available)
   */
  async getActionStatus(traceId) {
    try {
      const response = await fetch(`/api/admin/action/status/${traceId}`, {
        headers: this.defaultHeaders
      });
      
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.warn('Could not fetch action status:', error);
    }
    
    return null;
  }
}

// Export singleton instance
export const actionService = new ActionService();
export default ActionService;