/**
 * Processing Service
 * Handles video processing communication with backend
 * 
 * Features:
 * - WebSocket real-time updates
 * - Progress tracking
 * - Error handling
 * - Processing cancellation
 */

import { APIClient } from '../../../adapters/api/api-client.js';
import { storeManager } from '../../../infrastructure/state/store-manager.js';

export class ProcessingService {
  constructor(apiClient = null) {
    this.apiClient = apiClient || new APIClient();
    this.stores = storeManager;
    this.websocket = null;
    this.processingJobId = null;
    this.isConnected = false;
    this.currentStep = 'analyzing';
    
    // Listen for atomic workflow progress updates
    document.addEventListener('processingProgress', (event) => {
      this.handleAtomicProgressUpdate(event.detail);
    });
  }

  async startProcessing(video, intent) {
    console.log('🔄 Starting processing service:', { video, intent });
    
    try {
      // First try to use APIClient's processWithIntent if available
      if (this.apiClient.processWithIntent) {
        console.log('🚀 Using APIClient processWithIntent for expert-level routing...');
        console.log('📹 Processing video:', video, 'with intent:', intent);
        
        // Use the expert-level workflow routing with timeout
        const result = await Promise.race([
          this.apiClient.processWithIntent(video, intent, {
            progress_callback: (progress) => {
              console.log('📊 Backend progress update:', progress);
              this.handleProgressUpdate({ progress: progress.percentage || 0 });
              if (progress.step) {
                console.log('🔄 Processing step:', progress.step);
                this.handleStepChange({ step: progress.step });
              }
            }
          }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('API processing timeout after 5 minutes')), 300000)) // 5 minuten voor video processing
        ]);
        
        console.log('✅ Backend processing result:', result);
        
        // Process completed successfully
        this.handleProcessingComplete({ results: result });
        return;
      }
      
