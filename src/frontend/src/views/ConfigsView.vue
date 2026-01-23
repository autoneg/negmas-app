<template>
  <div class="configs-view">
    <!-- Left Panel: Configs List -->
    <div class="configs-list-panel">
      <!-- Header with Tabs -->
      <div class="filter-section">
        <div class="filter-header">
          <h3>Configurations</h3>
          <button class="btn-icon" @click="loadData" :disabled="loading" title="Refresh">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16" :class="{ 'spin-icon': loading }">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>
        </div>
        
        <!-- Tabs: Negotiations vs Tournaments -->
        <div class="tabs">
          <button 
            class="tab" 
            :class="{ active: currentTab === 'negotiations' }"
            @click="currentTab = 'negotiations'"
          >
            Negotiations
          </button>
          <button 
            class="tab" 
            :class="{ active: currentTab === 'tournaments' }"
            @click="currentTab = 'tournaments'"
          >
            Tournaments
          </button>
        </div>
        
        <!-- Search -->
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name or tag..."
          class="input-search"
        />
        
        <!-- Tag Filter -->
        <div class="filter-group" v-if="availableTags.length > 0">
          <label>Filter by Tag</label>
          <select v-model="selectedTag" class="input-select">
            <option value="">All Tags</option>
            <option v-for="tag in availableTags" :key="tag" :value="tag">{{ tag }}</option>
          </select>
        </div>
        
        <!-- Status Filter -->
        <div class="filter-group">
          <label>Status</label>
          <select v-model="statusFilter" class="input-select">
            <option value="all">All</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>
        
        <!-- Create New Button -->
        <button class="btn btn-primary" @click="createNew" style="margin-top: 16px; width: 100%;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          Create New
        </button>
      </div>
      
      <!-- Configs List -->
      <div class="list-section">
        <div v-if="loading" class="empty-state">
          <div class="spinner"></div>
          <p>Loading configurations...</p>
        </div>
        
        <div v-else-if="filteredConfigs.length === 0" class="empty-state">
          <p>No configurations found</p>
          <button class="btn btn-secondary" @click="createNew">Create your first config</button>
        </div>
        
        <div 
          v-else
          v-for="config in filteredConfigs" 
          :key="config.name"
          class="config-item"
          :class="{ 
            selected: selectedConfig?.name === config.name,
            disabled: isConfigDisabled(config)
          }"
          @click="selectConfig(config)"
        >
          <div class="config-item-header">
            <div class="config-item-title">
              {{ config.name }}
              <span v-if="isConfigDisabled(config)" class="badge badge-neutral">Disabled</span>
            </div>
          </div>
          <div class="config-item-meta">
            <span>{{ config.scenario_name || 'No scenario' }}</span>
          </div>
          <div class="config-item-meta">
            <span>{{ config.negotiators?.length || 0 }} negotiators</span>
          </div>
          <div v-if="config.tags && config.tags.length > 0" class="config-tags">
            <span v-for="tag in config.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Right Panel: Config Details -->
    <div class="config-details-panel">
      <div v-if="!selectedConfig" class="empty-state">
        <p>Select a configuration to view details</p>
      </div>
      
      <div v-else class="config-details">
        <!-- Header Actions -->
        <div class="details-header">
          <h3>{{ selectedConfig.name }}</h3>
          <div class="details-actions">
            <button 
              class="btn btn-sm btn-primary" 
              @click="startFromConfig"
              title="Start negotiation/tournament with this configuration"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
              Start
            </button>
            <button 
              class="btn btn-sm btn-secondary" 
              @click="editConfig"
              title="Edit"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
              Edit
            </button>
            <button 
              class="btn btn-sm btn-secondary" 
              @click="toggleEnabled"
              :title="isConfigDisabled(selectedConfig) ? 'Enable' : 'Disable'"
            >
              <svg v-if="isConfigDisabled(selectedConfig)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
              {{ isConfigDisabled(selectedConfig) ? 'Enable' : 'Disable' }}
            </button>
            <button class="btn btn-sm btn-secondary" @click="renameConfig" title="Rename">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
              </svg>
              Rename
            </button>
            <button class="btn btn-sm btn-danger" @click="deleteConfig" title="Delete">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
              Delete
            </button>
          </div>
        </div>
        
        <!-- Tags Editor -->
        <div class="details-section">
          <h4>Tags</h4>
          <div class="tags-editor">
            <div class="tags-list">
              <span v-for="(tag, idx) in selectedConfig.tags || []" :key="idx" class="tag">
                {{ tag }}
                <button class="tag-remove" @click="removeTag(idx)">×</button>
              </span>
            </div>
            <div class="tag-input-group">
              <input 
                v-model="newTag" 
                type="text" 
                placeholder="Add tag..." 
                class="input-text"
                @keyup.enter="addTag"
              />
              <button class="btn btn-sm btn-secondary" @click="addTag">Add</button>
            </div>
          </div>
        </div>
        
        <!-- Config Details -->
        <div class="details-section">
          <h4>Configuration</h4>
          
          <div class="detail-row">
            <span class="detail-label">Scenario:</span>
            <span class="detail-value">{{ selectedConfig.scenario_name || 'N/A' }}</span>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">Scenario Path:</span>
            <span class="detail-value">{{ selectedConfig.scenario_path || 'N/A' }}</span>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">Negotiators:</span>
            <span class="detail-value">{{ selectedConfig.negotiators?.length || 0 }}</span>
          </div>
          
          <div v-if="selectedConfig.negotiators && selectedConfig.negotiators.length > 0" class="detail-subsection">
            <div v-for="(neg, idx) in selectedConfig.negotiators" :key="idx" class="negotiator-item">
              <div class="negotiator-name">{{ neg.name }}</div>
              <div class="negotiator-type">{{ neg.type_name }}</div>
            </div>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">Mechanism:</span>
            <span class="detail-value">{{ selectedConfig.mechanism_type || 'SAOMechanism' }}</span>
          </div>
          
          <div v-if="selectedConfig.mechanism_params" class="detail-subsection">
            <h5>Mechanism Parameters</h5>
            <div v-for="(value, key) in selectedConfig.mechanism_params" :key="key" class="detail-row">
              <span class="detail-label">{{ key }}:</span>
              <span class="detail-value">{{ value !== null ? value : 'null' }}</span>
            </div>
          </div>
        </div>
        
        <!-- Raw JSON (collapsible) -->
        <div class="details-section">
          <button class="btn btn-ghost btn-sm" @click="showJson = !showJson">
            {{ showJson ? 'Hide' : 'Show' }} JSON
          </button>
          <pre v-if="showJson" class="json-view">{{ JSON.stringify(selectedConfig, null, 2) }}</pre>
        </div>
      </div>
    </div>
    
    <!-- Modals -->
    <NewNegotiationModal
      v-if="currentTab === 'negotiations'"
      :show="showNegotiationModal"
      :editMode="showEditModal"
      :startMode="showStartModal"
      :initialData="editingConfig || startingConfig"
      @close="closeModals"
      @saved="onConfigSaved"
      @start="onNegotiationStart"
    />
    
    <!-- Rename Modal -->
    <Teleport to="body">
      <div v-if="showRenameModal" class="modal-overlay" @click.self="showRenameModal = false">
        <div class="modal small">
          <div class="modal-header">
            <h3 class="modal-title">Rename Configuration</h3>
            <button class="modal-close" @click="showRenameModal = false">×</button>
          </div>
          <div class="modal-body" style="padding: 24px;">
            <input 
              v-model="newName" 
              type="text" 
              class="input-text" 
              placeholder="Enter new name"
              @keyup.enter="confirmRename"
              style="width: 100%;"
            />
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showRenameModal = false">Cancel</button>
            <button class="btn btn-primary" @click="confirmRename">Rename</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNegotiationsStore } from '../stores/negotiations'
