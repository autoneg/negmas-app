<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal large">
      <div class="modal-header">
        <h2>Start New Tournament</h2>
        <button class="modal-close" @click="$emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- Step 1: Competitors Selection -->
        <div v-if="step === 1" class="step">
          <h3>Select Competitors</h3>
          <p class="step-hint">Choose negotiator types that will compete</p>
          
          <div class="type-selector">
            <div class="type-search">
              <input
                v-model="competitorSearch"
                type="text"
                placeholder="Search negotiator types..."
                class="input-text"
              />
            </div>
            <div class="type-list">
              <label
                v-for="type in filteredCompetitorTypes"
                :key="type"
                class="type-checkbox"
              >
                <input
                  v-model="selectedCompetitors"
                  type="checkbox"
                  :value="type"
                  class="input-checkbox"
                />
                <span>{{ type }}</span>
              </label>
            </div>
          </div>
          
          <div v-if="selectedCompetitors.length > 0" class="selected-summary">
            <strong>Selected:</strong> {{ selectedCompetitors.length }} competitors
          </div>
        </div>

        <!-- Step 2: Scenarios Selection -->
        <div v-if="step === 2" class="step">
          <h3>Select Scenarios</h3>
          <p class="step-hint">Choose one or more scenarios for the tournament</p>
          
          <div class="scenario-search">
            <input
              v-model="scenarioSearch"
              type="text"
              placeholder="Search scenarios..."
              class="input-text"
            />
          </div>
          
          <div class="scenario-list">
            <label
              v-for="scenario in filteredScenarios"
              :key="scenario.path"
              class="scenario-checkbox"
            >
              <input
                v-model="selectedScenarioPaths"
                type="checkbox"
                :value="scenario.path"
                class="input-checkbox"
              />
              <div class="scenario-info">
                <div class="scenario-name">{{ scenario.name }}</div>
                <div class="scenario-meta">
                  <span class="badge">{{ scenario.source }}</span>
                  <span>{{ scenario.n_negotiators }} negotiators</span>
                  <span>{{ formatNumber(scenario.n_outcomes) }} outcomes</span>
                </div>
              </div>
            </label>
          </div>
          
          <div v-if="selectedScenarioPaths.length > 0" class="selected-summary">
            <strong>Selected:</strong> {{ selectedScenarioPaths.length }} scenarios
          </div>
        </div>

        <!-- Step 3: Tournament Settings -->
        <div v-if="step === 3" class="step">
          <h3>Tournament Settings</h3>
          
          <div class="settings-grid">
            <div class="form-group">
              <label>Mechanism Type</label>
              <select v-model="mechanismType" class="input-select">
                <option value="SAOMechanism">SAO Mechanism</option>
              </select>
            </div>

            <div class="form-group">
              <label>Repetitions</label>
              <input v-model.number="nRepetitions" type="number" min="1" class="input-text" />
            </div>

            <div class="form-group">
              <label>Number of Steps</label>
              <input v-model.number="nSteps" type="number" min="1" class="input-text" />
            </div>

            <div class="form-group">
              <label>Time Limit (seconds, 0 = none)</label>
              <input v-model.number="timeLimit" type="number" min="0" step="0.1" class="input-text" />
            </div>

            <div class="form-group">
              <label>Score Metric</label>
              <select v-model="finalScoreMetric" class="input-select">
                <option value="advantage">Advantage</option>
                <option value="utility">Utility</option>
                <option value="welfare">Welfare</option>
              </select>
            </div>

            <div class="form-group">
              <label>Score Statistic</label>
              <select v-model="finalScoreStat" class="input-select">
                <option value="mean">Mean</option>
                <option value="median">Median</option>
                <option value="min">Min</option>
                <option value="max">Max</option>
              </select>
            </div>

            <div class="form-group">
              <label>Parallel Jobs (-1 = all cores)</label>
              <input v-model.number="njobs" type="number" class="input-text" />
            </div>

            <div class="form-group">
              <label>Normalization</label>
              <select v-model="normalization" class="input-select">
                <option value="normalize">Normalize</option>
                <option value="none">None</option>
                <option value="scale_min">Scale Min</option>
                <option value="scale_max">Scale Max</option>
              </select>
            </div>
          </div>

          <div class="checkbox-group">
            <label class="checkbox-label">
              <input v-model="rotateUfuns" type="checkbox" class="input-checkbox" />
              <span>Rotate utility functions</span>
            </label>
            <label class="checkbox-label">
              <input v-model="selfPlay" type="checkbox" class="input-checkbox" />
              <span>Allow self-play</span>
            </label>
            <label class="checkbox-label">
              <input v-model="ignoreDiscount" type="checkbox" class="input-checkbox" />
              <span>Ignore discount factors</span>
            </label>
            <label class="checkbox-label">
              <input v-model="ignoreReserved" type="checkbox" class="input-checkbox" />
              <span>Ignore reserved values</span>
            </label>
            <label class="checkbox-label">
              <input v-model="saveStats" type="checkbox" class="input-checkbox" />
              <span>Save statistics</span>
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
        <button v-if="step === 3" class="btn btn-primary" @click="startTournament" :disabled="starting">
          {{ starting ? 'Starting...' : 'Start Tournament' }}
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
})

