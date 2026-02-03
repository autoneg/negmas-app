<template>
  <div class="single-tournament-view">
    <!-- Loading State -->
    <div v-if="loading" class="empty-state">
      <div class="spinner"></div>
      <p>Loading tournament...</p>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="empty-state">
      <p style="color: var(--error-color);">{{ error }}</p>
      <button class="btn btn-secondary" @click="router.push({ name: 'TournamentsList' })">
        ← Back to List
      </button>
    </div>
    
    <!-- Tournament Viewer -->
    <div v-else-if="currentSession" class="tournament-viewer">
      <!-- Compact Header -->
      <div class="viewer-header">
        <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
          <button class="btn btn-ghost btn-sm" @click="router.push({ name: 'TournamentsList' })" title="Back to tournaments list">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            Back
          </button>
          <div style="flex: 1;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
              <div>
                <h2>{{ currentSession.name || `Tournament ${currentSession.id.slice(0, 12)}` }}</h2>
                <div v-if="gridInit" class="tournament-info">
                  <span>{{ gridInit.competitors?.length || 0 }} competitors</span>
                  <span>×</span>
                  <span>{{ gridInit.scenarios?.length || 0 }} scenarios</span>
                  <span>=</span>
                  <span>{{ gridInit.total_negotiations || 0 }} negotiations</span>
                </div>
              </div>
              <!-- Stats in the middle -->
              <div v-if="gridInit" class="header-stats">
                <span class="header-stat">
                  <span class="header-stat-value">{{ tournamentStats.completionRate }}%</span>
                  <span class="header-stat-label">Done</span>
                </span>
                <span class="header-stat">
                  <span class="header-stat-value">{{ tournamentStats.successRate }}%</span>
                  <span class="header-stat-label">Success</span>
                </span>
                <span class="header-stat">
                  <span class="header-stat-value">{{ tournamentStats.agreementRate }}%</span>
                  <span class="header-stat-label">Agreed</span>
                </span>
                <span class="header-stat">
                  <span class="header-stat-value">{{ tournamentStats.timeoutRate }}%</span>
                  <span class="header-stat-label">Timeout</span>
                </span>
                <span v-if="tournamentStats.errors > 0" class="header-stat error">
                  <span class="header-stat-value">{{ tournamentStats.errorRate }}%</span>
                  <span class="header-stat-label">Errors</span>
                </span>
                <span v-if="streamingSession" class="header-live">
                  <span class="header-live-dot"></span>
                  LIVE
                </span>
              </div>
              <!-- Progress bar on the right -->
              <div v-if="gridInit" class="header-progress">
                <div class="header-progress-bar">
                  <div class="header-progress-fill" :style="{ width: tournamentStats.completionRate + '%' }"></div>
                </div>
                <span class="header-progress-count">{{ tournamentStats.completed }}/{{ gridInit.total_negotiations || 0 }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <!-- Data viewing buttons (completed tournaments only) -->
          <button
            v-if="currentSession.status === 'completed' || currentSession.isSaved"
            class="btn btn-ghost btn-sm"
            @click="showRankingModal = true"
            title="View tournament rankings by metric"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            Rankings
          </button>
          <button
            v-if="currentSession.status === 'completed' || currentSession.isSaved"
            class="btn btn-ghost btn-sm"
            @click="showDetailsModal = true"
            title="View negotiation details"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
            </svg>
            Details
          </button>
          <button
            v-if="currentSession.status === 'completed' || currentSession.isSaved"
            class="btn btn-ghost btn-sm"
            @click="showScoresModal = true"
            title="View all scores"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M3 3v18h18"></path>
              <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"></path>
            </svg>
            All Scores
          </button>
          <button
            v-if="currentSession.status === 'running' || currentSession.status === 'completed'"
            class="btn btn-ghost btn-sm"
            @click="viewNegotiations"
            title="View all negotiations"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
            View Negotiations
            <span v-if="negotiationsCount > 0" class="count-badge-sm">{{ negotiationsCount }}</span>
          </button>
          <button
            v-if="currentSession.status === 'running'"
            class="btn btn-secondary btn-sm"
            @click="stopTournament"
            title="Stop and save tournament progress"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <rect x="6" y="6" width="12" height="12" rx="1"></rect>
            </svg>
            Stop
          </button>
          <button class="btn btn-primary btn-sm" @click="showNewTournamentModal = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            New
          </button>
        </div>
      </div>
      
      <!-- Setup Progress Bar (only shown during initialization) -->
      <div v-if="setupProgress && setupProgress.current < setupProgress.total" class="setup-progress-bar-container">
        <div class="setup-progress-header">
          <div class="spinner-sm"></div>
          <span class="setup-message">{{ setupProgress.message || 'Initializing tournament...' }}</span>
        </div>
        <div v-if="setupProgress.total > 0" class="setup-progress-bar">
          <div class="setup-progress-fill" :style="{ width: ((setupProgress.current / setupProgress.total) * 100) + '%' }"></div>
        </div>
      </div>
      
      <!-- Main Panels -->
      <div class="panels-container">
        <!-- Top Row: Grid (2/3) + Leaderboard/Config (1/3) -->
        <div class="panels-top-row">
          <!-- Grid Panel (2/3 width) -->
          <div class="panel-grid-wrapper">
            <TournamentGridPanel 
              :gridInit="gridInit"
              :cellStates="cellStates"
              :selfPlay="currentSession.config?.self_play ?? true"
              :status="currentSession.status"
              :tournamentId="tournamentId"
              :liveNegotiations="liveNegotiations"
            />
          </div>
          
          <!-- Leaderboard / Config Tabbed Panel (1/3 width) -->
          <div class="panel-scores-wrapper">
            <TournamentInfoTabbedPanel 
              :leaderboard="leaderboard"
              :config="tournamentConfig"
              :status="currentSession.status"
              :tournamentId="tournamentId"
            />
          </div>
        </div>
        
        <!-- Bottom Row: Event Log (half) + Negotiations List (half) -->
        <div class="panels-bottom-row">
          <div class="panel-event-log-wrapper">
            <TournamentTabbedPanel 
              :events="eventLog" 
              :scoreHistory="scoreHistory"
              :scenarios="tournamentScenarios"
              :status="currentSession.status"
              :tournamentId="tournamentId"
              @clearEvents="clearEventLog" 
            />
          </div>
          <div class="panel-negotiations-wrapper">
            <TournamentNegotiationsPanel 
              :tournamentId="tournamentId"
              :liveNegotiations="liveNegotiations"
              :runningNegotiations="runningNegotiations"
              :gridInit="gridInit"
              :status="currentSession.status"
            />
          </div>
        </div>
        
        <!-- Failed Negotiations Panel (only shown when there are errors) -->
        <TournamentErrorsPanel
          v-if="errorNegotiations.length > 0"
          :errors="errorNegotiations"
          :status="currentSession.status"
        />
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>Tournament not found</p>
      <button class="btn btn-secondary" @click="router.push({ name: 'TournamentsList' })">
        ← Back to List
      </button>
    </div>
    
    <!-- New Tournament Modal -->
    <Teleport to="body">
      <NewTournamentModal
        :show="showNewTournamentModal"
        @close="showNewTournamentModal = false"
        @start="onTournamentStart"
      />
    </Teleport>
    
    <!-- Ranking Modal -->
    <TournamentRankingModal
      :show="showRankingModal"
      :tournamentId="tournamentId"
      @close="showRankingModal = false"
    />
    
    <!-- Details Modal -->
    <TournamentDataModal
      :show="showDetailsModal"
      :tournamentId="tournamentId"
      title="Negotiation Details"
      dataType="details"
      :defaultColumns="['scenario', 'partners', 'step', 'time', 'broken', 'timedout', 'agreement']"
      @close="showDetailsModal = false"
    />
    
    <!-- All Scores Modal -->
    <TournamentDataModal
      :show="showScoresModal"
      :tournamentId="tournamentId"
      title="All Scores"
      dataType="all_scores"
      :defaultColumns="['strategy', 'utility', 'advantage', 'welfare', 'scenario', 'partners']"
      @close="showScoresModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTournamentsStore } from '../stores/tournaments'
import { useNegotiationsStore } from '../stores/negotiations'
import { storeToRefs } from 'pinia'
import NewTournamentModal from '../components/NewTournamentModal.vue'
import TournamentGridPanel from '../components/TournamentGridPanel.vue'
import TournamentScoresPanel from '../components/TournamentScoresPanel.vue'
import TournamentErrorsPanel from '../components/TournamentErrorsPanel.vue'
import TournamentTabbedPanel from '../components/TournamentTabbedPanel.vue'
import TournamentInfoTabbedPanel from '../components/TournamentInfoTabbedPanel.vue'
import TournamentRankingModal from '../components/TournamentRankingModal.vue'
import TournamentDataModal from '../components/TournamentDataModal.vue'
import TournamentNegotiationsPanel from '../components/TournamentNegotiationsPanel.vue'

const router = useRouter()
const route = useRoute()
const tournamentsStore = useTournamentsStore()
const negotiationsStore = useNegotiationsStore()

const {
  currentSession,
  streamingSession,
  gridInit,
  cellStates,
  leaderboard,
  progress,
  setupProgress,
  liveNegotiations,
  runningNegotiations,
  errorNegotiations,
  eventLog,
  scoreHistory,
  tournamentScenarios,
} = storeToRefs(tournamentsStore)

const showNewTournamentModal = ref(false)
const showRankingModal = ref(false)
const showDetailsModal = ref(false)
const showScoresModal = ref(false)
const loading = ref(true)
const error = ref(null)

// Get tournament ID from route
const tournamentId = computed(() => route.params.id)

// Computed property for negotiations based on status
const displayedNegotiations = computed(() => {
  if (currentSession.value?.status === 'running') {
    return liveNegotiations.value || []
  } else if (currentSession.value?.status === 'completed') {
    return currentSession.value?.negotiations || []
  }
  return []
})

// Computed property for total negotiations count
const negotiationsCount = computed(() => {
  const running = runningNegotiations.value?.size || 0
  const completed = liveNegotiations.value?.length || 0
  return running + completed
})

// Computed config with competitor/scenario names from gridInit
const tournamentConfig = computed(() => {
  if (!currentSession.value?.config) return null
  
  const config = { ...currentSession.value.config }
  
  // Add competitor/scenario names from gridInit if available
  if (gridInit.value) {
    // Map competitor names to config format
    if (gridInit.value.competitors) {
      config.competitors = gridInit.value.competitors.map(name => ({
        name,
        type_name: name
      }))
    }
    
    // Map scenario names to config format
    if (gridInit.value.scenarios) {
      config.scenarios = gridInit.value.scenarios.map(name => ({
        name,
        path: name
      }))
    }
    
    // Add storage path from gridInit
    if (gridInit.value.storage_path) {
      config.storage_path = gridInit.value.storage_path
    }
  }
  
  return config
})

// Computed statistics from cellStates and liveNegotiations
const tournamentStats = computed(() => {
  // Get total from progress or gridInit
  const totalFromProgress = progress.value?.total || gridInit.value?.total_negotiations || 0
  
  // ALWAYS aggregate from cellStates first - this has the most accurate agreement/timeout/error counts
  // The progress event only has total/completed, not the detailed breakdown
  if (cellStates.value && Object.keys(cellStates.value).length > 0) {
    let totalNegs = 0
    let completedNegs = 0
    let agreementsCount = 0
    let timeoutsCount = 0
    let errorsCount = 0
    
    Object.values(cellStates.value).forEach(cell => {
      totalNegs += cell.total || 0
      completedNegs += cell.completed || 0
      agreementsCount += cell.agreements || 0
      timeoutsCount += cell.timeouts || 0
      errorsCount += cell.errors || 0
    })
    
    // Use progress total if available (more accurate), otherwise use aggregated total
    const total = totalFromProgress || totalNegs
    
    if (total === 0) {
      return {
        total: 0,
        agreements: 0,
        timeouts: 0,
        errors: 0,
        ended: 0,
        completed: 0,
        agreementRate: 0,
        timeoutRate: 0,
        errorRate: 0,
        endedRate: 0,
        successRate: 0,
        completionRate: 0
      }
    }
    
    const successfulNegs = completedNegs - errorsCount
    
    return {
      total,
      agreements: agreementsCount,
      timeouts: timeoutsCount,
      errors: errorsCount,
      ended: 0,  // Not tracked at cell level
      completed: completedNegs,
      agreementRate: completedNegs > 0 ? (agreementsCount / completedNegs * 100).toFixed(1) : 0,
      timeoutRate: completedNegs > 0 ? (timeoutsCount / completedNegs * 100).toFixed(1) : 0,
      errorRate: completedNegs > 0 ? (errorsCount / completedNegs * 100).toFixed(1) : 0,
      endedRate: 0,
      successRate: completedNegs > 0 ? (successfulNegs / completedNegs * 100).toFixed(1) : 0,
      completionRate: total > 0 ? (completedNegs / total * 100).toFixed(1) : 0
    }
  }
  
  // Fallback to liveNegotiations for completed tournaments (when cellStates is empty)
  const total = liveNegotiations.value?.length || 0
  if (total === 0) {
    return {
      total: totalFromProgress,
      agreements: 0,
      timeouts: 0,
      errors: 0,
      ended: 0,
      completed: 0,
      agreementRate: 0,
      timeoutRate: 0,
      errorRate: 0,
      endedRate: 0,
      successRate: 0,
      completionRate: 0
    }
  }

  let agreements = 0
  let timeouts = 0
  let errors = 0
  let ended = 0

  liveNegotiations.value.forEach(neg => {
    if (neg.has_agreement || neg.end_reason === 'agreement') {
      agreements++
    } else if (neg.end_reason === 'timeout') {
      timeouts++
    } else if (neg.has_error || neg.end_reason === 'error' || neg.end_reason === 'broken') {
      errors++
    } else if (neg.end_reason === 'ended') {
      ended++
    }
  })

  const expectedTotal = totalFromProgress || total
  const successfulNegs = total - errors

  return {
    total: expectedTotal,
    agreements,
    timeouts,
    errors,
    ended,
    completed: total,
    agreementRate: (agreements / total * 100).toFixed(1),
    timeoutRate: (timeouts / total * 100).toFixed(1),
    errorRate: (errors / total * 100).toFixed(1),
    endedRate: (ended / total * 100).toFixed(1),
    successRate: (successfulNegs / total * 100).toFixed(1),
    completionRate: expectedTotal > 0 ? (total / expectedTotal * 100).toFixed(1) : 0
  }
})

// Navigation to negotiations list
function viewNegotiations() {
  if (currentSession.value?.id) {
    router.push({ 
      name: 'TournamentNegotiationsList', 
      params: { tournamentId: currentSession.value.id }
    })
  }
}

// Debug: Watch setupProgress changes
watch(setupProgress, (newVal) => {
  console.log('[SingleTournamentView] setupProgress changed:', newVal)
}, { deep: true })

onMounted(async () => {
  const tournamentId = route.params.id
  
  if (!tournamentId) {
    error.value = 'No tournament ID provided'
    loading.value = false
    return
  }
  
  try {
    // First check running/completed sessions
    await tournamentsStore.loadSessions()
    const session = tournamentsStore.sessions.find(s => s.id === tournamentId)
    
    if (session) {
      // Found in sessions list
      tournamentsStore.selectSession(session)
      
      if (session.status === 'running' || session.status === 'pending') {
        // Start polling for running sessions
        tournamentsStore.startPolling(tournamentId, session.config || {})
      } else if (session.status === 'completed' || session.status === 'failed') {
        // Try to load saved data for completed/failed sessions
        const savedData = await tournamentsStore.loadSavedTournament(tournamentId)
        
        if (savedData) {
          // Populate streaming state with saved data
          gridInit.value = savedData.gridInit
          cellStates.value = savedData.cellStates || {}
          leaderboard.value = savedData.leaderboard || []
          
          // Update session with config if available
          if (savedData.config) {
            currentSession.value = {
              ...currentSession.value,
              config: savedData.config
            }
          }
          
          // Load negotiations list for the panel
          await tournamentsStore.loadTournamentNegotiations(tournamentId)
          
          // Load scenarios summary for the opposition vs outcomes plot
          await tournamentsStore.loadScenariosSummary(tournamentId)
        }
      }
      
      loading.value = false
    } else {
      // Not in sessions list - try loading from saved
      const savedData = await tournamentsStore.loadSavedTournament(tournamentId)
      
      if (savedData) {
        // Create a session-like object and select it
        const savedSession = {
          id: savedData.id,
          name: savedData.name || savedData.id,
          status: 'completed',
          n_competitors: savedData.n_competitors,
          n_scenarios: savedData.n_scenarios,
          n_negotiations: savedData.n_negotiations,
          n_agreements: savedData.n_agreements,
          agreement_rate: savedData.agreement_rate,
          negotiations: savedData.negotiations || [],
          config: savedData.config || null,
          isSaved: true,
        }
        
        tournamentsStore.selectSession(savedSession)
        
        // Populate the streaming state with saved data
        gridInit.value = savedData.gridInit
        cellStates.value = savedData.cellStates || {}
        leaderboard.value = savedData.leaderboard || []
        
        // Load negotiations list for the panel
        await tournamentsStore.loadTournamentNegotiations(tournamentId)
        
        // Load event log if available
        await tournamentsStore.loadEventLog(tournamentId)
        
        // Load scenarios summary for the opposition vs outcomes plot
        await tournamentsStore.loadScenariosSummary(tournamentId)
        
        loading.value = false
      } else {
        // Not found anywhere
        error.value = 'Tournament not found'
        loading.value = false
      }
    }
  } catch (err) {
    console.error('Error loading tournament:', err)
    error.value = 'Failed to load tournament'
    loading.value = false
  }
})

onUnmounted(() => {
  tournamentsStore.stopPolling()
})

function onTournamentStart(data) {
  showNewTournamentModal.value = false
  
  if (data.session_id) {
    // Store scenarios if provided
    if (data.scenarios) {
      tournamentsStore.tournamentScenarios = data.scenarios
    }
    router.push({ name: 'SingleTournament', params: { id: data.session_id } })
  }
}

async function stopTournament() {
  if (!currentSession.value) return
  if (confirm('Stop this tournament and save progress? You can continue it later from the tournaments list.')) {
    await tournamentsStore.cancelSession(currentSession.value.id)
    router.push({ name: 'TournamentsList' })
  }
}

// Keep cancelTournament as alias for backwards compatibility
const cancelTournament = stopTournament

function clearEventLog() {
  tournamentsStore.clearEventLog()
}

function handleViewNegotiation(neg) {
  // For running tournaments, click on a negotiation to view its live data
  // The negotiation object from liveNegotiations already has the data we need
  if (!neg || !neg.offers || neg.offers.length === 0) {
    console.warn('Negotiation has no offers yet')
    return
  }
  
  // Create a minimal negotiation session to load in the viewer
  // The negotiations store expects this format
  const sessionData = {
    id: `tournament-${currentSession.value.id}-neg-${neg.index || 0}`,
    scenario: neg.scenario_path || neg.scenario,
    issue_names: neg.issue_names || [],
    offers: neg.offers || [],
    agreement: neg.agreement || null,
    utilities: neg.utilities || {},
    partners: neg.partners || [],
    n_steps: neg.n_steps || neg.offers?.length || 0,
    end_reason: neg.end_reason || 'unknown',
    fromTournament: true,
    tournamentId: currentSession.value.id,
  }
  
  // Load this into the negotiations store
  negotiationsStore.loadTournamentNegotiation(sessionData)
  
  // Navigate to the negotiation viewer
  router.push({ name: 'SingleNegotiation', params: { id: sessionData.id } })
}

async function handleLoadTrace(tournamentId, negIndex) {
  // For saved tournaments, load the full negotiation trace from the server
  try {
    loading.value = true
    
    // Fetch full negotiation data from the API
    const response = await fetch(`/api/tournament/saved/${tournamentId}/negotiation/${negIndex}/full`)
    if (!response.ok) {
      throw new Error(`Failed to load negotiation: ${response.statusText}`)
    }
    
    const negData = await response.json()
    
    // Create session data for the negotiations store
    const sessionData = {
      id: `tournament-${tournamentId}-neg-${negIndex}`,
      scenario: negData.scenario_path || negData.scenario,
      issue_names: negData.issue_names || [],
      offers: negData.history || negData.offers || [],
      agreement: negData.agreement || null,
      utilities: negData.final_utilities || negData.utilities || {},
      partners: negData.partners || negData.negotiators || [],
      n_steps: negData.n_steps || negData.history?.length || 0,
      end_reason: negData.end_reason || 'unknown',
      outcome_space_data: negData.outcome_space_data || null,
      fromTournament: true,
      tournamentId: tournamentId,
      tournamentNegIndex: negIndex,
    }
    
    // Load into negotiations store
    negotiationsStore.loadTournamentNegotiation(sessionData)
    
    // Navigate to negotiation viewer
    router.push({ name: 'SingleNegotiation', params: { id: sessionData.id } })
  } catch (err) {
    console.error('Failed to load trace:', err)
    error.value = `Failed to load negotiation: ${err.message}`
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.single-tournament-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--bg-primary);
  padding: 16px;
  overflow: hidden;
}

.tournament-viewer {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
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

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
}

.viewer-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.tournament-info {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Integrated header stats - horizontal row in middle */
.header-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  justify-content: center;
}

.header-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.header-stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.header-stat-label {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.header-stat.error .header-stat-value {
  color: var(--error-color, rgb(239, 68, 68));
}

.header-live {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  color: rgb(239, 68, 68);
}

.header-live-dot {
  width: 8px;
  height: 8px;
  background: rgb(239, 68, 68);
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.header-progress-bar {
  width: 100px;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.header-progress-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
}

.header-progress-count {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 60px;
  text-align: right;
}

/* Setup progress bar (shown during initialization) */
.setup-progress-bar-container {
  padding: 8px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setup-progress-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.setup-message {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}

.setup-progress-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.setup-progress-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
  border-radius: 3px;
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.panels-container {
  flex: 1;
  overflow: hidden; /* Don't scroll the container, let children scroll */
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0; /* Allow flex shrinking */
}

.panels-top-row {
  display: flex;
  gap: 12px;
  flex: 0 0 auto; /* Don't grow, shrink to content */
  min-height: 200px; /* Minimum usable height */
  max-height: 40vh; /* Cap at 40% of viewport height */
}

.panel-grid-wrapper {
  flex: 2;
  min-width: 0;
  min-height: 0;
  overflow: hidden; /* Ensure child handles scrolling */
}

.panel-scores-wrapper {
  flex: 1;
  min-width: 300px;
  max-width: 400px;
  min-height: 0;
  overflow: hidden;
}

.panels-bottom-row {
  display: flex;
  gap: 12px;
  flex: 1 1 auto;
  min-height: 300px;
  overflow: hidden;
}

.panel-event-log-wrapper,
.panel-negotiations-wrapper {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Force both panels to fill their wrappers */
/* Use :deep() to pierce scoped CSS into child components */
.panel-event-log-wrapper > :deep(*),
.panel-negotiations-wrapper > :deep(*) {
  flex: 1 1 auto;
  height: 100%;
  min-height: 0;
}

@media (max-width: 1200px) {
  .panels-top-row {
    flex-direction: column;
  }
  
  .panel-scores-wrapper {
    max-width: none;
  }
  
  .panels-bottom-row {
    flex-direction: column;
  }
}

/* Buttons */
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

/* Negotiations Section */
.negotiations-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-top: 16px;
}

.btn-negotiations {
  padding: 12px 20px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.btn-negotiations:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.count-badge {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.live-indicator-small {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 6px 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.status-dot-small {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: rgb(16, 185, 129);
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

/* Header Progress Bar */
.header-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 200px;
}

.header-progress-text {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.progress-percentage {
  font-weight: 600;
  color: var(--primary-color);
  font-size: 14px;
}

.progress-count {
  color: var(--text-secondary);
  font-size: 12px;
}

.header-progress-bar {
  width: 100%;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.header-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-hover));
  border-radius: 3px;
  transition: width 0.3s ease;
}

.count-badge-sm {
  background: rgba(59, 130, 246, 0.15);
  color: var(--primary-color);
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  margin-left: 4px;
}

.error-value {
  background: rgb(239, 68, 68);
  color: white;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}
</style>
