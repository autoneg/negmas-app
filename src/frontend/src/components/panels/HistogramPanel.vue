<template>
  <!-- Issue Frequency / Histogram Panel -->
  <div 
    class="panel panel-compact panel-histogram" 
    :class="{ 'collapsed': collapsed }"
  >
    <span class="panel-collapsed-label" v-show="collapsed">HISTOGRAM</span>
    
    <!-- Floating Actions (Left side) -->
    <div class="panel-floating-actions panel-floating-actions-left">
      <!-- Histogram controls -->
      <div v-show="!collapsed" style="display: flex; gap: 4px;">
        <button class="panel-btn" title="Save as Image" @click="downloadPlot">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </button>
        <button class="panel-btn" title="Zoom" @click="$emit('zoom')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 3 21 3 21 9"/>
            <polyline points="9 21 3 21 3 15"/>
            <line x1="21" y1="3" x2="14" y2="10"/>
            <line x1="3" y1="21" x2="10" y2="14"/>
          </svg>
        </button>
        <button class="panel-btn" title="Reset View" @click="resetView">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
        </button>
      </div>
      
      <!-- Collapse button (always visible) -->
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
          alt="Histogram Preview" 
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
      
      <!-- Full Content (after clicking "View Interactive" or in full view) -->
      <div v-show="!compact || !previewImageUrl || showInteractive" style="width: 100%; height: 100%;">
        <div ref="histogramContainer" style="width: 100%; height: 100%;"></div>
        <div 
          v-show="!hasOffers" 
          class="empty-state-mini" 
          style="position: absolute; inset: 0; background: var(--bg-secondary);"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width: 24px; height: 24px; opacity: 0.4;">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M9 21V9"/>
          </svg>
          <span class="text-muted">Waiting...</span>
        </div>
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
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['zoom'])

// Refs
const histogramContainer = ref(null)
const collapsed = ref(false)
const histogramInitialized = ref(false)
const showInteractive = ref(false)

// Computed
const hasOffers = computed(() => {
  return props.negotiation?.offers && props.negotiation.offers.length > 0
})

// Preview image URL for compact mode
const previewImageUrl = computed(() => {
  if (props.compact && props.negotiation?.id && props.negotiation?.source === 'saved') {
    return `/api/negotiation/saved/${props.negotiation.id}/preview/histogram`
  }
  return null
})

const issueNames = computed(() => {
  if (!props.negotiation) return []
  const names = props.negotiation.issue_names || []
  // Fallback: try to extract from first offer
  if (names.length === 0 && hasOffers.value) {
    const firstOffer = props.negotiation.offers[0]?.offer
    if (typeof firstOffer === 'object' && firstOffer !== null && !Array.isArray(firstOffer)) {
      return Object.keys(firstOffer)
    }
  }
  return names
})

// Colors
function getPlotColors() {
  const isDark = document.documentElement.classList.contains('dark')
  return {
    bgColor: isDark ? '#1a1a1a' : '#ffffff',
    textColor: isDark ? '#e0e0e0' : '#333333',
    gridColor: isDark ? '#333333' : '#e0e0e0'
  }
}

function getNegotiatorColors() {
  const isColorBlind = document.documentElement.classList.contains('color-blind-mode')
  if (isColorBlind) {
    return ['#0173b2', '#de8f05', '#029e73', '#cc78bc', '#ca9161', '#fbafe4', '#949494', '#ece133']
  }
  return ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899']
}

