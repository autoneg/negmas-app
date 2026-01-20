<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Start New Negotiation</h2>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- Step 1: Scenario Selection -->
        <div v-if="step === 1" class="step">
          <h3>Select Scenario</h3>
          <div class="scenario-search">
            <input
              v-model="scenarioSearch"
              type="text"
              placeholder="Search scenarios..."
              class="input-text"
            />
          </div>
          <div class="scenario-list">
            <div
              v-for="scenario in filteredScenarios"
              :key="scenario.path"
              class="scenario-card"
              :class="{ selected: selectedScenario?.path === scenario.path }"
              @click="selectScenario(scenario)"
            >
              <div class="scenario-name">{{ scenario.name }}</div>
              <div class="scenario-meta">
                <span class="badge">{{ scenario.source }}</span>
                <span>{{ scenario.n_negotiators }} negotiators</span>
                <span>{{ formatNumber(scenario.n_outcomes) }} outcomes</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2: Negotiators Configuration -->
        <div v-if="step === 2" class="step">
          <h3>Configure Negotiators</h3>
          <p class="step-hint">
            Scenario requires {{ selectedScenario?.n_negotiators }} negotiators
          </p>

          <div
            v-for="(neg, idx) in negotiators"
            :key="idx"
            class="negotiator-config"
          >
            <h4>Negotiator {{ idx + 1 }}</h4>
            <div class="form-row">
              <label>Type</label>
              <select v-model="neg.type_name" class="input-select" @change="onNegotiatorTypeChange(idx)">
                <option value="">Select type...</option>
                <option v-for="type in negotiatorTypes" :key="type" :value="type">
                  {{ type }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>Name (optional)</label>
              <input v-model="neg.name" type="text" class="input-text" placeholder="Auto-generated if empty" />
            </div>
            <!-- Parameter configuration would go here -->
            <div v-if="neg.type_name && negotiatorParams[neg.type_name]" class="params-section">
              <h5>Parameters</h5>
              <div
                v-for="param in negotiatorParams[neg.type_name]"
                :key="param.name"
                class="param-row"
              >
                <label :title="param.help">{{ param.name }}</label>
                <input
                  v-if="param.type === 'float' || param.type === 'int'"
                  v-model.number="neg.params[param.name]"
                  type="number"
                  :step="param.type === 'float' ? 'any' : '1'"
                  class="input-text input-sm"
                  :placeholder="param.default !== null ? String(param.default) : ''"
                />
                <input
                  v-else-if="param.type === 'bool'"
                  v-model="neg.params[param.name]"
                  type="checkbox"
                  class="input-checkbox"
                />
                <input
                  v-else
                  v-model="neg.params[param.name]"
                  type="text"
                  class="input-text input-sm"
                  :placeholder="param.default !== null ? String(param.default) : ''"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Step 3: Mechanism Settings -->
        <div v-if="step === 3" class="step">
          <h3>Mechanism Settings</h3>
          
          <div class="form-row">
            <label>Mechanism Type</label>
            <select v-model="mechanismType" class="input-select">
              <option value="SAOMechanism">SAO Mechanism</option>
            </select>
          </div>

          <div class="form-row">
            <label>Number of Steps</label>
            <input v-model.number="mechanismParams.n_steps" type="number" class="input-text" />
          </div>

          <div class="form-row">
            <label>Time Limit (seconds, 0 = none)</label>
            <input v-model.number="mechanismParams.time_limit" type="number" step="0.1" class="input-text" />
          </div>

          <div class="form-row">
            <label>Step Delay (seconds)</label>
            <input v-model.number="stepDelay" type="number" step="0.01" min="0" class="input-text" />
          </div>

          <div class="form-row checkbox-row">
            <label>
              <input v-model="shareUfuns" type="checkbox" class="input-checkbox" />
              Share utility functions
            </label>
          </div>

          <div class="form-row checkbox-row">
            <label>
              <input v-model="normalize" type="checkbox" class="input-checkbox" />
              Normalize utilities
            </label>
          </div>

          <div class="form-row checkbox-row">
            <label>
              <input v-model="ignoreDiscount" type="checkbox" class="input-checkbox" />
              Ignore discount factors
            </label>
          </div>

          <div class="form-row checkbox-row">
            <label>
              <input v-model="ignoreReserved" type="checkbox" class="input-checkbox" />
              Ignore reserved values
            </label>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button v-if="step > 1" class="btn btn-secondary" @click="step--">
          Back
        </button>
        <button v-if="step < 3" class="btn btn-primary" @click="nextStep" :disabled="!canProceed">
          Next
        </button>
        <button v-if="step === 3" class="btn btn-primary" @click="startNegotiation" :disabled="starting">
          {{ starting ? 'Starting...' : 'Start Negotiation' }}
        </button>
        <button class="btn btn-secondary" @click="$emit('close')">
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  show: Boolean,
  preselectedScenario: Object,
})

const emit = defineEmits(['close', 'start'])

// Step management
const step = ref(1)
const starting = ref(false)

// Scenario selection
const scenarioSearch = ref('')
const scenarios = ref([])
const selectedScenario = ref(null)
const loadingScenarios = ref(false)

// Negotiators configuration
const negotiators = ref([])
const negotiatorTypes = ref([])
const negotiatorParams = ref({}) // Cache for negotiator params by type
const loadingNegotiators = ref(false)

// Mechanism settings
const mechanismType = ref('SAOMechanism')
const mechanismParams = ref({
  n_steps: 100,
  time_limit: 0,
})
const stepDelay = ref(0.1)
const shareUfuns = ref(false)
const normalize = ref(false)
const ignoreDiscount = ref(false)
const ignoreReserved = ref(false)

