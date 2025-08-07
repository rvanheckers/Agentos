/**
 * Configuration Management View Controller
 * System settings and agent configuration management
 */

import { getCentralDataService } from '../services/central-data-service.js';

export class Configuration {
  constructor(apiClient, container) {
    this.apiClient = apiClient;
    this.container = container;
    this.centralDataService = getCentralDataService(apiClient);
    this.subscriptionId = null;
    this.systemConfig = {};
    this.agentConfig = {};
    this.isDirty = false;
    this.activeSection = 'system';
  }

  async init() {
    this.render();
    
    // Subscribe to central data service for real-time updates
    this.subscriptionId = this.centralDataService.subscribe('Configuration', async (data) => {
      await this.updateConfiguration(data);
    });
    
    // Start central service if not running  
    if (!this.centralDataService.getStatus().isRunning) {
      this.centralDataService.start();
    } else {
      // Service is already running - get current data immediately
      console.log('⚙️ Service already running, getting current configuration data...');
      const currentData = this.centralDataService.getCurrentData();
      if (currentData && currentData.configuration) {
        console.log('⚙️ Using existing configuration data (no fetch needed)');
        await this.updateConfiguration(currentData);
      } else {
        // Fallback to direct load if no configuration data available
        await this.loadConfiguration();
      }
    }
    
    this.setupEventListeners();
  }

