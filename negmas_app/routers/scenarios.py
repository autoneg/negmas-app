"""Scenario API endpoints."""

import asyncio
import json
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..services import ScenarioLoader, compute_outcome_utilities

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

# Shared scenario loader
_loader = ScenarioLoader()


@router.get("")
async def list_scenarios(source: str | None = None):
    """List all available scenarios.

    Args:
        source: Optional filter by source (e.g., "anac2019").

    Returns:
        List of scenario info objects.
    """
    scenarios = await asyncio.to_thread(_loader.list_scenarios, source=source)
    return {"scenarios": [_scenario_to_dict(s) for s in scenarios]}


@router.get("/sources")
async def list_sources():
    """List available scenario sources."""
    sources = await asyncio.to_thread(_loader.list_sources)
    return {"sources": sources}


@router.get("/{path:path}/stats")
async def get_scenario_stats(path: str):
    """Get scenario statistics.

    Args:
        path: Full path to scenario directory.

    Returns:
        Scenario statistics if available.
    """
    stats = await asyncio.to_thread(_loader.get_scenario_stats, path)
    return asdict(stats)


@router.post("/{path:path}/stats/calculate")
async def calculate_scenario_stats(path: str, force: bool = False):
    """Calculate and save scenario statistics.

    Args:
        path: Full path to scenario directory.
        force: If True, recalculate even if stats exist.

    Returns:
        Computed scenario statistics.
    """
    stats = await asyncio.to_thread(_loader.calculate_and_save_stats, path, force)
    return asdict(stats)


@router.get("/{path:path}/plot-data")
async def get_scenario_plot_data(path: str, max_samples: int = 10000):
    """Get outcome utilities for plotting.

    Args:
        path: Full path to scenario directory.
        max_samples: Maximum number of outcomes to sample.

    Returns:
        Outcome utilities and negotiator names for plotting.
    """

    def _compute():
        scenario = _loader.load_scenario(path, load_stats=True)
        if scenario is None:
            return None

        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=max_samples * 2)
        )
        utilities, sampled, sample_size = compute_outcome_utilities(
            scenario.ufuns, outcomes, max_samples
        )

        # Get negotiator names
        negotiator_names = []
        for i, ufun in enumerate(scenario.ufuns):
            name = getattr(ufun, "name", None) or f"Negotiator {i + 1}"
            negotiator_names.append(name)

        return {
            "outcome_utilities": utilities,
            "negotiator_names": negotiator_names,
            "n_outcomes": scenario.outcome_space.cardinality,
            "sampled": sampled,
            "sample_size": sample_size,
        }

    result = await asyncio.to_thread(_compute)
    if result is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return result


@router.get("/{path:path}")
async def get_scenario(path: str):
    """Get details for a specific scenario.

    Args:
        path: Full path to scenario directory.

    Returns:
        Scenario info with full details.
    """
    info = await asyncio.to_thread(_loader.get_scenario_info, path)
    if info is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _scenario_to_dict(info)


def _scenario_to_dict(info) -> dict:
    """Convert ScenarioInfo to dict for JSON response."""
    return {
        "path": info.path,
        "name": info.name,
        "n_negotiators": info.n_negotiators,
        "n_issues": info.n_issues,
        "n_outcomes": info.n_outcomes,
        "rational_fraction": info.rational_fraction,
        "source": info.source,
        "has_stats": info.has_stats,
        "has_info": info.has_info,
        "issues": [
            {
                "name": i.name,
                "type": i.type,
                "values": i.values,
            }
            for i in info.issues
        ],
    }


@router.post("/bulk-calculate-stats")
async def bulk_calculate_stats(data: dict[str, Any]):
    """Calculate stats for multiple scenarios with SSE progress updates.

    Args:
        data: Dict with 'paths' (list of scenario paths) and optional 'force' (bool).

    Returns:
        SSE stream with progress updates.
    """
    paths: list[str] = data.get("paths", [])
    force: bool = data.get("force", False)

    if not paths:
        return {"error": "No paths provided"}

    async def generate():
        total = len(paths)
        completed = 0
        errors: list[dict[str, str]] = []

        for path in paths:
            try:
                # Calculate stats in thread pool
                stats = await asyncio.to_thread(
                    _loader.calculate_and_save_stats, path, force
                )
                completed += 1

                # Send progress update
                progress_data = {
                    "type": "progress",
                    "completed": completed,
                    "total": total,
                    "current_path": path,
                    "has_stats": stats.has_stats,
                    "rational_fraction": stats.rational_fraction,
                }
                yield {"event": "progress", "data": json.dumps(progress_data)}

            except Exception as e:
                completed += 1
                errors.append({"path": path, "error": str(e)})

                # Send error progress
                progress_data = {
                    "type": "progress",
                    "completed": completed,
                    "total": total,
                    "current_path": path,
                    "error": str(e),
                }
                yield {"event": "progress", "data": json.dumps(progress_data)}

        # Send completion event
        completion_data = {
            "type": "complete",
            "completed": completed,
            "total": total,
            "errors": errors,
        }
        yield {"event": "complete", "data": json.dumps(completion_data)}

    return EventSourceResponse(generate())
