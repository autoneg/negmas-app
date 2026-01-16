# Developer Guide

Welcome to the NegMAS App Developer Guide. This section covers the architecture, implementation details, and how to extend the application.

## Overview

NegMAS App is built as a modern web application with:

- **Backend**: FastAPI (Python) serving REST APIs and SSE streams
- **Frontend**: Server-rendered HTML with Jinja2, enhanced with Alpine.js
- **Real-time**: Server-Sent Events (SSE) for live negotiation updates
- **Visualization**: Plotly.js for interactive charts

## Architecture Principles

### Server-Rendered First

Unlike typical SPAs, NegMAS App uses server-rendered HTML as the foundation:

1. Jinja2 templates render the initial HTML
2. Alpine.js adds reactivity for state management
3. HTMX handles server interactions
4. SSE provides real-time updates

This approach offers:

- Fast initial page loads
- Better SEO (if needed)
- Progressive enhancement
- Simpler mental model

### Layered Backend

The backend follows a clean layered architecture:

```
┌─────────────────────────────────┐
│         Routers (API)           │  HTTP endpoints
├─────────────────────────────────┤
│        Services (Logic)         │  Business logic
├─────────────────────────────────┤
│         Models (Data)           │  Data structures
├─────────────────────────────────┤
│       NegMAS Library            │  Negotiation engine
└─────────────────────────────────┘
```

### Component-Based Frontend

Templates are organized as reusable components:

```
templates/
├── base.html           # Base layout
├── index.html          # Main entry with scripts
└── components/
    ├── pages/          # Full page templates
    ├── panels/         # Visualization panels
    ├── modals/         # Dialog components
    └── shared/         # Common components
```

## Documentation Sections

### [Architecture](architecture.md)

Deep dive into the system design:

- Data flow diagrams
- Component interactions
- Design decisions and rationale

### [Code Structure](code-structure.md)

Detailed project organization:

- Directory structure
- Module responsibilities
- Key classes and functions

### [Template System](templates.md)

Frontend architecture:

- Template hierarchy
- Component patterns
- Alpine.js integration

### [API Reference](api.md)

REST API documentation:

- Endpoints and methods
- Request/response formats
- SSE event types

### [Contributing](contributing.md)

How to contribute:

- Development setup
- Coding standards
- Pull request process

## Quick Reference

### Running in Development

```bash
# Install dependencies
uv sync --all-extras --dev

# Install local negmas packages (required)
for x in negmas negmas-llm negmas-genius-agents negmas-negolog negmas-rl; do
    uv pip install -e ../$x
done

# Start the server
negmas-app run

# Type checking
pyright negmas_app/

# Run tests
pytest tests/ -v
```

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `negmas_app/models/` | Data structures (dataclasses) |
| `negmas_app/routers/` | FastAPI route handlers |
| `negmas_app/services/` | Business logic |
| `negmas_app/templates/` | Jinja2 HTML templates |
| `negmas_app/static/` | CSS and JavaScript |

### Important Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application entry point |
| `base.html` | Base HTML template |
| `index.html` | Main page with Alpine.js app |
| `styles.css` | Main stylesheet |
| `layout.css` | Panel layout styles |

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | REST API, SSE, async support |
| Templates | Jinja2 | Server-side HTML rendering |
| Reactivity | Alpine.js | Client-side state management |
| Server Interaction | HTMX | HTML-over-the-wire |
| Visualization | Plotly.js | Interactive charts |
| Data Tables | Tabulator | Rich data grids |
| Real-time | SSE | Server-to-client streaming |
| Styling | CSS Variables | Theming support |
