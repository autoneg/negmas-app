"""Tournament management service for running cartesian tournaments."""

from __future__ import annotations

import asyncio
import json
import math
import multiprocessing
import queue
import shutil
import threading
import uuid
import warnings
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from negmas import Scenario
from negmas.sao import SAOMechanism, SAONegotiator
from negmas.tournaments.neg import cartesian_tournament, continue_cartesian_tournament

from ..models.tournament import (
    TournamentConfig,
    TournamentSession,
    TournamentStatus,
    TournamentProgress,
    TournamentResults,
    CompetitorScore,
    NegotiationResult,
    NegotiationEndReason,
    CellStatus,
    CellUpdate,
    LeaderboardEntry,
    TournamentGridInit,
)
from .scenario_loader import ScenarioLoader
from .negotiator_factory import _get_class_for_type
from .settings_service import SettingsService


# Global multiprocessing manager for creating picklable queues and shared state
# This must be module-level to work with multiprocessing
_mp_manager: Any = None


def _get_mp_manager() -> Any:
    """Get or create the global multiprocessing manager."""
    global _mp_manager
    if _mp_manager is None:
        _mp_manager = multiprocessing.Manager()
    return _mp_manager


def _create_mp_queue() -> Any:
    """Create a multiprocessing-compatible queue that can be pickled.

    This uses multiprocessing.Manager().Queue() which, unlike queue.Queue,
    can be serialized by cloudpickle for use in parallel tournament execution.
    """
    return _get_mp_manager().Queue()


def _create_mp_dict() -> Any:
    """Create a multiprocessing-compatible dict that can be pickled.

    This uses multiprocessing.Manager().dict() which, unlike regular dict,
    can be serialized by cloudpickle and shared across processes.
    """
    return _get_mp_manager().dict()


def _apply_normalization(
    scenario: Scenario, mode: str, recalculate_stats: bool = False
) -> Scenario:  # type: ignore[type-arg]
    """Apply normalization to a scenario based on the mode.

    Args:
        scenario: The scenario to normalize.
        mode: Normalization mode - "none", "scale_min", "scale_max", or "normalize".
        recalculate_stats: Whether to recalculate stats after normalization.

    Returns:
        The normalized scenario (may be a new object or the same if mode is "none").
    """
    if mode == "none" or not mode:
        return scenario
    elif mode == "scale_min":
        return scenario.scale_min(to=1.0, recalculate_stats=recalculate_stats)
    elif mode == "scale_max":
        return scenario.scale_max(to=1.0, recalculate_stats=recalculate_stats)
    elif mode == "normalize":
        return scenario.normalize(to=(0.0, 1.0), recalculate_stats=recalculate_stats)
    else:
        return scenario


@dataclass
class TournamentState:
    """Shared state for a running tournament, updated by callbacks."""

    # Grid structure (set at start)
    grid_init: TournamentGridInit | None = None

    # Mapping from (competitor, opponent, scenario, rep, rotated) -> cell index
    cell_index_map: dict[tuple[str, str, str, int, bool], int] = field(
        default_factory=dict
    )

    # All cell updates (completed cells)
    completed_cells: list[CellUpdate] = field(default_factory=list)

    # Currently running cell (if any)
    current_cell: CellUpdate | None = None

    # Current leaderboard
    leaderboard: list[LeaderboardEntry] = field(default_factory=list)

    # Progress tracking
    progress: TournamentProgress | None = None

    # Tournament status
    status: TournamentStatus = TournamentStatus.PENDING
    error: str | None = None

    # Event queue for SSE streaming - uses multiprocessing queue for parallel support
    # Note: default_factory uses _create_mp_queue which creates a picklable queue
    event_queue: Any = field(default_factory=_create_mp_queue)

    # Setup progress for polling (message, current step, total steps)
    setup_progress: dict[str, Any] | None = None

    # Live/running negotiations for polling - MP-safe dict for parallel execution
    live_negotiations: Any = field(default_factory=_create_mp_dict)

    # Completed negotiations with details (for polling - shows in Negotiations panel)
    completed_negotiations: list[dict[str, Any]] = field(default_factory=list)

    # Statistics per competitor
    competitor_stats: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Loaded scenarios (for reference)
    scenarios: list[Scenario] = field(default_factory=list)  # type: ignore[type-arg]
    scenario_names: list[str] = field(default_factory=list)
    scenario_paths: list[str] = field(default_factory=list)

    # Competitor info
    competitor_names: list[str] = field(default_factory=list)
    opponent_names: list[str] = field(default_factory=list)

    # Tournament configuration (stored for display during running tournaments)
    # This mirrors what negmas writes to config.yaml
    config: dict[str, Any] = field(default_factory=dict)

    def emit_setup_progress(self, message: str, current: int, total: int) -> None:
        """Emit a setup progress event (for both SSE and polling)."""
        data = {"message": message, "current": current, "total": total}
        self.setup_progress = data
        self.event_queue.put(("setup_progress", data))

    def emit_live_negotiation(self, run_id: str, data: dict[str, Any]) -> None:
        """Update live negotiation data (for polling)."""
        self.live_negotiations[run_id] = data

    def remove_live_negotiation(self, run_id: str) -> None:
        """Remove a completed negotiation from live negotiations."""
        self.live_negotiations.pop(run_id, None)


# Module-level callback functions for negotiation monitoring
# These match NegMAS signature: Callable[[str | int, SAOState], None]
# NegMAS wraps these with _PicklableCallback internally using cloudpickle,
# so they must use multiprocessing-safe types (Manager().Queue, Manager().dict)
# to be picklable across processes.


def _make_neg_start_callback(
    event_queue: Any,  # multiprocessing.Manager().Queue - picklable
    cancel_flags: Any,  # multiprocessing.Manager().dict - picklable
    live_negotiations: Any,  # multiprocessing.Manager().dict - for polling
    session_id: str,
) -> Callable[[str | int, Any], None]:
    """Create a negotiation start callback.

    Args:
        event_queue: MP-safe queue (from Manager().Queue()).
        cancel_flags: MP-safe dict (from Manager().dict()).
        live_negotiations: MP-safe dict for live negotiation state (for polling).
        session_id: The tournament session ID.
    """

    def callback(run_id: str | int, neg_state: Any) -> None:
        if cancel_flags.get(session_id, False):
            return
        run_key = str(run_id)
        data = {
            "run_id": run_key,
            "n_negotiators": neg_state.n_negotiators,
            "step": neg_state.step,
            "relative_time": neg_state.relative_time,
            "status": "running",
        }
        event_queue.put(("neg_start", data))
        # Store for polling
        live_negotiations[run_key] = data

    return callback


def _make_neg_progress_callback(
    event_queue: Any,  # multiprocessing.Manager().Queue - picklable
    cancel_flags: Any,  # multiprocessing.Manager().dict - picklable
    live_negotiations: Any,  # multiprocessing.Manager().dict - for polling
    session_id: str,
    sample_rate: int = 1,
) -> Callable[[str | int, Any], None]:
    """Create a negotiation progress callback.

    Args:
        event_queue: MP-safe queue (from Manager().Queue()).
        cancel_flags: MP-safe dict (from Manager().dict()).
        live_negotiations: MP-safe dict for live negotiation state (for polling).
        session_id: The tournament session ID.
        sample_rate: Emit progress event every N steps (1 = every step).
    """
    # Track last emitted step per run_id to implement sampling
    # Note: This is a regular dict captured in the closure, but it's okay because
    # cloudpickle serializes the entire closure state. Each worker process gets
    # its own copy of last_emitted, which is fine for sampling purposes.
    last_emitted: dict[str, int] = {}

    def callback(run_id: str | int, neg_state: Any) -> None:
        if cancel_flags.get(session_id, False):
            return

        run_key = str(run_id)
        current_step = neg_state.step

        # Only emit if we've advanced by sample_rate steps since last emit
        last_step = last_emitted.get(run_key, -sample_rate)
        if current_step - last_step < sample_rate:
            return

        last_emitted[run_key] = current_step

        data = {
            "run_id": run_key,
            "step": current_step,
            "relative_time": neg_state.relative_time,
            "current_offer": list(neg_state.current_offer)
            if neg_state.current_offer
            else None,
            "current_proposer": neg_state.current_proposer,
            "status": "running",
        }
        event_queue.put(("neg_progress", data))
        # Update for polling
        if run_key in live_negotiations:
            existing = dict(live_negotiations[run_key])
            existing.update(data)
            live_negotiations[run_key] = existing

    return callback


