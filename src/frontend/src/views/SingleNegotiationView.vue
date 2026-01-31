<template>
  <div class="single-negotiation-view">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading negotiation...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <p>{{ error }}</p>
      <button @click="handleBackNavigation" class="btn btn-primary">Go Back</button>
    </div>

    <!-- Main Content -->
    <div v-else-if="negotiation" class="negotiation-content">
      <!-- Header -->
      <div class="negotiation-header">
        <button @click="handleBackNavigation" class="btn btn-secondary">
          ← Back
        </button>
        <h2>{{ negotiation.scenario_name }}</h2>
        <div class="header-actions">
          <button @click="showStatsModal = true" class="btn btn-ghost btn-sm">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
              <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
            </svg>
            <span>Stats</span>
          </button>
          <button @click="handleResetLayout" class="btn btn-ghost btn-sm" title="Reset panel layout to default">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="3" y1="9" x2="21" y2="9"></line>
              <line x1="9" y1="21" x2="9" y2="9"></line>
            </svg>
            <span>Reset Layout</span>
          </button>
          <button 
            v-if="negotiation.status === 'completed' || negotiation.status === 'failed'"
            @click="handleDownloadNegotiation" 
            class="btn btn-ghost btn-sm" 
            title="Download negotiation data as ZIP"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            <span>Download</span>
          </button>
        </div>
      </div>

      <!-- Panel Layout -->
      <PanelLayout ref="panelLayoutRef">
        <!-- Left Column -->
        <template #left>
          <InfoPanel 
            :negotiation="negotiation"
            @togglePause="handleTogglePause"
            @stop="handleCancel"
            @showStats="handleShowStats"
          />
          
          <OfferHistoryPanel 
            :negotiation="negotiation"
            @saveOffersJson="handleSaveOffersJson"
            @zoom="handleZoom('Offer History', 'offerHistory')"
          />
          
          <HistogramPanel 
            :negotiation="negotiation"
            @zoom="handleZoom('Histogram', 'histogram')"
          />
          
          <ResultPanel 
            :negotiation="negotiation"
            @saveResults="handleSaveResults"
            @zoom="handleZoom('Result', 'result')"
          />
        </template>
        
        <!-- Right Column -->
        <template #right>
          <Utility2DPanel 
            :negotiation="negotiation"
            @saveAsImage="handleSaveAsImage('utility2d')"
            @zoom="handleZoom('2D Utility View', 'utility2d')"
          />
          
          <TimelinePanel 
            :negotiation="negotiation"
            @saveAsImage="handleSaveAsImage('timeline')"
            @zoom="handleZoom('Timeline', 'timeline')"
          />
        </template>
      </PanelLayout>

      <!-- Stats Modal -->
      <Teleport to="body">
        <StatsModal
          v-if="showStatsModal"
          :show="showStatsModal"
          :negotiation="negotiation"
          @close="showStatsModal = false"
        />
      </Teleport>

      <!-- Zoom Modal -->
      <Teleport to="body">
        <ZoomModal
          v-if="showZoomModal"
          :show="showZoomModal"
          :title="zoomPanelTitle"
          @close="showZoomModal = false"
        >
          <component 
            :is="zoomPanelComponent" 
            v-if="zoomPanelComponent && negotiation"
            :negotiation="negotiation"
            :adjustable="true"
            :initial-x-axis="zoomPanelType === 'utility2d' ? 0 : 'step'"
            :initial-y-axis="1"
            :initial-simplified="false"
            style="width: 100%; height: 100%;"
          />
        </ZoomModal>
      </Teleport>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, shallowRef, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useNegotiationsStore } from '../stores/negotiations'
import StatsModal from '../components/StatsModal.vue'
import ZoomModal from '../components/ZoomModal.vue'
import PanelLayout from '../components/panels/PanelLayout.vue'
import InfoPanel from '../components/panels/InfoPanel.vue'
import OfferHistoryPanel from '../components/panels/OfferHistoryPanel.vue'
import HistogramPanel from '../components/panels/HistogramPanel.vue'
import ResultPanel from '../components/panels/ResultPanel.vue'
import Utility2DPanel from '../components/panels/Utility2DPanel.vue'
import TimelinePanel from '../components/panels/TimelinePanel.vue'

const router = useRouter()
const route = useRoute()
const negotiationsStore = useNegotiationsStore()

// State
const negotiation = ref(null)
const loading = ref(true)
const error = ref(null)
const showStatsModal = ref(false)
const showZoomModal = ref(false)
const zoomPanelTitle = ref('')
const zoomPanelType = ref('')
const zoomPanelComponent = shallowRef(null)
const panelLayoutRef = ref(null)
const fromTournament = ref(false)

// Polling interval
let pollInterval = null

/**
 * Load negotiation and start polling if needed
 */
