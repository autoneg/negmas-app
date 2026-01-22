<template>
  <div class="single-negotiation-view">
    <!-- Loading State -->
    <div v-if="loading" class="empty-state">
      <p>Loading negotiation...</p>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="empty-state">
      <p style="color: var(--error-color);">{{ error }}</p>
      <button class="btn btn-secondary" @click="router.push({ name: 'NegotiationsList' })">
        ← Back to List
      </button>
    </div>
    
    <!-- Negotiation Viewer -->
    <div v-else-if="negotiation" class="negotiation-viewer">
      <!-- Tournament Context Breadcrumb (if from tournament) -->
      <div v-if="fromTournament" class="tournament-breadcrumb">
        <button class="breadcrumb-link" @click="backToTournament" title="Back to tournament">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          <span>Tournament</span>
        </button>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" style="opacity: 0.3;">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
        <span class="breadcrumb-current">Negotiation #{{ tournamentNegIndex !== null ? tournamentNegIndex + 1 : '?' }}</span>
      </div>
      
      <!-- Compact Header -->
      <div class="table-header" style="margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <button 
            class="btn btn-ghost btn-sm" 
            @click="fromTournament ? backToTournament() : router.push({ name: 'NegotiationsList' })" 
            :title="fromTournament ? 'Back to tournament' : 'Back to negotiations list'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            <span>{{ fromTournament ? 'Tournament' : 'Back' }}</span>
          </button>
          <h2 style="font-size: 16px;">Negotiation</h2>
          <span class="badge badge-primary" style="font-size: 12px;">{{ negotiation?.scenario_name || 'Unknown' }}</span>
          <span v-if="fromTournament" class="badge badge-secondary" style="font-size: 11px;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12" style="margin-right: 4px;">
              <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path>
              <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path>
              <path d="M4 22h16"></path>
              <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path>
              <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path>
              <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path>
            </svg>
            From Tournament
          </span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <!-- Stats button -->
          <button class="btn btn-ghost btn-sm" @click="handleShowStats" title="View scenario statistics">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
              <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
            </svg>
            <span>Stats</span>
          </button>
          <button class="btn btn-primary btn-sm" @click="showNewNegotiationModal = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            <span>New</span>
          </button>
        </div>
      </div>
      
      <!-- Panel System Layout -->
      <PanelLayout>
        <!-- Left Column -->
        <template #left>
          <!-- Info Panel (ultra-compact, ~80px) -->
          <InfoPanel 
            :negotiation="negotiation"
            @start="handleStartNegotiation"
            @togglePause="handleTogglePause"
            @stop="handleStopNegotiation"
            @showStats="handleShowStats"
          />
          
          <!-- Offer History Panel (scrollable) -->
          <OfferHistoryPanel 
            :negotiation="negotiation"
            @zoom="showZoomPanel('Offer History', 'offerHistory')"
          />
          
          <!-- Histogram Panel -->
          <HistogramPanel 
            :negotiation="negotiation"
            @zoom="showZoomPanel('Histogram', 'histogram')"
          />
          
          <!-- Issue Space 2D Panel - HIDDEN FOR NOW (future: tabbed zones feature) -->
          <!-- <IssueSpace2DPanel 
            :negotiation="negotiation"
            @zoom="showZoomPanel('Issue Space 2D', 'issueSpace')"
          /> -->
          
          <!-- Result Panel -->
          <ResultPanel 
            :negotiation="negotiation"
            @saveResults="handleSaveResults"
            @zoom="showZoomPanel('Result', 'result')"
          />
        </template>
        
        <!-- Right Column -->
        <template #right>
          <!-- 2D Utility View Panel -->
          <Utility2DPanel 
            :negotiation="negotiation"
            :adjustable="panelSettings?.panels?.adjustable ?? true"
            :initial-x-axis="panelSettings?.panels?.utilityView?.xAxis ?? 0"
            :initial-y-axis="panelSettings?.panels?.utilityView?.yAxis ?? 1"
            @zoom="showZoomPanel('2D Utility View', 'utility2d')"
          />
          
          <!-- Timeline Panel -->
          <TimelinePanel 
            :negotiation="negotiation"
            :adjustable="panelSettings?.panels?.adjustable ?? true"
            :initial-x-axis="panelSettings?.panels?.timeline?.xAxis ?? 'relative_time'"
            :initial-simplified="panelSettings?.panels?.timeline?.simplified ?? false"
            @zoom="showZoomPanel('Timeline', 'timeline')"
          />
        </template>
      </PanelLayout>
    </div>
    
    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>Negotiation not found</p>
      <button class="btn btn-secondary" @click="router.push({ name: 'NegotiationsList' })">
        ← Back to List
      </button>
    </div>
    
    <!-- New Negotiation Modal (teleported to body) -->
    <Teleport to="body">
      <NewNegotiationModal
        :show="showNewNegotiationModal"
        @close="showNewNegotiationModal = false"
        @start="onNegotiationStart"
      />
      
      <!-- Stats Modal -->
      <StatsModal
        :show="showStatsModal"
        :negotiation="negotiation"
        @close="showStatsModal = false"
      />
      
      <!-- Zoom Modal -->
      <ZoomModal
        :show="showZoomModal"
        :title="zoomPanelTitle"
        @close="closeZoomModal"
      >
        <component 
          :is="zoomPanelComponent" 
          v-if="zoomPanelComponent && negotiation"
          :negotiation="negotiation"
          :adjustable="panelSettings?.panels?.adjustable ?? true"
          :initial-x-axis="zoomPanelType === 'utility2d' ? (panelSettings?.panels?.utilityView?.xAxis ?? 0) : (panelSettings?.panels?.timeline?.xAxis ?? 'relative_time')"
          :initial-y-axis="panelSettings?.panels?.utilityView?.yAxis ?? 1"
          :initial-simplified="panelSettings?.panels?.timeline?.simplified ?? false"
          style="width: 100%; height: 100%;"
        />
      </ZoomModal>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, shallowRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useNegotiationsStore } from '../stores/negotiations'
