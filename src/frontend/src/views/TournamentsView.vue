<template>
  <div class="tournaments-view">
    <!-- Sessions List Sidebar -->
    <div class="sessions-sidebar">
      <div class="sidebar-header">
        <h3>Tournaments</h3>
        <button class="btn-icon" @click="loadData" :disabled="loading" title="Refresh">
          <span v-if="loading">⟳</span>
          <span v-else>↻</span>
        </button>
      </div>
      
      <button class="btn-primary btn-block" @click="showNewTournamentModal = true">
        + New Tournament
      </button>
      
      <!-- Running Tournaments -->
      <div v-if="runningSessions.length > 0" class="session-group">
        <h4>Running ({{ runningSessions.length }})</h4>
        <div class="session-list">
          <div
            v-for="session in runningSessions"
            :key="session.id"
            class="session-item running"
            :class="{ active: currentSession?.id === session.id }"
            @click="selectAndViewSession(session)"
          >
            <div class="session-name">Tournament {{ session.id.slice(0, 8) }}</div>
            <div class="session-meta">
              <span class="badge badge-running">Running</span>
              <span v-if="session.completed !== undefined" class="session-progress">
                {{ session.completed }}/{{ session.total }}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Completed Tournaments -->
      <div v-if="completedSessions.length > 0" class="session-group">
        <h4>Completed ({{ completedSessions.length }})</h4>
        <div class="session-list">
          <div
            v-for="session in completedSessions"
            :key="session.id"
            class="session-item completed"
            :class="{ active: currentSession?.id === session.id }"
            @click="selectAndViewSession(session)"
          >
            <div class="session-name">Tournament {{ session.id.slice(0, 8) }}</div>
            <div class="session-meta">
              <span class="badge badge-completed">Completed</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Failed Tournaments -->
      <div v-if="failedSessions.length > 0" class="session-group">
        <h4>Failed ({{ failedSessions.length }})</h4>
        <div class="session-list">
          <div
            v-for="session in failedSessions"
            :key="session.id"
            class="session-item failed"
            :class="{ active: currentSession?.id === session.id }"
            @click="selectAndViewSession(session)"
          >
            <div class="session-name">Tournament {{ session.id.slice(0, 8) }}</div>
            <div class="session-meta">
              <span class="badge badge-failed">Failed</span>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="sessions.length === 0 && !loading" class="empty-state-sm">
        No tournaments yet
      </div>
    </div>
    
    <!-- Main Viewer Panel -->
    <div class="viewer-panel">
      <div v-if="!currentSession" class="empty-state">
        <p>Select a tournament to view details</p>
        <p class="empty-hint">or start a new tournament</p>
      </div>
      
      <div v-else class="tournament-viewer">
        <!-- Header -->
        <div class="viewer-header">
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
                    <td class="competitor-cell">{{ entry.competitor }}</td>
                    <td class="score-cell">{{ entry.score?.toFixed(3) || 'N/A' }}</td>
                    <td>{{ entry.wins || 0 }}</td>
                    <td>{{ entry.agreements || 0 }}</td>
                    <td>{{ entry.avg_utility?.toFixed(3) || 'N/A' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <!-- Analytics Tab -->
          <div v-if="activeTab === 'analytics'" class="analytics-tab">
            <div v-if="leaderboard.length === 0" class="empty-state-sm">
              No analytics data yet
            </div>
            <div v-else>
              <div class="chart-section">
                <h4>Competitor Scores</h4>
                <div class="chart-container">
                  <canvas ref="scoresChart"></canvas>
                </div>
              </div>
              <div class="chart-section">
                <h4>Agreement Rates</h4>
                <div class="chart-container">
                  <canvas ref="agreementsChart"></canvas>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Configuration Tab -->
          <div v-if="activeTab === 'config'" class="config-tab">
            <div class="config-section">
              <h4>Tournament Configuration</h4>
              <p class="empty-hint">Configuration details would be displayed here</p>
              <div v-if="gridInit" class="config-details">
                <div class="config-item">
                  <label>Competitors:</label>
                  <span>{{ gridInit.competitors.length }}</span>
                </div>
                <div class="config-item">
                  <label>Scenarios:</label>
                  <span>{{ gridInit.scenarios.length }}</span>
                </div>
                <div class="config-item">
                  <label>Total Negotiations:</label>
                  <span>{{ gridInit.total_negotiations }}</span>
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
      </div>
    </div>
    
    <!-- New Tournament Modal (teleported to body to avoid overflow clipping) -->
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
import { ref, onMounted, watch, nextTick, onUnmounted, computed } from 'vue'
import { useTournamentsStore } from '../stores/tournaments'
import { storeToRefs } from 'pinia'
import Chart from 'chart.js/auto'
import NewTournamentModal from '../components/NewTournamentModal.vue'

const tournamentsStore = useTournamentsStore()
const {
  sessions,
  currentSession,
  loading,
  streamingSession,
  gridInit,
  cellStates,
  leaderboard,
  progress,
  tournamentComplete,
  runningSessions,
  completedSessions,
  failedSessions,
} = storeToRefs(tournamentsStore)

const activeTab = ref('grid')
const showNewTournamentModal = ref(false)
const scoresChart = ref(null)
const agreementsChart = ref(null)
let scoresChartInstance = null
let agreementsChartInstance = null

onMounted(async () => {
  await loadData()
})

onUnmounted(() => {
  tournamentsStore.stopStreaming()
  if (scoresChartInstance) scoresChartInstance.destroy()
  if (agreementsChartInstance) agreementsChartInstance.destroy()
})

async function loadData() {
  await tournamentsStore.loadSessions()
}

function selectAndViewSession(session) {
  tournamentsStore.selectSession(session)
  activeTab.value = 'grid'
}

function watchLive() {
  if (!currentSession.value) return
  tournamentsStore.startStreaming(currentSession.value.id)
  activeTab.value = 'grid'
}

function stopWatching() {
  tournamentsStore.stopStreaming()
}

async function cancelTournament() {
  if (!currentSession.value) return
  if (confirm('Are you sure you want to cancel this tournament?')) {
    await tournamentsStore.cancelSession(currentSession.value.id)
  }
}

function onTournamentStart(data) {
  // Start streaming the new tournament
  showNewTournamentModal.value = false
  tournamentsStore.startStreaming(data.session_id)
  activeTab.value = 'grid'
}

function getCellKey(competitor, scenario) {
  return `${competitor}::${scenario}`
}

function getCellClass(competitor, scenario) {
  const cellId = getCellKey(competitor, scenario)
  const cell = cellStates.value[cellId]
  
  if (!cell) return 'cell-pending'
  if (cell.status === 'running') return 'cell-running'
  if (cell.status === 'complete') {
    if (cell.agreement) return 'cell-agreement'
    return 'cell-no-agreement'
  }
  return 'cell-pending'
}

function getCellContent(competitor, scenario) {
  const cellId = getCellKey(competitor, scenario)
  const cell = cellStates.value[cellId]
  
  if (!cell) return '—'
  if (cell.status === 'running') return '⟳'
  if (cell.status === 'complete' && cell.score !== undefined) {
    return cell.score.toFixed(2)
  }
  return '—'
}

// Watch leaderboard and render charts
watch([leaderboard, () => activeTab.value], async ([newLeaderboard, newTab]) => {
  if (newTab === 'analytics' && newLeaderboard.length > 0) {
    await nextTick()
    renderCharts()
  }
})

function renderCharts() {
  renderScoresChart()
  renderAgreementsChart()
}

function renderScoresChart() {
  if (!scoresChart.value || leaderboard.value.length === 0) return
  
  if (scoresChartInstance) {
    scoresChartInstance.destroy()
  }
  
  const competitors = leaderboard.value.map(e => e.competitor)
  const scores = leaderboard.value.map(e => e.score || 0)
  
  scoresChartInstance = new Chart(scoresChart.value, {
    type: 'bar',
    data: {
      labels: competitors,
      datasets: [{
        label: 'Score',
        data: scores,
        backgroundColor: 'rgba(59, 130, 246, 0.6)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Score' },
        },
      },
      plugins: {
        legend: { display: false },
      },
    },
  })
}

function renderAgreementsChart() {
  if (!agreementsChart.value || leaderboard.value.length === 0) return
  
  if (agreementsChartInstance) {
    agreementsChartInstance.destroy()
  }
  
  const competitors = leaderboard.value.map(e => e.competitor)
  const agreements = leaderboard.value.map(e => e.agreements || 0)
  
  agreementsChartInstance = new Chart(agreementsChart.value, {
    type: 'bar',
    data: {
      labels: competitors,
      datasets: [{
        label: 'Agreements',
        data: agreements,
        backgroundColor: 'rgba(16, 185, 129, 0.6)',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Number of Agreements' },
        },
      },
      plugins: {
        legend: { display: false },
      },
    },
  })
}
</script>

<style scoped>
.tournaments-view {
  display: grid;
  grid-template-columns: 300px 1fr;
  height: 100%;
  gap: 8px;
  padding: 16px;
  overflow: hidden;
}

.sessions-sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.btn-block {
  width: 100%;
}

.session-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-group h4 {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.session-item {
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.session-item:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.session-item.active {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.session-name {
  font-weight: 500;
  margin-bottom: 4px;
  font-size: 0.9rem;
  font-family: monospace;
}

.session-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.75rem;
}

.badge {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.7rem;
  font-weight: 500;
}

.badge-running {
  background: rgba(59, 130, 246, 0.2);
  color: rgb(59, 130, 246);
}

.badge-completed {
  background: rgba(16, 185, 129, 0.2);
  color: rgb(16, 185, 129);
}

.badge-failed {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.session-progress {
  color: var(--text-secondary);
  font-family: monospace;
}

.viewer-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tournament-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.viewer-header h2 {
  margin: 0 0 8px 0;
  font-size: 1.3rem;
  font-family: monospace;
}

.tournament-info {
  display: flex;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.status-bar {
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 0.9rem;
}

.status-bar.live {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.status-indicator {
  font-weight: 600;
  color: #3b82f6;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s ease;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.tab {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.tab-content {
  flex: 1;
  overflow: auto;
}

.grid-tab,
.leaderboard-tab,
.analytics-tab,
.config-tab {
  height: 100%;
}

.tournament-grid {
  display: inline-block;
  min-width: 100%;
}

.grid-header {
  display: flex;
  gap: 2px;
  margin-bottom: 2px;
}

.grid-corner {
  width: 150px;
  flex-shrink: 0;
}

.grid-header-cell {
  width: 100px;
  padding: 8px;
  background: var(--bg-tertiary);
  font-size: 0.75rem;
  font-weight: 600;
  text-align: center;
  border-radius: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.grid-row {
  display: flex;
  gap: 2px;
  margin-bottom: 2px;
}

.grid-row-header {
  width: 150px;
  padding: 8px;
  background: var(--bg-tertiary);
  font-size: 0.85rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  border-radius: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.grid-cell {
  width: 100px;
  height: 60px;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.9rem;
  border: 2px solid transparent;
  transition: all 0.2s;
  flex-shrink: 0;
}

.cell-pending {
  background: var(--bg-primary);
  color: var(--text-secondary);
}

.cell-running {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  color: rgb(59, 130, 246);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.cell-agreement {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
  color: rgb(16, 185, 129);
}

.cell-no-agreement {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
  color: rgb(239, 68, 68);
}

.leaderboard-table-container {
  overflow: auto;
}

.leaderboard-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.leaderboard-table th,
.leaderboard-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.leaderboard-table th {
  background: var(--bg-tertiary);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

.leaderboard-table tbody tr:hover {
  background: var(--bg-hover);
}

.rank-cell {
  width: 60px;
  text-align: center;
  font-weight: 600;
}

.rank-medal {
  font-size: 1.3rem;
}

.competitor-cell {
  font-weight: 500;
}

.score-cell {
  font-family: monospace;
  font-weight: 600;
  color: var(--primary-color);
}

.analytics-tab {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.chart-section h4 {
  margin: 0 0 12px 0;
  font-size: 1rem;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.config-tab {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-section h4 {
  margin: 0 0 12px 0;
  font-size: 1rem;
}

.config-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-item {
  display: flex;
  gap: 12px;
  padding: 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.config-item label {
  font-weight: 500;
  min-width: 200px;
}

.empty-state,
.empty-state-sm {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  gap: 8px;
}

.empty-state {
  padding: 48px 24px;
}

.empty-state-sm {
  padding: 24px;
  font-size: 0.9rem;
}

.empty-hint {
  font-size: 0.85rem;
  margin: 0;
}

.btn-primary,
.btn-secondary {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.85rem;
}

.btn-icon {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.5rem;
  padding: 4px;
  transition: color 0.2s;
  line-height: 1;
}

.btn-icon:hover {
  color: var(--text-primary);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-content.large {
  max-width: 900px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.modal-body {
  padding: 16px;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid var(--border-color);
}
</style>
