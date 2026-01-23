"""Tournament API endpoints with SSE streaming."""

import asyncio
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..models.tournament import (
    TournamentConfig,
    TournamentProgress,
    TournamentSession,
    TournamentGridInit,
    CellUpdate,
    LeaderboardEntry,
)
from ..services.tournament_manager import TournamentManager
from ..services.tournament_storage import TournamentStorageService

router = APIRouter(prefix="/api/tournament", tags=["tournament"])

# Shared tournament manager (initialized lazily)
_manager: TournamentManager | None = None


def get_manager() -> TournamentManager:
    """Get or create the tournament manager instance."""
    global _manager
    if _manager is None:
        _manager = TournamentManager()
    return _manager


class TournamentConfigRequest(BaseModel):
    """Request model for tournament configuration.

    Range parameters (n_steps, time_limit, etc.) can be specified as:
    - Single value: 100, 60.0
    - Range [min, max]: [50, 200], [30.0, 120.0] - will sample randomly for each negotiation
    - null/None: No limit
    """

    competitor_types: list[str]
    scenario_paths: list[str]
    opponent_types: list[str] | None = None  # If None, competitors play each other
    competitor_params: list[dict] | None = None
    opponent_params: list[dict] | None = None
    n_repetitions: int = 1
    rotate_ufuns: bool = True
    self_play: bool = True
    mechanism_type: str = "SAOMechanism"
    # Mechanism settings - support single value or [min, max] range
    n_steps: int | list[int] | None = 100
    time_limit: float | list[float] | None = None

    # Time limits for negotiators - support single value or [min, max] range
    step_time_limit: float | list[float] | None = None
    negotiator_time_limit: float | list[float] | None = None
    hidden_time_limit: float | list[float] | None = None

    # Probabilistic ending - support single value or [min, max] range
    pend: float | list[float] | None = None
    pend_per_second: float | list[float] | None = None

    # Scoring
    final_score_metric: str = "advantage"
    final_score_stat: str = "mean"

    # Run ordering
    randomize_runs: bool = False
    sort_runs: bool = True

    # Information hiding
    id_reveals_type: bool = False
    name_reveals_type: bool = True
    mask_scenario_names: bool = False

    # Self-play options
    only_failures_on_self_play: bool = False

    # Save options
    save_stats: bool = True
    save_scenario_figs: bool = False
    save_every: int = 0

    # Scenario options
    # Normalization mode: "none", "scale_min", "scale_max", "normalize"
    normalization: str = "normalize"
    ignore_discount: bool = False  # Ignore discounting in utility functions
    ignore_reserved: bool = False  # Ignore reserved values in utility functions
    pass_opponent_ufun: bool = False  # Pass opponent utility function to negotiators
    raise_exceptions: bool = False  # Raise exceptions on negotiator errors

    # Execution
    njobs: int = -1
    save_path: str | None = None
    verbosity: int = 0

    # Path handling when save_path already exists
    path_exists: str = "continue"  # "continue", "overwrite", or "fail"


def _to_range_int(value: int | list[int] | None) -> int | tuple[int, int] | None:
    """Convert list [min, max] to tuple for int range parameters."""
    if value is None:
        return None
    if isinstance(value, list):
        if len(value) == 2:
            return (value[0], value[1])
        return value[0] if value else None
    return value


def _to_range_float(
    value: float | list[float] | None,
) -> float | tuple[float, float] | None:
    """Convert list [min, max] to tuple for float range parameters."""
    if value is None:
        return None
    if isinstance(value, list):
        if len(value) == 2:
            return (value[0], value[1])
        return value[0] if value else None
    return value


