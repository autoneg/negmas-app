<template>
  <div class="negotiations-view">
    <!-- Negotiations List View (hidden when viewing a specific negotiation) -->
    <div class="negotiations-list-view" v-show="!currentSession">
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
      
      <!-- Saved Negotiations Section -->
      <div class="session-group" style="margin-top: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h4>Saved ({{ savedNegotiations.length }})</h4>
          <div style="display: flex; gap: 4px;">
            <button 
              class="btn-sm btn-secondary" 
              @click="loadSavedNegs" 
              :disabled="savedNegotiationsLoading"
              title="Load saved negotiations"
            >
              {{ savedNegotiationsLoading ? '⟳' : '↻' }}
            </button>
            <button 
              class="btn-sm btn-ghost" 
              @click="handleClearSaved" 
              title="Clear all saved"
              v-if="savedNegotiations.length > 0"
            >
              🗑
            </button>
          </div>
        </div>
        
        <!-- Filters -->
        <div style="display: flex; gap: 4px; margin-bottom: 8px;" v-if="savedNegotiations.length > 0">
          <select 
            class="form-select-sm" 
            v-model="tagFilter" 
            @change="filterSavedNegotiations"
            style="flex: 1; font-size: 0.75rem;"
          >
            <option value="">All tags</option>
            <option v-for="tag in availableTags" :key="tag" :value="tag">{{ tag }}</option>
          </select>
          <label style="display: flex; align-items: center; gap: 4px; font-size: 0.7rem; white-space: nowrap;">
            <input type="checkbox" v-model="showArchived" @change="loadSavedNegs">
            <span>Archived</span>
          </label>
        </div>
        
        <!-- Saved negotiations list -->
        <div class="session-list" style="max-height: 400px; overflow-y: auto;" v-if="filteredSavedNegotiations.length > 0">
          <div
            v-for="neg in filteredSavedNegotiations"
            :key="neg.id"
            class="session-item saved"
            :class="{ active: currentSession?.id === neg.id }"
          >
            <div class="session-name" @click="viewSavedNegotiation(neg)">{{ neg.scenario_name }}</div>
            <div class="session-meta" style="font-size: 0.7rem;">
              <span v-if="neg.agreement" class="badge badge-agreement">✓</span>
              <span v-else class="badge badge-no-agreement">✗</span>
              <span class="text-muted">{{ neg.current_step }} steps</span>
            </div>
            <div v-if="neg.tags && neg.tags.length > 0" style="display: flex; gap: 2px; flex-wrap: wrap; margin-top: 4px;">
              <span 
                v-for="tag in neg.tags" 
                :key="tag" 
                class="badge badge-sm badge-neutral"
                style="font-size: 0.65rem;"
              >
                {{ tag }}
              </span>
            </div>
            <div style="display: flex; gap: 4px; margin-top: 6px;">
              <button class="btn-xs btn-ghost" @click.stop="editTags(neg)" title="Edit tags">🏷️</button>
              <button class="btn-xs btn-ghost" @click.stop="deleteSaved(neg.id)" title="Delete">🗑️</button>
            </div>
          </div>
        </div>
        
        <div v-else-if="savedNegotiationsLoading" class="empty-state-sm">
          Loading...
        </div>
        <div v-else class="empty-state-sm">
          No saved negotiations
        </div>
      </div>
      
      <div v-if="sessions.length === 0 && !loading && savedNegotiations.length === 0" class="empty-state-sm">
        No negotiations yet
      </div>
    </div>
    
    <!-- Main Viewer Panel -->
    <div class="viewer-panel" :class="{ 'viewer-fullscreen': currentSession }">
      <div v-if="!currentSession" class="empty-state">
        <p>Select a negotiation to view details</p>
        <p class="empty-hint">or start a new negotiation</p>
      </div>
      
      <div v-else class="negotiation-viewer">
        <!-- Compact Header -->
        <div class="table-header" style="margin-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <h2 style="font-size: 16px;">Negotiation</h2>
            <span class="badge badge-primary" style="font-size: 12px;">{{ negotiation?.scenario_name || 'Unknown' }}</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <!-- Close button -->
            <button class="btn btn-ghost btn-sm" @click="currentSession = null" title="Close negotiation view">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
              <span>Close</span>
            </button>
            <!-- Stats button -->
            <button class="btn btn-ghost btn-sm" @click="handleShowStats" title="View scenario statistics">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
                <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
              </svg>
              <span>Stats</span>
            </button>
            <button class="btn btn-primary btn-sm" @click="showNewNegotiationModal = true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              <span>New</span>
            </button>
          </div>
        </div>
        
        <!-- Panel System Layout -->
        <PanelLayout v-if="negotiation">
          <!-- Left Column -->
          <template #left>
            <!-- Info Panel (ultra-compact, ~80px) -->
            <InfoPanel 
              :negotiation="negotiation"
              @start="handleStartNegotiation"
              @togglePause="handleTogglePause"
              @stop="handleStopNegotiation"
              @showStats="handleShowStats"
            />
            
            <!-- Offer History Panel (scrollable) -->
            <OfferHistoryPanel 
              :negotiation="negotiation"
            />
            
            <!-- Histogram Panel -->
            <HistogramPanel 
              :negotiation="negotiation"
            />
            
            <!-- Result Panel -->
            <ResultPanel 
              :negotiation="negotiation"
              @saveResults="handleSaveResults"
            />
          </template>
          
          <!-- Right Column -->
          <template #right>
            <!-- 2D Utility View Panel -->
            <Utility2DPanel 
              :negotiation="negotiation"
              :adjustable="true"
            />
            
            <!-- Timeline Panel -->
            <TimelinePanel 
              :negotiation="negotiation"
              :adjustable="true"
            />
          </template>
        </PanelLayout>
      </div>
    </div>
    
    <!-- New Negotiation Modal (teleported to body) -->
    <Teleport to="body">
      <NewNegotiationModal
        :show="showNewNegotiationModal"
        @close="showNewNegotiationModal = false"
        @start="onNegotiationStart"
      />
      
      <!-- Tag Editor Modal -->
      <div 
        v-if="tagEditorNegotiation" 
        class="modal-overlay" 
        @click.self="closeTagEditor"
      >
        <div class="modal" style="max-width: 400px;">
          <div class="modal-header">
            <h2 class="modal-title">Edit Tags</h2>
            <button class="btn btn-ghost btn-sm" @click="closeTagEditor">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="modal-body" style="padding: 16px;">
            <div class="text-muted" style="font-size: 12px; margin-bottom: 8px;">
              Negotiation: <code>{{ tagEditorNegotiation?.id }}</code>
            </div>
            
            <!-- Current tags -->
            <div style="margin-bottom: 16px;">
              <div style="display: flex; flex-wrap: wrap; gap: 4px; min-height: 32px; padding: 8px; background: var(--bg-secondary); border-radius: 4px;">
                <span 
                  v-for="tag in tagEditorTags" 
                  :key="tag" 
                  class="badge badge-primary" 
                  style="display: flex; align-items: center; gap: 4px;"
                >
                  <span>{{ tag }}</span>
                  <button 
                    @click="removeTagFromEditor(tag)" 
                    style="background: none; border: none; padding: 0; cursor: pointer; color: inherit; opacity: 0.7;"
                  >
                    ×
                  </button>
                </span>
                <span v-if="tagEditorTags.length === 0" class="text-muted">No tags</span>
              </div>
            </div>
            
            <!-- Add new tag -->
            <div style="display: flex; gap: 8px; margin-bottom: 16px;">
              <input 
                type="text" 
                class="form-input" 
                placeholder="Add new tag..." 
                v-model="newTagInput" 
                @keydown.enter.prevent="addNewTag"
                style="flex: 1;"
              >
              <button 
                class="btn btn-secondary btn-sm" 
                @click="addNewTag" 
                :disabled="!newTagInput.trim()"
              >
                Add
              </button>
            </div>
            
            <!-- Existing tags suggestions -->
            <div v-if="availableTags.length > 0" style="margin-bottom: 16px;">
              <div class="text-muted" style="font-size: 11px; margin-bottom: 4px;">Quick add:</div>
              <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                <button 
                  v-for="tag in availableTags.filter(t => !tagEditorTags.includes(t)).slice(0, 10)" 
                  :key="tag" 
                  class="badge badge-neutral" 
                  style="cursor: pointer; border: none;"
                  @click="tagEditorTags.push(tag)"
                >
                  {{ tag }}
                </button>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="closeTagEditor">Cancel</button>
            <button class="btn btn-primary" @click="saveTagsFromEditor">Save Tags</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, onUnmounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useNegotiationsStore } from '../stores/negotiations'