def _make_neg_end_callback(
    event_queue: Any,  # multiprocessing.Manager().Queue - picklable
    cancel_flags: Any,  # multiprocessing.Manager().dict - picklable
    live_negotiations: Any,  # multiprocessing.Manager().dict - for polling
    session_id: str,
) -> Callable[[str | int, Any], None]:
    """Create a negotiation end callback.

    Args:
        event_queue: MP-safe queue (from Manager().Queue()).
        cancel_flags: MP-safe dict (from Manager().dict()).
        live_negotiations: MP-safe dict for live negotiation state (for polling).
        session_id: The tournament session ID.
    """

    def callback(run_id: str | int, neg_state: Any) -> None:
        if cancel_flags.get(session_id, False):
            return
        run_key = str(run_id)
        data = {
            "run_id": run_key,
            "step": neg_state.step,
            "relative_time": neg_state.relative_time,
            "agreement": list(neg_state.agreement) if neg_state.agreement else None,
            "timedout": neg_state.timedout,
            "broken": neg_state.broken,
            "has_error": neg_state.has_error,
            "status": "completed",
        }
        event_queue.put(("neg_end", data))
        # Remove from live negotiations (it's done)
        live_negotiations.pop(run_key, None)

    return callback


class TournamentManager:
    """Manage tournament sessions with real-time progress updates via callbacks."""

    def __init__(self):
        self.sessions: dict[str, TournamentSession] = {}
        # Use MP-safe dict for cancel flags so callbacks can be pickled for parallel execution
        self._cancel_flags: Any = _create_mp_dict()
        self._tournament_states: dict[str, TournamentState] = {}
        self._background_threads: dict[str, threading.Thread] = {}
        self.scenario_loader = ScenarioLoader()
        # Default tournaments directory
        self.tournaments_dir = Path.home() / "negmas" / "app" / "tournaments"
        self.tournaments_dir.mkdir(exist_ok=True, parents=True)

    def create_session(self, config: TournamentConfig) -> TournamentSession:
        """Create a new tournament session.

        Args:
            config: Tournament configuration.

        Returns:
            Created session (not yet started).
        """
        # Generate session ID with timestamp for uniqueness and consistency with save path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"{timestamp}_{short_uuid}"

        # Set default save_path if not provided
        if config.save_path is None:
            config.save_path = str(self.tournaments_dir / session_id)

        session = TournamentSession(
            id=session_id,
            status=TournamentStatus.PENDING,
            config=config,
        )
        self.sessions[session_id] = session
        self._cancel_flags[session_id] = False
        self._tournament_states[session_id] = TournamentState()
        return session

    def continue_session(self, tournament_path: str) -> TournamentSession:
        """Create a session to continue an existing tournament from disk.

        Args:
            tournament_path: Path to the existing tournament directory.

        Returns:
            Created session ready to be run via run_tournament_stream().

        Raises:
            ValueError: If the tournament path doesn't exist or is invalid.
        """
        path = Path(tournament_path)
        if not path.exists():
            raise ValueError(f"Tournament path does not exist: {tournament_path}")

        config_file = path / "config.yaml"
        if not config_file.exists():
            raise ValueError(f"Tournament config not found at: {config_file}")

        # Use the original tournament ID from the path name, not a new UUID
        # This ensures continuity with the saved tournament data
        session_id = path.name

        # Check if there's already an active session with this ID
        if session_id in self.sessions:
            existing = self.sessions[session_id]
            if existing.status in (TournamentStatus.RUNNING, TournamentStatus.PENDING):
                raise ValueError(
                    f"Tournament {session_id} is already running or pending"
                )
            # Clean up old session data
            self.sessions.pop(session_id, None)
            self._cancel_flags.pop(session_id, None)
            self._tournament_states.pop(session_id, None)
            self._background_threads.pop(session_id, None)

        # Create minimal config - continue_cartesian_tournament will load from config.yaml
        # We just need to know the path and basic settings
        config = TournamentConfig(
            competitor_types=[],  # Will be loaded from config.yaml
            scenario_paths=[],  # Will be loaded from saved scenarios
            save_path=str(path),
            path_exists="continue",  # Force continue mode
        )

        session = TournamentSession(
            id=session_id,
            status=TournamentStatus.PENDING,
            config=config,
        )
        self.sessions[session_id] = session
        self._cancel_flags[session_id] = False
        self._tournament_states[session_id] = TournamentState()
        return session

    def start_tournament(self, session_id: str) -> bool:
        """Start a tournament running in the background.

        This starts the tournament in a background thread without blocking.
        Use get_session() and get_tournament_state() to poll for progress.

        Args:
            session_id: The session ID to start.

        Returns:
            True if started successfully, False if session not found or already running.
        """
        session = self.sessions.get(session_id)
        state = self._tournament_states.get(session_id)

        if session is None or session.config is None or state is None:
            return False

        # Check if already running
        thread = self._background_threads.get(session_id)
        if thread is not None and thread.is_alive():
            return True  # Already running

        # Start the tournament in a background thread
        thread = threading.Thread(
            target=self._run_tournament_in_background,
            args=(session_id,),
            daemon=True,
        )
        self._background_threads[session_id] = thread
        thread.start()
        return True

    def get_session(self, session_id: str) -> TournamentSession | None:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def get_tournament_state(self, session_id: str) -> TournamentState | None:
        """Get the current tournament state for a session."""
        return self._tournament_states.get(session_id)

    def cancel_session(
        self, session_id: str, delete_results: bool = False
    ) -> dict[str, Any]:
        """Request cancellation of a running session.

        Args:
            session_id: Session to cancel.
            delete_results: If True, delete the tournament folder and all results.

        Returns:
            Status dict with 'success', 'status', and optional 'deleted_path'.
        """
        if session_id not in self._cancel_flags:
            return {"success": False, "error": "Session not found"}

        self._cancel_flags[session_id] = True

        session = self.sessions.get(session_id)
        state = self._tournament_states.get(session_id)

        result: dict[str, Any] = {"success": True, "status": "cancelled"}

        # Update state
        if state:
            state.status = TournamentStatus.CANCELLED
            # Signal the SSE stream to end
            state.event_queue.put(("cancelled", None))

        if session:
            session.status = TournamentStatus.CANCELLED
            session.end_time = datetime.now()

            # Delete results if requested
            if delete_results and session.config and session.config.save_path:
                save_path = Path(session.config.save_path)
                if save_path.exists():
                    shutil.rmtree(save_path)
                    result["deleted_path"] = str(save_path)

        return result

    def list_sessions(self) -> list[TournamentSession]:
        """List all tournament sessions."""
        return list(self.sessions.values())

    def _cleanup_redundant_csvs(self, path: Path) -> list[str]:
        """Remove redundant CSV files when parquet equivalents exist.

        When storage_format="parquet", negmas may still create CSV files alongside
        the parquet files. This method removes those redundant CSVs to save space.

        Args:
            path: Path to tournament directory.

        Returns:
            List of removed file paths.
        """
        removed: list[str] = []
        path = Path(path)

        if not path.exists():
            return removed

        # Files that may have redundant CSV/parquet pairs
        base_names = ["all_scores", "details"]

        for base_name in base_names:
            parquet_file = path / f"{base_name}.parquet"
            csv_file = path / f"{base_name}.csv"
            csv_gz_file = path / f"{base_name}.csv.gz"

            # Only remove CSV if parquet exists
            if parquet_file.exists():
                if csv_file.exists():
                    csv_file.unlink()
                    removed.append(str(csv_file))
                if csv_gz_file.exists():
                    csv_gz_file.unlink()
                    removed.append(str(csv_gz_file))

        return removed

    def _get_mechanism_class(self, mechanism_type: str) -> type[SAOMechanism]:
        """Get mechanism class by name."""
        mechanism_map = {
            "SAOMechanism": SAOMechanism,
        }

        if mechanism_type in mechanism_map:
            return mechanism_map[mechanism_type]

        try:
            from negmas import sao

            if hasattr(sao, mechanism_type):
                return getattr(sao, mechanism_type)
        except ImportError:
            pass

        return SAOMechanism

    def _build_config_for_display(
        self,
        config: TournamentConfig,
        scenario_names: list[str],
        competitor_names: list[str],
        opponent_names: list[str],
    ) -> dict[str, Any]:
        """Build a JSON-serializable config dict for display during running tournament.

        This mirrors the structure negmas writes to config.yaml so the frontend
        can display consistent information for both running and completed tournaments.
        """
        return {
            # Names (these get updated with actual names from negmas later)
            "competitor_names": competitor_names,
            "opponent_names": opponent_names,
            "scenario_names": scenario_names,
            # Full type paths
            "competitors": config.competitor_types,
            "opponents": config.opponent_types,
            # Tournament structure
            "n_repetitions": config.n_repetitions,
            "n_scenarios": len(scenario_names),
            "rotate_ufuns": config.rotate_ufuns,
            "self_play": config.self_play,
            "randomize_runs": config.randomize_runs,
            "sort_runs": config.sort_runs,
            # Mechanism settings
            "mechanism_type": config.mechanism_type,
            "n_steps": config.n_steps,
            "time_limit": config.time_limit,
            "step_time_limit": config.step_time_limit,
            "negotiator_time_limit": config.negotiator_time_limit,
            "hidden_time_limit": config.hidden_time_limit,
            "pend": config.pend,
            "pend_per_second": config.pend_per_second,
            # Scoring
            "final_score": [config.final_score_metric, config.final_score_stat],
            # Information revelation
            "id_reveals_type": config.id_reveals_type,
            "name_reveals_type": config.name_reveals_type,
            "mask_scenario_names": config.mask_scenario_names,
            "only_failures_on_self_play": config.only_failures_on_self_play,
            # Storage
            "path": config.save_path,
            "path_exists": config.path_exists,
            "storage_format": config.storage_format,
            "storage_optimization": config.storage_optimization,
            "memory_optimization": config.memory_optimization,
            "save_stats": config.save_stats,
            "save_scenario_figs": config.save_scenario_figs,
            "save_every": config.save_every,
            "save_negotiations_as_folders": config.save_negotiations_as_folders,
            # Scenario handling
            "ignore_discount": config.ignore_discount,
            "ignore_reserved": config.ignore_reserved,
            # Execution
            "njobs": config.njobs,
            "verbosity": config.verbosity,
            "raise_exceptions": config.raise_exceptions,
            # Opponent modeling
            "opponent_modeling_metrics": config.opponent_modeling_metrics,
            "distribute_opponent_modeling_scores": config.distribute_opponent_modeling_scores,
            # Params (if any)
            "competitor_params": config.competitor_params,
            "opponent_params": config.opponent_params,
        }

    def _create_callbacks(
        self, session_id: str, config: TournamentConfig
    ) -> tuple[
        Callable[[Any], None],
        Callable[[Any], None],
        Callable[[dict[str, Any]], None],
        Callable[[str, int, int], None],
        Callable[[str | int, Any], None] | None,
        Callable[[str | int, Any], None] | None,
        Callable[[str | int, Any], None] | None,
    ]:
        """Create callback functions for the tournament.

        These callbacks update the shared TournamentState and push events
        to the event queue for SSE streaming.

        Returns:
            Tuple of (before_start_callback, after_construction_callback,
                     after_end_callback, progress_callback, neg_start_callback,
                     neg_progress_callback, neg_end_callback)
        """
        state = self._tournament_states[session_id]

        # Negotiation monitoring callbacks (only if enabled)
        # NegMAS wraps these with _PicklableCallback using cloudpickle,
        # so closures work fine in parallel execution
        neg_start_callback = None
        neg_progress_callback = None
        neg_end_callback = None

        if config.monitor_negotiations:
            neg_start_callback = _make_neg_start_callback(
                state.event_queue,
                self._cancel_flags,
                state.live_negotiations,
                session_id,
            )
            neg_progress_callback = _make_neg_progress_callback(
                state.event_queue,
                self._cancel_flags,
                state.live_negotiations,
                session_id,
                sample_rate=config.progress_sample_rate,
            )
            neg_end_callback = _make_neg_end_callback(
                state.event_queue,
                self._cancel_flags,
                state.live_negotiations,
                session_id,
            )

        def before_start_callback(info: Any) -> None:
            """Called before each negotiation starts.

            Uses info.config to get competitor_names/opponent_names for index lookup.
            """
            if self._cancel_flags.get(session_id, False):
                return

            # Extract info about the upcoming negotiation
            scenario_name = info.s.outcome_space.name or "unknown"
            partner_names = list(info.partner_names) if info.partner_names else []
            rep = info.rep

            # Get name lists from config (negmas passes this with correct order)
            run_config = getattr(info, "config", {}) or {}
            config_competitor_names = run_config.get("competitor_names", [])
            config_opponent_names = run_config.get("opponent_names", [])

            # Update state names from config on first callback (replaces placeholders)
            if config_competitor_names and state.competitor_names[0].startswith(
                "Competitor "
            ):
                state.competitor_names = config_competitor_names
                # Emit updated grid_init with actual names
                if state.grid_init:
                    state.grid_init = TournamentGridInit(
                        competitors=config_competitor_names,
                        opponents=config_opponent_names or config_competitor_names,
                        scenarios=state.scenario_names,
                        n_repetitions=state.grid_init.n_repetitions,
                        rotate_ufuns=state.grid_init.rotate_ufuns,
                        total_negotiations=state.grid_init.total_negotiations,
                        storage_path=state.grid_init.storage_path,
                    )
                    state.event_queue.put(("grid_init", state.grid_init))
            if config_opponent_names and state.opponent_names[0].startswith(
                ("Opponent ", "Competitor ")
            ):
                state.opponent_names = config_opponent_names

            # Parse scenario name for rotation suffix (e.g., "domain-1" -> base="domain", rotated=True)
            base_scenario_name = scenario_name
            rotated = False
            if "-" in scenario_name:
                parts = scenario_name.rsplit("-", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    rotation_idx = int(parts[1])
                    if rotation_idx > 0:
                        rotated = True
                        base_scenario_name = parts[0]

            # Determine competitor/opponent indices using config name lists
            comp_idx = 0
            opp_idx = 0

            if len(partner_names) >= 2:
                p0, p1 = partner_names[0], partner_names[1]
                # Use config names for lookup (they're in the same order as types)
                if config_competitor_names and p0 in config_competitor_names:
                    comp_idx = config_competitor_names.index(p0)

                # For opponent index: if no explicit opponents (empty list), use competitor_names
                # Otherwise use opponent_names
                if config_opponent_names and p1 in config_opponent_names:
                    opp_idx = config_opponent_names.index(p1)
                elif config_competitor_names and p1 in config_competitor_names:
                    # No explicit opponents - competitors play each other
                    opp_idx = config_competitor_names.index(p1)

            scenario_idx = 0
            if base_scenario_name in state.scenario_names:
                scenario_idx = state.scenario_names.index(base_scenario_name)
            elif scenario_name in state.scenario_names:
                scenario_idx = state.scenario_names.index(scenario_name)

            # Create run_start update
            cell_start = CellUpdate(
                competitor_idx=comp_idx,
                opponent_idx=opp_idx,
                scenario_idx=scenario_idx,
                repetition=rep,
                rotated=rotated,
                status=CellStatus.RUNNING,
            )

            state.current_cell = cell_start
            state.event_queue.put(("run_start", cell_start))

        def after_construction_callback(info: Any) -> None:
            """Called after mechanism is constructed but before it runs."""
            # Can be used for additional setup if needed
            pass

        def after_end_callback(
            record: dict[str, Any], run_config: dict[str, Any] | None = None
        ) -> None:
            """Called after each negotiation ends with full results.

            Uses run_config to get competitor_names/opponent_names for index lookup.
            """
            if self._cancel_flags.get(session_id, False):
                return

            # Extract data from record
            scenario_name = record.get("scenario", "unknown")
            partners = record.get("partners", [])
            agreement = record.get("agreement")
            utilities = record.get("utilities", [])
            has_error = record.get("has_error", False)
            error_details = record.get("error_details")
            n_steps = record.get("last_step", 0)
            broken = record.get("broken", False)
            timedout = record.get("timedout", False)
            run_id = record.get("run_id")  # Unique ID for loading negotiation data

            # Get name lists from config (negmas passes this with correct order)
            run_config = run_config or {}
            config_competitor_names = run_config.get("competitor_names", [])
            config_opponent_names = run_config.get("opponent_names", [])

            # Determine end reason
            if has_error or broken:
                end_reason = NegotiationEndReason.BROKEN
            elif agreement is not None:
                end_reason = NegotiationEndReason.AGREEMENT
            elif timedout:
                end_reason = NegotiationEndReason.TIMEOUT
            else:
                end_reason = NegotiationEndReason.TIMEOUT

            # Parse scenario name for rotation suffix (e.g., "domain-1" -> base="domain", rotated=True)
            # negmas appends "-N" to scenario names for rotated runs where N > 0
            base_scenario_name = scenario_name
            rotated = False
            if "-" in scenario_name:
                parts = scenario_name.rsplit("-", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    rotation_idx = int(parts[1])
                    if rotation_idx > 0:
                        rotated = True
                        base_scenario_name = parts[0]

            # Get indices using config name lists
            comp_idx = 0
            opp_idx = 0
            scenario_idx = 0
            rep = 0

            if len(partners) >= 2:
                p0, p1 = partners[0], partners[1]
                # Use config names for lookup (they're in the same order as types)
                if config_competitor_names and p0 in config_competitor_names:
                    comp_idx = config_competitor_names.index(p0)

                # For opponent index: if no explicit opponents (empty list), use competitor_names
                # Otherwise use opponent_names
                if config_opponent_names and p1 in config_opponent_names:
                    opp_idx = config_opponent_names.index(p1)
                elif config_competitor_names and p1 in config_competitor_names:
                    # No explicit opponents - competitors play each other
                    opp_idx = config_competitor_names.index(p1)

            # Try to match the base scenario name to our list
            if base_scenario_name in state.scenario_names:
                scenario_idx = state.scenario_names.index(base_scenario_name)
            elif scenario_name in state.scenario_names:
                # Fallback to exact match (for non-rotated or differently named scenarios)
                scenario_idx = state.scenario_names.index(scenario_name)

            # Get scenario path
            scenario_path = None
            if scenario_idx < len(state.scenario_paths):
                scenario_path = state.scenario_paths[scenario_idx]

            # Create run_complete update
            cell_complete = CellUpdate(
                competitor_idx=comp_idx,
                opponent_idx=opp_idx,
                scenario_idx=scenario_idx,
                repetition=rep,
                rotated=rotated,
                status=CellStatus.COMPLETE,
                end_reason=end_reason,
                utilities=list(utilities) if utilities else None,
                error=error_details,
                scenario_path=scenario_path,
                n_steps=n_steps,
                agreement=tuple(agreement) if agreement else None,
                run_id=str(run_id) if run_id is not None else None,
            )

            state.completed_cells.append(cell_complete)
            state.current_cell = None
            state.event_queue.put(("run_complete", cell_complete))

            # Track completed negotiation with details for the Negotiations panel
            competitor_name = partners[0] if len(partners) >= 1 else "Unknown"
            opponent_name = partners[1] if len(partners) >= 2 else "Unknown"
            completed_neg = {
                "run_id": str(run_id)
                if run_id is not None
                else str(len(state.completed_negotiations)),
                "competitor": competitor_name,
                "opponent": opponent_name,
                "scenario": base_scenario_name,
                "result": end_reason.value,
                "agreement": list(agreement) if agreement else None,
                "utilities": list(utilities) if utilities else None,
                "n_steps": n_steps,
                "has_error": has_error,
                "error_details": error_details,
                "rotated": rotated,
            }
            state.completed_negotiations.append(completed_neg)

            # Update competitor statistics
            self._update_stats_from_record(state, record, config)

            # Build and emit leaderboard
            leaderboard = self._build_leaderboard(
                state.competitor_stats,
                config.final_score_metric,
                config.final_score_stat,
            )
            state.leaderboard = leaderboard
            state.event_queue.put(("leaderboard", leaderboard))

            # Update progress
            completed = len(state.completed_cells)
            total = state.progress.total if state.progress else 0
            state.progress = TournamentProgress(
                completed=completed,
                total=total,
                current_scenario=scenario_name,
                current_partners=list(partners) if partners else None,
                percent=(completed / total * 100) if total > 0 else 0,
            )
            state.event_queue.put(("progress", state.progress))

        def progress_callback(
            message: str,
            current: int,
            total: int,
            config_dict: dict[str, Any] | None = None,
        ) -> None:
            """Called during tournament setup to report progress.

            Args:
                message: Description of current setup phase.
                current: Current step (1-3 typically).
                total: Total steps (3 typically).
                config_dict: Optional config dict with competitor_names/opponent_names (from negmas).
            """
            if self._cancel_flags.get(session_id, False):
                return

            # On first call with config, extract competitor/opponent names
            # This happens during setup (step 1 of 3) before negotiations start
            if config_dict and current == 1:
                competitor_names = config_dict.get("competitor_names")
                opponent_names = config_dict.get("opponent_names")

                # Update state with real names (replacing placeholders)
                if competitor_names:
                    state.competitor_names = competitor_names
                if opponent_names:
                    state.opponent_names = opponent_names
                elif competitor_names and not config.opponent_types:
                    # When no explicit opponents, opponents = competitors
                    state.opponent_names = competitor_names

                # Emit updated grid_init with real names
                if state.grid_init and competitor_names:
                    state.grid_init = TournamentGridInit(
                        competitors=state.competitor_names,
                        opponents=state.opponent_names,
                        scenarios=state.scenario_names,
                        n_repetitions=state.grid_init.n_repetitions,
                        rotate_ufuns=state.grid_init.rotate_ufuns,
                        total_negotiations=state.grid_init.total_negotiations,
                        storage_path=state.grid_init.storage_path,
                    )
                    state.event_queue.put(("grid_init", state.grid_init))

            # Emit a setup_progress event (for both SSE and polling)
            state.emit_setup_progress(message, current, total)

        return (
            before_start_callback,
            after_construction_callback,
            after_end_callback,
            progress_callback,
            neg_start_callback,
            neg_progress_callback,
            neg_end_callback,
        )

    def _update_stats_from_record(
        self,
        state: TournamentState,
        record: dict[str, Any],
        config: TournamentConfig,
    ) -> None:
        """Update competitor statistics from a negotiation record.

        Collects all available metrics from the record including:
        - utilities: raw utility values
        - advantages: utility - partner utility (for 2-party)
        - welfare: sum of utilities
        - partner_welfare: partner's utility
        - time: negotiation time
        - Optimality metrics: nash, kalai, ks, max_welfare, pareto optimality
        - fairness: max(nash, kalai, ks optimality)
        """
        import math

        partners = record.get("partners", [])
        utilities = record.get("utilities", [])
        agreement = record.get("agreement")

        if not partners or not utilities:
            return

        # All metrics we can collect from records
        # These match the columns in all_scores.csv from negmas tournaments
        optimality_metrics = [
            "nash_optimality",
            "kalai_optimality",
            "ks_optimality",
            "max_welfare_optimality",
            "pareto_optimality",
            "fairness",
            "modified_kalai_optimality",
            "modified_ks_optimality",
        ]

        for i, name in enumerate(partners):
            # Dynamically create stats entry if it doesn't exist
            # (negmas may use different names than we initialized)
            if name not in state.competitor_stats:
                state.competitor_stats[name] = {
                    "utilities": [],
                    "advantages": [],
                    "welfare": [],
                    "partner_welfare": [],
                    "time": [],
                    "n_negotiations": 0,
                    "n_agreements": 0,
                }
                # Add optimality metric lists
                for metric in optimality_metrics:
                    state.competitor_stats[name][metric] = []

            stats = state.competitor_stats[name]
            stats["n_negotiations"] += 1

            if agreement is not None:
                stats["n_agreements"] += 1

            if i < len(utilities) and utilities[i] is not None:
                util_value = float(utilities[i])

                # Check for infinite/nan utility values and emit warning
                if math.isinf(util_value) or math.isnan(util_value):
                    scenario_name = record.get("scenario", "unknown")
                    warning_msg = (
                        f"Infinite utility ({util_value}) for {name} in {scenario_name}. "
                        f"Consider running 'negmas-app cache build scenarios --ensure-finite-reserved-values' "
                        f"to fix scenario reserved values."
                    )
                    state.event_queue.put(("warning", warning_msg))
                    # Skip adding infinite values to stats as they'll corrupt mean calculations
                    continue

                stats["utilities"].append(util_value)

                # Calculate advantage and partner_welfare if 2-party
                if len(utilities) == 2:
                    other_idx = 1 - i
                    if utilities[other_idx] is not None:
                        other_util = float(utilities[other_idx])
                        # Skip advantage calculation if other utility is also infinite/nan
                        if not (math.isinf(other_util) or math.isnan(other_util)):
                            advantage = util_value - other_util
                            stats["advantages"].append(advantage)
                            stats["partner_welfare"].append(other_util)

                # Calculate welfare (sum of all utilities)
                welfare = sum(
                    float(u)
                    for u in utilities
                    if u is not None
                    and not (math.isinf(float(u)) or math.isnan(float(u)))
                )
                if not math.isnan(welfare) and not math.isinf(welfare):
                    stats["welfare"].append(welfare)

            # Collect time if available
            time_val = record.get("time") or record.get("execution_time")
            if time_val is not None:
                try:
                    time_float = float(time_val)
                    if not (math.isnan(time_float) or math.isinf(time_float)):
                        stats["time"].append(time_float)
                except (ValueError, TypeError):
                    pass

            # Collect optimality metrics from record (these are per-negotiation, same for all parties)
            for metric in optimality_metrics:
                val = record.get(metric)
                if val is not None:
                    try:
                        val_float = float(val)
                        if not (math.isnan(val_float) or math.isinf(val_float)):
                            stats[metric].append(val_float)
                    except (ValueError, TypeError):
                        pass

    def _build_leaderboard(
        self,
        stats: dict[str, dict[str, Any]],
        metric: str,
        stat: str,
    ) -> list[LeaderboardEntry]:
        """Build a live leaderboard from current competitor statistics.

        Supports all metrics collected in _update_stats_from_record:
        - utility, advantage, welfare, partner_welfare, time
        - nash_optimality, kalai_optimality, ks_optimality
        - max_welfare_optimality, pareto_optimality
        - fairness, modified_kalai_optimality, modified_ks_optimality
        """
        import statistics as stats_module

        entries: list[LeaderboardEntry] = []

        for name, s in stats.items():
            # Map metric name to stats key
            # Default to advantages for backward compatibility
            metric_key = metric
            if metric == "advantage":
                metric_key = "advantages"
            elif metric == "utility":
                metric_key = "utilities"

            # Get values for the metric (may not exist for all strategies)
            values = s.get(metric_key, [])

            # Fallback: if the requested metric has no data, use advantages
            if not values and metric_key not in ["utilities", "advantages"]:
                values = s.get("advantages", [])

            if not values:
                score = 0.0
            elif stat == "mean":
                score = stats_module.mean(values)
            elif stat == "median":
                score = stats_module.median(values)
            elif stat == "min":
                score = min(values)
            elif stat == "max":
                score = max(values)
            elif stat == "std":
                score = stats_module.stdev(values) if len(values) > 1 else 0.0
            else:
                score = stats_module.mean(values)

            mean_utility = (
                stats_module.mean(s["utilities"]) if s.get("utilities") else None
            )

            entries.append(
                LeaderboardEntry(
                    name=name,
                    score=score,
                    rank=0,
                    n_negotiations=s["n_negotiations"],
                    n_agreements=s["n_agreements"],
                    mean_utility=mean_utility,
                )
            )

        # Sort by score - descending for most metrics, ascending for time
        reverse = metric != "time"
        entries.sort(key=lambda x: x.score, reverse=reverse)
        for i, entry in enumerate(entries):
            entry.rank = i + 1

        return entries

    def _run_tournament_in_background(self, session_id: str) -> None:
        """Run the tournament in a background thread using cartesian_tournament.

        This method is called in a separate thread and uses callbacks to
        update the shared TournamentState.
        """
        session = self.sessions.get(session_id)
        state = self._tournament_states.get(session_id)

        if session is None or session.config is None or state is None:
            return

        config = session.config

        try:
            # Check if we're continuing an existing tournament
            # (indicated by empty competitor_types and path_exists="continue")
            is_continue = (
                not config.competitor_types
                and config.save_path
                and config.path_exists == "continue"
            )

            if is_continue:
                # Use continue_cartesian_tournament for existing tournaments
                state.emit_setup_progress("Loading existing tournament...", 1, 3)

                # Load existing tournament config to get names and settings
                config_file = Path(config.save_path) / "config.yaml"
                if config_file.exists():
                    import yaml

                    with open(config_file, "r") as f:
                        saved_config = yaml.safe_load(f)

                    # Extract competitor/opponent names from saved config
                    competitor_names = saved_config.get("competitor_names", [])
                    opponent_names = saved_config.get("opponent_names", [])

                    # Get scenario names from scenarios directory
                    scenarios_dir = Path(config.save_path) / "scenarios"
                    scenario_names = []
                    scenario_paths = []
                    if scenarios_dir.exists():
                        for scenario_dir in sorted(scenarios_dir.iterdir()):
                            if scenario_dir.is_dir():
                                scenario_names.append(scenario_dir.name)
                                scenario_paths.append(str(scenario_dir))

                    # Initialize state with loaded names
                    state.competitor_names = (
                        competitor_names if competitor_names else ["Competitor"]
                    )
                    state.opponent_names = (
                        opponent_names
                        if opponent_names
                        else competitor_names
                        if competitor_names
                        else ["Opponent"]
                    )
                    state.scenario_names = scenario_names
                    state.scenario_paths = scenario_paths

                    # Calculate total negotiations
                    n_competitors = len(state.competitor_names)
                    n_opponents = len(state.opponent_names)
                    n_scenarios = len(scenario_names)
                    n_repetitions = saved_config.get("n_repetitions", 1)
                    rotate_ufuns = saved_config.get("rotate_ufuns", True)
                    rotation_factor = 2 if rotate_ufuns else 1
                    total_negotiations = (
                        n_competitors
                        * n_opponents
                        * n_scenarios
                        * n_repetitions
                        * rotation_factor
                    )

                    # Update config with loaded settings for callbacks
                    config.monitor_negotiations = saved_config.get(
                        "monitor_negotiations", True
                    )
                    config.progress_sample_rate = saved_config.get(
                        "progress_sample_rate", 5
                    )
                    config.final_score_metric = saved_config.get(
                        "final_score_metric", "advantage"
                    )
                    # Load njobs from saved config (default to -1 for serial)
                    config.njobs = saved_config.get("njobs", -1)
                    config.final_score_stat = saved_config.get(
                        "final_score_stat", "mean"
                    )

                    # Emit grid_init so frontend can display the grid
                    state.grid_init = TournamentGridInit(
                        competitors=state.competitor_names,
                        opponents=state.opponent_names,
                        scenarios=scenario_names,
                        n_repetitions=n_repetitions,
                        rotate_ufuns=rotate_ufuns,
                        total_negotiations=total_negotiations,
                        storage_path=config.save_path,
                    )
                    state.event_queue.put(("grid_init", state.grid_init))

                    # Load existing completed negotiations from results folder
                    # to initialize the grid with already-completed cells
                    from .tournament_storage import TournamentStorageService

                    existing_negotiations = (
                        TournamentStorageService._load_negotiations_summary(
                            Path(config.save_path)
                        )
                    )
                    n_already_completed = len(existing_negotiations)

                    if n_already_completed > 0:
                        # Build cell states from existing negotiations
                        _, cell_states_dict = (
                            TournamentStorageService._build_grid_structures(
                                Path(config.save_path), existing_negotiations
                            )
                        )

                        # Emit cell states for each completed cell
                        for cell_id, cell_data in cell_states_dict.items():
                            # Parse cell_id to get indices
                            parts = cell_id.split("::")
                            if len(parts) >= 3:
                                competitor, opponent, scenario = (
                                    parts[0],
                                    parts[1],
                                    parts[2],
                                )

                                # Find indices
                                comp_idx = (
                                    state.competitor_names.index(competitor)
                                    if competitor in state.competitor_names
                                    else 0
                                )
                                opp_idx = (
                                    state.opponent_names.index(opponent)
                                    if opponent in state.opponent_names
                                    else 0
                                )
                                scenario_idx = (
                                    scenario_names.index(scenario)
                                    if scenario in scenario_names
                                    else 0
                                )

                                # Determine end reason from cell data
                                if cell_data.get("errors", 0) > 0:
                                    end_reason = NegotiationEndReason.BROKEN
                                elif cell_data.get("agreements", 0) > 0:
                                    end_reason = NegotiationEndReason.AGREEMENT
                                elif cell_data.get("timeouts", 0) > 0:
                                    end_reason = NegotiationEndReason.TIMEOUT
                                else:
                                    end_reason = NegotiationEndReason.TIMEOUT

                                # Create cell update for completed cell
                                cell_update = CellUpdate(
                                    competitor_idx=comp_idx,
                                    opponent_idx=opp_idx,
                                    scenario_idx=scenario_idx,
                                    repetition=0,
                                    rotated=False,
                                    status=CellStatus.COMPLETE,
                                    end_reason=end_reason,
                                    utilities=cell_data.get("utilities"),
                                )
                                state.completed_cells.append(cell_update)
                                state.event_queue.put(("run_complete", cell_update))

                    # Initialize progress with already-completed count
                    state.progress = TournamentProgress(
                        completed=n_already_completed,
                        total=total_negotiations,
                        current_scenario=None,
                        current_partners=None,
                        percent=(n_already_completed / total_negotiations * 100)
                        if total_negotiations > 0
                        else 0,
                    )
                    state.event_queue.put(("progress", state.progress))

                # Update status
                state.status = TournamentStatus.RUNNING
                session.status = TournamentStatus.RUNNING
                session.start_time = datetime.now()

                # Create callbacks using the same factory method as regular tournaments
                (
                    before_start_callback,
                    after_construction_callback,
                    after_end_callback,
                    progress_callback,
                    neg_start_callback,
                    neg_progress_callback,
                    neg_end_callback,
                ) = self._create_callbacks(session_id, config)

                state.emit_setup_progress("Continuing tournament...", 2, 3)

                # Run continue_cartesian_tournament
                if not config.save_path:
                    state.status = TournamentStatus.FAILED
                    state.error = "Cannot continue tournament - no save path specified"
                    session.status = TournamentStatus.FAILED
                    session.error = state.error
                    state.event_queue.put(("error", state.error))
                    return

                # Suppress numpy/pandas warnings about empty arrays or single values
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore", message="invalid value encountered"
                    )
                    warnings.filterwarnings("ignore", message="Degrees of freedom")
                    results = continue_cartesian_tournament(
                        path=Path(config.save_path),
                        verbosity=config.verbosity,
                        njobs=config.njobs,  # Use config value (loaded from saved config)
                        before_start_callback=before_start_callback,
                        progress_callback=progress_callback,
                        neg_start_callback=neg_start_callback,
                        after_construction_callback=after_construction_callback,
                        neg_progress_callback=neg_progress_callback,
                        neg_end_callback=neg_end_callback,
                        after_end_callback=after_end_callback,
                    )

                if results is None:
                    state.status = TournamentStatus.FAILED
                    state.error = (
                        "Failed to continue tournament - invalid path or missing files"
                    )
                    session.status = TournamentStatus.FAILED
                    session.error = state.error
                    state.event_queue.put(("error", state.error))
                    return

                # Check if cancelled
                if self._cancel_flags.get(session_id, False):
                    state.status = TournamentStatus.CANCELLED
                    session.status = TournamentStatus.CANCELLED
                    session.end_time = datetime.now()
                    state.event_queue.put(("cancelled", None))
                    return

                # Build final scores from results
                final_scores: list[CompetitorScore] = []
                if results.final_scores is not None:
                    for idx, row in results.final_scores.iterrows():
                        if "strategy" in results.final_scores.columns:
                            name = str(row["strategy"])
                        else:
                            name = str(idx)
                        if "score" in results.final_scores.columns:
                            score = float(row["score"])
                        else:
                            score = float(row.iloc[0]) if len(row) > 0 else 0.0
                        final_scores.append(
                            CompetitorScore(
                                name=name,
                                type_name=name,
                                score=score,
                                rank=len(final_scores) + 1,
                            )
                        )

                total_completed = (
                    len(results.details) if results.details is not None else 0
                )
                total_agreements = 0
                if (
                    results.details is not None
                    and "agreement" in results.details.columns
                ):
                    total_agreements = int(results.details["agreement"].notna().sum())

                session.results = TournamentResults(
                    final_scores=final_scores,
                    negotiation_results=[],  # Don't rebuild from continue mode
                    total_negotiations=total_completed,
                    total_agreements=total_agreements,
                    overall_agreement_rate=(
                        total_agreements / total_completed
                        if total_completed > 0
                        else 0.0
                    ),
                    results_path=str(results.path) if results.path else None,
                )

                # Clean up redundant CSV files if parquet equivalents exist
                if config.save_path and config.storage_format == "parquet":
                    removed = self._cleanup_redundant_csvs(Path(config.save_path))
                    if removed:
                        print(
                            f"[TournamentManager] Cleaned up {len(removed)} redundant CSV files"
                        )

                state.status = TournamentStatus.COMPLETED
                session.status = TournamentStatus.COMPLETED
                session.end_time = datetime.now()

                # Emit complete event
                state.event_queue.put(("complete", session))
                return

            # Normal tournament flow (not continuing)
            # Emit initial setup progress
            state.emit_setup_progress("Loading scenarios...", 0, 4)

            # Load scenarios
            scenarios: list[Scenario] = []  # type: ignore[type-arg]
            scenario_names: list[str] = []
            scenario_paths: list[str] = []

            n_scenario_paths = len(config.scenario_paths)
            for idx, path in enumerate(config.scenario_paths):
                # Emit progress for each scenario
                if idx % 10 == 0 or idx == n_scenario_paths - 1:
                    state.emit_setup_progress(
                        f"Loading scenario {idx + 1}/{n_scenario_paths}...", 0, 4
                    )
                scenario = self.scenario_loader.load_scenario(
                    path, load_stats=False, load_info=False
                )  # Skip stats for tournament - not needed for execution
                if scenario is not None:
                    # Apply normalization (returns modified scenario)
                    scenario = _apply_normalization(
                        scenario, config.normalization, config.recalculate_stats
                    )
                    scenarios.append(scenario)
                    scenario_names.append(
                        Path(scenario.outcome_space.name or "unknown").name
                    )
                    scenario_paths.append(path)

            if not scenarios:
                state.status = TournamentStatus.FAILED
                state.error = "No valid scenarios found"
                session.status = TournamentStatus.FAILED
                session.error = "No valid scenarios found"
                state.event_queue.put(("error", "No valid scenarios found"))
                return

            # Store in state for callbacks
            state.scenarios = scenarios
            state.scenario_names = scenario_names
            state.scenario_paths = scenario_paths

            # Emit progress for competitor loading
            state.event_queue.put(
                (
                    "setup_progress",
                    {
                        "message": "Loading competitor classes...",
                        "current": 1,
                        "total": 4,
                    },
                )
            )

            # Get competitor classes
            competitors: list[type[SAONegotiator]] = []
            for type_name in config.competitor_types:
                cls = _get_class_for_type(type_name)
                if cls is not None:
                    competitors.append(cls)  # type: ignore[arg-type]

            if len(competitors) < 1:
                state.status = TournamentStatus.FAILED
                state.error = "At least 1 valid competitor required"
                session.status = TournamentStatus.FAILED
                session.error = state.error
                state.event_queue.put(("error", state.error))
                return

            # DON'T generate names here - let negmas do it and get them from results.config
            # after tournament completes. This ensures compatibility across tournaments.
            # We'll use placeholder names for the grid_init and update after first callback.
            # Names will be populated from results.config["competitor_names"] after tournament.

            # Use indices as temporary names for grid display before tournament starts
            # These will be replaced with actual names from results.config after tournament
            placeholder_competitor_names = [
                f"Competitor {i + 1}" for i in range(len(competitors))
            ]
            state.competitor_names = placeholder_competitor_names

            # DON'T initialize stats here - we'll create entries dynamically as callbacks arrive
            # with the actual names negmas generates

            # Get opponent classes if specified
            opponents: list[type[SAONegotiator]] | None = None

            if config.opponent_types is not None:
                # Emit progress for opponent loading
                state.event_queue.put(
                    (
                        "setup_progress",
                        {
                            "message": "Loading opponent classes...",
                            "current": 2,
                            "total": 4,
                        },
                    )
                )
                opponents = []
                for type_name in config.opponent_types:
                    cls = _get_class_for_type(type_name)
                    if cls is not None:
                        opponents.append(cls)  # type: ignore[arg-type]

                if len(opponents) < 1:
                    state.status = TournamentStatus.FAILED
                    state.error = "At least 1 valid opponent required"
                    session.status = TournamentStatus.FAILED
                    session.error = state.error
                    state.event_queue.put(("error", state.error))
                    return

                # DON'T generate opponent names - let negmas do it
                # Use placeholder names for grid display
                placeholder_opponent_names = [
                    f"Opponent {i + 1}" for i in range(len(opponents))
                ]
                state.opponent_names = placeholder_opponent_names
                # DON'T initialize stats - will be created dynamically in callbacks
            else:
                if len(competitors) < 2:
                    state.status = TournamentStatus.FAILED
                    state.error = "At least 2 competitors required when no opponents"
                    session.status = TournamentStatus.FAILED
                    session.error = state.error
                    state.event_queue.put(("error", state.error))
                    return
                # When no explicit opponents, opponents = competitors
                state.opponent_names = placeholder_competitor_names

            # Emit progress for building tournament configuration
            state.event_queue.put(
                (
                    "setup_progress",
                    {
                        "message": "Building tournament configuration...",
                        "current": 3,
                        "total": 4,
                    },
                )
            )

            # Calculate total negotiations
            n_competitors = len(competitors)
            n_opponents = len(state.opponent_names)
            n_scenarios = len(scenarios)

            if config.opponent_types is not None:
                n_pairings = n_competitors * n_opponents
            else:
                n_pairings = (
                    n_competitors * n_opponents
                    if config.self_play
                    else n_competitors * (n_opponents - 1)
                )
            if config.rotate_ufuns:
                n_pairings *= 2
            total_negotiations = n_scenarios * n_pairings * config.n_repetitions

            # Initialize grid and progress
            # Use placeholder names for initial display - will be updated after tournament
            grid_init = TournamentGridInit(
                competitors=placeholder_competitor_names,
                opponents=state.opponent_names,
                scenarios=scenario_names,
                n_repetitions=config.n_repetitions,
                rotate_ufuns=config.rotate_ufuns,
                total_negotiations=total_negotiations,
                storage_path=config.save_path,
            )
            state.grid_init = grid_init
            state.progress = TournamentProgress(
                completed=0, total=total_negotiations, percent=0.0
            )

            # Emit grid_init event
            state.event_queue.put(("grid_init", grid_init))
            state.event_queue.put(("progress", state.progress))

            # Create callbacks
            (
                before_cb,
                after_const_cb,
                after_end_cb,
                progress_cb,
                neg_start_cb,
                neg_progress_cb,
                neg_end_cb,
            ) = self._create_callbacks(session_id, config)

            # Get mechanism class
            mechanism_class = self._get_mechanism_class(config.mechanism_type)

            # Build tournament kwargs
            tournament_kwargs: dict[str, Any] = {
                "competitors": competitors,
                "scenarios": scenarios,
                "competitor_params": config.competitor_params,
                "opponent_params": config.opponent_params,
                "rotate_ufuns": config.rotate_ufuns,
                "n_repetitions": config.n_repetitions,
                "njobs": config.njobs,  # Use config value; callbacks now use MP-safe types
                "mechanism_type": mechanism_class,
                "n_steps": config.n_steps,
                "time_limit": config.time_limit,
                "self_play": config.self_play,
                "randomize_runs": config.randomize_runs,
                "sort_runs": config.sort_runs,
                "id_reveals_type": config.id_reveals_type,
                "name_reveals_type": config.name_reveals_type,
                "mask_scenario_names": config.mask_scenario_names,
                "only_failures_on_self_play": config.only_failures_on_self_play,
                "final_score": (config.final_score_metric, config.final_score_stat),
                "save_stats": config.save_stats,
                "save_scenario_figs": config.save_scenario_figs,
                "save_every": config.save_every,
                "verbosity": config.verbosity,
                "path": Path(config.save_path) if config.save_path else None,
                "path_exists": config.path_exists,
                "ignore_discount": config.ignore_discount,
                "ignore_reserved": config.ignore_reserved,
                "raise_exceptions": config.raise_exceptions,
                # Storage and memory optimization
                "storage_optimization": config.storage_optimization,
                "memory_optimization": config.memory_optimization,
                # Callbacks - now use MP-safe types (Manager().Queue, Manager().dict)
                # so they can be pickled for parallel execution
                "before_start_callback": before_cb,
                "after_construction_callback": after_const_cb,
                "after_end_callback": after_end_cb,
                "progress_callback": progress_cb,
                "neg_start_callback": neg_start_cb,
                "neg_progress_callback": neg_progress_cb,
                "neg_end_callback": neg_end_cb,
            }

            # Add storage format if specified
            if config.storage_format is not None:
                tournament_kwargs["storage_format"] = config.storage_format

            # Add opponent modeling metrics if specified
            if config.opponent_modeling_metrics:
                tournament_kwargs["opponent_modeling_metrics"] = (
                    config.opponent_modeling_metrics
                )

            # Add distribute_opponent_modeling_scores option
            if config.distribute_opponent_modeling_scores:
                tournament_kwargs["distribute_opponent_modeling_scores"] = True

            # Add save_negotiations_as_folders option
            tournament_kwargs["save_negotiations_as_folders"] = (
                config.save_negotiations_as_folders
            )

            # Add image format from performance settings
            perf_settings = SettingsService.load_performance()
            tournament_kwargs["image_format"] = perf_settings.plot_image_format

            # Add opponents if specified
            if opponents is not None:
                tournament_kwargs["opponents"] = opponents

            # Add optional time limits
            if config.step_time_limit is not None:
                tournament_kwargs["step_time_limit"] = config.step_time_limit
            if config.negotiator_time_limit is not None:
                tournament_kwargs["negotiator_time_limit"] = (
                    config.negotiator_time_limit
                )
            if config.hidden_time_limit is not None:
                tournament_kwargs["hidden_time_limit"] = config.hidden_time_limit
            if config.pend is not None:
                tournament_kwargs["pend"] = config.pend
            if config.pend_per_second is not None:
                tournament_kwargs["pend_per_second"] = config.pend_per_second

            # Store config in state for display during running tournament
            # This mirrors the structure negmas writes to config.yaml
            state.config = self._build_config_for_display(
                config,
                scenario_names,
                placeholder_competitor_names,
                state.opponent_names,
            )

            # Update status
            state.status = TournamentStatus.RUNNING
            session.status = TournamentStatus.RUNNING
            session.start_time = datetime.now()

            # Emit initial progress event before negotiations start
            state.event_queue.put(
                (
                    "tournament_progress",
                    {
                        "message": "Starting negotiations",
                        "completed": 0,
                        "total": total_negotiations,
                    },
                )
            )

            # Run the tournament (blocking in this thread)
            # Suppress numpy/pandas warnings about empty arrays or single values in std calculations
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="invalid value encountered")
                warnings.filterwarnings("ignore", message="Degrees of freedom")
                results = cartesian_tournament(**tournament_kwargs)  # type: ignore[arg-type]

            # Extract actual competitor/opponent names from results.config
            # These are the standardized names negmas generated, in the same order as we passed the types
            if results.config:
                actual_competitor_names = results.config.get("competitor_names", [])
                actual_opponent_names = results.config.get("opponent_names", [])
                if actual_competitor_names:
                    state.competitor_names = actual_competitor_names
                if actual_opponent_names:
                    state.opponent_names = actual_opponent_names
                elif not config.opponent_types:
                    # When no explicit opponents, opponents = competitors
                    state.opponent_names = actual_competitor_names

                # Update state.config with actual names from negmas
                if state.config:
                    state.config["competitor_names"] = state.competitor_names
                    state.config["opponent_names"] = state.opponent_names

                # Emit updated grid_init with actual names
                updated_grid_init = TournamentGridInit(
                    competitors=state.competitor_names,
                    opponents=state.opponent_names,
                    scenarios=scenario_names,
                    n_repetitions=config.n_repetitions,
                    rotate_ufuns=config.rotate_ufuns,
                    total_negotiations=total_negotiations,
                    storage_path=config.save_path,
                )
                state.grid_init = updated_grid_init
                state.event_queue.put(("grid_init", updated_grid_init))

            # Check if cancelled
            if self._cancel_flags.get(session_id, False):
                state.status = TournamentStatus.CANCELLED
                session.status = TournamentStatus.CANCELLED
                session.end_time = datetime.now()
                state.event_queue.put(("cancelled", None))
                return

            # Tournament completed successfully
            final_scores: list[CompetitorScore] = []
            if results.final_scores is not None:
                for idx, row in results.final_scores.iterrows():
                    # Get strategy name from column or index
                    if "strategy" in results.final_scores.columns:
                        name = str(row["strategy"])
                    else:
                        name = str(idx)
                    # Get score from 'score' column or first numeric column
                    if "score" in results.final_scores.columns:
                        score = float(row["score"])
                    else:
                        score = float(row.iloc[0]) if len(row) > 0 else 0.0
                    final_scores.append(
                        CompetitorScore(
                            name=name,
                            type_name=name,
                            score=score,
                            rank=len(final_scores) + 1,
                        )
                    )

            total_completed = len(results.details) if results.details is not None else 0
            total_agreements = 0
            if results.details is not None and "agreement" in results.details.columns:
                total_agreements = int(results.details["agreement"].notna().sum())

            # Build negotiation_results from completed_cells
            negotiation_results: list[NegotiationResult] = []
            for cell in state.completed_cells:
                scenario_name = (
                    state.scenario_names[cell.scenario_idx]
                    if cell.scenario_idx < len(state.scenario_names)
                    else "unknown"
                )
                competitor_name = (
                    state.competitor_names[cell.competitor_idx]
                    if cell.competitor_idx < len(state.competitor_names)
                    else "unknown"
                )
                opponent_name = (
                    state.opponent_names[cell.opponent_idx]
                    if cell.opponent_idx < len(state.opponent_names)
                    else "unknown"
                )

                neg_result = NegotiationResult(
                    scenario=scenario_name,
                    partners=[competitor_name, opponent_name],
                    agreement=cell.agreement,
                    utilities=cell.utilities,
                    advantages=None,  # Not tracked in cells
                    has_error=cell.end_reason
                    in (NegotiationEndReason.ERROR, NegotiationEndReason.BROKEN),
                    error_details=cell.error,
                    execution_time=None,  # Not tracked
                    end_reason=cell.end_reason,
                    scenario_path=cell.scenario_path,
                    n_steps=cell.n_steps,
                )
                negotiation_results.append(neg_result)

            session.results = TournamentResults(
                final_scores=final_scores,
                negotiation_results=negotiation_results,
                total_negotiations=total_completed,
                total_agreements=total_agreements,
                overall_agreement_rate=(
                    total_agreements / total_completed if total_completed > 0 else 0.0
                ),
                results_path=str(results.path) if results.path else None,
            )

            # Clean up redundant CSV files if parquet equivalents exist
            if config.save_path and config.storage_format == "parquet":
                removed = self._cleanup_redundant_csvs(Path(config.save_path))
                if removed:
                    print(
                        f"[TournamentManager] Cleaned up {len(removed)} redundant CSV files"
                    )

            state.status = TournamentStatus.COMPLETED
            session.status = TournamentStatus.COMPLETED
            session.end_time = datetime.now()

            # Emit complete event
            state.event_queue.put(("complete", session))

        except Exception as e:
            import traceback
            import sys

            # Get full traceback
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
            full_traceback = "".join(tb_lines)

            # Log to console/file
            print(f"[TournamentManager] Tournament {session_id} failed with error:")
            print(full_traceback)

            # Also log to a file for easier debugging
            try:
                log_path = Path("/tmp/negmas-tournament-error.log")
                with open(log_path, "a") as f:
                    f.write(f"\n{'=' * 60}\n")
                    f.write(f"Tournament {session_id} failed at {datetime.now()}\n")
                    f.write(f"{'=' * 60}\n")
                    f.write(full_traceback)
                    f.write("\n")
            except Exception:
                pass  # Don't fail if we can't write the log

            state.status = TournamentStatus.FAILED
            state.error = f"{str(e)}\n\nFull traceback written to /tmp/negmas-tournament-error.log"
            session.status = TournamentStatus.FAILED
            session.error = f"{str(e)}\n\nFull traceback written to /tmp/negmas-tournament-error.log"
            session.end_time = datetime.now()
            state.event_queue.put(("error", str(e)))

    async def run_tournament_stream(
        self,
        session_id: str,
    ) -> AsyncGenerator[
        TournamentProgress
        | TournamentSession
        | TournamentGridInit
        | CellUpdate
        | list[LeaderboardEntry]
        | dict[str, Any],
        None,
    ]:
        """Stream tournament progress updates.

        This starts the tournament in a background thread (if not already running)
        and yields events from the shared state's event queue.

        If the browser disconnects and reconnects, this will continue streaming
        from where the tournament currently is.

        Yields:
            - TournamentGridInit: Initial grid structure
            - CellUpdate: Cell status updates (running/complete)
            - list[LeaderboardEntry]: Leaderboard updates
            - TournamentProgress: Progress updates
            - TournamentSession: Final session state
        """
        session = self.sessions.get(session_id)
        state = self._tournament_states.get(session_id)

        if session is None or session.config is None or state is None:
            return

        # Check if tournament is already running
        thread = self._background_threads.get(session_id)
        if thread is None or not thread.is_alive():
            # Start the tournament in a background thread
            thread = threading.Thread(
                target=self._run_tournament_in_background,
                args=(session_id,),
                daemon=True,
            )
            self._background_threads[session_id] = thread
            thread.start()
        else:
            # Tournament already running - send current state first
            if state.grid_init:
                yield state.grid_init
            for cell in state.completed_cells:
                yield cell
            if state.leaderboard:
                yield state.leaderboard
            if state.progress:
                yield state.progress

        # Stream events from the queue
        while True:
            try:
                # Non-blocking get with timeout to allow checking for cancellation
                try:
                    event_type, event_data = state.event_queue.get(timeout=0.1)
                except queue.Empty:
                    # Check if tournament is still running
                    if state.status in (
                        TournamentStatus.COMPLETED,
                        TournamentStatus.FAILED,
                        TournamentStatus.CANCELLED,
                    ):
                        # Yield final session state
                        yield session
                        return
                    # Check if thread died unexpectedly
                    if thread and not thread.is_alive():
                        if state.status == TournamentStatus.RUNNING:
                            state.status = TournamentStatus.FAILED
                            state.error = "Tournament thread died unexpectedly"
                            session.status = TournamentStatus.FAILED
                            session.error = state.error
                        yield session
                        return
                    await asyncio.sleep(0)
                    continue

                # Handle different event types
                if event_type == "grid_init":
                    yield event_data
                elif event_type == "setup_progress":
                    yield event_data
                elif event_type == "run_start":
                    yield event_data
                elif event_type == "run_complete":
                    yield event_data
                elif event_type == "leaderboard":
                    yield event_data
                elif event_type == "progress":
                    yield event_data
                elif event_type == "warning":
                    # Yield warning as a dict with event_type for router to handle
                    yield {"event_type": "warning", "message": event_data}
                elif event_type == "complete":
                    yield event_data
                    return
                elif event_type == "cancelled":
                    yield session
                    return
                elif event_type == "error":
                    session.error = event_data
                    yield session
                    return

            except Exception:
                # If anything goes wrong, yield current session state
                yield session
                return

    async def run_tournament_batch(
        self,
        session_id: str,
    ) -> TournamentSession:
        """Run a tournament using parallel execution (no streaming).

        This method uses njobs from config for parallel execution but
        provides no progress updates. For progress updates, use run_tournament_stream().

        Returns:
            Completed TournamentSession.
        """
        session = self.sessions.get(session_id)
        if session is None or session.config is None:
            raise ValueError(f"Session not found: {session_id}")

        config = session.config
        session.status = TournamentStatus.RUNNING
        session.start_time = datetime.now()

        try:
            # Load scenarios
            scenarios: list[Scenario] = []  # type: ignore[type-arg]
            for path in config.scenario_paths:
                scenario = await asyncio.to_thread(
                    self.scenario_loader.load_scenario, path
                )
                if scenario is not None:
                    # Apply normalization (returns modified scenario)
                    scenario = _apply_normalization(
                        scenario, config.normalization, config.recalculate_stats
                    )
                    scenarios.append(scenario)

            if not scenarios:
                session.status = TournamentStatus.FAILED
                session.error = "No valid scenarios found"
                return session

            # Get competitor classes
            competitors: list[type[SAONegotiator]] = []
            for type_name in config.competitor_types:
                cls = await asyncio.to_thread(_get_class_for_type, type_name)
                if cls is not None:
                    competitors.append(cls)  # type: ignore[arg-type]

            if len(competitors) < 1:
                session.status = TournamentStatus.FAILED
                session.error = "At least 1 valid competitor required"
                return session

            # Get opponent classes if specified
            opponents: list[type[SAONegotiator]] | None = None
            if config.opponent_types is not None:
                opponents = []
                for type_name in config.opponent_types:
                    cls = await asyncio.to_thread(_get_class_for_type, type_name)
                    if cls is not None:
                        opponents.append(cls)  # type: ignore[arg-type]
                if len(opponents) < 1:
                    session.status = TournamentStatus.FAILED
                    session.error = "At least 1 valid opponent required"
                    return session
            else:
                if len(competitors) < 2:
                    session.status = TournamentStatus.FAILED
                    session.error = "At least 2 competitors required when no opponents"
                    return session

            mechanism_class = self._get_mechanism_class(config.mechanism_type)

            tournament_kwargs: dict[str, Any] = {
                "competitors": competitors,
                "scenarios": scenarios,
                "competitor_params": config.competitor_params,
                "opponent_params": config.opponent_params,
                "rotate_ufuns": config.rotate_ufuns,
                "n_repetitions": config.n_repetitions,
                "njobs": config.njobs,
                "mechanism_type": mechanism_class,
                "n_steps": config.n_steps,
                "time_limit": config.time_limit,
                "self_play": config.self_play,
                "randomize_runs": config.randomize_runs,
                "sort_runs": config.sort_runs,
                "id_reveals_type": config.id_reveals_type,
                "name_reveals_type": config.name_reveals_type,
                "mask_scenario_names": config.mask_scenario_names,
                "only_failures_on_self_play": config.only_failures_on_self_play,
                "final_score": (config.final_score_metric, config.final_score_stat),
                "save_stats": config.save_stats,
                "save_scenario_figs": config.save_scenario_figs,
                "save_every": config.save_every,
                "verbosity": config.verbosity,
                "path": Path(config.save_path) if config.save_path else None,
            }

            if opponents is not None:
                tournament_kwargs["opponents"] = opponents

            # Add opponent modeling metrics if specified
            if config.opponent_modeling_metrics:
                tournament_kwargs["opponent_modeling_metrics"] = (
                    config.opponent_modeling_metrics
                )

            # Add distribute_opponent_modeling_scores option
            if config.distribute_opponent_modeling_scores:
                tournament_kwargs["distribute_opponent_modeling_scores"] = True

            if config.step_time_limit is not None:
                tournament_kwargs["step_time_limit"] = config.step_time_limit
            if config.negotiator_time_limit is not None:
                tournament_kwargs["negotiator_time_limit"] = (
                    config.negotiator_time_limit
                )
            if config.hidden_time_limit is not None:
                tournament_kwargs["hidden_time_limit"] = config.hidden_time_limit
            if config.pend is not None:
                tournament_kwargs["pend"] = config.pend
            if config.pend_per_second is not None:
                tournament_kwargs["pend_per_second"] = config.pend_per_second

            results = await asyncio.to_thread(
                cartesian_tournament,
                **tournament_kwargs,  # type: ignore[arg-type]
            )

            final_scores: list[CompetitorScore] = []
            if results.final_scores is not None:
                for idx, row in results.final_scores.iterrows():
                    # Get strategy name from column or index
                    if "strategy" in results.final_scores.columns:
                        name = str(row["strategy"])
                    else:
                        name = str(idx)
                    # Get score from 'score' column or first numeric column
                    if "score" in results.final_scores.columns:
                        score = float(row["score"])
                    else:
                        score = float(row.iloc[0]) if len(row) > 0 else 0.0
                    final_scores.append(
                        CompetitorScore(
                            name=name,
                            type_name=name,
                            score=score,
                            rank=len(final_scores) + 1,
                        )
                    )

            total_negotiations = (
                len(results.details) if results.details is not None else 0
            )
            total_agreements = 0
            if results.details is not None and "agreement" in results.details.columns:
                total_agreements = int(results.details["agreement"].notna().sum())

            session.results = TournamentResults(
                final_scores=final_scores,
                total_negotiations=total_negotiations,
                total_agreements=total_agreements,
                overall_agreement_rate=(
                    total_agreements / total_negotiations
                    if total_negotiations > 0
                    else 0.0
                ),
                results_path=str(results.path) if results.path else None,
            )

            # Clean up redundant CSV files if parquet equivalents exist
            if config.save_path and config.storage_format == "parquet":
                removed = self._cleanup_redundant_csvs(Path(config.save_path))
                if removed:
                    print(
                        f"[TournamentManager] Cleaned up {len(removed)} redundant CSV files"
                    )

            session.status = TournamentStatus.COMPLETED
            session.end_time = datetime.now()

        except Exception as e:
            session.status = TournamentStatus.FAILED
            session.error = str(e)
            session.end_time = datetime.now()

        return session
