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
            <span v-if="scenario.tags && scenario.tags.length > 0" class="tags">
              <span v-for="tag in scenario.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
            </span>
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
        
        <!-- Scrollable content with panels -->
        <div class="details-content">
          <!-- Info Panel (Full Width) -->
          <div class="panel panel-full">
            <h3 class="panel-title">Information</h3>
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
            
            <!-- Description -->
            <div v-if="selectedScenario.description" class="description-section">
              <h4>Description</h4>
              <div class="description-text">{{ selectedScenario.description }}</div>
            </div>
            
            <!-- Issues -->
            <div v-if="selectedScenario.issues && selectedScenario.issues.length > 0" class="issues-section">
              <h4>Issues</h4>
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
              <h4>Tags</h4>
              <div class="tags">
                <span v-for="tag in selectedScenario.tags" :key="tag" class="badge">{{ tag }}</span>
              </div>
            </div>
          </div>
          
          <!-- Stats and Plot Side by Side -->
          <div class="panel-row">
            <!-- Stats Panel -->
            <div class="panel panel-half">
              <div class="panel-header">
                <h3 class="panel-title">Statistics</h3>
                <button 
                  v-if="!selectedScenario.has_stats && !loadingStats" 
                  class="btn-secondary btn-sm" 
                  @click="calculateStats"
                >
                  Calculate Stats
                </button>
              </div>
            
            <div v-if="!statsLoaded && !loadingStats" class="panel-empty">
              <p>Statistics not calculated yet</p>
              <button class="btn-primary btn-sm" @click="calculateStats">Calculate Stats</button>
            </div>
            
            <div v-else-if="loadingStats" class="loading-state">
              <span class="spinner"></span> Loading stats...
            </div>
            
            <div v-else-if="selectedScenarioStats" class="stats-grid">
              <div class="stat-item" v-if="selectedScenarioStats.n_pareto_outcomes">
                <label>Pareto Outcomes</label>
                <span>{{ formatNumber(selectedScenarioStats.n_pareto_outcomes) }}</span>
              </div>
              <div class="stat-item" v-if="selectedScenarioStats.opposition !== null && selectedScenarioStats.opposition !== undefined">
                <label>Opposition</label>
                <span>{{ selectedScenarioStats.opposition.toFixed(3) }}</span>
              </div>
              <div class="stat-item" v-if="selectedScenarioStats.rational_fraction !== null && selectedScenarioStats.rational_fraction !== undefined">
                <label>Rational Fraction</label>
                <span>{{ selectedScenarioStats.rational_fraction.toFixed(3) }}</span>
              </div>
              
              <!-- Nash Point -->
              <div class="stat-item full-width" v-if="selectedScenarioStats.nash_utils && selectedScenarioStats.nash_utils.length > 0">
                <label>Nash Point</label>
                <span>{{ formatUtilityList(selectedScenarioStats.nash_utils[0]) }}</span>
              </div>
              
              <!-- Kalai Point -->
              <div class="stat-item full-width" v-if="selectedScenarioStats.kalai_utils && selectedScenarioStats.kalai_utils.length > 0">
                <label>Kalai Point</label>
                <span>{{ formatUtilityList(selectedScenarioStats.kalai_utils[0]) }}</span>
              </div>
              
              <!-- KS Point -->
              <div class="stat-item full-width" v-if="selectedScenarioStats.ks_utils && selectedScenarioStats.ks_utils.length > 0">
                <label>KS Point</label>
                <span>{{ formatUtilityList(selectedScenarioStats.ks_utils[0]) }}</span>
              </div>
              
              <!-- Max Welfare Point -->
              <div class="stat-item full-width" v-if="selectedScenarioStats.max_welfare_utils && selectedScenarioStats.max_welfare_utils.length > 0">
                <label>Max Welfare</label>
                <span>{{ formatUtilityList(selectedScenarioStats.max_welfare_utils[0]) }}</span>
              </div>
            </div>
            </div>
          
            <!-- Visualization Panel -->
          <div class="panel panel-half">
            <div class="panel-header">
              <h3 class="panel-title">Utility Space Visualization</h3>
              <div class="panel-header-actions">
                <label v-if="plotDataLoaded" class="plot-mode-toggle">
                  <input type="checkbox" v-model="useInteractivePlot" />
                  <span>Interactive</span>
                </label>
                <button 
                  v-if="plotDataLoaded" 
                  class="btn-secondary btn-sm" 
                  @click="refreshPlot"
                  :title="useInteractivePlot ? 'Regenerate interactive plot' : 'Regenerate cached image'"
                >
                  Refresh
                </button>
              </div>
            </div>
            
            <div v-if="!plotDataLoaded && !loadingPlotData" class="panel-empty">
              <p>Click to load visualization</p>
              <button class="btn-primary btn-sm" @click="loadPlotData">Load Visualization</button>
            </div>
            
            <div v-else-if="loadingPlotData" class="loading-state">
              <span class="spinner"></span> Loading visualization...
            </div>
            
            <div v-else-if="selectedScenarioPlotData" class="plot-container">
              <!-- Cached WebP Image (default) -->
              <div v-if="!useInteractivePlot && plotImageUrl" class="plot-image-container">
                <img :src="plotImageUrl" alt="Scenario Plot" class="plot-image" />
                <p class="plot-hint">Toggle "Interactive" for customizable Plotly visualization</p>
              </div>
              
              <!-- Interactive Plotly Plot -->
              <div v-else class="plot-interactive-container">
                <!-- Negotiator Selection -->
                <div class="plot-controls" v-if="negotiatorNamesForPlot && negotiatorNamesForPlot.length > 1">
                  <label>X-Axis:</label>
                  <select v-model="plotNegotiator1" @change="renderPlot" class="input-select">
                    <option v-for="(name, idx) in negotiatorNamesForPlot" :key="idx" :value="idx">
                      {{ name }}
                    </option>
                  </select>
                  <label>Y-Axis:</label>
                  <select v-model="plotNegotiator2" @change="renderPlot" class="input-select">
                    <option v-for="(name, idx) in negotiatorNamesForPlot" :key="idx" :value="idx">
                      {{ name }}
                    </option>
                  </select>
                </div>
                <div ref="plotDiv" class="plot"></div>
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- New Negotiation Modal -->
    <NewNegotiationModal
      :show="showNewNegotiationModal"
      :preselected-scenario="selectedScenario"
      @close="showNewNegotiationModal = false"
      @start="onNegotiationStart"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useScenariosStore } from '../stores/scenarios'
