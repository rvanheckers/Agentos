/**
 * WebSocket Service voor Real-time Job Updates
 * ============================================
 * 
 * Biedt real-time communicatie met backend voor:
 * - Live job progress updates
 * - Worker status monitoring  
 * - Queue statistics
 * - System events
 * 
 * Features:
 * - Automatic reconnection
 * - Fallback naar polling
 * - Event-based architecture
 * - Connection health monitoring
 */

import { EventEmitter } from '../utils/event-emitter.js';
import { Logger } from './logger.js';

class WebSocketService extends EventEmitter {
    constructor() {
        super();
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.subscriptions = new Set();
        this.logger = new Logger('WebSocketService');
        
        // WebSocket server configuration
        this.wsUrl = this.getWebSocketUrl();
        
        // Fallback polling configuration
        this.pollingEnabled = false;
        this.pollingInterval = null;
        this.pollingDelay = 2000; // 2 seconds polling fallback
        
        this.logger.info('WebSocket Service initialized');
    }
    
    getWebSocketUrl() {
        /**
         * Generate WebSocket URL based on current environment
         */
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = 8765; // WebSocket server port
        
        return `${protocol}//${host}:${port}`;
    }
    
    async connect() {
        /**
         * Establish WebSocket connection with automatic fallback
         */
        if (this.isConnected) {
            this.logger.warn('Already connected to WebSocket');
            return true;
        }
        
        try {
            this.logger.info(`Attempting to connect to ${this.wsUrl}`);
            
            this.ws = new WebSocket(this.wsUrl);
            
            return new Promise((resolve, reject) => {
                const connectionTimeout = setTimeout(() => {
                    this.logger.warn('WebSocket connection timeout, falling back to polling');
                    this.ws.close();
                    this.startPollingFallback();
                    resolve(false); // Connection failed, but fallback enabled
                }, 5000);
                
                this.ws.onopen = () => {
                    clearTimeout(connectionTimeout);
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this.reconnectDelay = 1000;
                    this.pollingEnabled = false;
                    
                    this.logger.info('WebSocket connected successfully');
                    this.emit('connected');
                    
                    // Re-subscribe to previous subscriptions
                    this.resubscribeAll();
                    
                    resolve(true);
                };
                
                this.ws.onmessage = (event) => {
                    this.handleMessage(event.data);
                };
                
                this.ws.onclose = (event) => {
                    clearTimeout(connectionTimeout);
                    this.isConnected = false;
                    this.emit('disconnected');
                    
                    if (event.code !== 1000) { // Not a normal closure
                        this.logger.warn(`WebSocket closed unexpectedly: ${event.code} ${event.reason}`);
                        this.attemptReconnect();
                    } else {
                        this.logger.info('WebSocket closed normally');
                    }
                };
                
                this.ws.onerror = (error) => {
                    clearTimeout(connectionTimeout);
                    this.logger.error('WebSocket error:', error);
                    this.emit('error', error);
                    
                    // Start polling fallback
                    this.startPollingFallback();
                    resolve(false);
                };
            });
            
        } catch (error) {
            this.logger.error('Failed to create WebSocket connection:', error);
            this.startPollingFallback();
            return false;
        }
    }
    
    disconnect() {
        /**
         * Cleanly disconnect WebSocket and stop polling
         */
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
        
        this.isConnected = false;
        this.stopPollingFallback();
        this.emit('disconnected');
        this.logger.info('WebSocket disconnected');
    }
    
    handleMessage(data) {
        /**
         * Process incoming WebSocket messages
         */
        try {
            const message = JSON.parse(data);
            const { type, ...payload } = message;
            
            this.logger.debug(`Received ${type} message:`, payload);
            
            // Emit specific event for message type
            this.emit(type, payload);
            
            // Emit general message event
            this.emit('message', message);
            
        } catch (error) {
            this.logger.error('Failed to parse WebSocket message:', error);
        }
    }
    
    send(message) {
        /**
         * Send message to WebSocket server
         */
        if (!this.isConnected || !this.ws) {
            this.logger.warn('Cannot send message: WebSocket not connected');
            return false;
        }
        
        try {
            const payload = JSON.stringify(message);
            this.ws.send(payload);
            this.logger.debug('Sent message:', message);
            return true;
        } catch (error) {
            this.logger.error('Failed to send WebSocket message:', error);
            return false;
        }
    }
    