import { storeToRefs } from 'pinia'
import NewNegotiationModal from '../components/NewNegotiationModal.vue'
import StatsModal from '../components/StatsModal.vue'
import ZoomModal from '../components/ZoomModal.vue'
import PanelLayout from '../components/panels/PanelLayout.vue'
import InfoPanel from '../components/panels/InfoPanel.vue'
import OfferHistoryPanel from '../components/panels/OfferHistoryPanel.vue'
import ResultPanel from '../components/panels/ResultPanel.vue'
import Utility2DPanel from '../components/panels/Utility2DPanel.vue'
import TimelinePanel from '../components/panels/TimelinePanel.vue'
import HistogramPanel from '../components/panels/HistogramPanel.vue'
import IssueSpace2DPanel from '../components/panels/IssueSpace2DPanel.vue'

const router = useRouter()
const route = useRoute()
const negotiationsStore = useNegotiationsStore()
const {
  currentSession,
  streamingSession,
  sessionInit,
  offers,
  sessionComplete,
} = storeToRefs(negotiationsStore)

const showNewNegotiationModal = ref(false)
const showStatsModal = ref(false)
const showZoomModal = ref(false)
const zoomPanelTitle = ref('')
const zoomPanelType = ref('')
const zoomPanelComponent = shallowRef(null)
const loading = ref(true)
const error = ref(null)

// Panel settings loaded from localStorage
const panelSettings = ref(null)

// Tournament context (if this negotiation is from a tournament)
const fromTournament = computed(() => currentSession.value?.fromTournament === true)
const tournamentId = computed(() => currentSession.value?.tournamentId || null)
const tournamentNegIndex = computed(() => currentSession.value?.tournamentNegIndex ?? null)

