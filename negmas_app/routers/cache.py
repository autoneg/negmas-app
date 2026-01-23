"""API router for cache management."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Query

from ..services.scenario_cache_service import ScenarioCacheService

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.post("/scenarios/build")
async def build_scenario_caches(
    info: Annotated[bool, Query(description="Build info cache")] = False,
    stats: Annotated[bool, Query(description="Build stats cache")] = False,
    plots: Annotated[bool, Query(description="Build plot caches")] = False,
    all: Annotated[bool, Query(description="Build all caches")] = False,
):
    """Build cache files for all scenarios.

    Query parameters:
        - info: Build _info.yaml files
        - stats: Build _stats.yaml files
        - plots: Build plot files (_plot.webp or _plots/)
        - all: Build all cache types

    Returns build statistics.
    """
    # If all is specified, enable all cache types
    if all:
        info = stats = plots = True

    if not (info or stats or plots):
        return {
            "success": False,
            "error": "Must specify at least one cache type (info, stats, plots, or all)",
        }

    cache_service = ScenarioCacheService()

    # Run in thread to avoid blocking
    results = await asyncio.to_thread(
        cache_service.build_caches,
        build_info=info,
        build_stats=stats,
        build_plots=plots,
    )

    return {
        "success": True,
        "results": results,
    }


@router.post("/scenarios/clear")
async def clear_scenario_caches(
    info: Annotated[bool, Query(description="Clear info cache")] = False,
    stats: Annotated[bool, Query(description="Clear stats cache")] = False,
    plots: Annotated[bool, Query(description="Clear plot caches")] = False,
    all: Annotated[bool, Query(description="Clear all caches")] = False,
):
    """Clear cache files for all scenarios.

    Query parameters:
        - info: Clear _info.yaml files
        - stats: Clear _stats.yaml files
        - plots: Clear plot files (_plot.webp or _plots/)
        - all: Clear all cache types

    Returns clear statistics.
    """
    # If all is specified, enable all cache types
    if all:
        info = stats = plots = True

    if not (info or stats or plots):
        return {
            "success": False,
            "error": "Must specify at least one cache type (info, stats, plots, or all)",
        }

    cache_service = ScenarioCacheService()

    # Run in thread to avoid blocking
    results = await asyncio.to_thread(
        cache_service.clear_caches,
        clear_info=info,
        clear_stats=stats,
        clear_plots=plots,
    )

    return {
        "success": True,
        "results": results,
    }


@router.get("/scenarios/status")
async def get_scenario_cache_status():
    """Get cache status for all scenarios.

    Returns counts of scenarios with/without each cache type.
    """
    cache_service = ScenarioCacheService()

    # Run in thread to avoid blocking
    def count_caches():
        scenario_dirs = cache_service._find_all_scenario_dirs()

        stats = {
            "total": len(scenario_dirs),
            "with_info": 0,
            "with_stats": 0,
            "with_plots": 0,
        }

        for scenario_dir in scenario_dirs:
            # Check for info files
            if (scenario_dir / "_info.yaml").exists() or (
                scenario_dir / "_info.yml"
            ).exists():
                stats["with_info"] += 1

            # Check for stats files
            if (scenario_dir / "_stats.yaml").exists():
                stats["with_stats"] += 1

            # Check for plot files (bilateral or multilateral)
            if (scenario_dir / "_plot.webp").exists() or (
                scenario_dir / "_plots"
            ).exists():
                stats["with_plots"] += 1

        return stats

    stats = await asyncio.to_thread(count_caches)

    return {
        "success": True,
        "status": stats,
    }
