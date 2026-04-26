"""Sources API - Module inspection and scenario validation endpoints."""

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import (
    inspect_module_ast,
    inspect_module_dynamic,
    validate_scenario_path,
    list_scenario_folders,
)

router = APIRouter(prefix="/api/sources", tags=["sources"])


class ModuleInspectRequest(BaseModel):
    """Request to inspect a Python module."""

    path: str
    dynamic: bool = (
        False  # If True, actually import the module (more info but less safe)
    )


class ScenarioValidateRequest(BaseModel):
    """Request to validate a scenario path."""

    path: str


class ScenarioListRequest(BaseModel):
    """Request to list scenarios in a directory."""

    path: str


class AddCustomSourceRequest(BaseModel):
    """Request to add a custom source (negotiator/mechanism from module)."""

    module_path: str
    class_names: list[str]
    source_type: str  # "negotiator" or "mechanism"
    source_name: str  # Display name for the source


@router.post("/module/inspect")
async def inspect_module(request: ModuleInspectRequest):
    """Inspect a Python module for negotiator/mechanism classes.

    Args:
        request: Module inspection request with path and inspection mode.

    Returns:
        List of discovered classes with metadata.
    """
    path = Path(request.path).expanduser().resolve()

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.path}")

    if not path.is_file():
        raise HTTPException(status_code=400, detail="Path must be a file")

    if path.suffix != ".py":
        raise HTTPException(status_code=400, detail="File must be a Python file (.py)")

    # Run inspection in thread pool
    if request.dynamic:
        result = await asyncio.to_thread(inspect_module_dynamic, str(path))
    else:
        result = await asyncio.to_thread(inspect_module_ast, str(path))

    if result.error:
        return {
            "success": False,
            "error": result.error,
            "path": str(path),
            "module_name": result.module_name,
            "classes": [],
        }

    return {
        "success": True,
        "path": str(path),
        "module_name": result.module_name,
        "classes": [asdict(c) for c in result.classes],
        "negotiators": [asdict(c) for c in result.classes if c.is_negotiator],
        "mechanisms": [asdict(c) for c in result.classes if c.is_mechanism],
        "boa_components": [asdict(c) for c in result.classes if c.is_boa_component],
    }


@router.post("/scenario/validate")
async def validate_scenario(request: ScenarioValidateRequest):
    """Validate a scenario path (file or directory).

    Args:
        request: Scenario validation request with path.

    Returns:
        Validation result with scenario info if valid.
    """
    path = Path(request.path).expanduser().resolve()

    result = await asyncio.to_thread(validate_scenario_path, str(path))
    return result


@router.post("/scenario/list-folder")
async def list_scenarios_in_folder(request: ScenarioListRequest):
    """List all valid scenarios in a directory.

    Args:
        request: Request with directory path.

    Returns:
        List of valid scenarios found in the directory.
    """
    path = Path(request.path).expanduser().resolve()

    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Directory not found: {request.path}"
        )

    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Path must be a directory")

    results = await asyncio.to_thread(list_scenario_folders, str(path))
    return {
        "path": str(path),
        "scenarios": results,
        "count": len(results),
    }


@router.post("/browse/files")
async def browse_files(data: dict[str, Any]):
    """Browse files in a directory.

    Args:
        data: Dict with 'path' and optional 'extensions' filter.

    Returns:
        List of files and directories.
    """
    path_str = data.get("path", "~")
    extensions = data.get("extensions", [])  # e.g., [".py", ".pkl"]

    path = Path(path_str).expanduser().resolve()

    if not path.exists():
        # Try parent directory
        if path.parent.exists():
            path = path.parent
        else:
            path = Path.home()

    if not path.is_dir():
        path = path.parent

    items = []
    try:
        for item in sorted(path.iterdir()):
            if item.name.startswith("."):
                continue  # Skip hidden files

            item_info = {
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
            }

            if item.is_file():
                item_info["extension"] = item.suffix
                # Filter by extension if specified
                if extensions and item.suffix.lower() not in [
                    e.lower() for e in extensions
                ]:
                    continue

            items.append(item_info)
    except PermissionError:
        pass

    # Sort: directories first, then files
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    return {
        "current_path": str(path),
        "parent_path": str(path.parent) if path.parent != path else None,
        "items": items,
    }


@router.get("/home")
async def get_home_directory():
    """Get the user's home directory path."""
    return {"path": str(Path.home())}
