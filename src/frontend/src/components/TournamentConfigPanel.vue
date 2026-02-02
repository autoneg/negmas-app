<template>
  <div class="tournament-config-panel">
    <div class="panel-header">
      <h3 class="panel-title">Tournament Configuration</h3>
    </div>
    
    <div class="panel-body">
      <div v-if="!config" class="empty-state-sm">
        <p class="text-muted">No configuration available</p>
      </div>
      
      <div v-else class="config-sections">
        <!-- Basic Information -->
        <div class="config-section">
          <h4 class="config-section-title">Basic Information</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Name:</span>
              <span class="config-value">{{ config.name || 'Untitled Tournament' }}</span>
            </div>
            <div v-if="config.description" class="config-item">
              <span class="config-label">Description:</span>
              <span class="config-value">{{ config.description }}</span>
            </div>
            <div v-if="config.storage_path" class="config-item">
              <span class="config-label">Storage:</span>
              <div class="storage-path-container">
                <span class="config-value storage-path">{{ config.storage_path }}</span>
                <button 
                  class="btn-icon-sm" 
                  @click="openStorageFolder"
                  title="Open folder in file explorer"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Competitors -->
        <div class="config-section">
          <h4 class="config-section-title">Competitors ({{ config.competitors?.length || 0 }})</h4>
          <div class="config-items">
            <div class="competitor-list">
              <span 
                v-for="(competitor, idx) in config.competitors" 
                :key="idx"
                class="badge badge-sm clickable-badge"
                @click="handleNegotiatorClick(competitor.type_name || competitor.name)"
                title="Click for negotiator info"
              >
                {{ competitor.name || competitor.type_name }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- Scenarios -->
        <div class="config-section">
          <h4 class="config-section-title">Scenarios ({{ config.scenarios?.length || 0 }})</h4>
          <div class="config-items">
            <div class="scenario-list">
              <span 
                v-for="(scenario, idx) in config.scenarios" 
                :key="idx"
                class="badge badge-neutral badge-sm clickable-badge"
                @click="handleScenarioClick(scenario.path || scenario)"
                title="Click for scenario stats"
              >
                {{ scenario.name || scenario.path?.split('/').pop() }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- Tournament Settings -->
        <div class="config-section">
          <h4 class="config-section-title">Tournament Settings</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Self-play:</span>
              <span class="config-value">{{ config.self_play ? 'Enabled' : 'Disabled' }}</span>
            </div>
            <div class="config-item">
              <span class="config-label">Randomize:</span>
              <span class="config-value">{{ config.randomize ? 'Yes' : 'No' }}</span>
            </div>
            <div v-if="config.n_repetitions && config.n_repetitions > 1" class="config-item">
              <span class="config-label">Repetitions:</span>
              <span class="config-value">{{ config.n_repetitions }}</span>
            </div>
            <div v-if="config.rotate_ufuns" class="config-item">
              <span class="config-label">Rotate utilities:</span>
              <span class="config-value">{{ config.rotate_ufuns ? 'Yes' : 'No' }}</span>
            </div>
          </div>
        </div>
        
        <!-- Mechanism Settings -->
        <div class="config-section">
          <h4 class="config-section-title">Mechanism</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Type:</span>
              <span class="config-value">{{ config.mechanism_type || 'SAOMechanism' }}</span>
            </div>
            <div v-if="config.mechanism_params?.n_steps" class="config-item">
              <span class="config-label">Steps limit:</span>
              <span class="config-value">{{ config.mechanism_params.n_steps }}</span>
            </div>
            <div v-if="config.mechanism_params?.time_limit" class="config-item">
              <span class="config-label">Time limit:</span>
              <span class="config-value">{{ config.mechanism_params.time_limit }}s</span>
            </div>
            <div v-if="config.mechanism_params?.pend" class="config-item">
              <span class="config-label">Pend:</span>
              <span class="config-value">{{ config.mechanism_params.pend }}</span>
            </div>
          </div>
        </div>
        
        <!-- Scoring -->
        <div class="config-section">
          <h4 class="config-section-title">Scoring</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Metric:</span>
              <span class="config-value">{{ formatMetric(config.final_score?.metric) }}</span>
            </div>
            <div class="config-item">
              <span class="config-label">Statistic:</span>
              <span class="config-value">{{ formatStatistic(config.final_score?.statistic) }}</span>
            </div>
          </div>
        </div>
        
        <!-- Scenario Options -->
        <div v-if="hasScenarioOptions(config)" class="config-section">
          <h4 class="config-section-title">Scenario Options</h4>
          <div class="config-items">
            <div v-if="config.ignore_discount" class="config-item">
              <span class="config-label">Ignore discount:</span>
              <span class="config-value">Yes</span>
            </div>
            <div v-if="config.ignore_reserved" class="config-item">
              <span class="config-label">Ignore reserved:</span>
              <span class="config-value">Yes</span>
            </div>
            <div v-if="config.normalize" class="config-item">
              <span class="config-label">Normalize:</span>
              <span class="config-value">Yes</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Negotiator Info Modal -->
    <NegotiatorInfoModal
      :show="showNegotiatorModal"
      :typeName="selectedNegotiatorType"
      @close="showNegotiatorModal = false"
    />
    
    <!-- Scenario Stats Modal (for tournament scenarios) -->
    <StatsModal
      :show="showScenarioStatsModal"
      :tournamentId="tournamentId"
      :scenarioName="selectedScenarioName"
      @close="showScenarioStatsModal = false"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import NegotiatorInfoModal from './NegotiatorInfoModal.vue'
import StatsModal from './StatsModal.vue'

const props = defineProps({
  config: {
    type: Object,
    default: null
  },
  tournamentId: {
    type: String,
    default: null
  }
})

// Modal state for negotiator info
const showNegotiatorModal = ref(false)
const selectedNegotiatorType = ref('')

// Modal state for scenario stats
const showScenarioStatsModal = ref(false)
const selectedScenarioName = ref('')

// Click handlers
function handleNegotiatorClick(negotiatorName) {
  // Try to get the full type name from the type maps
  // competitor_type_map and opponent_type_map map short names to full type names
  let fullTypeName = negotiatorName
  
  if (props.config?.competitor_type_map && props.config.competitor_type_map[negotiatorName]) {
    fullTypeName = props.config.competitor_type_map[negotiatorName]
  } else if (props.config?.opponent_type_map && props.config.opponent_type_map[negotiatorName]) {
    fullTypeName = props.config.opponent_type_map[negotiatorName]
  }
  
  selectedNegotiatorType.value = fullTypeName
  showNegotiatorModal.value = true
}

function handleScenarioClick(scenarioPath) {
  // Extract just the scenario folder name from the path
  const scenarioName = scenarioPath?.split('/').pop() || scenarioPath
  selectedScenarioName.value = scenarioName
  showScenarioStatsModal.value = true
}

async function openStorageFolder() {
  if (!props.config?.storage_path) return
  
  try {
    const response = await fetch('/api/system/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: props.config.storage_path })
    })
    
    if (!response.ok) {
      console.error('Failed to open folder:', await response.text())
    }
  } catch (error) {
    console.error('Error opening folder:', error)
  }
}

function formatMetric(metric) {
  if (!metric) return 'Advantage'
  const mapping = {
    'advantage': 'Advantage',
    'utility': 'Utility',
    'welfare': 'Welfare',
    'nash_optimality': 'Nash Optimality',
    'kalai_optimality': 'Kalai Optimality',
    'pareto_optimality': 'Pareto Optimality'
  }
  return mapping[metric] || metric
}

function formatStatistic(stat) {
  if (!stat) return 'Mean'
  const mapping = {
    'mean': 'Mean',
    'median': 'Median',
    'sum': 'Sum',
    'min': 'Minimum',
    'max': 'Maximum'
  }
  return mapping[stat] || stat
}

function hasScenarioOptions(config) {
  return config && (config.ignore_discount || config.ignore_reserved || config.normalize)
}
</script>

<style scoped>
.tournament-config-panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 120px;
}

.config-sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-color);
}

.config-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.config-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
}

.config-label {
  color: var(--text-muted);
  min-width: 120px;
  flex-shrink: 0;
}

.config-value {
  color: var(--text-primary);
  font-weight: 500;
}

.storage-path-container {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.storage-path {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  font-size: 12px;
  word-break: break-all;
  flex: 1;
}

.competitor-list,
.scenario-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.badge-sm {
  padding: 3px 6px;
  font-size: 10px;
}

.badge-neutral {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

/* Clickable badges for competitor/scenario selection */
.clickable-badge {
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, transform 0.15s;
}

.clickable-badge:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
  transform: translateY(-1px);
}
</style>