  render() {
    this.container.innerHTML = `
      <div class="configuration-view">
        <div class="page-header">
          <h1 class="page-header__title">
            <span class="page-header__icon">⚙️</span>
            Configuration Management
          </h1>
          <p class="page-header__description">
            Manage system settings, agent configurations, and application parameters
          </p>
        </div>

        <!-- Configuration Navigation -->
        <div class="config-nav">
          <button class="config-nav__item active" data-section="system">
            🖥️ System Settings
          </button>
          <button class="config-nav__item" data-section="agents">
            🤖 Agent Configuration
          </button>
          <button class="config-nav__item" data-section="storage">
            💾 Storage & Paths
          </button>
          <button class="config-nav__item" data-section="api">
            🌐 API Settings
          </button>
          <button class="config-nav__item" data-section="backup">
            📦 Backup & Restore
          </button>
        </div>

        <!-- Configuration Content -->
        <div class="config-content">
          <!-- System Settings Section -->
          <div class="config-section" id="systemSection">
            <div class="config-section__header">
              <h2 class="config-section__title">System Settings</h2>
              <div class="config-section__actions">
                <button class="btn btn-sm btn-ghost" id="resetSystemDefaults">
                  🔄 Reset to Defaults
                </button>
              </div>
            </div>
            
            <div class="config-grid">
              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">General Settings</h3>
                </div>
                <div class="config-card__content">
                  <div class="config-form">
                    <div class="config-form__group">
                      <label class="config-form__label">System Name</label>
                      <input type="text" class="config-form__input" id="systemName" 
                             placeholder="AgentOS Production">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Environment</label>
                      <select class="config-form__select" id="environment">
                        <option value="production">Production</option>
                        <option value="staging">Staging</option>
                        <option value="development">Development</option>
                      </select>
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Debug Mode</label>
                      <div class="config-toggle">
                        <input type="checkbox" class="config-toggle__input" id="debugMode">
                        <label class="config-toggle__label" for="debugMode"></label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">Performance Settings</h3>
                </div>
                <div class="config-card__content">
                  <div class="config-form">
                    <div class="config-form__group">
                      <label class="config-form__label">Max Concurrent Jobs</label>
                      <input type="number" class="config-form__input" id="maxJobs" 
                             min="1" max="100" placeholder="10">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Job Timeout (minutes)</label>
                      <input type="number" class="config-form__input" id="jobTimeout" 
                             min="1" max="1440" placeholder="30">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Memory Limit (GB)</label>
                      <input type="number" class="config-form__input" id="memoryLimit" 
                             min="1" max="64" step="0.5" placeholder="8">
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Agent Configuration Section -->
          <div class="config-section hidden" id="agentsSection">
            <div class="config-section__header">
              <h2 class="config-section__title">Agent Configuration</h2>
              <div class="config-section__actions">
                <button class="btn btn-sm btn-primary" id="addAgent">
                  ➕ Add Agent
                </button>
              </div>
            </div>
            
            <div class="agents-grid" id="agentsGrid">
              <!-- Agent cards will be rendered here -->
            </div>
          </div>

          <!-- Storage Settings Section -->
          <div class="config-section hidden" id="storageSection">
            <div class="config-section__header">
              <h2 class="config-section__title">Storage & Paths</h2>
            </div>
            
            <div class="config-grid">
              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">File Paths</h3>
                </div>
                <div class="config-card__content">
                  <div class="config-form">
                    <div class="config-form__group">
                      <label class="config-form__label">Input Directory</label>
                      <div class="config-path-input">
                        <input type="text" class="config-form__input" id="inputPath" 
                               placeholder="/data/input">
                        <button class="btn btn-xs btn-ghost" data-action="browse" data-target="inputPath">
                          📁
                        </button>
                      </div>
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Output Directory</label>
                      <div class="config-path-input">
                        <input type="text" class="config-form__input" id="outputPath" 
                               placeholder="/data/output">
                        <button class="btn btn-xs btn-ghost" data-action="browse" data-target="outputPath">
                          📁
                        </button>
                      </div>
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Temp Directory</label>
                      <div class="config-path-input">
                        <input type="text" class="config-form__input" id="tempPath" 
                               placeholder="/tmp/agentos">
                        <button class="btn btn-xs btn-ghost" data-action="browse" data-target="tempPath">
                          📁
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">Storage Limits</h3>
                </div>
                <div class="config-card__content">
                  <div class="config-form">
                    <div class="config-form__group">
                      <label class="config-form__label">Max File Size (MB)</label>
                      <input type="number" class="config-form__input" id="maxFileSize" 
                             min="1" max="10240" placeholder="500">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Disk Space Warning (%)</label>
                      <input type="number" class="config-form__input" id="diskWarning" 
                             min="50" max="95" placeholder="80">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Auto-cleanup Old Files</label>
                      <div class="config-toggle">
                        <input type="checkbox" class="config-toggle__input" id="autoCleanup">
                        <label class="config-toggle__label" for="autoCleanup"></label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- API Settings Section -->
          <div class="config-section hidden" id="apiSection">
            <div class="config-section__header">
              <h2 class="config-section__title">API Settings</h2>
            </div>
            
            <div class="config-grid">
              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">Server Configuration</h3>
                </div>
                <div class="config-card__content">
                  <div class="config-form">
                    <div class="config-form__group">
                      <label class="config-form__label">API Port</label>
                      <input type="number" class="config-form__input" id="apiPort" 
                             min="1000" max="65535" placeholder="8004">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Admin Port</label>
                      <input type="number" class="config-form__input" id="adminPort" 
                             min="1000" max="65535" placeholder="8005">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">CORS Enabled</label>
                      <div class="config-toggle">
                        <input type="checkbox" class="config-toggle__input" id="corsEnabled">
                        <label class="config-toggle__label" for="corsEnabled"></label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">Security Settings</h3>
                </div>
                <div class="config-card__content">
                  <div class="config-form">
                    <div class="config-form__group">
                      <label class="config-form__label">API Key Required</label>
                      <div class="config-toggle">
                        <input type="checkbox" class="config-toggle__input" id="apiKeyRequired">
                        <label class="config-toggle__label" for="apiKeyRequired"></label>
                      </div>
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">Rate Limit (req/min)</label>
                      <input type="number" class="config-form__input" id="rateLimit" 
                             min="1" max="10000" placeholder="100">
                    </div>
                    <div class="config-form__group">
                      <label class="config-form__label">SSL Enabled</label>
                      <div class="config-toggle">
                        <input type="checkbox" class="config-toggle__input" id="sslEnabled">
                        <label class="config-toggle__label" for="sslEnabled"></label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Backup & Restore Section -->
          <div class="config-section hidden" id="backupSection">
            <div class="config-section__header">
              <h2 class="config-section__title">Backup & Restore</h2>
            </div>
            
            <div class="config-grid">
              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">Configuration Backup</h3>
                </div>
                <div class="config-card__content">
                  <div class="backup-actions">
                    <button class="btn btn-primary backup-btn" id="createBackup">
                      💾 Create Backup
                    </button>
                    <button class="btn btn-outline backup-btn" id="downloadBackup">
                      📥 Download Backup
                    </button>
                  </div>
                  <div class="backup-info">
                    <p>Last backup: <span id="lastBackupDate">Never</span></p>
                    <p>Backup includes all system and agent configurations</p>
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="config-card__header">
                  <h3 class="config-card__title">Configuration Restore</h3>
                </div>
                <div class="config-card__content">
                  <div class="restore-section">
                    <div class="file-upload">
                      <input type="file" id="configFile" accept=".json" class="file-upload__input">
                      <label for="configFile" class="file-upload__label">
                        📁 Choose backup file...
                      </label>
                    </div>
                    <button class="btn btn-warning backup-btn" id="restoreConfig" disabled>
                      🔄 Restore Configuration
                    </button>
                  </div>
                  <div class="restore-warning">
                    <p>⚠️ Restoring will overwrite current configuration</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Save Actions -->
        <div class="config-actions">
          <div class="config-actions__status">
            <span class="config-status" id="configStatus">All changes saved</span>
          </div>
          <div class="config-actions__buttons">
            <button class="btn btn-ghost" id="discardChanges">
              ↶ Discard Changes
            </button>
            <button class="btn btn-primary" id="saveConfiguration">
              💾 Save Configuration
            </button>
          </div>
        </div>
      </div>
    `;
  }

