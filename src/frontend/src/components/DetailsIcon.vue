<template>
  <button 
    class="details-icon-btn" 
    :class="{ 'details-icon-small': small }"
    @click.stop="$emit('click')"
    :title="title"
  >
    <!-- File tree / hierarchy icon -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 3h6v6H3z"/>
      <path d="M14 4h7"/>
      <path d="M14 9h7"/>
      <path d="M14 14h7"/>
      <path d="M14 19h7"/>
      <path d="M6 9v10"/>
      <path d="M6 14h4"/>
      <path d="M6 19h4"/>
    </svg>
  </button>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: 'View details'
  },
  small: {
    type: Boolean,
    default: false
  }
})

defineEmits(['click'])
</script>

<style>
/* Non-scoped styles for use anywhere */
.details-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 3px;
  background: var(--bg-tertiary, #e9ecef);
  border: 1px solid var(--border-color, #dee2e6);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary, #666);
  flex-shrink: 0;
}

.details-icon-btn:hover {
  background: var(--accent-primary, #007bff);
  border-color: var(--accent-primary, #007bff);
  color: white;
}

.details-icon-btn svg {
  width: 14px;
  height: 14px;
}

.details-icon-btn.details-icon-small {
  width: 18px;
  height: 18px;
  padding: 2px;
}

.details-icon-btn.details-icon-small svg {
  width: 12px;
  height: 12px;
}
</style>
