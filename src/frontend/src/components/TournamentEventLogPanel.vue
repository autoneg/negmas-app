<template>
  <div class="tournament-event-log-panel">
    <div class="panel-header">
      <h3 class="panel-title">Event Log</h3>
      <div class="panel-header-actions">
        <button 
          class="btn-icon-sm" 
          @click="autoscroll = !autoscroll"
          :title="autoscroll ? 'Disable auto-scroll' : 'Enable auto-scroll'"
        >
          <svg v-if="autoscroll" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="18 15 12 9 6 15"></polyline>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <polyline points="19 12 12 19 5 12"></polyline>
          </svg>
        </button>
        <button 
          class="btn-icon-sm" 
          @click="clearEvents"
          title="Clear event log"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="panel-body" ref="logContainer">
      <div v-if="events.length === 0" class="empty-state-sm">
        <p class="text-muted">No events yet</p>
      </div>
      
      <div v-else class="event-list">
        <div 
          v-for="event in events" 
          :key="event.id"
          class="event-item"
          :class="'event-' + event.type"
        >
          <span class="event-time">{{ formatTime(event.timestamp) }}</span>
          <span class="event-icon" :class="'icon-' + event.type">
            <svg v-if="event.type === 'started'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
            <svg v-else-if="event.type === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <svg v-else-if="event.type === 'failed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
            <svg v-else-if="event.type === 'agreement'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </span>
          <span class="event-message">{{ event.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  events: {
    type: Array,
    default: () => []
  }
})

const logContainer = ref(null)
const autoscroll = ref(true)

// Auto-scroll to bottom when new events arrive
watch(() => props.events.length, async () => {
  if (autoscroll.value && logContainer.value) {
    await nextTick()
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  })
}

function clearEvents() {
  // Emit event to parent to clear
  // For now, we'll just scroll to top
  if (logContainer.value) {
    logContainer.value.scrollTop = 0
  }
}
</script>

<style scoped>
.tournament-event-log-panel {
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
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.panel-header-actions {
  display: flex;
  gap: 4px;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-state-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 120px;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
  background: var(--bg-secondary);
  transition: background 0.15s;
}

.event-item:hover {
  background: var(--bg-tertiary);
}

.event-time {
  font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
  color: var(--text-muted);
  white-space: nowrap;
  font-size: 11px;
}

.event-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
}

.icon-started {
  background: var(--info-bg);
  color: var(--info-color);
}

.icon-completed {
  background: var(--success-bg);
  color: var(--success-color);
}

.icon-agreement {
  background: var(--success-bg);
  color: var(--success-color);
}

.icon-failed {
  background: var(--error-bg);
  color: var(--error-color);
}

.icon-info {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.event-message {
  flex: 1;
  color: var(--text-primary);
}

.event-started .event-message {
  color: var(--text-secondary);
}

.event-completed .event-message {
  color: var(--text-primary);
}

.event-failed .event-message {
  color: var(--error-color);
}
</style>