@router.post("/start")
async def start_tournament(request: TournamentConfigRequest):
    """Start a new tournament session.

    Returns session ID to use for streaming progress updates.
    """
    config = TournamentConfig(
        competitor_types=request.competitor_types,
        scenario_paths=request.scenario_paths,
        opponent_types=request.opponent_types,
        competitor_params=request.competitor_params,
        n_repetitions=request.n_repetitions,
        rotate_ufuns=request.rotate_ufuns,
        self_play=request.self_play,
        mechanism_type=request.mechanism_type,
        n_steps=_to_range_int(request.n_steps),
        time_limit=_to_range_float(request.time_limit),
        step_time_limit=_to_range_float(request.step_time_limit),
        negotiator_time_limit=_to_range_float(request.negotiator_time_limit),
        hidden_time_limit=_to_range_float(request.hidden_time_limit),
        pend=_to_range_float(request.pend),
        pend_per_second=_to_range_float(request.pend_per_second),
        final_score_metric=request.final_score_metric,
        final_score_stat=request.final_score_stat,
        randomize_runs=request.randomize_runs,
        sort_runs=request.sort_runs,
        id_reveals_type=request.id_reveals_type,
        name_reveals_type=request.name_reveals_type,
        mask_scenario_names=request.mask_scenario_names,
        only_failures_on_self_play=request.only_failures_on_self_play,
        save_stats=request.save_stats,
        save_scenario_figs=request.save_scenario_figs,
        save_every=request.save_every,
        normalization=request.normalization,
        ignore_discount=request.ignore_discount,
        ignore_reserved=request.ignore_reserved,
        pass_opponent_ufun=request.pass_opponent_ufun,
        raise_exceptions=request.raise_exceptions,
        njobs=request.njobs,
        save_path=request.save_path,
        verbosity=request.verbosity,
        path_exists=request.path_exists,
    )

    session = get_manager().create_session(config)

    return {
        "session_id": session.id,
        "status": session.status.value,
        "stream_url": f"/api/tournament/{session.id}/stream",
    }


@router.get("/{session_id}/stream")
async def stream_tournament(session_id: str):
    """Stream tournament progress via Server-Sent Events.

    Events:
    - grid_init: Initial grid structure (competitors, opponents, scenarios)
    - cell_start: Cell is starting (turn yellow)
    - cell_complete: Cell is complete (color based on result)
    - leaderboard: Updated leaderboard standings
    - progress: Progress update (completed, total, current_scenario, percent)
    - complete: Tournament finished (includes results)
    - error: Error occurred
    """
    session = get_manager().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        try:
            async for event in get_manager().run_tournament_stream(session_id):
                if isinstance(event, TournamentGridInit):
                    yield {
                        "event": "grid_init",
                        "data": json.dumps(
                            {
                                "competitors": event.competitors,
                                "opponents": event.opponents,
                                "scenarios": event.scenarios,
                                "n_repetitions": event.n_repetitions,
                                "rotate_ufuns": event.rotate_ufuns,
                                "total_negotiations": event.total_negotiations,
                            }
                        ),
                    }
                elif isinstance(event, dict) and "message" in event:
                    # Setup progress event from progress_callback
                    yield {
                        "event": "setup_progress",
                        "data": json.dumps(event),
                    }
                elif isinstance(event, CellUpdate):
                    # Build the event data
                    cell_data = {
                        "competitor_idx": event.competitor_idx,
                        "opponent_idx": event.opponent_idx,
                        "scenario_idx": event.scenario_idx,
                        "repetition": event.repetition,
                        "rotated": event.rotated,
                        "status": event.status.value,
                        "end_reason": event.end_reason.value
                        if event.end_reason
                        else None,
                        "utilities": event.utilities,
                        "error": event.error,
                    }
                    # Include detailed negotiation data for completed cells
                    if event.status.value == "complete":
                        cell_data["issue_names"] = event.issue_names
                        cell_data["scenario_path"] = event.scenario_path
                        cell_data["n_steps"] = event.n_steps
                        cell_data["agreement"] = (
                            list(event.agreement) if event.agreement else None
                        )
                        # Include offers if available
                        if event.offers:
                            cell_data["offers"] = [
                                {
                                    "step": o.step,
                                    "proposer": o.proposer,
                                    "proposer_index": o.proposer_index,
                                    "offer": list(o.offer) if o.offer else None,
                                    "offer_dict": o.offer_dict,
                                    "utilities": o.utilities,
                                }
                                for o in event.offers
                            ]
                    yield {
                        "event": "cell_start"
                        if event.status.value == "running"
                        else "cell_complete",
                        "data": json.dumps(cell_data),
                    }
                elif (
                    isinstance(event, list)
                    and len(event) > 0
                    and isinstance(event[0], LeaderboardEntry)
                ):
                    yield {
                        "event": "leaderboard",
                        "data": json.dumps(
                            [
                                {
                                    "name": entry.name,
                                    "score": entry.score,
                                    "rank": entry.rank,
                                    "n_negotiations": entry.n_negotiations,
                                    "n_agreements": entry.n_agreements,
                                    "mean_utility": entry.mean_utility,
                                }
                                for entry in event
                            ]
                        ),
                    }
                elif isinstance(event, TournamentProgress):
                    yield {
                        "event": "progress",
                        "data": json.dumps(
                            {
                                "completed": event.completed,
                                "total": event.total,
                                "current_scenario": event.current_scenario,
                                "current_partners": event.current_partners,
                                "percent": event.percent,
                            }
                        ),
                    }
                elif isinstance(event, TournamentSession):
                    # Final session state
                    results_data = None
                    if event.results is not None:
                        results_data = {
                            "final_scores": [
                                {
                                    "name": s.name,
                                    "type_name": s.type_name,
                                    "score": s.score,
                                    "rank": s.rank,
                                    "mean_utility": s.mean_utility,
                                    "mean_advantage": s.mean_advantage,
                                    "n_negotiations": s.n_negotiations,
                                    "n_agreements": s.n_agreements,
                                    "agreement_rate": s.agreement_rate,
                                }
                                for s in event.results.final_scores
                            ],
                            "negotiations": [
                                {
                                    "index": idx,
                                    "scenario": n.scenario,
                                    "partners": n.partners,
                                    "has_agreement": n.agreement is not None,
                                    "agreement": list(n.agreement)
                                    if n.agreement
                                    else None,
                                    "utilities": n.utilities,
                                    "advantages": n.advantages,
                                    "has_error": n.has_error,
                                    "error_details": n.error_details,
                                    "execution_time": n.execution_time,
                                    "end_reason": n.end_reason.value
                                    if n.end_reason
                                    else None,
                                }
                                for idx, n in enumerate(
                                    event.results.negotiation_results
                                )
                            ],
                            "total_negotiations": event.results.total_negotiations,
                            "total_agreements": event.results.total_agreements,
                            "overall_agreement_rate": event.results.overall_agreement_rate,
                            "execution_time": event.results.execution_time,
                            "results_path": event.results.results_path,
                        }

                    yield {
                        "event": "complete",
                        "data": json.dumps(
                            {
                                "status": event.status.value,
                                "results": results_data,
                                "error": event.error,
                                "duration_seconds": event.duration_seconds(),
                            }
                        ),
                    }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


