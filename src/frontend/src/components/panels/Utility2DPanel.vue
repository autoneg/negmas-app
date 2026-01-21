<template>
  <!-- 2D Utility View Panel -->
  <div 
    class="panel panel-compact panel-2d-utility" 
    :class="{ 'collapsed': collapsed }"
  >
    <span class="panel-collapsed-label" v-show="collapsed">2D VIEW</span>
    
    <!-- Floating Actions (LEFT side) -->
    <div class="panel-floating-actions panel-floating-actions-left">
      <!-- Axis Selectors -->
      <div 
        class="panel-inline-controls" 
        v-show="adjustable && !collapsed"
      >
        <select 
          class="form-select form-select-xs" 
          v-model.number="xAxisIndex" 
          @change="onAxisChange"
          title="X-Axis"
        >
          <option 
            v-for="(name, idx) in (negotiatorNames || [])" 
            :key="idx"
            :value="idx"
          >
            {{ name.substring(0, 6) }}
          </option>
        </select>
        <span style="font-size: 9px; opacity: 0.5;">×</span>
        <select 
          class="form-select form-select-xs" 
          v-model.number="yAxisIndex" 
          @change="onAxisChange"
          title="Y-Axis"
        >
          <option 
            v-for="(name, idx) in (negotiatorNames || [])" 
            :key="idx"
            :value="idx"
          >
            {{ name.substring(0, 6) }}
          </option>
        </select>
      </div>
      
      <!-- Save as Image -->
      <button 
        class="panel-btn" 
        title="Save as Image" 
        @click="saveAsImage" 
        v-show="!collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </button>
      
      <!-- Zoom -->
      <button 
        class="panel-btn" 
        title="Toggle Fullscreen" 
        @click="collapsed = !collapsed" 
        v-show="!collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 3 21 3 21 9"/>
          <polyline points="9 21 3 21 3 15"/>
          <line x1="21" y1="3" x2="14" y2="10"/>
          <line x1="3" y1="21" x2="10" y2="14"/>
        </svg>
      </button>
      
      <!-- Reset View -->
      <button 
        class="panel-btn" 
        title="Reset View" 
        @click="resetView" 
        v-show="!collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
        </svg>
      </button>
      
      <!-- Collapse -->
      <button 
        class="panel-btn panel-collapse-btn" 
        title="Toggle panel" 
        @click="collapsed = !collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </div>
    
    <!-- Panel Content -->
    <div 
      class="panel-content panel-content-compact" 
      style="padding: 0; position: relative;" 
      v-show="!collapsed"
    >
      <!-- WebP Preview Mode (for compact list view) -->
      <div v-if="compact && previewImageUrl && !showInteractive" style="width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--bg-secondary);">
        <img 
          :src="previewImageUrl" 
          alt="2D Utility Preview" 
          style="max-width: 100%; max-height: calc(100% - 40px); object-fit: contain;"
          @error="onImageError"
        />
        <button 
          class="btn btn-sm btn-secondary mt-2" 
          @click="showInteractive = true"
          style="margin-top: 8px;"
        >
          View Interactive
        </button>
      </div>
      
      <!-- Plotly Chart Container (Full or after clicking "View Interactive") -->
      <div 
        v-show="!compact || !previewImageUrl || showInteractive"
        ref="plotDiv" 
        style="width: 100%; height: 100%;"
      ></div>
      
      <!-- Loading State -->
      <div 
        v-show="!hasData" 
        class="empty-state-mini" 
        style="position: absolute; inset: 0; background: var(--bg-secondary);"
      >
        <svg 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          stroke-width="1.5" 
          style="width: 24px; height: 24px; opacity: 0.4;"
        >
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
        <span class="text-muted">Loading...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
  negotiation: {
    type: Object,
    default: null
  },
  adjustable: {
    type: Boolean,
    default: false
  },
  compact: {
    type: Boolean,
    default: false
  },
  initialXAxis: {
    type: Number,
    default: 0
  },
  initialYAxis: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['saveAsImage', 'zoom'])

