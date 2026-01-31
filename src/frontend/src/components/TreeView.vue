<template>
  <div class="tree-view" :class="{ 'tree-view-root': isRoot }">
    <!-- Primitive value -->
    <div v-if="isPrimitive" class="tree-node tree-leaf">
      <span v-if="nodeKey !== null" class="tree-key">{{ nodeKey }}:</span>
      <span :class="['tree-value', valueClass]">{{ formattedValue }}</span>
    </div>
    
    <!-- Object or Array -->
    <div v-else class="tree-node tree-branch">
      <div 
        class="tree-header" 
        :class="{ expanded: isExpanded, clickable: true }"
        @click="toggle"
      >
        <span class="tree-toggle">{{ isExpanded ? '▼' : '▶' }}</span>
        <span v-if="nodeKey !== null" class="tree-key">{{ nodeKey }}:</span>
        <span class="tree-type-badge" v-if="typeLabel">{{ typeLabel }}</span>
        <span class="tree-summary" v-if="!isExpanded">{{ summary }}</span>
      </div>
      
      <div v-if="isExpanded" class="tree-children">
        <TreeView
          v-for="(child, key) in children"
          :key="key"
          :data="child"
          :node-key="isArray ? Number(key) : String(key)"
          :depth="depth + 1"
          :default-expand-depth="defaultExpandDepth"
          :type-field="typeField"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  // The data to display
  data: {
    type: [Object, Array, String, Number, Boolean, null],
    default: null
  },
  // Key name for this node (null for root)
  nodeKey: {
    type: [String, Number],
    default: null
  },
  // Current depth in the tree
  depth: {
    type: Number,
    default: 0
  },
  // How many levels to expand by default
  defaultExpandDepth: {
    type: Number,
    default: 2
  },
  // Field name used for type information
  typeField: {
    type: String,
    default: 'type'
  }
})

// Track if this node is expanded
const isExpanded = ref(false)

// Check if this is the root node
const isRoot = computed(() => props.depth === 0)

// Check if data is a primitive value
const isPrimitive = computed(() => {
  return props.data === null || 
         props.data === undefined ||
         typeof props.data !== 'object'
})

// Check if data is an array
const isArray = computed(() => Array.isArray(props.data))

// Get children for objects/arrays (excluding type field)
const children = computed(() => {
  if (isPrimitive.value) return {}
  
  if (isArray.value) {
    return props.data
  }
  
  // For objects, filter out the type field for cleaner display
  const result = {}
  for (const [key, value] of Object.entries(props.data)) {
    if (key !== props.typeField) {
      result[key] = value
    }
  }
  return result
})

// Get the type label from type field
const typeLabel = computed(() => {
  if (isPrimitive.value) return null
  if (isArray.value) return `Array(${props.data.length})`
  
  const typeValue = props.data[props.typeField]
  if (!typeValue) return null
  
  // Shorten negmas type names for display
  if (typeof typeValue === 'string') {
    // Extract just the class name from full path
    const parts = typeValue.split('.')
    return parts[parts.length - 1]
  }
  return String(typeValue)
})

// Generate a summary for collapsed nodes
const summary = computed(() => {
  if (isPrimitive.value) return ''
  
  if (isArray.value) {
    if (props.data.length === 0) return '[]'
    if (props.data.length <= 3 && props.data.every(v => typeof v !== 'object' || v === null)) {
      return `[${props.data.map(formatPrimitive).join(', ')}]`
    }
    return `[${props.data.length} items]`
  }
  
  const keys = Object.keys(children.value)
  if (keys.length === 0) return '{}'
  if (keys.length <= 3) {
    return `{ ${keys.join(', ')} }`
  }
  return `{ ${keys.length} properties }`
})

// Get CSS class for value type
const valueClass = computed(() => {
  if (props.data === null || props.data === undefined) return 'value-null'
  if (typeof props.data === 'boolean') return 'value-boolean'
  if (typeof props.data === 'number') return 'value-number'
  if (typeof props.data === 'string') return 'value-string'
  return ''
})

// Format the displayed value
const formattedValue = computed(() => {
  return formatPrimitive(props.data)
})

function formatPrimitive(value) {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') {
    // Format floats nicely
    if (!Number.isInteger(value) && Math.abs(value) < 1000000) {
      return value.toFixed(6).replace(/\.?0+$/, '')
    }
    return String(value)
  }
  if (typeof value === 'string') {
    // Truncate long strings
    if (value.length > 100) {
      return `"${value.substring(0, 100)}..."`
    }
    return `"${value}"`
  }
  return String(value)
}

function toggle() {
  isExpanded.value = !isExpanded.value
}

// Auto-expand based on depth on mount
onMounted(() => {
  if (props.depth < props.defaultExpandDepth) {
    isExpanded.value = true
  }
})
</script>

<style scoped>
.tree-view {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  line-height: 1.5;
}

.tree-view-root {
  padding: 8px;
}

.tree-node {
  margin-left: 0;
}

.tree-branch > .tree-children {
  margin-left: 16px;
  padding-left: 8px;
  border-left: 1px solid var(--border-color, #e0e0e0);
}

.tree-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  border-radius: 3px;
  cursor: pointer;
  user-select: none;
}

.tree-header:hover {
  background: var(--bg-hover, rgba(0, 0, 0, 0.05));
}

.tree-header.clickable {
  cursor: pointer;
}

.tree-leaf {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  padding-left: 20px; /* Align with branch content */
}

.tree-toggle {
  width: 12px;
  font-size: 10px;
  color: var(--text-secondary, #666);
  flex-shrink: 0;
}

.tree-key {
  color: var(--text-primary, #333);
  font-weight: 500;
}

.tree-value {
  color: var(--text-secondary, #666);
}

.tree-value.value-null {
  color: var(--color-null, #999);
  font-style: italic;
}

.tree-value.value-boolean {
  color: var(--color-boolean, #d73a49);
}

.tree-value.value-number {
  color: var(--color-number, #005cc5);
}

.tree-value.value-string {
  color: var(--color-string, #22863a);
}

.tree-type-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--accent-primary, #007bff);
  color: white;
  font-weight: 500;
  margin-left: 4px;
}

.tree-summary {
  color: var(--text-tertiary, #999);
  font-size: 11px;
  margin-left: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

/* Dark mode adjustments */
:root[data-theme="dark"] .tree-view,
.dark .tree-view {
  --text-primary: #e0e0e0;
  --text-secondary: #b0b0b0;
  --text-tertiary: #808080;
  --bg-hover: rgba(255, 255, 255, 0.05);
  --border-color: #404040;
  --color-null: #6a737d;
  --color-boolean: #f97583;
  --color-number: #79b8ff;
  --color-string: #85e89d;
}
</style>
