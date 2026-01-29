<template>
  <div class="single-negotiation-view">
    <!-- Loading State -->
    <div v-if="loading" class="empty-state">
      <p>Loading negotiation...</p>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="empty-state">
      <p style="color: var(--error-color);">{{ error }}</p>
      <button class="btn btn-secondary" @click="handleBackNavigation">
        ← Back
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
            @click="handleBackNavigation" 
            :title="fromTournament ? 'Back to tournament' : fromConfigs ? 'Back to configs' : 'Back to negotiations list'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            <span>{{ fromTournament ? 'Tournament' : fromConfigs ? 'Configs' : 'Back' }}</span>
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
          <!-- Reset Layout button -->
          <button class="btn btn-ghost btn-sm" @click="handleResetLayout" title="Reset panel layout to default">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="3" y1="9" x2="21" y2="9"></line>
              <line x1="9" y1="21" x2="9" y2="9"></line>
            </svg>
            <span>Reset Layout</span>
          </button>
          <!-- Rerun button (only for saved negotiations) -->
          <button 
            v-if="negotiation?.isSaved && !fromTournament" 
            class="btn btn-ghost btn-sm" 
            @click="handleRerunNegotiation" 
            title="Rerun this negotiation with same configuration"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21 2v6h-6"></path>
              <path d="M3 12a9 9 0 0 1 15-6.7L21 8"></path>
              <path d="M3 22v-6h6"></path>
              <path d="M21 12a9 9 0 0 1-15 6.7L3 16"></path>
            </svg>
            <span>Rerun</span>
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
      <PanelLayout ref="panelLayoutRef">
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
      <button class="btn btn-secondary" @click="handleBackNavigation">
        ← Back
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
      
      <!-- Error Modal -->
      <div v-if="showErrorModal" class="modal-overlay active" @click.self="showErrorModal = false">
        <div class="modal-content" style="max-width: 500px; background: var(--bg-secondary);">
          <div class="modal-header" style="background: var(--bg-secondary);">
            <h3 class="modal-title">Negotiation Failed</h3>
            <button class="modal-close-btn" @click="showErrorModal = false" title="Close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="modal-body" style="background: var(--bg-secondary);">
            <div style="display: flex; align-items: flex-start; gap: 16px;">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24" style="color: var(--danger); flex-shrink: 0; margin-top: 2px;">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <div style="flex: 1;">
                <p style="margin: 0 0 12px 0; color: var(--text-primary); line-height: 1.5;">
                  The negotiation failed to start or encountered an error during execution.
                </p>
                <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 6px; border-left: 3px solid var(--danger);">
                  <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px;">Error Details</div>
                  <div style="font-family: monospace; font-size: 12px; color: var(--text-primary); white-space: pre-wrap; word-break: break-word;">{{ errorMessage }}</div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer" style="background: var(--bg-secondary);">
            <button class="btn btn-secondary" @click="showErrorModal = false">
              Close
            </button>
            <button class="btn btn-primary" @click="showErrorModal = false; handleBackNavigation()">
              Go Back
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, shallowRef, watch } from 'vue'
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

// Try to initialize store with error handling
let negotiationsStore
try {
  negotiationsStore = useNegotiationsStore()
  console.log('[SingleNegotiationView] Store type:', typeof negotiationsStore, 'Value:', negotiationsStore)
  
  if (!negotiationsStore) {
    throw new Error('useNegotiationsStore() returned null/undefined')
  }
} catch (e) {
  console.error('[SingleNegotiationView] Failed to get store:', e)
  // Re-throw to show error to user
  throw new Error(`Failed to initialize negotiations store: ${e.message}`)
}

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
const showErrorModal = ref(false)
const errorMessage = ref('')
const zoomPanelTitle = ref('')
const zoomPanelType = ref('')
const zoomPanelComponent = shallowRef(null)
const loading = ref(true)
const error = ref(null)

// Panel layout ref for reset functionality
const panelLayoutRef = ref(null)

// Panel settings loaded from localStorage
const panelSettings = ref(null)

