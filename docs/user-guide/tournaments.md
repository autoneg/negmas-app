# Running Tournaments

Tournaments allow you to compare negotiation strategies by running round-robin competitions across multiple scenarios.

## Overview

A tournament runs all combinations of:

- **Competitors**: Negotiator types that compete against each other
- **Opponents** (optional): Fixed negotiators that all competitors face
- **Scenarios**: Negotiation domains to test on

Each matchup runs a negotiation, and results are aggregated into scores and rankings.

## Creating a Tournament

### 1. Open Tournament Wizard

1. Go to **Tournaments** page via the sidebar
2. Click **"+ New"** in the header

### 2. Tournament Wizard Steps

The wizard has multiple steps accessible via tabs or the **Next** button:

#### Step 1: Basic Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Tournament Name** | Identifier for saving/loading | Auto-generated |
| **Repetitions** | Times to repeat each matchup | 1 |
| **Rotate** | Play both positions (A vs B and B vs A) | true |
| **Save to Disk** | Persist results for later viewing | true |

#### Step 2: Scenarios

Select negotiation scenarios for the tournament:

1. **Available List** (left): All scenarios
2. **Selected List** (right): Scenarios included in tournament
3. Use **arrow buttons** or **double-click** to move scenarios
4. Click **info icon** (ℹ️) to view scenario statistics
5. Use **search** to filter scenarios
6. Use **Select All** / **Clear All** for bulk selection

**Tips:**

- Start with 5-10 scenarios for quick tournaments
- Mix simple and complex scenarios for balanced testing
- Filter by ANAC year for themed tournaments

#### Step 3: Competitors

Select negotiator types to compete against each other:

1. **Available List**: All negotiator types
2. **Selected List**: Competitors in the tournament
3. Move negotiators using arrows or double-click
4. Click **info icon** (ℹ️) for negotiator details

**Minimum**: 2 competitors required

**Competition Matrix**: With N competitors and rotation enabled, each pair plays 2 × repetitions × scenarios negotiations.

#### Step 4: Opponents (Optional)

Fixed opponents that all competitors face (not competing for ranking):

- Useful for testing against specific baselines
- Opponents don't appear in the leaderboard
- Each competitor plays against each opponent on each scenario

#### Step 5: Mechanism Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **n_steps** | Maximum steps per negotiation | 100 |
| **time_limit** | Time limit per negotiation (seconds) | None |
| **hidden_time_limit** | Hidden deadline (seconds) | None |

#### Step 6: Save/Load

- **Save Configuration**: Save current setup for reuse
- **Load Configuration**: Load a previously saved tournament config
- **Recent Tournaments**: Quick access to recent configurations

### 3. Start Tournament

Click **Start Tournament** to begin execution.

## Tournament View

After starting, you're taken to the tournament view with real-time progress.

### Tournament Layout

```
┌─────────────────────────────────────────────────────────┐
│              Tournament Header & Progress               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                Competition Grid                         │
│            (Competitor × Opponent matrix)               │
│                                                         │
├────────────────────────┬────────────────────────────────┤
│                        │                                │
│     Leaderboard        │    Negotiations List           │
│     (Rankings)         │    (All matchups)              │
│                        │                                │
└────────────────────────┴────────────────────────────────┘
```

### Competition Grid Panel

Visual matrix showing all matchups:

**Axes:**

- **Rows**: Competitors (or scenarios if aggregated)
- **Columns**: Opponents (competitors + fixed opponents)

**Cell Colors:**

| Color | Meaning |
|-------|---------|
| Gray | Pending |
| Blue (pulsing) | Running |
| Green | Agreement reached |
| Orange | Timeout (no agreement) |
| Red | Error |
| Dark gray | Skipped (self-play disabled) |

**Cell Content:**

- Shows utilities (e.g., "0.72 / 0.65")
- Color intensity indicates utility value

**Interactions:**

- **Hover**: See full details tooltip
- **Click**: Open that negotiation in full view

### Leaderboard Panel

