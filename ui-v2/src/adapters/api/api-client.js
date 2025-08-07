/**
 * API Client Adapter voor MCP Backend Integration
 * 
 * Deze adapter voorziet in:
 * - MCP protocol ondersteuning
 * - Backwards compatibility met bestaande API
 * - Automatische fallback naar legacy endpoints
 * - Session management
 * - Real-time updates via WebSocket
 * - Agent configuration en workflow management
 */

import { AgentConfigService } from './agent-config.js';

export class APIClient {
  constructor() {
    this.baseUrl = 'http://localhost:8001';
    this.mcpBaseUrl = `${this.baseUrl}/api/mcp`;
    this.legacyBaseUrl = `${this.baseUrl}/api`;
    
    this.mcpAvailable = false;
    this.sessionId = null;
    this.websocket = null;
    this.agentConfig = null;
    this.isReady = false;
    
    // Initialize async met Promise tracking
    this.readyPromise = this.init();
  }

  async init() {
    try {
      this.agentConfig = new AgentConfigService(this);
      console.log('✅ AgentConfigService initialized');
      await this.checkMCPAvailability();
      
      // Discover agents on initialization
      await this.agentConfig.discoverAgents();
      console.log('✅ Agent discovery completed');
      
      this.isReady = true;
      console.log('✅ API Client fully initialized');
    } catch (error) {
      console.error('❌ API Client initialization failed:', error);
      this.isReady = true; // Still mark as ready to allow fallback
    }
  }

  async waitForReady() {
    await this.readyPromise;
    return this.isReady;
  }

  /**
   * Test of MCP endpoints beschikbaar zijn
   */
  async checkMCPAvailability() {
    // Temporarily disable MCP check until MCP system is fully implemented
    this.mcpAvailable = false;
    console.log('⚠️ MCP temporarily disabled, using legacy API');
  }

  /**
   * Krijg system status
   */
  async getStatus() {
    try {
      // Backend gebruikt /health endpoint
      const url = `${this.baseUrl}/health`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Status check failed: ${response.status}`);
      }
      
      const data = await response.json();
      return {
        ...data,
        mcp_available: this.mcpAvailable
      };
    } catch (error) {
      console.error('Status check error:', error);
      return {
        status: 'error',
        mcp_available: false,
        error: error.message
      };
    }
  }

  /**
   * Start Elite Video Pipeline processing
   */
  async processEliteVideo(input, intent, options = {}) {
    const endpoint = this.mcpAvailable 
      ? `${this.mcpBaseUrl}/pipelines/elite-video`
      : `${this.legacyBaseUrl}/agents/elite-video-pipeline`;
    
    const payload = this.mcpAvailable 
      ? this.buildMCPPayload(input, intent, options)
      : this.buildLegacyPayload(input, intent, options);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`API call failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      if (this.mcpAvailable && result.session_id) {
        this.sessionId = result.session_id;
        this.setupWebSocket(result.session_id);
      }
      
      return result;
    } catch (error) {
      console.error('Elite Video Pipeline error:', error);
      throw error;
    }
  }

