/**
 * File Validator Service
 * Clean validation logic - built from scratch
 * Inspired by dashboard.js validation but much cleaner
 */

export class FileValidator {
  constructor() {
    this.config = {
      // Video formats
      allowedTypes: [
        'video/mp4',
        'video/mov', 
        'video/avi',
        'video/webm',
        'video/mkv',
        'video/quicktime'
      ],
      
      // Size limits
      maxFileSize: 2 * 1024 * 1024 * 1024, // 2GB
      minFileSize: 1024, // 1KB
      
      // URL patterns
      allowedUrlPatterns: [
        /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.+/,
        /^https?:\/\/(www\.)?vimeo\.com\/.+/,
        /^https?:\/\/(www\.)?twitch\.tv\/.+/,
        /^https?:\/\/.+\.(mp4|mov|avi|webm|mkv)(\?.*)?$/i
      ]
    };
  }

  /**
   * Validate uploaded file
   */
  validateFile(file) {
    const errors = [];

    // Check if file exists
    if (!file) {
      return { valid: false, error: 'Geen bestand geselecteerd' };
    }

    // Check file type
    if (!this.isValidFileType(file.type)) {
      errors.push(`Bestandstype niet ondersteund: ${file.type}`);
    }

    // Check file size
    const sizeCheck = this.validateFileSize(file.size);
    if (!sizeCheck.valid) {
      errors.push(sizeCheck.error);
    }

    // Check file name
    const nameCheck = this.validateFileName(file.name);
    if (!nameCheck.valid) {
      errors.push(nameCheck.error);
    }

    return {
      valid: errors.length === 0,
      error: errors.length > 0 ? errors[0] : null,
      errors: errors,
      warnings: this.getFileWarnings(file)
    };
  }

  /**
   * Validate URL
   */
  validateUrl(url) {
    const errors = [];

    // Check if URL exists
    if (!url || typeof url !== 'string' || url.trim().length === 0) {
      return { valid: false, error: 'Geen URL ingevoerd' };
    }

    const cleanUrl = url.trim();

    // Check URL format
    try {
      new URL(cleanUrl);
    } catch (e) {
      return { valid: false, error: 'Ongeldige URL format' };
    }

    // Check if URL matches allowed patterns
    const isAllowed = this.config.allowedUrlPatterns.some(pattern => 
      pattern.test(cleanUrl)
    );

    if (!isAllowed) {
      errors.push('URL niet ondersteund. Gebruik YouTube, Vimeo, Twitch of directe video links.');
    }

    // Check URL accessibility (basic)
    if (cleanUrl.includes('localhost') || cleanUrl.includes('127.0.0.1')) {
      errors.push('Lokale URLs zijn niet toegestaan');
    }

    return {
      valid: errors.length === 0,
      error: errors.length > 0 ? errors[0] : null,
      errors: errors,
      warnings: this.getUrlWarnings(cleanUrl)
    };
  }

  /**
   * Check if file type is valid
   */
  isValidFileType(mimeType) {
    return this.config.allowedTypes.includes(mimeType);
  }

  /**
   * Validate file size
   */
  validateFileSize(size) {
    if (size < this.config.minFileSize) {
      return {
        valid: false,
        error: 'Bestand te klein (minimum 1KB)'
      };
    }

    if (size > this.config.maxFileSize) {
      return {
        valid: false,
        error: `Bestand te groot (maximum ${this.formatFileSize(this.config.maxFileSize)})`
      };
    }

    return { valid: true };
  }

  /**
   * Validate file name
   */
  validateFileName(name) {
    if (!name || name.trim().length === 0) {
      return {
        valid: false,
        error: 'Bestandsnaam ontbreekt'
      };
    }

    // Check for dangerous characters
    const dangerousChars = /[<>:"|?*\x00-\x1f]/;
    if (dangerousChars.test(name)) {
      return {
        valid: false,
        error: 'Bestandsnaam bevat ongeldige karakters'
      };
    }

    // Check length
    if (name.length > 255) {
      return {
        valid: false,
        error: 'Bestandsnaam te lang (maximum 255 karakters)'
      };
    }

    return { valid: true };
  }

  /**
   * Get file warnings (non-blocking issues)
   */
  getFileWarnings(file) {
    const warnings = [];

    // Large file warning
    if (file.size > 500 * 1024 * 1024) { // 500MB
      warnings.push('Groot bestand - upload kan lang duren');
    }

    // Old format warning
    if (file.type === 'video/avi') {
      warnings.push('AVI formaat kan compatibiliteitsproblemen hebben');
    }

    // Special characters in name
    if (/[^\w\-_. ]/.test(file.name)) {
      warnings.push('Speciale karakters in bestandsnaam kunnen problemen veroorzaken');
    }

    return warnings;
  }

  /**
   * Get URL warnings
   */
  getUrlWarnings(url) {
    const warnings = [];

    // HTTP warning
    if (url.startsWith('http://')) {
      warnings.push('HTTP link - HTTPS is veiliger');
    }

    // Very long URL
    if (url.length > 500) {
      warnings.push('Zeer lange URL - controleer of deze correct is');
    }

    return warnings;
  }

  /**
   * Format file size for display
   */
  formatFileSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${Math.round(size * 100) / 100} ${units[unitIndex]}`;
  }

  /**
   * Get detailed file info
   */
  getFileInfo(file) {
    return {
      name: file.name,
      size: this.formatFileSize(file.size),
      type: file.type,
      lastModified: new Date(file.lastModified).toLocaleString('nl-NL'),
      isValid: this.validateFile(file).valid,
      warnings: this.getFileWarnings(file)
    };
  }

  /**
   * Get supported formats for display
   */
  getSupportedFormats() {
    return {
      video: this.config.allowedTypes.map(type => type.replace('video/', '')),
      maxSize: this.formatFileSize(this.config.maxFileSize),
      supportedSites: [
        'YouTube (youtube.com, youtu.be)',
        'Vimeo (vimeo.com)', 
        'Twitch (twitch.tv)',
        'Directe video links (.mp4, .mov, etc.)'
      ]
    };
  }

  /**
   * Quick validation - just true/false
   */
  isValidFile(file) {
    return this.validateFile(file).valid;
  }

  /**
   * Quick URL validation - just true/false
   */
  isValidUrl(url) {
    return this.validateUrl(url).valid;
  }
}

export default FileValidator;