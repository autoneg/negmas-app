# NegMAS App

A modern web GUI for [NegMAS](https://github.com/yasserfarouk/negmas) - the Negotiation Agents and Mechanisms Simulation library.

> **Note**: This project was designed by humans but primarily implemented by AI (Claude Opus 4 and [OpenCode](https://opencode.ai)). The architecture, features, and design decisions were made by the maintainers, while the bulk of the code was generated through AI-assisted development.

**Run automated negotiations visually, analyze results in real-time, and explore negotiation scenarios.**

## Features

### Real-time Negotiation Visualization

- **2D Utility Space**: Visualize offers with Pareto frontier overlay
- **Utility Timeline**: Track utilities over negotiation rounds
- **Offer History**: Complete history with utility values
- **Offer Histogram**: Distribution of proposed values per issue
- **Result Analysis**: Compare outcomes against Nash, Kalai, and welfare optima

### Tournament System

- **Grid Visualization**: Real-time progress grid showing all matchups
- **Live Leaderboard**: Watch rankings update as negotiations complete
- **Score Analysis**: Analyze results by metric, scenario, or opponent
- **Raw Data Export**: Access detailed tournament data for analysis

### Scenario Management

- **Scenario Explorer**: Browse ANAC competition scenarios (2010-2022)
- **Scenario Creator**: Design custom scenarios with the built-in wizard
- **Statistics Calculation**: Compute Pareto frontiers, Nash points, and welfare optima
- **Quick Start**: Launch negotiations directly from the explorer

### Negotiator Support

- **Native NegMAS Agents**: All built-in NegMAS negotiators
- **Genius Agents**: ANAC competition agents via Genius Bridge
- **BOA Architecture**: Build custom agents from components
- **Virtual Negotiators**: Save configured agents for reuse

# NegMAS App

A modern web GUI for [NegMAS](https://github.com/yasserfarouk/negmas) - the Negotiation Agents and Mechanisms Simulation library.

> **Note**: This project was designed by humans but primarily implemented by AI (Claude Opus 4 and [OpenCode](https://opencode.ai)). The architecture, features, and design decisions were made by the maintainers, while the bulk of the code was generated through AI-assisted development.

**Run automated negotiations visually, analyze results in real-time, and explore negotiation scenarios with a modern Vue.js interface.**

## Features

### Real-time Negotiation Visualization

- **2D Utility Space**: Visualize offers with Pareto frontier, reserved values, and agreement markers
- **Utility Timeline**: Track utilities over negotiation rounds with adjustable axes
- **Offer History**: Complete history with utility values and proposer information
- **Issue Space 2D**: Distribution of offers across two issues with actual issue names
- **Histogram**: Distribution of proposed values per issue with performance optimizations
- **Result Analysis**: Compare outcomes against Nash, Kalai, KS, and welfare optima
- **Zoom Modal**: Fullscreen view for any panel
- **Stats Modal**: Comprehensive scenario statistics

### Tournament System

- **Competition Grid**: Real-time progress grid showing all matchups
  - Summary tab with aggregated agreement percentages
  - Per-scenario tabs with detailed cell status
  - Color-coded cells (running, complete, timeout, error)
- **Live Leaderboard**: Watch rankings update with medals for top 3
- **Clickable Negotiations**: Navigate from tournament to individual negotiation view
- **Tournament Context**: Breadcrumb and badges showing negotiation source
- **Score Analysis**: Analyze results by metric, scenario, or opponent
- **Save/Load**: Persistent storage for completed tournaments

### Scenario Management

- **Scenario Explorer**: Browse ANAC competition scenarios (2010-2022)
- **Quick Filters**: Search and filter by tags, year, domain
- **Statistics Calculation**: Compute Pareto frontiers, Nash points, and welfare optima
- **Quick Start**: Launch negotiations directly from the explorer

### Negotiator Support

- **Native NegMAS Agents**: All built-in NegMAS negotiators
- **Genius Agents**: ANAC competition agents via Genius Bridge
- **Virtual Negotiators**: Save configured agents for reuse
- **Custom Parameters**: Configure negotiator-specific settings

### Configuration System

- **Session Presets**: Save and load complete negotiation configurations
- **Recent Sessions**: Auto-saved last 10 configurations
- **Tournament Presets**: Save tournament setups for later use
- **Tagging System**: Organize saved negotiations and tournaments

## Quick Start

### Installation

```bash
# Using pip
pip install negmas-app

# Or using uv (recommended)
uv pip install negmas-app
```

### Running

```bash
# Start the app (opens browser at http://127.0.0.1:5174)
negmas-app start

# Alternative command (synonymous)
negmas-app run

# Kill servers
negmas-app kill

# Restart servers
negmas-app restart
```

### From Source

```bash
# Clone the repository
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app

# Run setup script (first time only)
./setup-dev.sh

# Or manually:
# Install dependencies
uv sync --all-extras --dev

# Install local negmas packages (for development)
for x in negmas negmas-llm negmas-genius-agents negmas-negolog negmas-rl; do
    uv pip install -e ../$x
done

# Install frontend dependencies
cd src/frontend && npm install && cd ../..

# Run the app
negmas-app start
```

## Architecture

NegMAS App is built with a modern Vue.js stack optimized for real-time visualization:

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Frontend)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Vue 3     │  │  Plotly.js  │  │   Vue Router        │  │
│  │   (UI)      │  │   (Charts)  │  │   (Navigation)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │   Pinia     │  │    Vite     │                           │
│  │   (State)   │  │   (Build)   │                           │
│  └─────────────┘  └─────────────┘                           │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/SSE
┌────────────────────────────┴────────────────────────────────┐
│                    FastAPI (Backend)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Routers   │  │  Services   │  │      Models         │  │
│  │   (API)     │  │  (Logic)    │  │   (Dataclasses)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                     NegMAS Library                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Mechanisms  │  │ Negotiators │  │     Scenarios       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | REST API, SSE, async support |
| Frontend | Vue 3 | Reactive UI components |
| State Management | Pinia | Centralized state stores |
| Routing | Vue Router | Client-side navigation |
| Build Tool | Vite | Fast dev server and builds |
| Visualization | Plotly.js | Interactive charts (WebGL) |
| Real-time | SSE | Server-to-client streaming |

### Project Structure

```
negmas-app/
├── negmas_app/           # Backend (Python)
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic
│   ├── models/           # Data models
│   └── main.py           # App entry point
├── src/frontend/         # Frontend (Vue.js)
│   ├── src/
│   │   ├── components/   # Reusable components
│   │   ├── views/        # Page components
│   │   ├── stores/       # Pinia stores
│   │   └── router/       # Route definitions
│   └── package.json
├── tests/                # Backend tests
└── _store/               # Legacy Alpine.js version
```

## Commands

```bash
# Start the app
negmas-app start          # Start both backend and frontend
negmas-app run            # Synonym for 'start'

# With options
negmas-app start --port 5174 --backend-port 8019
negmas-app start --no-dev  # Production mode (no auto-reload)

# Manage servers
negmas-app kill           # Kill both servers
negmas-app restart        # Restart both servers

# Legacy Alpine.js version
negmas-legacy run         # Run old version (for comparison)
```

## Documentation

### User Guide

- **Quick Start**: See `QUICK_START.md` for a 5-minute test guide
- **Testing**: See `TESTING_GUIDE.md` for comprehensive testing checklist
- **Deployment**: See `DEPLOYMENT_READY.md` for production deployment

### Developer Guide

- **Architecture**: See `AGENTS.md` for build commands and architecture
- **Session Tracking**: See `SESSION.md` for implementation details
- **Tasks**: See `TASKS.md` for feature completion status

### Testing

```bash
# Frontend tests
cd src/frontend && npm test -- --run

# Backend tests
pytest tests/ -v

# Type checking
pyright negmas_app/
```

Full documentation is available at: https://yasserfarouk.github.io/negmas-app/

- [Installation Guide](https://yasserfarouk.github.io/negmas-app/getting-started/installation/)
- [User Guide](https://yasserfarouk.github.io/negmas-app/user-guide/)
- [Developer Guide](https://yasserfarouk.github.io/negmas-app/developer-guide/)
- [API Reference](https://yasserfarouk.github.io/negmas-app/developer-guide/api/)

## Configuration

Configuration is stored in `~/negmas/app/settings.yaml`:

```yaml
# Negotiator sources - directories to scan for custom negotiators
negotiator_sources:
  - ~/my-negotiators

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

## Citation

If you use NegMAS App in your research, please cite the NegMAS library:

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

Contributions are welcome! Please see the [Contributing Guide](https://yasserfarouk.github.io/negmas-app/developer-guide/contributing/) for details.
