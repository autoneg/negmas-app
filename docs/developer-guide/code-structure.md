# Code Structure

This document provides a detailed overview of the NegMAS App codebase organization.

## Project Layout

```
negmas-app/
├── negmas_app/              # Python backend package
│   ├── models/              # Data structures
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   └── templates/           # Legacy Jinja templates
│
├── src/frontend/            # Vue.js frontend
│   ├── src/
│   │   ├── views/           # Page components
│   │   ├── components/      # Reusable components
│   │   └── stores/          # Pinia stores
│   ├── public/
│   └── package.json
│
├── docs/                    # MkDocs documentation
├── tests/                   # Test suite
├── pyproject.toml           # Python project config
└── mkdocs.yml               # Documentation config
```

## Backend Structure

### Models (`negmas_app/models/`)

Data structures using Python dataclasses:

| Module | Purpose |
|--------|---------|
| `mechanism.py` | Mechanism type definitions and parameters |
| `negotiation_definition.py` | Negotiation configuration structures |
| `negotiator.py` | Negotiator configuration and types |
| `scenario.py` | Scenario information and metadata |
| `session.py` | Negotiation session state and events |
| `settings.py` | Application settings dataclasses |
| `tournament.py` | Tournament configuration and results |

**Key Classes:**

```python
@dataclass
class NegotiationSession:
    """Active negotiation state"""
    id: str
    scenario_path: str
    mechanism: Any  # SAOMechanism instance
    negotiators: list[NegotiatorConfig]
    offers: list[OfferEvent]
    status: str  # 'running', 'completed', 'failed'

@dataclass
class OfferEvent:
    """Single offer in a negotiation"""
    step: int
    negotiator_id: str
    offer: tuple | None
    utilities: list[float]
    response: str  # 'accept', 'reject', 'end'
```

### Routers (`negmas_app/routers/`)

FastAPI route handlers organized by feature:

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| `negotiation.py` | `/api/negotiation/*` | Start, stream, manage negotiations |
| `scenarios.py` | `/api/scenarios/*` | List, load, import scenarios |
| `negotiators.py` | `/api/negotiators/*` | List, configure negotiators |
| `mechanisms.py` | `/api/mechanisms/*` | List mechanism types |
| `tournament.py` | `/api/tournament/*` | Tournament management |
| `settings.py` | `/api/settings/*` | Application settings |
| `sources.py` | `/api/sources/*` | Negotiator sources |
| `genius.py` | `/api/genius/*` | Genius bridge control |

**Example Router:**

```python
from fastapi import APIRouter, HTTPException
from ..services import SessionManager

router = APIRouter(prefix="/api/negotiation", tags=["negotiation"])

@router.post("/start")
async def start_negotiation(config: NegotiationConfig):
    session = await SessionManager.create_session(config)
    return {"session_id": session.id}

@router.get("/{session_id}/stream")
async def stream_negotiation(session_id: str):
    return EventSourceResponse(SessionManager.stream_session(session_id))
```

### Services (`negmas_app/services/`)

Business logic layer with single-responsibility modules:

| Module | Purpose |
|--------|---------|
| `session_manager.py` | Manages negotiation session lifecycle |
| `scenario_loader.py` | Loads and parses scenario files |
| `negotiator_factory.py` | Creates negotiator instances |
| `mechanism_factory.py` | Creates mechanism instances |
| `mechanism_registry.py` | Registers available mechanisms |
| `tournament_manager.py` | Runs tournaments |
| `tournament_storage.py` | Saves/loads tournament results |
| `negotiation_storage.py` | Saves/loads negotiation results |
| `settings_service.py` | Manages application settings |
| `outcome_analysis.py` | Calculates Pareto, Nash, etc. |
| `parameter_inspector.py` | Inspects negotiator parameters |
| `module_inspector.py` | Discovers negotiator classes |

**Key Service Patterns:**

```python
class SessionManager:
    """Singleton managing all negotiation sessions"""
    _sessions: dict[str, NegotiationSession] = {}
    
    @classmethod
    async def create_session(cls, config: NegotiationConfig) -> NegotiationSession:
        """Create and start a new negotiation session"""
        session = NegotiationSession(...)
        cls._sessions[session.id] = session
        asyncio.create_task(cls._run_session(session))
        return session
    
    @classmethod
    async def stream_session(cls, session_id: str) -> AsyncGenerator:
        """Stream session events via SSE"""
        session = cls._sessions.get(session_id)
        async for event in session.events():
            yield {"event": event.type, "data": event.to_json()}
```

## Frontend Structure

### Vue.js Application (`src/frontend/src/`)

The frontend is a Vue 3 single-page application:

```
src/frontend/src/
├── App.vue                      # Root component
├── main.js                      # Vue app initialization
├── router.js                    # Vue Router routes
│
├── views/                       # Page-level components
│   ├── NegotiationsListView.vue # /negotiations - list all
│   ├── SingleNegotiationView.vue# /negotiations/:id - detail
│   ├── TournamentsListView.vue  # /tournaments - list all
│   ├── SingleTournamentView.vue # /tournaments/:id - detail
│   ├── ScenariosView.vue        # /scenarios - explorer
│   ├── NegotiatorsView.vue      # /negotiators - explorer
│   └── ConfigsView.vue          # /configs - manager
│
├── components/                  # Reusable components
│   ├── panels/                  # Visualization panels
│   │   ├── BasePanel.vue        # Panel wrapper
│   │   ├── Utility2DPanel.vue   # 2D utility scatter plot
│   │   ├── TimelinePanel.vue    # Utility over time
│   │   ├── HistogramPanel.vue   # Issue value distribution
│   │   ├── OfferHistoryPanel.vue# Offer table
│   │   ├── InfoPanel.vue        # Status display
│   │   ├── ResultPanel.vue      # Final results
│   │   ├── IssueSpace2DPanel.vue# Issue scatter plot
│   │   └── PanelLayout.vue      # Grid layout manager
│   │
│   ├── NewNegotiationModal.vue  # Negotiation wizard
│   ├── NewTournamentModal.vue   # Tournament wizard
│   ├── TournamentGridPanel.vue  # Competition matrix
│   ├── TournamentScoresPanel.vue# Leaderboard
│   ├── TournamentNegotiationsPanel.vue
│   ├── StatsModal.vue           # Scenario stats
│   ├── NegotiatorInfoModal.vue  # Negotiator details
│   ├── SettingsModal.vue        # App settings
│   └── ...
│
└── stores/                      # Pinia state stores
    └── tournaments.js           # Tournament state
```

### Views vs Components

| Type | Location | Purpose |
|------|----------|---------|
| **Views** | `views/` | Full pages, mapped to routes |
| **Components** | `components/` | Reusable UI pieces |
| **Panels** | `components/panels/` | Visualization widgets |

### Single-File Components

Vue components use the single-file format:

```vue
<template>
  <!-- HTML template -->
  <div class="my-component">
    <h1>{{ title }}</h1>
    <button @click="handleClick">Click me</button>
  </div>
</template>

<script setup>
// JavaScript logic
import { ref } from 'vue'

const title = ref('Hello World')

function handleClick() {
  console.log('Clicked!')
}
</script>

<style scoped>
/* Scoped CSS */
.my-component {
  padding: 16px;
}
</style>
```

### Routing

Vue Router maps URLs to view components:

```javascript
// router.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/negotiations' },
  { 
    path: '/negotiations', 
    component: () => import('./views/NegotiationsListView.vue')
  },
  { 
    path: '/negotiations/:id', 
    component: () => import('./views/SingleNegotiationView.vue')
  },
  { 
    path: '/tournaments', 
    component: () => import('./views/TournamentsListView.vue')
  },
  { 
    path: '/tournaments/:id', 
    component: () => import('./views/SingleTournamentView.vue')
  },
  { path: '/scenarios', component: () => import('./views/ScenariosView.vue') },
  { path: '/negotiators', component: () => import('./views/NegotiatorsView.vue') },
  { path: '/configs', component: () => import('./views/ConfigsView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes
})
```

### State Management with Pinia

Pinia stores manage shared state:

```javascript
// stores/tournaments.js
import { defineStore } from 'pinia'

export const useTournamentsStore = defineStore('tournaments', {
  state: () => ({
    tournaments: [],
    currentTournament: null,
    loading: false,
  }),
  
  getters: {
    completedTournaments: (state) => 
      state.tournaments.filter(t => t.status === 'completed'),
    
    runningTournaments: (state) =>
      state.tournaments.filter(t => t.status === 'running'),
  },
  
  actions: {
    async fetchTournaments() {
      this.loading = true
      const response = await fetch('/api/tournament/list')
      this.tournaments = await response.json()
      this.loading = false
    },
    
    async startTournament(config) {
      const response = await fetch('/api/tournament/start', {
        method: 'POST',
        body: JSON.stringify(config)
      })
      return await response.json()
    },
  }
})
```

Using stores in components:

```vue
<script setup>
import { useTournamentsStore } from '@/stores/tournaments'

const store = useTournamentsStore()

// Access state
const tournaments = computed(() => store.tournaments)

// Call actions
onMounted(() => {
  store.fetchTournaments()
})
</script>
```

## Key Patterns

### Polling for Negotiations

Negotiations use polling for simplicity and reliability:

**Backend (FastAPI):**

```python
@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get current session state for polling"""
    session = SessionManager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.to_dict()
```

**Frontend (Vue):**

```javascript
// In SingleNegotiationView.vue
let pollInterval = null

function startPolling(sessionId) {
  pollInterval = setInterval(async () => {
    const response = await fetch(`/api/negotiation/${sessionId}`)
    const data = await response.json()
    
    offers.value = data.offers
    status.value = data.status
    updateCharts(data)
    
    if (data.status === 'completed') {
      clearInterval(pollInterval)
    }
  }, 200)
}

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
```

