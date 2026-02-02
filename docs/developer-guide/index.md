# Developer Guide

Welcome to the NegMAS App Developer Guide. This section covers the architecture, implementation details, and how to extend the application.

## Overview

NegMAS App is built as a modern web application with:

- **Backend**: FastAPI (Python) serving REST APIs and SSE streams
- **Frontend**: Vue.js 3 single-page application with Pinia state management
- **Real-time**: Server-Sent Events (SSE) for tournament updates, polling for negotiations
- **Visualization**: Plotly.js for interactive charts

## Architecture Principles

### Single-Page Application

NegMAS App uses a Vue.js SPA architecture:

1. Vue Router handles client-side navigation
2. Pinia stores manage global state
3. Components render reactive UI
4. REST APIs provide data, SSE streams real-time updates

This approach offers:

- Rich interactive experience
- Efficient state management
- Component reusability
- Modern development workflow

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

Vue single-file components are organized by feature:

```
src/frontend/src/
├── views/               # Page-level components (routes)
├── components/          # Reusable components
│   ├── panels/          # Visualization panels
│   └── ...              # Modals, controls, etc.
├── stores/              # Pinia state stores
└── router.js            # Route definitions
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

# Install frontend dependencies
cd src/frontend && npm install && cd ../..

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
| `src/frontend/src/views/` | Vue page components |
| `src/frontend/src/components/` | Reusable Vue components |
| `src/frontend/src/stores/` | Pinia state stores |

### Important Files

| File | Purpose |
|------|---------|
| `negmas_app/main.py` | FastAPI application entry point |
| `src/frontend/src/App.vue` | Root Vue component |
| `src/frontend/src/router.js` | Vue Router configuration |
| `src/frontend/src/main.js` | Vue app initialization |

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | REST API, SSE, async support |
| Frontend | Vue 3 | Component-based reactive UI |
| State Management | Pinia | Centralized state stores |
| Routing | Vue Router | Client-side navigation |
| Build Tool | Vite | Fast development and bundling |
| Visualization | Plotly.js | Interactive charts |
| Data Tables | Tabulator | Rich data grids |
| Real-time | SSE / Polling | Server-to-client updates |
| Styling | CSS Variables | Theming support |