// Tournament context (if this negotiation is from a tournament)
const fromTournament = ref(false)
const tournamentId = ref(null)
const tournamentNegIndex = ref(null)

// Check if coming from configs page
const fromConfigs = computed(() => route.query.from === 'configs')

// Computed negotiation data for panels
const negotiation = computed(() => {
  // Return null only if we have no session data at all
  if (!streamingSession.value && !currentSession.value) {
    console.log('[SingleNegotiationView] negotiation computed: no session data')
    return null
  }
  
  // Don't return null during loading - instead return whatever data we have
  // The template shows loading state separately via v-if="loading"
  console.log('[SingleNegotiationView] negotiation computed: building negotiation object', {
    loading: loading.value,
    hasCurrentSession: !!currentSession.value,
    hasSessionInit: !!sessionInit.value,
    hasOffers: offers.value.length,
    hasSessionComplete: !!sessionComplete.value
  })
  
  // Check for duplicate steps in offers array
  if (offers.value.length > 1) {
    const steps = offers.value.map(o => o.step)
    const uniqueSteps = new Set(steps)
    if (steps.length !== uniqueSteps.size) {
      console.warn('[SingleNegotiationView] ⚠️ DUPLICATE STEPS DETECTED in offers array!', {
        totalOffers: offers.value.length,
        uniqueSteps: uniqueSteps.size,
        firstFewSteps: steps.slice(0, 10),
        lastFewSteps: steps.slice(-10)
      })
    }
    
    // Check if steps restart from 0
    const maxStep = Math.max(...steps)
    const stepZeroCount = steps.filter(s => s === 0).length
    if (stepZeroCount > 1) {
      console.warn('[SingleNegotiationView] ⚠️ MULTIPLE STEP 0s DETECTED!', {
        count: stepZeroCount,
        maxStep,
        description: 'Steps may have restarted!'
      })
    }
  }
  
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
    // CRITICAL FIX: Only show agreement/final_utilities when negotiation completes
    // Do NOT fall back to currentSession during active negotiation - it may have stale data
    agreement: sessionComplete.value?.agreement || (currentSession.value?.status === 'completed' ? currentSession.value?.agreement : null),
    final_utilities: sessionComplete.value?.final_utilities || (currentSession.value?.status === 'completed' ? currentSession.value?.final_utilities : null),
    optimality_stats: sessionComplete.value?.optimality_stats,
    end_reason: sessionComplete.value?.end_reason || currentSession.value?.end_reason,
    error: sessionComplete.value?.error,
    relative_time: offers.value[offers.value.length - 1]?.relative_time || 0,
    pendingStart: streamingSession.value && offers.value.length === 0,
    paused: false, // TODO: Add pause state to store
    isSaved: currentSession.value?.status === 'completed' || currentSession.value?.status === 'failed'
  }
})

// Debug: Watch sessionInit for changes
watch(() => sessionInit.value, (newVal) => {
  console.log('[SingleNegotiationView] sessionInit changed:', {
    hasSessionInit: !!newVal,
    hasOutcomeSpaceData: !!newVal?.outcome_space_data,
    sessionInit: newVal
  })
}, { immediate: true, deep: true })

// Watch for errors in sessionComplete and show error dialog
watch(() => sessionComplete.value?.error, (errorMsg, oldErrorMsg) => {
  // Only show modal if error is new (different from previous)
  // This prevents showing stale errors on page load
  if (errorMsg && errorMsg !== oldErrorMsg) {
    console.log('[SingleNegotiationView] Error detected:', errorMsg)
    errorMessage.value = errorMsg
    showErrorModal.value = true
  }
}, { immediate: false })

