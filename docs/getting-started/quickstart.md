# Quick Start

Get up and running with NegMAS App in minutes.

## Starting the Application

```bash
negmas-app start
```

This starts:

- **Backend server** on port 8019
- **Frontend server** on port 5174
- Opens your browser to `http://127.0.0.1:5174`

## Running Your First Negotiation

### 1. Open the New Negotiation Dialog

Click the **"+ New"** button in the Negotiations page header.

### 2. Select a Scenario

1. In the **Scenario** section, you'll see a list of available scenarios
2. Use the search box to filter scenarios (try "Amsterdam" or "camera")
3. Click on a scenario card to select it
4. Click the **ℹ️ info icon** to view scenario statistics (Pareto frontier, Nash point, etc.)

### 3. Configure Negotiators

1. In the **Negotiators** section, two slots are shown (one per party)
2. Click on a negotiator card to select a different agent
3. Available negotiators include:
   - **AspirationNegotiator** - Starts high and concedes over time
   - **NaiveTitForTatNegotiator** - Mimics opponent's concession behavior
   - **BoulwareNegotiator** - Concedes slowly (tough negotiator)
   - **ConcederNegotiator** - Concedes quickly (soft negotiator)
4. Click the **ℹ️ info icon** on any negotiator to see its description and parameters

### 4. Adjust Parameters (Optional)

Scroll down to configure mechanism parameters:

- **Max Steps**: Maximum number of rounds (default: 100)
- **Time Limit**: Optional wall-clock time limit in seconds
- **Step Delay**: Animation speed for real-time mode (milliseconds)

### 5. Start the Negotiation

1. Choose your run mode:
   - **Real-time**: Watch step-by-step with live visualization updates
   - **Batch**: Run to completion instantly
2. Click **Start Negotiation**

## Understanding the Interface

### Navigation

The application has five main pages accessible from the sidebar:

- **Negotiations**: Run and view individual negotiations
- **Tournaments**: Run round-robin tournaments comparing strategies
- **Scenarios**: Browse and manage negotiation scenarios
- **Negotiators**: Explore available negotiation agents
- **Configs**: Manage saved configurations

### Negotiation View Panels

When viewing a negotiation, you'll see several visualization panels:

#### 2D Utility Space (Top Right)

- Each point represents an offer
- X-axis: Utility for first negotiator
- Y-axis: Utility for second negotiator
- **Green line**: Pareto frontier (optimal trade-offs)
- **Blue diamond**: Nash bargaining solution
- **Orange square**: Kalai-Smorodinsky solution
- **Star marker**: Final agreement (if reached)

#### Utility Timeline (Bottom Right)

- Shows how utilities evolve over negotiation rounds
- One line per negotiator (color-coded)
- X-axis: Step number or time
- Y-axis: Utility value

#### Offer History (Top Left)

- Scrollable list of all offers made
- Shows: Step, Proposer, Offer values, Utilities
- Click any row to highlight it in other panels

#### Histogram (Bottom Left)

- Distribution of proposed values for each issue
- Helps identify which values are commonly proposed

#### Info Panel

- Current negotiation status
- Negotiator information
- Progress (step/time)
- Final result when complete

### Controls

During a real-time negotiation:

- **Pause/Resume**: Toggle animation
- **Step**: Advance one step at a time
- **Skip to End**: Complete the negotiation instantly
- **Zoom**: Click the expand icon on any panel for fullscreen view

## Running Your First Tournament

### 1. Go to Tournaments Page

Click **Tournaments** in the sidebar.

### 2. Create New Tournament

Click **"+ New"** to open the tournament configuration.

### 3. Select Scenarios

1. In the **Scenarios** section, use the dual-list selector
2. Move scenarios from "Available" to "Selected" using the arrow buttons
3. Or double-click scenarios to move them

### 4. Select Competitors

1. In the **Competitors** section, select the negotiator types to compete
2. These will play against each other on all selected scenarios

### 5. Configure Settings

- **Repetitions**: How many times to repeat each matchup
- **Rotate**: If enabled, each pair plays both positions
- **n_steps**: Deadline for each negotiation

### 6. Start Tournament

Click **Start Tournament** to begin. You'll see:

- **Progress Grid**: Color-coded cells showing match status
- **Leaderboard**: Live rankings with scores
- **Negotiations List**: All negotiations with utilities and status

Click any cell or negotiation to view its full details.

## Next Steps

- [Running Negotiations](../user-guide/negotiations.md) - Detailed negotiation guide
- [Running Tournaments](../user-guide/tournaments.md) - Advanced tournament features
- [Scenario Explorer](../user-guide/scenarios.md) - Browse and import scenarios
