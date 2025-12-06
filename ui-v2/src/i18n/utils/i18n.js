/**
 * Enterprise-grade i18n system for UI v2
 * Supports interpolation, pluralization, and dynamic loading
 */

class I18nSystem {
  constructor() {
    this.currentLocale = 'en'; // Default to English
    this.fallbackLocale = 'en';
    this.translations = new Map();
    this.loadedLocales = new Set();
    this.observers = new Set();
    
    // Detect browser language
    this.detectLanguage();
    
    // Load initial locale
    this.loadLocale(this.currentLocale);
  }

  /**
   * Detect browser language and set default
   */
  detectLanguage() {
    const savedLocale = localStorage.getItem('preferred-locale');
    if (savedLocale && this.isSupported(savedLocale)) {
      this.currentLocale = savedLocale;
      return;
    }

    // Browser language detection
    const browserLang = navigator.language || navigator.userLanguage;
    const langCode = browserLang.split('-')[0]; // 'en-US' -> 'en'
    
    if (this.isSupported(langCode)) {
      this.currentLocale = langCode;
    }
  }

  /**
   * Check if locale is supported
   */
  isSupported(locale) {
    const supportedLocales = ['nl', 'en', 'de', 'fr'];
    return supportedLocales.includes(locale);
  }

  /**
   * Load locale translations
   */
  async loadLocale(locale, isRetry = false) {
    if (this.loadedLocales.has(locale)) {
      return this.translations.get(locale);
    }

    try {
      const response = await fetch(`./src/i18n/locales/${locale}.json?v=${Date.now()}`);
      if (!response.ok) {
        throw new Error(`Failed to load locale: ${locale}`);
      }
      
      const translations = await response.json();
      this.translations.set(locale, translations);
      this.loadedLocales.add(locale);
      
      return translations;
    } catch (error) {
      console.warn(`Failed to load locale ${locale}`);
      
      // Prevent infinite loop - if we're already trying fallback, create empty fallback
      if (isRetry || locale === this.fallbackLocale) {
        console.warn(`Creating empty fallback translations for ${locale}`);
        const emptyTranslations = {
          'common': {
            'loading': 'Loading...',
            'error': 'Error',
            'app_title': 'AgentOS VideoProcessor'
          },
          'results': {
            'download_started': 'Download started',
            'download_failed': 'Download failed',
            'all_downloads_started': 'All downloads started'
          }
        };
        this.translations.set(locale, emptyTranslations);
        this.loadedLocales.add(locale);
        return emptyTranslations;
      }
      
      // Try fallback locale once
      console.warn(`Falling back to ${this.fallbackLocale}`);
      return this.loadLocale(this.fallbackLocale, true);
    }
  }

  /**
   * Set current locale
   */
  async setLocale(locale) {
    if (!this.isSupported(locale)) {
      console.warn(`Unsupported locale: ${locale}`);
      return;
    }

    await this.loadLocale(locale);
    this.currentLocale = locale;
    
    // Save preference
    localStorage.setItem('preferred-locale', locale);
    
    // Notify observers
    this.notifyObservers();
    
    // Update document language
    document.documentElement.lang = locale;
  }

  /**
   * Get translation by key with interpolation support
   */
  t(key, params = {}) {
    const translation = this.getTranslation(key);
    
    if (!translation) {
      // More detailed debugging
      const currentTranslations = this.translations.get(this.currentLocale);
      console.warn(`Translation missing for key: ${key} (locale: ${this.currentLocale})`, {
        hasTranslations: !!currentTranslations,
        availableKeys: currentTranslations ? Object.keys(currentTranslations).slice(0, 5) : 'none',
        keyPath: key.split('.')
      });
      return key; // Return key as fallback
    }

    return this.interpolate(translation, params);
  }

  /**
   * Get raw translation without interpolation
   */
  getTranslation(key) {
    const currentTranslations = this.translations.get(this.currentLocale);
    const fallbackTranslations = this.translations.get(this.fallbackLocale);
    
    // Try current locale first
    let translation = this.getNestedValue(currentTranslations, key);
    
    // Fall back to fallback locale
    if (!translation && fallbackTranslations) {
      translation = this.getNestedValue(fallbackTranslations, key);
    }
    
    return translation;
  }

  /**
   * Get nested object value by dot notation key
   */
  getNestedValue(obj, key) {
    if (!obj) return null;
    
    return key.split('.').reduce((current, k) => {
      return current && current[k] !== undefined ? current[k] : null;
    }, obj);
  }

  /**
   * Interpolate parameters into translation string
   */
  interpolate(template, params) {
    if (typeof template !== 'string') {
      return template;
    }

    return template.replace(/\{(\w+)\}/g, (match, key) => {
      return params[key] !== undefined ? params[key] : match;
    });
  }

  /**
   * Pluralization support
   */
  plural(key, count, params = {}) {
    const pluralKey = count === 1 ? `${key}` : `${key}_plural`;
    return this.t(pluralKey, { count, ...params });
  }

  /**
   * Date formatting based on locale
   */
  formatDate(date, options = {}) {
    const defaultOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    };
    
