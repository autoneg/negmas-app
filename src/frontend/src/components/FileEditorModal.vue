<template>
  <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
    <div class="modal-content modal-xl file-editor-modal">
      <!-- Header -->
      <div class="modal-header">
        <div class="header-title-section">
          <h3 class="modal-title">{{ title }}</h3>
          <span class="file-path">{{ filePath }}</span>
        </div>
        <div class="header-actions">
          <button 
            v-if="hasChanges" 
            class="btn btn-secondary btn-sm" 
            @click="revert"
            title="Revert changes"
          >
            Revert
          </button>
          <button 
            class="btn btn-primary btn-sm" 
            @click="save"
            :disabled="saving || !hasChanges"
          >
            <span v-if="saving">Saving...</span>
            <span v-else>Save</span>
          </button>
          <button class="modal-close-btn" @click="close" title="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>
      
      <!-- Body -->
      <div class="modal-body">
        <div v-if="loading" class="loading-state">
          <span class="spinner"></span> Loading file...
        </div>
        
        <div v-else-if="error" class="error-state">
          <p class="error-message">{{ error }}</p>
          <button class="btn btn-secondary" @click="$emit('close')">Close</button>
        </div>
        
        <div v-else class="editor-container">
          <textarea
            ref="editor"
            v-model="content"
            class="code-editor"
            :placeholder="'Edit ' + filePath"
            spellcheck="false"
          ></textarea>
          
          <div class="editor-footer">
            <span class="file-info">
              {{ fileInfo }}
            </span>
            <span v-if="saveSuccess" class="save-success">
              ✓ Saved successfully. Caches invalidated.
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  show: Boolean,
  scenarioId: String,
  filePath: String,
  title: String,
})

const emit = defineEmits(['close', 'saved'])

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const content = ref('')
const originalContent = ref('')
const saveSuccess = ref(false)
const editor = ref(null)

const hasChanges = computed(() => content.value !== originalContent.value)

const fileInfo = computed(() => {
  const lines = content.value.split('\n').length
  const chars = content.value.length
  const bytes = new Blob([content.value]).size
  return `${lines} lines, ${chars} characters, ${bytes} bytes`
})

// Watch for show changes to load content
watch(() => props.show, async (show) => {
  if (show && props.scenarioId && props.filePath) {
    await loadFile()
  } else {
    // Reset state when closing
    content.value = ''
    originalContent.value = ''
    error.value = ''
    saveSuccess.value = false
  }
})

async function loadFile() {
  loading.value = true
  error.value = ''
  
  try {
    const response = await fetch(`/api/scenarios/${props.scenarioId}/files/${props.filePath}`)
    const data = await response.json()
    
    if (data.success) {
      content.value = data.content
      originalContent.value = data.content
    } else {
      error.value = 'Failed to load file: ' + (data.error || 'Unknown error')
    }
  } catch (err) {
    error.value = 'Failed to load file: ' + err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  saveSuccess.value = false
  error.value = ''
  
  try {
    const response = await fetch(
      `/api/scenarios/${props.scenarioId}/files/${props.filePath}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: content.value,
        }),
      }
    )
    
    const data = await response.json()
    
    if (data.success) {
      originalContent.value = content.value
      saveSuccess.value = true
      
      // Hide success message after 3 seconds
      setTimeout(() => {
        saveSuccess.value = false
      }, 3000)
      
      // Emit saved event to parent
      emit('saved')
    } else {
      error.value = 'Failed to save file: ' + (data.error || 'Unknown error')
    }
  } catch (err) {
    error.value = 'Failed to save file: ' + err.message
  } finally {
    saving.value = false
  }
}

function revert() {
  if (confirm('Discard all changes and revert to the original content?')) {
    content.value = originalContent.value
  }
}

function close() {
  if (hasChanges.value) {
    if (confirm('You have unsaved changes. Are you sure you want to close?')) {
      emit('close')
    }
  } else {
    emit('close')
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-content {
  background: var(--bg-secondary);
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  position: relative;
}

.modal-xl {
  max-width: 1000px;
  width: 95%;
  max-height: 90vh;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  border-radius: 12px 12px 0 0;
  position: relative;
  z-index: 1;
}

.file-editor-modal .modal-body {
  padding: 0;
  max-height: calc(90vh - 120px);
  overflow: hidden;
}

.header-title-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.file-path {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-family: 'Monaco', 'Courier New', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
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
  padding: 0;
  flex-shrink: 0;
}

.modal-close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-close-btn svg {
  width: 20px;
  height: 20px;
}

.editor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.code-editor {
  flex: 1;
  width: 100%;
  min-height: 400px;
  padding: 16px;
  border: none;
  border-radius: 0;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: var(--bg-primary);
  color: var(--text-primary);
  resize: none;
  outline: none;
  tab-size: 2;
}

.code-editor:focus {
  background: var(--bg-primary);
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  font-size: 0.85rem;
}

.file-info {
  color: var(--text-secondary);
}

.save-success {
  color: #10b981;
  font-weight: 500;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  gap: 16px;
}

.error-message {
  color: #ef4444;
  margin: 0;
}

.spinner {
  display: inline-block;
  width: 24px;
  height: 24px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
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
  font-size: 0.85rem;
  padding: 6px 12px;
}
</style>
