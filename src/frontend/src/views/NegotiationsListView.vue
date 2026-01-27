<template>
  <div class="negotiations-list-container">
    <!-- Header -->
    <div class="list-header">
      <div class="header-left">
        <!-- Tournament mode: back button + tournament name -->
        <template v-if="isTournamentMode">
          <button class="btn btn-ghost btn-sm" @click="goBackToTournament">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            Back to Tournament
          </button>
          <h2>{{ currentTournament?.name || 'Tournament Negotiations' }}</h2>
        </template>
        
        <!-- Normal mode: title + new button -->
        <template v-else>
          <h2>Negotiations</h2>
          <button class="btn btn-primary" @click="showNewNegotiationModal = true">
            + New Negotiation
          </button>
        </template>
      </div>
      <div class="header-right">
        <!-- Active Filters Display -->
        <div v-if="route.query.competitor || route.query.opponent || route.query.scenario" class="active-filters">
          <span class="filter-label">Filters:</span>
          <span v-if="route.query.competitor" class="filter-badge">
            Competitor: {{ route.query.competitor }}
            <button class="filter-remove" @click="removeFilter('competitor')" title="Remove filter">×</button>
          </span>
          <span v-if="route.query.opponent" class="filter-badge">
            Opponent: {{ route.query.opponent }}
            <button class="filter-remove" @click="removeFilter('opponent')" title="Remove filter">×</button>
          </span>
          <span v-if="route.query.scenario" class="filter-badge">
            Scenario: {{ route.query.scenario.split('/').pop() }}
            <button class="filter-remove" @click="removeFilter('scenario')" title="Remove filter">×</button>
          </span>
          <button class="btn-clear-filters" @click="clearAllFilters">Clear All</button>
        </div>
        
        <!-- Preview Selector -->
        <label style="display: flex; align-items: center; gap: 8px; font-size: 14px;">
          <span>Preview:</span>
          <select v-model="selectedPreview" class="form-select">
            <option value="none">None</option>
            <option value="utility2d">2D Utility Space</option>
            <option value="timeline">Timeline</option>
            <option value="histogram">Histogram</option>
            <option value="result">Result</option>
          </select>
        </label>
        
        <!-- Filters (hidden in tournament mode) -->
        <template v-if="!isTournamentMode">
          <select v-model="tagFilter" class="form-select" style="width: 150px;">
            <option value="">All Tags</option>
            <option v-for="tag in availableTags" :key="tag" :value="tag">{{ tag }}</option>
          </select>
          
          <label style="display: flex; align-items: center; gap: 6px; font-size: 14px;">
            <input type="checkbox" v-model="showArchived" @change="loadData">
            <span>Archived</span>
          </label>
        </template>
        
        <button class="btn btn-secondary" @click="loadData" :disabled="loading" title="Refresh">
          <span v-if="loading">⟳</span>
          <span v-else>↻</span>
        </button>
      </div>
    </div>
    
    <!-- Content Area -->
    <div class="content-area" :class="{ 'with-preview': selectedPreview !== 'none' }">
      <!-- Tables Container -->
      <div class="table-container" :class="{ 'with-preview': selectedPreview !== 'none' }">
        <!-- Running Negotiations Section -->
        <div v-if="runningNegotiations.length > 0" class="running-section">
          <div class="section-header">
            <h3>Running Negotiations ({{ runningNegotiations.length }})</h3>
          </div>
          <div class="running-table-wrapper">
            <table class="running-negotiations-table">
              <thead>
                <tr>
                  <th style="width: 180px;">Scenario</th>
                  <th style="width: 200px;">Negotiators</th>
                  <th style="width: 120px;">Progress</th>
                  <th style="width: 80px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="neg in runningNegotiations" 
                  :key="neg.id"
                  @click="selectNegotiation(neg)"
                  :class="{ 'selected': selectedNegotiation?.id === neg.id }"
                  class="clickable-row"
                >
                  <td class="scenario-cell">
                    <div class="scenario-name">{{ neg.scenario_name || 'Unknown' }}</div>
                    <div class="session-id">{{ neg.id }}</div>
                  </td>
                  <td class="negotiators-cell">
                    <div class="negotiators-list">
                      <span 
                        v-for="(name, idx) in neg.negotiator_names" 
                        :key="idx"
                        class="negotiator-badge-sm"
                        :style="{ background: getNegotiatorColor(idx, neg.negotiator_colors) }"
                      >
                        {{ name }}
                      </span>
                    </div>
                  </td>
                  <td class="progress-cell">
                    <div class="progress-info">
                      <div class="progress-text">
                        {{ formatRelativeTime(neg.relative_time) }}
                      </div>
                      <div class="progress-bar-mini">
                        <div 
                          class="progress-bar-fill" 
                          :style="{ width: getRelativeTimePercent(neg.relative_time) + '%' }"
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td class="actions-cell" @click.stop>
                    <button 
                      class="btn-icon-small" 
                      @click="viewNegotiation(neg.id)" 
                      title="View full details"
                    >
                      👁️
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <!-- Saved/Completed Negotiations Section -->
        <div class="saved-section">
          <div class="section-header">
            <h3>Saved & Completed Negotiations ({{ completedNegotiations.length }})</h3>
          </div>
          
          <!-- Search -->
          <div class="search-bar">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Search by scenario name, negotiators, or ID..."
              class="search-input"
            >
          </div>
          
          <!-- Table -->
          <div class="table-wrapper">
            <table class="negotiations-table">
            <thead>
              <tr>
                <th style="width: 160px;" @click="sortBy('date')">
                  Date
                  <span v-if="sortColumn === 'date'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                </th>
                <th style="width: 140px;">
                  Negotiation ID
                </th>
                <th @click="sortBy('scenario')">
                  Scenario
                  <span v-if="sortColumn === 'scenario'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                </th>
                <th @click="sortBy('negotiators')">
                  Negotiators
                  <span v-if="sortColumn === 'negotiators'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                </th>
                <th style="width: 140px;" @click="sortBy('result')">
                  Result
                  <span v-if="sortColumn === 'result'">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span>
                </th>
                <th style="width: 100px;">Tags</th>
                <th style="width: 100px;">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="neg in filteredAndSortedNegotiations" 
                :key="neg.id"
                @click="selectNegotiation(neg)"
                :class="{ 'selected': selectedNegotiation?.id === neg.id }"
                class="clickable-row"
              >
                <td class="date-cell">{{ formatDate(neg.timestamp || neg.created_at) }}</td>
                <td class="id-cell">{{ neg.id }}</td>
                <td class="scenario-cell">{{ neg.scenario_name || 'Unknown' }}</td>
                <td class="negotiators-cell">
                  <div class="negotiators-list">
                    <span 
                      v-for="(name, idx) in neg.negotiator_names" 
                      :key="idx"
                      class="negotiator-badge"
                      :style="{ background: getNegotiatorColor(idx, neg.negotiator_colors) }"
                    >
                      {{ name }}
                    </span>
                  </div>
                </td>
                <td class="result-cell">
                  <span v-if="neg.status === 'running'" class="badge badge-running" :title="getResultTooltip(neg)">Running</span>
                  <span v-else-if="neg.status === 'pending'" class="badge badge-pending" :title="getResultTooltip(neg)">Pending</span>
                  <span v-else-if="neg.status === 'failed'" class="badge badge-failed" :title="getResultTooltip(neg)">Failed</span>
                  <span v-else-if="neg.agreement" class="badge badge-agreement" :title="getResultTooltip(neg)">Agreement</span>
                  <span v-else-if="neg.end_reason === 'timedout'" class="badge badge-timeout" :title="getResultTooltip(neg)">Timeout</span>
                  <span v-else class="badge badge-disagreement" :title="getResultTooltip(neg)">Disagreement</span>
                </td>
                <td class="tags-cell">
                  <div class="tags-list">
                    <span 
                      v-for="tag in (neg.tags || []).slice(0, 2)" 
                      :key="tag"
                      class="tag-badge"
                    >
                      {{ tag }}
                    </span>
                    <span v-if="(neg.tags || []).length > 2" class="tag-more">
                      +{{ (neg.tags || []).length - 2 }}
                    </span>
                  </div>
                </td>
                <td class="actions-cell" @click.stop>
                  <button 
                    class="btn-icon-small" 
                    @click="viewNegotiation(neg.id)" 
                    title="View full details"
                  >
                    👁️
                  </button>
                  
                  <!-- Hide these buttons in tournament mode -->
                  <template v-if="!isTournamentMode">
                    <button 
                      class="btn-icon-small" 
                      @click="rerunNegotiation(neg.id)" 
                      title="Rerun negotiation"
                    >
                      🔄
                    </button>
                    <button 
                      class="btn-icon-small" 
                      @click="editTags(neg)" 
                      title="Edit tags"
                    >
                      🏷️
                    </button>
                    <button 
                      class="btn-icon-small" 
                      @click="deleteSaved(neg.id)" 
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
          
          <!-- Empty State -->
          <div v-if="filteredAndSortedNegotiations.length === 0 && !loading" class="empty-state">
            <p v-if="searchQuery">No negotiations match your search</p>
            <p v-else-if="tagFilter">No negotiations with tag "{{ tagFilter }}"</p>
            <p v-else>No negotiations yet. Start a new one!</p>
          </div>
          
          <!-- Loading State -->
          <div v-if="loading" class="loading-state">
            <p>Loading negotiations...</p>
          </div>
        </div>
        </div>
      </div>
      
      <!-- Preview Panel -->
      <div v-if="selectedPreview !== 'none'" class="preview-container">
        <div v-if="!selectedNegotiation" class="preview-empty">
          <p>Select a negotiation to preview</p>
        </div>
        <div v-else class="preview-content">
          <!-- Always show Result Panel at top when previewing other panels -->
          <div 
            v-if="selectedPreview !== 'result' && previewData" 
            class="preview-result-header"
          >
            <ResultPanel 
              :negotiation="previewData"
              :compact="true"
            />
          </div>
          
          <!-- Selected preview panel below (or full height if Result is selected) -->
          <div class="preview-panel-main">
            <component 
              :is="previewComponent" 
              v-if="previewComponent && previewData"
              :key="`${selectedNegotiation?.id}-${selectedPreview}`"
              :negotiation="previewData"
              :compact="true"
            />
            <div v-else class="preview-loading">
              <p>Loading preview...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- New Negotiation Modal -->
    <NewNegotiationModal 
      v-if="showNewNegotiationModal"
      :show="showNewNegotiationModal"
      @close="showNewNegotiationModal = false"
      @start="onNegotiationStart"
    />
    
    <!-- Tag Editor Modal -->
    <Teleport to="body">
      <div v-if="tagEditorNegotiation" class="modal-overlay active" @click.self="closeTagEditor">
        <div class="modal" style="max-width: 500px;">
          <div class="modal-header">
            <h3>Edit Tags</h3>
            <button class="modal-close" @click="closeTagEditor">×</button>
          </div>
          <div class="modal-body">
            <p class="text-muted" style="margin-bottom: 12px;">
              {{ tagEditorNegotiation.scenario_name }}
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
import { ref, onMounted, onUnmounted, computed, watch, shallowRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useNegotiationsStore } from '../stores/negotiations'
import { useTournamentsStore } from '../stores/tournaments'
import { storeToRefs } from 'pinia'
import NewNegotiationModal from '../components/NewNegotiationModal.vue'
import Utility2DPanel from '../components/panels/Utility2DPanel.vue'
import TimelinePanel from '../components/panels/TimelinePanel.vue'
import HistogramPanel from '../components/panels/HistogramPanel.vue'
import ResultPanel from '../components/panels/ResultPanel.vue'

