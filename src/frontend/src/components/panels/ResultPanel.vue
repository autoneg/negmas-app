<template>
  <!-- Result Panel - Shows agreement/result with optimality stats -->
  <div 
    class="panel panel-compact panel-result" 
    :class="{
      'collapsed': collapsed,
      'panel-result-agreement': negotiation?.agreement,
      'panel-result-disagreement': negotiation?.end_reason && !negotiation?.agreement && !negotiation?.error,
      'panel-result-error': negotiation?.error
    }"
    :style="negotiation?.agreement || negotiation?.optimality_stats ? 'max-height: 160px; flex: 0 0 auto;' : ''"
  >
    <span class="panel-collapsed-label" v-show="collapsed">RESULT</span>
    
    <!-- Floating Actions -->
    <div class="panel-floating-actions">
      <button 
        class="panel-btn" 
        title="Save Results" 
        @click="$emit('saveResults')" 
        v-show="negotiation?.agreement || negotiation?.end_reason"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </button>
      <button 
        class="panel-btn panel-collapse-btn" 
        title="Toggle panel" 
        @click="collapsed = !collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </div>
    
    <!-- Panel Content -->
    <div class="panel-content-ultra-compact" v-show="!collapsed" style="overflow-y: auto;">
      <!-- WebP Preview Mode (for compact list view) -->
      <div v-if="compact && previewImageUrl && !showInteractive" style="width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--bg-secondary); padding: 8px;">
        <img 
          :src="previewImageUrl" 
          alt="Result Preview" 
          style="max-width: 100%; max-height: calc(100% - 40px); object-fit: contain;"
          @error="onImageError"
        />
        <button 
          class="btn btn-sm btn-secondary mt-2" 
          @click="showInteractive = true"
          style="margin-top: 8px;"
        >
          View Full Result
        </button>
      </div>
      
      <!-- Full Result Content -->
      <div v-show="!compact || !previewImageUrl || showInteractive">
      <!-- Agreement Display -->
      <div v-if="negotiation?.agreement" class="result-row result-agreement-display">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; width: 100%;">
          <span class="result-state-badge agreement">Agreement Reached</span>
          
          <!-- Compact Agreement Summary -->
          <div class="agreement-summary">
            <span class="agreement-count">{{ agreementIssueCount }} issues agreed</span>
            <button 
              class="btn-view-agreement"
              @click="showAgreementModal = true"
              title="View full agreement details"
            >
              View Details
            </button>
          </div>
          
          <span class="result-separator">→</span>
          
          <!-- Final Utilities -->
          <div class="utilities-display">
            <span 
              v-for="(util, idx) in (negotiation.final_utilities || [])" 
              :key="idx"
              class="result-utility-labeled" 
              :style="{ color: negotiation?.negotiator_colors?.[idx] || 'var(--primary)' }"
            >
              <span class="utility-name">{{ negotiation?.negotiator_names?.[idx] || `N${idx + 1}` }}</span>
              <span class="utility-value">{{ util.toFixed(3) }}</span>
            </span>
          </div>
        </div>
      </div>
      
      <!-- Optimality Statistics - More prominent display -->
      <div 
        v-if="negotiation?.optimality_stats && hasOptimalityStats"
        class="result-optimality-section" 
        style="padding: 8px; background: var(--bg-tertiary); border-top: 1px solid var(--border-color); margin-top: 4px;"
      >
        <div style="font-size: 10px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">
          Agreement Quality
        </div>
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; font-size: 11px;">
          <!-- Pareto -->
          <div 
            class="optimality-stat-card" 
            style="text-align: center; padding: 4px; background: var(--bg-secondary); border-radius: 4px; border: 1px solid var(--border-color);"
          >
            <div class="text-muted" style="font-size: 9px; margin-bottom: 2px;">Pareto</div>
            <div 
              style="font-weight: 600; font-size: 13px;"
              :class="getOptimalityClass(negotiation.optimality_stats.pareto_optimality)"
            >
              {{ formatOptimality(negotiation.optimality_stats.pareto_optimality) }}
            </div>
          </div>
          <!-- Nash -->
          <div 
            class="optimality-stat-card" 
            style="text-align: center; padding: 4px; background: var(--bg-secondary); border-radius: 4px; border: 1px solid var(--border-color);"
          >
            <div class="text-muted" style="font-size: 9px; margin-bottom: 2px;">Nash</div>
            <div 
              style="font-weight: 600; font-size: 13px;"
              :class="getOptimalityClass(negotiation.optimality_stats.nash_optimality)"
            >
              {{ formatOptimality(negotiation.optimality_stats.nash_optimality) }}
            </div>
          </div>
          <!-- Kalai -->
          <div 
            class="optimality-stat-card" 
            style="text-align: center; padding: 4px; background: var(--bg-secondary); border-radius: 4px; border: 1px solid var(--border-color);"
          >
            <div class="text-muted" style="font-size: 9px; margin-bottom: 2px;">Kalai</div>
            <div 
              style="font-weight: 600; font-size: 13px;"
              :class="getOptimalityClass(negotiation.optimality_stats.kalai_optimality)"
            >
              {{ formatOptimality(negotiation.optimality_stats.kalai_optimality) }}
            </div>
          </div>
          <!-- Max Welfare -->
          <div 
            class="optimality-stat-card" 
            style="text-align: center; padding: 4px; background: var(--bg-secondary); border-radius: 4px; border: 1px solid var(--border-color);"
          >
            <div class="text-muted" style="font-size: 9px; margin-bottom: 2px;">Welfare</div>
            <div 
              style="font-weight: 600; font-size: 13px;"
              :class="getOptimalityClass(negotiation.optimality_stats.max_welfare_optimality)"
            >
              {{ formatOptimality(negotiation.optimality_stats.max_welfare_optimality) }}
            </div>
          </div>
          <!-- KS -->
          <div 
            class="optimality-stat-card" 
            style="text-align: center; padding: 4px; background: var(--bg-secondary); border-radius: 4px; border: 1px solid var(--border-color);"
          >
            <div class="text-muted" style="font-size: 9px; margin-bottom: 2px;">KS</div>
            <div 
              style="font-weight: 600; font-size: 13px;"
              :class="getOptimalityClass(negotiation.optimality_stats.ks_optimality)"
            >
              {{ formatOptimality(negotiation.optimality_stats.ks_optimality) }}
            </div>
          </div>
        </div>
      </div>
      
      <!-- Calculate Stats Button - Show when agreement exists but no optimality stats -->
      <div 
        v-if="negotiation?.agreement && !hasOptimalityStats && negotiation?.scenario_path"
        class="result-calculate-stats-section"
        style="padding: 8px; background: var(--bg-tertiary); border-top: 1px solid var(--border-color); margin-top: 4px;"
      >
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
          <div style="font-size: 11px; color: var(--text-secondary);">
            Agreement quality metrics not available
          </div>
          <button 
            class="btn btn-sm btn-primary calculate-stats-btn"
            @click="calculateStats"
            :disabled="calculatingStats"
            style="padding: 4px 12px; font-size: 11px;"
          >
            <span v-if="calculatingStats" class="spinner-small"></span>
            <span v-else>Calculate Stats</span>
          </button>
        </div>
        <div v-if="calculateStatsError" class="text-danger" style="font-size: 10px; margin-top: 4px;">
          {{ calculateStatsError }}
        </div>
      </div>
      
      <!-- No Agreement Display -->
      <div 
        v-if="negotiation?.end_reason && !negotiation?.agreement" 
        class="result-row result-final-state"
      >
        <span 
          class="result-state-badge" 
          :class="{
            'timeout': negotiation.end_reason === 'timeout' || negotiation.end_reason === 'no_agreement',
            'error': negotiation.error,
            'ended': !negotiation.error && negotiation.end_reason !== 'timeout' && negotiation.end_reason !== 'no_agreement'
          }"
        >
          {{ negotiation.error ? 'Error' : (negotiation.end_reason === 'timeout' || negotiation.end_reason === 'no_agreement' ? 'No Agreement' : 'Ended') }}
        </span>
        <span v-if="negotiation.error" class="result-error-scrollable">
          {{ negotiation.error }}
        </span>
        <span v-else class="text-muted result-reason">
          {{ negotiation.end_reason }}
        </span>
      </div>
      
      <!-- Progress (running) -->
      <div 
        v-if="!negotiation?.end_reason && !negotiation?.agreement && !negotiation?.pendingStart" 
        class="result-row result-row-progress"
      >
        <div class="progress-container" style="flex: 1; display: flex; align-items: center; gap: 8px;">
          <div class="progress-bar-container" style="flex: 1; height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden;">
            <div 
              class="progress-bar" 
              :style="{ width: Math.min(100, (negotiation?.relative_time || 0) * 100) + '%' }"
            ></div>
          </div>
          <span class="text-muted" style="font-size: 11px; min-width: 40px;">
            {{ Math.round((negotiation?.relative_time || 0) * 100) }}%
          </span>
        </div>
        <span class="text-muted" style="font-size: 10px; margin-left: 8px;">
          Step {{ negotiation?.step || 0 }}{{ negotiation?.n_steps ? '/' + negotiation.n_steps : '' }}
        </span>
      </div>
      
      <!-- Pending -->
      <div 
        v-if="negotiation?.pendingStart" 
        class="result-row result-row-center"
      >
        <span class="text-muted">Ready</span>
      </div>
      </div> <!-- End of full result content wrapper -->
    </div>
  </div>

  <!-- Agreement Detail Modal -->
  <div v-if="showAgreementModal" class="modal-overlay active" @click.self="showAgreementModal = false">
    <div class="modal-content modal-md">
      <div class="modal-header">
        <h3 class="modal-title">Agreement Details</h3>
        <button class="modal-close-btn" @click="showAgreementModal = false" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <div class="modal-body" style="max-height: 60vh; overflow-y: auto;">
        <!-- Agreement Summary -->
        <div class="agreement-summary-section">
          <div class="summary-stat">
            <span class="summary-label">Total Issues:</span>
            <span class="summary-value">{{ agreementIssueCount }}</span>
          </div>
          <div class="summary-stat">
            <span class="summary-label">Final Utilities:</span>
            <div class="utilities-list">
              <span 
                v-for="(util, idx) in (negotiation.final_utilities || [])" 
                :key="idx"
                class="utility-item"
                :style="{ color: negotiation?.negotiator_colors?.[idx] || 'var(--accent-primary)' }"
              >
                <strong>{{ negotiation?.negotiator_names?.[idx] || `Negotiator ${idx + 1}` }}:</strong>
                {{ util.toFixed(4) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Agreement Issues -->
        <div class="agreement-issues-section">
          <h4 class="section-title">Agreed Outcome</h4>
          <div class="agreement-issues-list">
            <div 
              v-for="(value, key) in negotiation.agreement" 
              :key="key"
              class="agreement-issue-row"
            >
              <span class="issue-name">{{ key }}</span>
              <span class="issue-value">{{ value }}</span>
            </div>
          </div>
        </div>

        <!-- Optimality Stats in Modal -->
        <div 
          v-if="negotiation?.optimality_stats && hasOptimalityStats"
          class="agreement-optimality-section"
        >
          <h4 class="section-title">Agreement Quality</h4>
          <div class="optimality-grid">
            <div v-if="negotiation.optimality_stats.pareto_optimality != null" class="optimality-card">
              <span class="optimality-label">Pareto Optimality</span>
              <span 
                class="optimality-value"
                :class="getOptimalityClass(negotiation.optimality_stats.pareto_optimality)"
              >
                {{ formatOptimality(negotiation.optimality_stats.pareto_optimality) }}
              </span>
            </div>
            <div v-if="negotiation.optimality_stats.nash_optimality != null" class="optimality-card">
              <span class="optimality-label">Nash Optimality</span>
              <span 
                class="optimality-value"
                :class="getOptimalityClass(negotiation.optimality_stats.nash_optimality)"
              >
                {{ formatOptimality(negotiation.optimality_stats.nash_optimality) }}
              </span>
            </div>
            <div v-if="negotiation.optimality_stats.kalai_optimality != null" class="optimality-card">
              <span class="optimality-label">Kalai Optimality</span>
              <span 
                class="optimality-value"
                :class="getOptimalityClass(negotiation.optimality_stats.kalai_optimality)"
              >
                {{ formatOptimality(negotiation.optimality_stats.kalai_optimality) }}
              </span>
            </div>
            <div v-if="negotiation.optimality_stats.max_welfare_optimality != null" class="optimality-card">
              <span class="optimality-label">Max Welfare Optimality</span>
              <span 
                class="optimality-value"
                :class="getOptimalityClass(negotiation.optimality_stats.max_welfare_optimality)"
              >
                {{ formatOptimality(negotiation.optimality_stats.max_welfare_optimality) }}
              </span>
            </div>
            <div v-if="negotiation.optimality_stats.ks_optimality != null" class="optimality-card">
              <span class="optimality-label">KS Optimality</span>
              <span 
                class="optimality-value"
                :class="getOptimalityClass(negotiation.optimality_stats.ks_optimality)"
              >
                {{ formatOptimality(negotiation.optimality_stats.ks_optimality) }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="showAgreementModal = false">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  negotiation: {
    type: Object,
    default: null
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['saveResults', 'statsCalculated'])

// Collapse state
const collapsed = ref(false)
const showInteractive = ref(false)
const showAgreementModal = ref(false)

// Calculate stats state
const calculatingStats = ref(false)
const calculateStatsError = ref('')

// Compute agreement issue count
const agreementIssueCount = computed(() => {
  if (!props.negotiation?.agreement) return 0
  return Object.keys(props.negotiation.agreement).length
})

// Preview image URL for compact mode
const previewImageUrl = computed(() => {
  if (props.compact && props.negotiation?.id && props.negotiation?.source === 'saved') {
    const timestamp = props.negotiation.saved_at || Date.now()
    return `/api/negotiation/saved/${props.negotiation.id}/preview/result?t=${timestamp}`
  }
  return null
})

// Image error handler for preview mode
function onImageError() {
  console.warn('Failed to load preview image, falling back to full result')
  showInteractive.value = true
}

// Check if optimality stats exist
const hasOptimalityStats = computed(() => {
  const stats = props.negotiation?.optimality_stats
  if (!stats) return false
  return stats.pareto_optimality != null || 
         stats.nash_optimality != null || 
         stats.kalai_optimality != null || 
         stats.max_welfare_optimality != null || 
         stats.ks_optimality != null
})

// Format optimality value
function formatOptimality(value) {
  if (value == null || isNaN(value)) return 'N/A'
  return (value * 100).toFixed(0) + '%'
}

// Get optimality class based on value
function getOptimalityClass(value) {
  if (value == null || isNaN(value)) return ''
  if (value >= 0.95) return 'text-success'
  if (value >= 0.7) return 'text-warning'
  return 'text-danger'
}

// Calculate outcome statistics
async function calculateStats() {
  if (!props.negotiation?.agreement || !props.negotiation?.scenario_path) {
    calculateStatsError.value = 'Missing agreement or scenario path'
    return
  }

  calculatingStats.value = true
  calculateStatsError.value = ''

  try {
    const response = await fetch('/api/negotiation/calculate-stats', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario_path: props.negotiation.scenario_path,
        agreement: props.negotiation.agreement,
        session_id: props.negotiation.isTemporary ? null : props.negotiation.id,
        source_path: props.negotiation.source_path || null
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to calculate statistics')
    }

    const data = await response.json()
    
    // Emit event so parent can update the negotiation object
    emit('statsCalculated', data.optimality_stats)
    
    console.log('[ResultPanel] Stats calculated:', data.optimality_stats, 'cached:', data.cached)
  } catch (error) {
    console.error('Failed to calculate stats:', error)
    calculateStatsError.value = error.message
  } finally {
    calculatingStats.value = false
  }
}
</script>

<style scoped>
/* Agreement display styles */
.agreement-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.agreement-count {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
}

.btn-view-agreement {
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-view-agreement:hover {
  background: var(--accent-primary-hover);
  transform: translateY(-1px);
}

.utilities-display {
  display: flex;
  gap: 12px;
  align-items: center;
}

.utility-value {
  font-weight: 700;
  font-size: 13px;
}

/* Modal styles */
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
  z-index: 10000;
  padding: 20px;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow: hidden;
}

.modal-md {
  max-width: 700px;
  width: 90vw;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
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

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  background: var(--bg-secondary);
}

/* Agreement modal sections */
.agreement-summary-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 20px;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.utilities-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.utility-item {
  font-size: 13px;
  padding: 4px 0;
}

.agreement-issues-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border-color);
}

.agreement-issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.agreement-issue-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--bg-secondary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}

.agreement-issue-row:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent-primary);
}

.issue-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.issue-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'SF Mono', Monaco, monospace;
}

.agreement-optimality-section {
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.optimality-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.optimality-card {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
  gap: 6px;
}

.optimality-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
}

.optimality-value {
  font-size: 20px;
  font-weight: 700;
}

/* Calculate Stats Button */
.calculate-stats-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.calculate-stats-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner-small {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

