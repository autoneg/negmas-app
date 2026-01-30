<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
      <div class="modal ranking-modal">
        <div class="modal-header">
          <h3>Tournament Rankings</h3>
          <button class="modal-close" @click="$emit('close')">×</button>
        </div>
        
        <div class="modal-body">
          <!-- Controls -->
          <div class="ranking-controls">
            <div class="control-group">
              <label class="control-label">Metric</label>
              <select v-model="selectedMetric" class="form-select" @change="loadRankings">
                <option v-for="m in availableMetrics" :key="m" :value="m">{{ formatMetricName(m) }}</option>
              </select>
            </div>
            
            <div class="control-group">
              <label class="control-label">Statistic</label>
              <select v-model="selectedStatistic" class="form-select" @change="loadRankings">
                <option v-for="s in availableStatistics" :key="s" :value="s">{{ formatStatName(s) }}</option>
              </select>
            </div>
            
            <div v-if="scenarios.length > 1" class="control-group">
              <label class="control-label">Scenario</label>
              <select v-model="filterScenario" class="form-select" @change="loadRankings">
                <option value="">All Scenarios</option>
                <option v-for="s in scenarios" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
            
            <div v-if="partners.length > 1" class="control-group">
              <label class="control-label">Partner</label>
              <select v-model="filterPartner" class="form-select" @change="loadRankings">
                <option value="">All Partners</option>
                <option v-for="p in partners" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
          </div>
          
          <!-- Loading -->
          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <span>Loading rankings...</span>
          </div>
          
          <!-- Error -->
          <div v-else-if="error" class="error-state">
            <span class="error-icon">⚠️</span>
            <span>{{ error }}</span>
          </div>
          
          <!-- Rankings Table -->
          <div v-else-if="leaderboard.length > 0" class="rankings-table-container">
            <table class="rankings-table">
              <thead>
                <tr>
                  <th class="rank-col">#</th>
                  <th class="strategy-col">Strategy</th>
                  <th class="score-col">{{ formatMetricName(selectedMetric) }} ({{ formatStatName(selectedStatistic) }})</th>
                  <th class="count-col">Count</th>
                  <th class="stats-col">Mean</th>
                  <th class="stats-col">Std</th>
                  <th class="stats-col">Min</th>
                  <th class="stats-col">Max</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in leaderboard" :key="entry.strategy" :class="{ 'top-rank': entry.rank === 1 }">
                  <td class="rank-col">
                    <span class="rank-badge" :class="getRankClass(entry.rank)">{{ entry.rank }}</span>
                  </td>
                  <td class="strategy-col">{{ entry.strategy }}</td>
                  <td class="score-col">
                    <span class="score-value">{{ formatScore(entry.score) }}</span>
                  </td>
                  <td class="count-col">{{ entry.count }}</td>
                  <td class="stats-col">{{ formatScore(entry.mean) }}</td>
                  <td class="stats-col">{{ formatScore(entry.std) }}</td>
                  <td class="stats-col">{{ formatScore(entry.min) }}</td>
                  <td class="stats-col">{{ formatScore(entry.max) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- Empty state -->
          <div v-else class="empty-state">
            <span>No ranking data available</span>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="$emit('close')">Close</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  tournamentId: { type: String, required: true }
})

const emit = defineEmits(['close'])

// State
const loading = ref(false)
const error = ref(null)
const leaderboard = ref([])
// Initial list includes all possible metrics (will be updated from API with actual available metrics)
// Note: reserved_value is intentionally excluded as it's not a useful ranking metric
const availableMetrics = ref([
  'utility', 
  'advantage', 
  'welfare', 
  'partner_welfare', 
  'time',
  'nash_optimality',
  'kalai_optimality',
  'ks_optimality',
  'max_welfare_optimality',
  'pareto_optimality'
])
const availableStatistics = ref(['mean', 'median', 'min', 'max', 'std', 'count'])
const scenarios = ref([])
const partners = ref([])

// Selections
const selectedMetric = ref('utility')
const selectedStatistic = ref('mean')
const filterScenario = ref('')
const filterPartner = ref('')

