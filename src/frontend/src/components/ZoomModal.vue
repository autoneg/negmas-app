<template>
  <!-- Zoom Modal - Fullscreen Panel View -->
  <div v-if="show" class="modal-overlay modal-fullscreen" @click.self="$emit('close')">
    <div class="modal-content modal-zoom">
      <!-- Header -->
      <div class="modal-header" style="padding: 12px 16px; border-bottom: 1px solid var(--border-color);">
        <h3 class="modal-title" style="font-size: 16px; margin: 0;">{{ title }}</h3>
        <button class="modal-close-btn" @click="$emit('close')" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <!-- Body - Full panel content -->
      <div class="modal-body" style="flex: 1; padding: 0; overflow: hidden;">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Panel'
  }
})

const emit = defineEmits(['close'])
</script>

<style scoped>
.modal-fullscreen {
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
}

.modal-zoom {
  width: 95vw;
  height: 95vh;
  max-width: none;
  max-height: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.modal-zoom .modal-body {
  overflow: hidden;
  position: relative;
}
</style>
