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
        <div v-if="loadingInfo || loadingStats" class="empty-state" style="padding: 40px;">
          <div class="loading-spinner"></div>
          <p>Loading scenario data...</p>
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
          <!-- Top Section: Basic Info & Metrics (3 columns) -->
          <div class="stats-grid-3col">
            <!-- Basic Information -->
            <div class="stats-section">
              <h4 class="stats-section-title">Basic Information</h4>
              <div v-if="scenarioInfo || props.negotiation?.scenario_path" class="stats-rows">
                <div v-if="props.negotiation?.scenario_path" class="stats-row">
                  <span class="stats-label">Scenario Path:</span>
                  <span class="stats-value monospace small" :title="props.negotiation.scenario_path">{{ truncatePath(props.negotiation.scenario_path) }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Name:</span>
                  <span class="stats-value">{{ scenarioInfo?.name || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Negotiators:</span>
                  <span class="stats-value">{{ scenarioInfo.n_negotiators || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Issues:</span>
                  <span class="stats-value">{{ scenarioInfo.n_issues || 0 }}</span>
                </div>
                <!-- Show issue names and value counts -->
                <div v-if="scenarioInfo?.issues && scenarioInfo.issues.length > 0" style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-color);">
                  <div v-for="(issue, idx) in scenarioInfo.issues" :key="`basic-issue-${idx}`" class="stats-row" style="flex-direction: column; align-items: flex-start; gap: 4px;">
                    <span class="stats-label" style="font-weight: 600;">{{ issue.name }}:</span>
                    <span class="stats-value" style="font-size: 11px; color: var(--text-secondary);">
                      <span v-if="issue.values && issue.values.length > 0">
                        {{ issue.values.slice(0, 3).join(', ') }}<span v-if="issue.values.length > 3"> (+{{ issue.values.length - 3 }} more)</span>
                      </span>
                      <span v-else-if="issue.min_value !== undefined && issue.max_value !== undefined">
                        Range: [{{ issue.min_value }}, {{ issue.max_value }}]
                      </span>
                    </span>
                  </div>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Total Outcomes:</span>
                  <span class="stats-value">{{ scenarioInfo.n_outcomes?.toLocaleString() || stats?.total_outcomes?.toLocaleString() || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Format:</span>
                  <span class="stats-value">{{ scenarioInfo.format?.toUpperCase() || 'N/A' }}</span>
                </div>
                <div class="stats-row">
                  <span class="stats-label">Normalized:</span>
                  <span class="stats-value">{{ scenarioInfo.normalized !== undefined ? (scenarioInfo.normalized ? 'Yes' : 'No') : 'N/A' }}</span>
                </div>
              </div>
            </div>
            
            <!-- Scenario Metrics -->
            <div class="stats-section">
              <h4 class="stats-section-title">Scenario Metrics</h4>
              <div class="stats-rows">
                <div v-if="scenarioInfo?.opposition !== undefined && scenarioInfo?.opposition !== null" class="stats-row">
                  <span class="stats-label">Opposition Level:</span>
                  <span class="stats-value">{{ scenarioInfo.opposition.toFixed(4) }}</span>
                </div>
                <div v-else-if="stats?.opposition !== undefined && stats?.opposition !== null" class="stats-row">
                  <span class="stats-label">Opposition Level:</span>
                  <span class="stats-value">{{ stats.opposition.toFixed(4) }}</span>
                </div>
                <div v-if="stats?.rational_fraction !== undefined && stats?.rational_fraction !== null" class="stats-row">
                  <span class="stats-label">Rational Fraction:</span>
                  <span class="stats-value">{{ (stats.rational_fraction * 100).toFixed(1) }}%</span>
                </div>
                <div v-else-if="scenarioInfo?.rational_fraction !== undefined && scenarioInfo?.rational_fraction !== null" class="stats-row">
                  <span class="stats-label">Rational Fraction:</span>
                  <span class="stats-value">{{ (scenarioInfo.rational_fraction * 100).toFixed(1) }}%</span>
                </div>
                <div v-if="paretoCount !== null && paretoCount > 0" class="stats-row">
                  <span class="stats-label">Pareto Outcomes:</span>
                  <span class="stats-value">{{ paretoCount.toLocaleString() }}</span>
                </div>
                <div v-else class="stats-row">
                  <span class="stats-label">Pareto Outcomes:</span>
                  <span class="stats-value text-muted">N/A</span>
                </div>
                <div v-if="stats?.utility_ranges" class="stats-row">
                  <span class="stats-label">Utility Ranges:</span>
                  <span class="stats-value monospace" style="font-size: 11px;">
                    {{ stats.utility_ranges.map(r => `[${r[0].toFixed(2)}, ${r[1].toFixed(2)}]`).join(', ') }}
                  </span>
                </div>
              </div>
            </div>
            
            <!-- Utility Functions -->
            <div class="stats-section">
              <h4 class="stats-section-title">Utility Functions</h4>
              <div v-if="loadingUfuns" class="empty-text">
                <div class="loading-spinner-small"></div>
                Loading utility functions...
              </div>
              <div v-else-if="ufunDetails && ufunDetails.length > 0" class="ufuns-list">
                <div v-for="(ufun, idx) in ufunDetails" :key="`ufun-${idx}`" class="ufun-item-compact">
                  <div class="ufun-header-compact">
                    <span class="ufun-name-compact">{{ ufun.name || `Utility Function ${idx + 1}` }}</span>
                    <span class="ufun-type-badge">{{ ufun.type }}</span>
                  </div>
                  <div class="ufun-details-compact">
                    <span v-if="stats?.reserved_values && stats.reserved_values[idx] !== null && stats.reserved_values[idx] !== undefined" class="ufun-meta-compact">
                      Reserved: {{ stats.reserved_values[idx].toFixed(3) }}
                    </span>
                    <span v-if="stats?.nash_point?.utilities && stats.nash_point.utilities[idx] !== undefined" class="ufun-meta-compact">
                      Nash: {{ stats.nash_point.utilities[idx].toFixed(3) }}
                    </span>
                  </div>
                  <!-- String representation (like in ScenariosView) -->
                  <div v-if="ufun.string_representation" class="ufun-representation">
                    <pre>{{ ufun.string_representation }}</pre>
                  </div>
                </div>
              </div>
              <div v-else-if="negotiatorNames && negotiatorNames.length > 0" class="ufuns-list">
                <div v-for="(name, idx) in negotiatorNames" :key="`ufun-${idx}`" class="ufun-item-compact">
                  <div class="ufun-header-compact">
                    <span class="ufun-name-compact">{{ name || `Negotiator ${idx + 1}` }}</span>
                  </div>
                  <div class="ufun-details-compact">
                    <span v-if="stats?.reserved_values && stats.reserved_values[idx] !== null" class="ufun-meta-compact">
                      Reserved: {{ stats.reserved_values[idx].toFixed(3) }}
                    </span>
                    <span v-if="stats?.nash_point?.utilities && stats.nash_point.utilities[idx] !== undefined" class="ufun-meta-compact">
                      Nash: {{ stats.nash_point.utilities[idx].toFixed(3) }}
                    </span>
                  </div>
                </div>
              </div>
              <div v-else-if="scenarioInfo?.n_negotiators" class="ufuns-list">
                <div v-for="idx in scenarioInfo.n_negotiators" :key="`ufun-${idx}`" class="ufun-item-compact">
                  <div class="ufun-header-compact">
                    <span class="ufun-name-compact">Negotiator {{ idx }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="empty-text">No utility functions</div>
            </div>
          </div>

          <!-- Issues Section -->
          <div v-if="scenarioInfo?.issues && scenarioInfo.issues.length > 0" class="stats-section-full">
            <h4 class="stats-section-title">Issues ({{ scenarioInfo.issues.length }})</h4>
            <div class="issues-grid">
              <div v-for="(issue, idx) in scenarioInfo.issues" :key="`issue-${idx}`" class="issue-card">
                <div class="issue-header">
                  <span class="issue-name">{{ issue.name }}</span>
                  <span class="issue-type-badge">{{ issue.type }}</span>
                </div>
                <div v-if="issue.values && issue.values.length > 0" class="issue-values">
                  <span v-for="(val, vidx) in issue.values.slice(0, 5)" :key="`val-${vidx}`" class="value-chip">
                    {{ val }}
                  </span>
                  <span v-if="issue.values.length > 5" class="value-chip more">
                    +{{ issue.values.length - 5 }} more
                  </span>
                </div>
                <div v-else-if="issue.min_value !== undefined && issue.max_value !== undefined" class="issue-range">
                  Range: [{{ issue.min_value }}, {{ issue.max_value }}]
                </div>
              </div>
            </div>
          </div>

          <!-- Solution Concepts (4 columns) -->
          <div v-if="stats && (stats.nash_point || stats.kalai_point || stats.kalai_smorodinsky_point || stats.max_welfare_point)" class="solution-concepts-section">
            <h4 class="stats-section-title" style="margin-bottom: 16px;">Solution Concepts</h4>
            <div class="stats-grid-4col">
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
                    <span class="stats-label">{{ negotiatorNames[idx] || `U${idx + 1}` }}:</span>
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
                    <span class="stats-label">{{ negotiatorNames[idx] || `U${idx + 1}` }}:</span>
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
                    <span class="stats-label">{{ negotiatorNames[idx] || `U${idx + 1}` }}:</span>
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
                    <span class="stats-label">{{ negotiatorNames[idx] || `U${idx + 1}` }}:</span>
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
          <div v-if="scenarioId && !stats?.has_stats && !calculatingStats" class="stats-section-full">
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
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  negotiation: {
    type: Object,
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

// Outcome detail modal
const showOutcomeModal = ref(false)
const outcomeModalTitle = ref('')
const outcomeModalData = ref(null)

// Compute scenario ID from path
const scenarioId = computed(() => {
  if (!props.negotiation?.scenario_path) return null
  return btoa(props.negotiation.scenario_path)
})

// Load scenario data when modal opens
watch(() => props.show, async (show) => {
  if (show && scenarioId.value) {
    // Load all data in parallel
    const promises = []
    if (!scenarioInfo.value) {
      promises.push(loadScenarioInfo())
    }
    if (!scenarioStats.value) {
      promises.push(loadScenarioStats())
    }
    if (ufunDetails.value.length === 0) {
      promises.push(loadUfunDetails())
    }
    await Promise.all(promises)
  }
})

// Load scenario info (from /info endpoint)
async function loadScenarioInfo() {
  if (!scenarioId.value) return
  
  loadingInfo.value = true
  try {
    const response = await fetch(`/api/scenarios/${scenarioId.value}/info`)
    if (response.ok) {
      scenarioInfo.value = await response.json()
    }
  } catch (err) {
    console.error('[StatsModal] Failed to load scenario info:', err)
  } finally {
    loadingInfo.value = false
  }
}

// Load scenario stats from backend
async function loadScenarioStats() {
  if (!scenarioId.value) return
  
  loadingStats.value = true
  try {
    const response = await fetch(`/api/scenarios/${scenarioId.value}/stats`)
    if (response.ok) {
      scenarioStats.value = await response.json()
    }
  } catch (err) {
    console.error('[StatsModal] Failed to load scenario stats:', err)
  } finally {
    loadingStats.value = false
  }
}

// Load ufun details from backend (includes ufun names, types, string representations)
async function loadUfunDetails() {
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
    }
  } catch (err) {
    console.error('[StatsModal] Failed to calculate scenario stats:', err)
    alert('Failed to calculate stats: ' + err.message)
  } finally {
    calculatingStats.value = false
  }
}

// Use scenario stats if available, otherwise fall back to outcome_space_data
const stats = computed(() => {
  // If we have full scenario stats, use them
  if (scenarioStats.value?.has_stats) {
    return {
      total_outcomes: scenarioStats.value.n_outcomes,
      sampled: false,
      sample_size: null,
      reserved_values: null, // Could extract from scenario stats if needed
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
      pareto_utilities: null, // Not included (too large)
      // Additional stats from scenario
      rational_fraction: scenarioStats.value.rational_fraction,
      opposition: scenarioStats.value.opposition,
      utility_ranges: scenarioStats.value.utility_ranges,
      n_pareto_outcomes: scenarioStats.value.n_pareto_outcomes,
    }
  }
  
  // Fall back to outcome_space_data
  return props.negotiation?.outcome_space_data || null
})

const negotiatorNames = computed(() => {
  return props.negotiation?.negotiator_names || []
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
  text-decoration: underline;
}

.text-muted {
  color: var(--text-tertiary) !important;
  font-style: italic;
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
  gap: 24px;
  padding: 8px;
}

.stats-grid-3col {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
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
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
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
  padding: 6px 0;
  gap: 12px;
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
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-text {
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
  padding: 12px;
}

/* Issues Grid */
.issues-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
  margin-top: 8px;
}

.issue-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 12px;
}

.issue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.issue-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.issue-type-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--accent-primary);
  color: white;
  font-weight: 500;
  text-transform: capitalize;
}

.issue-values {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.value-chip {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.value-chip.more {
  background: var(--bg-secondary);
  color: var(--text-tertiary);
  font-style: italic;
}

.issue-range {
  font-size: 11px;
  color: var(--text-secondary);
  font-family: 'SF Mono', Monaco, monospace;
}

/* Utility Functions Compact List */
.ufuns-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ufun-item-compact {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 8px 10px;
}

.ufun-header-compact {
  margin-bottom: 4px;
}

.ufun-name-compact {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.ufun-details-compact {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.ufun-meta-compact {
  font-size: 10px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid var(--border-color);
}

.ufun-type-badge {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--accent-primary);
  color: white;
  font-weight: 500;
  margin-left: 8px;
}

.ufun-representation {
  margin-top: 6px;
  padding: 6px 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.ufun-representation pre {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 10px;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
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

@media (max-width: 900px) {
  .stats-grid-3col {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .stats-grid-3col,
  .stats-grid-4col {
    grid-template-columns: 1fr;
  }
}
</style>
