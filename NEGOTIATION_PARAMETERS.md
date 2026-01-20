# Complete SAOMechanism + Mechanism Parameter Reference

This document lists ALL parameters available for creating SAO negotiations in NegMAS.

## Source Files
- `../negmas/src/negmas/mechanisms.py:598` - Base Mechanism class `__init__`
- `../negmas/src/negmas/sao/mechanism.py:97` - SAOMechanism class `__init__`

## Mechanism Base Class Parameters

### Outcome Space Definition (One of these required)
- `outcome_space: OutcomeSpace | None` - The negotiation agenda
- `issues: Sequence[Issue] | None` - A list of issues defining the outcome-space
- `outcomes: Sequence[Outcome] | int | None` - List of outcomes or number of outcomes

### Time Limits
- `n_steps: int | float | None` - Maximum number of negotiation rounds (None = infinity)
- `time_limit: float | None` - Maximum wall-time in seconds (None = infinity)
- `step_time_limit: float | None` - Maximum wall-time per negotiation round (seconds)
- `negotiator_time_limit: float | None` - Maximum time per negotiator action (seconds)
- `hidden_time_limit: float` - Hidden time limit not visible to negotiators (default: inf)

### Probabilistic Ending
- `pend: float` - Probability of ending negotiation at any step (default: 0)
- `pend_per_second: float` - Probability of ending per second (default: 0)

### Negotiator Management
- `max_n_negotiators: int | None` - Maximum allowed number of negotiators
- `dynamic_entry: bool` - Allow negotiators to enter/leave between rounds (default: False)

### Outcome Caching
- `cache_outcomes: bool` - Cache list of all possible outcomes (implicit, based on usage)
- `max_cardinality: int` - Maximum allowed number of outcomes in cached set (default: 10B)

### Metadata
- `annotation: dict[str, Any] | None` - Arbitrary annotation dictionary
- `name: str | None` - Name of the mechanism session (auto-generated if not provided)
- `id: str | None` - System-wide unique identifier (auto-generated if not provided)
- `type_name: str | None` - Type name for the mechanism

### Callbacks & Error Handling
- `extra_callbacks: bool` - Enable callbacks like on_round_start, etc. (default: False)
- `ignore_negotiator_exceptions: bool` - Silently ignore negotiator exceptions (default: False)
- `verbosity: int` - Verbosity level for logging (default: 0)

### Checkpointing
- `checkpoint_every: int` - Number of steps between checkpoints (default: 1, <=0 disables)
- `checkpoint_folder: PathLike | None` - Folder to save checkpoints (None disables)
- `checkpoint_filename: str | None` - Base filename for checkpoints
- `single_checkpoint: bool` - Only keep most recent checkpoint (default: True)
- `extra_checkpoint_info: dict[str, Any] | None` - Extra info to save with checkpoints
- `exist_ok: bool` - Override existing checkpoints (default: True)

### Advanced
- `initial_state: TState | None` - Initial mechanism state
- `nmi_factory: type[TNMI]` - Factory for creating negotiator-mechanism interfaces
- `genius_port: int` - Port for Genius negotiator connections (default: DEFAULT_JAVA_PORT)

## SAOMechanism-Specific Parameters

### Core Behavior
- `end_on_no_response: bool` - End if negotiator returns NO_RESPONSE (default: True)
- `offering_is_accepting: bool` - Proposing an offer implies accepting it (default: True)
- `allow_offering_just_rejected_outcome: bool` - Allow re-offering just-rejected outcomes (default: True)
- `one_offer_per_step: bool` - Each step processes only one negotiator's offer (default: False)

### Offer Validation
- `check_offers: bool` - Validate offers against outcome space (default: False)
- `enforce_issue_types: bool` - Enforce correct types for issue values (default: False)
- `cast_offers: bool` - Cast issue values to correct types if enforcement on (default: False)

### Execution
- `sync_calls: bool` - Synchronous calls (disables per-call timeouts) (default: False)
- `max_wait: int` - Maximum consecutive WAIT responses before timeout (default: sys.maxsize)

### Deprecated
- `avoid_ultimatum: bool` - **DEPRECATED** - Will be removed soon (forced to False)

### Inherited from Mechanism
- `dynamic_entry: bool` - Passed to parent (default: False)
- `extra_callbacks: bool` - Passed to parent (default: True for SAO)
- `name: str | None` - Passed to parent
- `initial_state: SAOState | None` - SAO-specific state
- All other Mechanism parameters via `**kwargs`

## BOA/MAP Components (from component_registry)

### Acceptance Policies (66 available)
Examples: AcceptAbove, AcceptAnyRational, AcceptBest, RandomAcceptancePolicy, RejectAlways, etc.
Full list available via `component_registry.query(component_type='acceptance')`

### Offering Policies (37 available)
Examples: OfferBest, OfferTop, RandomOfferingPolicy, TimeBasedOfferingPolicy, etc.
Full list available via `component_registry.query(component_type='offering')`

### Opponent Models (20 available)
Examples: FrequencyUFunModel, BayesianModel, PerfectModel, ZeroSumModel, etc.
Full list available via `component_registry.query(component_type='model')`

## Parameter Organization for UI

### Tab 1: Scenario Selection
- Scenario picker with filters (min/max outcomes, rational fraction, opposition)
- ignore_discount, ignore_reserved, normalize checkboxes

### Tab 2: Negotiators (with 3 sub-tabs)
**Sub-tab 1: Preset Agents**
- Year filter, tag filter, drag-and-drop ordering

**Sub-tab 2: Build Custom (BOA)**
- Acceptance Policy (required) - dropdown from acceptance components
- Offering Policy (required) - dropdown from offering components
- Opponent Model (optional) - dropdown from model components

**Sub-tab 3: Build Custom (MAP)**
- Acceptance Policy (required)
- Offering Policy (required)
- Models (multiple, add/remove)
- acceptance_first checkbox

### Tab 3: Mechanism Parameters

**Basic Time Limits:**
- n_steps (int input with range)
- time_limit (float input)
- step_time_limit (float input)
- negotiator_time_limit (float input)

**Probabilistic Ending:**
- pend (0-1 slider)
- pend_per_second (0-1 slider)

**Core Behavior:**
- end_on_no_response (checkbox)
- offering_is_accepting (checkbox)
- allow_offering_just_rejected_outcome (checkbox)
- one_offer_per_step (checkbox)

**Offer Validation:**
- check_offers (checkbox)
- enforce_issue_types (checkbox)
- cast_offers (checkbox, only enabled if enforce_issue_types=true)

**Advanced Settings (collapsible):**
- hidden_time_limit (float)
- max_wait (int)
- sync_calls (checkbox)
- max_n_negotiators (int)
- dynamic_entry (checkbox)
- max_cardinality (int)
- ignore_negotiator_exceptions (checkbox)
- verbosity (0-3 slider)

**Checkpointing (collapsible):**
- checkpoint_every (int)
- checkpoint_folder (text input)
- checkpoint_filename (text input)
- single_checkpoint (checkbox)

### Tab 4: Panels Configuration
- Adjustable panels checkbox
- Utility Space View: X/Y axis dropdowns
- Timeline View: X-axis dropdown, Simplified checkbox
- Issue Space 2D: X/Y axis dropdowns

### Tab 5: Display & Run
- Summary section
- Run mode selector (Real-time vs Batch)
- Step delay slider (0-1000ms)
- Display options: show_plot, show_offers
- Auto-save checkbox
- Visible panels checkboxes
- "Start without Monitoring" button
