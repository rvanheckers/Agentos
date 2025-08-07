/**
 * Real-time Processing Service
 * Handles WebSocket connections en real-time updates voor video processing
 */

import { getWebSocketUrl, log } from '../../infrastructure/config/environment.js';

export class RealtimeService {
  constructor() {
    this.websocket = null;
    this.sessionId = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.isConnecting = false;
    this.isManuallyDisconnected = false;
    
    this.listeners = new Map();
    this.messageQueue = [];
    
    this.setupEventListeners();
  }

  /**
   * Connect to WebSocket
   */
  async connect(sessionId = null) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      log('debug', 'WebSocket already connected');
      return;
    }

    if (this.isConnecting) {
      log('debug', 'WebSocket connection already in progress');
      return;
    }

    this.isConnecting = true;
    this.isManuallyDisconnected = false;
    this.sessionId = sessionId;

    try {
      const params = {};
      if (sessionId) {
        params.session_id = sessionId;
      }

      const wsUrl = getWebSocketUrl(params);
      log('info', 'Connecting to WebSocket:', wsUrl);

      this.websocket = new WebSocket(wsUrl);
      this.setupWebSocketHandlers();

    } catch (error) {
      log('error', 'Failed to create WebSocket connection:', error);
      this.isConnecting = false;
      this.handleConnectionError(error);
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  setupWebSocketHandlers() {
    if (!this.websocket) return;

    this.websocket.onopen = (event) => {
      log('info', '🔗 WebSocket verbonden');
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      
      // Process queued messages
      this.processMessageQueue();
      
      this.emit('connected', { sessionId: this.sessionId });
    };

    this.websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        log('error', 'Failed to parse WebSocket message:', error);
      }
    };

    this.websocket.onclose = (event) => {
      log('info', '🔌 WebSocket verbinding gesloten', event.code, event.reason);
      this.isConnecting = false;
      this.websocket = null;
      
      this.emit('disconnected', { 
        code: event.code, 
        reason: event.reason,
        wasClean: event.wasClean
      });

      // Auto-reconnect if not manually disconnected
      if (!this.isManuallyDisconnected && this.shouldReconnect(event.code)) {
        this.scheduleReconnect();
      }
    };

    this.websocket.onerror = (error) => {
      log('error', 'WebSocket error:', error);
      this.emit('error', error);
      this.handleConnectionError(error);
    };
  }

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(data) {
    log('debug', 'WebSocket message received:', data);

    // Emit specific event based on message type
    if (data.type) {
      this.emit(data.type, data);
    }

    // Always emit general message event
    this.emit('message', data);

    // Handle processing updates
    if (data.type === 'processing_update') {
      this.handleProcessingUpdate(data);
    }

    // Handle analysis updates
    if (data.type === 'analysis_update') {
      this.handleAnalysisUpdate(data);
    }

    // Handle completion
    if (data.type === 'processing_complete') {
      this.handleProcessingComplete(data);
    }

    // Handle errors
    if (data.type === 'processing_error') {
      this.handleProcessingError(data);
    }
  }

  /**
   * Handle processing updates
   */
  handleProcessingUpdate(data) {
    // Update global processing state
    const event = new CustomEvent('mcpUpdate', {
      detail: {
        status: 'processing',
        current_step: data.step,
        progress: data.progress,
        time_estimate: data.time_estimate,
        session_id: data.session_id
      }
    });
    
    document.dispatchEvent(event);
  }

  /**
   * Handle analysis updates (voor real-time analysis points)
   */
  handleAnalysisUpdate(data) {
    const event = new CustomEvent('mcpUpdate', {
      detail: {
        status: 'analyzing',
        analysis_points: data.points,
        current_timestamp: data.timestamp,
        session_id: data.session_id
      }
    });
    
    document.dispatchEvent(event);
  }

  /**
   * Handle processing completion
   */
  handleProcessingComplete(data) {
    const event = new CustomEvent('mcpUpdate', {
      detail: {
        status: 'completed',
        clips: data.clips,
        analytics: data.analytics,
        session_id: data.session_id
      }
    });
    
    document.dispatchEvent(event);
  }

  /**
   * Handle processing errors
   */
  handleProcessingError(data) {
    const event = new CustomEvent('mcpUpdate', {
      detail: {
        status: 'failed',
        error: data.error,
        error_details: data.details,
        session_id: data.session_id
      }
    });
    
    document.dispatchEvent(event);
  }

  /**
   * Send message via WebSocket
   */
  send(message) {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      try {
        const payload = typeof message === 'string' ? message : JSON.stringify(message);
        this.websocket.send(payload);
        log('debug', 'WebSocket message sent:', message);
      } catch (error) {
        log('error', 'Failed to send WebSocket message:', error);
      }
    } else {
      log('debug', 'WebSocket not connected, queueing message:', message);
      this.messageQueue.push(message);
    }
  }

  /**
   * Process queued messages
   */
  processMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.send(message);
    }
  }

  /**
   * Check if should reconnect
   */
  shouldReconnect(code) {
    // Don't reconnect on normal closure or policy violation
    const noReconnectCodes = [1000, 1001, 1008, 1011];
    return !noReconnectCodes.includes(code) && 
           this.reconnectAttempts < this.maxReconnectAttempts;
  }

  /**
   * Schedule reconnection
   */
  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      log('error', 'Max reconnect attempts reached');
      this.emit('reconnect_failed');
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    log('info', `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      if (!this.isManuallyDisconnected) {
        this.connect(this.sessionId);
      }
    }, delay);
  }

  /**
   * Handle connection errors
   */
  handleConnectionError(error) {
    this.isConnecting = false;
    
    // Emit error event
    this.emit('connection_error', error);
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    this.isManuallyDisconnected = true;
    
    if (this.websocket) {
      this.websocket.close(1000, 'Manual disconnect');
    }
    
    this.messageQueue = [];
    this.sessionId = null;
  }

  /**
   * Get connection status
   */
  getStatus() {
    if (!this.websocket) {
      return 'disconnected';
    }

    switch (this.websocket.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'disconnecting';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }

  /**
   * Check if connected
   */
  isConnected() {
    return this.websocket && this.websocket.readyState === WebSocket.OPEN;
  }

  /**
   * Setup DOM event listeners
   */
  setupEventListeners() {
    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && !this.isConnected() && !this.isManuallyDisconnected) {
        log('info', 'Page became visible, reconnecting WebSocket');
        this.connect(this.sessionId);
      }
    });

    // Handle online/offline events
    window.addEventListener('online', () => {
      if (!this.isConnected() && !this.isManuallyDisconnected) {
        log('info', 'Network back online, reconnecting WebSocket');
        this.connect(this.sessionId);
      }
    });

    window.addEventListener('offline', () => {
      log('info', 'Network offline');
      this.emit('network_offline');
    });
  }

  /**
   * Add event listener
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    
    this.listeners.get(event).add(callback);
    
    // Return unsubscribe function
    return () => {
      this.off(event, callback);
    };
  }

  /**
   * Remove event listener
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  /**
   * Emit event to listeners
   */
  emit(event, data = null) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          log('error', `Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Send ping to keep connection alive
   */
  ping() {
    this.send({ type: 'ping', timestamp: Date.now() });
  }

  /**
   * Start ping interval
   */
  startPingInterval(intervalMs = 30000) {
    this.stopPingInterval();
    
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.ping();
      }
    }, intervalMs);
  }

  /**
   * Stop ping interval
   */
  stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Subscribe to processing updates for specific session
   */
  subscribeToProcessing(sessionId, callbacks = {}) {
    this.sessionId = sessionId;
    
    // Connect if not already connected
    if (!this.isConnected()) {
      this.connect(sessionId);
    }
    
    // Setup callbacks
    const unsubscribeFunctions = [];
    
    if (callbacks.onUpdate) {
      unsubscribeFunctions.push(this.on('processing_update', callbacks.onUpdate));
    }
    
    if (callbacks.onAnalysis) {
      unsubscribeFunctions.push(this.on('analysis_update', callbacks.onAnalysis));
    }
    
    if (callbacks.onComplete) {
      unsubscribeFunctions.push(this.on('processing_complete', callbacks.onComplete));
    }
    
    if (callbacks.onError) {
      unsubscribeFunctions.push(this.on('processing_error', callbacks.onError));
    }
    
    // Return unsubscribe function
    return () => {
      unsubscribeFunctions.forEach(unsub => unsub());
    };
  }

  /**
   * Cleanup on page unload
   */
  cleanup() {
    this.stopPingInterval();
    this.disconnect();
    this.listeners.clear();
  }
}

// Cleanup bij page unload
window.addEventListener('beforeunload', () => {
  if (window.realtimeService) {
    window.realtimeService.cleanup();
  }
});

export default RealtimeService;