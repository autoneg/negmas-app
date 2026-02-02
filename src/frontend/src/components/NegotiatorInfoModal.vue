<template>
  <!-- Negotiator Info Modal -->
  <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
    <div class="modal-content modal-lg">
      <!-- Header -->
      <div class="modal-header">
        <h3 class="modal-title">Negotiator Information</h3>
        <button class="modal-close-btn" @click="$emit('close')" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <!-- Body -->
      <div class="modal-body" style="max-height: 80vh; overflow-y: auto; background: var(--bg-primary);">
        <div v-if="isLoading" class="empty-state" style="padding: 40px;">
          <div class="loading-spinner"></div>
          <p>Loading negotiator information...</p>
        </div>
        
        <div v-else-if="loadError" class="empty-state" style="padding: 40px;">
          <p style="color: var(--text-error);">{{ loadError }}</p>
          <button @click="loadData" class="btn btn-primary" style="margin-top: 16px;">
            Retry
          </button>
        </div>
        
        <div v-else-if="!negotiatorInfo" class="empty-state" style="padding: 40px;">
          <p>No information available for this negotiator.</p>
        </div>
        
        <div v-else class="info-container">
          <!-- Two-column layout -->
          <div class="info-grid-2col">
            <!-- Basic Information Panel -->
            <div class="info-section">
              <h4 class="info-section-title">
                <span class="collapse-icon">&#9660;</span>
                Basic Information
              </h4>
              <div class="info-rows">
                <div class="info-row">
                  <span class="info-label">Name:</span>
                  <span class="info-value">{{ negotiatorInfo.name }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Source:</span>
                  <span class="info-value">
                    <span class="badge badge-source">{{ negotiatorInfo.source }}</span>
                  </span>
                </div>
                <div v-if="negotiatorInfo.group" class="info-row">
                  <span class="info-label">Group:</span>
                  <span class="info-value">
                    <span class="badge badge-group">{{ negotiatorInfo.group }}</span>
                  </span>
                </div>
                <div class="info-row">
                  <span class="info-label">Available:</span>
                  <span class="info-value">
                    <span v-if="negotiatorInfo.available" class="status-badge success">Yes</span>
                    <span v-else class="status-badge warning">No</span>
                  </span>
                </div>
                <div v-if="negotiatorInfo.requires_bridge !== undefined" class="info-row">
                  <span class="info-label">Requires Bridge:</span>
                  <span class="info-value">
                    <span v-if="negotiatorInfo.requires_bridge" class="status-badge warning">Yes</span>
                    <span v-else class="status-badge success">No</span>
                  </span>
                </div>
              </div>
            </div>
            
            <!-- Type Information Panel -->
            <div class="info-section">
              <h4 class="info-section-title">
                <span class="collapse-icon">&#9660;</span>
                Type Information
              </h4>
              <div class="info-rows">
                <div class="info-row full-width">
                  <span class="info-label">Full Class Name:</span>
                  <span class="info-value monospace small">{{ negotiatorInfo.type_name }}</span>
                </div>
                <div v-if="negotiatorInfo.module_path" class="info-row full-width">
                  <span class="info-label">Module Path:</span>
                  <span class="info-value monospace small">{{ negotiatorInfo.module_path }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Description (full width) -->
          <div v-if="negotiatorInfo.description" class="info-section full-width">
            <h4 class="info-section-title">
              <span class="collapse-icon">&#9660;</span>
              Description
            </h4>
            <div class="description-content">
              {{ negotiatorInfo.description }}
            </div>
          </div>
          
          <!-- Two-column layout for tags and mechanisms -->
          <div class="info-grid-2col">
            <!-- Tags Panel -->
            <div class="info-section">
              <h4 class="info-section-title">
                <span class="collapse-icon">&#9660;</span>
                Tags
              </h4>
              <div v-if="negotiatorInfo.tags && negotiatorInfo.tags.length > 0" class="tags-container">
                <span v-for="(tag, idx) in negotiatorInfo.tags" :key="`tag-${idx}`" class="tag-chip">
                  {{ tag }}
                </span>
              </div>
              <div v-else class="empty-text">No tags</div>
            </div>
            
            <!-- Mechanisms Panel -->
            <div class="info-section">
              <h4 class="info-section-title">
                <span class="collapse-icon">&#9660;</span>
                Supported Mechanisms
              </h4>
              <div v-if="negotiatorInfo.mechanisms && negotiatorInfo.mechanisms.length > 0" class="tags-container">
                <span v-for="(mech, idx) in negotiatorInfo.mechanisms" :key="`mech-${idx}`" class="mechanism-chip">
                  {{ mech }}
                </span>
              </div>
              <div v-else class="empty-text">All mechanisms (no restrictions)</div>
            </div>
          </div>
          
          <!-- Parameters Section (full width) -->
          <div class="info-section full-width">
            <h4 class="info-section-title clickable" @click="showParams = !showParams">
              <span class="collapse-icon">{{ showParams ? '&#9660;' : '&#9654;' }}</span>
              Configurable Parameters
              <span class="param-count" v-if="parameters.length > 0">({{ parameters.length }})</span>
            </h4>
            <div v-if="showParams">
              <div v-if="loadingParams" class="empty-state" style="padding: 20px;">
                <div class="loading-spinner-small"></div>
                <p style="margin-top: 8px;">Loading parameters...</p>
              </div>
              <div v-else-if="parameters.length === 0" class="empty-text">
                No configurable parameters
              </div>
              <div v-else class="params-list">
                <div v-for="param in parameters" :key="param.name" class="param-item">
                  <div class="param-header">
                    <span class="param-name">{{ param.name }}</span>
                    <span v-if="param.required" class="badge badge-required">Required</span>
                    <span class="param-type">{{ param.type }}</span>
                  </div>
                  <div v-if="param.default !== null && param.default !== undefined" class="param-default">
                    Default: <code>{{ formatDefault(param.default) }}</code>
                  </div>
                  <div v-if="param.description" class="param-description">
                    {{ param.description }}
                  </div>
                  <div v-if="param.choices && param.choices.length > 0" class="param-choices">
                    Choices: {{ param.choices.join(', ') }}
                  </div>
                  <div v-if="param.min_value !== null || param.max_value !== null" class="param-range">
                    Range: {{ param.min_value ?? '-inf' }} to {{ param.max_value ?? '+inf' }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  typeName: {
    type: String,
    default: ''
  },
  // Optional: pass existing info to avoid re-fetching
  negotiator: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const negotiatorInfo = ref(null)
const parameters = ref([])
const isLoading = ref(false)
const loadingParams = ref(false)
const loadError = ref(null)
const showParams = ref(false)

// Load data when modal opens
watch(() => props.show, async (show) => {
  if (show && props.typeName) {
    await loadData()
  }
}, { immediate: true })

// Also watch for type name changes
watch(() => props.typeName, async (newType) => {
  if (props.show && newType) {
    await loadData()
  }
})

async function loadData() {
  if (!props.typeName) return
  
  isLoading.value = true
  loadError.value = null
  
  try {
    // If we have existing negotiator info passed as prop, use it
    if (props.negotiator) {
      negotiatorInfo.value = {
        type_name: props.negotiator.type_name,
        name: props.negotiator.name,
        source: props.negotiator.source,
        group: props.negotiator.group,
        description: props.negotiator.description,
        tags: props.negotiator.tags,
        mechanisms: props.negotiator.mechanisms,
        requires_bridge: props.negotiator.requires_bridge,
        available: props.negotiator.available,
        module_path: props.negotiator.module_path
      }
    } else {
      // Fetch negotiator info from API
      const encodedType = encodeURIComponent(props.typeName)
      const response = await fetch(`/api/negotiators/${encodedType}`)
      if (response.ok) {
        negotiatorInfo.value = await response.json()
      } else {
        loadError.value = `Failed to load negotiator info: ${response.status}`
        return
      }
    }
    
    // Load parameters
    await loadParameters()
  } catch (err) {
    console.error('[NegotiatorInfoModal] Failed to load data:', err)
    loadError.value = `Failed to load negotiator info: ${err.message}`
  } finally {
    isLoading.value = false
  }
}

async function loadParameters() {
  if (!props.typeName) return
  
  loadingParams.value = true
  try {
    const encodedType = encodeURIComponent(props.typeName)
    const response = await fetch(`/api/negotiators/${encodedType}/parameters`)
    if (response.ok) {
      const data = await response.json()
      parameters.value = data.parameters || []
    }
  } catch (err) {
    console.error('[NegotiatorInfoModal] Failed to load parameters:', err)
  } finally {
    loadingParams.value = false
  }
}

function formatDefault(value) {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<style scoped>
.modal-lg {
  max-width: 900px;
  width: 95vw;
  max-height: 90vh;
}

.modal-header {
  background: var(--bg-secondary);
}

.modal-footer {
  background: var(--bg-secondary);
}

.modal-close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.modal-close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-close-btn svg {
  width: 18px;
  height: 18px;
}

.info-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px;
}

.info-grid-2col {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-section {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.info-section.full-width {
  grid-column: 1 / -1;
}

.info-section-title {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-section-title.clickable {
  cursor: pointer;
}

.info-section-title.clickable:hover {
  color: var(--accent-primary);
}

.collapse-icon {
  font-size: 10px;
  color: var(--text-tertiary);
}

.info-rows {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 4px 0;
  gap: 8px;
}

.info-row:not(:last-child) {
  border-bottom: 1px solid var(--border-color);
}

.info-row.full-width {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.info-value {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
  text-align: right;
  word-break: break-word;
}

.info-value.monospace {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-weight: 400;
  text-align: left;
}

.info-value.monospace.small {
  font-size: 11px;
}

.description-content {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.mechanism-chip {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #e3f2fd;
  color: #1565c0;
}

.empty-text {
  font-size: 11px;
  color: var(--text-tertiary);
  font-style: italic;
  text-align: center;
  padding: 8px;
}

/* Badges */
.badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.badge-source {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.badge-group {
  background: #e8f5e9;
  color: #2e7d32;
}

.badge-required {
  background: #ffebee;
  color: #c62828;
}

.status-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.status-badge.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-badge.warning {
  background: #fff3e0;
  color: #e65100;
}

/* Parameters */
.param-count {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 400;
}

.params-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.param-item {
  padding: 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.param-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.param-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'SF Mono', Monaco, monospace;
}

.param-type {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: 'SF Mono', Monaco, monospace;
}

.param-default {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.param-default code {
  background: var(--bg-tertiary);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 10px;
}

.param-description {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 6px;
  line-height: 1.4;
}

.param-choices,
.param-range {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-radius: 50%;
  border-top-color: var(--accent-primary);
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

.loading-spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-radius: 50%;
  border-top-color: var(--accent-primary);
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .info-grid-2col {
    grid-template-columns: 1fr;
  }
}
</style>
