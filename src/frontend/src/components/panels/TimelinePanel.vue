<template>
  <!-- Utility Timeline Panel -->
  <div 
    class="panel panel-compact panel-timeline" 
    :class="{ 'collapsed': collapsed }"
  >
    <span class="panel-collapsed-label" v-show="collapsed">TIMELINE</span>
    
    <!-- Floating Actions (LEFT side) -->
    <div class="panel-floating-actions panel-floating-actions-left">
      <!-- X-Axis Selector -->
      <select 
        v-show="adjustable && !collapsed"
        class="form-select form-select-xs" 
        v-model="xAxisType" 
        @change="initPlots"
        title="X-Axis"
      >
        <option value="step">Step</option>
        <option value="time">Time</option>
        <option value="relative_time">Rel</option>
      </select>
      
      <!-- Full View Button -->
      <button 
        class="panel-btn" 
        :class="{ 'panel-btn-active': !simplified }" 
        title="Full View (per-agent)" 
        @click="simplified = false; initPlots()" 
        v-show="!collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7"/>
          <rect x="14" y="3" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/>
          <rect x="14" y="14" width="7" height="7"/>
        </svg>
      </button>
      
      <!-- Simplified View Button -->
      <button 
        class="panel-btn" 
        :class="{ 'panel-btn-active': simplified }" 
        title="Simplified View (single plot)" 
        @click="simplified = true; initPlots()" 
        v-show="!collapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
        </svg>
      </button>
      
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
        @click.stop="$emit('zoom')" 
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
      style="padding: 0; position: relative; overflow: hidden;" 
      v-show="!collapsed"
    >
      <!-- WebP Preview Mode (for compact list view) -->
      <div v-if="compact && previewImageUrl && !showInteractive" style="width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--bg-secondary);">
        <img 
          :src="previewImageUrl" 
          alt="Timeline Preview" 
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
      
      <!-- Timeline Container (Full or after clicking "View Interactive") -->
      <div 
        v-show="!compact || !previewImageUrl || showInteractive"
        ref="timelineContainer" 
        style="width: 100%; height: 100%; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding: 4px;"
      ></div>
      
      <!-- Empty State -->
      <div 
        v-show="!hasOffers" 
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
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span class="text-muted">Waiting...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { getColorsForNegotiation } from '@/composables/useNegotiatorColors.js'

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
    type: String,
    default: 'step' // 'step', 'time', 'relative_time'
  },
  initialSimplified: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['saveAsImage', 'zoom'])

// Refs
const timelineContainer = ref(null)
const collapsed = ref(false)
const plotsInitialized = ref(false)
const xAxisType = ref(props.initialXAxis)
const simplified = ref(props.initialSimplified)
const showInteractive = ref(false)

// Computed
const hasOffers = computed(() => {
  return props.negotiation?.offers && props.negotiation.offers.length > 0
})