const emit = defineEmits(['close', 'start'])

// Step management
const step = ref(1)
const starting = ref(false)

// Competitors
const competitorSearch = ref('')
const negotiatorTypes = ref([])
const selectedCompetitors = ref([])
const loadingTypes = ref(false)

// Scenarios
const scenarioSearch = ref('')
const scenarios = ref([])
const selectedScenarioPaths = ref([])
const loadingScenarios = ref(false)

// Tournament settings
const mechanismType = ref('SAOMechanism')
const nRepetitions = ref(1)
const nSteps = ref(100)
const timeLimit = ref(0)
const finalScoreMetric = ref('advantage')
const finalScoreStat = ref('mean')
const njobs = ref(-1)
const normalization = ref('normalize')
const rotateUfuns = ref(true)
const selfPlay = ref(true)
const ignoreDiscount = ref(false)
const ignoreReserved = ref(false)
const saveStats = ref(true)

// Computed
const filteredCompetitorTypes = computed(() => {
  if (!competitorSearch.value) return negotiatorTypes.value
  const search = competitorSearch.value.toLowerCase()
  return negotiatorTypes.value.filter(t => t.toLowerCase().includes(search))
})

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
  if (step.value === 1) return selectedCompetitors.value.length >= 2
  if (step.value === 2) return selectedScenarioPaths.value.length >= 1
  return true
})

// Methods
async function loadNegotiatorTypes() {
  loadingTypes.value = true
  try {
    const response = await fetch('/api/negotiators')
    const data = await response.json()
    negotiatorTypes.value = data.negotiators || []
  } catch (error) {
    console.error('Failed to load negotiator types:', error)
  } finally {
    loadingTypes.value = false
  }
}

async function loadScenarios() {
  loadingScenarios.value = true
  try {
    const response = await fetch('/api/scenarios')
    const data = await response.json()
    scenarios.value = data.scenarios || []
  } catch (error) {
    console.error('Failed to load scenarios:', error)
  } finally {
    loadingScenarios.value = false
  }
}

function nextStep() {
  if (canProceed.value) {
    step.value++
  }
}

async function startTournament() {
  if (starting.value) return
  starting.value = true
  
  try {
    const request = {
      competitor_types: selectedCompetitors.value,
      scenario_paths: selectedScenarioPaths.value,
      opponent_types: null, // null means competitors play each other
      competitor_params: null,
      opponent_params: null,
      n_repetitions: nRepetitions.value,
      rotate_ufuns: rotateUfuns.value,
      self_play: selfPlay.value,
      mechanism_type: mechanismType.value,
      n_steps: nSteps.value > 0 ? nSteps.value : null,
      time_limit: timeLimit.value > 0 ? timeLimit.value : null,
      final_score_metric: finalScoreMetric.value,
      final_score_stat: finalScoreStat.value,
      normalization: normalization.value,
      ignore_discount: ignoreDiscount.value,
      ignore_reserved: ignoreReserved.value,
      save_stats: saveStats.value,
      njobs: njobs.value,
    }
    
    const response = await fetch('/api/tournament/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
    
    const data = await response.json()
    emit('start', data)
    emit('close')
  } catch (error) {
    console.error('Failed to start tournament:', error)
    alert('Failed to start tournament: ' + error.message)
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
    selectedCompetitors.value = []
    selectedScenarioPaths.value = []
    loadNegotiatorTypes()
    loadScenarios()
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
  max-width: 900px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal.large {
  max-width: 1000px;
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
  margin: 0 0 8px 0;
  font-size: 1.25rem;
}

.step-hint {
  color: var(--text-secondary);
  margin: 0 0 20px 0;
  font-size: 0.9rem;
}

.type-selector {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.type-search {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.type-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px;
}

.type-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.type-checkbox:hover {
  background: var(--bg-hover);
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
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px;
}

.scenario-checkbox {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.scenario-checkbox:hover {
  background: var(--bg-hover);
}

.scenario-info {
  flex: 1;
}

.scenario-name {
  font-weight: 600;
  margin-bottom: 4px;
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

.selected-summary {
  margin-top: 16px;
  padding: 12px;
  background: var(--primary-bg);
  border: 1px solid var(--primary-color);
  border-radius: 6px;
  color: var(--text-primary);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: 500;
  font-size: 0.9rem;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 0.9rem;
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
