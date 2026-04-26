<template>
  <!-- Issue Space 2D Panel -->
  <div 
    class="panel panel-compact panel-issue-space" 
    :class="{ 'collapsed': collapsed }"
  >
    <span class="panel-collapsed-label" v-show="collapsed">ISSUE SPACE 2D</span>
    
    <!-- Floating Actions (Left side) -->
    <div class="panel-floating-actions panel-floating-actions-left">
      <div v-show="!collapsed" style="display: flex; gap: 4px; align-items: center;">
        <!-- Axis selectors -->
        <div class="panel-inline-controls" v-show="issueNames.length >= 2">
          <select 
            class="form-select form-select-xs" 
            v-model.number="issueXAxis" 
            @change="renderPlot"
            title="X-Axis Issue"
          >
            <option 
              v-for="(name, idx) in issueNames" 
              :key="idx"
              :value="idx"
            >
              {{ name.substring(0, 8) }}
            </option>
          </select>
          <span style="font-size: 9px; opacity: 0.5;">x</span>
          <select 
            class="form-select form-select-xs" 
            v-model.number="issueYAxis" 
            @change="renderPlot"
            title="Y-Axis Issue"
          >
            <option 
              v-for="(name, idx) in issueNames" 
              :key="idx"
              :value="idx"
            >
              {{ name.substring(0, 8) }}
            </option>
          </select>
        </div>
        
        <!-- Action buttons -->
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
      <div ref="plotDiv" style="width: 100%; height: 100%;"></div>
      <div 
        v-show="issueNames.length < 2" 
        class="empty-state-mini" 
        style="position: absolute; inset: 0; background: var(--bg-secondary);"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width: 24px; height: 24px; opacity: 0.4;">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
        <span class="text-muted">Need 2+ issues</span>
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
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['zoom'])

// Refs
const plotDiv = ref(null)
const collapsed = ref(false)
const plotInitialized = ref(false)
const issueXAxis = ref(0)
const issueYAxis = ref(1)