// Refs
const plotDiv = ref(null)
const collapsed = ref(false)
const plotInitialized = ref(false)
const showInteractive = ref(false)

// Axis indices
const xAxisIndex = ref(props.initialXAxis)
const yAxisIndex = ref(props.initialYAxis)

// Computed
const negotiatorNames = computed(() => props.negotiation?.negotiator_names || [])
const hasData = computed(() => !!props.negotiation?.outcome_space_data)

// Preview image URL for compact mode
const previewImageUrl = computed(() => {
  if (props.compact && props.negotiation?.id && props.negotiation?.source === 'saved') {
    return `/api/negotiation/saved/${props.negotiation.id}/preview/utility2d`
  }
  return null
})

// Colors
const LINE_DASHES = ['solid', 'dash', 'dot', 'dashdot']
const MARKER_SYMBOLS = ['circle', 'square', 'diamond', 'cross', 'triangle-up', 'triangle-down']

function getPlotColors() {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    bgColor: isDark ? '#1a1a1a' : '#ffffff',
    textColor: isDark ? '#e0e0e0' : '#333333',
    gridColor: isDark ? '#333333' : '#e0e0e0',
    outcomeColor: isDark ? '#6b7280' : '#9ca3af',
    paretoColor: isDark ? '#fbbf24' : '#f59e0b',
    nashColor: '#8b5cf6',
    kalaiColor: '#06b6d4',
    kalaiSmorodinskyColor: '#10b981',
    maxWelfareColor: '#f97316',
    agreementColor: '#ef4444'
  }
}

function getNegotiatorColors() {
  const isColorBlind = document.documentElement.classList.contains('color-blind-mode')
  if (isColorBlind) {
    return ['#0173b2', '#de8f05', '#029e73', '#cc78bc', '#ca9161', '#fbafe4', '#949494', '#ece133']
  }
  return ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899']
}

