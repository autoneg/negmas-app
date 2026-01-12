# Running Tournaments

Tournaments allow you to compare negotiation strategies across multiple scenarios.

## Creating a Tournament

1. Go to the **Tournaments** page
2. Click **New** to open the tournament wizard

## Tournament Configuration

### Step 1: Scenarios

Select which scenarios to include:

1. **Search**: Filter scenarios by name
2. **Select**: Click scenarios to add/remove them
3. **Select All**: Include all scenarios
4. **Clear All**: Remove all selections

**Tip**: For meaningful comparisons, select scenarios with similar characteristics (same number of parties, similar complexity).

### Step 2: Competitors

Select which negotiator types to compete:

1. **Search**: Filter negotiators by name
2. **Select**: Click to add/remove competitors
3. **Minimum**: At least 2 competitors required

**Note**: All competitors will play against each other on each scenario.

### Step 3: Settings

Configure tournament parameters:

#### Basic Settings

| Setting | Description |
|---------|-------------|
| **Repetitions** | How many times to repeat each pairing |
| **Max Steps** | Deadline for each negotiation |
| **Mechanism** | Protocol to use (default: SAO) |

#### Scoring

| Metric | Description |
|--------|-------------|
| **Advantage** | Utility relative to opponent |
| **Utility** | Raw utility achieved |
| **Welfare** | Social welfare contribution |

#### Options

- **Rotate Utility Functions**: Each pair plays both positions
- **Allow Self-Play**: Include agent vs itself matches

## Running a Tournament

Click **Start Tournament** to begin.

### Progress Tracking

While running:
- **Progress Bar**: Overall completion percentage
- **Current Match**: Which scenario/competitors are playing
- **Live Updates**: Results update in real-time

### Canceling

Click **Cancel** to stop a running tournament. Partial results are preserved.

## Tournament Results

### Summary Statistics

| Stat | Description |
|------|-------------|
| **Total Negotiations** | Number of negotiations run |
| **Total Agreements** | Negotiations reaching agreement |
| **Agreement Rate** | Percentage of agreements |
| **Duration** | Total execution time |

### Final Rankings

| Column | Description |
|--------|-------------|
| **Rank** | Position (1 = winner) |
| **Competitor** | Agent name and type |
| **Score** | Final score (based on chosen metric) |
| **Utility** | Average utility achieved |
| **Agreements** | Agreement count / total negotiations |

### Analyzing Results

Click on a tournament to see:
- Full rankings table
- Per-scenario breakdown
- Head-to-head comparisons

## Best Practices

### Scenario Selection

- Use diverse scenarios for robust comparisons
- Include both simple and complex scenarios
- Match scenario requirements to competitor capabilities

### Competitor Selection

- Include baseline strategies (e.g., Boulware, Conceder)
- Test similar strategies against each other
- Include both simple and sophisticated agents

### Repetitions

- Use 3-5 repetitions for preliminary results
- Use 10+ repetitions for statistical significance
- More repetitions for stochastic strategies

### Interpreting Results

- High utility doesn't mean good strategy (opponent matters)
- Advantage score accounts for opponent difficulty
- Agreement rate shows cooperativeness
- Consider per-scenario performance
