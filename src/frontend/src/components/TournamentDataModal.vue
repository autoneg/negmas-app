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
          
          <!-- AG Grid Table -->
          <div v-else-if="rowData.length > 0" class="grid-container">
            <AgGridVue
              class="ag-theme-alpine-dark data-grid"
              :rowData="rowData"
              :columnDefs="columnDefs"
              :defaultColDef="defaultColDef"
              :pagination="true"
              :paginationPageSize="50"
              :paginationPageSizeSelector="[25, 50, 100, 250, 500]"
              :animateRows="true"
              :suppressCellFocus="true"
              :enableCellTextSelection="true"
              @grid-ready="onGridReady"
            />
          </div>
          
          <!-- Empty state -->
          <div v-else class="empty-state">
            <span>No data available</span>
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
import { AgGridVue } from 'ag-grid-vue3'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'

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
const gridApi = ref(null)

// AG Grid column definitions
const columnDefs = ref([])

// Default column settings
const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  floatingFilter: true,
  minWidth: 80,
  flex: 1,
}

// Column type formatters
function getColumnDef(key, sampleValue) {
  const baseDef = {
    field: key,
    headerName: formatColumnName(key),
  }
  
  // Numeric columns
  const numericCols = ['step', 'time', 'utility', 'advantage', 'welfare', 'reserved_value', 
    'nash_optimality', 'kalai_optimality', 'ks_optimality', 'max_welfare_optimality', 
    'pareto_optimality', 'partner_welfare', 'count']
  
  if (numericCols.some(n => key.toLowerCase().includes(n)) || typeof sampleValue === 'number') {
    return {
      ...baseDef,
      filter: 'agNumberColumnFilter',
      valueFormatter: (params) => {
        if (params.value === null || params.value === undefined) return '-'
        if (typeof params.value === 'number') {
          return Number.isInteger(params.value) ? params.value : params.value.toFixed(4)
        }
        return params.value
      },
      cellClass: 'numeric-cell',
    }
  }
  
  // Boolean columns
  if (['broken', 'timedout', 'has_error', 'has_agreement', 'running', 'waiting', 'started'].includes(key)) {
    return {
      ...baseDef,
      filter: 'agSetColumnFilter',
      valueFormatter: (params) => {
        if (params.value === true) return 'Yes'
        if (params.value === false) return 'No'
        return '-'
      },
      cellClass: 'boolean-cell',
      width: 80,
      flex: 0,
    }
  }
  
  // Object/array columns (like agreement, utilities)
  if (typeof sampleValue === 'object' && sampleValue !== null) {
    return {
      ...baseDef,
      valueFormatter: (params) => {
        if (params.value === null || params.value === undefined) return '-'
        return JSON.stringify(params.value)
      },
      tooltipValueGetter: (params) => {
        if (params.value === null || params.value === undefined) return ''
        return JSON.stringify(params.value, null, 2)
      },
    }
  }
  
  // Default text column
  return {
    ...baseDef,
    filter: 'agTextColumnFilter',
  }
}

function formatColumnName(col) {
  return col.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function onGridReady(params) {
  gridApi.value = params.api
  // Auto-size columns to fit content
  params.api.sizeColumnsToFit()
}

function exportCsv() {
  if (gridApi.value) {
    gridApi.value.exportDataAsCsv({
      fileName: `${props.tournamentId}_${props.dataType}.csv`
    })
  }
}

// Load data from API
async function loadData() {
  if (!props.tournamentId) return
  
  loading.value = true
  error.value = null
  
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
    rowData.value = rows
    
    // Generate column definitions from first row
    if (rows.length > 0) {
      const firstRow = rows[0]
      const allKeys = Object.keys(firstRow)
      
      // Order columns: default columns first, then rest
      let orderedKeys = []
      if (props.defaultColumns.length > 0) {
        // Add default columns that exist in data
        orderedKeys = props.defaultColumns.filter(k => allKeys.includes(k))
        // Add remaining columns
        orderedKeys = [...orderedKeys, ...allKeys.filter(k => !orderedKeys.includes(k))]
      } else {
        orderedKeys = allKeys
      }
      
      columnDefs.value = orderedKeys.map(key => getColumnDef(key, firstRow[key]))
    }
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

.grid-container {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.data-grid {
  width: 100%;
  height: 100%;
}

/* AG Grid theme overrides for dark mode */
.ag-theme-alpine-dark {
  --ag-background-color: var(--bg-primary);
  --ag-header-background-color: var(--bg-secondary);
  --ag-odd-row-background-color: var(--bg-primary);
  --ag-row-hover-color: var(--bg-hover);
  --ag-border-color: var(--border-color);
  --ag-header-foreground-color: var(--text-primary);
  --ag-foreground-color: var(--text-primary);
  --ag-secondary-foreground-color: var(--text-secondary);
  --ag-input-focus-border-color: var(--primary);
  --ag-range-selection-border-color: var(--primary);
  --ag-font-size: 12px;
  --ag-font-family: var(--font-mono);
}

.ag-theme-alpine-dark .ag-header-cell {
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
}

.ag-theme-alpine-dark .ag-cell {
  font-family: var(--font-mono);
}

:deep(.numeric-cell) {
  text-align: right !important;
  font-family: var(--font-mono);
}

:deep(.boolean-cell) {
  text-align: center !important;
}

.modal-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
