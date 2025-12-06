/**
 * Download Manager Service
 * Handles file downloads with progress tracking and error handling
 */

export class DownloadManager {
  constructor(apiClient = null) {
    this.apiClient = apiClient;
    this.activeDownloads = new Map();
    this.downloadHistory = [];
  }

  /**
   * Download a file with optional progress callback
   * @param {string} url - File URL to download
   * @param {string} filename - Desired filename
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise} Download promise
   */
  async downloadFile(url, filename, onProgress = null) {
    console.log('🔽 Starting download:', filename, 'from', url);
    
    const downloadId = this.generateDownloadId();
    
    try {
      // Start download tracking
      this.activeDownloads.set(downloadId, {
        url,
        filename,
        startTime: Date.now(),
        status: 'starting'
      });

      // For simple downloads, use the browser's download mechanism
      if (!onProgress) {
        return this.simpleDownload(url, filename, downloadId);
      }

      // For downloads with progress tracking, use fetch + blob
      return this.progressDownload(url, filename, downloadId, onProgress);

    } catch (error) {
      console.error('❌ Download failed:', error);
      this.activeDownloads.delete(downloadId);
      throw error;
    }
  }

  /**
   * Simple download using browser's built-in mechanism
   * @param {string} url 
   * @param {string} filename 
   * @param {string} downloadId 
   * @returns {Promise}
   */
  simpleDownload(url, filename, downloadId) {
    return new Promise((resolve, reject) => {
      try {
        console.log('🔽 Simple download starting:', url, filename);
        
        // Use fetch to get the file and create blob URL
        fetch(url)
          .then(response => {
            if (!response.ok) {
              throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.blob();
          })
          .then(blob => {
            console.log('✅ Blob created, size:', blob.size);
            
            // Create blob URL and download
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = filename;
            link.style.display = 'none';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Clean up blob URL
            setTimeout(() => {
              URL.revokeObjectURL(blobUrl);
            }, 1000);
            
            this.onDownloadComplete(downloadId, filename);
            resolve(filename);
          })
          .catch(error => {
            console.error('❌ Download fetch error:', error);
            this.onDownloadError(downloadId, error);
            reject(error);
          });

      } catch (error) {
        console.error('❌ Download setup error:', error);
        this.onDownloadError(downloadId, error);
        reject(error);
      }
    });
  }

  /**
   * Download with progress tracking
   * @param {string} url 
   * @param {string} filename 
   * @param {string} downloadId 
   * @param {Function} onProgress 
   * @returns {Promise}
   */
  async progressDownload(url, filename, downloadId, onProgress) {
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentLength = response.headers.get('content-length');
      const total = contentLength ? parseInt(contentLength, 10) : 0;
      let loaded = 0;

      const reader = response.body.getReader();
      const chunks = [];

      // Update download status
      this.activeDownloads.set(downloadId, {
        ...this.activeDownloads.get(downloadId),
        status: 'downloading',
        total,
        loaded: 0
      });

      // Read stream with progress
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        chunks.push(value);
        loaded += value.length;

        // Update progress
        const progress = total > 0 ? (loaded / total) * 100 : 0;
        
        this.activeDownloads.set(downloadId, {
          ...this.activeDownloads.get(downloadId),
          loaded,
          progress
        });

        if (onProgress) {
          onProgress(progress, loaded, total);
        }
      }

      // Create blob and download
      const blob = new Blob(chunks);
      const downloadUrl = URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      link.click();

      // Cleanup
      URL.revokeObjectURL(downloadUrl);
      this.onDownloadComplete(downloadId, filename);
      
      return filename;

    } catch (error) {
      this.onDownloadError(downloadId, error);
      throw error;
    }
  }

  /**
   * Download multiple files as a zip (if supported)
   * @param {Array} files - Array of {url, filename} objects
   * @param {string} zipName - Name for the zip file
   * @returns {Promise}
   */
  async downloadMultipleAsZip(files, zipName = 'clips.zip') {
    console.log('📦 Creating zip download:', zipName, 'with', files.length, 'files');
    
    try {
      // Check if JSZip is available (would need to be loaded separately)
      if (typeof JSZip === 'undefined') {
        console.warn('⚠️ JSZip not available, falling back to individual downloads');
        return this.downloadMultipleIndividual(files);
      }

      const zip = new JSZip();
      const downloadPromises = [];

      // Fetch all files and add to zip
      for (const file of files) {
        const promise = fetch(file.url)
          .then(response => response.blob())
          .then(blob => zip.file(file.filename, blob));
        
        downloadPromises.push(promise);
      }

      await Promise.all(downloadPromises);

      // Generate zip blob and download
      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const downloadUrl = URL.createObjectURL(zipBlob);
      
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = zipName;
      link.click();

      URL.revokeObjectURL(downloadUrl);
      
      console.log('✅ Zip download completed:', zipName);
      return zipName;

    } catch (error) {
      console.error('❌ Zip download failed:', error);
      throw error;
    }
  }

  /**
   * Download multiple files individually
   * @param {Array} files - Array of {url, filename} objects
   * @returns {Promise}
   */
  async downloadMultipleIndividual(files) {
    console.log('🔽 Starting individual downloads:', files.length, 'files');
    
    const downloadPromises = files.map((file, index) => {
      // Stagger downloads to avoid overwhelming the browser
      return new Promise(resolve => {
        setTimeout(() => {
          this.downloadFile(file.url, file.filename)
            .then(resolve)
            .catch(resolve); // Continue even if one fails
        }, index * 500); // 500ms delay between downloads
      });
    });

    const results = await Promise.all(downloadPromises);
    console.log('✅ Individual downloads completed:', results.length);
    
    return results;
  }

  /**
   * Get download progress for a specific download
   * @param {string} downloadId 
   * @returns {Object|null}
   */
  getDownloadProgress(downloadId) {
    return this.activeDownloads.get(downloadId) || null;
  }

  /**
   * Get all active downloads
   * @returns {Array}
   */
  getActiveDownloads() {
    return Array.from(this.activeDownloads.entries()).map(([id, data]) => ({
      id,
      ...data
    }));
  }

  /**
   * Cancel a download (if possible)
   * @param {string} downloadId 
   */
  cancelDownload(downloadId) {
    if (this.activeDownloads.has(downloadId)) {
      this.activeDownloads.delete(downloadId);
      console.log('🚫 Download cancelled:', downloadId);
    }
  }

  /**
   * Get download history
   * @returns {Array}
   */
  getDownloadHistory() {
    return [...this.downloadHistory];
  }

  /**
   * Clear download history
   */
  clearHistory() {
    this.downloadHistory = [];
    console.log('🧹 Download history cleared');
  }

  // Private methods

  generateDownloadId() {
    return `download_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  onDownloadComplete(downloadId, filename) {
    const download = this.activeDownloads.get(downloadId);
    
    if (download) {
      const completedDownload = {
        ...download,
        status: 'completed',
        endTime: Date.now(),
        duration: Date.now() - download.startTime
      };

      this.downloadHistory.push(completedDownload);
      this.activeDownloads.delete(downloadId);

      console.log('✅ Download completed:', filename, 'in', completedDownload.duration + 'ms');
    }
  }

  onDownloadError(downloadId, error) {
    const download = this.activeDownloads.get(downloadId);
    
    if (download) {
      const failedDownload = {
        ...download,
        status: 'failed',
        error: error.message,
        endTime: Date.now(),
        duration: Date.now() - download.startTime
      };

      this.downloadHistory.push(failedDownload);
      this.activeDownloads.delete(downloadId);

      console.error('❌ Download failed:', download.filename, error.message);
    }
  }
}

export default DownloadManager;