// Computed
const hasOffers = computed(() => {
  return props.negotiation?.offers && props.negotiation.offers.length > 0
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
  // Use central color utility - respects colorblind mode and passed colors
  return getColorsForNegotiation(props.negotiation)
}

// Render plot
async function renderPlot() {
  // Early exit if collapsed - performance optimization
  if (collapsed.value) return
  
  const container = plotDiv.value
  if (!container || issueNames.value.length < 2) return
  
  // Don't render if panel is collapsed or hidden
  if (container.offsetParent === null || container.clientWidth === 0) {
    plotInitialized.value = false
    return
  }
  
  const neg = props.negotiation
  if (!neg || !neg.offers || neg.offers.length === 0) {
    container.innerHTML = ''
    plotInitialized.value = false
    return
  }
  
  try {
    const colors = getPlotColors()
    const negColors = getNegotiatorColors()
    const numAgents = neg.negotiator_names?.length || 2
    const issues = issueNames.value
    
    // Ensure valid axis selection
    const xIdx = Math.min(issueXAxis.value, issues.length - 1)
    const yIdx = Math.min(issueYAxis.value, issues.length - 1)
    
    // Collect data points by agent
    const dataByAgent = []
    for (let i = 0; i < numAgents; i++) {
      dataByAgent.push({ x: [], y: [], text: [] })
    }
    
    neg.offers.forEach((offer, offerIdx) => {
      const offerData = offer.offer
      if (typeof offerData === 'object' && offerData !== null && !Array.isArray(offerData)) {
        const xValue = offerData[issues[xIdx]]
        const yValue = offerData[issues[yIdx]]
        
        if (xValue !== undefined && yValue !== undefined) {
          const agentIdx = offer.proposer_index
          dataByAgent[agentIdx].x.push(xValue)
          dataByAgent[agentIdx].y.push(yValue)
          dataByAgent[agentIdx].text.push(`Step ${offerIdx + 1}<br>${issues[xIdx]}: ${xValue}<br>${issues[yIdx]}: ${yValue}`)
        }
      }
    })
    
    // Create traces
    const traces = []
    for (let agentIdx = 0; agentIdx < numAgents; agentIdx++) {
      if (dataByAgent[agentIdx].x.length > 0) {
        traces.push({
          x: dataByAgent[agentIdx].x,
          y: dataByAgent[agentIdx].y,
          text: dataByAgent[agentIdx].text,
          type: 'scatter',
          mode: 'markers',
          name: neg.negotiator_names?.[agentIdx] || `Agent ${agentIdx + 1}`,
          marker: {
            color: negColors[agentIdx % negColors.length],
            size: 6,
            opacity: 0.7,
            line: {
              color: colors.textColor,
              width: 0.5
            }
          },
          hovertemplate: '%{text}<extra></extra>'
        })
      }
    }
    
    // Add agreement marker if available
    if (neg.agreement && typeof neg.agreement === 'object' && !Array.isArray(neg.agreement)) {
      const agreementX = neg.agreement[issues[xIdx]]
      const agreementY = neg.agreement[issues[yIdx]]
      
      if (agreementX !== undefined && agreementY !== undefined) {
        traces.push({
          x: [agreementX],
          y: [agreementY],
          type: 'scatter',
          mode: 'markers',
          name: 'Agreement',
          marker: {
            color: '#10b981',
            size: 14,
            symbol: 'star',
            line: {
              color: colors.textColor,
              width: 1.5
            }
          },
          hovertemplate: `Agreement<br>${issues[xIdx]}: ${agreementX}<br>${issues[yIdx]}: ${agreementY}<extra></extra>`
        })
      }
    }
    
    const layout = {
      margin: { t: 10, r: 10, b: 40, l: 50 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { 
        family: '-apple-system, BlinkMacSystemFont, sans-serif', 
        size: 10, 
        color: colors.textColor 
      },
      legend: { 
        orientation: 'h', 
        y: 1.02,
        x: 0.5,
        xanchor: 'center',
        font: { color: colors.textColor, size: 9 } 
      },
      xaxis: {
        title: { text: issues[xIdx], font: { size: 10, color: colors.textColor } },
        tickfont: { color: colors.textColor, size: 9 },
        gridcolor: colors.gridColor,
        zeroline: false
      },
      yaxis: {
        title: { text: issues[yIdx], font: { size: 10, color: colors.textColor } },
        tickfont: { color: colors.textColor, size: 9 },
        gridcolor: colors.gridColor,
        zeroline: false
      }
    }
    
    await Plotly.newPlot(container, traces, layout, {
      responsive: true,
      displayModeBar: 'hover',
      modeBarButtonsToRemove: ['lasso2d', 'select2d']
    })
    
    plotInitialized.value = true
    nextTick(() => {
      if (container && window.Plotly) {
        Plotly.Plots.resize(container)
      }
    })
  } catch (e) {
    console.warn('Failed to render issue space plot:', e)
    plotInitialized.value = false
  }
}

// Reset view
function resetView() {
  const container = plotDiv.value
  if (container && window.Plotly) {
    Plotly.relayout(container, {
      'xaxis.autorange': true,
      'yaxis.autorange': true
    })
  }
}

// Download plot
function downloadPlot() {
  const container = plotDiv.value
  if (container && window.Plotly) {
    Plotly.downloadImage(container, {
      format: 'png',
      width: 1920,
      height: 1080,
      filename: `issue-space-2d-${props.negotiation?.id || 'plot'}`
    })
  }
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
    if (hasOffers.value && !collapsed.value && issueNames.value.length >= 2) {
      nextTick(() => {
        renderPlot()
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
  if (!newVal && hasOffers.value && issueNames.value.length >= 2) {
    nextTick(() => {
      renderPlot()
    })
  }
})

// Initialize on mount
onMounted(() => {
  if (hasOffers.value && !collapsed.value && issueNames.value.length >= 2) {
    nextTick(() => {
      renderPlot()
    })
  }
})

// Cleanup
onBeforeUnmount(() => {
  if (plotDiv.value && window.Plotly) {
    Plotly.purge(plotDiv.value)
  }
})

// Expose methods
defineExpose({
  renderPlot,
  resetView,
  downloadPlot
})
</script>

<style>
/* All styles are in panels.css - no additional styles needed */
</style>
