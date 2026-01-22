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
        <div style="display: flex; align-items: center; gap: 12px;">
          <button class="btn btn-ghost btn-sm" @click="router.push({ name: 'TournamentsList' })" title="Back to tournaments list">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            Back
          </button>
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
        </div>
        <div class="header-actions">
          <button
            v-if="currentSession.status === 'running'"
            class="btn btn-secondary btn-sm"
            @click="cancelTournament"
          >
            Cancel
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
      
      <!-- Stats Bar (single line with inline stats) -->
      <div v-if="currentSession.status === 'running' || currentSession.status === 'completed'" class="stats-bar">
        <div class="stats-inline">
          <span class="stat-inline">
            <span class="stat-label">Negotiations:</span>
            <span class="stat-value">
              {{ currentSession.status === 'completed' 
                ? (currentSession.n_negotiations || 0) 
                : `${progress?.completed || 0}/${progress?.total || 0}` 
              }}
            </span>
          </span>
          <span class="stat-inline" v-if="currentSession.status === 'completed' && currentSession.n_agreements !== undefined">
            <span class="stat-label">Agreements:</span>
            <span class="stat-value">
              {{ currentSession.n_agreements || 0 }} ({{ Math.round((currentSession.agreement_rate || 0) * 100) }}%)
            </span>
          </span>
          <span class="stat-inline" v-if="currentSession.status === 'running' && progress">
            <span class="stat-label">Progress:</span>
            <span class="stat-value">{{ Math.round(progress.percent || 0) }}%</span>
          </span>
          <span v-if="streamingSession" class="stat-inline live-indicator">
            <span class="status-dot"></span>
            LIVE
          </span>
        </div>
        <!-- Progress bar for running tournaments -->
        <div v-if="currentSession.status === 'running' && progress" class="progress-bar-inline">
          <div class="progress-fill" :style="{ width: progress.percent + '%' }"></div>
        </div>
      </div>
      
      <!-- Main Panels (always visible, stacked vertically) -->
      <div class="panels-container">
        <!-- Grid Panel -->
        <TournamentGridPanel 
          :gridInit="gridInit"
          :cellStates="cellStates"
          :selfPlay="currentSession.self_play || false"
        />
        
        <!-- Scores Panel -->
        <TournamentScoresPanel 
          :leaderboard="leaderboard"
          :status="currentSession.status"
        />
        
        <!-- Negotiations Panel -->
        <TournamentNegotiationsPanel 
          :negotiations="displayedNegotiations"
          :status="currentSession.status"
          :tournamentId="currentSession.id"
          @view-negotiation="handleViewNegotiation"
          @load-trace="handleLoadTrace"
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
  liveNegotiations,
} = storeToRefs(tournamentsStore)

const showNewTournamentModal = ref(false)
const loading = ref(true)
const error = ref(null)

// Computed property for negotiations based on status
const displayedNegotiations = computed(() => {
  if (currentSession.value?.status === 'running') {
    return liveNegotiations.value || []
  } else if (currentSession.value?.status === 'completed') {
    return currentSession.value?.negotiations || []
  }
  return []
})

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

async function cancelTournament() {
  if (!currentSession.value) return
  if (confirm('Are you sure you want to cancel this tournament?')) {
    await tournamentsStore.cancelSession(currentSession.value.id)
    router.push({ name: 'TournamentsList' })
  }
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

.panels-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
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
</style>
