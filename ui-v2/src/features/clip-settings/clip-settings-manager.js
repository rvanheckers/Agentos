/**
 * Clip Settings Manager
 * Handles the clip length selection and advanced settings
 */

import i18n from '../../i18n/utils/i18n.js';

export class ClipSettingsManager {
  constructor() {
    this.settings = {
      clip_length: 30,  // default
      max_moments: 6,   // optimal: balance between choice and quality
      min_gap: 1.0,     // optimal: prevents overlapping clips
      topk: 25          // optimal: balance between speed and precision
    };

    this.init();
  }

  init() {
    this.setupEventListeners();
    console.log('✅ ClipSettingsManager initialized');
  }

  setupEventListeners() {
    // Advanced toggle
    const advancedToggle = document.getElementById('advanced_toggle');
    if (advancedToggle) {
      advancedToggle.addEventListener('click', () => this.toggleAdvanced());
    }

    // Clip length radio buttons
    const clipLengthRadios = document.querySelectorAll('input[name="clip_length"]');
    clipLengthRadios.forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.settings.clip_length = parseInt(e.target.value);
        console.log('📏 Clip length changed to:', this.settings.clip_length);
      });
    });

    // Advanced settings inputs
    const advMaxMoments = document.getElementById('adv_max_moments');
    if (advMaxMoments) {
      advMaxMoments.addEventListener('change', (e) => {
        this.settings.max_moments = parseInt(e.target.value);
        console.log('🎯 Max moments changed to:', this.settings.max_moments);
      });
    }

    const advMinGap = document.getElementById('adv_min_gap');
    if (advMinGap) {
      advMinGap.addEventListener('change', (e) => {
        this.settings.min_gap = parseFloat(e.target.value);
        console.log('⏱️ Min gap changed to:', this.settings.min_gap);
      });
    }

    const advQuality = document.getElementById('adv_quality');
    if (advQuality) {
      advQuality.addEventListener('change', (e) => {
        // Convert quality setting to topk value
        const qualityMap = {
          'fast': 15,
          'balanced': 25,
          'precise': 40
        };
        this.settings.topk = qualityMap[e.target.value] || 25;
        console.log('🔍 Quality changed to:', e.target.value, '(topk:', this.settings.topk, ')');
      });
    }
  }

  toggleAdvanced() {
    const toggle = document.getElementById('advanced_toggle');
    const panel = document.getElementById('advanced_panel');

    if (!toggle || !panel) return;

    const isExpanded = toggle.getAttribute('aria-expanded') === 'true';

    toggle.setAttribute('aria-expanded', !isExpanded);
    panel.hidden = isExpanded;

    console.log('🔧 Advanced settings:', isExpanded ? 'closed' : 'opened');
  }

  getSettings() {
    // Collect current values from DOM
    const clipLengthInput = document.querySelector('input[name="clip_length"]:checked');
    if (clipLengthInput) {
      this.settings.clip_length = parseInt(clipLengthInput.value);
    }

    const advMaxMoments = document.getElementById('adv_max_moments');
    if (advMaxMoments) {
      this.settings.max_moments = parseInt(advMaxMoments.value);
    }

    const advMinGap = document.getElementById('adv_min_gap');
    if (advMinGap) {
      this.settings.min_gap = parseFloat(advMinGap.value);
    }

    const advQuality = document.getElementById('adv_quality');
    if (advQuality) {
      const qualityMap = {
        'fast': 15,
        'balanced': 25,
        'precise': 40
      };
      this.settings.topk = qualityMap[advQuality.value] || 25;
    }

    return this.settings;
  }

  getUserPreferences() {
    // Format for backend API
    const settings = this.getSettings();
    return {
      clip_length: settings.clip_length,
      max_moments: settings.max_moments,
      min_gap: settings.min_gap,
      topk: settings.topk
    };
  }

  reset() {
    // Reset to defaults
    this.settings = {
      clip_length: 30,
      max_moments: 6,
      min_gap: 1.0,
      topk: 25
    };

    // Reset DOM
    const defaultRadio = document.getElementById('clip_len_30');
    if (defaultRadio) {
      defaultRadio.checked = true;
    }

    const advMaxMoments = document.getElementById('adv_max_moments');
    if (advMaxMoments) advMaxMoments.value = 6;

    const advMinGap = document.getElementById('adv_min_gap');
    if (advMinGap) advMinGap.value = 1.0;

    const advQuality = document.getElementById('adv_quality');
    if (advQuality) advQuality.value = 'balanced';

    // Close advanced panel
    const toggle = document.getElementById('advanced_toggle');
    const panel = document.getElementById('advanced_panel');
    if (toggle && panel) {
      toggle.setAttribute('aria-expanded', 'false');
      panel.hidden = true;
    }

    console.log('🔄 Clip settings reset to defaults');
  }

  validate() {
    const settings = this.getSettings();
    const errors = [];

    // Validate clip_length
    if (![30, 45, 60].includes(settings.clip_length)) {
      errors.push('Clip length must be 30, 45, or 60 seconds');
    }

    // Validate max_moments
    if (settings.max_moments < 3 || settings.max_moments > 12) {
      errors.push('Max clips must be between 3 and 12');
    }

    // Validate min_gap
    if (settings.min_gap < 0 || settings.min_gap > 3) {
      errors.push('Min gap must be between 0 and 3 seconds');
    }

    // Validate topk (automatically set, so should always be valid)
    if (settings.topk < 15 || settings.topk > 50) {
      errors.push('Quality setting produced invalid analysis depth');
    }

    if (errors.length > 0) {
      console.error('❌ Validation errors:', errors);
      this.showError(errors.join(', '));
      return { valid: false, errors };
    }

    return { valid: true };
  }

  showSuccess(message = null) {
    const successEl = document.getElementById('job_success');
    const errorEl = document.getElementById('job_error');

    if (successEl) {
      const feedbackText = successEl.querySelector('.feedback-text');
      if (message) {
        feedbackText.textContent = message;
      } else {
        // Use i18n default with clip length
        const clipLength = this.getSettings().clip_length;
        feedbackText.textContent = i18n.t('clip_settings.feedback.job_started', { clipLength });
      }
      successEl.hidden = false;
      setTimeout(() => successEl.hidden = true, 5000);
    }

    if (errorEl) {
      errorEl.hidden = true;
    }
  }

  showError(message = null) {
    const errorEl = document.getElementById('job_error');
    const successEl = document.getElementById('job_success');

    if (errorEl) {
      const feedbackText = errorEl.querySelector('.feedback-text');
      if (message) {
        feedbackText.textContent = message;
      } else {
        feedbackText.textContent = i18n.t('clip_settings.feedback.validation_error');
      }
      errorEl.hidden = false;
      setTimeout(() => errorEl.hidden = true, 8000);
    }

    if (successEl) {
      successEl.hidden = true;
    }
  }

  hideAllFeedback() {
    const successEl = document.getElementById('job_success');
    const errorEl = document.getElementById('job_error');

    if (successEl) successEl.hidden = true;
    if (errorEl) errorEl.hidden = true;
  }
}

// Export singleton instance
export const clipSettingsManager = new ClipSettingsManager();