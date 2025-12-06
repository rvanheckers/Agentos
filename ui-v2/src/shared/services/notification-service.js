/**
 * Notification Service
 * Handles user notifications en feedback
 */

export class NotificationService {
  constructor() {
    this.container = null;
    this.notifications = new Map();
    this.setupContainer();
  }

  /**
   * Setup notification container
   */
  setupContainer() {
    this.container = document.getElementById('notificationContainer');
    if (!this.container) {
      console.warn('Notification container not found');
    }
  }

  /**
   * Show success notification
   */
  showSuccess(message, options = {}) {
    return this.show(message, 'success', options);
  }

  /**
   * Show error notification
   */
  showError(message, options = {}) {
    return this.show(message, 'error', { duration: 0, ...options });
  }

  /**
   * Show warning notification
   */
  showWarning(message, options = {}) {
    return this.show(message, 'warning', options);
  }

  /**
   * Show info notification
   */
  showInfo(message, options = {}) {
    return this.show(message, 'info', options);
  }

  /**
   * Show notification
   */
  show(message, type = 'info', options = {}) {
    if (!this.container) {
      console.warn('Cannot show notification: container not found');
      return null;
    }

    const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const duration = options.duration !== undefined ? options.duration : 5000;
    const closable = options.closable !== false;

    const notification = this.createNotificationElement(id, message, type, closable);
    
    // Add to container
    this.container.appendChild(notification);
    
    // Store reference
    this.notifications.set(id, {
      element: notification,
      timeout: null
    });

    // Animate in
    setTimeout(() => {
      notification.classList.add('show');
    }, 10);

    // Auto-hide
    if (duration > 0) {
      const timeout = setTimeout(() => {
        this.hide(id);
      }, duration);
      
      this.notifications.get(id).timeout = timeout;
    }

    return id;
  }

  /**
   * Create notification element
   */
  createNotificationElement(id, message, type, closable) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.id = id;

    const icon = this.getTypeIcon(type);
    
    notification.innerHTML = `
      <div class="notification-content">
        <div class="notification-icon">
          ${icon}
        </div>
        <div class="notification-message">
          ${message}
        </div>
        ${closable ? `
          <button class="notification-close" onclick="window.vibeCoder?.notificationService?.hide('${id}')">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
            </svg>
          </button>
        ` : ''}
      </div>
      <div class="notification-progress"></div>
    `;

    return notification;
  }

  /**
   * Get icon for notification type
   */
  getTypeIcon(type) {
    const icons = {
      success: `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
      `,
      error: `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
      `,
      warning: `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
      `,
      info: `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
        </svg>
      `
    };

    return icons[type] || icons.info;
  }

  /**
   * Hide notification
   */
  hide(id) {
    const notification = this.notifications.get(id);
    if (!notification) return;

    // Clear timeout
    if (notification.timeout) {
      clearTimeout(notification.timeout);
    }

    // Animate out
    notification.element.classList.add('hiding');
    
    setTimeout(() => {
      if (notification.element.parentNode) {
        notification.element.parentNode.removeChild(notification.element);
      }
      this.notifications.delete(id);
    }, 300);
  }

  /**
   * Hide all notifications
   */
  hideAll() {
    this.notifications.forEach((_, id) => {
      this.hide(id);
    });
  }

  /**
   * Show loading notification
   */
  showLoading(message, options = {}) {
    const id = this.show(`
      <div class="loading-notification">
        <div class="loading-spinner-small"></div>
        <span>${message}</span>
      </div>
    `, 'info', { duration: 0, closable: false, ...options });
    
    return id;
  }

  /**
   * Update notification message
   */
  update(id, message, type = null) {
    const notification = this.notifications.get(id);
    if (!notification) return;

    const messageElement = notification.element.querySelector('.notification-message');
    if (messageElement) {
      messageElement.innerHTML = message;
    }

    if (type) {
      notification.element.className = `notification ${type}`;
      const iconElement = notification.element.querySelector('.notification-icon');
      if (iconElement) {
        iconElement.innerHTML = this.getTypeIcon(type);
      }
    }
  }

  /**
   * Show processing progress notification
   */
  showProgress(message, progress = 0) {
    const id = `progress_${Date.now()}`;
    
    const notification = this.show(`
      <div class="progress-notification">
        <div class="progress-message">${message}</div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${progress}%"></div>
        </div>
        <div class="progress-text">${Math.round(progress)}%</div>
      </div>
    `, 'info', { duration: 0, closable: false });

    return notification;
  }

  /**
   * Update progress notification
   */
  updateProgress(id, progress, message = null) {
    const notification = this.notifications.get(id);
    if (!notification) return;

    const progressFill = notification.element.querySelector('.progress-fill');
    const progressText = notification.element.querySelector('.progress-text');
    const progressMessage = notification.element.querySelector('.progress-message');

    if (progressFill) {
      progressFill.style.width = `${progress}%`;
    }
    
    if (progressText) {
      progressText.textContent = `${Math.round(progress)}%`;
    }
    
    if (message && progressMessage) {
      progressMessage.textContent = message;
    }
  }
}

// Add notification styles to CSS
const notificationStyles = `
.notification {
  opacity: 0;
  transform: translateX(100%);
  transition: all 0.3s ease;
  margin-bottom: var(--space-2);
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  position: relative;
  overflow: hidden;
}

.notification.show {
  opacity: 1;
  transform: translateX(0);
}

.notification.hiding {
  opacity: 0;
  transform: translateX(100%);
}

.notification-content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  flex: 1;
}

.notification-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.notification.success .notification-icon {
  color: var(--success-500);
}

.notification.error .notification-icon {
  color: var(--danger-500);
}

.notification.warning .notification-icon {
  color: var(--warning-500);
}

.notification.info .notification-icon {
  color: var(--primary-500);
}

.notification-message {
  flex: 1;
  font-size: var(--text-sm);
  line-height: 1.4;
}

.notification-close {
  background: none;
  border: none;
  color: var(--gray-500);
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
  flex-shrink: 0;
}

.notification-close:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--gray-700);
}

.loading-notification {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.loading-spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--gray-300);
  border-top: 2px solid var(--primary-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.progress-notification {
  min-width: 200px;
}

.progress-message {
  font-size: var(--text-sm);
  margin-bottom: var(--space-2);
}

.progress-bar {
  height: 6px;
  background: var(--gray-200);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--space-2);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-500), var(--primary-400));
  transition: width 0.3s ease;
}

.progress-text {
  font-size: var(--text-xs);
  color: var(--gray-600);
  text-align: right;
}
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = notificationStyles;
  document.head.appendChild(styleElement);
}

export default NotificationService;