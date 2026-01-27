<template>
  <div class="tournament-grid-pane" :class="{ collapsed: isCollapsed }">
    <div class="tournament-panel-header" @click="isCollapsed = !isCollapsed">
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
              :class="{ 'self-play': i === j && !selfPlay }"
              :style="getSummaryCellStyle(i, j)"
              :title="competitor + ' vs ' + opponent"
            >
              <span class="summary-percent">{{ getSummaryCellPercent(i, j) }}</span>
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
              :class="getScenarioCellClass(i, j)"
              :title="getScenarioCellTooltip(i, j)"
            >
              <!-- For completed tournaments with multiple reps, show percentage -->
              <span 
                v-if="isCompleted && getScenarioCellPercent(i, j) !== null" 
                class="cell-percent"
                :style="{ 
                  fontSize: getScenarioCellProgress(i, j).total > 1 ? '11px' : '10px',
                  fontWeight: getScenarioCellProgress(i, j).total > 1 ? '600' : '500'
                }"
              >
                {{ getScenarioCellPercent(i, j) }}%
              </span>
              
              <!-- For running tournaments or single-rep completed, show icons -->
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
import { ref, computed } from 'vue'

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
  }
})

const isCollapsed = ref(false)
const currentTab = ref('summary')

const competitors = computed(() => props.gridInit?.competitors || [])
const opponents = computed(() => props.gridInit?.opponents || props.gridInit?.competitors || [])
const scenarios = computed(() => props.gridInit?.scenarios || [])
const isCompleted = computed(() => props.status === 'completed' || props.status === 'failed')

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
  
  if (state && isCompleted.value) {
    const total = state.total || 1
    const agreements = state.agreements || (state.has_agreement ? 1 : 0)
    const errors = state.errors || 0
    const timeouts = state.timeouts || 0
    
    tooltip += `\n\nNegotiations: ${total}`
    tooltip += `\nAgreements: ${agreements} (${Math.round(agreements/total * 100)}%)`
    if (errors > 0) tooltip += `\nErrors: ${errors}`
    if (timeouts > 0) tooltip += `\nTimeouts: ${timeouts}`
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
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.tournament-panel-header:hover {
  background: var(--bg-hover);
}

.tournament-panel-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
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