const router = useRouter()
const route = useRoute()
const negotiationsStore = useNegotiationsStore()
const tournamentsStore = useTournamentsStore()

// Tournament mode detection
const tournamentId = computed(() => route.params.tournamentId)
const isTournamentMode = computed(() => !!tournamentId.value)
const currentTournament = ref(null)

// Store refs
const {
  sessions,
  loading,
  savedNegotiations,
  savedNegotiationsLoading,
  tagFilter,
  showArchived,
  availableTags,
} = storeToRefs(negotiationsStore)

// Tournament store refs (for tournament mode)
const {
  currentSession: tournamentSession,
  liveNegotiations: tournamentLiveNegotiations,
  runningNegotiations: tournamentRunningNegotiations,
} = storeToRefs(tournamentsStore)

const showNewNegotiationModal = ref(false)
const searchQuery = ref('')
const selectedPreview = ref('utility2d')
const selectedNegotiation = ref(null)
const previewData = ref(null)
const previewComponent = shallowRef(null)

// Sorting
const sortColumn = ref('date')
const sortDirection = ref('desc')

// Tag editor state
const tagEditorNegotiation = ref(null)
const tagEditorTags = ref([])
const newTagInput = ref('')

// Data conversion utilities for tournament negotiations
function convertTournamentRunningNegotiation(neg) {
  // Convert from tournament running negotiation format to negotiation list format
  return {
    id: neg.run_id || neg.id,
    status: 'running',
    scenario_name: neg.scenario || 'Unknown',
    negotiator_names: neg.negotiator_names || [`Agent 0`, `Agent 1`],
    negotiator_colors: neg.negotiator_colors || ['#3b82f6', '#ef4444'],
    current_step: neg.step || 0,
    relative_time: neg.relative_time || 0,
    n_steps: neg.n_steps,
    created_at: neg.started_at || Date.now(),
  }
}

