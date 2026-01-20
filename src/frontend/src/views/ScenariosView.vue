<template>
  <div class="scenarios-view">
    <!-- Scenarios List Panel -->
    <div class="scenarios-list-panel">
      <!-- Filters -->
      <div class="filter-section">
        <div class="filter-header">
          <h3>Scenarios</h3>
          <button class="btn-icon" @click="loadData" :disabled="loading" title="Refresh">
            <span v-if="loading">⟳</span>
            <span v-else>↻</span>
          </button>
        </div>
        
        <!-- Search -->
        <input
          v-model="localSearch"
          type="text"
          placeholder="Search scenarios..."
          class="input-search"
          @input="updateSearch"
        />
        
        <!-- Source Filter -->
        <div class="filter-group">
          <label>Source</label>
          <select v-model="localSource" @change="updateSourceFilter" class="input-select">
            <option value="">All Sources</option>
            <option v-for="source in sources" :key="source" :value="source">{{ source }}</option>
          </select>
        </div>
        
        <!-- Outcomes Range -->
        <div class="filter-group">
          <label>Outcomes</label>
          <div class="range-inputs">
            <input
              v-model.number="localFilters.minOutcomes"
              type="number"
              placeholder="Min"
              class="input-range"
              @input="updateFilters"
            />
            <span>-</span>
            <input
              v-model.number="localFilters.maxOutcomes"
              type="number"
              placeholder="Max"
              class="input-range"
              @input="updateFilters"
            />
          </div>
        </div>
        
        <!-- Opposition Range -->
        <div class="filter-group">
          <label>Opposition</label>
          <div class="range-inputs">
            <input
              v-model.number="localFilters.minOpposition"
              type="number"
              step="0.1"
              placeholder="Min"
              class="input-range"
              @input="updateFilters"
            />
            <span>-</span>
            <input
              v-model.number="localFilters.maxOpposition"
              type="number"
              step="0.1"
              placeholder="Max"
              class="input-range"
              @input="updateFilters"
            />
          </div>
        </div>
        
        <!-- Rational Fraction Range -->
        <div class="filter-group">
          <label>Rational Fraction</label>
          <div class="range-inputs">
            <input
              v-model.number="localFilters.minRationalFraction"
              type="number"
              step="0.1"
              placeholder="Min"
              class="input-range"
              @input="updateFilters"
            />
            <span>-</span>
            <input
              v-model.number="localFilters.maxRationalFraction"
              type="number"
              step="0.1"
              placeholder="Max"
              class="input-range"
              @input="updateFilters"
            />
          </div>
        </div>
        
        <button class="btn-secondary btn-sm" @click="clearFilters">Clear Filters</button>
      </div>
      
      <!-- Scenarios List -->
      <div class="scenarios-list">
        <div v-if="loading" class="loading-state">
          <span class="spinner"></span> Loading scenarios...
        </div>
        
        <div v-else-if="filteredScenarios.length === 0" class="empty-state">
          No scenarios found
        </div>
        
        <div
          v-else
          v-for="scenario in filteredScenarios"
          :key="scenario.path"
          class="scenario-item"
          :class="{ active: selectedScenario?.path === scenario.path }"
          @click="selectScenario(scenario)"
        >
          <div class="scenario-name">{{ scenario.name }}</div>
          <div class="scenario-meta">
            <span class="badge">{{ scenario.source }}</span>
            <span v-if="scenario.n_outcomes">{{ formatNumber(scenario.n_outcomes) }} outcomes</span>
          </div>
          <div class="scenario-stats" v-if="scenario.rational_fraction !== null || scenario.opposition !== null">
            <span v-if="scenario.rational_fraction !== null" title="Rational Fraction">
              R: {{ scenario.rational_fraction.toFixed(2) }}
            </span>
            <span v-if="scenario.opposition !== null" title="Opposition">
              O: {{ scenario.opposition.toFixed(2) }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Scenario Details Panel -->
    <div class="scenario-details-panel">
      <div v-if="!selectedScenario" class="empty-state">
        <p>Select a scenario to view details</p>
      </div>
      
      <div v-else class="scenario-details">
        <!-- Header -->
        <div class="details-header">
          <h2>{{ selectedScenario.name }}</h2>
          <div class="header-actions">
            <button class="btn-primary btn-sm" @click="openNewNegotiation">
              Start Negotiation
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
            :class="{ active: activeTab === 'stats' }"
            @click="activeTab = 'stats'; loadStats()"
          >
            Stats
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'plot' }"
            @click="activeTab = 'plot'; loadPlotData()"
          >
            Visualization
          </button>
        </div>
        
        <!-- Info Tab -->
        <div v-if="activeTab === 'info'" class="tab-content">
          <div class="info-grid">
            <div class="info-item">
              <label>Source</label>
              <span>{{ selectedScenario.source }}</span>
            </div>
            <div class="info-item">
              <label>Negotiators</label>
              <span>{{ selectedScenario.n_negotiators }}</span>
            </div>
            <div class="info-item">
              <label>Issues</label>
              <span>{{ selectedScenario.n_issues }}</span>
            </div>
            <div class="info-item">
              <label>Outcomes</label>
              <span>{{ formatNumber(selectedScenario.n_outcomes) }}</span>
            </div>
            <div class="info-item" v-if="selectedScenario.rational_fraction !== null">
              <label>Rational Fraction</label>
              <span>{{ selectedScenario.rational_fraction.toFixed(3) }}</span>
            </div>
            <div class="info-item" v-if="selectedScenario.opposition !== null">
              <label>Opposition</label>
              <span>{{ selectedScenario.opposition.toFixed(3) }}</span>
            </div>
          </div>
          
          <!-- Issues -->
          <div v-if="selectedScenario.issues && selectedScenario.issues.length > 0" class="issues-section">
            <h3>Issues</h3>
            <div class="issues-list">
              <div v-for="(issue, idx) in selectedScenario.issues" :key="idx" class="issue-item">
                <div class="issue-name">{{ issue.name }}</div>
                <div class="issue-type">{{ issue.type }}</div>
                <div class="issue-values" v-if="issue.values && issue.values.length > 0">
                  {{ issue.values.length }} values
                </div>
              </div>
            </div>
          </div>
          
          <!-- Tags -->
          <div v-if="selectedScenario.tags && selectedScenario.tags.length > 0" class="tags-section">
            <h3>Tags</h3>
            <div class="tags">
              <span v-for="tag in selectedScenario.tags" :key="tag" class="badge">{{ tag }}</span>
            </div>
          </div>
        </div>
        
        <!-- Stats Tab -->
        <div v-if="activeTab === 'stats'" class="tab-content">
          <div v-if="loadingStats" class="loading-state">
            <span class="spinner"></span> Loading stats...
          </div>
          
          <div v-else-if="!selectedScenarioStats" class="empty-state">
            <p>No stats available</p>
            <button class="btn-primary btn-sm" @click="calculateStats">Calculate Stats</button>
          </div>
          
          <div v-else class="stats-grid">
            <div class="stat-item" v-if="selectedScenarioStats.pareto_n_outcomes">
              <label>Pareto Outcomes</label>
              <span>{{ formatNumber(selectedScenarioStats.pareto_n_outcomes) }}</span>
            </div>
            <div class="stat-item" v-if="selectedScenarioStats.pareto_volume !== null">
              <label>Pareto Volume</label>
              <span>{{ selectedScenarioStats.pareto_volume.toFixed(3) }}</span>
            </div>
            <div class="stat-item" v-if="selectedScenarioStats.nash_optimality !== null">
              <label>Nash Optimality</label>
              <span>{{ selectedScenarioStats.nash_optimality.toFixed(3) }}</span>
            </div>
            <div class="stat-item" v-if="selectedScenarioStats.kalai_optimality !== null">
              <label>Kalai Optimality</label>
              <span>{{ selectedScenarioStats.kalai_optimality.toFixed(3) }}</span>
            </div>
          </div>
        </div>
        
        <!-- Plot Tab -->
        <div v-if="activeTab === 'plot'" class="tab-content">
          <div v-if="loadingPlotData" class="loading-state">
            <span class="spinner"></span> Loading plot data...
          </div>
          
          <div v-else-if="!selectedScenarioPlotData" class="empty-state">
            <p>No plot data available</p>
          </div>
          
          <div v-else class="plot-container">
            <div ref="plotDiv" class="plot"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useScenariosStore } from '../stores/scenarios'