  /**
   * Upload file voor processing
   */
  async uploadFile(file, intent, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('intent', intent);
    
    if (this.mcpAvailable) {
      formData.append('return_context', 'true');
      formData.append('session_tracking', 'true');
    }
    
    Object.entries(options).forEach(([key, value]) => {
      formData.append(key, value);
    });

    const endpoint = this.mcpAvailable 
      ? `${this.mcpBaseUrl}/upload`
      : `${this.legacyBaseUrl}/upload`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      if (this.mcpAvailable && result.session_id) {
        this.sessionId = result.session_id;
        this.setupWebSocket(result.session_id);
      }
      
      return result;
    } catch (error) {
      console.error('File upload error:', error);
      throw error;
    }
  }

  /**
   * Process video from URL
   */
  async processVideoUrl(url, intent, options = {}) {
    // URL processing should create a job, not execute agent directly
    const endpoint = `${this.baseUrl}/api/jobs/create`;
    const payload = {
      input_source: url,
      user_id: "user1", // TODO: Get from auth
      workflow_type: intent || "visual_clips",
      ...options
    };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`URL processing failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      console.log('✅ URL processing successful:', result);
      return result;
    } catch (error) {
      console.error('URL processing error:', error);
      throw error;
    }
  }

  /**
   * Krijg session details (alleen MCP)
   */
  async getSessionDetails(sessionId = null) {
    if (!this.mcpAvailable) {
      return { error: 'MCP not available' };
    }

    const id = sessionId || this.sessionId;
    if (!id) {
      return { error: 'No session ID available' };
    }

    try {
      const response = await fetch(`${this.mcpBaseUrl}/sessions/${id}`);
      
      if (!response.ok) {
        throw new Error(`Session fetch failed: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Session fetch error:', error);
      return { error: error.message };
    }
  }

  /**
   * Cleanup session (alleen MCP)
   */
  async cleanupSession(sessionId = null) {
    if (!this.mcpAvailable) return;

    const id = sessionId || this.sessionId;
    if (!id) return;

    try {
      await fetch(`${this.mcpBaseUrl}/sessions/${id}`, {
        method: 'DELETE'
      });
      
      if (this.sessionId === id) {
        this.sessionId = null;
        this.closeWebSocket();
      }
    } catch (error) {
      console.error('Session cleanup error:', error);
    }
  }

  /**
   * Setup WebSocket voor real-time updates
   */
  setupWebSocket(sessionId) {
    if (!this.mcpAvailable || this.websocket) return;

    try {
      this.websocket = new WebSocket(`ws://localhost:8001/ws?session_id=${sessionId}`);
      
      this.websocket.onopen = () => {
        console.log('🔗 WebSocket verbonden');
      };
      
      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleWebSocketMessage(data);
        } catch (error) {
          console.error('WebSocket message parse error:', error);
        }
      };
      
      this.websocket.onclose = () => {
        console.log('🔌 WebSocket verbinding gesloten');
        this.websocket = null;
      };
      
      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('WebSocket setup error:', error);
    }
  }

  /**
   * Handle WebSocket berichten
   */
  handleWebSocketMessage(data) {
    const event = new CustomEvent('mcpUpdate', {
      detail: data
    });
    
    document.dispatchEvent(event);
  }

  /**
   * Call individual MCP agent with context sharing
   */
  async callMCPAgent(agentName, inputData, sessionId = null) {
    if (!this.mcpAvailable) {
      console.warn('MCP not available, falling back to legacy agent call');
      return this.callLegacyAgent(agentName, inputData);
    }

    const url = `${this.mcpBaseUrl}/agents/${agentName}`;
    const payload = {
      input_data: inputData,
      session_id: sessionId || this.sessionId,
      workflow_id: this.currentWorkflow || `single_agent_${Date.now()}`,
      return_context: true,
      mcp_options: {
        session_tracking: true,
        performance_analytics: true,
        context_sharing: true
      }
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`MCP Agent call failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      // Update session ID if provided
      if (result.session_id) {
        this.sessionId = result.session_id;
      }
      
      console.log(`✅ MCP Agent ${agentName} executed successfully`);
      return result;
    } catch (error) {
      console.error(`❌ MCP Agent ${agentName} error:`, error);
      // Fallback to legacy if MCP fails
      return this.callLegacyAgent(agentName, inputData);
    }
  }

  /**
   * Call legacy agent (fallback)
   */
  async callLegacyAgent(agentName, inputData) {
    const url = `${this.legacyBaseUrl}/agents/${agentName}`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(inputData)
      });

      if (!response.ok) {
        throw new Error(`Legacy Agent call failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      console.log(`✅ Legacy Agent ${agentName} executed successfully`);
      return result;
    } catch (error) {
      console.error(`❌ Legacy Agent ${agentName} error:`, error);
      throw error;
    }
  }

  /**
   * Sluit WebSocket verbinding
   */
  closeWebSocket() {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
  }

  /**
   * Bouw MCP payload
   */
  buildMCPPayload(input, intent, options) {
    return {
      input_data: {
        source: input,
        intent: intent,
        ...options
      },
      session_id: this.sessionId,
      return_context: true,
      workflow_id: `elite_video_${intent}_${Date.now()}`,
      mcp_options: {
        session_tracking: true,
        performance_analytics: true,
        resource_optimization: true
      }
    };
  }

  /**
   * Bouw legacy payload
   */
  buildLegacyPayload(input, intent, options) {
    return {
      input: input,
      intent: intent,
      ...options
    };
  }

  /**
   * Algemene agent call (backwards compatible)
   */
  async callAgent(agentName, input, options = {}) {
    // Gebruik agent config voor naam mapping
    const backendAgentName = this.agentConfig.getBackendAgentName(agentName);
    
    // Force legacy API until MCP is working
    const endpoint = `${this.legacyBaseUrl}/agents/${backendAgentName}`;
    const payload = { ...input, ...options };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Agent call failed: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`Agent ${backendAgentName} call error:`, error);
      throw error;
    }
  }

  /**
   * Execute atomic workflow with individual agents
   */
  async executeAtomicWorkflow(workflow, input, options = {}) {
    let currentData = { ...input };
    
    // Transform input format for atomic agents
    if (currentData.video && !currentData.video_path) {
      currentData.video_path = currentData.video;
    }
    
    const totalSteps = workflow.length;
    
    for (let i = 0; i < workflow.length; i++) {
      const agent = workflow[i];
      
      // Update progress
      const progress = (i / totalSteps) * 100;
      this.updateProgress(progress, `Processing with ${agent}...`);
      
      try {
        // Call atomic agent
        const result = await this.callAgent(agent, currentData, options);
        
        if (!result.success) {
          throw new Error(`Agent ${agent} failed: ${result.error}`);
        }
        
        // Merge results for next agent
        currentData = { ...currentData, ...result.data };
        
      } catch (error) {
        // Fallback to legacy system
        console.warn(`Atomic agent ${agent} failed, falling back to legacy`);
        return this.fallbackToLegacy(input, options);
      }
    }
    
    return currentData;
  }

  /**
   * Update progress for external listeners
   */
  updateProgress(progress, message) {
    const event = new CustomEvent('processingProgress', {
      detail: { progress, message }
    });
    document.dispatchEvent(event);
  }

  /**
   * Fallback to legacy system
   */
  async fallbackToLegacy(input, options = {}) {
    console.warn('Falling back to legacy agent system');
    
    // Use original legacy workflow
    const legacyAgents = ['video-analyzer', 'clipper'];
    
    let currentData = input;
    for (const agent of legacyAgents) {
      const result = await this.callAgent(agent, currentData, options);
      currentData = { ...currentData, ...result };
    }
    
    return currentData;
  }

  /**
   * Process video met workflow voor intent
   */
  async processWithIntent(input, intent, options = {}) {
    // Check of workflow beschikbaar is
    const workflowCheck = await this.agentConfig.isWorkflowAvailable(intent);
    
    if (!workflowCheck.available) {
      throw new Error(`Workflow niet beschikbaar voor intent '${intent}': ${workflowCheck.reason}`);
    }

    const workflow = this.agentConfig.getWorkflowForIntent(intent);
    
    if (workflow && workflow.length > 0) {
      // Use atomic workflow
      return await this.executeAtomicWorkflow(workflow, input, options);
    } else {
      // Fallback to legacy
      return await this.fallbackToLegacy(input, options);
    }
  }


  /**
   * Krijg beschikbare intents
   */
  getAvailableIntents() {
    if (!this.agentConfig) {
      throw new Error('API Client nog niet geïnitialiseerd. Gebruik await apiClient.waitForReady()');
    }
    return this.agentConfig.getAvailableIntents();
  }

  /**
   * Krijg agent status
   */
  async getAgentStatus(agentName = null) {
    if (!this.agentConfig) {
      throw new Error('API Client nog niet geïnitialiseerd. Gebruik await apiClient.waitForReady()');
    }
    
    if (agentName) {
      return this.agentConfig.getAgentStatus(agentName);
    }
    
    // Refresh alle agent statuses
    await this.agentConfig.discoverAgents();
    
    return this.agentConfig.getConfigurationSummary();
  }


  /**
   * Create clips from analysis results based on intent
   */
  createClipsFromAnalysis(analysisResult, intent) {
    const clips = [];
    
    // Use detected moments if available
    if (analysisResult.detected_moments && Array.isArray(analysisResult.detected_moments)) {
      analysisResult.detected_moments.forEach((moment, index) => {
        clips.push({
          start_time: moment.start_time || moment.start,
          end_time: moment.end_time || moment.end,
          formatting_mode: "intelligent", // Use intelligent clipper
          text_overlay: moment.description || moment.text || `Clip ${index + 1}`,
          effects: ["fade_in", "fade_out"]
        });
      });
    } else {
      // Fallback: create default clips based on intent
      console.log('⚠️ No detected moments, creating default clips for intent:', intent);
      
      const defaultClips = this.getDefaultClipsForIntent(intent);
      clips.push(...defaultClips);
    }
    
    console.log('📋 Created clips for processing:', clips);
    return clips;
  }

  /**
   * Get default clips configuration for intent
   */
  getDefaultClipsForIntent(intent) {
    const baseClips = [
      { start_time: 0, end_time: 30, formatting_mode: "intelligent", text_overlay: "Opening", effects: ["fade_in", "fade_out"] },
      { start_time: 30, end_time: 60, formatting_mode: "intelligent", text_overlay: "Highlight", effects: ["fade_in", "fade_out"] },
      { start_time: 60, end_time: 90, formatting_mode: "intelligent", text_overlay: "Key Moment", effects: ["fade_in", "fade_out"] }
    ];
    
    switch (intent) {
      case 'short_clips':
        return baseClips.slice(0, 2); // First 2 clips
      case 'key_moments':
        return baseClips.slice(1, 3); // Middle and last clips
      case 'smart_summary':
        return baseClips; // All clips
      default:
        return baseClips.slice(0, 1); // Just first clip
    }
  }

  /**
   * Determine if error is recoverable for retry logic
   */
  isRecoverableError(error) {
    const recoverablePatterns = [
      'timeout',
      'network',
      'connection',
      'service unavailable',
      'rate limit'
    ];
    
    const errorMessage = error.message.toLowerCase();
    return recoverablePatterns.some(pattern => errorMessage.includes(pattern));
  }

  /**
   * Get available intents from agent configuration
   */
  getAvailableIntents() {
    if (!this.agentConfig) {
      console.warn('⚠️ AgentConfig not initialized, returning default intents');
      return ['short_clips', 'key_moments', 'smart_summary'];
    }
    
    return this.agentConfig.getAvailableIntents();
  }

  /**
   * Check if specific intent workflow is available
   */
  async isIntentAvailable(intent) {
    if (!this.agentConfig) {
      return { available: false, reason: 'Agent configuration not ready' };
    }
    
    return await this.agentConfig.isWorkflowAvailable(intent);
  }

  /**
   * Get agent configuration summary for debugging
   */
  getAgentConfigSummary() {
    if (!this.agentConfig) {
      return { error: 'Agent configuration not initialized' };
    }
    
    return this.agentConfig.getConfigurationSummary();
  }

  /**
   * Get existing clips from backend
   */
  async getExistingClips(limit = 10) {
    try {
      const response = await fetch(`${this.legacyBaseUrl}/clips/recent?limit=${limit}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch clips: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Convert backend clip format to frontend format
      const clips = data.clips.map((clip, index) => ({
        url: `${this.baseUrl}${clip.path}`,
        path: clip.path,
        title: clip.filename,
        name: clip.filename,
        duration: clip.validation?.duration || null,
        description: clip.is_valid 
          ? `Size: ${(clip.size / (1024 * 1024)).toFixed(1)}MB${clip.validation?.duration ? `, ${clip.validation.duration.toFixed(1)}s` : ''}`
          : `⚠️ Invalid: ${clip.validation?.error || 'Unknown error'}`,
        created: clip.created,
        aiScore: clip.is_valid ? 8.5 : 0, // Score based on validity
        isValid: clip.is_valid,
        validation: clip.validation
      }));
      
      console.log('✅ Retrieved existing clips:', clips);
      return {
        success: true,
        clips: clips,
        total: data.total_available
      };
      
    } catch (error) {
      console.error('❌ Failed to get existing clips:', error);
      return {
        success: false,
        clips: [],
        error: error.message
      };
    }
  }

  /**
   * Cleanup bij unload
   */
  cleanup() {
    this.closeWebSocket();
    if (this.sessionId) {
      this.cleanupSession();
    }
  }
}

// Cleanup bij page unload
window.addEventListener('beforeunload', () => {
  if (window.apiClient) {
    window.apiClient.cleanup();
  }
});

export default APIClient;