    return new Intl.DateTimeFormat(this.currentLocale, { ...defaultOptions, ...options })
      .format(new Date(date));
  }

  /**
   * Number formatting based on locale
   */
  formatNumber(number, options = {}) {
    return new Intl.NumberFormat(this.currentLocale, options).format(number);
  }

  /**
   * Currency formatting
   */
  formatCurrency(amount, currency = 'EUR') {
    return new Intl.NumberFormat(this.currentLocale, {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  /**
   * Relative time formatting (e.g., "2 hours ago")
   */
  formatRelativeTime(date) {
    const rtf = new Intl.RelativeTimeFormat(this.currentLocale, { numeric: 'auto' });
    const now = new Date();
    const diffTime = date - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (Math.abs(diffDays) < 1) {
      const diffHours = Math.ceil(diffTime / (1000 * 60 * 60));
      if (Math.abs(diffHours) < 1) {
        const diffMinutes = Math.ceil(diffTime / (1000 * 60));
        return rtf.format(diffMinutes, 'minute');
      }
      return rtf.format(diffHours, 'hour');
    }
    
    return rtf.format(diffDays, 'day');
  }

  /**
   * Subscribe to locale changes
   */
  subscribe(callback) {
    this.observers.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.observers.delete(callback);
    };
  }

  /**
   * Notify all observers of locale change
   */
  notifyObservers() {
    this.observers.forEach(callback => {
      try {
        callback(this.currentLocale);
      } catch (error) {
        console.error('Error in i18n observer:', error);
      }
    });
  }

  /**
   * Get current locale info
   */
  getLocaleInfo() {
    return {
      current: this.currentLocale,
      fallback: this.fallbackLocale,
      loaded: Array.from(this.loadedLocales),
      direction: this.isRTL() ? 'rtl' : 'ltr'
    };
  }

  /**
   * Check if current locale is right-to-left
   */
  isRTL() {
    const rtlLocales = ['ar', 'he', 'fa', 'ur'];
    return rtlLocales.includes(this.currentLocale);
  }

  /**
   * Get available locales with native names
   */
  getAvailableLocales() {
    return [
      { code: 'nl', name: 'Nederlands', nativeName: 'Nederlands' },
      { code: 'en', name: 'English', nativeName: 'English' },
      { code: 'de', name: 'German', nativeName: 'Deutsch' },
      { code: 'fr', name: 'French', nativeName: 'Français' }
    ];
  }

  /**
   * Preload multiple locales for better performance
   */
  async preloadLocales(locales) {
    const promises = locales.map(locale => this.loadLocale(locale));
    await Promise.all(promises);
  }

  /**
   * Get translation with HTML support (for rich text)
   */
  tHTML(key, params = {}) {
    const translation = this.t(key, params);
    
    // Create a temporary element to safely parse HTML
    const temp = document.createElement('div');
    temp.innerHTML = translation;
    
    return temp.innerHTML;
  }

  /**
   * Batch translation for performance
   */
  tBatch(keys, params = {}) {
    const results = {};
    keys.forEach(key => {
      results[key] = this.t(key, params);
    });
    return results;
  }
}

// Create global instance
const i18n = new I18nSystem();

// Export for ES modules
export default i18n;

// Global access for legacy code
window.i18n = i18n;

// Helper functions for common use cases
export const t = (key, params) => i18n.t(key, params);
export const plural = (key, count, params) => i18n.plural(key, count, params);
export const formatDate = (date, options) => i18n.formatDate(date, options);
export const formatNumber = (number, options) => i18n.formatNumber(number, options);
export const formatCurrency = (amount, currency) => i18n.formatCurrency(amount, currency);
export const setLocale = (locale) => i18n.setLocale(locale);
export const getCurrentLocale = () => i18n.currentLocale;

// DOM helpers for declarative usage
export function initDOMTranslations() {
  // Find all elements with data-i18n attribute
  const elements = document.querySelectorAll('[data-i18n]');
  
  elements.forEach(element => {
    const key = element.dataset.i18n;
    const params = element.dataset.i18nParams ? JSON.parse(element.dataset.i18nParams) : {};
    
    if (element.dataset.i18nHtml === 'true') {
      element.innerHTML = i18n.tHTML(key, params);
    } else {
      element.textContent = i18n.t(key, params);
    }
    
    // Handle placeholders
    const placeholderKey = element.dataset.i18nPlaceholder;
    if (placeholderKey && element.hasAttribute('placeholder')) {
      const placeholderText = i18n.t(placeholderKey, params);
      console.log('🔍 Setting placeholder:', {
        element: element.id || element.tagName,
        key: placeholderKey,
        text: placeholderText
      });
      element.placeholder = placeholderText;
    }
    
    // Handle aria-labels
    const ariaLabelKey = element.dataset.i18nAriaLabel;
    if (ariaLabelKey) {
      element.setAttribute('aria-label', i18n.t(ariaLabelKey, params));
    }
    
    // Handle titles
    const titleKey = element.dataset.i18nTitle;
    if (titleKey) {
      element.title = i18n.t(titleKey, params);
    }
  });
}

// Auto-update DOM when locale changes
i18n.subscribe(() => {
  // Add small delay to ensure translations are loaded
  setTimeout(initDOMTranslations, 50);
});

// Initialize DOM translations on load (but don't auto-run on page load)
// Let the main app control when to run initDOMTranslations()
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    // Only run if we have translations loaded
    if (i18n.translations.has(i18n.currentLocale)) {
      initDOMTranslations();
    }
  });
} else {
  // Only run if we have translations loaded
  if (i18n.translations.has(i18n.currentLocale)) {
    initDOMTranslations();
  }
}