<template>
  <!-- Zoomed panel overlay -->
  <Teleport to="body">
    <div 
      v-if="show" 
      class="panel-zoom-overlay" 
      @click.self="$emit('close')" 
      style="position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px;"
    >
      <div class="panel" style="width: 90vw; height: 90vh; max-width: none;">
        <div class="panel-header">
          <span class="panel-title">{{ title }}</span>
          <div class="panel-actions">
            <button class="panel-btn" title="Close" @click="$emit('close')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>
        <div class="panel-content" style="padding: 0; position: relative; height: calc(100% - 48px);">
          <slot></slot>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Panel'
  }
})

defineEmits(['close'])
</script>

<style>
/* All styles are in panels.css - no additional styles needed */
</style>