// Initialize histogram
async function initHistogram(retryCount = 0) {
  // Early exit if collapsed - performance optimization
  if (collapsed.value) return
  
  const container = histogramContainer.value
  if (!container) return
  
  // Don't render if panel is collapsed or hidden
  if (container.offsetParent === null || container.clientWidth === 0) {
    histogramInitialized.value = false
    if (retryCount < 5) {
      setTimeout(() => initHistogram(retryCount + 1), 150 * (retryCount + 1))
    }
    return
  }
  
  const neg = props.negotiation
  if (!neg || !neg.offers || neg.offers.length === 0) {
    container.innerHTML = ''
    histogramInitialized.value = false
    return
  }
  
  try {
    const colors = getPlotColors()
    const negColors = getNegotiatorColors()
    const numAgents = neg.negotiator_names?.length || 2
    
    // Determine if issue-based or enumerated
    const firstOffer = neg.offers[0]?.offer
    const issues = issueNames.value
    const isEnumerated = issues.length === 0
    
    // Create plot div
    container.innerHTML = '<div id="histogram-plot" style="width: 100%; height: 100%;"></div>'
    const plotDiv = container.querySelector('#histogram-plot')
    if (!plotDiv) return
    
    if (isEnumerated) {
      // Enumerated: single histogram of outcomes
      const outcomeFreq = {}
      
      neg.offers.forEach(offer => {
        const offerData = offer.offer
        const key = Array.isArray(offerData) 
          ? offerData.join(', ')
          : typeof offerData === 'object' 
            ? JSON.stringify(offerData)
            : String(offerData)
        
        if (!outcomeFreq[key]) {
          outcomeFreq[key] = new Array(numAgents).fill(0)
        }
        outcomeFreq[key][offer.proposer_index]++
      })
      
      // Sort by total frequency
      const outcomes = Object.keys(outcomeFreq).sort((a, b) => {
        const totalA = outcomeFreq[a].reduce((s, v) => s + v, 0)
        const totalB = outcomeFreq[b].reduce((s, v) => s + v, 0)
        return totalB - totalA
      })
      
      const displayOutcomes = outcomes.slice(0, 15)
      
      const traces = []
      for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
        traces.push({
          x: displayOutcomes,
          y: displayOutcomes.map(o => outcomeFreq[o][agentIdx]),
          type: 'bar',
          name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
          marker: { 
            color: negColors[agentIdx % negColors.length],
            opacity: 0.85
          }
        })
      }
      
      const layout = {
        barmode: 'group',
        bargap: 0.15,
        bargroupgap: 0.1,
        margin: { t: 10, r: 10, b: 60, l: 35 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { 
          family: '-apple-system, BlinkMacSystemFont, sans-serif', 
          size: 9, 
          color: colors.textColor 
        },
        legend: { 
          orientation: 'h', 
          y: 1.02,
          x: 0.5,
          xanchor: 'center',
          font: { color: colors.textColor, size: 8 } 
        },
        xaxis: {
          tickfont: { color: colors.textColor, size: 7 },
          tickangle: -45,
          gridcolor: colors.gridColor
        },
        yaxis: {
          title: { text: 'Count', font: { size: 9, color: colors.textColor } },
          tickfont: { color: colors.textColor, size: 8 },
          gridcolor: colors.gridColor
        }
      }
      
      await Plotly.newPlot(plotDiv, traces, layout, {
        responsive: true,
        displayModeBar: 'hover',
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
      })
    } else {
      // Issue-based: subplots per issue
      const numIssues = issues.length
      const cols = Math.min(numIssues, 2)
      const rows = Math.ceil(numIssues / cols)
      
      const hGap = 0.12
      const vGap = 0.15
      const plotWidth = (1 - hGap * (cols - 1)) / cols
      const plotHeight = (1 - vGap * (rows - 1)) / rows
      
      const traces = []
      const layout = {
        barmode: 'group',
        bargap: 0.1,
        bargroupgap: 0.05,
        margin: { t: 20, r: 10, b: 20, l: 30 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { 
          family: '-apple-system, BlinkMacSystemFont, sans-serif', 
          size: 8, 
          color: colors.textColor 
        },
        legend: { 
          orientation: 'h', 
          y: 1.02,
          x: 0.5,
          xanchor: 'center',
          font: { color: colors.textColor, size: 8 } 
        },
        annotations: []
      }
      
      issues.forEach((issue, issueIdx) => {
        const row = Math.floor(issueIdx / cols)
        const col = issueIdx % cols
        
        const xStart = col * (plotWidth + hGap)
        const xEnd = xStart + plotWidth
        const yEnd = 1 - row * (plotHeight + vGap)
        const yStart = yEnd - plotHeight
        
        const xAxisName = issueIdx === 0 ? 'x' : `x${issueIdx + 1}`
        const yAxisName = issueIdx === 0 ? 'y' : `y${issueIdx + 1}`
        const xAxisKey = issueIdx === 0 ? 'xaxis' : `xaxis${issueIdx + 1}`
        const yAxisKey = issueIdx === 0 ? 'yaxis' : `yaxis${issueIdx + 1}`
        
        // Count frequencies
        const valueFreq = {}
        neg.offers.forEach(offer => {
          const offerData = offer.offer
          const value = typeof offerData === 'object' && offerData !== null
            ? offerData[issue]
            : undefined
          
          if (value !== undefined) {
            const key = String(value)
            if (!valueFreq[key]) {
              valueFreq[key] = new Array(numAgents).fill(0)
            }
            valueFreq[key][offer.proposer_index]++
          }
        })
        
        // Sort values
        const values = Object.keys(valueFreq).sort((a, b) => {
          const numA = parseFloat(a)
          const numB = parseFloat(b)
          if (!isNaN(numA) && !isNaN(numB)) return numA - numB
          return a.localeCompare(b)
        })
        
        // Create traces
        for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
          traces.push({
            x: values,
            y: values.map(v => valueFreq[v][agentIdx]),
            type: 'bar',
            name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
            marker: { 
              color: negColors[agentIdx % negColors.length],
              opacity: 0.85
            },
            xaxis: xAxisName,
            yaxis: yAxisName,
            showlegend: issueIdx === 0,
            legendgroup: `agent${agentIdx}`
          })
        }
        
        // Configure axes
        layout[xAxisKey] = {
          domain: [xStart, xEnd],
          tickfont: { color: colors.textColor, size: 7 },
          tickangle: values.some(v => v.length > 4) ? -45 : 0,
          gridcolor: colors.gridColor,
          anchor: yAxisName
        }
        
        layout[yAxisKey] = {
          domain: [yStart, yEnd],
          tickfont: { color: colors.textColor, size: 7 },
          gridcolor: colors.gridColor,
          anchor: xAxisName
        }
        
        // Add subplot title
        layout.annotations.push({
          text: `<b>${issue}</b>`,
          x: (xStart + xEnd) / 2,
          y: yEnd + 0.02,
          xref: 'paper',
          yref: 'paper',
          xanchor: 'center',
          yanchor: 'bottom',
          showarrow: false,
          font: { size: 9, color: colors.textColor }
        })
      })
      
      await Plotly.newPlot(plotDiv, traces, layout, {
        responsive: true,
        displayModeBar: 'hover',
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
      })
    }
    
    histogramInitialized.value = true
    nextTick(() => {
      if (plotDiv && window.Plotly) {
        Plotly.Plots.resize(plotDiv)
      }
    })
  } catch (e) {
    console.warn('Failed to initialize histogram plot:', e)
    histogramInitialized.value = false
  }
}

