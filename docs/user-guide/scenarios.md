# Scenario Explorer

The Scenario Explorer allows you to browse and analyze negotiation scenarios before using them.

## Accessing the Explorer

Click **Scenarios** in the header navigation.

## Interface Overview

### Left Panel: Scenario List

- **Search**: Filter by scenario name
- **Source Filter**: Filter by ANAC year or source
- **Results**: Scrollable list of matching scenarios

### Right Panel: Scenario Details

Select a scenario to view:
- Overview statistics
- Issue definitions
- File path

## Scenario Information

### Overview

| Field | Description |
|-------|-------------|
| **Source** | Origin (e.g., ANAC 2015, custom) |
| **Parties** | Number of negotiators required |
| **Issues** | Number of negotiation issues |
| **Outcomes** | Total possible outcomes |

### Issues

For each issue:
- **Name**: Issue identifier
- **Type**: Discrete, continuous, or integer
- **Values**: Possible values (for discrete issues)
- **Range**: Min/max (for continuous/integer issues)

## Using Scenarios

### Start a Negotiation

Click **Use in Negotiation** to:
1. Open the negotiation wizard
2. Pre-select this scenario
3. Continue configuration

### Scenario Sources

| Source | Description |
|--------|-------------|
| **ANAC 2010-2022** | Competition scenarios |
| **Custom** | User-added scenarios |
| **Examples** | Built-in example scenarios |

## Adding Custom Scenarios

### Scenario Format

Scenarios are defined with YAML files:

```yaml
# domain.yml
name: "My Scenario"
issues:
  - name: "Price"
    type: "discrete"
    values: ["Low", "Medium", "High"]
  - name: "Quality"
    type: "integer"
    min: 1
    max: 10
```

### Utility Functions

Each party needs a utility file:

```yaml
# party1.yml
ufun_type: "linear_additive"
weights:
  Price: 0.6
  Quality: 0.4
values:
  Price:
    Low: 0.0
    Medium: 0.5
    High: 1.0
  Quality: "linear"  # Linear from min to max
```

### Adding to NegMAS App

1. Create a scenario directory with domain + utility files
2. Add the path in **Settings > Custom Paths**
3. Click **Refresh** in scenario explorer
