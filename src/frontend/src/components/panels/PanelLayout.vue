<template>
  <div class="panels-container panels-layout-compact">
    <!-- LEFT COLUMN -->
    <div 
      ref="leftColumn" 
      class="panels-column panels-column-left resizable-panels-column"
      :style="leftColumnStyle"
    >
      <slot name="left" :add-resize-handle="addResizeHandle"></slot>
    </div>

    <!-- Resize handle between columns -->
    <div 
      class="resize-handle-vertical" 
      :class="{ 'dragging': isDraggingColumn }"
      @mousedown="startColumnResize"
    ></div>

    <!-- RIGHT COLUMN -->
    <div 
      ref="rightColumn" 
      class="panels-column panels-column-right resizable-panels-column"
    >
      <slot name="right" :add-resize-handle="addResizeHandle"></slot>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch, defineExpose } from 'vue'
import Plotly from 'plotly.js-dist-min'

// Default panel sizes
const DEFAULT_LAYOUT = {
  leftColumnFlex: 40,
  panelHeights: {
    left: {
      'panel-info': '0 0 120px',
      'panel-history': '1 1 0px',
      'panel-histogram': '1 1 0px',
      'panel-result': '0 0 80px'
    },
    right: {
      'panel-2d-utility': '1 1 0px',
      'panel-timeline': '1 1 0px'
    }
  }
}

// Column resize state
const leftColumn = ref(null)
const rightColumn = ref(null)
const isDraggingColumn = ref(false)
const leftColumnFlex = ref(DEFAULT_LAYOUT.leftColumnFlex)

// Panel heights (stored as flex values)
const panelHeights = ref({
  left: {},
  right: {}
})

const leftColumnStyle = computed(() => ({
  flex: `0 0 ${leftColumnFlex.value}%`
}))

// Load layout on mount
onMounted(async () => {
  // Load saved layout from settings API
  await loadLayoutFromSettings()
  
  // Add resize functionality after DOM is ready
  nextTick(() => {
    initializePanelResizing()
  })
})

// Watch for layout changes and save to settings API
let saveTimeout = null
watch([leftColumnFlex, panelHeights], () => {
  // Debounce saves to avoid hammering the API
  clearTimeout(saveTimeout)
  saveTimeout = setTimeout(() => {
    saveLayoutToSettings()
  }, 500)
}, { deep: true })

// Load layout from settings API
async function loadLayoutFromSettings() {
  try {
    const response = await fetch('/api/settings/layout')
    if (response.ok) {
      const data = await response.json()
      const savedLayout = data.panelLayout || {}
      
      if (savedLayout.leftColumnFlex !== undefined) {
        leftColumnFlex.value = savedLayout.leftColumnFlex
      }
      
      if (savedLayout.panelHeights) {
        panelHeights.value = savedLayout.panelHeights
      }
      
      console.log('[PanelLayout] Loaded layout from settings:', savedLayout)
    }
  } catch (error) {
    console.error('[PanelLayout] Failed to load layout from settings:', error)
  }
}

// Save layout to settings API
async function saveLayoutToSettings() {
  try {
    // Load current layout state
    const response = await fetch('/api/settings/layout')
    if (!response.ok) {
      console.error('[PanelLayout] Failed to load current layout state')
      return
    }
    
    const currentState = await response.json()
    
    // Update only the panelLayout section
    const updatedState = {
      ...currentState,
      panelLayout: {
        leftColumnFlex: leftColumnFlex.value,
        panelHeights: panelHeights.value
      }
    }
    
    // Save back to settings
    const saveResponse = await fetch('/api/settings/layout', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedState)
    })
    
    if (saveResponse.ok) {
      console.log('[PanelLayout] Saved layout to settings')
    } else {
      console.error('[PanelLayout] Failed to save layout to settings')
    }
  } catch (error) {
    console.error('[PanelLayout] Error saving layout:', error)
  }
}

// Reset layout to defaults
async function resetLayout() {
  console.log('[PanelLayout] Resetting layout to defaults')
  
  // Reset to defaults
  leftColumnFlex.value = DEFAULT_LAYOUT.leftColumnFlex
  panelHeights.value = { left: {}, right: {} }
  
  // Re-apply default sizes to all panels
  applyLayoutToPanels()
  
  // Save to settings
  await saveLayoutToSettings()
}

// Apply layout to panels (used after reset or load)
function applyLayoutToPanels() {
  const leftPanels = leftColumn.value ? Array.from(leftColumn.value.children).filter(el => 
    el.classList.contains('panel') || el.classList.contains('panel-compact')
  ) : []
  
  const rightPanels = rightColumn.value ? Array.from(rightColumn.value.children).filter(el => 
    el.classList.contains('panel') || el.classList.contains('panel-compact')
  ) : []
  
  applyLayoutToColumn(leftPanels, 'left')
  applyLayoutToColumn(rightPanels, 'right')
}

