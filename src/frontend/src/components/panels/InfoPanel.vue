<template>
  <!-- Negotiation Info Panel - Ultra Compact -->
  <div 
    class="panel panel-compact panel-info" 
    :class="{ 'collapsed': collapsed }"
  >
    <span class="panel-collapsed-label" v-show="collapsed">INFO</span>
    
    <!-- Floating Actions -->
    <div class="panel-floating-actions">
      <!-- Saved badge for saved negotiations -->
      <span v-if="negotiation?.isSaved" class="badge badge-xs badge-ghost" style="font-size: 9px;">
        SAVED
      </span>
      
      <!-- Start button for pending negotiations -->
      <button 
        v-if="negotiation?.pendingStart && !negotiation?.isSaved"
        class="panel-btn panel-btn-primary" 
        title="Start" 
        @click="$emit('start')"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
      </button>
      
      <!-- Pause/Resume and Cancel buttons for running negotiations -->
      <div 
        v-if="negotiation && !negotiation?.isSaved && !negotiation?.pendingStart && !negotiation?.agreement && !negotiation?.end_reason" 
        style="display: flex; gap: 2px;"
      >
        <button 
          class="panel-btn" 
          :title="negotiation?.paused ? 'Resume' : 'Pause'" 
          @click="$emit('togglePause')"
        >
          <svg v-if="!negotiation?.paused" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="4" width="4" height="16"></rect>
            <rect x="14" y="4" width="4" height="16"></rect>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
        </button>
        <button class="panel-btn" title="Cancel" @click="$emit('stop')">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <rect x="4" y="4" width="16" height="16" rx="2"></rect>
          </svg>
        </button>
      </div>
      
      <!-- Collapse button -->
      <button 
        class="panel-btn panel-collapse-btn" 
        title="Toggle panel" 
        @click="collapsed = !collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
      
      <!-- Stats button -->
      <button 
        class="panel-btn" 
        title="Scenario Stats" 
        @click="$emit('showStats')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/>
        </svg>
      </button>
    </div>
    
    <!-- Panel Content -->
    <div class="panel-content-ultra-compact" v-show="!collapsed">
      <!-- Row 1: Scenario + Status + Progress -->
      <div class="info-row">
        <span class="info-scenario">{{ negotiation?.scenario_name || 'Unknown' }}</span>
        <span 
          class="badge badge-xs" 
          :class="statusBadgeClass"
        >
          {{ statusText }}
        </span>
        <span class="info-stats">
          {{ negotiation?.step || 0 }}/{{ negotiation?.n_steps || '∞' }} steps
        </span>
        <span class="info-stats">
          {{ negotiation?.offers?.length || 0 }} offers
        </span>
        <div 
          class="info-progress" 
          v-show="!negotiation?.pendingStart && !negotiation?.agreement && !negotiation?.end_reason"
        >
          <div class="progress-mini">
            <div 
              class="progress-bar" 
              :style="{ width: Math.min(100, (negotiation?.relative_time || 0) * 100) + '%' }"
            ></div>
          </div>
        </div>
      </div>
      
      <!-- Row 2: Summary Section (when complete) -->
      <div v-if="showSummary" class="info-summary">
        <div class="summary-row">
          <span class="summary-label">Mechanism:</span>
          <span class="summary-value">SAO (Stacked Alternating Offers)</span>
        </div>
        <div class="summary-row" v-if="negotiation?.agreement">
          <span class="summary-label">Result:</span>
          <span class="summary-value success">Agreement Reached</span>
        </div>
        <div class="summary-row" v-else-if="negotiation?.end_reason">
          <span class="summary-label">Result:</span>
          <span class="summary-value">{{ endReasonText }}</span>
        </div>
        <div class="summary-row" v-if="negotiation?.final_utilities">
          <span class="summary-label">Utilities:</span>
          <span class="summary-value">{{ formatUtilities }}</span>
        </div>
        <div class="summary-row" v-if="negotiation?.n_steps">
          <span class="summary-label">Total Steps:</span>
          <span class="summary-value">{{ negotiation.step || 0 }} / {{ negotiation.n_steps }}</span>
        </div>
      </div>
      
      <!-- Row 3: ID (clickable to copy) -->
      <div class="info-row" v-show="negotiation?.id" style="font-size: 10px;">
        <span class="text-muted">ID:</span>
        <code 
          class="negotiation-id-display" 
          style="font-size: 10px; background: var(--bg-tertiary); padding: 1px 4px; border-radius: 3px; cursor: pointer; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
          :title="'Click to copy: ' + negotiation?.id"
          @click="copySessionId"
        >
          {{ negotiation?.id }}
        </code>
      </div>
      
      <!-- Row 4: Negotiators -->
      <div class="info-row info-row-negotiators">
        <span 
          v-for="(name, idx) in (negotiation?.negotiator_names || [])" 
          :key="idx"
          class="badge badge-xs" 
          :style="{ 
            background: negotiation?.negotiator_colors?.[idx] || 'var(--primary)', 
            color: 'white' 
          }"
        >
          {{ name }}
        </span>
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
  }
})

const emit = defineEmits(['start', 'togglePause', 'stop', 'showStats'])

// Collapse state
const collapsed = ref(false)

// Show summary section when negotiation is complete
const showSummary = computed(() => {
  if (!props.negotiation) return false
  return !!(props.negotiation.agreement || props.negotiation.end_reason)
})

// Computed status
const statusBadgeClass = computed(() => {
  if (!props.negotiation) return 'badge-neutral'
  if (props.negotiation.pendingStart) return 'badge-warning'
  if (props.negotiation.agreement) return 'badge-success'
  if (props.negotiation.end_reason) return 'badge-neutral'
  if (props.negotiation.paused) return 'badge-info'
  return 'badge-primary'
})

const statusText = computed(() => {
  if (!props.negotiation) return ''
  if (props.negotiation.pendingStart) return 'Pending'
  if (props.negotiation.agreement) return 'Done'
  if (props.negotiation.end_reason) return 'End'
  if (props.negotiation.paused) return 'Paused'
  return 'Running'
})

const endReasonText = computed(() => {
  if (!props.negotiation?.end_reason) return ''
  const reason = props.negotiation.end_reason
  if (reason === 'timedout') return 'Timeout (No Agreement)'
  if (reason === 'maxsteps') return 'Max Steps (No Agreement)'
  return reason.charAt(0).toUpperCase() + reason.slice(1)
})

const formatUtilities = computed(() => {
  if (!props.negotiation?.final_utilities) return 'N/A'
  return props.negotiation.final_utilities
    .map((u, idx) => {
      const name = props.negotiation.negotiator_names?.[idx] || `A${idx + 1}`
      return `${name.substring(0, 6)}: ${u.toFixed(3)}`
    })
    .join(', ')
})

// Copy session ID to clipboard
async function copySessionId() {
  if (!props.negotiation?.id) return
  
  try {
    await navigator.clipboard.writeText(props.negotiation.id)
    // TODO: Show toast notification
    console.log('Session ID copied to clipboard')
  } catch (err) {
    console.error('Failed to copy session ID:', err)
  }
}
</script>

<style scoped>
.info-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  margin: 4px 0;
  font-size: 11px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.summary-label {
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.summary-value {
  color: var(--text-primary);
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.summary-value.success {
  color: var(--success-color);
  font-weight: 600;
}
</style>
