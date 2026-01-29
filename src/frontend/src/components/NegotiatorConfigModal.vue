<template>
  <!-- Negotiator Configuration Modal -->
  <Teleport to="body">
    <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
      <div class="modal medium">
        <div class="modal-header">
          <h3>
            Configure Negotiator
            <span v-if="negotiatorName" class="text-muted" style="font-size: 14px; font-weight: normal;">
              - {{ negotiatorName }}
            </span>
          </h3>
          <button class="modal-close" @click="$emit('close')">×</button>
        </div>
        
        <div class="modal-body">
          <!-- Loading state -->
          <div v-if="loading" class="text-center" style="padding: 40px;">
            <div class="spinner"></div>
            <div class="text-muted" style="margin-top: 12px;">Loading parameters...</div>
          </div>
          
          <!-- Error state -->
          <div v-else-if="error" class="text-center" style="padding: 40px;">
            <div class="text-danger">{{ error }}</div>
          </div>
          
          <!-- No parameters -->
          <div v-else-if="parameters.length === 0" class="text-center" style="padding: 40px;">
            <div class="text-muted">No configurable parameters found for this negotiator type.</div>
          </div>
          
          <!-- Parameters form -->
          <div v-else>
            <div class="form-hint" style="margin-bottom: 16px;">
              Configure parameters for <strong>{{ getDisplayName(negotiatorType) }}</strong>
            </div>
            
            <div style="max-height: 400px; overflow-y: auto;">
              <div
                v-for="param in simpleParameters"
                :key="param.name"
                class="form-group"
                style="margin-bottom: 16px;"
              >
                <!-- Boolean parameters -->
                <div v-if="param.ui_type === 'bool'">
                  <label class="form-checkbox">
                    <input
                      type="checkbox"
                      :checked="values[param.name] ?? param.default"
                      @change="values[param.name] = $event.target.checked"
                    />
                    <span>{{ formatParamName(param.name) }}</span>
                    <span v-if="param.required" class="text-danger">*</span>
                  </label>
                  <div v-if="param.description" class="form-hint">{{ param.description }}</div>
                </div>
                
                <!-- Integer parameters -->
                <div v-else-if="param.ui_type === 'int' || param.ui_type === 'optional_int'">
                  <label class="form-label">
                    <span>{{ formatParamName(param.name) }}</span>
                    <span v-if="param.required" class="text-danger">*</span>
                    <span v-if="param.ui_type === 'optional_int'" class="text-muted">(optional)</span>
                  </label>
                  <input
                    type="number"
                    class="form-input"
                    style="max-width: 200px;"
                    :value="values[param.name] ?? param.default"
                    @input="values[param.name] = $event.target.value ? parseInt($event.target.value) : null"
                    :placeholder="param.default !== null ? String(param.default) : 'None'"
                  />
                  <div v-if="param.description" class="form-hint">{{ param.description }}</div>
                </div>
                
                <!-- Float parameters -->
                <div v-else-if="param.ui_type === 'float' || param.ui_type === 'optional_float'">
                  <label class="form-label">
                    <span>{{ formatParamName(param.name) }}</span>
                    <span v-if="param.required" class="text-danger">*</span>
                    <span v-if="param.ui_type === 'optional_float'" class="text-muted">(optional)</span>
                  </label>
                  <input
                    type="number"
                    class="form-input"
                    style="max-width: 200px;"
                    step="0.01"
                    :value="values[param.name] ?? param.default"
                    @input="values[param.name] = $event.target.value ? parseFloat($event.target.value) : null"
                    :placeholder="param.default !== null ? String(param.default) : 'None'"
                  />
                  <div v-if="param.description" class="form-hint">{{ param.description }}</div>
                </div>
                
                <!-- String parameters -->
                <div v-else-if="param.ui_type === 'string' || param.ui_type === 'optional_string'">
                  <label class="form-label">
                    <span>{{ formatParamName(param.name) }}</span>
                    <span v-if="param.required" class="text-danger">*</span>
                    <span v-if="param.ui_type === 'optional_string'" class="text-muted">(optional)</span>
                  </label>
                  <input
                    type="text"
                    class="form-input"
                    style="max-width: 300px;"
                    :value="values[param.name] ?? param.default ?? ''"
                    @input="values[param.name] = $event.target.value || null"
                    :placeholder="param.default !== null ? String(param.default) : 'None'"
                  />
                  <div v-if="param.description" class="form-hint">{{ param.description }}</div>
                </div>
                
                <!-- Choice parameters -->
                <div v-else-if="param.ui_type === 'choice'">
                  <label class="form-label">
                    <span>{{ formatParamName(param.name) }}</span>
                    <span v-if="param.required" class="text-danger">*</span>
                  </label>
                  <select
                    class="form-select"
                    style="max-width: 200px;"
                    :value="values[param.name] ?? param.default"
                    @change="values[param.name] = $event.target.value"
                  >
                    <option v-for="choice in param.choices" :key="choice" :value="choice">
                      {{ choice }}
                    </option>
                  </select>
                  <div v-if="param.description" class="form-hint">{{ param.description }}</div>
                </div>
              </div>
            </div>
            
            <!-- Show complex parameters as info -->
            <details v-if="complexParameters.length > 0" style="margin-top: 16px;">
              <summary class="text-muted" style="cursor: pointer; font-size: 13px;">
                Advanced parameters (not editable in UI)
              </summary>
              <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 6px; margin-top: 8px;">
                <div
                  v-for="param in complexParameters"
                  :key="param.name"
                  style="margin-bottom: 8px; font-size: 13px;"
                >
                  <code style="background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px;">
                    {{ param.name }}
                  </code>
                  <span class="text-muted">: {{ param.type }}</span>
                </div>
              </div>
            </details>
          </div>
        </div>
        
        <div class="modal-footer">
          <div style="display: flex; gap: 8px; align-items: center; margin-right: auto;">
            <button 
              class="btn btn-secondary" 
              @click="showSaveVirtual = true" 
              :disabled="loading"
              title="Save this configuration as a reusable virtual negotiator"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                <polyline points="17 21 17 13 7 13 7 21"></polyline>
                <polyline points="7 3 7 8 15 8"></polyline>
              </svg>
              Save as Virtual...
            </button>
          </div>
          <button class="btn btn-secondary" @click="$emit('close')">Cancel</button>
          <button class="btn btn-secondary" @click="resetToDefaults">Reset to Defaults</button>
          <button class="btn btn-primary" @click="apply" :disabled="loading">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Apply
          </button>
        </div>
      </div>
    </div>
    
    <!-- Save as Virtual Negotiator Modal -->
    <div v-if="showSaveVirtual" class="modal-overlay active" @click.self="showSaveVirtual = false">
      <div class="modal small">
        <div class="modal-header">
          <h3>Save as Virtual Negotiator</h3>
          <button class="modal-close" @click="showSaveVirtual = false">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Name <span class="text-danger">*</span></label>
            <input
              v-model="virtualName"
              type="text"
              class="form-input"
              placeholder="e.g., My Custom Aspiration"
              @keyup.enter="saveAsVirtual"
            />
            <div class="form-hint">Give this negotiator configuration a memorable name</div>
          </div>
          
          <div class="form-group">
            <label class="form-label">Description</label>
            <textarea
              v-model="virtualDescription"
              class="form-input"
              rows="3"
              placeholder="Optional description of what makes this configuration unique"
            ></textarea>
          </div>
          
          <div class="form-group">
            <label class="form-label">Tags</label>
            <input
              v-model="virtualTags"
              type="text"
              class="form-input"
              placeholder="e.g., aggressive, defensive, tournament"
            />
            <div class="form-hint">Comma-separated tags for organization</div>
          </div>
          
          <div v-if="saveVirtualError" class="text-danger" style="margin-top: 12px;">
            {{ saveVirtualError }}
          </div>
          
          <div v-if="saveVirtualSuccess" class="text-success" style="margin-top: 12px;">
            ✓ Virtual negotiator saved successfully!
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showSaveVirtual = false">Cancel</button>
          <button 
            class="btn btn-primary" 
            @click="saveAsVirtual"
            :disabled="!virtualName.trim() || savingVirtual"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
              <polyline points="17 21 17 13 7 13 7 21"></polyline>
              <polyline points="7 3 7 8 15 8"></polyline>
            </svg>
            {{ savingVirtual ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  negotiatorType: {
    type: String,
    default: ''
  },
  negotiatorName: {
    type: String,
    default: ''
  },
  existingParams: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close', 'apply', 'virtual-saved'])

const loading = ref(false)
const error = ref(null)
const parameters = ref([])
const values = ref({})

// Save as virtual state
const showSaveVirtual = ref(false)
const virtualName = ref('')
const virtualDescription = ref('')
const virtualTags = ref('')
const savingVirtual = ref(false)
const saveVirtualError = ref(null)
const saveVirtualSuccess = ref(false)

// Separate simple and complex parameters
const simpleParameters = computed(() => 
  parameters.value.filter(p => !p.is_complex)
)

const complexParameters = computed(() => 
  parameters.value.filter(p => p.is_complex)
)

// Watch for show changes to load parameters
watch(() => props.show, (newVal) => {
  if (newVal && props.negotiatorType) {
    loadParameters()
  }
})

async function loadParameters() {
  if (!props.negotiatorType) return
  
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(`/api/negotiators/${encodeURIComponent(props.negotiatorType)}/parameters`)
    if (!response.ok) {
      throw new Error(`Failed to load parameters: ${response.statusText}`)
    }
    
    const data = await response.json()
    parameters.value = data.parameters || []
    
    // Initialize values with existing params or defaults
    values.value = { ...props.existingParams }
    
  } catch (e) {
    console.error('Error loading negotiator parameters:', e)
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function formatParamName(name) {
  return name.replace(/_/g, ' ')
}

function getDisplayName(typeName) {
  if (!typeName) return ''
  const parts = typeName.split('.')
  return parts[parts.length - 1]
}

function resetToDefaults() {
  values.value = {}
}

function apply() {
  // Filter out null/undefined values
  const params = {}
  for (const [key, value] of Object.entries(values.value)) {
    if (value !== null && value !== undefined && value !== '') {
      params[key] = value
    }
  }
  
  // Emit only params (time pressure handled separately now)
  emit('apply', { params })
  emit('close')
}

async function saveAsVirtual() {
  if (!virtualName.value.trim()) {
    saveVirtualError.value = 'Name is required'
    return
  }
  
  savingVirtual.value = true
  saveVirtualError.value = null
  saveVirtualSuccess.value = false
  
  try {
    // Prepare params (same as apply)
    const params = {}
    for (const [key, value] of Object.entries(values.value)) {
      if (value !== null && value !== undefined && value !== '') {
        params[key] = value
      }
    }
    
    // Parse tags
    const tags = virtualTags.value
      .split(',')
      .map(t => t.trim())
      .filter(t => t.length > 0)
    
    // Create virtual negotiator
    const response = await fetch('/api/negotiators/virtual', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: virtualName.value.trim(),
        base_type_name: props.negotiatorType,
        params: params,
        description: virtualDescription.value.trim(),
        tags: tags
      })
    })
    
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to save virtual negotiator')
    }
    
    saveVirtualSuccess.value = true
    
    // Reset form and close after delay
    setTimeout(() => {
      showSaveVirtual.value = false
      virtualName.value = ''
      virtualDescription.value = ''
      virtualTags.value = ''
      saveVirtualSuccess.value = false
      
      // Emit event so parent can refresh negotiator list if needed
      emit('virtual-saved')
    }, 1500)
    
  } catch (e) {
    console.error('Error saving virtual negotiator:', e)
    saveVirtualError.value = e.message
  } finally {
    savingVirtual.value = false
  }
}
</script>

<style scoped>
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
