<template>
  <div 
    v-if="hasRunningNegotiations" 
    class="running-negotiations-panel"
  >
    <div class="panel-header">
      <h4>
        <span class="live-dot"></span>
        Running Negotiations
        <span class="count">({{ runningCount }})</span>
      </h4>
    </div>
    
    <div class="negotiations-grid">
      <div 
        v-for="[runId, neg] in runningNegotiationsArray" 
        :key="runId"
        class="neg-card"
      >
        <div class="neg-header">
          <span class="neg-id" :title="runId">{{ formatRunId(runId) }}</span>
          <span class="neg-step">Step {{ neg.step || 0 }}</span>
        </div>
        
        <div class="neg-progress">
          <div class="progress-bar-mini">
            <div 
              class="progress-fill-mini" 
              :style="{ width: formatProgress(neg.relative_time) }"
            ></div>
          </div>
          <span class="progress-text">{{ formatProgress(neg.relative_time) }}</span>
        </div>
        
        <div v-if="neg.current_offer" class="neg-offer">
          <span class="offer-label">Offer:</span>
          <span class="offer-value">{{ formatOffer(neg.current_offer) }}</span>
        </div>
        
        <div v-if="neg.current_proposer !== undefined" class="neg-proposer">
          <span class="proposer-label">By:</span>
          <span class="proposer-value">Agent {{ neg.current_proposer }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  runningNegotiations: {
    type: Map,
    default: () => new Map()
  }
})

const hasRunningNegotiations = computed(() => {
  return props.runningNegotiations && props.runningNegotiations.size > 0
})

const runningCount = computed(() => {
  return props.runningNegotiations?.size || 0
})

const runningNegotiationsArray = computed(() => {
  return Array.from(props.runningNegotiations.entries())
})

function formatRunId(runId) {
  if (!runId) return '-'
  const str = String(runId)
  if (str.length > 12) {
    return `#${str.slice(0, 8)}...`
  }
  return `#${str}`
}

function formatProgress(relativeTime) {
  if (relativeTime === undefined || relativeTime === null) return '0%'
  const percent = Math.round(relativeTime * 100)
  return `${Math.min(100, Math.max(0, percent))}%`
}

function formatOffer(offer) {
  if (!offer) return '-'
  if (Array.isArray(offer)) {
    if (offer.length > 3) {
      return `[${offer.slice(0, 3).join(', ')}, ...]`
    }
    return `[${offer.join(', ')}]`
  }
  return String(offer)
}
</script>

<style scoped>
.running-negotiations-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.panel-header {
  margin-bottom: 12px;
}

.panel-header h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: rgb(16, 185, 129);
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

.count {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 400;
}

.negotiations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}

.neg-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
}

.neg-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.neg-id {
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.neg-step {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
}

.neg-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.progress-bar-mini {
  flex: 1;
  height: 4px;
  background: var(--bg-primary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill-mini {
  height: 100%;
  background: rgb(16, 185, 129);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 35px;
  text-align: right;
}

.neg-offer {
  display: flex;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 11px;
}

.offer-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.offer-value {
  font-family: 'Monaco', 'Menlo', monospace;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.neg-proposer {
  display: flex;
  gap: 6px;
  font-size: 11px;
}

.proposer-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.proposer-value {
  color: var(--text-primary);
}
</style>
