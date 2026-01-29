# Polling Architecture - Implementation Plan

## Goal
Replace SSE streaming with simple HTTP polling for cleaner, more maintainable code.

## Current Problems
1. SSE streams replay entire history causing duplicates
2. Complex state sync between SSE, polling, and store
3. False errors on connection closure
4. Race conditions during navigation
5. Excessive console logging
6. Hard to debug and maintain

## New Architecture

### Backend Changes

#### 1. Use `mechanism.run()` in background thread with module-level callbacks
**File**: `negmas_app/services/session_manager.py`

```python
# Module-level callback to avoid pickling issues
def _negotiation_step_callback(mechanism, state, session_dict, session_id):
    """Module-level callback for negotiation steps (pickle-safe)"""
    session = session_dict[session_id]
    session.current_step = state.step
    
    # Store offers incrementally
    if len(mechanism.history) > len(session.offers):
        new_history = mechanism.history[len(session.offers):]
        for h in new_history:
            session.offers.append({
                'step': h.step,
                'offer': h.current_offer,
                'proposer': h.current_proposer,
                'relative_time': h.relative_time
            })

# Module-level runner function (pickle-safe)
def _run_negotiation_in_thread(session_id, session_dict, scenario, mechanism_type, 
                                mechanism_params, negotiator_configs):
    """Run negotiation synchronously in background thread"""
    
    session = session_dict[session_id]
    
    # Create mechanism
    mechanism = MechanismFactory.create_from_scenario_params(
        scenario, mechanism_type, mechanism_params
    )
    
    # Create negotiators
    negotiators = NegotiatorFactory.create_for_scenario(negotiator_configs, scenario)
    
    # Add negotiators
    for neg, ufun, config in zip(negotiators, scenario.ufuns, negotiator_configs):
        add_kwargs = {"ufun": ufun}
        if config.time_limit is not None:
            add_kwargs["time_limit"] = config.time_limit
        if config.n_steps is not None:
            add_kwargs["n_steps"] = config.n_steps
        mechanism.add(neg, **add_kwargs)
    
    # Run mechanism and collect history
    for state in mechanism:
        _negotiation_step_callback(mechanism, state, session_dict, session_id)
    
    # Store final results
    session.status = SessionStatus.COMPLETED
    session.agreement = mechanism.agreement
    # Calculate utilities, optimality stats, etc.

class SessionManager:
    async def start_negotiation_background(self, session_id: str, configs: list[NegotiatorConfig]):
        """Start negotiation in background thread"""
        
        session = self.sessions[session_id]
        session.status = SessionStatus.RUNNING
        
        # Get all needed data
        scenario = load_scenario(...)
        mechanism_type = self._mechanism_types[session_id]
        mechanism_params = self._mechanism_params[session_id]
        
        # Run in thread pool - uses module-level function (pickle-safe)
        asyncio.create_task(
            asyncio.to_thread(
                _run_negotiation_in_thread,
                session_id,
                self.sessions,  # Pass dict reference
                scenario,
                mechanism_type,
                mechanism_params,
                configs
            )
        )
```

#### 2. Remove SSE streaming endpoint
**File**: `negmas_app/routers/negotiation.py`

- Remove `/api/negotiation/{session_id}/stream` endpoint
- Keep GET `/api/negotiation/{session_id}` for polling
- Ensure it returns current state with all offers

#### 3. Simple state endpoint
**File**: `negmas_app/routers/negotiation.py`

```python
@router.get("/api/negotiation/{session_id}")
def get_negotiation_state(session_id: str):
    """Get current negotiation state (for polling)"""
    
    session = get_manager().get_session(session_id)
    
    return {
        "id": session.id,
        "status": session.status,
        "current_step": session.current_step,
        "n_steps": session.n_steps,
        "offers": session.offers,  # All offers so far
        "agreement": session.agreement,
        "final_utilities": session.final_utilities,
        # ... other state
    }
```

### Frontend Changes

#### 1. Remove SSE store logic
**File**: `src/frontend/src/stores/negotiations.js`

- Remove `eventSource` ref
- Remove `startStreaming()` function
- Remove `stopStreaming()` function
- Remove SSE event listeners
- Remove `sessionInit`, `sessionComplete` refs (use API data directly)
- Keep only `sessions` list and simple CRUD operations

