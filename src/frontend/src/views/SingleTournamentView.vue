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
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">
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
              <!-- Progress bar in header -->
              <div v-if="gridInit" class="header-progress">
                <div class="header-progress-text">
                  <span class="progress-percentage">{{ tournamentStats.completionRate }}%</span>
                  <span class="progress-count">{{ tournamentStats.completed }}/{{ gridInit.total_negotiations || 0 }}</span>
                </div>
                <div class="header-progress-bar">
                  <div class="header-progress-fill" :style="{ width: tournamentStats.completionRate + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="header-actions">
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
      
      <!-- Stats Bar (comprehensive statistics) -->
      <div v-if="currentSession.status === 'running' || currentSession.status === 'completed'" class="stats-bar">
        <!-- Setup Progress (before grid_init) -->
        <div v-if="setupProgress && !gridInit" class="setup-progress">
          <div class="setup-progress-header">
            <div class="spinner-sm"></div>
            <span class="setup-message">{{ setupProgress.message || 'Initializing tournament...' }}</span>
          </div>
          <div v-if="setupProgress.total > 0" class="setup-progress-bar">
            <div class="setup-progress-fill" :style="{ width: ((setupProgress.current / setupProgress.total) * 100) + '%' }"></div>
          </div>
        </div>
        
        <!-- Comprehensive Stats (after grid_init) -->
        <div v-else class="stats-inline">
          <span class="stat-inline">
            <span class="stat-label">Completion:</span>
            <span class="stat-value">{{ tournamentStats.completionRate }}%</span>
          </span>
          <span class="stat-inline">
            <span class="stat-label">Success:</span>
            <span class="stat-value">{{ tournamentStats.successRate }}%</span>
          </span>
          <span class="stat-inline">
            <span class="stat-label">Agreement:</span>
            <span class="stat-value">{{ tournamentStats.agreementRate }}%</span>
          </span>
          <span class="stat-inline">
            <span class="stat-label">Timeout:</span>
            <span class="stat-value">{{ tournamentStats.timeoutRate }}%</span>
          </span>
          <span class="stat-inline" v-if="tournamentStats.errors > 0">
            <span class="stat-label">Errors:</span>
            <span class="stat-value error-value">{{ tournamentStats.errorRate }}%</span>
          </span>
          <span v-if="streamingSession" class="stat-inline live-indicator">
            <span class="status-dot"></span>
            LIVE
          </span>
        </div>
      </div>
      
      <!-- Main Panels -->
      <div class="panels-container">
        <!-- Top Row: Grid (2/3) + Leaderboard (1/3) -->
        <div class="panels-top-row">
          <!-- Grid Panel (2/3 width) -->
          <div class="panel-grid-wrapper">
            <TournamentGridPanel 
              :gridInit="gridInit"
              :cellStates="cellStates"
              :selfPlay="currentSession.config?.self_play ?? true"
              :status="currentSession.status"
              :tournamentId="tournamentId"
            />
          </div>
          
          <!-- Scores Panel (1/3 width) -->
          <div class="panel-scores-wrapper">
            <TournamentScoresPanel 
              :leaderboard="leaderboard"
              :status="currentSession.status"
            />
          </div>
        </div>
        
        <!-- Bottom Row: Errors Panel -->
        <TournamentErrorsPanel
          v-if="currentSession.status === 'running' || currentSession.status === 'completed'"
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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTournamentsStore } from '../stores/tournaments'
import { useNegotiationsStore } from '../stores/negotiations'
import { storeToRefs } from 'pinia'
import NewTournamentModal from '../components/NewTournamentModal.vue'
import TournamentGridPanel from '../components/TournamentGridPanel.vue'
import TournamentScoresPanel from '../components/TournamentScoresPanel.vue'
import TournamentErrorsPanel from '../components/TournamentErrorsPanel.vue'

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
} = storeToRefs(tournamentsStore)

const showNewTournamentModal = ref(false)
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

// Computed statistics from cellStates and liveNegotiations
const tournamentStats = computed(() => {
  // Use progress data if available (updated in real-time)
  if (progress.value) {
    const total = progress.value.total || 0
    const completed = progress.value.completed || 0
    const agreements = progress.value.agreements || 0
    const timeouts = progress.value.timeouts || 0
    const errors = progress.value.errors || 0
    const ended = progress.value.ended || 0
    
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
    
    const successfulNegs = completed - errors
    
    return {
      total,
      agreements,
      timeouts,
      errors,
      ended,
      completed,
      agreementRate: (agreements / completed * 100).toFixed(1),
      timeoutRate: (timeouts / completed * 100).toFixed(1),
      errorRate: (errors / completed * 100).toFixed(1),
      endedRate: (ended / completed * 100).toFixed(1),
      successRate: completed > 0 ? (successfulNegs / completed * 100).toFixed(1) : 0,
      completionRate: (completed / total * 100).toFixed(1)
    }
  }
  
  // Fallback to cellStates for saved tournaments (aggregate cell-level stats)
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
    
    if (totalNegs === 0) {
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
      total: totalNegs,
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
      completionRate: (completedNegs / totalNegs * 100).toFixed(1)
    }
  }
  
  // Last fallback: liveNegotiations for completed tournaments
  const total = liveNegotiations.value?.length || 0
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

  const expectedTotal = gridInit.value?.total_negotiations || total
  const successfulNegs = total - errors

  return {
    total,
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
    completionRate: (total / expectedTotal * 100).toFixed(1)
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
        // Start streaming for running sessions
        tournamentsStore.startStreaming(tournamentId)
      } else if (session.status === 'completed' || session.status === 'failed') {
        // Try to load saved data for completed/failed sessions
        const savedData = await tournamentsStore.loadSavedTournament(tournamentId)
        
        if (savedData) {
          // Populate streaming state with saved data
          gridInit.value = savedData.gridInit
          cellStates.value = savedData.cellStates || {}
          leaderboard.value = savedData.leaderboard || []
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
          isSaved: true,
        }
        
        tournamentsStore.selectSession(savedSession)
        
        // Populate the streaming state with saved data
        gridInit.value = savedData.gridInit
        cellStates.value = savedData.cellStates || {}
        leaderboard.value = savedData.leaderboard || []
        
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
  tournamentsStore.stopStreaming()
})

function onTournamentStart(data) {
  showNewTournamentModal.value = false
  
  if (data.session_id) {
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

.stats-bar {
  padding: 8px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 12px;
}

.stats-inline {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
  margin-bottom: 8px;
}

.stat-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}

.live-indicator {
  color: rgb(239, 68, 68);
  font-weight: 700;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
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

.progress-bar-inline {
  width: 100%;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
}

.setup-progress {
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
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panels-top-row {
  display: flex;
  gap: 12px;
  min-height: 0;
}

.panel-grid-wrapper {
  flex: 2;
  min-width: 0;
}

.panel-scores-wrapper {
  flex: 1;
  min-width: 300px;
  max-width: 400px;
}

@media (max-width: 1200px) {
  .panels-top-row {
    flex-direction: column;
  }
  
  .panel-scores-wrapper {
    max-width: none;
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
  color: var(--color-error);
  font-weight: 600;
}
</style>