import NewNegotiationModal from '../components/NewNegotiationModal.vue'

const router = useRouter()
const negotiationsStore = useNegotiationsStore()

const currentTab = ref('negotiations')
const searchQuery = ref('')
const selectedTag = ref('')
const statusFilter = ref('all')
const loading = ref(false)
const selectedConfig = ref(null)
const newTag = ref('')
const showJson = ref(false)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showStartModal = ref(false)
const editingConfig = ref(null)
const startingConfig = ref(null)
const showRenameModal = ref(false)
const newName = ref('')

// Computed
const showNegotiationModal = computed(() => showCreateModal.value || showEditModal.value || showStartModal.value)

// Computed
const configs = computed(() => {
  if (currentTab.value === 'negotiations') {
    return negotiationsStore.sessionPresets || []
  } else {
    // TODO: Add tournament configs from store
    return []
  }
})

const filteredConfigs = computed(() => {
  let result = configs.value
  
  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(c => 
      c.name.toLowerCase().includes(query) ||
      c.scenario_name?.toLowerCase().includes(query) ||
      c.tags?.some(t => t.toLowerCase().includes(query))
    )
  }
  
  // Tag filter
  if (selectedTag.value) {
    result = result.filter(c => c.tags?.includes(selectedTag.value))
  }
  
  // Status filter
  if (statusFilter.value === 'enabled') {
    result = result.filter(c => !c.disabled)
  } else if (statusFilter.value === 'disabled') {
    result = result.filter(c => c.disabled)
  }
  
  return result
})

