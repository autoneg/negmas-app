<template>
  <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
    <div class="modal large">
      <!-- Success Message Toast -->
      <div v-if="saveSuccessMessage" class="success-toast">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        {{ saveSuccessMessage }}
      </div>
      
      <div class="modal-header">
        <h2 class="modal-title">Start New Negotiation</h2>
        <div class="modal-header-actions">
          <!-- Recent Sessions Dropdown -->
          <div class="dropdown">
            <button class="btn btn-sm btn-secondary" @click="recentDropdownOpen = !recentDropdownOpen; loadRecentSessions()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              Recent
            </button>
            <div v-if="recentDropdownOpen" class="dropdown-menu" style="right: 0; min-width: 280px;" @click.stop>
              <div v-if="negotiationsStore.recentSessions.length === 0" class="dropdown-item text-muted">
                No recent sessions
              </div>
              <div
                v-for="session in negotiationsStore.recentSessions"
                :key="session.name + session.last_used_at"
                class="dropdown-item"
                @click="loadFullSession(session); recentDropdownOpen = false"
              >
                <div class="font-medium">{{ session.scenario_name }}</div>
                <div class="text-muted" style="font-size: 11px;">
                  {{ session.negotiators.map(n => n.name).join(' vs ') }}
                </div>
              </div>
            </div>
          </div>
          
          <!-- Saved Sessions Dropdown -->
          <div class="dropdown">
            <button 
              class="btn btn-sm btn-secondary" 
              @click="savedDropdownOpen = !savedDropdownOpen"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                <polyline points="17 21 17 13 7 13 7 21"></polyline>
                <polyline points="7 3 7 8 15 8"></polyline>
              </svg>
              Load
            </button>
            <div v-if="savedDropdownOpen" class="dropdown-menu" style="right: 0; min-width: 280px;" @click.stop>
              <!-- Debug info -->
              <div style="background: yellow; padding: 4px; font-size: 10px; border-bottom: 1px solid #ccc;">
                DEBUG: {{ negotiationsStore.sessionPresets?.length || 0 }} presets, open={{ savedDropdownOpen }}, loading={{ isLoadingPresets }}
              </div>
              
              <div v-if="isLoadingPresets" class="dropdown-item text-muted">
                Loading saved sessions...
              </div>
              <div v-else-if="negotiationsStore.sessionPresets.length === 0" class="dropdown-item text-muted">
                No saved sessions
              </div>
              <div
                v-else
                v-for="preset in negotiationsStore.sessionPresets"
                :key="preset.name"
                class="dropdown-item"
                style="display: flex; justify-content: space-between; align-items: center;"
              >
                <div @click="loadFullSession(preset); savedDropdownOpen = false" style="flex: 1; cursor: pointer;">
                  <div class="font-medium">{{ preset.name }}</div>
                  <div class="text-muted" style="font-size: 11px;">{{ preset.scenario_name }}</div>
                </div>
                <button class="btn-icon-sm" @click.stop="deleteSessionPreset(preset.name)" title="Delete">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          <!-- Save Session Button -->
          <button class="btn btn-sm btn-primary" @click="showSaveModal = true" :disabled="!selectedScenario">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
              <polyline points="17 21 17 13 7 13 7 21"></polyline>
              <polyline points="7 3 7 8 15 8"></polyline>
            </svg>
            Save
          </button>
        </div>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body" style="padding: 0;">
        <!-- Wizard Layout with Vertical Tabs -->
        <div class="wizard-layout">
          <!-- Vertical Sidebar Tabs -->
          <div class="wizard-sidebar">
            <button
              class="wizard-tab"
              :class="{ active: currentTab === 'scenario', completed: !!selectedScenario }"
              @click="currentTab = 'scenario'"
              title="Scenario"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <span class="wizard-tab-label">Scenario</span>
            </button>
            <button
              class="wizard-tab"
              :class="{ active: currentTab === 'negotiators', completed: negotiators.length >= (selectedScenario?.n_negotiators || 2) }"
              @click="currentTab = 'negotiators'"
              title="Negotiators"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              <span class="wizard-tab-label">Negotiators</span>
            </button>
            <button
              class="wizard-tab"
              :class="{ active: currentTab === 'parameters' }"
              @click="currentTab = 'parameters'"
              title="Mechanism Parameters"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
              <span class="wizard-tab-label">Params</span>
            </button>
            <button
              class="wizard-tab"
              :class="{ active: currentTab === 'panels' }"
              @click="currentTab = 'panels'"
              title="Panel Configuration"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
              <span class="wizard-tab-label">Panels</span>
            </button>
            <button
              class="wizard-tab"
              :class="{ active: currentTab === 'display' }"
              @click="currentTab = 'display'"
              title="Display & Run"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
              <span class="wizard-tab-label">Run</span>
            </button>
          </div>

          <!-- Tab Content -->
          <div class="wizard-content">
            <!-- Tab 1: Scenario Selection -->
            <div v-show="currentTab === 'scenario'" class="tab-content">
              <div class="form-group">
                <label class="form-label">Search Scenarios</label>
                <input
                  type="text"
                  class="form-input"
                  placeholder="Type to search all scenarios..."
                  v-model="scenarioSearch"
                  @input="filterScenarios"
                />
              </div>

              <div class="form-group">
                <label class="form-label">Filter by Source <span class="text-muted">(optional)</span></label>
                <select class="form-select" v-model="sourceFilter" @change="filterScenarios">
                  <option value="">All sources</option>
                  <option v-for="source in scenarioSources" :key="source" :value="source">
                    {{ source }}
                  </option>
                </select>
              </div>

              <!-- Advanced Filters Toggle -->
              <div class="form-group">
                <button
                  type="button"
                  class="btn btn-link"
                  @click="showAdvancedFilters = !showAdvancedFilters"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    width="14"
                    height="14"
                    :style="{ transform: showAdvancedFilters ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"
                  >
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                  Advanced Filters
                </button>
              </div>

              <!-- Advanced Filters Panel -->
              <div v-if="showAdvancedFilters" class="advanced-filters">
                <div class="filters-grid">
                  <div>
                    <label class="form-label-sm">Min Outcomes</label>
                    <input type="number" class="form-input-sm" v-model.number="filters.minOutcomes" min="1" />
                  </div>
                  <div>
                    <label class="form-label-sm">Max Outcomes</label>
                    <input type="number" class="form-input-sm" v-model.number="filters.maxOutcomes" min="1" />
                  </div>
                  <div>
                    <label class="form-label-sm">Min Rational Fraction</label>
                    <input type="number" class="form-input-sm" v-model.number="filters.minRationalFraction" min="0" max="1" step="0.1" />
                  </div>
                  <div>
                    <label class="form-label-sm">Max Rational Fraction</label>
                    <input type="number" class="form-input-sm" v-model.number="filters.maxRationalFraction" min="0" max="1" step="0.1" />
                  </div>
                  <div>
                    <label class="form-label-sm">Min Opposition</label>
                    <input type="number" class="form-input-sm" v-model.number="filters.minOpposition" min="0" max="1" step="0.1" />
                  </div>
                  <div>
                    <label class="form-label-sm">Max Opposition</label>
                    <input type="number" class="form-input-sm" v-model.number="filters.maxOpposition" min="0" max="1" step="0.1" />
                  </div>
                </div>
                <div class="filters-footer">
                  <div class="text-muted-sm">
                    Note: Scenarios without calculated stats will be hidden when using advanced filters.
                  </div>
                  <button type="button" class="btn btn-sm btn-secondary" @click="clearFilters">
                    Clear Filters
                  </button>
                </div>
              </div>

              <!-- Scenario List -->
              <div class="form-group" v-if="filteredScenarios.length > 0">
                <label class="form-label">
                  Select Scenario
                  <span class="text-muted">({{ filteredScenarios.length }} found)</span>
                </label>
                <div class="scenario-list">
                  <div
                    v-for="scenario in filteredScenarios"
                    :key="scenario.path"
                    class="scenario-card"
                    :class="{ selected: selectedScenario?.path === scenario.path }"
                    @click="selectScenario(scenario)"
                  >
                    <div class="scenario-card-title">{{ scenario.name }}</div>
                    <div class="scenario-card-meta">
                      <span class="badge badge-neutral">{{ scenario.source }}</span>
                      <span>{{ scenario.n_negotiators }} parties</span>
                      <span>{{ scenario.issues?.length || 0 }} issues</span>
                      <span v-if="scenario.n_outcomes">{{ formatNumber(scenario.n_outcomes) }} outcomes</span>
                      <span v-if="scenario.opposition !== null && scenario.opposition !== undefined">
                        opp: {{ scenario.opposition.toFixed(2) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Selected Scenario Details -->
              <div class="form-group" v-if="selectedScenario">
                <label class="form-label">Scenario Details</label>
                <div class="scenario-details">
                  <div class="font-semibold">{{ selectedScenario.name }}</div>
                  <div class="text-secondary">
                    <div><strong>Issues:</strong></div>
                    <div v-for="issue in selectedScenario.issues || []" :key="issue.name" class="issue-item">
                      <span>{{ issue.name }}</span>
                      <span class="text-muted">({{ issue.type }})</span>
                      <span v-if="issue.values" class="text-muted">
                        : {{ issue.values.slice(0, 5).join(', ') }}{{ issue.values.length > 5 ? '...' : '' }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Scenario Loading Options -->
              <div class="form-group" v-if="selectedScenario">
                <label class="form-label">Utility Function Options</label>
                <div class="checkbox-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="options.ignoreDiscount" />
                    <span>Ignore discount factors</span>
                    <span class="text-muted-sm">(use stationary utilities)</span>
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="options.ignoreReserved" />
                    <span>Ignore reserved values</span>
                    <span class="text-muted-sm">(set to -infinity)</span>
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="options.normalize" />
                    <span>Normalize utilities</span>
                    <span class="text-muted-sm">(scale to [0, 1] range)</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- Tab 2: Negotiators -->
            <div v-show="currentTab === 'negotiators'" class="tab-content">
              <!-- Sub-tabs -->
              <div class="tabs-secondary">
                <button
                  class="tab"
                  :class="{ active: negotiatorSubTab === 'preset' }"
                  @click="negotiatorSubTab = 'preset'"
                >
                  Preset Agents
                </button>
                <button
                  class="tab"
                  :class="{ active: negotiatorSubTab === 'boa' }"
                  @click="negotiatorSubTab = 'boa'; loadBOAComponents()"
                >
                  Build Custom (BOA)
                </button>
                <button
                  class="tab"
                  :class="{ active: negotiatorSubTab === 'map' }"
                  @click="negotiatorSubTab = 'map'; loadBOAComponents()"
                >
                  Build Custom (MAP)
                </button>
              </div>

              <!-- Assigned Negotiators -->
              <div class="form-group">
                <label class="form-label">
                  Assigned Negotiators
                  <span class="text-muted">
                    ({{ negotiators.length }}/{{ selectedScenario?.n_negotiators || 2 }} required)
                  </span>
                </label>

                <div class="negotiator-list">
                  <div
                    v-for="(neg, index) in negotiators"
                    :key="index"
                    class="negotiator-item"
                    :class="{ selected: selectedSlot === index }"
                    @click="selectedSlot = index"
                  >
                    <div class="drag-handle">⋮⋮</div>
                    <div class="negotiator-item-content">
                      <input
                        type="text"
                        class="negotiator-name-input"
                        v-model="neg.name"
                        @click.stop
                        placeholder="Agent name"
                      />
                      <div class="negotiator-type">{{ getNegotiatorDisplayName(neg.type_name) }}</div>
                      <div v-if="neg.params && Object.keys(neg.params).length > 0" class="negotiator-params">
                        {{ formatParams(neg.params) }}
                      </div>
                      <span v-if="neg.source" class="badge badge-sm">{{ neg.source }}</span>
                    </div>
                    <button
                      class="btn-icon btn-sm"
                      @click.stop="openNegotiatorConfig(index)"
                      title="Configure parameters"
                      :class="{ 'has-config': neg.params && Object.keys(neg.params).length > 0 }"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                      </svg>
                    </button>
                  </div>
                </div>
                <div class="text-muted-sm">Click a slot to select it, then choose a negotiator below</div>
              </div>

              <!-- Sub-tab: Preset Negotiators -->
              <div v-show="negotiatorSubTab === 'preset'">
                <div class="form-group">
                  <label class="form-label">Search Negotiators</label>
                  <input
                    type="text"
                    class="form-input"
                    placeholder="Type to search all negotiators..."
                    v-model="negotiatorSearch"
                    @input="filterNegotiators"
                  />
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">Source <span class="text-muted">(optional)</span></label>
                    <select class="form-select" v-model="negotiatorSourceFilter" @change="filterNegotiators">
                      <option value="">All sources</option>
                      <option v-for="source in negotiatorSources" :key="source" :value="source">
                        {{ source }}
                      </option>
                    </select>
                  </div>

                  <div class="form-group" v-if="negotiatorSourceFilter === 'genius'">
                    <label class="form-label">Year <span class="text-muted">(optional)</span></label>
                    <select class="form-select" v-model="negotiatorYearFilter" @change="filterNegotiators">
                      <option value="">All years</option>
                      <option value="y2019">ANAC 2019</option>
                      <option value="y2018">ANAC 2018</option>
                      <option value="y2017">ANAC 2017</option>
                      <option value="y2016">ANAC 2016</option>
                      <option value="y2015">ANAC 2015</option>
                      <option value="y2014">ANAC 2014</option>
                      <option value="y2013">ANAC 2013</option>
                      <option value="y2012">ANAC 2012</option>
                      <option value="y2011">ANAC 2011</option>
                      <option value="y2010">ANAC 2010</option>
                      <option value="basic">Basic</option>
                      <option value="others">Others</option>
                    </select>
                  </div>

                  <div class="form-group">
                    <label class="form-label">Tag <span class="text-muted">(optional)</span></label>
                    <select class="form-select" v-model="negotiatorTagFilter" @change="filterNegotiators">
                      <option value="">All tags</option>
                      <option v-for="tag in allNegotiatorTags" :key="tag" :value="tag">
                        {{ tag }}
                      </option>
                    </select>
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label">
                    Available Negotiators
                    <span class="text-muted">({{ filteredNegotiators.length }} found)</span>
                  </label>
                  <div class="negotiator-grid">
                    <div
                      v-for="neg in filteredNegotiators"
                      :key="neg.type_name"
                      class="negotiator-card"
                      @click="selectNegotiatorForSlot(neg)"
                    >
                      <div class="negotiator-card-name">{{ neg.name }}</div>
                      <div class="negotiator-card-meta">
                        <span class="badge badge-sm">{{ neg.source }}</span>
                      </div>
                      <div v-if="neg.description" class="negotiator-card-desc">{{ neg.description }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Sub-tab: BOA Builder -->
              <div v-show="negotiatorSubTab === 'boa'">
                <div class="boa-builder">
                  <div class="form-group">
                    <label class="form-label">Acceptance Policy <span class="text-danger">*</span></label>
                    <select class="form-select" v-model="boaConfig.acceptance_policy">
                      <option value="">Select acceptance policy...</option>
                      <option v-for="c in boaComponents.acceptance" :key="c" :value="c">
                        {{ c }}
                      </option>
                    </select>
                  </div>

                  <div class="form-group">
                    <label class="form-label">Offering Policy <span class="text-danger">*</span></label>
                    <select class="form-select" v-model="boaConfig.offering_policy">
                      <option value="">Select offering policy...</option>
                      <option v-for="c in boaComponents.offering" :key="c" :value="c">
                        {{ c }}
                      </option>
                    </select>
                  </div>

                  <div class="form-group">
                    <label class="form-label">Opponent Model <span class="text-muted">(optional)</span></label>
                    <select class="form-select" v-model="boaConfig.opponent_model">
                      <option value="">None (no opponent modeling)</option>
                      <option v-for="c in boaComponents.model" :key="c" :value="c">
                        {{ c }}
                      </option>
                    </select>
                  </div>

                  <button
                    class="btn btn-primary"
                    @click="applyBOAToSlot"
                    :disabled="!boaConfig.acceptance_policy || !boaConfig.offering_policy"
                  >
                    Apply to Selected Slot
                  </button>
                </div>

                <div class="text-muted-sm">
                  <strong>BOA Architecture:</strong> Build modular negotiators by combining acceptance, offering, and opponent modeling components.
                </div>
              </div>

              <!-- Sub-tab: MAP Builder -->
              <div v-show="negotiatorSubTab === 'map'">
                <div class="map-builder">
                  <div class="form-group">
                    <label class="form-label">Acceptance Policy <span class="text-danger">*</span></label>
                    <select class="form-select" v-model="mapConfig.acceptance_policy">
                      <option value="">Select acceptance policy...</option>
                      <option v-for="c in boaComponents.acceptance" :key="c" :value="c">
                        {{ c }}
                      </option>
                    </select>
                  </div>

                  <div class="form-group">
                    <label class="form-label">Offering Policy <span class="text-danger">*</span></label>
                    <select class="form-select" v-model="mapConfig.offering_policy">
                      <option value="">Select offering policy...</option>
                      <option v-for="c in boaComponents.offering" :key="c" :value="c">
                        {{ c }}
                      </option>
                    </select>
                  </div>

                  <div class="form-group">
                    <label class="form-label">Models <span class="text-muted">(multiple allowed)</span></label>
                    <div class="model-selector">
                      <span v-for="(model, index) in mapConfig.models" :key="index" class="badge badge-primary">
                        {{ model }}
                        <button type="button" @click="mapConfig.models.splice(index, 1)" class="badge-remove">×</button>
                      </span>
                    </div>
                    <div class="model-add">
                      <select class="form-select" v-model="selectedMapModel">
                        <option value="">Add a model...</option>
                        <option
                          v-for="c in boaComponents.model"
                          :key="c"
                          :value="c"
                          :disabled="mapConfig.models.includes(c)"
                        >
                          {{ c }}
                        </option>
                      </select>
                      <button type="button" class="btn btn-secondary" @click="addMapModel">Add</button>
                    </div>
                    <div class="form-hint">Unlike BOA, MAP supports multiple opponent models that run in sequence.</div>
                  </div>

                  <div class="form-group">
                    <label class="checkbox-label">
                      <input type="checkbox" v-model="mapConfig.acceptance_first" />
                      <span>Evaluate Acceptance First</span>
                    </label>
                    <div class="form-hint">
                      If checked, acceptance is evaluated before offering. If unchecked, offering is evaluated first.
                    </div>
                  </div>

                  <button
                    class="btn btn-primary"
                    @click="applyMAPToSlot"
                    :disabled="!mapConfig.acceptance_policy || !mapConfig.offering_policy"
                  >
                    Apply to Selected Slot
                  </button>
                </div>

                <div class="text-muted-sm">
                  <strong>MAP Architecture:</strong> Advanced modular negotiators with multiple models and flexible component ordering.
                </div>
              </div>
            </div>

            <!-- Tab 3: Mechanism Parameters -->
            <div v-show="currentTab === 'parameters'" class="tab-content">
              <div class="form-group">
                <label class="form-label">Mechanism Protocol</label>
                <div class="mechanism-selector">
                  <button
                    type="button"
                    class="mechanism-card"
                    :class="{ selected: mechanismType === 'SAOMechanism' }"
                    @click="mechanismType = 'SAOMechanism'"
                  >
                    <span class="mechanism-name">SAO</span>
                    <span class="mechanism-desc">Stacked Alternating Offers</span>
                  </button>
                </div>
              </div>

              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="shareUfuns" />
                  <span>Share utility functions</span>
                </label>
                <div class="form-hint">Give each negotiator access to opponent's utility function</div>
              </div>

              <!-- Basic Time Limits -->
              <div class="param-section">
                <h4 class="param-section-title">Time Limits</h4>

                <div class="form-group">
                  <label class="form-label">Number of Steps</label>
                  <input
                    type="number"
                    class="form-input"
                    v-model.number="mechanismParams.n_steps"
                    placeholder="None (infinite)"
                  />
                  <div class="form-hint">Maximum number of negotiation rounds</div>
                </div>

                <div class="form-group">
                  <label class="form-label">Time Limit (seconds)</label>
                  <input
                    type="number"
                    class="form-input"
                    v-model.number="mechanismParams.time_limit"
                    step="0.1"
                    placeholder="None (infinite)"
                  />
                  <div class="form-hint">Maximum wall-time allowed for negotiation</div>
                </div>

                <div class="form-group">
                  <label class="form-label">Step Time Limit (seconds)</label>
                  <input
                    type="number"
                    class="form-input"
                    v-model.number="mechanismParams.step_time_limit"
                    step="0.1"
                    placeholder="None (infinite)"
                  />
                  <div class="form-hint">Maximum wall-time per negotiation round</div>
                </div>

                <div class="form-group">
                  <label class="form-label">Negotiator Time Limit (seconds)</label>
                  <input
                    type="number"
                    class="form-input"
                    v-model.number="mechanismParams.negotiator_time_limit"
                    step="0.1"
                    placeholder="None (infinite)"
                  />
                  <div class="form-hint">Maximum time per negotiator action</div>
                </div>
              </div>

              <!-- Probabilistic Ending -->
              <div class="param-section">
                <h4 class="param-section-title">Probabilistic Ending</h4>

                <div class="form-group">
                  <label class="form-label">Pend (probability)</label>
                  <input
                    type="number"
                    class="form-input"
                    v-model.number="mechanismParams.pend"
                    min="0"
                    max="1"
                    step="0.01"
                    placeholder="0"
                  />
                  <div class="form-hint">Probability of ending negotiation at any step</div>
                </div>

                <div class="form-group">
                  <label class="form-label">Pend per Second (probability)</label>
                  <input
                    type="number"
                    class="form-input"
                    v-model.number="mechanismParams.pend_per_second"
                    min="0"
                    max="1"
                    step="0.01"
                    placeholder="0"
                  />
                  <div class="form-hint">Probability of ending per second</div>
                </div>
              </div>

              <!-- Core Behavior -->
              <div class="param-section">
                <h4 class="param-section-title">Core Behavior</h4>

                <label class="checkbox-label">
                  <input type="checkbox" v-model="mechanismParams.end_on_no_response" />
                  <span>End on No Response</span>
                </label>
                <div class="form-hint">End if negotiator returns NO_RESPONSE</div>

                <label class="checkbox-label">
                  <input type="checkbox" v-model="mechanismParams.offering_is_accepting" />
                  <span>Offering is Accepting</span>
                </label>
                <div class="form-hint">Proposing an offer implies accepting it</div>

                <label class="checkbox-label">
                  <input type="checkbox" v-model="mechanismParams.allow_offering_just_rejected_outcome" />
                  <span>Allow Offering Just Rejected Outcome</span>
                </label>
                <div class="form-hint">Allow re-offering outcomes just rejected</div>

                <label class="checkbox-label">
                  <input type="checkbox" v-model="mechanismParams.one_offer_per_step" />
                  <span>One Offer per Step</span>
                </label>
                <div class="form-hint">Each step processes only one negotiator's offer</div>
              </div>

              <!-- Offer Validation -->
              <div class="param-section">
                <h4 class="param-section-title">Offer Validation</h4>

                <label class="checkbox-label">
                  <input type="checkbox" v-model="mechanismParams.check_offers" />
                  <span>Check Offers</span>
                </label>
                <div class="form-hint">Validate offers against outcome space</div>

                <label class="checkbox-label">
                  <input type="checkbox" v-model="mechanismParams.enforce_issue_types" />
                  <span>Enforce Issue Types</span>
                </label>
                <div class="form-hint">Enforce correct types for issue values</div>

                <label class="checkbox-label">
                  <input type="checkbox" v-model="mechanismParams.cast_offers" :disabled="!mechanismParams.enforce_issue_types" />
                  <span>Cast Offers</span>
                </label>
                <div class="form-hint">Cast issue values to correct types (requires enforce_issue_types)</div>
              </div>

              <!-- Advanced Settings (Collapsible) -->
              <div class="param-section collapsible">
                <h4 class="param-section-title" @click="showAdvancedMechParams = !showAdvancedMechParams">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    width="16"
                    height="16"
                    :style="{ transform: showAdvancedMechParams ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"
                  >
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                  Advanced Settings
                </h4>

                <div v-if="showAdvancedMechParams" class="param-section-content">
                  <div class="form-group">
                    <label class="form-label">Hidden Time Limit (seconds)</label>
                    <input
                      type="number"
                      class="form-input"
                      v-model.number="mechanismParams.hidden_time_limit"
                      step="0.1"
                      placeholder="inf"
                    />
                    <div class="form-hint">Time limit not visible to negotiators</div>
                  </div>

                  <div class="form-group">
                    <label class="form-label">Max Wait</label>
                    <input
                      type="number"
                      class="form-input"
                      v-model.number="mechanismParams.max_wait"
                      placeholder="sys.maxsize"
                    />
                    <div class="form-hint">Maximum consecutive WAIT responses before timeout</div>
                  </div>

                  <label class="checkbox-label">
                    <input type="checkbox" v-model="mechanismParams.sync_calls" />
                    <span>Synchronous Calls</span>
                  </label>
                  <div class="form-hint">Disable per-call timeouts (slower but easier debugging)</div>

                  <div class="form-group">
                    <label class="form-label">Max N Negotiators</label>
                    <input
                      type="number"
                      class="form-input"
                      v-model.number="mechanismParams.max_n_negotiators"
                      placeholder="None"
                    />
                    <div class="form-hint">Maximum allowed number of negotiators</div>
                  </div>

                  <label class="checkbox-label">
                    <input type="checkbox" v-model="mechanismParams.dynamic_entry" />
                    <span>Dynamic Entry</span>
                  </label>
                  <div class="form-hint">Allow negotiators to enter/leave between rounds</div>

                  <div class="form-group">
                    <label class="form-label">Max Cardinality</label>
                    <input
                      type="number"
                      class="form-input"
                      v-model.number="mechanismParams.max_cardinality"
                      placeholder="10000000000"
                    />
                    <div class="form-hint">Maximum number of outcomes in cached set</div>
                  </div>

                  <label class="checkbox-label">
                    <input type="checkbox" v-model="mechanismParams.ignore_negotiator_exceptions" />
                    <span>Ignore Negotiator Exceptions</span>
                  </label>
                  <div class="form-hint">Silently ignore negotiator exceptions</div>

                  <div class="form-group">
                    <label class="form-label">Verbosity (0-3)</label>
                    <input
                      type="number"
                      class="form-input"
                      v-model.number="mechanismParams.verbosity"
                      min="0"
                      max="3"
                      placeholder="0"
                    />
                    <div class="form-hint">Logging verbosity level</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tab 4: Panels Configuration -->
            <div v-show="currentTab === 'panels'" class="tab-content">
              <div class="form-group">
                <label class="form-label">Panel Configuration</label>
                <div class="form-hint">Configure which panels to display during the negotiation</div>
              </div>

              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="panels.adjustable" />
                  <span>Adjustable panels</span>
                </label>
                <div class="form-hint">Allow resizing panels during negotiation</div>
              </div>

              <div class="param-section">
                <h4 class="param-section-title">Utility Space View</h4>
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">X-Axis (Negotiator)</label>
                    <select class="form-select" v-model.number="panels.utilityView.xAxis">
                      <option v-for="(neg, idx) in negotiators" :key="idx" :value="idx">
                        {{ neg.name || `Agent ${idx + 1}` }}
                      </option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Y-Axis (Negotiator)</label>
                    <select class="form-select" v-model.number="panels.utilityView.yAxis">
                      <option v-for="(neg, idx) in negotiators" :key="idx" :value="idx">
                        {{ neg.name || `Agent ${idx + 1}` }}
                      </option>
                    </select>
                  </div>
                </div>
              </div>

              <div class="param-section">
                <h4 class="param-section-title">Timeline View</h4>
                <div class="form-group">
                  <label class="form-label">X-Axis</label>
                  <select class="form-select" v-model="panels.timeline.xAxis">
                    <option value="step">Step</option>
                    <option value="time">Time</option>
                    <option value="relative_time">Relative Time</option>
                  </select>
                </div>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="panels.timeline.simplified" />
                  <span>Simplified View</span>
                </label>
                <div class="form-hint">Show single plot instead of per-agent plots</div>
              </div>

              <div class="param-section">
                <h4 class="param-section-title">Issue Space 2D</h4>
                <div v-if="issueOptions.length >= 2" class="form-row">
                  <div class="form-group">
                    <label class="form-label">X-Axis (Issue)</label>
                    <select class="form-select" v-model.number="panels.issueSpace.xAxis">
                      <option v-for="opt in issueOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Y-Axis (Issue)</label>
                    <select class="form-select" v-model.number="panels.issueSpace.yAxis">
                      <option v-for="opt in issueOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                  </div>
                </div>
                <div v-else class="form-hint" style="color: var(--text-muted); font-style: italic;">
                  Not available for this scenario (requires 2+ named issues)
                </div>
                <div v-if="issueOptions.length >= 2" class="form-hint">Select which issues to display on X and Y axes</div>
              </div>
            </div>

            <!-- Tab 5: Display & Run -->
            <div v-show="currentTab === 'display'" class="tab-content">
              <div class="form-group">
                <label class="form-label">Summary</label>
                <div class="summary-box">
                  <div><strong>Scenario:</strong> {{ selectedScenario?.name || 'Not selected' }}</div>
                  <div>
                    <strong>Negotiators:</strong>
                    {{ negotiators.map(n => getNegotiatorDisplayName(n.type_name)).join(' vs ') || 'None' }}
                  </div>
                  <div><strong>Mechanism:</strong> {{ mechanismType.replace('Mechanism', '') }}</div>
                  <div><strong>Deadline:</strong> {{ getDeadlineSummary() }}</div>
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Run Mode</label>
                <div class="run-mode-selector">
                  <button
                    type="button"
                    class="run-mode-card"
                    :class="{ selected: runMode === 'realtime' }"
                    @click="runMode = 'realtime'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24">
                      <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                    <div class="run-mode-content">
                      <span class="run-mode-title">Real-time</span>
                      <span class="run-mode-desc">Watch step-by-step with live updates</span>
                    </div>
                  </button>
                  <button
                    type="button"
                    class="run-mode-card"
                    :class="{ selected: runMode === 'batch' }"
                    @click="runMode = 'batch'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24">
                      <polyline points="13 17 18 12 13 7"></polyline>
                      <polyline points="6 17 11 12 6 7"></polyline>
                    </svg>
                    <div class="run-mode-content">
                      <span class="run-mode-title">Batch</span>
                      <span class="run-mode-desc">Run instantly and show results</span>
                    </div>
                  </button>
                </div>
              </div>

              <div v-if="runMode === 'realtime'" class="form-group">
                <label class="form-label">Step Delay: {{ stepDelay }}ms</label>
                <input
                  type="range"
                  class="form-range"
                  v-model.number="stepDelay"
                  min="0"
                  max="1000"
                  step="50"
                />
                <div class="form-hint">Delay between steps for visualization</div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="displayOptions.showPlot" />
                    <span>Show live utility plot</span>
                  </label>
                </div>
                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="displayOptions.showOffers" />
                    <span>Show offer history</span>
                  </label>
                </div>
              </div>

              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="autoSave" />
                  <span>Auto-save negotiation</span>
                </label>
                <div class="form-hint">Save results to disk when negotiation completes</div>
              </div>

              <!-- Panel visibility controls removed - panels are always visible and can be collapsed individually -->
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
        <button v-if="currentTab !== 'scenario'" class="btn btn-secondary" @click="prevTab">Back</button>
        <button v-if="currentTab !== 'display'" class="btn btn-primary" @click="nextTab" :disabled="!canProceed">
          Next
        </button>
        <button v-if="currentTab === 'display'" class="btn btn-secondary" @click="startWithoutMonitoring" :disabled="starting">
          Start without Monitoring
        </button>
        <button v-if="currentTab === 'display'" class="btn btn-primary" @click="startNegotiation" :disabled="starting">
          {{ starting ? 'Starting...' : 'Start Negotiation' }}
        </button>
      </div>
    </div>
  </div>
  
  <!-- Save Session Modal -->
  <div v-if="showSaveModal" class="modal-overlay active" @click.self="showSaveModal = false">
    <div class="modal small">
      <div class="modal-header">
        <h2 class="modal-title">Save Session Configuration</h2>
        <button class="modal-close" @click="showSaveModal = false">×</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">Configuration Name</label>
          <input
            type="text"
            class="form-input"
            v-model="savePresetName"
            placeholder="e.g., My Default Setup"
            @keyup.enter="saveFullSession"
          />
          <div class="form-hint">
            Give this configuration a memorable name so you can easily load it later
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="showSaveModal = false">Cancel</button>
        <button class="btn btn-primary" @click="saveFullSession" :disabled="!savePresetName.trim()">
          Save Configuration
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useNegotiationsStore } from '../stores/negotiations'

const negotiationsStore = useNegotiationsStore()

const props = defineProps({
  show: Boolean,
  preselectedScenario: Object,
})

const emit = defineEmits(['close', 'start'])

// Debug: Watch show prop
watch(() => props.show, (newVal, oldVal) => {
  console.log('NewNegotiationModal show prop changed:', { from: oldVal, to: newVal })
  if (newVal) {
    // Check if modal actually renders
    setTimeout(() => {
      const overlay = document.querySelector('.modal-overlay')
      console.log('Modal overlay in DOM?', overlay ? 'YES' : 'NO')
      if (overlay) {
        const styles = window.getComputedStyle(overlay)
        console.log('Modal overlay computed styles:', {
          display: styles.display,
          position: styles.position,
          zIndex: styles.zIndex,
          visibility: styles.visibility,
          opacity: styles.opacity
        })
      }
    }, 100)
  }
})

// Debug: Watch sessionPresets
watch(() => negotiationsStore.sessionPresets, (newVal) => {
  console.log('[NewNegotiationModal] sessionPresets changed:', newVal?.length || 0, newVal)
}, { immediate: true, deep: true })

// Tab management
const currentTab = ref('scenario')
const negotiatorSubTab = ref('preset')

// Scenario data
const scenarios = ref([])
const selectedScenario = ref(null)
const scenarioSearch = ref('')
const sourceFilter = ref('')
const scenarioSources = ref([])
const showAdvancedFilters = ref(false)
const filters = ref({
  minOutcomes: null,
  maxOutcomes: null,
  minRationalFraction: null,
  maxRationalFraction: null,
  minOpposition: null,
  maxOpposition: null,
})

// Scenario options
const options = ref({
  ignoreDiscount: false,
  ignoreReserved: false,
  normalize: false,
})

// Negotiators data
const allNegotiators = ref([])
const negotiators = ref([])
const selectedSlot = ref(0)
const negotiatorSearch = ref('')
const negotiatorSourceFilter = ref('')
const negotiatorYearFilter = ref('')
const negotiatorTagFilter = ref('')
const negotiatorSources = ref([])
const allNegotiatorTags = ref([])

// BOA/MAP configuration
const boaComponents = ref({
  acceptance: [],
  offering: [],
  model: [],
})
const boaConfig = ref({
  acceptance_policy: '',
  offering_policy: '',
  opponent_model: '',
})
const mapConfig = ref({
  acceptance_policy: '',
  offering_policy: '',
  models: [],
  acceptance_first: false,
})
const selectedMapModel = ref('')

// Mechanism params
const mechanismType = ref('SAOMechanism')
const shareUfuns = ref(false) // Session-level parameter, not mechanism param
const mechanismParams = ref({
  n_steps: null,
  time_limit: null,
  step_time_limit: null,
  negotiator_time_limit: null,
  pend: 0,
  pend_per_second: 0,
  end_on_no_response: true,
  offering_is_accepting: true,
  allow_offering_just_rejected_outcome: true,
  one_offer_per_step: false,
  check_offers: false,
  enforce_issue_types: false,
  cast_offers: false,
  hidden_time_limit: null,
  max_wait: null,
  sync_calls: false,
  max_n_negotiators: null,
  dynamic_entry: false,
  max_cardinality: null,
  ignore_negotiator_exceptions: false,
  verbosity: 0,
})
const showAdvancedMechParams = ref(false)

// Panel configuration
const panels = ref({
  adjustable: false,
  utilityView: { xAxis: 0, yAxis: 1 },
  timeline: { xAxis: 'relative_time', simplified: false },
  issueSpace: { xAxis: 0, yAxis: 1 },
  visible: {
    info: true,
    history: true,
    result: true,
    utility2d: true,
    issueSpace2d: false,
    timeline: true,
    histogram: false,
  },
})

// Display & Run
const runMode = ref('realtime')
const stepDelay = ref(100)
const displayOptions = ref({
  showPlot: true,
  showOffers: true,
})
const autoSave = ref(true)
const starting = ref(false)

// Session preset management
const showSaveModal = ref(false)
const savePresetName = ref('')
const recentDropdownOpen = ref(false)
const savedDropdownOpen = ref(false)
const isLoadingPresets = ref(false)
const saveSuccessMessage = ref('')

// Computed
const filteredScenarios = computed(() => {
  let result = scenarios.value

  // Text search
  if (scenarioSearch.value) {
    const search = scenarioSearch.value.toLowerCase()
    result = result.filter(s =>
      s.name.toLowerCase().includes(search) ||
      s.source.toLowerCase().includes(search)
    )
  }

  // Source filter
  if (sourceFilter.value) {
    result = result.filter(s => s.source === sourceFilter.value)
  }

  // Advanced filters
  if (filters.value.minOutcomes !== null) {
    result = result.filter(s => s.n_outcomes && s.n_outcomes >= filters.value.minOutcomes)
  }
  if (filters.value.maxOutcomes !== null) {
    result = result.filter(s => s.n_outcomes && s.n_outcomes <= filters.value.maxOutcomes)
  }
  if (filters.value.minRationalFraction !== null) {
    result = result.filter(s => s.rational_fraction && s.rational_fraction >= filters.value.minRationalFraction)
  }
  if (filters.value.maxRationalFraction !== null) {
    result = result.filter(s => s.rational_fraction && s.rational_fraction <= filters.value.maxRationalFraction)
  }
  if (filters.value.minOpposition !== null) {
    result = result.filter(s => s.opposition !== null && s.opposition >= filters.value.minOpposition)
  }
  if (filters.value.maxOpposition !== null) {
    result = result.filter(s => s.opposition !== null && s.opposition <= filters.value.maxOpposition)
  }

  return result
})

const filteredNegotiators = computed(() => {
  let result = allNegotiators.value

  // Text search
  if (negotiatorSearch.value) {
    const search = negotiatorSearch.value.toLowerCase()
    result = result.filter(n =>
      n.name.toLowerCase().includes(search) ||
      n.type_name.toLowerCase().includes(search)
    )
  }

  // Source filter
  if (negotiatorSourceFilter.value) {
    result = result.filter(n => n.source === negotiatorSourceFilter.value)
  }

  // Year filter (for Genius agents)
  if (negotiatorYearFilter.value) {
    result = result.filter(n => n.anac_year === negotiatorYearFilter.value)
  }

  // Tag filter
  if (negotiatorTagFilter.value) {
    result = result.filter(n => n.tags && n.tags.includes(negotiatorTagFilter.value))
  }

  return result
})

const canProceed = computed(() => {
  if (currentTab.value === 'scenario') return !!selectedScenario.value
  if (currentTab.value === 'negotiators') {
    return negotiators.value.length === (selectedScenario.value?.n_negotiators || 2) &&
           negotiators.value.every(n => n.type_name)
  }
  return true
})

const issueOptions = computed(() => {
  if (!selectedScenario.value?.issues || selectedScenario.value.issues.length === 0) {
    // Fallback: if scenario loaded but issues not yet available, 
    // return empty to avoid showing fake names
    return []
  }
  return selectedScenario.value.issues.map((issue, idx) => ({
    value: idx,
    label: issue.name
  }))
})

// Check if histogram should be available for this scenario
// For enumerated outcome spaces (no named issues), histogram shows all outcomes
// which can be very slow for large spaces
const histogramAvailable = computed(() => {
  const scenario = selectedScenario.value
  if (!scenario) return true // Allow by default if no scenario selected yet
  
  // If scenario has named issues, histogram is efficient (shows per-issue distribution)
  if (scenario.issues && scenario.issues.length > 0) return true
  
  // For enumerated spaces, check outcome count against threshold
  const MAX_HISTOGRAM_OUTCOMES = 10000 // TODO: Get from settings
  const outcomeCount = scenario.n_outcomes || 0
  
  return outcomeCount <= MAX_HISTOGRAM_OUTCOMES
})

const histogramDisabledReason = computed(() => {
  if (histogramAvailable.value) return null
  
  const outcomeCount = selectedScenario.value?.n_outcomes || 0
  return `Histogram disabled: ${formatNumber(outcomeCount)} outcomes exceeds limit of 10,000 for enumerated outcome spaces`
})

// Methods
function formatNumber(num) {
  if (num === null || num === undefined) return 'N/A'
  if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
  return num.toString()
}

function clearFilters() {
  filters.value = {
    minOutcomes: null,
    maxOutcomes: null,
    minRationalFraction: null,
    maxRationalFraction: null,
    minOpposition: null,
    maxOpposition: null,
  }
}

function selectScenario(scenario) {
  selectedScenario.value = scenario
  
  // Initialize negotiators array
  const numNegotiators = scenario.n_negotiators || 2
  negotiators.value = Array.from({ length: numNegotiators }, () => ({
    type_name: '',
    name: '',
    params: {},
    source: '',
  }))
  selectedSlot.value = 0
  
  // Auto-disable histogram if outcome space is too large for enumerated spaces
  if (!histogramAvailable.value) {
    panels.value.visible.histogram = false
  }
}

function filterScenarios() {
  // Trigger computed property recalculation
}

function filterNegotiators() {
  // Trigger computed property recalculation
}

function getNegotiatorDisplayName(typeName) {
  if (!typeName) return 'Empty'
  const neg = allNegotiators.value.find(n => n.type_name === typeName)
  return neg?.name || typeName
}

function formatParams(params) {
  return Object.entries(params)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
    .substring(0, 50)
}

function selectNegotiatorForSlot(negotiator) {
  if (selectedSlot.value < negotiators.value.length) {
    negotiators.value[selectedSlot.value] = {
      type_name: negotiator.type_name,
      name: negotiator.name || `Agent ${selectedSlot.value + 1}`,
      params: {},
      source: negotiator.source,
    }
    // Move to next slot
    if (selectedSlot.value < negotiators.value.length - 1) {
      selectedSlot.value++
    }
  }
}

function openNegotiatorConfig(index) {
  // TODO: Implement negotiator parameter configuration modal
  console.log('Open config for negotiator', index)
}

async function loadBOAComponents() {
  if (boaComponents.value.acceptance.length > 0) return // Already loaded

  try {
    const response = await fetch('/api/components')
    const data = await response.json()
    
    boaComponents.value = {
      acceptance: data.acceptance || [],
      offering: data.offering || [],
      model: data.model || [],
    }
  } catch (error) {
    console.error('Failed to load BOA components:', error)
  }
}

function applyBOAToSlot() {
  if (selectedSlot.value < negotiators.value.length) {
    negotiators.value[selectedSlot.value] = {
      type_name: 'BOANegotiator',
      name: `BOA ${selectedSlot.value + 1}`,
      params: {
        acceptance_policy: boaConfig.value.acceptance_policy,
        offering_policy: boaConfig.value.offering_policy,
        opponent_model: boaConfig.value.opponent_model || null,
      },
      source: 'custom',
    }
    
    // Reset BOA config
    boaConfig.value = {
      acceptance_policy: '',
      offering_policy: '',
      opponent_model: '',
    }
  }
}

function addMapModel() {
  if (selectedMapModel.value && !mapConfig.value.models.includes(selectedMapModel.value)) {
    mapConfig.value.models.push(selectedMapModel.value)
    selectedMapModel.value = ''
  }
}

function applyMAPToSlot() {
  if (selectedSlot.value < negotiators.value.length) {
    negotiators.value[selectedSlot.value] = {
      type_name: 'MAPNegotiator',
      name: `MAP ${selectedSlot.value + 1}`,
      params: {
        acceptance_policy: mapConfig.value.acceptance_policy,
        offering_policy: mapConfig.value.offering_policy,
        models: mapConfig.value.models,
        acceptance_first: mapConfig.value.acceptance_first,
      },
      source: 'custom',
    }
    
    // Reset MAP config
    mapConfig.value = {
      acceptance_policy: '',
      offering_policy: '',
      models: [],
      acceptance_first: false,
    }
  }
}

function getDeadlineSummary() {
  const parts = []
  if (mechanismParams.value.n_steps) {
    parts.push(`${mechanismParams.value.n_steps} steps`)
  }
  if (mechanismParams.value.time_limit) {
    parts.push(`${mechanismParams.value.time_limit}s`)
  }
  return parts.length > 0 ? parts.join(' or ') : 'None (infinite)'
}

function prevTab() {
  const tabs = ['scenario', 'negotiators', 'parameters', 'panels', 'display']
  const currentIndex = tabs.indexOf(currentTab.value)
  if (currentIndex > 0) {
    currentTab.value = tabs[currentIndex - 1]
  }
}

function nextTab() {
  if (!canProceed.value) return
  
  const tabs = ['scenario', 'negotiators', 'parameters', 'panels', 'display']
  const currentIndex = tabs.indexOf(currentTab.value)
  if (currentIndex < tabs.length - 1) {
    currentTab.value = tabs[currentIndex + 1]
  }
}

async function startNegotiation() {
  if (starting.value) return
  starting.value = true

  try {
    // Only send fields that backend expects
    const request = {
      scenario_path: selectedScenario.value.path,
      negotiators: negotiators.value.map(n => ({
        type_name: n.type_name,
        name: n.name || null,
        params: n.params || {},
      })),
      mechanism_type: mechanismType.value,
      mechanism_params: mechanismParams.value,
      ignore_discount: options.value.ignoreDiscount,
      ignore_reserved: options.value.ignoreReserved,
      normalize: options.value.normalize,
      step_delay: stepDelay.value / 1000, // Convert ms to seconds
      share_ufuns: shareUfuns.value,
      auto_save: autoSave.value,
    }

    const response = await fetch('/api/negotiation/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })

    const data = await response.json()
    
    // Add to recent sessions
    const preset = buildSessionPreset(selectedScenario.value.name)
    await negotiationsStore.addToRecentSessions(preset)
    
    // Store panel settings in localStorage for this session
    if (data.session_id) {
      const panelSettings = {
        panels: panels.value,
        runMode: runMode.value,
        stepDelay: stepDelay.value,
        displayOptions: displayOptions.value,
      }
      localStorage.setItem(`negotiation_settings_${data.session_id}`, JSON.stringify(panelSettings))
    }
    
    emit('start', data)
    emit('close')
  } catch (error) {
    console.error('Failed to start negotiation:', error)
    alert('Failed to start negotiation: ' + error.message)
  } finally {
    starting.value = false
  }
}

async function startWithoutMonitoring() {
  // TODO: Implement background start
  await startNegotiation()
}

async function loadScenarios() {
  try {
    const response = await fetch('/api/scenarios')
    const data = await response.json()
    scenarios.value = data.scenarios || []
    
    // Extract unique sources
    scenarioSources.value = [...new Set(scenarios.value.map(s => s.source))]
    
    // If preselected scenario, select it
    if (props.preselectedScenario) {
      const found = scenarios.value.find(s => s.path === props.preselectedScenario.path)
      if (found) {
        selectScenario(found)
      }
    }
  } catch (error) {
    console.error('Failed to load scenarios:', error)
  }
}

async function loadNegotiators() {
  try {
    const response = await fetch('/api/negotiators')
    const data = await response.json()
    allNegotiators.value = data.negotiators || []
    
    // Extract unique sources
    negotiatorSources.value = [...new Set(allNegotiators.value.map(n => n.source))]
    
    // Extract unique tags
    const tags = new Set()
    allNegotiators.value.forEach(n => {
      if (n.tags) {
        n.tags.forEach(tag => tags.add(tag))
      }
    })
    allNegotiatorTags.value = Array.from(tags)
  } catch (error) {
    console.error('Failed to load negotiators:', error)
  }
}

// Session preset management functions
async function loadRecentSessions() {
  await negotiationsStore.loadRecentSessions()
}

async function loadSessionPresets() {
  isLoadingPresets.value = true
  try {
    await negotiationsStore.loadSessionPresets()
  } finally {
    isLoadingPresets.value = false
  }
}

function buildSessionPreset(name) {
  return {
    name,
    scenario_path: selectedScenario.value?.path,
    scenario_name: selectedScenario.value?.name,
    negotiators: negotiators.value.map(n => ({
      type_name: n.type_name,
      name: n.name,
      source: n.source || 'native',
      requires_bridge: n.requires_bridge || false,
      params: n.params || {}
    })),
    mechanism_type: mechanismType.value,
    mechanism_params: mechanismParams.value,
    share_ufuns: shareUfuns.value,
    mode: runMode.value,
    step_delay: stepDelay.value,
    show_plot: displayOptions.value.showPlot,
    show_offers: displayOptions.value.showOffers,
    panels: panels.value
  }
}

async function saveFullSession() {
  console.log('[NewNegotiationModal] saveFullSession called')
  console.log('[NewNegotiationModal] savePresetName:', savePresetName.value)
  console.log('[NewNegotiationModal] selectedScenario:', selectedScenario.value)
  
  if (!savePresetName.value.trim() || !selectedScenario.value) {
    console.log('[NewNegotiationModal] Validation failed - missing name or scenario')
    return
  }
  
  const preset = buildSessionPreset(savePresetName.value.trim())
  console.log('[NewNegotiationModal] Built preset:', preset)
  
  const result = await negotiationsStore.saveSessionPreset(preset)
  console.log('[NewNegotiationModal] Save result:', result)
  
  // Show success message
  saveSuccessMessage.value = `Configuration "${savePresetName.value.trim()}" saved successfully!`
  setTimeout(() => {
    saveSuccessMessage.value = ''
  }, 3000)
  
  showSaveModal.value = false
  savePresetName.value = ''
  console.log('[NewNegotiationModal] Save modal closed')
}

async function deleteSessionPreset(name) {
  if (confirm(`Delete preset "${name}"?`)) {
    await negotiationsStore.deleteSessionPreset(name)
    await loadSessionPresets()
  }
}

function loadFullSession(session) {
  // Find the scenario in the loaded scenarios
  const scenario = scenarios.value.find(s => s.path === session.scenario_path)
  
  // Set scenario
  selectedScenario.value = scenario || { 
    path: session.scenario_path, 
    name: session.scenario_name,
    n_negotiators: session.negotiators?.length || 2
  }
  
  // Set negotiators
  negotiators.value = (session.negotiators || []).map((n, i) => ({
    type_name: n.type_name,
    name: n.name || `Agent${i + 1}`,
    source: n.source || 'native',
    requires_bridge: n.requires_bridge || false,
    params: n.params || {}
  }))
  
  // Ensure we have the right number of slots
  const requiredSlots = selectedScenario.value.n_negotiators || 2
  while (negotiators.value.length < requiredSlots) {
    negotiators.value.push(null)
  }
  
  // Set mechanism
  mechanismType.value = session.mechanism_type || 'SAOMechanism'
  shareUfuns.value = session.share_ufuns ?? false
  
  // Set mechanism params
  if (session.mechanism_params) {
    Object.assign(mechanismParams.value, session.mechanism_params)
  }
  
  // Set display options
  runMode.value = session.mode || 'realtime'
  stepDelay.value = session.step_delay ?? 100
  displayOptions.value.showPlot = session.show_plot ?? true
  displayOptions.value.showOffers = session.show_offers ?? true
  
  // Set panels
  if (session.panels) {
    Object.assign(panels.value, session.panels)
  }
  
  // Jump to display tab
  currentTab.value = 'display'
  
  // Close dropdown
  recentDropdownOpen.value = false
  savedDropdownOpen.value = false
}

// Watch for modal open/close
watch(() => props.show, (newShow) => {
  if (newShow) {
    currentTab.value = 'scenario'
    negotiatorSubTab.value = 'preset'
    selectedScenario.value = null
    negotiators.value = []
    loadScenarios()
    loadNegotiators()
    loadRecentSessions()
    loadSessionPresets()
  }
})

onMounted(() => {
  if (props.show) {
    loadScenarios()
    loadNegotiators()
  }
  
  // Close dropdowns on outside click
  document.addEventListener('click', closeDropdowns)
})

function closeDropdowns() {
  recentDropdownOpen.value = false
  savedDropdownOpen.value = false
}

onUnmounted(() => {
  document.removeEventListener('click', closeDropdowns)
})
</script>

<style>
/* Base Modal Styles - Not scoped because modal is teleported to body */
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
  z-index: 1000;
}

.modal {
  background: var(--bg-primary);
  border-radius: 12px;
  width: 90%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  position: relative;
}

.modal.large {
  max-width: 1400px;
}

.modal.small {
  max-width: 500px;
}

.success-toast {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: #10b981;
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  z-index: 1001;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    transform: translateX(-50%) translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  margin: 0;
  font-size: 1.5rem;
}

.modal-header-actions {
  display: flex;
  gap: 8px;
}

.modal-close {
  background: none;
  border: none;
  font-size: 2rem;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.modal-close:hover {
  background: var(--bg-hover);
}

.modal-body {
  flex: 1;
  overflow: hidden;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
}

/* Wizard Layout */
.wizard-layout {
  display: flex;
  height: 100%;
}

.wizard-sidebar {
  width: 200px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.wizard-tab {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: none;
  border: none;
  border-left: 3px solid transparent;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  text-align: left;
}

.wizard-tab:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.wizard-tab.active {
  border-left-color: var(--primary-color);
  background: var(--bg-hover);
  color: var(--primary-color);
}

.wizard-tab.completed::after {
  content: '✓';
  margin-left: auto;
  color: var(--success-color);
}

.wizard-tab-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.wizard-tab-label {
  font-size: 0.9rem;
  font-weight: 500;
}

.wizard-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.tab-content {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Form Elements */
.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-label-sm {
  display: block;
  margin-bottom: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

.form-input,
.form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.form-input-sm {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.form-hint {
  margin-top: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row > .form-group {
  flex: 1;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  margin-bottom: 8px;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.text-muted {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.text-muted-sm {
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.text-danger {
  color: var(--danger-color);
}

.text-secondary {
  color: var(--text-secondary);
}

.font-semibold {
  font-weight: 600;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
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

.btn-link {
  background: none;
  border: none;
  color: var(--primary-color);
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.85rem;
}

.btn-icon {
  padding: 8px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: var(--bg-hover);
}

.btn-icon.has-config {
  background: var(--primary-bg);
  border-color: var(--primary-color);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Badges */
.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.badge-sm {
  padding: 2px 6px;
  font-size: 0.7rem;
}

.badge-neutral {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.badge-primary {
  background: var(--primary-color);
  color: white;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.badge-remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  font-size: 1.2rem;
  line-height: 1;
}

/* Advanced Filters */
.advanced-filters {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.filters-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

/* Scenario List */
.scenario-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.scenario-card {
  padding: 16px;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.scenario-card:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.scenario-card.selected {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.scenario-card-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.scenario-card-meta {
  display: flex;
  gap: 12px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.scenario-details {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 8px;
}

.issue-item {
  margin-left: 12px;
  margin-top: 4px;
}

/* Secondary Tabs */
.tabs-secondary {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--border-color);
}

.tab {
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  color: var(--text-secondary);
  font-weight: 500;
  transition: all 0.2s;
  margin-bottom: -2px;
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

/* Negotiator List & Grid */
.negotiator-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.negotiator-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.2s;
  cursor: pointer;
}

.negotiator-item:hover {
  background: var(--bg-hover);
}

.negotiator-item.selected {
  border-color: var(--primary-color);
  background: var(--bg-tertiary);
}

.drag-handle {
  color: var(--text-secondary);
  cursor: grab;
  font-size: 1.2rem;
}

.negotiator-item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.negotiator-name-input {
  background: transparent;
  border: none;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 2px 4px;
  color: var(--text-primary);
  outline: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s;
}

.negotiator-name-input:focus {
  border-bottom-color: var(--primary-color);
}

.negotiator-type {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.negotiator-params {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: monospace;
}

.negotiator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.negotiator-card {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.negotiator-card:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.negotiator-card-name {
  font-weight: 600;
  margin-bottom: 6px;
}

.negotiator-card-meta {
  margin-bottom: 6px;
}

.negotiator-card-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

/* BOA/MAP Builders */
.boa-builder,
.map-builder {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.model-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.model-add {
  display: flex;
  gap: 8px;
}

.model-add .form-select {
  flex: 1;
}

/* Mechanism Selector */
.mechanism-selector {
  display: flex;
  gap: 12px;
}

.mechanism-card {
  flex: 1;
  padding: 16px;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--bg-secondary);
}

.mechanism-card:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.mechanism-card.selected {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.mechanism-name {
  font-weight: 600;
  font-size: 1.1rem;
}

.mechanism-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* Parameter Sections */
.param-section {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.param-section:last-child {
  border-bottom: none;
}

.param-section-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.param-section.collapsible .param-section-title {
  cursor: pointer;
}

.param-section-content {
  margin-top: 12px;
}

/* Summary Box */
.summary-box {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Run Mode Selector */
.run-mode-selector {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.run-mode-card {
  padding: 16px;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--bg-secondary);
}

.run-mode-card:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.run-mode-card.selected {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.run-mode-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.run-mode-title {
  font-weight: 600;
}

.run-mode-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* Range Input */
.form-range {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-tertiary);
  outline: none;
  -webkit-appearance: none;
}

.form-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-color);
  cursor: pointer;
}

.form-range::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-color);
  cursor: pointer;
  border: none;
}

/* Visible Panels Grid */
/* Disabled checkbox label */
.checkbox-label.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.checkbox-label.disabled input[type="checkbox"] {
  cursor: not-allowed;
}
</style>
