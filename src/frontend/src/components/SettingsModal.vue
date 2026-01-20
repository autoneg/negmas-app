<template>
  <div v-if="show" class="modal-overlay" @click="closeModal">
    <div class="modal-content settings-modal" @click.stop>
      <div class="modal-header">
        <h2>Settings</h2>
        <button class="btn-icon" @click="closeModal">×</button>
      </div>
      
      <div class="modal-body">
        <div class="settings-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="settings-tab"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>
        
        <div class="settings-content">
          <!-- General Tab -->
          <div v-if="activeTab === 'general'" class="settings-section">
            <h3>General Settings</h3>
            
            <div class="setting-item">
              <label class="setting-label">
                <input
                  v-model="localSettings.general.dark_mode"
                  type="checkbox"
                  class="setting-checkbox"
                />
                <span class="setting-title">Dark Mode</span>
              </label>
              <p class="setting-description">Use dark color scheme throughout the application</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <input
                  v-model="localSettings.general.color_blind_mode"
                  type="checkbox"
                  class="setting-checkbox"
                />
                <span class="setting-title">Color Blind Mode</span>
              </label>
              <p class="setting-description">Use color-blind friendly palette (Okabe-Ito)</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <input
                  v-model="localSettings.general.save_negotiations"
                  type="checkbox"
                  class="setting-checkbox"
                />
                <span class="setting-title">Save Negotiations</span>
              </label>
              <p class="setting-description">Automatically save negotiations to disk</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <input
                  v-model="localSettings.general.cache_scenario_stats"
                  type="checkbox"
                  class="setting-checkbox"
                />
                <span class="setting-title">Cache Scenario Statistics</span>
              </label>
              <p class="setting-description">Automatically cache computed scenario statistics</p>
            </div>
          </div>
          
          <!-- Negotiation Tab -->
          <div v-if="activeTab === 'negotiation'" class="settings-section">
            <h3>Negotiation Defaults</h3>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Default Max Steps</span>
              </label>
              <input
                v-model.number="localSettings.negotiation.default_max_steps"
                type="number"
                min="1"
                class="setting-input"
              />
              <p class="setting-description">Default maximum number of negotiation steps</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Default Step Delay (ms)</span>
              </label>
              <input
                v-model.number="localSettings.negotiation.default_step_delay_ms"
                type="number"
                min="0"
                step="50"
                class="setting-input"
              />
              <p class="setting-description">Delay between steps when streaming negotiations (milliseconds)</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Default Time Limit (seconds)</span>
              </label>
              <input
                v-model.number="localSettings.negotiation.default_time_limit"
                type="number"
                min="0"
                class="setting-input"
                placeholder="No limit"
              />
              <p class="setting-description">Default time limit for negotiations (leave empty for no limit)</p>
            </div>
          </div>
          
          <!-- Genius Bridge Tab -->
          <div v-if="activeTab === 'genius'" class="settings-section">
            <h3>Genius Bridge</h3>
            
            <div class="setting-item">
              <label class="setting-label">
                <input
                  v-model="localSettings.genius_bridge.auto_start"
                  type="checkbox"
                  class="setting-checkbox"
                />
                <span class="setting-title">Auto-start Genius Bridge</span>
              </label>
              <p class="setting-description">Automatically start Genius bridge when needed</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Java Path</span>
              </label>
              <input
                v-model="localSettings.genius_bridge.java_path"
                type="text"
                class="setting-input"
                placeholder="Auto-detect"
              />
              <p class="setting-description">Path to Java executable (leave empty to auto-detect)</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Bridge Port</span>
              </label>
              <input
                v-model.number="localSettings.genius_bridge.port"
                type="number"
                min="1024"
                max="65535"
                class="setting-input"
              />
              <p class="setting-description">Port for Genius bridge communication</p>
            </div>
          </div>
          
          <!-- Performance Tab -->
          <div v-if="activeTab === 'performance'" class="settings-section">
            <h3>Performance Limits</h3>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Max Outcomes for Running</span>
              </label>
              <input
                v-model.number="localSettings.performance.max_outcomes_run"
                type="number"
                min="0"
                class="setting-input"
                placeholder="No limit"
              />
              <p class="setting-description">
                Maximum outcomes for running negotiations/tournaments (0 or empty = no limit)
              </p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Max Outcomes for Statistics</span>
              </label>
              <input
                v-model.number="localSettings.performance.max_outcomes_stats"
                type="number"
                min="0"
                class="setting-input"
                placeholder="1000000"
              />
              <p class="setting-description">
                Maximum outcomes for calculating scenario statistics (Pareto, Nash, etc.)
              </p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Max Outcomes for Info</span>
              </label>
              <input
                v-model.number="localSettings.performance.max_outcomes_info"
                type="number"
                min="0"
                class="setting-input"
                placeholder="10000000"
              />
              <p class="setting-description">
                Maximum outcomes for calculating any scenario info
              </p>
            </div>
          </div>
          
          <!-- Paths Tab -->
          <div v-if="activeTab === 'paths'" class="settings-section">
            <h3>Custom Paths</h3>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">User Scenarios Directory</span>
              </label>
              <input
                v-model="localSettings.paths.user_scenarios"
                type="text"
                class="setting-input"
                placeholder="~/negmas/app/scenarios"
              />
              <p class="setting-description">Directory for user-created scenarios</p>
            </div>
            
            <div class="setting-item">
              <label class="setting-label">
                <span class="setting-title">Additional Scenario Paths</span>
              </label>
              <div class="path-list">
                <div
                  v-for="(path, idx) in localSettings.paths.scenario_paths"
                  :key="idx"
                  class="path-item"
                >
                  <input
                    v-model="localSettings.paths.scenario_paths[idx]"
                    type="text"
                    class="setting-input"
                    placeholder="/path/to/scenarios"
                  />
                  <button
                    class="btn-icon-sm"
                    @click="removePath(idx)"
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              </div>
              <button class="btn-secondary btn-sm" @click="addPath">
                + Add Path
              </button>
              <p class="setting-description">Additional directories to search for scenarios</p>
            </div>
          </div>
          
          <!-- Import/Export Tab -->
          <div v-if="activeTab === 'import-export'" class="settings-section">
            <h3>Import/Export Settings</h3>
            
            <div class="setting-item">
              <button
                class="btn-primary"
                @click="handleExport"
                :disabled="exporting"
              >
                <span v-if="exporting">Exporting...</span>
                <span v-else>Export Settings</span>
              </button>
              <p class="setting-description">Download all settings as a ZIP file</p>
            </div>
            
            <div class="setting-item">
              <label class="btn-secondary">
                <input
                  ref="importInput"
                  type="file"
                  accept=".zip"
                  style="display: none"
                  @change="handleImport"
                />
                <span v-if="importing">Importing...</span>
                <span v-else>Import Settings</span>
              </label>
              <p class="setting-description">Upload a settings ZIP file to import</p>
              <p v-if="importStatus" class="import-status" :class="importStatusClass">
                {{ importStatus }}
              </p>
            </div>
            
            <div class="setting-item">
              <button
                class="btn-secondary"
                @click="handleReset"
              >
                Reset to Defaults
              </button>
              <p class="setting-description">Reset all settings to default values</p>
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn-secondary" @click="closeModal">
          Cancel
        </button>
        <button
          class="btn-primary"
          @click="saveAndClose"
          :disabled="saving"
        >
          <span v-if="saving">Saving...</span>
          <span v-else>Save</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useSettingsStore } from '../stores/settings'
