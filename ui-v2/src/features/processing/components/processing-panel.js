/**
 * Processing Panel Component
 * Manages real-time video processing visualization and updates
 * 
 * Features:
 * - Real-time WebSocket updates
 * - Progress visualization
 * - Processing step tracking
 * - Cancel/pause functionality
 * - Store integration
 */

import { storeManager } from '../../../infrastructure/state/store-manager.js';
import { ProcessingService } from '../services/processing-service.js';
import { AsyncJobService } from '../services/async-job-service.js';
import { websocketService } from '../../../shared/services/websocket-service.js';
import i18n from '../../../i18n/utils/i18n.js';

export class ProcessingPanel {
  constructor(container, dependencies = {}) {
    this.container = container;
    this.stores = dependencies.stores || storeManager;
    this.apiClient = dependencies.apiClient;
    this.processingService = new ProcessingService(this.apiClient);
    this.asyncJobService = new AsyncJobService(this.apiClient);
    
    // State
    this.isProcessing = false;
    this.currentStep = 'analyzing';
    this.progress = {
      analyzing: 0,
      extracting: 0,
      creating: 0
    };
    
    // Async state
    this.currentJob = null;
    this.queueAvailable = false;
    this.asyncMode = false;
    
    // WebSocket state
    this.websocketConnected = false;
    this.websocketSubscriptions = [];
    
    // Trevor Noah style messages
    this.trevorMessages = [
      "Kijk, AI is net als mijn oom - langzaam maar grondig...",
      "We analyseren je video zoals ik mijn materiaal analyseer - met precisie!",
      "Even geduld, de computer heeft nog geen koffie gehad vandaag...",
      "Je video wordt bekeken door onze digitale expert - hij knippert niet eens!",
      "We doen de magie... het duurt langer dan een TikTok, korter dan een Netflix serie",
      "AI is bezig, probeer niet te denken aan loading screens van de jaren 90...",
      "Je video krijgt nu de VIP behandeling - rood tapijt voor pixels!",
      "We maken je video klaar voor z'n close-up, Hollywood style!",
      "Onze AI kijkt naar je video alsof het de laatste aflevering van een serie is...",
      "Computer zegt: 'Ik ga even nadenken' - net als mensen, maar sneller!"
    ];
    
    this.currentMessageIndex = 0;
    this.messageTimer = null;
    
    // Process log system
    this.processLogs = [];
    this.currentLogIndex = 0;
    this.logStartTime = null;
    
    this.init();
  }

  async init() {
    this.setupEventListeners();
    this.setupStoreListeners();
    await this.setupWebSocket();
    await this.checkAsyncCapability();
    this.setupAsyncUI();
    console.log(`✅ ProcessingPanel component initialized (${this.asyncMode ? 'async' : 'sync'} mode)`);
  }
  
  async setupWebSocket() {
    /**
     * Initialize WebSocket connection for real-time updates
     */
    try {
      // Connect to WebSocket server
      const connected = await websocketService.connect();
      this.websocketConnected = connected;
      
      // Setup WebSocket event listeners
      this.setupWebSocketListeners();
      
      console.log(`🔌 WebSocket ${connected ? 'connected' : 'fallback mode'}`);
    } catch (error) {
      console.warn('⚠️ WebSocket setup failed:', error);
      this.websocketConnected = false;
    }
  }
  
  setupWebSocketListeners() {
    /**
     * Setup WebSocket event listeners for real-time updates
     */
    // Job progress updates
    const unsubscribeProgress = websocketService.on('job_progress_update', (data) => {
      this.handleWebSocketJobProgress(data);
    });
    this.websocketSubscriptions.push(unsubscribeProgress);
    
    // Job status changes
    const unsubscribeStatus = websocketService.on('job_status_change', (data) => {
      this.handleWebSocketJobStatus(data);
    });
    this.websocketSubscriptions.push(unsubscribeStatus);
    
    // Worker status updates
    const unsubscribeWorker = websocketService.on('worker_status_update', (data) => {
      this.handleWebSocketWorkerStatus(data);
    });
    this.websocketSubscriptions.push(unsubscribeWorker);
    
    // Queue statistics
    const unsubscribeQueue = websocketService.on('queue_stats_update', (data) => {
      this.handleWebSocketQueueStats(data);
    });
    this.websocketSubscriptions.push(unsubscribeQueue);
    
    // Connection events
    websocketService.on('connected', () => {
      this.websocketConnected = true;
      this.updateConnectionStatus();
      console.log('🔌 WebSocket connected');
    });
    
    websocketService.on('disconnected', () => {
      this.websocketConnected = false;
      this.updateConnectionStatus();
      console.log('🔌 WebSocket disconnected');
    });
    
    websocketService.on('fallback_enabled', () => {
      console.log('📡 Polling fallback enabled');
      this.updateConnectionStatus();
    });
  }

  async checkAsyncCapability() {
    try {
      const stats = await this.asyncJobService.getQueueStats();
      this.queueAvailable = stats.available !== false;
      this.asyncMode = this.queueAvailable;
      console.log(`📊 Queue available: ${this.queueAvailable}`);
    } catch (error) {
      console.warn('⚠️ Queue check failed, using sync mode:', error);
      this.queueAvailable = false;
      this.asyncMode = false;
    }
  }

  setupAsyncUI() {
    // Show/hide async UI elements based on capability
    const asyncPanel = this.container.querySelector('#asyncProcessingPanel');
    if (asyncPanel) {
      asyncPanel.style.display = this.asyncMode ? 'block' : 'none';
    }
    
    // Update queue status indicator
    this.updateQueueStatus();
  }

