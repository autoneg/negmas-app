<template>
  <div class="negotiations-view">
    <!-- Sessions List Sidebar -->
    <div class="sessions-sidebar">
      <div class="sidebar-header">
        <h3>Negotiations</h3>
        <button class="btn-icon" @click="loadData" :disabled="loading" title="Refresh">
          <span v-if="loading">⟳</span>
          <span v-else>↻</span>
        </button>
      </div>
      
      <button class="btn-primary btn-block" @click="showNewNegotiationModal = true">
        + New Negotiation
      </button>
      
      <!-- Running Sessions -->
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
            <div class="session-name">{{ session.scenario_name }}</div>
            <div class="session-meta">
              <span class="badge badge-running">Running</span>
              <span class="session-step">Step {{ session.current_step }}/{{ session.n_steps }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Completed Sessions -->
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
            <div class="session-name">{{ session.scenario_name }}</div>
            <div class="session-meta">
              <span v-if="session.agreement" class="badge badge-agreement">Agreement</span>
              <span v-else class="badge badge-no-agreement">No Agreement</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Failed Sessions -->
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
            <div class="session-name">{{ session.scenario_name }}</div>
            <div class="session-meta">
              <span class="badge badge-failed">Failed</span>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="sessions.length === 0 && !loading" class="empty-state-sm">
        No negotiations yet
      </div>
    </div>
    
    <!-- Main Viewer Panel -->
    <div class="viewer-panel">
      <div v-if="!currentSession" class="empty-state">
        <p>Select a negotiation to view details</p>
        <p class="empty-hint">or start a new negotiation</p>
      </div>
      
      <div v-else class="negotiation-viewer">
        <!-- Header -->
        <div class="viewer-header">
          <div>
            <h2>{{ sessionInit?.scenario_name || currentSession.scenario_name }}</h2>
            <div class="negotiator-tags">
              <span
                v-for="(name, idx) in sessionInit?.negotiator_names || currentSession.negotiator_names"
                :key="idx"
                class="negotiator-tag"
                :style="{ backgroundColor: getNegotiatorColor(idx) }"
              >
                {{ name }}
              </span>
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
              @click="cancelNegotiation"
            >
              Cancel
            </button>
          </div>
        </div>
        
        <!-- Live Status Bar -->
        <div v-if="streamingSession" class="status-bar live">
          <span class="status-indicator">● LIVE</span>
          <span>Step {{ offers.length }}/{{ sessionInit?.n_steps || '?' }}</span>
          <span v-if="sessionComplete">{{ sessionComplete.status.toUpperCase() }}</span>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
          <button
            class="tab"
            :class="{ active: activeTab === 'offers' }"
            @click="activeTab = 'offers'"
          >
            Offers ({{ offers.length }})
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'plot' }"
            @click="activeTab = 'plot'"
          >
            Utility Plot
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'outcome-space' }"
            @click="activeTab = 'outcome-space'"
          >
            Outcome Space
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'result' }"
            @click="activeTab = 'result'"
          >
            Result
          </button>
        </div>
        
        <!-- Tab Content -->
        <div class="tab-content">
          <!-- Offers Tab -->
          <div v-if="activeTab === 'offers'" class="offers-tab">
            <div v-if="offers.length === 0" class="empty-state-sm">
              No offers yet
            </div>
            <div v-else class="offers-table-container">
              <table class="offers-table">
                <thead>
                  <tr>
                    <th>Step</th>
                    <th>Proposer</th>
                    <th>Offer</th>
                    <th v-for="(name, idx) in sessionInit?.negotiator_names || []" :key="idx">
                      {{ name }} Utility
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(offer, idx) in offers" :key="idx">
                    <td>{{ offer.step }}</td>
                    <td>
                      <span
                        class="negotiator-tag-sm"
                        :style="{ backgroundColor: getNegotiatorColor(offer.proposer_index) }"
                      >
                        {{ offer.proposer }}
                      </span>
                    </td>
                    <td class="offer-cell">
                      {{ formatOffer(offer.offer) }}
                    </td>
                    <td v-for="(util, uidx) in offer.utilities" :key="uidx" class="utility-cell">
                      {{ util !== null ? util.toFixed(3) : 'N/A' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <!-- Utility Plot Tab -->
          <div v-if="activeTab === 'plot'" class="plot-tab">
            <div v-if="offers.length === 0" class="empty-state-sm">
              No offers to plot yet
            </div>
            <div v-else class="chart-container">
              <canvas ref="utilityChart"></canvas>
            </div>
          </div>
          
          <!-- Outcome Space Tab -->
          <div v-if="activeTab === 'outcome-space'" class="outcome-space-tab">
            <div v-if="!sessionInit?.outcome_space_data" class="empty-state-sm">
              No outcome space data available
            </div>
            <div v-else class="plot-container">
              <div ref="outcomeSpacePlot" class="plot"></div>
            </div>
          </div>
          
          <!-- Result Tab -->
          <div v-if="activeTab === 'result'" class="result-tab">
            <div v-if="!sessionComplete && currentSession.status === 'running'" class="empty-state-sm">
              Negotiation in progress...
            </div>
            <div v-else-if="sessionComplete || currentSession.status === 'completed'" class="result-content">
              <div class="result-header">
                <h3>
                  <span v-if="sessionComplete?.agreement || currentSession.agreement" class="status-success">
                    ✓ Agreement Reached
                  </span>
                  <span v-else class="status-failed">
                    ✗ No Agreement
                  </span>
                </h3>
              </div>
              
              <div v-if="sessionComplete?.agreement || currentSession.agreement" class="agreement-details">
                <h4>Agreement</h4>
                <div class="agreement-offer">
                  {{ formatOffer(sessionComplete?.agreement || currentSession.agreement) }}
                </div>
                <div class="utilities-grid">
                  <div
                    v-for="(util, idx) in sessionComplete?.final_utilities || []"
                    :key="idx"
                    class="utility-item"
                  >
                    <label>{{ sessionInit?.negotiator_names?.[idx] || `Negotiator ${idx + 1}` }}</label>
                    <span>{{ util !== null ? util.toFixed(3) : 'N/A' }}</span>
                  </div>
                </div>
              </div>
              
              <div v-if="sessionComplete?.optimality_stats" class="optimality-stats">
                <h4>Optimality Statistics</h4>
                <div class="stats-grid">
                  <div v-for="(value, key) in sessionComplete.optimality_stats" :key="key" class="stat-item">
                    <label>{{ formatStatName(key) }}</label>
                    <span>{{ typeof value === 'number' ? value.toFixed(3) : value }}</span>
                  </div>
                </div>
              </div>
              
              <div v-if="sessionComplete?.end_reason" class="end-reason">
                <label>End Reason:</label>
                <span>{{ sessionComplete.end_reason }}</span>
              </div>
              
              <div v-if="sessionComplete?.error" class="error-message">
                <strong>Error:</strong> {{ sessionComplete.error }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- New Negotiation Modal (teleported to body) -->
    <Teleport to="body">
      <NewNegotiationModal
        :show="showNewNegotiationModal"
        @close="showNewNegotiationModal = false"
        @start="onNegotiationStart"
      />
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useNegotiationsStore } from '../stores/negotiations'
import { storeToRefs } from 'pinia'
import Chart from 'chart.js/auto'
import Plotly from 'plotly.js-dist-min'
import NewNegotiationModal from '../components/NewNegotiationModal.vue'

const router = useRouter()
const route = useRoute()
const negotiationsStore = useNegotiationsStore()
const {
  sessions,
  currentSession,
  loading,
  streamingSession,
  sessionInit,
  offers,
  sessionComplete,
  runningSessions,
  completedSessions,
  failedSessions,
} = storeToRefs(negotiationsStore)

const activeTab = ref('offers')
const showNewNegotiationModal = ref(false)
const utilityChart = ref(null)
const outcomeSpacePlot = ref(null)
let chartInstance = null

onMounted(async () => {
  await loadData()
  
  // Check if we should start streaming a specific session from query params
  if (route.query.session_id) {
    const sessionId = route.query.session_id
    negotiationsStore.startStreaming(sessionId)
    activeTab.value = 'offers'
  }
})

onUnmounted(() => {
  negotiationsStore.stopStreaming()
  if (chartInstance) {
    chartInstance.destroy()
  }
})

async function loadData() {
  await negotiationsStore.loadSessions()
}

function onNegotiationStart(data) {
  // Close modal
  showNewNegotiationModal.value = false
  // Start streaming the new negotiation
  if (data.session_id) {
    negotiationsStore.startStreaming(data.session_id)
    activeTab.value = 'offers'
  }
}

function selectAndViewSession(session) {
  negotiationsStore.selectSession(session)
  activeTab.value = 'offers'
  
  // If session is completed, we might want to load full details
  if (session.status === 'completed' || session.status === 'failed') {
    // Could load saved session data here if needed
  }
}

function watchLive() {
  if (!currentSession.value) return
  negotiationsStore.startStreaming(currentSession.value.id)
  activeTab.value = 'offers'
}

function stopWatching() {
  negotiationsStore.stopStreaming()
}

async function cancelNegotiation() {
  if (!currentSession.value) return
  if (confirm('Are you sure you want to cancel this negotiation?')) {
    await negotiationsStore.cancelSession(currentSession.value.id)
  }
}

function getNegotiatorColor(index) {
  const colors = sessionInit.value?.negotiator_colors || currentSession.value?.negotiator_colors || []
  if (colors[index]) return colors[index]
  
  // Fallback colors
  const fallbackColors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
  return fallbackColors[index % fallbackColors.length]
}

function formatOffer(offer) {
  if (!offer) return 'N/A'
  if (typeof offer === 'string') return offer
  return JSON.stringify(offer)
}

function formatStatName(key) {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Watch offers and update utility chart
watch([offers, () => activeTab.value], async ([newOffers, newTab]) => {
  if (newTab === 'plot' && newOffers.length > 0) {
    await nextTick()
    renderUtilityChart()
  }
})

// Watch outcome space data
watch([sessionInit, () => activeTab.value], async ([newInit, newTab]) => {
  if (newTab === 'outcome-space' && newInit?.outcome_space_data && outcomeSpacePlot.value) {
    await nextTick()
    renderOutcomeSpace()
  }
})

function renderUtilityChart() {
  if (!utilityChart.value) return
  
  // Destroy existing chart
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  const negotiatorNames = sessionInit.value?.negotiator_names || []
  const datasets = []
  
  // Create a dataset for each negotiator
  negotiatorNames.forEach((name, idx) => {
    datasets.push({
      label: name,
      data: offers.value.map(o => ({ x: o.step, y: o.utilities[idx] })),
      borderColor: getNegotiatorColor(idx),
      backgroundColor: getNegotiatorColor(idx) + '40',
      borderWidth: 2,
      pointRadius: 3,
      tension: 0.1,
    })
  })
  
  chartInstance = new Chart(utilityChart.value, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: 'Step' },
        },
        y: {
          title: { display: true, text: 'Utility' },
        },
      },
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { mode: 'index', intersect: false },
      },
    },
  })
}