// Reset view
function resetView() {
  const container = histogramContainer.value
  if (container && window.Plotly) {
    const plot = container.querySelector('#histogram-plot')
    if (plot) {
      Plotly.relayout(plot, {
        'xaxis.autorange': true,
        'yaxis.autorange': true
      })
    }
  }
}

// Download plot
function downloadPlot() {
  const container = histogramContainer.value
  if (container && window.Plotly) {
    const plot = container.querySelector('#histogram-plot')
    if (plot) {
      Plotly.downloadImage(plot, {
        format: 'png',
        width: 1920,
        height: 1080,
        filename: `histogram-${props.negotiation?.id || 'plot'}`
      })
    }
  }
}

// Image error handler for preview mode
function onImageError() {
  console.warn('Failed to load preview image, falling back to interactive mode')
  showInteractive.value = true
}

// Watch for offer changes - throttled and incremental for smooth updates
let updateScheduled = false
let lastRenderedOfferCount = 0
const INCREMENTAL_UPDATE_INTERVAL = 10 // Update every 10 offers

function scheduleUpdate(force = false) {
  // Skip if panel is collapsed - major performance optimization
  if (collapsed.value) return
  
  const currentOfferCount = props.negotiation?.offers?.length || 0
  
  // Incremental updates: only render every N offers or on force
  if (!force && currentOfferCount > 0) {
    const offersSinceLastRender = currentOfferCount - lastRenderedOfferCount
    if (offersSinceLastRender < INCREMENTAL_UPDATE_INTERVAL) {
      return // Skip update
    }
  }
  
  if (updateScheduled) return
  updateScheduled = true
  requestAnimationFrame(() => {
    if (hasOffers.value && !collapsed.value) {
      nextTick(() => {
        initHistogram()
        lastRenderedOfferCount = props.negotiation?.offers?.length || 0
      })
    }
    updateScheduled = false
  })
}

watch(() => props.negotiation?.offers?.length, (newCount, oldCount) => {
  scheduleUpdate()
})

// Force update when negotiation completes
watch(() => props.negotiation?.agreement, (newAgreement) => {
  if (newAgreement !== undefined && newAgreement !== null) {
    scheduleUpdate(true) // Force final render with agreement
  }
})

watch(() => props.negotiation?.end_reason, (newEndReason) => {
  if (newEndReason) {
    scheduleUpdate(true) // Force final render on completion
  }
})

watch(collapsed, (newVal) => {
  if (!newVal && hasOffers.value) {
    nextTick(() => {
      initHistogram()
    })
  }
})

// Watch for switching from preview to interactive mode
watch(showInteractive, (newVal) => {
  if (newVal && hasOffers.value) {
    nextTick(() => {
      initHistogram()
    })
  }
})

// Initialize on mount
onMounted(() => {
  if (hasOffers.value && !collapsed.value) {
    nextTick(() => {
      initHistogram()
    })
  }
})

// Cleanup
onBeforeUnmount(() => {
  if (histogramContainer.value) {
    const plot = histogramContainer.value.querySelector('#histogram-plot')
    if (plot && window.Plotly) {
      Plotly.purge(plot)
    }
  }
})

// Expose methods
defineExpose({
  initHistogram,
  resetView,
  downloadPlot
})
</script>

<style>
/* All styles are in panels.css - no additional styles needed */
</style>
