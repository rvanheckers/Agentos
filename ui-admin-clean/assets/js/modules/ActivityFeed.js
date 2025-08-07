import { TimeManager } from './TimeManager.js';

export class ActivityFeed {
  constructor() {
    this.timeManager = new TimeManager();
  }

  getActivityIcon(type) {
    const icons = {
      'job_completed': '✅',
      'worker_online': '👷',
      'system_warning': '⚠️',
      'error': '❌',
      'info': 'ℹ️'
    };
    return icons[type] || '📋';
  }

  updateActivity(activityData) {
    const feed = document.getElementById('activity-feed');
    if (!feed) return;

    // Handle both array and object formats
    let activities = [];
    if (Array.isArray(activityData)) {
      activities = activityData;
    } else if (activityData && activityData.events && Array.isArray(activityData.events)) {
      activities = activityData.events;
    }

    if (activities.length === 0) {
      feed.innerHTML = `
        <div class="activity-item">
          <div class="activity-item__icon">📋</div>
          <div class="activity-item__content">
            <div class="activity-item__title">No recent activity</div>
            <div class="activity-item__description">System is running quietly</div>
            <div class="activity-item__time">-</div>
          </div>
        </div>
      `;
      return;
    }

    feed.innerHTML = activities.map(activity => `
      <div class="activity-item">
        <div class="activity-item__icon">${activity.icon || this.getActivityIcon(activity.type)}</div>
        <div class="activity-item__content">
          <div class="activity-item__title">${activity.message || activity.title || 'System Event'}</div>
          <div class="activity-item__description">${this.getActivityDescription(activity)}</div>
          <div class="activity-item__time" data-timestamp="${activity.timestamp}" data-absolute="false">${this.timeManager.formatTime(activity.timestamp)}</div>
        </div>
      </div>
    `).join('');
  }

  getActivityDescription(activity) {
    // Create meaningful descriptions based on activity type and status
    if (activity.type === 'job') {
      return `Video processing pipeline • Status: ${activity.status}`;
    } else if (activity.type === 'system') {
      return activity.message.includes('worker') ? 'Worker pool management' : 'System monitoring';
    }
    return activity.description || 'System activity';
  }
}