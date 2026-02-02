<template>
  <div class="tournament-tabbed-panel">
    <div class="panel-header">
      <div class="tab-buttons">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'events' }"
          @click="activeTab = 'events'"
        >
          Event Log
          <span v-if="events.length > 0" class="badge">{{ events.length }}</span>
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'scores' }"
          @click="activeTab = 'scores'"
        >
          Score History
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'scenarios' }"
          @click="activeTab = 'scenarios'"
        >
          Scenarios
          <span v-if="scenarios.length > 0" class="badge">{{ scenarios.length }}</span>
        </button>
      </div>
      
      <div class="panel-header-actions">
        <!-- Event Log actions -->
        <template v-if="activeTab === 'events'">
          <select v-model="eventFilter" class="filter-select" title="Filter events">
            <option value="all">All events</option>
            <option value="started">Started only</option>
            <option value="completed">Completed only</option>
            <option value="failed">Errors only</option>
            <option value="agreement">Agreements only</option>
          </select>
          <button 
            class="btn-icon-sm" 
            @click="autoscroll = !autoscroll"
            :title="autoscroll ? 'Disable auto-scroll' : 'Enable auto-scroll'"
          >
            <svg v-if="autoscroll" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <polyline points="19 12 12 19 5 12"></polyline>
            </svg>
          </button>
          <button 
            class="btn-icon-sm" 
            @click="clearEvents"
            title="Clear event log"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </template>
        
        <!-- Score History actions -->
        <template v-if="activeTab === 'scores'">
          <button 
            class="btn-icon-sm" 
            @click="exportScoresToCSV"
            title="Export scores to CSV"
            :disabled="scoreHistory.length === 0"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          </button>
        </template>
        
        <!-- Scenarios actions -->
        <template v-if="activeTab === 'scenarios'">
          <button 
            class="btn-icon-sm" 
            @click="exportScenarioPlot"
            title="Export plot as image"
            :disabled="scenarios.length === 0"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
          </button>
        </template>
      </div>
    </div>
    
    <div class="panel-body">
      <!-- Event Log Tab -->
      <div v-show="activeTab === 'events'" class="tab-content" ref="logContainer">
        <div v-if="filteredEvents.length === 0" class="empty-state-sm">
          <p class="text-muted">{{ events.length === 0 ? 'No events yet' : 'No matching events' }}</p>
        </div>
        
        <div v-else class="event-list">
          <div 
            v-for="event in filteredEvents" 
            :key="event.id"
            class="event-item"
            :class="'event-' + event.type"
          >
            <span class="event-time">{{ formatTime(event.timestamp) }}</span>
            <span class="event-icon" :class="'icon-' + event.type">
              <svg v-if="event.type === 'started'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
              <svg v-else-if="event.type === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <svg v-else-if="event.type === 'failed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
              <svg v-else-if="event.type === 'warning'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              <svg v-else-if="event.type === 'agreement'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </span>
            <span class="event-message">{{ event.message }}</span>
          </div>
        </div>
      </div>
      
      <!-- Score History Tab -->
      <div v-show="activeTab === 'scores'" class="tab-content score-chart-container">
        <div v-if="scoreHistory.length === 0" class="empty-state-sm">
          <p class="text-muted">No score data yet</p>
        </div>
        
        <div v-else class="chart-wrapper">
          <canvas ref="chartCanvas"></canvas>
          
          <!-- Legend -->
          <div class="chart-legend">
            <div 
              v-for="(competitor, idx) in competitors" 
              :key="competitor"
              class="legend-item"
              :class="{ hidden: hiddenCompetitors.has(competitor) }"
              @click="toggleCompetitor(competitor)"
            >
              <span class="legend-color" :style="{ backgroundColor: getColor(idx) }"></span>
              <span class="legend-label">{{ competitor }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Scenarios Tab -->
      <div v-show="activeTab === 'scenarios'" class="tab-content scenarios-container">
        <div v-if="scenarios.length === 0 && !savedPlotUrl" class="empty-state-sm">
          <p class="text-muted">No scenario data available</p>
        </div>
        
        <!-- Show saved plot image for completed tournaments -->
        <div v-else-if="savedPlotUrl" class="scenarios-plot-wrapper">
          <img :src="savedPlotUrl" alt="Scenario Opposition Plot" class="saved-plot-image" />
        </div>
        
        <!-- Show interactive plot for running tournaments -->
        <div v-else class="scenarios-plot-wrapper">
          <div ref="scenariosPlotDiv" class="scenarios-plot"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import Chart from 'chart.js/auto'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
  events: {
    type: Array,
    default: () => []
  },
  scoreHistory: {
    type: Array,
    default: () => []
  },
  scenarios: {
    type: Array,
    default: () => []
  },
  status: {
    type: String,
    default: 'running'
  },
  tournamentId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['clearEvents'])