class CancelRequest(BaseModel):
    """Request model for cancelling a tournament."""

    delete_results: bool = False  # If True, delete the tournament folder


@router.post("/{session_id}/cancel")
async def cancel_tournament(session_id: str, request: CancelRequest | None = None):
    """Cancel a running tournament.

    Args:
        session_id: Session to cancel.
        request: Optional request body with delete_results flag.
            - delete_results=False (default): Keep partial results
            - delete_results=True: Delete tournament folder and all results

    Returns:
        Status dict with cancellation result.
    """
    delete_results = request.delete_results if request else False
    result = get_manager().cancel_session(session_id, delete_results=delete_results)
    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Session not found")
        )
    return result


@router.get("/sessions/list")
async def list_sessions():
    """List all tournament sessions.

    Returns sessions grouped by status.
    """
    sessions = []
    for session in get_manager().list_sessions():
        config_data = None
        if session.config is not None:
            config_data = {
                "competitor_types": session.config.competitor_types,
                "scenario_paths": session.config.scenario_paths,
                "n_repetitions": session.config.n_repetitions,
                "mechanism_type": session.config.mechanism_type,
            }

        progress_data = None
        if session.progress is not None:
            progress_data = {
                "completed": session.progress.completed,
                "total": session.progress.total,
                "percent": session.progress.percent,
            }

        sessions.append(
            {
                "id": session.id,
                "status": session.status.value,
                "config": config_data,
                "progress": progress_data,
                "start_time": session.start_time.isoformat()
                if session.start_time
                else None,
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "error": session.error,
            }
        )

    # Sort by start time (most recent first)
    sessions.sort(key=lambda s: s["start_time"] or "", reverse=True)

    return {"sessions": sessions}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    session = get_manager().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    config_data = None
    if session.config is not None:
        config_data = {
            "competitor_types": session.config.competitor_types,
            "scenario_paths": session.config.scenario_paths,
            "n_repetitions": session.config.n_repetitions,
            "rotate_ufuns": session.config.rotate_ufuns,
            "self_play": session.config.self_play,
            "mechanism_type": session.config.mechanism_type,
            "n_steps": session.config.n_steps,
            "time_limit": session.config.time_limit,
            "final_score_metric": session.config.final_score_metric,
            "final_score_stat": session.config.final_score_stat,
        }

    progress_data = None
    if session.progress is not None:
        progress_data = {
            "completed": session.progress.completed,
            "total": session.progress.total,
            "current_scenario": session.progress.current_scenario,
            "current_partners": session.progress.current_partners,
            "percent": session.progress.percent,
        }

    results_data = None
    if session.results is not None:
        results_data = {
            "final_scores": [
                {
                    "name": s.name,
                    "type_name": s.type_name,
                    "score": s.score,
                    "rank": s.rank,
                    "mean_utility": s.mean_utility,
                    "mean_advantage": s.mean_advantage,
                    "n_negotiations": s.n_negotiations,
                    "n_agreements": s.n_agreements,
                    "agreement_rate": s.agreement_rate,
                }
                for s in session.results.final_scores
            ],
            "total_negotiations": session.results.total_negotiations,
            "total_agreements": session.results.total_agreements,
            "overall_agreement_rate": session.results.overall_agreement_rate,
            "execution_time": session.results.execution_time,
            "results_path": session.results.results_path,
        }

    return {
        "id": session.id,
        "status": session.status.value,
        "config": config_data,
        "progress": progress_data,
        "results": results_data,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "duration_seconds": session.duration_seconds(),
        "error": session.error,
    }


