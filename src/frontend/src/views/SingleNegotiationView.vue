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
      <!-- Debug: Show that we're in the right place -->
      <div style="background: red; color: white; padding: 10px; position: fixed; top: 0; right: 0; z-index: 9999; font-size: 12px;">
        DEBUG: {{ negotiation.id }} - {{ negotiation.status }}<br>
        scenario: {{ negotiation.scenario_name }}<br>
        offers: {{ negotiation.offers?.length || 0 }}<br>
        outcome_space: {{ !!negotiation.outcome_space_data }}
      </div>
      
      <!-- Header -->
      <div class="negotiation-header">
        <button @click="handleBackNavigation" class="btn btn-secondary">
          ← Back
        </button>
        <h2>{{ negotiation.scenario_name }}</h2>
        <div class="header-actions">
          <button @click="showStatsModal = true" class="btn btn-secondary">
            Stats
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
            @zoom="handleZoom('2D Utility View', 'utility2d')"
          />
          
          <TimelinePanel 
            :negotiation="negotiation"
            @zoom="handleZoom('Timeline', 'timeline')"
          />
        </template>
      </PanelLayout>

      <!-- Stats Modal -->
      <Teleport to="body">
        <StatsModal
          v-if="showStatsModal"
          :negotiation="negotiation"
          @close="showStatsModal = false"
        />
      </Teleport>

      <!-- Zoom Modal -->
      <Teleport to="body">
        <ZoomModal
          v-if="showZoomModal"
          :title="zoomPanelTitle"
          :panel-type="zoomPanelType"
          :panel-component="zoomPanelComponent"
          :negotiation="negotiation"
          @close="showZoomModal = false"
        />
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

    // Map to negotiation format
    negotiation.value = {
      id: sessionId,
      scenario_name: fullData.scenario,
      negotiator_names: fullData.partners || [],
      negotiator_types: fullData.negotiator_types || [],
      negotiator_colors: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'].slice(0, (fullData.partners || []).length),
      issue_names: fullData.issue_names || [],
      n_steps: fullData.n_steps,
      status: 'completed',
      agreement: fullData.agreement,
      final_utilities: fullData.utilities || [],
      optimality_stats: fullData.optimality_stats,
      outcome_space_data: fullData.outcome_space_data,
      offers: (fullData.history || []).map((item, idx) => ({
        step: item.step || idx,
        offer: item.offer || item.current_offer,
        proposer_index: item.proposer || item.current_proposer || 0,
        relative_time: item.relative_time || 0,
        utilities: item.utilities || [],
      })),
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