const availableTags = computed(() => {
  const tags = new Set()
  configs.value.forEach(c => {
    if (c.tags) {
      c.tags.forEach(t => tags.add(t))
    }
  })
  return Array.from(tags).sort()
})

// Methods
function isConfigDisabled(config) {
  // Disabled flag defaults to false if not set
  return config?.disabled === true
}

async function loadData() {
  loading.value = true
  try {
    if (currentTab.value === 'negotiations') {
      await negotiationsStore.loadSessionPresets()
    } else {
      // TODO: Load tournament configs
    }
  } finally {
    loading.value = false
  }
}

function selectConfig(config) {
  selectedConfig.value = config
  showJson.value = false
}

function createNew() {
  showCreateModal.value = true
}

function editConfig() {
  if (!selectedConfig.value) return
  console.log('[ConfigsView] Opening edit modal for:', selectedConfig.value.name)
  editingConfig.value = { ...selectedConfig.value }
  showEditModal.value = true
  console.log('[ConfigsView] showEditModal:', showEditModal.value, 'showNegotiationModal:', showNegotiationModal.value)
}

function startFromConfig() {
  if (!selectedConfig.value) return
  console.log('[ConfigsView] Opening start modal for:', selectedConfig.value.name)
  startingConfig.value = { ...selectedConfig.value }
  showStartModal.value = true
  console.log('[ConfigsView] showStartModal:', showStartModal.value, 'showNegotiationModal:', showNegotiationModal.value)
}

function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  showStartModal.value = false
  editingConfig.value = null
  startingConfig.value = null
}

async function onConfigSaved() {
  console.log('[ConfigsView] Config saved, reloading data')
  closeModals()
  await loadData()
  
  // Re-select the config to refresh the view
  if (selectedConfig.value) {
    const updatedConfig = configs.value.find(c => c.name === selectedConfig.value.name)
    if (updatedConfig) {
      selectedConfig.value = updatedConfig
    }
  }
}

function onNegotiationStart(data) {
  console.log('[ConfigsView] Negotiation started:', data)
  closeModals()
  // Navigate to the new negotiation
  if (data && data.session_id) {
    console.log('[ConfigsView] Navigating to /negotiations/' + data.session_id)
    router.push(`/negotiations/${data.session_id}`)
  } else {
    console.error('[ConfigsView] No session_id in response:', data)
  }
}

async function toggleEnabled() {
  if (!selectedConfig.value) return
  
  const configName = selectedConfig.value.name
  
  // Toggle the disabled flag (defaults to false/enabled if not set)
  selectedConfig.value.disabled = !isConfigDisabled(selectedConfig.value)
  
  await negotiationsStore.saveSessionPreset(selectedConfig.value)
  await loadData()
  
  // Re-select the config to refresh the view
  const updatedConfig = configs.value.find(c => c.name === configName)
  if (updatedConfig) {
    selectedConfig.value = updatedConfig
  }
}

function renameConfig() {
  if (!selectedConfig.value) return
  console.log('[ConfigsView] Opening rename modal for:', selectedConfig.value.name)
  newName.value = selectedConfig.value.name
  showRenameModal.value = true
  console.log('[ConfigsView] showRenameModal:', showRenameModal.value)
}