@router.post("/{session_id}/batch")
async def run_batch(session_id: str):
    """Run tournament in batch mode (no streaming, faster).

    Use this endpoint after creating a session with /start to run the tournament
    without streaming progress. Results will be available when the request completes.
    """
    try:
        session = await get_manager().run_tournament_batch(session_id)

        results_data = None
        if session.results is not None:
            results_data = {
                "final_scores": [
                    {
                        "name": s.name,
                        "type_name": s.type_name,
                        "score": s.score,
                        "rank": s.rank,
                        "mean_utility": s.mean_utility,
                        "mean_advantage": s.mean_advantage,
                        "n_negotiations": s.n_negotiations,
                        "n_agreements": s.n_agreements,
                        "agreement_rate": s.agreement_rate,
                    }
                    for s in session.results.final_scores
                ],
                "total_negotiations": session.results.total_negotiations,
                "total_agreements": session.results.total_agreements,
                "overall_agreement_rate": session.results.overall_agreement_rate,
                "execution_time": session.results.execution_time,
                "results_path": session.results.results_path,
            }

        return {
            "id": session.id,
            "status": session.status.value,
            "results": results_data,
            "duration_seconds": session.duration_seconds(),
            "error": session.error,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Saved Tournaments Endpoints
# =============================================================================


@router.post("/saved/{tournament_id}/continue")
async def continue_tournament(tournament_id: str):
    """Continue an incomplete tournament from a saved path.

    This endpoint creates a new session that continues an existing tournament.
    If the tournament is already complete, it will just load and return the results.
    If incomplete, it will resume running the remaining negotiations.

    Args:
        tournament_id: ID of the saved tournament to continue.

    Returns:
        Session info with session_id and stream_url for monitoring progress.
    """
    # Get the tournament path from storage service
    from pathlib import Path

    tournaments_dir = Path.home() / "negmas" / "app" / "tournaments"
    tournament_path = tournaments_dir / tournament_id

    if not tournament_path.exists():
        raise HTTPException(status_code=404, detail="Tournament not found")

    config_file = tournament_path / "config.yaml"
    if not config_file.exists():
        raise HTTPException(
            status_code=400, detail="Invalid tournament - missing config.yaml"
        )

    # Create a session for continuing this tournament
    try:
        session = get_manager().continue_session(str(tournament_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "session_id": session.id,
        "status": session.status.value,
        "stream_url": f"/api/tournament/{session.id}/stream",
        "tournament_path": str(tournament_path),
    }


@router.get("/saved/list")
async def list_saved_tournaments(archived: bool | None = None, tags: str | None = None):
    """List all saved tournaments from disk.

    Args:
        archived: Filter by archived status (true/false/null for all)
        tags: Comma-separated tags to filter by (match any)

    Returns summary info for each saved tournament.
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    tournaments = await asyncio.to_thread(
        TournamentStorageService.list_saved_tournaments,
        archived=archived,
        tags=tag_list,
    )
    return {"tournaments": tournaments, "count": len(tournaments)}


@router.get("/saved/{tournament_id}")
async def get_saved_tournament(tournament_id: str):
    """Load a saved tournament from disk.

    Returns full tournament data including scores and negotiation summaries.
    """
    tournament = await asyncio.to_thread(
        TournamentStorageService.load_tournament, tournament_id
    )
    if tournament is None:
        raise HTTPException(status_code=404, detail="Saved tournament not found")
    return tournament


@router.get("/saved/{tournament_id}/negotiation/{index}")
async def get_saved_tournament_negotiation(tournament_id: str, index: int):
    """Get full details of a specific negotiation from a saved tournament.

    Args:
        tournament_id: Tournament ID.
        index: Index of the negotiation in the tournament results.
    """
    negotiation = await asyncio.to_thread(
        TournamentStorageService.get_tournament_negotiation, tournament_id, index
    )
    if negotiation is None:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return negotiation


@router.delete("/saved/{tournament_id}")
async def delete_saved_tournament(tournament_id: str):
    """Delete a saved tournament from disk."""
    success = await asyncio.to_thread(
        TournamentStorageService.delete_tournament, tournament_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Saved tournament not found")
    return {"status": "deleted"}


class ArchiveRequest(BaseModel):
    """Request model for archiving/unarchiving."""

    archived: bool


@router.post("/saved/{tournament_id}/archive")
async def toggle_archive_tournament(tournament_id: str, request: ArchiveRequest):
    """Archive or unarchive a saved tournament."""
    success = await asyncio.to_thread(
        TournamentStorageService.set_archived, tournament_id, request.archived
    )
    if not success:
        raise HTTPException(status_code=404, detail="Saved tournament not found")
    return {"status": "updated", "archived": request.archived}


class TagsRequest(BaseModel):
    """Request model for updating tags."""

    tags: list[str]


@router.post("/saved/{tournament_id}/tags")
async def update_tournament_tags(tournament_id: str, request: TagsRequest):
    """Update tags for a saved tournament."""
    success = await asyncio.to_thread(
        TournamentStorageService.set_tags, tournament_id, request.tags
    )
    if not success:
        raise HTTPException(status_code=404, detail="Saved tournament not found")
    return {"status": "updated", "tags": request.tags}


@router.get("/saved/{tournament_id}/trace/{mechanism_name}")
async def get_negotiation_trace(
    tournament_id: str, mechanism_name: str, scenario: str | None = None
):
    """Get the full negotiation trace for a specific mechanism run.

    Args:
        tournament_id: Tournament ID.
        mechanism_name: The mechanism_name from the negotiation record.
        scenario: Optional scenario name to calculate per-offer utilities.

    Returns:
        Negotiation trace with full offer history and utilities if scenario provided.
    """
    if scenario:
        # Get trace with per-offer utility calculations
        trace = await asyncio.to_thread(
            TournamentStorageService.get_negotiation_trace_with_utilities,
            tournament_id,
            mechanism_name,
            scenario,
        )
    else:
        trace = await asyncio.to_thread(
            TournamentStorageService.get_negotiation_trace,
            tournament_id,
            mechanism_name,
        )
    if trace is None:
        raise HTTPException(status_code=404, detail="Negotiation trace not found")
    return trace


@router.get("/saved/{tournament_id}/negotiations/files")
async def list_negotiation_files(tournament_id: str):
    """List all negotiation trace files in a tournament.

    Args:
        tournament_id: Tournament ID.

    Returns:
        List of negotiation files with metadata.
    """
    files = await asyncio.to_thread(
        TournamentStorageService.list_negotiation_files, tournament_id
    )
    return {"files": files}


@router.get("/saved/{tournament_id}/scenario/{scenario_name}")
async def get_scenario_info(
    tournament_id: str, scenario_name: str, include_outcome_space: bool = True
):
    """Get scenario information from a saved tournament.

    Args:
        tournament_id: Tournament ID.
        scenario_name: Name of the scenario.
        include_outcome_space: If True, also compute outcome_space_data for visualization.

    Returns:
        Scenario info including outcome_space, issue_names, stats, and outcome_space_data.
    """
    scenario = await asyncio.to_thread(
        TournamentStorageService.get_scenario_info, tournament_id, scenario_name
    )
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Include outcome_space_data for visualization (Pareto frontier, special points, etc.)
    if include_outcome_space:
        outcome_space_data = await asyncio.to_thread(
            TournamentStorageService.get_outcome_space_data,
            tournament_id,
            scenario_name,
        )
        scenario["outcome_space_data"] = outcome_space_data

    return scenario


@router.get("/saved/{tournament_id}/scenario/{scenario_name}/outcome_space")
async def get_scenario_outcome_space(tournament_id: str, scenario_name: str):
    """Get outcome space data for a scenario from a saved tournament.

    This computes/loads the outcome_space_data needed for 2D utility visualization,
    including all sampled outcomes, Pareto frontier, and special solution points
    (Nash, Kalai, Kalai-Smorodinsky, Max Welfare).

    Args:
        tournament_id: Tournament ID.
        scenario_name: Name of the scenario.

    Returns:
        OutcomeSpaceData dict with outcome_utilities, pareto_utilities, special points.
    """
    outcome_space_data = await asyncio.to_thread(
        TournamentStorageService.get_outcome_space_data, tournament_id, scenario_name
    )
    if outcome_space_data is None:
        raise HTTPException(
            status_code=404,
            detail="Scenario not found or failed to compute outcome space",
        )
    return outcome_space_data


@router.get("/saved/{tournament_id}/files")
async def get_tournament_files(tournament_id: str):
    """Get list of available files in the tournament directory.

    Args:
        tournament_id: Tournament ID.

    Returns:
        Dict with file categories and their availability.
    """
    files = await asyncio.to_thread(
        TournamentStorageService.get_tournament_files, tournament_id
    )
    if not files:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return files


@router.get("/saved/{tournament_id}/config")
async def get_tournament_config(tournament_id: str):
    """Get tournament configuration from config.json.

    Args:
        tournament_id: Tournament ID.

    Returns:
        Config dict from the tournament.
    """
    config = await asyncio.to_thread(
        TournamentStorageService.get_tournament_config, tournament_id
    )
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.get("/saved/{tournament_id}/scores")
async def get_tournament_scores(tournament_id: str):
    """Get final scores from scores.csv.

    Args:
        tournament_id: Tournament ID.

    Returns:
        List of score dicts with strategy and score.
    """
    scores = await asyncio.to_thread(
        TournamentStorageService.get_scores_csv, tournament_id
    )
    if scores is None:
        raise HTTPException(status_code=404, detail="Scores not found")
    return {"scores": scores}


@router.get("/saved/{tournament_id}/type_scores")
async def get_tournament_type_scores(tournament_id: str):
    """Get detailed type scores from type_scores.csv.

    Args:
        tournament_id: Tournament ID.

    Returns:
        Dict with metrics, stat names, and per-strategy values.
    """
    type_scores = await asyncio.to_thread(
        TournamentStorageService.get_type_scores_csv, tournament_id
    )
    if type_scores is None:
        raise HTTPException(status_code=404, detail="Type scores not found")
    return type_scores


@router.get("/saved/{tournament_id}/all_scores")
async def get_tournament_all_scores(tournament_id: str):
    """Get per-negotiation scores from all_scores.csv.

    Args:
        tournament_id: Tournament ID.

    Returns:
        List of per-negotiation score dicts.
    """
    all_scores = await asyncio.to_thread(
        TournamentStorageService.get_all_scores_csv, tournament_id
    )
    if all_scores is None:
        raise HTTPException(status_code=404, detail="All scores not found")
    return {"scores": all_scores}


@router.get("/saved/{tournament_id}/details")
async def get_tournament_details(tournament_id: str):
    """Get detailed negotiation results from details.csv.

    Args:
        tournament_id: Tournament ID.

    Returns:
        List of detailed negotiation result dicts.
    """
    details = await asyncio.to_thread(
        TournamentStorageService.get_details_csv, tournament_id
    )
    if details is None:
        raise HTTPException(status_code=404, detail="Details not found")
    return {"details": details}


@router.get("/saved/{tournament_id}/score_analysis")
async def get_score_analysis(
    tournament_id: str,
    metric: str = "utility",
    statistic: str = "mean",
    scenario: str | None = None,
    partner: str | None = None,
):
    """Get aggregated score analysis by strategy.

    Computes a leaderboard of strategies based on the selected metric and statistic.

    Args:
        tournament_id: Tournament ID.
        metric: Score metric to analyze (utility, advantage, welfare, nash_optimality,
               kalai_optimality, ks_optimality, max_welfare_optimality, pareto_optimality,
               partner_welfare, time).
        statistic: Aggregation statistic (mean, median, min, max, std, truncated_mean,
                  count, sum).
        scenario: Optional scenario name to filter by.
        partner: Optional partner strategy to filter by.

    Returns:
        Leaderboard with strategy rankings and statistics.
    """
    analysis = await asyncio.to_thread(
        TournamentStorageService.get_score_analysis,
        tournament_id,
        metric,
        statistic,
        scenario,
        partner,
    )
    if analysis is None:
        raise HTTPException(status_code=404, detail="Score data not found")
    if "error" in analysis:
        raise HTTPException(status_code=400, detail=analysis["error"])
    return analysis


@router.get("/saved/{tournament_id}/negotiation/{index}/full")
async def get_full_negotiation(tournament_id: str, index: int):
    """Load complete negotiation data with all panel support.

    This endpoint loads a negotiation from a tournament with full data needed
    for displaying all UI panels (trace, utilities, outcome space, etc.).

    Args:
        tournament_id: Tournament ID.
        index: Index of the negotiation in the tournament results.

    Returns:
        Complete negotiation data including history, outcome_space_data,
        final_utilities, negotiators, and all metadata.
    """
    negotiation = await asyncio.to_thread(
        TournamentStorageService.load_full_negotiation, tournament_id, index
    )
    if negotiation is None:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return negotiation


class LoadNegotiationRequest(BaseModel):
    """Request model for loading negotiation from file path."""

    path: str


@router.post("/load_negotiation_from_file")
async def load_negotiation_from_file(request: LoadNegotiationRequest):
    """Load a negotiation from a file path (CSV trace file or folder).

    This allows loading negotiations from anywhere on disk, not just from
    saved tournaments. Useful for examining negotiations saved by
    cartesian_tournament or other sources.

    Args:
        request: Request with path to CSV file or folder.

    Returns:
        Negotiation data dict, or error if loading fails.
    """
    negotiation = await asyncio.to_thread(
        TournamentStorageService.load_negotiation_from_folder, request.path
    )
    if negotiation is None:
        raise HTTPException(
            status_code=404, detail="Could not load negotiation from path"
        )
    return negotiation


# =============================================================================
# Combine Tournaments Endpoints
# =============================================================================


class CombineTournamentsRequest(BaseModel):
    """Request model for combining tournaments."""

    tournament_ids: list[str] | None = None  # Combine by saved tournament IDs
    input_paths: list[str] | None = None  # Combine by filesystem paths
    output_name: str | None = None  # Name for combined tournament
    output_path: str | None = None  # Custom output path (optional)
    recursive: bool = True  # Recursively search paths
    metadata: dict | None = None  # Additional metadata


@router.post("/combine")
async def combine_tournaments(request: CombineTournamentsRequest):
    """Combine multiple tournaments into a single result.

    Supports two modes:
    1. Combine by tournament IDs: Select tournaments from saved tournaments list
    2. Combine by paths: Specify filesystem paths to search for tournaments

    Args:
        request: CombineTournamentsRequest with tournament_ids or input_paths

    Returns:
        CombineResult with success status, output location, and statistics.
    """
    if not request.tournament_ids and not request.input_paths:
        raise HTTPException(
            status_code=400,
            detail="Must provide either tournament_ids or input_paths",
        )

    result = await asyncio.to_thread(
        TournamentStorageService.combine_tournaments,
        tournament_ids=request.tournament_ids,
        input_paths=request.input_paths,
        output_name=request.output_name,
        output_path=request.output_path,
        recursive=request.recursive,
        metadata=request.metadata,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Combine failed")

    return {
        "success": True,
        "output_path": result.output_path,
        "output_id": result.output_id,
        "n_tournaments": result.n_tournaments,
        "n_negotiations": result.n_negotiations,
        "n_scenarios": result.n_scenarios,
        "n_competitors": result.n_competitors,
        "loaded_paths": result.loaded_paths,
    }


class FindTournamentsRequest(BaseModel):
    """Request model for finding tournaments in paths."""

    paths: list[str]
    recursive: bool = True


@router.post("/find_in_paths")
async def find_tournaments_in_paths(request: FindTournamentsRequest):
    """Find all tournament directories in the given paths.

    Use this to preview which tournaments will be combined before calling /combine.

    Args:
        request: FindTournamentsRequest with paths to search

    Returns:
        List of tournament summaries found in the paths.
    """
    tournaments = await asyncio.to_thread(
        TournamentStorageService.find_tournaments_in_paths,
        request.paths,
        request.recursive,
    )
    return {"tournaments": tournaments, "count": len(tournaments)}