import { storeToRefs } from 'pinia'
import NewNegotiationModal from '../components/NewNegotiationModal.vue'
import PanelLayout from '../components/panels/PanelLayout.vue'
import InfoPanel from '../components/panels/InfoPanel.vue'
import OfferHistoryPanel from '../components/panels/OfferHistoryPanel.vue'
import ResultPanel from '../components/panels/ResultPanel.vue'
import Utility2DPanel from '../components/panels/Utility2DPanel.vue'
import TimelinePanel from '../components/panels/TimelinePanel.vue'
import HistogramPanel from '../components/panels/HistogramPanel.vue'

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
  savedNegotiations,
  savedNegotiationsLoading,
  tagFilter,
  showArchived,
  availableTags,
} = storeToRefs(negotiationsStore)

const showNewNegotiationModal = ref(false)

// Tag editor state
const tagEditorNegotiation = ref(null)
const tagEditorTags = ref([])
const newTagInput = ref('')

// Filtered saved negotiations
const filteredSavedNegotiations = computed(() => {
  let result = savedNegotiations.value
  if (tagFilter.value) {
    result = result.filter(neg => neg.tags && neg.tags.includes(tagFilter.value))
  }
  return result
})

// Computed negotiation data for panels
const negotiation = computed(() => {
  if (!streamingSession.value && !currentSession.value) return null
  
  // Merge session data with streaming data
  return {
    id: currentSession.value?.id,
    scenario: sessionInit.value?.scenario_name || currentSession.value?.scenario_name,
    negotiator_names: sessionInit.value?.negotiator_names || currentSession.value?.negotiator_names,
    negotiator_colors: sessionInit.value?.negotiator_colors || currentSession.value?.negotiator_colors,
    issue_names: sessionInit.value?.issue_names,
    n_steps: sessionInit.value?.n_steps || currentSession.value?.n_steps,
    step: offers.value[offers.value.length - 1]?.step || 0,
    offers: offers.value,
    outcome_space_data: sessionInit.value?.outcome_space_data,
    agreement: sessionComplete.value?.agreement || currentSession.value?.agreement,
    final_utilities: sessionComplete.value?.final_utilities,
    optimality_stats: sessionComplete.value?.optimality_stats,
    end_reason: sessionComplete.value?.end_reason || currentSession.value?.end_reason,
    error: sessionComplete.value?.error,
    relative_time: offers.value[offers.value.length - 1]?.relative_time || 0,
    pendingStart: streamingSession.value && offers.value.length === 0,
    paused: false, // TODO: Add pause state to store
    isSaved: currentSession.value?.status === 'completed' || currentSession.value?.status === 'failed'
  }
})

