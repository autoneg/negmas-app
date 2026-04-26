<template>
  <!-- Negotiator/Component Selector Modal -->
  <Teleport to="body">
    <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
      <div class="modal large">
        <div class="modal-header">
          <h3>
            {{ modalTitle }}
          </h3>
          <button class="modal-close" @click="$emit('close')">x</button>
        </div>
        
        <div class="modal-body">
          <!-- Mode Tabs (when selecting negotiators) -->
          <div v-if="componentType === 'negotiator'" class="sub-tabs">
            <button
              class="tab"
              :class="{ active: selectionMode === 'preset' }"
              @click="selectionMode = 'preset'"
            >
              Preset Negotiators
            </button>
            <button
              class="tab"
              :class="{ active: selectionMode === 'virtual' }"
              @click="selectionMode = 'virtual'; loadVirtualNegotiators()"
            >
              Virtual Negotiators
            </button>
          </div>
          
          <!-- Loading state -->
          <div v-if="loading" class="text-center" style="padding: 40px;">
            <div class="spinner"></div>
            <div class="text-muted" style="margin-top: 12px;">Loading...</div>
          </div>
          
          <!-- Error state -->
          <div v-else-if="error" class="text-center" style="padding: 40px;">
            <div class="text-danger">{{ error }}</div>
            <button class="btn btn-secondary" style="margin-top: 12px;" @click="loadData">
              Retry
            </button>
          </div>
          
          <!-- Selection UI -->
          <div v-else>
            <!-- Search and Filters -->
            <div class="filter-row">
              <input
                type="text"
                class="form-input"
                :placeholder="searchPlaceholder"
                v-model="searchQuery"
              />
              <select
                v-if="componentType === 'negotiator' && selectionMode === 'preset'"
                class="form-select"
                v-model="sourceFilter"
              >
                <option value="">All Sources</option>
                <option v-for="source in sources" :key="source" :value="source">{{ source }}</option>
              </select>
            </div>
            
            <!-- Selected Items (for list/iterable mode) -->
            <div v-if="isList || isIterable" class="selected-items-section">
              <label class="form-label">
                Selected {{ componentTypeLabel }}s ({{ selectedItems.length }})
                <span v-if="isRequired && selectedItems.length === 0" class="text-danger">*</span>
              </label>
              <div class="selected-items-list">
                <div v-if="selectedItems.length === 0" class="text-muted" style="padding: 8px;">
                  No items selected. Click items below to add them.
                </div>
                <div
                  v-for="(item, index) in selectedItems"
                  :key="'selected-' + index"
                  class="selected-item"
                >
                  <div class="selected-item-content">
                    <div class="selected-item-name">{{ item.name || item.type_name }}</div>
                    <div v-if="item.params && Object.keys(item.params).length > 0" class="selected-item-params">
                      {{ formatParams(item.params) }}
                    </div>
                  </div>
                  <button
                    class="btn-icon btn-sm"
                    @click="configureSelectedItem(index)"
                    title="Configure"
                    v-if="componentType === 'negotiator'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                      <circle cx="12" cy="12" r="3"></circle>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                  </button>
                  <button
                    class="btn-icon btn-sm text-danger"
                    @click="removeSelectedItem(index)"
                    title="Remove"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Available Items Grid -->
            <div class="available-items-section">
              <label class="form-label">
                Available {{ componentTypeLabel }}s
                <span class="text-muted">({{ filteredItems.length }} found)</span>
              </label>
              <div class="items-grid">
                <div
                  v-for="item in filteredItems"
                  :key="item.type_name || item.name"
                  class="item-card"
                  :class="{ 
                    selected: isItemSelected(item),
                    disabled: !item.available && componentType === 'negotiator'
                  }"
                  @click="selectItem(item)"
                >
                  <div class="item-card-header">
                    <div class="item-card-name">{{ item.name }}</div>
                    <button 
                      v-if="componentType === 'negotiator'"
                      class="info-icon-btn" 
                      @click.stop="showItemInfo(item)"
                      title="View details"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                      </svg>
                    </button>
                  </div>
                  <div class="item-card-meta">
                    <span v-if="item.source" class="badge badge-sm">{{ item.source }}</span>
                    <span v-if="item.component_type" class="badge badge-sm">{{ item.component_type }}</span>
                  </div>
                  <div v-if="item.description" class="item-card-desc">
                    {{ truncateDescription(item.description) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
          <button 
            class="btn btn-primary" 
            @click="applySelection"
            :disabled="!canApply"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Apply
          </button>
        </div>
      </div>
    </div>
    
    <!-- Nested: Negotiator Config Modal for configuring selected items -->
    <NegotiatorConfigModal
      :show="showConfigModal"
      :negotiator-type="configModalType"
      :negotiator-name="configModalName"
      :existing-params="configModalParams"
      @close="showConfigModal = false"
      @apply="onConfigApply"
    />
    
    <!-- Nested: Negotiator Info Modal -->
    <NegotiatorInfoModal
      :show="showInfoModal"
      :type-name="infoModalTypeName"
      :negotiator="infoModalNegotiator"
      @close="showInfoModal = false"
    />
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import NegotiatorConfigModal from './NegotiatorConfigModal.vue'
import NegotiatorInfoModal from './NegotiatorInfoModal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  // Component type: 'negotiator', 'acceptance', 'offering', 'model', 'component'
  componentType: {
    type: String,
    default: 'negotiator'
  },
  // Parameter name (for display)
  paramName: {
    type: String,
    default: ''
  },
  // Whether this is a list/iterable parameter
  isList: {
    type: Boolean,
    default: false
  },
  isIterable: {
    type: Boolean,
    default: false
  },
  isDict: {
    type: Boolean,
    default: false
  },
  // Whether the parameter is required
  isRequired: {
    type: Boolean,
    default: false
  },
  // Existing value (for editing)
  existingValue: {
    type: [Array, Object, null],
    default: null
  }
})

