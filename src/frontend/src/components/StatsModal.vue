<template>
  <!-- Stats Modal -->
  <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
    <div class="modal-content modal-lg">
      <!-- Header -->
      <div class="modal-header">
        <h3 class="modal-title">Scenario Statistics</h3>
        <button class="modal-close-btn" @click="$emit('close')" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <!-- Body -->
      <div class="modal-body" style="max-height: 70vh; overflow-y: auto; background: var(--bg-primary);">
        <div v-if="!stats" class="empty-state" style="padding: 40px;">
          <p>No statistics available for this scenario.</p>
        </div>
        
        <div v-else class="stats-grid">
          <!-- Overview Section -->
          <div class="stats-section">
            <h4 class="stats-section-title">Overview</h4>
            <div class="stats-row">
              <span class="stats-label">Total Outcomes:</span>
              <span class="stats-value">{{ stats.total_outcomes?.toLocaleString() || 'N/A' }}</span>
            </div>
            <div v-if="stats.sampled" class="stats-row">
              <span class="stats-label">Sampled:</span>
              <span class="stats-value">{{ stats.sample_size?.toLocaleString() }} outcomes</span>
            </div>
            <div v-if="paretoCount !== null" class="stats-row">
              <span class="stats-label">Pareto Frontier:</span>
              <span class="stats-value">{{ paretoCount.toLocaleString() }} outcomes</span>
            </div>
          </div>
          
          <!-- Reserved Values Section -->
          <div v-if="stats.reserved_values && stats.reserved_values.length > 0" class="stats-section">
            <h4 class="stats-section-title">Reserved Values</h4>
            <div v-for="(value, idx) in stats.reserved_values" :key="idx" class="stats-row">
              <span class="stats-label">{{ negotiatorNames[idx] || `Negotiator ${idx + 1}` }}:</span>
              <span class="stats-value">{{ value !== null ? value.toFixed(3) : 'N/A' }}</span>
            </div>
          </div>
          
          <!-- Nash Point Section -->
          <div v-if="stats.nash_point" class="stats-section">
            <h4 class="stats-section-title">Nash Bargaining Solution</h4>
            <div class="stats-row">
              <span class="stats-label">Outcome:</span>
              <span class="stats-value monospace">{{ formatOutcome(stats.nash_point.outcome) }}</span>
            </div>
            <div v-for="(utility, idx) in stats.nash_point.utilities" :key="`nash-${idx}`" class="stats-row">
              <span class="stats-label">{{ negotiatorNames[idx] || `Negotiator ${idx + 1}` }} Utility:</span>
              <span class="stats-value">{{ utility.toFixed(3) }}</span>
            </div>
            <div v-if="stats.nash_point.welfare" class="stats-row">
              <span class="stats-label">Social Welfare:</span>
              <span class="stats-value">{{ stats.nash_point.welfare.toFixed(3) }}</span>
            </div>
          </div>
          
          <!-- Kalai-Smorodinsky Point Section -->
          <div v-if="stats.kalai_smorodinsky_point" class="stats-section">
            <h4 class="stats-section-title">Kalai-Smorodinsky Solution</h4>
            <div class="stats-row">
              <span class="stats-label">Outcome:</span>
              <span class="stats-value monospace">{{ formatOutcome(stats.kalai_smorodinsky_point.outcome) }}</span>
            </div>
            <div v-for="(utility, idx) in stats.kalai_smorodinsky_point.utilities" :key="`ks-${idx}`" class="stats-row">
              <span class="stats-label">{{ negotiatorNames[idx] || `Negotiator ${idx + 1}` }} Utility:</span>
              <span class="stats-value">{{ utility.toFixed(3) }}</span>
            </div>
            <div v-if="stats.kalai_smorodinsky_point.welfare" class="stats-row">
              <span class="stats-label">Social Welfare:</span>
              <span class="stats-value">{{ stats.kalai_smorodinsky_point.welfare.toFixed(3) }}</span>
            </div>
          </div>
          
          <!-- Kalai Point Section -->
          <div v-if="stats.kalai_point" class="stats-section">
            <h4 class="stats-section-title">Kalai Solution</h4>
            <div class="stats-row">
              <span class="stats-label">Outcome:</span>
              <span class="stats-value monospace">{{ formatOutcome(stats.kalai_point.outcome) }}</span>
            </div>
            <div v-for="(utility, idx) in stats.kalai_point.utilities" :key="`kalai-${idx}`" class="stats-row">
              <span class="stats-label">{{ negotiatorNames[idx] || `Negotiator ${idx + 1}` }} Utility:</span>
              <span class="stats-value">{{ utility.toFixed(3) }}</span>
            </div>
            <div v-if="stats.kalai_point.welfare" class="stats-row">
              <span class="stats-label">Social Welfare:</span>
              <span class="stats-value">{{ stats.kalai_point.welfare.toFixed(3) }}</span>
            </div>
          </div>
          
          <!-- Max Welfare Point Section -->
          <div v-if="stats.max_welfare_point" class="stats-section">
            <h4 class="stats-section-title">Maximum Social Welfare</h4>
            <div class="stats-row">
              <span class="stats-label">Outcome:</span>
              <span class="stats-value monospace">{{ formatOutcome(stats.max_welfare_point.outcome) }}</span>
            </div>
            <div v-for="(utility, idx) in stats.max_welfare_point.utilities" :key="`welfare-${idx}`" class="stats-row">
              <span class="stats-label">{{ negotiatorNames[idx] || `Negotiator ${idx + 1}` }} Utility:</span>
              <span class="stats-value">{{ utility.toFixed(3) }}</span>
            </div>
            <div v-if="stats.max_welfare_point.welfare" class="stats-row">
              <span class="stats-label">Social Welfare:</span>
              <span class="stats-value">{{ stats.max_welfare_point.welfare.toFixed(3) }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  negotiation: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const stats = computed(() => {
  return props.negotiation?.outcome_space_data || null
})

const negotiatorNames = computed(() => {
  return props.negotiation?.negotiator_names || []
})

const paretoCount = computed(() => {
  // Try to get from pareto_utilities array first
  if (stats.value?.pareto_utilities?.length) {
    return stats.value.pareto_utilities.length
  }
  
  // Fall back to info.n_pareto if available
  if (stats.value?.info?.n_pareto !== undefined && stats.value.info.n_pareto !== null) {
    return stats.value.info.n_pareto
  }
  
  // No pareto data available
  return null
})

function formatOutcome(outcome) {
  if (!outcome) return 'N/A'
  
  // If it's an object, format as key-value pairs
  if (typeof outcome === 'object' && !Array.isArray(outcome)) {
    const entries = Object.entries(outcome)
    if (entries.length === 0) return 'N/A'
    if (entries.length <= 3) {
      return entries.map(([k, v]) => `${k}: ${v}`).join(', ')
    }
    // For many issues, show first 2 and count
    const first = entries.slice(0, 2).map(([k, v]) => `${k}: ${v}`).join(', ')
    return `${first}, ... (${entries.length} issues)`
  }
  
  // If it's an array
  if (Array.isArray(outcome)) {
    if (outcome.length === 0) return 'N/A'
    if (outcome.length <= 5) {
      return outcome.join(', ')
    }
    return `${outcome.slice(0, 3).join(', ')}, ... (${outcome.length} values)`
  }
  
  // Fallback to string
  return String(outcome)
}
</script>

<style scoped>
.modal-header {
  background: var(--bg-secondary);
}

.modal-footer {
  background: var(--bg-secondary);
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
}

.modal-close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-close-btn svg {
  width: 18px;
  height: 18px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
  padding: 8px;
}

.stats-section {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.stats-section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.stats-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 6px 0;
  gap: 16px;
}

.stats-row:not(:last-child) {
  border-bottom: 1px solid var(--border-color);
}

.stats-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.stats-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
  text-align: right;
}

.stats-value.monospace {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 11px;
  font-weight: 400;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}
</style>
