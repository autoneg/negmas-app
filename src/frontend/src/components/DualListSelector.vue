<template>
  <div class="dual-list-container">
    <!-- Available items (left panel) -->
    <div class="dual-list-panel">
      <div class="dual-list-header">
        <div class="header-title">
          Available
          <span class="count-badge">{{ availableItems.length }}</span>
        </div>
        
        <!-- Search input -->
        <input 
          v-if="searchable"
          v-model="searchQuery"
          type="text" 
          class="form-input"
          :placeholder="searchPlaceholder"
        />
        
        <!-- Slot for custom filters (source, tags, advanced filters, etc.) -->
        <slot name="filters" :search="searchQuery"></slot>
      </div>
      
      <div class="dual-list-items">
        <div
          v-for="item in availableItems"
          :key="getItemKey(item)"
          class="dual-list-item"
          @click="addItem(item)"
        >
          <slot name="available-item" :item="item">
            <div class="item-content">
              <div class="item-name">{{ getItemLabel(item) }}</div>
            </div>
          </slot>
        </div>
        
        <div v-if="availableItems.length === 0" class="empty-state">
          No available items
        </div>
      </div>
      
      <div class="dual-list-footer">
        <button 
          class="btn btn-sm btn-secondary full-width" 
          @click="addAllAvailable"
          :disabled="availableItems.length === 0"
        >
          Add All Filtered
          <span>({{ availableItems.length }})</span>
        </button>
      </div>
    </div>
    
    <!-- Transfer buttons (center) -->
    <div class="transfer-buttons">
      <button 
        class="btn btn-sm btn-secondary transfer-btn" 
        @click="addAllAvailable"
        :disabled="availableItems.length === 0"
        title="Add all filtered"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <polyline points="13 17 18 12 13 7"></polyline>
          <polyline points="6 17 11 12 6 7"></polyline>
        </svg>
      </button>
      <button 
        class="btn btn-sm btn-secondary transfer-btn" 
        @click="removeAll"
        :disabled="selectedItems.length === 0"
        title="Remove all"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <polyline points="11 17 6 12 11 7"></polyline>
          <polyline points="18 17 13 12 18 7"></polyline>
        </svg>
      </button>
    </div>
    
    <!-- Selected items (right panel) -->
    <div class="dual-list-panel">
      <div class="dual-list-header">
        <div class="header-title">
          Selected
          <span class="badge badge-primary">{{ selectedItems.length }}</span>
        </div>
      </div>
      
      <div class="dual-list-items">
        <div
          v-for="item in selectedItems"
          :key="getItemKey(item)"
          class="dual-list-item selected"
        >
          <slot name="selected-item" :item="item" :remove="() => removeItem(item)">
            <div class="item-content">
              <div class="item-name">{{ getItemLabel(item) }}</div>
            </div>
            <button 
              class="btn-remove" 
              @click.stop="removeItem(item)"
              title="Remove"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </slot>
        </div>
        
        <div v-if="selectedItems.length === 0" class="empty-state">
          No items selected<br>
          <span class="empty-hint">Click items on the left or use "Add All Filtered"</span>
        </div>
      </div>
      
      <div class="dual-list-footer">
        <button 
          class="btn btn-sm btn-secondary full-width" 
          @click="removeAll"
          :disabled="selectedItems.length === 0"
        >
          Clear All
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  // All available items
  items: {
    type: Array,
    required: true
  },
  // Currently selected items (v-model)
  modelValue: {
    type: Array,
    default: () => []
  },
  // Function to get unique key from item
  itemKey: {
    type: [String, Function],
    default: 'id'
  },
  // Function to get display label from item
  itemLabel: {
    type: [String, Function],
    default: 'name'
  },
  // Enable search
  searchable: {
    type: Boolean,
    default: true
  },
  // Search placeholder
  searchPlaceholder: {
    type: String,
    default: 'Search...'
  },
  // Custom filter function (receives item and searchQuery)
  filterFn: {
    type: Function,
    default: null
  }
})

