/**
 * Centralized Logging Service
 * Replaces console.log statements throughout the application
 * Provides structured logging with levels and filtering
 */

export class Logger {
  constructor() {
    this.logLevel = this.getLogLevel();
    this.levels = {
      DEBUG: 0,
      INFO: 1,
      WARN: 2,
      ERROR: 3,
      SILENT: 4
    };
    
    this.colors = {
      DEBUG: '#6B7280',
      INFO: '#3B82F6', 
      WARN: '#F59E0B',
      ERROR: '#EF4444'
    };
    
    this.emojis = {
      DEBUG: '🔍',
      INFO: '✅',
      WARN: '⚠️',
      ERROR: '❌'
    };
    
    this.init();
  }

  /**
   * Initialize logger with environment detection
   */
  init() {
    const isDev = window.location.hostname === 'localhost' || 
                  window.location.hostname === '127.0.0.1';
    
    // Set default log level based on environment
    if (!localStorage.getItem('logLevel')) {
      localStorage.setItem('logLevel', isDev ? 'DEBUG' : 'WARN');
      this.logLevel = isDev ? 'DEBUG' : 'WARN';
    }
    
    // Make logger available globally for debugging
    if (isDev) {
      window.logger = this;
    }
    
    this.info('Logger initialized', { 
      level: this.logLevel, 
      environment: isDev ? 'development' : 'production' 
    });
  }

  /**
   * Get current log level from localStorage
   */
  getLogLevel() {
    return localStorage.getItem('logLevel') || 'INFO';
  }

  /**
   * Set log level and persist to localStorage
   */
  setLogLevel(level) {
    if (this.levels[level] !== undefined) {
      this.logLevel = level;
      localStorage.setItem('logLevel', level);
      this.info(`Log level changed to ${level}`);
    }
  }

  /**
   * Check if message should be logged based on current level
   */
  shouldLog(level) {
    return this.levels[level] >= this.levels[this.logLevel];
  }

  /**
   * Format message with timestamp and context
   */
  formatMessage(level, message, context = {}) {
    const timestamp = new Date().toISOString().substr(11, 12);
    const emoji = this.emojis[level];
    
    return {
      timestamp,
      level,
      message: `${emoji} ${message}`,
      context,
      color: this.colors[level]
    };
  }

  /**
   * Core logging method
   */
  log(level, message, context = {}) {
    if (!this.shouldLog(level)) return;
    
    const formatted = this.formatMessage(level, message, context);
    
    // Console output with styling
    const consoleMethod = level === 'ERROR' ? 'error' : 
                         level === 'WARN' ? 'warn' : 'log';
    
    console[consoleMethod](
      `%c${formatted.timestamp} ${formatted.message}`,
      `color: ${formatted.color}; font-weight: bold;`,
      context
    );
    
    // Store in session for debugging
    this.storeLog(formatted);
  }

  /**
   * Store recent logs in sessionStorage for debugging
   */
  storeLog(logEntry) {
    try {
      const logs = JSON.parse(sessionStorage.getItem('recentLogs') || '[]');
      logs.push(logEntry);
      
      // Keep only last 100 logs
      if (logs.length > 100) {
        logs.splice(0, logs.length - 100);
      }
      
      sessionStorage.setItem('recentLogs', JSON.stringify(logs));
    } catch (e) {
      // Silent fail if sessionStorage is not available
    }
  }

  /**
   * Debug level logging
   */
  debug(message, context = {}) {
    this.log('DEBUG', message, context);
  }

  /**
   * Info level logging
   */
  info(message, context = {}) {
    this.log('INFO', message, context);
  }

  /**
   * Warning level logging
   */
  warn(message, context = {}) {
    this.log('WARN', message, context);
  }

  /**
   * Error level logging
   */
  error(message, context = {}) {
    this.log('ERROR', message, context);
  }

  /**
   * Get recent logs for debugging
   */
  getRecentLogs() {
    try {
      return JSON.parse(sessionStorage.getItem('recentLogs') || '[]');
    } catch (e) {
      return [];
    }
  }

  /**
   * Clear stored logs
   */
  clearLogs() {
    sessionStorage.removeItem('recentLogs');
    this.info('Logs cleared');
  }

  /**
   * Component-specific logger
   */
  getComponentLogger(componentName) {
    return {
      debug: (message, context = {}) => this.debug(`[${componentName}] ${message}`, context),
      info: (message, context = {}) => this.info(`[${componentName}] ${message}`, context),
      warn: (message, context = {}) => this.warn(`[${componentName}] ${message}`, context),
      error: (message, context = {}) => this.error(`[${componentName}] ${message}`, context)
    };
  }

  /**
   * API request logging helper
   */
  logApiRequest(method, url, data = null, duration = null) {
    const context = { method, url, data, duration };
    
    if (duration) {
      this.info(`API ${method} ${url} (${duration}ms)`, context);
    } else {
      this.debug(`API ${method} ${url}`, context);
    }
  }

  /**
   * API error logging helper
   */
  logApiError(method, url, error, duration = null) {
    const context = { method, url, error: error.message, duration };
    this.error(`API ${method} ${url} failed`, context);
  }

  /**
   * Performance logging helper
   */
  logPerformance(operation, duration, context = {}) {
    const level = duration > 1000 ? 'WARN' : 'DEBUG';
    this.log(level, `${operation} took ${duration}ms`, context);
  }

  /**
   * Progress logging helper
   */
  logProgress(operation, progress, total = 100, context = {}) {
    const percentage = Math.round((progress / total) * 100);
    this.debug(`${operation} progress: ${percentage}%`, { progress, total, ...context });
  }
}

// Export singleton instance
export const logger = new Logger();

// Export component logger helper
export const getLogger = (componentName) => logger.getComponentLogger(componentName);