function convertTournamentCompletedNegotiation(neg) {
  // Convert from tournament completed negotiation format to negotiation list format
  const scenarioName = neg.scenario ? 
    neg.scenario.split('/').pop() : 
    'Unknown'
  
  return {
    id: neg.id || `neg_${neg.index}`,
    status: neg.has_error ? 'failed' : 'completed',
    scenario_name: scenarioName,
    negotiator_names: neg.partners || [],
    negotiator_colors: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'].slice(0, (neg.partners || []).length),
    agreement: neg.agreement,
    agreement_dict: neg.agreement_dict,
    final_utilities: neg.utilities || [],
    has_agreement: neg.has_agreement,
    end_reason: neg.has_error ? 'error' : (neg.has_agreement ? 'agreement' : 'disagreement'),
    timestamp: neg.timestamp || Date.now(),
    source: 'tournament',
    index: neg.index,
  }
}

// Separate running from completed negotiations
const runningNegotiations = computed(() => {
  if (isTournamentMode.value) {
    // Use tournament store's runningNegotiations (plain object)
    if (!tournamentRunningNegotiations.value) return []
    return Object.values(tournamentRunningNegotiations.value)
      .map(neg => convertTournamentRunningNegotiation(neg))
  } else {
    // Use negotiations store's sessions
    return sessions.value.filter(s => 
      s.status === 'running' || s.status === 'pending'
    )
  }
})

