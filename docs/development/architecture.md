# Architecture

This document describes the architecture of NegMAS App.

## Overview

NegMAS App is a web application built with:

- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 + Alpine.js + HTMX
- **Real-time**: Server-Sent Events (SSE)
- **Visualization**: Plotly.js

```
┌─────────────┐     HTTP/SSE     ┌─────────────┐
│   Browser   │ <--------------> │   FastAPI   │
│             │                  │   Server    │
│  Alpine.js  │                  │             │
│    HTMX     │                  │   NegMAS    │
│  Plotly.js  │                  │   Library   │
└─────────────┘                  └─────────────┘
```

## Backend Architecture

### Layers

```
┌─────────────────────────────────────────┐
│              Routers (HTTP)             │
│  negotiation.py, scenarios.py, etc.    │
├─────────────────────────────────────────┤
│              Services (Logic)           │
│  session_manager.py, scenario_loader.py │
├─────────────────────────────────────────┤
│              Models (Data)              │
│  session.py, negotiator.py, etc.       │
├─────────────────────────────────────────┤
│              NegMAS Library             │
│  SAOMechanism, Negotiators, etc.       │
└─────────────────────────────────────────┘
```

### Key Components

#### Routers (`negmas_app/routers/`)

Handle HTTP requests and responses:

- `negotiation.py` - Start/stop negotiations, SSE streaming
- `scenarios.py` - List/load scenarios
- `negotiators.py` - List negotiator types
- `settings.py` - Application settings

#### Services (`negmas_app/services/`)

Business logic layer:

- `session_manager.py` - Manage negotiation sessions
- `scenario_loader.py` - Load and parse scenarios
- `negotiator_factory.py` - Create negotiator instances
- `mechanism_factory.py` - Create mechanism instances

#### Models (`negmas_app/models/`)

Data structures (dataclasses):

- `session.py` - NegotiationSession, OfferEvent
- `negotiator.py` - NegotiatorConfig
- `scenario.py` - ScenarioInfo

## Frontend Architecture

### Technology Stack

| Technology | Purpose |
|------------|---------|
| **Jinja2** | Server-side template rendering |
| **Alpine.js** | Reactive state management |
| **HTMX** | Server interactions |
| **Plotly.js** | Interactive charts |
| **SSE** | Real-time updates |

### State Management

Alpine.js manages client-side state:

```javascript
function app() {
    return {
        // Reactive state
        currentNegotiation: null,
        runningNegotiations: [],
        
        // Methods
        async startNegotiation() { ... },
        selectNegotiation(neg) { ... }
    }
}
```

### Panel System

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PanelRegistry  │────>│  LayoutManager  │────>│ LayoutRenderer  │
│                 │     │                 │     │                 │
│ Panel defs      │     │ State           │     │ DOM rendering   │
│ Lifecycle       │     │ Persistence     │     │ Interactions    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Data Flow

### Starting a Negotiation

```
1. User clicks "Start"
   │
2. Browser sends POST /api/negotiation/start
   │
3. Router creates NegotiatorFactory instances
   │
4. Service creates SAOMechanism
   │
5. Service starts negotiation in background
   │
6. Router returns negotiation ID
   │
7. Browser connects to SSE endpoint
   │
8. Service streams OfferEvents via SSE
   │
9. Browser updates UI in real-time
```

### SSE Event Format

```json
{
    "event": "offer",
    "data": {
        "step": 5,
        "negotiator": "Agent1",
        "offer": {"price": 100, "quantity": 50},
        "utilities": [0.75, 0.62],
        "response": "reject"
    }
}
```

## File Organization

```
negmas_app/
├── __init__.py
├── main.py              # FastAPI app entry point
│
├── models/              # Data structures
│   ├── session.py       # NegotiationSession
│   ├── negotiator.py    # NegotiatorConfig
│   └── scenario.py      # ScenarioInfo
│
├── routers/             # HTTP endpoints
│   ├── negotiation.py   # /api/negotiation/*
│   ├── scenarios.py     # /api/scenarios/*
│   └── negotiators.py   # /api/negotiators/*
│
├── services/            # Business logic
│   ├── session_manager.py
│   ├── scenario_loader.py
│   └── negotiator_factory.py
│
├── static/
│   ├── css/
│   │   ├── styles.css   # Main styles
│   │   └── layout.css   # Panel layout styles
│   └── js/
│       ├── panel-registry.js
│       ├── layout-manager.js
│       └── layout-renderer.js
│
└── templates/
    ├── base.html        # Base template
    └── index.html       # Main page
```

## Key Design Decisions

### Why FastAPI?

- Async support for SSE streaming
- Automatic API documentation
- Type hints and validation
- Modern Python features

### Why Alpine.js + HTMX?

- Minimal JavaScript bundle size
- Server-rendered HTML (good SEO, fast initial load)
- Progressive enhancement
- Simple mental model

### Why SSE over WebSockets?

- Simpler protocol (HTTP-based)
- Automatic reconnection
- Server-to-client only (which is our use case)
- Better browser support

### Why Panel System?

- Flexible workspace customization
- Plugin architecture for extensions
- Familiar VS Code-style interface
- Persistent user preferences