async function confirmRename() {
  console.log('[ConfigsView] confirmRename called, newName:', newName.value)
  if (!selectedConfig.value || !newName.value.trim()) {
    console.log('[ConfigsView] Validation failed')
    return
  }
  
  const oldName = selectedConfig.value.name
  const newNameTrimmed = newName.value.trim()
  
  console.log('[ConfigsView] Renaming from', oldName, 'to', newNameTrimmed)
  
  // Update the config name
  selectedConfig.value.name = newNameTrimmed
  
  // Delete old config and save with new name
  await negotiationsStore.deleteSessionPreset(oldName)
  await negotiationsStore.saveSessionPreset(selectedConfig.value)
  
  showRenameModal.value = false
  newName.value = ''
  
  console.log('[ConfigsView] Rename complete, reloading data')
  
  // Reload and re-select with new name
  await loadData()
  const updatedConfig = configs.value.find(c => c.name === newNameTrimmed)
  if (updatedConfig) {
    selectedConfig.value = updatedConfig
    console.log('[ConfigsView] Re-selected config:', updatedConfig.name)
  }
}

async function deleteConfig() {
  if (!selectedConfig.value) return
  
  if (confirm(`Delete configuration "${selectedConfig.value.name}"?`)) {
    await negotiationsStore.deleteSessionPreset(selectedConfig.value.name)
    selectedConfig.value = null
    await loadData()
  }
}

function addTag() {
  if (!selectedConfig.value || !newTag.value.trim()) return
  
  if (!selectedConfig.value.tags) {
    selectedConfig.value.tags = []
  }
  
  if (!selectedConfig.value.tags.includes(newTag.value.trim())) {
    selectedConfig.value.tags.push(newTag.value.trim())
    negotiationsStore.saveSessionPreset(selectedConfig.value)
  }
  
  newTag.value = ''
}

function removeTag(idx) {
  if (!selectedConfig.value || !selectedConfig.value.tags) return
  
  selectedConfig.value.tags.splice(idx, 1)
  negotiationsStore.saveSessionPreset(selectedConfig.value)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.configs-view {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}

.configs-list-panel {
  width: 350px;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
}

.config-details-panel {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.filter-section {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.filter-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  background: var(--bg-primary);
  border-radius: 8px;
  padding: 4px;
}

.tab {
  flex: 1;
  padding: 8px 12px;
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tab.active {
  background: var(--primary-color);
  color: white;
}

.filter-group {
  margin-bottom: 12px;
}

.filter-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
  text-transform: uppercase;
}

.list-section {
  flex: 1;
  overflow-y: auto;
}

.config-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: background 0.2s;
}

.config-item:hover {
  background: var(--bg-hover);
}

.config-item.selected {
  background: var(--bg-tertiary);
  border-left: 3px solid var(--primary-color);
}

.config-item.disabled {
  opacity: 0.5;
}

.config-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.config-item-title {
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-item-meta {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.config-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.tag-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  font-size: 14px;
  line-height: 1;
}

.tag-remove:hover {
  color: var(--danger);
}

.config-details {
  max-width: 900px;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--border-color);
}

.details-header h3 {
  margin: 0;
  font-size: 1.5rem;
}

.details-actions {
  display: flex;
  gap: 8px;
}

.details-section {
  margin-bottom: 32px;
}

.details-section h4 {
  margin: 0 0 16px 0;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.details-section h5 {
  margin: 16px 0 8px 0;
  font-size: 0.95rem;
  color: var(--text-secondary);
  font-weight: 600;
}

.tags-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
}

.tag-input-group {
  display: flex;
  gap: 8px;
}

.tag-input-group .input-text {
  flex: 1;
}

.detail-row {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  gap: 16px;
}

.detail-label {
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 320px;
  flex-shrink: 0;
  word-break: break-word;
}

.detail-value {
  color: var(--text-primary);
  flex: 1;
  word-break: break-word;
}

.detail-subsection {
  margin-left: 20px;
  margin-top: 8px;
}

.negotiator-item {
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: 6px;
  margin-bottom: 8px;
}

.negotiator-name {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.negotiator-type {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: monospace;
}

.json-view {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12px;
  margin-top: 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spin-icon {
  animation: spin 0.8s linear infinite;
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.badge-neutral {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}
</style>