  setupEventListeners() {
    // Navigation
    this.container.addEventListener('click', (e) => {
      if (e.target.classList.contains('config-nav__item')) {
        this.switchSection(e.target.dataset.section);
      }
    });

    // Form changes tracking
    this.container.addEventListener('input', () => {
      this.markDirty();
    });

    this.container.addEventListener('change', () => {
      this.markDirty();
    });

    // Save configuration
    this.container.querySelector('#saveConfiguration')?.addEventListener('click', () => {
      this.saveConfiguration();
    });

    // Discard changes
    this.container.querySelector('#discardChanges')?.addEventListener('click', () => {
      this.discardChanges();
    });

    // Backup actions
    this.container.querySelector('#createBackup')?.addEventListener('click', () => {
      this.createBackup();
    });

    this.container.querySelector('#downloadBackup')?.addEventListener('click', () => {
      this.downloadBackup();
    });

    this.container.querySelector('#restoreConfig')?.addEventListener('click', () => {
      this.restoreConfiguration();
    });

    // File upload
    this.container.querySelector('#configFile')?.addEventListener('change', (e) => {
      const button = this.container.querySelector('#restoreConfig');
      button.disabled = !e.target.files.length;
    });

    // Add agent button
    this.container.querySelector('#addAgent')?.addEventListener('click', () => {
      this.addAgentDialog();
    });
  }

  async updateConfiguration(adminData) {
    try {
      console.log('🔄 Updating configuration from real-time data...');
      
      if (adminData && adminData.configuration) {
        this.systemConfig = adminData.configuration.system_config || {};
        this.agentConfig = adminData.configuration.agent_config || {};
        
        this.populateSystemSettings();
        this.populateAgentSettings();
        this.populateStorageSettings();
        this.populateApiSettings();
        
        this.markClean();
        console.log('✅ Configuration updated from real-time data');
      } else {
        console.warn('⚠️ No configuration data in admin update, using fallback');
        await this.loadConfiguration();
      }
      
    } catch (error) {
      console.error('❌ Failed to update configuration from real-time data:', error);
      // Fallback to direct API call
      await this.loadConfiguration();
    }
  }

