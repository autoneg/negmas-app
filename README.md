# NegMAS App

A modern web GUI for [NegMAS](https://github.com/yasserfarouk/negmas) - the Negotiation Agents and Mechanisms Simulation library.

> **Note**: This project was designed by humans but primarily implemented by AI (Claude Opus 4 and [OpenCode](https://opencode.ai)). The architecture, features, and design decisions were made by the maintainers, while the bulk of the code was generated through AI-assisted development.

**Run automated negotiations visually, analyze results in real-time, and explore negotiation scenarios with a modern Vue.js interface.**

## Features

### Real-time Negotiation Visualization

- **2D Utility Space**: Visualize offers with Pareto frontier, Nash point, Kalai point, and agreement markers
- **Utility Timeline**: Track utilities over negotiation rounds with adjustable axes
- **Offer History**: Complete history with utility values and proposer information
- **Issue Space 2D**: Distribution of offers across two issues with actual issue names
- **Histogram**: Distribution of proposed values per issue
- **Result Analysis**: Compare outcomes against Nash, Kalai, KS, and welfare optima
- **Zoom Modal**: Fullscreen view for any panel

### Tournament System

- **Competition Grid**: Real-time progress grid showing all matchups
  - Summary tab with aggregated agreement percentages
  - Per-scenario tabs with detailed cell status
  - Color-coded cells (running, complete, timeout, error)
- **Live Leaderboard**: Watch rankings update with medals for top 3
- **Negotiations Panel**: Browse all tournament negotiations with utilities and completion status
- **Clickable Negotiations**: Click any negotiation to view full details with offer history
- **Tournament Context**: Navigate from tournament to individual negotiation and back
- **Save/Load**: Persistent storage for completed tournaments

### Scenario Management

- **Scenario Explorer**: Browse 279 ANAC competition scenarios (2010-2022)
- **Quick Filters**: Search and filter by tags, year, domain
- **Statistics Display**: View Pareto frontiers, Nash points, Kalai points, welfare optima
- **Quick Start**: Launch negotiations directly from the explorer
- **Import/Export**: Import scenarios from files or export existing ones

### Negotiator Support

- **Native NegMAS Agents**: All built-in NegMAS negotiators (Aspiration, TitForTat, Boulware, etc.)
- **Genius Agents**: ANAC competition agents via Genius Bridge
- **Custom Parameters**: Configure negotiator-specific settings with full parameter documentation

## Quick Start

### Installation

```bash
# Using pip
pip install negmas-app

# Or using uv (recommended)
uv pip install negmas-app
```

### First-Time Setup

After installation, run the setup command to extract bundled scenarios:

```bash
negmas-app setup
```

This extracts 279 scenarios to `~/negmas/app/scenarios/` and optionally builds caches for faster loading.

### Running

```bash
# Start the app (opens browser at http://127.0.0.1:5174)
negmas-app start

# Kill servers
negmas-app kill

# Restart servers
negmas-app restart
```

### From Source (Development)

```bash
# Clone and setup
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app
./setup-dev.sh

# Run the app
negmas-app start
```

## Architecture

NegMAS App uses a modern Vue.js frontend with a FastAPI backend:

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Frontend)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Vue 3     │  │  Plotly.js  │  │   Vue Router        │  │
│  │   (UI)      │  │   (Charts)  │  │   (Navigation)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │   Pinia     │  │    Vite     │                           │
│  │   (State)   │  │   (Build)   │                           │
│  └─────────────┘  └─────────────┘                           │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP (polling for negotiations, SSE for tournaments)
┌────────────────────────────┴────────────────────────────────┐
│                    FastAPI (Backend)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Routers   │  │  Services   │  │      Models         │  │
│  │   (API)     │  │  (Logic)    │  │   (Dataclasses)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                     NegMAS Library                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Mechanisms  │  │ Negotiators │  │     Scenarios       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
negmas-app/
├── negmas_app/              # Backend (Python/FastAPI)
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   ├── models/              # Data models (dataclasses)
│   └── main.py              # App entry point
├── src/frontend/            # Frontend (Vue.js)
│   └── src/
│       ├── components/      # Reusable Vue components
│       │   └── panels/      # Visualization panels
│       ├── views/           # Page-level components
│       ├── stores/          # Pinia state stores
│       └── router.js        # Route definitions
├── docs/                    # Documentation (MkDocs)
└── tests/                   # Backend tests
```

## Commands

### Application Commands

```bash
negmas-app start              # Start both backend and frontend
negmas-app run                # Synonym for 'start'
negmas-app kill               # Kill both servers
negmas-app restart            # Restart both servers
negmas-app start --port 5174 --backend-port 8019  # Custom ports
negmas-app start --no-dev     # Production mode (no auto-reload)
```

### Setup Commands

```bash
negmas-app setup              # First-time setup (extract scenarios)
negmas-app setup --skip-cache # Skip building cache files
negmas-app setup --force      # Overwrite existing files
negmas-app update-scenarios   # Update scenarios from package
```

### Cache Commands

```bash
negmas-app cache build scenarios --all    # Build all caches
negmas-app cache build scenarios --stats  # Build stats cache only
negmas-app cache clear scenarios --all    # Clear all caches
```

## Documentation

Full documentation is available at: https://yasserfarouk.github.io/negmas-app/

- **[User Guide](https://yasserfarouk.github.io/negmas-app/user-guide/)** - Running negotiations and tournaments
- **[Developer Guide](https://yasserfarouk.github.io/negmas-app/developer-guide/)** - Architecture and extending the app
- **[API Reference](https://yasserfarouk.github.io/negmas-app/developer-guide/api/)** - Backend REST API

### Build Documentation Locally

```bash
# Install mkdocs
pip install mkdocs-material

# Serve docs locally
mkdocs serve

# Build static site
mkdocs build
```

## Configuration

Configuration is stored in `~/negmas/app/settings.yaml`:

```yaml
# Additional scenario directories
scenario_sources:
  - ~/my-scenarios

# Default mechanism parameters
default_n_steps: 100
default_time_limit: 180

# Auto-save settings
auto_save: true
save_path: ~/negmas/app/negotiations
```

## Citation

If you use NegMAS App in your research, please cite:

```bibtex
@inproceedings{mohammad2023negmas,
  title={NegMAS: A Platform for Situated Negotiations},
  author={Mohammad, Yasser and Greenwald, Amy and Nakadai, Shinji},
  booktitle={Proceedings of the 2023 International Conference on 
             Autonomous Agents and Multiagent Systems},
  year={2023}
}
```

## Related Projects

- [NegMAS](https://github.com/yasserfarouk/negmas) - The underlying negotiation library
- [SCML](https://github.com/yasserfarouk/scml) - Supply Chain Management League
- [Genius](http://ii.tudelft.nl/genius/) - Negotiation environment (for Genius agents)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! See the [Contributing Guide](https://yasserfarouk.github.io/negmas-app/developer-guide/contributing/).
