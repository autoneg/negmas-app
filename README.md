# NegMAS App

A modern web GUI for [NegMAS](https://github.com/yasserfarouk/negmas) - the Negotiation Agents and Mechanisms Simulation library.

> **Note**: This project was designed by humans but primarily implemented by AI (Claude Opus 4 and [OpenCode](https://opencode.ai)). The architecture, features, and design decisions were made by the maintainers, while the bulk of the code was generated through AI-assisted development.

**Run automated negotiations visually, analyze results in real-time, and explore negotiation scenarios with a modern Vue.js interface.**

## ⚠️ First-Time Setup Required

After installing NegMAS App, you **must run the setup command** to extract bundled scenarios:

```bash
negmas-app setup
```

This command will:
- Extract 279 scenarios from the bundled `scenarios.zip` file to `~/negmas/app/scenarios/`
- Check for Genius Bridge and offer to download it if not found (required for ANAC/Genius agents)

The app will prompt you interactively if you try to run it without scenarios.

**Safe to run multiple times** - only copies missing files, preserves your modifications.

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
- **Pre-built Caches**: Fast loading with optional pre-generated info, stats, and plots

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

### First-Time Setup

After installation, run the setup command to copy bundled scenarios to your user directory:

```bash
# Copy scenarios to ~/negmas/app/scenarios/
negmas-app setup

# Skip pre-generated cache files (faster, smaller)
negmas-app setup --skip-cache

# Force overwrite existing files
negmas-app setup --force
```

**Important**: Once scenarios are copied to `~/negmas/app/scenarios/`, they take priority over package scenarios. You can customize or add scenarios in this directory without modifying the package.

To update scenarios from the package later:

```bash
# Update scenarios (skips existing by default)
negmas-app update-scenarios

# Force overwrite all scenarios
negmas-app update-scenarios --force
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

### Basic Commands

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
```

### Setup Commands

```bash
# First-time setup (required)
negmas-app setup          # Extract scenarios with cache files

# Setup options
negmas-app setup --skip-cache     # Extract scenarios without cache files
negmas-app setup --force          # Overwrite existing files

# Update scenarios (safe - preserves modifications)
negmas-app update-scenarios       # Add missing scenarios only
negmas-app update-scenarios --force   # Overwrite all scenarios
```

### Cache Management

Caching significantly improves performance by pre-computing scenario information:

```bash
# Build caches
negmas-app cache build scenarios --all              # Build all caches (info, stats, plots)
negmas-app cache build scenarios --info --stats     # Build specific caches
negmas-app cache build scenarios --plots --refresh  # Rebuild plot caches
negmas-app cache build scenarios --stats --compact  # Stats without Pareto points (saves 50% space)

# Build for custom directory
negmas-app cache build scenarios --path ~/my-scenarios --all

# Clear caches
negmas-app cache clear scenarios --all              # Clear all caches
negmas-app cache clear scenarios --plots            # Clear only plots
negmas-app cache clear scenarios --force            # Skip confirmation
```

**Cache Types:**

| Cache Type | Files | Purpose | Size |
|------------|-------|---------|------|
| **Info** | `_info.yaml` | Basic scenario metadata (outcome count, issue names, etc.) | ~1 MB |
| **Stats** | `_stats.yaml` | Pre-computed Pareto frontier, Nash, Kalai, KS points | ~1-5 MB |
| **Plots** | `_plot.webp` or `_plots/` | Pre-rendered outcome space visualizations | ~10-20 MB |

**Performance Impact:**

- **Without caches**: Scenario loading takes 1-5 seconds, stats calculation 2-10 seconds
- **With info cache**: Scenario loading < 100ms
- **With stats cache**: Stats display instant (no calculation)
- **With plot cache**: Plot display instant (no rendering)

**Compact Mode:**

Use `--compact` when building stats to exclude individual Pareto frontier points, saving ~50% disk space. The app will still show Pareto curves by computing them on demand when needed.

### Legacy Commands

```bash
# Alpine.js version (legacy)
negmas-legacy run         # Run old version (for comparison)
negmas-legacy kill        # Kill legacy server
```

## Setup & Scenarios

### First-Time Setup

NegMAS App includes 279 bundled scenarios from ANAC competitions (2010-2022). These are stored as a compressed `scenarios.zip` file (~570 KB) in the package and must be extracted before use.

**Interactive Setup:**

When you first run `negmas-app start`, you'll be prompted to set up scenarios:

```
┌─────────────────── Scenarios Not Found ────────────────────┐
│                                                            │
│  NegMAS App requires scenarios to be extracted from       │
│  the bundled scenarios.zip file.                          │
│                                                            │
│  Scenarios will be extracted to:                          │
│  ~/negmas/app/scenarios                                   │
│                                                            │
└────────────────────────────────────────────────────────────┘

Would you like to extract scenarios now? [Y/n]:
```

The setup wizard will then ask you about cache options:

```
Cache Options

┌──────────┬──────────────────────────────────────┬────────┐
│ Type     │ Description                          │ Size   │
├──────────┼──────────────────────────────────────┼────────┤
│ Info     │ Basic scenario information           │ ~1 MB  │
│          │ → Speeds up scenario browsing        │        │
├──────────┼──────────────────────────────────────┼────────┤
│ Stats    │ Pre-calculated statistics            │ ~1-5MB │
│          │ → Speeds up initial scenario view    │        │
├──────────┼──────────────────────────────────────┼────────┤
│ Plots    │ Pre-rendered visualizations          │ ~10MB  │
│          │ → Instant plot display               │        │
└──────────┴──────────────────────────────────────┴────────┘

Build info cache? [Y/n]:
Build stats cache? [Y/n]:
Build plots cache? [y/N]:
```

**Manual Setup:**

```bash
negmas-app setup
```

### Scenario Directory Structure

After setup, scenarios are organized by competition year:

```
~/negmas/app/scenarios/
├── anac2010/        # 3 scenarios
├── anac2011/        # 9 scenarios
├── anac2012/        # 73 scenarios
├── anac2013/        # 19 scenarios
├── anac2015/        # 16 scenarios
├── anac2016/        # 17 scenarios
├── anac2017/        # 11 scenarios
├── anac2018/        # 5 scenarios
├── anac2019/        # 6 scenarios
├── anac2020/        # 5 scenarios
├── anac2021/        # 51 scenarios
├── anac2022/        # 51 scenarios
└── others/          # 13 scenarios
```

Each scenario directory contains:
- `domain.yml` or `domain.xml` - Domain definition
- `util1.yml`, `util2.yml`, etc. - Utility functions
- `_info.yaml` - Cached scenario info (optional)
- `_stats.yaml` - Cached statistics (optional)
- `_plot.webp` - Cached plot (optional)

### Safe Re-running

The setup command is **safe to run multiple times**:

```bash
negmas-app setup       # Skips existing files, adds missing ones
negmas-app setup --force   # Overwrites everything
```

This is useful if:
- You accidentally deleted some scenarios
- A new version adds more scenarios
- You want to restore default versions

### Custom Scenarios

You can add your own scenarios alongside the bundled ones:

```bash
# Add to user directory
mkdir -p ~/negmas/app/scenarios/my-scenarios
cp my-domain.yml ~/negmas/app/scenarios/my-scenarios/

# Or configure additional paths in settings
echo "scenario_paths:\n  - ~/my-other-scenarios" >> ~/negmas/app/settings.yaml
```

The app will automatically discover and load scenarios from all configured paths.

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
