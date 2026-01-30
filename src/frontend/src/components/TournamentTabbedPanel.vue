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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  events: {
    type: Array,
    default: () => []
  },
  scoreHistory: {
    type: Array,
    default: () => []
  },
  status: {
    type: String,
    default: 'running'
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
  }
})

onMounted(() => {
  if (activeTab.value === 'scores' && props.scoreHistory.length > 0) {
    updateChart()
  }
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})

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
</style>