function renderOutcomeSpace() {
  if (!outcomeSpacePlot.value || !sessionInit.value?.outcome_space_data) return
  
  const data = sessionInit.value.outcome_space_data
  const negotiatorNames = sessionInit.value.negotiator_names
  const utilities = data.outcome_utilities
  
  if (negotiatorNames.length === 2) {
    // 2D scatter plot
    const trace = {
      x: utilities.map(u => u[0]),
      y: utilities.map(u => u[1]),
      mode: 'markers',
      type: 'scatter',
      marker: { size: 3, color: 'rgba(59, 130, 246, 0.4)' },
      name: 'Outcomes',
    }
    
    const traces = [trace]
    
    // Add Pareto frontier
    if (data.pareto_utilities) {
      traces.push({
        x: data.pareto_utilities.map(u => u[0]),
        y: data.pareto_utilities.map(u => u[1]),
        mode: 'markers',
        type: 'scatter',
        marker: { size: 4, color: 'rgba(239, 68, 68, 0.8)' },
        name: 'Pareto',
      })
    }
    
    // Add special points
    if (data.nash_point) {
      traces.push({
        x: [data.nash_point[0]],
        y: [data.nash_point[1]],
        mode: 'markers',
        type: 'scatter',
        marker: { size: 10, color: '#10b981', symbol: 'star' },
        name: 'Nash',
      })
    }
    
    const layout = {
      xaxis: { title: negotiatorNames[0] },
      yaxis: { title: negotiatorNames[1] },
      hovermode: 'closest',
      margin: { l: 50, r: 20, t: 30, b: 50 },
    }
    
    Plotly.newPlot(outcomeSpacePlot.value, traces, layout, { responsive: true })
  }
}
</script>

