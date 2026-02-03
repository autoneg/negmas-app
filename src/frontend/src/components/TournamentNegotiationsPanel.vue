<template>
  <div class="tournament-negotiations-panel">
    <div class="panel-header">
      <div class="panel-title">
        <span>Negotiations</span>
        <span v-if="totalCount > 0" class="badge">{{ totalCount }}</span>
      </div>
      
      <div class="panel-header-actions">
        <!-- Filter dropdown -->
        <select v-model="filter" class="filter-select" title="Filter negotiations">
          <option value="all">All</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="agreement">Agreements</option>
          <option value="timeout">Timeouts</option>
          <option value="error">Errors</option>
        </select>
        
        <!-- Auto-scroll toggle -->
        <button 
          class="btn-icon-sm" 
          @click="autoscroll = !autoscroll"
          :title="autoscroll ? 'Disable auto-scroll' : 'Enable auto-scroll'"
        >
          <svg v-if="autoscroll" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="18 15 12 9 6 15"></polyline>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <polyline points="19 12 12 19 5 12"></polyline>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="panel-body" ref="listContainer">
      <!-- Empty state -->
      <div v-if="filteredNegotiations.length === 0 && runningList.length === 0" class="empty-state-sm">
        <p class="text-muted">{{ totalCount === 0 ? 'No negotiations yet' : 'No matching negotiations' }}</p>
      </div>
      
      <!-- Negotiations list -->
      <div v-else class="negotiations-list">
        <!-- Running negotiations (always at top) -->
        <div 
          v-for="neg in runningList" 
          :key="'running-' + neg.run_id"
          class="negotiation-item running"
          @click="handleClick(neg, true)"
        >
          <div class="neg-status">
            <span class="status-indicator running"></span>
          </div>
          <div class="neg-info">
            <div class="neg-row-top">
              <div class="neg-partners">
                <span class="competitor" :title="neg.competitor">{{ neg.competitor || 'Unknown' }}</span>
                <span class="vs">vs</span>
                <span class="opponent" :title="neg.opponent">{{ neg.opponent || 'Unknown' }}</span>
              </div>
              <div class="neg-progress-inline">
                <span v-if="neg.relative_time !== undefined" class="time">{{ (neg.relative_time * 100).toFixed(0) }}%</span>
                <span v-if="neg.step !== undefined" class="step">Step {{ neg.step }}</span>
              </div>
            </div>
            <div class="neg-row-bottom">
              <span v-if="neg.scenario" class="scenario" :title="neg.scenario">{{ neg.scenario }}</span>
            </div>
          </div>
        </div>
        
        <!-- Completed negotiations -->
        <div 
          v-for="neg in filteredNegotiations" 
          :key="'completed-' + (neg.run_id || neg.index)"
          class="negotiation-item"
          :class="getStatusClass(neg)"
          @click="handleClick(neg, false)"
        >
          <div class="neg-status">
            <span class="status-indicator" :class="getStatusClass(neg)"></span>
          </div>
          <div class="neg-info">
            <div class="neg-row-top">
              <div class="neg-partners">
                <span class="competitor" :title="neg.competitor || neg.partners?.[0]">{{ neg.competitor || neg.partners?.[0] || 'Unknown' }}</span>
                <span class="vs">vs</span>
                <span class="opponent" :title="neg.opponent || neg.partners?.[1]">{{ neg.opponent || neg.partners?.[1] || 'Unknown' }}</span>
              </div>
              <div class="neg-result-inline">
                <span v-if="getEndReason(neg) === 'agreement'" class="result-text agreement">Agreement</span>
                <span v-else-if="getEndReason(neg) === 'timeout'" class="result-text timeout">Timeout</span>
                <span v-else-if="getEndReason(neg) === 'ended'" class="result-text ended">Ended</span>
                <span v-else-if="getEndReason(neg) === 'cancelled'" class="result-text cancelled">Cancelled</span>
                <span v-else-if="getEndReason(neg) === 'error' || getEndReason(neg) === 'broken'" class="result-text error">Error</span>
              </div>
            </div>
            <div class="neg-row-bottom">
              <span v-if="neg.run_id != null" class="run-id" :title="'Run ID: ' + neg.run_id">
                {{ formatRunId(neg.run_id) }}
              </span>
              <span v-if="neg.scenario_path || neg.scenario" class="scenario" :title="neg.scenario_path || neg.scenario">
                {{ neg.scenario_path || neg.scenario }}
              </span>
              <span v-if="neg.utilities" class="utilities" :title="'Utilities: ' + formatUtilitiesShort(neg.utilities)">
                {{ formatUtilitiesShort(neg.utilities) }}
              </span>
              <span v-if="neg.n_steps" class="step">{{ neg.n_steps }}s</span>
              <button 
                v-if="neg.run_id"
                class="btn-icon-xs"
                @click.stop="openNegotiationFolder(neg)"
                title="Open negotiation folder"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Negotiation Detail Modal -->
  <Teleport to="body">
    <div v-if="showModal" class="modal-overlay active" @click.self="closeModal">
      <div class="modal-content modal-xlg">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ selectedNegotiation?.partners?.[0] || selectedNegotiation?.competitor || 'Unknown' }} 
            vs 
            {{ selectedNegotiation?.partners?.[1] || selectedNegotiation?.opponent || 'Unknown' }}
            <span v-if="getModalScenario()" class="modal-subtitle">
              - {{ truncateScenario(getModalScenario(), 40) }}
            </span>
          </h3>
          <div class="modal-header-actions">
            <button 
              class="btn btn-sm btn-secondary" 
              @click="openFullView"
              title="Open in full view"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                <polyline points="15 3 21 3 21 9"></polyline>
                <line x1="10" y1="14" x2="21" y2="3"></line>
              </svg>
              Full View
            </button>
            <button class="modal-close-btn" @click="closeModal" title="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>
        
        <div class="modal-body negotiation-modal-body">
          <div v-if="loadingNegotiation" class="loading-state">
            <div class="spinner"></div>
            <p>Loading negotiation data...</p>
          </div>
          
          <div v-else-if="negotiationError" class="error-state">
            <p>{{ negotiationError }}</p>
            <button class="btn btn-secondary" @click="closeModal">Close</button>
          </div>
          
          <div v-else-if="negotiationData" class="negotiation-content">
            <!-- Info bar -->
            <div class="info-bar">
              <div class="info-item">
                <span class="info-label">Status:</span>
                <span class="result-badge" :class="getStatusClass(selectedNegotiation)">
                  {{ selectedNegotiation?.end_reason || (selectedIsRunning ? 'Running' : 'Unknown') }}
                </span>
              </div>
              <div v-if="negotiationData.n_steps" class="info-item">
                <span class="info-label">Steps:</span>
                <span class="info-value">{{ negotiationData.n_steps }}</span>
              </div>
              <div v-if="negotiationData.utilities" class="info-item">
                <span class="info-label">Utilities:</span>
                <span class="info-value">
                  {{ formatUtilities(negotiationData.utilities) }}
                </span>
              </div>
              <div v-if="negotiationData.agreement" class="info-item">
                <span class="info-label">Agreement:</span>
                <span class="info-value monospace">{{ formatAgreement(negotiationData.agreement) }}</span>
              </div>
            </div>
            
            <!-- Panels container -->
            <div class="panels-row">
              <!-- Offer History Panel (abbreviated) -->
              <div class="panel offer-history-panel">
                <div class="inner-panel-header">
                  <span>Offer History</span>
                  <span class="badge-sm">{{ negotiationData.offers?.length || 0 }} offers</span>
                </div>
                <div class="panel-content">
                  <div v-if="!negotiationData.offers || negotiationData.offers.length === 0" class="empty-state-sm">
                    <p>No offers recorded</p>
                  </div>
                  <div v-else class="offers-list">
                    <!-- First few offers -->
                    <div 
                      v-for="(offer, idx) in firstOffers" 
                      :key="'first-' + idx"
                      class="offer-item"
                    >
                      <span class="offer-step">{{ offer.step ?? offer.originalIdx }}</span>
                      <span class="offer-proposer" :class="getProposerClass(offer, offer.originalIdx)">
                        {{ getProposerName(offer, offer.originalIdx) }}
                      </span>
                      <span class="offer-value monospace">{{ formatOffer(offer) }}</span>
                      <span v-if="offer.utilities" class="offer-utils">
                        {{ formatOfferUtilities(offer.utilities) }}
                      </span>
                    </div>
                    <!-- Ellipsis separator if there are hidden offers -->
                    <div v-if="hasHiddenOffers" class="offer-ellipsis">
                      <span>... {{ hiddenOffersCount }} more offers ...</span>
                    </div>
                    <!-- Last few offers -->
                    <div 
                      v-for="(offer, idx) in lastOffers" 
                      :key="'last-' + idx"
                      class="offer-item"
                      :class="{ 'is-agreement': idx === lastOffers.length - 1 && selectedNegotiation?.end_reason === 'agreement' }"
                    >
                      <span class="offer-step">{{ offer.step ?? offer.originalIdx }}</span>
                      <span class="offer-proposer" :class="getProposerClass(offer, offer.originalIdx)">
                        {{ getProposerName(offer, offer.originalIdx) }}
                      </span>
                      <span class="offer-value monospace">{{ formatOffer(offer) }}</span>
                      <span v-if="offer.utilities" class="offer-utils">
                        {{ formatOfferUtilities(offer.utilities) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Outcome Stats Panel -->
              <div v-if="negotiationData.agreement_stats" class="panel stats-panel">
                <div class="inner-panel-header">
                  <span>Outcome Quality</span>
                </div>
                <div class="panel-content">
                  <div class="stats-grid">
                    <div class="stat-item">
                      <span class="stat-label">Pareto Optimality</span>
                      <span class="stat-value" :class="getOptimalityClass(negotiationData.agreement_stats.pareto_optimality)">
                        {{ formatOptimality(negotiationData.agreement_stats.pareto_optimality) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">Nash Optimality</span>
                      <span class="stat-value" :class="getOptimalityClass(negotiationData.agreement_stats.nash_optimality)">
                        {{ formatOptimality(negotiationData.agreement_stats.nash_optimality) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">Kalai Optimality</span>
                      <span class="stat-value" :class="getOptimalityClass(negotiationData.agreement_stats.kalai_optimality)">
                        {{ formatOptimality(negotiationData.agreement_stats.kalai_optimality) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">Max Welfare</span>
                      <span class="stat-value" :class="getOptimalityClass(negotiationData.agreement_stats.max_welfare_optimality)">
                        {{ formatOptimality(negotiationData.agreement_stats.max_welfare_optimality) }}
                      </span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-label">KS Optimality</span>
                      <span class="stat-value" :class="getOptimalityClass(negotiationData.agreement_stats.ks_optimality)">
                        {{ formatOptimality(negotiationData.agreement_stats.ks_optimality) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Chart from 'chart.js/auto'

const props = defineProps({
  tournamentId: {
    type: String,
    required: true
  },
  liveNegotiations: {
    type: Array,
    default: () => []
  },
  runningNegotiations: {
    type: Object,
    default: () => ({})
  },
  gridInit: {
    type: Object,
    default: null
  },
  status: {
    type: String,
    default: 'running'
  }
})

const emit = defineEmits(['viewNegotiation'])

const router = useRouter()

// State
const filter = ref('all')
const autoscroll = ref(true)
const listContainer = ref(null)
const showModal = ref(false)
const selectedNegotiation = ref(null)
const selectedIsRunning = ref(false)
const loadingNegotiation = ref(false)
const negotiationError = ref(null)
const negotiationData = ref(null)
const chartCanvas = ref(null)
let chartInstance = null

// Transform running negotiations map to array with competitor/opponent info
const runningList = computed(() => {
  if (!props.runningNegotiations) return []
  
  const list = []
  const runningMap = props.runningNegotiations instanceof Map 
    ? Object.fromEntries(props.runningNegotiations) 
    : props.runningNegotiations
    
  for (const [runId, neg] of Object.entries(runningMap)) {
    if (neg && neg.status === 'running') {
      list.push({
        run_id: runId,
        competitor: neg.competitor || 'Unknown',
        opponent: neg.opponent || 'Unknown',
        scenario: neg.scenario || '',
        step: neg.step,
        relative_time: neg.relative_time,
        current_offer: neg.current_offer,
        current_proposer: neg.current_proposer
      })
    }
  }
  return list
})

// Filter completed negotiations
const filteredNegotiations = computed(() => {
  let negs = props.liveNegotiations || []
  
  if (filter.value === 'running') {
    return [] // Running shown separately
  } else if (filter.value === 'completed') {
    negs = negs.filter(n => {
      const reason = getEndReason(n)
      return reason && reason !== 'error' && reason !== 'broken'
    })
  } else if (filter.value === 'agreement') {
    negs = negs.filter(n => getEndReason(n) === 'agreement' || n.has_agreement)
  } else if (filter.value === 'timeout') {
    negs = negs.filter(n => getEndReason(n) === 'timeout')
  } else if (filter.value === 'error') {
    negs = negs.filter(n => {
      const reason = getEndReason(n)
      return reason === 'error' || reason === 'broken' || n.has_error
    })
  }
  
  // Return in reverse order (newest first)
  return [...negs].reverse()
})

// Total count
const totalCount = computed(() => {
  return runningList.value.length + (props.liveNegotiations?.length || 0)
})

// Abbreviated offer lists for modal (first 3 and last 3)
const OFFERS_TO_SHOW = 3

const firstOffers = computed(() => {
  const offers = negotiationData.value?.offers || []
  if (offers.length <= OFFERS_TO_SHOW * 2) {
    // Show all if 6 or fewer
    return offers.map((o, i) => ({ ...o, originalIdx: i }))
  }
  return offers.slice(0, OFFERS_TO_SHOW).map((o, i) => ({ ...o, originalIdx: i }))
})

const lastOffers = computed(() => {
  const offers = negotiationData.value?.offers || []
  if (offers.length <= OFFERS_TO_SHOW * 2) {
    return [] // All shown in firstOffers
  }
  const startIdx = offers.length - OFFERS_TO_SHOW
  return offers.slice(startIdx).map((o, i) => ({ ...o, originalIdx: startIdx + i }))
})

const hasHiddenOffers = computed(() => {
  const offers = negotiationData.value?.offers || []
  return offers.length > OFFERS_TO_SHOW * 2
})

const hiddenOffersCount = computed(() => {
  const offers = negotiationData.value?.offers || []
  return Math.max(0, offers.length - OFFERS_TO_SHOW * 2)
})

// Can show 2D chart
const canShowChart = computed(() => {
  return negotiationData.value?.offers?.length > 0 && 
         negotiationData.value?.offers[0]?.utilities?.length === 2
})

// Auto-scroll when new negotiations arrive
watch(() => props.liveNegotiations?.length, async () => {
  if (autoscroll.value && listContainer.value) {
    await nextTick()
    listContainer.value.scrollTop = 0 // Scroll to top since newest are first
  }
})

// Update chart when modal data changes
watch(() => negotiationData.value, () => {
  if (showModal.value && canShowChart.value) {
    nextTick(() => updateChart())
  }
}, { deep: true })

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})

// Helper to get end reason from negotiation (handles both old and new format)
function getEndReason(neg) {
  if (!neg) return ''
  // New format uses 'result', old format uses 'end_reason'
  return neg.result || neg.end_reason || ''
}

function getStatusClass(neg) {
  if (!neg) return ''
  const reason = getEndReason(neg)
  if (reason === 'agreement' || neg.has_agreement) return 'agreement'
  if (reason === 'timeout') return 'timeout'
  if (reason === 'error' || reason === 'broken' || neg.has_error) return 'error'
  return 'completed'
}

function truncateScenario(path, maxLen = 20) {
  if (!path) return ''
  // Extract just the scenario name from path
  const parts = path.split(/[/\\]/)
  const name = parts[parts.length - 1] || path
  if (name.length <= maxLen) return name
  return name.slice(0, maxLen - 3) + '...'
}

function formatUtilitiesShort(utils) {
  if (!utils) return ''
  if (Array.isArray(utils)) {
    return utils.map(u => u?.toFixed(2) ?? '?').join(', ')
  }
  if (typeof utils === 'object') {
    return Object.values(utils).map(u => u?.toFixed(2) ?? '?').join(', ')
  }
  return String(utils)
}

function formatRunId(runId) {
  // Handle run_id which may be a string, number (including negative), or null/undefined
  if (runId == null) return ''
  const str = String(runId)
  // For numeric run_ids (like -1544328854951236011), show first 8 chars
  if (str.length > 10) {
    return str.substring(0, 10) + '...'
  }
  return str
}

function getModalScenario() {
  return selectedNegotiation.value?.scenario_path || 
         selectedNegotiation.value?.scenario || 
         negotiationData.value?.scenario
}

async function handleClick(neg, isRunning) {
  selectedNegotiation.value = neg
  selectedIsRunning.value = isRunning
  showModal.value = true
  loadingNegotiation.value = true
  negotiationError.value = null
  negotiationData.value = null
  
  try {
    if (isRunning) {
      // For running negotiations, we have limited data
      negotiationData.value = {
        partners: [neg.competitor, neg.opponent],
        scenario: neg.scenario,
        n_steps: neg.step,
        offers: neg.current_offer ? [{ offer: neg.current_offer, proposer: neg.current_proposer, step: neg.step }] : [],
        isRunning: true
      }
    } else {
      // For completed negotiations, load full data if available
      if (neg.offers && neg.offers.length > 0) {
        // Already have data from live stream
        negotiationData.value = {
          partners: neg.partners,
          scenario: neg.scenario_path || neg.scenario,
          n_steps: neg.n_steps,
          offers: neg.offers,
          agreement: neg.agreement,
          utilities: neg.utilities,
          issue_names: neg.issue_names
        }
      } else {
        // Need to load from server - prefer run_id if available
        let response
        if (neg.run_id) {
          // Use run_id endpoint (more reliable)
          response = await fetch(`/api/tournament/saved/${props.tournamentId}/negotiation/by-run-id/${neg.run_id}`)
        } else {
          // Fallback to index-based endpoint (for backwards compatibility)
          response = await fetch(`/api/tournament/saved/${props.tournamentId}/negotiation/${neg.index}`)
        }
        if (!response.ok) {
          throw new Error(`Failed to load negotiation: ${response.statusText}`)
        }
        const data = await response.json()
        negotiationData.value = {
          partners: data.partners || neg.partners,
          scenario: data.scenario_path || data.scenario || neg.scenario,
          n_steps: data.n_steps || data.history?.length,
          offers: data.history || data.offers || [],
          agreement: data.agreement,
          utilities: data.final_utilities || data.utilities,
          issue_names: data.issue_names,
          outcome_space_data: data.outcome_space_data,
          agreement_stats: data.agreement_stats
        }
      }
    }
  } catch (error) {
    console.error('Failed to load negotiation:', error)
    negotiationError.value = error.message || 'Failed to load negotiation data'
  } finally {
    loadingNegotiation.value = false
  }
}

function closeModal() {
  showModal.value = false
  selectedNegotiation.value = null
  negotiationData.value = null
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
}

function openFullView() {
  // Save the negotiation data before closing the modal
  const neg = selectedNegotiation.value
  
  closeModal()
  
  // Navigate to SingleNegotiationView with tournament context
  // Prefer run_id over index for more reliable loading
  if (neg) {
    const identifier = neg.run_id 
      ? `tournament:${props.tournamentId}:run:${neg.run_id}`
      : `tournament:${props.tournamentId}:${neg.index ?? 0}`
    router.push({
      name: 'SingleNegotiation',
      params: { id: identifier }
    })
  }
}

async function openNegotiationFolder(neg) {
  if (!neg.run_id) {
    console.warn('No run_id available for this negotiation')
    return
  }
  
  try {
    // First get the path from the API
    const pathResponse = await fetch(`/api/tournament/saved/${props.tournamentId}/negotiation/by-run-id/${neg.run_id}/path`)
    if (!pathResponse.ok) {
      throw new Error('Failed to get negotiation path')
    }
    const { path } = await pathResponse.json()
    
    // Then open it in the system viewer
    const openResponse = await fetch('/api/system/open-path', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    if (!openResponse.ok) {
      throw new Error('Failed to open folder')
    }
  } catch (error) {
    console.error('Failed to open negotiation folder:', error)
    alert('Failed to open negotiation folder: ' + error.message)
  }
}

function formatUtilities(utils) {
  if (!utils) return 'N/A'
  if (Array.isArray(utils)) {
    return utils.map(u => u?.toFixed(3) ?? 'N/A').join(', ')
  }
  if (typeof utils === 'object') {
    return Object.values(utils).map(u => u?.toFixed(3) ?? 'N/A').join(', ')
  }
  return String(utils)
}

function formatAgreement(agreement) {
  if (!agreement) return 'None'
  if (Array.isArray(agreement)) {
    return `(${agreement.join(', ')})`
  }
  return String(agreement)
}

function formatOffer(offer) {
  if (!offer) return 'None'
  const offerValue = offer.offer || offer.current_offer || offer
  if (Array.isArray(offerValue)) {
    return `(${offerValue.join(', ')})`
  }
  if (typeof offerValue === 'object') {
    return `(${Object.values(offerValue).join(', ')})`
  }
  return String(offerValue)
}

function formatOfferUtilities(utils) {
  if (!utils || !Array.isArray(utils)) return ''
  return `[${utils.map(u => u?.toFixed(2) ?? '?').join(', ')}]`
}

function getProposerName(offer, idx) {
  const proposer = offer.proposer ?? offer.negotiator ?? offer.current_proposer
  if (proposer !== undefined && proposer !== null) {
    // If it's an index, try to get the name
    if (typeof proposer === 'number' && negotiationData.value?.partners) {
      return negotiationData.value.partners[proposer] || `Agent ${proposer}`
    }
    return String(proposer)
  }
  // Alternate between partners based on step
  if (negotiationData.value?.partners) {
    return negotiationData.value.partners[idx % 2] || `Agent ${idx % 2}`
  }
  return `Agent ${idx % 2}`
}

function getProposerClass(offer, idx) {
  const proposer = offer.proposer ?? offer.negotiator ?? offer.current_proposer
  let proposerIdx = 0
  if (typeof proposer === 'number') {
    proposerIdx = proposer
  } else if (proposer && negotiationData.value?.partners) {
    proposerIdx = negotiationData.value.partners.indexOf(proposer)
    if (proposerIdx < 0) proposerIdx = idx % 2
  } else {
    proposerIdx = idx % 2
  }
  return `proposer-${proposerIdx}`
}

function formatOptimality(value) {
  if (value === null || value === undefined) return 'N/A'
  return (value * 100).toFixed(1) + '%'
}

function getOptimalityClass(value) {
  if (value === null || value === undefined) return ''
  if (value >= 0.95) return 'optimality-excellent'
  if (value >= 0.8) return 'optimality-good'
  if (value >= 0.5) return 'optimality-fair'
  return 'optimality-poor'
}

function updateChart() {
  if (!chartCanvas.value || !negotiationData.value?.offers) return
  
  const ctx = chartCanvas.value.getContext('2d')
  
  // Extract utilities from offers
  const points = negotiationData.value.offers
    .filter(o => o.utilities && o.utilities.length >= 2)
    .map((o, idx) => ({
      x: o.utilities[0],
      y: o.utilities[1],
      step: o.step ?? idx
    }))
  
  if (points.length === 0) return
  
  // Create datasets
  const datasets = [
    {
      label: 'Offer Trajectory',
      data: points,
      borderColor: '#3b82f6',
      backgroundColor: '#3b82f620',
      pointBackgroundColor: points.map((_, i) => 
        i === points.length - 1 && selectedNegotiation.value?.end_reason === 'agreement' 
          ? '#10b981' 
          : '#3b82f6'
      ),
      pointRadius: points.map((_, i) => i === points.length - 1 ? 8 : 4),
      showLine: true,
      tension: 0.1
    }
  ]
  
  // Add outcome space points if available
  if (negotiationData.value.outcome_space_data?.outcome_utilities) {
    datasets.unshift({
      label: 'Outcome Space',
      data: negotiationData.value.outcome_space_data.outcome_utilities.map(u => ({ x: u[0], y: u[1] })),
      borderColor: 'transparent',
      backgroundColor: 'rgba(156, 163, 175, 0.3)',
      pointRadius: 2,
      showLine: false
    })
  }
  
  if (chartInstance) {
    chartInstance.data.datasets = datasets
    chartInstance.update('none')
  } else {
    chartInstance = new Chart(ctx, {
      type: 'scatter',
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => `Step ${item.raw.step ?? item.dataIndex}: (${item.parsed.x?.toFixed(3)}, ${item.parsed.y?.toFixed(3)})`
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: negotiationData.value.partners?.[0] || 'Agent 0' },
            min: 0,
            max: 1,
            grid: { color: 'rgba(255,255,255,0.1)' }
          },
          y: {
            title: { display: true, text: negotiationData.value.partners?.[1] || 'Agent 1' },
            min: 0,
            max: 1,
            grid: { color: 'rgba(255,255,255,0.1)' }
          }
        }
      }
    })
  }
}
</script>

<style scoped>
.tournament-negotiations-panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  gap: 12px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.badge {
  background: var(--primary-color);
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.badge-sm {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-select {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
}

.btn-icon-sm {
  padding: 4px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon-sm:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.panel-body {
  flex: 1;
  min-height: 0; /* Required for flex children to shrink below content size */
  overflow-y: auto;
  padding: 6px;
}

.empty-state-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 80px;
  color: var(--text-muted);
  font-size: 13px;
}

.negotiations-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.negotiation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 5px;
  background: var(--bg-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.negotiation-item:hover {
  background: var(--bg-tertiary);
}

.negotiation-item.running {
  border-left: 3px solid var(--primary-color);
  background: rgba(59, 130, 246, 0.1);
}

.negotiation-item.agreement {
  border-left: 3px solid var(--success-color, #10b981);
}

.negotiation-item.timeout {
  border-left: 3px solid var(--warning-color, #f59e0b);
}

.negotiation-item.error {
  border-left: 3px solid var(--error-color, #ef4444);
}

.neg-status {
  flex-shrink: 0;
}

.status-indicator {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-indicator.running {
  background: var(--primary-color);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-indicator.agreement {
  background: var(--success-color, #10b981);
}

.status-indicator.timeout {
  background: var(--warning-color, #f59e0b);
}

.status-indicator.error {
  background: var(--error-color, #ef4444);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.neg-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.neg-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.neg-row-bottom {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  color: var(--text-muted);
}

.neg-partners {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  min-width: 0;
  flex: 1;
}

.competitor {
  color: var(--primary-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vs {
  color: var(--text-muted);
  font-size: 9px;
  flex-shrink: 0;
}

.opponent {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.neg-result-inline {
  flex-shrink: 0;
}

.result-text {
  font-size: 10px;
  font-weight: 500;
}

.result-text.agreement {
  color: var(--success-color, #10b981);
}

.result-text.timeout {
  color: var(--warning-color, #f59e0b);
}

.result-text.ended {
  color: var(--text-secondary);
}

.result-text.cancelled {
  color: var(--text-muted);
}

.result-text.error {
  color: var(--error-color, #ef4444);
}

.neg-details {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 1px;
  font-size: 10px;
  color: var(--text-muted);
}

.scenario {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.run-id {
  font-family: monospace;
  font-size: 9px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 1px 4px;
  border-radius: 2px;
  flex-shrink: 0;
}

.btn-icon-xs {
  padding: 2px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}

.btn-icon-xs:hover {
  background: var(--bg-tertiary);
  color: var(--primary-color);
}

.utilities {
  color: var(--text-secondary);
  font-family: monospace;
  font-size: 10px;
  flex-shrink: 0;
}

.meta {
  padding: 1px 3px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  font-size: 9px;
}

.meta.rotated {
  background: rgba(139, 92, 246, 0.2);
  color: #8b5cf6;
}

.step {
  color: var(--text-secondary);
  font-size: 10px;
}

.neg-progress-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.neg-progress, .neg-result {
  flex-shrink: 0;
}

.time {
  font-size: 10px;
  color: var(--primary-color);
  font-weight: 500;
}

.result-badge {
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
}

.result-badge.agreement {
  background: rgba(16, 185, 129, 0.2);
  color: var(--success-color, #10b981);
}

.result-badge.timeout {
  background: rgba(245, 158, 11, 0.2);
  color: var(--warning-color, #f59e0b);
}

.result-badge.error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--error-color, #ef4444);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s;
}

.modal-overlay.active {
  opacity: 1;
  visibility: visible;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-xlg {
  width: 90%;
  max-width: 1000px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.modal-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-subtitle {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-close-btn {
  padding: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
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

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.negotiation-modal-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 350px;
}

.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  gap: 16px;
  color: var(--text-secondary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.info-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.info-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.info-value {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
}

.monospace {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
}

.panels-row {
  display: flex;
  gap: 14px;
  flex: 1;
  min-height: 0;
}

.panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.offer-history-panel {
  max-width: 50%;
}

.utility-chart-panel {
  min-width: 280px;
}

.inner-panel-header {
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.chart-container {
  height: 280px;
  padding: 10px;
}

.offers-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.offer-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  border-radius: 3px;
  background: var(--bg-primary);
  font-size: 11px;
}

.offer-item.is-agreement {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.offer-step {
  width: 26px;
  color: var(--text-muted);
  font-size: 10px;
}

.offer-proposer {
  min-width: 70px;
  font-weight: 500;
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.offer-proposer.proposer-0 {
  color: var(--primary-color);
}

.offer-proposer.proposer-1 {
  color: #10b981;
}

.offer-value {
  flex: 1;
  color: var(--text-primary);
  font-size: 10px;
}

.offer-utils {
  color: var(--text-secondary);
  font-size: 9px;
}

/* Button styles */
.btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.btn:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.btn-secondary {
  background: var(--bg-secondary);
}

/* Offer ellipsis separator */
.offer-ellipsis {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  color: var(--text-muted);
  font-size: 10px;
  font-style: italic;
}

/* Stats panel styles */
.stats-panel {
  min-width: 200px;
  max-width: 280px;
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: var(--bg-primary);
  border-radius: 4px;
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.stat-value {
  font-size: 12px;
  font-weight: 600;
}

.optimality-excellent {
  color: var(--success-color, #10b981);
}

.optimality-good {
  color: #22c55e;
}

.optimality-fair {
  color: var(--warning-color, #f59e0b);
}

.optimality-poor {
  color: var(--error-color, #ef4444);
}
</style>
