"""Scenario API endpoints."""

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..services import ScenarioLoader, compute_outcome_utilities
from ..services.plot_service import (
    generate_and_save_plot,
    get_plot_path,
    has_cached_plot,
)
from ..models.scenario import (
    IssueDefinition,
    ValueFunctionDefinition,
    UtilityFunctionDefinition,
    ScenarioDefinition,
)

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


@router.get("/{path:path}/quick-info")
async def get_quick_info(path: str):
    """Calculate basic info (n_outcomes, opposition) quickly on-demand.

    This is faster than full stats calculation and useful for displaying
    basic info when selecting a scenario.

    Args:
        path: Full path to scenario directory.

    Returns:
        Dict with n_outcomes, opposition, rational_fraction
    """
    from negmas import Scenario
    from negmas.preferences.ops import opposition_level, is_rational

    try:
        # Load scenario
        scenario_path = Path(path)
        scenario = await asyncio.to_thread(Scenario.load, scenario_path)

        # Calculate n_outcomes (sample up to 50k)
        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=50000)
        )
        n_outcomes = len(outcomes)

        # Calculate opposition
        opposition = 0.0
        if len(scenario.ufuns) >= 2 and n_outcomes > 0:
            opposition = float(
                await asyncio.to_thread(
                    opposition_level, scenario.ufuns, outcomes=outcomes, max_tests=50000
                )
            )

        # Calculate rational fraction
        rational_fraction = 0.0
        if n_outcomes > 0:
            n_rational = sum(1 for o in outcomes if is_rational(scenario.ufuns, o))
            rational_fraction = n_rational / n_outcomes

        return {
            "n_outcomes": n_outcomes,
            "opposition": opposition,
            "rational_fraction": rational_fraction,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate info: {str(e)}"
        )


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
async def get_scenario_plot_data(
    path: str, max_samples: int = 10000, force_regenerate: bool = False
):
    """Get outcome utilities for plotting and generate/cache plot image.

    Args:
        path: Full path to scenario directory.
        max_samples: Maximum number of outcomes to sample.
        force_regenerate: If True, regenerate plot even if cached version exists.

    Returns:
        Outcome utilities and negotiator names for plotting, plus plot metadata.
    """

    def _compute():
        scenario = _loader.load_scenario(path, load_stats=True, load_info=True)
        if scenario is None:
            return None

        # Check if we have a cached plot and should use it
        plot_path = get_plot_path(path)
        has_cached = has_cached_plot(path)

        # Generate plot if needed (doesn't exist or force regenerate)
        if not has_cached or force_regenerate:
            plot_metadata = generate_and_save_plot(
                scenario, path, max_samples=max_samples
            )
        else:
            # Just get metadata without regenerating
            negotiator_names = []
            for i, ufun in enumerate(scenario.ufuns):
                name = getattr(ufun, "name", None) or f"Negotiator {i + 1}"
                negotiator_names.append(name)

            plot_metadata = {
                "plot_path": str(plot_path),
                "exists": True,
                "negotiator_names": negotiator_names,
                "cached": True,
            }

        # Compute utilities for interactive Plotly plot
        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=max_samples * 2)
        )
        utilities, sampled, sample_size = compute_outcome_utilities(
            scenario.ufuns, outcomes, max_samples
        )

        return {
            "outcome_utilities": utilities,
            "negotiator_names": plot_metadata["negotiator_names"],
            "n_outcomes": scenario.outcome_space.cardinality,
            "sampled": sampled,
            "sample_size": sample_size,
            "plot_cached": has_cached and not force_regenerate,
            "plot_path": str(plot_path),
        }

    result = await asyncio.to_thread(_compute)
    if result is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return result


@router.get("/{path:path}/plot-image")
async def get_scenario_plot_image(path: str):
    """Serve the cached plot image for a scenario.

    Args:
        path: Full path to scenario directory.

    Returns:
        WebP image file.
    """
    plot_path = get_plot_path(path)

    if not plot_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Plot image not found. Call /plot-data first to generate it.",
        )

    return FileResponse(
        plot_path, media_type="image/webp", filename=f"{Path(path).name}_plot.webp"
    )


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
        "opposition": info.opposition,
        "source": info.source,
        "tags": info.tags,
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


# --- Pydantic models for scenario creation API ---


class ValueFunctionInput(BaseModel):
    """Input model for value function definition."""

    issue_index: int
    type: str = "table"  # "table", "linear", "identity"
    mapping: dict[str, float] | None = None
    slope: float | None = None
    intercept: float | None = None


class UtilityFunctionInput(BaseModel):
    """Input model for utility function definition."""

    name: str
    type: str = "linear_additive"
    reserved_value: float = 0.0
    weights: list[float] | None = None
    values: list[ValueFunctionInput] | None = None
    bias: float | None = None


class IssueInput(BaseModel):
    """Input model for issue definition."""

    name: str
    type: str  # "categorical", "integer", "continuous"
    values: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None


class ScenarioCreateInput(BaseModel):
    """Input model for creating a new scenario."""

    name: str
    issues: list[IssueInput]
    ufuns: list[UtilityFunctionInput]
    description: str = ""
    tags: list[str] = []
    save_path: str | None = None  # Optional custom save path


@router.post("/create")
async def create_scenario(data: ScenarioCreateInput):
    """Create a new scenario from definition.

    Args:
        data: Scenario definition with issues and utility functions.

    Returns:
        Created scenario info.
    """

    def _create():
        # Convert Pydantic models to dataclasses
        issues = [
            IssueDefinition(
                name=i.name,
                type=i.type,
                values=i.values,
                min_value=i.min_value,
                max_value=i.max_value,
            )
            for i in data.issues
        ]

        ufuns = []
        for u in data.ufuns:
            values = None
            if u.values:
                values = [
                    ValueFunctionDefinition(
                        issue_index=v.issue_index,
                        type=v.type,
                        mapping=v.mapping,
                        slope=v.slope,
                        intercept=v.intercept,
                    )
                    for v in u.values
                ]
            ufuns.append(
                UtilityFunctionDefinition(
                    name=u.name,
                    type=u.type,
                    reserved_value=u.reserved_value,
                    weights=u.weights,
                    values=values,
                    bias=u.bias,
                )
            )

        definition = ScenarioDefinition(
            name=data.name,
            issues=issues,
            ufuns=ufuns,
            description=data.description,
            tags=data.tags,
        )

        save_path = Path(data.save_path) if data.save_path else None
        scenario, created_path, error = _loader.create_scenario(definition, save_path)

        if error:
            return {"success": False, "error": error}

        # Get info for the created scenario
        if scenario is not None and created_path is not None:
            info = _loader.get_scenario_info(str(created_path))
            if info:
                return {
                    "success": True,
                    "scenario": _scenario_to_dict(info),
                    "path": str(created_path),
                }

        return {"success": True, "path": str(created_path) if created_path else None}

    result = await asyncio.to_thread(_create)
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Unknown error")
        )
    return result
