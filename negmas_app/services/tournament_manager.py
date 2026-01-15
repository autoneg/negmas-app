"""Tournament management service for running cartesian tournaments."""

from __future__ import annotations

import asyncio
import json
import queue
import shutil
import threading
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from negmas import Scenario
from negmas.sao import SAOMechanism, SAONegotiator
from negmas.tournaments.neg import cartesian_tournament

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
    TournamentOffer,
)
from .scenario_loader import ScenarioLoader
from .negotiator_factory import _get_class_for_type


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

    # Event queue for SSE streaming
    event_queue: queue.Queue[Any] = field(default_factory=queue.Queue)

    # Statistics per competitor
    competitor_stats: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Loaded scenarios (for reference)
    scenarios: list[Scenario] = field(default_factory=list)  # type: ignore[type-arg]
    scenario_names: list[str] = field(default_factory=list)
    scenario_paths: list[str] = field(default_factory=list)

    # Competitor info
    competitor_names: list[str] = field(default_factory=list)
    opponent_names: list[str] = field(default_factory=list)


class TournamentManager:
    """Manage tournament sessions with real-time progress updates via callbacks."""

    def __init__(self):
        self.sessions: dict[str, TournamentSession] = {}
        self._cancel_flags: dict[str, bool] = {}
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
        session_id = str(uuid.uuid4())[:8]

        # Set default save_path if not provided
        if config.save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            config.save_path = str(self.tournaments_dir / f"{timestamp}_{session_id}")

        session = TournamentSession(
            id=session_id,
            status=TournamentStatus.PENDING,
            config=config,
        )
        self.sessions[session_id] = session
        self._cancel_flags[session_id] = False
        self._tournament_states[session_id] = TournamentState()
        return session

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

    def _save_tournament_config(self, config: TournamentConfig, path: Path) -> None:
        """Save tournament configuration to the tournament directory."""
        path = Path(path)
        path.mkdir(exist_ok=True, parents=True)

        config_dict = {
            "competitor_types": config.competitor_types,
            "scenario_paths": config.scenario_paths,
            "opponent_types": config.opponent_types,
            "competitor_params": config.competitor_params,
            "n_repetitions": config.n_repetitions,
            "rotate_ufuns": config.rotate_ufuns,
            "self_play": config.self_play,
            "mechanism_type": config.mechanism_type,
            "n_steps": config.n_steps,
            "time_limit": config.time_limit,
            "step_time_limit": config.step_time_limit,
            "negotiator_time_limit": config.negotiator_time_limit,
            "hidden_time_limit": config.hidden_time_limit,
            "pend": config.pend,
            "pend_per_second": config.pend_per_second,
            "final_score_metric": config.final_score_metric,
            "final_score_stat": config.final_score_stat,
            "randomize_runs": config.randomize_runs,
            "sort_runs": config.sort_runs,
            "id_reveals_type": config.id_reveals_type,
            "name_reveals_type": config.name_reveals_type,
            "mask_scenario_names": config.mask_scenario_names,
            "only_failures_on_self_play": config.only_failures_on_self_play,
            "save_stats": config.save_stats,
            "save_scenario_figs": config.save_scenario_figs,
            "save_every": config.save_every,
            "capture_offers": config.capture_offers,
            "normalize": config.normalize,
            "njobs": config.njobs,
            "verbosity": config.verbosity,
        }

        config_file = path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2)

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

    def _create_callbacks(
        self, session_id: str, config: TournamentConfig
    ) -> tuple[
        Callable[[Any], None],
        Callable[[Any], None],
        Callable[[dict[str, Any]], None],
        Callable[[str, int, int], None],
    ]:
        """Create callback functions for the tournament.

        These callbacks update the shared TournamentState and push events
        to the event queue for SSE streaming.

        Returns:
            Tuple of (before_start_callback, after_construction_callback,
                     after_end_callback, progress_callback)
        """
        state = self._tournament_states[session_id]

        def before_start_callback(info: Any) -> None:
            """Called before each negotiation starts."""
            if self._cancel_flags.get(session_id, False):
                return

            # Extract info about the upcoming negotiation
            scenario_name = info.s.outcome_space.name or "unknown"
            partner_names = list(info.partner_names) if info.partner_names else []
            rep = info.rep

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

            # Determine competitor/opponent indices
            comp_idx = 0
            opp_idx = 0

            if len(partner_names) >= 2:
                p0, p1 = partner_names[0], partner_names[1]
                # Find indices in our lists
                if p0 in state.competitor_names:
                    comp_idx = state.competitor_names.index(p0)
                if p1 in state.opponent_names:
                    opp_idx = state.opponent_names.index(p1)

            scenario_idx = 0
            if base_scenario_name in state.scenario_names:
                scenario_idx = state.scenario_names.index(base_scenario_name)
            elif scenario_name in state.scenario_names:
                scenario_idx = state.scenario_names.index(scenario_name)

            # Create cell_start update
            cell_start = CellUpdate(
                competitor_idx=comp_idx,
                opponent_idx=opp_idx,
                scenario_idx=scenario_idx,
                repetition=rep,
                rotated=rotated,
                status=CellStatus.RUNNING,
            )

            state.current_cell = cell_start
            state.event_queue.put(("cell_start", cell_start))

        def after_construction_callback(info: Any) -> None:
            """Called after mechanism is constructed but before it runs."""
            # Can be used for additional setup if needed
            pass

        def after_end_callback(record: dict[str, Any]) -> None:
            """Called after each negotiation ends with full results."""
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

            # Get indices
            comp_idx = 0
            opp_idx = 0
            scenario_idx = 0
            rep = 0

            if len(partners) >= 2:
                p0, p1 = partners[0], partners[1]
                if p0 in state.competitor_names:
                    comp_idx = state.competitor_names.index(p0)
                if p1 in state.opponent_names:
                    opp_idx = state.opponent_names.index(p1)

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

            # Create cell_complete update
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
            )

            state.completed_cells.append(cell_complete)
            state.current_cell = None
            state.event_queue.put(("cell_complete", cell_complete))

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

        def progress_callback(message: str, current: int, total: int) -> None:
            """Called during tournament setup to report progress.

            Args:
                message: Description of current setup phase.
                current: Current step (1-3 typically).
                total: Total steps (3 typically).
            """
            if self._cancel_flags.get(session_id, False):
                return

            # Emit a setup_progress event
            state.event_queue.put(
                (
                    "setup_progress",
                    {
                        "message": message,
                        "current": current,
                        "total": total,
                    },
                )
            )

        return (
            before_start_callback,
            after_construction_callback,
            after_end_callback,
            progress_callback,
        )

    def _update_stats_from_record(
        self,
        state: TournamentState,
        record: dict[str, Any],
        config: TournamentConfig,
    ) -> None:
        """Update competitor statistics from a negotiation record."""
        partners = record.get("partners", [])
        utilities = record.get("utilities", [])
        agreement = record.get("agreement")

        if not partners or not utilities:
            return

        for i, name in enumerate(partners):
            if name not in state.competitor_stats:
                continue

            stats = state.competitor_stats[name]
            stats["n_negotiations"] += 1

            if agreement is not None:
                stats["n_agreements"] += 1

            if i < len(utilities) and utilities[i] is not None:
                stats["utilities"].append(float(utilities[i]))

                # Calculate advantage if 2-party
                if len(utilities) == 2:
                    other_idx = 1 - i
                    if utilities[other_idx] is not None:
                        advantage = float(utilities[i]) - float(utilities[other_idx])
                        stats["advantages"].append(advantage)

    def _build_leaderboard(
        self,
        stats: dict[str, dict[str, Any]],
        metric: str,
        stat: str,
    ) -> list[LeaderboardEntry]:
        """Build a live leaderboard from current competitor statistics."""
        import statistics as stats_module

        entries: list[LeaderboardEntry] = []

        for name, s in stats.items():
            if metric == "advantage":
                values = s["advantages"]
            elif metric == "utility":
                values = s["utilities"]
            else:
                values = s["advantages"]

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

            mean_utility = stats_module.mean(s["utilities"]) if s["utilities"] else None

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

        entries.sort(key=lambda x: x.score, reverse=True)
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
            # Emit initial setup progress
            state.event_queue.put(
                (
                    "setup_progress",
                    {
                        "message": "Loading scenarios...",
                        "current": 0,
                        "total": 4,
                    },
                )
            )

            # Load scenarios
            scenarios: list[Scenario] = []  # type: ignore[type-arg]
            scenario_names: list[str] = []
            scenario_paths: list[str] = []

            n_scenario_paths = len(config.scenario_paths)
            for idx, path in enumerate(config.scenario_paths):
                # Emit progress for each scenario
                if idx % 10 == 0 or idx == n_scenario_paths - 1:
                    state.event_queue.put(
                        (
                            "setup_progress",
                            {
                                "message": f"Loading scenario {idx + 1}/{n_scenario_paths}...",
                                "current": 0,
                                "total": 4,
                            },
                        )
                    )
                scenario = self.scenario_loader.load_scenario(path)
                if scenario is not None:
                    if config.normalize:
                        scenario.normalize()
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
            competitor_names: list[str] = []
            for type_name in config.competitor_types:
                cls = _get_class_for_type(type_name)
                if cls is not None:
                    competitors.append(cls)  # type: ignore[arg-type]
                    competitor_names.append(cls.__name__)

            if len(competitors) < 1:
                state.status = TournamentStatus.FAILED
                state.error = "At least 1 valid competitor required"
                session.status = TournamentStatus.FAILED
                session.error = state.error
                state.event_queue.put(("error", state.error))
                return

            state.competitor_names = competitor_names

            # Initialize competitor stats
            for name in competitor_names:
                state.competitor_stats[name] = {
                    "utilities": [],
                    "advantages": [],
                    "n_negotiations": 0,
                    "n_agreements": 0,
                }

            # Get opponent classes if specified
            opponents: list[type[SAONegotiator]] | None = None
            opponent_names: list[str] = []

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
                        opponent_names.append(cls.__name__)
                if len(opponents) < 1:
                    state.status = TournamentStatus.FAILED
                    state.error = "At least 1 valid opponent required"
                    session.status = TournamentStatus.FAILED
                    session.error = state.error
                    state.event_queue.put(("error", state.error))
                    return
                state.opponent_names = opponent_names
                # Add opponent stats too if they're also being scored
                for name in opponent_names:
                    if name not in state.competitor_stats:
                        state.competitor_stats[name] = {
                            "utilities": [],
                            "advantages": [],
                            "n_negotiations": 0,
                            "n_agreements": 0,
                        }
            else:
                if len(competitors) < 2:
                    state.status = TournamentStatus.FAILED
                    state.error = "At least 2 competitors required when no opponents"
                    session.status = TournamentStatus.FAILED
                    session.error = state.error
                    state.event_queue.put(("error", state.error))
                    return
                state.opponent_names = competitor_names

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
            grid_init = TournamentGridInit(
                competitors=competitor_names,
                opponents=state.opponent_names,
                scenarios=scenario_names,
                n_repetitions=config.n_repetitions,
                rotate_ufuns=config.rotate_ufuns,
                total_negotiations=total_negotiations,
            )
            state.grid_init = grid_init
            state.progress = TournamentProgress(
                completed=0, total=total_negotiations, percent=0.0
            )

            # Emit grid_init event
            state.event_queue.put(("grid_init", grid_init))
            state.event_queue.put(("progress", state.progress))

            # Create callbacks
            before_cb, after_const_cb, after_end_cb, progress_cb = (
                self._create_callbacks(session_id, config)
            )

            # Get mechanism class
            mechanism_class = self._get_mechanism_class(config.mechanism_type)

            # Build tournament kwargs
            tournament_kwargs: dict[str, Any] = {
                "competitors": competitors,
                "scenarios": scenarios,
                "competitor_params": None,
                "rotate_ufuns": config.rotate_ufuns,
                "n_repetitions": config.n_repetitions,
                "njobs": -1,  # Serial for callbacks to work properly
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
                "ignore_discount": config.ignore_discount,
                "ignore_reserved": config.ignore_reserved,
                # Callbacks
                "before_start_callback": before_cb,
                "after_construction_callback": after_const_cb,
                "after_end_callback": after_end_cb,
                "progress_callback": progress_cb,
            }

            # Save config before starting
            if config.save_path:
                self._save_tournament_config(config, Path(config.save_path))

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

            # Update status
            state.status = TournamentStatus.RUNNING
            session.status = TournamentStatus.RUNNING
            session.start_time = datetime.now()

            # Run the tournament (blocking in this thread)
            results = cartesian_tournament(**tournament_kwargs)  # type: ignore[arg-type]

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
        | list[LeaderboardEntry],
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
                elif event_type == "cell_start":
                    yield event_data
                elif event_type == "cell_complete":
                    yield event_data
                elif event_type == "leaderboard":
                    yield event_data
                elif event_type == "progress":
                    yield event_data
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
                    if config.normalize:
                        scenario.normalize()
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
                "competitor_params": None,
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

            if config.save_path:
                self._save_tournament_config(config, Path(config.save_path))

            if opponents is not None:
                tournament_kwargs["opponents"] = opponents

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

            session.status = TournamentStatus.COMPLETED
            session.end_time = datetime.now()

        except Exception as e:
            session.status = TournamentStatus.FAILED
            session.error = str(e)
            session.end_time = datetime.now()

        return session