onMounted(async () => {
  await loadData()
  
  // Check if we should start streaming a specific session from query params
  if (route.query.session_id) {
    const sessionId = route.query.session_id
    negotiationsStore.startStreaming(sessionId)
  }
})

onUnmounted(() => {
  negotiationsStore.stopStreaming()
})

async function loadData() {
  await negotiationsStore.loadSessions()
  await negotiationsStore.loadSavedNegotiations(showArchived.value)
}

async function loadSavedNegs() {
  await negotiationsStore.loadSavedNegotiations(showArchived.value)
}

function filterSavedNegotiations() {
  // Filtering happens via computed property
}

async function viewSavedNegotiation(neg) {
  // Load the full saved negotiation data
  const data = await negotiationsStore.loadSavedNegotiation(neg.id)
  if (data) {
    // Create a session-like object and select it
    const session = {
      id: data.id,
      scenario_name: data.scenario_name,
      scenario_path: data.scenario_path,
      status: data.status,
      current_step: data.current_step,
      n_steps: data.n_steps,
      negotiator_names: data.negotiator_names,
      negotiator_types: data.negotiator_types,
      negotiator_colors: data.negotiator_colors,
      issue_names: data.issue_names,
      agreement: data.agreement,
      final_utilities: data.final_utilities,
      end_reason: data.end_reason,
      isSaved: true,
    }
    
    negotiationsStore.selectSession(session)
    
    // Populate the offers and outcome space data
    sessionInit.value = {
      scenario_name: data.scenario_name,
      negotiator_names: data.negotiator_names,
      negotiator_types: data.negotiator_types,
      negotiator_colors: data.negotiator_colors,
      issue_names: data.issue_names,
      n_steps: data.n_steps,
      time_limit: data.time_limit,
      outcome_space_data: data.outcome_space_data,
    }
    
    offers.value = data.offers || []
    
    sessionComplete.value = {
      agreement: data.agreement,
      final_utilities: data.final_utilities,
      optimality_stats: data.optimality_stats,
      end_reason: data.end_reason,
    }
  }
}