// Preview image URL for compact mode
const previewImageUrl = computed(() => {
  if (props.compact && props.negotiation?.id && props.negotiation?.source === 'saved') {
    const timestamp = props.negotiation.saved_at || Date.now()
    return `/api/negotiation/saved/${props.negotiation.id}/preview/timeline?t=${timestamp}`
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
    agreementColor: '#ef4444'
  }
}

function getNegotiatorColors() {
  // Use central color utility - respects colorblind mode and passed colors
  return getColorsForNegotiation(props.negotiation)
}

function getXValue(offer) {
  if (xAxisType.value === 'time') return offer.time || 0
  if (xAxisType.value === 'relative_time') return offer.relative_time || 0
  return offer.step || 0
}

function getXAxisTitle() {
  if (xAxisType.value === 'time') return 'Time (s)'
  if (xAxisType.value === 'relative_time') return 'Relative Time'
  return 'Step'
}

function getXAxisRange(offers) {
  if (!offers || offers.length === 0) return null
  
  if (xAxisType.value === 'relative_time') {
    // Always 0-1 for relative time
    return [0, 1]
  } else if (xAxisType.value === 'time') {
    // For time, let Plotly autorange based on actual data
    // This handles milliseconds, seconds, etc. properly
    return null  // null means autorange
  } else {
    // Step: dynamic range
    const maxStep = Math.max(...offers.map(o => o.step || 0))
    return [0, maxStep]
  }
}

// Initialize timeline plots
async function initPlots() {
  const container = timelineContainer.value
  if (!container) return
  
  // Don't render if panel is collapsed or hidden
  if (container.offsetParent === null || container.clientWidth === 0) {
    plotsInitialized.value = false
    return
  }
  
  const neg = props.negotiation
  if (!neg || !neg.offers || neg.offers.length === 0) {
    plotsInitialized.value = false
    return
  }
  
  try {
    const colors = getPlotColors()
    const negColors = getNegotiatorColors()
    const isColorBlind = document.documentElement.classList.contains('color-blind-mode')
    const numAgents = neg.negotiator_names?.length || 2
    const xAxisTitle = getXAxisTitle()
    
    // Clear container
    container.innerHTML = ''
    
    if (simplified.value) {
      // SIMPLIFIED VIEW: Single plot showing each agent's own utility for their offers
      const plotId = 'timeline-plot-simplified'
      const plotWrapper = document.createElement('div')
      plotWrapper.style.cssText = 'flex: 1; min-height: 0; height: 100%;'
      plotWrapper.innerHTML = `<div id="${plotId}" style="width: 100%; height: 100%;"></div>`
      container.appendChild(plotWrapper)
      
      const traces = []
      
      // Each agent gets one trace showing their own utility for their own offers
      for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
        const agentOffers = neg.offers
          .filter(o => Number(o.proposer_index) === agentIdx)
          .sort((a, b) => getXValue(a) - getXValue(b)) // Sort by x-axis value
        
        const xValues = agentOffers.map(getXValue)
        const yValues = agentOffers.map(o => o.utilities[agentIdx] || 0)
        
        traces.push({
          x: xValues,
          y: yValues,
          type: 'scatter',
          mode: 'lines+markers',
          name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
          line: { 
            color: negColors[agentIdx % negColors.length], 
            width: 2,
            dash: isColorBlind ? LINE_DASHES[agentIdx % LINE_DASHES.length] : 'solid'
          },
          marker: {
            color: negColors[agentIdx % negColors.length],
            size: 6,
            symbol: isColorBlind ? MARKER_SYMBOLS[agentIdx % MARKER_SYMBOLS.length] : 'circle'
          }
        })
      }
      
      // Add agreement markers if exists
      if (neg.agreement && neg.final_utilities) {
        const lastOffer = neg.offers[neg.offers.length - 1]
        for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
          if (neg.final_utilities.length > agentIdx) {
            traces.push({
              x: [getXValue(lastOffer)],
              y: [neg.final_utilities[agentIdx]],
              type: 'scatter',
              mode: 'markers',
              name: agentIdx === 0 ? 'Agreement' : undefined,
              showlegend: agentIdx === 0,
              marker: { 
                color: colors.agreementColor, 
                size: 14, 
                symbol: 'star', 
                line: { color: '#fff', width: 1 } 
              }
            })
          }
        }
      }
      
      const layout = {
        title: { 
          text: 'Utility of Own Offers',
          font: { size: 13, color: colors.textColor }
        },
        xaxis: { 
          title: { text: xAxisTitle, font: { color: colors.textColor, size: 11 } },
          tickfont: { color: colors.textColor, size: 10 },
          gridcolor: colors.gridColor,
          linecolor: colors.gridColor,
          ...(getXAxisRange(neg.offers) && { range: getXAxisRange(neg.offers) })
        },
        yaxis: { 
          title: { text: 'Utility', font: { color: colors.textColor, size: 11 } },
          tickfont: { color: colors.textColor, size: 10 },
          gridcolor: colors.gridColor,
          linecolor: colors.gridColor
        },
        margin: { t: 40, r: 20, b: 50, l: 50 },
        showlegend: true,
        legend: { 
          orientation: 'h', 
          y: -0.15, 
          x: 0.5, 
          xanchor: 'center', 
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
          filename: 'utility-timeline-simplified', 
          scale: 2 
        }
      }
      
      await Plotly.newPlot(plotId, traces, layout, config)
    } else {
      // FULL VIEW: N plots, one per negotiator
      const containerHeight = container.clientHeight || 300
      const plotHeight = Math.max(120, Math.floor((containerHeight - (numAgents - 1) * 8) / numAgents))
      
      for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
        const plotId = `timeline-plot-${agentIdx}`
        const plotWrapper = document.createElement('div')
        plotWrapper.style.cssText = `flex: 0 0 ${plotHeight}px; min-height: ${plotHeight}px; height: ${plotHeight}px;`
        plotWrapper.innerHTML = `<div id="${plotId}" style="width: 100%; height: 100%;"></div>`
        container.appendChild(plotWrapper)
        
        const traces = []
        
        // Create N series per plot - each series j shows utility of offers from agent j for agent agentIdx
        for (let proposerIdx = 0; proposerIdx < numAgents; proposerIdx++) {
          const proposerOffers = neg.offers
            .filter(o => Number(o.proposer_index) === proposerIdx)
            .sort((a, b) => getXValue(a) - getXValue(b)) // Sort by x-axis value
          
          const xValues = proposerOffers.map(getXValue)
          const yValues = proposerOffers.map(o => o.utilities[agentIdx] || 0)
          
          // Own offers get thick solid line, others get dashed
          const isOwnOffers = proposerIdx === agentIdx
          
          traces.push({
            x: xValues,
            y: yValues,
            type: 'scatter',
            mode: 'lines',
            name: neg.negotiator_names?.[proposerIdx] || `Agent ${proposerIdx + 1}`,
            line: { 
              color: negColors[proposerIdx % negColors.length], 
              width: isOwnOffers ? 3 : 1.5,
              dash: isOwnOffers ? 'solid' : LINE_DASHES[(proposerIdx + 1) % LINE_DASHES.length]
            }
          })
        }
        
        // Add agreement marker if exists
        if (neg.agreement && neg.final_utilities && neg.final_utilities.length > agentIdx) {
          const lastOffer = neg.offers[neg.offers.length - 1]
          traces.push({
            x: [getXValue(lastOffer)],
            y: [neg.final_utilities[agentIdx]],
            type: 'scatter',
            mode: 'markers',
            name: 'Agreement',
            showlegend: agentIdx === 0,
            marker: { 
              color: colors.agreementColor, 
              size: 10, 
              symbol: 'star', 
              line: { color: '#fff', width: 1 } 
            }
          })
        }
        
        // Only show legend on the last plot to avoid overlap
        const isLastPlot = agentIdx === numAgents - 1
        
        const layout = {
          title: { 
            text: `${neg.negotiator_names?.[agentIdx] || 'Agent ' + (agentIdx + 1)}'s Utility`,
            font: { size: 11, color: colors.textColor }
          },
          xaxis: { 
            title: { text: isLastPlot ? xAxisTitle : '', font: { color: colors.textColor, size: 9 } },
            tickfont: { color: colors.textColor, size: 8 },
            gridcolor: colors.gridColor,
            linecolor: colors.gridColor,
            ...(getXAxisRange(neg.offers) && { range: getXAxisRange(neg.offers) })
          },
          yaxis: { 
            title: { text: 'Utility', font: { color: colors.textColor, size: 9 } },
            tickfont: { color: colors.textColor, size: 8 },
            gridcolor: colors.gridColor,
            linecolor: colors.gridColor
          },
          margin: { t: 25, r: 15, b: isLastPlot ? 40 : 20, l: 35 },
          showlegend: isLastPlot,
          legend: { 
            orientation: 'h', 
            y: -0.35, 
            x: 0.5, 
            xanchor: 'center', 
            font: { color: colors.textColor, size: 8 } 
          },
          paper_bgcolor: colors.bgColor,
          plot_bgcolor: colors.bgColor,
          font: { 
            family: '-apple-system, BlinkMacSystemFont, sans-serif', 
            size: 9, 
            color: colors.textColor 
          }
        }
        
        const config = {
          responsive: true,
          displayModeBar: 'hover',
          modeBarButtonsToRemove: ['lasso2d', 'select2d'],
          toImageButtonOptions: { 
            format: 'png', 
            filename: `utility-timeline-${agentIdx}`, 
            scale: 2 
          }
        }
        
        await Plotly.newPlot(plotId, traces, layout, config)
      }
    }
    
    plotsInitialized.value = true
  } catch (e) {
    console.warn('Failed to initialize timeline plots:', e)
    plotsInitialized.value = false
  }
}

