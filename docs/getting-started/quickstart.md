# Quick Start

Get up and running with NegMAS App in minutes.

## Starting the Server

```bash
negmas-app
```

This starts the server at http://127.0.0.1:8019. Open this URL in your browser.

## Running Your First Negotiation

### 1. Open the New Negotiation Dialog

Click the **"New Negotiation"** button in the header or sidebar.

### 2. Select a Scenario

1. In the **Scenario** tab, search for a scenario or browse by source
2. Try searching for "Amsterdam" - a classic bilateral negotiation
3. Click on the scenario card to select it

### 3. Configure Negotiators

1. Switch to the **Negotiators** tab
2. Two default negotiators are already assigned
3. To change a negotiator:
   - Click on a slot to select it
   - Search or browse for a different negotiator type
   - Click on a negotiator card to assign it

### 4. Adjust Parameters (Optional)

1. Switch to the **Parameters** tab
2. Set the deadline (e.g., 100 steps)
3. Choose the mechanism protocol (SAO is default)

### 5. Start the Negotiation

1. Switch to the **Run** tab
2. Choose **Real-time** mode to watch step-by-step
3. Click **Start Negotiation**

## Understanding the Interface

### Main Panels

- **Left Zone**: Offer History and Histogram
- **Right Zone**: 2D Utility Space and Timeline
- **Bottom**: Negotiation Info and Results

### Reading the Visualizations

#### 2D Utility View
- Each point is an offer
- X-axis: Utility for Negotiator 1
- Y-axis: Utility for Negotiator 2
- Points closer to top-right are better for both

#### Utility Timeline
- Shows how utilities evolve over time
- Multiple lines (one per negotiator)
- Watch for convergence patterns

#### Offer History
- Chronological list of all offers
- Shows who made each offer
- Color-coded utility values

## Next Steps

- [Running Negotiations](../user-guide/negotiations.md) - Detailed guide
- [Running Tournaments](../user-guide/tournaments.md) - Compare strategies
- [Panel System](../panels/index.md) - Customize your workspace
