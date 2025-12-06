/**
 * Compact Processing Timer Component
 * Simple, elegant timer that matches the UI style
 */
class ProcessingTimer {
  constructor(container, options = {}) {
    this.container = container;
    this.startTime = null;
    this.timer = null;
    this.options = {
      showEstimation: options.showEstimation !== false,
      ...options
    };

    this.phases = [
      { name: 'analyzing', label: 'Analyzing video...', duration: 45 },
      { name: 'extracting', label: 'Finding best moments...', duration: 90 },
      { name: 'creating', label: 'Creating clips...', duration: 30 }
    ];

    this.currentPhase = 0;
    this.init();
  }

  init() {
    this.render();
  }

  render() {
    this.container.innerHTML = `
      <div class="timer-display">
        <span class="timer-icon">⏱️</span>
        <span class="timer-text" id="timerText">00:00</span>
        <span class="timer-message" id="timerMessage">Starting video analysis...</span>
      </div>
    `;
  }

  start() {
    this.startTime = Date.now();
    this.currentPhase = 0;
    this.updateDisplay();

    this.timer = setInterval(() => {
      this.updateDisplay();
      this.updatePhase();
    }, 1000);
  }

  updateDisplay() {
    if (!this.startTime) return;

    const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;

    const timeDisplay = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

    const timerText = document.getElementById('timerText');
    if (timerText) {
      timerText.textContent = timeDisplay;
    }
  }

  updatePhase() {
    const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
    const timerMessage = document.getElementById('timerMessage');

    if (!timerMessage) return;

    let message = '';
    if (elapsed < 30) {
      message = 'Starting video analysis...';
    } else if (elapsed < 60) {
      message = 'AI is analyzing your content...';
    } else if (elapsed < 120) {
      message = 'Finding best moments...';
    } else if (elapsed < 180) {
      message = 'Creating clips...';
    } else {
      message = 'Almost done, finalizing...';
    }

    timerMessage.textContent = message;
  }

  complete() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }

    const timerMessage = document.getElementById('timerMessage');
    if (timerMessage) {
      timerMessage.textContent = '✅ Processing completed!';
    }
  }

  stop() {
    this.complete();
  }

  destroy() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}

// Make available globally
window.ProcessingTimer = ProcessingTimer;