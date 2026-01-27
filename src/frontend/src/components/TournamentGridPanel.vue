<template>
  <div class="tournament-grid-pane" :class="{ collapsed: isCollapsed }">
    <div class="tournament-panel-header">
      <div @click="isCollapsed = !isCollapsed" style="flex: 1; cursor: pointer; user-select: none;">
        <h3>
          <svg 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            stroke-width="2" 
            width="14" 
            height="14" 
            :style="{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
          Competition Grid
        </h3>
      </div>
      
      <!-- Display Mode Selector -->
      <div class="grid-display-controls" @click.stop>
        <label class="grid-control-label">Cell Display:</label>
        <div class="grid-mode-selector">
          <button 
            v-for="mode in availableModes" 
            :key="mode.value"
            class="grid-mode-btn"
            :class="{ active: displayModes.includes(mode.value) }"
            :title="mode.description"
            @click="toggleDisplayMode(mode.value)"
          >
            {{ mode.label }}
          </button>
        </div>
        
        <!-- Export Button with Dropdown -->
        <div class="export-dropdown" v-if="competitors.length > 0">
          <button class="export-btn" @click="showExportMenu = !showExportMenu">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Export
          </button>
          <div v-if="showExportMenu" class="export-menu" @click.stop>
            <button @click="exportGrid('current')">Export Current View</button>
            <button @click="exportGrid('all')">Export All Statistics</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="tournament-panel-content" v-show="!isCollapsed">
      <!-- Tabs: Summary + Scenarios -->
      <div class="tournament-scenario-tabs" v-if="scenarios.length > 0">
        <button 
          class="tournament-scenario-tab" 
          :class="{ active: currentTab === 'summary' }"
          @click="currentTab = 'summary'"
        >
          Summary
        </button>
        <button
          v-for="(scenario, idx) in scenarios"
          :key="idx"
          class="tournament-scenario-tab" 
          :class="{ active: currentTab === idx }"
          @click="currentTab = idx"
        >
          {{ scenario.split('/').pop().slice(0, 15) }}
        </button>
      </div>
      
      <div class="tournament-grid-wrapper">
        <!-- Empty state when grid not initialized -->
        <div v-if="competitors.length === 0" class="tournament-grid-empty">
          <div class="spinner"></div>
          <p>Initializing tournament grid...</p>
        </div>
        
        <!-- Summary Grid (aggregated across all scenarios) -->
        <div 
          v-else-if="currentTab === 'summary'" 
          class="tournament-grid"
          :style="{ gridTemplateColumns: `auto repeat(${opponents.length}, 1fr)` }"
        >
          <!-- Header Row -->
          <div class="tournament-grid-header-cell corner-cell"></div>
          <div
            v-for="(opponent, j) in opponents"
            :key="'sh-' + j"
            class="tournament-grid-header-cell column-header"
            :title="opponent"
          >
            <span class="header-name">{{ opponent.slice(0, 12) }}</span>
          </div>
          
          <!-- Data Rows -->
          <template v-for="(competitor, i) in competitors" :key="'sr-' + i">
            <div class="tournament-grid-row-header" :title="competitor">
              <span class="row-header-name">{{ competitor.slice(0, 12) }}</span>
            </div>
            <div
              v-for="(opponent, j) in opponents"
              :key="'sc-' + i + '-' + j"
              class="tournament-cell summary-cell"
              :class="{ 
                'self-play': i === j && !selfPlay,
                'has-running': isCellRunning(i, j, 'summary')
              }"
              :style="getSummaryCellStyle(i, j)"
              :title="getSummaryCellTooltip(i, j)"
              @click="navigateToCellNegotiations(i, j, 'summary')"
            >
              <!-- Running indicator -->
              <div v-if="isCellRunning(i, j, 'summary')" class="cell-running-indicator">
                <div class="spinner spinner-cell"></div>
              </div>
              
              <div class="cell-metrics-display">
                <div 
                  v-for="metric in getCellDisplayValues(i, j, null)" 
                  :key="metric.mode"
                  class="cell-metric"
                  :style="{ color: getModeColor(metric.mode) }"
                >
                  <span class="metric-label">{{ metric.label }}:</span>
                  <span class="metric-value">{{ metric.value }}%</span>
                </div>
              </div>
            </div>
          </template>
        </div>
        
        <!-- Scenario-specific Grid -->
        <div 
          v-else-if="typeof currentTab === 'number'"
          class="tournament-grid"
          :style="{ gridTemplateColumns: `auto repeat(${opponents.length}, 1fr)` }"
        >
          <!-- Header Row -->
          <div class="tournament-grid-header-cell corner-cell"></div>
          <div
            v-for="(opponent, j) in opponents"
            :key="'h-' + j"
            class="tournament-grid-header-cell column-header"
            :title="opponent"
          >
            <span class="header-name">{{ opponent.slice(0, 12) }}</span>
          </div>
          
          <!-- Data Rows -->
          <template v-for="(competitor, i) in competitors" :key="'r-' + i">
            <div class="tournament-grid-row-header" :title="competitor">
              <span class="row-header-name">{{ competitor.slice(0, 12) }}</span>
            </div>
            <div
              v-for="(opponent, j) in opponents"
              :key="'c-' + i + '-' + j"
              class="tournament-cell"
              :class="[
                getScenarioCellClass(i, j),
                { 'has-running': isCellRunning(i, j, currentTab) }
              ]"
              :title="getScenarioCellTooltip(i, j)"
              @click="navigateToCellNegotiations(i, j, currentTab)"
            >
              <!-- Running indicator -->
              <div v-if="isCellRunning(i, j, currentTab)" class="cell-running-indicator">
                <div class="spinner spinner-cell"></div>
              </div>
              
              <!-- For cells with multiple reps or completed tournaments, show metrics -->
              <div 
                v-if="shouldShowMetrics(i, j)" 
                class="cell-metrics-display"
              >
                <div 
                  v-for="metric in getCellDisplayValues(i, j, currentTab)" 
                  :key="metric.mode"
                  class="cell-metric"
                  :style="{ color: getModeColor(metric.mode) }"
                >
                  <span class="metric-label">{{ metric.label }}:</span>
                  <span class="metric-value">{{ metric.value }}%</span>
                </div>
              </div>
              
              <!-- For single-rep running/pending cells, show icons -->
              <template v-else>
                <!-- Icon based on state -->
                <div v-if="getScenarioCellStatus(i, j) === 'running'" class="spinner spinner-xs"></div>
                <svg
                  v-else-if="getScenarioCellStatus(i, j) === 'agreement' || getScenarioCellStatus(i, j) === 'complete'"
                  class="tournament-cell-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <svg
                  v-else-if="getScenarioCellStatus(i, j) === 'timeout'"
                  class="tournament-cell-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <svg
                  v-else-if="getScenarioCellStatus(i, j) === 'error' || getScenarioCellStatus(i, j) === 'broken'"
                  class="tournament-cell-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="15" y1="9" x2="9" y2="15"></line>
                  <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
              </template>
              
              <!-- Progress indicator for multiple runs (bottom of cell) -->
              <div
                v-if="getScenarioCellProgress(i, j).total > 1 && !isCompleted"
                style="position: absolute; bottom: 2px; left: 2px; right: 2px; font-size: 8px; opacity: 0.7;"
              >
                {{ getScenarioCellProgress(i, j).completed }}/{{ getScenarioCellProgress(i, j).total }}
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTournamentsStore } from '../stores/tournaments'
import { useRouter } from 'vue-router'