// Extract data loading into a reusable function
async function loadNegotiationData(sessionId) {
  console.log('[SingleNegotiationView] loadNegotiationData called for:', sessionId)
  
  if (!sessionId) {
    error.value = 'No negotiation ID provided'
    loading.value = false
    return
  }
  
  // CRITICAL: Clear any existing polling interval first to prevent multiple intervals
  if (negotiationsStore._singleViewPollInterval) {
    console.log('[SingleNegotiationView] Clearing existing polling interval')
    clearInterval(negotiationsStore._singleViewPollInterval)
    negotiationsStore._singleViewPollInterval = null
  }
  
  // Reset state - CRITICAL: Clear all old negotiation data to prevent stale data display
  loading.value = true
  error.value = null
  sessionInit.value = null
  offers.value = []
  sessionComplete.value = null
  fromTournament.value = false
  tournamentId.value = null
  tournamentNegIndex.value = null
  console.log('[SingleNegotiationView] Reset all state: loading=true, cleared all negotiation data')
  
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
    // Check if this is a tournament negotiation
    if (sessionId.startsWith('tournament:') || route.query.tournament_id) {
      // Handle tournament negotiation
      const tournamentIdValue = route.query.tournament_id || sessionId.split(':')[1]
      const indexStr = route.query.index || sessionId.split(':')[2]
      const index = parseInt(indexStr, 10)
      
      if (!tournamentIdValue || isNaN(index)) {
        throw new Error('Invalid tournament negotiation reference')
      }
      
      // Set tournament context for back navigation
      fromTournament.value = true
      tournamentId.value = tournamentIdValue
      tournamentNegIndex.value = index
      
      console.log('[SingleNegotiationView] Loading tournament negotiation:', tournamentIdValue, index)
      const response = await fetch(`/api/tournament/saved/${tournamentIdValue}/negotiation/${index}`)
      
      if (!response.ok) {
        if (response.status === 404) {
          error.value = `Tournament negotiation not found: ${tournamentIdValue}/${index}`
        } else {
          error.value = `Failed to load tournament negotiation: ${response.statusText}`
        }
        loading.value = false
        return
      }
      
      const fullData = await response.json()
      console.log('[SingleNegotiationView] Tournament negotiation loaded:', fullData)
      
      // Map history to offers format (offers array with step, offer, time, proposer)
      const offers = (fullData.history || []).map((item, idx) => ({
        step: item.step || idx,
        offer: item.offer || item.current_offer,
        time: item.time || item.relative_time || 0,
        proposer: item.proposer || item.current_proposer || 0,
        relative_time: item.relative_time || 0
      }))
      
      // Populate session data
      sessionInit.value = {
        scenario_name: fullData.scenario,
        negotiator_names: fullData.partners || [],
        negotiator_types: fullData.negotiator_types || [],
        negotiator_colors: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'].slice(0, (fullData.partners || []).length),
        issue_names: fullData.issue_names || [],
        n_steps: fullData.n_steps || offers.length,
        time_limit: fullData.time_limit,
        outcome_space_data: fullData.outcome_space_data,
      }
      
      offers.value = offers
      
      sessionComplete.value = {
        agreement: fullData.agreement,
        final_utilities: fullData.utilities || [],
        optimality_stats: fullData.optimality_stats,
        end_reason: fullData.has_agreement ? 'agreement' : 'disagreement',
        error: fullData.error,
      }
      
      loading.value = false
      return
    }
    
    // Regular negotiation handling (existing code)
    // First check running/completed sessions
    console.log('[SingleNegotiationView] Loading sessions list...')
    await negotiationsStore.loadSessions()
    const session = negotiationsStore.sessions.find(s => s.id === sessionId)
    console.log('[SingleNegotiationView] Session found:', !!session, session?.status)
    
    if (session) {
      // Found in sessions list
      negotiationsStore.selectSession(session)
      
      if (session.status === 'running' || session.status === 'pending') {
        // For running sessions, load current state first, then start streaming
        try {
          console.log('[SingleNegotiationView] Loading current state for session:', sessionId)
          const currentState = await negotiationsStore.getSession(sessionId)
          console.log('[SingleNegotiationView] Current state loaded:', {
            hasData: !!currentState,
            status: currentState?.status,
            current_step: currentState?.current_step,
            offers_count: currentState?.offers?.length || 0
          })
          if (currentState) {
            // Populate with current state
            sessionInit.value = {
              scenario_name: currentState.scenario_name,
              negotiator_names: currentState.negotiator_names,
              negotiator_types: currentState.negotiator_types,
              negotiator_colors: currentState.negotiator_colors,
              issue_names: currentState.issue_names,
              n_steps: currentState.n_steps,
              time_limit: currentState.time_limit,
              outcome_space_data: currentState.outcome_space_data,
            }
            
            offers.value = currentState.offers || []
            console.log('[SingleNegotiationView] Set offers.value to:', offers.value.length, 'offers')
            
            // If already completed, show completion state
            if (currentState.status === 'completed' || currentState.status === 'failed') {
              sessionComplete.value = {
                agreement: currentState.agreement,
                final_utilities: currentState.final_utilities,
                optimality_stats: currentState.optimality_stats,
                end_reason: currentState.end_reason,
                error: currentState.error,
              }
            } else {
              // Still running - clear any old completion data and poll for updates
              // IMPORTANT: Clear sessionComplete to avoid showing old agreement markers
              sessionComplete.value = null
              
              // Poll for updates instead of streaming
              // (SSE stream would restart the negotiation from beginning!)
              console.log('[SingleNegotiationView] Setting up polling for running negotiation')
              const pollInterval = setInterval(async () => {
                try {
                  const updated = await negotiationsStore.getSession(sessionId)
                  if (updated) {
                    console.log('[Polling] Received update:', {
                      offersLength: updated.offers?.length,
                      currentLength: offers.value.length,
                      status: updated.status,
                      hasAgreement: !!updated.agreement
                    })
                    
                    // Update offers if there are new ones
                    if (updated.offers && updated.offers.length > offers.value.length) {
                      // Log the new offers to detect duplicates
                      const newOffers = updated.offers.slice(offers.value.length)
                      console.log('[Polling] New offers received:', {
                        newCount: newOffers.length,
                        firstNew: newOffers[0] ? {
                          step: newOffers[0].step,
                          relative_time: newOffers[0].relative_time
                        } : null,
                        lastNew: newOffers[newOffers.length - 1] ? {
                          step: newOffers[newOffers.length - 1].step,
                          relative_time: newOffers[newOffers.length - 1].relative_time
                        } : null
                      })
                      
                      // Check for step number anomalies (restarting from 0 or duplicates)
                      if (offers.value.length > 0 && newOffers.length > 0) {
                        const lastOldStep = offers.value[offers.value.length - 1].step
                        const firstNewStep = newOffers[0].step
                        if (firstNewStep <= lastOldStep) {
                          console.warn('[Polling] ⚠️ STEP NUMBER ANOMALY DETECTED!', {
                            lastOldStep,
                            firstNewStep,
                            description: firstNewStep === 0 ? 'Steps restarted from 0!' : 'Step numbers went backwards!'
                          })
                        }
                      }
                      
                      offers.value = updated.offers
                      console.log('[Polling] Updated offers array, total:', offers.value.length)
                    }
                    
                    // Check if completed
                    if (updated.status === 'completed' || updated.status === 'failed') {
                      console.log('[Polling] Negotiation completed:', {
                        status: updated.status,
                        hasAgreement: !!updated.agreement,
                        totalOffers: updated.offers?.length,
                        endReason: updated.end_reason
                      })
                      sessionComplete.value = {
                        agreement: updated.agreement,
                        final_utilities: updated.final_utilities,
                        optimality_stats: updated.optimality_stats,
                        end_reason: updated.end_reason,
                        error: updated.error,
                      }
                      clearInterval(pollInterval)
                      await negotiationsStore.loadSessions()
                      console.log('[SingleNegotiationView] Negotiation completed, stopped polling')
                    }
                  }
                } catch (err) {
                  console.error('[SingleNegotiationView] Polling error:', err)
                }
              }, 1000) // Poll every second
              
              // Store interval for cleanup
              negotiationsStore._singleViewPollInterval = pollInterval
            }
            
            // Data is loaded, set loading to false
            console.log('[SingleNegotiationView] Running negotiation data loaded, setting loading=false')
            loading.value = false
          }
        } catch (err) {
          console.error('Failed to load current state:', err)
          error.value = 'Failed to load negotiation'
          loading.value = false
          setTimeout(() => {
            router.push({ name: 'NegotiationsList' })
          }, 2000)
        }
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
      
      console.log('[SingleNegotiationView] Data loading complete, setting loading=false')
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
        // Not found anywhere - redirect to negotiations list
        console.log('[SingleNegotiationView] Negotiation not found, redirecting to list')
        router.push({ name: 'NegotiationsList' })
      }
    }
  } catch (err) {
    console.error('Error loading negotiation:', err)
    error.value = 'Failed to load negotiation'
    loading.value = false
    // Auto-redirect after showing error briefly
    setTimeout(() => {
      router.push({ name: 'NegotiationsList' })
    }, 2000)
  }
}

