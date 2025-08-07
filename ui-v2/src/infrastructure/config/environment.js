/**
 * Environment Configuration
 * Centralized configuration voor verschillende omgevingen
 */

export const Environment = {
  // API Configuration
  API: {
    BASE_URL: 'http://localhost:8001',
    MCP_BASE_URL: 'http://localhost:8001/api/mcp',
    LEGACY_BASE_URL: 'http://localhost:8001/api',
    WEBSOCKET_URL: 'ws://localhost:8001/ws',
    MEDIA_BASE_URL: 'http://localhost:8001',
    TIMEOUT: 30000, // 30 seconds
    RETRY_ATTEMPTS: 3
  },
  
  // Upload Configuration
  UPLOAD: {
    MAX_FILE_SIZE: 2 * 1024 * 1024 * 1024, // 2GB
    ALLOWED_TYPES: [
      'video/mp4',
      'video/mov', 
      'video/avi',
      'video/webm',
      'video/quicktime'
    ],
    CHUNK_SIZE: 1024 * 1024 // 1MB chunks
  },
  
  // Processing Configuration
  PROCESSING: {
    DEFAULT_TIMEOUT: 10 * 60 * 1000, // 10 minutes
    POLL_INTERVAL: 1000, // 1 second
    MAX_RETRIES: 5
  },
  
  // UI Configuration
  UI: {
    DEFAULT_LANGUAGE: 'nl',
    SUPPORTED_LANGUAGES: ['nl', 'en', 'de', 'fr'],
    NOTIFICATION_DURATION: 5000,
    ANIMATION_DURATION: 300
  },
  
  // Feature Flags
  FEATURES: {
    MCP_ENABLED: true,
    WEBSOCKET_ENABLED: true,
    FILE_UPLOAD_ENABLED: true,
    URL_PROCESSING_ENABLED: true,
    ANALYTICS_ENABLED: true
  },
  
  // Debug Configuration
  DEBUG: {
    ENABLED: true,
    LOG_LEVEL: 'info', // error, warn, info, debug
    API_LOGGING: true,
    PERFORMANCE_MONITORING: true
  }
};

/**
 * Get environment specific configuration
 */
export function getConfig(path) {
  const keys = path.split('.');
  let config = Environment;
  
  for (const key of keys) {
    if (config[key] === undefined) {
      console.warn(`Configuration key not found: ${path}`);
      return null;
    }
    config = config[key];
  }
  
  return config;
}

/**
 * Check if feature is enabled
 */
export function isFeatureEnabled(feature) {
  return Environment.FEATURES[feature] === true;
}

/**
 * Get API endpoint URL
 */
