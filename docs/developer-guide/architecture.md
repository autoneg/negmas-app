# Architecture

This document describes the architecture of NegMAS App in detail.

## System Overview

NegMAS App is a web application for running and visualizing automated negotiations. It connects a FastAPI backend to a browser-based frontend, with real-time updates via Server-Sent Events.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Browser                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  Alpine.js  │  │  Plotly.js  │  │  Tabulator  │                 │
│  │   (State)   │  │  (Charts)   │  │  (Tables)   │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          │                                          │
│                    HTTP / SSE                                       │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────┐
│                    FastAPI Server                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Routers   │──│  Services   │──│   Models    │                 │
│  │   (API)     │  │  (Logic)    │  │   (Data)    │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│                          │                                          │
│                    ┌─────┴─────┐                                    │
│                    │  NegMAS   │                                    │
│                    │  Library  │                                    │
│                    └───────────┘                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Backend Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Routers (HTTP Layer)                        │
│  negotiation.py | scenarios.py | negotiators.py | tournament.py │
├─────────────────────────────────────────────────────────────────┤
│                     Services (Business Logic)                   │
│  session_manager | scenario_loader | negotiator_factory | ...   │
├─────────────────────────────────────────────────────────────────┤
│                     Models (Data Structures)                    │
│  session.py | scenario.py | negotiator.py | tournament.py       │
├─────────────────────────────────────────────────────────────────┤
│                     NegMAS Library                              │
│  SAOMechanism | Negotiators | Scenarios | UtilityFunctions      │
└─────────────────────────────────────────────────────────────────┘
```

### Routers

Handle HTTP requests and format responses:

| Router | Prefix | Responsibility |
|--------|--------|----------------|
| `negotiation.py` | `/api/negotiation` | Start, stop, stream negotiations |
| `scenarios.py` | `/api/scenarios` | List, load, create scenarios |
| `negotiators.py` | `/api/negotiators` | List, configure negotiators |
| `mechanisms.py` | `/api/mechanisms` | List mechanism types |
| `tournament.py` | `/api/tournament` | Tournament management |
| `settings.py` | `/api/settings` | Application settings |
| `genius.py` | `/api/genius` | Genius bridge control |

### Services

Encapsulate business logic:

| Service | Responsibility |
|---------|----------------|
| `SessionManager` | Manages active negotiation sessions |
| `ScenarioLoader` | Loads and parses scenario files |
| `NegotiatorFactory` | Creates negotiator instances |
| `MechanismFactory` | Creates mechanism instances |
| `TournamentManager` | Runs tournament competitions |
| `TournamentStorage` | Persists tournament results |
| `NegotiationStorage` | Persists negotiation results |
| `SettingsService` | Manages application settings |
| `OutcomeAnalysis` | Calculates Pareto, Nash, welfare optima |

### Models

Data structures (Python dataclasses):

```python
@dataclass
class NegotiationSession:
    id: str
    scenario_path: str
    mechanism: SAOMechanism
    negotiators: list[NegotiatorConfig]
    offers: list[OfferEvent]
    status: Literal['running', 'completed', 'failed']
    start_time: datetime
    end_time: datetime | None

@dataclass
class OfferEvent:
    step: int
    negotiator_id: str
    offer: tuple | None
    utilities: list[float]
    response: Literal['accept', 'reject', 'end']
    timestamp: float
```

## Frontend Architecture

### Technology Stack

| Technology | Purpose |
|------------|---------|
| **Jinja2** | Server-side HTML rendering |
| **Alpine.js** | Client-side reactivity and state |
| **HTMX** | Server interactions without full page reload |
| **Plotly.js** | Interactive visualization charts |
| **Tabulator** | Rich data tables |
| **SSE** | Real-time server-to-client updates |

### State Management

Alpine.js manages all client-side state in a single `app()` function:

```javascript
function app() {
    return {
        // Navigation
        currentPage: 'negotiations',  // 'negotiations' | 'tournaments' | 'scenarios' | 'negotiators'
        
        // Negotiation state
        currentNegotiation: null,     // Selected negotiation or null
        runningNegotiations: [],      // Active negotiations
        completedNegotiations: [],    // Finished negotiations
        savedNegotiations: [],        // Loaded from storage
        
        // Tournament state
        selectedTournament: null,     // Selected tournament or null
        runningTournaments: [],       // Active tournaments
        completedTournaments: [],     // Finished tournaments
        
        // UI state
        showNewNegotiation: false,    // Modal visibility
        showSettings: false,
        zoomedPanel: null,            // Zoomed panel name or null
        
        // Methods
        async init() { ... },
        async startNegotiation() { ... },
        selectNegotiation(neg) { ... },
        // ... hundreds more
    }
}
```

### Component Hierarchy

```
base.html
├── <head> - Meta, CSS, JS imports
├── <body x-data="app()">
│   ├── toast.html - Notification toasts
│   ├── header.html - Navigation bar
│   ├── sidebar.html - Left sidebar
│   │
│   ├── <main> (negotiations page)
│   │   ├── negotiations_list_page.html - Table view
│   │   └── negotiation_view_page.html - Single view
│   │       ├── negotiation_info_panel.html
│   │       ├── offer_history_panel.html
│   │       ├── utility_2d_panel.html
│   │       ├── timeline_panel.html
│   │       ├── histogram_panel.html
│   │       └── result_panel.html
│   │
│   ├── <div> (tournaments page)
│   │   ├── tournaments_list_page.html - Table view
│   │   └── tournament_view_page.html - Single view
│   │       ├── tournament_grid_panel.html
│   │       ├── tournament_scores_panel.html
│   │       └── tournament_negotiations_panel.html
│   │
│   ├── scenarios_page.html
│   ├── negotiators_page.html
│   │
│   └── Modals
│       ├── new_negotiation_modal.html
│       ├── new_tournament_modal.html
│       ├── settings_modal.html
│       └── ...
│
└── index.html (extends base.html)
    └── {% block scripts %}
        └── Alpine.js app() function