// Computed
const filteredScenarios = computed(() => {
  if (!scenarioSearch.value) return scenarios.value
  const search = scenarioSearch.value.toLowerCase()
  return scenarios.value.filter(s =>
    s.name.toLowerCase().includes(search) ||
    s.source.toLowerCase().includes(search) ||
    (s.tags && s.tags.some(t => t.toLowerCase().includes(search)))
  )
})

const canProceed = computed(() => {
  if (step.value === 1) return selectedScenario.value !== null
  if (step.value === 2) {
    return negotiators.value.length === selectedScenario.value?.n_negotiators &&
           negotiators.value.every(n => n.type_name)
  }
  return true
})

// Methods
async function loadScenarios() {
  loadingScenarios.value = true
  try {
    const response = await fetch('/api/scenarios')
    const data = await response.json()
    scenarios.value = data.scenarios || []
    
    // If preselected scenario, select it
    if (props.preselectedScenario) {
      const found = scenarios.value.find(s => s.path === props.preselectedScenario.path)
      if (found) {
        selectScenario(found)
      }
    }
  } catch (error) {
    console.error('Failed to load scenarios:', error)
  } finally {
    loadingScenarios.value = false
  }
}

async function loadNegotiatorTypes() {
  loadingNegotiators.value = true
  try {
    const response = await fetch('/api/negotiators')
    const data = await response.json()
    negotiatorTypes.value = data.negotiators || []
  } catch (error) {
    console.error('Failed to load negotiator types:', error)
  } finally {
    loadingNegotiators.value = false
  }
}

async function onNegotiatorTypeChange(idx) {
  const neg = negotiators.value[idx]
  if (!neg.type_name) return
  
  // Load params for this type if not cached
  if (!negotiatorParams.value[neg.type_name]) {
    try {
      const response = await fetch(`/api/negotiators/${neg.type_name}/inspect`)
      const data = await response.json()
      negotiatorParams.value[neg.type_name] = data.parameters || []
    } catch (error) {
      console.error('Failed to load negotiator params:', error)
      negotiatorParams.value[neg.type_name] = []
    }
  }
  
  // Initialize params object with defaults
  neg.params = {}
  for (const param of negotiatorParams.value[neg.type_name]) {
    if (param.default !== null) {
      neg.params[param.name] = param.default
    }
  }
}

function selectScenario(scenario) {
  selectedScenario.value = scenario
  
  // Initialize negotiators array
  negotiators.value = Array.from({ length: scenario.n_negotiators }, () => ({
    type_name: '',
    name: null,
    params: {},
  }))
}

function nextStep() {
  if (canProceed.value) {
    step.value++
  }
}

async function startNegotiation() {
  if (starting.value) return
  starting.value = true
  
  try {
    const request = {
      scenario_path: selectedScenario.value.path,
      negotiators: negotiators.value.map(n => ({
        type_name: n.type_name,
        name: n.name || null,
        params: n.params,
      })),
      mechanism_type: mechanismType.value,
      mechanism_params: {
        n_steps: mechanismParams.value.n_steps || null,
        time_limit: mechanismParams.value.time_limit || null,
      },
      step_delay: stepDelay.value,
      share_ufuns: shareUfuns.value,
      normalize: normalize.value,
      ignore_discount: ignoreDiscount.value,
      ignore_reserved: ignoreReserved.value,
      auto_save: true,
    }
    
    const response = await fetch('/api/negotiation/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
    
    const data = await response.json()
    emit('start', data)
    emit('close')
  } catch (error) {
    console.error('Failed to start negotiation:', error)
    alert('Failed to start negotiation: ' + error.message)
  } finally {
    starting.value = false
  }
}

function formatNumber(num) {
  if (num === null || num === undefined) return 'N/A'
  if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
  return num.toString()
}

// Watch for modal open/close
watch(() => props.show, (newShow) => {
  if (newShow) {
    step.value = 1
    selectedScenario.value = null
    negotiators.value = []
    loadScenarios()
    loadNegotiatorTypes()
  }
})
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
  z-index: 1000;
}

.modal {
  background: var(--bg-primary);
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
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
  font-size: 1.5rem;
}

.modal-close {
  background: none;
  border: none;
  font-size: 2rem;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.modal-close:hover {
  background: var(--bg-hover);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
}

.step {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.step h3 {
  margin: 0 0 16px 0;
  font-size: 1.25rem;
}

.step-hint {
  color: var(--text-secondary);
  margin: 0 0 20px 0;
  font-size: 0.9rem;
}

.scenario-search {
  margin-bottom: 16px;
}

.scenario-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.scenario-card {
  padding: 16px;
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.scenario-card:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.scenario-card.selected {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.scenario-name {
  font-weight: 600;
  margin-bottom: 8px;
}

.scenario-meta {
  display: flex;
  gap: 12px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  font-size: 0.75rem;
  font-weight: 500;
}

.negotiator-config {
  padding: 20px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 16px;
}

.negotiator-config h4 {
  margin: 0 0 16px 0;
  font-size: 1.1rem;
}

.params-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.params-section h5 {
  margin: 0 0 12px 0;
  font-size: 0.95rem;
  color: var(--text-secondary);
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.form-row label {
  font-weight: 500;
  font-size: 0.9rem;
}

.checkbox-row {
  flex-direction: row;
  align-items: center;
}

.checkbox-row label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.param-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.param-row label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.input-text,
.input-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.input-sm {
  padding: 6px 10px;
  font-size: 0.85rem;
}

.input-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.btn {
  padding: 10px 20px;
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

.btn-primary:hover:not(:disabled) {
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

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