Real-time rankings as negotiations complete:

| Column | Description |
|--------|-------------|
| **Rank** | Position (🥇🥈🥉 for top 3) |
| **Competitor** | Negotiator name |
| **Score** | Aggregate score |
| **Utility** | Average utility achieved |
| **Agreements** | Agreement count / total |

**Scoring Methods:**

- **Advantage**: Utility relative to opponent average
- **Utility**: Raw utility achieved
- **Welfare**: Social welfare contribution

### Negotiations Panel

List of all tournament negotiations:

**Each Row Shows:**

- Negotiator names (both parties)
- Scenario name
- Utilities achieved (color-coded)
- Completion status (Agreement/Timeout/Ended/Error)
- Step count

**Interactions:**

- **Click row**: Expand to show offer summary
- **Click "Open Full View"**: View complete negotiation details

### Progress Indicators

**Header Progress Bar:**

- Shows percentage complete
- Displays current negotiation count

**Status Indicators:**

- Total negotiations planned
- Negotiations completed
- Agreements reached
- Average utility

## Viewing Completed Tournaments

### From Tournaments List

1. Go to **Tournaments** page
2. View the list of saved tournaments
3. Click any row to open tournament details

### Tournament Details

For completed tournaments:

- Full competition grid
- Final leaderboard
- Complete negotiations list
- All negotiations viewable in detail

## Tournament Controls

### During Execution

| Control | Action |
|---------|--------|
| **Pause** | Pause tournament (finish current negotiation) |
| **Resume** | Continue from paused state |
| **Cancel** | Stop tournament, keep partial results |

### Panel Controls

| Control | Action |
|---------|--------|
| **Expand** (⤢) | View panel fullscreen |
| **Export** | Export data to CSV/JSON |

## Advanced Features

### Viewing Individual Negotiations

1. Click any cell in the competition grid, OR
2. Click any row in the negotiations panel, OR
3. Click "Open Full View" in expanded row

This opens the full single-negotiation view with:

- Complete offer history
- All visualization panels
- Detailed results

### Exporting Results

**Grid Export:**

- Screenshot of competition grid
- CSV of cell values

**Leaderboard Export:**

- CSV with all rankings and scores

**Negotiations Export:**

- Full negotiation traces
- CSV with all offers and utilities

### Comparing Tournaments

Run multiple tournaments with different:

- Competitor sets
- Scenarios
- Settings

Compare leaderboards to see how rankings change.

## Best Practices

### Tournament Design

| Goal | Recommendation |
|------|----------------|
| **Quick test** | 2-3 competitors, 5 scenarios, 1 repetition |
| **Thorough comparison** | 5+ competitors, 20+ scenarios, 3 repetitions |
| **Statistical significance** | 10+ repetitions, diverse scenarios |

### Scenario Selection

- **Diverse complexity**: Mix simple (2 issues) and complex (10+ issues)
- **Diverse opposition**: Include high and low opposition scenarios
- **Consistent requirements**: All scenarios should match competitor capabilities

### Competitor Selection

- **Include baselines**: Always include standard strategies (Boulware, Conceder)
- **Test variations**: Compare similar strategies with different parameters
- **Balance complexity**: Mix simple and sophisticated agents

### Interpreting Results

| Metric | Interpretation |
|--------|----------------|
| **High utility, low agreements** | Aggressive but inefficient |
| **High agreements, low utility** | Cooperative but possibly exploited |
| **High advantage score** | Consistently outperforms opponents |
| **Consistent across scenarios** | Robust strategy |

### Troubleshooting

**Tournaments running slowly:**

- Reduce repetitions for initial testing
- Use smaller scenario sets
- Check for Genius Bridge issues (Java agents are slower)

**Many failed negotiations:**

- Check reserved values in scenarios
- Increase max steps
- Verify negotiator compatibility with scenarios

**Unexpected rankings:**

- Check if some negotiators fail on certain scenarios
- Look at per-scenario breakdown
- Verify scoring method matches your goals