async function loadNegotiation(sessionId) {
  loading.value = true
  error.value = null
  
  console.log('[SingleNegotiationView] Loading session:', sessionId)

  try {
    // Check if this is a tournament negotiation
    if (sessionId.startsWith('tournament:') || route.query.tournament_id) {
      await loadTournamentNegotiation(sessionId)
      return
    }

    // Try to load from active sessions first
    let data = await negotiationsStore.getSession(sessionId)
    
    // If not in active sessions, try saved negotiations
    if (!data) {
      console.log('[SingleNegotiationView] Not in active sessions, trying saved...')
      data = await negotiationsStore.loadSavedNegotiation(sessionId)
    }
    
    console.log('[SingleNegotiationView] Got session data:', data)
    
    if (!data) {
      console.log('[SingleNegotiationView] No data, setting error')
      error.value = 'Negotiation not found'
      loading.value = false
      return
    }

    // If session is pending and not yet initialized, keep loading state and poll
    if ((data.status === 'pending' || data.status === 'running') && !data.scenario_name) {
      console.log('[SingleNegotiationView] Session not initialized yet, keeping loading state and polling')
      // Session exists but hasn't been initialized by the thread yet
      // Start polling and keep loading state until we get data
      startPolling(sessionId)
      return // Stay in loading state
    }

    console.log('[SingleNegotiationView] Setting negotiation data and exiting loading')
    // Update state
    negotiation.value = data
    negotiationsStore.selectSession({ id: data.id, status: data.status })
    loading.value = false

    // Start polling if running
    if (data.status === 'running' || data.status === 'pending') {
      console.log('[SingleNegotiationView] Starting polling for running/pending session')
      startPolling(sessionId)
    }
  } catch (err) {
    console.error('[SingleNegotiationView] Load error:', err)
    error.value = err.message || 'Failed to load negotiation'
    loading.value = false
  }
}

/**
 * Load tournament negotiation
 */
async function loadTournamentNegotiation(sessionId) {
  fromTournament.value = true
  const tournamentIdValue = route.query.tournament_id || sessionId.split(':')[1]
  const indexStr = route.query.index || sessionId.split(':')[2]
  const index = parseInt(indexStr, 10)

  if (!tournamentIdValue || isNaN(index)) {
    error.value = 'Invalid tournament negotiation reference'
    loading.value = false
    return
  }

  try {
    const response = await fetch(`/api/tournament/saved/${tournamentIdValue}/negotiation/${index}`)
    
    if (!response.ok) {
      error.value = response.status === 404 
        ? `Tournament negotiation not found: ${tournamentIdValue}/${index}`
        : `Failed to load tournament negotiation: ${response.statusText}`
      loading.value = false
      return
    }

    const fullData = await response.json()

    // Extract negotiator names from either partners or negotiators array
    const negotiatorNames = fullData.partners || 
      (fullData.negotiators || []).map(n => n.name || n.short_type || 'Unknown')
    const negotiatorTypes = fullData.negotiator_types || 
      (fullData.negotiators || []).map(n => n.type || n.short_type || 'Unknown')
    
    // Get issue names for converting arrays to dicts
    const issueNames = fullData.issue_names || []
    
    // Helper to convert array to dict using issue_names
    const arrayToDict = (arr) => {
      if (!arr || !Array.isArray(arr) || issueNames.length === 0) {
        return arr  // Return as-is if not an array or no issue names
      }
      const dict = {}
      issueNames.forEach((name, i) => {
        if (i < arr.length) {
          dict[name] = arr[i]
        }
      })
      return dict
    }
    
    // Convert agreement array to dict if needed
    const agreement = arrayToDict(fullData.agreement)

    // Map to negotiation format
    negotiation.value = {
      id: sessionId,
      scenario_name: fullData.scenario,
      negotiator_names: negotiatorNames,
      negotiator_types: negotiatorTypes,
      negotiator_colors: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'].slice(0, negotiatorNames.length),
      issue_names: issueNames,
      n_steps: fullData.n_steps,
      status: 'completed',
      agreement: agreement,
      final_utilities: fullData.final_utilities || fullData.utilities || [],
      optimality_stats: fullData.optimality_stats || {
        pareto_optimality: fullData.pareto_optimality,
        nash_optimality: fullData.nash_optimality,
        kalai_optimality: fullData.kalai_optimality,
        ks_optimality: fullData.ks_optimality,
        max_welfare_optimality: fullData.max_welfare_optimality,
      },
      outcome_space_data: fullData.outcome_space_data,
      offers: (fullData.history || []).map((item, idx) => {
        // Convert offer array to dict using issue_names
        const rawOffer = item.offer || item.current_offer
        const offer = arrayToDict(rawOffer)
        
        return {
          step: item.step ?? idx,
          offer: offer,
          proposer_index: item.proposer ?? item.current_proposer ?? (item.negotiator ? 0 : 0),
          relative_time: item.relative_time || 0,
          utilities: item.utilities || [],
        }
      }),
    }

    loading.value = false
  } catch (err) {
    console.error('[SingleNegotiationView] Tournament load error:', err)
    error.value = 'Failed to load tournament negotiation'
    loading.value = false
  }
}