function applyLayoutToColumn(panels, columnKey) {
  panels.forEach((panel, index) => {
    const panelClass = panel.className.split(' ').find(c => c.startsWith('panel-'))
    const savedFlex = panelHeights.value[columnKey]?.[panelClass]
    
    if (savedFlex) {
      panel.style.flex = savedFlex
    } else {
      // Apply defaults
      const defaultFlex = getDefaultFlexForPanel(panel)
      panel.style.flex = defaultFlex
    }
    
    // Set min height
    panel.style.minHeight = getMinHeightForPanel(panel)
    
    // Last panel always fills remaining space
    if (index === panels.length - 1) {
      panel.style.flex = '1 1 auto'
    }
  })
}

// Get default flex value based on panel type
function getDefaultFlexForPanel(panel) {
  if (panel.classList.contains('panel-info')) return '0 0 120px'
  if (panel.classList.contains('panel-result')) return '0 0 80px'
  return '1 1 0px' // All other panels share space equally
}

// Get minimum height based on panel type
function getMinHeightForPanel(panel) {
  if (panel.classList.contains('panel-info')) return '80px'
  if (panel.classList.contains('panel-result')) return '50px'
  if (panel.classList.contains('panel-history')) return '100px'
  if (panel.classList.contains('panel-histogram')) return '100px'
  if (panel.classList.contains('panel-2d-utility')) return '150px'
  if (panel.classList.contains('panel-timeline')) return '120px'
  return '50px'
}

// Expose resetLayout for parent components
defineExpose({ resetLayout })

// Initialize panel resizing by injecting resize handles
function initializePanelResizing() {
  // Add resize handles between panels in both columns
  addResizeHandlesToColumn(leftColumn.value, 'left')
  addResizeHandlesToColumn(rightColumn.value, 'right')
}

function addResizeHandlesToColumn(columnEl, columnKey) {
  if (!columnEl) return
  
  const panels = Array.from(columnEl.children).filter(el => 
    el.classList.contains('panel') || el.classList.contains('panel-compact')
  )
  
  console.log(`[PanelLayout] Adding resize handles to ${columnKey} column:`)
  panels.forEach((panel, idx) => {
    console.log(`  Panel ${idx}:`, panel.className.split(' ').find(c => c.startsWith('panel-')))
  })
  
  if (panels.length === 0) return
  
  // Apply saved or default sizes to panels
  panels.forEach((panel, index) => {
    const panelClass = panel.className.split(' ').find(c => c.startsWith('panel-'))
    const savedFlex = panelHeights.value[columnKey]?.[panelClass]
    
    // Use saved flex if available, otherwise use default
    const initialFlex = savedFlex || getDefaultFlexForPanel(panel)
    const minHeight = getMinHeightForPanel(panel)
    
    // Last panel always uses flex: 1 1 auto to fill remaining space
    if (index === panels.length - 1) {
      panel.style.flex = `1 1 auto`
      panel.style.minHeight = minHeight
      return // No resize handle after last panel
    }
    
    // Check if handle already exists
    if (panel.nextElementSibling?.classList.contains('resize-handle-horizontal')) {
      return
    }
    
    // Create resize handle
    const handle = document.createElement('div')
    handle.className = 'resize-handle-horizontal'
    handle.dataset.columnKey = columnKey
    handle.dataset.panelIndex = index
    
    // Insert handle after panel
    panel.parentNode.insertBefore(handle, panel.nextSibling)
    
    // Apply initial flex size
    panel.style.flex = initialFlex
    panel.style.minHeight = minHeight
    
    // Add drag handler
    handle.addEventListener('mousedown', (e) => startPanelResize(e, columnKey, index))
  })
}
    // Check if handle already exists
    if (panel.nextElementSibling?.classList.contains('resize-handle-horizontal')) {
      return
    }
    
    // Create resize handle
    const handle = document.createElement('div')
    handle.className = 'resize-handle-horizontal'
    handle.dataset.columnKey = columnKey
    handle.dataset.panelIndex = index
    
    // Insert handle after panel
    panel.parentNode.insertBefore(handle, panel.nextSibling)
    
    // Apply initial flex size
    panel.style.flex = initialFlex
    panel.style.minHeight = minHeight
    
    // Add drag handler
    handle.addEventListener('mousedown', (e) => startPanelResize(e, columnKey, index))
  })
}