// Debug: watch items prop
watch(() => props.items, (newItems) => {
  console.log('[DualListSelector] Items changed:', {
    length: newItems?.length,
    sample: newItems?.slice(0, 2)
  })
}, { immediate: true })

const emit = defineEmits(['update:modelValue', 'add', 'remove', 'add-all', 'remove-all'])

const searchQuery = ref('')

// Helper to get item key
const getItemKey = (item) => {
  if (typeof props.itemKey === 'function') {
    return props.itemKey(item)
  }
  return item[props.itemKey]
}

// Helper to get item label
const getItemLabel = (item) => {
  if (typeof props.itemLabel === 'function') {
    return props.itemLabel(item)
  }
  return item[props.itemLabel]
}

// Check if item is selected
const isSelected = (item) => {
  const key = getItemKey(item)
  return props.modelValue.some(selected => getItemKey(selected) === key)
}

// Get selected items as full objects
const selectedItems = computed(() => {
  return props.items.filter(item => isSelected(item))
})

// Get available (not selected) items
const availableItems = computed(() => {
  let items = props.items.filter(item => !isSelected(item))
  
  // Apply custom filter or default search
  if (props.filterFn) {
    items = items.filter(item => props.filterFn(item, searchQuery.value))
  } else if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    items = items.filter(item => {
      const label = getItemLabel(item).toLowerCase()
      return label.includes(query)
    })
  }
  
  return items
})

// Add single item
const addItem = (item) => {
  if (!isSelected(item)) {
    const newValue = [...props.modelValue, item]
    emit('update:modelValue', newValue)
    emit('add', item)
  }
}

// Remove single item
const removeItem = (item) => {
  const key = getItemKey(item)
  const newValue = props.modelValue.filter(selected => getItemKey(selected) !== key)
  emit('update:modelValue', newValue)
  emit('remove', item)
}

// Add all available (filtered) items
const addAllAvailable = () => {
  const newItems = availableItems.value.filter(item => !isSelected(item))
  if (newItems.length > 0) {
    const newValue = [...props.modelValue, ...newItems]
    emit('update:modelValue', newValue)
    emit('add-all', newItems)
  }
}

// Remove all selected items
const removeAll = () => {
  if (props.modelValue.length > 0) {
    emit('update:modelValue', [])
    emit('remove-all')
  }
}
</script>

<style scoped>
.dual-list-container {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 12px;
  height: 450px;
}

.dual-list-panel {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-primary);
}

.dual-list-header {
  padding: 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.header-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.count-badge {
  font-weight: normal;
  color: var(--text-muted);
  font-size: 12px;
}

.form-input {
  width: 100%;
  font-size: 13px;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.form-input::placeholder {
  color: var(--text-muted);
}

.dual-list-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.dual-list-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  background: var(--bg-tertiary);
  transition: background 0.15s ease;
}

.dual-list-item:hover {
  background: var(--bg-hover);
}

.dual-list-item.selected {
  background: var(--primary-bg);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dual-list-item.selected:hover {
  background: var(--bg-hover);
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-remove {
  padding: 4px;
  margin-left: 8px;
  background: transparent;
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}

.btn-remove:hover {
  background: var(--danger-bg);
  color: var(--danger);
}

.empty-state {
  text-align: center;
  padding: 20px;
  font-size: 13px;
  color: var(--text-muted);
}

.empty-hint {
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.8;
}

.dual-list-footer {
  padding: 8px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.full-width {
  width: 100%;
}

.transfer-buttons {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.transfer-btn {
  padding: 8px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--primary);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  font-size: 11px;
  padding: 4px 8px;
}

.btn-secondary {
  background: var(--bg-secondary);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.badge-primary {
  background: var(--primary-bg);
  color: var(--primary);
}
</style>
