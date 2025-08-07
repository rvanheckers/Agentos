/**
 * SmartFilter - Modulaire filtering component
 * Herbruikbaar voor alle admin views die filtering nodig hebben
 */

export class SmartFilter {
  constructor(options) {
    this.filterTypes = options.filterTypes || {};
    this.presets = options.presets || {};
    this.onFilterChange = options.onFilterChange || (() => {});
    this.currentFilter = options.defaultFilter || 'default';
    this.container = null;
    this.searchTimeout = null;
  }

  init(container) {
    this.container = container;
    this.render();
    this.setupEventListeners();
    this.setupStickyBehavior();
  }

  render() {
    const presetsHTML = Object.entries(this.presets).map(([key, preset]) => `
      <button class="filter-preset ${this.currentFilter === key ? 'filter-preset--active' : ''}" 
              data-preset="${key}">
        ${preset.icon || ''} ${preset.label}
      </button>
    `).join('');

    this.container.innerHTML = `
      <div class="smart-filter">
        <!-- Quick Filters Section -->
        <div class="quick-filters">
          <div class="quick-filters__header">
            <h3 class="quick-filters__title">
              Quick Filters
            </h3>
            <button class="btn btn-sm btn-ghost" id="clearAllFilters">
              Clear All
            </button>
          </div>
          <div class="quick-filters__presets">
            ${presetsHTML}
          </div>
        </div>

        <!-- Search & Filter Section (only show if filterTypes are defined) -->
        ${Object.keys(this.filterTypes).length > 0 ? `
        <div class="search-filter">
          <div class="search-filter__header">
            <h3 class="search-filter__title">Search & Filter</h3>
            <button class="btn btn-sm btn-link" id="toggleAdvanced">
              Advanced
            </button>
          </div>
          
          <div class="search-filter__controls">
            <div class="search-control">
              <input type="text" 
                     class="search-input" 
                     id="searchInput"
                     placeholder="Search services..."
                     autocomplete="off">
              <button class="search-clear" id="clearSearch" style="display: none;">
                ✕
              </button>
            </div>
          </div>

          <!-- Basic Filter Controls -->
          <div class="basic-filters">
            <h4 class="basic-filters__title">Filter Controls</h4>
            <div class="filter-dropdowns">
              ${this.renderStatusFilter()}
              ${this.renderDateFilter()}
              ${this.renderSortFilter()}
            </div>
          </div>

          <!-- Advanced Filters (Hidden by default) -->
          <div class="advanced-filters" id="advancedFilters" style="display: none;">
            <h4 class="advanced-filters__title">Advanced Filters</h4>
            ${this.renderAdvancedFilters()}
          </div>
        </div>
        ` : ''}

        <!-- Results Info & Actions (only show if filterTypes are defined) -->
        ${Object.keys(this.filterTypes).length > 0 ? `
        <div class="filter-results">
          <div class="results-info">
            <span class="results-count" id="resultsCount">Loading...</span>
          </div>
          <div class="results-actions">
            <button class="btn btn-sm btn-outline" id="exportResults">
              📤 Export
            </button>
            <button class="btn btn-sm btn-outline" id="refreshResults">
              🔄 Refresh
            </button>
          </div>
        </div>
        ` : ''}
      </div>
    `;
  }

  renderStatusFilter() {
    // Context-aware status options based on current filter/preset
    let statusOptions = [];
    
    if (this.currentFilter === 'live-queue') {
      // Live Queue: only show active job statuses
      statusOptions = [
        { value: 'all', label: 'All Active' },
        { value: 'queued', label: 'Queued' },
        { value: 'processing', label: 'Processing' },
        { value: 'pending', label: 'Pending' }
      ];
    } else if (this.currentFilter === 'job-history') {
      // Job History: only show historical/completed job statuses
      statusOptions = [
        { value: 'all', label: 'All History' },
        { value: 'completed', label: 'Completed' },
        { value: 'failed', label: 'Failed' },
        { value: 'cancelled', label: 'Cancelled' }
      ];
    } else if (this.currentFilter === 'alerts') {
      // Alerts: focus on problem statuses  
      statusOptions = [
        { value: 'all', label: 'All Issues' },
        { value: 'failed', label: 'Failed' },
        { value: 'cancelled', label: 'Cancelled' },
        { value: 'processing', label: 'Stuck Processing' }
      ];
    } else {
      // Default: comprehensive list
      statusOptions = this.filterTypes.statusOptions || [
        { value: 'all', label: 'All Status' },
        { value: 'queued', label: 'Queued' },
        { value: 'processing', label: 'Processing' },
        { value: 'pending', label: 'Pending' },
        { value: 'completed', label: 'Completed' },
        { value: 'failed', label: 'Failed' }
      ];
    }

    return `
      <div class="filter-dropdown">
        <label class="filter-dropdown__label">STATUS</label>
        <select class="filter-dropdown__select" id="statusFilter">
          ${statusOptions.map(option => `
            <option value="${option.value}">${option.label}</option>
          `).join('')}
        </select>
      </div>
    `;
  }