const props = defineProps({
  gridInit: {
    type: Object,
    default: null
  },
  cellStates: {
    type: Object,
    default: () => ({})
  },
  selfPlay: {
    type: Boolean,
    default: false
  },
  status: {
    type: String,
    default: 'unknown'
  },
  tournamentId: {
    type: String,
    default: null
  }
})

const tournamentsStore = useTournamentsStore()
const router = useRouter()
const isCollapsed = ref(false)
const currentTab = ref('summary')
const showExportMenu = ref(false)

// Close export menu when clicking outside
if (typeof document !== 'undefined') {
  document.addEventListener('click', () => {
    showExportMenu.value = false
  })
}

// Available display modes with unique colors
const availableModes = [
  { value: 'completion', label: 'Complete', description: 'Show completion percentage', color: '#3b82f6' }, // blue
  { value: 'agreement', label: 'Agreement', description: 'Show agreement rate', color: '#10b981' }, // green
  { value: 'success', label: 'Success', description: 'Show success rate (no errors)', color: '#8b5cf6' }, // purple
  { value: 'timeout', label: 'Timeout', description: 'Show timeout rate', color: '#f59e0b' }, // amber
  { value: 'error', label: 'Error', description: 'Show error rate', color: '#ef4444' } // red
]

function getModeColor(mode) {
  return availableModes.find(m => m.value === mode)?.color || '#6b7280'
}