    subscribeToJob(jobId) {
        /**
         * Subscribe to real-time updates for specific job
         */
        this.subscriptions.add(jobId);
        
        const success = this.send({
            type: 'subscribe_job',
            job_id: jobId
        });
        
        if (success) {
            this.logger.info(`Subscribed to job ${jobId}`);
        }
        
        return success;
    }
    
    unsubscribeFromJob(jobId) {
        /**
         * Unsubscribe from job updates
         */
        this.subscriptions.delete(jobId);
        
        const success = this.send({
            type: 'unsubscribe_job',
            job_id: jobId
        });
        
        if (success) {
            this.logger.info(`Unsubscribed from job ${jobId}`);
        }
        
        return success;
    }
    
    requestJobStatus(jobId) {
        /**
         * Request current status for specific job
         */
        return this.send({
            type: 'request_job_status',
            job_id: jobId
        });
    }
    
    requestQueueStats() {
        /**
         * Request current queue statistics
         */
        return this.send({
            type: 'request_queue_stats'
        });
    }
    
    ping() {
        /**
         * Send ping to check connection health
         */
        return this.send({
            type: 'ping'
        });
    }
    
    resubscribeAll() {
        /**
         * Re-subscribe to all previous subscriptions
         */
        this.subscriptions.forEach(jobId => {
            this.send({
                type: 'subscribe_job',
                job_id: jobId
            });
        });
        
        this.logger.info(`Re-subscribed to ${this.subscriptions.size} jobs`);
    }
    
    attemptReconnect() {
        /**
         * Attempt to reconnect with exponential backoff
         */
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.logger.error('Max reconnection attempts reached, starting polling fallback');
            this.startPollingFallback();
            return;
        }
        
        this.reconnectAttempts++;
        this.logger.info(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    }
    
    startPollingFallback() {
        /**
         * Start polling fallback for job updates
         */
        if (this.pollingEnabled) {
            return; // Already polling
        }
        
        this.pollingEnabled = true;
        this.logger.info('Starting polling fallback mode');
        
        this.pollingInterval = setInterval(() => {
            this.pollJobUpdates();
        }, this.pollingDelay);
        
        this.emit('fallback_enabled');
    }
    
    stopPollingFallback() {
        /**
         * Stop polling fallback
         */
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        
        this.pollingEnabled = false;
        this.logger.info('Stopped polling fallback');
        this.emit('fallback_disabled');
    }
    
    async pollJobUpdates() {
        /**
         * Poll for job updates using REST API
         */
        if (this.subscriptions.size === 0) {
            return; // No jobs to poll
        }
        
        const apiBaseUrl = 'http://localhost:8001';
        
        try {
            // Poll each subscribed job
            for (const jobId of this.subscriptions) {
                const response = await fetch(`${apiBaseUrl}/api/jobs/${jobId}`);
                if (response.ok) {
                    const jobData = await response.json();
                    const jobStatus = jobData.job || jobData;
                    
                    // Emit the same events as WebSocket would
                    this.emit('job_status', {
                        job_id: jobId,
                        status: jobStatus.status,
                        progress: jobStatus.progress,
                        current_step: jobStatus.current_step,
                        timestamp: new Date().toISOString(),
                        source: 'polling'
                    });
                }
            }
            
            // Poll queue stats  
            const queueResponse = await fetch(`${apiBaseUrl}/api/resources/analytics`);
            if (queueResponse.ok) {
                const analyticsData = await queueResponse.json();
                this.emit('queue_stats', {
                    ...analyticsData,
                    timestamp: new Date().toISOString(),
                    source: 'polling'
                });
            }
            
        } catch (error) {
            this.logger.error('Polling failed:', error);
        }
    }
    
    getConnectionStatus() {
        /**
         * Get current connection status
         */
        return {
            connected: this.isConnected,
            polling: this.pollingEnabled,
            subscriptions: Array.from(this.subscriptions),
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

// Create singleton instance
const websocketService = new WebSocketService();

export { websocketService, WebSocketService };