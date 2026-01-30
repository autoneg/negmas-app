<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay active" @click.self="$emit('close')">
      <div class="modal data-modal">
        <div class="modal-header">
          <h3>{{ title }}</h3>
          <div class="header-info">
            <span v-if="rowData.length > 0" class="row-count">{{ rowData.length }} rows</span>
          </div>
          <button class="modal-close" @click="$emit('close')">×</button>
        </div>
        
        <div class="modal-body">
          <!-- Loading -->
          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <span>Loading data...</span>
          </div>
          
          <!-- Error -->
          <div v-else-if="error" class="error-state">
            <span class="error-icon">⚠️</span>
            <span>{{ error }}</span>
          </div>
          
          <!-- Data Table -->
          <div v-else-if="rowData.length > 0" class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in columns" :key="col.field" @click="sortBy(col.field)" class="sortable">
                    {{ col.headerName }}
                    <span v-if="sortField === col.field" class="sort-indicator">
                      {{ sortDirection === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in paginatedData" :key="idx">
                  <td v-for="col in columns" :key="col.field" :class="col.cellClass">
                    {{ formatCell(row[col.field], col) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- Empty state -->
          <div v-else class="empty-state">
            <span>No data available</span>
          </div>
          
          <!-- Pagination -->
          <div v-if="rowData.length > 0" class="pagination">
            <button class="btn btn-sm" @click="currentPage = 1" :disabled="currentPage === 1">First</button>
            <button class="btn btn-sm" @click="currentPage--" :disabled="currentPage === 1">Prev</button>
            <span class="page-info">Page {{ currentPage }} of {{ totalPages }} ({{ rowData.length }} rows)</span>
            <button class="btn btn-sm" @click="currentPage++" :disabled="currentPage >= totalPages">Next</button>
            <button class="btn btn-sm" @click="currentPage = totalPages" :disabled="currentPage >= totalPages">Last</button>
            <select v-model="pageSize" class="page-size-select">
              <option :value="25">25 per page</option>
              <option :value="50">50 per page</option>
              <option :value="100">100 per page</option>
              <option :value="250">250 per page</option>
            </select>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="exportCsv" :disabled="rowData.length === 0">
            Export CSV
          </button>
          <button class="btn btn-secondary" @click="$emit('close')">Close</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  tournamentId: { type: String, required: true },
  title: { type: String, default: 'Tournament Data' },
  dataType: { type: String, default: 'details' }, // 'details' or 'all_scores'
  defaultColumns: { type: Array, default: () => [] }
})

const emit = defineEmits(['close'])

// State
const loading = ref(false)
const error = ref(null)
const rowData = ref([])
const columns = ref([])
const currentPage = ref(1)
const pageSize = ref(50)
const sortField = ref(null)
const sortDirection = ref('asc')

// Computed
const totalPages = computed(() => Math.ceil(rowData.value.length / pageSize.value))

const sortedData = computed(() => {
  if (!sortField.value) return rowData.value
  
  return [...rowData.value].sort((a, b) => {
    const aVal = a[sortField.value]
    const bVal = b[sortField.value]
    
    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1
    
    let comparison = 0
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      comparison = aVal - bVal
    } else {
      comparison = String(aVal).localeCompare(String(bVal))
    }
    
    return sortDirection.value === 'asc' ? comparison : -comparison
  })
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return sortedData.value.slice(start, start + pageSize.value)
})

// Methods
function sortBy(field) {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDirection.value = 'asc'
  }
}