import { storeToRefs } from 'pinia'

const props = defineProps({
  show: Boolean,
})

const emit = defineEmits(['close'])

const settingsStore = useSettingsStore()
const { settings, saving } = storeToRefs(settingsStore)

const activeTab = ref('general')
const localSettings = ref(null)
const exporting = ref(false)
const importing = ref(false)
const importStatus = ref('')
const importStatusClass = ref('')
const importInput = ref(null)

const tabs = [
  { id: 'general', label: 'General' },
  { id: 'negotiation', label: 'Negotiation' },
  { id: 'genius', label: 'Genius Bridge' },
  { id: 'performance', label: 'Performance' },
  { id: 'paths', label: 'Paths' },
  { id: 'import-export', label: 'Import/Export' },
]

// Watch for modal open to load fresh settings
watch(() => props.show, (newVal) => {
  if (newVal) {
    loadLocalSettings()
    activeTab.value = 'general'
    importStatus.value = ''
  }
})

onMounted(() => {
  if (props.show) {
    loadLocalSettings()
  }
})

function loadLocalSettings() {
  // Deep copy settings to local state
  localSettings.value = JSON.parse(JSON.stringify(settings.value))
  
  // Ensure arrays exist
  if (!localSettings.value.paths.scenario_paths) {
    localSettings.value.paths.scenario_paths = []
  }
}

