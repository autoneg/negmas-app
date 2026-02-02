<template>
  <!-- Stats Modal -->
  <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
    <div class="modal-content modal-xlg">
      <!-- Header -->
      <div class="modal-header">
        <h3 class="modal-title">Scenario Statistics & Information</h3>
        <button class="modal-close-btn" @click="$emit('close')" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <!-- Body -->
      <div class="modal-body" style="max-height: 80vh; overflow-y: auto; background: var(--bg-primary);">
        <div v-if="isLoading" class="empty-state" style="padding: 40px;">
          <div class="loading-spinner"></div>
          <p>Loading scenario data...</p>
        </div>
        
        <div v-else-if="loadError" class="empty-state" style="padding: 40px;">
          <p style="color: var(--text-error);">{{ loadError }}</p>
          <button @click="loadAllData" class="btn btn-primary" style="margin-top: 16px;">
            Retry
          </button>
        </div>
        
        <div v-else-if="!scenarioInfo && !stats" class="empty-state" style="padding: 40px;">
          <p>No data available for this scenario.</p>
          <button 
            v-if="scenarioId && !calculatingStats" 
            @click="calculateStats" 
            class="btn btn-primary"
            style="margin-top: 16px;"
          >
            Calculate Statistics
          </button>
          <div v-if="calculatingStats" style="margin-top: 16px;">
            <div class="loading-spinner"></div>
            <p style="margin-top: 8px;">Calculating statistics...</p>
          </div>
        </div>
        
        <div v-else class="stats-container">
          <!-- Top Section: 4 collapsible panels -->
          <div class="stats-grid-4col">
            <!-- Basic Information Panel -->
            <div class="stats-section" :class="{ collapsed: !panels.basicInfo }">
              <h4 class="stats-section-title clickable" @click="togglePanel('basicInfo')">
                <span class="collapse-icon">{{ panels.basicInfo ? '▼' : '▶' }}</span>
                Basic Information
                <DetailsIcon 
                  v-if="scenarioId && panels.basicInfo"
                  title="View full scenario details"
                  @click="showObjectDetail('scenario', 'Scenario', 'Scenario')"
                />
              </h4>
              <div v-show="panels.basicInfo" class="stats-rows">
                <div v-if="props.negotiation?.scenario_path" class="stats-row">
                  <span class="stats-label">Path:</span>
                  <span class="stats-value monospace small" :title="props.negotiation.scenario_path">{{ truncatePath(props.negotiation.scenario_path) }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Name:</span>
                  <span class="stats-value">{{ scenarioInfo?.name || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Format:</span>
                  <span class="stats-value">
                    <span v-if="scenarioInfo?.format_label" class="format-badge" :class="formatClass">{{ scenarioInfo.format_label }}</span>
                    <span v-else class="text-muted">N/A</span>
                  </span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Negotiators:</span>
                  <span class="stats-value">{{ scenarioInfo?.n_negotiators || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Issues:</span>
                  <span class="stats-value">{{ scenarioInfo?.n_issues || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Outcomes:</span>
                  <span class="stats-value">{{ scenarioInfo?.n_outcomes?.toLocaleString() || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Normalized:</span>
                  <span class="stats-value">
                    <span v-if="scenarioInfo?.normalized === true" class="status-badge success">Yes</span>
                    <span v-else-if="scenarioInfo?.normalized === false" class="status-badge warning">No</span>
                    <span v-else class="text-muted">N/A</span>
                  </span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Finite UFs:</span>
                  <span class="stats-value">
                    <span v-if="scenarioInfo?.finite_ufuns === true" class="status-badge success">Yes</span>
                    <span v-else-if="scenarioInfo?.finite_ufuns === false" class="status-badge warning">No</span>
                    <span v-else class="text-muted">N/A</span>
                  </span>
                </div>
                <!-- Tags -->
                <div v-if="scenarioInfo?.tags && scenarioInfo.tags.length > 0" class="stats-row" style="flex-wrap: wrap;">
                  <span class="stats-label">Tags:</span>
                  <span class="stats-value">
                    <span v-for="(tag, idx) in scenarioInfo.tags" :key="`tag-${idx}`" class="tag-chip">{{ tag }}</span>
                  </span>
                </div>
              </div>
            </div>
            
            <!-- Scenario Metrics Panel -->
            <div class="stats-section" :class="{ collapsed: !panels.metrics }">
              <h4 class="stats-section-title clickable" @click="togglePanel('metrics')">
                <span class="collapse-icon">{{ panels.metrics ? '▼' : '▶' }}</span>
                Scenario Metrics
              </h4>
              <div v-show="panels.metrics" class="stats-rows">
                <div class="stats-row">
                  <span class="stats-label">Opposition:</span>
                  <span class="stats-value">{{ formatNumber(scenarioInfo?.opposition, 4) }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Rational Fraction:</span>
                  <span class="stats-value">{{ formatPercent(scenarioInfo?.rational_fraction) }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Pareto Outcomes:</span>
                  <span class="stats-value">{{ scenarioInfo?.n_pareto?.toLocaleString() || paretoCount?.toLocaleString() || 'N/A' }}</span>
                </div>
                <div v-if="stats?.utility_ranges" class="stats-row">
                  <span class="stats-label">Utility Ranges:</span>
                  <span class="stats-value monospace" style="font-size: 11px;">
                    {{ stats.utility_ranges.map(r => `[${r[0].toFixed(2)}, ${r[1].toFixed(2)}]`).join(', ') }}
                  </span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Has Stats:</span>
                  <span class="stats-value">
                    <span v-if="scenarioInfo?.has_stats" class="status-badge success">Yes</span>
                    <span v-else class="status-badge warning">No</span>
                  </span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Has Info:</span>
                  <span class="stats-value">
                    <span v-if="scenarioInfo?.has_info" class="status-badge success">Yes</span>
                    <span v-else class="status-badge warning">No</span>
                  </span>
                </div>
              </div>
            </div>

            <!-- Outcome Space Panel -->
            <div class="stats-section" :class="{ collapsed: !panels.outcomeSpace }">
              <h4 class="stats-section-title clickable" @click="togglePanel('outcomeSpace')">
                <span class="collapse-icon">{{ panels.outcomeSpace ? '▼' : '▶' }}</span>
                Outcome Space
                <DetailsIcon 
                  v-if="scenarioId && panels.outcomeSpace"
                  title="View full outcome space details"
                  @click="showObjectDetail('outcome_space', 'Outcome Space', 'OutcomeSpace')"
                />
              </h4>
              <div v-show="panels.outcomeSpace" class="stats-rows">
                <div v-if="scenarioInfo?.issues && scenarioInfo.issues.length > 0">
                  <div v-for="(issue, idx) in scenarioInfo.issues" :key="`issue-${idx}`" class="issue-item">
                    <div class="issue-header-compact">
                      <span class="issue-name-compact">{{ issue.name }}</span>
                      <span class="issue-type-badge-small">{{ formatIssueType(issue.type) }}</span>
                    </div>
                    <div class="issue-values-compact">
                      <span v-if="issue.values && issue.values.length > 0" class="issue-values-text">
                        {{ issue.values.slice(0, 4).join(', ') }}<span v-if="issue.values.length > 4"> (+{{ issue.values.length - 4 }})</span>
                      </span>
                      <span v-else-if="issue.min_value !== undefined && issue.max_value !== undefined" class="issue-range-text">
                        [{{ issue.min_value }}, {{ issue.max_value }}]
                      </span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-text">No issues data</div>
              </div>
            </div>
            
            <!-- Utility Functions Panel -->
            <div class="stats-section" :class="{ collapsed: !panels.ufuns }">
              <h4 class="stats-section-title clickable" @click="togglePanel('ufuns')">
                <span class="collapse-icon">{{ panels.ufuns ? '▼' : '▶' }}</span>
                Utility Functions
              </h4>
              <div v-show="panels.ufuns">
                <div v-if="loadingUfuns" class="empty-text">
                  <div class="loading-spinner-small"></div>
                  Loading...
                </div>
                <div v-else-if="ufunDetails && ufunDetails.length > 0" class="ufuns-list">
                  <div v-for="(ufun, idx) in ufunDetails" :key="`ufun-${idx}`" class="ufun-item">
                    <UfunDisplay 
                      :ufun="ufun"
                      :index="idx"
                      :show-details-icon="!!scenarioId"
                      @details="showObjectDetail('ufun', ufun.name || `Utility Function ${idx + 1}`, ufun.type || 'UtilityFunction', idx)"
                    />
                  </div>
                </div>
                <div v-else-if="scenarioInfo?.n_negotiators" class="ufuns-list">
                  <div v-for="idx in scenarioInfo.n_negotiators" :key="`ufun-${idx}`" class="ufun-placeholder">
                    Utility Function {{ idx }}
                  </div>
                </div>
                <div v-else class="empty-text">No utility functions</div>
              </div>
            </div>
          </div>

          <!-- Solution Concepts (4 columns) -->
          <div v-if="stats && (stats.nash_point || stats.kalai_point || stats.kalai_smorodinsky_point || stats.max_welfare_point)" class="solution-concepts-section">
            <h4 class="stats-section-title clickable" @click="togglePanel('solutions')" style="margin-bottom: 16px;">
              <span class="collapse-icon">{{ panels.solutions ? '▼' : '▶' }}</span>
              Solution Concepts
            </h4>
            <div v-show="panels.solutions" class="stats-grid-4col">
              <!-- Nash Point -->
              <div v-if="stats.nash_point" class="stats-section compact">
                <h5 class="solution-title">Nash Bargaining</h5>
                <div class="stats-rows">
                  <div class="stats-row">
                    <span class="stats-label">Outcome:</span>
                    <span 
                      class="stats-value monospace small clickable" 
                      @click="showOutcomeDetail('Nash', stats.nash_point.outcome)"
                      title="Click to see full outcome"
                    >
                      {{ formatOutcome(stats.nash_point.outcome) }}
                    </span>
                  </div>
                  <div v-for="(utility, idx) in stats.nash_point.utilities" :key="`nash-${idx}`" class="stats-row">
                    <span class="stats-label">{{ getUfunName(idx) }}:</span>
                    <span class="stats-value">{{ utility.toFixed(3) }}</span>
                  </div>
                  <div v-if="stats.nash_point.welfare" class="stats-row">
                    <span class="stats-label">Welfare:</span>
                    <span class="stats-value">{{ stats.nash_point.welfare.toFixed(3) }}</span>
                  </div>
                </div>
              </div>

              <!-- Kalai Point -->
              <div v-if="stats.kalai_point" class="stats-section compact">
                <h5 class="solution-title">Kalai</h5>
                <div class="stats-rows">
                  <div class="stats-row">
                    <span class="stats-label">Outcome:</span>
                    <span 
                      class="stats-value monospace small clickable" 
                      @click="showOutcomeDetail('Kalai', stats.kalai_point.outcome)"
                      title="Click to see full outcome"
                    >
                      {{ formatOutcome(stats.kalai_point.outcome) }}
                    </span>
                  </div>
                  <div v-for="(utility, idx) in stats.kalai_point.utilities" :key="`kalai-${idx}`" class="stats-row">
                    <span class="stats-label">{{ getUfunName(idx) }}:</span>
                    <span class="stats-value">{{ utility.toFixed(3) }}</span>
                  </div>
                  <div v-if="stats.kalai_point.welfare" class="stats-row">
                    <span class="stats-label">Welfare:</span>
                    <span class="stats-value">{{ stats.kalai_point.welfare.toFixed(3) }}</span>
                  </div>
                </div>
              </div>

              <!-- KS Point -->
              <div v-if="stats.kalai_smorodinsky_point" class="stats-section compact">
                <h5 class="solution-title">Kalai-Smorodinsky</h5>
                <div class="stats-rows">
                  <div class="stats-row">
                    <span class="stats-label">Outcome:</span>
                    <span 
                      class="stats-value monospace small clickable" 
                      @click="showOutcomeDetail('Kalai-Smorodinsky', stats.kalai_smorodinsky_point.outcome)"
                      title="Click to see full outcome"
                    >
                      {{ formatOutcome(stats.kalai_smorodinsky_point.outcome) }}
                    </span>
                  </div>
                  <div v-for="(utility, idx) in stats.kalai_smorodinsky_point.utilities" :key="`ks-${idx}`" class="stats-row">
                    <span class="stats-label">{{ getUfunName(idx) }}:</span>
                    <span class="stats-value">{{ utility.toFixed(3) }}</span>
                  </div>
                  <div v-if="stats.kalai_smorodinsky_point.welfare" class="stats-row">
                    <span class="stats-label">Welfare:</span>
                    <span class="stats-value">{{ stats.kalai_smorodinsky_point.welfare.toFixed(3) }}</span>
                  </div>
                </div>
              </div>

              <!-- Max Welfare Point -->
              <div v-if="stats.max_welfare_point" class="stats-section compact">
                <h5 class="solution-title">Max Welfare</h5>
                <div class="stats-rows">
                  <div class="stats-row">
                    <span class="stats-label">Outcome:</span>
                    <span 
                      class="stats-value monospace small clickable" 
                      @click="showOutcomeDetail('Max Welfare', stats.max_welfare_point.outcome)"
                      title="Click to see full outcome"
                    >
                      {{ formatOutcome(stats.max_welfare_point.outcome) }}
                    </span>
                  </div>
                  <div v-for="(utility, idx) in stats.max_welfare_point.utilities" :key="`welfare-${idx}`" class="stats-row">
                    <span class="stats-label">{{ getUfunName(idx) }}:</span>
                    <span class="stats-value">{{ utility.toFixed(3) }}</span>
                  </div>
                  <div v-if="stats.max_welfare_point.welfare" class="stats-row">
                    <span class="stats-label">Welfare:</span>
                    <span class="stats-value">{{ stats.max_welfare_point.welfare.toFixed(3) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Calculate Stats Button (if no stats) -->
          <div v-if="scenarioId && !scenarioInfo?.has_stats && !calculatingStats" class="stats-section-full">
            <button @click="calculateStats" class="btn btn-primary" style="width: 100%;">
              Calculate Full Statistics
            </button>
          </div>
          <div v-if="calculatingStats" class="stats-section-full">
            <div class="empty-state" style="padding: 20px;">
              <div class="loading-spinner"></div>
              <p style="margin-top: 8px;">Calculating statistics...</p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">
          Close
        </button>
      </div>
    </div>
  </div>

  <!-- Outcome Detail Modal -->
  <div v-if="showOutcomeModal" class="modal-overlay active" @click.self="showOutcomeModal = false">
    <div class="modal-content modal-sm">
      <div class="modal-header">
        <h3 class="modal-title">{{ outcomeModalTitle }}</h3>
        <button class="modal-close-btn" @click="showOutcomeModal = false" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="modal-body" style="max-height: 60vh; overflow-y: auto; background: var(--bg-primary);">
        <div v-if="Array.isArray(outcomeModalData)" class="outcome-detail-list">
          <div v-for="(value, idx) in outcomeModalData" :key="`val-${idx}`" class="outcome-detail-row">
            <span class="outcome-detail-label">{{ scenarioInfo?.issues?.[idx]?.name || `Issue ${idx + 1}` }}:</span>
            <span class="outcome-detail-value">{{ value }}</span>
          </div>
        </div>
        <div v-else-if="typeof outcomeModalData === 'object'" class="outcome-detail-list">
          <div v-for="(value, key) in outcomeModalData" :key="`key-${key}`" class="outcome-detail-row">
            <span class="outcome-detail-label">{{ key }}:</span>
            <span class="outcome-detail-value">{{ value }}</span>
          </div>
        </div>
        <div v-else class="outcome-detail-list">
          <p>{{ outcomeModalData }}</p>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="showOutcomeModal = false">Close</button>
      </div>
    </div>
  </div>

  <!-- Object Detail Modal (for ufuns, outcome space, scenario) -->
  <ObjectDetailModal
    :show="showObjectDetailModal"
    :title="objectDetailTitle"
    :object-type="objectDetailType"
    :fetch-url="objectDetailUrl"
    :large="true"
    :default-expand-depth="2"
    @close="showObjectDetailModal = false"
  />
</template>

<script setup>
import { computed, ref, watch, reactive } from 'vue'
import UfunDisplay from './UfunDisplay.vue'
import ObjectDetailModal from './ObjectDetailModal.vue'
import DetailsIcon from './DetailsIcon.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  negotiation: {
    type: Object,
    default: null
  },
  // Optional: for tournament scenarios, provide tournamentId and scenarioName
  // instead of using negotiation.scenario_path
  tournamentId: {
    type: String,
    default: null
  },
  scenarioName: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['close'])

const scenarioStats = ref(null)
const scenarioInfo = ref(null)
const ufunDetails = ref([])
const loadingStats = ref(false)
const loadingInfo = ref(false)
const loadingUfuns = ref(false)
const calculatingStats = ref(false)
const loadError = ref(null)

// Track which scenario path we've loaded data for
const loadedScenarioPath = ref(null)

// Collapsible panel states
const panels = reactive({
  basicInfo: true,
  metrics: true,
  outcomeSpace: true,
  ufuns: true,
  solutions: true
})

// Outcome detail modal
const showOutcomeModal = ref(false)
const outcomeModalTitle = ref('')
const outcomeModalData = ref(null)

// Object detail modal (for ufuns, outcome space, etc.)
const showObjectDetailModal = ref(false)
const objectDetailTitle = ref('')
const objectDetailType = ref('')
const objectDetailUrl = ref('')

// Compute scenario ID from path (for regular scenarios)
const scenarioId = computed(() => {
  // If tournament scenario, we don't use scenarioId - we use tournamentId + scenarioName directly
  if (props.tournamentId && props.scenarioName) return null
  if (!props.negotiation?.scenario_path) return null
  return btoa(props.negotiation.scenario_path)
})

// Check if this is a tournament scenario
const isTournamentScenario = computed(() => {
  return !!(props.tournamentId && props.scenarioName)
})

// Combined loading state
const isLoading = computed(() => loadingInfo.value || loadingStats.value)

// Reset all data
function resetData() {
  scenarioInfo.value = null
  scenarioStats.value = null
  ufunDetails.value = []
  loadError.value = null
}

// Load all data
async function loadAllData() {
  // Need either scenarioId (regular) or tournamentId+scenarioName (tournament)
  if (!scenarioId.value && !isTournamentScenario.value) return
  
  loadError.value = null
  
  // Load all data in parallel
  await Promise.all([
    loadScenarioInfo(),
    loadScenarioStats(),
    loadUfunDetails()
  ])
  
  // Mark as loaded for this path/scenario
  loadedScenarioPath.value = isTournamentScenario.value 
    ? `tournament:${props.tournamentId}:${props.scenarioName}`
    : props.negotiation?.scenario_path
}

// Load scenario data when modal opens or scenario changes
watch(() => props.show, async (show) => {
  if (show) {
    const currentKey = isTournamentScenario.value 
      ? `tournament:${props.tournamentId}:${props.scenarioName}`
      : props.negotiation?.scenario_path
    
    if (currentKey && (loadedScenarioPath.value !== currentKey || !scenarioInfo.value)) {
      resetData()
      await loadAllData()
    }
  }
}, { immediate: true })

// Also watch for scenario path changes while modal is open
watch(() => props.negotiation?.scenario_path, async (newPath, oldPath) => {
  if (props.show && newPath && newPath !== oldPath && !isTournamentScenario.value) {
    resetData()
    await loadAllData()
  }
})

// Watch for tournament scenario changes
watch([() => props.tournamentId, () => props.scenarioName], async ([newTournamentId, newScenarioName], [oldTournamentId, oldScenarioName]) => {
  if (props.show && isTournamentScenario.value && (newTournamentId !== oldTournamentId || newScenarioName !== oldScenarioName)) {
    resetData()
    await loadAllData()
  }
})

// Load scenario info (from /info endpoint or tournament API)
async function loadScenarioInfo() {
  // Need either scenarioId or tournament params
  if (!scenarioId.value && !isTournamentScenario.value) return
  
  loadingInfo.value = true
  try {
    let response
    if (isTournamentScenario.value) {
      // Use tournament-specific API
      response = await fetch(`/api/tournament/saved/${props.tournamentId}/scenario/${props.scenarioName}`)
    } else {
      // Use regular scenario API
      response = await fetch(`/api/scenarios/${scenarioId.value}/info`)
    }
    
    if (response.ok) {
      const data = await response.json()
      // Tournament API returns different structure - normalize it
      if (isTournamentScenario.value) {
        scenarioInfo.value = {
          name: data.name || props.scenarioName,
          n_issues: data.n_issues || data.issue_names?.length || 0,
          n_outcomes: data.n_outcomes,
          n_negotiators: data.n_negotiators || 2,
          issue_names: data.issue_names || [],
          issues: data.issues || [],
          opposition: data.opposition,
          rational_fraction: data.rational_fraction,
          has_stats: !!data.stats,
          has_info: !!(data.n_outcomes || data.opposition),
          stats: data.stats,
          outcome_space_data: data.outcome_space_data,
          ufuns: data.ufuns,
        }
        // Also set stats if available in the response
        if (data.stats) {
          scenarioStats.value = data.stats
        }
      } else {
        scenarioInfo.value = data
      }
    } else {
      const errorText = await response.text()
      console.error('[StatsModal] Failed to load scenario info:', response.status, errorText)
      loadError.value = `Failed to load scenario info: ${response.status}`
    }
  } catch (err) {
    console.error('[StatsModal] Failed to load scenario info:', err)
    loadError.value = `Failed to load scenario info: ${err.message}`
  } finally {
    loadingInfo.value = false
  }
}

// Load scenario stats from backend
async function loadScenarioStats() {
  // For tournament scenarios, stats are loaded with info - skip separate call
  if (isTournamentScenario.value) return
  if (!scenarioId.value) return
  
  loadingStats.value = true
  try {
    const response = await fetch(`/api/scenarios/${scenarioId.value}/stats`)
    if (response.ok) {
      scenarioStats.value = await response.json()
    }
    // Don't set error for stats - they might not exist
  } catch (err) {
    console.error('[StatsModal] Failed to load scenario stats:', err)
  } finally {
    loadingStats.value = false
  }
}

// Load ufun details from backend (includes ufun names, types, string representations)
async function loadUfunDetails() {
  // For tournament scenarios, ufuns come with the scenario info
  if (isTournamentScenario.value) {
    // Ufuns are already loaded with scenario info
    if (scenarioInfo.value?.ufuns) {
      ufunDetails.value = scenarioInfo.value.ufuns
    }
    return
  }
  if (!scenarioId.value) return
  
  loadingUfuns.value = true
  try {
    const response = await fetch(`/api/scenarios/${scenarioId.value}/ufuns`)
    if (response.ok) {
      const data = await response.json()
      if (data.success && data.ufuns) {
        ufunDetails.value = data.ufuns
      }
    }
  } catch (err) {
    console.error('[StatsModal] Failed to load ufun details:', err)
  } finally {
    loadingUfuns.value = false
  }
}

// Calculate scenario stats (user action)
async function calculateStats() {
  // Not supported for tournament scenarios yet
  if (isTournamentScenario.value) return
  if (!scenarioId.value) return
  
  if (!confirm('This will calculate scenario statistics. For large outcome spaces, this may take some time. Continue?')) {
    return
  }
  
  calculatingStats.value = true
  try {
    const response = await fetch(`/api/scenarios/${scenarioId.value}/stats/calculate`, {
      method: 'POST'
    })
    if (response.ok) {
      scenarioStats.value = await response.json()
      // Reload info to get updated has_stats
      await loadScenarioInfo()
    }
  } catch (err) {
    console.error('[StatsModal] Failed to calculate scenario stats:', err)
    alert('Failed to calculate stats: ' + err.message)
  } finally {
    calculatingStats.value = false
  }
}

// Toggle panel visibility
function togglePanel(panel) {
  panels[panel] = !panels[panel]
}

// Use scenario stats if available, otherwise fall back to outcome_space_data
const stats = computed(() => {
  // For tournament scenarios, stats are inside scenarioInfo
  if (isTournamentScenario.value && scenarioInfo.value?.stats) {
    const tournamentStats = scenarioInfo.value.stats
    return {
      total_outcomes: scenarioInfo.value.n_outcomes,
      sampled: false,
      sample_size: null,
      reserved_values: null,
      nash_point: tournamentStats.nash_outcomes?.[0] ? {
        outcome: tournamentStats.nash_outcomes[0],
        utilities: tournamentStats.nash_utils[0],
        welfare: tournamentStats.nash_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      kalai_point: tournamentStats.kalai_outcomes?.[0] ? {
        outcome: tournamentStats.kalai_outcomes[0],
        utilities: tournamentStats.kalai_utils[0],
        welfare: tournamentStats.kalai_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      kalai_smorodinsky_point: tournamentStats.ks_outcomes?.[0] ? {
        outcome: tournamentStats.ks_outcomes[0],
        utilities: tournamentStats.ks_utils[0],
        welfare: tournamentStats.ks_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      max_welfare_point: tournamentStats.max_welfare_outcomes?.[0] ? {
        outcome: tournamentStats.max_welfare_outcomes[0],
        utilities: tournamentStats.max_welfare_utils[0],
        welfare: tournamentStats.max_welfare_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      pareto_utilities: tournamentStats.pareto_utils,
      rational_fraction: tournamentStats.rational_fraction,
      opposition: tournamentStats.opposition,
      utility_ranges: tournamentStats.utility_ranges,
      n_pareto_outcomes: tournamentStats.pareto_outcomes?.length,
      has_stats: true
    }
  }
  
  // If we have full scenario stats, use them
  if (scenarioStats.value?.has_stats) {
    return {
      total_outcomes: scenarioStats.value.n_outcomes,
      sampled: false,
      sample_size: null,
      reserved_values: null,
      nash_point: scenarioStats.value.nash_outcomes?.[0] ? {
        outcome: scenarioStats.value.nash_outcomes[0],
        utilities: scenarioStats.value.nash_utils[0],
        welfare: scenarioStats.value.nash_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      kalai_point: scenarioStats.value.kalai_outcomes?.[0] ? {
        outcome: scenarioStats.value.kalai_outcomes[0],
        utilities: scenarioStats.value.kalai_utils[0],
        welfare: scenarioStats.value.kalai_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      kalai_smorodinsky_point: scenarioStats.value.ks_outcomes?.[0] ? {
        outcome: scenarioStats.value.ks_outcomes[0],
        utilities: scenarioStats.value.ks_utils[0],
        welfare: scenarioStats.value.ks_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      max_welfare_point: scenarioStats.value.max_welfare_outcomes?.[0] ? {
        outcome: scenarioStats.value.max_welfare_outcomes[0],
        utilities: scenarioStats.value.max_welfare_utils[0],
        welfare: scenarioStats.value.max_welfare_utils[0].reduce((a, b) => a + b, 0)
      } : null,
      pareto_utilities: null,
      rational_fraction: scenarioStats.value.rational_fraction,
      opposition: scenarioStats.value.opposition,
      utility_ranges: scenarioStats.value.utility_ranges,
      n_pareto_outcomes: scenarioStats.value.n_pareto_outcomes,
      has_stats: true
    }
  }
  
  // Fall back to outcome_space_data
  return props.negotiation?.outcome_space_data || null
})

const paretoCount = computed(() => {
  // Try n_pareto_outcomes from stats first
  if (stats.value?.n_pareto_outcomes !== undefined && stats.value?.n_pareto_outcomes !== null) {
    return stats.value.n_pareto_outcomes
  }
  
  // Try to get from pareto_utilities array
  if (stats.value?.pareto_utilities?.length) {
    return stats.value.pareto_utilities.length
  }
  
  // Fall back to info.n_pareto if available
  if (stats.value?.info?.n_pareto !== undefined && stats.value.info.n_pareto !== null) {
    return stats.value.info.n_pareto
  }
  
  // No pareto data available
  return null
})

// Format class for scenario format badge
const formatClass = computed(() => {
  const format = scenarioInfo.value?.format_label
  if (format === 'Genius') return 'format-genius'
  if (format === 'NegMAS') return 'format-negmas'
  if (format === 'GeniusWeb') return 'format-geniusweb'
  return ''
})

// Get ufun name by index (prefer ufun name over negotiator name)
function getUfunName(idx) {
  // First try ufun details
  if (ufunDetails.value?.[idx]?.name) {
    return ufunDetails.value[idx].name
  }
  // Fall back to negotiator names from negotiation
  if (props.negotiation?.negotiator_names?.[idx]) {
    return props.negotiation.negotiator_names[idx]
  }
  return `U${idx + 1}`
}

// Format issue type
function formatIssueType(type) {
  if (!type) return '?'
  // Convert class names like "CategoricalIssue" to just "categorical"
  return type.replace(/Issue$/, '').toLowerCase()
}

// Format number with fallback
function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return 'N/A'
  return Number(value).toFixed(decimals)
}

// Format percentage
function formatPercent(value) {
  if (value === null || value === undefined) return 'N/A'
  return `${(value * 100).toFixed(1)}%`
}

function formatOutcome(outcome) {
  if (!outcome) return 'N/A'
  
  // If it's an object, format as key-value pairs
  if (typeof outcome === 'object' && !Array.isArray(outcome)) {
    const entries = Object.entries(outcome)
    if (entries.length === 0) return 'N/A'
    if (entries.length <= 3) {
      return entries.map(([k, v]) => `${k}: ${v}`).join(', ')
    }
    // For many issues, show first 2 and count
    const first = entries.slice(0, 2).map(([k, v]) => `${k}: ${v}`).join(', ')
    return `${first}, ... (${entries.length} issues)`
  }
  
  // If it's an array
  if (Array.isArray(outcome)) {
    if (outcome.length === 0) return 'N/A'
    if (outcome.length <= 5) {
      return outcome.join(', ')
    }
    return `${outcome.slice(0, 3).join(', ')}, ... (${outcome.length} values)`
  }
  
  // Fallback to string
  return String(outcome)
}

function showOutcomeDetail(title, outcome) {
  outcomeModalTitle.value = `${title} Solution - Full Outcome`
  outcomeModalData.value = outcome
  showOutcomeModal.value = true
}

// Show object detail modal (ufun, outcome space, scenario)
function showObjectDetail(type, title, objectType, index = null) {
  if (!scenarioId.value) return
  
  objectDetailTitle.value = title
  objectDetailType.value = objectType
  
  // Build URL based on type
  if (type === 'ufun' && index !== null) {
    objectDetailUrl.value = `/api/scenarios/${scenarioId.value}/ufuns/${index}/serialized`
  } else if (type === 'outcome_space') {
    objectDetailUrl.value = `/api/scenarios/${scenarioId.value}/outcome-space/serialized`
  } else if (type === 'scenario') {
    objectDetailUrl.value = `/api/scenarios/${scenarioId.value}/serialized`
  }
  
  showObjectDetailModal.value = true
}

function truncatePath(path) {
  if (!path) return 'N/A'
  // Show last 2 path segments or the whole path if short
  const parts = path.split('/')
  if (parts.length <= 3) return path
  return '.../' + parts.slice(-2).join('/')
}
</script>

<style scoped>
.modal-xlg {
  max-width: 1600px;
  width: 95vw;
  max-height: 90vh;
}

.modal-sm {
  max-width: 600px;
  width: 90vw;
}

.clickable {
  cursor: pointer;
  transition: color 0.2s;
}

.clickable:hover {
  color: var(--accent-primary);
}

.text-muted {
  color: var(--text-tertiary) !important;
  font-style: italic;
}

.collapse-icon {
  font-size: 10px;
  margin-right: 6px;
  color: var(--text-tertiary);
}

.stats-section.collapsed {
  padding-bottom: 12px;
}

.outcome-detail-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.outcome-detail-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 4px;
  border: 1px solid var(--border-color);
  gap: 16px;
}

.outcome-detail-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.outcome-detail-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
  font-family: 'SF Mono', Monaco, monospace;
}

.modal-header {
  background: var(--bg-secondary);
}

.modal-footer {
  background: var(--bg-secondary);
}

.modal-close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.modal-close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-close-btn svg {
  width: 18px;
  height: 18px;
}

.stats-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px;
}

.stats-grid-4col {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stats-section-full {
  grid-column: 1 / -1;
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.stats-section {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.stats-section.compact {
  padding: 12px;
}

.stats-section-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
  display: flex;
  align-items: center;
}

.stats-section-title.clickable:hover {
  color: var(--accent-primary);
}

.solution-title {
  font-size: 12px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--accent-primary);
}

.solution-concepts-section {
  grid-column: 1 / -1;
}

.stats-rows {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stats-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 4px 0;
  gap: 8px;
}

.stats-row:not(:last-child) {
  border-bottom: 1px solid var(--border-color);
}

.stats-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.stats-value {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
  text-align: right;
  word-break: break-word;
}

.stats-value.monospace {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 10px;
  font-weight: 400;
}

.stats-value.monospace.small {
  font-size: 9px;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-text {
  font-size: 11px;
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
  padding: 8px;
}

/* Format badges */
.format-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.format-genius {
  background: #e3f2fd;
  color: #1565c0;
}

.format-negmas {
  background: #e8f5e9;
  color: #2e7d32;
}

.format-geniusweb {
  background: #fff3e0;
  color: #e65100;
}

/* Status badges */
.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.status-badge.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-badge.warning {
  background: #fff3e0;
  color: #e65100;
}

/* Tag chips */
.tag-chip {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  margin-right: 4px;
  margin-bottom: 4px;
  display: inline-block;
}

/* Issue items */
.issue-item {
  padding: 6px 0;
  border-bottom: 1px solid var(--border-color);
}

.issue-item:last-child {
  border-bottom: none;
}

.issue-header-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}

.issue-name-compact {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
}

.issue-type-badge-small {
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  text-transform: capitalize;
}

.issue-values-compact {
  margin-top: 2px;
}

.issue-values-text,
.issue-range-text {
  font-size: 10px;
  color: var(--text-tertiary);
  font-family: 'SF Mono', Monaco, monospace;
}

/* Utility Functions List */
.ufuns-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ufun-placeholder {
  padding: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.loading-spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-radius: 50%;
  border-top-color: var(--accent-primary);
  animation: spin 1s linear infinite;
  margin-right: 6px;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1200px) {
  .stats-grid-4col {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .stats-grid-4col {
    grid-template-columns: 1fr;
  }
}

/* Ufun item in list */
.ufun-item {
  margin-bottom: 8px;
}

.ufun-item:last-child {
  margin-bottom: 0;
}
</style>