// Tab state
const activeTab = ref('events')

// Event log state
const logContainer = ref(null)
const autoscroll = ref(true)
const eventFilter = ref('all')

// Score chart state
const chartCanvas = ref(null)
const hiddenCompetitors = ref(new Set())
let chartInstance = null

// Scenarios plot state
const scenariosPlotDiv = ref(null)
const savedPlotUrl = ref(null)

// Color palette for chart lines
const colors = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
]

// Filtered events based on filter selection
const filteredEvents = computed(() => {
  if (eventFilter.value === 'all') {
    return props.events
  }
  return props.events.filter(e => e.type === eventFilter.value)
})

// Get unique competitors from score history
const competitors = computed(() => {
  const names = new Set()
  props.scoreHistory.forEach(snapshot => {
    if (snapshot.scores) {
      Object.keys(snapshot.scores).forEach(name => names.add(name))
    }
  })
  return Array.from(names).sort()
})

// Auto-scroll to bottom when new events arrive
watch(() => props.events.length, async () => {
  if (autoscroll.value && logContainer.value && activeTab.value === 'events') {
    await nextTick()
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})

// Update chart when score history changes
watch(() => props.scoreHistory, () => {
  if (activeTab.value === 'scores') {
    updateChart()
  }
}, { deep: true })

// Update chart when tab changes
watch(activeTab, (newTab) => {
  if (newTab === 'scores') {
    nextTick(() => updateChart())
  } else if (newTab === 'scenarios') {
    nextTick(() => loadOrRenderScenariosPlot())
  }
})

// Update scenarios plot when data changes
watch(() => props.scenarios, () => {
  if (activeTab.value === 'scenarios') {
    loadOrRenderScenariosPlot()
  }
}, { deep: true })

// Watch for tournamentId changes to load saved plot
watch(() => props.tournamentId, () => {
  if (props.tournamentId && props.status === 'completed') {
    checkSavedPlot()
  }
})

onMounted(() => {
  if (activeTab.value === 'scores' && props.scoreHistory.length > 0) {
    updateChart()
  }
  if (activeTab.value === 'scenarios') {
    loadOrRenderScenariosPlot()
  }
  // Try to load saved plot for completed tournaments
  if (props.tournamentId && props.status === 'completed') {
    checkSavedPlot()
  }
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  // Clean up Plotly
  if (scenariosPlotDiv.value) {
    Plotly.purge(scenariosPlotDiv.value)
  }
})

// Check if saved plot exists and load it
async function checkSavedPlot() {
  if (!props.tournamentId) return
  
  try {
    const response = await fetch(`/api/tournament/saved/${props.tournamentId}/scenario_plot`, {
      method: 'HEAD'
    })
    if (response.ok) {
      savedPlotUrl.value = `/api/tournament/saved/${props.tournamentId}/scenario_plot`
    } else {
      savedPlotUrl.value = null
    }
  } catch {
    savedPlotUrl.value = null
  }
}

// Decide whether to load saved plot or render interactive plot
async function loadOrRenderScenariosPlot() {
  if (savedPlotUrl.value) {
    // Already have saved plot URL, no need to render
    return
  }
  
  if (props.tournamentId && props.status === 'completed') {
    // Try to load saved plot first
    await checkSavedPlot()
    if (savedPlotUrl.value) return
  }
  
  // Render interactive plot
  if (props.scenarios.length > 0) {
    renderScenariosPlot()
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  })
}

function clearEvents() {
  emit('clearEvents')
  if (logContainer.value) {
    logContainer.value.scrollTop = 0
  }
}

function getColor(index) {
  return colors[index % colors.length]
}

function toggleCompetitor(name) {
  if (hiddenCompetitors.value.has(name)) {
    hiddenCompetitors.value.delete(name)
  } else {
    hiddenCompetitors.value.add(name)
  }
  hiddenCompetitors.value = new Set(hiddenCompetitors.value) // Trigger reactivity
  updateChart()
}

