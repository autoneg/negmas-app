<template>
  <div class="negotiators-view">
    <!-- Negotiators List Panel -->
    <div class="negotiators-list-panel">
      <!-- Filters -->
      <div class="filter-section">
        <div class="filter-header">
          <h3>Negotiators</h3>
          <button class="btn-icon" @click="loadData" :disabled="loading" title="Refresh">
            <span v-if="loading">⟳</span>
            <span v-else>↻</span>
          </button>
        </div>
        
        <!-- Search -->
        <input
          v-model="localSearch"
          type="text"
          placeholder="Search negotiators..."
          class="input-search"
          @input="updateSearch"
        />
        
        <!-- Source Filter -->
        <div class="filter-group">
          <label>Source</label>
          <select v-model="localSource" @change="updateSourceFilter" class="input-select">
            <option value="">All Sources</option>
            <option v-for="source in sources" :key="source.id" :value="source.id">
              {{ source.name }}
            </option>
          </select>
        </div>
        
        <!-- Group Filter -->
        <div class="filter-group" v-if="availableGroups.length > 0">
          <label>Group</label>
          <select v-model="localGroup" @change="updateGroupFilter" class="input-select">
            <option value="">All Groups</option>
            <option v-for="group in availableGroups" :key="group" :value="group">
              {{ group }}
            </option>
          </select>
        </div>
        
        <!-- Mechanism Filter -->
        <div class="filter-group" v-if="availableMechanisms.length > 0">
          <label>Mechanism</label>
          <select v-model="localMechanism" @change="updateMechanismFilter" class="input-select">
            <option value="">All Mechanisms</option>
            <option v-for="mech in availableMechanisms" :key="mech" :value="mech">
              {{ mech }}
            </option>
          </select>
        </div>
        
        <!-- Available Only Filter -->
        <div class="filter-group">
          <label class="checkbox-label">
            <input
              v-model="localAvailableOnly"
              type="checkbox"
              @change="updateAvailableFilter"
            />
            <span>Show available only</span>
          </label>
        </div>
        
        <div style="display: flex; gap: 8px; margin-top: 8px;">
          <button class="btn-secondary btn-sm" @click="clearFilters" style="flex: 1;">Clear Filters</button>
          <button class="btn-secondary btn-sm" @click="showSaveFilterDialog = true" style="flex: 1;">Save Filter</button>
          <select v-model="selectedFilterId" @change="loadSavedFilter" class="input-select btn-sm" style="flex: 1;">
            <option value="">Load Filter...</option>
            <option v-for="filter in savedFilters" :key="filter.id" :value="filter.id">{{ filter.name }}</option>
          </select>
        </div>
      </div>
      
      <!-- Negotiators List -->
      <div class="negotiators-list">
        <div v-if="loading" class="loading-state">
          <span class="spinner"></span> Loading negotiators...
        </div>
        
        <div v-else-if="filteredNegotiators.length === 0" class="empty-state">
          No negotiators found
        </div>
        
        <div
          v-else
          v-for="negotiator in filteredNegotiators"
          :key="negotiator.type_name"
          class="negotiator-item"
          :class="{ 
            active: selectedNegotiator?.type_name === negotiator.type_name,
            unavailable: !negotiator.available
          }"
          @click="selectNegotiator(negotiator)"
        >
          <div class="negotiator-name">{{ negotiator.name }}</div>
          <div class="negotiator-meta">
            <span class="badge badge-source">{{ negotiator.source }}</span>
            <span v-if="negotiator.group" class="badge badge-group">{{ negotiator.group }}</span>
            <span v-if="!negotiator.available" class="badge badge-unavailable">Unavailable</span>
          </div>
          <div class="negotiator-type">{{ negotiator.type_name }}</div>
        </div>
      </div>
      
      <!-- Virtual Negotiators Section -->
      <div class="virtual-section">
        <div class="virtual-header">
          <h4>Virtual Negotiators</h4>
          <button class="btn-sm btn-primary" @click="showCreateVirtual = true">
            + New
          </button>
        </div>
        <div v-if="virtualNegotiators.length === 0" class="empty-state-sm">
          No virtual negotiators
        </div>
        <div v-else class="virtual-list">
          <div
            v-for="vn in virtualNegotiators"
            :key="vn.id"
            class="virtual-item"
            @click="selectVirtualNegotiator(vn)"
          >
            <span>{{ vn.name }}</span>
            <button class="btn-icon-sm" @click.stop="deleteVirtual(vn.id)" title="Delete">×</button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Negotiator Details Panel -->
    <div class="negotiator-details-panel">
      <div v-if="!selectedNegotiator" class="empty-state">
        <p>Select a negotiator to view details</p>
      </div>
      
      <div v-else class="negotiator-details">
        <!-- Header -->
        <div class="details-header">
          <div>
            <h2>{{ selectedNegotiator.name }}</h2>
            <p class="type-name">{{ selectedNegotiator.type_name }}</p>
          </div>
          <div class="header-actions">
            <button 
              v-if="selectedNegotiator.available"
              class="btn-primary btn-sm" 
              @click="useInNegotiation"
            >
              Use in Negotiation
            </button>
          </div>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
          <button
            class="tab"
            :class="{ active: activeTab === 'info' }"
            @click="activeTab = 'info'"
          >
            Info
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'params' }"
            @click="activeTab = 'params'; loadParameters()"
          >
            Parameters
          </button>
        </div>
        
        <!-- Info Tab -->
        <div v-if="activeTab === 'info'" class="tab-content">
          <div class="info-grid">
            <div class="info-item">
              <label>Source</label>
              <span>{{ selectedNegotiator.source }}</span>
            </div>
            <div class="info-item" v-if="selectedNegotiator.group">
              <label>Group</label>
              <span>{{ selectedNegotiator.group }}</span>
            </div>
            <div class="info-item">
              <label>Available</label>
              <span :class="selectedNegotiator.available ? 'status-yes' : 'status-no'">
                {{ selectedNegotiator.available ? 'Yes' : 'No' }}
              </span>
            </div>
            <div class="info-item" v-if="selectedNegotiator.requires_bridge">
              <label>Requires Bridge</label>
              <span>{{ selectedNegotiator.requires_bridge ? 'Yes' : 'No' }}</span>
            </div>
          </div>
          
          <!-- Description -->
          <div v-if="selectedNegotiator.description" class="description-section">
            <h3>Description</h3>
            <p>{{ selectedNegotiator.description }}</p>
          </div>
          
          <!-- Mechanisms -->
          <div v-if="selectedNegotiator.mechanisms && selectedNegotiator.mechanisms.length > 0" class="mechanisms-section">
            <h3>Supported Mechanisms</h3>
            <div class="tags">
              <span v-for="mech in selectedNegotiator.mechanisms" :key="mech" class="badge">
                {{ mech }}
              </span>
            </div>
          </div>
          
          <!-- Tags -->
          <div v-if="selectedNegotiator.tags && selectedNegotiator.tags.length > 0" class="tags-section">
            <h3>Tags</h3>
            <div class="tags">
              <span v-for="tag in selectedNegotiator.tags" :key="tag" class="badge">{{ tag }}</span>
            </div>
          </div>
        </div>
        
        <!-- Parameters Tab -->
        <div v-if="activeTab === 'params'" class="tab-content">
          <div v-if="loadingParams" class="loading-state">
            <span class="spinner"></span> Loading parameters...
          </div>
          
          <div v-else-if="!selectedNegotiatorParams || selectedNegotiatorParams.length === 0" class="empty-state">
            <p>No configurable parameters</p>
          </div>
          
          <div v-else class="params-list">
            <div v-for="param in selectedNegotiatorParams" :key="param.name" class="param-item">
              <div class="param-header">
                <span class="param-name">{{ param.name }}</span>
                <span v-if="param.required" class="badge badge-required">Required</span>
              </div>
              <div class="param-type">Type: {{ param.type }}</div>
              <div v-if="param.default !== null && param.default !== undefined" class="param-default">
                Default: {{ param.default }}
              </div>
              <div v-if="param.description" class="param-description">
                {{ param.description }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Create Virtual Negotiator Modal -->
    <div v-if="showCreateVirtual" class="modal-overlay active" @click="showCreateVirtual = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Create Virtual Negotiator</h3>
          <button class="btn-icon" @click="showCreateVirtual = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Name</label>
            <input v-model="newVirtualName" type="text" class="input-text" placeholder="My Custom Negotiator" />
          </div>
          <div class="form-group">
            <label>Base Negotiator</label>
            <select v-model="newVirtualBase" class="input-select">
              <option value="">Select base negotiator...</option>
              <option v-for="neg in negotiators.filter(n => n.available)" :key="neg.type_name" :value="neg.type_name">
                {{ neg.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>Description (optional)</label>
            <textarea v-model="newVirtualDescription" class="input-textarea" rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateVirtual = false">Cancel</button>
          <button class="btn-primary" @click="createVirtual" :disabled="!newVirtualName || !newVirtualBase">
            Create
          </button>
        </div>
      </div>
    </div>
    
    <!-- Save Filter Dialog -->
    <div v-if="showSaveFilterDialog" class="modal-overlay" @click="showSaveFilterDialog = false">
      <div class="modal save-filter-modal" @click.stop>
        <div class="modal-header">
          <h3>Save Current Filter</h3>
          <button class="btn-close" @click="showSaveFilterDialog = false">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>Filter Name</label>
            <input
              v-model="saveFilterName"
              type="text"
              class="input-text"
              placeholder="e.g., Available SAO Negotiators"
              @keyup.enter="saveCurrentFilter"
            />
          </div>
          
          <div class="form-group">
            <label>Description (optional)</label>
            <textarea
              v-model="saveFilterDescription"
              class="input-text"
              rows="3"
              placeholder="Optional description for this filter"
            ></textarea>
          </div>
          
          <p v-if="saveFilterError" class="error-message">{{ saveFilterError }}</p>
          <p v-if="saveFilterSuccess" class="success-message">{{ saveFilterSuccess }}</p>
        </div>
        
        <div class="modal-footer">
          <button class="btn-secondary" @click="showSaveFilterDialog = false">Cancel</button>
          <button
            class="btn-primary"
            @click="saveCurrentFilter"
            :disabled="!saveFilterName || savingFilter"
          >
            <span v-if="savingFilter">Saving...</span>
            <span v-else>Save Filter</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useNegotiatorsStore } from '../stores/negotiators'
import { storeToRefs } from 'pinia'

const negotiatorsStore = useNegotiatorsStore()
const {
  negotiators,
  sources,
  selectedNegotiator,
  selectedNegotiatorParams,
  virtualNegotiators,
  loading,
  loadingParams,
  filter,
  filteredNegotiators,
  availableGroups,
  availableMechanisms,
} = storeToRefs(negotiatorsStore)

// Local state for inputs
const localSearch = ref('')
const localSource = ref('')
const localGroup = ref('')
const localMechanism = ref('')
const localAvailableOnly = ref(true)
const activeTab = ref('info')

// Virtual negotiator creation
const showCreateVirtual = ref(false)
const newVirtualName = ref('')
const newVirtualBase = ref('')
const newVirtualDescription = ref('')

// Filter save/load state
const showSaveFilterDialog = ref(false)
const saveFilterName = ref('')
const saveFilterDescription = ref('')
const savingFilter = ref(false)
const saveFilterError = ref('')
const saveFilterSuccess = ref('')
const savedFilters = ref([])
const selectedFilterId = ref('')

// Load data on mount
onMounted(async () => {
  await loadData()
  await loadSavedFilters()
})

async function loadData() {
  await Promise.all([
    negotiatorsStore.loadNegotiators(),
    negotiatorsStore.loadSources(),
    negotiatorsStore.loadVirtualNegotiators(),
  ])
  
  // Set initial filter
  negotiatorsStore.updateFilter({ availableOnly: true })
}

function updateSearch() {
  negotiatorsStore.updateFilter({ search: localSearch.value })
}

function updateSourceFilter() {
  negotiatorsStore.updateFilter({ source: localSource.value })
  negotiatorsStore.loadNegotiators(localSource.value, localGroup.value, localSearch.value)
}

function updateGroupFilter() {
  negotiatorsStore.updateFilter({ group: localGroup.value })
  negotiatorsStore.loadNegotiators(localSource.value, localGroup.value, localSearch.value)
}

function updateMechanismFilter() {
  negotiatorsStore.updateFilter({ mechanism: localMechanism.value })
}

function updateAvailableFilter() {
  negotiatorsStore.updateFilter({ availableOnly: localAvailableOnly.value })
}

function clearFilters() {
  localSearch.value = ''
  localSource.value = ''
  localGroup.value = ''
  localMechanism.value = ''
  localAvailableOnly.value = true
  
  negotiatorsStore.updateFilter({
    search: '',
    source: '',
    group: '',
    mechanism: '',
    availableOnly: true,
  })
}

function selectNegotiator(negotiator) {
  negotiatorsStore.selectNegotiator(negotiator)
  activeTab.value = 'info'
}

function selectVirtualNegotiator(vn) {
  // TODO: Handle virtual negotiator selection
  console.log('Selected virtual negotiator:', vn)
}

async function loadParameters() {
  if (!selectedNegotiator.value) return
  if (selectedNegotiatorParams.value && selectedNegotiatorParams.value.length > 0) return // Already loaded
  
  await negotiatorsStore.loadNegotiatorParameters(selectedNegotiator.value.type_name)
}

async function createVirtual() {
  if (!newVirtualName.value || !newVirtualBase.value) return
  
  await negotiatorsStore.createVirtualNegotiator(
    newVirtualName.value,
    newVirtualBase.value,
    {},
    newVirtualDescription.value
  )
  
  // Reset form
  showCreateVirtual.value = false
  newVirtualName.value = ''
  newVirtualBase.value = ''
  newVirtualDescription.value = ''
}

async function deleteVirtual(id) {
  if (confirm('Are you sure you want to delete this virtual negotiator?')) {
    await negotiatorsStore.deleteVirtualNegotiator(id)
  }
}

function useInNegotiation() {
  // TODO: Navigate to negotiations with this negotiator selected
  console.log('Use negotiator in negotiation:', selectedNegotiator.value)
}

// Filter save/load functions
async function loadSavedFilters() {
  try {
    const response = await fetch('/api/filters?type=negotiator')
    const data = await response.json()
    if (data.success) {
      savedFilters.value = data.filters
    }
  } catch (error) {
    console.error('Failed to load saved filters:', error)
  }
}

async function saveCurrentFilter() {
  if (!saveFilterName.value) return
  
  saveFilterError.value = ''
  saveFilterSuccess.value = ''
  savingFilter.value = true
  
  try {
    const filterData = {
      search: localSearch.value,
      source: localSource.value,
      group: localGroup.value,
      mechanism: localMechanism.value,
      availableOnly: localAvailableOnly.value,
    }
    
    const response = await fetch('/api/filters', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: saveFilterName.value,
        type: 'negotiator',
        data: filterData,
        description: saveFilterDescription.value,
      }),
    })
    
    const data = await response.json()
    
    if (data.success) {
      saveFilterSuccess.value = 'Filter saved successfully!'
      // Reload saved filters
      await loadSavedFilters()
      // Clear form after 1.5 seconds
      setTimeout(() => {
        showSaveFilterDialog.value = false
        saveFilterName.value = ''
        saveFilterDescription.value = ''
        saveFilterError.value = ''
        saveFilterSuccess.value = ''
      }, 1500)
    } else {
      saveFilterError.value = 'Failed to save filter: ' + (data.error || 'Unknown error')
    }
  } catch (error) {
    saveFilterError.value = 'Failed to save filter: ' + error.message
  } finally {
    savingFilter.value = false
  }
}

