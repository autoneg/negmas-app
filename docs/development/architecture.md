# Architecture

This document describes the architecture of NegMAS App.

## Overview

NegMAS App is a web application built with:

- **Backend**: FastAPI (Python)
- **Frontend**: Vue.js 3 with Pinia state management
- **Real-time**: Server-Sent Events (SSE) for tournaments, polling for negotiations
- **Visualization**: Plotly.js

```
┌─────────────────┐     HTTP/SSE     ┌─────────────────┐
│     Browser     │ <--------------> │    FastAPI      │
│                 │                  │    Server       │
│     Vue 3       │                  │                 │
│     Pinia       │                  │     NegMAS      │
│   Plotly.js     │                  │    Library      │
└─────────────────┘                  └─────────────────┘
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

- `negotiation.py` - Start/stop negotiations, streaming
- `scenarios.py` - List/load scenarios
- `negotiators.py` - List negotiator types
- `settings.py` - Application settings
- `tournament.py` - Tournament management

#### Services (`negmas_app/services/`)

Business logic layer:

- `session_manager.py` - Manage negotiation sessions
- `scenario_loader.py` - Load and parse scenarios
- `negotiator_factory.py` - Create negotiator instances
- `mechanism_factory.py` - Create mechanism instances
- `tournament_manager.py` - Run tournament competitions

#### Models (`negmas_app/models/`)

Data structures (dataclasses):

- `session.py` - NegotiationSession, OfferEvent
- `negotiator.py` - NegotiatorConfig
- `scenario.py` - ScenarioInfo
- `tournament.py` - TournamentSession, TournamentConfig

## Frontend Architecture

### Technology Stack

| Technology | Purpose |
|------------|---------|
| **Vue 3** | Component-based reactive UI |
| **Pinia** | Centralized state management |
| **Vue Router** | Client-side navigation |
| **Plotly.js** | Interactive charts |
| **Vite** | Build tool and dev server |

### State Management

Pinia stores manage client-side state:

```javascript
// stores/tournaments.js
export const useTournamentsStore = defineStore('tournaments', () => {
  // Reactive state
  const currentTournament = ref(null)
  const runningTournaments = ref([])
  
  // Actions
  async function startTournament(config) { ... }
  function connectToStream(sessionId) { ... }
  
  return { currentTournament, runningTournaments, startTournament, connectToStream }
})
```

### Component Structure

```
src/frontend/src/
├── views/                    # Page components
│   ├── NegotiationsListView.vue
│   ├── SingleNegotiationView.vue
│   ├── TournamentsListView.vue
│   └── SingleTournamentView.vue
├── components/               # Reusable components
│   ├── panels/               # Visualization panels
│   └── ...                   # Modals, controls
└── stores/                   # Pinia stores
    └── tournaments.js
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
7. Browser starts polling GET /api/negotiation/{id}
   │
8. Browser updates UI in real-time
```

### Tournament SSE Event Format

```json
{
    "event": "cell_update",
    "data": {
        "cell_key": "Agent1_vs_Agent2_scenario1",
        "status": "completed",
        "utilities": [0.75, 0.62],
        "agreement": true
    }
}
```

## File Organization

```
negmas-app/
├── negmas_app/              # Python backend
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── models/              # Data structures
│   ├── routers/             # HTTP endpoints
│   └── services/            # Business logic
│
├── src/frontend/            # Vue.js frontend
│   ├── src/
│   │   ├── App.vue          # Root component
│   │   ├── main.js          # Vue initialization
│   │   ├── router.js        # Route definitions
│   │   ├── views/           # Page components
│   │   ├── components/      # Reusable components
│   │   └── stores/          # Pinia stores
│   ├── package.json
│   └── vite.config.js
│
└── docs/                    # Documentation
```

## Key Design Decisions

### Why FastAPI?

- Async support for SSE streaming
- Automatic API documentation
- Type hints and validation
- Modern Python features

### Why Vue.js?

- Component-based architecture
- Reactive data binding
- Rich ecosystem (Router, Pinia)
- Excellent developer experience
- Modern build tooling (Vite)

### Why SSE for Tournaments?

- Efficient for many concurrent updates
- Simpler than WebSockets
- Automatic reconnection
- Server-to-client only (fits use case)

### Why Polling for Negotiations?

- Simpler implementation
- More reliable for single sessions
- Easier debugging
- No connection management needed

### Why Plotly.js?

- Interactive charts (zoom, pan, hover)
- Publication-ready export
- Same API as Python plotly
- 2D/3D support
