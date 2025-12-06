/**
 * Moment Selector Component
 * Displays detected moments and allows user selection
 */

export class MomentSelector {
    constructor(jobId, apiBaseUrl = '/api') {
        this.jobId = jobId;
        this.apiBaseUrl = apiBaseUrl;
        this.moments = [];
        this.selectedIndices = new Set();
        this.container = null;
    }

    /**
     * Fetch moments from API
     */
    async fetchMoments() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/jobs/${this.jobId}/moments`);

            if (!response.ok) {
                if (response.status === 400) {
                    // Job not ready yet
                    return { ready: false, message: 'Moments not ready yet. Phase 1 still running...' };
                }
                if (response.status === 403) {
                    throw new Error('Not authorized to access this job');
                }
                if (response.status === 404) {
                    throw new Error('Job not found or moments not available yet');
                }
                throw new Error(`Failed to fetch moments: ${response.statusText}`);
            }

            const data = await response.json();

            // Handle both direct response and wrapped response formats
            const momentsData = data.data || data;

            this.moments = momentsData.moments || [];
            return { ready: true, data: momentsData };
        } catch (error) {
            console.error('Error fetching moments:', error);
            throw error;
        }
    }

    /**
     * Toggle moment selection
     */
    toggleMoment(momentIndex) {
        if (this.selectedIndices.has(momentIndex)) {
            this.selectedIndices.delete(momentIndex);
        } else {
            this.selectedIndices.add(momentIndex);
        }
        // Only update the UI elements that need updating (don't re-render checkboxes)
        this.updateUIState();
    }

    /**
     * Select all moments
     */
    selectAll() {
        this.moments.forEach(m => this.selectedIndices.add(m.moment_index));
        this.updateUIComplete();
    }

    /**
     * Clear all selections
     */
    clearAll() {
        this.selectedIndices.clear();
        this.updateUIComplete();
    }

    /**
     * Generate clips for selected moments
     */
    async generateClips() {
        if (this.selectedIndices.size === 0) {
            this.showNotification('Please select at least one moment', 'warning');
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/jobs/${this.jobId}/generate-clips`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selected_moments: Array.from(this.selectedIndices)
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to generate clips');
            }

            const result = await response.json();
            const resultData = result.data || result;

            this.showNotification(
                `Started generating ${this.selectedIndices.size} clips!`,
                'success'
            );

            return resultData;
        } catch (error) {
            console.error('Error generating clips:', error);
            this.showNotification(error.message, 'error');
            throw error;
        }
    }

    /**
     * Render moment selector UI
     */
    render() {
        const container = document.createElement('div');
        container.className = 'moment-selector';
        container.innerHTML = `
            <div class="moment-selector-header">
                <h2>📊 Found ${this.moments.length} Viral Moments</h2>
                <p>Select which clips you want to generate:</p>
            </div>

            <div class="moment-list" id="moment-list">
                ${this.renderMoments()}
            </div>

            <div class="moment-selector-footer">
                <div class="selection-info">
                    Selected: <strong id="selected-count">0</strong> of ${this.moments.length} moments
                </div>
                <div class="action-buttons">
                    <button id="select-all-btn" class="btn btn-secondary">Select All</button>
                    <button id="clear-all-btn" class="btn btn-secondary">Clear</button>
                    <button id="generate-btn" class="btn btn-primary" disabled>
                        Generate Selected Clips
                    </button>
                </div>
            </div>
        `;

        this.container = container;
        this.attachEventListeners(container);
        return container;
    }

    /**
     * Render individual moment cards
     */
    renderMoments() {
        if (!this.moments || this.moments.length === 0) {
            return '<div class="no-moments">No moments found.</div>';
        }

        return this.moments.map(moment => `
            <div class="moment-card ${this.selectedIndices.has(moment.moment_index) ? 'selected' : ''}"
                 data-index="${moment.moment_index}">
                <div class="moment-checkbox">
                    <input
                        type="checkbox"
                        id="moment-${moment.moment_index}"
                        data-index="${moment.moment_index}"
                        ${this.selectedIndices.has(moment.moment_index) ? 'checked' : ''}
                    >
                </div>
                <div class="moment-content">
                    <div class="moment-header">
                        <label for="moment-${moment.moment_index}" class="moment-title">
                            Moment ${moment.moment_index + 1}
                        </label>
                        <span class="moment-timing">
                            ${this.formatTime(moment.start_time)} - ${this.formatTime(moment.end_time)}
                        </span>
                    </div>
                    <div class="moment-score">
                        🔥 Viral Score: <strong>${moment.viral_score || 'N/A'}</strong>
                    </div>
                    <div class="moment-description">
                        ${moment.description || 'No description available'}
                    </div>
                    ${moment.sentence_text ? `
                        <div class="moment-text">
                            "${moment.sentence_text}"
                        </div>
                    ` : ''}
                    ${moment.keywords && Array.isArray(moment.keywords) && moment.keywords.length > 0 ? `
                        <div class="moment-keywords">
                            ${moment.keywords.map(k => `<span class="keyword-tag">${k}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * Format seconds to MM:SS
     */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners(container) {
        // Checkbox change events
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.toggleMoment(index);
            });
        });

        // Card click to toggle (except when clicking checkbox)
        container.querySelectorAll('.moment-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't toggle if clicking the checkbox itself
                if (e.target.type === 'checkbox' || e.target.tagName === 'LABEL') {
                    return;
                }
                const index = parseInt(card.dataset.index);
                const checkbox = card.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                this.toggleMoment(index);
            });
        });

        // Select All button
        const selectAllBtn = container.querySelector('#select-all-btn');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                this.selectAll();
            });
        }

        // Clear button
        const clearAllBtn = container.querySelector('#clear-all-btn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => {
                this.clearAll();
            });
        }

        // Generate button
        const generateBtn = container.querySelector('#generate-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', async (e) => {
                e.preventDefault(); // Prevent any default form behavior
                e.stopPropagation(); // Stop event bubbling

                generateBtn.disabled = true;
                generateBtn.textContent = 'Generating...';

                try {
                    await this.generateClips();

                    // Show success message without reloading
                    this.showSuccessMessage(this.selectedIndices.size);

                    // Disable further interactions
                    this.disableSelection();
                } catch (error) {
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Selected Clips';
                }
            });
        }
    }

    /**
     * Update UI state only (count and button) - used during checkbox clicks to avoid conflicts
     */
    updateUIState() {
        if (!this.container) return;

        // Update selected count
        const countEl = this.container.querySelector('#selected-count');
        if (countEl) {
            countEl.textContent = this.selectedIndices.size;
        }

        // Update generate button state
        const generateBtn = this.container.querySelector('#generate-btn');
        if (generateBtn) {
            generateBtn.disabled = this.selectedIndices.size === 0;
        }

        // Update card selected class (visual feedback)
        this.container.querySelectorAll('.moment-card').forEach(card => {
            const index = parseInt(card.dataset.index);
            if (this.selectedIndices.has(index)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    }

    /**
     * Complete UI update including checkboxes - used for Select All / Clear All
     */
    updateUIComplete() {
        if (!this.container) return;

        // Update selected count
        const countEl = this.container.querySelector('#selected-count');
        if (countEl) {
            countEl.textContent = this.selectedIndices.size;
        }

        // Update generate button state
        const generateBtn = this.container.querySelector('#generate-btn');
        if (generateBtn) {
            generateBtn.disabled = this.selectedIndices.size === 0;
        }

        // Update checkboxes
        this.container.querySelectorAll('input[type="checkbox"][data-index]').forEach(checkbox => {
            const index = parseInt(checkbox.dataset.index);
            checkbox.checked = this.selectedIndices.has(index);
        });

        // Update card selected class
        this.container.querySelectorAll('.moment-card').forEach(card => {
            const index = parseInt(card.dataset.index);
            if (this.selectedIndices.has(index)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    }

    /**
     * Show success message after generating clips
     */
    showSuccessMessage(clipCount) {
        if (!this.container) return;

        const footer = this.container.querySelector('.moment-selector-footer');
        if (footer) {
            footer.innerHTML = `
                <div style="background: #d4edda; border: 2px solid #28a745; border-radius: 12px; padding: 30px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 16px;">✅</div>
                    <h3 style="color: #155724; margin: 0 0 12px 0; font-size: 24px;">Clips Generation Started!</h3>
                    <p style="color: #155724; margin: 0 0 20px 0; font-size: 16px;">
                        Generating ${clipCount} clip${clipCount > 1 ? 's' : ''} from selected moments.
                    </p>
                    <p style="color: #155724; margin: 0; font-size: 14px;">
                        This process will take a few minutes. You can check progress in the main UI.
                    </p>
                    <div style="margin-top: 20px;">
                        <a href="/" style="display: inline-block; background: #28a745; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500;">
                            ← Back to Main UI
                        </a>
                    </div>
                </div>
            `;
        }
    }

    /**
     * Disable selection after clips are generated
     */
    disableSelection() {
        if (!this.container) return;

        // Disable all checkboxes
        this.container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.disabled = true;
        });

        // Disable all cards
        this.container.querySelectorAll('.moment-card').forEach(card => {
            card.style.opacity = '0.6';
            card.style.pointerEvents = 'none';
        });
    }

    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#fff3cd'};
            color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#856404'};
            padding: 16px 24px;
            border-radius: 8px;
            border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#ffeaa7'};
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;

        document.body.appendChild(notification);

        // Auto remove after 4 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.MomentSelector = MomentSelector;
}

export default MomentSelector;
