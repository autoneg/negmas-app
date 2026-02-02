# Creating Custom Panels

This guide walks you through creating custom visualization panels for NegMAS App using Vue.js.

## Overview

Panels are Vue single-file components that display negotiation data. They:

1. Accept data via **props**
2. Render visualizations using **Plotly.js** or other libraries
3. React to data changes via Vue's **reactivity system**
4. Support expand/collapse via the **BasePanel** wrapper

## Quick Start

### 1. Create Panel Component

Create a new file in `src/frontend/src/components/panels/`:

```vue
<!-- MyCustomPanel.vue -->
<template>
  <BasePanel 
    title="My Custom Panel"
    :expanded="expanded"
    @toggle="expanded = !expanded"
  >
    <div class="panel-content">
      <div v-if="!data" class="empty-state">
        No data available
      </div>
      <div v-else class="my-visualization">
        <p>Current step: {{ data.step }}</p>
        <p>Status: {{ data.status }}</p>
      </div>
    </div>
  </BasePanel>
</template>

<script setup>
import { ref } from 'vue'
import BasePanel from './BasePanel.vue'

// Props
const props = defineProps({
  data: Object,
  config: Object
})

// Local state
const expanded = ref(false)
</script>

<style scoped>
.panel-content {
  padding: 12px;
}

.empty-state {
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
}

.my-visualization {
  /* Your styles */
}
</style>
```

### 2. Import and Use

In your view component (e.g., `SingleNegotiationView.vue`):

```vue
<script setup>
import MyCustomPanel from '@/components/panels/MyCustomPanel.vue'
</script>

<template>
  <div class="panel-grid">
    <!-- Other panels -->
    <MyCustomPanel :data="negotiationData" />
  </div>
</template>
```

## Panel Structure

### BasePanel Wrapper

Always wrap your content in `BasePanel` for consistent styling:

```vue
<template>
  <BasePanel 
    title="Panel Title"
    :expanded="expanded"
    @toggle="expanded = !expanded"
    :loading="loading"
    :error="error"
  >
    <template #header-actions>
      <!-- Optional custom header buttons -->
      <button @click="refresh">Refresh</button>
    </template>
    
    <div class="panel-content">
      <!-- Your content -->
    </div>
  </BasePanel>
</template>
```

### BasePanel Props

| Prop | Type | Description |
|------|------|-------------|
| `title` | `string` | Panel title in header |
| `expanded` | `boolean` | Whether panel is fullscreen |
| `loading` | `boolean` | Shows loading spinner |
| `error` | `string` | Shows error message |

### BasePanel Events

| Event | Description |
|-------|-------------|
| `@toggle` | Emitted when expand/collapse clicked |

## Creating Chart Panels

Most panels display Plotly.js charts. Here's the pattern:

```vue
<template>
  <BasePanel title="My Chart" :expanded="expanded" @toggle="expanded = !expanded">
    <div ref="chartContainer" class="chart-container"></div>
  </BasePanel>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import Plotly from 'plotly.js-dist-min'
import BasePanel from './BasePanel.vue'

const props = defineProps({
  data: Array,
  config: Object
})

const chartContainer = ref(null)
const expanded = ref(false)

// Chart layout configuration
const layout = {
  margin: { t: 30, r: 20, b: 40, l: 50 },
  xaxis: { title: 'X Axis' },
  yaxis: { title: 'Y Axis' },
  showlegend: true
}

const plotConfig = {
  responsive: true,
  displayModeBar: true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d']
}

function updateChart() {
  if (!chartContainer.value || !props.data?.length) return
  
  const traces = [{
    x: props.data.map(d => d.x),
    y: props.data.map(d => d.y),
    type: 'scatter',
    mode: 'markers',
    name: 'Data Points'
  }]
  
  Plotly.react(chartContainer.value, traces, layout, plotConfig)
}

// Resize chart when expanded changes
function handleResize() {
  if (chartContainer.value) {
    Plotly.Plots.resize(chartContainer.value)
  }
}

// Watch for data changes
watch(() => props.data, updateChart, { deep: true })

// Watch for expand/collapse
watch(expanded, async () => {
  await nextTick()
  handleResize()
})

// Initial render
onMounted(() => {
  updateChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartContainer.value) {
    Plotly.purge(chartContainer.value)
  }
})
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
</style>
```

## Common Panel Patterns

### Handling Empty State

```vue
<template>
  <BasePanel title="My Panel">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      Loading...
    </div>
    
    <div v-else-if="!data" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>No data to display</p>
    </div>
    
    <div v-else class="panel-content">
      <!-- Actual content -->
    </div>
  </BasePanel>
</template>
```

