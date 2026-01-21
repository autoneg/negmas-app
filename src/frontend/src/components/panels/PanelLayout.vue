<template>
  <div class="panels-container panels-layout-compact">
    <!-- LEFT COLUMN -->
    <div 
      ref="leftColumn" 
      class="panels-column panels-column-left"
      :style="leftColumnStyle"
    >
      <slot name="left"></slot>
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
      class="panels-column panels-column-right"
    >
      <slot name="right"></slot>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import Plotly from 'plotly.js-dist-min'

// Column resize state
const leftColumn = ref(null)
const rightColumn = ref(null)
const isDraggingColumn = ref(false)
const leftColumnFlex = ref(40) // Start at 40%

const leftColumnStyle = computed(() => ({
  flex: `0 0 ${leftColumnFlex.value}%`
}))

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
  const plotDivs = document.querySelectorAll('[id^="timeline-plot"], [id^="utility-2d-plot"]')
  plotDivs.forEach(plotDiv => {
    try {
      Plotly.Plots.resize(plotDiv)
    } catch (err) {
      // Ignore errors for plots that don't exist yet
    }
  })
}

// Panel resize between panels (horizontal handles)
// Note: Individual panels will handle their own resize logic via props/events
</script>

<style scoped>
/* Styles are already in panels.css - no additional styles needed */
</style>