### SSE Streaming for Tournaments

Tournaments use Server-Sent Events for efficient real-time updates:

**Backend (FastAPI):**

```python
@router.get("/{session_id}/stream")
async def stream(session_id: str):
    async def event_generator():
        async for event in TournamentManager.stream_session(session_id):
            yield {"event": event.type, "data": json.dumps(event.data)}
    return EventSourceResponse(event_generator())
```

**Frontend (Vue - stores/tournaments.js):**

```javascript
function startStreaming(sessionId) {
  eventSource.value = new EventSource(`/api/tournament/${sessionId}/stream`)
  
  eventSource.value.addEventListener('cell_update', (e) => {
    const data = JSON.parse(e.data)
    updateCellState(data)
  })
  
  eventSource.value.addEventListener('leaderboard', (e) => {
    leaderboard.value = JSON.parse(e.data)
  })
  
  eventSource.value.addEventListener('complete', (e) => {
    tournamentComplete.value = JSON.parse(e.data)
    eventSource.value.close()
  })
}
```

### Panel Components

Visualization panels follow a consistent pattern:

```vue
<!-- panels/MyPanel.vue -->
<template>
  <BasePanel 
    title="My Panel" 
    :expanded="expanded"
    @toggle="expanded = !expanded"
  >
    <div ref="chartContainer" class="chart-container"></div>
  </BasePanel>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import Plotly from 'plotly.js-dist-min'
import BasePanel from './BasePanel.vue'

const props = defineProps({
  data: Array,
  config: Object
})

const chartContainer = ref(null)
const expanded = ref(false)

function updateChart() {
  if (!chartContainer.value || !props.data) return
  
  Plotly.react(chartContainer.value, [{
    x: props.data.map(d => d.x),
    y: props.data.map(d => d.y),
    type: 'scatter'
  }], {
    margin: { t: 20, r: 20, b: 40, l: 40 }
  })
}

watch(() => props.data, updateChart, { deep: true })
onMounted(updateChart)
</script>
```

### API Calls

Components call the backend via fetch:

```javascript
async function fetchScenarios() {
  loading.value = true
  try {
    const response = await fetch('/api/scenarios')
    if (!response.ok) throw new Error('Failed to fetch')
    scenarios.value = await response.json()
  } catch (error) {
    console.error('Error:', error)
    showError('Failed to load scenarios')
  } finally {
    loading.value = false
  }
}
```

## Adding New Features

### Adding a New Panel

1. **Create component** in `src/frontend/src/components/panels/`:

```vue
<!-- MyNewPanel.vue -->
<template>
  <BasePanel title="My New Panel">
    <div class="panel-content">
      <!-- Your visualization -->
    </div>
  </BasePanel>
</template>

<script setup>
import BasePanel from './BasePanel.vue'

const props = defineProps({
  data: Object
})
</script>
```

2. **Import and use** in a view:

```vue
<script setup>
import MyNewPanel from '@/components/panels/MyNewPanel.vue'
</script>

<template>
  <div class="panel-grid">
    <MyNewPanel :data="panelData" />
  </div>
</template>
```

### Adding a New View

1. **Create view** in `src/frontend/src/views/`:

```vue
<!-- MyNewView.vue -->
<template>
  <div class="my-view">
    <h1>My New Page</h1>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
</script>
```

2. **Add route** in `router.js`:

```javascript
{
  path: '/my-new-page',
  component: () => import('./views/MyNewView.vue')
}
```

3. **Add navigation** in sidebar (App.vue or navigation component)

### Adding a New API Endpoint

1. **Create or update router** in `negmas_app/routers/`:

```python
@router.get("/my-endpoint")
async def my_endpoint():
    result = await MyService.do_something()
    return {"data": result}
```

2. **Register router** in `main.py` if new file:

```python
from .routers import my_router
app.include_router(my_router.router)
```

### Adding a New Service

1. **Create service** in `negmas_app/services/`:

```python
class MyService:
    @classmethod
    async def do_something(cls) -> Result:
        # Business logic
        return result
```

2. **Import in router** as needed

## Build and Development

### Frontend Development

```bash
cd src/frontend

# Install dependencies
npm install

# Development server with hot reload
npm run dev

# Production build
npm run build
```

### Backend Development

```bash
# Install dependencies
uv sync --all-extras --dev

# Install local negmas packages
for x in negmas negmas-llm negmas-genius-agents negmas-negolog negmas-rl; do
  uv pip install -e ../$x
done

# Run development server
negmas-app start --dev
```

### Full Application

```bash
# Start both frontend and backend
negmas-app start

# Kill running servers
negmas-app kill

# Restart servers
negmas-app restart
```
