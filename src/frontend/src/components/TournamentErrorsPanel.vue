<template>
  <div class="tournament-errors-pane" :class="{ collapsed: isCollapsed }">
    <div class="tournament-panel-header" @click="isCollapsed = !isCollapsed">
      <h3>
        <svg 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="2" 
          width="14" 
          height="14" 
          :style="{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
        <span>Failed Negotiations</span>
        <span v-if="errors.length > 0" class="error-badge">{{ errors.length }}</span>
      </h3>
    </div>
    
    <div class="tournament-panel-content" v-show="!isCollapsed">
      <!-- Empty state -->
      <div v-if="errors.length === 0" class="empty-state-mini">
        <p>{{ status === 'completed' ? 'No errors occurred' : 'No errors yet' }}</p>
      </div>
      
      <!-- Error list -->
      <div v-else class="errors-list">
        <div
          v-for="(error, idx) in errors"
          :key="idx"
          class="error-entry"
        >
          <div class="error-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
          </div>
          <div class="error-details">
            <div class="error-participants">
              <strong>{{ error.partners.join(' vs ') }}</strong>
              <span class="error-scenario">{{ getScenarioName(error.scenario) }}</span>
            </div>
            <div class="error-message">{{ error.error || 'Unknown error' }}</div>
            <div class="error-meta">
              Step {{ error.n_steps || 0 }} • {{ formatTime(error.timestamp) }}
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
  errors: {
    type: Array,
    default: () => []
  },
  status: {
    type: String,
    default: 'running'
  }
})

const isCollapsed = ref(false)

function getScenarioName(path) {
  if (!path) return 'Unknown'
  return path.split('/').pop()
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}
</script>

<style scoped>
.tournament-errors-pane {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.tournament-errors-pane.collapsed .tournament-panel-content {
  display: none;
}

.tournament-panel-header {
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.tournament-panel-header:hover {
  background: var(--bg-hover);
}

.tournament-panel-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-badge {
  background: var(--color-error);
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.tournament-panel-content {
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.empty-state-mini {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary);
  font-size: 13px;
}

.errors-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-entry {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 6px;
  transition: all 0.2s;
}

.error-entry:hover {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.3);
}

.error-icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  color: var(--color-error);
  margin-top: 2px;
}

.error-details {
  flex: 1;
  min-width: 0;
}

.error-participants {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.error-participants strong {
  font-size: 13px;
  color: var(--text-primary);
}

.error-scenario {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
}

.error-message {
  font-size: 12px;
  color: var(--text-primary);
  margin-bottom: 4px;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  line-height: 1.4;
  word-break: break-word;
}

.error-meta {
  font-size: 11px;
  color: var(--text-secondary);
}
</style>