const completedNegotiations = computed(() => {
  if (isTournamentMode.value) {
    // Use tournament store's liveNegotiations
    if (!tournamentLiveNegotiations.value) return []
    return tournamentLiveNegotiations.value
      .map(neg => convertTournamentCompletedNegotiation(neg))
  } else {
    // Use negotiations store's sessions + savedNegotiations
    return [
      ...sessions.value.filter(s => 
        s.status === 'completed' || s.status === 'failed'
      ).map(s => ({
        ...s,
        source: 'session',
        timestamp: s.created_at || s.started_at || Date.now()
      })),
      ...savedNegotiations.value.map(s => ({
        ...s,
        source: 'saved',
        timestamp: s.created_at || s.completed_at || Date.now()
      }))
    ]
  }
})

// Combine all negotiations (sessions + saved) - for backward compatibility
const allNegotiations = computed(() => {
  return [...runningNegotiations.value, ...completedNegotiations.value]
})

// Filter by search query and tags (only completed negotiations)
const filteredAndSortedNegotiations = computed(() => {
  let result = completedNegotiations.value
  
  // Filter by query parameters (from grid cell click)
  if (route.query.competitor || route.query.opponent || route.query.scenario) {
    result = result.filter(neg => {
      const negotiatorNames = neg.negotiator_names || []
      const scenarioName = neg.scenario_name || ''
      
      let match = true
      
      // Filter by competitor (first negotiator)
      if (route.query.competitor) {
        match = match && negotiatorNames.some(name => name.includes(route.query.competitor))
      }
      
      // Filter by opponent (second negotiator)
      if (route.query.opponent) {
        match = match && negotiatorNames.some(name => name.includes(route.query.opponent))
      }
      
      // Filter by scenario
      if (route.query.scenario) {
        const scenarioShort = route.query.scenario.split('/').pop()
        match = match && scenarioName.includes(scenarioShort)
      }
      
      return match
    })
  }
  
  // Filter by tag
  if (tagFilter.value) {
    result = result.filter(neg => neg.tags && neg.tags.includes(tagFilter.value))
  }
  
  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(neg => {
      const scenarioMatch = (neg.scenario_name || '').toLowerCase().includes(query)
      const negotiatorsMatch = (neg.negotiator_names || []).some(name => 
        name.toLowerCase().includes(query)
      )
      const idMatch = (neg.id || '').toLowerCase().includes(query)
      return scenarioMatch || negotiatorsMatch || idMatch
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
      case 'scenario':
        aVal = (a.scenario_name || '').toLowerCase()
        bVal = (b.scenario_name || '').toLowerCase()
        break
      case 'negotiators':
        aVal = (a.negotiator_names || []).join(',').toLowerCase()
        bVal = (b.negotiator_names || []).join(',').toLowerCase()
        break
      case 'result':
        aVal = getResultText(a)
        bVal = getResultText(b)
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
  // Add keyboard event listener for arrow navigation
  window.addEventListener('keydown', handleKeyNavigation)
  
  // Start polling for running negotiations
  startPolling()
})

onUnmounted(() => {
  // Clean up keyboard event listener
  window.removeEventListener('keydown', handleKeyNavigation)
  
  // Stop polling
  stopPolling()
})

// Keyboard navigation
function handleKeyNavigation(event) {
  // Only handle if not typing in an input/textarea
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.tagName === 'SELECT') {
    return
  }
  
  const negotiations = filteredAndSortedNegotiations.value
  if (negotiations.length === 0) return
  
  const currentIndex = selectedNegotiation.value 
    ? negotiations.findIndex(n => n.id === selectedNegotiation.value.id)
    : -1
  
  let newIndex = -1
  
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    // Move to next negotiation, or select first if none selected
    newIndex = currentIndex === -1 ? 0 : Math.min(currentIndex + 1, negotiations.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    // Move to previous negotiation, or select last if none selected
    newIndex = currentIndex === -1 ? negotiations.length - 1 : Math.max(currentIndex - 1, 0)
  }
  
  if (newIndex !== -1 && newIndex !== currentIndex) {
    selectNegotiation(negotiations[newIndex])
    
    // Scroll the selected row into view
    const tableBody = document.querySelector('.negotiations-table tbody')
    const selectedRow = tableBody?.children[newIndex]
    if (selectedRow) {
      selectedRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }
}

// Watch for preview selection changes
watch(selectedPreview, (newVal) => {
  if (newVal === 'none') {
    previewComponent.value = null
    previewData.value = null
  } else if (selectedNegotiation.value) {
    loadPreviewData(selectedNegotiation.value)
  }
})

// Watch for negotiation selection changes
watch(selectedNegotiation, (newVal) => {
  if (newVal && selectedPreview.value !== 'none') {
    loadPreviewData(newVal)
  } else {
    previewData.value = null
  }
})

async function loadData() {
  if (isTournamentMode.value) {
    // Load tournament session data
    try {
      const tournament = await tournamentsStore.loadSavedTournament(tournamentId.value)
      currentTournament.value = tournament
      
      // If tournament is running, ensure we're connected to SSE
      if (tournament && tournament.status === 'running') {
        await tournamentsStore.connectToTournament(tournamentId.value)
      } else if (tournament && tournament.is_complete) {
        // For completed tournaments, load negotiation details
        await tournamentsStore.loadTournamentNegotiations(tournamentId.value)
      }
    } catch (error) {
      console.error('Failed to load tournament:', error)
    }
  } else {
    // Normal mode: load from negotiations store
    await negotiationsStore.loadSessions()
    await negotiationsStore.loadSavedNegotiations(showArchived.value)
  }
}

// Navigation helper for tournament mode
function goBackToTournament() {
  if (tournamentId.value) {
    router.push({ name: 'SingleTournament', params: { id: tournamentId.value } })
  }
}

// Filter management
function removeFilter(filterName) {
  const query = { ...route.query }
  delete query[filterName]
  router.replace({ query })
}

function clearAllFilters() {
  router.replace({ query: {} })
}

// Polling for running negotiations (only in normal mode)
let pollingInterval = null

function startPolling() {
  // Don't poll in tournament mode - we use SSE instead
  if (isTournamentMode.value) {
    console.log('[NegotiationsListView] Tournament mode - using SSE, no polling needed')
    return
  }
  
  console.log('[NegotiationsListView] Starting polling')
  // Poll every 2 seconds when there are running negotiations
  pollingInterval = setInterval(async () => {
    if (runningNegotiations.value.length > 0) {
      console.log('[NegotiationsListView] Polling: found', runningNegotiations.value.length, 'running negotiations')
      // Only reload sessions (not saved negotiations) to update progress
      await negotiationsStore.loadSessions()
      console.log('[NegotiationsListView] Sessions reloaded, current_step:', 
        runningNegotiations.value.map(n => ({ id: n.id, step: n.current_step })))
      
      // If a running negotiation is selected for preview, reload its preview data
      if (selectedNegotiation.value && 
          selectedNegotiation.value.status === 'running' && 
          selectedPreview.value !== 'none') {
        // Find the updated session data
        const updatedSession = negotiationsStore.sessions.find(s => s.id === selectedNegotiation.value.id)
        if (updatedSession) {
          // Update selectedNegotiation with latest data
          selectedNegotiation.value = updatedSession
          // Reload preview with updated data
          await loadPreviewData(updatedSession)
          console.log('[NegotiationsListView] Updated preview for running negotiation:', updatedSession.id)
        }
      }
    } else if (pollingInterval) {
      // No running negotiations, reduce polling frequency
      // This will catch when a negotiation completes and moves to saved
      console.log('[NegotiationsListView] No running negotiations, switching to slow polling')
      clearInterval(pollingInterval)
      pollingInterval = setInterval(async () => {
        await negotiationsStore.loadSessions()
        await negotiationsStore.loadSavedNegotiations(showArchived.value)
        
        // If we found running negotiations, switch back to fast polling
        if (runningNegotiations.value.length > 0) {
          stopPolling()
          startPolling()
        }
      }, 10000) // Check every 10 seconds when idle
    }
  }, 2000) // Update every 2 seconds when running
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

async function selectNegotiation(neg) {
  selectedNegotiation.value = neg
  
  if (selectedPreview.value !== 'none') {
    await loadPreviewData(neg)
  }
}

async function loadPreviewData(neg) {
  try {
    // Load full negotiation data if not already loaded
    let fullData
    
    if (neg.source === 'saved') {
      fullData = await negotiationsStore.loadSavedNegotiation(neg.id)
    } else {
      // For running/completed sessions, get full session data from API
      fullData = await negotiationsStore.getSession(neg.id)
    }
    
    if (!fullData) {
      previewData.value = null
      return
    }
    
    // Format data for preview panels
    previewData.value = {
      id: fullData.id,
      source: neg.source, // Add source field for preview image detection
      saved_at: fullData.created_at || fullData.start_time || neg.created_at, // For cache busting
      scenario_name: fullData.scenario_name,
      negotiator_names: fullData.negotiator_names,
      negotiator_colors: fullData.negotiator_colors,
      issue_names: fullData.issue_names,
      n_steps: fullData.n_steps,
      step: fullData.current_step || fullData.step,
      relative_time: fullData.relative_time || (fullData.offers?.[fullData.offers.length - 1]?.relative_time) || 0,
      offers: fullData.offers || [],
      outcome_space_data: fullData.outcome_space_data,
      agreement: fullData.agreement,
      final_utilities: fullData.final_utilities,
      optimality_stats: fullData.optimality_stats,
      end_reason: fullData.end_reason,
      status: fullData.status,
      isSaved: neg.source === 'saved'
    }
    
    // Set preview component based on selection
    switch (selectedPreview.value) {
      case 'utility2d':
        previewComponent.value = Utility2DPanel
        break
      case 'timeline':
        previewComponent.value = TimelinePanel
        break
      case 'histogram':
        previewComponent.value = HistogramPanel
        break
      case 'result':
        previewComponent.value = ResultPanel
        break
      default:
        previewComponent.value = null
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
  
  // Less than 1 minute
  if (diff < 60000) return 'Just now'
  
  // Less than 1 hour
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return `${mins}m ago`
  }
  
  // Less than 24 hours
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}h ago`
  }
  
  // Less than 7 days
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}d ago`
  }
  
  // Format as date
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  })
}

