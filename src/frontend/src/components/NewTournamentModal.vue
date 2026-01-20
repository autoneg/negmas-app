<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal large">
      <div class="modal-header">
        <h2>New Tournament</h2>
        <button class="modal-close" @click="$emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="modal-body" style="padding: 0;">
        <div class="wizard-layout">
          <!-- Sidebar with tabs -->
          <div class="wizard-sidebar">
            <!-- Preset selector at top -->
            <div class="wizard-preset-selector">
              <label class="form-label">Load Preset</label>
              <select v-model="selectedPreset" class="form-select" @change="loadPreset">
                <option value="">-- Select preset --</option>
                <option v-for="preset in presets" :key="preset" :value="preset">{{ preset }}</option>
              </select>
            </div>
            
            <button 
              class="wizard-tab" 
              :class="{ active: currentTab === 'scenarios', completed: selectedScenarios.length > 0 }" 
              @click="currentTab = 'scenarios'"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <span class="wizard-tab-label">1. Scenarios</span>
              <span v-if="selectedScenarios.length > 0" class="wizard-badge">{{ selectedScenarios.length }}</span>
            </button>
            
            <button 
              class="wizard-tab" 
              :class="{ active: currentTab === 'competitors', completed: selectedCompetitors.length >= 1 }" 
              @click="currentTab = 'competitors'"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              <span class="wizard-tab-label">2. Competitors</span>
              <span v-if="selectedCompetitors.length > 0" class="wizard-badge">{{ selectedCompetitors.length }}</span>
            </button>
            
            <button 
              class="wizard-tab" 
              :class="{ active: currentTab === 'opponents', completed: opponentsSameAsCompetitors || selectedOpponents.length >= 1 }" 
              @click="currentTab = 'opponents'"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              <span class="wizard-tab-label">3. Opponents</span>
              <span v-if="!opponentsSameAsCompetitors && selectedOpponents.length > 0" class="wizard-badge">{{ selectedOpponents.length }}</span>
              <span v-else-if="opponentsSameAsCompetitors" class="wizard-badge badge-info">=</span>
            </button>
            
            <button 
              class="wizard-tab" 
              :class="{ active: currentTab === 'settings' }" 
              @click="currentTab = 'settings'"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
              <span class="wizard-tab-label">4. Settings</span>
            </button>
            
            <button 
              class="wizard-tab" 
              :class="{ active: currentTab === 'review', completed: canStartTournament }" 
              @click="currentTab = 'review'"
            >
              <svg class="wizard-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"></path>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
              </svg>
              <span class="wizard-tab-label">5. Review</span>
            </button>
          </div>
          
          <!-- Main content area -->
          <div class="wizard-content">
            <!-- Tab 1: Scenarios -->
            <div v-if="currentTab === 'scenarios'" class="wizard-panel">
              <div class="panel-header">
                <h3>Select Scenarios</h3>
              </div>
              
              <DualListSelector
                v-model="selectedScenarios"
                :items="scenarios"
                :item-key="(s) => s.path"
                :item-label="(s) => s.name"
                search-placeholder="Search scenarios..."
                :filter-fn="filterScenarios"
              >
                <template #filters>
                  <select v-model="scenarioSourceFilter" class="form-select filter-select">
                    <option value="">All sources</option>
                    <option v-for="src in scenarioSources" :key="src" :value="src">{{ src }}</option>
                  </select>
                  
                  <button class="btn btn-sm filter-toggle" @click="showAdvancedScenarioFilters = !showAdvancedScenarioFilters">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                    </svg>
                    Advanced Filters
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"
                         :style="{ transform: showAdvancedScenarioFilters ? 'rotate(180deg)' : '' }">
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </button>
                  
                  <div v-if="showAdvancedScenarioFilters" class="advanced-filters">
                    <div class="filter-row">
                      <label class="filter-label">Outcomes</label>
                      <div class="filter-range">
                        <input v-model.number="scenarioFilters.minOutcomes" type="number" placeholder="Min" class="filter-input" min="1" />
                        <span>-</span>
                        <input v-model.number="scenarioFilters.maxOutcomes" type="number" placeholder="Max" class="filter-input" min="1" />
                      </div>
                    </div>
                    <div class="filter-row">
                      <label class="filter-label">Rational Fraction</label>
                      <div class="filter-range">
                        <input v-model.number="scenarioFilters.minRationalFraction" type="number" placeholder="Min" class="filter-input" min="0" max="1" step="0.01" />
                        <span>-</span>
                        <input v-model.number="scenarioFilters.maxRationalFraction" type="number" placeholder="Max" class="filter-input" min="0" max="1" step="0.01" />
                      </div>
                    </div>
                    <div class="filter-row">
                      <label class="filter-label">Opposition</label>
                      <div class="filter-range">
                        <input v-model.number="scenarioFilters.minOpposition" type="number" placeholder="Min" class="filter-input" min="0" max="1" step="0.01" />
                        <span>-</span>
                        <input v-model.number="scenarioFilters.maxOpposition" type="number" placeholder="Max" class="filter-input" min="0" max="1" step="0.01" />
                      </div>
                    </div>
                    <button class="btn btn-sm btn-secondary" @click="clearScenarioFilters">
                      Clear Filters
                    </button>
                  </div>
                </template>
                
                <template #available-item="{ item }">
                  <div class="item-content">
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-meta">
                      <span class="badge badge-secondary">{{ item.source }}</span>
                      <span>{{ item.n_negotiators }}p</span>
                      <span v-if="item.n_outcomes">{{ formatNumber(item.n_outcomes) }} outcomes</span>
                      <span v-if="item.opposition != null" :title="`Opposition: ${item.opposition}`">
                        opp: {{ item.opposition?.toFixed(2) }}
                      </span>
                    </div>
                  </div>
                </template>
                
                <template #selected-item="{ item, remove }">
                  <div class="item-content">
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-meta">
                      <span>{{ item.source }}</span>
                      <span v-if="item.n_outcomes">{{ formatNumber(item.n_outcomes) }} out</span>
                      <span v-if="item.opposition != null">opp: {{ item.opposition?.toFixed(2) }}</span>
                    </div>
                  </div>
                  <button class="btn-remove" @click.stop="remove" title="Remove">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </template>
              </DualListSelector>
              
              <!-- Opposition vs Outcomes Graph (collapsible) -->
              <div v-if="selectedScenarios.length > 0" class="scenario-stats-graph">
                <div class="graph-header" @click="showOppositionGraph = !showOppositionGraph">
                  <span class="graph-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"
                         :style="{ transform: showOppositionGraph ? 'rotate(0deg)' : 'rotate(-90deg)' }">
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                    Opposition vs Outcomes
                  </span>
                  <span class="graph-count">{{ selectedScenarios.length }} scenarios</span>
                </div>
                <div v-if="showOppositionGraph" class="graph-content">
                  <div class="graph-placeholder">Chart placeholder - integrate with existing charting library</div>
                </div>
              </div>
            </div>
            
            <!-- Tab 2: Competitors -->
            <div v-if="currentTab === 'competitors'" class="wizard-panel">
              <div class="panel-header">
                <h3>Select Competitors</h3>
                <span class="panel-hint">(these agents will be scored)</span>
              </div>
              
              <DualListSelector
                v-model="selectedCompetitors"
                :items="negotiators"
                :item-key="(n) => n.type_name"
                :item-label="(n) => n.name"
                search-placeholder="Search negotiators..."
                :filter-fn="filterCompetitors"
              >
                <template #filters>
                  <select v-model="competitorSourceFilter" class="form-select filter-select">
                    <option value="">All sources</option>
                    <option value="virtual">Virtual (saved configs)</option>
                    <option v-for="src in negotiatorSources" :key="src" :value="src">{{ src }}</option>
                  </select>
                  
                  <select v-model="competitorTagFilter" class="form-select filter-select">
                    <option value="">All tags</option>
                    <option v-for="tag in negotiatorTags" :key="tag" :value="tag">{{ tag }}</option>
                  </select>
                </template>
                
                <template #available-item="{ item }">
                  <div class="item-content">
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-meta">
                      <span class="badge badge-secondary">{{ item.source }}</span>
                      <span v-if="item.description" class="item-description">{{ item.description }}</span>
                    </div>
                  </div>
                </template>
                
                <template #selected-item="{ item, remove }">
                  <div class="item-content">
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-meta">
                      <span v-if="item.has_params" class="badge badge-warning">Params</span>
                      <span v-if="item.is_virtual" class="badge badge-info">Virtual</span>
                    </div>
                  </div>
                  <div class="item-actions">
                    <button class="btn-config" @click.stop="configureCompetitor(item)" title="Configure">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                      </svg>
                    </button>
                    <button class="btn-remove" @click.stop="remove" title="Remove">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                </template>
              </DualListSelector>
            </div>
            
            <!-- Tab 3: Opponents -->
            <div v-if="currentTab === 'opponents'" class="wizard-panel">
              <div class="panel-header">
                <h3>Select Opponents</h3>
                <span class="panel-hint">(agents that competitors play against)</span>
              </div>
              
              <!-- Same as competitors checkbox -->
              <div class="form-group checkbox-card">
                <label class="form-checkbox">
                  <input v-model="opponentsSameAsCompetitors" type="checkbox" />
                  <span class="checkbox-text">Same as competitors</span>
                </label>
                <div class="checkbox-hint">
                  When checked, competitors play against each other (standard tournament mode).
                  Uncheck to specify separate opponents - competitors will play against opponents but only competitors are scored.
                </div>
              </div>
              
              <!-- Dual-list (shown when not same as competitors) -->
              <DualListSelector
                v-if="!opponentsSameAsCompetitors"
                v-model="selectedOpponents"
                :items="negotiators"
                :item-key="(n) => n.type_name"
                :item-label="(n) => n.name"
                search-placeholder="Search negotiators..."
                :filter-fn="filterOpponents"
              >
                <template #filters>
                  <select v-model="opponentSourceFilter" class="form-select filter-select">
                    <option value="">All sources</option>
                    <option value="virtual">Virtual (saved configs)</option>
                    <option v-for="src in negotiatorSources" :key="src" :value="src">{{ src }}</option>
                  </select>
                </template>
                
                <template #available-item="{ item }">
                  <div class="item-content">
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-meta">
                      <span class="badge badge-secondary">{{ item.source }}</span>
                      <span v-if="item.description" class="item-description">{{ item.description }}</span>
                    </div>
                  </div>
                </template>
                
                <template #selected-item="{ item, remove }">
                  <div class="item-content">
                    <div class="item-name">{{ item.name }}</div>
                    <div class="item-meta">
                      <span v-if="isAlsoCompetitor(item)" class="badge badge-success">Also competitor</span>
                    </div>
                  </div>
                  <button class="btn-remove" @click.stop="remove" title="Remove">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </template>
              </DualListSelector>
              
              <!-- Info when not using dual-list -->
              <div v-if="!opponentsSameAsCompetitors" class="info-panel">
                <button class="btn btn-sm btn-secondary" @click="copyCompetitorsToOpponents">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  Copy from competitors
                </button>
              </div>
            </div>
            
            <!-- Tab 4: Settings -->
            <div v-if="currentTab === 'settings'" class="wizard-panel">
              <div class="panel-header">
                <h3>Tournament Settings</h3>
              </div>
              
              <div class="settings-grid">
                <div class="form-group">
                  <label class="form-label">Repetitions</label>
                  <input v-model.number="settings.nRepetitions" type="number" min="1" max="100" class="form-input" />
                  <div class="form-hint">Run each pairing multiple times</div>
                </div>
                
                <div class="form-group">
                  <label class="form-label">
                    Max Steps
                    <label class="inline-checkbox">
                      <input v-model="settings.nStepsRangeEnabled" type="checkbox" />
                      <span>Range</span>
                    </label>
                  </label>
                  <div v-if="!settings.nStepsRangeEnabled">
                    <input v-model.number="settings.nSteps" type="number" min="1" class="form-input" />
                  </div>
                  <div v-else class="range-inputs">
                    <input v-model.number="settings.nStepsMin" type="number" min="1" placeholder="Min" class="form-input" />
                    <span>-</span>
                    <input v-model.number="settings.nStepsMax" type="number" min="1" placeholder="Max" class="form-input" />
                  </div>
                  <div v-if="settings.nStepsRangeEnabled" class="form-hint">Random sample per negotiation</div>
                </div>
                
                <div class="form-group">
                  <label class="form-label">
                    Time Limit (seconds)
                    <label class="inline-checkbox">
                      <input v-model="settings.timeLimitRangeEnabled" type="checkbox" />
                      <span>Range</span>
                    </label>
                  </label>
                  <div v-if="!settings.timeLimitRangeEnabled">
                    <input v-model.number="settings.timeLimit" type="number" min="0" step="0.1" placeholder="No limit" class="form-input" />
                  </div>
                  <div v-else class="range-inputs">
                    <input v-model.number="settings.timeLimitMin" type="number" min="0" step="0.1" placeholder="Min" class="form-input" />
                    <span>-</span>
                    <input v-model.number="settings.timeLimitMax" type="number" min="0" step="0.1" placeholder="Max" class="form-input" />
                  </div>
                  <div v-if="!settings.timeLimitRangeEnabled" class="form-hint">Max time per negotiation</div>
                  <div v-else class="form-hint">Random sample per negotiation</div>
                </div>
                
                <div class="form-group">
                  <label class="form-label">Mechanism</label>
                  <select v-model="settings.mechanismType" class="form-select">
                    <option value="SAOMechanism">SAO Mechanism</option>
                  </select>
                </div>
                
                <div class="form-group">
                  <label class="form-label">Score Metric</label>
                  <select v-model="settings.finalScoreMetric" class="form-select">
                    <option value="advantage">Advantage</option>
                    <option value="utility">Utility</option>
                    <option value="welfare">Welfare</option>
                    <option value="partner_welfare">Partner Welfare</option>
                  </select>
                </div>
                
                <div class="form-group">
                  <label class="form-label">Score Statistic</label>
                  <select v-model="settings.finalScoreStat" class="form-select">
                    <option value="mean">Mean</option>
                    <option value="median">Median</option>
                    <option value="min">Min</option>
                    <option value="max">Max</option>
                    <option value="std">Std Dev</option>
                  </select>
                </div>
              </div>
              
              <div class="form-group">
                <label class="form-checkbox">
                  <input v-model="settings.rotateUfuns" type="checkbox" />
                  <span>Rotate Utility Functions</span>
                </label>
                <div class="form-hint">Each pair plays both positions</div>
              </div>
              
              <div class="form-group">
                <label class="form-checkbox">
                  <input v-model="settings.selfPlay" type="checkbox" />
                  <span>Allow Self-Play</span>
                </label>
                <div class="form-hint">Allow competitors to play against themselves</div>
              </div>
              
              <div class="form-group">
                <label class="form-label">Utility Function Normalization</label>
                <select v-model="settings.normalization" class="form-select">
                  <option value="normalize">Normalize to [0, 1] (recommended)</option>
                  <option value="scale_max">Scale so max = 1.0</option>
                  <option value="scale_min">Scale so min = 1.0</option>
                  <option value="none">No normalization</option>
                </select>
                <div class="form-hint">How to transform utility values for fair cross-scenario comparison</div>
                <div v-if="settings.normalization === 'none'" class="warning-box">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                  <strong>Warning:</strong> Aggregating results without normalization may give disproportionate influence to scenarios with different utility scales.
                </div>
              </div>
              
              <div class="form-group">
                <label class="form-checkbox">
                  <input v-model="settings.ignoreDiscount" type="checkbox" />
                  <span>Ignore Discounting</span>
                </label>
                <div class="form-hint">Use base utility functions, ignoring time-based discounting</div>
              </div>
              
              <div class="form-group">
                <label class="form-checkbox">
                  <input v-model="settings.ignoreReserved" type="checkbox" />
                  <span>Ignore Reserved Values</span>
                </label>
                <div class="form-hint">Ignore reserved/disagreement values in utility functions</div>
              </div>
              
              <!-- Advanced Settings (Collapsible) -->
              <details class="advanced-settings">
                <summary>Advanced Settings</summary>
                
                <div class="advanced-section">
                  <h4>Time Limits</h4>
                  <div class="settings-grid-3">
                    <div class="form-group">
                      <label class="form-label">Step Time Limit</label>
                      <input v-model.number="settings.stepTimeLimit" type="number" min="0" step="0.1" placeholder="None" class="form-input" />
                      <div class="form-hint">Per-step limit (s)</div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">Negotiator Time</label>
                      <input v-model.number="settings.negotiatorTimeLimit" type="number" min="0" step="0.1" placeholder="None" class="form-input" />
                      <div class="form-hint">Total per negotiator (s)</div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">Hidden Time Limit</label>
                      <input v-model.number="settings.hiddenTimeLimit" type="number" min="0" step="0.1" placeholder="None" class="form-input" />
                      <div class="form-hint">Not revealed to agents</div>
                    </div>
                  </div>
                  
                  <h4>Probabilistic Ending</h4>
                  <div class="settings-grid">
                    <div class="form-group">
                      <label class="form-label">End Probability (per step)</label>
                      <input v-model.number="settings.pend" type="number" min="0" max="1" step="0.01" placeholder="0" class="form-input" />
                      <div class="form-hint">Prob. of ending each step</div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">End Prob. (per second)</label>
                      <input v-model.number="settings.pendPerSecond" type="number" min="0" max="1" step="0.01" placeholder="0" class="form-input" />
                      <div class="form-hint">Prob. of ending per second</div>
                    </div>
                  </div>
                  
                  <h4>Information Hiding</h4>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.idRevealsType" type="checkbox" />
                      <span>ID Reveals Type</span>
                    </label>
                    <div class="form-hint">Negotiator ID reveals its type to opponents</div>
                  </div>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.nameRevealsType" type="checkbox" />
                      <span>Name Reveals Type</span>
                    </label>
                    <div class="form-hint">Negotiator name reveals its type to opponents</div>
                  </div>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.maskScenarioNames" type="checkbox" />
                      <span>Mask Scenario Names</span>
                    </label>
                    <div class="form-hint">Hide scenario names from negotiators</div>
                  </div>
                  
                  <h4>Run Ordering</h4>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.randomizeRuns" type="checkbox" />
                      <span>Randomize Runs</span>
                    </label>
                    <div class="form-hint">Randomize order of negotiations</div>
                  </div>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.sortRuns" type="checkbox" />
                      <span>Sort Runs</span>
                    </label>
                    <div class="form-hint">Sort runs by scenario/competitors</div>
                  </div>
                  
                  <h4>Self-Play Options</h4>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.onlyFailuresOnSelfPlay" type="checkbox" />
                      <span>Only Failures on Self-Play</span>
                    </label>
                    <div class="form-hint">Only record failures for self-play negotiations</div>
                  </div>
                  
                  <h4>Save Options</h4>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.saveStats" type="checkbox" />
                      <span>Save Statistics</span>
                    </label>
                  </div>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.saveScenarioFigs" type="checkbox" />
                      <span>Save Scenario Figures</span>
                    </label>
                  </div>
                  <div class="form-group">
                    <label class="form-label">Save Every N Negotiations</label>
                    <input v-model.number="settings.saveEvery" type="number" min="0" placeholder="0 (only at end)" class="form-input" />
                    <div class="form-hint">0 = save only at end</div>
                  </div>
                  
                  <h4>Information Sharing</h4>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.passOpponentUfun" type="checkbox" />
                      <span>Pass Opponent Utility Function</span>
                    </label>
                    <div class="form-hint">Give each negotiator access to opponent's utility function via private_info</div>
                  </div>
                  
                  <h4>Error Handling</h4>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.raiseExceptions" type="checkbox" />
                      <span>Raise Exceptions</span>
                    </label>
                    <div class="form-hint">Stop tournament on negotiator errors (useful for debugging)</div>
                  </div>
                  
                  <h4>Execution & Performance</h4>
                  <div class="settings-grid-3">
                    <div class="form-group">
                      <label class="form-label">Parallel Jobs</label>
                      <input v-model.number="settings.njobs" type="number" class="form-input" placeholder="-1" />
                      <div class="form-hint">-1=serial, 0=all cores, N=specific</div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">External Timeout (s)</label>
                      <input v-model.number="settings.externalTimeout" type="number" min="0" placeholder="None" class="form-input" />
                      <div class="form-hint">Timeout for parallel negotiations</div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">Verbosity Level</label>
                      <input v-model.number="settings.verbosity" type="number" min="0" max="3" placeholder="0" class="form-input" />
                      <div class="form-hint">0=silent, 1-3=more verbose</div>
                    </div>
                  </div>
                  
                  <h4>Plotting & Visualization</h4>
                  <div class="settings-grid">
                    <div class="form-group">
                      <label class="form-label">Plot Fraction</label>
                      <input v-model.number="settings.plotFraction" type="number" min="0" max="1" step="0.1" placeholder="0.0" class="form-input" />
                      <div class="form-hint">Fraction of negotiations to plot (0.0-1.0)</div>
                    </div>
                  </div>
                  
                  <h4>Advanced Negotiator Options</h4>
                  <div class="form-group">
                    <label class="form-checkbox">
                      <input v-model="settings.rotatePrivateInfos" type="checkbox" />
                      <span>Rotate Private Infos</span>
                    </label>
                    <div class="form-hint">Rotate private information with utility functions when rotate_ufuns is enabled</div>
                  </div>
                  
                  <h4>Storage & Memory Optimization</h4>
                  <div class="settings-grid-3">
                    <div class="form-group">
                      <label class="form-label">Storage Optimization</label>
                      <select v-model="settings.storageOptimization" class="form-select">
                        <option value="speed">Speed (keep all files)</option>
                        <option value="balanced">Balanced</option>
                        <option value="space">Space (remove results/)</option>
                        <option value="max">Max (minimal files)</option>
                      </select>
                      <div class="form-hint">Controls disk space usage</div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">Memory Optimization</label>
                      <select v-model="settings.memoryOptimization" class="form-select">
                        <option value="speed">Speed (keep all in RAM)</option>
                        <option value="balanced">Balanced</option>
                        <option value="space">Space (load from disk)</option>
                      </select>
                      <div class="form-hint">Controls RAM usage</div>
                    </div>
                    <div class="form-group">
                      <label class="form-label">Storage Format</label>
                      <select v-model="settings.storageFormat" class="form-select">
                        <option value="">Auto (default)</option>
                        <option value="csv">CSV (human-readable)</option>
                        <option value="gzip">Gzip (compressed CSV)</option>
                        <option value="parquet">Parquet (best compression)</option>
                      </select>
                      <div class="form-hint">Format for large result files</div>
                    </div>
                  </div>
                </div>
              </details>
            </div>
            
            <!-- Tab 5: Review -->
            <div v-if="currentTab === 'review'" class="wizard-panel">
              <div class="panel-header">
                <h3>Review Tournament Configuration</h3>
              </div>
              
              <div class="review-container">
                <!-- Left column -->
                <div class="review-column">
                  <div class="review-section">
                    <h4>Scenarios</h4>
                    <div class="review-value">{{ selectedScenarios.length }} selected</div>
                    <div v-if="selectedScenarios.length > 0" class="review-list">
                      <div v-for="s in selectedScenarios.slice(0, 5)" :key="s.path" class="review-item">
                        {{ s.name }}
                      </div>
                      <div v-if="selectedScenarios.length > 5" class="review-more">
                        +{{ selectedScenarios.length - 5 }} more
                      </div>
                    </div>
                  </div>
                  
                  <div class="review-section">
                    <h4>Competitors</h4>
                    <div class="review-value">{{ selectedCompetitors.length }} selected</div>
                    <div v-if="selectedCompetitors.length > 0" class="review-list">
                      <div v-for="c in selectedCompetitors.slice(0, 5)" :key="c.type_name" class="review-item">
                        {{ c.name }}
                      </div>
                      <div v-if="selectedCompetitors.length > 5" class="review-more">
                        +{{ selectedCompetitors.length - 5 }} more
                      </div>
                    </div>
                  </div>
                  
                  <div class="review-section">
                    <h4>Opponents</h4>
                    <div v-if="opponentsSameAsCompetitors" class="review-value">
                      Same as competitors
                    </div>
                    <div v-else class="review-value">{{ selectedOpponents.length }} selected</div>
                  </div>
                  
                  <div class="review-section">
                    <h4>Estimated Total Negotiations</h4>
                    <div class="review-value estimated-total">
                      {{ estimatedTotalNegotiations.toLocaleString() }}
                    </div>
                    <div class="review-formula">
                      = {{ selectedScenarios.length }} scenarios × {{ selectedCompetitors.length }} competitors × 
                      {{ opponentsSameAsCompetitors ? selectedCompetitors.length : selectedOpponents.length }} opponents × 
                      {{ settings.nRepetitions }} repetitions
                      {{ settings.rotateUfuns ? ' × 2 (rotated)' : '' }}
                    </div>
                  </div>
                </div>
                
                <!-- Right column -->
                <div class="review-column">
                  <div class="review-section">
                    <h4>Settings</h4>
                    <div class="review-grid">
                      <div class="review-row">
                        <span class="review-label">Repetitions:</span>
                        <span class="review-value">{{ settings.nRepetitions }}</span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Max Steps:</span>
                        <span class="review-value">
                          {{ settings.nStepsRangeEnabled ? `${settings.nStepsMin}-${settings.nStepsMax}` : settings.nSteps }}
                        </span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Time Limit:</span>
                        <span class="review-value">
                          {{ settings.timeLimitRangeEnabled ? `${settings.timeLimitMin}-${settings.timeLimitMax}s` : (settings.timeLimit || 'None') }}
                        </span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Mechanism:</span>
                        <span class="review-value">{{ settings.mechanismType }}</span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Score Metric:</span>
                        <span class="review-value">{{ settings.finalScoreMetric }}</span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Score Statistic:</span>
                        <span class="review-value">{{ settings.finalScoreStat }}</span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Rotate Ufuns:</span>
                        <span class="review-value">{{ settings.rotateUfuns ? 'Yes' : 'No' }}</span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Self-Play:</span>
                        <span class="review-value">{{ settings.selfPlay ? 'Yes' : 'No' }}</span>
                      </div>
                      <div class="review-row">
                        <span class="review-label">Normalization:</span>
                        <span class="review-value">{{ settings.normalization }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div class="review-section">
                    <h4>Save Configuration</h4>
                    <div class="save-config-form">
                      <input v-model="presetName" type="text" placeholder="Preset name..." class="form-input" />
                      <button class="btn btn-secondary" @click="savePreset" :disabled="!presetName">
                        Save
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">
          Cancel
        </button>
        <button 
          v-if="currentTab === 'review'" 
          class="btn btn-primary" 
          @click="startTournament" 
          :disabled="!canStartTournament || starting"
        >
          {{ starting ? 'Starting...' : 'Start Tournament' }}
        </button>
        <button v-else class="btn btn-primary" @click="goToReview">
          Review & Start
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import DualListSelector from './DualListSelector.vue'

const props = defineProps({
  show: Boolean,
})

const emit = defineEmits(['close', 'start'])

// Current tab
const currentTab = ref('scenarios')

// Scenarios
const scenarios = ref([])
const selectedScenarios = ref([])
const scenarioSourceFilter = ref('')
const showAdvancedScenarioFilters = ref(false)
const scenarioFilters = ref({
  minOutcomes: null,
  maxOutcomes: null,
  minRationalFraction: null,
  maxRationalFraction: null,
  minOpposition: null,
  maxOpposition: null,
})
const showOppositionGraph = ref(false)

// Competitors
const negotiators = ref([])
const selectedCompetitors = ref([])
const competitorSourceFilter = ref('')
const competitorTagFilter = ref('')

// Opponents
const selectedOpponents = ref([])
const opponentsSameAsCompetitors = ref(true)
const opponentSourceFilter = ref('')

// Settings
const settings = ref({
  nRepetitions: 1,
  nSteps: 100,
  nStepsRangeEnabled: false,
  nStepsMin: 50,
  nStepsMax: 150,
  timeLimit: 0,
  timeLimitRangeEnabled: false,
  timeLimitMin: 10,
  timeLimitMax: 60,
  mechanismType: 'SAOMechanism',
  finalScoreMetric: 'advantage',
  finalScoreStat: 'mean',
  rotateUfuns: true,
  selfPlay: true,
  normalization: 'normalize',
  ignoreDiscount: false,
  ignoreReserved: false,
  // Advanced settings
  stepTimeLimit: null,
  negotiatorTimeLimit: null,
  hiddenTimeLimit: null,
  pend: 0,
  pendPerSecond: 0,
  idRevealsType: false,
  nameRevealsType: false,
  maskScenarioNames: false,
  randomizeRuns: false,
  sortRuns: false,
  onlyFailuresOnSelfPlay: false,
  saveStats: true,
  saveScenarioFigs: false,
  saveEvery: 0,
  passOpponentUfun: false,
  raiseExceptions: false,
  // NEW: Execution & Performance
  njobs: -1,
  externalTimeout: null,
  verbosity: 0,
  // NEW: Plotting
  plotFraction: 0.0,
  // NEW: Advanced negotiator options
  rotatePrivateInfos: true,
  // Storage
  storageOptimization: 'balanced',
  memoryOptimization: 'balanced',
  storageFormat: '',
})

// Presets
const presets = ref([])
const selectedPreset = ref('')
const presetName = ref('')

// UI state
const starting = ref(false)

// Computed
const scenarioSources = computed(() => {
  const sources = scenarios.value.map(s => s.source)
  return [...new Set(sources)]
})

const negotiatorSources = computed(() => {
  const sources = negotiators.value.map(n => n.source)
  return [...new Set(sources)]
})

const negotiatorTags = computed(() => {
  const tags = negotiators.value.flatMap(n => n.tags || [])
  return [...new Set(tags)]
})

const canStartTournament = computed(() => {
  return selectedScenarios.value.length >= 1 &&
         selectedCompetitors.value.length >= 1 &&
         (opponentsSameAsCompetitors.value || selectedOpponents.value.length >= 1)
})

const estimatedTotalNegotiations = computed(() => {
  const scenarios = selectedScenarios.value.length || 0
  const competitors = selectedCompetitors.value.length || 0
  const opponents = opponentsSameAsCompetitors.value ? competitors : (selectedOpponents.value.length || 0)
  const repetitions = settings.value.nRepetitions || 1
  const rotationMultiplier = settings.value.rotateUfuns ? 2 : 1
  
  return scenarios * competitors * opponents * repetitions * rotationMultiplier
})

// Filter functions
const filterScenarios = (scenario, searchQuery) => {
  // Apply search
  const query = searchQuery.toLowerCase()
  const matchesSearch = !query ||
    scenario.name.toLowerCase().includes(query) ||
    scenario.source.toLowerCase().includes(query) ||
    (scenario.tags && scenario.tags.some(t => t.toLowerCase().includes(query)))
  
  if (!matchesSearch) return false
  
  // Apply source filter
  if (scenarioSourceFilter.value && scenario.source !== scenarioSourceFilter.value) {
    return false
  }
  
  // Apply advanced filters
  const f = scenarioFilters.value
  if (f.minOutcomes && scenario.n_outcomes < f.minOutcomes) return false
  if (f.maxOutcomes && scenario.n_outcomes > f.maxOutcomes) return false
  if (f.minRationalFraction != null && (scenario.rational_fraction == null || scenario.rational_fraction < f.minRationalFraction)) return false
  if (f.maxRationalFraction != null && (scenario.rational_fraction == null || scenario.rational_fraction > f.maxRationalFraction)) return false
  if (f.minOpposition != null && (scenario.opposition == null || scenario.opposition < f.minOpposition)) return false
  if (f.maxOpposition != null && (scenario.opposition == null || scenario.opposition > f.maxOpposition)) return false
  
  return true
}

const filterCompetitors = (negotiator, searchQuery) => {
  const query = searchQuery.toLowerCase()
  const matchesSearch = !query ||
    negotiator.name.toLowerCase().includes(query) ||
    negotiator.type_name.toLowerCase().includes(query)
  
  if (!matchesSearch) return false
  
  if (competitorSourceFilter.value) {
    if (competitorSourceFilter.value === 'virtual' && !negotiator.is_virtual) return false
    if (competitorSourceFilter.value !== 'virtual' && negotiator.source !== competitorSourceFilter.value) return false
  }
  
  if (competitorTagFilter.value) {
    if (!negotiator.tags || !negotiator.tags.includes(competitorTagFilter.value)) return false
  }
  
  return true
}

const filterOpponents = (negotiator, searchQuery) => {
  const query = searchQuery.toLowerCase()
  const matchesSearch = !query ||
    negotiator.name.toLowerCase().includes(query) ||
    negotiator.type_name.toLowerCase().includes(query)
  
  if (!matchesSearch) return false
  
  if (opponentSourceFilter.value) {
    if (opponentSourceFilter.value === 'virtual' && !negotiator.is_virtual) return false
    if (opponentSourceFilter.value !== 'virtual' && negotiator.source !== opponentSourceFilter.value) return false
  }
  
  return true
}

// Methods
const formatNumber = (num) => {
  if (num === null || num === undefined) return 'N/A'
  if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
  return num.toString()
}

const clearScenarioFilters = () => {
  scenarioFilters.value = {
    minOutcomes: null,
    maxOutcomes: null,
    minRationalFraction: null,
    maxRationalFraction: null,
    minOpposition: null,
    maxOpposition: null,
  }
}

const configureCompetitor = (competitor) => {
  // TODO: Open competitor config modal
  console.log('Configure competitor:', competitor)
}

const isAlsoCompetitor = (opponent) => {
  return selectedCompetitors.value.some(c => c.type_name === opponent.type_name)
}

const copyCompetitorsToOpponents = () => {
  selectedOpponents.value = [...selectedCompetitors.value]
}

const goToReview = () => {
  currentTab.value = 'review'
}

const loadPreset = () => {
  // TODO: Load preset configuration
  console.log('Load preset:', selectedPreset.value)
}

const savePreset = () => {
  // TODO: Save current configuration as preset
  console.log('Save preset:', presetName.value)
}

const startTournament = async () => {
  if (!canStartTournament.value || starting.value) return
  
  starting.value = true
  
  try {
    const request = {
      competitor_types: selectedCompetitors.value.map(c => c.type_name),
      scenario_paths: selectedScenarios.value.map(s => s.path),
      opponent_types: opponentsSameAsCompetitors.value ? null : selectedOpponents.value.map(o => o.type_name),
      competitor_params: null,
      opponent_params: null,
      n_repetitions: settings.value.nRepetitions,
      rotate_ufuns: settings.value.rotateUfuns,
      self_play: settings.value.selfPlay,
      mechanism_type: settings.value.mechanismType,
      n_steps: settings.value.nStepsRangeEnabled ? [settings.value.nStepsMin, settings.value.nStepsMax] : settings.value.nSteps,
      time_limit: settings.value.timeLimitRangeEnabled ? [settings.value.timeLimitMin, settings.value.timeLimitMax] : (settings.value.timeLimit || null),
      final_score_metric: settings.value.finalScoreMetric,
      final_score_stat: settings.value.finalScoreStat,
      normalization: settings.value.normalization,
      ignore_discount: settings.value.ignoreDiscount,
      ignore_reserved: settings.value.ignoreReserved,
      save_stats: settings.value.saveStats,
      // Advanced settings
      step_time_limit: settings.value.stepTimeLimit || null,
      negotiator_time_limit: settings.value.negotiatorTimeLimit || null,
      hidden_time_limit: settings.value.hiddenTimeLimit || null,
      pend: settings.value.pend || 0,
      pend_per_second: settings.value.pendPerSecond || 0,
      id_reveals_type: settings.value.idRevealsType,
      name_reveals_type: settings.value.nameRevealsType,
      mask_scenario_names: settings.value.maskScenarioNames,
      randomize_runs: settings.value.randomizeRuns,
      sort_runs: settings.value.sortRuns,
      only_failures_on_self_play: settings.value.onlyFailuresOnSelfPlay,
      save_scenario_figs: settings.value.saveScenarioFigs,
      save_every: settings.value.saveEvery || 0,
      pass_opponent_ufun: settings.value.passOpponentUfun,
      raise_exceptions: settings.value.raiseExceptions,
      // NEW: Execution & Performance
      njobs: settings.value.njobs,
      external_timeout: settings.value.externalTimeout || null,
      verbosity: settings.value.verbosity || 0,
      // NEW: Plotting
      plot_fraction: settings.value.plotFraction || 0.0,
      // NEW: Advanced negotiator options
      rotate_private_infos: settings.value.rotatePrivateInfos,
      // Storage
      storage_optimization: settings.value.storageOptimization,
      memory_optimization: settings.value.memoryOptimization,
      storage_format: settings.value.storageFormat || null,
    }
    
    const response = await fetch('/api/tournament/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()
    emit('start', data)
    emit('close')
  } catch (error) {
    console.error('Failed to start tournament:', error)
    alert('Failed to start tournament: ' + error.message)
  } finally {
    starting.value = false
  }
}

const loadData = async () => {
  try {
    const [scenariosRes, negotiatorsRes] = await Promise.all([
      fetch('/api/scenarios'),
      fetch('/api/negotiators'),
    ])
    
    const scenariosData = await scenariosRes.json()
    const negotiatorsData = await negotiatorsRes.json()
    
    scenarios.value = scenariosData.scenarios || []
    negotiators.value = negotiatorsData.negotiators || []
  } catch (error) {
    console.error('Failed to load data:', error)
  }
}

// Watch for modal open/close
watch(() => props.show, (newShow) => {
  if (newShow) {
    currentTab.value = 'scenarios'
    selectedScenarios.value = []
    selectedCompetitors.value = []
    selectedOpponents.value = []
    opponentsSameAsCompetitors.value = true
    loadData()
  }
})
</script>

<style scoped>
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
  max-width: 1100px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal.large {
  max-width: 1200px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
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

.wizard-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  height: 600px;
}

.wizard-sidebar {
  border-right: 1px solid var(--border-color);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
}

.wizard-preset-selector {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.wizard-tab {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.wizard-tab:hover {
  background: var(--bg-hover);
}

.wizard-tab.active {
  background: var(--bg-primary);
  color: var(--primary);
  border-left-color: var(--primary);
}

.wizard-tab.completed .wizard-badge {
  background: var(--success-bg);
  color: var(--success);
}

.wizard-tab-icon {
  width: 18px;
  height: 18px;
}

.wizard-tab-label {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
}

.wizard-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
}

.wizard-badge.badge-info {
  background: var(--info-bg);
  color: var(--info);
}

.wizard-content {
  overflow-y: auto;
  padding: 24px;
}

.wizard-panel {
  animation: fadeIn 0.3s ease-out;
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

.panel-header {
  margin-bottom: 20px;
}

.panel-header h3 {
  margin: 0 0 4px 0;
  font-size: 1.25rem;
}

.panel-hint {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.form-label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--text-secondary);
}

.form-select,
.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
}

.filter-select {
  margin-top: 8px;
  font-size: 12px;
  padding: 4px 8px;
}

.filter-toggle {
  margin-top: 8px;
  width: 100%;
  font-size: 11px;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.advanced-filters {
  margin-top: 8px;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  font-size: 11px;
}

.filter-row {
  margin-bottom: 6px;
}

.filter-label {
  font-size: 10px;
  margin-bottom: 2px;
  display: block;
}

.filter-range {
  display: flex;
  gap: 4px;
  align-items: center;
}

.filter-input {
  width: 70px;
  font-size: 11px;
  padding: 3px 6px;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  flex-wrap: wrap;
}

.item-description {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}

.btn-config,
.btn-remove {
  padding: 4px;
  background: transparent;
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.btn-config:hover {
  background: var(--primary-bg);
  color: var(--primary);
}

.btn-remove:hover {
  background: var(--danger-bg);
  color: var(--danger);
}

.badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.badge-secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.badge-warning {
  background: var(--warning-bg);
  color: var(--warning);
}

.badge-info {
  background: var(--info-bg);
  color: var(--info);
}

.badge-success {
  background: var(--success-bg);
  color: var(--success);
}

.scenario-stats-graph {
  margin-top: 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.graph-header {
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.graph-title {
  font-weight: 600;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.graph-count {
  color: var(--text-muted);
  font-size: 11px;
}

.graph-content {
  padding: 8px;
}

.graph-placeholder {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 13px;
}

.checkbox-card {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.checkbox-text {
  font-weight: 500;
}

.checkbox-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
  margin-left: 26px;
}

.info-panel {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  display: flex;
  justify-content: center;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.settings-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inline-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  font-weight: normal;
  font-size: 11px;
}

.range-inputs {
  display: flex;
  gap: 8px;
  align-items: center;
}

.range-inputs input {
  width: 80px;
}

.form-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.warning-box {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(255, 193, 7, 0.15);
  border: 1px solid rgba(255, 193, 7, 0.5);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-warning);
  display: flex;
  align-items: center;
  gap: 6px;
}

.advanced-settings {
  margin-top: 24px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
}

.advanced-settings summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--text-secondary);
  list-style: none;
}

.advanced-settings summary::-webkit-details-marker {
  display: none;
}

.advanced-section {
  margin-top: 16px;
}

.advanced-section h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 16px 0 12px;
}

.advanced-section h4:first-child {
  margin-top: 0;
}

.review-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.review-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.review-section h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.review-value {
  font-weight: 500;
  margin-bottom: 6px;
}

.review-list {
  font-size: 13px;
  color: var(--text-secondary);
}

.review-item {
  padding: 4px 0;
  border-bottom: 1px solid var(--border-color);
}

.review-item:last-child {
  border-bottom: none;
}

.review-more {
  padding: 4px 0;
  color: var(--text-muted);
  font-style: italic;
}

.estimated-total {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
}

.review-formula {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.4;
}

.review-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}

.review-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-color);
}

.review-label {
  color: var(--text-secondary);
}

.save-config-form {
  display: flex;
  gap: 8px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary);
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

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  font-size: 11px;
  padding: 6px 12px;
}
</style>
