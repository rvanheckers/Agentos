/**
 * Filter Presets Configuration
 * Modulaire configuratie voor slimme filtering per view
 */

// Queue Management Filter Presets
export const QUEUE_FILTER_PRESETS = {
  'live-queue': {
    label: 'Live Queue',
    icon: '🔄',
    badge: 'Default',
    filter: {
      view: 'live-queue',
      status: ['queued', 'processing'],
      dateRange: 'today',
      sortBy: 'recent',
      limit: 50
    }
  },
  'job-history': {
    label: 'Job History',
    icon: '📋',
    filter: {
      view: 'job-history',
      status: 'all',
      dateRange: 'week',
      sortBy: 'recent',
      limit: 100
    }
  },
  'performance': {
    label: 'Performance',
    icon: '📊',
    filter: {
      view: 'performance',
      dateRange: 'week',
      sortBy: 'recent',
      limit: 50
    }
  },
  'alerts': {
    label: 'Alerts',
    icon: '🚨',
    filter: {
      view: 'alerts',
      status: ['failed'],
      dateRange: 'week',
      sortBy: 'recent',
      limit: 50
    }
  }
};

// Job History Filter Presets  
export const HISTORY_FILTER_PRESETS = {
  'today': {
    label: 'Today',
    icon: '📅',
    badge: 'Default',
    filter: {
      dateRange: 'today',
      sortBy: 'recent',
      limit: 100
    }
  },
  'this-week': {
    label: 'This Week',
    icon: '📆',
    filter: {
      dateRange: 'week',
      sortBy: 'recent',
      limit: 200
    }
  },
  'successful': {
    label: 'Successful Jobs',
    icon: '✅',
    filter: {
      status: ['completed'],
      dateRange: 'month',
      sortBy: 'recent',
      limit: 200
    }
  },
  'errors': {
    label: 'Error Analysis',
    icon: '🔍',
    filter: {
      status: ['failed'],
      dateRange: 'month',
      sortBy: 'recent',
      limit: 100
    }
  },
  'all-history': {
    label: 'Complete History',
    icon: '📚',
    filter: {
      status: 'all',
      sortBy: 'recent',
      limit: 50,
      pagination: true
    }
  }
};

// System Logs Filter Presets
export const LOGS_FILTER_PRESETS = {
  'live-logs': {
    label: 'Live Logs',
    icon: '📋',
    badge: 'Default',
    filter: {
      metric: 'live-logs',
      level: 'all',
      source: 'all',
      dateRange: 'today',
      sortBy: 'recent',
      limit: 100
    }
  },
  'search': {
    label: 'Advanced Search',
    icon: '🔍',
    filter: {
      metric: 'search',
      level: 'all',
      source: 'all',
      dateRange: 'week',
      sortBy: 'recent',
      limit: 200
    }
  },
  'analysis': {
    label: 'Log Analysis',
    icon: '📊',
    filter: {
      metric: 'analysis',
      level: 'all',
      source: 'all',
      dateRange: 'week',
      sortBy: 'recent',
      limit: 500
    }
  },
  'tools': {
    label: 'Management Tools',
    icon: '🛠️',
    filter: {
      metric: 'tools',
      level: 'all',
      source: 'all',
      dateRange: 'all',
      sortBy: 'recent',
      limit: 1000
    }
  }
};

// Workers Management Filter Presets
export const WORKERS_FILTER_PRESETS = {
  'active-workers': {
    label: 'Active Workers',
    icon: '🟢',
    badge: 'Default',
    filter: {
      status: ['active', 'processing'],
      sortBy: 'activity',
      limit: 20
    }
  },
  'idle-workers': {
    label: 'Idle Workers',
    icon: '🟡',
    filter: {
      status: ['idle'],
      sortBy: 'last_activity',
      limit: 50
    }
  },
  'offline-workers': {
    label: 'Offline Workers',
    icon: '🔴',
    filter: {
      status: ['offline', 'error'],
      sortBy: 'last_seen',
      limit: 50
    }
  },
  'all-workers': {
    label: 'All Workers',
    icon: '👥',
    filter: {
      status: 'all',
      sortBy: 'status',
      limit: 100
    }
  }
};