async function loadSavedFilter() {
  if (!selectedFilterId.value) return
  
  try {
    const response = await fetch(`/api/filters/${selectedFilterId.value}`)
    const data = await response.json()
    
    if (data.success && data.filter) {
      const filterData = data.filter.data
      
      // Apply filter data to local state
      localSearch.value = filterData.search || ''
      localSource.value = filterData.source || ''
      localGroup.value = filterData.group || ''
      localMechanism.value = filterData.mechanism || ''
      localAvailableOnly.value = filterData.availableOnly ?? true
      
      // Update store
      negotiatorsStore.updateFilter({
        search: localSearch.value,
        source: localSource.value,
        group: localGroup.value,
        mechanism: localMechanism.value,
        availableOnly: localAvailableOnly.value,
      })
      
      // Reload negotiators with new filters
      await negotiatorsStore.loadNegotiators(localSource.value, localGroup.value, localSearch.value)
    }
    
    // Reset selection after loading
    selectedFilterId.value = ''
  } catch (error) {
    console.error('Failed to load filter:', error)
    alert('Failed to load filter: ' + error.message)
  }
}
</script>

<style scoped>
.negotiators-view {
  display: grid;
  grid-template-columns: 350px 1fr;
  height: 100%;
  gap: 8px;
  padding: 16px;
  overflow: hidden;
}

