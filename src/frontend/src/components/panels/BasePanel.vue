<template>
  <div 
    class="panel panel-compact" 
    :class="{ 'collapsed': collapsed }"
    :ref="panelRef"
  >
    <!-- Collapsed label (shown when panel is collapsed) -->
    <span v-if="collapsed" class="panel-collapsed-label">{{ collapsedLabel }}</span>
    
    <!-- Floating actions (top-right buttons) -->
    <div class="panel-floating-actions" :class="actionsPosition === 'left' ? 'panel-floating-actions-left' : ''">
      <!-- Custom action buttons slot (before default buttons) -->
      <slot name="actions"></slot>
      
      <!-- Download button -->
      <button 
        v-if="showDownload && !collapsed"
        class="panel-btn" 
        title="Save as Image" 
        @click="handleDownload"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </button>
      
      <!-- Zoom button -->
      <button 
        v-if="showZoom && !collapsed"
        class="panel-btn" 
        title="Zoom" 
        @click="handleZoom"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <polyline points="15 3 21 3 21 9"/>
          <polyline points="9 21 3 21 3 15"/>
          <line x1="21" y1="3" x2="14" y2="10"/>
          <line x1="3" y1="21" x2="10" y2="14"/>
        </svg>
      </button>
      
      <!-- Refresh button -->
      <button 
        v-if="showRefresh && !collapsed"
        class="panel-btn" 
        title="Refresh" 
        @click="$emit('refresh')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
        </svg>
      </button>
      
      <!-- Collapse toggle button -->
      <button 
        v-if="collapsible"
        class="panel-btn panel-collapse-btn" 
        title="Toggle panel" 
        @click="toggleCollapse"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>
    </div>
    
    <!-- Panel content -->
    <div 
      v-show="!collapsed" 
      class="panel-content panel-content-compact"
      :style="contentStyle"
    >
      <!-- Default slot for panel content -->
      <slot></slot>
      
      <!-- Loading state -->
      <div v-if="loading" class="empty-state-mini">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="24" height="24" style="opacity: 0.4;">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
        <span class="text-muted">Loading...</span>
      </div>
      
      <!-- Empty state -->
      <div v-else-if="empty" class="empty-state-mini">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="24" height="24" style="opacity: 0.4;">
          <circle cx="12" cy="12" r="10"/>
        </svg>
        <span class="text-muted">{{ emptyMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  // Panel title for collapsed label
  title: {
    type: String,
    required: true,
  },
  
  // Custom collapsed label (defaults to title)
  collapsedLabel: {
    type: String,
    default: null,
  },
  
  // Position of action buttons
  actionsPosition: {
    type: String,
    default: 'right', // 'right' or 'left'
  },
  
  // Show/hide action buttons
  showDownload: {
    type: Boolean,
    default: true,
  },
  showZoom: {
    type: Boolean,
    default: true,
  },
  showRefresh: {
    type: Boolean,
    default: false,
  },
  collapsible: {
    type: Boolean,
    default: true,
  },
  
  // Panel state
  initiallyCollapsed: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  empty: {
    type: Boolean,
    default: false,
  },
  emptyMessage: {
    type: String,
    default: 'No data',
  },
  
  // Content styling
  contentStyle: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['collapse', 'zoom', 'download', 'refresh'])

const collapsed = ref(props.initiallyCollapsed)
const panelRef = ref(null)

const computedCollapsedLabel = computed(() => {
  return props.collapsedLabel || props.title.toUpperCase()
})

function toggleCollapse() {
  collapsed.value = !collapsed.value
  emit('collapse', collapsed.value)
}

function handleZoom() {
  emit('zoom', {
    title: props.title,
    panelRef: panelRef.value,
  })
}

function handleDownload() {
  emit('download', {
    title: props.title,
    panelRef: panelRef.value,
  })
}

// Expose methods for parent components
defineExpose({
  collapse: () => { collapsed.value = true },
  expand: () => { collapsed.value = false },
  toggle: toggleCollapse,
})
</script>

<style>
/* Panel base styles */
.panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.panel-compact {
  min-height: 48px;
}

.panel.collapsed {
  min-height: 24px;
  max-height: 24px;
  cursor: pointer;
}

.panel-collapsed-label {
  position: absolute;
  top: 50%;
  left: 8px;
  transform: translateY(-50%);
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  pointer-events: none;
}

/* Floating actions */
.panel-floating-actions {
  position: absolute;
  top: 4px;
  right: 4px;
  display: flex;
  gap: 2px;
  z-index: 10;
}

.panel-floating-actions-left {
  left: 4px;
  right: auto;
}

.panel-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text-secondary);
}

.panel-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
  border-color: var(--primary);
}

.panel-btn:active {
  transform: scale(0.95);
}

.panel-btn svg {
  width: 12px;
  height: 12px;
}

.panel-collapse-btn svg {
  transition: transform 0.2s;
}

.collapsed .panel-collapse-btn svg {
  transform: rotate(-90deg);
}

/* Panel content */
.panel-content {
  flex: 1;
  overflow: auto;
  padding: 12px;
  position: relative;
}

.panel-content-compact {
  padding: 8px;
}

/* Empty state */
.empty-state-mini {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--bg-secondary);
}

.empty-state-mini svg {
  width: 24px;
  height: 24px;
  opacity: 0.4;
}

.empty-state-mini .text-muted {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
