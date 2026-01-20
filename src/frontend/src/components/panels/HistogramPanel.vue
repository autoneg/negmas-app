<template>
  <!-- Issue Frequency / Histogram Panel with Tabs for Issue Space 2D -->
  <div 
    class="panel panel-compact panel-histogram" 
    :class="{ 'collapsed': collapsed }"
  >
    <span class="panel-collapsed-label" v-show="collapsed">HISTOGRAM</span>
    
    <!-- Floating Actions (Left side) -->
    <div class="panel-floating-actions panel-floating-actions-left">
      <!-- Histogram controls -->
      <div v-if="activeTab === 'histogram' && !collapsed" style="display: flex; gap: 4px;">
        <button class="panel-btn" title="Save as Image" @click="$emit('saveHistogramImage')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </button>
        <button class="panel-btn" title="Zoom" @click="$emit('zoomHistogram')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 3 21 3 21 9"/>
            <polyline points="9 21 3 21 3 15"/>
            <line x1="21" y1="3" x2="14" y2="10"/>
            <line x1="3" y1="21" x2="10" y2="14"/>
          </svg>
        </button>
      </div>
      
      <!-- Issue Space 2D controls -->
      <div v-if="activeTab === 'issueSpace' && !collapsed" style="display: flex; gap: 4px; align-items: center;">
        <div class="panel-inline-controls" v-show="issueNames.length >= 2">
          <select 
            class="form-select form-select-xs" 
            v-model.number="issueXAxis" 
            @change="renderIssueSpacePlot"
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
            @change="renderIssueSpacePlot"
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
        <button class="panel-btn" title="Save as Image" @click="$emit('saveIssueSpaceImage')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </button>
        <button class="panel-btn" title="Zoom" @click="$emit('zoomIssueSpace')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 3 21 3 21 9"/>
            <polyline points="9 21 3 21 3 15"/>
            <line x1="21" y1="3" x2="14" y2="10"/>
            <line x1="3" y1="21" x2="10" y2="14"/>
          </svg>
        </button>
        <button class="panel-btn" title="Reset View" @click="resetIssueSpaceView">
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
    
    <!-- Tab Buttons (Centered at top) -->
    <div 
      class="panel-floating-actions" 
      style="left: 50%; transform: translateX(-50%); right: auto;" 
      v-show="!collapsed"
    >
      <div style="display: flex; gap: 2px; padding: 2px; background: var(--bg-tertiary); border-radius: 4px;">
        <button 
          class="panel-tab-btn" 
          :class="{ 'active': activeTab === 'histogram' }"
          @click="switchTab('histogram')"
          style="padding: 4px 8px; font-size: 11px; background: transparent; border: none; cursor: pointer; border-radius: 3px; transition: background 0.2s;"
          :style="activeTab === 'histogram' ? 'background: var(--bg-secondary); font-weight: 500;' : ''"
        >
          Histogram
        </button>
        <button 
          class="panel-tab-btn" 
          :class="{ 'active': activeTab === 'issueSpace' }"
          @click="switchTab('issueSpace')"
          style="padding: 4px 8px; font-size: 11px; background: transparent; border: none; cursor: pointer; border-radius: 3px; transition: background 0.2s;"
          :style="activeTab === 'issueSpace' ? 'background: var(--bg-secondary); font-weight: 500;' : ''"
          :disabled="issueNames.length < 2"
        >
          Issue Space 2D
        </button>
      </div>
    </div>
    
    <!-- Panel Content -->
    <div 
      class="panel-content panel-content-compact" 
      style="padding: 0; position: relative; overflow: hidden;" 
      v-show="!collapsed"
    >
      <!-- Histogram View -->
      <div v-show="activeTab === 'histogram'" style="width: 100%; height: 100%;">
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
      
      <!-- Issue Space 2D View -->
      <div v-show="activeTab === 'issueSpace'" style="width: 100%; height: 100%;">
        <div ref="issueSpaceDiv" style="width: 100%; height: 100%;"></div>
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
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
  negotiation: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['saveHistogramImage', 'zoomHistogram', 'saveIssueSpaceImage', 'zoomIssueSpace'])

// Refs
const histogramContainer = ref(null)
const issueSpaceDiv = ref(null)
const collapsed = ref(false)
const activeTab = ref('histogram')
const histogramInitialized = ref(false)
const issueSpaceInitialized = ref(false)
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
  const isColorBlind = document.documentElement.classList.contains('color-blind-mode')
  if (isColorBlind) {
    return ['#0173b2', '#de8f05', '#029e73', '#cc78bc', '#ca9161', '#fbafe4', '#949494', '#ece133']
  }
  return ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899']
}

// Switch tab
function switchTab(tab) {
  activeTab.value = tab
  nextTick(() => {
    if (tab === 'histogram') {
      initHistogram()
    } else {
      renderIssueSpacePlot()
    }
  })
}

// Initialize histogram
async function initHistogram(retryCount = 0) {
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

// Render issue space 2D plot
async function renderIssueSpacePlot() {
  const plotDiv = issueSpaceDiv.value
  if (!plotDiv || issueNames.value.length < 2) return
  
  // TODO: Implement Issue Space 2D visualization
  // This would show a 2D scatter plot of offers in issue space
  console.log('Issue Space 2D plot - to be implemented')
}

// Reset issue space view
function resetIssueSpaceView() {
  if (issueSpaceDiv.value && window.Plotly) {
    Plotly.Plots.resize(issueSpaceDiv.value)
  }
}

// Watch for offer changes - throttled for smooth updates
let updateScheduled = false
function scheduleUpdate() {
  if (updateScheduled) return
  updateScheduled = true
  requestAnimationFrame(() => {
    if (hasOffers.value && !collapsed.value && activeTab.value === 'histogram') {
      nextTick(() => {
        initHistogram()
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
      if (activeTab.value === 'histogram') {
        initHistogram()
      } else {
        renderIssueSpacePlot()
      }
    })
  }
})

// Initialize on mount
onMounted(() => {
  if (hasOffers.value && !collapsed.value && activeTab.value === 'histogram') {
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
  if (issueSpaceDiv.value && window.Plotly) {
    Plotly.purge(issueSpaceDiv.value)
  }
})

// Expose methods
defineExpose({
  initHistogram,
  renderIssueSpacePlot
})
</script>

<style>
/* All styles are in panels.css - no additional styles needed */
</style>
