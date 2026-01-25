"""Scenario API endpoints."""

import asyncio
import base64
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
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

# Shared scenario loader (initialized lazily)
_loader: ScenarioLoader | None = None

# Cache for loaded scenarios within a request (path -> Scenario)
# This avoids reloading the same scenario multiple times
_scenario_cache: dict[str, Any] = {}


def get_loader() -> ScenarioLoader:
    """Get or create the scenario loader instance."""
    global _loader
    if _loader is None:
        _loader = ScenarioLoader()
    return _loader


def encode_scenario_path(path: str | Path) -> str:
    """Encode a scenario path for use in URLs."""
    return base64.urlsafe_b64encode(str(path).encode()).decode()


def decode_scenario_path(encoded: str) -> str:
    """Decode a scenario path from URL."""
    return base64.urlsafe_b64decode(encoded.encode()).decode()


async def get_cached_scenario(
    path: str, load_stats: bool = True, load_info: bool = True
):
    """Get a scenario from cache or load it.

    This ensures we only load a scenario once per request.
    """
    from negmas import Scenario

    cache_key = f"{path}:{load_stats}:{load_info}"
    if cache_key not in _scenario_cache:
        scenario = await asyncio.to_thread(
            Scenario.load, Path(path), load_stats=load_stats, load_info=load_info
        )
        _scenario_cache[cache_key] = scenario
    return _scenario_cache[cache_key]


@router.get("")
async def list_scenarios(source: str | None = None):
    """List all available scenarios.

    Args:
        source: Optional filter by source (e.g., "anac2019").

    Returns:
        List of scenario info objects.
    """
    scenarios = await asyncio.to_thread(get_loader().list_scenarios, source=source)
    return {"scenarios": [_scenario_to_dict(s) for s in scenarios]}


@router.get("/sources")
async def list_sources():
    """List available scenario sources."""
    sources = await asyncio.to_thread(get_loader().list_sources)
    return {"sources": sources}


@router.get("/{scenario_id}/quick-info")
async def get_quick_info(scenario_id: str):
    """Calculate basic info (n_outcomes, opposition) quickly on-demand.

    This is faster than full stats calculation and useful for displaying
    basic info when selecting a scenario.

    Args:
        scenario_id: Base64-encoded scenario path.

    Returns:
        Dict with n_outcomes, opposition, rational_fraction
    """
    from negmas import Scenario
    from negmas.preferences.ops import opposition_level, is_rational

    try:
        # Load scenario
        path = decode_scenario_path(scenario_id)
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


@router.get("/{scenario_id}/stats")
async def get_scenario_stats(scenario_id: str):
    """Get cached stats for a scenario.

    Args:
        scenario_id: Base64-encoded scenario path.

    Returns:
        Cached scenario statistics.
    """
    path = decode_scenario_path(scenario_id)
    stats = await asyncio.to_thread(get_loader().get_scenario_stats, path)
    return asdict(stats)


@router.post("/{scenario_id}/stats/calculate")
async def calculate_scenario_stats(scenario_id: str, force: bool = False):
    """Calculate and save scenario statistics.

    Args:
        scenario_id: Base64-encoded scenario path.
        force: If True, recalculate even if stats exist.

    Returns:
        Computed scenario statistics.
    """
    path = decode_scenario_path(scenario_id)
    stats = await asyncio.to_thread(get_loader().calculate_and_save_stats, path, force)
    return asdict(stats)


@router.get("/{scenario_id}/plot-data")
async def get_scenario_plot_data(
    scenario_id: str, max_samples: int = 10000, force_regenerate: bool = False
):
    """Get plot data for a scenario.

    Args:
        scenario_id: Base64-encoded scenario path.
        max_samples: Maximum number of outcome samples for plot.
        force_regenerate: Force regeneration even if cached.

    Returns:
        Plot data with utilities, outcomes, etc.
    """
    path = decode_scenario_path(scenario_id)

    def _compute():
        scenario = get_loader().load_scenario(path, load_stats=True, load_info=True)
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