  renderDateFilter() {
    const dateOptions = this.filterTypes.dateOptions || [
      { value: 'all', label: 'All Time' },
      { value: 'today', label: 'Today' },
      { value: 'yesterday', label: 'Yesterday' },
      { value: 'week', label: 'This Week' },
      { value: 'month', label: 'This Month' },
      { value: 'custom', label: 'Custom Range' }
    ];

    return `
      <div class="filter-dropdown">
        <label class="filter-dropdown__label">DATE RANGE</label>
        <select class="filter-dropdown__select" id="dateFilter">
          ${dateOptions.map(option => `
            <option value="${option.value}">${option.label}</option>
          `).join('')}
        </select>
      </div>
    `;
  }

  renderSortFilter() {
    const sortOptions = this.filterTypes.sortOptions || [
      { value: 'recent', label: 'Most Recent' },
      { value: 'oldest', label: 'Oldest First' },
      { value: 'status', label: 'By Status' },
      { value: 'progress', label: 'By Progress' }
    ];

    return `
      <div class="filter-dropdown">
        <label class="filter-dropdown__label">SORT BY</label>
        <select class="filter-dropdown__select" id="sortFilter">
          ${sortOptions.map(option => `
            <option value="${option.value}">${option.label}</option>
          `).join('')}
        </select>
      </div>
    `;
  }

  renderAdvancedFilters() {
    return `
      <div class="advanced-filter-grid">
        <div class="advanced-filter-group">
          <h5 class="filter-group-title">📊 Performance Filters</h5>
          <div class="advanced-filter-item">
            <label class="filter-dropdown__label">Progress Range</label>
            <div class="range-inputs">
              <input type="number" id="progressMin" placeholder="Min %" min="0" max="100" class="range-input">
              <span class="range-separator">to</span>
              <input type="number" id="progressMax" placeholder="Max %" min="0" max="100" class="range-input">
            </div>
          </div>

          <div class="advanced-filter-item">
            <label class="filter-dropdown__label">Duration</label>
            <select id="durationFilter" class="filter-dropdown__select">
              <option value="all">Any Duration</option>
              <option value="fast">< 2 minutes</option>
              <option value="normal">2-10 minutes</option>
              <option value="slow"> > 10 minutes</option>
            </select>
          </div>
        </div>

        <div class="advanced-filter-group">
          <h5 class="filter-group-title">👤 User & System Filters</h5>
          <div class="advanced-filter-item">
            <label class="filter-dropdown__label">User ID</label>
            <input type="text" id="userIdFilter" placeholder="Filter by user..." class="filter-input">
          </div>

          <div class="advanced-filter-item">
            <label class="filter-dropdown__label">Retry Count</label>
            <select id="retryCountFilter" class="filter-dropdown__select">
              <option value="all">Any</option>
              <option value="0">No Retries</option>
              <option value="1+">1+ Retries</option>
              <option value="3+">3+ Retries</option>
            </select>
          </div>
        </div>
      </div>
    `;
  }

