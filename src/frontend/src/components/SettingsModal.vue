<template>
  <div v-if="show" class="modal-overlay active" @click="closeModal">
    <div class="modal macos-settings-modal" @click.stop>
      <!-- macOS-style title bar -->
      <div class="macos-titlebar">
        <div class="titlebar-controls">
          <button class="titlebar-btn close" @click="closeModal"></button>
          <button class="titlebar-btn minimize"></button>
          <button class="titlebar-btn maximize"></button>
        </div>
        <div class="titlebar-title">Settings</div>
        <div class="titlebar-spacer"></div>
      </div>
      
      <!-- macOS-style sidebar + content layout -->
      <div class="macos-content">
        <!-- Sidebar navigation -->
        <div class="macos-sidebar">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="sidebar-item"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path :d="tab.icon" />
            </svg>
            <span class="sidebar-label">{{ tab.label }}</span>
          </button>
        </div>
        
        <!-- Settings content area -->
        <div class="macos-main">
          <!-- General Tab -->
          <div v-if="activeTab === 'general'" class="settings-panel">
            <h2 class="panel-title">General</h2>
            
            <div class="setting-group">
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Appearance</div>
                  <div class="setting-desc">Choose dark or light mode</div>
                </div>
                <label class="setting-control toggle">
                  <input
                    v-model="localSettings.general.dark_mode"
                    type="checkbox"
                    class="toggle-input"
                  />
                  <span class="toggle-slider"></span>
                  <span class="toggle-label">{{ localSettings.general.dark_mode ? 'Dark' : 'Light' }}</span>
                </label>
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Color Blind Mode</div>
                  <div class="setting-desc">Use colorblind-friendly palette (Okabe-Ito)</div>
                </div>
                <label class="setting-control toggle">
                  <input
                    v-model="localSettings.general.color_blind_mode"
                    type="checkbox"
                    class="toggle-input"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
            
            <div class="setting-group">
              <div class="setting-group-title">Data Management</div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Save Negotiations</div>
                  <div class="setting-desc">Automatically save negotiations to disk</div>
                </div>
                <label class="setting-control toggle">
                  <input
                    v-model="localSettings.general.save_negotiations"
                    type="checkbox"
                    class="toggle-input"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Cache Scenario Statistics</div>
                  <div class="setting-desc">Automatically cache computed scenario statistics</div>
                </div>
                <label class="setting-control toggle">
                  <input
                    v-model="localSettings.general.cache_scenario_stats"
                    type="checkbox"
                    class="toggle-input"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>
          
          <!-- Negotiation Tab -->
          <div v-if="activeTab === 'negotiation'" class="settings-panel">
            <h2 class="panel-title">Negotiation</h2>
            
            <div class="setting-group">
              <div class="setting-group-title">Default Parameters</div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Maximum Steps</div>
                  <div class="setting-desc">Default maximum number of negotiation steps</div>
                </div>
                <input
                  v-model.number="localSettings.negotiation.default_max_steps"
                  type="number"
                  min="1"
                  class="setting-input number"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Step Delay</div>
                  <div class="setting-desc">Delay between steps when streaming (milliseconds)</div>
                </div>
                <input
                  v-model.number="localSettings.negotiation.default_step_delay_ms"
                  type="number"
                  min="0"
                  step="50"
                  class="setting-input number"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Time Limit</div>
                  <div class="setting-desc">Default time limit for negotiations (seconds, 0 = no limit)</div>
                </div>
                <input
                  v-model.number="localSettings.negotiation.default_time_limit"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="No limit"
                />
              </div>
            </div>
          </div>
          
          <!-- Genius Bridge Tab -->
          <div v-if="activeTab === 'genius'" class="settings-panel">
            <h2 class="panel-title">Genius Bridge</h2>
            
            <div class="setting-group">
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Auto-start Bridge</div>
                  <div class="setting-desc">Automatically start Genius bridge when needed</div>
                </div>
                <label class="setting-control toggle">
                  <input
                    v-model="localSettings.genius_bridge.auto_start"
                    type="checkbox"
                    class="toggle-input"
                  />
                  <span class="toggle-slider"></span>
                </label>
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Java Path</div>
                  <div class="setting-desc">Path to Java executable (leave empty to auto-detect)</div>
                </div>
                <input
                  v-model="localSettings.genius_bridge.java_path"
                  type="text"
                  class="setting-input text"
                  placeholder="Auto-detect"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Bridge Port</div>
                  <div class="setting-desc">Port for Genius bridge communication</div>
                </div>
                <input
                  v-model.number="localSettings.genius_bridge.port"
                  type="number"
                  min="1024"
                  max="65535"
                  class="setting-input number"
                />
              </div>
            </div>
          </div>
          
          <!-- Performance Tab -->
          <div v-if="activeTab === 'performance'" class="settings-panel">
            <h2 class="panel-title">Performance</h2>
            
            <div class="setting-group">
              <div class="setting-group-title">Outcome Limits</div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Max Outcomes for Running</div>
                  <div class="setting-desc">Maximum outcomes for running negotiations/tournaments (0 = no limit)</div>
                </div>
                <input
                  v-model.number="localSettings.performance.max_outcomes_run"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="No limit"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Max Outcomes for Statistics</div>
                  <div class="setting-desc">Maximum outcomes for calculating scenario statistics</div>
                </div>
                <input
                  v-model.number="localSettings.performance.max_outcomes_stats"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="1000000"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Max Outcomes for Plots</div>
                  <div class="setting-desc">Maximum outcomes for generating plots with full outcome space (0 = no limit)</div>
                </div>
                <input
                  v-model.number="localSettings.performance.max_outcomes_plots"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="500000"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Max Outcomes for Pareto Frontier</div>
                  <div class="setting-desc">Maximum outcomes for showing Pareto frontier in plots (0 = no limit)</div>
                </div>
                <input
                  v-model.number="localSettings.performance.max_outcomes_pareto"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="1000000"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Max Outcomes for Rationality</div>
                  <div class="setting-desc">Maximum outcomes for calculating rationality fraction (0 = no limit)</div>
                </div>
                <input
                  v-model.number="localSettings.performance.max_outcomes_rationality"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="10000000"
                />
              </div>
            </div>
            
            <div class="setting-group">
              <div class="setting-group-title">Cache Limits</div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Max Pareto Outcomes to Save</div>
                  <div class="setting-desc">Maximum Pareto outcomes to save in cache files (0 = no limit)</div>
                </div>
                <input
                  v-model.number="localSettings.performance.max_pareto_outcomes"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="No limit"
                />
              </div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Max Pareto Utils to Save</div>
                  <div class="setting-desc">Maximum Pareto utilities to save in cache files (0 = no limit)</div>
                </div>
                <input
                  v-model.number="localSettings.performance.max_pareto_utils"
                  type="number"
                  min="0"
                  class="setting-input number"
                  placeholder="No limit"
                />
              </div>
            </div>
            
            <div class="setting-group">
              <div class="setting-group-title">Image Settings</div>
              
              <div class="setting-row">
                <div class="setting-info">
                  <div class="setting-name">Plot Image Format</div>
                  <div class="setting-desc">Format for saving plot images (webp is smallest)</div>
                </div>
                <select
                  v-model="localSettings.performance.plot_image_format"
                  class="setting-input"
                >
                  <option value="webp">WebP (Smallest, Recommended)</option>
                  <option value="png">PNG</option>
                  <option value="jpg">JPEG</option>
                  <option value="svg">SVG (Vector)</option>
                </select>
              </div>
            </div>
          </div>
          
          <!-- Paths Tab -->
          <div v-if="activeTab === 'paths'" class="settings-panel">
            <h2 class="panel-title">Paths</h2>
            
            <div class="setting-group">
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">User Scenarios Directory</div>
                  <div class="setting-desc">Directory for user-created scenarios</div>
                </div>
                <input
                  v-model="localSettings.paths.user_scenarios"
                  type="text"
                  class="setting-input text full-width"
                  placeholder="~/negmas/app/scenarios"
                />
              </div>
              
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">Additional Scenario Paths</div>
                  <div class="setting-desc">Additional directories to search for scenarios</div>
                </div>
                <div class="path-list">
                  <div
                    v-for="(path, idx) in localSettings.paths.scenario_paths"
                    :key="idx"
                    class="path-item"
                  >
                    <input
                      v-model="localSettings.paths.scenario_paths[idx]"
                      type="text"
                      class="setting-input text"
                      placeholder="/path/to/scenarios"
                    />
                    <button
                      class="btn-icon-remove"
                      @click="removePath(idx)"
                      title="Remove"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10" />
                        <line x1="15" y1="9" x2="9" y2="15" />
                        <line x1="9" y1="9" x2="15" y2="15" />
                      </svg>
                    </button>
                  </div>
                </div>
                <button class="btn-add-path" @click="addPath">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="16" />
                    <line x1="8" y1="12" x2="16" y2="12" />
                  </svg>
                  Add Path
                </button>
              </div>
            </div>
          </div>
          
          <!-- Cache Tab -->
          <div v-if="activeTab === 'cache'" class="settings-panel">
            <h2 class="panel-title">Cache Management</h2>
            
            <div class="setting-group">
              <div class="setting-group-title">Scenario Caches</div>
              
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">Cache Status</div>
                  <div class="setting-desc">Current cache file statistics</div>
                </div>
                <div v-if="cacheStatus" class="cache-stats">
                  <div class="stat-item">
                    <span class="stat-label">Total Scenarios:</span>
                    <span class="stat-value">{{ cacheStatus.total }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">With Info:</span>
                    <span class="stat-value">{{ cacheStatus.with_info }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">With Stats:</span>
                    <span class="stat-value">{{ cacheStatus.with_stats }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">With Plots:</span>
                    <span class="stat-value">{{ cacheStatus.with_plots }}</span>
                  </div>
                </div>
                <button
                  class="btn-action secondary"
                  @click="loadCacheStatus"
                  :disabled="loadingCacheStatus"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                  </svg>
                  <span v-if="loadingCacheStatus">Loading...</span>
                  <span v-else>Refresh Status</span>
                </button>
              </div>
              
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">Build Caches</div>
                  <div class="setting-desc">Generate cache files for scenarios (info, stats, or plots)</div>
                </div>
                
                <!-- Base folder selection -->
                <div class="setting-group">
                  <label class="setting-label">Base Folder</label>
                  <div class="folder-input-group">
                    <input
                      type="text"
                      v-model="cacheBuildFolder"
                      placeholder="~/negmas/app/scenarios"
                      class="folder-input"
                    />
                    <button
                      class="btn-action secondary small"
                      @click="resetCacheBuildFolder"
                      title="Reset to default"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                      </svg>
                    </button>
                  </div>
                  <div class="setting-hint">Leave empty to use default: ~/negmas/app/scenarios</div>
                </div>
                
                <div class="cache-options">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="buildOptions.info" />
                    <span>Info (_info.yaml)</span>
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="buildOptions.stats" />
                    <span>Stats (_stats.yaml)</span>
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="buildOptions.plots" />
                    <span>Plots (_plot.webp or _plots/)</span>
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="buildOptions.refresh" />
                    <span>Refresh (rebuild existing files)</span>
                  </label>
                  <label class="checkbox-label" title="Fix -inf/inf/nan reserved values by setting them to ufun.min(). This prevents tournament scores from becoming -inf when negotiations fail.">
                    <input type="checkbox" v-model="buildOptions.ensureFiniteReservedValues" />
                    <span>Fix infinite reserved values</span>
                  </label>
                </div>
                
                <div class="setting-group" v-if="buildOptions.stats">
                  <label class="setting-label">Pareto Limits (0 = no limit)</label>
                  <div class="pareto-limits">
                    <div class="limit-input-group">
                      <label class="limit-label">Max Outcomes:</label>
                      <input
                        type="number"
                        v-model.number="buildOptions.maxParetoOutcomes"
                        min="0"
                        class="limit-input"
                        placeholder="No limit"
                      />
                    </div>
                    <div class="limit-input-group">
                      <label class="limit-label">Max Utils:</label>
                      <input
                        type="number"
                        v-model.number="buildOptions.maxParetoUtils"
                        min="0"
                        class="limit-input"
                        placeholder="No limit"
                      />
                    </div>
                  </div>
                  <div class="setting-hint">Leave empty to use Performance tab settings</div>
                </div>
                <button
                  class="btn-action primary"
                  @click="buildCaches"
                  :disabled="buildingCaches || !hasSelectedBuildOptions"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                  <span v-if="buildingCaches">Building...</span>
                  <span v-else>Build Caches</span>
                </button>
                
                <!-- Progress bar -->
                <div v-if="buildProgress" class="cache-progress">
                  <div class="progress-header">
                    <span class="progress-text">
                      Building {{ buildProgress.current }}/{{ buildProgress.total }} scenarios
                    </span>
                    <span class="progress-percent">
                      {{ Math.round((buildProgress.current / buildProgress.total) * 100) }}%
                    </span>
                  </div>
                  <div class="progress-bar">
                    <div
                      class="progress-fill"
                      :style="{ width: `${(buildProgress.current / buildProgress.total) * 100}%` }"
                    ></div>
                  </div>
                  <div v-if="buildCurrentScenario" class="progress-current">
                    Current: {{ buildCurrentScenario }}
                  </div>
                </div>
                
                <p v-if="buildResult" class="cache-result" :class="buildResultClass">
                  {{ buildResult }}
                </p>
              </div>
              
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">Clear Caches</div>
                  <div class="setting-desc">Delete cache files for all scenarios</div>
                </div>
                <div class="cache-options">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="clearOptions.info" />
                    <span>Info (_info.yaml)</span>
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="clearOptions.stats" />
                    <span>Stats (_stats.yaml)</span>
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="clearOptions.plots" />
                    <span>Plots (_plot.webp or _plots/)</span>
                  </label>
                </div>
                <button
                  class="btn-action danger"
                  @click="clearCaches"
                  :disabled="clearingCaches || !hasSelectedClearOptions"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                  <span v-if="clearingCaches">Clearing...</span>
                  <span v-else>Clear Caches</span>
                </button>
                <p v-if="clearResult" class="cache-result" :class="clearResultClass">
                  {{ clearResult }}
                </p>
              </div>
            </div>
          </div>
          
          <!-- Filters Tab -->
          <div v-if="activeTab === 'filters'" class="settings-panel">
            <h2 class="panel-title">Saved Filters</h2>
            
            <div class="setting-group">
              <div class="setting-group-title">Manage your saved filters for scenarios and negotiators</div>
              
              <!-- Filter type tabs -->
              <div class="filter-type-tabs">
                <button
                  class="filter-type-tab"
                  :class="{ active: filterTypeTab === 'scenario' }"
                  @click="filterTypeTab = 'scenario'; loadFilters()"
                >
                  Scenario Filters
                </button>
                <button
                  class="filter-type-tab"
                  :class="{ active: filterTypeTab === 'negotiator' }"
                  @click="filterTypeTab = 'negotiator'; loadFilters()"
                >
                  Negotiator Filters
                </button>
              </div>
              
              <!-- Filters list -->
              <div v-if="loadingFilters" class="filters-loading">
                Loading filters...
              </div>
              
              <div v-else-if="savedFilters.length === 0" class="filters-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                <p>No {{ filterTypeTab }} filters saved yet</p>
                <p class="filters-empty-hint">Save filters from the {{ filterTypeTab === 'scenario' ? 'Scenarios' : 'Negotiators' }} view to access them here</p>
              </div>
              
              <div v-else class="filters-list">
                <div
                  v-for="filter in savedFilters"
                  :key="filter.id"
                  class="filter-item"
                  :class="{ 'is-default': filter.id === defaultFilterId }"
                >
                  <div class="filter-info">
                    <div class="filter-name">
                      {{ filter.name }}
                      <span v-if="filter.id === defaultFilterId" class="default-badge">DEFAULT</span>
                    </div>
                    <div class="filter-desc" v-if="filter.description">{{ filter.description }}</div>
                    <div class="filter-meta">
                      Created: {{ formatDate(filter.created_at) }}
                    </div>
                  </div>
                  <div class="filter-item-actions">
                    <button
                      class="btn-action secondary small"
                      @click="duplicateFilter(filter.id)"
                      :disabled="duplicatingFilterId === filter.id"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </svg>
                      <span v-if="duplicatingFilterId === filter.id">Duplicating...</span>
                      <span v-else>Duplicate</span>
                    </button>
                    <button
                      v-if="filter.id !== defaultFilterId"
                      class="btn-action secondary small"
                      @click="setDefaultFilter(filter.id)"
                      :disabled="settingDefaultFilterId === filter.id"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                      </svg>
                      <span v-if="settingDefaultFilterId === filter.id">Setting...</span>
                      <span v-else>Set Default</span>
                    </button>
                    <button
                      v-else
                      class="btn-action secondary small"
                      @click="clearDefaultFilter()"
                      :disabled="clearingDefaultFilter"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                      <span v-if="clearingDefaultFilter">Clearing...</span>
                      <span v-else>Clear Default</span>
                    </button>
                    <button
                      class="btn-action danger small"
                      @click="deleteFilter(filter.id)"
                      :disabled="deletingFilterId === filter.id"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                      <span v-if="deletingFilterId === filter.id">Deleting...</span>
                      <span v-else>Delete</span>
                    </button>
                  </div>
                </div>
              </div>
              
              <p v-if="filterActionResult" class="filter-result" :class="filterResultClass">
                {{ filterActionResult }}
              </p>
              
              <!-- Export/Import actions -->
              <div class="filter-actions">
                <button
                  class="btn-action primary"
                  @click="exportFilters"
                  :disabled="savedFilters.length === 0 || exportingFilters"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  <span v-if="exportingFilters">Exporting...</span>
                  <span v-else>Export Filters</span>
                </button>
                
                <button
                  class="btn-action secondary"
                  @click="triggerImportFilters"
                  :disabled="importingFilters"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span v-if="importingFilters">Importing...</span>
                  <span v-else>Import Filters</span>
                </button>
                
                <!-- Hidden file input for import -->
                <input
                  ref="importFileInput"
                  type="file"
                  accept=".json"
                  @change="handleImportFile"
                  style="display: none"
                />
              </div>
            </div>
          </div>
          
          <!-- Import/Export Tab -->
          <div v-if="activeTab === 'import-export'" class="settings-panel">
            <h2 class="panel-title">Import & Export</h2>
            
            <div class="setting-group">
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">Export Settings</div>
                  <div class="setting-desc">Download all settings as a ZIP file</div>
                </div>
                <button
                  class="btn-action primary"
                  @click="handleExport"
                  :disabled="exporting"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  <span v-if="exporting">Exporting...</span>
                  <span v-else>Export Settings</span>
                </button>
              </div>
              
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">Import Settings</div>
                  <div class="setting-desc">Upload a settings ZIP file to import</div>
                </div>
                <label class="btn-action secondary">
                  <input
                    ref="importInput"
                    type="file"
                    accept=".zip"
                    style="display: none"
                    @change="handleImport"
                  />
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span v-if="importing">Importing...</span>
                  <span v-else>Import Settings</span>
                </label>
                <p v-if="importStatus" class="import-status" :class="importStatusClass">
                  {{ importStatus }}
                </p>
              </div>
              
              <div class="setting-row vertical">
                <div class="setting-info">
                  <div class="setting-name">Reset to Defaults</div>
                  <div class="setting-desc">Reset all settings to default values</div>
                </div>
                <button
                  class="btn-action danger"
                  @click="handleReset"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="1 4 1 10 7 10" />
                    <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                  </svg>
                  Reset to Defaults
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Footer with Save/Cancel buttons -->
      <div class="macos-footer">
        <button class="btn-footer secondary" @click="closeModal">
          Cancel
        </button>
        <button
          class="btn-footer primary"
          @click="saveAndClose"
          :disabled="saving"
        >
          <span v-if="saving">Saving...</span>
          <span v-else>Save</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useSettingsStore } from '../stores/settings'
import { storeToRefs } from 'pinia'

const props = defineProps({
  show: Boolean,
})

const emit = defineEmits(['close'])

const settingsStore = useSettingsStore()
const { settings, saving } = storeToRefs(settingsStore)

const activeTab = ref('general')
const localSettings = ref(null)
const exporting = ref(false)
const importing = ref(false)
const importStatus = ref('')
const importStatusClass = ref('')
const importInput = ref(null)

// Filters tab state
const filterTypeTab = ref('scenario')
const savedFilters = ref([])
const loadingFilters = ref(false)
const deletingFilterId = ref(null)
const filterActionResult = ref('')
const filterResultClass = ref('')
const exportingFilters = ref(false)
const importingFilters = ref(false)
const importFileInput = ref(null)
const defaultFilterId = ref(null)
const settingDefaultFilterId = ref(null)
const clearingDefaultFilter = ref(false)
const duplicatingFilterId = ref(null)

const tabs = [
  { 
    id: 'general', 
    label: 'General',
    icon: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5'
  },
  { 
    id: 'negotiation', 
    label: 'Negotiation',
    icon: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75'
  },
  { 
    id: 'genius', 
    label: 'Genius',
    icon: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z'
  },
  { 
    id: 'performance', 
    label: 'Performance',
    icon: 'M22 12h-4l-3 9L9 3l-3 9H2'
  },
  { 
    id: 'paths', 
    label: 'Paths',
    icon: 'M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'
  },
  { 
    id: 'cache', 
    label: 'Cache',
    icon: 'M3 12h4l3 9 4-18 3 9h4'
  },
  { 
    id: 'filters', 
    label: 'Filters',
    icon: 'M22 3H2l8 9.46V19l4 2v-8.54L22 3z'
  },
  { 
    id: 'import-export', 
    label: 'Import/Export',
    icon: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3'
  },
]

// Watch for modal open to load fresh settings
watch(() => props.show, (newVal) => {
  if (newVal) {
    loadLocalSettings()
    activeTab.value = 'general'
    importStatus.value = ''
  }
})

onMounted(() => {
  if (props.show) {
    loadLocalSettings()
  }
})

function loadLocalSettings() {
  // Deep copy settings to local state
  localSettings.value = JSON.parse(JSON.stringify(settings.value))
  
  // Ensure arrays exist
  if (!localSettings.value.paths.scenario_paths) {
    localSettings.value.paths.scenario_paths = []
  }
}

function closeModal() {
  emit('close')
}

async function saveAndClose() {
  // Update store settings
  settings.value = JSON.parse(JSON.stringify(localSettings.value))
  
  const result = await settingsStore.saveSettings()
  
  if (result.success) {
    closeModal()
  } else {
    alert('Failed to save settings. Please try again.')
  }
}

function addPath() {
  localSettings.value.paths.scenario_paths.push('')
}

function removePath(index) {
  localSettings.value.paths.scenario_paths.splice(index, 1)
}

async function handleExport() {
  exporting.value = true
  const result = await settingsStore.exportSettings()
  exporting.value = false
  
  if (!result.success) {
    alert('Failed to export settings')
  }
}

async function handleImport(event) {
  const file = event.target.files?.[0]
  if (!file) return
  
  importing.value = true
  importStatus.value = ''
  
  const result = await settingsStore.importSettings(file)
  
  importing.value = false
  
  if (result.success) {
    importStatus.value = result.message
    importStatusClass.value = 'success'
    
    // Reload local settings
    loadLocalSettings()
    
    if (result.partial) {
      importStatus.value += ' (with some errors)'
      importStatusClass.value = 'warning'
    }
  } else {
    importStatus.value = result.message || 'Import failed'
    importStatusClass.value = 'error'
  }
}

// Cache management state
const cacheStatus = ref(null)
const loadingCacheStatus = ref(false)
const buildingCaches = ref(false)
const clearingCaches = ref(false)
const buildResult = ref('')
const clearResult = ref('')
const buildResultClass = ref('')
const clearResultClass = ref('')
const cacheBuildFolder = ref('')
const buildProgress = ref(null)
const buildCurrentScenario = ref('')

const buildOptions = ref({
  info: false,
  stats: false,
  plots: false,
  refresh: false,
  ensureFiniteReservedValues: false,
  maxParetoOutcomes: null,
  maxParetoUtils: null,
})

const clearOptions = ref({
  info: false,
  stats: false,
  plots: false,
})

const hasSelectedBuildOptions = computed(() => {
  return buildOptions.value.info || buildOptions.value.stats || buildOptions.value.plots
})

const hasSelectedClearOptions = computed(() => {
  return clearOptions.value.info || clearOptions.value.stats || clearOptions.value.plots
})

// Cache management methods
async function loadCacheStatus() {
  loadingCacheStatus.value = true
  try {
    const response = await fetch('/api/cache/scenarios/status')
    const data = await response.json()
    if (data.success) {
      cacheStatus.value = data.status
    }
  } catch (error) {
    console.error('Failed to load cache status:', error)
  } finally {
    loadingCacheStatus.value = false
  }
}

async function buildCaches() {
  if (!hasSelectedBuildOptions.value) return
  
  buildingCaches.value = true
  buildResult.value = ''
  buildProgress.value = null
  buildCurrentScenario.value = ''
  
  try {
    const params = new URLSearchParams()
    if (buildOptions.value.info) params.append('info', 'true')
    if (buildOptions.value.stats) params.append('stats', 'true')
    if (buildOptions.value.plots) params.append('plots', 'true')
    if (buildOptions.value.refresh) params.append('refresh', 'true')
    if (buildOptions.value.ensureFiniteReservedValues) params.append('ensure_finite_reserved_values', 'true')
    if (cacheBuildFolder.value) params.append('base_path', cacheBuildFolder.value)
    
    // Add Pareto limits if specified
    if (buildOptions.value.maxParetoOutcomes) {
      params.append('max_pareto_outcomes', buildOptions.value.maxParetoOutcomes.toString())
    }
    if (buildOptions.value.maxParetoUtils) {
      params.append('max_pareto_utils', buildOptions.value.maxParetoUtils.toString())
    }
    
    // Use EventSource for SSE to get progress updates
    const eventSource = new EventSource(`/api/cache/scenarios/build-stream?${params}`)
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'progress') {
        buildProgress.value = data
        buildCurrentScenario.value = data.current_scenario || ''
      } else if (data.type === 'complete') {
        eventSource.close()
        
        const results = data.results
        buildResult.value = `Built caches for ${results.successful}/${results.total} scenarios. `
        if (buildOptions.value.info) buildResult.value += `Info: ${results.info_created}. `
        if (buildOptions.value.stats) buildResult.value += `Stats: ${results.stats_created}. `
        if (buildOptions.value.plots) buildResult.value += `Plots: ${results.plots_created}. `
        if (results.reserved_values_fixed > 0) buildResult.value += `Reserved values fixed: ${results.reserved_values_fixed}. `
        
        if (results.failed > 0) {
          buildResult.value += `(${results.failed} failed)`
          buildResultClass.value = 'warning'
        } else {
          buildResultClass.value = 'success'
        }
        
        buildingCaches.value = false
        buildProgress.value = null
        buildCurrentScenario.value = ''
        
        // Reload cache status
        loadCacheStatus()
      } else if (data.type === 'error') {
        eventSource.close()
        buildResult.value = 'Error: ' + (data.error || 'Unknown error')
        buildResultClass.value = 'error'
        buildingCaches.value = false
        buildProgress.value = null
        buildCurrentScenario.value = ''
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
      buildResult.value = 'Connection error during cache build'
      buildResultClass.value = 'error'
      buildingCaches.value = false
      buildProgress.value = null
      buildCurrentScenario.value = ''
    }
  } catch (error) {
    buildResult.value = 'Failed to build caches: ' + error.message
    buildResultClass.value = 'error'
    buildingCaches.value = false
    buildProgress.value = null
    buildCurrentScenario.value = ''
  }
}

function resetCacheBuildFolder() {
  cacheBuildFolder.value = ''
}

async function clearCaches() {
  if (!hasSelectedClearOptions.value) return
  
  const types = []
  if (clearOptions.value.info) types.push('info')
  if (clearOptions.value.stats) types.push('stats')
  if (clearOptions.value.plots) types.push('plots')
  
  if (!confirm(`Are you sure you want to delete ${types.join(', ')} cache files for all scenarios? This cannot be undone.`)) {
    return
  }
  
  clearingCaches.value = true
  clearResult.value = ''
  
  try {
    const params = new URLSearchParams()
    if (clearOptions.value.info) params.append('info', 'true')
    if (clearOptions.value.stats) params.append('stats', 'true')
    if (clearOptions.value.plots) params.append('plots', 'true')
    
    const response = await fetch(`/api/cache/scenarios/clear?${params}`, {
      method: 'POST',
    })
    const data = await response.json()
    
    if (data.success) {
      const results = data.results
      clearResult.value = `Cleared caches from ${results.total} scenarios. `
      if (clearOptions.value.info) clearResult.value += `Info: ${results.info_deleted}. `
      if (clearOptions.value.stats) clearResult.value += `Stats: ${results.stats_deleted}. `
      if (clearOptions.value.plots) clearResult.value += `Plots: ${results.plots_deleted}. `
      clearResultClass.value = 'success'
      
      // Reload cache status
      await loadCacheStatus()
    } else {
      clearResult.value = 'Error: ' + (data.error || 'Unknown error')
      clearResultClass.value = 'error'
    }
  } catch (error) {
    clearResult.value = 'Failed to clear caches: ' + error.message
    clearResultClass.value = 'error'
  } finally {
    clearingCaches.value = false
  }
}

// Load cache status when cache tab is opened
watch(activeTab, (newVal) => {
  if (newVal === 'cache' && !cacheStatus.value) {
    loadCacheStatus()
  }
  if (newVal === 'filters') {
    loadFilters()
  }
})

// Filter management methods
async function loadFilters() {
  loadingFilters.value = true
  filterActionResult.value = ''
  try {
    // Load filters list
    const response = await fetch(`/api/filters?type=${filterTypeTab.value}`)
    const data = await response.json()
    if (data.success) {
      savedFilters.value = data.filters
    }
    
    // Load default filter ID
    const defaultResponse = await fetch(`/api/filters/default/${filterTypeTab.value}`)
    const defaultData = await defaultResponse.json()
    if (defaultData.success && defaultData.filter) {
      defaultFilterId.value = defaultData.filter.id
    } else {
      defaultFilterId.value = null
    }
  } catch (error) {
    console.error('Failed to load filters:', error)
  } finally {
    loadingFilters.value = false
  }
}

async function deleteFilter(filterId) {
  if (!confirm('Are you sure you want to delete this filter? This cannot be undone.')) {
    return
  }
  
  deletingFilterId.value = filterId
  filterActionResult.value = ''
  
  try {
    const response = await fetch(`/api/filters/${filterId}`, {
      method: 'DELETE',
    })
    const data = await response.json()
    
    if (data.success) {
      filterActionResult.value = 'Filter deleted successfully'
      filterResultClass.value = 'success'
      // Reload filters
      await loadFilters()
    } else {
      filterActionResult.value = 'Error: ' + (data.error || 'Unknown error')
      filterResultClass.value = 'error'
    }
  } catch (error) {
    filterActionResult.value = 'Failed to delete filter: ' + error.message
    filterResultClass.value = 'error'
  } finally {
    deletingFilterId.value = null
  }
}

function formatDate(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString()
}

async function setDefaultFilter(filterId) {
  settingDefaultFilterId.value = filterId
  filterActionResult.value = ''
  
  try {
    const response = await fetch(`/api/filters/default/${filterTypeTab.value}/${filterId}`, {
      method: 'POST'
    })
    const data = await response.json()
    
    if (data.success) {
      defaultFilterId.value = filterId
      filterActionResult.value = 'Default filter set successfully'
      filterResultClass.value = 'success'
    } else {
      filterActionResult.value = 'Failed to set default filter'
      filterResultClass.value = 'error'
    }
  } catch (error) {
    filterActionResult.value = 'Error setting default filter: ' + error.message
    filterResultClass.value = 'error'
  } finally {
    settingDefaultFilterId.value = null
  }
}

async function clearDefaultFilter() {
  clearingDefaultFilter.value = true
  filterActionResult.value = ''
  
  try {
    const response = await fetch(`/api/filters/default/${filterTypeTab.value}`, {
      method: 'DELETE'
    })
    const data = await response.json()
    
    if (data.success) {
      defaultFilterId.value = null
      filterActionResult.value = 'Default filter cleared successfully'
      filterResultClass.value = 'success'
    } else {
      filterActionResult.value = 'Failed to clear default filter'
      filterResultClass.value = 'error'
    }
  } catch (error) {
    filterActionResult.value = 'Error clearing default filter: ' + error.message
    filterResultClass.value = 'error'
  } finally {
    clearingDefaultFilter.value = false
  }
}

async function duplicateFilter(filterId) {
  duplicatingFilterId.value = filterId
  filterActionResult.value = ''
  
  try {
    const response = await fetch(`/api/filters/${filterId}/duplicate`, {
      method: 'POST'
    })
    const data = await response.json()
    
    if (data.success) {
      filterActionResult.value = `Filter duplicated as "${data.filter.name}"`
      filterResultClass.value = 'success'
      // Reload filters to show the new one
      await loadFilters()
    } else {
      filterActionResult.value = 'Failed to duplicate filter'
      filterResultClass.value = 'error'
    }
  } catch (error) {
    filterActionResult.value = 'Error duplicating filter: ' + error.message
    filterResultClass.value = 'error'
  } finally {
    duplicatingFilterId.value = null
  }
}

async function exportFilters() {
  exportingFilters.value = true
  filterActionResult.value = ''
  
  try {
    const response = await fetch('/api/filters/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filter_type: filterTypeTab.value
      })
    })
    
    if (response.ok) {
      // Download the file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `negmas-${filterTypeTab.value}-filters.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      filterActionResult.value = 'Filters exported successfully'
      filterResultClass.value = 'success'
    } else {
      filterActionResult.value = 'Failed to export filters'
      filterResultClass.value = 'error'
    }
  } catch (error) {
    filterActionResult.value = 'Error exporting filters: ' + error.message
    filterResultClass.value = 'error'
  } finally {
    exportingFilters.value = false
  }
}

