# NegMAS App

**A Visual Interface for Automated Negotiation**

NegMAS App is a web-based GUI for the [NegMAS](https://github.com/yasserfarouk/negmas) automated negotiation library. It provides an intuitive interface for running, visualizing, and analyzing automated negotiations.

!!! info "AI-Assisted Development"
    This project was designed by humans but primarily implemented by AI (Claude Opus 4 and [OpenCode](https://opencode.ai)). The architecture, features, and design decisions were made by the maintainers, while the bulk of the code was generated through AI-assisted development.

## Key Features

### Real-time Negotiation Visualization

Watch negotiations unfold step-by-step with live updates:

- **2D Utility Space**: Visualize offers in the utility space with Pareto frontier overlay
- **Utility Timeline**: Track how utilities evolve over negotiation rounds
- **Offer History**: See the complete history of offers with utility values
- **Offer Histogram**: Analyze the distribution of proposed values per issue
- **Result Analysis**: Compare outcomes against Nash, Kalai, and welfare optima

### Tournament System

Run round-robin tournaments to compare negotiation strategies:

- **Grid Visualization**: Real-time progress grid showing all matchups
- **Live Leaderboard**: Watch rankings update as negotiations complete
- **Score Analysis**: Analyze results by metric, scenario, or opponent
- **Raw Data Export**: Access detailed tournament data for further analysis

### Scenario Management

Browse and analyze negotiation scenarios:

- **Scenario Explorer**: Browse ANAC competition scenarios (2010-2022)
- **Scenario Creator**: Design custom scenarios with the built-in wizard
- **Statistics Calculation**: Compute Pareto frontiers, Nash points, and welfare optima
- **Quick Start**: Launch negotiations directly from the explorer

### Negotiator Support

Work with a wide variety of negotiation agents:

- **Native NegMAS Agents**: All built-in NegMAS negotiators
- **Genius Agents**: ANAC competition agents via Genius Bridge
- **BOA Architecture**: Build custom agents from acceptance, offering, and modeling components
- **Virtual Negotiators**: Save configured agents for reuse

## Documentation Structure

This documentation is organized into two main sections:

### [User Guide](user-guide/index.md)

For users who want to experiment with negotiations and NegMAS:

- [Running Negotiations](user-guide/negotiations.md) - Configure and run single negotiations
- [Running Tournaments](user-guide/tournaments.md) - Compare strategies across scenarios
- [Scenario Explorer](user-guide/scenarios.md) - Browse and create negotiation scenarios
- [Negotiator Explorer](user-guide/negotiators.md) - Discover and configure negotiation agents
- [Settings & Configuration](user-guide/settings.md) - Customize the application

### [Developer Guide](developer-guide/index.md)

For developers who want to understand or extend the application:

- [Architecture Overview](developer-guide/architecture.md) - System design and data flow
- [Code Structure](developer-guide/code-structure.md) - Project organization and components
- [Template System](developer-guide/templates.md) - Frontend templates and components
- [API Reference](developer-guide/api.md) - Backend REST API documentation
- [Contributing](developer-guide/contributing.md) - How to contribute to the project

## Quick Start

```bash
# Install
pip install negmas-app

# Run
negmas-app

# Open browser at http://127.0.0.1:8019
```

See the [Installation Guide](getting-started/installation.md) for detailed instructions.

## Citation

If you use NegMAS App in your research, please cite the NegMAS library:

```bibtex
@inproceedings{mohammad2023negmas,
  title={NegMAS: A Platform for Situated Negotiations},
  author={Mohammad, Yasser and Greenwald, Amy and Nakadai, Shinji},
  booktitle={Proceedings of the 2023 International Conference on Autonomous Agents and Multiagent Systems},
  year={2023}
}
```

For the Supply Chain Management League (SCML), please also cite:

```bibtex
@article{mohammad2024scml,
  title={Supply Chain Management World},
  author={Mohammad, Yasser},
  journal={AI Magazine},
  year={2024}
}
```

## Quick Links

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Getting Started**

    ---

    Install NegMAS App and run your first negotiation

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

-   :material-play-circle:{ .lg .middle } **User Guide**

    ---

    Learn how to use the application effectively

    [:octicons-arrow-right-24: User Guide](user-guide/index.md)

-   :material-code-braces:{ .lg .middle } **Developer Guide**

    ---

    Understand the architecture and extend the app

    [:octicons-arrow-right-24: Developer Guide](developer-guide/index.md)

-   :material-trophy:{ .lg .middle } **Tournaments**

    ---

    Compare strategies in round-robin tournaments

    [:octicons-arrow-right-24: Running Tournaments](user-guide/tournaments.md)

</div>

## Related Projects

- [NegMAS](https://github.com/yasserfarouk/negmas) - The underlying negotiation library
- [SCML](https://github.com/yasserfarouk/scml) - Supply Chain Management League
- [Genius](http://ii.tudelft.nl/genius/) - Negotiation environment (for Genius agents)

## License

NegMAS App is open source software licensed under the MIT license.
