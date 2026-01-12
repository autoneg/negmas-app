# Creating Custom Panels

This guide walks you through creating custom panels for NegMAS App. Custom panels allow you to add new visualizations and data views tailored to your specific needs.

## Overview

A panel is a self-contained UI component that:

1. **Registers** with the Panel Registry
2. **Renders** HTML content based on state
3. **Initializes** any interactive elements
4. **Updates** when state changes
5. **Cleans up** when removed

## Quick Start

Here's a minimal panel that displays the current step:

```javascript
// my-panel.js
PanelRegistry.register('my-step-counter', {
    name: 'Step Counter',
    description: 'Shows the current negotiation step',
    icon: 'counter',
    
    render(state) {
        const step = state.currentNegotiation?.step ?? 0;
        return `
            <div class="step-counter-panel">
                <div class="step-value">${step}</div>
                <div class="step-label">Current Step</div>
            </div>
        `;
    }
});
```

Include it in your HTML:

```html
<script src="/static/js/panel-registry.js"></script>
<script src="/static/js/my-panel.js"></script>
```

## Panel Definition

### Required Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `string` | Display name for the panel |
| `render` | `function` | Returns HTML string |

### Optional Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `description` | `string` | `''` | Tooltip description |
| `icon` | `string` | `'default'` | Icon identifier |
| `category` | `string` | `'custom'` | For panel picker grouping |
| `init` | `function` | `null` | Called after first render |
| `update` | `function` | `null` | Called on state changes |
| `destroy` | `function` | `null` | Called before removal |
| `defaultZone` | `string` | `'right'` | Preferred initial zone |
| `minWidth` | `number` | `200` | Minimum width in pixels |
| `minHeight` | `number` | `100` | Minimum height in pixels |

## Lifecycle Methods

### `render(state)`

Called to generate the panel's HTML content. Must return a string.

```javascript
render(state) {
    const { currentNegotiation } = state;
    
    // Handle no data gracefully
    if (!currentNegotiation) {
        return `<div class="panel-empty">No negotiation selected</div>`;
    }
    
    // Return HTML string
    return `
        <div class="my-panel">
            <h3>${currentNegotiation.scenario}</h3>
            <p>Status: ${currentNegotiation.status}</p>
        </div>
    `;
}
```

!!! warning "Pure Rendering"
    The `render` method should be pure - it only generates HTML based on state.
    Don't attach event listeners or modify DOM here. Use `init` for that.

### `init(element, state)`

Called once after the panel is first rendered and mounted to the DOM.

```javascript
init(element, state) {
    // Find elements
    const button = element.querySelector('.my-button');
    
    // Attach event listeners
    button?.addEventListener('click', () => {
        console.log('Button clicked!');
    });
    
    // Initialize libraries (e.g., Plotly)
    const chartDiv = element.querySelector('.chart');
    if (chartDiv) {
        Plotly.newPlot(chartDiv, [], {});
    }
    
    // Store references for later (optional)
    element._myPanelState = {
        chart: chartDiv,
        button: button
    };
}
```

### `update(element, state)`

Called whenever the application state changes. Use this to efficiently update the panel.

```javascript
update(element, state) {
    const { currentNegotiation } = state;
    if (!currentNegotiation) return;
    
    // Update specific elements instead of re-rendering
    const stepEl = element.querySelector('.step-value');
    if (stepEl) {
        stepEl.textContent = currentNegotiation.step;
    }
    
    // Update charts
    const chart = element._myPanelState?.chart;
    if (chart && currentNegotiation.offers) {
        Plotly.react(chart, getChartData(currentNegotiation), {});
    }
}
```

!!! tip "Performance"
    For frequently updating data (like real-time negotiations), prefer updating
    specific DOM elements in `update()` rather than re-rendering the entire panel.

### `destroy(element)`

Called before the panel is removed. Clean up event listeners, timers, etc.

```javascript
destroy(element) {
    // Clean up Plotly chart
    const chart = element._myPanelState?.chart;
    if (chart) {
        Plotly.purge(chart);
    }
    
    // Remove event listeners if needed
    // (Usually not necessary if element is being removed)
    
    // Clear stored state
    delete element._myPanelState;
}
```

## Complete Example: Welfare Metrics Panel

Here's a complete example of a panel that displays welfare metrics:

