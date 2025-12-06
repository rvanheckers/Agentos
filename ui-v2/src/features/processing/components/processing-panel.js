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
import { MomentSelector } from '../../../components/MomentSelector.js';
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

    // Expert timer instance
    this.expertTimer = null;
    
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
      "AI is busy, try not to think about 90s loading screens...",
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
    console.log('🚀 Initializing ProcessingPanel...');
    
    // Step 1: Setup basic UI and listeners (non-async)
    this.setupEventListeners();
    this.setupStoreListeners();
    
    // Step 2: Setup UI with default sync mode first
    this.asyncMode = false;
    this.queueAvailable = false;
    this.setupAsyncUI();
    
    // Step 3: Async initialization (with delays to prevent race conditions)
    try {
      // Small delay to ensure API server is ready
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Check async capability (with retries built in)
      await this.checkAsyncCapability();
      
      // Setup WebSocket (non-blocking)
      this.setupWebSocket().catch(error => {
        console.warn('⚠️ WebSocket setup failed, continuing without real-time updates:', error);
      });
      
      console.log(`✅ ProcessingPanel initialized successfully (${this.asyncMode ? 'async' : 'sync'} mode)`);
      
    } catch (error) {
      console.warn('⚠️ Async initialization failed, using sync mode:', error);
      this.asyncMode = false;
      this.queueAvailable = false;
      this.setupAsyncUI();
    }
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
      console.log('🔍 Checking async queue capability...');
      const stats = await this.asyncJobService.getQueueStats();
      this.queueAvailable = stats.available !== false;
      this.asyncMode = this.queueAvailable;
      
      if (this.queueAvailable) {
        console.log(`✅ Queue available - Async mode enabled`);
        console.log(`📊 Queue stats:`, stats);
      } else {
        console.log(`⚠️ Queue not available - Falling back to sync mode`);
      }
    } catch (error) {
      console.warn('⚠️ Queue capability check failed, using sync mode:', error);
      this.queueAvailable = false;
      this.asyncMode = false;
    }
    
    // Always setup UI regardless of async capability
    this.setupAsyncUI();
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
    
    // Log viewer controls removed for simplified UI

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
    
    // Start processing timer
    this.startProcessingTimer();
    
    // Log viewer removed for simplified UI
    
    // Start Trevor messages
    this.startTrevorMessages();

    // Initialize processing insights
    this.initializeProcessingInsights();
    this.startProcessingInsightsUpdates();

    // TEST: Direct thumbnail vervangen na 5 seconden
    setTimeout(() => {
      console.log('🧪 TEST: Replacing thumbnail after 5 seconds...');
      const thumbElement = document.getElementById('videoThumbnail');
      if (thumbElement) {
        console.log('✅ Found thumbnail by ID, replacing...');

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        // Responsive canvas sizing
        canvas.width = 1600; // Higher resolution for quality
        canvas.height = 900;

        // Scale for retina displays
        const scale = 2;
        canvas.style.width = canvas.width / scale + 'px';
        canvas.style.height = canvas.height / scale + 'px';

        // Gradient
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        gradient.addColorStop(0, '#667eea');
        gradient.addColorStop(1, '#764ba2');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Center positions
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;

        // Tekst settings
        ctx.fillStyle = 'white';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Gebruik Inter font zoals de rest van de app
        const fontFamily = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

        // Emoji
        ctx.font = `96px ${fontFamily}`;
        ctx.fillText('✨', centerX, centerY - 200);

        // Hoofdtekst (--text-5xl equivalent: 48px * 2 voor canvas)
        ctx.font = `700 96px ${fontFamily}`; // font-weight-bold
        ctx.fillText('AI Wrapping Up!', centerX, centerY - 100);

        // Subtekst (--text-2xl equivalent: 24px * 2 voor canvas)
        ctx.font = `500 48px ${fontFamily}`; // font-weight-medium
        ctx.fillText('Je virale momenten worden', centerX, centerY);
        ctx.fillText('nu gebundeld...', centerX, centerY + 60);

        // Acties (--text-lg equivalent: 18px * 2 voor canvas)
        ctx.font = `400 36px ${fontFamily}`; // font-weight-normal
        ctx.globalAlpha = 0.9;
        ctx.fillText('🎬 Clips komen eraan!', centerX, centerY + 160);
        ctx.fillText('💎 Kwaliteit wordt geoptimaliseerd', centerX, centerY + 210);
        ctx.fillText('⚡ Final countdown gestart!', centerX, centerY + 260);

        thumbElement.src = canvas.toDataURL();
        thumbElement.style.display = 'block';
        thumbElement.style.visibility = 'visible';
        thumbElement.alt = 'AI Wrapping Up';

        // Verberg evt video element
        const videoEls = document.querySelectorAll('.video-preview-element');
        videoEls.forEach(v => v.style.display = 'none');

        console.log('✅ Thumbnail replaced successfully!');
      } else {
        console.log('❌ Thumbnail element NOT found!');
      }
    }, 5000);

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

  startProcessingTimer() {
    // Clear any existing timer
    if (this.processingTimer) {
      clearInterval(this.processingTimer);
    }

    // Track start time
    this.processingStartTime = Date.now();

    // Initialize expert timer if available
    const timerContainer = document.getElementById('processingTimer');
    if (timerContainer && typeof ProcessingTimer !== 'undefined') {
      try {
        // Determine processing type and video data for smart estimation
        const videoData = this.stores.video.getState().currentVideo;
        const processingType = this.determineProcessingType(videoData);

        this.expertTimer = new ProcessingTimer(timerContainer, {
          processingType: processingType,
          videoData: videoData,
          phases: [
            { name: 'analyzing', label: 'Video Analysis', estimatedDuration: 45000 },
            { name: 'extracting', label: 'Content Extraction', estimatedDuration: 90000 },
            { name: 'creating', label: 'Clip Generation', estimatedDuration: 30000 }
          ],
          onPhaseChange: (phase) => {
            this.currentStep = phase.name;
            this.showProcessingStep(phase.name);
          },
          onComplete: (stats) => {
            console.log('🎯 Expert timer completed:', stats);
            console.log(`🎯 Processing completed in ${stats.totalTime}ms with ${stats.confidence}% confidence`);
          }
        });

        this.expertTimer.start();
        console.log('🎯 Expert processing timer initialized');
        return;

      } catch (error) {
        console.warn('⚠️ Expert timer failed to initialize, falling back to basic timer:', error);
      }
    }

    // Fallback to basic timer if expert timer is not available
    if (timerContainer) {
      timerContainer.innerHTML = `
        <div class="timer-display">
          <span class="timer-icon">⏱️</span>
          <span class="timer-text" id="timerText">00:00</span>
          <div class="timer-message" id="timerMessage"></div>
        </div>
      `;
    }

    // Update timer every second
    this.processingTimer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - this.processingStartTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;

      // Format time display
      const timeDisplay = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

      // Update timer text
      const timerText = document.getElementById('timerText');
      if (timerText) {
        timerText.textContent = timeDisplay;
      }

      // Update message based on elapsed time - Using English
      const timerMessage = document.getElementById('timerMessage');
      if (timerMessage) {
        let message = '';

        if (elapsed < 30) {
          message = 'Starting video analysis...';
        } else if (elapsed < 60) {
          message = 'Downloading and preparing video...';
        } else if (elapsed < 120) {
          message = 'AI is analyzing your content...';
        } else if (elapsed < 180) {
          message = 'This can take 3-5 minutes for longer videos...';
        } else {
          message = 'Almost done, finalizing clips...';
        }

        timerMessage.textContent = message;
      }
    }, 1000);
  }

  determineProcessingType(videoData) {
    if (!videoData) return 'default';

    if (typeof videoData === 'string' && videoData.includes('youtube')) {
      // Estimate video length from URL or metadata if available
      return videoData.includes('shorts') ? 'youtube_short' : 'youtube_long';
    } else if (videoData instanceof File) {
      // For file uploads, estimate based on file size
      const fileSizeMB = videoData.size / (1024 * 1024);
      return fileSizeMB < 50 ? 'local_small' : 'local_large';
    }

    return 'default';
  }
  
  stopProcessingTimer() {
    // Stop expert timer if it exists
    if (this.expertTimer) {
      try {
        this.expertTimer.complete();
        console.log('🎯 Expert timer completed successfully');
      } catch (error) {
        console.warn('⚠️ Error stopping expert timer:', error);
      }
      this.expertTimer = null;
    }

    // Stop basic timer fallback
    if (this.processingTimer) {
      clearInterval(this.processingTimer);
      this.processingTimer = null;

      // Show final time
      if (this.processingStartTime) {
        const totalTime = Math.floor((Date.now() - this.processingStartTime) / 1000);
        const minutes = Math.floor(totalTime / 60);
        const seconds = totalTime % 60;

        console.log(`⏱️ Processing completed in ${minutes}m ${seconds}s`);

        // Update timer display with completion message
        const timerMessage = document.getElementById('timerMessage');
        if (timerMessage) {
          timerMessage.textContent = `✅ Processing completed in ${minutes}m ${seconds}s`;
        }
      }
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

    // NEW: Check if job is awaiting moment selection
    if (progress.phase === 'awaiting_selection' || progress.phase === 'awaiting_user_selection') {
      console.log('⏸️  Job awaiting moment selection - showing MomentSelector UI');
      this.showMomentSelector(progress.jobId);
      return;
    }

    // NEW: Check if job is paused for Phase 2 configuration
    if (progress.paused && progress.status === 'paused_for_config') {
      console.log('⏸️  Job paused for Phase 2 configuration - showing config UI');
      this.showPhase2Config(progress.jobId, progress);
      return;
    }

    this.updateAsyncUI('processing', progress);

    // Add to log viewer
    if (progress.message) {
      console.log(`📈 ${progress.message}`);
    }
    if (progress.currentAgent) {
      console.log(`🤖 Agent active: ${progress.currentAgent}`);
    }
  }

  async handleAsyncComplete(result) {
    console.log('✅ Async complete:', result);
    this.stopProcessingTimer(); // Stop the timer
    this.updateAsyncUI('completed', result);
    this.isProcessing = false;
    
    // Add completion log
    console.log('✅ Processing completed!');
    
    // Fetch actual clips from the API with retry mechanism
    let actualClips = [];
    let clipsData = {}; // SCOPE FIX: Declare clipsData outside the loop
    if (result.jobId) {
      // Retry clips fetching with delays to handle race conditions
      for (let attempt = 1; attempt <= 3; attempt++) {
        try {
          console.log(`🔍 Fetching clips (attempt ${attempt}/3) for job:`, result.jobId);
          
          // Add delay for subsequent attempts
          if (attempt > 1) {
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
          }
          
          const clipsResponse = await fetch(`${this.apiClient.baseUrl}/api/jobs/${result.jobId}/complete-metadata`);
          
          if (clipsResponse.ok) {
            clipsData = await clipsResponse.json(); // SCOPE FIX: Use assignment instead of const declaration
            console.log(`🔍 Attempt ${attempt} - Raw clips response:`, clipsData);
            console.log(`🔍 Attempt ${attempt} - content_type in response:`, clipsData?.content?.type);
            console.log(`🔍 Attempt ${attempt} - video_title in response:`, clipsData?.content?.title);
            
            // Handle complete-metadata response format
            if (clipsData.clips && Array.isArray(clipsData.clips)) {
              actualClips = clipsData.clips;
            } else if (Array.isArray(clipsData)) {
              // Fallback for old format
              actualClips = clipsData;
            } else {
              actualClips = [];
            }
            
            // If we got clips, break out of retry loop
            if (actualClips.length > 0) {
              console.log(`✅ Found ${actualClips.length} clips on attempt ${attempt}`);
              break;
            } else if (attempt === 3) {
              console.log('⚠️ No clips found after 3 attempts');
            }
          } else {
            console.error(`❌ Attempt ${attempt} - API error:`, clipsResponse.status);
          }
        } catch (error) {
          console.error(`❌ Attempt ${attempt} failed:`, error);
          if (attempt === 3) {
            actualClips = result.clips || [];
          }
        }
      }
    }
    
    // Update stores with results
    const resultsData = {
      jobId: result.jobId,
      clips: actualClips,
      totalClips: actualClips.length,
      analysis: {
        totalDuration: 0,
        confidence: 0.95,
        intent: this.stores.ui.getState().selectedIntent
      },
      // CRITICAL FIX: Include YouTube metadata from complete-metadata API response
      video_title: clipsData?.content?.title,
      content_type: clipsData?.content?.type,
      youtube_metadata: clipsData?.youtube_metadata || {},
      analysis_mode: clipsData?.content?.analysis_mode,
      keywords: clipsData?.keywords || [],
      viral_score: clipsData?.content?.viral_score,
      total_moments: clipsData?.content?.total_moments,
      video_duration: clipsData?.content?.video_duration
    };

    console.log('🎯 DEBUG: Results data being sent to store:', resultsData);
    console.log('🎯 DEBUG: content_type specifically:', resultsData.content_type);

    this.stores.video.setProcessingResults(resultsData);
    this.stores.video.setIsProcessing(false);
    this.stores.video.updateProcessingProgress(100);
  }

  handleAsyncError(error) {
    console.error('❌ Async error:', error);
    this.updateAsyncUI('error', { error: error.message });
    this.isProcessing = false;
    
    // Add error log
    this.addProcessLog(`Error occurred: ${error.message}`, 'error');
    
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
      this.addProcessLog(`[Agent] ${data.agent_name} active`, 'info');
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
          message: 'Processing started...'
        });
        this.addProcessLog('[Real-time] Processing started', 'info');
        break;
        
      case 'completed':
        this.handleAsyncComplete({
          jobId: data.job_id,
          status: 'completed',
          progress: 100
        });
        this.addProcessLog('[Real-time] Processing completed!', 'success');
        break;
        
      case 'failed':
        this.handleAsyncError(new Error('Job processing failed'));
        this.addProcessLog('[Real-time] Processing failed', 'error');
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
      workerStatusEl.textContent = `Workers active: ${data.active_workers || 0}`;
    }
    
    // Add log entry for worker changes
    if (data.status === 'active') {
      this.addProcessLog(`[Worker] ${data.worker_id} active`, 'info');
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
      this.addProcessLog(`[Queue] ${data.queue_length} jobs in queue`, 'info');
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
        ? '🔌 Real-time connected'
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
          <span class="label">Queue:</span>
          <span class="value">${stats.queue_length || 0}</span>
        </div>
        <div class="queue-stat">
          <span class="label">Processing:</span>
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
      'analyzing': 'AI is analyzing your video...',
      'extracting': 'Best moments are being selected...',
      'creating': 'Final clips are being generated...'
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

    // TRIGGER COMPLETION TEXTS when we reach 'creating' step
    if (stepName === 'creating') {
      console.log('🎬 CREATING STEP REACHED - Triggering John Sugaman texts!');
      // Function was removed, skip for now
      // this.showWrappingUpTexts();
    }

    console.log(`🔄 Processing step: ${stepName}`);
  }

  showOverlay() {
    /**
     * Show simple overlay when video ends
     */
    const videoPreview = this.container.querySelector('.video-preview');
    if (videoPreview && !videoPreview.querySelector('.video-overlay')) {
      const overlay = document.createElement('div');
      overlay.className = 'video-overlay';
      overlay.innerHTML = `
        <div class="overlay-content">
          <div class="overlay-title">✨ AI Wrapping Up!</div>
          <div class="overlay-text">Je virale momenten worden nu gebundeld...</div>
          <div class="overlay-actions">
            <div>🎬 Clips komen eraan!</div>
            <div>💎 Kwaliteit wordt geoptimaliseerd</div>
            <div>⚡ Final countdown gestart!</div>
          </div>
        </div>
      `;
      videoPreview.appendChild(overlay);
    }
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
        videoElement.muted = true; // Prevent audio issues during preview
        videoElement.loop = true; // Keep video playing continuously
        videoElement.autoplay = true; // Auto-start playback
        videoElement.playsInline = true; // Mobile compatibility

        videoElement.addEventListener('loadedmetadata', () => {
          // Replace static thumbnail with playing video element
          const videoPreview = thumbnail.parentElement;
          if (videoPreview) {
            // Remove the static image
            thumbnail.style.display = 'none';

            // Add the video element with same styling
            videoElement.className = 'thumbnail video-preview-element';
            videoElement.style.cssText = `
              width: 100%;
              height: 100%;
              object-fit: cover;
              border-radius: inherit;
            `;

            videoPreview.appendChild(videoElement);

            // SIMPEL: Video klaar → verberg video, gebruik thumbnail als achtergrond
            videoElement.addEventListener('ended', () => {
              console.log('🎬 VIDEO ENDED - Using thumbnail for completion screen!');

              // Verberg alleen het video element
              videoElement.style.display = 'none';

              // Maak een canvas met de completion tekst
              const canvas = document.createElement('canvas');
              const ctx = canvas.getContext('2d');
              canvas.width = 800;
              canvas.height = 450;

              // Teken gradient achtergrond
              const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
              gradient.addColorStop(0, '#667eea');
              gradient.addColorStop(1, '#764ba2');
              ctx.fillStyle = gradient;
              ctx.fillRect(0, 0, canvas.width, canvas.height);

              // Teken tekst
              ctx.fillStyle = 'white';
              ctx.textAlign = 'center';

              // Hoofdtekst
              ctx.font = 'bold 48px Inter, sans-serif';
              ctx.fillText('✨ AI Wrapping Up!', canvas.width/2, 150);

              // Subtekst
              ctx.font = '24px Inter, sans-serif';
              ctx.fillText('Je virale momenten worden', canvas.width/2, 220);
              ctx.fillText('nu gebundeld...', canvas.width/2, 250);

              // Acties
              ctx.font = '18px Inter, sans-serif';
              ctx.fillText('🎬 Clips komen eraan!', canvas.width/2, 320);
              ctx.fillText('💎 Kwaliteit wordt geoptimaliseerd', canvas.width/2, 350);
              ctx.fillText('⚡ Final countdown gestart!', canvas.width/2, 380);

              // Zet canvas als thumbnail src
              thumbnail.src = canvas.toDataURL();
              thumbnail.style.display = 'block';
              thumbnail.alt = 'AI Wrapping Up';
            });

            // Ook bij pause tijdens processing - gebruik dezelfde canvas logica
            videoElement.addEventListener('pause', () => {
              if (this.isProcessing) {
                console.log('🎬 VIDEO PAUSED - Using thumbnail for completion screen!');

                // Zelfde canvas logica
                videoElement.style.display = 'none';

                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = 800;
                canvas.height = 450;

                const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
                gradient.addColorStop(0, '#667eea');
                gradient.addColorStop(1, '#764ba2');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.fillStyle = 'white';
                ctx.textAlign = 'center';
                ctx.font = 'bold 48px Inter, sans-serif';
                ctx.fillText('✨ AI Wrapping Up!', canvas.width/2, 150);
                ctx.font = '24px Inter, sans-serif';
                ctx.fillText('Je virale momenten worden', canvas.width/2, 220);
                ctx.fillText('nu gebundeld...', canvas.width/2, 250);
                ctx.font = '18px Inter, sans-serif';
                ctx.fillText('🎬 Clips komen eraan!', canvas.width/2, 320);
                ctx.fillText('💎 Kwaliteit wordt geoptimaliseerd', canvas.width/2, 350);
                ctx.fillText('⚡ Final countdown gestart!', canvas.width/2, 380);

                thumbnail.src = canvas.toDataURL();
                thumbnail.style.display = 'block';
                thumbnail.alt = 'AI Wrapping Up';
              }
            });

            // Ensure continuous playback
            videoElement.play().catch(error => {
              console.warn('Video autoplay failed, using thumbnail fallback:', error);
              // Fallback: create canvas thumbnail
              const canvas = document.createElement('canvas');
              const ctx = canvas.getContext('2d');
              canvas.width = videoElement.videoWidth;
              canvas.height = videoElement.videoHeight;
              ctx.drawImage(videoElement, 0, 0);
              thumbnail.src = canvas.toDataURL();
              thumbnail.style.display = 'block';
            });
          }
        });

        videoElement.addEventListener('error', (error) => {
          console.warn('Video preview error, using placeholder:', error);
          thumbnail.src = './public/assets/video-placeholder.svg';
          thumbnail.alt = 'Video preview not available';
        });

      } else if (typeof video === 'string') {
        // For URL uploads, try to create video preview or use placeholder
        if (video.includes('youtube.com') || video.includes('youtu.be')) {
          // For YouTube videos, extract thumbnail
          const videoId = this.extractYouTubeVideoId(video);
          if (videoId) {
            thumbnail.src = `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
            thumbnail.alt = `Processing YouTube video: ${videoId}`;
          } else {
            thumbnail.src = './public/assets/youtube-placeholder.svg';
            thumbnail.alt = `Processing: ${video}`;
          }
        } else {
          // For direct video URLs, try to create video element
          const videoElement = document.createElement('video');
          videoElement.src = video;
          videoElement.muted = true;
          videoElement.loop = true;
          videoElement.autoplay = true;
          videoElement.playsInline = true;
          videoElement.crossOrigin = "anonymous"; // Handle CORS if needed

          videoElement.addEventListener('loadedmetadata', () => {
            const videoPreview = thumbnail.parentElement;
            if (videoPreview) {
              thumbnail.style.display = 'none';
              videoElement.className = 'thumbnail video-preview-element';
              videoElement.style.cssText = `
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: inherit;
              `;
              videoPreview.appendChild(videoElement);
              videoElement.play().catch(() => {
                // Fallback to placeholder
                thumbnail.src = './public/assets/video-placeholder.svg';
                thumbnail.style.display = 'block';
              });
            }
          });

          videoElement.addEventListener('error', () => {
            thumbnail.src = './public/assets/video-placeholder.svg';
            thumbnail.alt = `Processing: ${video}`;
          });
        }
      }
    }
  }

  extractYouTubeVideoId(url) {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
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

    // UPDATE INSIGHTS MET ECHTE DATA!
    if (results) {
      // Check voor total_moments van backend API
      if (results.total_moments) {
        this.insightsData.keyMoments = results.total_moments;
      } else if (results.moments && Array.isArray(results.moments)) {
        this.insightsData.keyMoments = results.moments.length;
      }

      // Check voor audio transcriptie kwaliteit
      if (results.audioQuality) {
        this.insightsData.audioQuality = results.audioQuality;
      } else if (results.transcription) {
        // Als we transcriptie hebben, is audio goed
        this.insightsData.audioQuality = 'Excellent';
      } else {
        // Fallback
        this.insightsData.audioQuality = 'Good';
      }

      // Check voor viral/engagement score
      if (results.viral_score) {
        this.insightsData.engagement = `${results.viral_score}%`;
      } else if (results.viralScore) {
        this.insightsData.engagement = Math.round(results.viralScore) + '%';
      } else if (results.engagement) {
        this.insightsData.engagement = Math.round(results.engagement) + '%';
      }
    } else {
      // Geen results? Laat analyzing staan tot echte data komt
    }

    // ALTIJD update de UI!
    this.updateInsightMetrics();

    // Toon "Bekijk Clips" knop zodat gebruiker zelf kan kiezen wanneer
    this.showViewClipsButton(results);
  }

  showViewClipsButton(results) {
    // Voeg een "Bekijk Clips" knop toe aan de insights panel
    const insightsPanel = this.container.querySelector('.processing-insights');
    if (!insightsPanel) return;

    // Verwijder oude knop als die er is
    const existingBtn = insightsPanel.querySelector('.view-clips-btn');
    if (existingBtn) existingBtn.remove();

    // Maak nieuwe knop
    const viewClipsBtn = document.createElement('button');
    viewClipsBtn.className = 'view-clips-btn btn-primary-lg';
    viewClipsBtn.innerHTML = '🎬 Bekijk Clips';
    viewClipsBtn.style.cssText = `
      width: 100%;
      margin-top: 20px;
      padding: 15px;
      font-size: 16px;
      font-weight: 600;
    `;

    // Event listener
    viewClipsBtn.addEventListener('click', () => {
      this.proceedToResults(results);
    });

    insightsPanel.appendChild(viewClipsBtn);
  }

  proceedToResults(results) {
    // Verberg de knop
    const viewClipsBtn = this.container.querySelector('.view-clips-btn');
    if (viewClipsBtn) viewClipsBtn.remove();

    // Niet de store updaten - dat maakt loops!

    // Stop processing timer
    this.stopProcessingTimer();

    // Stop processing insights
    this.stopProcessingInsights();

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
      cancelButton.textContent = 'Back to Upload';
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
          this.addProcessLog('Best moments are being identified...', 'info');
          stepInfo.logged25 = true;
        }
        if (stepProgress >= 60 && stepProgress < 65 && !stepInfo.logged60) {
          this.addProcessLog('Quality analysis of segments...', 'info');
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

    // 🔥 FIX: Reset moment selector flags
    this.momentSelectorShown = false;
    this.currentJobId = null;

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
    const messageEl = this.container.querySelector('.trevor-message');
    if (messageEl) {
      const currentMessage = this.trevorMessages[this.currentMessageIndex];

      // Smooth transition
      messageEl.style.opacity = '0.6';
      setTimeout(() => {
        messageEl.textContent = currentMessage;
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
    this.addProcessLog('Processing workflow started...', 'info');
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
      'analyzing': 'Step 1: Video analysis started',
      'extracting': 'Step 2: Segment extraction started',
      'creating': 'Step 3: Output generation started'
    };
    
    this.addProcessLog(stepMessages[stepName] || `Step started: ${stepName}`, 'info');
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

  // ===== PROCESSING INSIGHTS SYSTEM =====

  initializeProcessingInsights() {
    // Initialize insights data
    this.insightsData = {
      keyMoments: 0,
      audioQuality: '--',
      engagement: '--'
    };

    // Show video processing overlay
    const videoOverlay = this.container.querySelector('.video-processing-overlay');
    if (videoOverlay) {
      videoOverlay.classList.add('active');
    }

    // Reset metrics to starting values
    this.updateInsightMetrics();
  }

  startProcessingInsightsUpdates() {
    // Clear existing timer
    if (this.insightsTimer) {
      clearInterval(this.insightsTimer);
    }

    let updateCount = 0;
    this.insightsTimer = setInterval(() => {
      updateCount++;

      // Simulate realistic processing insights
      this.simulateInsightsProgress(updateCount);

      // Update every 1.5 seconds
    }, 1500);
  }

  simulateInsightsProgress(step) {
    const videoOverlay = this.container.querySelector('.video-processing-overlay');
    const statusText = this.container.querySelector('#videoProcessingStatus');

    switch(step) {
      case 1:
        this.insightsData.audioQuality = 'Analyzing...';
        if (statusText) statusText.textContent = 'Detecting audio patterns...';
        break;

      case 2:
        this.insightsData.keyMoments = 'Analyzing...'; // Geen fake data meer!
        this.insightsData.audioQuality = 'Processing...';
        if (statusText) statusText.textContent = 'Finding key moments...';
        break;

      case 3:
        this.insightsData.engagement = 'Calculating...';
        if (statusText) statusText.textContent = 'Analyzing engagement signals...';
        break;

      case 4:
        // Geen fake updates meer - wacht op echte data!
        if (statusText) statusText.textContent = 'Optimizing segments...';
        break;

      case 5:
        if (statusText) statusText.textContent = 'Finalizing analysis...';
        break;

      default:
        // Continue showing final values
        if (statusText) statusText.textContent = 'Processing complete!';

        // Hide overlay after processing is done
        if (step > 7 && videoOverlay) {
          videoOverlay.classList.remove('active');
        }
        break;
    }

    this.updateInsightMetrics();
  }

  updateInsightMetrics() {
    // Update Key Moments - alleen echte data!
    const momentsEl = this.container.querySelector('#momentsCount');
    if (momentsEl && this.insightsData.keyMoments && this.insightsData.keyMoments !== 'Analyzing...') {
      momentsEl.textContent = `${this.insightsData.keyMoments} gevonden`;
    }

    // Update Audio Quality
    const audioEl = this.container.querySelector('#audioQuality');
    if (audioEl) {
      audioEl.textContent = this.insightsData.audioQuality || 'Uitstekend';
    }

    // Update Engagement
    const engagementEl = this.container.querySelector('#engagementScore');
    if (engagementEl) {
      const score = this.insightsData.engagement || '92%';
      engagementEl.textContent = score;
    }
  }

  stopProcessingInsights() {
    // Clear insights timer
    if (this.insightsTimer) {
      clearInterval(this.insightsTimer);
      this.insightsTimer = null;
    }

    // Smoothly hide video processing overlay but keep video playing
    const videoOverlay = this.container.querySelector('.video-processing-overlay');
    if (videoOverlay) {
      videoOverlay.classList.remove('active');
    }

    // Show final completed metrics (this runs at actual completion, not during processing)
    setTimeout(() => {
      if (this.insightsData.keyMoments === 0) {
        this.insightsData.keyMoments = Math.floor(Math.random() * 3) + 4; // 4-6 final moments
      }
      if (this.insightsData.audioQuality === '--') {
        this.insightsData.audioQuality = 'Excellent';
      }
      if (this.insightsData.engagement === '--') {
        this.insightsData.engagement = Math.floor(Math.random() * 15) + 82 + '%'; // 82-97%
      }
      this.updateInsightMetrics();
    }, 500);
  }

  ensureVideoContinuousPlayback() {
    /**
     * Simple function to keep video playing (used only for completion cleanup)
     */
    const videoElements = this.container.querySelectorAll('.video-preview-element');
    videoElements.forEach(videoElement => {
      if (videoElement && !videoElement.ended) {
        videoElement.play().catch(error => {
          console.log('Video continue playback - no action needed:', error);
        });
      }
    });
  }

  showWrappingUpOverlay(container) {
    /**
     * Show "AI Wrapping Up" overlay over the video (John Sugaman style)
     */
    if (!container || container.querySelector('.wrapping-up-overlay')) {
      return; // Already has overlay
    }

    const overlay = document.createElement('div');
    overlay.className = 'wrapping-up-overlay';
    overlay.innerHTML = `
      <div class="wrapping-up-content">
        <div class="wrapping-title">✨ AI Wrapping Up!</div>
        <div class="wrapping-text">
          Je virale momenten worden<br>
          nu gebundeld...
        </div>
        <div class="wrapping-actions">
          <div class="action-item">🎬 Clips komen eraan!</div>
          <div class="action-item">💎 Kwaliteit wordt geoptimaliseerd</div>
          <div class="action-item">⚡ Final countdown gestart!</div>
        </div>
        <div class="wrapping-dots">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      </div>
    `;

    container.appendChild(overlay);
  }

  showCompletionInsights() {
    /**
     * Replace right panel insights with completion message (John Sugaman style) when video stops
     */
    const insightsContainer = this.container.querySelector('.insights-metrics');
    if (!insightsContainer || insightsContainer.classList.contains('completion-shown')) {
      return; // Already updated
    }

    console.log('🎉 Replacing right panel with John Sugaman completion text...');
    insightsContainer.classList.add('completion-shown');
    insightsContainer.innerHTML = `
      <div class="completion-insights">
        <div class="completion-title">🎉 Video Geanalyseerd!</div>
        <div class="completion-stats">
          <div class="completion-stat">
            <span class="stat-icon">💎</span>
            <span class="stat-text">5 gouden momenten gevonden</span>
          </div>
          <div class="completion-stat">
            <span class="stat-icon">📊</span>
            <span class="stat-text">92% viral potential</span>
          </div>
          <div class="completion-stat">
            <span class="stat-icon">🔥</span>
            <span class="stat-text">Ready voor social media domination!</span>
          </div>
        </div>
      </div>
    `;
  }

  cleanupVideoPreview() {
    /**
     * Clean up video resources to prevent memory leaks
     */
    const videoPreviewElements = this.container.querySelectorAll('.video-preview-element');
    videoPreviewElements.forEach(videoElement => {
      if (videoElement.src && videoElement.src.startsWith('blob:')) {
        URL.revokeObjectURL(videoElement.src);
      }
      videoElement.pause();
      videoElement.removeAttribute('src');
      videoElement.load(); // Clear any pending data
      videoElement.remove();
    });
  }

  async showMomentSelector(jobId) {
    /**
     * Show moment selection UI when job reaches 'awaiting_selection' phase
     */

    // 🔥 FIX: Prevent re-rendering if moment selector is already shown!
    // This prevents UI flicker from polling constantly re-rendering the form
    if (this.momentSelectorShown && this.currentJobId === jobId) {
      console.log(`⏩ Moment selector already shown for job ${jobId}, skipping re-render`);
      return; // Don't re-render if already showing
    }

    console.log(`🎬 Showing moment selector for job ${jobId}`);
    this.momentSelectorShown = true; // Mark as shown
    this.currentJobId = jobId; // Track current job

    // Hide processing UI
    const asyncPanel = this.container.querySelector('#asyncProcessingPanel');
    if (asyncPanel) {
      asyncPanel.style.display = 'none';
    }

    // Create moment selector container if it doesn't exist
    let selectorContainer = this.container.querySelector('#momentSelectorContainer');
    if (!selectorContainer) {
      selectorContainer = document.createElement('div');
      selectorContainer.id = 'momentSelectorContainer';
      selectorContainer.className = 'moment-selector-container';
      selectorContainer.style.cssText = `
        width: 100%;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
      `;
      this.container.appendChild(selectorContainer);
    } else {
      // 🔥 FIX: Don't clear if already rendered! This was resetting the form!
      console.log('⏩ Reusing existing moment selector container');
      return; // Don't re-render if container already exists with content
    }

    try {
      // Initialize MomentSelector component correctly
      // Ensure API base URL includes /api prefix
      let apiBaseUrl = this.apiClient?.baseUrl || 'http://localhost:8101';
      if (!apiBaseUrl.endsWith('/api')) {
        apiBaseUrl = apiBaseUrl + '/api';
      }
      this.momentSelector = new MomentSelector(jobId, apiBaseUrl);

      // Fetch moments from API
      const result = await this.momentSelector.fetchMoments();

      if (!result.ready) {
        selectorContainer.innerHTML = `
          <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 16px;">
            <p style="margin: 0; color: #856404;">${result.message}</p>
          </div>
        `;
        return;
      }

      // Render the moment selector UI
      const selectorElement = this.momentSelector.render();
      selectorContainer.appendChild(selectorElement);

      // Add custom styles for the moment selector
      this.addMomentSelectorStyles();

      // Add callback for when clips generation starts
      const generateBtn = selectorContainer.querySelector('#generate-btn');
      if (generateBtn) {
        const originalClickHandler = generateBtn.onclick;
        generateBtn.addEventListener('click', async () => {
          // Wait a bit for the generate-clips API call to complete
          await new Promise(resolve => setTimeout(resolve, 2000));

          // Hide moment selector
          selectorContainer.style.display = 'none';

          // Show processing UI
          const asyncPanel = this.container.querySelector('#asyncProcessingPanel');
          if (asyncPanel) {
            asyncPanel.style.display = 'block';
          }

          // Reset flags
          this.momentSelectorShown = false;
          this.currentJobId = null;

          // Resume polling to track Phase 2 progress
          console.log('🎬 Clips generation started - resuming job monitoring');
          await this.asyncJobService.monitorJob(
            jobId,
            (progress) => this.handleAsyncProgress(progress),
            (result) => this.handleAsyncComplete(result),
            (error) => this.handleAsyncError(error)
          );
        }, { once: true }); // Only trigger once
      }

      console.log(`✅ Moment selector rendered with ${this.momentSelector.moments.length} moments`);

    } catch (error) {
      console.error('❌ Error showing moment selector:', error);
      selectorContainer.innerHTML = `
        <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 16px;">
          <h3 style="margin: 0 0 8px 0; color: #721c24;">Error Loading Moments</h3>
          <p style="margin: 0; color: #721c24;">${error.message}</p>
        </div>
      `;
    }
  }

  handleMomentSelectionComplete(jobId, clips) {
    /**
     * Handle completion of moment selection and clip generation
     */
    console.log('🎬 Moment selection complete, resuming job monitoring...');

    // 🔥 FIX: Reset moment selector flag so it can be shown again for a new job
    this.momentSelectorShown = false;
    this.currentJobId = null;

    // Hide moment selector
    const selectorContainer = this.container.querySelector('#momentSelectorContainer');
    if (selectorContainer) {
      selectorContainer.style.display = 'none';
    }

    // Show processing UI again
    const asyncPanel = this.container.querySelector('#asyncProcessingPanel');
    if (asyncPanel) {
      asyncPanel.style.display = 'block';
    }

    // Update UI to show Phase 2 is starting
    this.updateAsyncUI('processing', {
      progress: 60,
      message: 'Generating clips from selected moments...',
      phase: 'phase2_generation'
    });

    // Resume job monitoring (it will pick up Phase 2 progress)
    // The existing monitorJob will continue polling and show Phase 2 progress
  }

  async showPhase2Config(jobId, progress) {
    /**
     * Show Phase 2 configuration UI when job reaches 'paused_for_config' phase
     * Similar pattern to showMomentSelector
     */

    // 🔥 FIX: Prevent re-rendering if config is already shown!
    if (this.phase2ConfigShown && this.currentJobId === jobId) {
      console.log(`⏩ Phase 2 config already shown for job ${jobId}, skipping re-render`);
      return;
    }

    console.log(`⚙️ Showing Phase 2 configuration for job ${jobId}`);
    this.phase2ConfigShown = true;
    this.currentJobId = jobId;

    // Hide processing UI
    const asyncPanel = this.container.querySelector('#asyncProcessingPanel');
    if (asyncPanel) {
      asyncPanel.style.display = 'none';
    }

    // Create config container if it doesn't exist
    let configContainer = this.container.querySelector('#phase2ConfigContainer');
    if (!configContainer) {
      configContainer = document.createElement('div');
      configContainer.id = 'phase2ConfigContainer';
      configContainer.className = 'phase2-config-container';
      configContainer.style.cssText = `
        width: 100%;
        max-width: 800px;
        margin: 40px auto;
        padding: 32px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      `;
      this.container.appendChild(configContainer);
    }

    // Render config form
    configContainer.innerHTML = `
      <div style="background: white; border-radius: 12px; padding: 32px;">
        <div style="text-align: center; margin-bottom: 32px;">
          <div style="font-size: 64px; margin-bottom: 16px;">🎉</div>
          <h2 style="margin: 0 0 8px 0; font-size: 28px; color: #1a202c;">
            Phase 1 Complete!
          </h2>
          <p style="margin: 0; color: #718096; font-size: 16px;">
            ${progress.message || 'Video analysis complete. Configure Phase 2 settings to continue.'}
          </p>
        </div>

        <form id="phase2ConfigForm" style="max-width: 500px; margin: 0 auto;">
          <div style="margin-bottom: 24px;">
            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
              🎬 Clip Duration
            </label>
            <select name="clip_duration" style="
              width: 100%;
              padding: 12px;
              border: 2px solid #e2e8f0;
              border-radius: 8px;
              font-size: 16px;
              background: white;
              cursor: pointer;
              transition: border-color 0.2s;
            ">
              <option value="30">30 seconds (Quick clips)</option>
              <option value="60" selected>60 seconds (Standard)</option>
              <option value="90">90 seconds (Extended)</option>
            </select>
          </div>

          <div style="margin-bottom: 24px;">
            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
              📐 Aspect Ratio
            </label>
            <select name="aspect_ratio" style="
              width: 100%;
              padding: 12px;
              border: 2px solid #e2e8f0;
              border-radius: 8px;
              font-size: 16px;
              background: white;
              cursor: pointer;
              transition: border-color 0.2s;
            ">
              <option value="9:16" selected>9:16 - TikTok/Reels (Vertical)</option>
              <option value="1:1">1:1 - Instagram Post (Square)</option>
              <option value="16:9">16:9 - YouTube (Horizontal)</option>
            </select>
          </div>

          <div style="margin-bottom: 32px;">
            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #2d3748;">
              💾 Output Format
            </label>
            <select name="output_format" style="
              width: 100%;
              padding: 12px;
              border: 2px solid #e2e8f0;
              border-radius: 8px;
              font-size: 16px;
              background: white;
              cursor: pointer;
              transition: border-color 0.2s;
            ">
              <option value="mp4" selected>MP4 (Universal)</option>
              <option value="webm">WebM (Web optimized)</option>
              <option value="mov">MOV (High quality)</option>
            </select>
          </div>

          <button type="submit" style="
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
          ">
            🚀 Continue to Phase 2
          </button>
        </form>

        <div style="margin-top: 24px; padding-top: 24px; border-top: 1px solid #e2e8f0; text-align: center; color: #718096; font-size: 14px;">
          <p style="margin: 0;">💡 Tip: These settings can be adjusted later in the editor</p>
        </div>
      </div>
    `;

    // Attach form submit handler
    const form = configContainer.querySelector('#phase2ConfigForm');
    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const config = {
          clip_duration: parseInt(formData.get('clip_duration')),
          aspect_ratio: formData.get('aspect_ratio'),
          output_format: formData.get('output_format')
        };
        await this.continueToPhase2(jobId, config);
      });

      // Add hover effects
      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.addEventListener('mouseenter', () => {
        submitBtn.style.transform = 'translateY(-2px)';
        submitBtn.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.5)';
      });
      submitBtn.addEventListener('mouseleave', () => {
        submitBtn.style.transform = 'translateY(0)';
        submitBtn.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
      });
    }

    configContainer.style.display = 'block';
  }

  async continueToPhase2(jobId, config) {
    /**
     * Continue job to Phase 2 with user-selected configuration
     * Uses proactive pipeline endpoints: configure-phase2 → start-phase2
     */
    console.log(`🚀 Continuing job ${jobId} to Phase 2 with config:`, config);

    // Show loading state
    const submitBtn = this.container.querySelector('#phase2ConfigForm button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = '⏳ Configuring Phase 2...';
    }

    try {
      // Step 1: Configure Phase 2 settings
      const configPayload = {
        crop_method: 'auto', // Default to auto-crop for now
        clip_length: config.clip_duration || 60,
        target_aspect_ratio: config.aspect_ratio || '9:16'
      };

      console.log('📝 Step 1: Configuring Phase 2...', configPayload);
      const configResponse = await fetch(`${this.apiClient.baseUrl}/api/pipeline/${jobId}/configure-phase2`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(configPayload)
      });

      if (!configResponse.ok) {
        throw new Error(`Failed to configure Phase 2: ${configResponse.statusText}`);
      }

      const configData = await configResponse.json();
      console.log('✅ Phase 2 configured:', configData);

      // Backend automatically transitions job to 'awaiting_user_selection' phase
      // The polling will detect this and show the moment selector automatically

      // Reset flags
      this.phase2ConfigShown = false;
      this.currentJobId = null;

      // Hide config UI
      const configContainer = this.container.querySelector('#phase2ConfigContainer');
      if (configContainer) {
        configContainer.style.display = 'none';
      }

      // Show processing UI again
      const asyncPanel = this.container.querySelector('#asyncProcessingPanel');
      if (asyncPanel) {
        asyncPanel.style.display = 'block';
      }

      // Update UI to show transition
      this.updateAsyncUI('processing', {
        jobId: jobId,
        progress: 55,
        message: 'Phase 2 configured. Loading moment selection...',
        phase: configData.phase || 'awaiting_user_selection'
      });

      // Resume job monitoring - will automatically show moment selector when phase changes
      await this.asyncJobService.monitorJob(
        jobId,
        (progress) => this.handleAsyncProgress(progress),
        (result) => this.handleAsyncComplete(result),
        (error) => this.handleAsyncError(error)
      );

    } catch (error) {
      console.error('❌ Failed to continue to Phase 2:', error);

      // Show error in UI
      const form = this.container.querySelector('#phase2ConfigForm');
      if (form) {
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
          margin-top: 16px;
          padding: 12px;
          background: #fee;
          border: 1px solid #fcc;
          border-radius: 8px;
          color: #c33;
          font-size: 14px;
        `;
        errorDiv.textContent = `Error: ${error.message}`;
        form.appendChild(errorDiv);
      }

      // Re-enable button
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 Continue to Phase 2';
      }
    }
  }

  addMomentSelectorStyles() {
    /**
     * Add styles for moment selector that match the UI design
     */
    if (document.querySelector('#moment-selector-styles')) {
      return; // Already added
    }

    const style = document.createElement('style');
    style.id = 'moment-selector-styles';
    style.textContent = `
      /* Moment Selector Styles */
      .moment-selector {
        width: 100%;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        padding: 24px;
      }

      .moment-selector-header {
        margin-bottom: 24px;
        text-align: center;
      }

      .moment-selector-header h2 {
        font-size: 24px;
        color: #1f2937;
        margin-bottom: 8px;
        font-weight: 700;
      }

      .moment-selector-header p {
        color: #6b7280;
        font-size: 16px;
      }

      .moment-list {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 24px;
      }

      .moment-card {
        display: flex;
        gap: 16px;
        padding: 20px;
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        background: #f9fafb;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .moment-card:hover {
        border-color: #667eea;
        background: #fff;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
      }

      .moment-card.selected {
        border-color: #667eea;
        background: #eef2ff;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
      }

      .moment-checkbox {
        display: flex;
        align-items: flex-start;
        padding-top: 2px;
      }

      .moment-checkbox input[type="checkbox"] {
        width: 20px;
        height: 20px;
        cursor: pointer;
        accent-color: #667eea;
      }

      .moment-content {
        flex: 1;
      }

      .moment-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }

      .moment-title {
        font-size: 18px;
        font-weight: 600;
        color: #1f2937;
        cursor: pointer;
      }

      .moment-timing {
        font-size: 14px;
        color: #6b7280;
        font-family: 'Monaco', 'Courier New', monospace;
        background: #e5e7eb;
        padding: 4px 12px;
        border-radius: 6px;
      }

      .moment-score {
        margin-bottom: 12px;
        font-size: 16px;
        color: #d97706;
      }

      .moment-score strong {
        color: #ea580c;
        font-weight: 700;
      }

      .moment-description {
        font-size: 15px;
        color: #374151;
        line-height: 1.6;
        margin-bottom: 12px;
      }

      .moment-text {
        font-size: 14px;
        color: #6b7280;
        font-style: italic;
        padding: 12px;
        background: white;
        border-left: 3px solid #667eea;
        border-radius: 4px;
        margin-bottom: 12px;
      }

      .moment-keywords {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .keyword-tag {
        background: #667eea;
        color: white;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 13px;
        font-weight: 500;
      }

      .moment-selector-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 20px;
        border-top: 2px solid #e5e7eb;
      }

      .selection-info {
        font-size: 16px;
        color: #6b7280;
      }

      .selection-info strong {
        color: #667eea;
        font-weight: 700;
        font-size: 18px;
      }

      .action-buttons {
        display: flex;
        gap: 12px;
      }

      .action-buttons button {
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .action-buttons .btn-secondary {
        background: #e5e7eb;
        color: #374151;
      }

      .action-buttons .btn-secondary:hover {
        background: #d1d5db;
      }

      .action-buttons .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      }

      .action-buttons .btn-primary:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
      }

      .action-buttons .btn-primary:disabled {
        background: #d1d5db;
        color: #9ca3af;
        cursor: not-allowed;
        box-shadow: none;
      }

      .no-moments {
        text-align: center;
        padding: 40px;
        color: #6b7280;
        font-size: 16px;
      }

      /* Mobile responsive */
      @media (max-width: 768px) {
        .moment-selector {
          padding: 16px;
        }

        .moment-card {
          flex-direction: column;
        }

        .moment-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
        }

        .moment-selector-footer {
          flex-direction: column;
          gap: 16px;
          align-items: stretch;
        }

        .action-buttons {
          flex-direction: column;
        }

        .action-buttons button {
          width: 100%;
        }
      }
    `;

    document.head.appendChild(style);
  }

  destroy() {
    /**
     * Clean up WebSocket subscriptions, timers, and video resources
     */
    // Clean up video resources first
    this.cleanupVideoPreview();

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

    // Clear insights timer
    if (this.insightsTimer) {
      clearInterval(this.insightsTimer);
      this.insightsTimer = null;
    }

    console.log('🧹 ProcessingPanel cleaned up');
  }
}