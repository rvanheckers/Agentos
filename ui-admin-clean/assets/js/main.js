/**
 * AgentOS Admin - Main Application Entry Point
 * Clean, modular architecture with single responsibilities
 */

import { config } from '../../config/environment.js';
import { APIClient } from './api/client.js';
import { getCentralDataService } from './services/central-data-service.js';
// DatabaseSelector removed - using PostgreSQL only
import { Dashboard } from './views/Dashboard.js';
// import { WorkersView } from './views/Workers.js';  // REMOVED: Consolidated into AgentsWorkers.js
import { SystemControls } from './views/SystemControls.js';
import { JobHistory } from './views/JobHistory.js';
import { SystemLogs } from './views/SystemLogs.js';
import { Analytics } from './views/Analytics.js';
import { Configuration } from './views/Configuration.js';
import { AgentsWorkersView } from './views/AgentsWorkers.js';
import { ManagersView } from './views/Managers.js';

class App {
  constructor() {
    this.apiClient = new APIClient(config);
    this.centralDataService = getCentralDataService(this.apiClient);
    this.currentView = null;
    this.sidebar = null;
    this.databaseSelector = null;
    this.currentDatabase = 'dual'; // Default database mode
  }

  async init() {
    console.log('🚀 Initializing AgentOS Admin...');
    
    try {
      // 🚀 PERFORMANCE: Register Central Data Service globally for API client access
      window.centralDataService = this.centralDataService;
      console.log('💾 Central Data Service registered globally');
      
      // Start Central Data Service for caching
      this.centralDataService.start();
      console.log('🚀 Central Data Service started');
      
      this.setupLayout();
      this.setupNavigation();
      this.setupConnectionStatusHandler();
      this.setupAdminNotifications();
      this.setupStatusLegend();
      this.setupDevToolsFix();
      // Database selector removed - using PostgreSQL only
      this.setupRouting();
      await this.loadCurrentView();
      this.hideLoading();
      
      console.log('✅ AgentOS Admin initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize app:', error);
      this.showError('Failed to initialize application');
    }
  }

  setupLayout() {
    const app = document.getElementById('app');
    app.innerHTML = `
      <!-- Header -->
      <header class="header">
        <div class="header__left">
          <button class="mobile-menu-toggle" id="mobileMenuToggle">☰</button>
          <div class="header__logo">A</div>
          <h1 class="header__title">AgentOS Admin</h1>
        </div>
        <div class="header__right">
          <!-- Unified System Status (combines connection + system health) -->
          <div class="system-status" id="systemStatus">
            <div class="system-status__indicator">
              <div class="system-status__dot" id="systemStatusDot"></div>
              <span class="system-status__text" id="systemStatusText">System Starting...</span>
            </div>
            <button class="system-status__help" id="systemStatusHelp" title="Show status legend">
              ℹ️
            </button>
          </div>
        </div>
      </header>

      <!-- Sidebar -->
      <nav class="sidebar" id="sidebar">
        <div class="sidebar__content">
          <div class="sidebar__section">
            <div class="sidebar__section-title">📊 Activity Monitoring</div>
            <div class="sidebar__nav">
              <div class="sidebar__nav-item active" data-view="dashboard">
                <div class="sidebar__nav-icon">📊</div>
                Live Dashboard
              </div>
              <div class="sidebar__nav-item" data-view="queue">
                <div class="sidebar__nav-icon">📋</div>
                Jobs & Queue
              </div>
              <div class="sidebar__nav-item" data-view="analytics">
                <div class="sidebar__nav-icon">📈</div>
                Analytics
              </div>
              <div class="sidebar__nav-item" data-view="logs">
                <div class="sidebar__nav-icon">📜</div>
                Logs & Debug
              </div>
            </div>
          </div>
          
          <div class="sidebar__section">
            <div class="sidebar__section-title">🏗️ Framework Management</div>
            <div class="sidebar__nav">
              <div class="sidebar__nav-item" data-view="system-controls">
                <div class="sidebar__nav-icon">🎛️</div>
                System Control
              </div>
              <div class="sidebar__nav-item" data-view="agents-workers">
                <div class="sidebar__nav-icon">👷</div>
                Agents & Workers
              </div>
              <div class="sidebar__nav-item" data-view="managers">
                <div class="sidebar__nav-icon">🏢</div>
                Service Managers
              </div>
              <div class="sidebar__nav-item" data-view="config">
                <div class="sidebar__nav-icon">⚙️</div>
                Configuration
              </div>
              <div class="sidebar__nav-item" data-view="advanced-tools">
                <div class="sidebar__nav-icon">🔧</div>
                Advanced Tools
              </div>
            </div>
          </div>
          
          <div class="sidebar__section">
            <div class="sidebar__section-title">🚀 Quick Actions</div>
            <div class="sidebar__nav sidebar__nav--actions">
              <div class="sidebar__nav-item sidebar__nav-item--action" data-action="restart-system">
                <div class="sidebar__nav-icon">🔄</div>
                Restart System
              </div>
              <div class="sidebar__nav-item sidebar__nav-item--action" data-action="scale-workers">
                <div class="sidebar__nav-icon">⚡</div>
                Scale Workers
              </div>
              <div class="sidebar__nav-item sidebar__nav-item--action" data-action="clear-queue">
                <div class="sidebar__nav-icon">🧹</div>
                Clear Queue
              </div>
              <div class="sidebar__nav-item sidebar__nav-item--action" data-action="maintenance-mode">
                <div class="sidebar__nav-icon">🔧</div>
                Maintenance Mode
              </div>
            </div>
          </div>
        </div>
      </nav>

      <!-- Sidebar overlay for mobile -->
      <div class="sidebar-overlay" id="sidebarOverlay"></div>

      <!-- Main content -->
      <main class="main">
        <div class="main__content" id="mainContent">
          <!-- Content will be loaded here -->
        </div>
      </main>
    `;
  }

