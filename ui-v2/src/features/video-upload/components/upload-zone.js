/**
 * Upload Zone Component
 * Replaces dashboard.js upload logic (lines 500-800)
 * Clean component-based file upload with drag & drop
 */

import { storeManager } from '../../../infrastructure/state/store-manager.js';
import { UploadService } from '../services/upload-service.js';
import { FileValidator } from '../services/file-validator.js';
import i18n from '../../../i18n/utils/i18n.js';

export class UploadZone {
  constructor(container, dependencies = {}) {
    console.log('🔍 UPLOADZONE: Constructor called');
    console.log('🔍 UPLOADZONE: dependencies.apiClient exists:', !!dependencies.apiClient);
    console.log('🔍 UPLOADZONE: dependencies.apiClient.baseUrl:', dependencies.apiClient?.baseUrl);
    
    this.container = container;
    this.stores = dependencies.stores || storeManager;
    this.apiClient = dependencies.apiClient;
    
    console.log('🔍 UPLOADZONE: this.apiClient exists:', !!this.apiClient);
    console.log('🔍 UPLOADZONE: this.apiClient.baseUrl:', this.apiClient?.baseUrl);
    console.log('🔍 UPLOADZONE: About to create UploadService with apiClient');
    
    this.uploadService = new UploadService(this.apiClient);
    this.validator = new FileValidator();
    
    this.isDragActive = false;
    this.isUploading = false;
    this.eventListenersAttached = false;
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupStoreListeners();
    console.log('✅ UploadZone component initialized');
    
    // Make available for debugging
    if (typeof window !== 'undefined') {
      window.uploadZone = this;
      
      // Auto-check function for issues
      window.uploadZone.autoCheck = () => {
        console.log('🔍 AUTO-CHECKING UPLOAD ZONE...');
        this.runFullDiagnostic();
        
        // Check if upload step container is hidden
        const uploadStepContainer = document.querySelector('#stepUpload, .step-upload');
        if (uploadStepContainer && uploadStepContainer.classList.contains('hidden')) {
          console.log('🚨 DETECTED ISSUE: Upload step container is hidden!');
          console.log('🔧 AUTO-FIXING STEP VISIBILITY...');
          uploadStepContainer.classList.remove('hidden');
          uploadStepContainer.classList.add('active');
        }
        
        // If upload zone exists but no click handler, auto-fix
        const uploadZone = document.querySelector('#uploadZone');
        if (uploadZone && !this.uploadZoneClickHandler) {
          console.log('🚨 DETECTED ISSUE: Upload zone exists but no click handler!');
          console.log('🔧 AUTO-FIXING...');
          this.forceFixUpload();
        }
        
        // Check if upload zone itself is not visible
        if (uploadZone) {
          const rect = uploadZone.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0) {
            console.log('🚨 DETECTED ISSUE: Upload zone has zero dimensions!');
            console.log('🔧 AUTO-FIXING UPLOAD ZONE VISIBILITY...');
            
            // Force reset CSS properties
            uploadZone.style.display = '';
            uploadZone.style.visibility = '';
            uploadZone.style.opacity = '';
            uploadZone.classList.remove('hidden', 'upload-hidden');
            
            // Ensure parent container is visible
            if (uploadStepContainer) {
              uploadStepContainer.classList.remove('hidden');
              uploadStepContainer.classList.add('active');
            }
          }
        }
      };
      
      // Test command - simulates what should happen
      window.uploadZone.testCommands = () => {
        console.log('🧪 === TESTING ALL COMMANDS ===');
        
        console.log('📋 Available commands:');
        console.log('  window.uploadZone.runFullDiagnostic() - Run complete diagnostic');
        console.log('  window.uploadZone.autoCheck() - Check for issues');  
        console.log('  window.uploadZone.forceFixUpload() - Force fix upload');
        console.log('  window.uploadZone.forceTestClick() - Test click');
        console.log('  window.uploadZone.debugStatus() - Show debug status');
        
        console.log('🧪 Running test sequence...');
        
        setTimeout(() => {
          console.log('1️⃣ Running diagnostic...');
          this.runFullDiagnostic();
        }, 1000);
        
        setTimeout(() => {
          console.log('2️⃣ Running auto-check...');
          this.autoCheck();
        }, 2000);
        
        // REMOVED: Automatic forceTestClick - should only be triggered manually
        // setTimeout(() => {
        //   console.log('3️⃣ Testing click...');
        //   this.forceTestClick();
        // }, 3000);
        
        setTimeout(() => {
          console.log('4️⃣ Debug status...');
          this.debugStatus();
        }, 4000);
        
        setTimeout(() => {
          console.log('✅ All test commands completed!');
          console.log('💡 You can now run individual commands manually');
        }, 5000);
      };
      
      // Auto-check every 5 seconds when on upload step
      this.autoCheckInterval = setInterval(() => {
        const currentStep = this.stores?.ui?.getState()?.currentStep;
        if (currentStep === 'upload') {
          const uploadZone = document.querySelector('#uploadZone');
          const hasHandler = !!this.uploadZoneClickHandler;
          
          if (uploadZone && !hasHandler) {
            console.log('🚨 AUTO-DETECTED UPLOAD ISSUE - FIXING...');
            this.forceFixUpload();
          }
        }
      }, 5000);
    }
  }
  
  removeEventListeners() {
    console.log('🧹 Removing event listeners');
    
    // Remove click listeners from upload zone
    if (this.uploadZoneElement && this.uploadZoneClickHandler) {
      this.uploadZoneElement.removeEventListener('click', this.uploadZoneClickHandler);
      console.log('🧹 Removed click listener from upload zone');
    }
    
    // Remove change listener from file input
    if (this.fileInputElement && this.fileInputChangeHandler) {
      this.fileInputElement.removeEventListener('change', this.fileInputChangeHandler);
      console.log('🧹 Removed change listener from file input');
    }
    
    // Remove drag listeners
    if (this.uploadZoneElement) {
      if (this.dragOverHandler) {
        this.uploadZoneElement.removeEventListener('dragover', this.dragOverHandler);
        console.log('🧹 Removed dragover listener');
      }
      if (this.dragLeaveHandler) {
        this.uploadZoneElement.removeEventListener('dragleave', this.dragLeaveHandler);
        console.log('🧹 Removed dragleave listener');
      }
      if (this.dropHandler) {
        this.uploadZoneElement.removeEventListener('drop', this.dropHandler);
        console.log('🧹 Removed drop listener');
      }
    }
    
    // Clear references
    this.uploadZoneElement = null;
    this.fileInputElement = null;
    this.uploadZoneClickHandler = null;
    this.fileInputChangeHandler = null;
    this.dragOverHandler = null;
    this.dragLeaveHandler = null;
    this.dropHandler = null;
    this.eventListenersAttached = false;
  }

  setupEventListeners() {
    // Prevent duplicate setup
    if (this.eventListenersAttached) {
      console.log('⚠️ Event listeners already attached, skipping setup');
      return;
    }
    
    // Always remove existing listeners first to ensure clean state
    this.removeEventListeners();
    
    // Extra safety: remove any orphaned listeners from document
    const existingUploadZone = document.querySelector('#uploadZone');
    const existingFileInput = document.querySelector('#fileInput');
    if (existingUploadZone && existingUploadZone._uploadClickHandler) {
      existingUploadZone.removeEventListener('click', existingUploadZone._uploadClickHandler);
      delete existingUploadZone._uploadClickHandler;
    }
    if (existingFileInput && existingFileInput._uploadChangeHandler) {
      existingFileInput.removeEventListener('change', existingFileInput._uploadChangeHandler);
      delete existingFileInput._uploadChangeHandler;
    }
    
    // Try multiple ways to find the upload zone and file input
    let uploadZone = this.container.querySelector('#uploadZone');
    let fileInput = this.container.querySelector('#fileInput');
    
    // Fallback: try to find in document if not in container
    if (!uploadZone) {
      uploadZone = document.querySelector('#uploadZone');
      console.log('🔍 Upload zone found in document (not container):', !!uploadZone);
    }
    if (!fileInput) {
      fileInput = document.querySelector('#fileInput');
      console.log('🔍 File input found in document (not container):', !!fileInput);
    }
    
    // Second fallback: try by class name
    if (!uploadZone) {
      uploadZone = this.container.querySelector('.upload-zone') || document.querySelector('.upload-zone');
      console.log('🔍 Upload zone found by class:', !!uploadZone);
    }
    
    console.log('🔧 Setting up event listeners - uploadZone:', !!uploadZone, 'fileInput:', !!fileInput);
    
    if (uploadZone && fileInput) {
      // Store event handlers for potential cleanup
      this.uploadZoneClickHandler = (e) => {
        console.log('🖱️ Upload zone clicked, isUploading:', this.isUploading);
        
        // Don't prevent default if target is already the file input
        if (e.target.id === 'fileInput') {
          console.log('🖱️ Click on file input directly, allowing default');
          return;
        }
        
        e.preventDefault();
        e.stopPropagation();
        
        if (!this.isUploading) {
          console.log('🖱️ Triggering file input click');
          // Use setTimeout to avoid event conflicts
          setTimeout(() => {
            fileInput.click();
          }, 0);
        } else {
          console.log('🖱️ Not clicking because isUploading is true');
        }
      };
      
      this.fileInputChangeHandler = (e) => {
        console.log('📁 File selected:', e.target.files[0]?.name);
        if (e.target.files.length > 0) {
          this.handleFileUpload(e.target.files[0]);
        }
      };
      
      this.dragOverHandler = (e) => this.handleDragOver(e);
      this.dragLeaveHandler = (e) => this.handleDragLeave(e);
      this.dropHandler = (e) => this.handleDrop(e);

      uploadZone.addEventListener('click', this.uploadZoneClickHandler);
      fileInput.addEventListener('change', this.fileInputChangeHandler);

      // Drag & Drop events
      uploadZone.addEventListener('dragover', this.dragOverHandler);
      uploadZone.addEventListener('dragleave', this.dragLeaveHandler);
      uploadZone.addEventListener('drop', this.dropHandler);

      // Mobile touch interactions
      this.setupMobileTouchInteractions(uploadZone, fileInput);
      
      // Store handlers on DOM elements for orphan cleanup
      uploadZone._uploadClickHandler = this.uploadZoneClickHandler;
      fileInput._uploadChangeHandler = this.fileInputChangeHandler;
      
      // Store references for cleanup
      this.uploadZoneElement = uploadZone;
      this.fileInputElement = fileInput;
      this.eventListenersAttached = true;
      
      console.log('✅ Event listeners successfully attached');
    } else {
      console.error('❌ Could not find upload zone or file input elements');
      console.log('Container:', this.container);
      console.log('Available elements in container:', this.container.querySelectorAll('*'));
    }

    // URL upload
    const urlInput = this.container.querySelector('#urlInput');
    const urlSubmit = this.container.querySelector('#urlSubmit');
    
    if (urlInput && urlSubmit) {
      urlSubmit.addEventListener('click', () => this.handleUrlUpload());
      urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          this.handleUrlUpload();
        }
      });
    }
  }

  setupStoreListeners() {
    // Listen to upload progress
    this.stores.video.addListener((newState, prevState) => {
      if (newState.uploadProgress !== prevState.uploadProgress) {
        this.updateUploadProgress(newState.uploadProgress);
      }
      
      if (newState.uploadError !== prevState.uploadError && newState.uploadError) {
        this.handleUploadError(newState.uploadError);
      }
    });

    // Listen to UI state changes
    this.stores.ui.addListener((newState, prevState) => {
      if (newState.dragOverActive !== prevState.dragOverActive) {
        this.updateDragState(newState.dragOverActive);
      }
      
      // Reset upload zone when navigating back to upload step
      if (newState.currentStep === 'upload' && prevState.currentStep !== 'upload') {
        console.log('🔄 Navigated to upload step, resetting upload zone');
        this.resetUploadZone();
      }
      
      // Handle new session after completing processing
      if (newState.currentStep === 'intent' && prevState.currentStep === 'results') {
        console.log('🔄 New session started from results, preparing for complete reset');
        this.prepareForNewSession();
      }
      
      // Extra reset when going from intent to upload (after processing completion)
      if (newState.currentStep === 'upload' && prevState.currentStep === 'intent') {
        console.log('🔄 Moving to upload after intent, ensuring clean state');
        setTimeout(() => {
          this.forceCompleteReset();
        }, 100);
      }
    });
  }

  handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    
    if (!this.isDragActive) {
      this.isDragActive = true;
      this.stores.ui.setDragOverActive(true);
      this.updateDragVisuals(true);
    }
  }

  handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Only handle if leaving the main container
    if (!this.container.contains(e.relatedTarget)) {
      this.isDragActive = false;
      this.stores.ui.setDragOverActive(false);
      this.updateDragVisuals(false);
    }
  }

  handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    this.isDragActive = false;
    this.stores.ui.setDragOverActive(false);
    this.updateDragVisuals(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      this.handleFileUpload(files[0]);
    }
  }

  async handleFileUpload(file) {
    console.log('🔄 Starting file upload:', file.name);
    console.log('🔍 File details:', { name: file.name, size: file.size, type: file.type });
    
    try {
      // Validate file
      console.log('🔍 About to validate file...');
      const validation = this.validator.validateFile(file);
      console.log('🔍 Validation result:', validation);
      
      if (!validation.valid) {
        console.error('❌ File validation failed:', validation.error);
        this.stores.ui.showError(validation.error);
        return;
      }
      
      console.log('✅ File validation passed');

      console.log('🚀 DEBUG: Starting upload process for:', file.name);
      
      this.isUploading = true;
      this.updateUploadState(true);
      
      console.log('🚀 DEBUG: Set upload state');
      
      // Set video in store
      this.stores.video.setCurrentVideo(file, {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified
      });

      console.log('🚀 DEBUG: Set current video in store');

      // Show upload started feedback
      this.showUserFeedback('info', i18n.t('upload.feedback.upload_started', { fileName: file.name }), 0);
      
      console.log('🚀 DEBUG: Showed user feedback');
      
      // Start upload with progress tracking
      console.log('🔄 About to call uploadService.uploadFile with file:', file.name);
      let result;
      try {
        result = await this.uploadService.uploadFile(file, (progress) => {
          this.stores.video.setUploadProgress(progress);
          this.updateUploadProgressFeedback(progress);
        });
        console.log('✅ uploadService.uploadFile returned:', result);
      } catch (uploadError) {
        console.error('❌ uploadService.uploadFile failed:', uploadError);
        console.error('❌ Upload error details:', uploadError.message, uploadError.stack);
        throw uploadError;
      }

      if (result.success) {
        console.log('✅ File upload completed');
        
        // Show success feedback to user
        this.showUploadSuccess(file.name);
        
        // Get selected intent from UI store
        const selectedIntent = this.stores.ui.getState().selectedIntent;
        
        // Start video processing with proper format for async job service
        const videoInput = {
          filePath: result.filePath,  // This is the file:// path from upload
          path: result.filePath,      // Alternative field name
          url: result.filePath,       // Alternative field name
          metadata: result.metadata,
          source: 'file_upload'
        };
        
        console.log('🎬 Created videoInput object:', videoInput);
        console.log('📁 Upload result was:', result);
        this.stores.startVideoUpload(videoInput, 'file');
        
        // Navigate to processing step after short delay
        setTimeout(() => {
          this.stores.ui.navigateToStep('processing');
        }, 1500);
        
      } else {
        throw new Error(result.error || 'Upload failed');
      }

    } catch (error) {
      console.error('❌ Upload error:', error);
      
      // Fallback: try to proceed with File object directly (legacy mode)
      console.log('🔄 Upload failed, trying fallback with File object...');
      
      try {
        // Create fallback videoInput with File object
        const fallbackVideoInput = {
          filePath: `file:///${file.name}`, // Fake file path for testing
          path: `file:///${file.name}`,
          url: `file:///${file.name}`,
          metadata: { originalName: file.name, size: file.size },
          source: 'file_upload_fallback',
          file: file // Keep original file reference
        };
        
        console.log('🎬 Created fallback videoInput:', fallbackVideoInput);
        this.stores.startVideoUpload(fallbackVideoInput, 'file');
        
        // Navigate to processing
        setTimeout(() => {
          this.stores.ui.navigateToStep('processing');
        }, 1500);
        
      } catch (fallbackError) {
        console.error('❌ Even fallback failed:', fallbackError);
        this.stores.video.setProcessingError(error.message);
        this.isUploading = false;
        this.updateUploadState(false);
      }
    }
  }

  async handleUrlUpload() {
    const urlInput = this.container.querySelector('#urlInput');
    const url = urlInput?.value?.trim();
    
    if (!url) {
      this.stores.ui.showError('Voer een geldige URL in');
      return;
    }

    console.log('🔄 Starting URL upload:', url);

    try {
      // Validate URL
      const validation = this.validator.validateUrl(url);
      if (!validation.valid) {
        this.stores.ui.showError(validation.error);
        return;
      }

      this.isUploading = true;
      this.updateUploadState(true);

      // Set URL in store
      this.stores.video.setCurrentVideo(url, {
        source: 'url',
        originalUrl: url
      });

      // Start URL processing
      const result = await this.uploadService.processUrl(url, (progress) => {
        this.stores.video.setUploadProgress(progress);
      });

      if (result.success) {
        console.log('✅ URL processing completed');
        
        // Show user confirmation
        this.stores.ui.showSuccess('✅ Video gedownload! Processing start nu...');
        
        // Brief pause to show confirmation
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Start video processing with original URL, not local path
        this.stores.startVideoUpload(url, 'url');
        
        // Clear input
        urlInput.value = '';
        
      } else {
        throw new Error(result.error || 'URL processing failed');
      }

    } catch (error) {
      console.error('❌ URL upload error:', error);
      this.stores.video.setProcessingError(error.message);
      this.isUploading = false;
      this.updateUploadState(false);
    }
  }

  updateDragVisuals(isDragOver) {
    const uploadZone = this.container.querySelector('#uploadZone');
    if (uploadZone) {
      if (isDragOver) {
        uploadZone.classList.add('drag-over');
      } else {
        uploadZone.classList.remove('drag-over');
      }
    }
  }

  updateUploadState(isUploading) {
    const uploadZone = this.container.querySelector('#uploadZone');
    const uploadTitle = this.container.querySelector('.upload-title');
    
    if (uploadZone) {
      if (isUploading) {
        uploadZone.classList.add('uploading');
        uploadZone.style.pointerEvents = 'none';
      } else {
        uploadZone.classList.remove('uploading');
        uploadZone.style.pointerEvents = 'auto';
      }
    }

    if (uploadTitle && isUploading) {
      uploadTitle.textContent = 'Uploaden...'; // Simple text without percentage
    }
  }

  updateUploadProgress(progress) {
    // Update progress visual feedback
    const uploadZone = this.container.querySelector('#uploadZone');
    if (uploadZone) {
      const progressBar = uploadZone.querySelector('.upload-progress');
      if (!progressBar) {
        const bar = document.createElement('div');
        bar.className = 'upload-progress';
        bar.innerHTML = `
          <div class="progress-bar">
            <div class="progress-fill" style="width: 0%"></div>
          </div>
        `;
        uploadZone.appendChild(bar);
      }
      
      const progressFill = uploadZone.querySelector('.progress-fill');
      const progressText = uploadZone.querySelector('.progress-text');
      
      if (progressFill) progressFill.style.width = progress + '%';
      // Removed percentage text overlay - progress shown in progress bar only
    }
  }

  updateDragState(dragActive) {
    this.updateDragVisuals(dragActive);
  }

  handleUploadError(error) {
    console.error('Upload error feedback:', error);
    this.isUploading = false;
    this.updateUploadState(false);
    
    // Remove progress indicators
    const progressBar = this.container.querySelector('.upload-progress');
    if (progressBar) {
      progressBar.remove();
    }
    
    // Show visible error feedback to user
    this.showUserFeedback('error', i18n.t('upload.validation.upload_failed') + ': ' + error, 5000);
    
    // Update upload zone with error state
    this.updateUploadZoneWithError(error);
  }

  // Public methods for external control
  reset() {
    this.isUploading = false;
    this.isDragActive = false;
    this.updateUploadState(false);
    this.updateDragVisuals(false);
    
    // Clear file input
    const fileInput = this.container.querySelector('#fileInput');
    if (fileInput) fileInput.value = '';
    
    // Clear URL input
    const urlInput = this.container.querySelector('#urlInput');
    if (urlInput) urlInput.value = '';
    
    // Remove progress indicators
    const progressBar = this.container.querySelector('.upload-progress');
    if (progressBar) progressBar.remove();
  }

  showUserFeedback(type, message, duration = 3000) {
    // Create or update feedback element
    let feedbackElement = this.container.querySelector('.upload-feedback');
    if (!feedbackElement) {
      feedbackElement = document.createElement('div');
      feedbackElement.className = 'upload-feedback';
      
      // Insert after upload zone
      const uploadZone = this.container.querySelector('#uploadZone');
      if (uploadZone) {
        uploadZone.parentNode.insertBefore(feedbackElement, uploadZone.nextSibling);
      }
    }
    
    // Set feedback content and style
    feedbackElement.className = `upload-feedback ${type}`;
    feedbackElement.innerHTML = `
      <div class="feedback-content">
        <span class="feedback-icon">
          ${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}
        </span>
        <span class="feedback-message">${message}</span>
      </div>
    `;
    
    // Add CSS styles
    this.addFeedbackStyles();
    
    // Show feedback
    feedbackElement.style.display = 'block';
    setTimeout(() => feedbackElement.classList.add('show'), 10);
    
    // Auto-hide after duration
    if (duration > 0) {
      setTimeout(() => {
        feedbackElement.classList.remove('show');
        setTimeout(() => {
          if (feedbackElement.parentNode) {
            feedbackElement.parentNode.removeChild(feedbackElement);
          }
        }, 300);
      }, duration);
    }
  }
  
  addFeedbackStyles() {
    // Add CSS if not already added
    if (document.querySelector('#upload-feedback-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'upload-feedback-styles';
    style.textContent = `
      .upload-feedback {
        margin: 15px 0;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid;
        display: none;
        opacity: 0;
        transform: translateY(-10px);
        transition: all 0.3s ease;
      }
      
      .upload-feedback.show {
        opacity: 1;
        transform: translateY(0);
      }
      
      .upload-feedback.success {
        background: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
      }
      
      .upload-feedback.error {
        background: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
      }
      
      .upload-feedback.info {
        background: #d1ecf1;
        border-color: #bee5eb;
        color: #0c5460;
      }
      
      .feedback-content {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      
      .feedback-icon {
        font-size: 16px;
      }
      
      .feedback-message {
        flex: 1;
        font-weight: 500;
      }
      
      /* Upload zone states */
      .upload-zone.upload-error {
        border-color: #dc3545 !important;
        background: #fff5f5;
      }
      
      .upload-zone.upload-success {
        border-color: #28a745 !important;
        background: #f8fff8;
      }
      
      .upload-zone.upload-error .upload-title,
      .upload-zone.upload-success .upload-title {
        color: inherit;
      }
    `;
    document.head.appendChild(style);
  }
  
  updateUploadZoneWithError(error) {
    const uploadZone = this.container.querySelector('#uploadZone');
    if (!uploadZone) return;
    
    // Add error state styling
    uploadZone.classList.add('upload-error');
    
    // Update upload title with error
    const uploadTitle = uploadZone.querySelector('.upload-title');
    if (uploadTitle) {
      uploadTitle.textContent = i18n.t('upload.feedback.upload_failed');
    }
    
    const uploadSubtitle = uploadZone.querySelector('.upload-subtitle');
    if (uploadSubtitle) {
      uploadSubtitle.textContent = i18n.t('upload.feedback.upload_retry');
    }
    
    // Reset after 3 seconds
    setTimeout(() => {
      uploadZone.classList.remove('upload-error');
      if (uploadTitle) uploadTitle.textContent = i18n.t('upload.drop_zone');
      if (uploadSubtitle) uploadSubtitle.textContent = i18n.t('upload.click_to_select');
    }, 3000);
  }
  
  updateUploadProgressFeedback(progress) {
    const feedbackElement = this.container.querySelector('.upload-feedback');
    if (feedbackElement) {
      const message = feedbackElement.querySelector('.feedback-message');
      if (message) {
        message.textContent = i18n.t('upload.progress.uploading', { progress: Math.round(progress) });
      }
    }
  }

  showUploadSuccess(fileName) {
    this.showUserFeedback('success', i18n.t('upload.feedback.upload_success', { fileName }), 2000);
    
    // Update upload zone with success state
    const uploadZone = this.container.querySelector('#uploadZone');
    if (uploadZone) {
      uploadZone.classList.add('upload-success');
      
      const uploadTitle = uploadZone.querySelector('.upload-title');
      if (uploadTitle) {
        uploadTitle.textContent = '✅ ' + i18n.t('common.success');
      }
    }
  }

  resetUploadZone() {
    console.log('🔄 Resetting upload zone to default state');
    
    // Reset component state
    this.isUploading = false;
    this.isDragActive = false;
    
    // Reset upload zone visual state
    const uploadZone = this.container.querySelector('#uploadZone');
    if (uploadZone) {
      uploadZone.classList.remove('upload-success', 'upload-error', 'uploading');
      
      // Reset title and subtitle
      const uploadTitle = uploadZone.querySelector('.upload-title');
      const uploadSubtitle = uploadZone.querySelector('.upload-subtitle');
      
      if (uploadTitle) {
        uploadTitle.textContent = i18n.t('upload.drop_zone');
      }
      if (uploadSubtitle) {
        uploadSubtitle.textContent = i18n.t('upload.click_to_select');
      }
    }
    
    // Clear file input
    const fileInput = this.container.querySelector('#fileInput');
    if (fileInput) {
      fileInput.value = '';
    }
    
    // Clear URL input
    const urlInput = this.container.querySelector('#urlInput');
    if (urlInput) {
      urlInput.value = '';
    }
    
    // Re-setup event listeners to ensure they work
    console.log('🔄 Re-setting up event listeners after reset');
    this.eventListenersAttached = false; // Force re-setup
    setTimeout(() => {
      this.setupEventListeners();
      // Debug status after reset
      this.debugStatus();
    }, 100); // Small delay to ensure DOM is ready
    
    // Remove any upload feedback
    const feedbackElements = this.container.querySelectorAll('.upload-feedback');
    feedbackElements.forEach(element => {
      if (element.parentNode) {
        element.parentNode.removeChild(element);
      }
    });
    
    // Reset stores state
    this.stores.ui.setUploadZoneActive(false);
    this.stores.ui.setDragOverActive(false);
    this.stores.video.setState({
      uploadProgress: 0,
      uploadError: null,
      currentVideo: null,
      videoMetadata: null
    });
  }
  
  debugStatus() {
    console.log('🔍 UploadZone Debug Status:');
    console.log('- isUploading:', this.isUploading);
    console.log('- isDragActive:', this.isDragActive);
    console.log('- uploadZoneElement exists:', !!this.uploadZoneElement);
    console.log('- fileInputElement exists:', !!this.fileInputElement);
    console.log('- uploadZoneClickHandler exists:', !!this.uploadZoneClickHandler);
    
    const uploadZone = this.container.querySelector('#uploadZone');
    const fileInput = this.container.querySelector('#fileInput');
    console.log('- uploadZone found in DOM:', !!uploadZone);
    console.log('- fileInput found in DOM:', !!fileInput);
    console.log('- uploadZone classes:', uploadZone?.className);
    console.log('- uploadZone style.display:', uploadZone?.style.display);
    console.log('- uploadZone style.pointerEvents:', uploadZone?.style.pointerEvents);
    console.log('- container element:', this.container);
    
    if (uploadZone) {
      const rect = uploadZone.getBoundingClientRect();
      console.log('- uploadZone position:', { x: rect.x, y: rect.y, width: rect.width, height: rect.height });
      console.log('- uploadZone is visible:', rect.width > 0 && rect.height > 0);
    }
  }
  
  forceTestClick() {
    console.log('🧪 Force testing upload zone click');
    const uploadZone = this.container.querySelector('#uploadZone');
    const fileInput = this.container.querySelector('#fileInput');
    
    if (uploadZone && fileInput) {
      console.log('🧪 Elements found, forcing file input click');
      fileInput.click();
    } else {
      console.log('🧪 Elements not found - uploadZone:', !!uploadZone, 'fileInput:', !!fileInput);
    }
  }
  
  runFullDiagnostic() {
    console.log('🩺 === UPLOAD ZONE FULL DIAGNOSTIC ===');
    console.log('🩺 Component state:');
    console.log('  - isUploading:', this.isUploading);
    console.log('  - isDragActive:', this.isDragActive);
    console.log('  - eventListenersAttached:', this.eventListenersAttached);
    
    console.log('🩺 DOM elements:');
    const uploadZone = document.querySelector('#uploadZone');
    const fileInput = document.querySelector('#fileInput');
    console.log('  - uploadZone exists:', !!uploadZone);
    console.log('  - fileInput exists:', !!fileInput);
    
    if (uploadZone) {
      console.log('  - uploadZone classes:', uploadZone.className);
      console.log('  - uploadZone visible:', uploadZone.offsetWidth > 0 && uploadZone.offsetHeight > 0);
      console.log('  - uploadZone pointer-events:', getComputedStyle(uploadZone).pointerEvents);
    }
    
    if (fileInput) {
      console.log('  - fileInput hidden attr:', fileInput.hasAttribute('hidden'));
      console.log('  - fileInput display:', getComputedStyle(fileInput).display);
    }
    
    console.log('🩺 Event listeners:');
    console.log('  - stored uploadZoneElement:', !!this.uploadZoneElement);
    console.log('  - stored fileInputElement:', !!this.fileInputElement);
    console.log('  - stored clickHandler:', !!this.uploadZoneClickHandler);
    
    // REMOVED: Automatic file input click - should only happen on user interaction
    // console.log('🩺 Testing direct file input click...');
    // if (fileInput) {
    //   try {
    //     fileInput.click();
    //     console.log('✅ Direct file input click succeeded');
    //   } catch (e) {
    //     console.log('❌ Direct file input click failed:', e);
    //   }
    // }
    
    console.log('🩺 === END DIAGNOSTIC ===');
  }
  
  forceFixUpload() {
    console.log('🔧 === FORCE FIXING UPLOAD ===');
    
    // 1. Complete reset
    this.isUploading = false;
    this.isDragActive = false;
    this.eventListenersAttached = false;
    
    // 2. Force remove all listeners
    this.removeEventListeners();
    
    // 3. Wait and re-setup
    setTimeout(() => {
      console.log('🔧 Re-setting up after force fix...');
      this.setupEventListeners();
      this.debugStatus();
      
      // REMOVED: Automatic test click - should only happen on user interaction
      // setTimeout(() => {
      //   console.log('🔧 Testing after force fix...');
      //   this.forceTestClick();
      // }, 100);
    }, 200);
    
    console.log('🔧 === FORCE FIX COMPLETE ===');
  }
  
  prepareForNewSession() {
    console.log('🚀 Preparing for new session after processing completion');
    
    // Mark for deep reset
    this.needsDeepReset = true;
    
    // Clear any lingering state
    this.isUploading = false;
    this.isDragActive = false;
    
    // Clear stores state
    this.stores.ui.setUploadZoneActive(false);
    this.stores.ui.setDragOverActive(false);
  }
  
  forceCompleteReset() {
    console.log('🔄 === FORCE COMPLETE RESET AFTER PROCESSING ===');
    
    // 1. Nuclear reset of all state
    this.isUploading = false;
    this.isDragActive = false;
    this.eventListenersAttached = false;
    this.needsDeepReset = false;
    
    // 2. Clear all DOM state
    const uploadZone = document.querySelector('#uploadZone');
    const fileInput = document.querySelector('#fileInput');
    const uploadStepContainer = document.querySelector('#stepUpload, .step-upload');
    
    // Force fix step container visibility first
    if (uploadStepContainer) {
      console.log('🔧 Ensuring upload step container is visible');
      uploadStepContainer.classList.remove('hidden');
      uploadStepContainer.classList.add('active');
      uploadStepContainer.style.display = '';
    }
    
    if (uploadZone) {
      uploadZone.classList.remove('upload-success', 'upload-error', 'uploading', 'drag-over', 'hidden');
      uploadZone.style.pointerEvents = 'auto';
      uploadZone.style.display = '';
      uploadZone.style.visibility = '';
      uploadZone.style.opacity = '';
    }
    
    if (fileInput) {
      fileInput.value = '';
      fileInput.disabled = false;
    }
    
    // 3. Force remove and re-add event listeners
    this.removeEventListeners();
    
    // 4. Reset stores to clean state
    this.stores.video.setState({
      uploadProgress: 0,
      uploadError: null,
      currentVideo: null,
      videoMetadata: null,
      isProcessing: false,
      processingProgress: 0,
      clips: [],
      processingResults: null
    });
    
    // 5. Re-setup everything fresh
    setTimeout(() => {
      console.log('🔄 Re-setting up everything fresh...');
      this.setupEventListeners();
      
      // Double-check visibility after setup
      setTimeout(() => {
        console.log('🧪 Testing reset result...');
        
        // Force visibility check one more time
        if (uploadStepContainer && uploadStepContainer.classList.contains('hidden')) {
          console.log('🚨 Step container still hidden after reset, force fixing...');
          uploadStepContainer.classList.remove('hidden');
          uploadStepContainer.classList.add('active');
        }
        
        this.debugStatus();
        
        // Run auto-check to verify everything is working
        setTimeout(() => {
          this.autoCheck();
        }, 50);
      }, 100);
    }, 150);
    
    console.log('🔄 === COMPLETE RESET FINISHED ===');
  }
  
  setupMobileTouchInteractions(uploadZone, fileInput) {
    // Mobile-specific touch interactions
    this.isMobileDevice = /Mobi|Android/i.test(navigator.userAgent) || window.innerWidth <= 768;
    
    if (!this.isMobileDevice) {
      return; // Skip mobile interactions on desktop
    }

    console.log('📱 Setting up mobile touch interactions');

    // Touch state tracking
    this.touchState = {
      startX: 0,
      startY: 0,
      startTime: 0,
      moved: false,
      tapHold: false
    };

    // Touch start handler
    this.touchStartHandler = (e) => {
      if (this.isUploading) return;
      
      const touch = e.touches[0];
      this.touchState = {
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: Date.now(),
        moved: false,
        tapHold: false
      };

      // Add visual feedback for touch
      uploadZone.classList.add('touch-active');
      
      // Start tap-hold timer (for alternative upload trigger)
      this.tapHoldTimer = setTimeout(() => {
        if (!this.touchState.moved) {
          this.touchState.tapHold = true;
          this.triggerHapticFeedback();
          uploadZone.classList.add('tap-hold-active');
        }
      }, 800);
    };

    // Touch move handler
    this.touchMoveHandler = (e) => {
      if (this.isUploading) return;
      
      const touch = e.touches[0];
      const deltaX = Math.abs(touch.clientX - this.touchState.startX);
      const deltaY = Math.abs(touch.clientY - this.touchState.startY);
      
      // If moved more than 10px, it's not a tap
      if (deltaX > 10 || deltaY > 10) {
        this.touchState.moved = true;
        uploadZone.classList.remove('touch-active', 'tap-hold-active');
        
        if (this.tapHoldTimer) {
          clearTimeout(this.tapHoldTimer);
          this.tapHoldTimer = null;
        }
      }
    };

    // Touch end handler
    this.touchEndHandler = (e) => {
      if (this.isUploading) return;
      
      e.preventDefault();
      
      const touchDuration = Date.now() - this.touchState.startTime;
      
      // Clear tap-hold timer
      if (this.tapHoldTimer) {
        clearTimeout(this.tapHoldTimer);
        this.tapHoldTimer = null;
      }

      // Remove visual feedback
      uploadZone.classList.remove('touch-active', 'tap-hold-active');

      // Handle different touch patterns
      if (!this.touchState.moved && touchDuration < 500) {
        // Quick tap - trigger file selection
        console.log('📱 Quick tap detected - opening file picker');
        this.triggerHapticFeedback('light');
        setTimeout(() => fileInput.click(), 100);
      } else if (this.touchState.tapHold) {
        // Tap-hold - trigger file selection with feedback
        console.log('📱 Tap-hold detected - opening file picker');
        this.triggerHapticFeedback('medium');
        setTimeout(() => fileInput.click(), 100);
      }
    };

    // Touch cancel handler
    this.touchCancelHandler = (e) => {
      uploadZone.classList.remove('touch-active', 'tap-hold-active');
      if (this.tapHoldTimer) {
        clearTimeout(this.tapHoldTimer);
        this.tapHoldTimer = null;
      }
    };

    // Add touch event listeners
    uploadZone.addEventListener('touchstart', this.touchStartHandler, { passive: false });
    uploadZone.addEventListener('touchmove', this.touchMoveHandler, { passive: false });
    uploadZone.addEventListener('touchend', this.touchEndHandler, { passive: false });
    uploadZone.addEventListener('touchcancel', this.touchCancelHandler, { passive: false });

    // Store handlers for cleanup
    this.mobileHandlers = {
      touchStart: this.touchStartHandler,
      touchMove: this.touchMoveHandler,
      touchEnd: this.touchEndHandler,
      touchCancel: this.touchCancelHandler
    };

    // Add mobile-specific CSS classes
    uploadZone.classList.add('mobile-touch-enabled');
    this.addMobileTouchStyles();
  }

  addMobileTouchStyles() {
    // Add mobile-specific styles if not already added
    if (document.querySelector('#mobile-upload-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'mobile-upload-styles';
    style.textContent = `
      .mobile-touch-enabled {
        user-select: none;
        -webkit-touch-callout: none;
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
      }
      
      .mobile-touch-enabled.touch-active {
        transform: scale(0.98);
        transition: transform 0.1s ease-out;
        background-color: rgba(59, 130, 246, 0.05);
      }
      
      .mobile-touch-enabled.tap-hold-active {
        background-color: rgba(59, 130, 246, 0.1);
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
      }
      
      @media (max-width: 768px) {
        .upload-zone {
          min-height: 200px;
          padding: 24px 16px;
        }
        
        .upload-title {
          font-size: 1.2rem;
        }
        
        .upload-subtitle {
          font-size: 0.9rem;
        }
      }
    `;
    document.head.appendChild(style);
  }

  triggerHapticFeedback(intensity = 'light') {
    // Trigger haptic feedback on mobile devices that support it
    if ('vibrate' in navigator) {
      const patterns = {
        light: [10],
        medium: [20],
        heavy: [50]
      };
      navigator.vibrate(patterns[intensity] || patterns.light);
    }
  }

  removeEventListeners() {
    console.log('🧹 Removing event listeners');
    
    // Remove click listeners from upload zone
    if (this.uploadZoneElement && this.uploadZoneClickHandler) {
      this.uploadZoneElement.removeEventListener('click', this.uploadZoneClickHandler);
      console.log('🧹 Removed click listener from upload zone');
    }
    
    // Remove change listener from file input
    if (this.fileInputElement && this.fileInputChangeHandler) {
      this.fileInputElement.removeEventListener('change', this.fileInputChangeHandler);
      console.log('🧹 Removed change listener from file input');
    }
    
    // Remove drag listeners
    if (this.uploadZoneElement) {
      if (this.dragOverHandler) {
        this.uploadZoneElement.removeEventListener('dragover', this.dragOverHandler);
        console.log('🧹 Removed dragover listener');
      }
      if (this.dragLeaveHandler) {
        this.uploadZoneElement.removeEventListener('dragleave', this.dragLeaveHandler);
        console.log('🧹 Removed dragleave listener');
      }
      if (this.dropHandler) {
        this.uploadZoneElement.removeEventListener('drop', this.dropHandler);
        console.log('🧹 Removed drop listener');
      }
      
      // Remove mobile touch listeners
      if (this.mobileHandlers && this.isMobileDevice) {
        this.uploadZoneElement.removeEventListener('touchstart', this.mobileHandlers.touchStart);
        this.uploadZoneElement.removeEventListener('touchmove', this.mobileHandlers.touchMove);
        this.uploadZoneElement.removeEventListener('touchend', this.mobileHandlers.touchEnd);
        this.uploadZoneElement.removeEventListener('touchcancel', this.mobileHandlers.touchCancel);
        console.log('🧹 Removed mobile touch listeners');
      }
    }
    
    // Clear mobile handlers
    this.mobileHandlers = null;
    this.touchState = null;
    
    // Clear tap-hold timer
    if (this.tapHoldTimer) {
      clearTimeout(this.tapHoldTimer);
      this.tapHoldTimer = null;
    }
    
    // Clear references
    this.uploadZoneElement = null;
    this.fileInputElement = null;
    this.uploadZoneClickHandler = null;
    this.fileInputChangeHandler = null;
    this.dragOverHandler = null;
    this.dragLeaveHandler = null;
    this.dropHandler = null;
    this.eventListenersAttached = false;
  }

  destroy() {
    this.removeEventListeners();
    
    // Clear auto-check interval
    if (this.autoCheckInterval) {
      clearInterval(this.autoCheckInterval);
    }
    
    console.log('🧹 UploadZone component destroyed');
  }
}

export default UploadZone;