<style scoped>
.negotiations-view {
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
  overflow: hidden;
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

.badge-agreement {
  background: rgba(16, 185, 129, 0.2);
  color: rgb(16, 185, 129);
}

.badge-no-agreement {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.badge-failed {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.session-step {
  color: var(--text-secondary);
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

.negotiation-viewer {
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
}

.negotiator-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.negotiator-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
  color: white;
}

.negotiator-tag-sm {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 500;
  color: white;
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
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-indicator {
  font-weight: 600;
  color: #ef4444;
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
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.offers-tab,
.plot-tab,
.outcome-space-tab,
.result-tab {
  flex: 1;
  overflow: auto;
}

.offers-table-container {
  overflow: auto;
}

.offers-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.offers-table th,
.offers-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.offers-table th {
  background: var(--bg-tertiary);
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

.offers-table tbody tr:hover {
  background: var(--bg-hover);
}

.offer-cell {
  font-family: monospace;
  font-size: 0.8rem;
}

.utility-cell {
  font-family: monospace;
}

.chart-container {
  height: 400px;
  width: 100%;
}

.plot-container {
  height: 500px;
  width: 100%;
}

.plot {
  width: 100%;
  height: 100%;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.result-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.status-success {
  color: #10b981;
}

.status-failed {
  color: #ef4444;
}

.agreement-details h4,
.optimality-stats h4 {
  margin: 0 0 12px 0;
  font-size: 1rem;
}

.agreement-offer {
  padding: 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-family: monospace;
  margin-bottom: 16px;
}

.utilities-grid,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.utility-item,
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.utility-item label,
.stat-item label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.utility-item span,
.stat-item span {
  font-size: 1rem;
  font-family: monospace;
}

.end-reason {
  padding: 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.end-reason label {
  font-weight: 500;
  margin-right: 8px;
}

.error-message {
  padding: 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  color: #ef4444;
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