function getResultText(neg) {
  if (neg.status === 'running') return 'Running'
  if (neg.status === 'pending') return 'Pending'
  if (neg.status === 'failed') return 'Failed'
  if (neg.agreement) return 'Agreement'
  if (neg.end_reason === 'timedout') return 'Timeout'
  return 'Disagreement'
}

function getNegotiatorColor(index, colors) {
  if (colors && colors[index]) return colors[index]
  
  const fallbackColors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
  return fallbackColors[index % fallbackColors.length]
}

function getRelativeTimePercent(relativeTime) {
  if (relativeTime === undefined || relativeTime === null) return 0
  // relative_time is 0.0 to 1.0, convert to percentage
  return Math.min(100, Math.max(0, relativeTime * 100))
}

function formatRelativeTime(relativeTime) {
  if (relativeTime === undefined || relativeTime === null) return 'Starting...'
  // Format as percentage with 1 decimal place
  const percent = relativeTime * 100
  return `${percent.toFixed(1)}%`
}

function getProgressPercent(neg) {
  // Fallback for compatibility - prefer relative_time
  if (neg.relative_time !== undefined && neg.relative_time !== null) {
    return getRelativeTimePercent(neg.relative_time)
  }
  if (!neg.n_steps || !neg.current_step) return 0
  return Math.min(100, (neg.current_step / neg.n_steps) * 100)
}

