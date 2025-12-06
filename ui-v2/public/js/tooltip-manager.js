/**
 * Tooltip Manager - Multilingual tooltips for info icons
 * Integrates with i18n system for proper language support
 */

class TooltipManager {
  constructor() {
    this.tooltips = new Map();
    this.currentTooltip = null;
    this.init();
  }

  init() {
    // Initialize tooltips after DOM is loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.initTooltips());
    } else {
      this.initTooltips();
    }
  }

  initTooltips() {
    // Find all info icons with tooltip keys
    const infoIcons = document.querySelectorAll('.info-icon[data-tooltip-key]');

    infoIcons.forEach(icon => {
      const tooltipKey = icon.getAttribute('data-tooltip-key');

      // Prevent default button behavior and stop propagation
      icon.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        // Don't do anything on click - tooltips are hover/focus only
      });

      // Add hover event listeners
      icon.addEventListener('mouseenter', (e) => {
        e.stopPropagation();
        this.showTooltip(e.currentTarget, tooltipKey);
      });

      icon.addEventListener('mouseleave', (e) => {
        e.stopPropagation();
        this.hideTooltip();
      });

      // Add focus event listeners for accessibility
      icon.addEventListener('focus', (e) => {
        e.stopPropagation();
        this.showTooltip(e.currentTarget, tooltipKey);
      });

      icon.addEventListener('blur', (e) => {
        e.stopPropagation();
        this.hideTooltip();
      });

      // Store tooltip key for quick access
      this.tooltips.set(icon, tooltipKey);
    });

    // Hide tooltip when clicking elsewhere
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.info-icon')) {
        this.hideTooltip();
      }
    });

    // Update tooltips when language changes
    document.addEventListener('languageChanged', () => this.updateAllTooltips());
  }

  showTooltip(iconElement, tooltipKey) {
    this.hideTooltip(); // Hide any existing tooltip

    // Get translated text using i18n system
    const tooltipText = this.getTranslatedTooltip(tooltipKey);
    if (!tooltipText) return;

    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip purple-theme';
    tooltip.textContent = tooltipText;

    // Add unique ID for debugging
    tooltip.id = `tooltip-${Date.now()}`;

    // Add to DOM first to get dimensions
    document.body.appendChild(tooltip);

    // Get accurate positioning with fixed position
    const iconRect = iconElement.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    // Calculate center position above the icon
    let leftPos = iconRect.left + (iconRect.width / 2) - (tooltipRect.width / 2);
    const topPos = iconRect.top - tooltipRect.height - 10; // 10px gap above icon

    // Prevent tooltip from going off-screen on the right
    const rightEdge = leftPos + tooltipRect.width;
    if (rightEdge > window.innerWidth - 10) {
      leftPos = window.innerWidth - tooltipRect.width - 10;
    }

    // Prevent tooltip from going off-screen on the left
    if (leftPos < 10) {
      leftPos = 10;
    }

    // Apply positioning with fixed position (already set in CSS)
    tooltip.style.left = leftPos + 'px';
    tooltip.style.top = topPos + 'px';

    // Show with animation
    requestAnimationFrame(() => {
      tooltip.classList.add('show');
    });

    this.currentTooltip = tooltip;
  }

  hideTooltip() {
    if (this.currentTooltip) {
      this.currentTooltip.classList.remove('show');

      // Remove after animation
      setTimeout(() => {
        if (this.currentTooltip && this.currentTooltip.parentNode) {
          this.currentTooltip.parentNode.removeChild(this.currentTooltip);
        }
        this.currentTooltip = null;
      }, 200);
    }
  }

  getTranslatedTooltip(tooltipKey) {
    // Use global i18n system if available
    if (window.i18n && window.i18n.t) {
      return window.i18n.t(tooltipKey);
    }

    // Fallback to hardcoded translations
    const fallbackTranslations = this.getFallbackTranslations();
    const currentLang = document.documentElement.lang || 'nl';

    return fallbackTranslations[currentLang]?.[tooltipKey] ||
           fallbackTranslations['nl']?.[tooltipKey] ||
           'Info not available';
  }

  getFallbackTranslations() {
    return {
      'nl': {
        'clip_settings.advanced.max_moments.tooltip': 'Aanbevolen: 6 clips. Meer clips = meer keuze, minder clips = betere kwaliteit per clip',
        'clip_settings.advanced.min_gap.tooltip': 'Aanbevolen: 1.0s. Minimale afstand tussen clips om overlap te voorkomen',
        'clip_settings.advanced.quality.tooltip': 'Bepaalt hoe zorgvuldig de AI clips selecteert. Precies duurt langer maar geeft betere resultaten'
      },
      'en': {
        'clip_settings.advanced.max_moments.tooltip': 'Recommended: 6 clips. More clips = more choice, fewer clips = better quality per clip',
        'clip_settings.advanced.min_gap.tooltip': 'Recommended: 1.0s. Minimum distance between clips to prevent overlap',
        'clip_settings.advanced.quality.tooltip': 'Determines how carefully AI selects clips. Precise takes longer but gives better results'
      },
      'es': {
        'clip_settings.advanced.max_moments.tooltip': 'Recomendado: 6 clips. Más clips = más opciones, menos clips = mejor calidad por clip',
        'clip_settings.advanced.min_gap.tooltip': 'Recomendado: 1.0s. Distancia mínima entre clips para evitar superposición',
        'clip_settings.advanced.quality.tooltip': 'Determina qué tan cuidadosamente la IA selecciona clips. Preciso toma más tiempo pero da mejores resultados'
      },
      'fr': {
        'clip_settings.advanced.max_moments.tooltip': 'Recommandé: 6 clips. Plus de clips = plus de choix, moins de clips = meilleure qualité par clip',
        'clip_settings.advanced.min_gap.tooltip': 'Recommandé: 1.0s. Distance minimale entre clips pour éviter le chevauchement',
        'clip_settings.advanced.quality.tooltip': 'Détermine avec quelle attention l\'IA sélectionne les clips. Précis prend plus de temps mais donne de meilleurs résultats'
      }
    };
  }

  updateAllTooltips() {
    // Update any currently visible tooltip
    if (this.currentTooltip) {
      const activeIcon = document.querySelector('.info-icon:hover, .info-icon:focus');
      if (activeIcon) {
        const tooltipKey = this.tooltips.get(activeIcon);
        if (tooltipKey) {
          const newText = this.getTranslatedTooltip(tooltipKey);
          if (newText) {
            this.currentTooltip.textContent = newText;
          }
        }
      }
    }
  }

  // Public method to add new tooltips dynamically
  addTooltip(iconElement, tooltipKey) {
    if (this.tooltips.has(iconElement)) return;

    iconElement.addEventListener('mouseenter', (e) => this.showTooltip(e.target, tooltipKey));
    iconElement.addEventListener('mouseleave', () => this.hideTooltip());
    iconElement.addEventListener('focus', (e) => this.showTooltip(e.target, tooltipKey));
    iconElement.addEventListener('blur', () => this.hideTooltip());

    this.tooltips.set(iconElement, tooltipKey);
  }

  // Public method to remove tooltips
  removeTooltip(iconElement) {
    if (this.tooltips.has(iconElement)) {
      // Remove event listeners would require stored references
      // For now, just remove from map
      this.tooltips.delete(iconElement);
    }
  }
}

// Initialize tooltip manager
let tooltipManager;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    tooltipManager = new TooltipManager();
    window.tooltipManager = tooltipManager; // Make globally available
  });
} else {
  tooltipManager = new TooltipManager();
  window.tooltipManager = tooltipManager;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TooltipManager;
}