// Get display modes from store, or use local storage, or default to ['completion']
const displayModes = ref([])

onMounted(() => {
  // Load from localStorage or use default
  const saved = localStorage.getItem('tournament-grid-display-modes')
  if (saved) {
    try {
      displayModes.value = JSON.parse(saved)
    } catch (e) {
      displayModes.value = ['completion']
    }
  } else {
    displayModes.value = ['completion']
  }
})

function toggleDisplayMode(mode) {
  const index = displayModes.value.indexOf(mode)
  if (index > -1) {
    // Remove mode if already selected (but keep at least one)
    if (displayModes.value.length > 1) {
      displayModes.value.splice(index, 1)
    }
  } else {
    // Add mode (limit to 3 modes max)
    if (displayModes.value.length < 3) {
      displayModes.value.push(mode)
    }
  }
  
  // Save to localStorage
  localStorage.setItem('tournament-grid-display-modes', JSON.stringify(displayModes.value))
}

// Export grid data to CSV
function exportGrid(mode) {
  showExportMenu.value = false
  
  const rows = []
  const isAllStats = mode === 'all'
  
  // Determine what data to export based on current tab
  const tabName = currentTab.value === 'summary' ? 'Summary' : scenarios.value[currentTab.value]?.split('/').pop() || 'Grid'
  
  // Header row
  if (isAllStats) {
    rows.push(['Competitor', 'Opponent', 'Scenario', 'Total', 'Completed', 'Completion%', 'Agreements', 'Agreement%', 'Success%', 'Timeouts', 'Timeout%', 'Errors', 'Error%'])
  } else {
    const headers = ['Competitor', 'Opponent']
    if (currentTab.value !== 'summary') {
      headers.push('Scenario')
    }
    displayModes.value.forEach(mode => {
      const label = availableModes.find(m => m.value === mode)?.label || mode
      headers.push(`${label}%`)
    })
    rows.push(headers)
  }
  
  // Data rows
  if (currentTab.value === 'summary') {
    // Export summary across all scenarios
    competitors.value.forEach((competitor, i) => {
      opponents.value.forEach((opponent, j) => {
        if (i === j && !props.selfPlay) return
        
        if (isAllStats) {
          // Export detailed stats for each scenario
          scenarios.value.forEach(scenario => {
            const key = `${competitor}::${opponent}::${scenario}`
            const state = props.cellStates[key]
            if (state) {
              const metrics = calculateCellMetrics(state)
              rows.push([
                competitor,
                opponent,
                scenario.split('/').pop(),
                state.total || 0,
                state.completed || 0,
                metrics.completion,
                state.agreements || 0,
                metrics.agreement,
                metrics.success,
                state.timeouts || 0,
                metrics.timeout,
                state.errors || 0,
                metrics.error
              ])
            }
          })
        } else {
          // Export current view metrics (aggregated)
          const values = getCellDisplayValues(i, j, null)
          const row = [competitor, opponent]
          values.forEach(v => row.push(v.value))
          rows.push(row)
        }
      })
    })
  } else {
    // Export specific scenario
    const scenario = scenarios.value[currentTab.value]
    competitors.value.forEach((competitor, i) => {
      opponents.value.forEach((opponent, j) => {
        if (i === j && !props.selfPlay) return
        
        const key = `${competitor}::${opponent}::${scenario}`
        const state = props.cellStates[key]
        
        if (state) {
          const metrics = calculateCellMetrics(state)
          
          if (isAllStats) {
            rows.push([
              competitor,
              opponent,
              scenario.split('/').pop(),
              state.total || 0,
              state.completed || 0,
              metrics.completion,
              state.agreements || 0,
              metrics.agreement,
              metrics.success,
              state.timeouts || 0,
              metrics.timeout,
              state.errors || 0,
              metrics.error
            ])
          } else {
            const values = getCellDisplayValues(i, j, currentTab.value)
            const row = [competitor, opponent, scenario.split('/').pop()]
            values.forEach(v => row.push(v.value))
            rows.push(row)
          }
        }
      })
    })
  }
  
  // Convert to CSV
  const csv = rows.map(row => row.map(cell => {
    // Escape cells that contain commas or quotes
    const str = String(cell)
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }).join(',')).join('\n')
  
  // Download
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
  const filename = `tournament-grid-${tabName}-${isAllStats ? 'all' : 'view'}-${timestamp}.csv`
  
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

// Check if a cell has running negotiations
function isCellRunning(i, j, scenarioKey) {
  if (i === j && !props.selfPlay) return false
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  
  if (scenarioKey === 'summary') {
    // Check if any scenario in this cell is running
    return scenarios.value.some(scenario => {
      const key = `${competitor}::${opponent}::${scenario}`
      const state = props.cellStates[key]
      return state && (state.status === 'running' || (state.running && state.running > 0))
    })
  } else {
    // Check specific scenario
    const scenario = scenarios.value[scenarioKey]
    const key = `${competitor}::${opponent}::${scenario}`
    const state = props.cellStates[key]
    return state && (state.status === 'running' || (state.running && state.running > 0))
  }
}

// Navigate to negotiations filtered by cell
function navigateToCellNegotiations(i, j, scenarioKey) {
  if (i === j && !props.selfPlay) return // Can't click self-play cells
  if (!props.tournamentId) return // Need tournament ID
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  
  // Build query params for filtering
  const query = {
    competitor: competitor,
    opponent: opponent
  }
  
  // Add scenario filter if not summary
  if (scenarioKey !== 'summary') {
    const scenario = scenarios.value[scenarioKey]
    query.scenario = scenario
  }
  
  // Navigate to tournament negotiations list with filters
  router.push({
    name: 'TournamentNegotiationsList',
    params: { tournamentId: props.tournamentId },
    query
  })
}

const competitors = computed(() => props.gridInit?.competitors || [])
const opponents = computed(() => props.gridInit?.opponents || props.gridInit?.competitors || [])
const scenarios = computed(() => props.gridInit?.scenarios || [])
const isCompleted = computed(() => props.status === 'completed' || props.status === 'failed')

// Calculate all metrics for a given cell
function calculateCellMetrics(state) {
  if (!state || state.completed === 0) {
    return {
      completion: 0,
      agreement: 0,
      success: 0,
      timeout: 0,
      error: 0
    }
  }
  
  const total = state.total || 1
  const completed = state.completed || 0
  const agreements = Math.min(state.agreements || 0, completed)
  const errors = Math.min(state.errors || 0, completed)
  const timeouts = Math.min(state.timeouts || 0, completed)
  
  return {
    completion: Math.round((completed / total) * 100),
    agreement: completed > 0 ? Math.round((agreements / completed) * 100) : 0,
    success: completed > 0 ? Math.round(((completed - errors) / completed) * 100) : 0,
    timeout: completed > 0 ? Math.round((timeouts / completed) * 100) : 0,
    error: completed > 0 ? Math.round((errors / completed) * 100) : 0
  }
}

// Get display values for a cell based on selected modes
function getCellDisplayValues(i, j, scenarioKey = null) {
  if (i === j && !props.selfPlay) return []
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  
  let state
  if (scenarioKey) {
    // Specific scenario cell
    const scenario = scenarios.value[scenarioKey]
    const key = `${competitor}::${opponent}::${scenario}`
    state = props.cellStates[key]
  } else {
    // Summary cell - aggregate across all scenarios
    let totalAgg = 0, completedAgg = 0, agreementsAgg = 0, errorsAgg = 0, timeoutsAgg = 0
    
    scenarios.value.forEach(scenario => {
      const key = `${competitor}::${opponent}::${scenario}`
      const s = props.cellStates[key]
      if (s && s.completed > 0) {
        totalAgg += s.total || 1
        completedAgg += s.completed || 0
        agreementsAgg += Math.min(s.agreements || 0, s.completed || 0)
        errorsAgg += Math.min(s.errors || 0, s.completed || 0)
        timeoutsAgg += Math.min(s.timeouts || 0, s.completed || 0)
      }
    })
    
    state = {
      total: totalAgg,
      completed: completedAgg,
      agreements: agreementsAgg,
      errors: errorsAgg,
      timeouts: timeoutsAgg
    }
  }
  
  const metrics = calculateCellMetrics(state)
  
  return displayModes.value.map(mode => ({
    mode,
    value: metrics[mode],
    label: availableModes.find(m => m.value === mode)?.label || mode
  }))
}

function getSummaryCellStyle(i, j) {
  if (i === j && !props.selfPlay) return {}
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  
  // Calculate aggregate results across all scenarios
  let total = 0
  let agreements = 0
  let errors = 0
  let timeouts = 0
  let hasAnyData = false
  
  scenarios.value.forEach(scenario => {
    const key = `${competitor}::${opponent}::${scenario}`
    const state = props.cellStates[key]
    if (state && state.completed > 0) {
      hasAnyData = true
      total += state.total || 1
      agreements += Math.min(state.agreements || 0, state.completed || 0)
      errors += Math.min(state.errors || 0, state.completed || 0)
      timeouts += Math.min(state.timeouts || 0, state.completed || 0)
    }
  })
  
  if (!hasAnyData || total === 0) return {}
  
  // Color based on agreement rate, but dim if errors/timeouts
  const percent = Math.min(1, agreements / total)
  const errorRate = Math.min(1, errors / total)
  const timeoutRate = Math.min(1, timeouts / total)
  
  // Add pulsing animation if cell is currently active
  const isActive = scenarios.value.some(scenario => {
    const key = `${competitor}::${opponent}::${scenario}`
    const state = props.cellStates[key]
    return state && state.status === 'running' && (state.running || 0) > 0
  })
  
  let style = {}
  
  if (errorRate > 0.5) {
    // Mostly errors - show red
    style.background = `rgba(239, 68, 68, ${0.2 + errorRate * 0.3})`
  } else if (timeoutRate > 0.5) {
    // Mostly timeouts - show orange
    style.background = `rgba(251, 146, 60, ${0.2 + timeoutRate * 0.3})`
  } else {
    // Show green based on agreement rate
    const green = Math.round(16 + percent * 169) // 16 to 185
    style.background = `rgba(16, ${green}, 129, ${0.1 + percent * 0.3})`
  }
  
  if (isActive) {
    style.animation = 'pulse-cell 2s ease-in-out infinite'
  }
  
  return style
}

function getSummaryCellPercent(i, j) {
  if (i === j && !props.selfPlay) return '-'
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  
  let total = 0
  let agreements = 0
  let hasAnyData = false
  
  scenarios.value.forEach(scenario => {
    const key = `${competitor}::${opponent}::${scenario}`
    const state = props.cellStates[key]
    if (state && state.completed > 0) {
      hasAnyData = true
      total += state.total || 1
      // Ensure agreements never exceeds completed
      agreements += Math.min(state.agreements || 0, state.completed || 0)
    }
  })
  
  if (!hasAnyData || total === 0) return '...'
  
  // Ensure percent is clamped to 0-100 range
  const percent = Math.min(100, Math.max(0, Math.round((agreements / total) * 100)))
  return `${percent}%`
}

function getSummaryCellTooltip(i, j) {
  if (i === j && !props.selfPlay) return 'Self-play disabled'
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  
  let totalAgg = 0, completedAgg = 0, agreementsAgg = 0, errorsAgg = 0, timeoutsAgg = 0
  
  scenarios.value.forEach(scenario => {
    const key = `${competitor}::${opponent}::${scenario}`
    const state = props.cellStates[key]
    if (state && state.completed > 0) {
      totalAgg += state.total || 1
      completedAgg += state.completed || 0
      agreementsAgg += Math.min(state.agreements || 0, state.completed || 0)
      errorsAgg += Math.min(state.errors || 0, state.completed || 0)
      timeoutsAgg += Math.min(state.timeouts || 0, state.completed || 0)
    }
  })
  
  if (totalAgg === 0) return `${competitor} vs ${opponent}\n\nNo data yet`
  
  const metrics = calculateCellMetrics({
    total: totalAgg,
    completed: completedAgg,
    agreements: agreementsAgg,
    errors: errorsAgg,
    timeouts: timeoutsAgg
  })
  
  let tooltip = `${competitor} vs ${opponent}\n`
  tooltip += `\nTotal negotiations: ${totalAgg}`
  tooltip += `\nCompleted: ${completedAgg} (${metrics.completion}%)`
  tooltip += `\nAgreements: ${agreementsAgg} (${metrics.agreement}%)`
  tooltip += `\nSuccess: ${metrics.success}%`
  tooltip += `\nTimeouts: ${timeoutsAgg} (${metrics.timeout}%)`
  tooltip += `\nErrors: ${errorsAgg} (${metrics.error}%)`
  
  return tooltip
}

function getScenarioCellClass(i, j) {
  if (i === j && !props.selfPlay) return 'self-play'
  
  const status = getScenarioCellStatus(i, j)
  
  const classes = []
  if (status === 'running') classes.push('cell-running')
  else if (status === 'agreement' || status === 'complete') classes.push('cell-complete')
  else if (status === 'timeout') classes.push('cell-timeout')
  else if (status === 'error' || status === 'broken') classes.push('cell-error')
  else classes.push('cell-pending')
  
  return classes.join(' ')
}

function getScenarioCellStatus(i, j) {
  if (i === j && !props.selfPlay) return 'self-play'
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  const scenario = scenarios.value[currentTab.value]
  
  const key = `${competitor}::${opponent}::${scenario}`
  const state = props.cellStates[key]
  
  if (!state) return 'pending'
  if (state.status === 'running') return 'running'
  if (state.status === 'error' || state.has_error) return 'error'
  if (state.status === 'timeout') return 'timeout'
  if (state.status === 'complete') {
    return state.has_agreement ? 'agreement' : 'complete'
  }
  
  return 'pending'
}

function getScenarioCellTooltip(i, j) {
  if (i === j && !props.selfPlay) return 'Self-play disabled'
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  const scenario = scenarios.value[currentTab.value]
  
  const key = `${competitor}::${opponent}::${scenario}`
  const state = props.cellStates[key]
  
  let tooltip = `${competitor} vs ${opponent}\n${scenario}`
  
  if (state) {
    const total = state.total || 1
    const completed = state.completed || 0
    const agreements = state.agreements || 0
    const errors = state.errors || 0
    const timeouts = state.timeouts || 0
    
    const metrics = calculateCellMetrics(state)
    
    tooltip += `\n\nNegotiations: ${completed}/${total}`
    tooltip += `\nCompletion: ${metrics.completion}%`
    if (completed > 0) {
      tooltip += `\nAgreements: ${agreements} (${metrics.agreement}%)`
      tooltip += `\nSuccess: ${metrics.success}%`
      tooltip += `\nTimeouts: ${timeouts} (${metrics.timeout}%)`
      tooltip += `\nErrors: ${errors} (${metrics.error}%)`
    }
  } else {
    tooltip += `\n\nWaiting to start...`
  }
  
  return tooltip
}

function getScenarioCellProgress(i, j) {
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  const scenario = scenarios.value[currentTab.value]
  
  const key = `${competitor}::${opponent}::${scenario}`
  const state = props.cellStates[key]
  
  return {
    completed: state?.completed || 0,
    total: state?.total || 1
  }
}

function getScenarioCellPercent(i, j) {
  if (i === j && !props.selfPlay) return null
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  const scenario = scenarios.value[currentTab.value]
  
  const key = `${competitor}::${opponent}::${scenario}`
  const state = props.cellStates[key]
  
  if (!state || !isCompleted.value) return null
  
  const total = state.total || 1
  const agreements = state.agreements || (state.has_agreement ? 1 : 0)
  
  return Math.round((agreements / total) * 100)
}

// Determine if cell should show metrics vs icons
function shouldShowMetrics(i, j) {
  if (i === j && !props.selfPlay) return false
  
  const competitor = competitors.value[i]
  const opponent = opponents.value[j]
  const scenario = scenarios.value[currentTab.value]
  
  const key = `${competitor}::${opponent}::${scenario}`
  const state = props.cellStates[key]
  
  // Always show metrics if tournament is completed
  if (isCompleted.value && state) return true
  
  // Show metrics if this cell has multiple expected negotiations (total > 1)
  if (state && state.total > 1) return true
  
  // Show metrics if any negotiations have completed in this cell
  if (state && state.completed > 0) return true
  
  return false
}
</script>

<style scoped>
.tournament-grid-pane {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.tournament-grid-pane.collapsed .tournament-panel-content {
  display: none;
}

.tournament-panel-header {
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: background 0.2s;
}

.tournament-panel-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.grid-display-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.grid-control-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  margin: 0;
}

.grid-mode-selector {
  display: flex;
  gap: 4px;
}

.grid-mode-btn {
  padding: 4px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: var(--text-secondary);
  transition: all 0.2s;
  white-space: nowrap;
  font-weight: 500;
}

.grid-mode-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--primary-color);
}