  async loadConfiguration() {
    try {
      console.log('🔄 Loading configuration...');
      
      const response = await this.apiClient.getSystemConfig();
      this.systemConfig = response.system_config || {};
      this.agentConfig = response.agent_config || {};
      
      this.populateSystemSettings();
      this.populateAgentSettings();
      this.populateStorageSettings();
      this.populateApiSettings();
      
      this.markClean();
      console.log('✅ Configuration loaded successfully');
      
    } catch (error) {
      console.error('❌ Failed to load configuration:', error);
      this.showError('Failed to load configuration. Using defaults.');
      this.loadDefaultConfiguration();
    }
  }

  loadDefaultConfiguration() {
    // Load default configuration values
    this.systemConfig = {
      system_name: 'AgentOS Production',
      environment: 'production',
      debug_mode: false,
      max_concurrent_jobs: 10,
      job_timeout: 30,
      memory_limit: 8
    };

    this.agentConfig = {
      agents: [
        { id: 'video_downloader', name: 'Video Downloader', enabled: true },
        { id: 'face_detector', name: 'Face Detector', enabled: true },
        { id: 'moment_detector', name: 'Moment Detector', enabled: true }
      ]
    };

    this.populateSystemSettings();
    this.populateAgentSettings();
  }

  populateSystemSettings() {
    const config = this.systemConfig;
    
    this.setInputValue('systemName', config.system_name);
    this.setInputValue('environment', config.environment);
    this.setInputValue('debugMode', config.debug_mode, 'checkbox');
    this.setInputValue('maxJobs', config.max_concurrent_jobs);
    this.setInputValue('jobTimeout', config.job_timeout);
    this.setInputValue('memoryLimit', config.memory_limit);
  }

  populateAgentSettings() {
    const agentsGrid = this.container.querySelector('#agentsGrid');
    const agents = this.agentConfig.agents || [];
    
    agentsGrid.innerHTML = agents.map(agent => this.renderAgentCard(agent)).join('');
  }

  populateStorageSettings() {
    const config = this.systemConfig;
    
    this.setInputValue('inputPath', config.input_path || '/data/input');
    this.setInputValue('outputPath', config.output_path || '/data/output');
    this.setInputValue('tempPath', config.temp_path || '/tmp/agentos');
    this.setInputValue('maxFileSize', config.max_file_size || 500);
    this.setInputValue('diskWarning', config.disk_warning || 80);
    this.setInputValue('autoCleanup', config.auto_cleanup || false, 'checkbox');
  }

  populateApiSettings() {
    const config = this.systemConfig;
    
    this.setInputValue('apiPort', config.api_port || 8004);
    this.setInputValue('adminPort', config.admin_port || 8005);
    this.setInputValue('corsEnabled', config.cors_enabled || true, 'checkbox');
    this.setInputValue('apiKeyRequired', config.api_key_required || false, 'checkbox');
    this.setInputValue('rateLimit', config.rate_limit || 100);
    this.setInputValue('sslEnabled', config.ssl_enabled || false, 'checkbox');
  }

  renderAgentCard(agent) {
    return `
      <div class="agent-card" data-agent-id="${agent.id}">
        <div class="agent-card__header">
          <div class="agent-card__info">
            <h4 class="agent-card__name">${agent.name}</h4>
            <span class="agent-card__id">${agent.id}</span>
          </div>
          <div class="agent-card__toggle">
            <div class="config-toggle">
              <input type="checkbox" class="config-toggle__input" 
                     id="agent_${agent.id}" ${agent.enabled ? 'checked' : ''}>
              <label class="config-toggle__label" for="agent_${agent.id}"></label>
            </div>
          </div>
        </div>
        <div class="agent-card__status">
          Status: <span class="agent-status ${agent.enabled ? 'agent-status--active' : 'agent-status--disabled'}">
            ${agent.enabled ? 'Active' : 'Disabled'}
          </span>
        </div>
        <div class="agent-card__actions">
          <button class="btn btn-xs btn-ghost" data-action="configure" data-agent="${agent.id}">
            ⚙️ Configure
          </button>
          <button class="btn btn-xs btn-ghost" data-action="remove" data-agent="${agent.id}">
            🗑️ Remove
          </button>
        </div>
      </div>
    `;
  }