/**
 * Start polling for updates
 */
function startPolling(sessionId) {
  // Clear any existing interval
  if (pollInterval) {
    clearInterval(pollInterval)
  }

  pollInterval = setInterval(async () => {
    try {
      // Try active sessions first
      let updated = await negotiationsStore.getSession(sessionId)
      
      // If not in active sessions (might be completed and saved), try saved
      if (!updated) {
        updated = await negotiationsStore.loadSavedNegotiation(sessionId)
      }
      
      if (updated) {
        negotiation.value = updated
        
        // If we were in loading state and now have data, exit loading
        if (loading.value && updated.scenario_name) {
          loading.value = false
        }

        // Stop polling if completed
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(pollInterval)
          pollInterval = null
          await negotiationsStore.loadSessions()
        }
      } else {
        // Session not found in active or saved - stop polling
        clearInterval(pollInterval)
        pollInterval = null
        console.log('[SingleNegotiationView] Session not found, stopped polling')
      }
    } catch (err) {
      console.error('[SingleNegotiationView] Polling error:', err)
    }
  }, 1000) // Poll every second
}

/**
 * Handle zoom panel
 */
function handleZoom(title, panelType) {
  zoomPanelTitle.value = title
  zoomPanelType.value = panelType
  
  // Map panel type to component
  const componentMap = {
    'offerHistory': OfferHistoryPanel,
    'histogram': HistogramPanel,
    'result': ResultPanel,
    'utility2d': Utility2DPanel,
    'timeline': TimelinePanel
  }
  
  zoomPanelComponent.value = componentMap[panelType] || null
  showZoomModal.value = true
}

/**
 * Handle toggle pause
 */
async function handleTogglePause() {
  if (!negotiation.value?.id) return
  
  try {
    if (negotiation.value.status === 'paused') {
      await negotiationsStore.resumeSession(negotiation.value.id)
    } else {
      await negotiationsStore.pauseSession(negotiation.value.id)
    }
  } catch (err) {
    console.error('[SingleNegotiationView] Failed to toggle pause:', err)
  }
}

/**
 * Handle show stats
 */
function handleShowStats() {
  showStatsModal.value = true
}

/**
 * Handle reset layout
 */
function handleResetLayout() {
  if (panelLayoutRef.value) {
    panelLayoutRef.value.resetLayout()
  }
}

/**
 * Handle cancel
 */
async function handleCancel() {
  if (!negotiation.value?.id) return
  if (!confirm('Are you sure you want to cancel this negotiation?')) return
  
  try {
    await negotiationsStore.cancelSession(negotiation.value.id)
    router.push({ name: 'NegotiationsList' })
  } catch (err) {
    console.error('[SingleNegotiationView] Failed to cancel:', err)
  }
}

/**
 * Handle save results
 */
function handleSaveResults() {
  console.log('[SingleNegotiationView] Save results')
  // TODO: Implement save results to file
}

/**
 * Handle save offers as JSON
 */
function handleSaveOffersJson() {
  if (!negotiation.value?.offers) return
  
  const data = {
    scenario_name: negotiation.value.scenario_name,
    negotiator_names: negotiation.value.negotiator_names,
    offers: negotiation.value.offers,
    agreement: negotiation.value.agreement,
    final_utilities: negotiation.value.final_utilities,
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${negotiation.value.scenario_name || 'negotiation'}_offers.json`
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * Handle save as image
 */
function handleSaveAsImage(panelType) {
  console.log('[SingleNegotiationView] Save as image:', panelType)
  // TODO: Implement save panel as image
}

/**
 * Handle download negotiation folder (zip)
 */
async function handleDownloadNegotiation() {
  if (!negotiation.value?.id) return
  
  try {
    const response = await fetch(`/api/negotiation/saved/${negotiation.value.id}/download`)
    if (!response.ok) {
      throw new Error('Download failed')
    }
    
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${negotiation.value.scenario_name || 'negotiation'}_${negotiation.value.id}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('[SingleNegotiationView] Failed to download negotiation:', err)
    alert('Failed to download negotiation: ' + err.message)
  }
}

/**
 * Handle back navigation
 */
function handleBackNavigation() {
  if (fromTournament.value && route.query.tournament_id) {
    router.push({
      name: 'SingleTournament',
      params: { id: route.query.tournament_id }
    })
  } else if (route.query.from === 'configs') {
    router.push({ name: 'Configs' })
  } else {
    router.push({ name: 'NegotiationsList' })
  }
}

// Lifecycle
onMounted(async () => {
  const sessionId = route.params.id
  await loadNegotiation(sessionId)
})

onUnmounted(() => {
  // Cleanup polling
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
})

// Watch for route changes
watch(() => route.params.id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    // Cleanup old polling
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
    
    // Load new negotiation
    await loadNegotiation(newId)
  }
})
</script>

<style scoped>
.single-negotiation-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-color);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.negotiation-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.negotiation-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.negotiation-header h2 {
  flex: 1;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}
</style>
