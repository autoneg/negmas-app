"""API router for cache management."""

import asyncio
import json
from pathlib import Path
from queue import Queue
from typing import Annotated

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from ..services.scenario_cache_service import ScenarioCacheService

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.post("/scenarios/build")
async def build_scenario_caches(
    info: Annotated[bool, Query(description="Build info cache")] = False,
    stats: Annotated[bool, Query(description="Build stats cache")] = False,
    plots: Annotated[bool, Query(description="Build plot caches")] = False,
    all: Annotated[bool, Query(description="Build all caches")] = False,
    max_pareto_outcomes: Annotated[
        int | None,
        Query(description="Max Pareto outcomes to save. None means no limit."),
    ] = None,
    max_pareto_utils: Annotated[
        int | None,
        Query(description="Max Pareto utils to save. None means no limit."),
    ] = None,
    refresh: Annotated[
        bool, Query(description="Force rebuild existing cache files")
    ] = False,
):
    """Build cache files for all scenarios.

    Query parameters:
        - info: Build _info.yaml files
        - stats: Build _stats.yaml files
        - plots: Build plot files (_plot.webp or _plots/)
        - all: Build all cache types
        - max_pareto_outcomes: Max Pareto outcomes to save. If Pareto frontier exceeds this, it won't be saved.
        - max_pareto_utils: Max Pareto utilities to save. If Pareto frontier exceeds this, they won't be saved.
        - refresh: Force rebuild existing files (default: skip existing)

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
        max_pareto_outcomes=max_pareto_outcomes,
        max_pareto_utils=max_pareto_utils,
        refresh=refresh,
    )

    return {
        "success": True,
        "results": results,
    }


@router.get("/scenarios/build-stream")
async def build_scenario_caches_stream(
    info: Annotated[bool, Query(description="Build info cache")] = False,
    stats: Annotated[bool, Query(description="Build stats cache")] = False,
    plots: Annotated[bool, Query(description="Build plot caches")] = False,
    all: Annotated[bool, Query(description="Build all caches")] = False,
    max_pareto_outcomes: Annotated[
        int | None,
        Query(description="Max Pareto outcomes to save. None means no limit."),
    ] = None,
    max_pareto_utils: Annotated[
        int | None,
        Query(description="Max Pareto utils to save. None means no limit."),
    ] = None,
    refresh: Annotated[
        bool, Query(description="Force rebuild existing cache files")
    ] = False,
    base_path: Annotated[
        str | None,
        Query(description="Base path for scenarios (default: ~/negmas/app/scenarios)"),
    ] = None,
    ensure_finite_reserved_values: Annotated[
        bool,
        Query(description="Fix -inf/inf/nan reserved values in utility functions"),
    ] = False,
):
    """Build cache files for all scenarios with SSE progress streaming.

    Query parameters:
        - info: Build _info.yaml files
        - stats: Build _stats.yaml files
        - plots: Build plot files (_plot.webp or _plots/)
        - all: Build all cache types
        - max_pareto_outcomes: Max Pareto outcomes to save. If Pareto frontier exceeds this, it won't be saved.
        - max_pareto_utils: Max Pareto utilities to save. If Pareto frontier exceeds this, they won't be saved.
        - refresh: Force rebuild existing files (default: skip existing)
        - base_path: Custom base path for scenarios
        - ensure_finite_reserved_values: Fix -inf/inf/nan reserved values in utility functions

    Streams progress events and final results via SSE.
    """
    # If all is specified, enable all cache types
    if all:
        info = stats = plots = True

    if not (info or stats or plots):

        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "error": "Must specify at least one cache type (info, stats, plots, or all)",
                    }
                ),
            }

        return EventSourceResponse(error_generator())

    async def event_generator():
        try:
            # Convert base_path to Path if provided
            scenarios_root = Path(base_path) if base_path else None

            # Create cache service with custom root
            cache_service = ScenarioCacheService(scenarios_root=scenarios_root)

            # Get total count first
            scenario_dirs = cache_service._find_all_scenario_dirs()
            total = len(scenario_dirs)

            if total == 0:
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {
                            "type": "complete",
                            "results": {
                                "total": 0,
                                "successful": 0,
                                "failed": 0,
                                "info_created": 0,
                                "stats_created": 0,
                                "stats_skipped": 0,
                                "plots_created": 0,
                                "errors": [],
                                "skipped": [],
                            },
                        }
                    ),
                }
                return

            # Create queue for progress events
            progress_queue: Queue = Queue()

            # Progress callback that puts events in queue
            def on_progress(current: int, total: int, scenario_name: str):
                progress_queue.put(
                    {
                        "type": "progress",
                        "current": current,
                        "total": total,
                        "current_scenario": scenario_name,
                    }
                )

            # Run build in background thread
            build_task = asyncio.create_task(
                asyncio.to_thread(
                    cache_service.build_caches_with_callback,
                    build_info=info,
                    build_stats=stats,
                    build_plots=plots,
                    max_pareto_outcomes=max_pareto_outcomes,
                    max_pareto_utils=max_pareto_utils,
                    refresh=refresh,
                    ensure_finite_reserved_values=ensure_finite_reserved_values,
                    progress_callback=on_progress,
                )
            )

            # Stream progress events as they arrive
            while not build_task.done():
                # Check for progress events (non-blocking)
                while not progress_queue.empty():
                    event = progress_queue.get()
                    yield {"event": "message", "data": json.dumps(event)}
                # Small delay to avoid busy-waiting
                await asyncio.sleep(0.1)

            # Drain any remaining events
            while not progress_queue.empty():
                event = progress_queue.get()
                yield {"event": "message", "data": json.dumps(event)}

            # Get final results
            results = await build_task

            # Send final completion event
            yield {
                "event": "message",
                "data": json.dumps(
                    {
                        "type": "complete",
                        "results": {
                            "total": results["total"],
                            "successful": results["successful"],
                            "failed": results["failed"],
                            "info_created": results["info_created"],
                            "stats_created": results["stats_created"],
                            "stats_skipped": results["stats_skipped"],
                            "plots_created": results["plots_created"],
                            "reserved_values_fixed": results.get(
                                "reserved_values_fixed", 0
                            ),
                            "errors": results["errors"],
                            "skipped": results["skipped"],
                        },
                    }
                ),
            }

        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "error": str(e)}),
            }

    return EventSourceResponse(event_generator())


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