@router.get("/{scenario_id}/available-plots")
async def get_available_plots(scenario_id: str):
    """Get list of available plot files for a scenario.

    Args:
        scenario_id: Base64-encoded scenario path.

    Returns:
        List of plot file information for bilateral or multilateral scenarios.
    """
    from pathlib import Path

    path = decode_scenario_path(scenario_id)
    scenario_dir = Path(path)
    plots_dir = scenario_dir / "_plots"

    # Check if multilateral (has _plots/ folder)
    if plots_dir.exists() and plots_dir.is_dir():
        # Multilateral scenario - list all plots in _plots/
        plot_files = sorted(plots_dir.glob("*.webp")) + sorted(plots_dir.glob("*.png"))
        return {
            "type": "multilateral",
            "plots": [
                {"name": p.stem, "filename": p.name, "path": str(p)} for p in plot_files
            ],
        }
    else:
        # Bilateral scenario - single plot file
        single_plot = scenario_dir / "_plot.webp"
        if not single_plot.exists():
            single_plot = scenario_dir / "_plot.png"

        if single_plot.exists():
            return {
                "type": "bilateral",
                "plots": [
                    {
                        "name": "plot",
                        "filename": single_plot.name,
                        "path": str(single_plot),
                    }
                ],
            }
        else:
            return {"type": "bilateral", "plots": []}


