# NegMAS App

A modern web GUI for [NegMAS](https://github.com/yasserfarouk/negmas) - the Negotiation Agents and Mechanisms Simulation library.

**Run automated negotiations visually, analyze results in real-time, and explore negotiation scenarios.**

## Features

- **Interactive Negotiations** - Run SAO (Stacked Alternating Offers) negotiations with real-time visualization
- **Rich Visualizations** - 2D utility space plots, utility timelines, offer histograms, and more
- **Scenario Explorer** - Browse and load ANAC competition scenarios (2010-2022)
- **Tournament Mode** - Run tournaments with multiple negotiators across scenarios
- **Customizable Panels** - Flexible panel layout system with drag-and-resize support
- **Dark Mode** - Full dark/light theme support with color-blind friendly palettes
- **Export Results** - Save negotiations as JSON, export plots as images

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv pip install negmas-app

# Or using pip
pip install negmas-app
```

### Running

```bash
# Start the server
negmas-app

# Or with uv
uv run negmas-app
```

Open http://127.0.0.1:8019 in your browser.

### From Source

```bash
# Clone the repository
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app

# Install dependencies
uv sync

# Run the app
uv run negmas-app
```

## Usage

### Running a Negotiation

1. Click **Start Negotiation** on the Negotiations page
2. Select a scenario from the dropdown (or browse in Scenario Explorer)
3. Choose negotiators for each party
4. Configure mechanism parameters (steps, time limit, etc.)
5. Click **Start** to begin the negotiation

### Panels

The negotiation view includes several panels:

| Panel | Description |
|-------|-------------|
| **Info** | Shows scenario name, negotiators, progress |
| **Offer History** | Live stream of offers with utilities |
| **2D Utility View** | Scatter plot of outcome space with Pareto frontier |
| **Utility Timeline** | Per-agent utility over time |
| **Offer Histogram** | Distribution of proposed values per issue |
| **Result** | Final agreement and utilities |

### Layout Presets

Switch between layouts using the dropdown in the header:

- **Default** - Two-column with offer history left, charts right
- **Focus** - Three-column with large center chart
- **Compact** - All panels in tabs, no bottom row
- **Analysis** - All panels visible in stacked mode

## Configuration

Configuration is stored in `~/negmas/app/settings.yaml`:

```yaml
# Negotiator sources - directories to scan for custom negotiators
negotiator_sources:
  - ~/my-negotiators
  - /path/to/more/negotiators

# Scenario sources - additional scenario directories
scenario_sources:
  - ~/my-scenarios

# Default mechanism parameters
default_n_steps: 100
default_time_limit: 180

# Auto-save completed negotiations
auto_save: true
save_path: ~/negmas/app/negotiations
```

Local project config in `negmas_app/settings.yaml` overrides global settings.

## Development

### Setup

```bash
# Clone and install dev dependencies
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app
uv sync

# Run tests
uv run pytest tests/ -v

# Type checking
uv run pyright negmas_app/

# Run the app in development
uv run negmas-app
```

### Project Structure

```
negmas_app/
├── models/          # Pydantic/dataclass models
├── routers/         # FastAPI route handlers
├── services/        # Business logic
├── static/
│   ├── css/         # Stylesheets
│   └── js/          # Panel system, layout manager
├── templates/       # Jinja2 HTML templates
└── main.py          # FastAPI app entry point
```

### Documentation

```bash
# Install docs dependencies
uv pip install -e ".[docs]"

# Serve docs locally
uv run mkdocs serve

# Build docs
uv run mkdocs build
```

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Frontend**: Jinja2 + Alpine.js + Plotly.js
- **Real-time**: Server-Sent Events (SSE)
- **Styling**: Custom CSS with CSS variables
- **Docs**: MkDocs Material

## Related Projects

- [NegMAS](https://github.com/yasserfarouk/negmas) - The underlying negotiation library
- [SCML](https://github.com/yasserfarouk/scml) - Supply Chain Management League

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see the [Contributing Guide](https://yasserfarouk.github.io/negmas-app/development/contributing/) for details.