#### 2. Simplify SingleNegotiationView
**File**: `src/frontend/src/views/SingleNegotiationView.vue`

```javascript
// Simple polling approach
async function loadAndPollNegotiation(sessionId) {
  loading.value = true
  
  // Initial load
  const state = await negotiationsStore.getSession(sessionId)
  updateViewState(state)
  loading.value = false
  
  // Poll if running
  if (state.status === 'running' || state.status === 'pending') {
    pollInterval = setInterval(async () => {
      const updated = await negotiationsStore.getSession(sessionId)
      updateViewState(updated)
      
      if (updated.status === 'completed' || updated.status === 'failed') {
        clearInterval(pollInterval)
        await negotiationsStore.loadSessions()
      }
    }, 1000)
  }
}

function updateViewState(state) {
  // Simple state update
  offers.value = state.offers || []
  negotiatorNames.value = state.negotiator_names || []
  
  if (state.status === 'completed' || state.status === 'failed') {
    agreement.value = state.agreement
    finalUtilities.value = state.final_utilities
  }
}
```

#### 3. Simplify NegotiationsListView
**File**: `src/frontend/src/views/NegotiationsListView.vue`

```javascript
// Just start negotiation, then navigate
async function onNegotiationStart(data) {
  showNewNegotiationModal.value = false
  
  if (data.session_id) {
    // Navigate immediately - view will handle polling
    router.push({ name: 'SingleNegotiation', params: { id: data.session_id } })
  }
}
```

#### 4. Remove SSE from NewNegotiationModal
**File**: `src/frontend/src/components/NewNegotiationModal.vue`

- Remove `stream_url` from response
- Just return `session_id`

## Migration Steps

### Step 1: Backend - Add background runner
- [ ] Implement `start_negotiation_background()` in SessionManager
- [ ] Implement `_run_negotiation_sync()` using `mechanism.run()`
- [ ] Store offers incrementally during mechanism iteration
- [ ] Update session state on completion
- [ ] Test: negotiation runs and state is stored correctly

### Step 2: Backend - Ensure GET endpoint works
- [ ] Verify `/api/negotiation/{session_id}` returns complete state
- [ ] Include all offers in response
- [ ] Include outcome_space_data for visualizations
- [ ] Test: endpoint returns correct data during and after negotiation

### Step 3: Frontend - Simplify store
- [ ] Remove SSE-related code from negotiations.js
- [ ] Keep only sessions list and getSession()
- [ ] Test: store can fetch and list sessions

### Step 4: Frontend - Update SingleNegotiationView
- [ ] Remove SSE stream checks
- [ ] Implement simple polling loop
- [ ] Remove complex state synchronization logic
- [ ] Test: view polls and updates correctly

### Step 5: Frontend - Update NegotiationsListView
- [ ] Remove startStreaming() call
- [ ] Just navigate after starting negotiation
- [ ] Test: can start negotiation and navigate

### Step 6: Frontend - Update NewNegotiationModal
- [ ] Remove stream_url generation
- [ ] Test: modal starts negotiation correctly

### Step 7: Backend - Remove SSE endpoint (optional)
- [ ] Comment out or remove `/stream` endpoint
- [ ] Can keep for backward compatibility initially

### Step 8: Cleanup
- [ ] Remove console.log debugging statements
- [ ] Clean up unused refs and functions
- [ ] Update documentation

## Testing Checklist

After implementation:
- [ ] Start first negotiation - runs and completes without errors
- [ ] Start second negotiation - no blank screen
- [ ] Navigate between negotiations - smooth transitions
- [ ] Refresh during running negotiation - picks up where it left off
- [ ] Multiple negotiations running - all update correctly
- [ ] Console is clean - minimal logging
- [ ] No error modals on successful completion
- [ ] No duplicate steps or offers

## Rollback Plan

If polling architecture has issues:
```bash
git checkout main
```

Keep this branch for reference and future improvements.

## Expected Outcomes

1. **Simpler code** - ~200 lines removed
2. **More reliable** - no SSE connection management
3. **Cleaner console** - remove debug logging
4. **Easier to debug** - straightforward polling loop
5. **No race conditions** - backend state is authoritative
6. **Better UX** - no false errors, smooth updates