### Incremental Chart Updates

For real-time data, use `Plotly.extendTraces` instead of full re-renders:

```javascript
function addDataPoint(point) {
  if (!chartContainer.value) return
  
  Plotly.extendTraces(chartContainer.value, {
    x: [[point.x]],
    y: [[point.y]]
  }, [0])  // Trace index
}

// Watch for new offers
watch(() => props.offers?.length, (newLen, oldLen) => {
  if (newLen > oldLen && props.offers) {
    const newOffers = props.offers.slice(oldLen)
    newOffers.forEach(addDataPoint)
  }
})
```

### Responding to User Interaction

```vue
<script setup>
const emit = defineEmits(['select', 'highlight'])

function handlePointClick(event) {
  const pointIndex = event.points[0].pointIndex
  emit('select', props.data[pointIndex])
}

onMounted(() => {
  chartContainer.value?.on('plotly_click', handlePointClick)
})
</script>
```

## Data Sources

### Negotiation Data

Available via props from parent views:

| Prop | Type | Description |
|------|------|-------------|
| `offers` | `Array` | List of offer events |
| `negotiators` | `Array` | Negotiator info |
| `scenario` | `Object` | Scenario details |
| `status` | `String` | 'running', 'completed', etc. |
| `stats` | `Object` | Pareto, Nash, etc. |

### Tournament Data

| Prop | Type | Description |
|------|------|-------------|
| `gridInit` | `Object` | Grid structure |
| `cellStates` | `Object` | Cell status map |
| `leaderboard` | `Array` | Rankings |
| `negotiations` | `Array` | All negotiations |

## Styling Guidelines

### CSS Variables

Use CSS variables for consistent theming:

```css
.my-panel {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.highlight {
  color: var(--accent-color);
}
```

### Panel Sizes

Panels should be responsive. Avoid fixed dimensions:

```css
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 200px;  /* Reasonable minimum */
}
```

### Scoped Styles

Always use `<style scoped>` to prevent style leakage:

```vue
<style scoped>
/* These styles only affect this component */
.panel-content {
  padding: 12px;
}
</style>
```

## Best Practices

### 1. Performance

- Use `Plotly.react` (not `Plotly.newPlot`) for updates
- Debounce frequent updates
- Clean up event listeners in `onUnmounted`

### 2. Accessibility

- Include labels on charts
- Provide text alternatives for visual data
- Support keyboard navigation where possible

### 3. Error Handling

```vue
<script setup>
const error = ref(null)

async function loadData() {
  try {
    error.value = null
    // ... load data
  } catch (e) {
    error.value = e.message
    console.error('Panel error:', e)
  }
}
</script>

<template>
  <BasePanel :error="error">
    <!-- ... -->
  </BasePanel>
</template>
```

### 4. Testing

Test your panel with:

- No data (empty state)
- Single data point
- Large datasets
- Rapid updates
- Resize events

## Example: Custom Statistics Panel

Here's a complete example showing negotiation statistics:

```vue
<!-- StatsPanel.vue -->
<template>
  <BasePanel title="Statistics" :expanded="expanded" @toggle="expanded = !expanded">
    <div v-if="!stats" class="empty-state">
      No statistics available
    </div>
    
    <div v-else class="stats-grid">
      <div class="stat-item">
        <div class="stat-label">Nash Distance</div>
        <div class="stat-value">{{ formatNumber(stats.nash_distance) }}</div>
      </div>
      
      <div class="stat-item">
        <div class="stat-label">Pareto Distance</div>
        <div class="stat-value">{{ formatNumber(stats.pareto_distance) }}</div>
      </div>
      
      <div class="stat-item">
        <div class="stat-label">Social Welfare</div>
        <div class="stat-value">{{ formatNumber(stats.welfare) }}</div>
      </div>
      
      <div class="stat-item">
        <div class="stat-label">Fairness</div>
        <div class="stat-value">{{ formatNumber(stats.fairness) }}</div>
      </div>
    </div>
  </BasePanel>
</template>

<script setup>
import { ref, computed } from 'vue'
import BasePanel from './BasePanel.vue'

const props = defineProps({
  stats: Object
})

const expanded = ref(false)

function formatNumber(value) {
  if (value == null) return '—'
  return value.toFixed(3)
}
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 12px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  font-family: monospace;
}

.empty-state {
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
}
</style>
```

## Next Steps

- [Built-in Panels](builtin-panels.md) - See existing panel implementations
- [Panel API Reference](api-reference.md) - Full API documentation
- [Layout System](layout-system.md) - How panels are arranged