      // Fallback to legacy processing method
      await this.legacyProcessing(video, intent);
      
    } catch (error) {
      console.error('❌ Processing failed:', error);
      
      // Geen mock processing meer - we willen de echte backend gebruiken
      throw new Error(`Processing failed: ${error.message}`);
    }
  }

  async legacyProcessing(video, intent) {
    // Initialize processing job
    const jobResponse = await this.initializeProcessingJob(video, intent);
    this.processingJobId = jobResponse.job_id;
    
    // Connect to WebSocket for real-time updates
    await this.connectWebSocket(this.processingJobId);
    
    // Start actual processing
    await this.startProcessingJob(this.processingJobId);
    
    console.log('✅ Legacy processing started successfully:', this.processingJobId);
  }

  async mockProcessing(video, intent) {
    console.log('🔧 Starting mock processing workflow...');
    
    // Generate mock job ID
    this.processingJobId = `mock_job_${Date.now()}`;
    
    // Minimum processing time for professional UX (user should see meaningful AI work)
    const MINIMUM_PROCESSING_TIME = 10000; // 10 seconds minimum for professional feel
    const startTime = Date.now();
    
    // Simulate detailed processing steps with professional timing (10+ seconds)
    const steps = [
      { step: 'analyzing', progress: 0, duration: 1200, message: 'Video wordt geladen en gevalideerd...' },
      { step: 'analyzing', progress: 12, duration: 1500, message: 'Audio-kwaliteit analyseren...' },
      { step: 'analyzing', progress: 25, duration: 1800, message: 'Visuele content detectie uitvoeren...' },
      { step: 'analyzing', progress: 40, duration: 1500, message: 'Gezichten en objecten herkennen...' },
      { step: 'analyzing', progress: 50, duration: 1000, message: 'Scene-overgangen detecteren...' },
      { step: 'extracting', progress: 60, duration: 1500, message: 'Emotionele hoogtepunten identificeren...' },
      { step: 'extracting', progress: 70, duration: 1200, message: 'Optimale segmenten selecteren...' },
      { step: 'extracting', progress: 80, duration: 1000, message: 'Timing en duur optimaliseren...' },
      { step: 'creating', progress: 87, duration: 1200, message: 'Video clips genereren...' },
      { step: 'creating', progress: 94, duration: 1000, message: 'Kwaliteit optimaliseren...' },
      { step: 'creating', progress: 98, duration: 800, message: 'Metadata voorbereiden...' },
      { step: 'creating', progress: 100, duration: 600, message: 'Voltooien en finaliseren...' }
    ];
    
    // Execute steps with detailed progress feedback
    for (const stepData of steps) {
      await new Promise(resolve => setTimeout(resolve, stepData.duration));
      
      this.handleStepChange({ 
        step: stepData.step,
        message: stepData.message,
        substep: this.getSubstepName(stepData.step, stepData.progress)
      });
      
      this.handleProgressUpdate({ 
        progress: stepData.progress,
        step: stepData.step,
        message: stepData.message
      });
      
      console.log(`📊 Processing step: ${stepData.step} - ${stepData.progress}% - ${stepData.message}`);
    }
    
    // Ensure minimum processing time has elapsed
    const elapsedTime = Date.now() - startTime;
    if (elapsedTime < MINIMUM_PROCESSING_TIME) {
      const remainingTime = MINIMUM_PROCESSING_TIME - elapsedTime;
      console.log(`⏱️ Ensuring minimum processing time, waiting additional ${remainingTime}ms...`);
      
      // Show final processing message during wait
      this.handleProgressUpdate({ 
        progress: 100,
        message: 'AI-analyse voltooid, resultaten worden voorbereid voor weergave...'
      });
      
      await new Promise(resolve => setTimeout(resolve, remainingTime));
    }
    
    // Generate mock results
    const mockResults = this.generateMockResults(video, intent);
    this.handleProcessingComplete({ results: mockResults });
    
    console.log('✅ Mock processing completed successfully');
  }

  getSubstepName(step, progress) {
    const substeps = {
      analyzing: {
        0: 'Initialiseren',
        12: 'Audio-analyse',
        25: 'Visuele detectie',
        40: 'Object herkenning',
        50: 'Scene-analyse'
      },
      extracting: {
        60: 'Hoogtepunt detectie',
        70: 'Segment selectie',
        80: 'Timing optimalisatie'
      },
      creating: {
        87: 'Video generatie',
        94: 'Kwaliteit controle',
        98: 'Metadata prep',
        100: 'Finalisering'
      }
    };
    
    const stepSubsteps = substeps[step] || {};
    const closestProgress = Object.keys(stepSubsteps)
      .map(Number)
      .filter(p => p <= progress)
      .sort((a, b) => b - a)[0];
    
    return stepSubsteps[closestProgress] || step;
  }

  generateMockResults(video, intent) {
    const clipCount = intent === 'smart_summary' ? 1 : Math.floor(Math.random() * 3) + 2;
    const clips = [];
    
    for (let i = 0; i < clipCount; i++) {
      clips.push({
        url: `./io/output/mock_clip_${i + 1}_${intent}.mp4`,
        name: `mock_clip_${i + 1}_${intent}.mp4`,
        description: `AI heeft dit segment geïdentificeerd als ${this.getMockClipDescription(i, intent)}`,
        aiScore: (7.5 + Math.random() * 2.5).toFixed(1),
        duration: Math.floor(20 + Math.random() * 40),
        type: ['best_moment', 'emotional_peak', 'action_scene', 'highlight'][i] || 'highlight',
        thumbnail: `./io/output/mock_clip_${i + 1}_thumb.jpg`
      });
    }
    
    return {
      clips: clips,
      analysis: {
        totalDuration: clips.reduce((sum, clip) => sum + clip.duration, 0),
        confidence: 0.85 + Math.random() * 0.15,
        intent: intent,
        processing_time: '2.3s',
        mock_mode: true
      },
      metadata: {
        processed_at: new Date().toISOString(),
        video_source: typeof video === 'string' ? 'url' : 'file',
        mock_generated: true
      }
    };
  }

  getMockClipDescription(index, intent) {
    const descriptions = {
      short_clips: ['perfect TikTok moment', 'viral potential clip', 'engaging highlight'],
      key_moments: ['hoogtepunt van de video', 'emotioneel piekmoment', 'actie scene'],
      smart_summary: ['belangrijk segment', 'kerninhoud', 'essentieel deel']
    };
    
    const intentDescriptions = descriptions[intent] || descriptions.short_clips;
    return intentDescriptions[index] || intentDescriptions[0];
  }

  async initializeProcessingJob(video, intent) {
    console.log('📋 Initializing processing job...');
    
    const payload = {
      intent: intent,
      video_info: this.getVideoInfo(video),
      processing_options: this.getProcessingOptions(intent)
    };
    
    try {
      const response = await this.apiClient.post('/api/processing/init', payload);
      console.log('✅ Processing job initialized:', response.job_id);
      return response;
    } catch (error) {
      console.error('❌ Failed to initialize processing job:', error);
      throw new Error('Kan verwerkingssessie niet starten');
    }
  }

  getVideoInfo(video) {
    if (video instanceof File) {
      return {
        type: 'file',
        name: video.name,
        size: video.size,
        mime_type: video.type,
        duration: null // Will be detected by backend
      };
    } else if (typeof video === 'string') {
      return {
        type: 'url',
        url: video,
        source: this.detectVideoSource(video)
      };
    }
    
    return { type: 'unknown' };
  }

  detectVideoSource(url) {
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      return 'youtube';
    } else if (url.includes('vimeo.com')) {
      return 'vimeo';
    } else if (url.includes('twitch.tv')) {
      return 'twitch';
    }
    return 'direct';
  }

  getProcessingOptions(intent) {
    const options = {
      short_clips: {
        segment_duration: 60,
        max_segments: 5,
        quality: 'high',
        optimize_for: 'engagement'
      },
      key_moments: {
        segment_duration: 180,
        max_segments: 3,
        quality: 'high',
        optimize_for: 'highlights'
      },
      smart_summary: {
        target_duration: 300,
        max_segments: 1,
        quality: 'high',
        optimize_for: 'content'
      }
    };
    
    return options[intent] || options.short_clips;
  }

  async connectWebSocket(jobId) {
    console.log('🔌 Connecting to WebSocket for job:', jobId);
    
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `ws://localhost:8001/ws/processing/${jobId}`;
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
          console.log('✅ WebSocket connected');
          this.isConnected = true;
          resolve();
        };
        
        this.websocket.onmessage = (event) => {
          this.handleWebSocketMessage(event);
        };
        
        this.websocket.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          this.isConnected = false;
          reject(new Error('WebSocket verbinding mislukt'));
        };
        
        this.websocket.onclose = () => {
          console.log('🔌 WebSocket disconnected');
          this.isConnected = false;
        };
        
        // Connection timeout
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error('WebSocket verbinding timeout'));
          }
        }, 5000);
        
      } catch (error) {
        console.error('❌ Error creating WebSocket:', error);
        reject(error);
      }
    });
  }

  handleWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);
      console.log('📨 WebSocket message:', data);
      
      switch (data.type) {
        case 'progress':
          this.handleProgressUpdate(data);
          break;
        case 'step_change':
          this.handleStepChange(data);
          break;
        case 'completed':
          this.handleProcessingComplete(data);
          break;
        case 'error':
          this.handleProcessingError(data);
          break;
        case 'cancelled':
          this.handleProcessingCancelled(data);
          break;
        default:
          console.log('📨 Unknown WebSocket message type:', data.type);
      }
    } catch (error) {
      console.error('❌ Error parsing WebSocket message:', error);
    }
  }

  handleProgressUpdate(data) {
    console.log('📊 Progress update:', data.progress);
    
    // Update store with progress - use the correct parameters
    this.stores.video.updateProcessingProgress(
      data.progress, 
      data.step || this.currentStep, 
      data.time_remaining
    );
    
    // Update time estimate if provided
    if (data.time_remaining) {
      this.stores.video.setProcessingTimeEstimate(data.time_remaining);
    }
  }

  handleStepChange(data) {
    console.log('🔄 Processing step change:', data.step);
    
    // Update current step
    this.currentStep = data.step;
    
    // Update current processing step
    this.stores.video.updateProcessingProgress(data.progress || 0, data.step);
  }

  handleProcessingComplete(data) {
    console.log('✅ Processing completed:', data.results);
    
    // Update store with results
    this.stores.video.setProcessingResults(data.results);
    this.stores.video.setIsProcessing(false);
    
    // Close WebSocket
    this.closeWebSocket();
  }

  handleProcessingError(data) {
    console.error('❌ Processing error from WebSocket:', data.error);
    
    // Update store with error
    this.stores.video.setProcessingError(data.error);
    this.stores.video.setIsProcessing(false);
    
    // Close WebSocket
    this.closeWebSocket();
  }

  handleProcessingCancelled(data) {
    console.log('🛑 Processing cancelled:', data.reason);
    
    // Update store
    this.stores.video.setProcessingError('Verwerking geannuleerd');
    this.stores.video.setIsProcessing(false);
    
    // Close WebSocket
    this.closeWebSocket();
  }

  async startProcessingJob(jobId) {
    console.log('▶️ Starting processing job:', jobId);
    
    try {
      const response = await this.apiClient.post(`/api/processing/${jobId}/start`);
      console.log('✅ Processing job started:', response);
      return response;
    } catch (error) {
      console.error('❌ Failed to start processing job:', error);
      throw new Error('Kan verwerking niet starten');
    }
  }

  async cancelProcessing() {
    console.log('🛑 Cancelling processing job:', this.processingJobId);
    
    if (!this.processingJobId) {
      throw new Error('Geen actieve verwerkingssessie om te annuleren');
    }
    
    try {
      // Cancel via API
      await this.apiClient.post(`/api/processing/${this.processingJobId}/cancel`);
      
      // Close WebSocket
      this.closeWebSocket();
      
      // Reset state
      this.processingJobId = null;
      
      console.log('✅ Processing cancelled successfully');
      
    } catch (error) {
      console.error('❌ Error cancelling processing:', error);
      throw new Error('Kan verwerking niet annuleren');
    }
  }

  closeWebSocket() {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
      this.isConnected = false;
      console.log('🔌 WebSocket closed');
    }
  }

  // Fallback for when WebSocket is not available
  async pollProcessingStatus() {
    if (!this.processingJobId) return;
    
    console.log('📊 Polling processing status (fallback mode)');
    
    try {
      const response = await this.apiClient.get(`/api/processing/${this.processingJobId}/status`);
      
      // Simulate WebSocket messages
      if (response.status === 'completed') {
        this.handleProcessingComplete({ results: response.results });
      } else if (response.status === 'error') {
        this.handleProcessingError({ error: response.error });
      } else if (response.status === 'processing') {
        this.handleProgressUpdate({ progress: response.progress });
        
        // Continue polling
        setTimeout(() => this.pollProcessingStatus(), 2000);
      }
      
    } catch (error) {
      console.error('❌ Error polling processing status:', error);
      this.handleProcessingError({ error: 'Verbinding met server verloren' });
    }
  }

  getProcessingJobId() {
    return this.processingJobId;
  }

  isProcessingActive() {
    return this.processingJobId !== null && this.stores.video.getState().isProcessing;
  }

  /**
   * Handle atomic workflow progress updates
   */
  handleAtomicProgressUpdate(progressData) {
    const { progress, message } = progressData;
    
    // Extract agent name from message to determine step
    const agentName = this.extractAgentFromMessage(message);
    const stepName = this.getStepNameFromAgent(agentName);
    
    console.log('📊 Atomic workflow progress:', {
      progress,
      message,
      agentName,
      stepName
    });
    
    // Update store with atomic workflow progress
    this.stores.video.updateProcessingProgress(progress, stepName);
  }

  /**
   * Extract agent name from progress message
   */
  extractAgentFromMessage(message) {
    if (!message) return null;
    
    const agentPatterns = [
      'video_downloader',
      'audio_transcriber', 
      'moment_detector',
      'face_detector',
      'intelligent_cropper',
      'video_cutter',
      'script_generator'
    ];
    
    for (const agent of agentPatterns) {
      if (message.includes(agent)) {
        return agent;
      }
    }
    
    return null;
  }

  /**
   * Get user-friendly step name from agent name
   */
  getStepNameFromAgent(agentName) {
    const stepNames = {
      'video_downloader': 'Video downloaden...',
      'audio_transcriber': 'Audio transcriberen...',
      'moment_detector': 'Top 3 virale momenten detecteren...',
      'face_detector': 'Gezichten detecteren voor alle clips...',
      'intelligent_cropper': 'Slimme framing per clip berekenen...',
      'video_cutter': '3 AI clips genereren...',
      'script_generator': 'Script genereren...'
    };
    
    return stepNames[agentName] || 'Verwerken...';
  }

  /**
   * Update progress for atomic workflow
   */
  updateProgressForAtomicWorkflow(completedAgents, totalAgents, currentAgent) {
    const progress = (completedAgents / totalAgents) * 100;
    const stepName = this.getStepNameFromAgent(currentAgent);
    
    this.stores.video.updateProcessingProgress(progress, stepName);
  }
}