.grid-mode-btn.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  font-weight: 600;
}

.export-dropdown {
  position: relative;
  margin-left: 8px;
}

.export-btn {
  padding: 4px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: var(--text-secondary);
  transition: all 0.2s;
  white-space: nowrap;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.export-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--primary-color);
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  min-width: 180px;
}

.export-menu button {
  display: block;
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  text-align: left;
  font-size: 12px;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.2s;
}

.export-menu button:first-child {
  border-radius: 4px 4px 0 0;
}

.export-menu button:last-child {
  border-radius: 0 0 4px 4px;
}

.export-menu button:hover {
  background: var(--bg-hover);
}

.tournament-panel-content {
  padding: 0;
}

.tournament-scenario-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
}

.tournament-scenario-tab {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: all 0.2s;
  white-space: nowrap;
}

.tournament-scenario-tab:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.tournament-scenario-tab.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.tournament-grid-wrapper {
  padding: 16px;
  overflow: auto;
  max-height: 500px;
}

.tournament-grid-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  gap: 12px;
  color: var(--text-secondary);
}

.tournament-grid {
  display: grid;
  gap: 1px;
  background: var(--border-color);
  border: 1px solid var(--border-color);
  width: fit-content;
  min-width: 100%;
}

.tournament-grid-header-cell {
  background: var(--bg-tertiary);
  padding: 8px;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  min-width: 60px;
}