function getResultTooltip(neg) {
  const tooltip = []
  
  // Add status
  tooltip.push(`Status: ${neg.status || 'Unknown'}`)
  
  // Add end reason if available
  if (neg.end_reason) {
    tooltip.push(`End Reason: ${neg.end_reason}`)
  }
  
  // Add error if failed
  if (neg.error) {
    tooltip.push(`Error: ${neg.error}`)
  }
  
  // Add agreement details if available
  if (neg.agreement_dict && Object.keys(neg.agreement_dict).length > 0) {
    tooltip.push('\nAgreement:')
    Object.entries(neg.agreement_dict).forEach(([key, value]) => {
      tooltip.push(`  ${key}: ${value}`)
    })
  } else if (neg.agreement) {
    tooltip.push(`\nAgreement: ${JSON.stringify(neg.agreement)}`)
  }
  
  // Add final utilities if available
  if (neg.final_utilities && neg.final_utilities.length > 0) {
    tooltip.push('\nFinal Utilities:')
    neg.final_utilities.forEach((utility, idx) => {
      const name = neg.negotiator_names?.[idx] || `Agent ${idx}`
      tooltip.push(`  ${name}: ${utility.toFixed(3)}`)
    })
  }
  
  // Add step count if available
  if (neg.n_steps !== undefined) {
    tooltip.push(`\nSteps: ${neg.current_step || neg.step || 0}/${neg.n_steps}`)
  }
  
  return tooltip.length > 0 ? tooltip.join('\n') : 'No additional information'
}