// Analytics Filter Presets
export const ANALYTICS_FILTER_PRESETS = {
  'performance': {
    label: 'Performance Metrics',
    icon: '📊',
    badge: 'Default',
    filter: {
      metric: 'performance',
      dateRange: 'week',
      granularity: 'daily'
    }
  },
  'usage-stats': {
    label: 'Usage Statistics',
    icon: '📈',
    filter: {
      metric: 'usage',
      dateRange: 'month',
      granularity: 'daily'
    }
  },
  'error-trends': {
    label: 'Error Trends',
    icon: '📉',
    filter: {
      metric: 'errors',
      dateRange: 'month',
      granularity: 'daily'
    }
  },
  'capacity': {
    label: 'Capacity Planning',
    icon: '⚖️',
    filter: {
      metric: 'capacity',
      dateRange: 'month',
      granularity: 'hourly'
    }
  }
};

// Filter Type Configurations
export const FILTER_TYPES = {
  queue: {
    statusOptions: [
      { value: 'all', label: 'All Status' },
      { value: 'queued', label: '📥 Queued' },
      { value: 'processing', label: '⚡ Processing' },
      { value: 'completed', label: '✅ Completed' },
      { value: 'failed', label: '❌ Failed' },
      { value: 'cancelled', label: '🚫 Cancelled' }
    ],
    dateOptions: [
      { value: 'all', label: 'All Time' },
      { value: 'today', label: 'Today' },
      { value: 'yesterday', label: 'Yesterday' },
      { value: 'week', label: 'This Week' },
      { value: 'month', label: 'This Month' },
      { value: 'custom', label: 'Custom Range' }
    ],
    sortOptions: [
      { value: 'recent', label: 'Most Recent' },
      { value: 'oldest', label: 'Oldest First' },
      { value: 'status', label: 'By Status' },
      { value: 'progress', label: 'By Progress' },
      { value: 'duration', label: 'By Duration' }
    ]
  },
  
  logs: {
    levelOptions: [
      { value: 'all', label: 'All Levels' },
      { value: 'error', label: '🔴 Error' },
      { value: 'warning', label: '🟡 Warning' },
      { value: 'info', label: '🔵 Info' },
      { value: 'debug', label: '⚪ Debug' }
    ],
    sourceOptions: [
      { value: 'all', label: 'All Sources' },
      { value: 'api', label: '🌐 API Server' },
      { value: 'worker', label: '👷 Workers' },
      { value: 'system', label: '⚙️ System' },
      { value: 'websocket', label: '🔗 WebSocket' }
    ],
    dateOptions: [
      { value: 'last-hour', label: 'Last Hour' },
      { value: 'today', label: 'Today' },
      { value: 'yesterday', label: 'Yesterday' },
      { value: 'week', label: 'This Week' },
      { value: 'month', label: 'This Month' }
    ]
  },

  workers: {
    statusOptions: [
      { value: 'all', label: 'All Workers' },
      { value: 'active', label: '🟢 Active' },
      { value: 'idle', label: '🟡 Idle' },
      { value: 'processing', label: '⚡ Processing' },
      { value: 'offline', label: '🔴 Offline' },
      { value: 'error', label: '❌ Error' }
    ],
    sortOptions: [
      { value: 'status', label: 'By Status' },
      { value: 'activity', label: 'By Activity' },
      { value: 'performance', label: 'By Performance' },
      { value: 'last_seen', label: 'Last Seen' }
    ]
  },

  analytics: {
    metricOptions: [
      { value: 'performance', label: '📊 Performance' },
      { value: 'usage', label: '📈 Usage' },
      { value: 'errors', label: '📉 Errors' },
      { value: 'capacity', label: '⚖️ Capacity' }
    ],
    granularityOptions: [
      { value: 'hourly', label: 'Hourly' },
      { value: 'daily', label: 'Daily' },
      { value: 'weekly', label: 'Weekly' },
      { value: 'monthly', label: 'Monthly' }
    ]
  }
};

// Pagination Settings
export const PAGINATION_SETTINGS = {
  defaultPageSize: 50,
  pageSizeOptions: [25, 50, 100, 200],
  maxItemsWithoutPagination: 100
};

// Export Helper Functions
export function getFilterPresets(viewType) {
  const presetMap = {
    'queue': QUEUE_FILTER_PRESETS,
    'history': HISTORY_FILTER_PRESETS,
    'logs': LOGS_FILTER_PRESETS,
    'workers': WORKERS_FILTER_PRESETS,
    'analytics': ANALYTICS_FILTER_PRESETS
  };
  
  return presetMap[viewType] || {};
}

export function getFilterTypes(viewType) {
  return FILTER_TYPES[viewType] || FILTER_TYPES.queue;
}