import { storeToRefs } from 'pinia'
import Plotly from 'plotly.js-dist-min'
import NewNegotiationModal from '../components/NewNegotiationModal.vue'

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

const plotDiv = ref(null)
const plotNegotiator1 = ref(0)
const plotNegotiator2 = ref(1)
const useInteractivePlot = ref(false) // Default to cached PNG
const plotImageUrl = computed(() => {
  if (!selectedScenario.value) return null
  return `/api/scenarios/${encodeURIComponent(selectedScenario.value.path)}/plot-image`
})
const showNewNegotiationModal = ref(false)
const router = useRouter()

// Computed properties
const statsLoaded = computed(() => selectedScenarioStats.value !== null)
const plotDataLoaded = computed(() => selectedScenarioPlotData.value !== null)
const negotiatorNamesForPlot = computed(() => {
  // Prefer stats negotiator_names, fallback to plot data negotiator_names
  if (selectedScenarioStats.value?.negotiator_names) {
    return selectedScenarioStats.value.negotiator_names
  }
  if (selectedScenarioPlotData.value?.negotiator_names) {
    return selectedScenarioPlotData.value.negotiator_names
  }
  return []
})

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

async function selectScenario(scenario) {
  scenariosStore.selectScenario(scenario)
  // Auto-load stats when selecting a scenario
  if (scenario.has_stats) {
    await scenariosStore.loadScenarioStats(scenario.path)
  }
  // Auto-load plot data
  await scenariosStore.loadScenarioPlotData(scenario.path)
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

async function loadPlotData(forceRegenerate = false) {
  if (!selectedScenario.value) return
  await scenariosStore.loadScenarioPlotData(selectedScenario.value.path, 10000, forceRegenerate)
}

async function refreshPlot() {
  // Force regenerate the plot (both cached image and interactive data)
  await loadPlotData(true)
}

// Watch for plot data changes and render plot
watch(selectedScenarioPlotData, async (data) => {
  if (data && plotDiv.value && useInteractivePlot.value) {
    await nextTick()
    renderPlot()
  }
})

// Watch for interactive mode changes
watch(useInteractivePlot, async (isInteractive) => {
  if (isInteractive && selectedScenarioPlotData.value && plotDiv.value) {
    await nextTick()
    renderPlot()
  }
})

// Watch for stats changes and render plot if plot data is loaded
watch(selectedScenarioStats, async (stats) => {
  if (stats && selectedScenarioPlotData.value && plotDiv.value) {
    await nextTick()
    renderPlot()
  }
})

function renderPlot() {
  const data = selectedScenarioPlotData.value
  if (!plotDiv.value || !data || !data.outcome_utilities) return
  
  const utilities = data.outcome_utilities
  const stats = selectedScenarioStats.value
  const names = negotiatorNamesForPlot.value
  
  // Use selected negotiators for axes
  const idx1 = plotNegotiator1.value
  const idx2 = plotNegotiator2.value
  
  // Extract utilities for selected negotiators
  const x = utilities.map(u => u[idx1])
  const y = utilities.map(u => u[idx2])
  
  // Create main scatter trace
  const trace = {
    x: x,
    y: y,
    mode: 'markers',
    type: 'scatter',
    marker: { size: 3, color: 'rgba(59, 130, 246, 0.3)' },
    name: 'Outcomes',
    hovertemplate: `${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                   `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
  }
  
  const traces = [trace]
  
  // Add Pareto frontier if available in stats
  if (stats?.pareto_utils && stats.pareto_utils.length > 0) {
    const paretoX = stats.pareto_utils.map(u => u[idx1])
    const paretoY = stats.pareto_utils.map(u => u[idx2])
    traces.push({
      x: paretoX,
      y: paretoY,
      mode: 'markers',
      type: 'scatter',
      marker: { size: 5, color: 'red', symbol: 'diamond' },
      name: 'Pareto Frontier',
      hovertemplate: `Pareto<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add Nash point if available
  if (stats?.nash_utils && stats.nash_utils.length > 0) {
    traces.push({
      x: stats.nash_utils.map(u => u[idx1]),
      y: stats.nash_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { size: 10, color: 'green', symbol: 'star' },
      name: 'Nash',
      hovertemplate: `Nash<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add Kalai point if available
  if (stats?.kalai_utils && stats.kalai_utils.length > 0) {
    traces.push({
      x: stats.kalai_utils.map(u => u[idx1]),
      y: stats.kalai_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { size: 10, color: 'orange', symbol: 'square' },
      name: 'Kalai',
      hovertemplate: `Kalai<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add KS point if available
  if (stats?.ks_utils && stats.ks_utils.length > 0) {
    traces.push({
      x: stats.ks_utils.map(u => u[idx1]),
      y: stats.ks_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { size: 10, color: 'purple', symbol: 'cross' },
      name: 'KS',
      hovertemplate: `KS<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add Max Welfare point if available
  if (stats?.max_welfare_utils && stats.max_welfare_utils.length > 0) {
    traces.push({
      x: stats.max_welfare_utils.map(u => u[idx1]),
      y: stats.max_welfare_utils.map(u => u[idx2]),
      mode: 'markers',
      type: 'scatter',
      marker: { size: 10, color: 'blue', symbol: 'diamond-open' },
      name: 'Max Welfare',
      hovertemplate: `Max Welfare<br>${names[idx1] || 'N1'}: %{x:.3f}<br>` +
                     `${names[idx2] || 'N2'}: %{y:.3f}<extra></extra>`
    })
  }
  
  // Add reservation value lines if available
  const shapes = []
  if (data.reserved_values && data.reserved_values.length > 0) {
    const reservedVal1 = data.reserved_values[idx1]
    const reservedVal2 = data.reserved_values[idx2]
    
    // Vertical line for negotiator 1's reservation value
    if (reservedVal1 !== null && reservedVal1 !== undefined) {
      shapes.push({
        type: 'line',
        x0: reservedVal1,
        x1: reservedVal1,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: {
          color: 'rgba(128, 128, 128, 0.5)',
          width: 2,
          dash: 'dash'
        }
      })
    }
    
    // Horizontal line for negotiator 2's reservation value
    if (reservedVal2 !== null && reservedVal2 !== undefined) {
      shapes.push({
        type: 'line',
        x0: 0,
        x1: 1,
        xref: 'paper',
        y0: reservedVal2,
        y1: reservedVal2,
        line: {
          color: 'rgba(128, 128, 128, 0.5)',
          width: 2,
          dash: 'dash'
        }
      })
    }
  }
  
  const layout = {
    xaxis: { title: names[idx1] || `Negotiator ${idx1}` },
    yaxis: { 
      title: names[idx2] || `Negotiator ${idx2}`,
      scaleanchor: 'x',
      scaleratio: 1
    },
    hovermode: 'closest',
    margin: { l: 60, r: 20, t: 30, b: 60 },
    showlegend: true,
    legend: { x: 1, y: 1, xanchor: 'right' },
    shapes: shapes
  }
  
  Plotly.newPlot(plotDiv.value, traces, layout, { responsive: true })
}

function formatUtilityList(utils) {
  if (!utils || !Array.isArray(utils)) return 'N/A'
  return '(' + utils.map(u => u.toFixed(3)).join(', ') + ')'
}

function openNewNegotiation() {
  showNewNegotiationModal.value = true
}

function onNegotiationStart(data) {
  // Navigate to negotiations view and start streaming
  router.push({
    name: 'negotiations',
    query: { session_id: data.session_id }
  })
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

.tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  background: var(--primary-light);
  color: var(--primary-color);
  font-size: 0.7rem;
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

.details-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-right: 8px; /* Space for scrollbar */
}

/* Panel row for side-by-side layout */
.panel-row {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.panel {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

/* Full width panel */
.panel-full {
  width: 100%;
}

/* Half width panels for side-by-side */
.panel-half {
  flex: 1;
  min-width: 0; /* Allow flex shrinking */
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-title {
  margin: 0 0 12px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-empty {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.description-section,
.issues-section,
.tags-section {
  margin-top: 16px;
}

.description-section h4,
.issues-section h4,
.tags-section h4 {
  margin: 0 0 8px 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.description-text {
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.stat-item.full-width {
  grid-column: 1 / -1;
}

.plot-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.plot-controls label {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.plot-controls .input-select {
  flex: 1;
  max-width: 200px;
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

/* Plot visualization styles */
.plot-mode-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  user-select: none;
}

.plot-mode-toggle input[type="checkbox"] {
  cursor: pointer;
}

.plot-image-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.plot-image {
  max-width: 100%;
  height: auto;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: white;
}

.plot-hint {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
  font-style: italic;
}

.plot-interactive-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