const emit = defineEmits(['close', 'apply'])

// State
const loading = ref(false)
const error = ref(null)
const searchQuery = ref('')
const sourceFilter = ref('')
const selectionMode = ref('preset')

// Available items
const negotiators = ref([])
const virtualNegotiators = ref([])
const components = ref([])
const sources = ref([])

// Selected items (for list/iterable mode)
const selectedItems = ref([])
// Single selected item (for non-list mode)
const selectedItem = ref(null)

// Nested modals
const showConfigModal = ref(false)
const configModalType = ref('')
const configModalName = ref('')
const configModalParams = ref({})
const configItemIndex = ref(-1)

const showInfoModal = ref(false)
const infoModalTypeName = ref('')
const infoModalNegotiator = ref(null)

// Computed
const modalTitle = computed(() => {
  const action = (props.isList || props.isIterable) ? 'Select' : 'Choose'
  const type = componentTypeLabel.value
  return props.paramName 
    ? `${action} ${type} for "${props.paramName}"`
    : `${action} ${type}`
})

const componentTypeLabel = computed(() => {
  switch (props.componentType) {
    case 'negotiator': return 'Negotiator'
    case 'acceptance': return 'Acceptance Policy'
    case 'offering': return 'Offering Policy'
    case 'model': return 'Model'
    case 'component': return 'Component'
    default: return 'Item'
  }
})

const searchPlaceholder = computed(() => {
  return `Search ${componentTypeLabel.value.toLowerCase()}s...`
})

const filteredItems = computed(() => {
  let items = []
  
  if (props.componentType === 'negotiator') {
    items = selectionMode.value === 'preset' 
      ? negotiators.value 
      : virtualNegotiators.value
  } else {
    // For BOA components
    items = components.value
  }
  
  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    items = items.filter(item => 
      item.name?.toLowerCase().includes(query) ||
      item.description?.toLowerCase().includes(query) ||
      item.type_name?.toLowerCase().includes(query)
    )
  }
  
  // Apply source filter (for negotiators)
  if (sourceFilter.value && props.componentType === 'negotiator') {
    items = items.filter(item => item.source === sourceFilter.value)
  }
  
  return items
})

const canApply = computed(() => {
  if (props.isList || props.isIterable) {
    return !props.isRequired || selectedItems.value.length > 0
  }
  return !!selectedItem.value
})

// Watch for modal open
watch(() => props.show, async (newVal) => {
  if (newVal) {
    // Reset state
    searchQuery.value = ''
    sourceFilter.value = ''
    error.value = null
    
    // Initialize selected items from existing value
    if (props.existingValue) {
      if (props.isList || props.isIterable) {
        selectedItems.value = Array.isArray(props.existingValue) 
          ? [...props.existingValue] 
          : []
      } else {
        selectedItem.value = props.existingValue
      }
    } else {
      selectedItems.value = []
      selectedItem.value = null
    }
    
    await loadData()
  }
})