// Reset view
function resetView() {
  if (timelineContainer.value && plotsInitialized.value) {
    // Reset zoom/pan for all plots in container
    const plots = timelineContainer.value.querySelectorAll('[id^="timeline-plot-"]')
    plots.forEach(plot => {
      if (plot && window.Plotly) {
        // Reset axes to autoscale
        Plotly.relayout(plot, {
          'xaxis.autorange': true,
          'yaxis.autorange': true
        })
      }
    })
  }
}

// Download plot as image
async function saveAsImage() {
  if (timelineContainer.value && plotsInitialized.value && window.Plotly) {
    const plots = timelineContainer.value.querySelectorAll('[id^="timeline-plot-"]')
    if (plots.length === 0) return
    
    try {
      // If single plot (simplified view), download it directly
      if (simplified.value && plots.length === 1) {
        const imgData = await Plotly.toImage(plots[0], {
          format: 'png',
          width: 1200,
          height: 800
        })
        // Create download link
        const link = document.createElement('a')
        link.download = 'timeline-utility.png'
        link.href = imgData
        link.click()
      } else {
        // For multiple plots, download the first one
        const imgData = await Plotly.toImage(plots[0], {
          format: 'png',
          width: 1200,
          height: 600
        })
        const link = document.createElement('a')
        link.download = 'timeline-utility.png'
        link.href = imgData
        link.click()
      }
    } catch (err) {
      console.error('Failed to download image:', err)
    }
  }
}

