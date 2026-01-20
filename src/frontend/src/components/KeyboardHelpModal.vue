<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal help-modal">
      <div class="modal-header">
        <h2 class="modal-title">Keyboard Shortcuts</h2>
        <button class="modal-close" @click="$emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="modal-body">
        <div class="shortcuts-grid">
          <div class="shortcuts-section">
            <h3>Navigation</h3>
            <div class="shortcut-item" v-for="shortcut in navigationShortcuts" :key="shortcut.key">
              <kbd class="key">{{ shortcut.key }}</kbd>
              <span class="description">{{ shortcut.description }}</span>
            </div>
          </div>
          
          <div class="shortcuts-section">
            <h3>Actions</h3>
            <div class="shortcut-item" v-for="shortcut in actionShortcuts" :key="shortcut.key">
              <kbd class="key">{{ shortcut.key }}</kbd>
              <span class="description">{{ shortcut.description }}</span>
            </div>
          </div>
          
          <div class="shortcuts-section">
            <h3>General</h3>
            <div class="shortcut-item" v-for="shortcut in generalShortcuts" :key="shortcut.key">
              <kbd class="key">{{ shortcut.key }}</kbd>
              <span class="description">{{ shortcut.description }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="btn-secondary" @click="$emit('close')">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close'])

const navigationShortcuts = [
  { key: '1', description: 'Go to Negotiations' },
  { key: '2', description: 'Go to Tournaments' },
  { key: '3', description: 'Go to Scenarios' },
  { key: '4', description: 'Go to Negotiators' },
]

const actionShortcuts = [
  { key: 'N', description: 'New Negotiation' },
  { key: 'T', description: 'New Tournament' },
  { key: 'R', description: 'Refresh Current View' },
]

const generalShortcuts = [
  { key: 'S', description: 'Open Settings' },
  { key: '?', description: 'Show Keyboard Shortcuts' },
  { key: 'Esc', description: 'Close Modal/Panel' },
  { key: 'Cmd/Ctrl + ,', description: 'Open Settings' },
]
</script>

<style scoped>
.help-modal {
  max-width: 700px;
}

.shortcuts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}

.shortcuts-section h3 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.shortcut-item:last-child {
  border-bottom: none;
}

.key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 80px;
  padding: 6px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  text-align: center;
  box-shadow: 0 2px 0 var(--border-color);
}

.description {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
}

/* Responsive */
@media (max-width: 768px) {
  .shortcuts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