function updateChart() {
  if (!chartCanvas.value || props.scoreHistory.length === 0) return
  
  const ctx = chartCanvas.value.getContext('2d')
  
  // Prepare datasets
  const datasets = competitors.value
    .filter(name => !hiddenCompetitors.value.has(name))
    .map((name, idx) => {
      const originalIdx = competitors.value.indexOf(name)
      const data = props.scoreHistory.map((snapshot, i) => ({
        x: i,
        y: snapshot.scores?.[name] ?? null
      })).filter(d => d.y !== null)
      
      return {
        label: name,
        data: data,
        borderColor: getColor(originalIdx),
        backgroundColor: getColor(originalIdx) + '20',
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 5,
        fill: false
      }
    })
  
  // Labels for x-axis (negotiation numbers)
  const labels = props.scoreHistory.map((s, i) => s.negotiation || i + 1)
  
  if (chartInstance) {
    chartInstance.data.labels = labels
    chartInstance.data.datasets = datasets
    chartInstance.update('none')
  } else {
    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: false // We use custom legend
          },
          tooltip: {
            callbacks: {
              title: (items) => `Negotiation ${items[0]?.label || ''}`,
              label: (item) => `${item.dataset.label}: ${item.parsed.y?.toFixed(3) || 'N/A'}`
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Negotiation'
            },
            grid: {
              color: 'rgba(255,255,255,0.1)'
            }
          },
          y: {
            title: {
              display: true,
              text: 'Score'
            },
            grid: {
              color: 'rgba(255,255,255,0.1)'
            }
          }
        }
      }
    })
  }
}

function exportScoresToCSV() {
  if (props.scoreHistory.length === 0) return
  
  const headers = ['negotiation', ...competitors.value]
  const rows = props.scoreHistory.map((snapshot, i) => {
    const row = [snapshot.negotiation || i + 1]
    competitors.value.forEach(name => {
      row.push(snapshot.scores?.[name] ?? '')
    })
    return row.join(',')
  })
  
  const csv = [headers.join(','), ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'score_history.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// Scenarios plot functions
const isLoadingScenariosData = ref(false)

async function renderScenariosPlot() {
  if (!scenariosPlotDiv.value || props.scenarios.length === 0) return
  
  await nextTick()
  
  const isDark = document.documentElement.classList.contains('dark')
  const plotColors = {
    background: isDark ? '#1a1a2e' : '#ffffff',
    text: isDark ? '#e0e0e0' : '#333333',
    grid: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
    marker: isDark ? '#4fc3f7' : '#1976d2',
  }
  
  // Find scenarios missing data and fetch quick-info for them
  const scenariosMissingData = props.scenarios.filter(s => {
    const nOutcomes = s.n_outcomes ?? s.stats?.n_outcomes
    const opposition = s.opposition ?? s.stats?.opposition
    return nOutcomes == null || opposition == null || isNaN(nOutcomes) || isNaN(opposition)
  })
  
  if (scenariosMissingData.length > 0 && !isLoadingScenariosData.value) {
    // Show loading message
    scenariosPlotDiv.value.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Loading scenario data... (${scenariosMissingData.length} scenarios)</div>`
    
    isLoadingScenariosData.value = true
    try {
      // Fetch quick-info for all scenarios missing data in parallel
      const fetchPromises = scenariosMissingData.map(async (scenario) => {
        try {
          const response = await fetch(`/api/scenarios/${scenario.id}/quick-info`)
          if (response.ok) {
            const data = await response.json()
            // Update the scenario object with the fetched data
            scenario.n_outcomes = data.n_outcomes ?? scenario.n_outcomes
            scenario.opposition = data.opposition ?? scenario.opposition
            scenario.rational_fraction = data.rational_fraction ?? scenario.rational_fraction
          }
        } catch (error) {
          console.warn(`Failed to fetch quick-info for ${scenario.name}:`, error)
        }
      })
      await Promise.all(fetchPromises)
    } finally {
      isLoadingScenariosData.value = false
    }
  }
  
  // Extract data from scenarios
  const x = [] // n_outcomes
  const y = [] // opposition
  const hoverText = []
  let scenariosWithoutData = 0
  
  for (const scenario of props.scenarios) {
    const nOutcomes = scenario.n_outcomes ?? scenario.stats?.n_outcomes
    const opposition = scenario.opposition ?? scenario.stats?.opposition
    
    // Check for valid numeric values (not null, undefined, or NaN)
    if (nOutcomes != null && opposition != null && !isNaN(nOutcomes) && !isNaN(opposition)) {
      x.push(nOutcomes)
      y.push(opposition)
      hoverText.push(`${scenario.name}<br>Outcomes: ${nOutcomes}<br>Opposition: ${opposition.toFixed(3)}`)
    } else {
      scenariosWithoutData++
    }
  }
  
  if (x.length === 0) {
    Plotly.purge(scenariosPlotDiv.value)
    const message = scenariosWithoutData > 0
      ? `No scenario data available<br><span style="font-size: 11px;">${scenariosWithoutData} scenario(s) missing opposition or outcome data.</span>`
      : 'No scenario data available'
    scenariosPlotDiv.value.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">${message}</div>`
    return
  }
  
  const trace = {
    x: x,
    y: y,
    mode: 'markers',
    type: 'scatter',
    marker: {
      size: 10,
      color: plotColors.marker,
      opacity: 0.7,
    },
    text: hoverText,
    hoverinfo: 'text',
  }
  
  // Build title with data availability info
  const totalScenarios = props.scenarios.length
  const titleText = scenariosWithoutData > 0
    ? `Opposition vs Outcomes (${x.length}/${totalScenarios} with data)`
    : 'Opposition vs Number of Outcomes'
  
  const layout = {
    title: {
      text: titleText,
      font: { size: 14, color: plotColors.text }
    },
    xaxis: {
      title: { text: 'Number of Outcomes', font: { size: 12, color: plotColors.text } },
      type: 'log',
      gridcolor: plotColors.grid,
      tickfont: { color: plotColors.text },
      linecolor: plotColors.grid,
    },
    yaxis: {
      title: { text: 'Opposition Level', font: { size: 12, color: plotColors.text } },
      range: [0, 1],
      gridcolor: plotColors.grid,
      tickfont: { color: plotColors.text },
      linecolor: plotColors.grid,
    },
    paper_bgcolor: plotColors.background,
    plot_bgcolor: plotColors.background,
    margin: { t: 40, r: 20, b: 50, l: 60 },
    showlegend: false,
  }
  
  const config = {
    responsive: true,
    displayModeBar: false,
  }
  
  try {
    await Plotly.newPlot(scenariosPlotDiv.value, [trace], layout, config)
  } catch (error) {
    console.error('Failed to render scenarios plot:', error)
  }
}

async function exportScenarioPlot() {
  if (!scenariosPlotDiv.value || props.scenarios.length === 0) return
  
  try {
    // Use Plotly's built-in image export
    const imageData = await Plotly.toImage(scenariosPlotDiv.value, {
      format: 'png',
      width: 800,
      height: 600,
      scale: 2
    })
    
    // Download the image
    const a = document.createElement('a')
    a.href = imageData
    a.download = 'scenarios_opposition_plot.png'
    a.click()
  } catch (error) {
    console.error('Failed to export scenarios plot:', error)
  }
}
</script>

<style scoped>
.tournament-tabbed-panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  gap: 12px;
}

.tab-buttons {
  display: flex;
  gap: 4px;
}

.tab-btn {
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--primary-color);
  color: white;
}

