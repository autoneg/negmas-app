"""Scenario API endpoints."""

import asyncio
from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from ..services import ScenarioLoader

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