  setupEventListeners() {
    // Preset buttons
    this.container.addEventListener('click', (e) => {
      if (e.target.classList.contains('filter-preset')) {
        this.applyPreset(e.target.dataset.preset);
      }
    });

    // Search input with debouncing
    const searchInput = this.container.querySelector('#searchInput');
    searchInput?.addEventListener('input', (e) => {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.applyFilter({ search: e.target.value });
        this.toggleClearSearch(e.target.value);
      }, 300);
    });

    // Clear search
    this.container.querySelector('#clearSearch')?.addEventListener('click', () => {
      searchInput.value = '';
      this.applyFilter({ search: '' });
      this.toggleClearSearch('');
    });

    // Filter dropdowns
    this.container.addEventListener('change', (e) => {
      if (e.target.classList.contains('filter-dropdown__select')) {
        this.handleFilterChange();
      }
    });

    // Advanced filters toggle
    this.container.querySelector('#toggleAdvanced')?.addEventListener('click', () => {
      this.toggleAdvancedFilters();
    });

    // Clear all filters
    this.container.querySelector('#clearAllFilters')?.addEventListener('click', () => {
      this.clearAllFilters();
    });

    // Export and refresh
    this.container.querySelector('#exportResults')?.addEventListener('click', () => {
      this.exportResults();
    });

    this.container.querySelector('#refreshResults')?.addEventListener('click', () => {
      this.refreshResults();
    });

    // Advanced filter inputs
    this.container.addEventListener('input', (e) => {
      if (e.target && e.target.closest && e.target.closest('.advanced-filters')) {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
          this.handleFilterChange();
        }, 500);
      }
    });
  }

  applyPreset(presetKey) {
    this.currentFilter = presetKey;
    const preset = this.presets[presetKey];
    
    // Update UI
    this.container.querySelectorAll('.filter-preset').forEach(btn => {
      btn.classList.toggle('filter-preset--active', btn.dataset.preset === presetKey);
    });

    // Re-render the filter controls to show context-appropriate options
    this.rerenderFilterControls();

    // Apply preset filters - pass the complete preset data including custom criteria
    if (preset && preset.filter) {
      // Pass the preset filter data directly to preserve custom criteria like responseTime: '>500'
      this.onFilterChange({
        preset: presetKey,
        filter: preset.filter,
        ...preset.filter
      });
    }
  }

  setActivePreset(presetKey) {
    // Just update UI without triggering filter change
    this.currentFilter = presetKey;
    if (this.container) {
      this.container.querySelectorAll('.filter-preset').forEach(btn => {
        btn.classList.toggle('filter-preset--active', btn.dataset.preset === presetKey);
      });
    }
  }

  applyFilter(filterData) {
    // Update the form values to reflect the filter data
    this.updateFormValues(filterData);
    
    const fullFilter = this.buildFilterObject(filterData);
    this.onFilterChange(fullFilter);
  }

  buildFilterObject(additionalFilters = {}) {
    const filter = {
      search: this.container.querySelector('#searchInput')?.value || '',
      status: this.container.querySelector('#statusFilter')?.value || 'all',
      dateRange: this.container.querySelector('#dateFilter')?.value || 'all',
      sortBy: this.container.querySelector('#sortFilter')?.value || 'recent',
      ...additionalFilters
    };

    // Add advanced filters if visible
    const advancedVisible = this.container.querySelector('#advancedFilters')?.style.display !== 'none';
    if (advancedVisible) {
      filter.progressMin = this.container.querySelector('#progressMin')?.value || null;
      filter.progressMax = this.container.querySelector('#progressMax')?.value || null;
      filter.userId = this.container.querySelector('#userIdFilter')?.value || '';
      filter.retryCount = this.container.querySelector('#retryCountFilter')?.value || 'all';
      filter.duration = this.container.querySelector('#durationFilter')?.value || 'all';
    }

    return filter;
  }

  handleFilterChange() {
    // Don't automatically set to 'custom' and remove active state
    // This will be handled by the parent component if needed
    const filter = this.buildFilterObject();
    this.onFilterChange(filter);
  }

  toggleAdvancedFilters() {
    const advancedDiv = this.container.querySelector('#advancedFilters');
    const toggleBtn = this.container.querySelector('#toggleAdvanced');
    const isVisible = advancedDiv.style.display !== 'none';

    if (isVisible) {
      advancedDiv.style.display = 'none';
      toggleBtn.innerHTML = '⚙️ Advanced';
    } else {
      advancedDiv.style.display = 'block';
      toggleBtn.innerHTML = '⚙️ Hide Advanced';
    }
  }

  toggleClearSearch(value) {
    const clearBtn = this.container.querySelector('#clearSearch');
    if (clearBtn) {
      clearBtn.style.display = value ? 'block' : 'none';
    }
  }

  clearAllFilters() {
    // Reset all inputs
    this.container.querySelector('#searchInput').value = '';
    this.container.querySelector('#statusFilter').value = 'all';
    this.container.querySelector('#dateFilter').value = 'all';
    this.container.querySelector('#sortFilter').value = 'recent';

    // Reset advanced filters
    this.container.querySelectorAll('.advanced-filters input, .advanced-filters select').forEach(input => {
      if (input.type === 'number' || input.type === 'text') {
        input.value = '';
      } else {
        input.value = input.querySelector('option')?.value || '';
      }
    });

    // Apply default preset
    this.applyPreset(Object.keys(this.presets)[0] || 'default');
  }


  updateResultsCount(count, total, context = {}) {
    const countEl = this.container.querySelector('#resultsCount');
    if (!countEl) return;
    
    const { 
      currentTab = 'unknown', 
      totalJobs = total,
      activeJobs = 0,
      completedJobs = 0,
      hasFilters = false 
    } = context;
    
    let message = '';
    
    // Generate context-aware messaging
    if (count === 0) {
      // Empty state messaging
      switch(currentTab) {
        case 'live-queue':
          message = activeJobs === 0 
            ? `No active jobs • ${completedJobs} completed jobs available in Job History`
            : `No jobs match current filters • ${activeJobs} active jobs total`;
          break;
        case 'job-history':
          message = completedJobs === 0
            ? `No completed jobs • ${activeJobs} active jobs in Live Queue`
            : `No jobs match current filters • ${completedJobs} completed jobs total`;
          break;
        case 'performance':
          message = `No data for performance analysis • ${totalJobs} total jobs available`;
          break;
        case 'alerts':
          message = `No alerts generated • ${totalJobs} jobs monitored`;
          break;
        default:
          message = `No results found • ${totalJobs} total jobs available`;
      }
    } else {
      // Results found messaging
      switch(currentTab) {
        case 'live-queue':
          const suffix = hasFilters ? ` filtered from ${activeJobs} active jobs` : ` active job${count > 1 ? 's' : ''}`;
          message = `${count}${suffix} • ${totalJobs} total jobs`;
          break;
        case 'job-history':
          const historySuffix = hasFilters ? ` filtered from ${completedJobs} completed jobs` : ` completed job${count > 1 ? 's' : ''}`;
          message = `${count}${historySuffix} • ${totalJobs} total jobs`;
          break;
        case 'performance':
          message = `${count} jobs analyzed • Performance data available`;
          break;
        case 'alerts':
          message = `${count} alert${count > 1 ? 's' : ''} • ${totalJobs} jobs monitored`;
          break;
        default:
          message = `${count} of ${totalJobs} jobs`;
      }
    }
    
    countEl.innerHTML = `
      <div class="results-info">
        <span class="results-message">${message}</span>
        ${count > 0 ? `<span class="results-count">(${count.toLocaleString()})</span>` : ''}
      </div>
    `;
  }

  exportResults() {
    // Trigger export functionality
    console.log('Export requested with current filter:', this.buildFilterObject());
    
    // Call the onFilterChange callback with a special export action
    if (this.onFilterChange) {
      this.onFilterChange({
        action: 'export',
        filter: this.buildFilterObject()
      });
    }
  }

  refreshResults() {
    const filter = this.buildFilterObject();
    this.onFilterChange({ ...filter, forceRefresh: true });
  }

  getCurrentFilter() {
    return this.buildFilterObject();
  }

  updateActiveButton() {
    // Update the visual active state of preset buttons
    this.container.querySelectorAll('.filter-preset').forEach(btn => {
      btn.classList.remove('filter-preset--active');
    });
    
    // Set the active button based on currentFilter
    const activeBtn = this.container.querySelector(`[data-preset="${this.currentFilter}"]`);
    if (activeBtn) {
      activeBtn.classList.add('filter-preset--active');
    }
  }

  rerenderFilterControls() {
    // Re-render the filter dropdowns section with context-appropriate options
    const filterDropdownsContainer = this.container.querySelector('.filter-dropdowns');
    if (filterDropdownsContainer) {
      // Save current values before re-rendering
      const currentValues = {
        status: this.container.querySelector('#statusFilter')?.value || 'all',
        dateRange: this.container.querySelector('#dateFilter')?.value || 'all',
        sortBy: this.container.querySelector('#sortFilter')?.value || 'recent'
      };
      
      // Re-render with context-appropriate options
      filterDropdownsContainer.innerHTML = `
        ${this.renderStatusFilter()}
        ${this.renderDateFilter()}
        ${this.renderSortFilter()}
      `;
      
      // Re-attach event listeners
      this.attachDropdownListeners();
      
      // Restore values where applicable
      if (this.container.querySelector('#statusFilter')) {
        const statusSelect = this.container.querySelector('#statusFilter');
        // Only restore if the option exists in the new context
        if (Array.from(statusSelect.options).some(opt => opt.value === currentValues.status)) {
          statusSelect.value = currentValues.status;
        }
      }
      
      if (this.container.querySelector('#dateFilter')) {
        this.container.querySelector('#dateFilter').value = currentValues.dateRange;
      }
      
      if (this.container.querySelector('#sortFilter')) {
        this.container.querySelector('#sortFilter').value = currentValues.sortBy;
      }
    }
  }
  
  attachDropdownListeners() {
    // Re-attach event listeners to dropdowns after re-render
    this.container.querySelectorAll('.filter-dropdown__select').forEach(select => {
      select.addEventListener('change', () => this.handleFilterChange());
    });
  }

  updateFormValues(filterData) {
    // Update form elements to match the filter data
    if (!this.container || !filterData) return;

    // Update search input
    if (filterData.search !== undefined) {
      const searchInput = this.container.querySelector('#searchInput');
      if (searchInput) {
        searchInput.value = filterData.search;
        this.toggleClearSearch(filterData.search);
      }
    }

    // Update status dropdown
    if (filterData.status !== undefined) {
      const statusSelect = this.container.querySelector('#statusFilter');
      if (statusSelect) {
        // Handle both single values and arrays
        let statusValue = filterData.status;
        if (Array.isArray(statusValue)) {
          // For Live Queue with ['queued', 'processing', 'pending'], show 'queued'
          // For other arrays, show 'all' if multiple values
          statusValue = statusValue.length === 1 ? statusValue[0] : 
                       (statusValue.includes('queued') && statusValue.includes('processing')) ? 'queued' : 'all';
        }
        statusSelect.value = statusValue;
      }
    }

    // Update date range dropdown
    if (filterData.dateRange !== undefined) {
      const dateSelect = this.container.querySelector('#dateFilter');
      if (dateSelect) {
        dateSelect.value = filterData.dateRange;
      }
    }

    // Update sort dropdown
    if (filterData.sortBy !== undefined) {
      const sortSelect = this.container.querySelector('#sortFilter');
      if (sortSelect) {
        sortSelect.value = filterData.sortBy;
      }
    }

    // Update advanced filters if present
    if (filterData.userId !== undefined) {
      const userIdInput = this.container.querySelector('#userIdFilter');
      if (userIdInput) userIdInput.value = filterData.userId;
    }

    if (filterData.progressMin !== undefined) {
      const progressMinInput = this.container.querySelector('#progressMin');
      if (progressMinInput) progressMinInput.value = filterData.progressMin;
    }

    if (filterData.progressMax !== undefined) {
      const progressMaxInput = this.container.querySelector('#progressMax');
      if (progressMaxInput) progressMaxInput.value = filterData.progressMax;
    }

    if (filterData.retryCount !== undefined) {
      const retrySelect = this.container.querySelector('#retryCountFilter');
      if (retrySelect) retrySelect.value = filterData.retryCount;
    }

    if (filterData.duration !== undefined) {
      const durationSelect = this.container.querySelector('#durationFilter');
      if (durationSelect) durationSelect.value = filterData.duration;
    }
  }

  setupStickyBehavior() {
    // DISABLED: Sticky behavior causes scroll conflicts - keep filter in normal flow
    const filterElement = this.container.querySelector('.smart-filter');
    if (!filterElement) return;
    
    console.log('🔧 Sticky behavior disabled to prevent scroll conflicts');
    
    // No sticky behavior - just store reference for cleanup
    this.filterElement = filterElement;
    
    // Store empty handler for cleanup
    this.scrollHandler = null;
    
    console.log('🔧 Sticky behavior disabled - normal scroll flow maintained');
  }

  destroy() {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
    
    // Cleanup scroll listener and reset element
    if (this.scrollHandler) {
      window.removeEventListener('scroll', this.scrollHandler);
    }
    
    // Reset sticky element to normal state
    if (this.filterElement) {
      this.filterElement.style.position = 'static';
      this.filterElement.style.top = 'auto';
      this.filterElement.style.left = 'auto';
      this.filterElement.style.right = 'auto';
      this.filterElement.style.zIndex = 'auto';
    }
  }
}