  setupEventListeners() {
    // Mobile device detection
    this.isMobileDevice = /Mobi|Android/i.test(navigator.userAgent) || window.innerWidth <= 768;

    // Cancel processing button
    const cancelButton = this.container.querySelector('#cancelProcessing');
    if (cancelButton) {
      cancelButton.addEventListener('click', () => {
        this.handleCancelProcessing();
      });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isProcessing) {
        this.handleCancelProcessing();
      }
    });
    
    // Log viewer controls
    this.setupLogViewerControls();

    // Mobile-specific interactions
    if (this.isMobileDevice) {
      this.setupMobileProcessingInteractions();
    }
  }
  
  setupLogViewerControls() {
    const toggleButton = this.container.querySelector('#toggleLogs');
    const prevButton = this.container.querySelector('#prevLog');
    const nextButton = this.container.querySelector('#nextLog');
    const logContent = this.container.querySelector('.log-viewer-content');
    
    if (toggleButton && logContent) {
      toggleButton.addEventListener('click', () => {
        const isCollapsed = logContent.classList.contains('collapsed');
        logContent.classList.toggle('collapsed');
        toggleButton.textContent = isCollapsed ? '🔼' : '🔽';
      });
    }
    
    if (prevButton) {
      prevButton.addEventListener('click', () => {
        this.navigateLog(-1);
      });
    }
    
    if (nextButton) {
      nextButton.addEventListener('click', () => {
        this.navigateLog(1);
      });
    }
  }

  setupStoreListeners() {
    // Listen for processing state changes
    this.stores.video.addListener((newState, prevState) => {
      // Processing started
      if (newState.isProcessing && !prevState.isProcessing) {
        // Get intent from UI store
        const selectedIntent = this.stores.ui.getState().selectedIntent;
        this.startProcessing(newState.currentVideo, selectedIntent);
      }
      
      // Processing completed
      if (!newState.isProcessing && prevState.isProcessing) {
        this.completeProcessing(newState.processingResults);
      }
      
      // Progress updates
      if (newState.processingProgress !== prevState.processingProgress) {
        this.updateProgress(newState.processingProgress);
      }
      
      // Error handling
      if (newState.processingError && !prevState.processingError) {
        this.handleProcessingError(newState.processingError);
      }
    });
  }

  async startProcessing(video, intent) {
    console.log('🔄 Starting processing:', { video, intent, asyncMode: this.asyncMode });
    
    this.isProcessing = true;
    this.currentStep = 'analyzing';
    
    // Initialize log viewer
    this.initLogViewer();
    
    // Start Trevor messages
    this.startTrevorMessages();
    
    // Update UI for processing start
    this.showProcessingStepWithLog('analyzing');
    this.updateVideoPreview(video);
    
    if (this.asyncMode) {
      // Use async job processing
      await this.startAsyncProcessing(video, intent);
    } else {
      // Use sync processing (original behavior)
      this.startProgressAnimation();
      this.startGradualProgress();
      // Continue with original sync processing
    }
  }

  async startAsyncProcessing(video, intent) {
    try {
      console.log('🎬 ProcessingPanel received video:', video);
      console.log('🔍 Video object keys:', Object.keys(video || {}));
      console.log('🎯 Intent:', intent);
      
      // Submit async job
      const jobResult = await this.asyncJobService.submitJob(video, {
        workflowType: intent || 'default',
        userId: 'ui_user'
      });
      
      if (!jobResult.success) {
        throw new Error(jobResult.error || 'Failed to submit job');
      }

      this.currentJob = jobResult;
      
      // Handle sync fallback mode
      if (jobResult.syncMode) {
        this.handleSyncModeResult(jobResult);
        return;
      }

      // Start monitoring async job
      this.updateAsyncUI('queued', jobResult);
      
      // Subscribe to WebSocket updates for this job
      if (this.websocketConnected) {
        websocketService.subscribeToJob(jobResult.jobId);
        console.log(`🔌 Subscribed to WebSocket updates for job ${jobResult.jobId}`);
      }
      
      await this.asyncJobService.monitorJob(
        jobResult.jobId,
        (progress) => this.handleAsyncProgress(progress),
        (result) => this.handleAsyncComplete(result),
        (error) => this.handleAsyncError(error)
      );

    } catch (error) {
      console.error('❌ Async processing failed:', error);
      this.handleAsyncError(error);
    }
  }

  handleAsyncProgress(progress) {
    console.log('📈 Async progress:', progress);
    this.updateAsyncUI('processing', progress);
    
    // Add to log viewer
    if (progress.message) {
      this.addProcessLog(progress.message, 'info');
    }
    if (progress.currentAgent) {
      this.addProcessLog(`Agent actief: ${progress.currentAgent}`, 'info');
    }
  }

  async handleAsyncComplete(result) {
    console.log('✅ Async complete:', result);
    this.updateAsyncUI('completed', result);
    this.isProcessing = false;
    
    // Add completion log
    this.addProcessLog('Verwerking voltooid!', 'success');
    
    // Fetch actual clips from the API (since result.clips is often empty)
    let actualClips = [];
    if (result.jobId) {
      try {
        console.log('🔍 Fetching clips from API for job:', result.jobId);
        console.log('🔍 API URL will be:', `${this.apiClient.baseUrl}/api/jobs/${result.jobId}/clips`);
        const clipsResponse = await fetch(`${this.apiClient.baseUrl}/api/jobs/${result.jobId}/clips`);
        console.log('🔍 Clips response status:', clipsResponse.status);
        console.log('🔍 Clips response ok:', clipsResponse.ok);
        
        if (clipsResponse.ok) {
          const clipsData = await clipsResponse.json();
          console.log('🔍 Raw clips response data:', clipsData);
          
          // Handle different response formats
          if (Array.isArray(clipsData)) {
            actualClips = clipsData;
          } else if (clipsData.clips && Array.isArray(clipsData.clips)) {
            actualClips = clipsData.clips;
          } else {
            actualClips = [];
          }
          
          console.log('✅ Fetched clips from API:', actualClips);
          console.log('📊 actualClips.length:', actualClips.length);
        } else {
          console.error('❌ Clips API responded with error:', clipsResponse.status, clipsResponse.statusText);
          const errorText = await clipsResponse.text();
          console.error('❌ Error response body:', errorText);
        }
      } catch (error) {
        console.error('❌ Failed to fetch clips:', error);
        actualClips = result.clips || [];
      }
    }
    
    // Update stores with results
    this.stores.video.setProcessingResults({
      jobId: result.jobId,
      clips: actualClips,
      totalClips: actualClips.length,
      analysis: {
        totalDuration: 0,
        confidence: 0.95,
        intent: this.stores.ui.getState().selectedIntent
      }
    });
    this.stores.video.setIsProcessing(false);
    this.stores.video.updateProcessingProgress(100);
  }

  handleAsyncError(error) {
    console.error('❌ Async error:', error);
    this.updateAsyncUI('error', { error: error.message });
    this.isProcessing = false;
    
    // Add error log
    this.addProcessLog(`Fout opgetreden: ${error.message}`, 'error');
    
    // Update stores with error
    this.stores.video.setProcessingError(error.message);
    this.stores.video.setIsProcessing(false);
  }
  
  // WebSocket Event Handlers
  handleWebSocketJobProgress(data) {
    /**
     * Handle real-time job progress updates from WebSocket
     */
    if (!this.currentJob || data.job_id !== this.currentJob.jobId) {
      return; // Not our job
    }
    
    console.log('🔌 WebSocket progress update:', data);
    
    // Update progress UI
    this.handleAsyncProgress({
      progress: data.progress,
      message: data.current_step,
      currentAgent: data.agent_name,
      timestamp: data.timestamp
    });
    
    // Add real-time log entry
    if (data.current_step) {
      this.addProcessLog(`[Real-time] ${data.current_step}`, 'info');
    }
    
    if (data.agent_name) {
      this.addProcessLog(`[Agent] ${data.agent_name} actief`, 'info');
    }
  }
  
  handleWebSocketJobStatus(data) {
    /**
     * Handle job status changes from WebSocket
     */
    if (!this.currentJob || data.job_id !== this.currentJob.jobId) {
      return; // Not our job
    }
    
    console.log('🔌 WebSocket status update:', data);
    
    // Handle different status changes
    switch (data.status) {
      case 'processing':
        this.updateAsyncUI('processing', { 
          progress: data.progress || 0,
          message: 'Processing gestart...'
        });
        this.addProcessLog('[Real-time] Processing gestart', 'info');
        break;
        
      case 'completed':
        this.handleAsyncComplete({
          jobId: data.job_id,
          status: 'completed',
          progress: 100
        });
        this.addProcessLog('[Real-time] Verwerking voltooid!', 'success');
        break;
        
      case 'failed':
        this.handleAsyncError(new Error('Job processing failed'));
        this.addProcessLog('[Real-time] Processing gefaald', 'error');
        break;
    }
  }
  
  handleWebSocketWorkerStatus(data) {
    /**
     * Handle worker status updates from WebSocket
     */
    console.log('🔌 Worker status update:', data);
    
    // Update worker status in UI
    const workerStatusEl = this.container.querySelector('#workerStatus');
    if (workerStatusEl) {
      workerStatusEl.textContent = `Workers actief: ${data.active_workers || 0}`;
    }
    
    // Add log entry for worker changes
    if (data.status === 'active') {
      this.addProcessLog(`[Worker] ${data.worker_id} actief`, 'info');
    }
  }
  
  handleWebSocketQueueStats(data) {
    /**
     * Handle queue statistics updates from WebSocket
     */
    console.log('🔌 Queue stats update:', data);
    
    // Update queue status in UI
    this.updateQueueStatsDisplay(data);
    
    // Log queue status changes
    if (data.queue_length !== undefined) {
      this.addProcessLog(`[Queue] ${data.queue_length} jobs in wachtrij`, 'info');
    }
  }
  
  updateConnectionStatus() {
    /**
     * Update UI based on WebSocket connection status
     */
    const statusEl = this.container.querySelector('#connectionStatus');
    if (statusEl) {
      const status = websocketService.getConnectionStatus();
      statusEl.innerHTML = status.connected 
        ? '🔌 Real-time verbonden'
        : status.polling 
          ? '📡 Polling mode'
          : '❌ Offline';
    }
  }
  
  updateQueueStatsDisplay(stats) {
    /**
     * Update queue statistics display
     */
    const queueEl = this.container.querySelector('#queueStats');
    if (queueEl) {
      queueEl.innerHTML = `
        <div class="queue-stat">
          <span class="label">Wachtrij:</span>
          <span class="value">${stats.queue_length || 0}</span>
        </div>
        <div class="queue-stat">
          <span class="label">Bezig:</span>
          <span class="value">${stats.processing_jobs || 0}</span>
        </div>
      `;
    }
  }

  handleSyncModeResult(result) {
    console.log('🔄 Sync mode result:', result);
    // Simulate progress then complete
    this.updateAsyncUI('processing', { progress: 50, message: 'Processing in sync mode...' });
    
    setTimeout(() => {
      this.handleAsyncComplete({
        jobId: result.jobId,
        clips: result.clips.clips,
        totalClips: result.clips.total_clips
      });
    }, 1000);
  }

  updateAsyncUI(status, data = {}) {
    const asyncPanel = this.container.querySelector('#asyncProcessingPanel');
    if (!asyncPanel) return;

    // Update status
    const statusEl = asyncPanel.querySelector('#processingStatus');
    if (statusEl) {
      statusEl.textContent = this.getStatusText(status);
      statusEl.className = `processing-status status-${status}`;
    }

    // Update progress
    const progressEl = asyncPanel.querySelector('#processingProgress');
    if (progressEl && data.progress !== undefined) {
      progressEl.style.width = `${data.progress}%`;
      // Note: Removed percentage text overlay - progress shown in dedicated progress bar only
    }

    // Update message
    const messageEl = asyncPanel.querySelector('#processingMessage');
    if (messageEl && data.message) {
      messageEl.textContent = data.message;
    }

    // Update current agent
    const agentEl = asyncPanel.querySelector('#currentAgent');
    if (agentEl && data.currentAgent) {
      agentEl.textContent = data.currentAgent;
    }

    // Show clips if completed
    if (status === 'completed' && data.clips) {
      this.renderAsyncClips(data.clips);
    }
  }

  getStatusText(status) {
    const statusTexts = {
      queued: 'In Queue',
      processing: 'Processing',
      completed: 'Completed',
      error: 'Error',
      cancelled: 'Cancelled'
    };
    return statusTexts[status] || status;
  }

  renderAsyncClips(clips) {
    const clipsContainer = this.container.querySelector('#processingClips');
    if (!clipsContainer) return;

    clipsContainer.innerHTML = '';
    clipsContainer.style.display = 'block';

    if (!clips || clips.length === 0) {
      clipsContainer.innerHTML = '<p>No clips generated</p>';
      return;
    }

    const header = document.createElement('h4');
    header.textContent = `Generated ${clips.length} clips:`;
    clipsContainer.appendChild(header);

    clips.forEach((clip) => {
      const clipEl = document.createElement('div');
      clipEl.className = 'clip-item';
      clipEl.innerHTML = `
        <div class="clip-info">
          <strong>${clip.title || `Clip ${clip.clip_id}`}</strong>
          <span class="clip-type">${clip.type}</span>
          <p class="clip-description">${clip.description || ''}</p>
        </div>
        <div class="clip-actions">
          <button class="btn-download" data-clip-id="${clip.clip_id}">
            📥 Download
          </button>
        </div>
      `;

      const downloadBtn = clipEl.querySelector('.btn-download');
      downloadBtn.addEventListener('click', () => {
        this.downloadClip(clip.clip_id, clip.title);
      });

      clipsContainer.appendChild(clipEl);
    });
  }

  async downloadClip(clipId, title) {
    if (!this.currentJob) return;
    
    try {
      await this.asyncJobService.downloadClip(this.currentJob.jobId, clipId, title);
    } catch (error) {
      console.error('❌ Download failed:', error);
    }
  }

  updateQueueStatus() {
    const queueEl = this.container.querySelector('#queueStatus');
    if (!queueEl) return;

    if (this.queueAvailable) {
      queueEl.innerHTML = `
        <span class="status-indicator">🟢</span>
        <span>Queue System Online</span>
      `;
      queueEl.className = 'queue-status online';
    } else {
      queueEl.innerHTML = `
        <span class="status-indicator">🔴</span>
        <span>Queue Offline - Using Sync</span>
      `;
      queueEl.className = 'queue-status offline';
    }
  }

  async startSyncProcessing(video, intent) {
    try {
      console.log('🚀 Starting video processing with backend agents...');
      await this.processingService.startProcessing(video, intent);
      console.log('✅ Video processing completed successfully!');
    } catch (error) {
      console.error('❌ Processing service error:', error);
      this.handleProcessingError(error.message);
    }
  }

  updateProgress(progressValue) {
    if (typeof progressValue === 'undefined') return;
    
    console.log('📊 Processing progress update:', progressValue);
    
    // Update current step progress
    this.progress[this.currentStep] = progressValue;
    
    // Update progress bars
    this.updateProgressBars();
    
    // Update overall progress display
    this.updateOverallProgress(progressValue);
  }
  
  updateOverallProgress(progress) {
    // Update main progress bar if it exists
    const mainProgressBar = this.container.querySelector('#mainProgressBar .progress-fill');
    if (mainProgressBar) {
      mainProgressBar.style.width = `${progress}%`;
    }
    
    // Removed progress text update - progress shown in progress bar only
  }

  updateDetailedMessage(message) {
    // Update the time estimate element with detailed processing message
    const timeEstimateElement = this.container.querySelector('#timeEstimate');
    if (timeEstimateElement) {
      timeEstimateElement.textContent = message;
    }
    
    // Also show message in the current active step
    const activeStep = this.container.querySelector('.processing-step.active');
    if (activeStep) {
      let messageElement = activeStep.querySelector('.step-detail-message');
      if (!messageElement) {
        messageElement = document.createElement('div');
        messageElement.className = 'step-detail-message';
        messageElement.style.cssText = `
          font-size: 0.875rem;
          color: #6b7280;
          margin-top: 4px;
          font-style: italic;
        `;
        
        const stepDescription = activeStep.querySelector('.step-description');
        if (stepDescription) {
          stepDescription.parentNode.insertBefore(messageElement, stepDescription.nextSibling);
        }
      }
      messageElement.textContent = message;
    }
  }

  updateSubstep(substep) {
    // Update substep indicator in the active step
    const activeStep = this.container.querySelector('.processing-step.active');
    if (activeStep) {
      let substepElement = activeStep.querySelector('.step-substep');
      if (!substepElement) {
        substepElement = document.createElement('div');
        substepElement.className = 'step-substep';
        substepElement.style.cssText = `
          font-size: 0.75rem;
          color: #4f46e5;
          font-weight: 600;
          margin-top: 2px;
        `;
        
        const stepTitle = activeStep.querySelector('.step-title');
        if (stepTitle) {
          stepTitle.parentNode.insertBefore(substepElement, stepTitle.nextSibling);
        }
      }
      substepElement.textContent = `• ${substep}`;
    }
  }

  showProcessingStep(stepName) {
    // Remove active class from all steps
    const allSteps = this.container.querySelectorAll('.processing-step');
    allSteps.forEach(step => {
      step.classList.remove('active', 'completed');
    });
    
    // Update processing subtitle based on step
    const stepTexts = {
      'analyzing': 'AI analyseert je video...',
      'extracting': 'Beste momenten worden geselecteerd...',
      'creating': 'Finale clips worden gegenereerd...'
    };
    this.updateProcessingSubtitle(stepTexts[stepName] || 'Processing...');
    
    // Mark completed steps
    const stepOrder = ['analyzing', 'extracting', 'creating'];
    const currentIndex = stepOrder.indexOf(stepName);
    
    stepOrder.forEach((step, index) => {
      const stepElement = this.container.querySelector(`#step${step.charAt(0).toUpperCase() + step.slice(1)}`);
      if (stepElement) {
        if (index < currentIndex) {
          stepElement.classList.add('completed');
        } else if (index === currentIndex) {
          stepElement.classList.add('active');
        }
      }
    });
    
    console.log(`🔄 Processing step: ${stepName}`);
  }

  updateProgressBars() {
    // Update analyzing progress bar
    const analyzingBar = this.container.querySelector('#analyzingProgress .progress-fill');
    if (analyzingBar) {
      analyzingBar.style.width = `${this.progress.analyzing || 0}%`;
    }
    
    // Update extracting progress bar
    const extractingBar = this.container.querySelector('#extractingProgress .progress-fill');
    if (extractingBar) {
      extractingBar.style.width = `${this.progress.extracting || 0}%`;
    }
    
    // Update creating progress bar
    const creatingBar = this.container.querySelector('#creatingProgress .progress-fill');
    if (creatingBar) {
      creatingBar.style.width = `${this.progress.creating || 0}%`;
    }
    
    // Update step-specific progress based on current step
    const currentStepProgress = this.progress[this.currentStep] || 0;
    const activeStepBar = this.container.querySelector('.processing-step.active .progress-fill');
    if (activeStepBar) {
      activeStepBar.style.width = `${currentStepProgress}%`;
    }
  }

  addProgressBarToStep(stepId, progress) {
    const step = this.container.querySelector(`#${stepId}`);
    if (!step) return;
    
    const progressContainer = document.createElement('div');
    progressContainer.className = 'step-progress';
    progressContainer.innerHTML = `
      <div class="progress-bar">
        <div class="progress-fill" style="width: ${progress}%"></div>
      </div>
    `;
    
    step.appendChild(progressContainer);
  }

  updateVideoPreview(video) {
    const thumbnail = this.container.querySelector('#videoThumbnail');
    if (thumbnail && video) {
      // For file uploads, create object URL for preview
      if (video instanceof File) {
        const videoElement = document.createElement('video');
        videoElement.src = URL.createObjectURL(video);
        videoElement.addEventListener('loadedmetadata', () => {
          // Capture first frame as thumbnail
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          canvas.width = videoElement.videoWidth;
          canvas.height = videoElement.videoHeight;
          ctx.drawImage(videoElement, 0, 0);
          thumbnail.src = canvas.toDataURL();
        });
      } else if (typeof video === 'string') {
        // For URL uploads, use a placeholder or fetch thumbnail
        thumbnail.src = './public/assets/video-placeholder.svg';
        thumbnail.alt = `Processing: ${video}`;
      }
    }
  }

  startProgressAnimation() {
    // Start scanning line animation
    const scanningLine = this.container.querySelector('.scanning-line');
    if (scanningLine) {
      scanningLine.style.animation = 'scan 3s ease-in-out infinite';
    }
    
    // Animate analysis points
    const analysisPoints = this.container.querySelectorAll('.analysis-point');
    analysisPoints.forEach((point, index) => {
      setTimeout(() => {
        point.classList.add('active');
      }, index * 1000);
    });
  }

  updateTimeEstimate(timeRemaining) {
    const timeElement = this.container.querySelector('#timeEstimate');
    if (timeElement) {
      // Show simple "please wait" message instead of time calculations
      const translation = i18n.t('processing.time_remaining');
      // Fall back to English if translation not available
      timeElement.textContent = translation === 'processing.time_remaining' ? 'Please wait while we process your video' : translation;
    }
  }

  async handleCancelProcessing() {
    console.log('🛑 Cancel processing requested');
    
    // Confirm cancellation
    const confirmed = confirm(i18n.t('processing.confirm_cancel'));
    if (!confirmed) return;
    
    try {
      // Cancel processing service
      await this.processingService.cancelProcessing();
      
      // Update store
      this.stores.video.setProcessingError(i18n.t('processing.cancelled_by_user'));
      this.stores.ui.navigateToStep('upload');
      
      console.log('✅ Processing cancelled successfully');
    } catch (error) {
      console.error('❌ Error cancelling processing:', error);
      this.stores.ui.showError(i18n.t('processing.cancel_error'));
    }
  }

  completeProcessing(results) {
    console.log('✅ Processing completed:', results);
    
    // Clear progress timer
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }
    
    this.isProcessing = false;
    
    // Stop Trevor messages
    this.stopTrevorMessages();
    
    // Complete all steps visually
    this.progress.analyzing = 100;
    this.progress.extracting = 100;
    this.progress.creating = 100;
    
    // Show completion animation
    this.showProcessingStep('creating');
    this.updateProgressBars();
    
    // Mark all steps as completed
    const allSteps = this.container.querySelectorAll('.processing-step');
    allSteps.forEach(step => {
      step.classList.add('completed');
    });
    
    // Navigate to results after short delay
    setTimeout(() => {
      this.stores.ui.navigateToStep('results');
    }, 1500);
  }

  handleProcessingError(error) {
    console.error('❌ Processing error:', error);
    
    this.isProcessing = false;
    
    // Show error state
    const allSteps = this.container.querySelectorAll('.processing-step');
    allSteps.forEach(step => {
      step.classList.add('error');
    });
    
    // Update error message
    const errorElement = this.container.querySelector('.processing-error');
    if (errorElement) {
      errorElement.textContent = error;
      errorElement.style.display = 'block';
    }
    
    // Show retry option
    this.showRetryOption(error);
  }

  showRetryOption(error) {
    const cancelButton = this.container.querySelector('#cancelProcessing');
    if (cancelButton) {
      cancelButton.textContent = 'Terug naar Upload';
      cancelButton.onclick = () => {
        this.stores.ui.navigateToStep('upload');
      };
    }
  }

  startGradualProgress() {
    // Clear any existing timers
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
    }
    
    let stepTimes = {
      analyzing: { duration: 3000, currentProgress: 0 }, // 3 seconds
      extracting: { duration: 4000, currentProgress: 0 }, // 4 seconds (was te snel)
      creating: { duration: 2500, currentProgress: 0 }    // 2.5 seconds
    };
    
    let currentStepIndex = 0;
    let steps = ['analyzing', 'extracting', 'creating'];
    let stepStartTime = Date.now();
    
    this.progressTimer = setInterval(() => {
      if (!this.isProcessing) {
        clearInterval(this.progressTimer);
        return;
      }
      
      let currentStepName = steps[currentStepIndex];
      let stepInfo = stepTimes[currentStepName];
      let elapsed = Date.now() - stepStartTime;
      
      // Calculate smooth progress for current step
      let stepProgress = Math.min((elapsed / stepInfo.duration) * 100, 95); // Max 95% until completion
      
      // Add intermediate logging for better UX
      if (currentStepName === 'extracting') {
        if (stepProgress >= 25 && stepProgress < 30 && !stepInfo.logged25) {
          this.addProcessLog('Beste momenten worden geïdentificeerd...', 'info');
          stepInfo.logged25 = true;
        }
        if (stepProgress >= 60 && stepProgress < 65 && !stepInfo.logged60) {
          this.addProcessLog('Kwaliteitsanalyse van segmenten...', 'info');
          stepInfo.logged60 = true;
        }
      }
      
      // Update current step progress
      this.progress[currentStepName] = stepProgress;
      this.updateProgressBars();
      
      // Move to next step when current reaches 90%
      if (stepProgress >= 90 && currentStepIndex < steps.length - 1) {
        // Mark previous step as completed first
        this.progress[currentStepName] = 100;
        
        // Move to next step
        currentStepIndex++;
        stepStartTime = Date.now();
        this.currentStep = steps[currentStepIndex];
        this.showProcessingStepWithLog(this.currentStep);
        
        console.log(`✅ Completed step: ${currentStepName}, moving to: ${this.currentStep}`);
      }
      
      // Stop timer when all steps are complete
      if (currentStepIndex >= steps.length - 1 && stepProgress >= 95) {
        this.progress[currentStepName] = 100;
        console.log(`✅ All processing steps completed, stopping timer`);
        clearInterval(this.progressTimer);
        this.progressTimer = null;
        return;
      }
      
      // Update time estimate
      let totalRemaining = 0;
      for (let i = currentStepIndex; i < steps.length; i++) {
        let stepName = steps[i];
        if (i === currentStepIndex) {
          totalRemaining += stepTimes[stepName].duration - elapsed;
        } else {
          totalRemaining += stepTimes[stepName].duration;
        }
      }
      
      this.updateTimeEstimate(Math.max(totalRemaining / 1000, 0));
    }, 1000); // Update every second
  }
  
  reset() {
    this.isProcessing = false;
    this.currentStep = 'analyzing';
    this.progress = {
      analyzing: 0,
      extracting: 0,
      creating: 0
    };
    
    // Clear progress timer
    if (this.progressTimer) {
      clearInterval(this.progressTimer);
      this.progressTimer = null;
    }
    
    // Reset UI state
    const allSteps = this.container.querySelectorAll('.processing-step');
    allSteps.forEach(step => {
      step.classList.remove('active', 'completed', 'error');
    });
    
    // Reset progress bars
    const progressBars = this.container.querySelectorAll('.progress-fill');
    progressBars.forEach(bar => {
      bar.style.width = '0%';
    });
    
    console.log('🔄 ProcessingPanel reset');
  }

  // Trevor Noah Style Message System
  startTrevorMessages() {
    this.currentMessageIndex = 0;
    this.updateTrevorMessage();
    
    // Change message every 4 seconds
    this.messageTimer = setInterval(() => {
      this.currentMessageIndex = (this.currentMessageIndex + 1) % this.trevorMessages.length;
      this.updateTrevorMessage();
    }, 4000);
  }

  updateTrevorMessage() {
    const messageEl = this.container.querySelector('#trevorMessage');
    if (messageEl) {
      // Fade out
      messageEl.style.opacity = '0';
      
      setTimeout(() => {
        messageEl.textContent = this.trevorMessages[this.currentMessageIndex];
        // Fade in
        messageEl.style.opacity = '1';
      }, 200);
    }
  }

  stopTrevorMessages() {
    if (this.messageTimer) {
      clearInterval(this.messageTimer);
      this.messageTimer = null;
    }
  }

  updateProcessingSubtitle(text) {
    const subtitleEl = this.container.querySelector('#processingSubtitle');
    if (subtitleEl) {
      subtitleEl.textContent = text;
    }
  }
  
  // ===== PROCESS LOG SYSTEM =====
  
  initLogViewer() {
    this.logStartTime = Date.now();
    this.processLogs = [];
    this.currentLogIndex = 0;
    this.addProcessLog('Verwerkingsproces gestart...', 'info');
    this.showLogViewer();
  }
  
  addProcessLog(message, type = 'info') {
    const timestamp = this.getLogTimestamp();
    const logEntry = {
      time: timestamp,
      message: message,
      type: type,
      id: this.processLogs.length
    };
    
    this.processLogs.push(logEntry);
    this.currentLogIndex = this.processLogs.length - 1;
    this.updateLogViewer();
    
    // Also log to console for developers
    console.log(`[${timestamp}] ${message}`);
  }
  
  getLogTimestamp() {
    if (!this.logStartTime) return '00:00';
    const elapsed = Date.now() - this.logStartTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
  
  showLogViewer() {
    const logViewer = this.container.querySelector('#processLogViewer');
    if (logViewer && logViewer.isConnected) {
      logViewer.style.display = 'block';
      // Scroll into view smoothly
      logViewer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
  
  hideLogViewer() {
    const logViewer = this.container.querySelector('#processLogViewer');
    if (logViewer) {
      logViewer.style.display = 'none';
    }
  }
  
  updateLogViewer() {
    const carousel = this.container.querySelector('#logCarousel');
    const counter = this.container.querySelector('#logCounter');
    const prevBtn = this.container.querySelector('#prevLog');
    const nextBtn = this.container.querySelector('#nextLog');
    
    if (!carousel || this.processLogs.length === 0) return;
    
    // Update carousel content
    const currentLog = this.processLogs[this.currentLogIndex];
    carousel.innerHTML = `
      <div class="log-entry active type-${currentLog.type}">
        <span class="log-time">${currentLog.time}</span>
        <span class="log-message">${currentLog.message}</span>
      </div>
    `;
    
    // Update counter
    if (counter) {
      counter.textContent = `${this.currentLogIndex + 1} van ${this.processLogs.length}`;
    }
    
    // Update navigation buttons
    if (prevBtn) {
      prevBtn.disabled = this.currentLogIndex === 0;
    }
    if (nextBtn) {
      nextBtn.disabled = this.currentLogIndex === this.processLogs.length - 1;
    }
  }
  
  navigateLog(direction) {
    const newIndex = this.currentLogIndex + direction;
    if (newIndex >= 0 && newIndex < this.processLogs.length) {
      this.currentLogIndex = newIndex;
      this.updateLogViewer();
    }
  }
  
  // Enhanced step tracking with logging
  showProcessingStepWithLog(stepName) {
    this.showProcessingStep(stepName);
    
    const stepMessages = {
      'analyzing': 'Stap 1: Video-analyse gestart',
      'extracting': 'Stap 2: Segment extractie gestart', 
      'creating': 'Stap 3: Output generatie gestart'
    };
    
    this.addProcessLog(stepMessages[stepName] || `Stap gestart: ${stepName}`, 'info');
  }
  
  setupMobileProcessingInteractions() {
    console.log('📱 Setting up mobile processing interactions');

    // Add mobile-specific styles
    this.addMobileProcessingStyles();

    // Setup swipe gestures for log navigation
    this.setupMobileLogNavigation();

    // Setup pull-to-refresh for status updates
    this.setupPullToRefresh();

    // Setup mobile cancel gesture
    this.setupMobileCancelGesture();

    // Setup screen wake lock to prevent sleep during processing
    this.setupScreenWakeLock();
  }

  setupMobileLogNavigation() {
    const logViewer = this.container.querySelector('#processLogViewer');
    if (!logViewer) return;

    let touchState = {
      startX: 0,
      startY: 0,
      moved: false
    };

    const touchStartHandler = (e) => {
      const touch = e.touches[0];
      touchState = {
        startX: touch.clientX,
        startY: touch.clientY,
        moved: false
      };
    };

    const touchMoveHandler = (e) => {
      const touch = e.touches[0];
      const deltaX = Math.abs(touch.clientX - touchState.startX);
      const deltaY = Math.abs(touch.clientY - touchState.startY);
      
      if (deltaX > 20 || deltaY > 20) {
        touchState.moved = true;
      }
    };

    const touchEndHandler = (e) => {
      if (!touchState.moved) return;

      const touch = e.changedTouches[0];
      const deltaX = touch.clientX - touchState.startX;
      
      if (Math.abs(deltaX) > 50) {
        // Swipe navigation
        if (deltaX > 0) {
          // Swipe right - previous log
          this.navigateLog(-1);
          this.triggerHapticFeedback('light');
        } else {
          // Swipe left - next log
          this.navigateLog(1);
          this.triggerHapticFeedback('light');
        }
      }
    };

    logViewer.addEventListener('touchstart', touchStartHandler, { passive: false });
    logViewer.addEventListener('touchmove', touchMoveHandler, { passive: false });
    logViewer.addEventListener('touchend', touchEndHandler, { passive: false });

    // Store for cleanup
    logViewer._mobileHandlers = {
      touchStart: touchStartHandler,
      touchMove: touchMoveHandler,
      touchEnd: touchEndHandler
    };
  }

  setupPullToRefresh() {
    const processingContainer = this.container.querySelector('.processing-container') || this.container;
    let pullToRefreshState = {
      startY: 0,
      currentY: 0,
      pulling: false,
      threshold: 60
    };

    const touchStartHandler = (e) => {
      if (processingContainer.scrollTop === 0) {
        pullToRefreshState.startY = e.touches[0].clientY;
        pullToRefreshState.pulling = true;
      }
    };

    const touchMoveHandler = (e) => {
      if (!pullToRefreshState.pulling) return;

      pullToRefreshState.currentY = e.touches[0].clientY;
      const pullDistance = pullToRefreshState.currentY - pullToRefreshState.startY;

      if (pullDistance > 0 && processingContainer.scrollTop === 0) {
        e.preventDefault();
        
        // Visual feedback
        const pullIndicator = this.getPullToRefreshIndicator();
        const progress = Math.min(pullDistance / pullToRefreshState.threshold, 1);
        
        pullIndicator.style.opacity = progress;
        pullIndicator.style.transform = `translateY(${Math.min(pullDistance * 0.5, 30)}px)`;
        
        if (pullDistance > pullToRefreshState.threshold) {
          pullIndicator.classList.add('ready');
        } else {
          pullIndicator.classList.remove('ready');
        }
      }
    };

    const touchEndHandler = (e) => {
      if (!pullToRefreshState.pulling) return;

      const pullDistance = pullToRefreshState.currentY - pullToRefreshState.startY;
      const pullIndicator = this.getPullToRefreshIndicator();
      
      if (pullDistance > pullToRefreshState.threshold) {
        // Trigger refresh
        this.handleMobileRefresh();
        this.triggerHapticFeedback('medium');
      }

      // Reset visual state
      pullIndicator.style.opacity = '';
      pullIndicator.style.transform = '';
      pullIndicator.classList.remove('ready');
      
      pullToRefreshState.pulling = false;
    };

    processingContainer.addEventListener('touchstart', touchStartHandler, { passive: false });
    processingContainer.addEventListener('touchmove', touchMoveHandler, { passive: false });
    processingContainer.addEventListener('touchend', touchEndHandler, { passive: false });

    // Store for cleanup
    processingContainer._pullToRefreshHandlers = {
      touchStart: touchStartHandler,
      touchMove: touchMoveHandler,
      touchEnd: touchEndHandler
    };
  }

  setupMobileCancelGesture() {
    const cancelButton = this.container.querySelector('#cancelProcessing');
    if (!cancelButton) return;

    // Long press to cancel with confirmation
    let longPressTimer = null;
    let touchStartTime = 0;

    const touchStartHandler = (e) => {
      touchStartTime = Date.now();
      
      longPressTimer = setTimeout(() => {
        // Long press detected
        this.triggerHapticFeedback('heavy');
        cancelButton.classList.add('long-press-active');
        
        // Show confirmation after long press
        setTimeout(() => {
          this.showMobileCancelConfirmation();
        }, 200);
      }, 800);

      // Visual feedback
      cancelButton.classList.add('touch-active');
    };

    const touchEndHandler = (e) => {
      const touchDuration = Date.now() - touchStartTime;
      
      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }

      cancelButton.classList.remove('touch-active', 'long-press-active');

      // Short tap - regular cancel
      if (touchDuration < 500) {
        this.handleCancelProcessing();
      }
    };

    cancelButton.addEventListener('touchstart', touchStartHandler, { passive: false });
    cancelButton.addEventListener('touchend', touchEndHandler, { passive: false });

    // Store for cleanup
    cancelButton._mobileHandlers = {
      touchStart: touchStartHandler,
      touchEnd: touchEndHandler
    };
  }

  setupScreenWakeLock() {
    // Request screen wake lock during processing to prevent screen sleep
    this.wakeLock = null;

    const requestWakeLock = async () => {
      try {
        if ('wakeLock' in navigator) {
          this.wakeLock = await navigator.wakeLock.request('screen');
          console.log('📱 Screen wake lock acquired');
          
          this.wakeLock.addEventListener('release', () => {
            console.log('📱 Screen wake lock released');
          });
        }
      } catch (err) {
        console.log('📱 Wake lock not supported or denied:', err);
      }
    };

    const releaseWakeLock = () => {
      if (this.wakeLock) {
        this.wakeLock.release();
        this.wakeLock = null;
      }
    };

    // Request wake lock when processing starts
    this.stores.video.addListener((newState, prevState) => {
      if (newState.isProcessing && !prevState.isProcessing) {
        requestWakeLock();
      } else if (!newState.isProcessing && prevState.isProcessing) {
        releaseWakeLock();
      }
    });
  }

  getPullToRefreshIndicator() {
    let indicator = this.container.querySelector('.pull-to-refresh-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.className = 'pull-to-refresh-indicator';
      indicator.innerHTML = `
        <div class="refresh-icon">↻</div>
        <div class="refresh-text">Pull to refresh status</div>
      `;
      this.container.insertBefore(indicator, this.container.firstChild);
    }
    return indicator;
  }

  handleMobileRefresh() {
    console.log('📱 Mobile refresh triggered');
    
    // Add refresh animation
    const indicator = this.getPullToRefreshIndicator();
    indicator.classList.add('refreshing');
    
    // Simulate refresh action
    setTimeout(() => {
      indicator.classList.remove('refreshing');
      this.showMobileToast('Status updated');
    }, 1000);
  }

  showMobileCancelConfirmation() {
    const confirmation = document.createElement('div');
    confirmation.className = 'mobile-cancel-confirmation';
    confirmation.innerHTML = `
      <div class="confirmation-content">
        <h3>Cancel Processing?</h3>
        <p>This will stop the current video processing.</p>
        <div class="confirmation-actions">
          <button class="btn-cancel">Continue</button>
          <button class="btn-confirm">Cancel Processing</button>
        </div>
      </div>
    `;

    document.body.appendChild(confirmation);
    
    // Add event listeners
    confirmation.querySelector('.btn-cancel').addEventListener('click', () => {
      confirmation.remove();
    });
    
    confirmation.querySelector('.btn-confirm').addEventListener('click', () => {
      confirmation.remove();
      this.handleCancelProcessing();
    });

    // Auto-close after 5 seconds
    setTimeout(() => {
      if (confirmation.parentNode) {
        confirmation.remove();
      }
    }, 5000);
  }

  showMobileToast(message) {
    let toast = document.querySelector('.mobile-processing-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'mobile-processing-toast';
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
      toast.classList.remove('show');
    }, 2000);
  }

  triggerHapticFeedback(intensity = 'light') {
    if ('vibrate' in navigator) {
      const patterns = {
        light: [10],
        medium: [20],
        heavy: [50]
      };
      navigator.vibrate(patterns[intensity] || patterns.light);
    }
  }

  addMobileProcessingStyles() {
    if (document.querySelector('#mobile-processing-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'mobile-processing-styles';
    style.textContent = `
      @media (max-width: 768px) {
        .processing-panel {
          padding: 16px;
        }
        
        .processing-step {
          padding: 16px;
          margin-bottom: 12px;
          border-radius: 12px;
        }
        
        .processing-step.active {
          transform: scale(1.02);
          transition: transform 0.2s ease;
        }
        
        .progress-bar {
          height: 8px;
          border-radius: 4px;
        }
        
        #cancelProcessing {
          padding: 14px 24px;
          font-size: 16px;
          border-radius: 12px;
          transition: all 0.2s ease;
        }
        
        #cancelProcessing.touch-active {
          transform: scale(0.95);
          background-color: #ef4444;
        }
        
        #cancelProcessing.long-press-active {
          background-color: #dc2626;
          box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.3);
        }
        
        #processLogViewer {
          border-radius: 12px;
          overflow: hidden;
          touch-action: pan-x;
        }
        
        .log-carousel {
          min-height: 60px;
          display: flex;
          align-items: center;
          padding: 12px;
        }
      }
      
      .pull-to-refresh-indicator {
        position: absolute;
        top: -60px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 10px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        opacity: 0;
        transition: opacity 0.3s ease;
        z-index: 10;
      }
      
      .pull-to-refresh-indicator.ready .refresh-icon {
        color: #3b82f6;
        animation: spin 1s linear infinite;
      }
      
      .pull-to-refresh-indicator.refreshing .refresh-icon {
        animation: spin 1s linear infinite;
      }
      
      @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
      
      .mobile-cancel-confirmation {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        padding: 20px;
      }
      
      .confirmation-content {
        background: white;
        border-radius: 16px;
        padding: 24px;
        max-width: 320px;
        width: 100%;
      }
      
      .confirmation-actions {
        display: flex;
        gap: 12px;
        margin-top: 20px;
      }
      
      .confirmation-actions button {
        flex: 1;
        padding: 12px;
        border: none;
        border-radius: 8px;
        font-weight: 500;
      }
      
      .btn-cancel {
        background: #f3f4f6;
        color: #374151;
      }
      
      .btn-confirm {
        background: #ef4444;
        color: white;
      }
      
      .mobile-processing-toast {
        position: fixed;
        bottom: 100px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 12px 24px;
        border-radius: 24px;
        font-size: 14px;
        font-weight: 500;
        z-index: 1000;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
      }
      
      .mobile-processing-toast.show {
        opacity: 1;
      }
    `;
    document.head.appendChild(style);
  }

  destroy() {
    /**
     * Clean up WebSocket subscriptions and timers
     */
    // Clean up mobile event listeners
    if (this.isMobileDevice) {
      // Clean up log viewer handlers
      const logViewer = this.container.querySelector('#processLogViewer');
      if (logViewer && logViewer._mobileHandlers) {
        logViewer.removeEventListener('touchstart', logViewer._mobileHandlers.touchStart);
        logViewer.removeEventListener('touchmove', logViewer._mobileHandlers.touchMove);
        logViewer.removeEventListener('touchend', logViewer._mobileHandlers.touchEnd);
        delete logViewer._mobileHandlers;
      }

      // Clean up pull-to-refresh handlers
      const processingContainer = this.container.querySelector('.processing-container') || this.container;
      if (processingContainer._pullToRefreshHandlers) {
        processingContainer.removeEventListener('touchstart', processingContainer._pullToRefreshHandlers.touchStart);
        processingContainer.removeEventListener('touchmove', processingContainer._pullToRefreshHandlers.touchMove);
        processingContainer.removeEventListener('touchend', processingContainer._pullToRefreshHandlers.touchEnd);
        delete processingContainer._pullToRefreshHandlers;
      }

      // Clean up cancel button handlers
      const cancelButton = this.container.querySelector('#cancelProcessing');
      if (cancelButton && cancelButton._mobileHandlers) {
        cancelButton.removeEventListener('touchstart', cancelButton._mobileHandlers.touchStart);
        cancelButton.removeEventListener('touchend', cancelButton._mobileHandlers.touchEnd);
        delete cancelButton._mobileHandlers;
      }

      // Release wake lock
      if (this.wakeLock) {
        this.wakeLock.release();
        this.wakeLock = null;
      }
    }

    // Unsubscribe from WebSocket events
    this.websocketSubscriptions.forEach(unsubscribe => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    });
    this.websocketSubscriptions = [];
    
    // Unsubscribe from current job
    if (this.currentJob && this.websocketConnected) {
      websocketService.unsubscribeFromJob(this.currentJob.jobId);
    }
    
    // Clear timers
    if (this.messageTimer) {
      clearInterval(this.messageTimer);
      this.messageTimer = null;
    }
    
    console.log('🧹 ProcessingPanel cleaned up');
  }
}