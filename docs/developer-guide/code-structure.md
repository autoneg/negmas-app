# Code Structure

This document provides a detailed overview of the NegMAS App codebase organization.

## Project Layout

```
negmas-app/
├── negmas_app/           # Main application package
│   ├── models/           # Data structures
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic
│   ├── static/           # Static assets
│   │   ├── css/          # Stylesheets
│   │   └── js/           # JavaScript modules
│   ├── templates/        # HTML templates
│   │   ├── components/   # Reusable components
│   │   ├── base.html     # Base layout
│   │   └── index.html    # Main entry point
│   ├── __init__.py
│   └── main.py           # FastAPI app
├── docs/                 # Documentation
├── scenarios/            # Built-in scenarios
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
└── mkdocs.yml            # Documentation config
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
| `scenarios.py` | `/api/scenarios/*` | List, load, create scenarios |
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
    return {"session_id": session.id, "stream_url": f"/api/negotiation/{session.id}/stream"}

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
| `virtual_negotiator_service.py` | Manages virtual negotiators |
| `virtual_mechanism_service.py` | Manages virtual mechanisms |
| `definition_service.py` | Scenario definition management |

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

### Templates (`negmas_app/templates/`)

Jinja2 templates organized hierarchically:

```
templates/
├── base.html                 # Base layout with head, scripts
├── index.html                # Main page extending base
└── components/
    ├── pages/                # Full-page components
    │   ├── negotiations_list_page.html
    │   ├── negotiation_view_page.html
    │   ├── tournaments_list_page.html
    │   ├── tournament_view_page.html
    │   ├── scenarios_page.html
    │   └── negotiators_page.html
    ├── panels/               # Visualization panels
    │   ├── negotiation_info_panel.html
    │   ├── offer_history_panel.html
    │   ├── utility_2d_panel.html
    │   ├── timeline_panel.html
    │   ├── histogram_panel.html
    │   ├── result_panel.html
    │   ├── tournament_grid_panel.html
    │   ├── tournament_scores_panel.html
    │   ├── tournament_negotiations_panel.html
    │   ├── tournament_score_analysis_panel.html
    │   └── tournament_raw_data_panel.html
    ├── modals/               # Dialog components
    │   ├── new_negotiation_modal.html
    │   ├── new_tournament_modal.html
    │   ├── negotiator_config_modal.html
    │   ├── settings_modal.html
    │   └── ...
    └── shared/               # Common components
        ├── header.html
        ├── sidebar.html
        └── toast.html
```

### Template Hierarchy

```
base.html
├── Includes: header.html, sidebar.html, toast.html
├── Includes: page components (scenarios_page, negotiators_page, etc.)
├── Includes: modal components
└── Block: scripts (filled by index.html)

index.html (extends base.html)
└── Block: scripts
    └── Alpine.js application code
```

### Static Assets (`negmas_app/static/`)

```
static/
├── css/
│   ├── styles.css         # Main stylesheet
│   └── layout.css         # Panel layout styles
└── js/
    ├── panel-registry.js  # Panel registration system
    ├── layout-manager.js  # Layout state management
    └── layout-renderer.js # DOM rendering
```

## Key Patterns

### Alpine.js Application

The main application state is defined in `index.html`:

```javascript
function app() {
    return {
        // State
        currentPage: 'negotiations',
        currentNegotiation: null,
        runningNegotiations: [],
        completedNegotiations: [],
        
        // Computed
        get filteredScenarios() { ... },
        
        // Methods
        async init() { ... },
        async startNegotiation() { ... },
        selectNegotiation(neg) { ... },
        
        // ... hundreds more properties and methods
    }
}
```

### SSE Streaming

Real-time updates use Server-Sent Events:

```python
# Backend (router)
@router.get("/{session_id}/stream")
async def stream(session_id: str):
    async def event_generator():
        async for event in SessionManager.stream_session(session_id):
            yield {"event": event.type, "data": json.dumps(event.data)}
    return EventSourceResponse(event_generator())
```

```javascript
// Frontend
const eventSource = new EventSource(`/api/negotiation/${sessionId}/stream`);
eventSource.addEventListener('offer', (e) => {
    const offer = JSON.parse(e.data);
    this.updateOfferHistory(offer);
    this.updatePlots(offer);
});
```

### Component Inclusion

Templates use Jinja2 includes for modularity:

```html
<!-- base.html -->
<main class="content-area" x-show="currentPage === 'negotiations'">
    {% include 'components/pages/negotiations_list_page.html' %}
    {% include 'components/pages/negotiation_view_page.html' %}
</main>

<!-- negotiations_list_page.html -->
<div x-show="!currentNegotiation">
    <!-- List view content -->
</div>

<!-- negotiation_view_page.html -->
<div x-show="currentNegotiation">
    {% include 'components/panels/negotiation_info_panel.html' %}
    {% include 'components/panels/offer_history_panel.html' %}
    <!-- ... -->
</div>
```

## Adding New Features

### Adding a New Panel

1. Create template in `templates/components/panels/`:

```html
<!-- my_panel.html -->
<div class="panel" data-panel-id="my-panel">
    <div class="panel-header">
        <span class="panel-title">My Panel</span>
    </div>
    <div class="panel-content">
        <!-- Panel content -->
    </div>
</div>
```

2. Include in the appropriate page component
3. Add update logic in `index.html` JavaScript

### Adding a New API Endpoint

1. Create or update router in `routers/`:

```python
@router.get("/my-endpoint")
async def my_endpoint():
    result = await MyService.do_something()
    return {"data": result}
```

2. Register router in `main.py` if new file

### Adding a New Service

1. Create service in `services/`:

```python
class MyService:
    @classmethod
    async def do_something(cls) -> Result:
        # Business logic
        return result
```

2. Import in router as needed