```javascript
/**
 * Welfare Metrics Panel
 * Shows social welfare metrics for the current negotiation
 */
PanelRegistry.register('welfare-metrics', {
    name: 'Welfare Metrics',
    description: 'Social welfare analysis of negotiation outcomes',
    icon: 'chart',
    category: 'analysis',
    defaultZone: 'bottomRight',
    minWidth: 250,
    minHeight: 150,
    
    render(state) {
        const neg = state.currentNegotiation;
        
        if (!neg) {
            return `
                <div class="panel-empty">
                    <svg viewBox="0 0 24 24" width="32" height="32">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                    </svg>
                    <p>Select a negotiation to view metrics</p>
                </div>
            `;
        }
        
        return `
            <div class="welfare-metrics-panel">
                <div class="metrics-grid">
                    <div class="metric">
                        <span class="metric-label">Nash Product</span>
                        <span class="metric-value" data-metric="nash">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Social Welfare</span>
                        <span class="metric-value" data-metric="welfare">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Fairness (Gini)</span>
                        <span class="metric-value" data-metric="gini">-</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Pareto Optimal</span>
                        <span class="metric-value" data-metric="pareto">-</span>
                    </div>
                </div>
                <div class="metrics-chart"></div>
            </div>
        `;
    },
    
    init(element, state) {
        // Initialize the chart
        const chartDiv = element.querySelector('.metrics-chart');
        if (chartDiv) {
            Plotly.newPlot(chartDiv, [], {
                margin: { t: 20, r: 20, b: 30, l: 40 },
                height: 150,
                showlegend: false
            }, {
                responsive: true,
                displayModeBar: false
            });
        }
        
        // Store reference
        element._welfareChart = chartDiv;
        
        // Initial update
        this.update(element, state);
    },
    
    update(element, state) {
        const neg = state.currentNegotiation;
        if (!neg || !neg.offers || neg.offers.length === 0) return;
        
        // Calculate metrics
        const metrics = this._calculateMetrics(neg);
        
        // Update metric displays
        element.querySelector('[data-metric="nash"]').textContent = 
            metrics.nash.toFixed(4);
        element.querySelector('[data-metric="welfare"]').textContent = 
            metrics.welfare.toFixed(4);
        element.querySelector('[data-metric="gini"]').textContent = 
            metrics.gini.toFixed(4);
        element.querySelector('[data-metric="pareto"]').textContent = 
            metrics.paretoOptimal ? 'Yes' : 'No';
        
        // Update chart
        const chart = element._welfareChart;
        if (chart) {
            const trace = {
                x: neg.offers.map((_, i) => i),
                y: neg.offers.map(o => this._calculateWelfare(o.utilities)),
                type: 'scatter',
                mode: 'lines',
                name: 'Welfare',
                line: { color: 'var(--primary)' }
            };
            Plotly.react(chart, [trace], {
                margin: { t: 20, r: 20, b: 30, l: 40 },
                height: 150,
                xaxis: { title: 'Step' },
                yaxis: { title: 'Welfare' }
            });
        }
    },
    
    destroy(element) {
        if (element._welfareChart) {
            Plotly.purge(element._welfareChart);
            delete element._welfareChart;
        }
    },
    
    // Helper methods (private by convention)
    _calculateMetrics(neg) {
        const lastOffer = neg.offers[neg.offers.length - 1];
        const utilities = lastOffer?.utilities || [];
        
        return {
            nash: utilities.reduce((a, b) => a * b, 1),
            welfare: this._calculateWelfare(utilities),
            gini: this._calculateGini(utilities),
            paretoOptimal: this._checkParetoOptimal(neg, utilities)
        };
    },
    
    _calculateWelfare(utilities) {
        return utilities.reduce((a, b) => a + b, 0);
    },
    
    _calculateGini(utilities) {
        if (utilities.length < 2) return 0;
        const sorted = [...utilities].sort((a, b) => a - b);
        const n = sorted.length;
        let sum = 0;
        for (let i = 0; i < n; i++) {
            sum += (2 * (i + 1) - n - 1) * sorted[i];
        }
        const mean = sorted.reduce((a, b) => a + b, 0) / n;
        return sum / (n * n * mean) || 0;
    },
    
    _checkParetoOptimal(neg, utilities) {
        // Simplified check - would need Pareto frontier for accuracy
        return neg.pareto_frontier?.some(p => 
            Math.abs(p[0] - utilities[0]) < 0.01 &&
            Math.abs(p[1] - utilities[1]) < 0.01
        ) ?? false;
    }
});
```

## Panel Styling

### Using CSS Variables

Your panel should use CSS variables for consistent theming:

```css
.my-panel {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
}

.my-panel .value {
    color: var(--primary);
    font-weight: var(--font-weight-semibold);
}

.my-panel .muted {
    color: var(--text-muted);
    font-size: var(--font-size-sm);
}
```

### Available CSS Variables

```css
/* Colors */
--primary: #3b82f6;
--success: #10b981;
--warning: #f59e0b;
--danger: #ef4444;

/* Backgrounds */
--bg-primary: #ffffff;
--bg-secondary: #f3f4f6;
--bg-tertiary: #e5e7eb;

/* Text */
--text-primary: #111827;
--text-secondary: #4b5563;
--text-muted: #9ca3af;

/* Spacing */
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 16px;
--spacing-lg: 24px;

/* Borders */
--border-color: #e5e7eb;
--radius-sm: 4px;
--radius-md: 8px;
```

