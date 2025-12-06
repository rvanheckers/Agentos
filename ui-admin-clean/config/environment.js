/**
 * Environment Configuration
 * Single source of truth for app settings
 */

export const config = {
  api: {
    baseUrl: 'http://localhost:8001',
    timeout: 30000,
    retryAttempts: 3
  },
  
  ui: {
    refreshInterval: 30000, // 30 seconds
    animationDuration: 200
  },
  
  features: {
    realTimeUpdates: true,
    debugMode: window.location.hostname === 'localhost'
  }
};