// Load data on mount
onMounted(async () => {
  console.log('[SingleNegotiationView] onMounted called')
  const sessionId = route.params.id
  await loadNegotiationData(sessionId)
})

// Watch for route changes and reload data when navigating to a different negotiation
// IMPORTANT: Don't trigger on initial load (onMounted handles that)
let isInitialMount = true
watch(() => route.params.id, async (newId, oldId) => {
  // Skip the first run (initial mount)
  if (isInitialMount) {
    isInitialMount = false
    console.log('[SingleNegotiationView] Route watcher: skipping initial mount')
    return
  }
  
  if (newId && newId !== oldId) {
    console.log('[SingleNegotiationView] Route changed, loading new negotiation:', newId)
    // Cleanup any existing polling
    if (negotiationsStore._singleViewPollInterval) {
      clearInterval(negotiationsStore._singleViewPollInterval)
      negotiationsStore._singleViewPollInterval = null
    }
    await loadNegotiationData(newId)
  }
})

onUnmounted(() => {
  // Cleanup streaming
  negotiationsStore.stopStreaming()
  
  // Also cleanup any event source we created directly
  if (negotiationsStore.eventSource) {
    negotiationsStore.eventSource.close()
  }
  
  // Cleanup polling interval if it exists
  if (negotiationsStore._singleViewPollInterval) {
    clearInterval(negotiationsStore._singleViewPollInterval)
    negotiationsStore._singleViewPollInterval = null
  }
})

