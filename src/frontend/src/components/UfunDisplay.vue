<template>
  <div class="ufun-display">
    <div class="ufun-header">
      <span class="ufun-name">{{ ufun.name || `Utility Function ${index + 1}` }}</span>
      <span class="ufun-type-badge">{{ formatUfunType(ufun.type) }}</span>
    </div>
    
    <!-- Ufun details based on type -->
    <div class="ufun-details">
      <!-- Reserved Value -->
      <div v-if="hasReservedValue" class="ufun-detail-row">
        <span class="detail-label">Reserved:</span>
        <span class="detail-value">{{ formatNumber(getReservedValue()) }}</span>
      </div>
      
      <!-- For LinearAdditive: show weights -->
      <div v-if="hasWeights" class="ufun-detail-row">
        <span class="detail-label">Weights:</span>
        <span class="detail-value monospace">{{ formatWeights() }}</span>
      </div>
      
      <!-- For Discounted: show discount factor and base ufun type -->
      <div v-if="isDiscounted" class="ufun-detail-row">
        <span class="detail-label">Discount:</span>
        <span class="detail-value">{{ formatNumber(getDiscountFactor()) }}</span>
      </div>
      
      <div v-if="isDiscounted && baseUfunType" class="ufun-detail-row">
        <span class="detail-label">Base Type:</span>
        <span class="detail-value">{{ formatUfunType(baseUfunType) }}</span>
      </div>
      
      <!-- For any ufun with bias -->
      <div v-if="hasBias" class="ufun-detail-row">
        <span class="detail-label">Bias:</span>
        <span class="detail-value">{{ formatNumber(getBias()) }}</span>
      </div>
      
      <!-- Show file path if available -->
      <div v-if="ufun.file_path" class="ufun-detail-row">
        <span class="detail-label">File:</span>
        <span class="detail-value monospace small">{{ ufun.file_path }}</span>
      </div>
    </div>
    
    <!-- String representation fallback -->
    <div v-if="showStringRep && ufun.string_representation" class="ufun-string-rep">
      <pre>{{ ufun.string_representation }}</pre>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  ufun: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    default: 0
  },
  showStringRep: {
    type: Boolean,
    default: false
  },
  compact: {
    type: Boolean,
    default: false
  }
})

// Check if this is a discounted utility function
const isDiscounted = computed(() => {
  const type = props.ufun.type || ''
  return type.includes('Discount')
})

// Get base ufun type for discounted functions
const baseUfunType = computed(() => {
  // If string_representation contains "Base:", extract the type
  const rep = props.ufun.string_representation || ''
  const match = rep.match(/Base:\s*\(Type:\s*([^|)]+)/)
  if (match) return match[1].trim()
  return null
})

// Check for reserved value
const hasReservedValue = computed(() => {
  // Check in string_representation
  const rep = props.ufun.string_representation || ''
  if (rep.includes('Reserved:')) return true
  // Check direct property
  if (props.ufun.reserved_value !== undefined && props.ufun.reserved_value !== null) return true
  return false
})

// Get reserved value
function getReservedValue() {
  // Try direct property first
  if (props.ufun.reserved_value !== undefined && props.ufun.reserved_value !== null) {
    return props.ufun.reserved_value
  }
  // Extract from string_representation
  const rep = props.ufun.string_representation || ''
  const match = rep.match(/Reserved:\s*([\d.-]+)/)
  if (match) return parseFloat(match[1])
  return 0
}

// Check for weights
const hasWeights = computed(() => {
  const rep = props.ufun.string_representation || ''
  return rep.includes('Weights:')
})

// Format weights
function formatWeights() {
  const rep = props.ufun.string_representation || ''
  const match = rep.match(/Weights:\s*\[([^\]]+)\]/)
  if (match) {
    // Parse and format weights more compactly
    const weights = match[1].split(',').map(w => parseFloat(w.trim()))
    if (weights.length <= 4) {
      return '[' + weights.map(w => w.toFixed(3)).join(', ') + ']'
    }
    // Show first 3 and count for many weights
    return '[' + weights.slice(0, 3).map(w => w.toFixed(3)).join(', ') + `, ... (${weights.length})]`
  }
  return ''
}

// Check for bias
const hasBias = computed(() => {
  const rep = props.ufun.string_representation || ''
  return rep.includes('Bias:')
})

// Get bias
function getBias() {
  const rep = props.ufun.string_representation || ''
  const match = rep.match(/Bias:\s*([\d.-]+)/)
  if (match) return parseFloat(match[1])
  return 0
}

// Get discount factor
function getDiscountFactor() {
  const rep = props.ufun.string_representation || ''
  const match = rep.match(/Discount:\s*([\d.-]+)/)
  if (match) return parseFloat(match[1])
  return 1
}

// Format ufun type name
function formatUfunType(type) {
  if (!type) return 'Unknown'
  // Remove common suffixes
  return type
    .replace(/UtilityFunction$/, '')
    .replace(/UFun$/, '')
    .replace(/Ufun$/, '')
}

// Format number
function formatNumber(value, decimals = 3) {
  if (value === null || value === undefined) return 'N/A'
  const num = Number(value)
  if (isNaN(num)) return 'N/A'
  return num.toFixed(decimals)
}
</script>

<style scoped>
.ufun-display {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 10px 12px;
}

.ufun-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.ufun-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.ufun-type-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--accent-primary);
  color: white;
  font-weight: 500;
}

.ufun-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ufun-detail-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 3px 0;
  gap: 8px;
}

.ufun-detail-row:not(:last-child) {
  border-bottom: 1px solid var(--border-color);
}

.detail-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
}

.detail-value {
  font-size: 11px;
  color: var(--text-primary);
  font-weight: 500;
  text-align: right;
}

.detail-value.monospace {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 10px;
}

.detail-value.monospace.small {
  font-size: 9px;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ufun-string-rep {
  margin-top: 8px;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.ufun-string-rep pre {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 10px;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
