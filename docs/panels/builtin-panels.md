# Built-in Panels

NegMAS App includes several built-in panels for visualizing negotiation data. This reference documents each panel's purpose, data requirements, and configuration options.

## Panel Summary

| Panel ID | Name | Description |
|----------|------|-------------|
| `info` | Negotiation Info | Status, progress, and negotiator details |
| `offer-history` | Offer History | Chronological list of all offers |
| `offer-histogram` | Offer Histogram | Distribution of offer values per issue |
| `utility-2d` | 2D Utility View | Scatter plot in utility space |
| `utility-timeline` | Utility Timeline | Utility values over time |
| `result` | Result | Final agreement and outcome |

---

## Negotiation Info (`info`)

Displays real-time negotiation status and metadata.

### Content

- **Status**: Running, Completed, or Failed
- **Progress**: Current step / max steps
- **Time**: Elapsed time and time limit (if set)
- **Negotiators**: List of participating agents with their types

### Data Requirements

```javascript
state.currentNegotiation = {
    status: 'running' | 'completed' | 'failed',
    step: number,
    max_steps: number | null,
    time_elapsed: number,
    time_limit: number | null,
    negotiators: [
        { name: string, type: string }
    ]
}
```

### Best Zone Placement

- Bottom-left (default)
- Left sidebar (tabbed with other info panels)

---

## Offer History (`offer-history`)

Shows a chronological table of all offers made during the negotiation.

### Content

- **Step Number**: When the offer was made
- **Negotiator**: Who made the offer
- **Offer Values**: The actual offer (issue values)
- **Utilities**: Utility value for each negotiator
- **Response**: Accept, Reject, or Pending

### Data Requirements

```javascript
state.currentNegotiation = {
    offers: [
        {
            step: number,
            negotiator: string,
            offer: { [issue: string]: any },
            utilities: number[],
            response: 'accept' | 'reject' | 'pending'
        }
    ],
    issues: [{ name: string, type: string }]
}
```

### Features

- Scrollable table with fixed header
- Color-coded utilities (higher = greener)
- Click to highlight offer in other panels
- Auto-scroll to latest offer

### Best Zone Placement

- Left zone (stacked or tabbed)
- Good for detailed offer analysis

---

## Offer Histogram (`offer-histogram`)

Visualizes the distribution of offer values across issues.

### Content

For each issue, shows a grouped bar chart:
- X-axis: Issue values
- Y-axis: Number of offers with that value
- Grouped by: Negotiator (different colors)

### Data Requirements

```javascript
state.currentNegotiation = {
    offers: [...],
    issues: [
        { 
            name: string, 
            type: 'discrete' | 'continuous',
            values: string[] | null,  // For discrete
            min: number | null,       // For continuous
            max: number | null
        }
    ],
    negotiators: [{ name: string }]
}
```

### Features

- Supports both discrete and continuous issues
- Groups bars by negotiator
- Interactive: hover for details
- Responds to color-blind mode

### Best Zone Placement

- Left zone (tabbed with offer-history)
- Right zone (if analyzing offer patterns)

---

## 2D Utility View (`utility-2d`)

Scatter plot showing offers in the utility space of two negotiators.

### Content

- **X-axis**: Utility for Negotiator A
- **Y-axis**: Utility for Negotiator B
- **Points**: Each offer plotted by its utilities
- **Pareto Frontier**: Line showing efficient outcomes (optional)
- **Current Offer**: Highlighted with different marker

### Data Requirements

```javascript
state.currentNegotiation = {
    offers: [
        {
            utilities: [number, number],  // [utilA, utilB]
            step: number
        }
    ],
    pareto_frontier: [[number, number], ...] | null,
    agreement: { utilities: [number, number] } | null
}
```

### Configuration

Configure which negotiators map to X and Y axes in the Panels tab of the negotiation wizard:

```javascript
newNeg.panels.utilityView = {
    xAxis: 0,  // Index of negotiator for X-axis
    yAxis: 1   // Index of negotiator for Y-axis
}
```

### Features

- Color-coded by time (older = lighter)
- Hover for offer details
- Agreement point highlighted
- Optional Pareto frontier overlay
- Zoom and pan enabled

### Best Zone Placement

- Right zone (stacked with timeline)
- Center zone (in Focus layout)

---

## Utility Timeline (`utility-timeline`)

Line chart showing how utilities evolve over the negotiation.

### Content

- **X-axis**: Step number (or time)
- **Y-axis**: Utility value
- **Lines**: One per negotiator
- **Markers**: Key events (agreement, etc.)

### Data Requirements

```javascript
state.currentNegotiation = {
    offers: [
        {
            step: number,
            time: number,  // Optional
            utilities: number[]
        }
    ],
    negotiators: [{ name: string }]
}
```

### Configuration

```javascript
newNeg.panels.timeline = {
    xAxis: 'step' | 'time'  // What to use for X-axis
}
```

### Features

- Multiple line series (one per negotiator)
- Distinct line styles in color-blind mode
- Hover for exact values
- Auto-scaling Y-axis
- Legend with toggleable series

### Best Zone Placement

- Right zone (stacked below utility-2d)
- Good for seeing negotiation dynamics

---

## Result (`result`)

Displays the final outcome of the negotiation.

### Content

**When Agreement Reached:**
- Agreement details (issue values)
- Final utilities for each negotiator
- Social welfare metrics

**When No Agreement:**
- Reason for failure
- Best offer that was rejected
- Reservation values

### Data Requirements

```javascript
state.currentNegotiation = {
    status: 'completed',
    agreement: {
        offer: { [issue: string]: any },
        utilities: number[],
        step: number
    } | null,
    failure_reason: string | null,
    best_rejected_offer: {...} | null
}
```

### Features

- Clear success/failure indication
- Welfare metrics (Nash, Kalai-Smorodinsky)
- Comparison to optimal outcomes
- Export result option

### Best Zone Placement

- Bottom-right (default)
- Tabbed with info in compact layouts

---

## Common Panel Features

All panels share these capabilities:

### Lifecycle Methods

```javascript
{
    render(state) { ... },      // Generate HTML
    init(element, state) { },   // Called once after mount
    update(element, state) { }, // Called on state change
    destroy(element) { }        // Cleanup before unmount
}
```

### State Access

Panels receive the full negotiation state object:

```javascript
function update(element, state) {
    const { currentNegotiation } = state;
    if (!currentNegotiation) return;
    
    // Access negotiation data
    const { offers, negotiators, issues } = currentNegotiation;
}
```

### Theme Support

Panels automatically adapt to:
- Light/dark mode
- Color-blind friendly palette
- Custom CSS variables

### Error Handling

Panels gracefully handle missing data:

```javascript
render(state) {
    if (!state.currentNegotiation) {
        return '<div class="panel-empty">Select a negotiation</div>';
    }
    // Normal rendering...
}
```
