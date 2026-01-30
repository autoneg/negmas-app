<template>
  <div class="tournaments-list-container">
    <!-- Header -->
    <div class="list-header">
      <div class="header-left">
        <h2>Tournaments</h2>
        <button class="btn btn-primary" @click="showNewTournamentModal = true">
          + New Tournament
        </button>
      </div>
      <div class="header-right">
        <!-- Preview Selector -->
        <label style="display: flex; align-items: center; gap: 8px; font-size: 14px;">
          <span>Preview:</span>
          <select v-model="selectedPreview" class="form-select">
            <option value="none">None</option>
            <option value="grid">Grid</option>
            <option value="leaderboard">Leaderboard</option>
            <option value="config">Configuration</option>
          </select>
        </label>
        
        <!-- Filters -->
        <select v-model="tournamentTagFilter" class="form-select" style="width: 150px;">
          <option value="">All Tags</option>
          <option v-for="tag in availableTournamentTags" :key="tag" :value="tag">{{ tag }}</option>
        </select>
        
        <label style="display: flex; align-items: center; gap: 6px; font-size: 14px;">
          <input type="checkbox" v-model="showArchivedTournaments" @change="loadData">
          <span>Archived</span>
        </label>
        
        <button class="btn btn-secondary" @click="loadData" :disabled="loading" title="Refresh">
          <span v-if="loading">⟳</span>
          <span v-else>↻</span>
        </button>
      </div>
    </div>
    
    <!-- Content Area -->
    <div class="content-area" :class="{ 'with-preview': selectedPreview !== 'none' }">
      <!-- Tables Container -->
      <div class="table-container" :style="{ width: selectedPreview === 'none' ? '100%' : '66.67%' }">
        
        <!-- Running Tournaments Section -->
        <div v-if="runningTournaments.length > 0" class="running-section">
          <div class="section-header">
            <h3>Running Tournaments ({{ runningTournaments.length }})</h3>
          </div>
          <div class="running-table-wrapper">
            <table class="running-tournaments-table">
              <thead>
                <tr>
                  <th style="width: 180px;">Name/ID</th>
                  <th style="width: 100px;">Competitors</th>
                  <th style="width: 100px;">Scenarios</th>
                  <th style="width: 150px;">Progress</th>
                  <th style="width: 100px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="tourn in runningTournaments" 
                  :key="tourn.id"
                  @click="selectTournament(tourn)"
                  :class="{ 'selected': selectedTournament?.id === tourn.id }"
                  class="clickable-row"
                >
                  <td class="name-cell">
                    <div class="tournament-name">{{ tourn.name || tourn.id?.slice(0, 12) || 'Unknown' }}</div>
                    <div class="session-id">{{ tourn.id?.slice(0, 8) }}</div>
                  </td>
                  <td class="count-cell">{{ tourn.n_competitors || 0 }}</td>
                  <td class="count-cell">{{ tourn.n_scenarios || 0 }}</td>
                  <td class="progress-cell">
                    <div class="progress-info">
                      <div class="progress-text">
                        {{ tourn.completed || 0 }}/{{ tourn.total || 0 }} negotiations
                      </div>
                      <div class="progress-bar-mini">
                        <div 
                          class="progress-bar-fill" 
                          :style="{ width: getProgressPercent(tourn) + '%' }"
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td class="actions-cell" @click.stop>
                    <button 
                      class="btn-icon-small btn-danger" 
                      @click="stopTournament(tourn)"
                      title="Stop tournament"
                    >
                      Stop
                    </button>
                    <button 
                      class="btn-icon-small" 
                      @click="viewTournament(tourn.id)" 
                      title="View full details"
                    >
                      View
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- Completed Tournaments Section -->
        <div class="completed-section">
          <div class="section-header">
            <h3>Completed Tournaments ({{ completedTournaments.length }})</h3>
          </div>
          
          <!-- Search -->
          <div class="search-bar">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Search by name, competitors, scenarios, or ID..."
              class="search-input"
            >
          </div>
          
          <!-- Table -->
          <div class="table-wrapper">
            <table class="tournaments-table">
              <thead>
                <tr>
                  <th style="width: 160px;" @click="sortBy('date')">
                    Date
                    <span v-if="sortColumn === 'date'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th @click="sortBy('name')">
                    Name/ID
                    <span v-if="sortColumn === 'name'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 100px;" @click="sortBy('competitors')">
                    Competitors
                    <span v-if="sortColumn === 'competitors'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 100px;" @click="sortBy('scenarios')">
                    Scenarios
                    <span v-if="sortColumn === 'scenarios'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 100px;" @click="sortBy('status')">
                    Status
                    <span v-if="sortColumn === 'status'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                  </th>
                  <th style="width: 180px;">Statistics</th>
                  <th style="width: 80px;">Tags</th>
                  <th style="width: 120px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="tourn in filteredAndSortedTournaments" 
                  :key="tourn.id"
                  @click="selectTournament(tourn)"
                  :class="{ 'selected': selectedTournament?.id === tourn.id }"
                  class="clickable-row"
                >
                  <td class="date-cell">{{ formatDate(tourn.timestamp || tourn.created_at) }}</td>
                  <td class="name-cell">{{ tourn.name || tourn.id?.slice(0, 12) || 'Unknown' }}</td>
                  <td class="count-cell">{{ tourn.n_competitors || 0 }}</td>
                  <td class="count-cell">{{ tourn.n_scenarios || 0 }}</td>
                  <td class="status-cell">
                    <span v-if="tourn.is_complete" class="badge badge-completed">Completed</span>
                    <span v-else-if="tourn.status === 'failed'" class="badge badge-failed">Failed</span>
                    <span v-else class="badge badge-pending">Incomplete</span>
                  </td>
                  <td class="stats-cell">
                    <div class="tournament-stats">
                      <div class="stat-item" title="Completion Rate">
                        <span class="stat-label">Complete:</span>
                        <span class="stat-value">{{ getTournamentStats(tourn).completion }}%</span>
                      </div>
                      <div class="stat-item" title="Success Rate (no errors)">
                        <span class="stat-label">Success:</span>
                        <span class="stat-value">{{ getTournamentStats(tourn).success }}%</span>
                      </div>
                      <div class="stat-item" title="Number of Errors">
                        <span class="stat-label">Errors:</span>
                        <span class="stat-value stat-error">{{ getTournamentStats(tourn).errors }}</span>
                      </div>
                    </div>
                  </td>
                  <td class="tags-cell">
                    <div class="tags-list">
                      <span 
                        v-for="tag in (tourn.tags || []).slice(0, 2)" 
                        :key="tag"
                        class="tag-badge"
                      >
                        {{ tag }}
                      </span>
                      <span v-if="(tourn.tags || []).length > 2" class="tag-more">
                        +{{ (tourn.tags || []).length - 2 }}
                      </span>
                    </div>
                  </td>
                  <td class="actions-cell" @click.stop>
                    <!-- Run/Continue button for incomplete tournaments -->
                    <button 
                      v-if="!tourn.is_complete"
                      class="btn-icon-small btn-success" 
                      @click="continueTournament(tourn.id)"
                      title="Run/Continue tournament"
                    >
                      Run
                    </button>
                    
                    <button 
                      class="btn-icon-small" 
                      @click="viewTournament(tourn.id)" 
                      title="View full details"
                    >
                      View
                    </button>
                    <button 
                      class="btn-icon-small" 
                      @click="editTournamentTags(tourn)" 
                      title="Edit tags"
                    >
                      Tags
                    </button>
                    <button 
                      class="btn-icon-small btn-danger-text" 
                      @click="deleteSavedTourn(tourn.id)" 
                      title="Delete"
                    >
                      Del
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            
            <!-- Empty State -->
            <div v-if="filteredAndSortedTournaments.length === 0 && !loading" class="empty-state">
              <p v-if="searchQuery">No tournaments match your search</p>
              <p v-else-if="tournamentTagFilter">No tournaments with tag "{{ tournamentTagFilter }}"</p>
              <p v-else>No completed tournaments yet. Start a new one!</p>
            </div>
            
            <!-- Loading State -->
            <div v-if="loading" class="loading-state">
              <p>Loading tournaments...</p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Preview Panel -->
      <div v-if="selectedPreview !== 'none'" class="preview-container">
        <div v-if="!selectedTournament" class="preview-empty">
          <p>Select a tournament to preview</p>
        </div>
        <div v-else class="preview-content">
          <!-- Grid Preview -->
          <div v-if="selectedPreview === 'grid' && previewData?.gridInit" class="preview-grid">
            <h3 style="padding: 12px 16px; margin: 0; border-bottom: 1px solid var(--border-color);">Grid</h3>
            <div style="overflow: auto; padding: 16px;">
              <div class="tournament-grid-compact">
                <div class="grid-header">
                  <div class="grid-corner"></div>
                  <div
                    v-for="scenario in previewData.gridInit.scenarios.slice(0, 5)"
                    :key="scenario"
                    class="grid-header-cell"
                  >
                    {{ scenario.split('/').pop().slice(0, 10) }}
                  </div>
                  <div v-if="previewData.gridInit.scenarios.length > 5" class="grid-header-cell">...</div>
                </div>
                <div
                  v-for="competitor in previewData.gridInit.competitors.slice(0, 8)"
                  :key="competitor"
                  class="grid-row"
                >
                  <div class="grid-row-header">{{ competitor.slice(0, 15) }}</div>
                  <div
                    v-for="scenario in previewData.gridInit.scenarios.slice(0, 5)"
                    :key="scenario"
                    class="grid-cell"
                    :class="getCellClass(competitor, scenario)"
                  >
                    {{ getCellContent(competitor, scenario) }}
                  </div>
                  <div v-if="previewData.gridInit.scenarios.length > 5" class="grid-cell">...</div>
                </div>
                <div v-if="previewData.gridInit.competitors.length > 8" class="grid-row">
                  <div class="grid-row-header">...</div>
                  <div class="grid-cell" v-for="i in Math.min(5, previewData.gridInit.scenarios.length)" :key="i">...</div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Leaderboard Preview -->
          <div v-else-if="selectedPreview === 'leaderboard' && previewData?.leaderboard" class="preview-leaderboard">
            <h3 style="padding: 12px 16px; margin: 0; border-bottom: 1px solid var(--border-color);">Leaderboard</h3>
            <table class="leaderboard-table-compact">
              <thead>
                <tr>
                  <th style="width: 50px;">Rank</th>
                  <th>Competitor</th>
                  <th style="width: 80px;">Score</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(entry, idx) in previewData.leaderboard.slice(0, 10)" :key="entry.competitor">
                  <td class="rank-cell">
                    <span v-if="idx === 0">🥇</span>
                    <span v-else-if="idx === 1">🥈</span>
                    <span v-else-if="idx === 2">🥉</span>
                    <span v-else>{{ idx + 1 }}</span>
                  </td>
                  <td>{{ entry.competitor }}</td>
                  <td>{{ entry.score?.toFixed(2) || 'N/A' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- Config Preview -->
          <div v-else-if="selectedPreview === 'config' && previewData?.gridInit" class="preview-config">
            <h3 style="padding: 12px 16px; margin: 0; border-bottom: 1px solid var(--border-color);">Configuration</h3>
            <div style="padding: 16px;">
              <div class="config-item">
                <span class="config-label">Competitors:</span>
                <span>{{ previewData.gridInit.competitors.length }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">Scenarios:</span>
                <span>{{ previewData.gridInit.scenarios.length }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">Total Negotiations:</span>
                <span>{{ previewData.gridInit.total_negotiations }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">Repetitions:</span>
                <span>{{ previewData.gridInit.n_repetitions }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">Rotate Ufuns:</span>
                <span>{{ previewData.gridInit.rotate_ufuns ? 'Yes' : 'No' }}</span>
              </div>
            </div>
          </div>
          
          <!-- Loading -->
          <div v-else class="preview-loading">
            <p>Loading preview...</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- New Tournament Modal -->
    <NewTournamentModal 
      v-if="showNewTournamentModal"
      :show="showNewTournamentModal"
      @close="showNewTournamentModal = false"
      @start="onTournamentStart"
    />
    
    <!-- Tag Editor Modal -->
    <Teleport to="body">
      <div v-if="tagEditorTournament" class="modal-overlay active" @click.self="closeTagEditor">
        <div class="modal" style="max-width: 500px;">
          <div class="modal-header">
            <h3>Edit Tags</h3>
            <button class="modal-close" @click="closeTagEditor">×</button>
          </div>
          <div class="modal-body">
            <p class="text-muted" style="margin-bottom: 12px;">
              {{ tagEditorTournament.name || tagEditorTournament.id }}
            </p>
            
            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; min-height: 40px; padding: 8px; background: var(--bg-secondary); border-radius: 6px;">
              <span 
                v-for="tag in tagEditorTags" 
                :key="tag"
                class="badge badge-primary"
                style="display: flex; align-items: center; gap: 6px; cursor: pointer;"
                @click="removeTagFromEditor(tag)"
              >
                {{ tag }}
                <span style="font-weight: bold;">×</span>
              </span>
              <span v-if="tagEditorTags.length === 0" class="text-muted">
                No tags yet
              </span>
            </div>
            
            <div style="display: flex; gap: 8px;">
              <input 
                type="text" 
                v-model="newTagInput" 
                @keyup.enter="addNewTag"
                placeholder="Add new tag..."
                class="form-input"
                style="flex: 1;"
              >
              <button class="btn btn-secondary" @click="addNewTag">Add</button>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeTagEditor">Cancel</button>
            <button class="btn btn-primary" @click="saveTagsFromEditor">Save</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTournamentsStore } from '../stores/tournaments'
import { storeToRefs } from 'pinia'
import NewTournamentModal from '../components/NewTournamentModal.vue'

const router = useRouter()
const tournamentsStore = useTournamentsStore()
const {
  sessions,
  loading,
  savedTournaments,
  savedTournamentsLoading,
  tournamentTagFilter,
  showArchivedTournaments,
  availableTournamentTags,
} = storeToRefs(tournamentsStore)

const showNewTournamentModal = ref(false)
const searchQuery = ref('')
const selectedPreview = ref('none')
const selectedTournament = ref(null)
const previewData = ref(null)

// Sorting
const sortColumn = ref('date')
const sortDirection = ref('desc')

// Tag editor state
const tagEditorTournament = ref(null)
const tagEditorTags = ref([])
const newTagInput = ref('')

// Running tournaments come from sessions only
const runningTournaments = computed(() => {
  return sessions.value
    .filter(s => s.status === 'running' || s.status === 'pending')
    .map(s => ({
      ...s,
      source: 'session',
      timestamp: s.created_at || s.started_at || Date.now()
    }))
})

// Completed tournaments come from saved tournaments, excluding any that are currently running
const completedTournaments = computed(() => {
  // Get IDs of running tournaments to exclude them from saved list
  const runningIds = new Set(runningTournaments.value.map(t => t.id))
  
  return savedTournaments.value
    .filter(s => !runningIds.has(s.id)) // Don't show running tournaments in completed section
    .map(s => ({
      ...s,
      source: 'saved',
      timestamp: s.created_at || s.completed_at || Date.now()
    }))
})

// For backward compatibility - combine all tournaments
const allTournaments = computed(() => {
  return [...runningTournaments.value, ...completedTournaments.value]
})

// Helper to calculate progress percentage
function getProgressPercent(tourn) {
  const total = tourn.total || 0
  const completed = tourn.completed || 0
  if (total === 0) return 0
  return Math.min(100, Math.round((completed / total) * 100))
}

// Filter and sort completed tournaments only (running shown separately)
const filteredAndSortedTournaments = computed(() => {
  let result = completedTournaments.value
  
  // Filter by tag
  if (tournamentTagFilter.value) {
    result = result.filter(tourn => tourn.tags && tourn.tags.includes(tournamentTagFilter.value))
  }
  
  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(tourn => {
      const nameMatch = (tourn.name || '').toLowerCase().includes(query)
      const idMatch = (tourn.id || '').toLowerCase().includes(query)
      return nameMatch || idMatch
    })
  }
  
  // Sort
  result.sort((a, b) => {
    let aVal, bVal
    
    switch (sortColumn.value) {
      case 'date':
        aVal = new Date(a.timestamp || 0)
        bVal = new Date(b.timestamp || 0)
        break
      case 'name':
        aVal = (a.name || a.id || '').toLowerCase()
        bVal = (b.name || b.id || '').toLowerCase()
        break
      case 'competitors':
        aVal = a.n_competitors || 0
        bVal = b.n_competitors || 0
        break
      case 'scenarios':
        aVal = a.n_scenarios || 0
        bVal = b.n_scenarios || 0
        break
      case 'status':
        aVal = a.status || 'unknown'
        bVal = b.status || 'unknown'
        break
      default:
        return 0
    }
    
    if (aVal < bVal) return sortDirection.value === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDirection.value === 'asc' ? 1 : -1
    return 0
  })
  
  return result
})

onMounted(async () => {
  await loadData()
  // Start polling for running tournaments
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

// Polling for running tournaments to update progress
let pollingInterval = null

function startPolling() {
  // Poll every 3 seconds when there are running tournaments
  pollingInterval = setInterval(async () => {
    if (runningTournaments.value.length > 0) {
      // Only reload sessions to update progress - don't reload saved
      await tournamentsStore.loadSessions()
    } else if (pollingInterval) {
      // No running tournaments, switch to slower polling
      clearInterval(pollingInterval)
      pollingInterval = setInterval(async () => {
        await tournamentsStore.loadSessions()
        // If we found running tournaments, switch back to fast polling
        if (runningTournaments.value.length > 0) {
          stopPolling()
          startPolling()
        }
      }, 10000) // Check every 10 seconds when idle
    }
  }, 3000) // Update every 3 seconds when running
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

// Watch for preview selection changes
watch(selectedPreview, (newVal) => {
  if (newVal === 'none') {
    previewData.value = null
  } else if (selectedTournament.value) {
    loadPreviewData(selectedTournament.value)
  }
})

// Watch for tournament selection changes
watch(selectedTournament, (newVal) => {
  if (newVal && selectedPreview.value !== 'none') {
    loadPreviewData(newVal)
  } else {
    previewData.value = null
  }
})

async function loadData() {
  await tournamentsStore.loadSessions()
  await tournamentsStore.loadSavedTournaments(showArchivedTournaments.value)
}

async function selectTournament(tourn) {
  selectedTournament.value = tourn
  
  if (selectedPreview.value !== 'none') {
    await loadPreviewData(tourn)
  }
}

async function loadPreviewData(tourn) {
  try {
    let fullData
    
    if (tourn.source === 'saved') {
      fullData = await tournamentsStore.loadSavedTournament(tourn.id)
    } else {
      fullData = tourn
    }
    
    if (!fullData) {
      previewData.value = null
      return
    }
    
    previewData.value = {
      id: fullData.id,
      name: fullData.name,
      gridInit: fullData.gridInit,
      cellStates: fullData.cellStates || {},
      leaderboard: fullData.leaderboard || []
    }
  } catch (error) {
    console.error('Failed to load preview data:', error)
    previewData.value = null
  }
}

function sortBy(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = 'asc'
  }
}

function formatDate(timestamp) {
  if (!timestamp) return 'Unknown'
  
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return `${mins}m ago`
  }
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}h ago`
  }
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}d ago`
  }
  
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  })
}

function getTournamentStats(tourn) {
  // Calculate statistics from tournament data
  const total = tourn.total || 0
  const completed = tourn.completed || 0
  const errors = tourn.n_errors || 0
  
  if (total === 0) {
    return { completion: 0, success: 0, errors: 0 }
  }
  
  const completion = Math.round((completed / total) * 100)
  const success = completed > 0 ? Math.round(((completed - errors) / completed) * 100) : 0
  
  return { 
    completion, 
    success, 
    errors 
  }
}

function getCellClass(competitor, scenario) {
  if (!previewData.value?.cellStates) return 'pending'
  const key = `${competitor}::${scenario}`
  const state = previewData.value.cellStates[key]
  if (!state) return 'pending'
  return state.status || 'pending'
}

function getCellContent(competitor, scenario) {
  if (!previewData.value?.cellStates) return '⋯'
  const key = `${competitor}::${scenario}`
  const state = previewData.value.cellStates[key]
  if (!state) return '⋯'
  
  if (state.status === 'running') return '⟳'
  if (state.status === 'pending') return '⋯'
  if (state.status === 'failed') return '✗'
  
  if (state.utility !== undefined) {
    return state.utility.toFixed(2)
  }
  
  return '✓'
}

function viewTournament(tournamentId) {
  router.push({ name: 'SingleTournament', params: { id: tournamentId } })
}

async function deleteSavedTourn(tournamentId) {
  if (confirm('Are you sure you want to delete this saved tournament?')) {
    try {
      console.log('[TournamentsListView] Deleting tournament:', tournamentId)
      await tournamentsStore.deleteSavedTournament(tournamentId)
      console.log('[TournamentsListView] Tournament deleted successfully')
      
      // Clear selection if deleted tournament was selected
      if (selectedTournament.value?.id === tournamentId) {
        selectedTournament.value = null
        previewData.value = null
      }
    } catch (error) {
      console.error('[TournamentsListView] Failed to delete tournament:', error)
      alert(`Failed to delete tournament: ${error.message}`)
    }
  }
}

function editTournamentTags(tourn) {
  tagEditorTournament.value = tourn
  tagEditorTags.value = [...(tourn.tags || [])]
  newTagInput.value = ''
}

function closeTagEditor() {
  tagEditorTournament.value = null
  tagEditorTags.value = []
  newTagInput.value = ''
}

function removeTagFromEditor(tag) {
  const index = tagEditorTags.value.indexOf(tag)
  if (index > -1) {
    tagEditorTags.value.splice(index, 1)
  }
}

function addNewTag() {
  const tag = newTagInput.value.trim()
  if (tag && !tagEditorTags.value.includes(tag)) {
    tagEditorTags.value.push(tag)
    newTagInput.value = ''
  }
}

async function saveTagsFromEditor() {
  if (tagEditorTournament.value) {
    await tournamentsStore.updateTournamentTags(
      tagEditorTournament.value.id,
      tagEditorTags.value
    )
    closeTagEditor()
  }
}

function onTournamentStart(data) {
  showNewTournamentModal.value = false
  
  if (data.session_id) {
    router.push({ name: 'SingleTournament', params: { id: data.session_id } })
  }
}

async function continueTournament(tournamentId) {
  try {
    const response = await fetch(`/api/tournament/saved/${tournamentId}/continue`, {
      method: 'POST'
    })
    
    if (!response.ok) {
      const error = await response.json()
      alert(`Failed to continue tournament: ${error.detail || 'Unknown error'}`)
      return
    }
    
    const data = await response.json()
    // Navigate to tournament view with streaming
    router.push({ name: 'SingleTournament', params: { id: data.session_id } })
  } catch (error) {
    console.error('Failed to continue tournament:', error)
    alert(`Failed to continue tournament: ${error.message}`)
  }
}

async function stopTournament(tourn) {
  if (!confirm(`Stop tournament ${tourn.name || tourn.id}?`)) {
    return
  }
  
  try {
    // Find the session ID if this is a running session
    let sessionId = tourn.id
    if (tourn.source === 'session' && tourn.session_id) {
      sessionId = tourn.session_id
    }
    
    const response = await fetch(`/api/tournament/${sessionId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delete_results: false })
    })
    
    if (!response.ok) {
      const error = await response.json()
      alert(`Failed to stop tournament: ${error.detail || 'Unknown error'}`)
      return
    }
    
    // Refresh tournament list
    await loadData()
    
    // Clear selection if we stopped the selected tournament
    if (selectedTournament.value?.id === tourn.id) {
      selectedTournament.value = null
      previewData.value = null
    }
  } catch (error) {
    console.error('Failed to stop tournament:', error)
    alert(`Failed to stop tournament: ${error.message}`)
  }
}
</script>

<style scoped>
.tournaments-list-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.content-area {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border-right: 1px solid var(--border-color);
  transition: width 0.3s ease;
  overflow: auto;
}

/* Running Tournaments Section */
.running-section {
  flex-shrink: 0;
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.section-header {
  padding: 8px 16px;
  background: var(--bg-secondary);
}

.section-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.running-table-wrapper {
  overflow-x: auto;
}

.running-tournaments-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.running-tournaments-table thead {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.running-tournaments-table th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.running-tournaments-table tbody tr {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.running-tournaments-table tbody tr:hover {
  background: var(--bg-hover);
}

.running-tournaments-table tbody tr.selected {
  background: rgba(59, 130, 246, 0.1);
}

.running-tournaments-table tbody tr.clickable-row {
  cursor: pointer;
}

.running-tournaments-table td {
  padding: 8px 12px;
}

.tournament-name {
  font-weight: 500;
}

.session-id {
  font-size: 10px;
  color: var(--text-muted);
  font-family: monospace;
  margin-top: 2px;
}

.progress-cell {
  min-width: 120px;
}

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-text {
  font-size: 11px;
  color: var(--text-secondary);
}

.progress-bar-mini {
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
}

/* Completed Tournaments Section */
.completed-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.completed-section .section-header {
  flex-shrink: 0;
}

.search-bar {
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  position: relative;
}

.tournaments-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.tournaments-table thead {
  position: sticky;
  top: 0;
  background: var(--bg-secondary);
  z-index: 10;
  border-bottom: 2px solid var(--border-color);
}

.tournaments-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.tournaments-table th:hover {
  background: var(--bg-hover);
}

.tournaments-table tbody tr {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.tournaments-table tbody tr:hover {
  background: var(--bg-hover);
}

.tournaments-table tbody tr.selected {
  background: rgba(59, 130, 246, 0.1);
}

.tournaments-table tbody tr.clickable-row {
  cursor: pointer;
}

.tournaments-table td {
  padding: 12px 16px;
}

.date-cell {
  color: var(--text-secondary);
  font-size: 13px;
}

.name-cell {
  font-weight: 500;
}

.count-cell {
  text-align: center;
  color: var(--text-secondary);
}

.stats-cell {
  padding: 8px 12px !important;
}

.tournament-stats {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  gap: 8px;
}

.stat-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-value {
  font-weight: 600;
  color: var(--text-primary);
}

.stat-error {
  color: rgb(239, 68, 68);
}

.text-muted {
  color: var(--text-secondary);
  font-size: 12px;
}

.status-cell .badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-running {
  background: rgba(59, 130, 246, 0.2);
  color: rgb(59, 130, 246);
}

.badge-pending {
  background: rgba(245, 158, 11, 0.2);
  color: rgb(245, 158, 11);
}

.badge-completed {
  background: rgba(16, 185, 129, 0.2);
  color: rgb(16, 185, 129);
}

.badge-failed {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.tags-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag-badge {
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 3px;
  font-size: 11px;
  color: var(--text-secondary);
}

.tag-more {
  font-size: 11px;
  color: var(--text-secondary);
}

.actions-cell {
  display: flex;
  gap: 4px;
}

.btn-icon-small {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-icon-small:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.btn-icon-small.btn-success {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.btn-icon-small.btn-success:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: #10b981;
}

.btn-icon-small.btn-danger {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.btn-icon-small.btn-danger:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
}

.btn-icon-small.btn-danger-text {
  color: #ef4444;
}

.btn-icon-small.btn-danger-text:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
}

.empty-state,
.loading-state {
  padding: 48px 24px;
  text-align: center;
  color: var(--text-secondary);
}

.preview-container {
  width: 33.33%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  overflow: hidden;
}

.preview-empty,
.preview-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.preview-content {
  flex: 1;
  overflow: auto;
}

.tournament-grid-compact {
  display: inline-block;
  font-size: 11px;
}

.grid-header,
.grid-row {
  display: flex;
}

.grid-corner,
.grid-header-cell,
.grid-row-header,
.grid-cell {
  border: 1px solid var(--border-color);
  padding: 4px 6px;
  text-align: center;
}

.grid-corner {
  width: 100px;
  background: var(--bg-tertiary);
}

.grid-header-cell {
  width: 60px;
  background: var(--bg-tertiary);
  font-weight: 600;
}

.grid-row-header {
  width: 100px;
  background: var(--bg-tertiary);
  font-weight: 600;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grid-cell {
  width: 60px;
  font-family: monospace;
}

.grid-cell.pending {
  background: var(--bg-primary);
}

.grid-cell.running {
  background: rgba(59, 130, 246, 0.1);
  color: rgb(59, 130, 246);
}

.grid-cell.completed {
  background: rgba(16, 185, 129, 0.1);
}

.grid-cell.failed {
  background: rgba(239, 68, 68, 0.1);
  color: rgb(239, 68, 68);
}

.leaderboard-table-compact {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.leaderboard-table-compact th,
.leaderboard-table-compact td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.leaderboard-table-compact th {
  background: var(--bg-tertiary);
  font-weight: 600;
  position: sticky;
  top: 0;
}

.leaderboard-table-compact .rank-cell {
  text-align: center;
  font-weight: 600;
}

.config-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.config-label {
  font-weight: 600;
  color: var(--text-secondary);
}

.form-select {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
}

.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
}
</style>