function viewNegotiation(sessionId) {
  router.push({ name: 'SingleNegotiation', params: { id: sessionId } })
}

async function rerunNegotiation(sessionId) {
  try {
    const data = await negotiationsStore.rerunNegotiation(sessionId)
    
    if (data?.session_id) {
      // Extract step_delay and share_ufuns from the stream_url
      const url = new URL(data.stream_url, window.location.origin)
      const stepDelay = parseFloat(url.searchParams.get('step_delay') || '0.1')
      const shareUfuns = url.searchParams.get('share_ufuns') === 'true'
      
      // Start streaming the new negotiation
      negotiationsStore.startStreaming(data.session_id, stepDelay, shareUfuns)
      
      // Navigate to the new negotiation
      router.push({ name: 'SingleNegotiation', params: { id: data.session_id } })
    }
  } catch (error) {
    console.error('Failed to rerun negotiation:', error)
    alert('Failed to rerun negotiation: ' + error.message)
  }
}

async function deleteSaved(sessionId) {
  if (confirm('Are you sure you want to delete this saved negotiation?')) {
    await negotiationsStore.deleteSavedNegotiation(sessionId)
    
    // Clear selection if deleted
    if (selectedNegotiation.value?.id === sessionId) {
      selectedNegotiation.value = null
      previewData.value = null
    }
  }
}

