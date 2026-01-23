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
        <span class="result-state-badge agreement">Agreement</span>
        <span 
          v-for="(value, key) in negotiation.agreement" 
          :key="key"
          class="result-item"
        >
          <span class="text-muted">{{ key }}</span>=<strong>{{ value }}</strong>
        </span>
        <span class="result-separator">→</span>
        <span 
          v-for="(util, idx) in (negotiation.final_utilities || [])" 
          :key="idx"
          class="result-utility-labeled" 
          :style="{ color: negotiation?.negotiator_colors?.[idx] || 'var(--primary)' }"
        >
          <span class="utility-name">{{ (negotiation?.negotiator_names?.[idx] || '').substring(0, 3) }}</span>
          <span>{{ util.toFixed(3) }}</span>
        </span>
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

const emit = defineEmits(['saveResults'])

// Collapse state
const collapsed = ref(false)
const showInteractive = ref(false)

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
</script>

<style>
/* All styles are in panels.css - no additional styles needed */
</style>
