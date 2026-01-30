<template>
  <div class="tournament-info-tabbed-panel">
    <div class="panel-header">
      <div class="tab-buttons">
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'leaderboard' }"
          @click="activeTab = 'leaderboard'"
        >
          {{ isCompleted ? 'Final Rankings' : 'Leaderboard' }}
          <span v-if="leaderboard.length > 0" class="badge">{{ leaderboard.length }}</span>
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: activeTab === 'config' }"
          @click="activeTab = 'config'"
        >
          Configuration
        </button>
      </div>
    </div>
    
    <div class="panel-body">
      <!-- Leaderboard Tab -->
      <div v-show="activeTab === 'leaderboard'" class="tab-content">
        <div v-if="leaderboard.length === 0" class="empty-state-sm">
          <p class="text-muted">{{ isCompleted ? 'No scores available' : 'Waiting for results...' }}</p>
        </div>
        
        <div v-else class="leaderboard-list">
          <div
            v-for="entry in leaderboard"
            :key="entry.competitor || entry.name"
            class="leaderboard-entry"
            :class="'rank-' + entry.rank"
          >
            <div class="leaderboard-rank">
              <span v-if="entry.rank === 1" class="rank-medal">1</span>
              <span v-else-if="entry.rank === 2" class="rank-medal silver">2</span>
              <span v-else-if="entry.rank === 3" class="rank-medal bronze">3</span>
              <span v-else class="rank-number">{{ entry.rank }}</span>
            </div>
            <div class="leaderboard-info">
              <div class="leaderboard-name">{{ entry.competitor || entry.name }}</div>
              <div class="leaderboard-stats">
                <span v-if="!isCompleted">
                  {{ entry.n_negotiations || 0 }} games | {{ entry.n_agreements || 0 }} agr
                </span>
                <span v-else>
                  {{ entry.n_negotiations || '-' }} games | u:{{ (entry.mean_utility || entry.avg_utility)?.toFixed(2) || '-' }}
                </span>
              </div>
            </div>
            <div class="leaderboard-score">{{ formatScore(entry) }}</div>
          </div>
        </div>
      </div>
      
      <!-- Configuration Tab -->
      <div v-show="activeTab === 'config'" class="tab-content">
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
                  class="config-badge"
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
                  class="config-badge config-badge-neutral"
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
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  leaderboard: {
    type: Array,
    default: () => []
  },
  config: {
    type: Object,
    default: null
  },
  status: {
    type: String,
    default: 'running'
  }
})

const activeTab = ref('leaderboard')

const isCompleted = computed(() => props.status === 'completed')

/**
 * Format the score for display, handling null/undefined/NaN/Infinity cases.
 */
function formatScore(entry) {
  if (entry.score !== null && entry.score !== undefined && 
      isFinite(entry.score) && !isNaN(entry.score)) {
    return entry.score.toFixed(3)
  }
  
  if (entry.mean_utility !== null && entry.mean_utility !== undefined &&
      isFinite(entry.mean_utility) && !isNaN(entry.mean_utility)) {
    return entry.mean_utility.toFixed(3)
  }
  
  if (entry.avg_utility !== null && entry.avg_utility !== undefined &&
      isFinite(entry.avg_utility) && !isNaN(entry.avg_utility)) {
    return entry.avg_utility.toFixed(3)
  }
  
  return 'N/A'
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
</script>

<style scoped>
.tournament-info-tabbed-panel {
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
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.tab-buttons {
  display: flex;
  gap: 4px;
}

.tab-btn {
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--primary-color);
  color: white;
}

.badge {
  background: rgba(255,255,255,0.2);
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.tab-btn:not(.active) .badge {
  background: var(--bg-tertiary);
}

.panel-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-state-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 120px;
  color: var(--text-muted);
  font-size: 13px;
}

/* Leaderboard styles */
.leaderboard-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.leaderboard-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  transition: all 0.2s;
}

.leaderboard-entry:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.leaderboard-entry.rank-1 {
  border-color: #fbbf24;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, var(--bg-secondary) 100%);
}

.leaderboard-entry.rank-2 {
  border-color: #94a3b8;
  background: linear-gradient(135deg, rgba(148, 163, 184, 0.1) 0%, var(--bg-secondary) 100%);
}

.leaderboard-entry.rank-3 {
  border-color: #d97706;
  background: linear-gradient(135deg, rgba(217, 119, 6, 0.1) 0%, var(--bg-secondary) 100%);
}

.leaderboard-rank {
  min-width: 32px;
  text-align: center;
}

.rank-medal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #78350f;
}

.rank-medal.silver {
  background: linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%);
  color: #334155;
}

.rank-medal.bronze {
  background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
  color: #78350f;
}

.rank-number {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.leaderboard-info {
  flex: 1;
  min-width: 0;
}

.leaderboard-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.leaderboard-stats {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.leaderboard-score {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary-color);
  font-family: 'Monaco', 'Menlo', monospace;
}

/* Config styles */
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
  font-size: 11px;
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
  gap: 4px;
}

.config-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
}

.config-label {
  color: var(--text-muted);
  min-width: 90px;
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
  font-family: 'SF Mono', 'Monaco', monospace;
  font-size: 11px;
  word-break: break-all;
  flex: 1;
}

.competitor-list,
.scenario-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.config-badge {
  display: inline-block;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.config-badge-neutral {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.btn-icon-sm {
  padding: 4px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon-sm:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
</style>
