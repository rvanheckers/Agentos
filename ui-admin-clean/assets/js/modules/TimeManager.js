/**
 * Professional TimeManager - 0.1% Expert Implementation  
 * Industry Standard: Backend sends UTC with 'Z', JavaScript handles the rest
 */

export class TimeManager {
  constructor() {
    this.timeUpdateInterval = null;
    // Simple in-memory cache for parsed timestamps (no conflict with Redis/API cache)
    this.timestampCache = new Map();
    console.log('🌍 TimeManager (0.1% Expert Edition) - Backend UTC timestamps expected');
  }

  /**
   * Parse timestamp - SIMPLE because backend now sends proper UTC
   * @param {string} timestamp - UTC timestamp with Z suffix
   * @returns {Date} - Parsed date object
   */
  parseTimestamp(timestamp) {
    if (!timestamp) return null;
    
    try {
      // Backend now sends proper UTC: "2025-07-20T20:37:41.513Z"
      // JavaScript Date() automatically converts to local time
      return new Date(timestamp);
    } catch (error) {
      console.warn('⚠️ Invalid timestamp:', timestamp, error);
      return null;
    }
  }

  /**
   * Format relative time (e.g., "2m ago", "Just now")
   */
  formatTime(timestamp) {
    const date = this.parseTimestamp(timestamp);
    if (!date || isNaN(date.getTime())) {
      return 'Invalid time';
    }

    const now = new Date();
    const diffMs = now - date;
    
    // Development debug (disabled to prevent spam with many jobs)
    // if (window.location.hostname === 'localhost') {
    //   console.log('🕐 Time parsing:', {
    //     input: timestamp,
    //     parsed: date.toLocaleString(),
    //     now: now.toLocaleString(),
    //     diffMin: Math.round(diffMs / 60000)
    //   });
    // }

    // Handle future dates (small tolerance for clock skew)
    if (diffMs < -300000) return 'Future';

    // Relative time formatting
    if (diffMs < 30000) return 'Just now';
    if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
    if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`;
    if (diffMs < 604800000) return `${Math.floor(diffMs / 86400000)}d ago`;

    // Absolute date for older items
    return date.toLocaleDateString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Format absolute timestamp (exact time display)
   */
  formatAbsoluteTime(timestamp) {
    const date = this.parseTimestamp(timestamp);
    if (!date || isNaN(date.getTime())) {
      return 'Invalid time';
    }

    return date.toLocaleString('nl-NL', {
      day: '2-digit',
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  /**
   * Update all timestamp displays in DOM
   */
  updateTimeDisplays() {
    const timeElements = document.querySelectorAll('[data-timestamp]');
    timeElements.forEach(element => {
      const timestamp = element.dataset.timestamp;
      if (timestamp) {
        const useAbsolute = element.dataset.absolute === 'true';
        element.textContent = useAbsolute ? 
          this.formatAbsoluteTime(timestamp) : 
          this.formatTime(timestamp);
      }
    });
  }

  /**
   * Start automatic time updates
   */
  startTimeUpdates() {
    this.timeUpdateInterval = setInterval(() => {
      this.updateTimeDisplays();
    }, 60000); // Update every minute
  }

  /**
   * Stop automatic time updates
   */
  stopTimeUpdates() {
    if (this.timeUpdateInterval) {
      clearInterval(this.timeUpdateInterval);
      this.timeUpdateInterval = null;
    }
  }
}