function triggerImportFilters() {
  if (importFileInput.value) {
    importFileInput.value.click()
  }
}

async function handleImportFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  
  importingFilters.value = true
  filterActionResult.value = ''
  
  try {
    const text = await file.text()
    
    // Ask user about overwrite behavior
    const overwrite = confirm(
      'Do you want to overwrite filters with the same name?\n\n' +
      'Yes: Replace existing filters with same name\n' +
      'No: Keep both (imported filters get " (Imported)" suffix)'
    )
    
    const response = await fetch('/api/filters/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        json_data: text,
        overwrite: overwrite
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      filterActionResult.value = `Successfully imported ${result.imported} filter(s)`
      if (result.errors && result.errors.length > 0) {
        filterActionResult.value += `. Errors: ${result.errors.join(', ')}`
      }
      filterResultClass.value = result.errors && result.errors.length > 0 ? 'warning' : 'success'
      
      // Reload filters
      await loadFilters()
    } else {
      filterActionResult.value = 'Import failed'
      if (result.errors && result.errors.length > 0) {
        filterActionResult.value += `: ${result.errors.join(', ')}`
      }
      filterResultClass.value = 'error'
    }
  } catch (error) {
    filterActionResult.value = 'Error importing filters: ' + error.message
    filterResultClass.value = 'error'
  } finally {
    importingFilters.value = false
    // Clear file input
    if (importFileInput.value) {
      importFileInput.value.value = ''
    }
  }
}