// Computed negotiation data for panels
const negotiation = computed(() => {
  if (!streamingSession.value && !currentSession.value) return null
  
  // Merge session data with streaming data
  return {
    id: currentSession.value?.id,
    scenario_name: sessionInit.value?.scenario_name || currentSession.value?.scenario_name,
    negotiator_names: sessionInit.value?.negotiator_names || currentSession.value?.negotiator_names,
    negotiator_colors: sessionInit.value?.negotiator_colors || currentSession.value?.negotiator_colors,
    issue_names: sessionInit.value?.issue_names,
    n_steps: sessionInit.value?.n_steps || currentSession.value?.n_steps,
    step: offers.value[offers.value.length - 1]?.step || 0,
    offers: offers.value,
    outcome_space_data: sessionInit.value?.outcome_space_data,
    agreement: sessionComplete.value?.agreement || currentSession.value?.agreement,
    final_utilities: sessionComplete.value?.final_utilities || currentSession.value?.final_utilities,
    optimality_stats: sessionComplete.value?.optimality_stats,
    end_reason: sessionComplete.value?.end_reason || currentSession.value?.end_reason,
    error: sessionComplete.value?.error,
    relative_time: offers.value[offers.value.length - 1]?.relative_time || 0,
    pendingStart: streamingSession.value && offers.value.length === 0,
    paused: false, // TODO: Add pause state to store
    isSaved: currentSession.value?.status === 'completed' || currentSession.value?.status === 'failed'
  }
})

onMounted(async () => {
  const sessionId = route.params.id
  
  if (!sessionId) {
    error.value = 'No negotiation ID provided'
    loading.value = false
    return
  }
  
  // Load panel settings from localStorage
  const settingsKey = `negotiation_settings_${sessionId}`
  const storedSettings = localStorage.getItem(settingsKey)
  if (storedSettings) {
    try {
      panelSettings.value = JSON.parse(storedSettings)
    } catch (e) {
      console.error('Failed to parse panel settings:', e)
    }
  }
  
  try {
    // First check running/completed sessions
    await negotiationsStore.loadSessions()
    const session = negotiationsStore.sessions.find(s => s.id === sessionId)
    
    if (session) {
      // Found in sessions list
      negotiationsStore.selectSession(session)
      
      if (session.status === 'running' || session.status === 'pending') {
        // Start streaming for running sessions
        negotiationsStore.startStreaming(sessionId)
      } else if (session.status === 'completed' || session.status === 'failed') {
        // Try to load saved data for completed/failed sessions
        const savedData = await negotiationsStore.loadSavedNegotiation(sessionId)
        
        if (savedData) {
          // Populate streaming state with saved data
          sessionInit.value = {
            scenario_name: savedData.scenario_name,
            negotiator_names: savedData.negotiator_names,
            negotiator_types: savedData.negotiator_types,
            negotiator_colors: savedData.negotiator_colors,
            issue_names: savedData.issue_names,
            n_steps: savedData.n_steps,
            time_limit: savedData.time_limit,
            outcome_space_data: savedData.outcome_space_data,
          }
          
          offers.value = savedData.offers || []
          
          sessionComplete.value = {
            agreement: savedData.agreement,
            final_utilities: savedData.final_utilities,
            optimality_stats: savedData.optimality_stats,
            end_reason: savedData.end_reason,
          }
        }
      }
      
      loading.value = false
    } else {
      // Not in sessions list - try loading from saved
      const savedData = await negotiationsStore.loadSavedNegotiation(sessionId)
      
      if (savedData) {
        // Create a session-like object and select it
        const savedSession = {
          id: savedData.id,
          scenario_name: savedData.scenario_name,
          scenario_path: savedData.scenario_path,
          status: savedData.status,
          current_step: savedData.current_step,
          n_steps: savedData.n_steps,
          negotiator_names: savedData.negotiator_names,
          negotiator_types: savedData.negotiator_types,
          negotiator_colors: savedData.negotiator_colors,
          issue_names: savedData.issue_names,
          agreement: savedData.agreement,
          final_utilities: savedData.final_utilities,
          end_reason: savedData.end_reason,
          isSaved: true,
        }
        
        negotiationsStore.selectSession(savedSession)
        
        // Populate the streaming state with saved data
        sessionInit.value = {
          scenario_name: savedData.scenario_name,
          negotiator_names: savedData.negotiator_names,
          negotiator_types: savedData.negotiator_types,
          negotiator_colors: savedData.negotiator_colors,
          issue_names: savedData.issue_names,
          n_steps: savedData.n_steps,
          time_limit: savedData.time_limit,
          outcome_space_data: savedData.outcome_space_data,
        }
        
        offers.value = savedData.offers || []
        
        sessionComplete.value = {
          agreement: savedData.agreement,
          final_utilities: savedData.final_utilities,
          optimality_stats: savedData.optimality_stats,
          end_reason: savedData.end_reason,
        }
        
        loading.value = false
      } else {
        // Not found anywhere
        error.value = 'Negotiation not found'
        loading.value = false
      }
    }
  } catch (err) {
    console.error('Error loading negotiation:', err)
    error.value = 'Failed to load negotiation'
    loading.value = false
  }
})

