<template>
  <div 
    class="tournament-negotiations-panel" 
    v-show="negotiations.length > 0"
    :class="{ collapsed: isCollapsed }"
  >
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
        <span>{{ isRunning ? 'Live Negotiations' : 'Negotiations' }}</span>
        ({{ negotiations.length }})
      </h3>
    </div>
    
    <div class="tournament-panel-content negotiations-list" v-show="!isCollapsed">
      <table class="tournament-table tournament-negotiations-table">
        <thead>
          <tr>
            <th style="width: 50px;">#</th>
            <th>Scenario</th>
            <th>Partners</th>
            <th style="width: 100px;">Result</th>
            <th style="width: 120px;">Utilities</th>
            <th v-if="!isRunning" style="width: 80px;">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(neg, idx) in displayedNegotiations"
            :key="negKey(neg, idx)"
            class="negotiation-row"
            :class="{ clickable: isRunning }"
            @click="isRunning ? handleRowClick(neg) : null"
            :title="isRunning ? 'Click to view details' : ''"
          >
            <td>{{ getDisplayIndex(neg, idx) }}</td>
            <td class="scenario-cell">
              <span :title="neg.scenario">{{ formatScenario(neg.scenario) }}</span>
            </td>
            <td class="partners-cell">{{ formatPartners(neg.partners) }}</td>
            <td>
              <span 
                class="badge badge-sm" 
                :class="getBadgeClass(neg)"
              >
                {{ getResultText(neg) }}
              </span>
            </td>
            <td class="utilities-cell">{{ formatUtilities(neg.utilities) }}</td>
            <td v-if="!isRunning">
              <button 
                class="btn btn-xs btn-primary" 
                @click.stop="handleViewClick(neg, idx)"
                :disabled="loadingIndex === idx"
                title="View in negotiation viewer"
              >
                <span v-if="loadingIndex === idx" class="spinner-xs"></span>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
                {{ loadingIndex === idx ? 'Loading...' : 'View' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  negotiations: {
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

const emit = defineEmits(['view-negotiation', 'load-trace'])

const isCollapsed = ref(false)
const loadingIndex = ref(null)

const isRunning = computed(() => props.status === 'running')

// For running tournaments, show newest first (reversed)
const displayedNegotiations = computed(() => {
  if (isRunning.value) {
    return [...props.negotiations].reverse()
  }
  return props.negotiations
})

function negKey(neg, idx) {
  return `${isRunning.value ? 'live' : 'final'}-${neg.id || idx}`
}

function getDisplayIndex(neg, idx) {
  if (isRunning.value) {
    // For reversed list, calculate original index
    return props.negotiations.length - idx
  }
  return (neg.index !== undefined ? neg.index : idx) + 1
}

function formatScenario(scenario) {
  if (!scenario) return '-'
  const parts = scenario.split('/')
  return parts[parts.length - 1].slice(0, 20)
}

function formatPartners(partners) {
  if (!partners || partners.length === 0) return '-'
  return partners.join(' vs ')
}

function formatUtilities(utilities) {
  if (!utilities || utilities.length === 0) return '-'
  return utilities.map(u => u.toFixed(2)).join(', ')
}

function getBadgeClass(neg) {
  if (neg.has_error) return 'badge-danger'
  if (neg.has_agreement) return 'badge-success'
  return 'badge-warning'
}

function getResultText(neg) {
  if (neg.has_error) return 'Error'
  if (neg.has_agreement) return 'Agreement'
  return 'No Agreement'
}

function handleRowClick(neg) {
  emit('view-negotiation', neg)
}

async function handleViewClick(neg, idx) {
  loadingIndex.value = idx
  try {
    await emit('load-trace', props.tournamentId, idx)
  } finally {
    loadingIndex.value = null
  }
}
</script>

<style scoped>
.tournament-negotiations-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.tournament-negotiations-panel.collapsed .tournament-panel-content {
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
  max-height: 400px;
  overflow: auto;
}

.tournament-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.tournament-table thead {
  position: sticky;
  top: 0;
  background: var(--bg-tertiary);
  z-index: 10;
}

.tournament-table th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border-color);
  white-space: nowrap;
}

.tournament-table tbody tr {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.tournament-table tbody tr:hover {
  background: var(--bg-hover);
}

.tournament-table tbody tr.clickable {
  cursor: pointer;
}

.tournament-table td {
  padding: 8px 12px;
}

.scenario-cell {
  font-size: 12px;
  max-width: 200px;
}

.scenario-cell span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.partners-cell {
  font-size: 12px;
  color: var(--text-secondary);
}

.utilities-cell {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 11px;
  color: var(--text-secondary);
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-sm {
  padding: 2px 6px;
  font-size: 10px;
}

.badge-success {
  background: rgba(16, 185, 129, 0.2);
  color: rgb(16, 185, 129);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.2);
  color: rgb(245, 158, 11);
}

.badge-danger {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.btn {
  padding: 4px 8px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.btn:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-xs {
  padding: 3px 6px;
  font-size: 10px;
}

.btn-primary {
  background: var(--primary-color);
}

.spinner-xs {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