function handleReset() {
  if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
    settingsStore.resetToDefaults()
    loadLocalSettings()
  }
}
</script>

<style scoped>
/* Modal overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

/* macOS-style modal */
.macos-settings-modal {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  width: 900px;
  max-width: 95vw;
  height: 700px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* macOS titlebar */
.macos-titlebar {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  -webkit-app-region: drag;
}

.titlebar-controls {
  display: flex;
  gap: 8px;
  -webkit-app-region: no-drag;
}

.titlebar-btn {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  transition: opacity 0.2s;
}

.titlebar-btn:hover {
  opacity: 0.8;
}

.titlebar-btn.close {
  background: #ff5f57;
}

.titlebar-btn.minimize {
  background: #febc2e;
}

.titlebar-btn.maximize {
  background: #28c840;
}

.titlebar-title {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.titlebar-spacer {
  flex: 1;
}

/* Content layout with sidebar */
.macos-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar */
.macos-sidebar {
  width: 180px;
  background: var(--bg-tertiary);
  border-right: 1px solid var(--border-color);
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
  font-size: 0.9rem;
}

.sidebar-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.sidebar-item.active {
  background: var(--primary-color);
  color: white;
}

.sidebar-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.sidebar-label {
  flex: 1;
  font-weight: 500;
}

/* Main content area */
.macos-main {
  flex: 1;
  overflow-y: auto;
  padding: 32px 40px;
  background: var(--bg-primary);
}

.settings-panel {
  max-width: 600px;
}

.panel-title {
  margin: 0 0 24px 0;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--text-primary);
}

/* Setting groups */
.setting-group {
  margin-bottom: 32px;
}

.setting-group-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

/* Setting rows */
.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-row.vertical {
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-info {
  flex: 1;
  margin-right: 16px;
}

.setting-name {
  font-weight: 500;
  font-size: 0.95rem;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.setting-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* Toggle switch */
.toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle-input {
  display: none;
}

.toggle-slider {
  position: relative;
  width: 48px;
  height: 28px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  transition: all 0.3s;
  flex-shrink: 0;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  left: 2px;
  top: 2px;
  background: white;
  border-radius: 50%;
  transition: all 0.3s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-input:checked + .toggle-slider {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

.toggle-input:checked + .toggle-slider::before {
  transform: translateX(20px);
}

.toggle-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  min-width: 40px;
}

/* Input fields */
.setting-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.9rem;
  transition: all 0.2s;
}

.setting-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.setting-input.number {
  width: 120px;
}

.setting-input.text {
  width: 100%;
  max-width: 400px;
}

.setting-input.full-width {
  width: 100%;
  max-width: none;
}

/* Path list */
.path-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  margin-bottom: 12px;
}

.path-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.path-item .setting-input {
  flex: 1;
}

.btn-icon-remove {
  width: 28px;
  height: 28px;
  padding: 4px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-icon-remove:hover {
  background: #fee;
  border-color: #f88;
  color: #e44;
}

.btn-icon-remove svg {
  width: 16px;
  height: 16px;
}

.btn-add-path {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
  align-self: flex-start;
}

.btn-add-path:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.btn-add-path svg {
  width: 16px;
  height: 16px;
}

/* Action buttons */
.btn-action {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  align-self: flex-start;
}

.btn-action svg {
  width: 18px;
  height: 18px;
}

.btn-action.primary {
  background: var(--primary-color);
  color: white;
}

.btn-action.primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-action.secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-action.secondary:hover {
  background: var(--bg-hover);
}

.btn-action.danger {
  background: #fee;
  color: #e44;
  border: 1px solid #fcc;
}

.btn-action.danger:hover {
  background: #fdd;
  border-color: #faa;
}

.btn-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Import status */
.import-status {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
}

.import-status.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.import-status.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.import-status.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Footer */
.macos-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.btn-footer {
  padding: 8px 24px;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-footer.secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-footer.secondary:hover {
  background: var(--bg-hover);
}

.btn-footer.primary {
  background: var(--primary-color);
  color: white;
}

.btn-footer.primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-footer.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Cache management styles */
.cache-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.stat-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 1rem;
}

.cache-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--text-primary);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.cache-result {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.cache-result.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.cache-result.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.cache-result.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Folder input group */
.folder-input-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.folder-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-family: 'Courier New', monospace;
}

.folder-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.setting-hint {
  margin-top: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  opacity: 0.8;
}

/* Pareto limits input styling */
.pareto-limits {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.limit-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.limit-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.limit-input {
  flex: 1;
  padding: 6px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 0.9rem;
  color: var(--text-primary);
  transition: border-color 0.2s;
}

.limit-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.limit-input::placeholder {
  color: var(--text-secondary);
  opacity: 0.5;
}

/* Cache progress bar */
.cache-progress {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.progress-text {
  color: var(--text-primary);
  font-weight: 500;
}

.progress-percent {
  color: var(--primary-color);
  font-weight: 600;
}

.progress-bar {
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-current {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-family: 'Courier New', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Filters tab styles */
.filter-type-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.filter-type-tab {
  padding: 8px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-type-tab:hover {
  color: var(--text-primary);
}

.filter-type-tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.filters-loading {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.filters-empty {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-secondary);
}

.filters-empty svg {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  opacity: 0.5;
}

.filters-empty p {
  margin: 8px 0;
  font-size: 0.95rem;
}

.filters-empty-hint {
  font-size: 0.85rem;
  opacity: 0.7;
}

.filters-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.2s;
}

.filter-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filter-item.is-default {
  border-color: var(--primary-color);
  background: rgba(var(--primary-color-rgb), 0.05);
}

.filter-info {
  flex: 1;
}

.filter-name {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.default-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--primary-color);
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.filter-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.filter-item-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.btn-action.small {
  padding: 6px 12px;
  font-size: 0.85rem;
}

.btn-action.small svg {
  width: 14px;
  height: 14px;
}

.filter-result {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  font-size: 0.9rem;
}

.filter-result.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.filter-result.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.filter-result.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Filter export/import actions */
.filter-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}
</style>
