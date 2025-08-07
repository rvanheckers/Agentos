/**
 * Results Grid Component
 * Replaces dashboard.js results logic (lines 2000-2800)
 * Clean component-based results display with video player integration
 */

import { storeManager } from '../../../infrastructure/state/store-manager.js';
import { DownloadManager } from '../services/download-manager.js';
import { PathResolver, Environment } from '../../../infrastructure/config/environment.js';
import i18n from '../../../i18n/utils/i18n.js';

export class ResultsGrid {
  constructor(container, dependencies = {}) {
    this.container = container;
    this.stores = dependencies.stores || storeManager;
    this.apiClient = dependencies.apiClient;
    this.downloadManager = new DownloadManager(this.apiClient);
    
    this.currentResults = null;
    this.selectedClips = new Set();
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupStoreListeners();
    console.log('✅ ResultsGrid component initialized');
  }

  setupEventListeners() {
    // Note: Download all clips button is set up in setupClipEventListeners() 
    // when results are actually visible, not here in initial setup

    // Create new clips button  
    const createNewBtn = document.getElementById('createNewClips');
    if (createNewBtn) {
      createNewBtn.addEventListener('click', () => this.createNewClips());
    }
  }

  setupStoreListeners() {
    // Listen to video store changes for results display
    this.stores.video.addListener((newState, prevState) => {
      if (newState.processingResults && !prevState.processingResults) {
        this.displayResults(newState.processingResults);
      }
      
      if (newState.processingResults !== prevState.processingResults) {
        this.currentResults = newState.processingResults;
      }
    });

    // Listen to UI state changes
    this.stores.ui.addListener((newState, prevState) => {
      if (newState.currentStep === 'results' && prevState.currentStep !== 'results') {
        this.onResultsStepActivated();
      }
      
      // Re-render results when language changes
      if (newState.language !== prevState.language && this.currentResults) {
        console.log('🌐 Language changed, re-rendering results');
        this.displayResults(this.currentResults);
      }
    });
  }

  displayResults(results) {
    console.log('🎬 RESULTS GRID - displayResults called with:', results);
    console.log('📊 RESULTS GRID - DETAILED ANALYSIS:');
    console.log('  - results type:', typeof results);
    console.log('  - results keys:', results ? Object.keys(results) : 'no results');
    console.log('  - results.clips:', results?.clips);
    console.log('  - results.output_files:', results?.output_files);
    console.log('  - results.clips?.length:', results?.clips?.length);
    console.log('  - results.output_files?.length:', results?.output_files?.length);
    
    const resultsContent = document.getElementById('resultsContent');
    const clipCount = document.getElementById('clipCount');
    
    if (!resultsContent) {
      console.error('🚨 CRITICAL: resultsContent element not found!');
      return;
    }
    
    // Check for clips in different formats
    let clipsToDisplay = null;
    let clipCountValue = 0;
    
    if (results?.clips && Array.isArray(results.clips) && results.clips.length > 0) {
      console.log('✅ Found clips in results.clips array');
      clipsToDisplay = results.clips;
      clipCountValue = results.clips.length;
    } else if (results?.output_files && Array.isArray(results.output_files) && results.output_files.length > 0) {
      console.log('✅ Found clips in results.output_files array');
      clipsToDisplay = results.output_files;
      clipCountValue = results.output_files.length;
    } else if (results?.clips?.output_videos && Array.isArray(results.clips.output_videos) && results.clips.output_videos.length > 0) {
      console.log('✅ Found clips in results.clips.output_videos array');
      clipsToDisplay = results.clips.output_videos;
      clipCountValue = results.clips.output_videos.length;
    } else if (results?.clips?.data?.output_videos && Array.isArray(results.clips.data.output_videos) && results.clips.data.output_videos.length > 0) {
      console.log('✅ Found clips in results.clips.data.output_videos array');
      clipsToDisplay = results.clips.data.output_videos;
      clipCountValue = results.clips.data.output_videos.length;
    } else if (results?.clips && typeof results.clips === 'object' && results.clips.data?.output_videos) {
      console.log('✅ Found clips in nested clips.data.output_videos');
      clipsToDisplay = results.clips.data.output_videos;
      clipCountValue = results.clips.data.output_videos.length;
    } else {
      console.log('⚠️ NO CLIPS FOUND IN ANY EXPECTED LOCATION:');
      console.log('  - results.clips:', results?.clips);
      console.log('  - results.clips type:', typeof results?.clips);
      console.log('  - results.output_files:', results?.output_files);
      console.log('  - results.clips?.output_videos:', results?.clips?.output_videos);
      console.log('  - results.clips?.data:', results?.clips?.data);
      console.log('  - Will show no results message');
    }

    console.log(`🎬 Displaying ${clipCountValue} clips from:`, clipsToDisplay);

    // Update clip count
    if (clipCount) {
      clipCount.textContent = clipCountValue;
    }
    this.currentResults = results;

    // Handle no results case
    if (!clipsToDisplay || clipCountValue === 0) {
      console.log('📭 No clips to display - showing no results message');
      this.displayNoResults();
      return;
    }

    // Generate results grid HTML
    console.log('🏗️ Generating HTML for clips...');
    const resultsHTML = this.generateResultsHTML(clipsToDisplay);
    console.log('📝 Generated HTML length:', resultsHTML.length);
    resultsContent.innerHTML = resultsHTML;

    // Setup individual clip event listeners
    this.setupClipEventListeners();
    
    // Trigger animations
    this.animateResultsIn();
    
    console.log('✅ Results display completed successfully');
  }