export function getApiUrl(endpoint, useMCP = true) {
  const baseUrl = useMCP && isFeatureEnabled('MCP_ENABLED') 
    ? Environment.API.MCP_BASE_URL 
    : Environment.API.LEGACY_BASE_URL;
    
  return `${baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
}

/**
 * Get WebSocket URL
 */
export function getWebSocketUrl(params = {}) {
  const url = new URL(Environment.API.WEBSOCKET_URL);
  
  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });
  
  return url.toString();
}

/**
 * Validate file for upload
 */
export function validateFile(file) {
  const errors = [];
  
  // Check file size
  if (file.size > Environment.UPLOAD.MAX_FILE_SIZE) {
    errors.push(`Bestand te groot (max ${formatFileSize(Environment.UPLOAD.MAX_FILE_SIZE)})`);
  }
  
  // Check file type
  if (!Environment.UPLOAD.ALLOWED_TYPES.includes(file.type)) {
    errors.push(`Bestandstype niet ondersteund: ${file.type}`);
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Format file size
 */
export function formatFileSize(bytes) {
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  if (bytes === 0) return '0 Bytes';
  
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Development mode check
 */
export function isDevelopment() {
  return Environment.DEBUG.ENABLED || 
         location.hostname === 'localhost' || 
         location.hostname === '127.0.0.1';
}

/**
 * Log function with level checking
 */
export function log(level, message, ...args) {
  if (!Environment.DEBUG.ENABLED) return;
  
  const levels = { error: 0, warn: 1, info: 2, debug: 3 };
  const currentLevel = levels[Environment.DEBUG.LOG_LEVEL] || 2;
  const messageLevel = levels[level] || 2;
  
  if (messageLevel <= currentLevel) {
    console[level](`[VibeCoder] ${message}`, ...args);
  }
}

/**
 * Path Resolution Service - Universal path handling
 * Based on working legacy implementation
 */
export const PathResolver = {
  /**
   * Convert server filesystem path to frontend-accessible URL
   * ./io/downloads/video.mp4 → http://localhost:8001/io/downloads/video.mp4
   */
  toMediaUrl(serverPath) {
    if (!serverPath) return null;
    
    // Normalize server path
    const normalizedPath = this.normalizeServerPath(serverPath);
    
    // Return full media URL (ensure no double slashes)
    const baseUrl = Environment.API.MEDIA_BASE_URL.endsWith('/') ? 
      Environment.API.MEDIA_BASE_URL.slice(0, -1) : Environment.API.MEDIA_BASE_URL;
    const cleanPath = normalizedPath.startsWith('/') ? normalizedPath : '/' + normalizedPath;
    return `${baseUrl}${cleanPath}`;
  },
  
  /**
   * Convert media URL back to server filesystem path  
   * http://localhost:8001/io/downloads/video.mp4 → ./io/downloads/video.mp4
   */
  toServerPath(mediaUrl) {
    if (!mediaUrl) return null;
    
    // Extract path from URL
    let pathPart = mediaUrl;
    if (mediaUrl.includes(Environment.API.MEDIA_BASE_URL)) {
      pathPart = mediaUrl.replace(Environment.API.MEDIA_BASE_URL, '');
    }
    
    // Ensure starts with ./
    if (!pathPart.startsWith('./') && pathPart.startsWith('/')) {
      pathPart = '.' + pathPart;
    }
    
    return pathPart;
  },
  
  /**
   * Normalize server paths for consistent handling
   */
  normalizeServerPath(serverPath) {
    let path = serverPath;
    
    // Handle different formats
    if (path.startsWith('./io/')) {
      return path.substring(1); // ./io/downloads/video.mp4 → /io/downloads/video.mp4
    }
    
    if (path.startsWith('/io/')) {
      return path; // Already normalized
    }
    
    if (path.includes('/io/')) {
      // Extract from '/io/' onwards, whether it's /mnt/c/.../io/output or ./io/output  
      const ioIndex = path.indexOf('/io/');
      return path.substring(ioIndex);
    }
    
    // Default assumption - probably a filename in downloads
    return `/io/downloads/${path}`;
  },
  
  /**
   * Get server path for AI agents (always relative)
   * Used for video_path in API calls to agents
   */
  getServerPathForAgent(pathOrUrl) {
    if (!pathOrUrl) return null;
    
    // If it's already a server path, return as-is
    if (pathOrUrl.startsWith('./io/')) {
      return pathOrUrl;
    }
    
    // If it's a media URL, convert to server path
    if (pathOrUrl.startsWith('http')) {
      return this.toServerPath(pathOrUrl);
    }
    
    // If it's just a filename, assume downloads
    if (!pathOrUrl.includes('/')) {
      return `./io/downloads/${pathOrUrl}`;
    }
    
    return pathOrUrl;
  },
  
  /**
   * Get media URL for frontend display (always HTTP)
   * Used for video players and download links
   */
  getMediaUrlForDisplay(pathOrUrl) {
    if (!pathOrUrl) return null;
    
    // If it's already a media URL, return as-is
    if (pathOrUrl.startsWith('http')) {
      return pathOrUrl;
    }
    
    // Convert server path to media URL
    return this.toMediaUrl(pathOrUrl);
  }
};

export default Environment;