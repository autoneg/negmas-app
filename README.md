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
# Start the server
negmas-app

# Open browser at http://127.0.0.1:8019
```

### From Source

```bash
# Clone the repository
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app

# Install dependencies
uv sync --all-extras --dev

# Install local negmas packages (for development)
for x in negmas negmas-llm negmas-genius-agents negmas-negolog negmas-rl; do
    uv pip install -e ../$x
done

# Run the app
negmas-app run
```

## Architecture

NegMAS App is built with a modern stack optimized for real-time visualization:

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Frontend)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Alpine.js  │  │  Plotly.js  │  │     Tabulator       │  │
│  │   (State)   │  │   (Charts)  │  │      (Tables)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
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
| Templates | Jinja2 | Server-side HTML rendering |
| Reactivity | Alpine.js | Client-side state management |
| Visualization | Plotly.js | Interactive charts |
| Data Tables | Tabulator | Rich data grids |
| Real-time | SSE | Server-to-client streaming |

## Documentation

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