```

## Data Flow

### Starting a Negotiation

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │────>│ Alpine  │────>│ FastAPI │────>│ NegMAS  │
│ clicks  │     │  app()  │     │ router  │     │ library │
│ Start   │     │         │     │         │     │         │
└─────────┘     └────┬────┘     └────┬────┘     └────┬────┘
                     │               │               │
                POST /api/negotiation/start          │
                     │───────────────>│              │
                     │               │   Create      │
                     │               │   mechanism   │
                     │               │───────────────>│
                     │               │               │
                     │<──────────────│   session_id  │
                     │   session_id  │               │
                     │               │               │
            Connect to SSE stream    │               │
                     │───────────────>│              │
                     │               │   Run async   │
                     │               │───────────────>│
                     │               │               │
                     │<──────────────│   OfferEvent  │
                     │   SSE offer   │               │
                     │               │               │
              Update plots           │               │
```

### SSE Event Types

| Event | Payload | Description |
|-------|---------|-------------|
| `offer` | `{step, negotiator, offer, utilities, response}` | New offer made |
| `progress` | `{step, total_steps, elapsed_time}` | Progress update |
| `complete` | `{agreement, final_utilities, end_reason}` | Negotiation ended |
| `error` | `{message, details}` | Error occurred |

### Tournament Data Flow

```
User starts tournament
        │
        ▼
┌───────────────────┐
│ TournamentManager │
│  creates session  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  For each match:  │◄────────┐
│  - Load scenario  │         │
│  - Create agents  │         │
│  - Run negotiation│         │
│  - Record result  │         │
└────────┬──────────┘         │
         │                    │
         ├──── SSE: progress ─┤
         │                    │
         ▼                    │
    More matches? ────────────┘
         │ No
         ▼
┌───────────────────┐
│  Calculate scores │
│  Send SSE: complete│
└───────────────────┘
```

## Key Design Decisions

### Why Server-Rendered HTML?

NegMAS App uses server-rendered HTML instead of a JavaScript SPA:

**Advantages:**

- Fast initial page load (no JS bundle to download)
- Works without JavaScript (progressive enhancement)
- Simpler state management (server is source of truth)
- Better for complex forms and wizards

**Trade-offs:**

- More server requests
- Less client-side interactivity
- Larger HTML payloads

### Why Alpine.js?

Alpine.js was chosen over React/Vue for:

- **Small bundle** (~15KB vs 100KB+)
- **No build step** - works directly in HTML
- **Declarative** - `x-show`, `x-for`, `@click` in HTML
- **Sufficient** - complex state is on server

### Why SSE over WebSockets?

Server-Sent Events are preferred for real-time updates:

- **Simpler** - Just HTTP, no protocol upgrade
- **Automatic reconnection** - Built into browsers
- **Unidirectional** - Perfect for server→client updates
- **Debuggable** - Standard HTTP tools work

### Why Plotly.js?

Plotly was chosen for visualizations:

- **Interactive** - Zoom, pan, hover tooltips
- **Publication-ready** - Export as PNG/SVG
- **Python compatible** - Same API as plotly.py
- **2D/3D support** - For future extensions

## Performance Considerations

### Negotiation Streaming

- Offers are streamed individually (not batched)
- Charts update incrementally (not re-render)
- Large negotiations use virtualized tables

### Scenario Loading

- Scenarios are cached after first load
- Statistics computed lazily on demand
- Pareto frontiers computed in background

### Tournament Execution

- Negotiations run sequentially (NegMAS limitation)
- Results streamed as completed
- Progress updates every negotiation