function editTags(neg) {
  tagEditorNegotiation.value = neg
  tagEditorTags.value = [...(neg.tags || [])]
  newTagInput.value = ''
}

function closeTagEditor() {
  tagEditorNegotiation.value = null
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
  if (tagEditorNegotiation.value) {
    await negotiationsStore.updateNegotiationTags(
      tagEditorNegotiation.value.id,
      tagEditorTags.value
    )
    await loadData()  // Reload to show updated tags
    closeTagEditor()
  }
}

function onNegotiationStart(data) {
  showNewNegotiationModal.value = false
  
  if (data.session_id) {
    // Start streaming immediately before navigation
    // Extract step_delay and share_ufuns from the stream_url
    const url = new URL(data.stream_url, window.location.origin)
    const stepDelay = parseFloat(url.searchParams.get('step_delay') || '0.1')
    const shareUfuns = url.searchParams.get('share_ufuns') === 'true'
    
    negotiationsStore.startStreaming(data.session_id, stepDelay, shareUfuns)
    
    // Navigate to single negotiation view
    router.push({ name: 'SingleNegotiation', params: { id: data.session_id } })
  }
}
</script>

<style scoped>
.negotiations-list-container {
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
  flex-wrap: wrap;
}

.active-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.filter-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: var(--primary-color);
  color: white;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.filter-remove {
  background: transparent;
  border: none;
  color: white;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  margin-left: 2px;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.filter-remove:hover {
  opacity: 1;
}

.btn-clear-filters {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear-filters:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--primary-color);
}

.content-area {
  display: flex;
  flex-direction: row;
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
}

.table-container.with-preview {
  flex: 0 0 66.67%;
  max-width: 66.67%;
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

.negotiations-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.negotiations-table thead {
  position: sticky;
  top: 0;
  background: var(--bg-secondary);
  z-index: 10;
  border-bottom: 2px solid var(--border-color);
}

.negotiations-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.negotiations-table th:hover {
  background: var(--bg-hover);
}

.negotiations-table tbody tr {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.negotiations-table tbody tr:hover {
  background: var(--bg-hover);
}

.negotiations-table tbody tr.selected {
  background: rgba(59, 130, 246, 0.1);
}

.negotiations-table tbody tr.clickable-row {
  cursor: pointer;
}

.negotiations-table td {
  padding: 12px 16px;
}

.date-cell {
  color: var(--text-secondary);
  font-size: 13px;
}

.scenario-cell {
  font-weight: 500;
}

.negotiators-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.negotiator-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}

.result-cell .badge {
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

.badge-agreement {
  background: rgba(16, 185, 129, 0.2);
  color: rgb(16, 185, 129);
}

.badge-timeout {
  background: rgba(245, 158, 11, 0.2);
  color: rgb(245, 158, 11);
}

.badge-disagreement {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
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

.empty-state,
.loading-state {
  padding: 48px 24px;
  text-align: center;
  color: var(--text-secondary);
}

.preview-container {
  flex: 0 0 33.33%;
  max-width: 33.33%;
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
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-result-header {
  flex-shrink: 0;
  max-height: 200px;
  overflow: auto;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 1rem;
}

.preview-panel-main {
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: auto;
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

/* Running Negotiations Section Styles */
.running-section {
  margin-bottom: 16px;
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 16px;
}

.section-header {
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 6px 6px 0 0;
  margin-bottom: 8px;
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

.running-negotiations-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.running-negotiations-table thead {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.running-negotiations-table th {
  padding: 6px 8px;
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.running-negotiations-table tbody tr {
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.running-negotiations-table tbody tr:hover {
  background: var(--bg-hover);
}

.running-negotiations-table tbody tr.selected {
  background: rgba(59, 130, 246, 0.1);
}

.running-negotiations-table tbody tr.clickable-row {
  cursor: pointer;
}

.running-negotiations-table td {
  padding: 8px;
}

.negotiator-badge-sm {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  color: white;
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

.session-id {
  font-size: 10px;
  color: var(--text-muted);
  font-family: monospace;
  margin-top: 2px;
}

.saved-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.saved-section .section-header {
  margin-bottom: 0;
  border-radius: 6px 6px 0 0;
}

/* Button styles for tournament mode */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-ghost {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-ghost:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
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

</style>
