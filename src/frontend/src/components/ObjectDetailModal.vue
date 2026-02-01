<template>
  <Teleport to="body">
    <div v-if="show" class="odm-overlay" @click.self="$emit('close')">
      <div class="odm-modal" :class="{ 'odm-large': large }">
        <!-- Header -->
        <div class="odm-header">
          <div class="odm-title-section">
            <h3>{{ title || 'Object Details' }}</h3>
            <span v-if="objectType" class="odm-type-badge">{{ objectType }}</span>
          </div>
          <div class="odm-actions">
            <button 
              class="odm-btn-icon" 
              @click="copyToClipboard" 
              :title="copied ? 'Copied!' : 'Copy as JSON'"
            >
              {{ copied ? '✓' : '📋' }}
            </button>
            <button 
              class="odm-btn-icon" 
              @click="expandAll"
              title="Expand all"
            >
              ⊞
            </button>
            <button 
              class="odm-btn-icon" 
              @click="collapseAll"
              title="Collapse all"
            >
              ⊟
            </button>
            <button class="odm-btn-close" @click="$emit('close')">×</button>
          </div>
        </div>
        
        <!-- Body -->
        <div class="odm-body">
          <!-- Loading State -->
          <div v-if="loading" class="odm-loading-state">
            <div class="odm-loading-spinner"></div>
            <p>Loading data...</p>
          </div>
          
          <!-- Error State -->
          <div v-else-if="error" class="odm-error-state">
            <p>{{ error }}</p>
            <button v-if="fetchUrl" @click="fetchData" class="odm-btn odm-btn-primary">
              Retry
            </button>
          </div>
          
          <!-- Tree View -->
          <div v-else-if="displayData" class="odm-tree-container" ref="treeContainer">
            <TreeView 
              :data="displayData" 
              :default-expand-depth="expandDepth"
              :key="treeKey"
            />
          </div>
          
          <!-- Empty State -->
          <div v-else class="odm-empty-state">
            <p>No data available</p>
          </div>
        </div>
        
        <!-- Footer (optional) -->
        <div v-if="$slots.footer" class="odm-footer">
          <slot name="footer"></slot>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import TreeView from './TreeView.vue'

const props = defineProps({
  // Control visibility
  show: {
    type: Boolean,
    default: false
  },
  // Title for the modal
  title: {
    type: String,
    default: ''
  },
  // Object type badge (e.g., "UtilityFunction", "OutcomeSpace")
  objectType: {
    type: String,
    default: ''
  },
  // Data to display (if provided directly)
  data: {
    type: [Object, Array],
    default: null
  },
  // URL to fetch data from (alternative to data prop)
  fetchUrl: {
    type: String,
    default: ''
  },
  // Make modal larger
  large: {
    type: Boolean,
    default: true
  },
  // Default expand depth
  defaultExpandDepth: {
    type: Number,
    default: 2
  }
})

const emit = defineEmits(['close', 'loaded', 'error'])

// State
const loading = ref(false)
const error = ref(null)
const fetchedData = ref(null)
const expandDepth = ref(props.defaultExpandDepth)
const treeKey = ref(0)
const copied = ref(false)
const treeContainer = ref(null)

// Computed data to display
const displayData = computed(() => {
  if (props.data) return props.data
  if (fetchedData.value?.data) return fetchedData.value.data
  return fetchedData.value
})

// Watch for show changes to trigger fetch
watch(() => props.show, (newShow) => {
  if (newShow && props.fetchUrl) {
    fetchData()
  }
})

// Watch for URL changes - always refetch when URL changes
watch(() => props.fetchUrl, (newUrl, oldUrl) => {
  if (newUrl !== oldUrl) {
    fetchedData.value = null
    error.value = null
    if (props.show && newUrl) {
      fetchData()
    }
  }
})

// Fetch data from URL
async function fetchData() {
  if (!props.fetchUrl) return
  
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(props.fetchUrl)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    const data = await response.json()
    fetchedData.value = data
    emit('loaded', data)
  } catch (err) {
    error.value = `Failed to load data: ${err.message}`
    emit('error', err)
  } finally {
    loading.value = false
  }
}

// Expand all nodes
function expandAll() {
  expandDepth.value = 100
  treeKey.value++
}

// Collapse all nodes
function collapseAll() {
  expandDepth.value = 0
  treeKey.value++
}

// Copy data to clipboard as JSON
async function copyToClipboard() {
  try {
    const jsonStr = JSON.stringify(displayData.value, null, 2)
    await navigator.clipboard.writeText(jsonStr)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

// Initial fetch if URL provided and modal is shown
onMounted(() => {
  if (props.show && props.fetchUrl) {
    fetchData()
  }
})
</script>

<style>
/* ObjectDetailModal styles - NOT scoped because of Teleport */
.odm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2100;
  padding: 20px;
}

.odm-modal {
  background: var(--bg-primary, white);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  max-height: 80vh;
  width: 600px;
  max-width: 90vw;
}

.odm-modal.odm-large {
  width: 900px;
  max-height: 85vh;
}

.odm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  flex-shrink: 0;
}

.odm-title-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.odm-title-section h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #333);
}

.odm-type-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #28a745;
  color: white;
  font-weight: 500;
}

.odm-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.odm-btn-icon {
  background: none;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary, #666);
  transition: all 0.2s;
}

.odm-btn-icon:hover {
  background: var(--bg-secondary, #f5f5f5);
  border-color: var(--text-secondary, #666);
}

.odm-btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-secondary, #666);
  padding: 0 4px;
  line-height: 1;
}

.odm-btn-close:hover {
  color: var(--text-primary, #333);
}

.odm-body {
  flex: 1;
  overflow: auto;
  padding: 0;
  min-height: 200px;
}

.odm-tree-container {
  padding: 12px;
  overflow: auto;
  max-height: 100%;
}

.odm-loading-state,
.odm-error-state,
.odm-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--text-secondary, #666);
}

.odm-loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color, #e0e0e0);
  border-top-color: var(--accent-primary, #007bff);
  border-radius: 50%;
  animation: odm-spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes odm-spin {
  to { transform: rotate(360deg); }
}

.odm-error-state {
  color: var(--color-error, #dc3545);
}

.odm-error-state .odm-btn {
  margin-top: 12px;
}

.odm-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border-color, #e0e0e0);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.odm-btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: none;
}

.odm-btn-primary {
  background: var(--accent-primary, #007bff);
  color: white;
}

.odm-btn-primary:hover {
  background: var(--accent-primary-hover, #0056b3);
}

/* Dark mode */
:root[data-theme="dark"] .odm-modal,
.dark .odm-modal {
  --bg-primary: #1e1e1e;
  --bg-secondary: #2d2d2d;
  --text-primary: #e0e0e0;
  --text-secondary: #b0b0b0;
  --border-color: #404040;
}
</style>
