# Architecture

This document describes the architecture of NegMAS App in detail.

## System Overview

NegMAS App is a modern web application for running and visualizing automated negotiations. It uses a Vue.js frontend with a FastAPI backend, communicating via REST API and Server-Sent Events (SSE) for real-time updates.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Browser                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Vue 3     │  │  Plotly.js  │  │    Pinia    │                 │
│  │ (Components)│  │  (Charts)   │  │   (State)   │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          │                                          │
│                    HTTP / SSE                                       │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────┐
│                    FastAPI Server (Port 8019)                       │
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

## Frontend Architecture

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Vue 3** | 3.x | Component-based reactive UI |
| **Pinia** | 2.x | Centralized state management |
| **Vue Router** | 4.x | Client-side routing |
| **Vite** | 5.x | Build tool and dev server |
| **Plotly.js** | 2.x | Interactive visualizations |

### Component Architecture

```
src/frontend/src/
├── App.vue                      # Root component with layout
├── main.js                      # Vue app initialization
├── router.js                    # Route definitions
│
├── views/                       # Page-level components (routes)
│   ├── NegotiationsListView.vue # /negotiations list
│   ├── SingleNegotiationView.vue# /negotiations/:id detail
│   ├── TournamentsListView.vue  # /tournaments list
│   ├── SingleTournamentView.vue # /tournaments/:id detail
│   ├── ScenariosView.vue        # /scenarios browser
│   ├── NegotiatorsView.vue      # /negotiators browser
│   └── ConfigsView.vue          # /configs manager
│
├── components/                  # Reusable components
│   ├── panels/                  # Visualization panels
│   │   ├── BasePanel.vue        # Panel wrapper with expand/collapse
│   │   ├── Utility2DPanel.vue   # 2D utility space scatter plot
│   │   ├── TimelinePanel.vue    # Utility over time chart
│   │   ├── HistogramPanel.vue   # Issue value distribution
│   │   ├── OfferHistoryPanel.vue# Scrollable offer table
│   │   ├── InfoPanel.vue        # Negotiation status/details
│   │   ├── ResultPanel.vue      # Final results display
│   │   ├── IssueSpace2DPanel.vue# Offer distribution by issues
│   │   └── PanelLayout.vue      # Grid layout manager
│   │
│   ├── NewNegotiationModal.vue  # Negotiation configuration wizard
│   ├── NewTournamentModal.vue   # Tournament configuration wizard
│   ├── TournamentGridPanel.vue  # Competition matrix display
│   ├── TournamentScoresPanel.vue# Leaderboard display
│   ├── TournamentNegotiationsPanel.vue # Negotiations list
│   ├── StatsModal.vue           # Scenario statistics popup
│   ├── NegotiatorInfoModal.vue  # Negotiator details popup
│   ├── SettingsModal.vue        # Application settings
│   └── ...
│
└── stores/                      # Pinia state stores
    └── tournaments.js           # Tournament state management
```

### State Management

**Pinia Stores** manage global state:

```javascript
// stores/tournaments.js
export const useTournamentsStore = defineStore('tournaments', {
  state: () => ({
    tournaments: [],           // List of all tournaments
    currentTournament: null,   // Currently viewing
    runningTournaments: [],    // Active tournaments
  }),
  
  actions: {
    async fetchTournaments() { ... },
    async startTournament(config) { ... },
    async cancelTournament(id) { ... },
  },
  
  getters: {
    completedTournaments: (state) => 
      state.tournaments.filter(t => t.status === 'completed'),
  }
})
```

**Component-level State** for local UI:

```javascript
// In a Vue component
const showModal = ref(false)
const selectedItem = ref(null)
const formData = reactive({
  name: '',
  scenarios: [],
  competitors: []
})
```

### Routing

Vue Router handles navigation:

```javascript
// router.js
const routes = [
  { path: '/', redirect: '/negotiations' },
  { path: '/negotiations', component: NegotiationsListView },
  { path: '/negotiations/:id', component: SingleNegotiationView },
  { path: '/tournaments', component: TournamentsListView },
  { path: '/tournaments/:id', component: SingleTournamentView },
  { path: '/scenarios', component: ScenariosView },
  { path: '/negotiators', component: NegotiatorsView },
  { path: '/configs', component: ConfigsView },
]
```

### Real-time Updates

The application uses different update strategies for different features:

#### Negotiations: Polling

Negotiations use polling for simplicity and reliability:

```javascript
// In SingleNegotiationView.vue
const pollInterval = setInterval(async () => {
  const response = await fetch(`/api/negotiation/${sessionId}`)
  const data = await response.json()
  
  offers.value = data.offers
  status.value = data.status
  updateCharts(data)
  
  if (data.status === 'completed') {
    clearInterval(pollInterval)
  }
}, 200) // Poll every 200ms during active negotiation
```

#### Tournaments: Server-Sent Events (SSE)

Tournaments use SSE for efficient streaming of many concurrent updates:

```javascript
// In stores/tournaments.js
const eventSource = new EventSource(`/api/tournament/${sessionId}/stream`)

eventSource.addEventListener('grid_init', (event) => {
  const data = JSON.parse(event.data)
  gridInit.value = data
})

eventSource.addEventListener('cell_update', (event) => {
  const data = JSON.parse(event.data)
  updateCell(data)
})

eventSource.addEventListener('leaderboard', (event) => {
  const data = JSON.parse(event.data)
  leaderboard.value = data
})
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
| `scenarios.py` | `/api/scenarios` | List, load, import scenarios |
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

Data structures using Python dataclasses:

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

## Data Flow

### Negotiation Polling Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │────>│   Vue   │────>│ FastAPI │────>│ NegMAS  │
│ clicks  │     │ Component│     │ router  │     │ library │
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
              Start polling loop     │               │
                     │               │               │
              GET /api/negotiation/{id}              │
                     │───────────────>│              │
                     │<──────────────│   state data  │
                     │               │               │
              Update Vue state       │               │
              Re-render charts       │               │
                     │               │               │
              (repeat until complete)│               │
```

### Tournament SSE Event Types

| Event | Payload | Description |
|-------|---------|-------------|
| `grid_init` | `{competitors, opponents, scenarios, ...}` | Initial grid structure |
| `run_start` | `{competitor_idx, opponent_idx, scenario_idx, ...}` | Negotiation run starting |
| `run_complete` | `{competitor_idx, opponent_idx, scenario_idx, run_id, ...}` | Negotiation run completed |
| `leaderboard` | `[{rank, name, score, ...}, ...]` | Updated rankings |
| `progress` | `{completed, total, percentage}` | Overall progress |
| `complete` | `{status, duration, ...}` | Tournament finished |
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

### Why Vue.js?

Vue.js was chosen for the frontend rewrite:

**Advantages:**

- **Component-based**: Clean separation of concerns
- **Reactive**: Automatic UI updates when data changes
- **Ecosystem**: Vue Router, Pinia, excellent tooling
- **Performance**: Virtual DOM, efficient re-rendering
- **Developer experience**: Single-file components, hot reload

**Trade-offs:**

- Requires build step (Vite handles this efficiently)
- Larger bundle size (~100KB)
- More complex than server-rendered HTML

### Why Pinia?

Pinia replaced Vuex for state management:

- **Type-safe**: Full TypeScript support
- **Simple API**: No mutations, just actions
- **Devtools**: Excellent Vue DevTools integration
- **Modular**: Stores can be composed

### Why Polling for Negotiations?

Polling was chosen over SSE for individual negotiations:

**Advantages:**

- **Simpler implementation**: No connection management complexity
- **More reliable**: Automatic recovery from network issues
- **Easier debugging**: Standard HTTP request/response
- **Stateless server**: No need to track open connections

**Trade-offs:**

- Slightly higher latency (poll interval dependent)
- More HTTP requests than SSE

### Why SSE for Tournaments?

Tournaments use SSE because they have many concurrent updates:

- **Efficient**: Single connection for hundreds of cell updates
- **Real-time**: Immediate updates as negotiations complete
- **Scalable**: Less overhead than polling many endpoints

### Why Plotly.js?

Plotly was chosen for visualizations:

- **Interactive**: Zoom, pan, hover tooltips
- **Publication-ready**: Export as PNG/SVG
- **Python compatible**: Same API as plotly.py
- **2D/3D support**: For future extensions

### Why FastAPI?

FastAPI provides the backend framework:

- **Fast**: High performance with async support
- **Type-safe**: Pydantic models for validation
- **Auto-docs**: Swagger/OpenAPI documentation
- **SSE support**: Easy Server-Sent Events

## Performance Considerations

### Frontend Performance

- **Lazy loading**: Routes loaded on demand
- **Virtual scrolling**: Large lists don't render all items
- **Chart updates**: Incremental updates, not full re-renders
- **Debouncing**: Search inputs debounced to reduce API calls

### Backend Performance

- **Async handlers**: Non-blocking request processing
- **Scenario caching**: Loaded scenarios cached in memory
- **Lazy statistics**: Computed on demand, then cached
- **Streaming**: Results streamed as they complete

### Negotiation Streaming

- Offers streamed individually (not batched)
- Charts update incrementally
- Large negotiations use virtualized tables

### Tournament Execution

- Negotiations run sequentially (NegMAS limitation)
- Results streamed as completed
- Progress updates every negotiation

## Directory Structure

```
negmas-app/
├── negmas_app/              # Python backend
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   ├── models/              # Data structures
│   └── templates/           # Legacy Jinja templates
│
├── src/frontend/            # Vue.js frontend
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   ├── router.js
│   │   ├── views/
│   │   ├── components/
│   │   └── stores/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── docs/                    # MkDocs documentation
├── tests/                   # Test suite
└── pyproject.toml          # Python project config
```