function formatColumnName(col) {
  return col.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function getColumnDef(key, sampleValue) {
  const baseDef = {
    field: key,
    headerName: formatColumnName(key),
    cellClass: ''
  }
  
  // Numeric columns
  const numericCols = ['step', 'time', 'utility', 'advantage', 'welfare', 'reserved_value', 
    'nash_optimality', 'kalai_optimality', 'ks_optimality', 'max_welfare_optimality', 
    'pareto_optimality', 'partner_welfare', 'count']
  
  if (numericCols.some(n => key.toLowerCase().includes(n)) || typeof sampleValue === 'number') {
    return { ...baseDef, type: 'number', cellClass: 'numeric-cell' }
  }
  
  // Boolean columns
  if (['broken', 'timedout', 'has_error', 'has_agreement', 'running', 'waiting', 'started'].includes(key)) {
    return { ...baseDef, type: 'boolean', cellClass: 'boolean-cell' }
  }
  
  // Object/array columns
  if (typeof sampleValue === 'object' && sampleValue !== null) {
    return { ...baseDef, type: 'object' }
  }
  
  return baseDef
}

function formatCell(value, col) {
  if (value === null || value === undefined) return '-'
  
  if (col.type === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  
  if (col.type === 'number' && typeof value === 'number') {
    return Number.isInteger(value) ? value : value.toFixed(4)
  }
  
  if (col.type === 'object') {
    return JSON.stringify(value)
  }
  
  return value
}

function exportCsv() {
  if (rowData.value.length === 0) return
  
  const headers = columns.value.map(c => c.field)
  const csvContent = [
    headers.join(','),
    ...rowData.value.map(row => 
      headers.map(h => {
        const val = row[h]
        if (val === null || val === undefined) return ''
        if (typeof val === 'object') return `"${JSON.stringify(val).replace(/"/g, '""')}"`
        if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
          return `"${val.replace(/"/g, '""')}"`
        }
        return val
      }).join(',')
    )
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.tournamentId}_${props.dataType}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

// Load data from API
async function loadData() {
  if (!props.tournamentId) return
  
  loading.value = true
  error.value = null
  rowData.value = []
  columns.value = []
  currentPage.value = 1
  sortField.value = null
  
  try {
    const endpoint = props.dataType === 'all_scores' 
      ? `/api/tournament/saved/${props.tournamentId}/all_scores`
      : `/api/tournament/saved/${props.tournamentId}/details`
    
    const response = await fetch(endpoint)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const result = await response.json()
    
    // Details endpoint returns {details: [...]}, all_scores returns {scores: [...]}
    const rows = result.details || result.scores || []
    
    // Generate column definitions from first row
    if (rows.length > 0) {
      const firstRow = rows[0]
      const allKeys = Object.keys(firstRow)
      
      // Order columns: default columns first, then rest
      let orderedKeys = []
      if (props.defaultColumns.length > 0) {
        orderedKeys = props.defaultColumns.filter(k => allKeys.includes(k))
        orderedKeys = [...orderedKeys, ...allKeys.filter(k => !orderedKeys.includes(k))]
      } else {
        orderedKeys = allKeys
      }
      
      columns.value = orderedKeys.map(key => getColumnDef(key, firstRow[key]))
    }
    
    rowData.value = rows
  } catch (e) {
    console.error('[TournamentDataModal] Failed to load data:', e)
    error.value = 'Failed to load data'
  } finally {
    loading.value = false
  }
}

// Watch for show changes
watch(() => props.show, (newShow) => {
  if (newShow) {
    loadData()
  }
})

// Reset page when page size changes
watch(pageSize, () => {
  currentPage.value = 1
})

// Load on mount if already visible
onMounted(() => {
  if (props.show) {
    loadData()
  }
})
</script>

<style scoped>
.data-modal {
  max-width: 1400px;
  width: 95%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.modal-header h3 {
  flex: 1;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.row-count {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 4px 8px;
  border-radius: 4px;
}

.modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 16px;
  min-height: 0;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  color: var(--text-secondary);
}

.error-state {
  color: var(--danger);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.table-container {
  flex: 1;
  overflow: auto;
  min-height: 0;
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: var(--font-mono);
}

.data-table th,
.data-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.data-table th {
  position: sticky;
  top: 0;
  background: var(--bg-secondary);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-secondary);
  z-index: 1;
}

.data-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.data-table th.sortable:hover {
  background: var(--bg-hover);
}

.sort-indicator {
  margin-left: 4px;
  font-size: 10px;
}

.data-table tbody tr:hover {
  background: var(--bg-hover);
}

.data-table tbody tr:nth-child(even) {
  background: var(--bg-tertiary);
}

.data-table tbody tr:nth-child(even):hover {
  background: var(--bg-hover);
}

.numeric-cell {
  text-align: right !important;
}

.boolean-cell {
  text-align: center !important;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0 0 0;
  border-top: 1px solid var(--border-color);
  margin-top: 12px;
}

.page-info {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 0 12px;
}

.page-size-select {
  padding: 4px 8px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  margin-left: 8px;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.modal-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