async function deleteSaved(sessionId) {
  if (confirm('Are you sure you want to delete this saved negotiation?')) {
    await negotiationsStore.deleteSavedNegotiation(sessionId)
  }
}

async function handleClearSaved() {
  if (confirm(`Clear all saved negotiations${showArchived.value ? ' including archived' : ''}?`)) {
    await negotiationsStore.clearAllSavedNegotiations(showArchived.value)
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
    closeTagEditor()
  }
}

async function loadData() {
  await negotiationsStore.loadSessions()
  await negotiationsStore.loadSavedNegotiations(showArchived.value)
}

function onNegotiationStart(data) {
  // Close modal
  showNewNegotiationModal.value = false
  
  // Start streaming the new negotiation
  if (data.session_id) {
    // Create a temporary session object and select it
    const tempSession = {
      id: data.session_id,
      scenario_name: data.scenario_name || 'New Negotiation',
      status: 'running',
      current_step: 0,
    }
    negotiationsStore.selectSession(tempSession)
    
    // Start streaming
    negotiationsStore.startStreaming(data.session_id)
    
    // Reload sessions list to get the actual session data
    negotiationsStore.loadSessions()
  }
}

function selectAndViewSession(session) {
  negotiationsStore.selectSession(session)
  
  // If session is completed, we might want to load full details
  if (session.status === 'completed' || session.status === 'failed') {
    // Could load saved session data here if needed
  }
}

function watchLive() {
  if (!currentSession.value) return
  negotiationsStore.startStreaming(currentSession.value.id)
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

// Panel event handlers
function handleStartNegotiation() {
  // Start/resume negotiation
  console.log('Start negotiation')
}

function handleTogglePause() {
  // Toggle pause
  console.log('Toggle pause')
}

function handleStopNegotiation() {
  // Stop negotiation
  if (currentSession.value) {
    cancelNegotiation()
  }
}

function handleShowStats() {
  // Show scenario stats
  console.log('Show stats')
}

function handleSaveResults() {
  // Save results to file
  console.log('Save results')
}

</script>

<style scoped>
.negotiations-view {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.negotiations-list-view {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow: auto;
  width: 400px;
  max-width: 100%;
  margin: 16px;
  height: calc(100% - 32px);
}

.viewer-panel {
  display: none; /* Hidden when no session */
}

/* When viewing a negotiation, show fullscreen */
.viewer-panel.viewer-fullscreen {
  display: flex;
  flex-direction: column;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--bg-primary);
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
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.viewer-panel.viewer-fullscreen {
  border: none;
  border-radius: 0;
  background: var(--bg-primary);
  height: 100vh;
  padding: 16px;
}

.negotiation-viewer {
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
  gap: 8px;
  padding: 48px 24px;
}

.empty-hint {
  font-size: 0.85rem;
}

.btn-primary {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
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
</style>