import { storeToRefs } from 'pinia'
import Plotly from 'plotly.js-dist-min'

const scenariosStore = useScenariosStore()
const {
  scenarios,
  sources,
  selectedScenario,
  selectedScenarioStats,
  selectedScenarioPlotData,
  loading,
  loadingStats,
  loadingPlotData,
  filter,
  filteredScenarios,
} = storeToRefs(scenariosStore)

// Local state for inputs (to avoid direct mutation of store)
const localSearch = ref('')
const localSource = ref('')
const localFilters = ref({
  minOutcomes: null,
  maxOutcomes: null,
  minOpposition: null,
  maxOpposition: null,
  minRationalFraction: null,
  maxRationalFraction: null,
})

const activeTab = ref('info')
const plotDiv = ref(null)

// Load data on mount
onMounted(async () => {
  await loadData()
})

async function loadData() {
  await Promise.all([
    scenariosStore.loadSources(),
    scenariosStore.loadScenarios(),
  ])
}

function updateSearch() {
  scenariosStore.updateFilter({ search: localSearch.value })
}

function updateSourceFilter() {
  scenariosStore.updateFilter({ source: localSource.value })
  scenariosStore.loadScenarios(localSource.value)
}

function updateFilters() {
  scenariosStore.updateFilter(localFilters.value)
}