// Image error handler for preview mode
function onImageError() {
  console.warn('Failed to load preview image, falling back to interactive mode')
  showInteractive.value = true
}

// Watch for offer changes - throttled for smooth updates
let updateScheduled = false
function scheduleUpdate() {
  if (updateScheduled) return
  updateScheduled = true
  requestAnimationFrame(() => {
    if (hasOffers.value && !collapsed.value) {
      nextTick(() => {
        initPlots()
      })
    }
    updateScheduled = false
  })
}

watch(() => props.negotiation?.offers?.length, () => {
  scheduleUpdate()
})

watch(collapsed, (newVal) => {
  if (!newVal && hasOffers.value) {
    nextTick(() => {
      initPlots()
    })
  }
})

// Watch for switching from preview to interactive mode
watch(showInteractive, (newVal) => {
  if (newVal && hasOffers.value) {
    nextTick(() => {
      initPlots()
    })
  }
})

// Initialize on mount
onMounted(() => {
  if (hasOffers.value && !collapsed.value) {
    nextTick(() => {
      initPlots()
    })
  }
})

// Cleanup on unmount
onBeforeUnmount(() => {
  if (timelineContainer.value) {
    const plots = timelineContainer.value.querySelectorAll('[id^="timeline-plot-"]')
    plots.forEach(plot => {
      if (plot && window.Plotly) {
        Plotly.purge(plot)
      }
    })
  }
})

// Expose methods
defineExpose({
  resetView,
  initPlots
})
</script>

<style>
/* All styles are in panels.css - no additional styles needed */
</style>