.badge {
  background: rgba(255,255,255,0.2);
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.tab-btn:not(.active) .badge {
  background: var(--bg-tertiary);
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-select {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
}

.btn-icon-sm {
  padding: 4px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon-sm:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-icon-sm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.panel-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-state-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 120px;
  color: var(--text-muted);
  font-size: 13px;
}

/* Event Log styles */
.event-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
  background: var(--bg-secondary);
  transition: background 0.15s;
}

.event-item:hover {
  background: var(--bg-tertiary);
}

.event-time {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  color: var(--text-muted);
  white-space: nowrap;
  font-size: 11px;
}

.event-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
}

.icon-started {
  background: var(--info-bg, rgba(59, 130, 246, 0.2));
  color: var(--info-color, #3b82f6);
}

.icon-completed {
  background: var(--success-bg, rgba(16, 185, 129, 0.2));
  color: var(--success-color, #10b981);
}

.icon-agreement {
  background: var(--success-bg, rgba(16, 185, 129, 0.2));
  color: var(--success-color, #10b981);
}

.icon-failed {
  background: var(--error-bg, rgba(239, 68, 68, 0.2));
  color: var(--error-color, #ef4444);
}

.icon-warning {
  background: var(--warning-bg, rgba(245, 158, 11, 0.2));
  color: var(--warning-color, #f59e0b);
}

.icon-info {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.event-message {
  flex: 1;
  color: var(--text-primary);
}

.event-started .event-message {
  color: var(--text-secondary);
}

.event-failed .event-message {
  color: var(--error-color, #ef4444);
}

.event-warning .event-message {
  color: var(--warning-color, #f59e0b);
}

/* Score Chart styles */
.score-chart-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chart-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 200px;
}

.chart-wrapper canvas {
  flex: 1;
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid var(--border-color);
  margin-top: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
}

.legend-item:hover {
  background: var(--bg-tertiary);
}

.legend-item.hidden {
  opacity: 0.4;
}

.legend-item.hidden .legend-color {
  background-color: var(--text-muted) !important;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-label {
  color: var(--text-primary);
}

/* Scenarios Tab styles */
.scenarios-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.scenarios-plot-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 200px;
  align-items: center;
  justify-content: center;
}

.scenarios-plot {
  flex: 1;
  width: 100%;
  min-height: 250px;
}

.saved-plot-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 4px;
}
</style>