function clearFilters() {
  localSearch.value = ''
  localSource.value = ''
  localFilters.value = {
    minOutcomes: null,
    maxOutcomes: null,
    minOpposition: null,
    maxOpposition: null,
    minRationalFraction: null,
    maxRationalFraction: null,
  }
  scenariosStore.updateFilter({
    search: '',
    source: '',
    ...localFilters.value,
  })
}

function selectScenario(scenario) {
  scenariosStore.selectScenario(scenario)
  activeTab.value = 'info'
}

async function loadStats() {
  if (!selectedScenario.value) return
  if (selectedScenarioStats.value) return // Already loaded
  
  await scenariosStore.loadScenarioStats(selectedScenario.value.path)
}

async function calculateStats() {
  if (!selectedScenario.value) return
  await scenariosStore.calculateScenarioStats(selectedScenario.value.path, true)
}

async function loadPlotData() {
  if (!selectedScenario.value) return
  if (selectedScenarioPlotData.value) return // Already loaded
  
  await scenariosStore.loadScenarioPlotData(selectedScenario.value.path)
}

// Watch for plot data changes and render plot
watch(selectedScenarioPlotData, async (data) => {
  if (data && plotDiv.value) {
    await nextTick()
    renderPlot(data)
  }
})

function renderPlot(data) {
  if (!plotDiv.value || !data.outcome_utilities) return
  
  const utilities = data.outcome_utilities
  const names = data.negotiator_names
  
  // Create traces for 2D or 3D plot
  if (names.length === 2) {
    // 2D scatter plot
    const trace = {
      x: utilities.map(u => u[0]),
      y: utilities.map(u => u[1]),
      mode: 'markers',
      type: 'scatter',
      marker: {
        size: 4,
        color: 'rgba(59, 130, 246, 0.6)',
      },
      name: 'Outcomes',
    }
    
    const layout = {
      xaxis: { title: names[0] },
      yaxis: { title: names[1] },
      hovermode: 'closest',
      margin: { l: 50, r: 20, t: 30, b: 50 },
    }
    
    Plotly.newPlot(plotDiv.value, [trace], layout, { responsive: true })
  } else if (names.length === 3) {
    // 3D scatter plot
    const trace = {
      x: utilities.map(u => u[0]),
      y: utilities.map(u => u[1]),
      z: utilities.map(u => u[2]),
      mode: 'markers',
      type: 'scatter3d',
      marker: {
        size: 3,
        color: 'rgba(59, 130, 246, 0.6)',
      },
      name: 'Outcomes',
    }
    
    const layout = {
      scene: {
        xaxis: { title: names[0] },
        yaxis: { title: names[1] },
        zaxis: { title: names[2] },
      },
      margin: { l: 0, r: 0, t: 0, b: 0 },
    }
    
    Plotly.newPlot(plotDiv.value, [trace], layout, { responsive: true })
  }
}

function openNewNegotiation() {
  // TODO: Emit event or navigate to negotiations with this scenario selected
  console.log('Open new negotiation with scenario:', selectedScenario.value)
}

function formatNumber(num) {
  if (num === null || num === undefined) return 'N/A'
  if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K'
  return num.toString()
}
</script>

<style scoped>
.scenarios-view {
  display: grid;
  grid-template-columns: 350px 1fr;
  height: 100%;
  gap: 8px;
  padding: 16px;
  overflow: hidden;
}

.scenarios-list-panel {
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

.input-search,
.input-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-range {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.scenarios-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scenario-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.scenario-item:hover {
  border-color: var(--primary-color);
  background: var(--bg-hover);
}

.scenario-item.active {
  border-color: var(--primary-color);
  background: var(--primary-bg);
}

.scenario-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.scenario-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.scenario-stats {
  display: flex;
  gap: 12px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  font-size: 0.75rem;
  font-weight: 500;
}

.scenario-details-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.scenario-details {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.details-header h2 {
  margin: 0;
  font-size: 1.3rem;
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

.info-grid,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.info-item,
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item label,
.stat-item label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.info-item span,
.stat-item span {
  font-size: 1rem;
  color: var(--text-primary);
}

.issues-section,
.tags-section {
  margin-top: 24px;
}

.issues-section h3,
.tags-section h3 {
  margin: 0 0 12px 0;
  font-size: 1rem;
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.issue-name {
  flex: 1;
  font-weight: 500;
}

.issue-type,
.issue-values {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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

.plot-container {
  width: 100%;
  height: 500px;
}

.plot {
  width: 100%;
  height: 100%;
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
  font-size: 1.2rem;
  padding: 4px;
  transition: color 0.2s;
}

.btn-icon:hover {
  color: var(--text-primary);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