// Format helpers
function formatMetricName(metric) {
  const names = {
    utility: 'Utility',
    reserved_value: 'Reserved Value',
    advantage: 'Advantage',
    partner_welfare: 'Partner Welfare',
    welfare: 'Welfare',
    time: 'Time',
    nash_optimality: 'Nash Optimality',
    kalai_optimality: 'Kalai Optimality',
    ks_optimality: 'KS Optimality',
    max_welfare_optimality: 'Max Welfare Opt.',
    pareto_optimality: 'Pareto Optimality'
  }
  return names[metric] || metric
}

function formatStatName(stat) {
  const names = {
    mean: 'Mean',
    median: 'Median',
    min: 'Min',
    max: 'Max',
    std: 'Std Dev',
    truncated_mean: 'Trimmed Mean',
    count: 'Count',
    sum: 'Sum'
  }
  return names[stat] || stat
}

function formatScore(value) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') {
    return value.toFixed(4)
  }
  return value
}

function getRankClass(rank) {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  if (rank === 3) return 'bronze'
  return ''
}

// Load rankings from API
async function loadRankings() {
  if (!props.tournamentId) return
  
  loading.value = true
  error.value = null
  
  try {
    const params = new URLSearchParams({
      metric: selectedMetric.value,
      statistic: selectedStatistic.value
    })
    
    if (filterScenario.value) {
      params.append('scenario', filterScenario.value)
    }
    if (filterPartner.value) {
      params.append('partner', filterPartner.value)
    }
    
    const response = await fetch(`/api/tournament/saved/${props.tournamentId}/score_analysis?${params}`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const data = await response.json()
    
    if (data.error) {
      error.value = data.error
      return
    }
    
    leaderboard.value = data.leaderboard || []
    
    // Always update available options when returned
    if (data.available_metrics?.length > 0) {
      availableMetrics.value = data.available_metrics
      // If current metric is not in available, switch to first available
      if (!data.available_metrics.includes(selectedMetric.value) && data.available_metrics.length > 0) {
        selectedMetric.value = data.available_metrics[0]
      }
    }
    if (data.available_statistics?.length > 0) {
      availableStatistics.value = data.available_statistics
    }
    if (data.scenarios?.length > 0) {
      scenarios.value = data.scenarios
    }
    if (data.partners?.length > 0) {
      partners.value = data.partners
    }
  } catch (e) {
    console.error('[TournamentRankingModal] Failed to load rankings:', e)
    error.value = 'Failed to load rankings'
  } finally {
    loading.value = false
  }
}

// Watch for show changes
watch(() => props.show, (newShow) => {
  if (newShow) {
    loadRankings()
  }
})

// Load on mount if already visible
onMounted(() => {
  if (props.show) {
    loadRankings()
  }
})
</script>

<style scoped>
.ranking-modal {
  max-width: 1000px;
  width: 90%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.ranking-controls {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 150px;
}

.control-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.form-select {
  padding: 6px 10px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  color: var(--text-secondary);
}

.error-state {
  color: var(--danger);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.rankings-table-container {
  flex: 1;
  overflow: auto;
}

.rankings-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.rankings-table th,
.rankings-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.rankings-table th {
  background: var(--bg-secondary);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-secondary);
  position: sticky;
  top: 0;
  z-index: 1;
}

.rankings-table tbody tr:hover {
  background: var(--bg-hover);
}

.rankings-table tbody tr.top-rank {
  background: rgba(var(--success-rgb, 16, 185, 129), 0.1);
}

.rank-col {
  width: 50px;
  text-align: center !important;
}

.strategy-col {
  min-width: 150px;
}

.score-col {
  min-width: 120px;
}

.count-col,
.stats-col {
  width: 80px;
  text-align: right !important;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  font-weight: 600;
  font-size: 12px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.rank-badge.gold {
  background: linear-gradient(135deg, #FFD700, #FFA500);
  color: #000;
}

.rank-badge.silver {
  background: linear-gradient(135deg, #C0C0C0, #A0A0A0);
  color: #000;
}

.rank-badge.bronze {
  background: linear-gradient(135deg, #CD7F32, #B87333);
  color: #fff;
}

.score-value {
  font-weight: 600;
  font-family: var(--font-mono);
}

.modal-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
