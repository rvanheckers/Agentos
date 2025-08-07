/**
 * Video State Management
 * Handles all video-related state: files, metadata, processing status
 */

export class VideoStore {
  constructor() {
    this.state = {
      // Current video
      currentVideo: null,
      videoMetadata: null,
      uploadProgress: 0,
      
      // Processing
      isProcessing: false,
      processingStage: null, // 'analyzing' | 'extracting' | 'creating'
      processingProgress: 0,
      estimatedTimeRemaining: null,
      
      // Results
      clips: [],
      processingResults: null,
      aiAnalysis: null,
      
      // Upload state
      uploadMethod: null, // 'file' | 'url'
      uploadSource: null,
      uploadError: null,
      
      // Video properties
      duration: null,
      format: null,
      resolution: null,
      fileSize: null
    };
    
    this.listeners = new Set();
  }

  /**
   * Get current state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Update state with partial updates
   */
  setState(updates) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };
    this.notifyListeners(prevState, this.state);
  }

  /**
   * Set current video file
   */
  setCurrentVideo(file, metadata = null) {
    this.setState({
      currentVideo: file,
      videoMetadata: metadata,
      uploadMethod: file instanceof File ? 'file' : 'url',
      uploadSource: file instanceof File ? file.name : file,
      uploadError: null
    });
  }

  /**
   * Update upload progress
   */
  setUploadProgress(progress) {
    this.setState({ uploadProgress: Math.max(0, Math.min(100, progress)) });
  }

  /**
   * Set video metadata
   */
  setVideoMetadata(metadata) {
    this.setState({
      videoMetadata: metadata,
      duration: metadata.duration,
      format: metadata.format,
      resolution: metadata.resolution,
      fileSize: metadata.fileSize
    });
  }

  /**
   * Start processing
   */
  startProcessing(stage = 'analyzing') {
    this.setState({
      isProcessing: true,
      processingStage: stage,
      processingProgress: 0,
      estimatedTimeRemaining: null,
      clips: [],
      processingResults: null
    });
  }

  /**
   * Update processing progress (legacy method)
   */
  updateProcessingProgress(progress, stage = null, timeRemaining = null) {
    const updates = {
      processingProgress: Math.max(0, Math.min(100, progress))
    };
    
    if (stage) updates.processingStage = stage;
    if (timeRemaining !== null) updates.estimatedTimeRemaining = timeRemaining;
    
    this.setState(updates);
  }


  /**
   * Set processing state
   */
  setIsProcessing(isProcessing) {
    this.setState({ isProcessing });
  }

  /**
   * Set processing error
   */
  setProcessingError(error) {
    this.setState({ 
      processingError: error,
      isProcessing: false 
    });
  }

  /**
   * Set processing results
   */
  setProcessingResults(results) {
    this.setState({
      isProcessing: false,
      processingResults: results,
      clips: results.clips || [],
      aiAnalysis: results.analysis || null,
      processingProgress: 100
    });
  }


  /**
   * Add generated clip
   */
  addClip(clip) {
    const clips = [...this.state.clips, clip];
    this.setState({ clips });
  }

  /**
   * Update clip
   */
  updateClip(clipId, updates) {
    const clips = this.state.clips.map(clip => 
      clip.id === clipId ? { ...clip, ...updates } : clip
    );
    this.setState({ clips });
  }

  /**
   * Remove clip
   */
  removeClip(clipId) {
    const clips = this.state.clips.filter(clip => clip.id !== clipId);
    this.setState({ clips });
  }

  /**
   * Reset video state (for new upload)
   */
  reset() {
    this.setState({
      currentVideo: null,
      videoMetadata: null,
      uploadProgress: 0,
      isProcessing: false,
      processingStage: null,
      processingProgress: 0,
      estimatedTimeRemaining: null,
      clips: [],
      processingResults: null,
      aiAnalysis: null,
      uploadMethod: null,
      uploadSource: null,
      uploadError: null,
      duration: null,
      format: null,
      resolution: null,
      fileSize: null
    });
  }

  /**
   * Add state listener
   */
  addListener(callback) {
    this.listeners.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(callback);
    };
  }

  /**
   * Notify all listeners of state changes
   */
  notifyListeners(prevState, newState) {
    this.listeners.forEach(callback => {
      try {
        callback(newState, prevState);
      } catch (error) {
        console.error('VideoStore listener error:', error);
      }
    });
  }

  /**
   * Get processing stage display name
   */
  getProcessingStageDisplay() {
    const stages = {
      'analyzing': 'Analyseren van video content',
      'extracting': 'Beste segmenten selecteren', 
      'creating': 'Video clips genereren'
    };
    return stages[this.state.processingStage] || 'Verwerken...';
  }

  /**
   * Check if video is ready for processing
   */
  isVideoReady() {
    return this.state.currentVideo && !this.state.isProcessing && !this.state.uploadError;
  }

  /**
   * Get formatted file size
   */
  getFormattedFileSize() {
    if (!this.state.fileSize) return null;
    
    const bytes = this.state.fileSize;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  }

  /**
   * Get formatted duration
   */
  getFormattedDuration() {
    if (!this.state.duration) return null;
    
    const minutes = Math.floor(this.state.duration / 60);
    const seconds = Math.floor(this.state.duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }
  
  /**
   * Reset video store to initial state
   */
  reset() {
    console.log('🔄 Resetting VideoStore to initial state');
    
    this.setState({
      // Current video
      currentVideo: null,
      videoMetadata: null,
      uploadProgress: 0,
      
      // Processing
      isProcessing: false,
      processingStage: null,
      processingProgress: 0,
      estimatedTimeRemaining: null,
      processingError: null,
      
      // Results
      clips: [],
      processingResults: null,
      aiAnalysis: null,
      
      // Upload state
      uploadMethod: null,
      uploadSource: null,
      uploadError: null,
      
      // Video properties
      duration: null,
      format: null,
      resolution: null,
      fileSize: null
    });
  }
}

export default VideoStore;