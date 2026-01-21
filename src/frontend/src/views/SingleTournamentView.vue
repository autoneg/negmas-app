<template>
  <div class="single-tournament-view">
    <!-- Loading State -->
    <div v-if="loading" class="empty-state">
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
      <!-- Header -->
      <div class="viewer-header">
        <div style="display: flex; align-items: center; gap: 12px;">
          <button class="btn btn-ghost btn-sm" @click="router.push({ name: 'TournamentsList' })" title="Back to tournaments list">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            <span>Back</span>
          </button>
          <div>
            <h2>Tournament {{ currentSession.id.slice(0, 12) }}</h2>
            <div v-if="gridInit" class="tournament-info">
              <span>{{ gridInit.competitors.length }} competitors</span>
              <span>×</span>
              <span>{{ gridInit.scenarios.length }} scenarios</span>
              <span>=</span>
              <span>{{ gridInit.total_negotiations }} negotiations</span>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <button
            v-if="currentSession.status === 'running' && !streamingSession"
            class="btn-primary btn-sm"
            @click="watchLive"
          >
            Watch Live
          </button>
          <button
            v-if="streamingSession"
            class="btn-secondary btn-sm"
            @click="stopWatching"
          >
            Stop Watching
          </button>
          <button
            v-if="currentSession.status === 'running'"
            class="btn-secondary btn-sm"
            @click="cancelTournament"
          >
            Cancel
          </button>
          <button class="btn btn-primary btn-sm" @click="showNewTournamentModal = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            <span>New</span>
          </button>
        </div>
      </div>
      
      <!-- Live Status Bar -->
      <div v-if="streamingSession && progress" class="status-bar live">
        <span class="status-indicator">● LIVE</span>
        <span>{{ progress.completed }}/{{ progress.total }} completed</span>
        <span v-if="progress.current_scenario">{{ progress.current_scenario }}</span>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress.percent + '%' }"></div>
        </div>
      </div>
      
      <!-- Tabs -->
      <div class="tabs">
        <button
          class="tab"
          :class="{ active: activeTab === 'grid' }"
          @click="activeTab = 'grid'"
        >
          Grid
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'leaderboard' }"
          @click="activeTab = 'leaderboard'"
        >
          Leaderboard
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'analytics' }"
          @click="activeTab = 'analytics'"
        >
          Analytics
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'config' }"
          @click="activeTab = 'config'"
        >
          Configuration
        </button>
      </div>
      
      <!-- Tab Content -->
      <div class="tab-content">
        <!-- Grid Tab -->
        <div v-if="activeTab === 'grid'" class="grid-tab">
          <div v-if="!gridInit" class="empty-state-sm">
            Loading grid...
          </div>
          <div v-else class="tournament-grid">
            <div class="grid-header">
              <div class="grid-corner"></div>
              <div
                v-for="scenario in gridInit.scenarios"
                :key="scenario"
                class="grid-header-cell"
              >
                {{ scenario.split('/').pop() }}
              </div>
            </div>
            <div
              v-for="competitor in gridInit.competitors"
              :key="competitor"
              class="grid-row"
            >
              <div class="grid-row-header">{{ competitor }}</div>
              <div
                v-for="scenario in gridInit.scenarios"
                :key="scenario"
                class="grid-cell"
                :class="getCellClass(competitor, scenario)"
              >
                {{ getCellContent(competitor, scenario) }}
              </div>
            </div>
          </div>
        </div>
        
        <!-- Leaderboard Tab -->
        <div v-if="activeTab === 'leaderboard'" class="leaderboard-tab">
          <div v-if="leaderboard.length === 0" class="empty-state-sm">
            No leaderboard data yet
          </div>
          <div v-else class="leaderboard-table-container">
            <table class="leaderboard-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Competitor</th>
                  <th>Score</th>
                  <th>Wins</th>
                  <th>Agreements</th>
                  <th>Avg Utility</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(entry, idx) in leaderboard" :key="entry.competitor">
                  <td class="rank-cell">
                    <span v-if="idx === 0" class="rank-medal">🥇</span>
                    <span v-else-if="idx === 1" class="rank-medal">🥈</span>
                    <span v-else-if="idx === 2" class="rank-medal">🥉</span>
                    <span v-else>{{ idx + 1 }}</span>
                  </td>
                  <td>{{ entry.competitor }}</td>
                  <td>{{ entry.score?.toFixed(2) || 'N/A' }}</td>
                  <td>{{ entry.wins }}</td>
                  <td>{{ entry.agreements }}/{{ entry.total }}</td>
                  <td>{{ entry.avg_utility?.toFixed(3) || 'N/A' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- Analytics Tab -->
        <div v-if="activeTab === 'analytics'" class="analytics-tab">
          <div class="empty-state-sm">
            Analytics charts coming soon
          </div>
        </div>
        
        <!-- Config Tab -->
        <div v-if="activeTab === 'config'" class="config-tab">
          <div v-if="!gridInit" class="empty-state-sm">
            Loading configuration...
          </div>
          <div v-else class="config-grid">
            <div class="config-item">
              <label>Competitors:</label>
              <span>{{ gridInit.competitors.length }}</span>
            </div>
            <div class="config-item">
              <label>Scenarios:</label>
              <span>{{ gridInit.scenarios.length }}</span>
            </div>
            <div class="config-item">
              <label>Repetitions:</label>
              <span>{{ gridInit.n_repetitions }}</span>
            </div>
            <div class="config-item">
              <label>Rotate Utility Functions:</label>
              <span>{{ gridInit.rotate_ufuns ? 'Yes' : 'No' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>Tournament not found</p>
      <button class="btn btn-secondary" @click="router.push({ name: 'TournamentsList' })">
        ← Back to List
      </button>
    </div>
    
    <!-- New Tournament Modal (teleported to body) -->
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTournamentsStore } from '../stores/tournaments'
import { storeToRefs } from 'pinia'
import NewTournamentModal from '../components/NewTournamentModal.vue'

const router = useRouter()
const route = useRoute()
const tournamentsStore = useTournamentsStore()
const {
  currentSession,
  streamingSession,
  gridInit,
  cellStates,
  leaderboard,
  progress,
  tournamentComplete,
} = storeToRefs(tournamentsStore)

const showNewTournamentModal = ref(false)
const loading = ref(true)
const error = ref(null)
const activeTab = ref('grid')

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
  // Close modal
  showNewTournamentModal.value = false
  
  // Navigate to the new tournament
  if (data.session_id) {
    router.push({ name: 'SingleTournament', params: { id: data.session_id } })
  }
}

function watchLive() {
  if (!currentSession.value) return
  tournamentsStore.startStreaming(currentSession.value.id)
}

function stopWatching() {
  tournamentsStore.stopStreaming()
}

async function cancelTournament() {
  if (!currentSession.value) return
  if (confirm('Are you sure you want to cancel this tournament?')) {
    await tournamentsStore.cancelSession(currentSession.value.id)
    router.push({ name: 'TournamentsList' })
  }
}

function getCellClass(competitor, scenario) {
  const key = `${competitor}::${scenario}`
  const state = cellStates.value[key]
  if (!state) return 'pending'
  return state.status || 'pending'
}

function getCellContent(competitor, scenario) {
  const key = `${competitor}::${scenario}`
  const state = cellStates.value[key]
  if (!state) return '⋯'
  
  if (state.status === 'running') return '⟳'
  if (state.status === 'pending') return '⋯'
  if (state.status === 'failed') return '✗'
  
  // Completed - show utility
  if (state.utility !== undefined) {
    return state.utility.toFixed(2)
  }
  
  return '✓'
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
  height: 100%;
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

.empty-state-sm {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.85rem;
  padding: 24px;
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
  font-size: 1.2rem;
}

.tournament-info {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 0.85rem;
}

.status-bar.live {
  border-color: rgb(239, 68, 68);
  background: rgba(239, 68, 68, 0.05);
}

.status-indicator {
  color: rgb(239, 68, 68);
  font-weight: 600;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
}

.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid var(--border-color);
  margin-bottom: 12px;
}

.tab {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s;
  margin-bottom: -2px;
}

.tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.tab-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.tournament-grid {
  display: inline-block;
  min-width: 100%;
}

.grid-header {
  display: flex;
  position: sticky;
  top: 0;
  background: var(--bg-primary);
  z-index: 10;
}

.grid-corner {
  width: 150px;
  min-width: 150px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.grid-header-cell {
  width: 80px;
  min-width: 80px;
  padding: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  font-size: 0.75rem;
  font-weight: 600;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.grid-row {
  display: flex;
}

.grid-row-header {
  width: 150px;
  min-width: 150px;
  padding: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  font-size: 0.85rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  position: sticky;
  left: 0;
  z-index: 5;
}

.grid-cell {
  width: 80px;
  min-width: 80px;
  padding: 8px;
  border: 1px solid var(--border-color);
  text-align: center;
  font-size: 0.8rem;
  font-family: monospace;
}

.grid-cell.pending {
  background: var(--bg-primary);
  color: var(--text-secondary);
}

.grid-cell.running {
  background: rgba(59, 130, 246, 0.1);
  color: rgb(59, 130, 246);
}

.grid-cell.completed {
  background: rgba(16, 185, 129, 0.1);
  color: var(--text-primary);
}

.grid-cell.failed {
  background: rgba(239, 68, 68, 0.1);
  color: rgb(239, 68, 68);
}

.leaderboard-table-container {
  overflow: auto;
}

.leaderboard-table {
  width: 100%;
  border-collapse: collapse;
}

.leaderboard-table th,
.leaderboard-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.leaderboard-table th {
  background: var(--bg-secondary);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 10;
}

.leaderboard-table tbody tr:hover {
  background: var(--bg-hover);
}

.rank-cell {
  text-align: center;
  font-weight: 600;
}

.rank-medal {
  font-size: 1.2rem;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.config-item label {
  font-weight: 600;
  color: var(--text-secondary);
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