// Methods
async function loadData() {
  loading.value = true
  error.value = null
  
  try {
    if (props.componentType === 'negotiator') {
      await loadNegotiators()
    } else {
      await loadComponents()
    }
  } catch (e) {
    console.error('Error loading data:', e)
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function loadNegotiators() {
  const response = await fetch('/api/negotiators')
  if (!response.ok) {
    throw new Error(`Failed to load negotiators: ${response.statusText}`)
  }
  const data = await response.json()
  negotiators.value = data.negotiators || []
  
  // Extract unique sources
  const uniqueSources = new Set(negotiators.value.map(n => n.source).filter(Boolean))
  sources.value = [...uniqueSources].sort()
}

async function loadVirtualNegotiators() {
  const response = await fetch('/api/negotiators/virtual')
  if (!response.ok) {
    throw new Error(`Failed to load virtual negotiators: ${response.statusText}`)
  }
  const data = await response.json()
  virtualNegotiators.value = (data.virtual_negotiators || []).map(vn => ({
    ...vn,
    name: vn.name,
    type_name: vn.base_type_name,
    source: 'virtual',
    available: true,
    is_virtual: true
  }))
}

async function loadComponents() {
  const response = await fetch('/api/negotiators/boa/components')
  if (!response.ok) {
    throw new Error(`Failed to load components: ${response.statusText}`)
  }
  const data = await response.json()
  
  // Filter by component type
  const componentTypeMap = {
    'acceptance': 'acceptance',
    'offering': 'offering',
    'model': 'model'
  }
  const typeKey = componentTypeMap[props.componentType] || props.componentType
  
  if (data.components && data.components[typeKey]) {
    components.value = data.components[typeKey]
  } else {
    // If no specific type, combine all
    components.value = Object.values(data.components || {}).flat()
  }
}

function isItemSelected(item) {
  const key = item.type_name || item.name
  if (props.isList || props.isIterable) {
    return selectedItems.value.some(s => (s.type_name || s.name) === key)
  }
  return selectedItem.value && (selectedItem.value.type_name || selectedItem.value.name) === key
}

function selectItem(item) {
  if (!item.available && props.componentType === 'negotiator' && !item.is_virtual) {
    return // Don't select unavailable negotiators
  }
  
  if (props.isList || props.isIterable) {
    // Toggle selection for list mode
    const key = item.type_name || item.name
    const existingIndex = selectedItems.value.findIndex(s => (s.type_name || s.name) === key)
    
    if (existingIndex >= 0) {
      // Already selected - remove it
      selectedItems.value.splice(existingIndex, 1)
    } else {
      // Add to selection
      selectedItems.value.push({
        type_name: item.type_name,
        name: item.name,
        source: item.source,
        params: {},
        is_virtual: item.is_virtual || false
      })
    }
  } else {
    // Single selection mode
    selectedItem.value = {
      type_name: item.type_name,
      name: item.name,
      source: item.source,
      params: {},
      is_virtual: item.is_virtual || false
    }
  }
}

function removeSelectedItem(index) {
  selectedItems.value.splice(index, 1)
}

function configureSelectedItem(index) {
  const item = selectedItems.value[index]
  configItemIndex.value = index
  configModalType.value = item.type_name
  configModalName.value = item.name
  configModalParams.value = item.params || {}
  showConfigModal.value = true
}

function onConfigApply({ params }) {
  if (configItemIndex.value >= 0 && configItemIndex.value < selectedItems.value.length) {
    selectedItems.value[configItemIndex.value].params = params
  }
  showConfigModal.value = false
}

function showItemInfo(item) {
  infoModalTypeName.value = item.type_name
  infoModalNegotiator.value = item
  showInfoModal.value = true
}

function truncateDescription(desc) {
  if (!desc) return ''
  return desc.length > 100 ? desc.substring(0, 100) + '...' : desc
}

function formatParams(params) {
  if (!params || Object.keys(params).length === 0) return ''
  return Object.entries(params)
    .slice(0, 3)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
}

function applySelection() {
  if (props.isList || props.isIterable) {
    emit('apply', selectedItems.value)
  } else {
    emit('apply', selectedItem.value)
  }
  emit('close')
}
</script>

<style scoped>
.sub-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  padding: 4px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.sub-tabs .tab {
  flex: 1;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.sub-tabs .tab:hover {
  color: var(--text-primary);
  background: var(--bg-secondary);
}

.sub-tabs .tab.active {
  background: var(--bg-primary);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-row .form-input {
  flex: 1;
}

.filter-row .form-select {
  min-width: 150px;
}

.selected-items-section {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.selected-items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 150px;
  overflow-y: auto;
}

.selected-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.selected-item-content {
  flex: 1;
  min-width: 0;
}

.selected-item-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.selected-item-params {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.available-items-section {
  flex: 1;
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
  padding: 4px;
}

.item-card {
  padding: 12px;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.item-card:hover {
  border-color: var(--primary);
  background: var(--bg-tertiary);
}

.item-card.selected {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, var(--bg-secondary));
}

.item-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.item-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}

.item-card-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.item-card-meta {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.item-card-desc {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.badge-sm {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.info-icon-btn {
  padding: 4px;
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-icon-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-icon {
  padding: 4px;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-icon.text-danger:hover {
  color: var(--danger);
}

.spinner {
  border: 3px solid var(--border-color);
  border-top-color: var(--primary);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
