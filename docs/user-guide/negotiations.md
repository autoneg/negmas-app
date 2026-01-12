# Running Negotiations

This guide covers how to configure and run negotiations in NegMAS App.

## Starting a New Negotiation

Click **New Negotiation** in the header or sidebar to open the configuration wizard.

## Configuration Wizard

### Step 1: Scenario Selection

Select the negotiation scenario:

1. **Search**: Type to search all scenarios
2. **Filter by Source**: Filter by ANAC year or custom sources
3. **Click to Select**: Click a scenario card to select it

**Scenario Details** shows:
- Number of issues
- Issue types and values
- Number of parties required

**Utility Function Options**:
- **Ignore discount factors**: Use stationary utilities
- **Ignore reserved values**: Set reserved values to -infinity

### Step 2: Negotiators

Assign negotiation agents to each party:

#### Preset Agents
1. Click a slot to select it
2. Search or browse available negotiators
3. Click a negotiator to assign it

#### Custom BOA Agents
Build custom agents using the BOA (Bidding-Opponent modeling-Acceptance) architecture:
1. Select an **Acceptance Policy**
2. Select an **Offering Policy**
3. Optionally add an **Opponent Model**
4. Click **Apply to Selected Slot**

#### Configuring Parameters
Click the gear icon on any negotiator to configure its parameters:
- Aspiration parameters
- Concession rates
- Strategy-specific options

### Step 3: Parameters

Configure the negotiation mechanism:

#### Mechanism Protocol
- **SAO**: Stacked Alternating Offers (default)
- **TAU**: Time-based Acceptance Utility
- **GB**: General Bargaining

#### Deadline Settings
- **Max Steps**: Maximum number of rounds
- **Time Limit**: Maximum wall-clock time (optional)
- **Pend per Offer**: Offer timeout (optional)

#### Information Sharing
- **Share utility functions**: Give agents access to opponent utilities

### Step 4: Panels

Configure the visualization panels:

#### Utility Space View
- Select which negotiator maps to X-axis
- Select which negotiator maps to Y-axis

#### Timeline View
- Choose X-axis: Step or Time

### Step 5: Run

Choose how to run the negotiation:

#### Real-time Mode
- Watch step-by-step with live updates
- Adjust **Step Delay** for animation speed
- Good for understanding negotiation dynamics

#### Batch Mode
- Run instantly to completion
- View results immediately
- Good for quick analysis

#### Options
- **Show live utility plot**: Enable/disable 2D view
- **Show offer history**: Enable/disable history panel
- **Auto-save**: Save results when complete

## During a Negotiation

### Controls

In real-time mode:
- **Pause/Resume**: Click the pause button
- **Step**: Advance one step at a time
- **Skip to End**: Complete the negotiation instantly

### Understanding the Visualizations

#### 2D Utility Space
- Each point represents an offer
- Color indicates time (lighter = older)
- Current offer is highlighted
- Pareto frontier shown (if available)

#### Utility Timeline
- Line chart showing utility over time
- One line per negotiator
- Hover for exact values

#### Offer History
- Scrollable table of all offers
- Click a row to highlight in other panels
- Color-coded utility values

#### Negotiation Info
- Current status (Running/Completed)
- Progress: Step X / Max Steps
- Elapsed time
- Negotiator details

### Results

When a negotiation completes:

#### Agreement Reached
- **Agreement Details**: Final offer values
- **Utilities**: Value for each negotiator
- **Welfare Metrics**: Nash, Kalai-Smorodinsky, etc.

#### No Agreement
- **Failure Reason**: Why the negotiation failed
- **Best Rejected Offer**: Closest to agreement
- **Reserved Values**: What each agent got

## Managing Negotiations

### Viewing History

Completed negotiations appear in the sidebar. Click to view:
- Full offer history
- Final results
- All visualizations

### Saving Sessions

Save your negotiation configuration for reuse:

1. Configure the negotiation
2. Click **Save** in the wizard header
3. Enter a name for the preset
4. Access saved sessions from **Load** dropdown

### Exporting Results

Export negotiation data:
- **JSON**: Full negotiation data
- **CSV**: Offer history table
- **PNG**: Chart screenshots
