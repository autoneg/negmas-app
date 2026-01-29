<template>
  <div class="scenarios-view">
    <!-- Registration Loading Overlay -->
    <div v-if="!registrationStatus.registered && registrationStatus.in_progress" class="registration-overlay">
      <div class="registration-modal">
        <h3>Loading Scenarios...</h3>
        <p>Registering scenario databases. This happens once on server startup.</p>
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: registrationProgress + '%' }"
          ></div>
        </div>
        <p class="progress-text">
          {{ registrationStatus.progress.current }} / {{ registrationStatus.progress.total }} categories
          <span v-if="registrationStatus.total_scenarios > 0">({{ registrationStatus.total_scenarios }} scenarios found)</span>
        </p>
      </div>
    </div>

    <!-- Scenarios List Panel -->
    <div class="scenarios-list-panel">
      <!-- Filters -->
      <div class="filter-section">
        <div class="filter-header">
          <h3>Scenarios</h3>
          <button class="btn-icon" @click="loadData" :disabled="loading" title="Refresh">
            <span v-if="loading">⟳</span>
            <span v-else>↻</span>
          </button>
        </div>
        
        <!-- Search -->
        <input
          v-model="localSearch"
          type="text"
          placeholder="Search scenarios..."
          class="input-search"
          @input="updateSearch"
        />
        
        <!-- Source Filter -->
        <div class="filter-group">
          <label>Source</label>
          <select v-model="localSource" @change="updateSourceFilter" class="input-select">
            <option value="">All Sources</option>
            <option v-for="source in sources" :key="source" :value="source">{{ source }}</option>
          </select>
        </div>
        
        <!-- Outcomes Range -->
        <div class="filter-group">
          <label>Outcomes</label>
          <div class="range-inputs">
            <input
              v-model.number="localFilters.minOutcomes"
              type="number"
              placeholder="Min"
              class="input-range"
              @input="updateFilters"
            />
            <span>-</span>
            <input
              v-model.number="localFilters.maxOutcomes"
              type="number"
              placeholder="Max"
              class="input-range"
              @input="updateFilters"
            />
          </div>
        </div>
        
        <!-- Advanced Filters Toggle -->
        <button class="btn-secondary btn-sm" @click="showAdvancedFilters = !showAdvancedFilters" style="margin-top: 8px;">
          {{ showAdvancedFilters ? '▼' : '▶' }} Advanced Filters
        </button>
        
        <!-- Advanced Filters (Collapsible) -->
        <div v-show="showAdvancedFilters" class="advanced-filters">
          <!-- Negotiators Range -->
          <div class="filter-group">
            <label>Negotiators</label>
            <div class="range-inputs">
              <input
                v-model.number="localFilters.minNegotiators"
                type="number"
                placeholder="Min"
                class="input-range"
                @input="updateFilters"
              />
              <span>-</span>
              <input
                v-model.number="localFilters.maxNegotiators"
                type="number"
                placeholder="Max"
                class="input-range"
                @input="updateFilters"
              />
            </div>
          </div>
          
          <!-- Opposition Range -->
          <div class="filter-group">
            <label>Opposition</label>
            <div class="range-inputs">
              <input
                v-model.number="localFilters.minOpposition"
                type="number"
                step="0.1"
                placeholder="Min"
                class="input-range"
                @input="updateFilters"
              />
              <span>-</span>
              <input
                v-model.number="localFilters.maxOpposition"
                type="number"
                step="0.1"
                placeholder="Max"
                class="input-range"
                @input="updateFilters"
              />
            </div>
          </div>
          
          <!-- Rational Fraction Range -->
          <div class="filter-group">
            <label>Rational Fraction</label>
            <div class="range-inputs">
              <input
                v-model.number="localFilters.minRationalFraction"
                type="number"
                step="0.1"
                placeholder="Min"
                class="input-range"
                @input="updateFilters"
              />
              <span>-</span>
              <input
                v-model.number="localFilters.maxRationalFraction"
                type="number"
                step="0.1"
                placeholder="Max"
                class="input-range"
                @input="updateFilters"
              />
            </div>
          </div>
          
          <!-- Boolean Filters -->
          <div class="filter-group">
            <label>Normalized</label>
            <select v-model="localFilters.normalized" @change="updateFilters" class="input-select">
              <option :value="null">Any</option>
              <option :value="true">Yes</option>
              <option :value="false">No</option>
            </select>
          </div>
          
          <div class="filter-group">
            <label>ANAC</label>
            <select v-model="localFilters.anac" @change="updateFilters" class="input-select">
              <option :value="null">Any</option>
              <option :value="true">Yes</option>
              <option :value="false">No</option>
            </select>
          </div>
          
          <div class="filter-group">
            <label>Type</label>
            <select v-model="localFilters.file" @change="updateFilters" class="input-select">
              <option :value="null">Any</option>
              <option :value="false">Folder</option>
              <option :value="true">File</option>
            </select>
          </div>
          
          <div class="filter-group">
            <label>Format</label>
            <select v-model="localFilters.format" @change="updateFilters" class="input-select">
              <option value="">Any</option>
              <option value="yaml">YAML</option>
              <option value="xml">XML</option>
              <option value="json">JSON</option>
            </select>
          </div>
        </div>
        
        <!-- Reverse Filter Checkbox -->
        <div class="filter-group" style="margin-top: 12px;">
          <label class="checkbox-label">
            <input 
              type="checkbox" 
              v-model="localFilters.reverseFilter" 
              @change="updateFilters"
            />
            <span>Reverse Filter (exclude matching items)</span>
          </label>
        </div>
        
        <div style="display: flex; gap: 8px; margin-top: 8px;">
          <button class="btn-secondary btn-sm" @click="clearFilters" style="flex: 1;">Clear Filters</button>
          <button class="btn-secondary btn-sm" @click="showSaveFilterDialog = true" style="flex: 1;">Save Filter</button>
          <select v-model="selectedFilterId" @change="loadSavedFilter" class="input-select btn-sm" style="flex: 1;">
            <option value="">Load Filter...</option>
            <option v-for="filter in savedFilters" :key="filter.id" :value="filter.id">{{ filter.name }}</option>
          </select>
        </div>
      </div>
      
      <!-- List Header with Count and Bulk Actions -->
      <div class="list-header">
        <div class="list-count">
          {{ filteredScenarios.length }} scenario{{ filteredScenarios.length !== 1 ? 's' : '' }}
        </div>
        <div class="bulk-actions" v-if="filteredScenarios.length > 0">
          <button 
            class="btn-icon" 
            @click="showBulkActionsMenu = !showBulkActionsMenu"
            title="Bulk actions for filtered scenarios"
          >
            ⋮
          </button>
          <div v-if="showBulkActionsMenu" class="bulk-menu">
            <button class="bulk-menu-item" @click="bulkUpdateStatus('enabled')">
              ✓ Enable All
            </button>
            <button class="bulk-menu-item" @click="bulkUpdateStatus('disabled')">
              ⊘ Disable All
            </button>
            <button class="bulk-menu-item" @click="bulkUpdateStatus('archived')">
              📦 Archive All
            </button>
            <hr class="bulk-menu-divider">
            <button class="bulk-menu-item bulk-delete" @click="bulkDelete">
              🗑 Delete All
            </button>
          </div>
        </div>
      </div>
      
      <!-- Scenarios List -->
      <div class="scenarios-list">
        <div v-if="loading" class="loading-state">
          <span class="spinner"></span> Loading scenarios...
        </div>
        
        <div v-else-if="filteredScenarios.length === 0" class="empty-state">
          No scenarios found
        </div>
        
        <div
          v-else
          v-for="scenario in filteredScenarios"
          :key="scenario.path"
          class="scenario-item"
          :class="{ active: selectedScenario?.path === scenario.path }"
          @click="selectScenario(scenario)"
        >
          <div class="scenario-name">{{ scenario.name }}</div>
          <div class="scenario-meta">
            <span class="badge">{{ scenario.source }}</span>
            <span v-if="scenario.tags && scenario.tags.length > 0" class="tags">
              <span v-for="tag in scenario.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
            </span>
            <span v-if="scenario.n_outcomes">{{ formatNumber(scenario.n_outcomes) }} outcomes</span>
          </div>
          <div class="scenario-stats" v-if="scenario.rational_fraction !== null || scenario.opposition !== null">
            <span v-if="scenario.rational_fraction !== null" title="Rational Fraction">
              R: {{ (scenario.rational_fraction * 100).toFixed(1) }}%
            </span>
            <span v-if="scenario.opposition !== null" title="Opposition">
              O: {{ scenario.opposition.toFixed(2) }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Scenario Details Panel -->
    <div class="scenario-details-panel">
      <div v-if="!selectedScenario" class="empty-state">
        <p>Select a scenario to view details</p>
      </div>
      
      <div v-else class="scenario-details">
        <!-- Header -->
        <div class="details-header">
          <div class="details-header-title">
            <h2>{{ selectedScenario.name }}</h2>
            <button 
              class="btn-icon-folder" 
              @click="openScenarioFolder"
              title="Open scenario folder in file explorer"
            >
              📁
            </button>
          </div>
          <div class="header-actions">
            <!-- Status dropdown -->
            <div class="status-dropdown" v-if="!selectedScenario.readonly">
              <button 
                class="btn-secondary btn-sm dropdown-toggle"
                @click="toggleStatusDropdown"
                :class="{ 
                  'status-disabled': selectedScenario.status === 'disabled',
                  'status-archived': selectedScenario.status === 'archived'
                }"
              >
                {{ getStatusLabel(selectedScenario.status) }}
                <span class="dropdown-arrow">▼</span>
              </button>
              <div v-if="showStatusDropdown" class="dropdown-menu">
                <button 
                  class="dropdown-item"
                  @click="updateScenarioStatus('enabled')"
                  :class="{ active: selectedScenario.status === 'enabled' }"
                >
                  ✓ Enabled
                </button>
                <button 
                  class="dropdown-item"
                  @click="updateScenarioStatus('disabled')"
                  :class="{ active: selectedScenario.status === 'disabled' }"
                >
                  ⊘ Disabled
                </button>
                <button 
                  class="dropdown-item"
                  @click="updateScenarioStatus('archived')"
                  :class="{ active: selectedScenario.status === 'archived' }"
                >
                  📦 Archived
                </button>
              </div>
            </div>
            
            <button 
              v-if="!selectedScenario.readonly"
              class="btn-danger btn-sm" 
              @click="deleteScenario"
              title="Delete scenario from disk"
            >
              🗑 Delete
            </button>
            
            <button 
              class="btn-secondary btn-sm" 
              @click="refreshAllCaches"
              :disabled="refreshingCache"
              title="Refresh all cached data (stats, plot, info)"
            >
              <span v-if="refreshingCache" class="spinner-small"></span>
              <span v-else>↻</span>
              Refresh Cache
            </button>
            <button class="btn-primary btn-sm" @click="openNewNegotiation">
              Start Negotiation
            </button>
          </div>
        </div>
        
        <!-- Scrollable content with 2-column layout -->
        <div class="details-content">
          <!-- Left Column -->
          <div class="details-column">
            <!-- Info Panel (Top Half) -->
            <div class="panel collapsible-panel" :class="{ collapsed: panelsCollapsed.info }">
              <div class="panel-header-collapsible" @click="togglePanel('info')">
                <h3 class="panel-title">
                  <span class="collapse-icon">{{ panelsCollapsed.info ? '▶' : '▼' }}</span>
                  Information
                </h3>
              </div>
              
              <div v-if="!panelsCollapsed.info" class="panel-content">
                <div class="info-grid-compact">
                  <div class="info-item">
                    <label>Source</label>
                    <span>{{ selectedScenario.source }}</span>
                  </div>
                  <div class="info-item">
                    <label>Negotiators</label>
                    <span>{{ selectedScenario.n_negotiators }}</span>
                  </div>
                  <div class="info-item">
                    <label>Issues</label>
                    <span>{{ selectedScenario.n_issues }}</span>
                  </div>
                  <div class="info-item">
                    <label>Outcomes</label>
                    <span>{{ formatNumber(selectedScenario.n_outcomes) }}</span>
                  </div>
                  <div class="info-item" v-if="selectedScenario.rational_fraction !== null">
                    <label>Rational Fraction</label>
                    <span>{{ (selectedScenario.rational_fraction * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="info-item" v-if="selectedScenario.opposition !== null">
                    <label>Opposition</label>
                    <span>{{ selectedScenario.opposition.toFixed(3) }}</span>
                  </div>
                  <div class="info-item" v-if="selectedScenario.format">
                    <label>Format</label>
                    <span>{{ selectedScenario.format.toUpperCase() }}</span>
                  </div>
                  <div class="info-item" v-if="selectedScenario.normalized !== null">
                    <label>Normalized</label>
                    <span>{{ selectedScenario.normalized ? 'Yes' : 'No' }}</span>
                  </div>
                </div>
                
                <!-- Description -->
                <div v-if="selectedScenario.description" class="description-section">
                  <h4>Description</h4>
                  <div class="description-text">{{ selectedScenario.description }}</div>
                </div>
                
                <!-- Tags -->
                <div v-if="selectedScenario.tags && selectedScenario.tags.length > 0" class="tags-section">
                  <h4>Tags</h4>
                  <div class="tags">
                    <span v-for="tag in selectedScenario.tags" :key="tag" class="badge">{{ tag }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Statistics Panel (Top Half) -->
            <div class="panel collapsible-panel" :class="{ collapsed: panelsCollapsed.stats }">
              <div class="panel-header-collapsible" @click="togglePanel('stats')">
                <h3 class="panel-title">
                  <span class="collapse-icon">{{ panelsCollapsed.stats ? '▶' : '▼' }}</span>
                  Statistics
                </h3>
                <div class="panel-header-actions" @click.stop>
                  <button 
                    v-if="statsLoaded" 
                    class="btn-secondary btn-sm" 
                    @click="showOutcomes = !showOutcomes"
                    :title="showOutcomes ? 'Hide outcomes' : 'Show outcomes'"
                  >
                    {{ showOutcomes ? 'Hide' : 'Show' }} Outcomes
                  </button>
                  <button 
                    v-if="!selectedScenario.has_stats && !loadingStats" 
                    class="btn-secondary btn-sm" 
                    @click="calculateStats"
                  >
                    Calculate
                  </button>
                </div>
              </div>
              
              <div v-if="!panelsCollapsed.stats" class="panel-content">
                <div v-if="!statsLoaded && !loadingStats" class="panel-empty">
                  <p>Statistics not calculated yet</p>
                  <button class="btn-primary btn-sm" @click="calculateStats">Calculate Stats</button>
                </div>
                
                <div v-else-if="loadingStats" class="loading-state">
                  <span class="spinner"></span> Loading stats...
                </div>
                
                <div v-else-if="selectedScenarioStats" class="stats-grid-compact">
                  <div class="stat-item" v-if="selectedScenarioStats.n_pareto_outcomes !== null && selectedScenarioStats.n_pareto_outcomes !== undefined">
                    <label>Pareto Outcomes</label>
                    <span>{{ formatNumber(selectedScenarioStats.n_pareto_outcomes) }}</span>
                  </div>
                  <div class="stat-item" v-if="selectedScenarioStats.opposition !== null && selectedScenarioStats.opposition !== undefined">
                    <label>Opposition</label>
                    <span>{{ selectedScenarioStats.opposition.toFixed(3) }}</span>
                  </div>
                  <div class="stat-item" v-if="selectedScenarioStats.rational_fraction !== null && selectedScenarioStats.rational_fraction !== undefined">
                    <label>Rational Fraction</label>
                    <span>{{ (selectedScenarioStats.rational_fraction * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="stat-item" v-if="selectedScenarioStats.nash_utils && selectedScenarioStats.nash_utils.length > 0">
                    <label>Nash Utils</label>
                    <span class="utils-compact">{{ formatUtilityList(selectedScenarioStats.nash_utils[0]) }}</span>
                  </div>
                  <div class="stat-item" v-if="selectedScenarioStats.kalai_utils && selectedScenarioStats.kalai_utils.length > 0">
                    <label>Kalai Utils</label>
                    <span class="utils-compact">{{ formatUtilityList(selectedScenarioStats.kalai_utils[0]) }}</span>
                  </div>
                  <div class="stat-item" v-if="selectedScenarioStats.ks_utils && selectedScenarioStats.ks_utils.length > 0">
                    <label>KS Utils</label>
                    <span class="utils-compact">{{ formatUtilityList(selectedScenarioStats.ks_utils[0]) }}</span>
                  </div>
                  <div class="stat-item" v-if="selectedScenarioStats.max_welfare_utils && selectedScenarioStats.max_welfare_utils.length > 0">
                    <label>Max Welfare Utils</label>
                    <span class="utils-compact">{{ formatUtilityList(selectedScenarioStats.max_welfare_utils[0]) }}</span>
                  </div>
                  
                  <!-- Outcomes (if enabled) -->
                  <div v-if="showOutcomes && selectedScenarioStats.nash_outcomes && selectedScenarioStats.nash_outcomes.length > 0" class="stat-item full-width">
                    <label>Nash Outcome</label>
                    <span class="outcome-text">{{ formatOutcome(selectedScenarioStats.nash_outcomes[0]) }}</span>
                  </div>
                  <div v-if="showOutcomes && selectedScenarioStats.kalai_outcomes && selectedScenarioStats.kalai_outcomes.length > 0" class="stat-item full-width">
                    <label>Kalai Outcome</label>
                    <span class="outcome-text">{{ formatOutcome(selectedScenarioStats.kalai_outcomes[0]) }}</span>
                  </div>
                  <div v-if="showOutcomes && selectedScenarioStats.ks_outcomes && selectedScenarioStats.ks_outcomes.length > 0" class="stat-item full-width">
                    <label>KS Outcome</label>
                    <span class="outcome-text">{{ formatOutcome(selectedScenarioStats.ks_outcomes[0]) }}</span>
                  </div>
                  <div v-if="showOutcomes && selectedScenarioStats.max_welfare_outcomes && selectedScenarioStats.max_welfare_outcomes.length > 0" class="stat-item full-width">
                    <label>Max Welfare Outcome</label>
                    <span class="outcome-text">{{ formatOutcome(selectedScenarioStats.max_welfare_outcomes[0]) }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Outcome Space Panel (Bottom Half) -->
            <div class="panel collapsible-panel" :class="{ collapsed: panelsCollapsed.outcomeSpace }">
              <div class="panel-header-collapsible" @click="togglePanel('outcomeSpace')">
                <h3 class="panel-title">
                  <span class="collapse-icon">{{ panelsCollapsed.outcomeSpace ? '▶' : '▼' }}</span>
                  Outcome Space
                </h3>
                <div class="panel-header-actions" @click.stop>
                  <button 
                    v-if="scenarioFiles?.domain_file" 
                    class="btn-secondary btn-sm" 
                    @click="openFileEditor(scenarioFiles.domain_file, 'Domain')"
                    title="Edit domain file to modify outcome space"
                  >
                    Edit Domain
                  </button>
                  <button 
                    v-if="selectedScenario.issues && selectedScenario.issues.length > 0"
                    class="btn-text btn-sm" 
                    @click="showIssueValues = !showIssueValues"
                  >
                    {{ showIssueValues ? 'Hide Values' : 'Show Values' }}
                  </button>
                </div>
              </div>
              
              <div v-if="!panelsCollapsed.outcomeSpace" class="panel-content">
                <div v-if="selectedScenario.issues && selectedScenario.issues.length > 0" class="issues-list-compact">
                  <div v-for="(issue, idx) in selectedScenario.issues" :key="idx" class="issue-item-compact">
                    <div class="issue-header-compact">
                      <span class="issue-name">{{ issue.name }}</span>
                      <span class="issue-meta-compact">
                        <span class="issue-type badge">{{ issue.type }}</span>
                        <span v-if="issue.values && issue.values.length > 0" class="issue-count">
                          {{ issue.values.length }} values
                        </span>
                        <span v-else-if="issue.min_value !== null && issue.max_value !== null" class="issue-range">
                          [{{ issue.min_value }}, {{ issue.max_value }}]
                        </span>
                      </span>
                    </div>
                    <div v-if="showIssueValues && issue.values && issue.values.length > 0" class="issue-values">
                      <div class="values-grid-compact">
                        <span v-for="(value, vIdx) in issue.values.slice(0, 30)" :key="vIdx" class="value-chip-compact">
                          {{ value }}
                        </span>
                        <span v-if="issue.values.length > 30" class="value-more">
                          +{{ issue.values.length - 30 }} more...
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="panel-empty">
                  <p>No outcome space information available</p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Right Column -->
          <div class="details-column">
            <!-- Utility Functions Panel (Top) -->
            <div class="panel collapsible-panel" :class="{ collapsed: panelsCollapsed.ufuns }">
              <div class="panel-header-collapsible" @click="togglePanel('ufuns')">
                <h3 class="panel-title">
                  <span class="collapse-icon">{{ panelsCollapsed.ufuns ? '▶' : '▼' }}</span>
                  Utility Functions
                </h3>
                <div class="panel-header-actions" @click.stop v-if="scenarioFiles?.domain_file && !selectedScenario?.readonly">
                  <button 
                    class="btn-secondary btn-sm" 
                    @click="openFileEditor(scenarioFiles.domain_file, 'Domain')"
                    title="Edit domain file"
                  >
                    Edit Domain
                  </button>
                </div>
                <div class="panel-header-actions" v-if="selectedScenario?.readonly">
                  <span class="readonly-badge" title="This scenario is from a read-only source">Read-Only</span>
                </div>
              </div>
              
              <div v-if="!panelsCollapsed.ufuns" class="panel-content">
                <div v-if="ufunDetails.length > 0" class="ufuns-info">
                  <div v-for="(ufun, idx) in ufunDetails" :key="idx" class="ufun-item">
                    <div class="ufun-header">
                      <div class="ufun-title-row">
                        <span class="ufun-name">{{ ufun.name || `Negotiator ${idx + 1}` }}</span>
                        <span class="ufun-type badge">{{ ufun.type }}</span>
                      </div>
                      <button 
                        v-if="ufun.file_path && !selectedScenario?.readonly" 
                        class="btn-edit-ufun" 
                        @click="openFileEditor(ufun.file_path, ufun.name)"
                        title="Edit utility function file"
                      >
                        Edit
                      </button>
                    </div>
                    <div class="ufun-details">
                      <span v-if="selectedScenarioPlotData?.reserved_values && selectedScenarioPlotData.reserved_values[idx] !== null" class="ufun-meta">
                        Reserved Value: {{ selectedScenarioPlotData.reserved_values[idx].toFixed(3) }}
                      </span>
                      <span v-if="selectedScenarioStats && selectedScenarioStats.nash_utils" class="ufun-meta">
                        Nash Util: {{ selectedScenarioStats.nash_utils[0]?.[idx]?.toFixed(3) || 'N/A' }}
                      </span>
                    </div>
                    
                    <!-- Display negmas string representation -->
                    <div v-if="ufun.string_representation" class="ufun-representation">
                      <pre>{{ ufun.string_representation }}</pre>
                    </div>
                  </div>
                </div>
                <div v-else-if="selectedScenarioStats?.negotiator_names" class="ufuns-info">
                  <div v-for="(name, idx) in selectedScenarioStats.negotiator_names" :key="idx" class="ufun-item">
                    <div class="ufun-header">
                      <span class="ufun-name">{{ name || `Negotiator ${idx + 1}` }}</span>
                    </div>
                    <div class="ufun-details">
                      <span v-if="selectedScenarioPlotData?.reserved_values && selectedScenarioPlotData.reserved_values[idx] !== null" class="ufun-meta">
                        Reserved Value: {{ selectedScenarioPlotData.reserved_values[idx].toFixed(3) }}
                      </span>
                      <span v-if="selectedScenarioStats && selectedScenarioStats.nash_utils" class="ufun-meta">
                        Nash Util: {{ selectedScenarioStats.nash_utils[0]?.[idx]?.toFixed(3) || 'N/A' }}
                      </span>
                    </div>
                  </div>
                </div>
                <div v-else-if="selectedScenario.n_negotiators" class="ufuns-info">
                  <div v-for="idx in selectedScenario.n_negotiators" :key="idx" class="ufun-item">
                    <div class="ufun-header">
                      <span class="ufun-name">Negotiator {{ idx }}</span>
                    </div>
                    <div class="ufun-details">
                      <span class="ufun-meta text-secondary">Load stats to see utility details</span>
                    </div>
                  </div>
                </div>
                <div v-else class="panel-empty">
                  <p>No utility function information available</p>
                </div>
              </div>
            </div>
            
            <!-- Visualization Panel (Bottom) -->
            <div class="panel collapsible-panel" :class="{ collapsed: panelsCollapsed.visualization }">
              <div class="panel-header-collapsible" @click="togglePanel('visualization')">
                <h3 class="panel-title">
                  <span class="collapse-icon">{{ panelsCollapsed.visualization ? '▶' : '▼' }}</span>
                  2D Utility View
                </h3>
                <div class="panel-header-actions" @click.stop>
                  <label v-if="plotDataLoaded" class="plot-mode-toggle">
                    <input type="checkbox" v-model="useInteractivePlot" />
                    <span>Interactive</span>
                  </label>
                  <button 
                    v-if="plotDataLoaded" 
                    class="btn-secondary btn-sm" 
                    @click="refreshPlot"
                    :title="useInteractivePlot ? 'Regenerate interactive plot' : 'Regenerate cached image'"
                  >
                    Refresh
                  </button>
                </div>
              </div>
              
              <div v-if="!panelsCollapsed.visualization" class="panel-content">
                <div v-if="!plotDataLoaded && !loadingPlotData" class="panel-empty">
                  <p>Click to load visualization</p>
                  <button class="btn-primary btn-sm" @click="loadPlotData">Load Visualization</button>
                </div>
                
                <div v-else-if="loadingPlotData" class="loading-state">
                  <span class="spinner"></span> Loading visualization...
                </div>
                
                <div v-else-if="selectedScenarioPlotData" class="plot-container-compact">
                  <!-- Cached WebP Image (default) -->
                  <div v-if="!useInteractivePlot && plotImageUrl" class="plot-image-container-compact">
                    <!-- Plot selector for multilateral scenarios -->
                    <div v-if="isMultilateral && availablePlots?.plots?.length > 1" class="plot-selector-compact">
                      <label>Plot:</label>
                      <select v-model="selectedPlotName" class="input-select">
                        <option v-for="plot in availablePlots.plots" :key="plot.name" :value="plot.name">
                          {{ plot.name }}
                        </option>
                      </select>
                    </div>
                    
                    <div class="plot-image-wrapper">
                      <img :src="plotImageUrl" :key="plotImageUrl" alt="Scenario Plot" class="plot-image-compact" />
                    </div>
                    <p class="plot-hint">Toggle "Interactive" for customizable view</p>
                    <p class="plot-warning" v-if="selectedScenario.n_negotiators > 2" title="For multilateral scenarios, cached plots show solution points (Nash, Kalai, etc.) calculated for only the 2 displayed negotiators, while interactive plots show the global solution points projected onto the 2D view">
                      ⚠ Multilateral: Solution points may differ between cached and interactive views
                    </p>
                  </div>
                  
                  <!-- Interactive Plotly Plot -->
                  <div v-else class="plot-interactive-container-compact">
                    <!-- Negotiator Selection -->
                    <div class="plot-controls-compact" v-if="negotiatorNamesForPlot && negotiatorNamesForPlot.length > 1">
                      <label>X:</label>
                      <select v-model="plotNegotiator1" @change="renderPlot" class="input-select">
                        <option v-for="(name, idx) in negotiatorNamesForPlot" :key="idx" :value="idx">
                          {{ name }}
                        </option>
                      </select>
                      <label>Y:</label>
                      <select v-model="plotNegotiator2" @change="renderPlot" class="input-select">
                        <option v-for="(name, idx) in negotiatorNamesForPlot" :key="idx" :value="idx">
                          {{ name }}
                        </option>
                      </select>
                    </div>
                    <div ref="plotDiv" class="plot-compact"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- New Negotiation Modal (teleported to body to avoid overflow clipping) -->
    <Teleport to="body">
      <NewNegotiationModal
        :show="showNewNegotiationModal"
        :preselected-scenario="selectedScenario"
        @close="showNewNegotiationModal = false"
        @start="onNegotiationStart"
      />
    </Teleport>
    
    <!-- File Editor Modal -->
    <Teleport to="body">
      <FileEditorModal
        :show="showFileEditor"
        :scenario-id="selectedScenario?.id"
        :file-path="editingFile"
        :title="`Edit ${editingFileTitle}`"
        @close="showFileEditor = false"
        @saved="onFileSaved"
      />
    </Teleport>
    
    <!-- Save Filter Dialog -->
    <Teleport to="body">
      <div v-if="showSaveFilterDialog" class="modal-overlay" @click="showSaveFilterDialog = false">
        <div class="modal save-filter-modal" @click.stop>
          <div class="modal-header">
            <h3>Save Current Filter</h3>
            <button class="btn-close" @click="showSaveFilterDialog = false">×</button>
          </div>
          
          <div class="modal-body">
            <div class="form-group">
              <label>Filter Name</label>
              <input
                v-model="saveFilterName"
                type="text"
                class="input-text"
                placeholder="e.g., ANAC Bilateral Scenarios"
                @keyup.enter="saveCurrentFilter"
              />
            </div>
            
            <div class="form-group">
              <label>Description (optional)</label>
              <textarea
                v-model="saveFilterDescription"
                class="input-text"
                rows="3"
                placeholder="Optional description for this filter"
              ></textarea>
            </div>
            
            <p v-if="saveFilterError" class="error-message">{{ saveFilterError }}</p>
            <p v-if="saveFilterSuccess" class="success-message">{{ saveFilterSuccess }}</p>
          </div>
          
          <div class="modal-footer">
            <button class="btn-secondary" @click="showSaveFilterDialog = false">Cancel</button>
            <button
              class="btn-primary"
              @click="saveCurrentFilter"
              :disabled="!saveFilterName || savingFilter"
            >
              <span v-if="savingFilter">Saving...</span>
              <span v-else>Save Filter</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useScenariosStore } from '../stores/scenarios'
import { useNegotiationsStore } from '../stores/negotiations'
import { storeToRefs } from 'pinia'
import Plotly from 'plotly.js-dist-min'
import NewNegotiationModal from '../components/NewNegotiationModal.vue'
import FileEditorModal from '../components/FileEditorModal.vue'

const scenariosStore = useScenariosStore()
const negotiationsStore = useNegotiationsStore()
const {
  scenarios,
  sources,
  selectedScenario,
  selectedScenarioStats,
  selectedScenarioPlotData,
  loading,
  loadingStats,
  loadingPlotData,
  filter,
  filteredScenarios,
} = storeToRefs(scenariosStore)

// Local state for inputs (to avoid direct mutation of store)
const localSearch = ref('')
const localSource = ref('')
const showAdvancedFilters = ref(false)
const localFilters = ref({
  minOutcomes: null,
  maxOutcomes: null,
  minNegotiators: null,
  maxNegotiators: null,
  minOpposition: null,
  maxOpposition: null,
  minRationalFraction: null,
  maxRationalFraction: null,
  normalized: null,
  anac: null,
  file: null,
  format: '',
  reverseFilter: false,
})

const plotDiv = ref(null)
const plotNegotiator1 = ref(0)
const plotNegotiator2 = ref(1)
const useInteractivePlot = ref(false) // Default to cached PNG
const refreshingCache = ref(false)
const availablePlots = ref(null)
const selectedPlotName = ref(null)
const showOutcomes = ref(false) // Hide outcomes by default to save space
const showIssueValues = ref(false) // Hide issue values by default

// UFun details and file editor state
const ufunDetails = ref([])
const scenarioFiles = ref(null)
const showFileEditor = ref(false)
const editingFile = ref(null)
const editingFileTitle = ref('')

// Status dropdown state
const showStatusDropdown = ref(false)
const showBulkActionsMenu = ref(false)

// Collapsible panel states
const panelsCollapsed = ref({
  info: false,
  stats: false,
  outcomeSpace: false,
  ufuns: false,
  visualization: false,
})

function togglePanel(panelName) {
  panelsCollapsed.value[panelName] = !panelsCollapsed.value[panelName]
}

// Filter save/load state
const showSaveFilterDialog = ref(false)
const saveFilterName = ref('')
const saveFilterDescription = ref('')
const savingFilter = ref(false)
const saveFilterError = ref('')
const saveFilterSuccess = ref('')
const savedFilters = ref([])
const selectedFilterId = ref('')
const plotCacheBuster = ref(Date.now()) // Timestamp to force browser to reload plot images

const plotImageUrl = computed(() => {
  if (!selectedScenario.value) return null
  const basePath = `/api/scenarios/${selectedScenario.value.id}/plot-image`
  const params = new URLSearchParams()
  
  if (selectedPlotName.value) {
    params.set('plot_name', selectedPlotName.value)
  }
  
  // Add cache buster to prevent browser from using stale cached images
  params.set('_t', plotCacheBuster.value.toString())
  
  return `${basePath}?${params.toString()}`
})
const showNewNegotiationModal = ref(false)
const router = useRouter()
const registrationStatus = ref({
  registered: false,
  in_progress: false,
  progress: { total: 0, current: 0, status: 'not_started' },
  total_scenarios: 0
})
let registrationPollInterval = null

// Computed properties
const registrationProgress = computed(() => {
  const { total, current } = registrationStatus.value.progress
  if (total === 0) return 0
  return Math.round((current / total) * 100)
})

const statsLoaded = computed(() => selectedScenarioStats.value !== null)
const plotDataLoaded = computed(() => selectedScenarioPlotData.value !== null)
const isMultilateral = computed(() => availablePlots.value?.type === 'multilateral')
const negotiatorNamesForPlot = computed(() => {
  // Prefer stats negotiator_names, fallback to plot data negotiator_names
  if (selectedScenarioStats.value?.negotiator_names) {
    return selectedScenarioStats.value.negotiator_names
  }
  if (selectedScenarioPlotData.value?.negotiator_names) {
    return selectedScenarioPlotData.value.negotiator_names
  }
  return []
})

// Load data on mount
onMounted(async () => {
  // Start polling registration status
  await checkRegistrationStatus()
  startRegistrationPolling()
  
  await loadData()
  await loadSavedFilters()
  await loadDefaultFilter()
})

onBeforeUnmount(() => {
  // Stop polling when component unmounts
  if (registrationPollInterval) {
    clearInterval(registrationPollInterval)
  }
})

async function checkRegistrationStatus() {
  try {
    const response = await fetch('/api/scenarios/registration-status')
    const data = await response.json()
    registrationStatus.value = data
    
    // If registration is complete, stop polling
    if (data.registered && registrationPollInterval) {
      clearInterval(registrationPollInterval)
      registrationPollInterval = null
    }
  } catch (error) {
    console.error('Failed to check registration status:', error)
  }
}

function startRegistrationPolling() {
  // Poll every 500ms while registration is in progress
  registrationPollInterval = setInterval(async () => {
    await checkRegistrationStatus()
  }, 500)
}

async function loadData() {
  await Promise.all([
    scenariosStore.loadSources(),
    scenariosStore.loadScenarios(),
  ])
}

async function loadDefaultFilter() {
  try {
    const response = await fetch('/api/filters/default/scenario')
    const data = await response.json()
    
    if (data.success && data.filter) {
      // Apply default filter
      const filterData = data.filter.data
      localSearch.value = filterData.search || ''
      localSource.value = filterData.source || ''
      localFilters.value = {
        minOutcomes: filterData.minOutcomes || null,
        maxOutcomes: filterData.maxOutcomes || null,
        minNegotiators: filterData.minNegotiators || null,
        maxNegotiators: filterData.maxNegotiators || null,
        minOpposition: filterData.minOpposition || null,
        maxOpposition: filterData.maxOpposition || null,
        minRationalFraction: filterData.minRationalFraction || null,
        maxRationalFraction: filterData.maxRationalFraction || null,
        normalized: filterData.normalized || '',
        anac: filterData.anac || '',
        file: filterData.file || '',
        format: filterData.format || '',
        reverseFilter: filterData.reverseFilter ?? false,
      }
      
      // Update store with default filter
      scenariosStore.updateFilter({
        search: localSearch.value,
        source: localSource.value,
        ...localFilters.value
      })
      
      // Reload scenarios if source changed
      if (localSource.value) {
        scenariosStore.loadScenarios(localSource.value)
      }
    }
  } catch (error) {
    console.error('Failed to load default filter:', error)
  }
}

function updateSearch() {
  scenariosStore.updateFilter({ search: localSearch.value })
}

function updateSourceFilter() {
  scenariosStore.updateFilter({ source: localSource.value })
  scenariosStore.loadScenarios(localSource.value)
}

function updateFilters() {
  scenariosStore.updateFilter(localFilters.value)
}

function clearFilters() {
  localSearch.value = ''
  localSource.value = ''
  localFilters.value = {
    minOutcomes: null,
    maxOutcomes: null,
    minNegotiators: null,
    maxNegotiators: null,
    minOpposition: null,
    maxOpposition: null,
    minRationalFraction: null,
    maxRationalFraction: null,
    normalized: null,
    anac: null,
    file: null,
    format: '',
    reverseFilter: false,
  }
  scenariosStore.updateFilter({
    search: '',
    source: '',
    ...localFilters.value,
  })
}

// Filter save/load functions
async function loadSavedFilters() {
  try {
    const response = await fetch('/api/filters?type=scenario')
    const data = await response.json()
    if (data.success) {
      savedFilters.value = data.filters
    }
  } catch (error) {
    console.error('Failed to load saved filters:', error)
  }
}

async function saveCurrentFilter() {
  if (!saveFilterName.value) return
  
  saveFilterError.value = ''
  saveFilterSuccess.value = ''
  savingFilter.value = true
  
  try {
    const filterData = {
      search: localSearch.value,
      source: localSource.value,
      ...localFilters.value,
    }
    
    const response = await fetch('/api/filters', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: saveFilterName.value,
        type: 'scenario',
        data: filterData,
        description: saveFilterDescription.value,
      }),
    })
    
    const data = await response.json()
    
    if (data.success) {
      saveFilterSuccess.value = 'Filter saved successfully!'
      // Reload saved filters
      await loadSavedFilters()
      // Clear form after 1.5 seconds
      setTimeout(() => {
        showSaveFilterDialog.value = false
        saveFilterName.value = ''
        saveFilterDescription.value = ''
        saveFilterError.value = ''
        saveFilterSuccess.value = ''
      }, 1500)
    } else {
      saveFilterError.value = 'Failed to save filter: ' + (data.error || 'Unknown error')
    }
  } catch (error) {
    saveFilterError.value = 'Failed to save filter: ' + error.message
  } finally {
    savingFilter.value = false
  }
}

async function loadSavedFilter() {
  if (!selectedFilterId.value) return
  
  try {
    const response = await fetch(`/api/filters/${selectedFilterId.value}`)
    const data = await response.json()
    
    if (data.success && data.filter) {
      const filterData = data.filter.data
      
      // Apply filter data to local state
      localSearch.value = filterData.search || ''
      localSource.value = filterData.source || ''
      localFilters.value = {
        minOutcomes: filterData.minOutcomes ?? null,
        maxOutcomes: filterData.maxOutcomes ?? null,
        minNegotiators: filterData.minNegotiators ?? null,
        maxNegotiators: filterData.maxNegotiators ?? null,
        minOpposition: filterData.minOpposition ?? null,
        maxOpposition: filterData.maxOpposition ?? null,
        minRationalFraction: filterData.minRationalFraction ?? null,
        maxRationalFraction: filterData.maxRationalFraction ?? null,
        normalized: filterData.normalized ?? null,
        anac: filterData.anac ?? null,
        file: filterData.file ?? null,
        format: filterData.format || '',
        reverseFilter: filterData.reverseFilter ?? false,
      }
      
      // Update store
      scenariosStore.updateFilter({
        search: localSearch.value,
        source: localSource.value,
        ...localFilters.value,
      })
      
      // If source changed, reload scenarios
      if (localSource.value) {
        await scenariosStore.loadScenarios(localSource.value)
      }
    }
    
    // Reset selection after loading
    selectedFilterId.value = ''
  } catch (error) {
    console.error('Failed to load filter:', error)
    alert('Failed to load filter: ' + error.message)
  }
}

async function selectScenario(scenario) {
  // First, load full scenario details (includes issues)
  try {
    const response = await fetch(`/api/scenarios/${scenario.id}/info`)
    const data = await response.json()
    if (data) {
      // Update scenario with full details
      Object.assign(scenario, data)
    }
  } catch (error) {
    console.error('Failed to load scenario details:', error)
  }
  
  scenariosStore.selectScenario(scenario)
  
  // Reset plot selection and update cache buster for fresh plot
  availablePlots.value = null
  selectedPlotName.value = null
  plotCacheBuster.value = Date.now()
  
  // Reset ufun details
  ufunDetails.value = []
  scenarioFiles.value = null
  
  // Load available plots
  await loadAvailablePlots()
  
  // Load ufun details
  await loadUfunDetails()
  
  // Auto-load stats when selecting a scenario
  if (scenario.has_stats) {
    await scenariosStore.loadScenarioStats(scenario.id)
  }
  // Auto-load plot data
  await scenariosStore.loadScenarioPlotData(scenario.id)
}

async function loadStats() {
  if (!selectedScenario.value) return
  if (selectedScenarioStats.value) return // Already loaded
  
  await scenariosStore.loadScenarioStats(selectedScenario.value.id)
}

async function loadUfunDetails() {
  if (!selectedScenario.value) return
  
  try {
    const response = await fetch(`/api/scenarios/${selectedScenario.value.id}/ufuns`)
    const data = await response.json()
    if (data.success) {
      ufunDetails.value = data.ufuns
      scenarioFiles.value = data.files
    } else {
      console.error('Failed to load ufun details:', data.error)
      ufunDetails.value = []
      scenarioFiles.value = null
    }
  } catch (error) {
    console.error('Failed to load ufun details:', error)
    ufunDetails.value = []
    scenarioFiles.value = null
  }
}

function openFileEditor(filePath, title) {
  editingFile.value = filePath
  editingFileTitle.value = title
  showFileEditor.value = true
}

async function onFileSaved() {
  // Only reload the currently selected scenario's details, not all scenarios
  // This is much faster - we don't need to reload the entire list
  if (selectedScenario.value) {
    // Update plot cache buster to force browser to reload image
    plotCacheBuster.value = Date.now()
    
    // Reload detailed info for this scenario
    await selectScenario(selectedScenario.value)
    
    // Reload ufun details (they may have changed)
    await loadUfunDetails()
  }
}

async function loadAvailablePlots() {
  if (!selectedScenario.value) return
  
  try {
    const response = await fetch(`/api/scenarios/${selectedScenario.value.id}/available-plots`)
    const data = await response.json()
    availablePlots.value = data
    
    // Set default selected plot (first one)
    if (data.plots && data.plots.length > 0) {
      selectedPlotName.value = data.plots[0].name
    }
  } catch (error) {
    console.error('Failed to load available plots:', error)
    availablePlots.value = null
  }
}

async function calculateStats() {
  if (!selectedScenario.value) return
  await scenariosStore.calculateScenarioStats(selectedScenario.value.id, true)
}

async function refreshAllCaches() {
  if (!selectedScenario.value) return
  
  refreshingCache.value = true
  try {
    const scenarioId = selectedScenario.value.id
    const scenarioPath = selectedScenario.value.path
    
    // Recalculate stats with force=true (respects max_outcomes_pareto and max_outcomes_rationality from settings)
    await scenariosStore.calculateScenarioStats(scenarioId, true)
    
    // Regenerate plot with force_regenerate=true
    await loadPlotData(true)
    
    // Reload scenario list to get updated info (has_stats, etc.)
    await scenariosStore.loadScenarios()
    
    // Find and re-select the scenario to update the UI
    const updatedScenario = scenariosStore.scenarios.find(s => s.path === scenarioPath)
    if (updatedScenario) {
      // Update selectedScenario with new metadata
      selectedScenario.value = updatedScenario
      
      // Reload stats from the refreshed cache
      await scenariosStore.loadScenarioStats(scenarioId)
      
      // Reload plot data from the refreshed cache
      await loadPlotData(false) // false because we already regenerated above
    }
  } catch (error) {
    console.error('Failed to refresh caches:', error)
  } finally {
    refreshingCache.value = false
  }
}

async function openScenarioFolder() {
  if (!selectedScenario.value) return
  
  try {
    const response = await fetch(`/api/scenarios/${selectedScenario.value.id}/open-folder`, {
      method: 'POST',
    })
    
    if (!response.ok) {
      throw new Error('Failed to open folder')
    }
  } catch (error) {
    console.error('Failed to open scenario folder:', error)
    alert('Failed to open scenario folder. See console for details.')
  }
}

async function loadPlotData(forceRegenerate = false) {
  if (!selectedScenario.value) return
  
  // Update cache buster when regenerating plot
  if (forceRegenerate) {
    plotCacheBuster.value = Date.now()
  }
  
  await scenariosStore.loadScenarioPlotData(selectedScenario.value.id, 10000, forceRegenerate)
}

async function refreshPlot() {
  // Force regenerate the plot (both cached image and interactive data)
  plotCacheBuster.value = Date.now()
  await loadPlotData(true)
}

// Watch for plot data changes and render plot
watch(selectedScenarioPlotData, async (data) => {
  if (data && useInteractivePlot.value) {
    await nextTick()
    if (plotDiv.value) {
      renderPlot()
    }
  }
})

// Watch for interactive mode changes
watch(useInteractivePlot, async (isInteractive) => {
  if (isInteractive && selectedScenarioPlotData.value) {
    await nextTick()
    // Check plotDiv after DOM update
    if (plotDiv.value) {
      renderPlot()
    }
  }
})

// Watch for stats changes and render plot if plot data is loaded
watch(selectedScenarioStats, async (stats) => {
  if (stats && selectedScenarioPlotData.value && useInteractivePlot.value) {
    await nextTick()
    if (plotDiv.value) {
      renderPlot()
    }
  }
})

function renderPlot() {
  const data = selectedScenarioPlotData.value
  if (!plotDiv.value) {
    console.warn('renderPlot: plotDiv not available')
    return
  }
  if (!data) {
    console.warn('renderPlot: no plot data')
    return
  }
  if (!data.outcome_utilities) {
    console.warn('renderPlot: no outcome_utilities in data')
    return
  }
  
  const utilities = data.outcome_utilities
  const stats = selectedScenarioStats.value
  const names = negotiatorNamesForPlot.value
  
  // Use selected negotiators for axes
  const idx1 = plotNegotiator1.value
  const idx2 = plotNegotiator2.value
  
  // Extract utilities for selected negotiators
  const x = utilities.map(u => u[idx1])
  const y = utilities.map(u => u[idx2])
  
  // Create main scatter trace
  const trace = {
    x: x,
    y: y,
    mode: 'markers',
    type: 'scatter',
    marker: { size: 3, color: 'rgba(59, 130, 246, 0.3)' },
    name: 'Outcomes',
    hovertemplate: `${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                   `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
  }
  
  const traces = [trace]
  
  // Add Pareto frontier if available in stats
  if (stats?.pareto_utils && stats.pareto_utils.length > 0) {
    const paretoX = stats.pareto_utils.map(u => u[idx1])
    const paretoY = stats.pareto_utils.map(u => u[idx2])
    traces.push({
      x: paretoX,
      y: paretoY,
      mode: 'markers',
      type: 'scatter',
      marker: { size: 4, color: 'red', symbol: 'circle' },
      name: 'Pareto',
      hovertemplate: `Pareto<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add Nash point if available
  // Using markers from negmas/src/negmas/plots/util.py (NASH_MARKER, NASH_COLOR)
  if (stats?.nash_utils && stats.nash_utils.length > 0) {
    traces.push({
      x: stats.nash_utils.map(u => u[idx1]),
      y: stats.nash_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { 
        size: 14, 
        color: 'rgba(0,0,0,0)', 
        symbol: 'triangle-left',
        line: { color: 'brown', width: 2.5 }
      },
      name: 'Nash',
      hovertemplate: `Nash<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add Kalai point if available
  // Using markers from negmas/src/negmas/plots/util.py (KALAI_MARKER, KALAI_COLOR)
  if (stats?.kalai_utils && stats.kalai_utils.length > 0) {
    traces.push({
      x: stats.kalai_utils.map(u => u[idx1]),
      y: stats.kalai_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { 
        size: 14, 
        color: 'rgba(0,0,0,0)', 
        symbol: 'triangle-down',
        line: { color: 'green', width: 2.5 }
      },
      name: 'Kalai',
      hovertemplate: `Kalai<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add KS point if available
  // Using markers from negmas/src/negmas/plots/util.py (KS_MARKER, KS_COLOR)
  if (stats?.ks_utils && stats.ks_utils.length > 0) {
    traces.push({
      x: stats.ks_utils.map(u => u[idx1]),
      y: stats.ks_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { 
        size: 14, 
        color: 'rgba(0,0,0,0)', 
        symbol: 'triangle-up',
        line: { color: 'cyan', width: 2.5 }
      },
      name: 'KS',
      hovertemplate: `KS<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add Max Welfare point if available
  // Using markers from negmas/src/negmas/plots/util.py (WELFARE_MARKER, WELFARE_COLOR)
  if (stats?.max_welfare_utils && stats.max_welfare_utils.length > 0) {
    traces.push({
      x: stats.max_welfare_utils.map(u => u[idx1]),
      y: stats.max_welfare_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { 
        size: 14, 
        color: 'rgba(0,0,0,0)', 
        symbol: 'triangle-right',
        line: { color: 'blue', width: 2.5 }
      },
      name: 'MaxWelfare',
      hovertemplate: `Max Welfare<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add reservation value lines if available
  const shapes = []
  if (data.reserved_values && data.reserved_values.length > 0) {
    const reservedVal1 = data.reserved_values[idx1]
    const reservedVal2 = data.reserved_values[idx2]
    
    // Vertical line for negotiator 1's reservation value (idx1)
    if (reservedVal1 !== null && reservedVal1 !== undefined && !isNaN(reservedVal1) && isFinite(reservedVal1)) {
      shapes.push({
        type: 'line',
        x0: reservedVal1,
        x1: reservedVal1,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: {
          color: 'red',
          width: 2,
          dash: 'dash'
        }
      })
    }
    
    // Horizontal line for negotiator 2's reservation value (idx2)
    if (reservedVal2 !== null && reservedVal2 !== undefined && !isNaN(reservedVal2) && isFinite(reservedVal2)) {
      shapes.push({
        type: 'line',
        x0: 0,
        x1: 1,
        xref: 'paper',
        y0: reservedVal2,
        y1: reservedVal2,
        line: {
          color: 'red',
          width: 2,
          dash: 'dash'
        }
      })
    }
  }
  
  const layout = {
    xaxis: { title: names[idx1] || `Negotiator ${idx1}` },
    yaxis: { 
      title: names[idx2] || `Negotiator ${idx2}`,
      scaleanchor: 'x',
      scaleratio: 1
    },
    hovermode: 'closest',
    margin: { l: 60, r: 20, t: 30, b: 60 },
    showlegend: true,
    legend: { x: 1, y: 1, xanchor: 'right' },
    shapes: shapes
  }
  
  Plotly.newPlot(plotDiv.value, traces, layout, { responsive: true })
}

function formatUtilityList(utils) {
  if (!utils || !Array.isArray(utils)) return 'N/A'
  return '(' + utils.map(u => u.toFixed(3)).join(', ') + ')'
}

function formatOutcome(outcome) {
  if (!outcome || typeof outcome !== 'object') return 'N/A'
  // Format as "Issue1: Value1, Issue2: Value2, ..."
  return Object.entries(outcome)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ')
}

function openNewNegotiation() {
  console.log('openNewNegotiation called, current value:', showNewNegotiationModal.value)
  showNewNegotiationModal.value = true
  console.log('openNewNegotiation set to:', showNewNegotiationModal.value)
}

function onNegotiationStart(data) {
  if (data.session_id) {
    // Navigate to single negotiation view (polling will start automatically)
    router.push({
      name: 'SingleNegotiation',
      params: { id: data.session_id }
    })
  }
}

function formatNumber(num) {
  if (num === null || num === undefined) return 'N/A'
  if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
  return num.toString()
}

// Status management functions
function getStatusLabel(status) {
  switch (status) {
    case 'disabled':
      return '⊘ Disabled'
    case 'archived':
      return '📦 Archived'
    default:
      return '✓ Enabled'
  }
}

function toggleStatusDropdown() {
  showStatusDropdown.value = !showStatusDropdown.value
}

// Close dropdown when clicking outside
onMounted(() => {
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.status-dropdown')) {
      showStatusDropdown.value = false
    }
    if (!e.target.closest('.bulk-actions')) {
      showBulkActionsMenu.value = false
    }
  })
})

async function updateScenarioStatus(newStatus) {
  if (!selectedScenario.value) return
  
  try {
    const response = await fetch(`/api/scenarios/${selectedScenario.value.id}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update status')
    }
    
    // Update local state
    selectedScenario.value.status = newStatus
    
    // Reload scenarios list to reflect status change
    await loadData()
    
    showStatusDropdown.value = false
  } catch (error) {
    console.error('Failed to update scenario status:', error)
    alert(`Failed to update status: ${error.message}`)
  }
}

async function deleteScenario() {
  if (!selectedScenario.value) return
  
  const scenarioName = selectedScenario.value.name
  const confirmed = confirm(
    `Are you sure you want to delete "${scenarioName}"?\n\n` +
    `This will permanently delete the scenario from disk. This action cannot be undone.`
  )
  
  if (!confirmed) return
  
  try {
    const response = await fetch(`/api/scenarios/${selectedScenario.value.id}`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to delete scenario')
    }
    
    // Clear selection
    scenariosStore.selectScenario(null)
    
    // Reload scenarios list
    await loadData()
    
    alert(`Scenario "${scenarioName}" deleted successfully`)
  } catch (error) {
    console.error('Failed to delete scenario:', error)
    alert(`Failed to delete scenario: ${error.message}`)
  }
}

// Bulk operations
async function bulkUpdateStatus(newStatus) {
  showBulkActionsMenu.value = false
  
  const count = filteredScenarios.value.length
  const statusLabel = getStatusLabel(newStatus).toLowerCase()
  
  const confirmed = confirm(
    `Are you sure you want to ${statusLabel.replace(/[✓⊘📦]\s/, '')} ${count} scenario${count !== 1 ? 's' : ''}?`
  )
  
  if (!confirmed) return
  
  try {
    const paths = filteredScenarios.value.map(s => s.path)
    
    const response = await fetch('/api/scenarios/bulk-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths, status: newStatus })
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update statuses')
    }
    
    const result = await response.json()
    
    // Reload scenarios list
    await loadData()
    
    alert(
      `Successfully updated ${result.successful} scenario${result.successful !== 1 ? 's' : ''}.` +
      (result.failed > 0 ? `\n${result.failed} failed.` : '')
    )
  } catch (error) {
    console.error('Failed to bulk update statuses:', error)
    alert(`Failed to update statuses: ${error.message}`)
  }
}

async function bulkDelete() {
  showBulkActionsMenu.value = false
  
  const count = filteredScenarios.value.length
  const readonlyCount = filteredScenarios.value.filter(s => s.readonly).length
  
  if (readonlyCount === count) {
    alert('All filtered scenarios are read-only and cannot be deleted.')
    return
  }
  
  const deletableCount = count - readonlyCount
  const message = readonlyCount > 0
    ? `This will permanently delete ${deletableCount} scenario${deletableCount !== 1 ? 's' : ''} from disk.\n(${readonlyCount} read-only scenario${readonlyCount !== 1 ? 's' : ''} will be skipped)\n\nThis action cannot be undone. Are you sure?`
    : `This will permanently delete ${count} scenario${count !== 1 ? 's' : ''} from disk.\n\nThis action cannot be undone. Are you sure?`
  
  const confirmed = confirm(message)
  
  if (!confirmed) return
  
  try {
    // Filter out readonly scenarios
    const paths = filteredScenarios.value
      .filter(s => !s.readonly)
      .map(s => s.path)
    
    const response = await fetch('/api/scenarios/bulk-delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths })
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to delete scenarios')
    }
    
    const result = await response.json()
    
    // Clear selection if it was deleted
    if (selectedScenario.value && paths.includes(selectedScenario.value.path)) {
      scenariosStore.selectScenario(null)
    }
    
    // Reload scenarios list
    await loadData()
    
    alert(
      `Successfully deleted ${result.successful} scenario${result.successful !== 1 ? 's' : ''}.` +
      (result.failed > 0 ? `\n${result.failed} failed.` : '')
    )
  } catch (error) {
    console.error('Failed to bulk delete:', error)
    alert(`Failed to delete scenarios: ${error.message}`)
  }
}


</script>

<style scoped>
/* Registration Loading Overlay */
.registration-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.registration-modal {
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  padding: 32px;
  min-width: 400px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.registration-modal h3 {
  margin: 0 0 12px 0;
  font-size: 1.5rem;
  color: var(--color-primary);
}

.registration-modal p {
  margin: 8px 0;
  color: var(--text-secondary);
}

.progress-bar {
  width: 100%;
  height: 24px;
  background: var(--bg-primary);
  border-radius: 12px;
  overflow: hidden;
  margin: 20px 0;
  border: 1px solid var(--border-color);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-success));
  transition: width 0.3s ease;
  border-radius: 12px;
}

.progress-text {
  font-size: 0.95rem;
  color: var(--text-primary);
  font-weight: 500;
}

.scenarios-view {
  display: grid;
  grid-template-columns: 350px 1fr;
  height: 100%;
  gap: 8px;
  padding: 16px;
  overflow: hidden;
}

.scenarios-list-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.input-search,
.input-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-range {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.85rem;
}

/* List header with count and bulk actions */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  margin-bottom: 8px;
}

.list-count {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.bulk-actions {
  position: relative;
}

.btn-icon {
  padding: 4px 8px;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.2rem;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.bulk-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 160px;
  overflow: hidden;
}

.bulk-menu-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  border: none;
  background: none;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.15s;
}

.bulk-menu-item:hover {
  background: var(--bg-hover);
}

.bulk-menu-item.bulk-delete {
  color: #dc3545;
}

.bulk-menu-item.bulk-delete:hover {
  background: #fee;
}

.bulk-menu-divider {
  margin: 4px 0;
  border: none;
  border-top: 1px solid var(--border-color);
}

.scenarios-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scenario-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.scenario-item:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.scenario-item.active {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.scenario-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.scenario-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.scenario-stats {
  display: flex;
  gap: 12px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  font-size: 0.75rem;
  font-weight: 500;
}

.tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  background: var(--primary-light);
  color: var(--primary-color);
  font-size: 0.7rem;
  font-weight: 500;
}

.scenario-details-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.scenario-details {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.details-header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.details-header h2 {
  margin: 0;
  font-size: 1.3rem;
}

.btn-icon-folder {
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon-folder:hover {
  background: var(--bg-tertiary);
  border-color: var(--primary-color);
  transform: scale(1.05);
}

.btn-icon-folder:active {
  transform: scale(0.95);
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* Status dropdown */
.status-dropdown {
  position: relative;
}

.dropdown-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.dropdown-toggle:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.dropdown-toggle.status-disabled {
  background: #fee;
  border-color: #f88;
  color: #c00;
}

.dropdown-toggle.status-archived {
  background: #ffeaa7;
  border-color: #fdcb6e;
  color: #856404;
}

.dropdown-arrow {
  font-size: 0.7rem;
  margin-left: 4px;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 140px;
  overflow: hidden;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: none;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: var(--bg-hover);
}

.dropdown-item.active {
  background: var(--primary-color);
  color: white;
  font-weight: 500;
}

.btn-danger {
  background: #dc3545;
  color: white;
  border: 1px solid #dc3545;
}

.btn-danger:hover {
  background: #c82333;
  border-color: #bd2130;
}

.details-content {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding-right: 8px;
  align-items: start;
}

.details-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* Panel row for side-by-side layout */
.panel-row {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

/* Collapsible panels */
.collapsible-panel {
  transition: all 0.3s ease;
}

.collapsible-panel.collapsed {
  flex-grow: 0;
}

.collapsible-panel.collapsed .panel-content {
  display: none;
}

.panel-header-collapsible {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  margin-bottom: 12px;
  padding: 8px;
  margin: -8px -8px 12px -8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.panel-header-collapsible:hover {
  background: var(--bg-hover);
}

.panel-header-collapsible .panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.collapse-icon {
  font-size: 0.8rem;
  color: var(--text-secondary);
  transition: transform 0.2s;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Compact info grid - 4 columns */
.info-grid-compact {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px 12px;
}

/* Compact stats grid - 2 columns */
.stats-grid-compact {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}

.stats-grid-compact .stat-item.full-width {
  grid-column: 1 / -1;
}

.utils-compact {
  font-size: 0.85rem;
  font-family: monospace;
}

/* Full width panel */
.panel-full {
  width: 100%;
}

/* Half width panels for side-by-side */
.panel-half {
  flex: 1;
  min-width: 0; /* Allow flex shrinking */
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-title {
  margin: 0 0 12px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-empty {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.description-section,
.issues-section,
.tags-section {
  margin-top: 16px;
}

.description-section h4,
.issues-section h4,
.tags-section h4 {
  margin: 0 0 8px 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.description-text {
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.stat-item.full-width {
  grid-column: 1 / -1;
}

.plot-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.plot-controls label {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.plot-controls .input-select {
  flex: 1;
  max-width: 200px;
}

.plot-selector {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.plot-selector label {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.plot-selector .input-select {
  flex: 1;
  max-width: 300px;
}

.info-grid,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.info-item,
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item label,
.stat-item label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.info-item span,
.stat-item span {
  font-size: 1rem;
  color: var(--text-primary);
}

.outcome-text {
  font-size: 0.9rem;
  color: var(--text-primary);
  font-family: monospace;
  word-break: break-word;
  line-height: 1.4;
}

.issues-section,
.tags-section {
  margin-top: 24px;
}

.tags-section {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.issues-section h3,
.tags-section h3,
.issues-section h4,
.tags-section h4 {
  margin: 0;
  font-size: 1rem;
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Compact issues list */
.issues-list-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 400px;
  overflow-y: auto;
}

.issue-item-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.issue-header-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.issue-meta-compact {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
}

.values-grid-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 150px;
  overflow-y: auto;
}

.value-chip-compact {
  padding: 2px 6px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 3px;
  font-size: 0.75rem;
  color: var(--text-primary);
  font-family: 'Monaco', 'Courier New', monospace;
}

.issue-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.issue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.issue-name {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.95rem;
}

.issue-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
}

.issue-type {
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 0.75rem;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.issue-count,
.issue-range {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.issue-values {
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.values-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.value-chip {
  padding: 4px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 0.8rem;
  color: var(--text-primary);
  font-family: 'Monaco', 'Courier New', monospace;
}

.value-more {
  padding: 4px 10px;
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-style: italic;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h4 {
  margin: 0;
}

.btn-text {
  background: none;
  border: none;
  color: var(--primary-color);
  cursor: pointer;
  font-weight: 500;
  padding: 4px 8px;
  font-size: 0.85rem;
  transition: opacity 0.2s;
}

.btn-text:hover {
  opacity: 0.8;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: var(--text-secondary);
  gap: 12px;
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-small {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 4px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.plot-container {
  width: 100%;
  height: 500px;
}

/* Compact plot container - smaller size */
.plot-container-compact {
  width: 100%;
  max-height: 400px;
  overflow: auto;
}

.plot-image-container-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plot-image-wrapper {
  width: 100%;
  max-height: 350px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.plot-image-compact {
  max-width: 100%;
  max-height: 350px;
  width: auto;
  height: auto;
  display: block;
  object-fit: contain;
}

.plot-selector-compact {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 0.85rem;
}

.plot-selector-compact label {
  font-weight: 500;
  color: var(--text-primary);
}

.plot-selector-compact .input-select {
  flex: 1;
  max-width: 200px;
  font-size: 0.85rem;
  padding: 4px 8px;
}

.plot-interactive-container-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plot-controls-compact {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 0.85rem;
}

.plot-controls-compact label {
  font-weight: 500;
  color: var(--text-primary);
}

.plot-controls-compact .input-select {
  flex: 1;
  max-width: 150px;
  font-size: 0.85rem;
  padding: 4px 8px;
}

.plot-compact {
  width: 100%;
  height: 350px;
}

/* UFuns panel styles */
.ufuns-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ufun-item {
  padding: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.ufun-header {
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.ufun-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.ufun-name {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.ufun-type {
  font-size: 0.7rem;
  padding: 2px 6px;
  background: var(--primary-light);
  color: var(--primary-color);
  border-radius: 3px;
  font-weight: 600;
  text-transform: uppercase;
}

.btn-edit-ufun {
  padding: 4px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--primary-color);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-edit-ufun:hover {
  background: var(--primary-light);
  border-color: var(--primary-color);
}

.ufun-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ufun-meta {
  font-size: 0.85rem;
  color: var(--text-secondary);
}


.ufun-representation {
  margin-top: 8px;
  padding: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  font-size: 0.75rem;
  overflow-x: auto;
}

.ufun-representation pre {
  margin: 0;
  font-family: 'Monaco', 'Courier New', monospace;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-wrap: break-word;
}

.text-secondary {
  color: var(--text-secondary);
}

.plot {
  width: 100%;
  height: 100%;
}

.btn-primary,
.btn-secondary {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.85rem;
}

.btn-icon {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.2rem;
  padding: 4px;
  transition: color 0.2s;
}

.btn-icon:hover {
  color: var(--text-primary);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Plot visualization styles */
.plot-mode-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  user-select: none;
}

.plot-mode-toggle input[type="checkbox"] {
  cursor: pointer;
}

.plot-image-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.plot-image {
  max-width: 100%;
  height: auto;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: white;
}

.plot-hint {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
  font-style: italic;
}

.plot-warning {
  font-size: 0.8rem;
  color: #f59e0b;
  margin: 4px 0 0 0;
  padding: 6px 8px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 4px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  line-height: 1.4;
}

.plot-interactive-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Save filter dialog styles */
.save-filter-modal {
  max-width: 500px;
  width: 90%;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.input-text {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 0.9rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: inherit;
}

.input-text:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

textarea.input-text {
  resize: vertical;
  min-height: 60px;
}

.error-message {
  margin: 12px 0 0;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 4px;
  font-size: 0.85rem;
}

.success-message {
  margin: 12px 0 0;
  padding: 8px 12px;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 4px;
  font-size: 0.85rem;
}

.btn-sm {
  font-size: 0.85rem;
  padding: 6px 12px;
}

/* Read-only badge styling */
.readonly-badge {
  display: inline-block;
  padding: 4px 10px;
  background: #fbbf24;
  color: #78350f;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Checkbox label styling */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}
</style>