  generateResultsHTML(results) {
    console.log('🏗️ GENERATE RESULTS HTML - Input:', results);
    console.log('📋 Input type:', typeof results);
    console.log('📋 Is array:', Array.isArray(results));
    
    // Handle different result formats
    let clips = [];
    
    if (Array.isArray(results)) {
      console.log('✅ Processing as direct array');
      clips = results.map((clip, index) => {
        console.log(`📄 Processing clip ${index}:`, clip);
        
        // For video streaming, prefer direct file path over download endpoint
        clip.streamUrl = clip.file_path;
        clip.downloadUrl = clip.download_url;
        
        // Convert file path to streaming URL if needed
        if (clip.streamUrl && !clip.streamUrl.startsWith('http')) {
          clip.streamUrl = PathResolver.getMediaUrlForDisplay(clip.streamUrl);
        }
        
        // For download, use the download endpoint
        if (clip.downloadUrl && !clip.downloadUrl.startsWith('http')) {
          clip.downloadUrl = `${Environment.API.BASE_URL}${clip.downloadUrl}`;
        }
        
        // Use stream URL for video player, download URL for download button
        clip.url = clip.streamUrl || clip.downloadUrl;
        
        console.log(`🎯 URL mapping: stream="${clip.streamUrl}", download="${clip.downloadUrl}", final="${clip.url}"`);
        
        console.log(`✅ Final clip URL: ${clip.url}`);
        console.log(`🔽 Download URL will be: ${clip.streamUrl || clip.url}`);
        return clip;
      });
    } else if (results && results.clips && Array.isArray(results.clips)) {
      console.log('✅ Processing results.clips array');
      clips = results.clips.map((clip, index) => {
        console.log(`📄 Processing clip ${index}:`, clip);
        
        // For video streaming, prefer direct file path over download endpoint
        clip.streamUrl = clip.file_path;
        clip.downloadUrl = clip.download_url;
        
        // Convert file path to streaming URL if needed
        if (clip.streamUrl && !clip.streamUrl.startsWith('http')) {
          clip.streamUrl = PathResolver.getMediaUrlForDisplay(clip.streamUrl);
        }
        
        // For download, use the download endpoint
        if (clip.downloadUrl && !clip.downloadUrl.startsWith('http')) {
          clip.downloadUrl = `${Environment.API.BASE_URL}${clip.downloadUrl}`;
        }
        
        // Use stream URL for video player, download URL for download button
        clip.url = clip.streamUrl || clip.downloadUrl;
        
        console.log(`🎯 URL mapping: stream="${clip.streamUrl}", download="${clip.downloadUrl}", final="${clip.url}"`);
        
        console.log(`✅ Final clip URL: ${clip.url}`);
        return clip;
      });
    } else if (results && (results.output_videos || results.output_files) && Array.isArray(results.output_videos || results.output_files)) {
      console.log('✅ Processing output_videos/output_files');
      // Convert output files/videos to clip format
      const outputData = results.output_videos || results.output_files;
      console.log('📋 Output data:', outputData);
      
      clips = outputData.map((file, index) => {
        console.log(`📄 Processing output file ${index}:`, file);
        
        // Use display_url if available, otherwise convert path to URL
        const displayUrl = file.display_url || PathResolver.getMediaUrlForDisplay(file.path || file);
        console.log(`🔗 Display URL: ${displayUrl}`);
        
        const processedClip = {
          url: displayUrl,
          path: file.path || file, // Keep server path for backend operations
          title: file.title || file.filename || `Clip ${index + 1}`,
          duration: file.duration || 'Unknown',
          description: file.description || `Generated clip (${file.file_size_mb || 'Unknown size'}MB)`,
          clipType: file.clipType || this.getClipTypeByIndex(index),
          presetInfo: this.getPresetInfoByType(file.clipType || this.getClipTypeByIndex(index))
        };
        
        console.log(`✅ Processed clip ${index}:`, processedClip);
        return processedClip;
      });
    } else {
      console.warn('⚠️ No valid clips found in results:', results);
      console.warn('⚠️ Results structure not recognized');
      clips = [];
    }
    
    console.log(`📊 Final clips array (${clips.length} items):`, clips);
    
    if (clips.length === 0) {
      console.log('📭 No clips found - returning no results HTML');
      return `<div class="no-results">${i18n.t('results.no_clips_found')}</div>`;
    }
    
    return clips.map((clip, index) => `
      <div class="result-clip ${!clip.isValid ? 'invalid-clip' : ''}" data-clip-index="${index}">
        <div class="clip-preview">
          ${clip.isValid !== false ? `
          <video preload="metadata" data-clip-url="${clip.url}" style="width: 100%; max-height: 200px; cursor: pointer;">
            <source src="${clip.url}" type="video/mp4">
            ${i18n.t('results.video_not_supported')}
          </video>` : `
          <div class="invalid-video-placeholder">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="currentColor">
              <path d="M24 4C12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20S35.05 4 24 4zm10 28.5l-2.5 2.5L24 27.5 16.5 35l-2.5-2.5L21.5 24 14 16.5l2.5-2.5L24 21.5l7.5-7.5 2.5 2.5L26.5 24l7.5 7.5z"/>
            </svg>
            <p>Invalid Video</p>
          </div>`}
          <div class="clip-overlay">
            ${clip.isValid !== false ? `
            <button class="clip-select-btn" data-clip-index="${index}">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            </button>` : `
            <div class="invalid-indicator">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 2a8 8 0 100 16 8 8 0 000-16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
              </svg>
            </div>`}
          </div>
        </div>
        
        <div class="clip-info">
          <div class="clip-header">
            <h3>${this.getClipTitle(clip, index)}</h3>
            <div class="clip-metadata">
              <span class="clip-score">${i18n.t('results.ai_score')}: ${this.formatScore(clip.aiScore)}</span>
              <span class="clip-duration">${this.formatDuration(clip.duration)}</span>
            </div>
          </div>
          
          <p class="clip-description">${clip.description || i18n.t('results.optimized_segment')}</p>
          
          ${clip.presetInfo ? `
          <div class="clip-preset-info">
            <span class="preset-icon">${clip.presetInfo.icon}</span>
            <span class="preset-tempo">${i18n.t('presets.tempo')}: ${clip.presetInfo.tempo}</span>
            <span class="preset-separator">|</span>
            <span class="preset-color">${clip.presetInfo.color}</span>
            <span class="preset-separator">|</span>
            <span class="preset-features">${clip.presetInfo.features.join(' • ')}</span>
          </div>
          ` : ''}
          
          <div class="clip-actions">
            <button class="btn-primary clip-download-btn" data-clip-url="${clip.streamUrl || clip.url}" data-clip-name="${clip.name || 'clip_' + (index + 1)}">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path fill-rule="evenodd" d="M8 1v8l2-2m-2 2L6 7m2 2v8m-4-4h8" clip-rule="evenodd"/>
              </svg>
              ${i18n.t('results.download_segment')}
            </button>
            
            <button class="btn-secondary video-play-btn" data-clip-index="${index}">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" class="play-icon">
                <path d="M8 2a6 6 0 100 12A6 6 0 008 2zM7 5v6l4-3-4-3z"/>
              </svg>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" class="pause-icon" style="display:none;">
                <path d="M8 2a6 6 0 100 12A6 6 0 008 2zM7 3h2v10H7V3zM9 3h2v10H9V3z"/>
              </svg>
              <span class="play-text">${i18n.t('results.play_video')}</span>
            </button>
            
            <button class="btn-secondary clip-share-btn" data-clip-url="${clip.url}">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 2a1 1 0 011 1v4l2-2m-2 2L7 5m2 2v6a1 1 0 01-2 0V8H5a1 1 0 010-2h2V3a1 1 0 011-1z"/>
              </svg>
              ${i18n.t('results.share_clip')}
            </button>
          </div>
        </div>
      </div>
    `).join('');
  }

