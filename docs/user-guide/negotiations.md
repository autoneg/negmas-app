# Running Negotiations

This guide covers how to configure, run, and analyze negotiations in NegMAS App.

## Starting a New Negotiation

1. Go to the **Negotiations** page using the sidebar
2. Click **"+ New"** in the header to open the New Negotiation modal

## Configuration Steps

### Step 1: Select a Scenario

The scenario defines the negotiation domain (issues, possible values, and utility functions).

1. Browse the list of available scenarios
2. Use the **search box** to filter by name (e.g., "Amsterdam", "camera")
3. Use **source filters** to narrow by ANAC year or category
4. **Click a scenario card** to select it (highlighted with blue border)
5. Click the **info icon** (ℹ️) to view scenario statistics:
   - Pareto frontier visualization
   - Nash, Kalai, and KS bargaining solutions
   - Opposition vs Outcomes plot
   - Issue details

**Scenario Options:**

- **Ignore discount factors**: Use stationary utilities (ignore time pressure)
- **Ignore reserved values**: Set reserved values to negative infinity

### Step 2: Select Negotiators

Assign negotiation agents to each party in the scenario.

1. Each party slot shows a dropdown with available negotiators
2. **Click a negotiator card** to select it for that slot
3. Click the **info icon** (ℹ️) to view negotiator details:
   - Description and strategy overview
   - Supported mechanisms
   - Configurable parameters

**Available Negotiator Types:**

| Type | Strategy |
|------|----------|
| **AspirationNegotiator** | Starts high, concedes over time based on aspiration function |
| **NaiveTitForTatNegotiator** | Mimics opponent's concession rate |
| **BoulwareNegotiator** | Concedes slowly - tough negotiator |
| **ConcederNegotiator** | Concedes quickly - cooperative negotiator |
| **LinearTFTNegotiator** | Linear tit-for-tat strategy |
| **NiceNegotiator** | Always proposes Pareto-optimal offers |
| **RandomNegotiator** | Makes random valid offers |
| **Genius Agents** | ANAC competition agents (requires Genius Bridge) |

### Step 3: Configure Parameters

#### Mechanism Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| **Max Steps** | Maximum number of negotiation rounds | 100 |
| **Time Limit** | Wall-clock time limit in seconds | None |

#### Run Mode

| Mode | Description | Best For |
|------|-------------|----------|
| **Real-time** | Watch step-by-step with live visualization | Understanding dynamics |
| **Batch** | Run instantly to completion | Quick analysis |

#### Real-time Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| **Step Delay** | Milliseconds between steps (animation speed) | 200 |

### Step 4: Start the Negotiation

1. Choose **Real-time** or **Batch** mode
2. Click **Start Negotiation**
3. For batch mode: View results immediately
4. For real-time mode: Watch the negotiation unfold

## Negotiation View

After starting, you're taken to the single negotiation view with multiple visualization panels.

### Panel Layout

The default layout shows:

```
┌─────────────────────────────────────────────────────────┐
│                     Header Bar                          │
├───────────────┬─────────────────────────────────────────┤
│               │                                         │
│  Offer        │           2D Utility Space              │
│  History      │                                         │
│               │                                         │
├───────────────┼─────────────────────────────────────────┤
│               │                                         │
│  Info         │           Utility Timeline              │
│  Panel        │                                         │
│               │                                         │
└───────────────┴─────────────────────────────────────────┘
```

### 2D Utility Space Panel

Visualizes offers in the utility space for both negotiators.

**Elements:**

- **Gray dots**: Possible outcomes
- **Blue line**: Pareto frontier (optimal trade-offs)
- **Colored markers**: Offers made (color = proposer)
- **Blue diamond** (◆): Nash bargaining solution
- **Orange square** (■): Kalai-Smorodinsky solution
- **Purple diamond** (◇): Max welfare point
- **Red dashed lines**: Reserved values (fallback utilities)
- **Star marker** (★): Final agreement (if reached)

**Interactions:**

- Hover over points to see exact values
- Zoom with scroll wheel
- Pan by dragging
- Double-click to reset view

### Utility Timeline Panel

Shows how utility values evolve over negotiation rounds.

**Elements:**

- One line per negotiator (color-coded)
- X-axis: Step number
- Y-axis: Utility value (0-1)
- Horizontal dashed lines: Reserved values

**Interactions:**

- Hover for exact values at each step
- Zoom to focus on specific regions

### Offer History Panel

Scrollable table showing all offers made.

| Column | Description |
|--------|-------------|
| **Step** | Round number |
| **Proposer** | Who made the offer |
| **Offer** | Issue values |
| **Utilities** | Utility for each negotiator |
| **Response** | Accept/Reject/End |

**Interactions:**

- Click a row to highlight it in other panels
- Scroll to navigate long histories

### Info Panel

Shows current negotiation status.

**During Negotiation:**

- Status: Running / Paused
- Current step / Max steps
- Elapsed time
- Negotiator information

**After Completion:**

- Final status: Agreement / Timeout / Ended
- Agreement details (if reached)
- Final utilities
- Comparison to Nash, Kalai, Max Welfare

### Result Panel

Shown after negotiation completes.

**If Agreement Reached:**

- Agreement values for each issue
- Utility achieved by each negotiator
- Welfare metrics (sum, product, min)
- Comparison to optimal solutions

**If No Agreement:**

- Failure reason (timeout, ended, etc.)
- Reserved values applied
- Best rejected offer (closest to agreement)

### Additional Panels

Available via the panel selector:

| Panel | Description |
|-------|-------------|
| **Histogram** | Distribution of proposed values per issue |
| **Issue Space 2D** | Scatter plot of offers across two issues |

## Controls During Negotiation

### Real-time Mode Controls

| Control | Action |
|---------|--------|
| **Pause** | Pause the negotiation |
| **Resume** | Continue from paused state |
| **Step** | Advance exactly one step |
| **Skip to End** | Complete instantly |

### Panel Controls

| Control | Action |
|---------|--------|
| **Expand** (⤢) | View panel in fullscreen |
| **Collapse** (⤡) | Return to grid layout |
| **Reset Zoom** | Reset chart to default view |

## Viewing Completed Negotiations

### From Negotiations List

1. Go to **Negotiations** page
2. Click any row in the completed negotiations table
3. View full details and visualizations

### Negotiation Details

For completed negotiations, you can see:

- Complete offer history
- Final agreement or failure reason
- All visualization panels
- Export options

## Managing Negotiations

### Deleting Negotiations

1. In the negotiations list, hover over a row
2. Click the delete icon (🗑️)
3. Confirm deletion

### Refreshing Data

Click the refresh button in the header to reload the negotiations list.

## Tips and Best Practices

### Choosing Scenarios

- Start with simple scenarios (few issues) to understand dynamics
- Use ANAC scenarios for realistic domains
- Check the opposition score to gauge difficulty

### Choosing Negotiators

- Use **AspirationNegotiator** for balanced behavior
- Use **BoulwareNegotiator** to test against tough opponents
- Use **ConcederNegotiator** to test against cooperative opponents
- Mix strategies to see how they interact

### Understanding Results

- **Utility > Reserved Value**: Better than no agreement
- **Close to Pareto**: Efficient outcome
- **Close to Nash**: Fair outcome
- **High Welfare**: Good for both parties

### Debugging Failed Negotiations

If negotiations fail (no agreement):

1. Check if reserved values are too high
2. Try increasing max steps
3. Use more cooperative negotiators
4. Check if scenario has viable agreements (Pareto frontier)