  setupNavigation() {
    // Mobile menu toggle
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    mobileToggle?.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      sidebarOverlay.classList.toggle('active');
    });

    // Close sidebar when clicking overlay
    sidebarOverlay?.addEventListener('click', () => {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.remove('active');
    });

    // Navigation items with DevTools-friendly event handling
    const navItems = document.querySelectorAll('.sidebar__nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', (e) => {
        // Prevent any event conflicts with DevTools
        e.preventDefault();
        e.stopPropagation();
        
        const view = e.currentTarget.dataset.view;
        const action = e.currentTarget.dataset.action;
        
        // Add small delay to prevent DevTools inspection conflicts
        requestAnimationFrame(() => {
          if (view) {
            this.navigateToView(view, e.currentTarget);
          } else if (action) {
            this.handleQuickAction(action);
          }
        });
      });
    });
  }

  setupConnectionStatusHandler() {
    console.log('🔌 Setting up connection status handler...');
    
    // Subscribe to connection status updates from CentralDataService
    this.centralDataService.subscribe('connection_status', (data) => {
      if (data.type === 'connection_status') {
        this.updateConnectionStatus(data.data);
      }
    });

    // Initialize connection status display
    this.updateConnectionStatus({
      connectionMode: 'connecting',
      timestamp: new Date().toISOString(),
      reconnectAttempts: 0,
      websocketConnected: false
    });
  }

  updateConnectionStatus(statusData) {
    const statusElement = document.getElementById('systemStatus');
    if (!statusElement) return;

    const dot = document.getElementById('systemStatusDot');
    const text = document.getElementById('systemStatusText');
    
    if (!dot || !text) return;

    // Update unified system status based on connection mode
    switch (statusData.connectionMode) {
      case 'websocket':
        dot.className = 'system-status__dot system-status__dot--realtime';
        text.textContent = 'System Online (Real-time)';
        statusElement.title = 'System healthy • WebSocket connected • Real-time updates active';
        console.log('🔌 System status: Real-time WebSocket mode');
        break;
        
      case 'polling':
        dot.className = 'system-status__dot system-status__dot--polling';
        text.textContent = 'System Online (Periodic refresh)';
        const attempts = statusData.reconnectAttempts > 0 ? ` • ${statusData.reconnectAttempts} reconnect attempts` : '';
        statusElement.title = `System healthy • Polling mode active • Updates every 30 seconds${attempts}`;
        console.log('🔄 System status: Polling mode');
        break;
        
      case 'connecting':
        dot.className = 'system-status__dot system-status__dot--connecting';
        text.textContent = 'System Starting...';
        statusElement.title = 'System initializing • Establishing data connection';
        console.log('🔌 System status: Starting up...');
        break;
        
      case 'disconnected':
        dot.className = 'system-status__dot system-status__dot--degraded';
        text.textContent = 'System Degraded';
        statusElement.title = 'System issues detected • Limited functionality available';
        console.log('❌ System status: Degraded service');
        break;
        
      default:
        dot.className = 'system-status__dot system-status__dot--unknown';
        text.textContent = 'System Status Unknown';
        statusElement.title = 'Unable to determine system health';
    }
  }

  setupAdminNotifications() {
    console.log('📢 Setting up admin notification system...');
    
    // Listen for admin notifications from CentralDataService
    window.addEventListener('admin-notification', (event) => {
      this.showNotification(event.detail);
    });

    // Create notification container if it doesn't exist
    if (!document.getElementById('notificationContainer')) {
      const container = document.createElement('div');
      container.id = 'notificationContainer';
      container.className = 'notification-container';
      document.body.appendChild(container);
    }
  }

  showNotification(notification) {
    const container = document.getElementById('notificationContainer');
    if (!container) return;

    // Create notification element
    const notificationEl = document.createElement('div');
    notificationEl.className = `notification notification--${notification.type}`;
    
    notificationEl.innerHTML = `
      <div class="notification__icon">
        ${notification.type === 'success' ? '✅' : 
          notification.type === 'warning' ? '⚠️' : 
          notification.type === 'error' ? '❌' : 'ℹ️'}
      </div>
      <div class="notification__content">
        <div class="notification__title">${notification.title}</div>
        <div class="notification__message">${notification.message}</div>
      </div>
      <button class="notification__close">×</button>
    `;

    // Add close functionality
    const closeBtn = notificationEl.querySelector('.notification__close');
    closeBtn.addEventListener('click', () => {
      this.removeNotification(notificationEl);
    });

    // Add to container
    container.appendChild(notificationEl);

    // Auto-remove after duration
    if (notification.duration) {
      setTimeout(() => {
        this.removeNotification(notificationEl);
      }, notification.duration);
    }

    console.log(`📢 Notification shown: ${notification.title}`);
  }

  removeNotification(notificationEl) {
    if (notificationEl && notificationEl.parentNode) {
      notificationEl.style.opacity = '0';
      notificationEl.style.transform = 'translateX(100%)';
      
      setTimeout(() => {
        if (notificationEl.parentNode) {
          notificationEl.parentNode.removeChild(notificationEl);
        }
      }, 300); // Match CSS transition duration
    }
  }

  setupStatusLegend() {
    console.log('ℹ️ Setting up status legend...');
    
    const helpButton = document.getElementById('systemStatusHelp');
    if (!helpButton) return;

    helpButton.addEventListener('click', () => {
      this.showStatusLegend();
    });
  }

  showStatusLegend() {
    // Create status legend modal/popup
    const legendModal = document.createElement('div');
    legendModal.className = 'status-legend-modal';
    legendModal.innerHTML = `
      <div class="status-legend-content">
        <div class="status-legend-header">
          <h3>System Status Guide</h3>
          <button class="status-legend-close">×</button>
        </div>
        <div class="status-legend-body">
          <div class="status-legend-item">
            <div class="status-legend-dot status-legend-dot--realtime"></div>
            <div class="status-legend-info">
              <strong>System Online (Real-time)</strong>
              <span>Live WebSocket connection active. Data updates instantly.</span>
            </div>
          </div>
          <div class="status-legend-item">
            <div class="status-legend-dot status-legend-dot--polling"></div>
            <div class="status-legend-info">
              <strong>System Online (Periodic refresh)</strong>
              <span>Backup mode active. Data refreshes every 30 seconds.</span>
            </div>
          </div>
          <div class="status-legend-item">
            <div class="status-legend-dot status-legend-dot--connecting"></div>
            <div class="status-legend-info">
              <strong>System Starting...</strong>
              <span>System initializing and establishing connections.</span>
            </div>
          </div>
          <div class="status-legend-item">
            <div class="status-legend-dot status-legend-dot--degraded"></div>
            <div class="status-legend-info">
              <strong>System Degraded</strong>
              <span>Issues detected. Limited functionality available.</span>
            </div>
          </div>
        </div>
        <div class="status-legend-footer">
          <small>Click the info button (ℹ️) anytime to view this guide</small>
        </div>
      </div>
    `;

    // Add to page
    document.body.appendChild(legendModal);

    // Add close functionality
    const closeBtn = legendModal.querySelector('.status-legend-close');
    const modal = legendModal;
    
    const closeLegend = () => {
      modal.style.opacity = '0';
      setTimeout(() => {
        if (modal.parentNode) {
          modal.parentNode.removeChild(modal);
        }
      }, 200);
    };

    closeBtn.addEventListener('click', closeLegend);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeLegend();
      }
    });

    // Escape key to close
    const escapeHandler = (e) => {
      if (e.key === 'Escape') {
        closeLegend();
        document.removeEventListener('keydown', escapeHandler);
      }
    };
    document.addEventListener('keydown', escapeHandler);

    console.log('ℹ️ Status legend displayed');
  }

  setupDevToolsFix() {
    // Prevent DevTools from making elements unresponsive
    const preventDevToolsFreeze = () => {
      // Remove any DevTools-injected styles that cause blur/disable
      const navItems = document.querySelectorAll('.sidebar__nav-item');
      navItems.forEach(item => {
        // Force remove any blocking styles
        item.style.pointerEvents = 'auto';
        item.style.opacity = '1';
        item.style.filter = 'none';
        item.style.userSelect = 'none';
      });
    };

    // Monitor for DevTools-injected changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
          const target = mutation.target;
          if (target.classList && target.classList.contains('sidebar__nav-item')) {
            // Force menu items to stay interactive
            setTimeout(() => {
              target.style.pointerEvents = 'auto';
              target.style.opacity = '1';
              target.style.filter = 'none';
            }, 0);
          }
        }
      });
    });

    // Observe the sidebar for style changes
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
      observer.observe(sidebar, {
        attributes: true,
        attributeFilter: ['style'],
        subtree: true
      });
    }

    // Periodically check and fix any DevTools interference
    setInterval(() => {
      const activeElement = document.querySelector('.sidebar__nav-item:hover');
      if (activeElement) {
        preventDevToolsFreeze();
      }
    }, 100);

    // Override DevTools element selection
    document.addEventListener('selectstart', (e) => {
      if (e.target && e.target.closest && e.target.closest('.sidebar__nav-item')) {
        e.preventDefault();
      }
    });
  }

  handleQuickAction(action) {
    switch (action) {
      case 'restart-system':
        if (confirm('Are you sure you want to restart the system?')) {
          this.restartSystem();
        }
        break;
      case 'scale-workers':
        this.scaleWorkers();
        break;
      case 'clear-queue':
        if (confirm('Are you sure you want to clear all pending jobs?')) {
          this.clearQueue();
        }
        break;
      case 'maintenance-mode':
        this.toggleMaintenanceMode();
        break;
      default:
        console.log('Unknown quick action:', action);
    }
  }

  async restartSystem() {
    try {
      console.log('🔄 Restarting system...');
      await this.apiClient.request('/api/admin/system/restart', { method: 'POST' });
      alert('✅ System restart initiated');
    } catch (error) {
      console.error('Failed to restart system:', error);
      alert('❌ Failed to restart system');
    }
  }

  async clearQueue() {
    try {
      console.log('🧹 Clearing queue...');
      await this.apiClient.request('/api/admin/queue/clear', { method: 'POST' });
      alert('✅ Queue cleared successfully');
    } catch (error) {
      console.error('Failed to clear queue:', error);
      alert('❌ Failed to clear queue');
    }
  }

  async scaleWorkers() {
    const count = prompt('How many workers to add? (Use negative number to remove)', '5');
    if (count && !isNaN(count)) {
      try {
        const numCount = parseInt(count);
        if (numCount > 0) {
          console.log(`⚡ Adding ${numCount} workers...`);
          alert(`✅ Request to add ${numCount} workers sent`);
        } else {
          console.log(`⚡ Removing ${Math.abs(numCount)} workers...`);
          alert(`✅ Request to remove ${Math.abs(numCount)} workers sent`);
        }
        // TODO: Call actual API endpoint when available
        // await this.apiClient.request('/api/admin/workers/scale', { method: 'POST', body: JSON.stringify({ count: numCount }) });
      } catch (error) {
        console.error('Failed to scale workers:', error);
        alert('❌ Failed to scale workers');
      }
    }
  }

  async toggleMaintenanceMode() {
    try {
      console.log('🔧 Toggling maintenance mode...');
      const result = await this.apiClient.request('/api/admin/maintenance-toggle', { method: 'POST' });
      const status = result.data?.maintenance_mode ? 'enabled' : 'disabled';
      alert(`✅ Maintenance mode ${status}`);
    } catch (error) {
      console.error('Failed to toggle maintenance mode:', error);
      alert('❌ Failed to toggle maintenance mode');
    }
  }

  // Database selector methods removed - using PostgreSQL only

  showDatabaseSwitchNotification(database, metrics) {
    // Create a temporary notification
    const notification = document.createElement('div');
    notification.className = 'database-switch-notification';
    notification.innerHTML = `
      <div class="notification-content">
        <div class="notification-icon">🔄</div>
        <div class="notification-text">
          <div class="notification-title">Database switched to ${database.toUpperCase()}</div>
          <div class="notification-details">Response time: ${metrics.responseTime}ms</div>
        </div>
      </div>
    `;
    
    // Add notification styles
    notification.style.cssText = `
      position: fixed;
      top: 80px;
      right: 20px;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
      z-index: 1001;
      transform: translateX(100%);
      transition: transform 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
      notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        document.body.removeChild(notification);
      }, 300);
    }, 3000);
  }

  setupRouting() {
    // Handle browser back/forward buttons
    window.addEventListener('popstate', () => {
      this.loadCurrentView();
    });
  }

  getCurrentViewFromURL() {
    const hash = window.location.hash.slice(1); // Remove #
    return hash || 'dashboard'; // Default to dashboard
  }

  async loadCurrentView() {
    const viewName = this.getCurrentViewFromURL();
    
    // Update active sidebar item
    document.querySelectorAll('.sidebar__nav-item').forEach(item => {
      item.classList.remove('active');
      if (item.dataset.view === viewName) {
        item.classList.add('active');
      }
    });
    
    await this.loadView(viewName);
  }

  async navigateToView(viewName, navItem) {
    try {
      // Prevent DevTools focus conflicts
      if (document.activeElement && document.activeElement !== document.body) {
        document.activeElement.blur();
      }
      
      // Update URL without page reload
      window.history.pushState({}, '', `#${viewName}`);
      
      // Update active navigation with null checks
      document.querySelectorAll('.sidebar__nav-item').forEach(item => {
        item.classList.remove('active');
      });
      if (navItem) {
        navItem.classList.add('active');
      }

      // Close mobile sidebar with null checks
      const sidebar = document.getElementById('sidebar');
      const sidebarOverlay = document.getElementById('sidebarOverlay');
      if (sidebar) sidebar.classList.remove('open');
      if (sidebarOverlay) sidebarOverlay.classList.remove('active');

      // Load view with proper error handling
      await this.loadView(viewName);
      
    } catch (error) {
      console.error(`Navigation failed for ${viewName}:`, error);
      this.showError(`Failed to navigate to ${viewName} view`);
    }
  }

  async loadView(viewName) {
    const container = document.getElementById('mainContent');
    
    // Destroy current view
    if (this.currentView?.destroy) {
      this.currentView.destroy();
    }

    switch (viewName) {
      case 'dashboard':
        await this.loadDashboard();
        break;
      case 'agents-workers':
        await this.loadAgentsWorkers();
        break;
      case 'queue':
        await this.loadJobHistory(); // Use new redesigned Jobs & Queue view
        break;
      case 'advanced-tools':
        await this.loadAdvancedTools();
        break;
      case 'system-controls':
        await this.loadSystemControls();
        break;
      case 'history':
        await this.loadJobHistory();
        break;
      case 'analytics':
        await this.loadAnalytics();
        break;
      case 'logs':
        await this.loadSystemLogs();
        break;
      case 'config':
        await this.loadConfiguration();
        break;
      case 'managers':
        await this.loadManagers();
        break;
      default:
        container.innerHTML = `
          <div class="page-header">
            <h1 class="page-header__title">${viewName.charAt(0).toUpperCase() + viewName.slice(1)}</h1>
            <p class="page-header__description">This view is not implemented yet.</p>
          </div>
          <div class="dashboard__section">
            <p>The ${viewName} view will be available in a future update.</p>
          </div>
        `;
        this.currentView = null;
    }
  }


  async loadDashboard() {
    const container = document.getElementById('mainContent');
    this.currentView = new Dashboard(this.apiClient, container);
    await this.currentView.init();
  }

  async loadAgentsWorkers() {
    const container = document.getElementById('mainContent');
    // Combined Agents & Workers view as per ADMIN_FRAMEWORK_MANAGEMENT_PLAN.md
    this.currentView = new AgentsWorkersView(this.apiClient);
    await this.currentView.init(container);
  }

  async loadAdvancedTools() {
    const container = document.getElementById('mainContent');
    container.innerHTML = `
      <div class="page-header">
        <h1 class="page-header__title">🔧 Advanced Tools</h1>
        <p class="page-header__description">Log analysis, performance tuning, debug interfaces, and configuration import/export</p>
      </div>
      <div class="dashboard__section">
        <h3>🚧 Under Development</h3>
        <p>Advanced Tools view will include:</p>
        <ul>
          <li>📊 Log analysis tools</li>
          <li>⚡ Performance tuning</li>
          <li>🐛 Debug interfaces</li>
          <li>📤 Import/export configs</li>
        </ul>
        <p><strong>Coming in Phase 4 of the implementation roadmap.</strong></p>
      </div>
    `;
    this.currentView = null;
  }

  async loadQueue() {
    // Redirect to new Jobs & Queue implementation
    await this.loadJobHistory();
  }

  async loadWorkers() {
    // REDIRECT: Workers view is now part of AgentsWorkers consolidated view
    await this.loadAgentsWorkers();
  }


  async loadSystemControls() {
    const container = document.getElementById('mainContent');
    this.currentView = new SystemControls(this.apiClient);
    await this.currentView.init(container);
  }

  async loadJobHistory() {
    const container = document.getElementById('mainContent');
    this.currentView = new JobHistory(this.apiClient, container);
    await this.currentView.init();
  }

  async loadAnalytics() {
    const container = document.getElementById('mainContent');
    this.currentView = new Analytics(this.apiClient, container);
    await this.currentView.init();
  }

  async loadSystemLogs() {
    const container = document.getElementById('mainContent');
    this.currentView = new SystemLogs(this.apiClient, container);
    await this.currentView.init();
  }

  async loadConfiguration() {
    const container = document.getElementById('mainContent');
    this.currentView = new Configuration(this.apiClient, container);
    await this.currentView.init();
  }

  async loadManagers() {
    const container = document.getElementById('mainContent');
    this.currentView = new ManagersView(this.apiClient);
    await this.currentView.init(container);
  }

  hideLoading() {
    const loading = document.getElementById('loading');
    const app = document.getElementById('app');
    
    loading.classList.add('hidden');
    app.classList.remove('hidden');
  }

  showError(message) {
    console.error(message);
    // Could implement a toast notification system here
    alert(message); // Temporary error display
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  try {
    console.log('🔧 DOM loaded, initializing app...');
    const app = new App();
    window.adminApp = app;  // Make app globally accessible for status updates
    app.init();
  } catch (error) {
    console.error('💥 Failed to initialize app:', error);
    
    // Show error in loading screen
    const loading = document.getElementById('loading');
    if (loading) {
      loading.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: #dc2626;">
          <h2>⚠️ Initialization Error</h2>
          <p>Failed to load the admin dashboard.</p>
          <details style="margin-top: 1rem; text-align: left;">
            <summary>Error Details</summary>
            <pre style="background: #f3f4f6; padding: 1rem; border-radius: 0.5rem; margin-top: 0.5rem;">${error.message}\n${error.stack}</pre>
          </details>
          <p style="margin-top: 1rem;">
            <button onclick="location.reload()" style="padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 0.25rem; cursor: pointer;">
              🔄 Retry
            </button>
          </p>
        </div>
      `;
    }
  }
});

// Global error handler for unhandled errors
window.addEventListener('error', (event) => {
  console.error('💥 Global error:', event.error);
});

// Global handler for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.error('💥 Unhandled promise rejection:', event.reason);
});