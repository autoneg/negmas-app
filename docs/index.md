# NegMAS App

**A Visual Interface for Automated Negotiation**

NegMAS App is a web-based GUI for the [NegMAS](https://github.com/yasserfarouk/negmas) automated negotiation library. It provides an intuitive interface for:

- Running and visualizing negotiations in real-time
- Comparing negotiation strategies through tournaments
- Exploring negotiation scenarios and outcome spaces
- Analyzing negotiation results with interactive charts

## Features

### Real-time Negotiation Visualization

Watch negotiations unfold step-by-step with live updates:

- **2D Utility Space**: Visualize offers in the utility space of two negotiators
- **Utility Timeline**: Track how utilities evolve over time
- **Offer History**: See the complete history of offers made
- **Offer Histogram**: Analyze the distribution of offer values per issue

### Flexible Panel Layout

Customize your workspace with a VS Code-style dockable panel system:

- Drag and drop panels to rearrange
- Switch between tabbed and stacked views
- Save and restore custom layouts
- Choose from built-in presets (Default, Focus, Compact, Analysis)

### Tournament System

Run round-robin tournaments to compare negotiation strategies:

- Select multiple competitors and scenarios
- Configure repetitions and scoring metrics
- View live progress and final rankings
- Export results for further analysis

### Scenario Explorer

Browse and analyze negotiation scenarios:

- Filter by source (ANAC competitions, custom scenarios)
- View issue definitions and outcome spaces
- Quick-start negotiations from any scenario

## Quick Links

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Getting Started**

    ---

    Install NegMAS App and run your first negotiation

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

-   :material-view-dashboard:{ .lg .middle } **Panel System**

    ---

    Learn about the flexible panel layout system

    [:octicons-arrow-right-24: Panel Overview](panels/index.md)

-   :material-code-tags:{ .lg .middle } **Create Custom Panels**

    ---

    Build your own visualization panels

    [:octicons-arrow-right-24: Creating Panels](panels/creating-panels.md)

-   :material-trophy:{ .lg .middle } **Tournaments**

    ---

    Compare strategies in tournaments

    [:octicons-arrow-right-24: Running Tournaments](user-guide/tournaments.md)

</div>

## Architecture

NegMAS App is built with:

- **Backend**: FastAPI + Python
- **Frontend**: Jinja2 templates + Alpine.js + HTMX
- **Visualization**: Plotly.js for interactive charts
- **Real-time**: Server-Sent Events (SSE) for live updates

## License

NegMAS App is open source software licensed under the MIT license.