// Initialize plot
async function initPlot() {
  if (!plotDiv.value) return
  
  // Don't render if panel is collapsed or hidden
  if (plotDiv.value.offsetParent === null || plotDiv.value.clientWidth === 0) {
    plotInitialized.value = false
    return
  }
  
  const neg = props.negotiation
  if (!neg || !neg.outcome_space_data) {
    plotInitialized.value = false
    return
  }
  
  try {
    const colors = getPlotColors()
    const osd = neg.outcome_space_data
    const negColors = getNegotiatorColors()
    const isColorBlind = document.documentElement.classList.contains('color-blind-mode')
    
    const xIdx = xAxisIndex.value
    const yIdx = yAxisIndex.value
    
    const traces = []
    
    // 1. All outcomes - use scattergl (WebGL) for large outcome spaces
    if (osd.outcome_utilities && osd.outcome_utilities.length > 0) {
      traces.push({
        x: osd.outcome_utilities.map(u => u[xIdx] || 0),
        y: osd.outcome_utilities.map(u => u[yIdx] || 0),
        type: 'scattergl',
        mode: 'markers',
        name: 'Outcomes',
        marker: { color: colors.outcomeColor, size: 3, opacity: 0.5 },
        hoverinfo: 'skip'
      })
    }
    
    // 2. Pareto frontier
    if (osd.pareto_utilities && osd.pareto_utilities.length > 0) {
      traces.push({
        x: osd.pareto_utilities.map(u => u[xIdx] || 0),
        y: osd.pareto_utilities.map(u => u[yIdx] || 0),
        type: 'scattergl',
        mode: 'markers',
        name: 'Pareto Frontier',
        marker: { color: colors.paretoColor, size: 6, opacity: 0.7 }
      })
    }
    
    // 3. Nash point
    if (osd.nash_point && osd.nash_point.length > Math.max(xIdx, yIdx)) {
      traces.push({
        x: [osd.nash_point[xIdx]],
        y: [osd.nash_point[yIdx]],
        type: 'scattergl',
        mode: 'markers',
        name: 'Nash',
        marker: { 
          color: 'rgba(0,0,0,0)',
          size: 14, 
          symbol: 'triangle-left',
          line: { color: colors.nashColor, width: 2.5 }
        }
      })
    }
    
    // 4. Kalai point
    if (osd.kalai_point && osd.kalai_point.length > Math.max(xIdx, yIdx)) {
      traces.push({
        x: [osd.kalai_point[xIdx]],
        y: [osd.kalai_point[yIdx]],
        type: 'scattergl',
        mode: 'markers',
        name: 'Kalai',
        marker: { 
          color: 'rgba(0,0,0,0)',
          size: 14, 
          symbol: 'triangle-down',
          line: { color: colors.kalaiColor, width: 2.5 }
        }
      })
    }
    
    // 5. Kalai-Smorodinsky point
    if (osd.kalai_smorodinsky_point && osd.kalai_smorodinsky_point.length > Math.max(xIdx, yIdx)) {
      traces.push({
        x: [osd.kalai_smorodinsky_point[xIdx]],
        y: [osd.kalai_smorodinsky_point[yIdx]],
        type: 'scattergl',
        mode: 'markers',
        name: 'Kalai-Smorodinsky',
        marker: { 
          color: 'rgba(0,0,0,0)',
          size: 14, 
          symbol: 'triangle-up',
          line: { color: colors.kalaiSmorodinskyColor, width: 2.5 }
        }
      })
    }
    
    // 6. Max welfare point
    if (osd.max_welfare_point && osd.max_welfare_point.length > Math.max(xIdx, yIdx)) {
      traces.push({
        x: [osd.max_welfare_point[xIdx]],
        y: [osd.max_welfare_point[yIdx]],
        type: 'scattergl',
        mode: 'markers',
        name: 'Max Welfare',
        marker: { 
          color: 'rgba(0,0,0,0)',
          size: 14, 
          symbol: 'triangle-right',
          line: { color: colors.maxWelfareColor, width: 2.5 }
        }
      })
    }
    
    // 7. Offer traces per negotiator
    const offers = neg.offers || []
    const numAgents = neg.negotiator_names?.length || 2
    for (let i = 0; i < numAgents; i++) {
      const agentOffers = offers.filter(o => Number(o.proposer_index) === i)
      traces.push({
        x: agentOffers.map(o => o.utilities[xIdx] || 0),
        y: agentOffers.map(o => o.utilities[yIdx] || 0),
        type: 'scattergl',
        mode: 'lines+markers',
        name: neg.negotiator_names?.[i] || `Agent ${i + 1}`,
        line: { 
          color: negColors[i % negColors.length], 
          width: 2,
          dash: isColorBlind ? LINE_DASHES[i % LINE_DASHES.length] : 'solid'
        },
        marker: { 
          color: negColors[i % negColors.length], 
          size: isColorBlind ? 8 : 6,
          symbol: isColorBlind ? MARKER_SYMBOLS[i % MARKER_SYMBOLS.length] : 'circle'
        }
      })
    }
    
    // 8. Agreement point
    if (neg.agreement && neg.final_utilities && neg.final_utilities.length > Math.max(xIdx, yIdx)) {
      traces.push({
        x: [neg.final_utilities[xIdx]],
        y: [neg.final_utilities[yIdx]],
        type: 'scattergl',
        mode: 'markers',
        name: 'Agreement',
        marker: { 
          color: colors.agreementColor, 
          size: 16, 
          symbol: 'star', 
          line: { color: '#fff', width: 2 } 
        }
      })
    }
    
    const layout = {
      xaxis: { 
        title: { 
          text: neg.negotiator_names?.[xIdx] || `Agent ${xIdx + 1}`, 
          font: { color: colors.textColor } 
        },
        tickfont: { color: colors.textColor },
        gridcolor: colors.gridColor,
        linecolor: colors.gridColor,
        zerolinecolor: colors.gridColor
      },
      yaxis: { 
        title: { 
          text: neg.negotiator_names?.[yIdx] || `Agent ${yIdx + 1}`, 
          font: { color: colors.textColor } 
        },
        tickfont: { color: colors.textColor },
        gridcolor: colors.gridColor,
        linecolor: colors.gridColor,
        zerolinecolor: colors.gridColor
      },
      margin: { t: 30, r: 30, b: 50, l: 50 },
      legend: { 
        orientation: 'h', 
        y: -0.15, 
        font: { color: colors.textColor, size: 10 } 
      },
      paper_bgcolor: colors.bgColor,
      plot_bgcolor: colors.bgColor,
      font: { 
        family: '-apple-system, BlinkMacSystemFont, sans-serif', 
        size: 11, 
        color: colors.textColor 
      }
    }
    
    const config = {
      responsive: true,
      displayModeBar: 'hover',
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      toImageButtonOptions: { 
        format: 'png', 
        filename: '2d-utility-view', 
        scale: 2 
      }
    }
    
    await Plotly.react(plotDiv.value, traces, layout, config)
    plotInitialized.value = true
  } catch (e) {
    console.warn('Failed to initialize outcome space plot:', e)
    plotInitialized.value = false
  }
}