function closeModal() {
  emit('close')
}

async function saveAndClose() {
  // Update store settings
  settings.value = JSON.parse(JSON.stringify(localSettings.value))
  
  const result = await settingsStore.saveSettings()
  
  if (result.success) {
    closeModal()
  } else {
    alert('Failed to save settings. Please try again.')
  }
}

function addPath() {
  localSettings.value.paths.scenario_paths.push('')
}

function removePath(index) {
  localSettings.value.paths.scenario_paths.splice(index, 1)
}

async function handleExport() {
  exporting.value = true
  const result = await settingsStore.exportSettings()
  exporting.value = false
  
  if (!result.success) {
    alert('Failed to export settings')
  }
}

async function handleImport(event) {
  const file = event.target.files?.[0]
  if (!file) return
  
  importing.value = true
  importStatus.value = ''
  
  const result = await settingsStore.importSettings(file)
  
  importing.value = false
  
  if (result.success) {
    importStatus.value = result.message
    importStatusClass.value = 'success'
    
    // Reload local settings
    loadLocalSettings()
    
    if (result.partial) {
      importStatus.value += ' (with some errors)'
      importStatusClass.value = 'warning'
    }
  } else {
    importStatus.value = 'Import failed: ' + (result.error || 'Unknown error')
    importStatusClass.value = 'error'
  }
  
  // Clear file input
  if (importInput.value) {
    importInput.value.value = ''
  }
}

function handleReset() {
  if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
    settingsStore.resetToDefaults()
    loadLocalSettings()
  }
}
</script>

<style scoped>
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
  z-index: 2000;
}

.modal-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.settings-modal {
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.4rem;
}

.modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.settings-tabs {
  display: flex;
  gap: 4px;
  padding: 16px 24px 0 24px;
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
}

.settings-tab {
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
  transition: all 0.2s;
}

.settings-tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.settings-tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.settings-section h3 {
  margin: 0 0 20px 0;
  font-size: 1.1rem;
  color: var(--text-primary);
}

.setting-item {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  margin-bottom: 8px;
}

.setting-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.setting-title {
  font-weight: 500;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.setting-description {
  margin: 8px 0 0 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.setting-input {
  width: 100%;
  max-width: 400px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.9rem;
  margin-top: 8px;
}

.setting-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.path-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0;
}

.path-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.path-item .setting-input {
  margin-top: 0;
  flex: 1;
}

.import-status {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
}

.import-status.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.import-status.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.import-status.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
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
  opacity: 0.6;
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
  font-size: 1.8rem;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.btn-icon:hover {
  color: var(--text-primary);
}

.btn-icon-sm {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.4rem;
  padding: 4px;
  line-height: 1;
  transition: color 0.2s;
}

.btn-icon-sm:hover {
  color: #ef4444;
}
</style>