.negotiators-list-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.input-search,
.input-select,
.input-text,
.input-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.input-textarea {
  resize: vertical;
  font-family: inherit;
}

.negotiators-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.negotiator-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.negotiator-item:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.negotiator-item.active {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.negotiator-item.unavailable {
  opacity: 0.6;
}

.negotiator-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.negotiator-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.negotiator-type {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-family: monospace;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.badge-source {
  background: var(--bg-tertiary);
}

.badge-group {
  background: rgba(59, 130, 246, 0.2);
  color: rgb(59, 130, 246);
}

.badge-unavailable {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.badge-required {
  background: rgba(239, 68, 68, 0.2);
  color: rgb(239, 68, 68);
}

.virtual-section {
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
}

.virtual-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.virtual-header h4 {
  margin: 0;
  font-size: 0.95rem;
}

.virtual-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.virtual-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.virtual-item:hover {
  border-color: var(--primary-color);
}

.empty-state-sm {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.85rem;
  padding: 12px;
}

.negotiator-details-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.negotiator-details {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.details-header h2 {
  margin: 0 0 4px 0;
  font-size: 1.3rem;
}

.type-name {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-family: monospace;
}

.header-actions {
  display: flex;
  gap: 8px;
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
  overflow-y: auto;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.info-item span {
  font-size: 1rem;
  color: var(--text-primary);
}

.status-yes {
  color: #10b981;
}

.status-no {
  color: #ef4444;
}

.description-section,
.mechanisms-section,
.tags-section {
  margin-top: 24px;
}

.description-section h3,
.mechanisms-section h3,
.tags-section h3 {
  margin: 0 0 12px 0;
  font-size: 1rem;
}

.description-section p {
  margin: 0;
  line-height: 1.6;
  color: var(--text-primary);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.params-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.param-item {
  padding: 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.param-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.param-name {
  font-weight: 500;
  font-family: monospace;
}

.param-type,
.param-default {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.param-description {
  font-size: 0.9rem;
  color: var(--text-primary);
  line-height: 1.5;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: var(--text-secondary);
  gap: 12px;
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.btn-icon-sm {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.2rem;
  padding: 2px 4px;
  line-height: 1;
}

.btn-icon-sm:hover {
  color: var(--danger-color);
}

/* Modal Styles */
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
  max-width: 500px;
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

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Save filter dialog styles */
.save-filter-modal {
  max-width: 500px;
  width: 90%;
}

.input-text {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 0.9rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: inherit;
}

.input-text:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

textarea.input-text {
  resize: vertical;
  min-height: 60px;
}

.error-message {
  margin: 12px 0 0;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 4px;
  font-size: 0.85rem;
}

.success-message {
  margin: 12px 0 0;
  padding: 8px 12px;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 4px;
  font-size: 0.85rem;
}

.btn-sm {
  font-size: 0.85rem;
  padding: 6px 12px;
}
</style>