// Update plot when offers change (incremental)
async function updatePlot() {
  if (!plotInitialized.value) {
    await initPlot()
    return
  }
  
  // For simplicity, just re-render the entire plot
  // In production, could use Plotly.extendTraces for better performance
  await initPlot()
}

// Reset view
function resetView() {
  if (plotDiv.value && plotInitialized.value && window.Plotly) {
    // Reset zoom/pan to original view
    Plotly.relayout(plotDiv.value, {
      'xaxis.autorange': true,
      'yaxis.autorange': true
    })
  }
}

// Download plot as image
async function saveAsImage() {
  if (plotDiv.value && plotInitialized.value && window.Plotly) {
    try {
      const imgData = await Plotly.toImage(plotDiv.value, {
        format: 'png',
        width: 1200,
        height: 1000
      })
      // Create download link
      const link = document.createElement('a')
      link.download = 'utility-2d.png'
      link.href = imgData
      link.click()
    } catch (err) {
      console.error('Failed to download image:', err)
    }
  }
}

// Axis change handler
function onAxisChange() {
  plotInitialized.value = false
  nextTick(() => {
    initPlot()
  })
}

// Image error handler for preview mode
function onImageError() {
  console.warn('Failed to load preview image, falling back to interactive mode')
  showInteractive.value = true
}

// Watch for data changes - throttled for smooth updates
let updateScheduled = false
function scheduleUpdate() {
  if (updateScheduled) return
  updateScheduled = true
  requestAnimationFrame(() => {
    if (hasData.value && !collapsed.value) {
      updatePlot()
    }
    updateScheduled = false
  })
}

watch(() => props.negotiation?.offers?.length, () => {
  scheduleUpdate()
})

watch(() => props.negotiation?.outcome_space_data, () => {
  if (hasData.value && !collapsed.value) {
    nextTick(() => {
      initPlot()
    })
  }
})

// Watch for agreement/final_utilities changes (when negotiation completes)
watch(() => props.negotiation?.final_utilities, () => {
  if (hasData.value && !collapsed.value) {
    nextTick(() => {
      initPlot()
    })
  }
}, { deep: true })

watch(collapsed, (newVal) => {
  if (!newVal && hasData.value) {
    nextTick(() => {
      initPlot()
    })
  }
})

// Watch for switching from preview to interactive mode
watch(showInteractive, (newVal) => {
  if (newVal && hasData.value) {
    nextTick(() => {
      initPlot()
    })
  }
})

// Initialize on mount
onMounted(() => {
  if (hasData.value && !collapsed.value) {
    nextTick(() => {
      initPlot()
    })
  }
})

// Cleanup on unmount
onBeforeUnmount(() => {
  if (plotDiv.value) {
    Plotly.purge(plotDiv.value)
  }
})

// Expose methods for parent component
defineExpose({
  resetView,
  initPlot
})
</script>

<style>
/* All styles are in panels.css - no additional styles needed */
</style>