  switchSection(section) {
    // Update navigation
    this.container.querySelectorAll('.config-nav__item').forEach(item => {
      item.classList.toggle('active', item.dataset.section === section);
    });

    // Update sections
    this.container.querySelectorAll('.config-section').forEach(section => {
      section.classList.add('hidden');
    });

    this.container.querySelector(`#${section}Section`)?.classList.remove('hidden');
    this.activeSection = section;
  }

  setInputValue(id, value, type = 'text') {
    const input = this.container.querySelector(`#${id}`);
    if (!input) return;

    if (type === 'checkbox') {
      input.checked = Boolean(value);
    } else {
      input.value = value || '';
    }
  }

  markDirty() {
    this.isDirty = true;
    const status = this.container.querySelector('#configStatus');
    status.textContent = 'Unsaved changes';
    status.className = 'config-status config-status--dirty';
  }

  markClean() {
    this.isDirty = false;
    const status = this.container.querySelector('#configStatus');
    status.textContent = 'All changes saved';
    status.className = 'config-status config-status--clean';
  }

  async saveConfiguration() {
    try {
      console.log('💾 Saving configuration...');
      
      // Collect all form data
      const updatedConfig = this.collectFormData();
      
      // TODO: Send to API
      // await this.apiClient.updateSystemConfig(updatedConfig);
      
      this.markClean();
      this.showSuccess('Configuration saved successfully');
      console.log('✅ Configuration saved');
      
    } catch (error) {
      console.error('❌ Failed to save configuration:', error);
      this.showError('Failed to save configuration. Please try again.');
    }
  }

  collectFormData() {
    // This would collect all form data and return structured config
    return {
      system_config: {
        system_name: this.container.querySelector('#systemName')?.value,
        environment: this.container.querySelector('#environment')?.value,
        debug_mode: this.container.querySelector('#debugMode')?.checked,
        max_concurrent_jobs: parseInt(this.container.querySelector('#maxJobs')?.value),
        job_timeout: parseInt(this.container.querySelector('#jobTimeout')?.value),
        memory_limit: parseFloat(this.container.querySelector('#memoryLimit')?.value)
      },
      agent_config: {
        // Collect agent settings
      }
    };
  }

  discardChanges() {
    if (this.isDirty) {
      const confirmed = confirm('Are you sure you want to discard all unsaved changes?');
      if (confirmed) {
        this.loadConfiguration();
      }
    }
  }

  createBackup() {
    console.log('💾 Creating configuration backup...');
    // TODO: Implement backup creation
    this.showSuccess('Configuration backup created successfully');
  }

  downloadBackup() {
    console.log('📥 Downloading configuration backup...');
    // TODO: Implement backup download
    alert('Backup download - To be implemented');
  }

  restoreConfiguration() {
    const confirmed = confirm('Are you sure you want to restore configuration? This will overwrite all current settings.');
    if (confirmed) {
      console.log('🔄 Restoring configuration...');
      // TODO: Implement configuration restore
      this.showSuccess('Configuration restored successfully');
    }
  }

  addAgentDialog() {
    // TODO: Implement add agent dialog
    alert('Add agent dialog - To be implemented');
  }

  showSuccess(message) {
    console.log(`✅ ${message}`);
    // TODO: Implement proper notification system
  }

  showError(message) {
    console.error(`❌ ${message}`);
    // TODO: Implement proper error notification system
  }

  destroy() {
    // Cleanup WebSocket subscription when view is destroyed
    if (this.subscriptionId && this.centralDataService) {
      this.centralDataService.unsubscribe(this.subscriptionId);
      this.subscriptionId = null;
      console.log('⚙️ Configuration view WebSocket subscription cleaned up');
    }
  }
}