onUnmounted(() => {
  negotiationsStore.stopStreaming()
})

function onNegotiationStart(data) {
  // Close modal
  showNewNegotiationModal.value = false
  
  // Navigate to the new negotiation
  if (data.session_id) {
    // Start streaming immediately before navigation
    // Extract step_delay and share_ufuns from the stream_url
    const url = new URL(data.stream_url, window.location.origin)
    const stepDelay = parseFloat(url.searchParams.get('step_delay') || '0.1')
    const shareUfuns = url.searchParams.get('share_ufuns') === 'true'
    
    negotiationsStore.startStreaming(data.session_id, stepDelay, shareUfuns)
    
    router.push({ name: 'SingleNegotiation', params: { id: data.session_id } })
  }
}

// Panel event handlers
function handleStartNegotiation() {
  // Start/resume negotiation
  console.log('Start negotiation')
}

function handleTogglePause() {
  // Toggle pause
  console.log('Toggle pause')
}

async function handleStopNegotiation() {
  // Stop negotiation
  if (currentSession.value && confirm('Are you sure you want to cancel this negotiation?')) {
    await negotiationsStore.cancelSession(currentSession.value.id)
    router.push({ name: 'NegotiationsList' })
  }
}

function handleShowStats() {
  console.log('[SingleNegotiationView] Opening stats modal')
  console.log('[SingleNegotiationView] negotiation:', negotiation.value)
  console.log('[SingleNegotiationView] outcome_space_data:', negotiation.value?.outcome_space_data)
  showStatsModal.value = true
}

function showZoomPanel(title, panelType) {
  zoomPanelTitle.value = title
  zoomPanelType.value = panelType
  
  // Map panel type to component
  const componentMap = {
    'offerHistory': OfferHistoryPanel,
    'histogram': HistogramPanel,
    'issueSpace': IssueSpace2DPanel,
    'result': ResultPanel,
    'utility2d': Utility2DPanel,
    'timeline': TimelinePanel
  }
  
  zoomPanelComponent.value = componentMap[panelType] || null
  showZoomModal.value = true
}

function closeZoomModal() {
  showZoomModal.value = false
  zoomPanelComponent.value = null
}

function handleSaveResults() {
  // Save results to file
  console.log('Save results')
}

function backToTournament() {
  // Navigate back to the tournament this negotiation came from
  if (tournamentId.value) {
    router.push({ name: 'SingleTournament', params: { id: tournamentId.value } })
  } else {
    // Fallback to tournaments list
    router.push({ name: 'TournamentsList' })
  }
}
</script>

<style scoped>
.single-negotiation-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--bg-primary);
  padding: 16px;
  overflow: hidden;
}

.negotiation-viewer {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.tournament-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  margin-bottom: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.breadcrumb-link {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: var(--primary-color);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}

.breadcrumb-link:hover {
  background: var(--bg-hover);
  color: var(--primary-hover);
}

.breadcrumb-current {
  font-weight: 500;
  color: var(--text-primary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  gap: 16px;
  padding: 48px 24px;
  height: 100%;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.badge-primary {
  background: rgba(59, 130, 246, 0.2);
  color: rgb(59, 130, 246);
}

.badge-secondary {
  background: rgba(107, 114, 128, 0.2);
  color: rgb(107, 114, 128);
}

.btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
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
  font-size: 0.8rem;
}

.btn-ghost {
  background: transparent;
  border: none;
}

.btn-ghost:hover {
  background: var(--bg-hover);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.btn-primary:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}
</style>