function onNegotiationStart(data) {
  // Close modal
  showNewNegotiationModal.value = false
  
  // Navigate to the new negotiation
  // Since we're using background mode, the negotiation is already running
  // We don't need to start SSE streaming - just navigate and let polling handle updates
  if (data.session_id) {
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

function handleResetLayout() {
  console.log('[SingleNegotiationView] Resetting panel layout')
  if (panelLayoutRef.value) {
    panelLayoutRef.value.resetLayout()
  }
}

async function handleRerunNegotiation() {
  if (!currentSession.value?.id) return
  
  try {
    const data = await negotiationsStore.rerunNegotiation(currentSession.value.id)
    
    if (data?.session_id) {
      // Rerun uses background mode, so just navigate - polling will handle updates
      router.push({ name: 'SingleNegotiation', params: { id: data.session_id } })
    }
  } catch (error) {
    console.error('Failed to rerun negotiation:', error)
    alert('Failed to rerun negotiation: ' + error.message)
  }
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
  // If we have a fromList query param, navigate back to the tournament negotiations list
  if (route.query.fromList === 'true' && tournamentId.value) {
    router.push({ 
      name: 'TournamentNegotiationsList', 
      params: { tournamentId: tournamentId.value } 
    })
  } else if (tournamentId.value) {
    // Otherwise go to tournament detail view
    router.push({ name: 'SingleTournament', params: { id: tournamentId.value } })
  } else {
    // Fallback to tournaments list
    router.push({ name: 'TournamentsList' })
  }
}

function handleBackNavigation() {
  if (fromTournament.value) {
    backToTournament()
  } else if (fromConfigs.value) {
    // Check if we came from tournaments tab in configs
    if (route.query.tab === 'tournaments') {
      router.push({ name: 'Configs', query: { tab: 'tournaments' } })
    } else {
      router.push({ name: 'Configs' })
    }
  } else {
    router.push({ name: 'NegotiationsList' })
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
</style>