  setupClipEventListeners() {
    const resultsContent = document.getElementById('resultsContent');
    if (!resultsContent) return;

    // Setup mobile interaction detection
    this.isMobileDevice = /Mobi|Android/i.test(navigator.userAgent) || window.innerWidth <= 768;

    // Setup "Download All" button - do this here when results are visible
    const downloadAllBtn = document.getElementById('downloadAllClips');
    console.log('🔍 Setting up Download All button:', downloadAllBtn);
    if (downloadAllBtn) {
      console.log('✅ Found downloadAllClips button in results, adding event listener');
      // Remove any existing listener first
      downloadAllBtn.replaceWith(downloadAllBtn.cloneNode(true));
      const newDownloadAllBtn = document.getElementById('downloadAllClips');
      
      newDownloadAllBtn.addEventListener('click', (e) => {
        e.preventDefault();
        console.log('🔽 Download All button clicked via results event listener');
        this.downloadAllClips();
      });
    } else {
      console.error('❌ downloadAllClips button not found in results!');
    }

    // Download individual clips
    resultsContent.querySelectorAll('.clip-download-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        console.log('🔽 Download button clicked:', e.currentTarget);
        
        let url = e.currentTarget.dataset.clipUrl;
        const name = e.currentTarget.dataset.clipName;
        
        // Fix URL by using PathResolver to convert to proper media URL
        if (url && !url.startsWith('http')) {
          url = PathResolver.getMediaUrlForDisplay(url);
        }
        
        console.log('🔽 Download URL:', url);
        console.log('🔽 Download Name:', name);
        
        if (!url) {
          console.error('❌ No download URL found!');
          this.stores.ui.showError('Download URL not available');
          return;
        }
        
        this.downloadClip(url, name);
      });
    });

    // Video play/pause button handler
    resultsContent.querySelectorAll('.video-play-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(btn.dataset.clipIndex);
        const video = resultsContent.querySelectorAll('video')[index];
        const playIcon = btn.querySelector('.play-icon');
        const pauseIcon = btn.querySelector('.pause-icon');
        const playText = btn.querySelector('.play-text');
        
        if (video) {
          if (video.paused) {
            video.play().then(() => {
              console.log(`▶️ Video ${index} started playing`);
              playIcon.style.display = 'none';
              pauseIcon.style.display = 'inline';
              playText.textContent = i18n.t('results.pause_video');
            }).catch(err => {
              console.error(`❌ Video ${index} play failed:`, err);
            });
          } else {
            video.pause();
            console.log(`⏸️ Video ${index} paused`);
            playIcon.style.display = 'inline';
            pauseIcon.style.display = 'none';
            playText.textContent = i18n.t('results.play_video');
          }
        }
      });
    });

    // Share clips
    resultsContent.querySelectorAll('.clip-share-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const url = e.currentTarget.dataset.clipUrl;
        this.shareClip(url);
      });
    });

    // Clip selection
    resultsContent.querySelectorAll('.clip-select-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.currentTarget.dataset.clipIndex);
        this.toggleClipSelection(index);
      });
    });

    // Setup mobile-specific interactions
    this.setupMobileVideoInteractions(resultsContent);

    // Setup TikTok/YouTube style video behavior
    this.setupTikTokStyleVideos(resultsContent);
  }

  displayNoResults() {
    const resultsContent = document.getElementById('resultsContent');
    if (!resultsContent) return;

    resultsContent.innerHTML = `
      <div class="no-results">
        <div class="no-results-icon">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="30" stroke="currentColor" stroke-width="2" opacity="0.3"/>
            <path d="M22 32h20M32 22v20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h3>${i18n.t('results.no_results')}</h3>
        <p>${i18n.t('results.no_results_description')}</p>
        <button class="btn-primary" onclick="window.vibeCoder.showStep('upload')">
          ${i18n.t('results.try_again')}
        </button>
      </div>
    `;
  }

  downloadClip(url, name = null) {
    console.log('🔽 Downloading clip:', url, 'with name:', name);
    
    if (!url) {
      console.error('❌ No URL provided for download');
      this.stores.ui.showError('Download URL is missing');
      return;
    }

    if (!this.downloadManager) {
      console.error('❌ Download manager not initialized');
      this.stores.ui.showError('Download system not available');
      return;
    }
    
    try {
      const filename = name || `clip_${Date.now()}.mp4`;
      console.log('🔽 Starting download with filename:', filename);
      
      this.downloadManager.downloadFile(url, filename)
        .then(() => {
          console.log('✅ Download completed successfully');
          this.stores.ui.showSuccess(i18n.t('results.download_started') || 'Download started');
        })
        .catch((error) => {
          console.error('❌ Download promise error:', error);
          this.stores.ui.showError(i18n.t('results.download_failed') || 'Download failed');
        });
      
    } catch (error) {
      console.error('❌ Download error:', error);
      this.stores.ui.showError(i18n.t('results.download_failed') || 'Download failed');
    }
  }

  downloadAllClips() {
    console.log('🔽 Download All Clips button clicked!');
    console.log('🔍 Current results:', this.currentResults);
    
    if (!this.currentResults?.clips?.length) {
      console.error('❌ No clips available for download');
      this.stores.ui.showError(i18n.t('results.no_clips_to_download') || 'No clips to download');
      return;
    }

    console.log('🔽 Downloading all clips:', this.currentResults.clips.length);
    console.log('🔽 Clip URLs:', this.currentResults.clips.map(c => c.url || c.downloadUrl));

    if (!this.downloadManager) {
      console.error('❌ Download manager not available');
      this.stores.ui.showError('Download system not available');
      return;
    }

    try {
      const downloads = this.currentResults.clips.map((clip, index) => {
        console.log(`🔍 Clip ${index + 1} data:`, clip);
        console.log(`🔍 Available URLs: streamUrl="${clip.streamUrl}", downloadUrl="${clip.downloadUrl}", url="${clip.url}", file_path="${clip.file_path}"`);
        
        // Try multiple URL sources
        let url = clip.streamUrl || clip.downloadUrl || clip.url || clip.file_path;
        const name = clip.name || clip.title || `clip_${index + 1}.mp4`;
        
        // Fix URL by using PathResolver to convert to proper media URL
        if (url && !url.startsWith('http')) {
          url = PathResolver.getMediaUrlForDisplay(url);
        }
        
        console.log(`🔽 Starting download ${index + 1}: URL="${url}", Name="${name}"`);
        
        if (!url) {
          console.error(`❌ No URL found for clip ${index + 1}:`, clip);
          throw new Error(`No download URL available for ${name}`);
        }
        
        return this.downloadManager.downloadFile(url, name);
      });

      Promise.all(downloads).then(() => {
        console.log('✅ All downloads completed successfully');
        this.stores.ui.showSuccess(i18n.t('results.all_downloads_started') || 'All downloads started');
      }).catch((error) => {
        console.error('❌ Batch download error:', error);
        this.stores.ui.showError(i18n.t('results.download_failed') || 'Download failed');
      });

    } catch (error) {
      console.error('❌ Download all error:', error);
      this.stores.ui.showError(i18n.t('results.download_failed') || 'Download failed');
    }
  }

  shareClip(url) {
    console.log('📤 Sharing clip:', url);
    
    if (navigator.share) {
      navigator.share({
        title: i18n.t('results.share_title'),
        text: i18n.t('results.share_text'),
        url: url
      }).catch(err => console.log('Share cancelled:', err));
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(url).then(() => {
        this.stores.ui.showSuccess(i18n.t('results.link_copied'));
      }).catch(() => {
        this.stores.ui.showError(i18n.t('results.share_failed'));
      });
    }
  }

  toggleClipSelection(index) {
    if (this.selectedClips.has(index)) {
      this.selectedClips.delete(index);
    } else {
      this.selectedClips.add(index);
    }
    
    this.updateSelectionUI();
  }

  updateSelectionUI() {
    const resultsContent = document.getElementById('resultsContent');
    if (!resultsContent) return;

    resultsContent.querySelectorAll('.result-clip').forEach((clip, index) => {
      const isSelected = this.selectedClips.has(index);
      const selectBtn = clip.querySelector('.clip-select-btn');
      
      clip.classList.toggle('selected', isSelected);
      selectBtn.classList.toggle('selected', isSelected);
    });

    // Update download all button to show selection count
    const downloadAllBtn = document.getElementById('downloadAllClips');
    if (downloadAllBtn && this.selectedClips.size > 0) {
      const spanElement = downloadAllBtn.querySelector('span');
      if (spanElement) {
        spanElement.textContent = 
          i18n.t('results.download_selected', { count: this.selectedClips.size });
      }
    } else if (downloadAllBtn) {
      const spanElement = downloadAllBtn.querySelector('span');
      if (spanElement) {
        spanElement.textContent = i18n.t('results.actions.download_all');
      }
    }
  }

  createNewClips() {
    console.log('🔄 Creating new clips - navigating to upload');
    
    // Reset state
    this.reset();
    
    // Navigate back to upload step
    this.stores.ui.navigateToStep('intent');
  }

  onResultsStepActivated() {
    console.log('📊 Results step activated');
    
    // Trigger any necessary updates when results step becomes active
    if (this.currentResults) {
      this.animateResultsIn();
    }
  }

  animateResultsIn() {
    const clips = document.querySelectorAll('.result-clip');
    clips.forEach((clip, index) => {
      clip.style.opacity = '0';
      clip.style.transform = 'translateY(20px)';
      
      setTimeout(() => {
        clip.style.transition = 'all 0.4s ease';
        clip.style.opacity = '1';
        clip.style.transform = 'translateY(0)';
      }, index * 100);
    });
  }

  handleVideoError(videoElement) {
    const clipPreview = videoElement.closest('.clip-preview');
    if (!clipPreview) return;

    const clipUrl = videoElement.dataset.clipUrl || videoElement.src;
    console.error('❌ Video playback failed for:', clipUrl);
    
    // Log additional debugging info
    console.error('Video element state:', {
      readyState: videoElement.readyState,
      networkState: videoElement.networkState,
      error: videoElement.error ? {
        code: videoElement.error.code,
        message: videoElement.error.message
      } : null
    });

    clipPreview.innerHTML = `
      <div class="video-error">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="currentColor">
          <path d="M24 4C12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20S35.05 4 24 4zm10 28.5l-2.5 2.5L24 27.5 16.5 35l-2.5-2.5L21.5 24 14 16.5l2.5-2.5L24 21.5l7.5-7.5 2.5 2.5L26.5 24l7.5 7.5z"/>
        </svg>
        <p>${i18n.t('results.video_error')}</p>
        <p class="error-details">URL: ${clipUrl}</p>
        <button class="btn-secondary retry-video-btn" onclick="this.parentElement.parentElement.querySelector('video')?.load()">
          ${i18n.t('results.retry_video') || 'Retry'}
        </button>
      </div>
    `;
  }

  formatScore(score) {
    if (score === null || score === undefined) return 'N/A';
    return typeof score === 'number' ? score.toFixed(1) : score;
  }

  formatDuration(duration) {
    if (!duration) return '';
    
    const minutes = Math.floor(duration / 60);
    const seconds = Math.floor(duration % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  getClipTypeByIndex(index) {
    const types = ['viral_moment', 'key_highlight', 'smart_summary'];
    return types[index % types.length];
  }

  getClipTitle(clip, index) {
    const titles = {
      'viral_moment': i18n.t('results.clips.viral_moment') || '🎬 Viral Moment',
      'key_highlight': i18n.t('results.clips.key_highlight') || '🎬 Key Highlight',
      'smart_summary': i18n.t('results.clips.smart_summary') || '🎬 Smart Summary'
    };
    
    return titles[clip.clipType] || clip.title || `${i18n.t('results.clip_title')} ${index + 1}`;
  }

  getPresetInfoByType(clipType) {
    const presets = {
      'viral_moment': {
        icon: '🎯',
        tempo: i18n.t('presets.tempo_high') || 'hoog',
        color: '🎨 ' + (i18n.t('presets.colors_bright') || 'Kleuren: fel'),
        features: [
          '📝 ' + (i18n.t('presets.auto_captions') || 'Captions: automatisch'),
          '✨ ' + (i18n.t('presets.hype_template') || 'Hype template')
        ]
      },
      'key_highlight': {
        icon: '🎯',
        tempo: i18n.t('presets.tempo_moderate') || 'gematigd',
        color: '🎨 ' + (i18n.t('presets.colors_natural') || 'Kleuren: natuurlijk'),
        features: [
          '🔤 ' + (i18n.t('presets.text_timestamps') || 'Tekst: timestamps'),
          '👤 ' + (i18n.t('presets.face_focus') || 'Face focus')
        ]
      },
      'smart_summary': {
        icon: '🎯',
        tempo: i18n.t('presets.tempo_calm') || 'rustig',
        color: '🎤 ' + (i18n.t('presets.voiceover_ai') || 'Voice-over: AI'),
        features: [
          '📚 ' + (i18n.t('presets.intro_outro') || 'Structuur: intro + slot'),
          '🤖 ' + (i18n.t('presets.ai_script') || 'AI-script')
        ]
      }
    };
    
    return presets[clipType] || null;
  }

  reset() {
    this.currentResults = null;
    this.selectedClips.clear();
    
    const resultsContent = document.getElementById('resultsContent');
    if (resultsContent) {
      resultsContent.innerHTML = '';
    }
    
    console.log('🧹 ResultsGrid reset');
  }

  setupMobileVideoInteractions(resultsContent) {
    if (!this.isMobileDevice) {
      return; // Skip mobile interactions on desktop
    }

    console.log('📱 Setting up mobile video interactions');

    // Add mobile-specific CSS styles
    this.addMobileResultsStyles();

    // Setup mobile video controls
    resultsContent.querySelectorAll('video').forEach((video, index) => {
      this.setupMobileVideoControls(video, index);
    });

    // Setup swipe gestures for result cards
    resultsContent.querySelectorAll('.result-clip').forEach((clip, index) => {
      this.setupMobileCardGestures(clip, index);
    });
  }

  setupMobileVideoControls(video, index) {
    // Touch state for video interactions
    let videoTouchState = {
      startX: 0,
      startY: 0,
      startTime: 0,
      moved: false,
      tapCount: 0,
      lastTap: 0
    };

    const touchStartHandler = (e) => {
      const touch = e.touches[0];
      const currentTime = Date.now();
      
      videoTouchState = {
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: currentTime,
        moved: false,
        tapCount: currentTime - videoTouchState.lastTap < 300 ? videoTouchState.tapCount + 1 : 1,
        lastTap: currentTime
      };

      // Visual feedback
      video.style.filter = 'brightness(0.9)';
    };

    const touchMoveHandler = (e) => {
      const touch = e.touches[0];
      const deltaX = Math.abs(touch.clientX - videoTouchState.startX);
      const deltaY = Math.abs(touch.clientY - videoTouchState.startY);
      
      if (deltaX > 10 || deltaY > 10) {
        videoTouchState.moved = true;
        video.style.filter = '';
      }
    };

    const touchEndHandler = (e) => {
      e.preventDefault();
      
      const touchDuration = Date.now() - videoTouchState.startTime;
      video.style.filter = '';

      if (!videoTouchState.moved && touchDuration < 500) {
        if (videoTouchState.tapCount === 1) {
          // Single tap - play/pause
          setTimeout(() => {
            if (videoTouchState.tapCount === 1) {
              this.handleVideoTap(video, index);
            }
          }, 300);
        } else if (videoTouchState.tapCount === 2) {
          // Double tap - fullscreen or toggle mute
          this.handleVideoDoubleTap(video, index);
        }
      }
    };

    // Add touch event listeners
    video.addEventListener('touchstart', touchStartHandler, { passive: false });
    video.addEventListener('touchmove', touchMoveHandler, { passive: false });
    video.addEventListener('touchend', touchEndHandler, { passive: false });

    // Store handlers for cleanup
    video._mobileHandlers = {
      touchStart: touchStartHandler,
      touchMove: touchMoveHandler,
      touchEnd: touchEndHandler
    };

    // Enable native video controls for mobile
    video.controls = true;
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
  }

  setupMobileCardGestures(clip, index) {
    let cardTouchState = {
      startX: 0,
      startY: 0,
      moved: false,
      direction: null
    };

    const touchStartHandler = (e) => {
      if (e.target.tagName === 'VIDEO' || e.target.tagName === 'BUTTON') {
        return; // Don't interfere with video or button interactions
      }

      const touch = e.touches[0];
      cardTouchState = {
        startX: touch.clientX,
        startY: touch.clientY,
        moved: false,
        direction: null
      };
    };

    const touchMoveHandler = (e) => {
      if (e.target.tagName === 'VIDEO' || e.target.tagName === 'BUTTON') {
        return;
      }

      const touch = e.touches[0];
      const deltaX = touch.clientX - cardTouchState.startX;
      const deltaY = touch.clientY - cardTouchState.startY;
      
      if (Math.abs(deltaX) > 50 || Math.abs(deltaY) > 50) {
        cardTouchState.moved = true;
        
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
          cardTouchState.direction = deltaX > 0 ? 'right' : 'left';
          
          // Visual swipe feedback
          const transform = `translateX(${deltaX * 0.3}px)`;
          clip.style.transform = transform;
          clip.style.opacity = Math.max(0.7, 1 - Math.abs(deltaX) / 200);
        }
      }
    };

    const touchEndHandler = (e) => {
      if (e.target.tagName === 'VIDEO' || e.target.tagName === 'BUTTON') {
        return;
      }

      // Reset visual state
      clip.style.transform = '';
      clip.style.opacity = '';

      if (cardTouchState.moved) {
        const deltaX = Math.abs(cardTouchState.startX - (e.changedTouches[0]?.clientX || cardTouchState.startX));
        
        if (deltaX > 100) {
          // Swipe action completed
          if (cardTouchState.direction === 'right') {
            this.handleCardSwipeRight(clip, index);
          } else if (cardTouchState.direction === 'left') {
            this.handleCardSwipeLeft(clip, index);
          }
        }
      }
    };

    clip.addEventListener('touchstart', touchStartHandler, { passive: false });
    clip.addEventListener('touchmove', touchMoveHandler, { passive: false });
    clip.addEventListener('touchend', touchEndHandler, { passive: false });

    // Store handlers for cleanup
    clip._mobileHandlers = {
      touchStart: touchStartHandler,
      touchMove: touchMoveHandler,
      touchEnd: touchEndHandler
    };
  }

  handleVideoTap(video, index) {
    console.log(`📱 Video ${index} tapped`);
    
    // Trigger haptic feedback
    this.triggerHapticFeedback('light');
    
    if (video.paused) {
      video.play().catch(err => {
        console.error(`❌ Video ${index} play failed:`, err);
      });
    } else {
      video.pause();
    }
  }

  handleVideoDoubleTap(video, index) {
    console.log(`📱 Video ${index} double-tapped`);
    
    // Trigger haptic feedback
    this.triggerHapticFeedback('medium');
    
    // Try to enter fullscreen
    if (video.requestFullscreen) {
      video.requestFullscreen();
    } else if (video.webkitRequestFullscreen) {
      video.webkitRequestFullscreen();
    } else if (video.mozRequestFullScreen) {
      video.mozRequestFullScreen();
    } else {
      // Fallback: toggle mute
      video.muted = !video.muted;
      
      // Show feedback
      const feedback = video.muted ? '🔇 Muted' : '🔊 Unmuted';
      this.showMobileToast(feedback);
    }
  }

  handleCardSwipeRight(clip, index) {
    console.log(`📱 Card ${index} swiped right - quick select`);
    
    // Trigger haptic feedback
    this.triggerHapticFeedback('medium');
    
    // Quick select/deselect
    this.toggleClipSelection(index);
    
    // Visual feedback
    this.showMobileToast('Clip selected');
  }

  handleCardSwipeLeft(clip, index) {
    console.log(`📱 Card ${index} swiped left - quick download`);
    
    // Trigger haptic feedback
    this.triggerHapticFeedback('heavy');
    
    // Quick download
    const downloadBtn = clip.querySelector('.clip-download-btn');
    if (downloadBtn) {
      const url = downloadBtn.dataset.clipUrl;
      const name = downloadBtn.dataset.clipName;
      this.downloadClip(url, name);
      
      // Visual feedback
      this.showMobileToast('Download started');
    }
  }

  showMobileToast(message) {
    // Create or update toast
    let toast = document.querySelector('.mobile-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'mobile-toast';
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add('show');

    // Auto-hide after 2 seconds
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

  addMobileResultsStyles() {
    if (document.querySelector('#mobile-results-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'mobile-results-styles';
    style.textContent = `
      @media (max-width: 768px) {
        .result-clip {
          margin-bottom: 24px;
          border-radius: 12px;
          overflow: hidden;
          touch-action: pan-y;
        }
        
        .result-clip video {
          border-radius: 8px;
          width: 100%;
          height: auto;
          max-height: 250px;
          object-fit: cover;
        }
        
        .clip-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 12px;
        }
        
        .clip-actions button {
          flex: 1;
          min-width: calc(50% - 4px);
          padding: 12px 16px;
          font-size: 14px;
          border-radius: 8px;
        }
        
        .clip-info {
          padding: 16px;
        }
        
        .clip-header h3 {
          font-size: 1.1rem;
          margin-bottom: 8px;
        }
        
        .clip-metadata {
          font-size: 0.8rem;
          margin-bottom: 12px;
        }
      }
      
      .mobile-toast {
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
      
      .mobile-toast.show {
        opacity: 1;
      }
    `;
    document.head.appendChild(style);
  }

  destroy() {
    // Clean up mobile event listeners
    if (this.isMobileDevice) {
      const resultsContent = document.getElementById('resultsContent');
      if (resultsContent) {
        // Remove video mobile handlers
        resultsContent.querySelectorAll('video').forEach(video => {
          if (video._mobileHandlers) {
            video.removeEventListener('touchstart', video._mobileHandlers.touchStart);
            video.removeEventListener('touchmove', video._mobileHandlers.touchMove);
            video.removeEventListener('touchend', video._mobileHandlers.touchEnd);
            delete video._mobileHandlers;
          }
        });

        // Remove card mobile handlers
        resultsContent.querySelectorAll('.result-clip').forEach(clip => {
          if (clip._mobileHandlers) {
            clip.removeEventListener('touchstart', clip._mobileHandlers.touchStart);
            clip.removeEventListener('touchmove', clip._mobileHandlers.touchMove);
            clip.removeEventListener('touchend', clip._mobileHandlers.touchEnd);
            delete clip._mobileHandlers;
          }
        });
      }
    }

    // Cleanup intersection observer
    if (this.videoObserver) {
      this.videoObserver.disconnect();
      this.videoObserver = null;
      console.log('👁️ Video intersection observer cleaned up');
    }

    this.reset();
    console.log('🧹 ResultsGrid component destroyed');
  }

  setupTikTokStyleVideos(container) {
    console.log('🎵 Setting up TikTok-style video behavior');
    
    const videos = container.querySelectorAll('video');
    this.videos = Array.from(videos);
    this.currentlyPlaying = null;
    
    videos.forEach((video, index) => {
      // Configure for TikTok-style autoplay
      video.muted = true;  // Required for autoplay
      video.loop = true;   // Loop like TikTok
      video.controls = false; // Hide controls initially
      video.playsInline = true; // iOS compatibility
      
      console.log(`🎬 Video ${index} configured for TikTok-style playback`);
      
      // Pre-check: fetch video to verify it's actually a video file
      const videoUrl = video.src || video.querySelector('source')?.src;
      if (videoUrl) {
        fetch(videoUrl, { method: 'HEAD' })
          .then(response => {
            const contentLength = parseInt(response.headers.get('content-length') || '0');
            console.log(`📏 Video ${index} size: ${contentLength} bytes`);
            
            // If file is suspiciously small (< 1KB), it's likely not a real video
            if (contentLength < 1000) {
              console.error(`❌ Video ${index} is too small to be a real video (${contentLength} bytes)`);
              this.showVideoError(video, index);
            }
          })
          .catch(err => {
            console.error(`❌ Failed to check video ${index}:`, err);
          });
      }
      
      // Add event listeners
      video.addEventListener('loadedmetadata', () => {
        console.log(`✅ Video ${index} metadata loaded, ready for intersection observer`);
      });
      
      // Additional check: if video has no duration or is too short, it's likely invalid
      video.addEventListener('loadeddata', () => {
        if (!video.duration || video.duration < 0.1 || isNaN(video.duration)) {
          console.error(`❌ Video ${index} has invalid duration:`, video.duration);
          this.showVideoError(video, index);
        }
      });
      
      // Also check if video fails during loading
      video.addEventListener('stalled', () => {
        console.warn(`⚠️ Video ${index} stalled during loading`);
      });
      
      video.addEventListener('suspend', () => {
        // Browser optimization - video loading paused to save bandwidth/memory
        // This is normal behavior when multiple videos are present
      });
      
      video.addEventListener('play', () => {
        console.log(`▶️ Video ${index}: started playing (muted: ${video.muted})`);
        this.currentlyPlaying = index;
        this.pauseOtherVideos(index);
      });
      
      video.addEventListener('pause', () => {
        console.log(`⏸️ Video ${index}: paused`);
      });
      
      // Click to toggle mute/unmute and controls
      video.addEventListener('click', (e) => {
        e.preventDefault();
        this.handleVideoClick(video, index);
      });
      
      // Handle video loading errors
      video.addEventListener('error', (e) => {
        console.error(`❌ Video ${index} failed to load:`, e);
        this.showVideoError(video, index);
      });
      
      // Store video index for reference
      video.dataset.videoIndex = index;
    });
    
    // Setup intersection observer for autoplay
    this.setupVideoIntersectionObserver();
  }
  
  setupVideoIntersectionObserver() {
    console.log('👁️ Setting up intersection observer for video autoplay');
    
    if (!window.IntersectionObserver) {
      console.warn('⚠️ IntersectionObserver not supported, falling back to manual controls');
      return;
    }
    
    const options = {
      root: null,
      rootMargin: '-20% 0px -20% 0px', // Video must be at least 60% visible
      threshold: 0.6
    };
    
    this.videoObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const video = entry.target;
        const index = parseInt(video.dataset.videoIndex);
        
        if (entry.isIntersecting) {
          console.log(`👁️ Video ${index} is visible, starting muted autoplay`);
          this.playVideoMuted(video, index);
        } else {
          console.log(`👁️ Video ${index} is not visible, pausing`);
          this.pauseVideo(video, index);
        }
      });
    }, options);
    
    // Observe all videos
    this.videos.forEach(video => {
      this.videoObserver.observe(video);
    });
  }
  
  playVideoMuted(video, index) {
    if (video.readyState >= 2) { // HAVE_CURRENT_DATA
      video.muted = true;
      video.play().then(() => {
        console.log(`✅ Video ${index} started playing (muted autoplay)`);
      }).catch(err => {
        console.log(`⚠️ Video ${index} autoplay failed (expected):`, err.message);
      });
    }
  }
  
  pauseVideo(video, index) {
    if (!video.paused) {
      video.pause();
      console.log(`⏸️ Video ${index} paused (out of viewport)`);
    }
  }
  
  pauseOtherVideos(currentIndex) {
    this.videos.forEach((video, index) => {
      if (index !== currentIndex && !video.paused) {
        video.pause();
        console.log(`⏸️ Paused video ${index} (single video priority)`);
      }
    });
  }
  
  handleVideoClick(video, index) {
    console.log(`🖱️ Video ${index} clicked`);
    
    if (video.muted) {
      // Unmute and show controls (like TikTok/YouTube)
      video.muted = false;
      video.controls = true;
      this.showVideoFeedback(video, '🔊 Audio enabled');
      console.log(`🔊 Video ${index} unmuted, controls enabled`);
    } else {
      // Toggle play/pause
      if (video.paused) {
        video.play();
      } else {
        video.pause();
      }
    }
  }
  
  showVideoError(video, index) {
    console.log(`🚫 Showing error message for video ${index}`);
    
    // Create error overlay
    const errorOverlay = document.createElement('div');
    errorOverlay.className = 'video-error-overlay';
    errorOverlay.innerHTML = `
      <div class="error-content">
        <div class="error-icon">⚠️</div>
        <div class="error-title">Video niet beschikbaar</div>
        <div class="error-message">Deze video kan niet worden afgespeeld</div>
        <div class="error-details">Het videobestand is mogelijk beschadigd of gebruikt een niet-ondersteund formaat</div>
      </div>
    `;
    
    // Add styles for error overlay
    errorOverlay.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.85);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10;
    `;
    
    // Style the error content
    const errorContent = errorOverlay.querySelector('.error-content');
    errorContent.style.cssText = `
      text-align: center;
      color: white;
      padding: 20px;
    `;
    
    const errorIcon = errorOverlay.querySelector('.error-icon');
    errorIcon.style.cssText = `
      font-size: 48px;
      margin-bottom: 10px;
    `;
    
    const errorTitle = errorOverlay.querySelector('.error-title');
    errorTitle.style.cssText = `
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 5px;
    `;
    
    const errorMessage = errorOverlay.querySelector('.error-message');
    errorMessage.style.cssText = `
      font-size: 14px;
      margin-bottom: 10px;
      opacity: 0.9;
    `;
    
    const errorDetails = errorOverlay.querySelector('.error-details');
    errorDetails.style.cssText = `
      font-size: 12px;
      opacity: 0.7;
      max-width: 250px;
      margin: 0 auto;
    `;
    
    // Hide the video and show error
    video.style.display = 'none';
    
    const videoContainer = video.closest('.clip-item') || video.parentElement;
    videoContainer.style.position = 'relative';
    videoContainer.appendChild(errorOverlay);
  }

  showVideoFeedback(video, message) {
    // Create temporary feedback overlay
    const feedback = document.createElement('div');
    feedback.textContent = message;
    feedback.style.cssText = `
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(0, 0, 0, 0.8);
      color: white;
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 14px;
      pointer-events: none;
      z-index: 1000;
      animation: fadeInOut 2s ease-in-out;
    `;
    
    // Add CSS animation if not exists
    if (!document.querySelector('#videoFeedbackStyle')) {
      const style = document.createElement('style');
      style.id = 'videoFeedbackStyle';
      style.textContent = `
        @keyframes fadeInOut {
          0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
          30% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
          70% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
          100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
        }
      `;
      document.head.appendChild(style);
    }
    
    const videoContainer = video.closest('.clip-item');
    videoContainer.style.position = 'relative';
    videoContainer.appendChild(feedback);
    
    setTimeout(() => {
      feedback.remove();
    }, 2000);
  }
}

export default ResultsGrid;