function startPanelResize(event, columnKey, panelIndex) {
  const handle = event.target
  const column = columnKey === 'left' ? leftColumn.value : rightColumn.value
  
  // IMPORTANT: Filter panels at resize time, not at handle creation time
  // because the DOM may have changed
  const panels = Array.from(column.children).filter(el => 
    el.classList.contains('panel') || el.classList.contains('panel-compact')
  )
  
  console.log(`[PanelLayout] Starting resize: column=${columnKey}, panelIndex=${panelIndex}`)
  console.log(`[PanelLayout] Total panels in column:`, panels.length)
  console.log(`[PanelLayout] All panels:`, panels.map((p, i) => `${i}: ${p.className}`))
  
  const topPanel = panels[panelIndex]
  const bottomPanel = panels[panelIndex + 1]
  
  if (!topPanel || !bottomPanel) {
    console.error(`[PanelLayout] Cannot find panels! topPanel=${!!topPanel}, bottomPanel=${!!bottomPanel}`)
    return
  }
  
  console.log('[PanelLayout] Top panel:', topPanel.className, 'Bottom panel:', bottomPanel.className)
  
  const startY = event.clientY
  const startTopHeight = topPanel.offsetHeight
  const startBottomHeight = bottomPanel.offsetHeight
  
  console.log(`[PanelLayout] Initial heights: top=${startTopHeight}px, bottom=${startBottomHeight}px, total=${startTopHeight + startBottomHeight}px`)
  
  handle.classList.add('dragging')
  
  function onMouseMove(e) {
    const delta = e.clientY - startY
    
    // Use 50px as minimum for more flexibility
    const MIN_PANEL_HEIGHT = 50
    
    // Calculate total available height (must stay constant)
    const totalHeight = startTopHeight + startBottomHeight
    
    // Calculate new top height with constraints
    let newTopHeight = startTopHeight + delta
    newTopHeight = Math.max(MIN_PANEL_HEIGHT, newTopHeight)  // Enforce minimum
    newTopHeight = Math.min(totalHeight - MIN_PANEL_HEIGHT, newTopHeight)  // Leave room for bottom
    
    // Bottom height is whatever's left to maintain total
    const newBottomHeight = totalHeight - newTopHeight
    
    console.log(`[PanelLayout] Resizing: delta=${delta}px, newTop=${newTopHeight}px, newBottom=${newBottomHeight}px`)
    
    // Apply new heights with fixed flex-basis
    topPanel.style.flex = `0 0 ${newTopHeight}px`
    bottomPanel.style.flex = `0 0 ${newBottomHeight}px`
    
    // Verify the styles were applied
    console.log(`[PanelLayout] Applied styles: top.flex="${topPanel.style.flex}", bottom.flex="${bottomPanel.style.flex}"`)
    console.log(`[PanelLayout] Actual heights: top=${topPanel.offsetHeight}px, bottom=${bottomPanel.offsetHeight}px`)
    
    // Save to state using panel class names
    const topPanelClass = topPanel.className.split(' ').find(c => c.startsWith('panel-'))
    const bottomPanelClass = bottomPanel.className.split(' ').find(c => c.startsWith('panel-'))
    
    if (topPanelClass) {
      panelHeights.value[columnKey][topPanelClass] = `0 0 ${newTopHeight}px`
    }
    if (bottomPanelClass) {
      panelHeights.value[columnKey][bottomPanelClass] = `0 0 ${newBottomHeight}px`
    }
  }
  
  function onMouseUp() {
    handle.classList.remove('dragging')
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    
    // Resize Plotly plots after panel resize completes
    nextTick(() => {
      resizePlotlyPlots()
    })
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// Column resize logic
function startColumnResize(event) {
  isDraggingColumn.value = true
  const handle = event.target
  const container = handle.parentElement
  
  function onMouseMove(e) {
    if (!container) return
    
    const containerRect = container.getBoundingClientRect()
    const mouseX = e.clientX - containerRect.left
    const newLeftWidth = (mouseX / containerRect.width) * 100
    
    // Constrain between 20% and 70%
    if (newLeftWidth >= 20 && newLeftWidth <= 70) {
      leftColumnFlex.value = newLeftWidth
    }
  }
  
  function onMouseUp() {
    isDraggingColumn.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    
    // Resize all Plotly plots after column resize completes
    nextTick(() => {
      resizePlotlyPlots()
    })
  }
  
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// Resize all Plotly plots in the container
function resizePlotlyPlots() {
  // Find all divs that might contain Plotly plots
  // Look for plots by checking for Plotly's internal class or data attribute
  const allDivs = document.querySelectorAll('.panel-content [ref], .panel-content > div')
  
  allDivs.forEach(div => {
    try {
      // Check if this div has a Plotly plot
      if (div._fullLayout || div.data) {
        Plotly.Plots.resize(div)
      }
    } catch (err) {
      // Ignore errors for divs that don't have Plotly plots
    }
  })
  
  // Also try the original selectors for backwards compatibility
  const plotDivs = document.querySelectorAll('[id^="timeline-plot"], [id^="utility-2d-plot"], [id^="histogram-plot"]')
  plotDivs.forEach(plotDiv => {
    try {
      Plotly.Plots.resize(plotDiv)
    } catch (err) {
      // Ignore errors for plots that don't exist yet
    }
  })
}

function addResizeHandle() {
  // Helper function exposed to slot (not used currently)
}
</script>

<style scoped>
/* Remove default flex since we're setting explicit heights */
.resizable-panels-column > .panel,
.resizable-panels-column > .panel-compact {
  min-height: 50px;
}
</style>