@router.get("/{scenario_id}/plot-image")
async def get_scenario_plot_image(scenario_id: str, plot_name: str | None = None):
    """Serve the cached plot image for a scenario.

    Args:
        scenario_id: Base64-encoded scenario path.
        plot_name: Optional plot name for multilateral scenarios (e.g., "util1-util2").
                   If not provided, returns the default/first plot.

    Returns:
        WebP/PNG/JPG/SVG image file.
    """
    from pathlib import Path

    path = decode_scenario_path(scenario_id)
    scenario_dir = Path(path)
    plots_dir = scenario_dir / "_plots"

    # Check if multilateral (has _plots/ folder)
    if plots_dir.exists() and plots_dir.is_dir():
        # Multilateral scenario
        if plot_name:
            # Try to find the specific plot
            plot_path = plots_dir / f"{plot_name}.webp"
            if not plot_path.exists():
                plot_path = plots_dir / f"{plot_name}.png"
            if not plot_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Plot '{plot_name}' not found in multilateral scenario.",
                )
        else:
            # Return first available plot
            plot_files = sorted(plots_dir.glob("*.webp")) + sorted(
                plots_dir.glob("*.png")
            )
            if not plot_files:
                raise HTTPException(
                    status_code=404, detail="No plot images found in _plots/ directory."
                )
            plot_path = plot_files[0]
    else:
        # Bilateral scenario - single _plot.webp
        from ..services.plot_service import find_existing_plot

        plot_path = find_existing_plot(path)

        if not plot_path:
            raise HTTPException(
                status_code=404,
                detail="Plot image not found. Call /plot-data first to generate it.",
            )

    # Determine media type from extension
    ext = plot_path.suffix.lower()
    media_types = {
        ".webp": "image/webp",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
    }
    media_type = media_types.get(ext, "image/webp")

    # Add cache headers to prevent browser from caching stale plots
    # Use file modification time as ETag for proper cache invalidation
    file_mtime = plot_path.stat().st_mtime
    headers = {
        "Cache-Control": "no-cache, must-revalidate",
        "ETag": f'"{int(file_mtime)}"',
    }

    return FileResponse(
        plot_path,
        media_type=media_type,
        filename=f"{Path(path).name}_plot{ext}",
        headers=headers,
    )


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get details for a specific scenario.

    Args:
        scenario_id: Base64-encoded scenario path.

    Returns:
        Scenario info with full details.
    """
    path = decode_scenario_path(scenario_id)
    info = await asyncio.to_thread(get_loader().get_scenario_info, path)
    if info is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return _scenario_to_dict(info)


def _scenario_to_dict(info) -> dict:
    """Convert ScenarioInfo to dict for JSON response."""
    import math

    # Helper to sanitize numeric values for JSON
    def sanitize_number(val):
        if val is None:
            return None
        if isinstance(val, (int, float)):
            if math.isinf(val) or math.isnan(val):
                return None  # Convert inf/nan to None for JSON compatibility
        return val

    return {
        "id": encode_scenario_path(info.path),  # Base64-encoded ID for URLs
        "path": info.path,
        "name": info.name,
        "n_negotiators": info.n_negotiators,
        "n_issues": info.n_issues,
        "n_outcomes": sanitize_number(info.n_outcomes),
        "rational_fraction": sanitize_number(info.rational_fraction),
        "opposition": sanitize_number(info.opposition),
        "source": info.source,
        "tags": info.tags,
        "has_stats": info.has_stats,
        "has_info": info.has_info,
        "normalized": info.normalized,
        "format": info.format,
        "description": info.description,
        "readonly": info.readonly,
        "issues": [
            {
                "name": i.name,
                "type": i.type,
                "values": i.values,
                "min_value": i.min_value,
                "max_value": i.max_value,
            }
            for i in info.issues
        ],
    }


@router.get("/{scenario_id}/info")
async def get_scenario_info(scenario_id: str):
    """Get full details for a specific scenario by loading it directly.

    This loads the Scenario object and extracts all information from it,
    including issues from outcome_space, ufuns, and cached stats/info.

    Args:
        scenario_id: Base64-encoded scenario path.

    Returns:
        Scenario info with full details including issues, ufuns, stats.
    """
    try:
        # Decode the path
        path = decode_scenario_path(scenario_id)
        scenario_path = Path(path)

        # Load scenario once and cache it
        scenario = await get_cached_scenario(path, load_stats=True, load_info=True)

        # Extract issue information from outcome_space
        issues = []
        for issue in scenario.outcome_space.issues:
            issue_info = {
                "name": issue.name,
                "type": type(issue).__name__,
                "values": issue.values
                if hasattr(issue, "values") and issue.values
                else None,
                "min_value": issue.min_value if hasattr(issue, "min_value") else None,
                "max_value": issue.max_value if hasattr(issue, "max_value") else None,
            }
            issues.append(issue_info)

        # Extract basic info
        n_outcomes = scenario.outcome_space.cardinality
        if n_outcomes == float("inf"):
            # Sample for infinite spaces
            n_outcomes = len(
                list(scenario.outcome_space.enumerate_or_sample(max_cardinality=50000))
            )

        # Get cached stats if available
        has_stats = (
            (scenario_path / "_stats.yaml").exists()
            if scenario_path.is_dir()
            else False
        )
        has_info = (
            (scenario_path / "_info.yaml").exists() if scenario_path.is_dir() else False
        )

        # Extract from scenario.info dict if available
        info_dict = scenario.info or {}
        normalized = info_dict.get(
            "normalized",
            scenario.is_normalized if hasattr(scenario, "is_normalized") else None,
        )
        description = info_dict.get("description", "")

        # Detect format from files
        format_type = None
        if scenario_path.is_dir():
            if (scenario_path / "domain.xml").exists():
                format_type = "xml"
            elif (scenario_path / "domain.yaml").exists():
                format_type = "yaml"
            elif (scenario_path / "domain.json").exists():
                format_type = "json"

        return {
            "id": encode_scenario_path(str(scenario_path)),
            "path": str(scenario_path),
            "name": scenario_path.name
            if scenario_path.is_dir()
            else scenario_path.stem,
            "n_negotiators": len(scenario.ufuns),
            "n_issues": len(scenario.outcome_space.issues),
            "n_outcomes": n_outcomes if n_outcomes != float("inf") else None,
            "rational_fraction": info_dict.get("rational_fraction"),
            "opposition": info_dict.get("opposition"),
            "source": scenario_path.parent.name
            if scenario_path.is_dir()
            else "unknown",
            "tags": [],
            "has_stats": has_stats,
            "has_info": has_info,
            "normalized": normalized,
            "format": format_type,
            "description": description,
            "issues": issues,
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {path}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load scenario: {str(e)}"
        )


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
                    get_loader().calculate_and_save_stats, path, force
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
        scenario, created_path, error = get_loader().create_scenario(
            definition, save_path
        )

        if error:
            return {"success": False, "error": error}

        # Get info for the created scenario
        if scenario is not None and created_path is not None:
            info = get_loader().get_scenario_info(str(created_path))
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


@router.get("/{scenario_id}/ufuns")
async def get_ufun_details(scenario_id: str):
    """Get detailed information about all utility functions in a scenario.

    This uses the cached scenario to avoid reloading.

    Args:
        scenario_id: Base64-encoded scenario path.

    Returns:
        Dict with ufuns array and scenario files information.
    """
    from ..services.ufun_info_service import get_ufun_info, get_scenario_files

    try:
        # Decode path
        path = decode_scenario_path(scenario_id)
        scenario_path = Path(path)

        # Use cached scenario
        scenario = await get_cached_scenario(path, load_info=True, load_stats=False)

        # Get file information
        files_info = get_scenario_files(scenario_path)

        # Extract ufun details
        ufuns = []
        for i, ufun in enumerate(scenario.ufuns):
            ufun_info = get_ufun_info(ufun, scenario_path)
            ufun_info["index"] = i
            ufuns.append(ufun_info)

        return {
            "success": True,
            "ufuns": ufuns,
            "files": files_info,
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{scenario_id}/files/{file_path:path}")
async def get_scenario_file_content(scenario_id: str, file_path: str):
    """Get the content of a scenario file for editing.

    Args:
        scenario_id: Base64-encoded scenario path.
        file_path: Relative path to the file within the scenario.

    Returns:
        Dict with file content and metadata.
    """
    try:
        path = decode_scenario_path(scenario_id)
        scenario_path = Path(path)
        full_file_path = scenario_path / file_path

        # Security check - ensure file is within scenario directory
        if not full_file_path.resolve().is_relative_to(scenario_path.resolve()):
            raise HTTPException(
                status_code=403, detail="Access denied: file outside scenario directory"
            )

        if not full_file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        if not full_file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Not a file: {file_path}")

        # Read file content
        content = full_file_path.read_text(encoding="utf-8")

        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "full_path": str(full_file_path),
            "size": len(content),
            "extension": full_file_path.suffix,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FileUpdateRequest(BaseModel):
    """Request body for updating a scenario file."""

    content: str


@router.put("/{scenario_id}/files/{file_path:path}")
async def update_scenario_file(
    scenario_id: str, file_path: str, request: FileUpdateRequest
):
    """Update the content of a scenario file and invalidate related caches.

    Args:
        scenario_id: Base64-encoded scenario path.
        file_path: Relative path to the file within the scenario.
        request: Request body with new file content.

    Returns:
        Dict with success status.
    """
    try:
        path = decode_scenario_path(scenario_id)
        scenario_path = Path(path)

        # Check if scenario is read-only
        scenario_info = get_loader().get_scenario_info(str(scenario_path))
        if scenario_info and scenario_info.readonly:
            raise HTTPException(
                status_code=403,
                detail="Cannot modify read-only scenario. This scenario is from a read-only source.",
            )

        full_file_path = scenario_path / file_path

        # Security check - ensure file is within scenario directory
        if not full_file_path.resolve().is_relative_to(scenario_path.resolve()):
            raise HTTPException(
                status_code=403, detail="Access denied: file outside scenario directory"
            )

        if not full_file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        # Write updated content
        full_file_path.write_text(request.content, encoding="utf-8")

        # Invalidate caches
        await _invalidate_scenario_caches(scenario_path)

        return {
            "success": True,
            "message": f"File updated: {file_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _invalidate_scenario_caches(scenario_path: Path):
    """Delete cache files for a scenario after modification.

    Args:
        scenario_path: Path to the scenario directory.
    """
    # Delete info cache
    for info_file in ["_info.yaml", "_info.yml"]:
        cache_file = scenario_path / info_file
        if cache_file.exists():
            cache_file.unlink()

    # Delete stats cache
    stats_file = scenario_path / "_stats.yaml"
    if stats_file.exists():
        stats_file.unlink()

    # Delete plot caches
    plot_file = scenario_path / "_plot.webp"
    if plot_file.exists():
        plot_file.unlink()

    plots_dir = scenario_path / "_plots"
    if plots_dir.exists() and plots_dir.is_dir():
        import shutil

        shutil.rmtree(plots_dir)


@router.post("/{scenario_id}/open-folder")
async def open_scenario_folder(scenario_id: str):
    """Open the scenario folder in the system file explorer.

    Args:
        scenario_id: Base64-encoded scenario path.

    Returns:
        Dict with success status.
    """
    import subprocess
    import sys

    try:
        path = decode_scenario_path(scenario_id)
        scenario_path = Path(path)

        if not scenario_path.exists():
            raise HTTPException(status_code=404, detail=f"Scenario not found: {path}")

        # Open folder in system file explorer based on OS
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", str(scenario_path)], check=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(["explorer", str(scenario_path)], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(scenario_path)], check=True)

        return {
            "success": True,
            "message": f"Opened folder: {scenario_path.name}",
        }

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if plot_file.exists():
        plot_file.unlink()

    plots_dir = scenario_path / "_plots"
    if plots_dir.exists() and plots_dir.is_dir():
        import shutil

        shutil.rmtree(plots_dir)