.tournament-grid-header-cell.corner-cell {
  min-width: 120px;
}

.tournament-grid-row-header {
  background: var(--bg-tertiary);
  padding: 8px;
  font-size: 11px;
  font-weight: 600;
  text-align: left;
  display: flex;
  align-items: center;
  min-width: 120px;
}

.row-header-name,
.header-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tournament-cell {
  background: var(--bg-primary);
  padding: 8px;
  min-width: 60px;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.tournament-cell:not(.self-play):hover {
  background: var(--bg-hover);
  transform: scale(1.02);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.tournament-cell.has-running {
  background: rgba(59, 130, 246, 0.08);
  animation: pulse-running 2s ease-in-out infinite;
}

.cell-running-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
  z-index: 10;
}

.spinner-cell {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(59, 130, 246, 0.2);
  border-top-color: rgb(59, 130, 246);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.cell-metrics-display {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
}

.cell-metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  font-weight: 600;
  gap: 4px;
}

.metric-label {
  font-weight: 500;
  opacity: 0.8;
  white-space: nowrap;
}

.metric-value {
  font-weight: 700;
  white-space: nowrap;
}

.tournament-cell.self-play {
  background: repeating-linear-gradient(
    45deg,
    var(--bg-tertiary),
    var(--bg-tertiary) 5px,
    var(--bg-secondary) 5px,
    var(--bg-secondary) 10px
  );
  opacity: 0.5;
}

.tournament-cell.summary-cell {
  font-weight: 600;
}

.tournament-cell.cell-pending {
  color: var(--text-secondary);
}

.tournament-cell.cell-running {
  background: rgba(59, 130, 246, 0.1);
  color: rgb(59, 130, 246);
}

.tournament-cell.cell-complete {
  background: rgba(16, 185, 129, 0.1);
  color: rgb(16, 185, 129);
}

.cell-percent {
  font-weight: 600;
  color: var(--text-primary);
}

.tournament-cell.cell-timeout {
  background: rgba(251, 146, 60, 0.1);
  color: rgb(251, 146, 60);
}

.tournament-cell.cell-timeout {
  background: rgba(245, 158, 11, 0.1);
  color: rgb(245, 158, 11);
}

.tournament-cell.cell-error {
  background: rgba(239, 68, 68, 0.1);
  color: rgb(239, 68, 68);
}

.tournament-cell-icon {
  width: 16px;
  height: 16px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-xs {
  width: 12px;
  height: 12px;
  border-width: 1.5px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse-running {
  0%, 100% { 
    background: rgba(59, 130, 246, 0.08);
  }
  50% { 
    background: rgba(59, 130, 246, 0.15);
  }
}

@keyframes pulse-cell {
  0%, 100% { 
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% { 
    opacity: 0.9;
    box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
  }
}
</style>