### Color-Blind Mode Support

Check for color-blind mode and use appropriate colors:

```javascript
render(state) {
    const colorBlind = document.documentElement.classList.contains('color-blind-mode');
    const colors = colorBlind 
        ? ['#0072B2', '#E69F00', '#009E73', '#CC79A7']  // Color-blind safe
        : ['#3b82f6', '#ef4444', '#10b981', '#f59e0b']; // Default
    
    // Use colors in your visualization
}
```

## Working with Plotly

Many panels use Plotly.js for charts. Here are best practices:

### Initialization

```javascript
init(element, state) {
    const chartDiv = element.querySelector('.chart');
    
    Plotly.newPlot(chartDiv, [], {
        margin: { t: 30, r: 20, b: 40, l: 50 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: 'var(--text-primary)' },
        xaxis: { gridcolor: 'var(--border-color)' },
        yaxis: { gridcolor: 'var(--border-color)' }
    }, {
        responsive: true,
        displayModeBar: false
    });
}
```

### Efficient Updates

Use `Plotly.react()` for updates instead of `newPlot()`:

```javascript
update(element, state) {
    const chartDiv = element.querySelector('.chart');
    const data = prepareData(state);
    
    // react() efficiently updates existing chart
    Plotly.react(chartDiv, data, chartDiv.layout);
}
```

### Cleanup

Always purge Plotly charts on destroy:

```javascript
destroy(element) {
    const chartDiv = element.querySelector('.chart');
    if (chartDiv) {
        Plotly.purge(chartDiv);
    }
}
```

## Icons

### Using Built-in Icons

The panel registry includes common icons:

```javascript
{
    icon: 'chart',      // Line chart
    icon: 'bar-chart',  // Bar chart
    icon: 'list',       // List view
    icon: 'info',       // Information
    icon: 'settings',   // Settings gear
    icon: 'grid',       // Grid layout
}
```

### Custom SVG Icons

Add custom icons to `PanelIcons`:

```javascript
PanelIcons['my-custom-icon'] = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6v6l4 2"/>
    </svg>
`;

// Then use it
{ icon: 'my-custom-icon' }
```

## Best Practices

### 1. Handle Missing Data

Always check for missing or incomplete data:

```javascript
render(state) {
    const neg = state.currentNegotiation;
    
    if (!neg) {
        return '<div class="panel-empty">No negotiation selected</div>';
    }
    
    if (!neg.offers || neg.offers.length === 0) {
        return '<div class="panel-empty">Waiting for offers...</div>';
    }
    
    // Normal rendering
}
```

### 2. Minimize Re-renders

Use `update()` for incremental changes:

```javascript
// Good: Update specific elements
update(element, state) {
    element.querySelector('.step').textContent = state.currentNegotiation.step;
}

// Bad: Re-render everything
update(element, state) {
    element.innerHTML = this.render(state);  // Avoid this!
}
```

### 3. Clean Up Resources

Always clean up in `destroy()`:

```javascript
destroy(element) {
    // Clear intervals/timeouts
    clearInterval(element._updateInterval);
    
    // Purge charts
    Plotly.purge(element.querySelector('.chart'));
    
    // Remove event listeners on window/document
    window.removeEventListener('resize', element._resizeHandler);
    
    // Clear stored state
    delete element._myState;
}
```

### 4. Use Semantic HTML

Structure your panel content semantically:

```html
<div class="panel-content">
    <header class="panel-header">
        <h3>Panel Title</h3>
    </header>
    <main class="panel-body">
        <!-- Content -->
    </main>
    <footer class="panel-footer">
        <!-- Actions -->
    </footer>
</div>
```

### 5. Support Keyboard Navigation

Make interactive elements keyboard accessible:

```javascript
init(element, state) {
    const buttons = element.querySelectorAll('button');
    buttons.forEach(btn => {
        btn.setAttribute('tabindex', '0');
        btn.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                btn.click();
            }
        });
    });
}
```

## Debugging

### Console Logging

Use namespaced logging:

```javascript
render(state) {
    console.log('[MyPanel] Rendering with state:', state);
    // ...
}
```

### Panel Registry Inspection

```javascript
// List all registered panels
console.log(PanelRegistry.getAll());

// Get specific panel definition
console.log(PanelRegistry.get('my-panel'));
```

### Layout State Inspection

```javascript
// Current layout
console.log(LayoutManager.getActiveLayout());

// Specific zone
console.log(LayoutManager.getZone('right'));
```
