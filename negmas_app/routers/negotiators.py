"""Negotiator API endpoints."""

import asyncio

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ..services import (
    NegotiatorFactory,
    BOAFactory,
    get_negotiator_parameters,
    clear_parameter_cache,
    VirtualNegotiatorService,
)


# Pydantic models for request/response validation
class VirtualNegotiatorCreate(BaseModel):
    """Request body for creating a virtual negotiator."""

    name: str
    base_type_name: str
    params: dict | None = None
    description: str = ""
    tags: list[str] | None = None


class VirtualNegotiatorUpdate(BaseModel):
    """Request body for updating a virtual negotiator."""

    name: str | None = None
    params: dict | None = None
    description: str | None = None
    tags: list[str] | None = None


router = APIRouter(prefix="/api/negotiators", tags=["negotiators"])


@router.get("")
async def list_negotiators(
    source: str | None = Query(None, description="Filter by source ID"),
    group: str | None = Query(None, description="Filter by group within source"),
    search: str | None = Query(None, description="Search in name/description"),
):
    """List available negotiators with optional filtering.

    Args:
        source: Filter by source ID (e.g., "native", "genius", "llm")
        group: Filter by group within source (e.g., "y2019" for genius)
        search: Search string to match against name/description

    Returns:
        List of negotiator info objects.
    """
    negotiators = await asyncio.to_thread(
        NegotiatorFactory.list_available,
        source=source,
        group=group,
        search=search,
    )
    return {
        "negotiators": [
            {
                "type_name": n.type_name,
                "name": n.name,
                "source": n.source,
                "group": n.group,
                "description": n.description,
                "tags": n.tags,
                "mechanisms": n.mechanisms,
                "requires_bridge": n.requires_bridge,
                "available": n.available,
            }
            for n in negotiators
        ],
        "count": len(negotiators),
    }


@router.get("/sources")
async def list_sources():
    """List all available negotiator sources.

    Returns:
        List of source info objects with availability status.
    """
    sources = await asyncio.to_thread(NegotiatorFactory.get_available_sources)

    # Count negotiators per source
    all_negotiators = await asyncio.to_thread(NegotiatorFactory.list_available)
    source_counts = {}
    for neg in all_negotiators:
        source_counts[neg.source] = source_counts.get(neg.source, 0) + 1

    return {
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "mechanisms": s.mechanisms,
                "requires_bridge": s.requires_bridge,
                "builtin": s.builtin,
                "available": NegotiatorFactory.is_source_available(s.id),
                "count": source_counts.get(s.id, 0),
                "unavailable_reason": NegotiatorFactory.get_source_unavailable_reason(
                    s.id
                ),
            }
            for s in sources
        ]
    }


@router.get("/boa/components")
async def list_boa_components(
    component_type: str | None = Query(
        None, description="Filter by type: acceptance, offering, model"
    ),
):
    """List available BOA (Bidding-Opponent-Acceptance) components.

    Args:
        component_type: Filter by component type (acceptance, offering, model).

    Returns:
        Dict mapping component type to list of components.
    """
    components = await asyncio.to_thread(BOAFactory.list_components, component_type)
    return {
        "components": {
            ctype: [
                {
                    "name": c.name,
                    "type_name": c.type_name,
                    "component_type": c.component_type,
                    "description": c.description,
                }
                for c in clist
            ]
            for ctype, clist in components.items()
        },
        "counts": {ctype: len(clist) for ctype, clist in components.items()},
    }


@router.post("/refresh")
async def refresh_registry():
    """Refresh the negotiator registry.

    Call this after changing negotiator source settings.
    """
    await asyncio.to_thread(NegotiatorFactory.refresh_registry)
    return {"status": "ok", "message": "Registry refreshed"}


@router.post("/cache/clear")
async def clear_cache_endpoint():
    """Clear the negotiator parameter cache.

    Call this if negotiator parameters seem stale.
    """
    count = await asyncio.to_thread(clear_parameter_cache)
    return {"status": "ok", "message": f"Cleared {count} cached entries"}


# =============================================================================
# Virtual Negotiator Endpoints
# =============================================================================


@router.get("/virtual")
async def list_virtual_negotiators(
    search: str | None = Query(None, description="Search in name/description/tags"),
    tags: str | None = Query(None, description="Comma-separated tags to filter by"),
    base_type: str | None = Query(None, description="Filter by base negotiator type"),
):
    """List all virtual negotiators with optional filtering.

    Args:
        search: Search string to match in name/description/tags
        tags: Comma-separated tags (match any)
        base_type: Filter by base negotiator type name

    Returns:
        List of virtual negotiator objects.
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    virtual_negotiators = await asyncio.to_thread(
        VirtualNegotiatorService.list_all,
        search=search,
        tags=tag_list,
        base_type=base_type,
    )
    return {
        "virtual_negotiators": [vn.to_dict() for vn in virtual_negotiators],
        "count": len(virtual_negotiators),
    }


@router.post("/virtual")
async def create_virtual_negotiator(data: VirtualNegotiatorCreate):
    """Create a new virtual negotiator.

    Args:
        data: Virtual negotiator creation data

    Returns:
        The created virtual negotiator.
    """
    try:
        vn = await asyncio.to_thread(
            VirtualNegotiatorService.create,
            name=data.name,
            base_type_name=data.base_type_name,
            params=data.params,
            description=data.description,
            tags=data.tags,
        )
        return {"virtual_negotiator": vn.to_dict(), "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/virtual/tags")
async def get_virtual_negotiator_tags():
    """Get all unique tags used by virtual negotiators.

    Returns:
        List of unique tags sorted alphabetically.
    """
    tags = await asyncio.to_thread(VirtualNegotiatorService.get_all_tags)
    return {"tags": tags, "count": len(tags)}


@router.get("/virtual/{vn_id}")
async def get_virtual_negotiator(vn_id: str):
    """Get a virtual negotiator by ID.

    Args:
        vn_id: Virtual negotiator ID

    Returns:
        Virtual negotiator details or 404.
    """
    vn = await asyncio.to_thread(VirtualNegotiatorService.get, vn_id)
    if vn is None:
        raise HTTPException(status_code=404, detail="Virtual negotiator not found")
    return {"virtual_negotiator": vn.to_dict()}


@router.put("/virtual/{vn_id}")
async def update_virtual_negotiator(vn_id: str, data: VirtualNegotiatorUpdate):
    """Update an existing virtual negotiator.

    Args:
        vn_id: Virtual negotiator ID
        data: Fields to update

    Returns:
        The updated virtual negotiator.
    """
    try:
        vn = await asyncio.to_thread(
            VirtualNegotiatorService.update,
            vn_id=vn_id,
            name=data.name,
            params=data.params,
            description=data.description,
            tags=data.tags,
        )
        if vn is None:
            raise HTTPException(status_code=404, detail="Virtual negotiator not found")
        return {"virtual_negotiator": vn.to_dict(), "status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/virtual/{vn_id}")
async def delete_virtual_negotiator(vn_id: str):
    """Delete a virtual negotiator.

    Args:
        vn_id: Virtual negotiator ID

    Returns:
        Deletion status.
    """
    deleted = await asyncio.to_thread(VirtualNegotiatorService.delete, vn_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Virtual negotiator not found")
    return {"status": "deleted", "id": vn_id}


@router.post("/virtual/{vn_id}/duplicate")
async def duplicate_virtual_negotiator(
    vn_id: str,
    new_name: str | None = Query(None, description="Name for the duplicate"),
):
    """Duplicate an existing virtual negotiator.

    Args:
        vn_id: Virtual negotiator ID to duplicate
        new_name: Optional name for the duplicate (defaults to "Copy of <name>")

    Returns:
        The duplicated virtual negotiator.
    """
    vn = await asyncio.to_thread(
        VirtualNegotiatorService.duplicate, vn_id, new_name=new_name
    )
    if vn is None:
        raise HTTPException(status_code=404, detail="Virtual negotiator not found")
    return {"virtual_negotiator": vn.to_dict(), "status": "duplicated"}


# =============================================================================
# Dynamic Type Routes (must come last due to path matching)
# =============================================================================


@router.get("/{type_name:path}/parameters")
async def get_negotiator_params(
    type_name: str,
    use_cache: bool = Query(True, description="Whether to use cached results"),
):
    """Get configurable parameters for a negotiator type.

    Args:
        type_name: Full type name of the negotiator (e.g., "negmas.sao.AspirationNegotiator")
        use_cache: Whether to use cached parameter info

    Returns:
        List of parameter info objects with type, default, and UI hints.
    """
    params = await asyncio.to_thread(
        get_negotiator_parameters, type_name, use_cache=use_cache
    )
    return {
        "type_name": type_name,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "default": p.default,
                "required": p.required,
                "description": p.description,
                "ui_type": p.ui_type,
                "choices": p.choices,
                "min_value": p.min_value,
                "max_value": p.max_value,
                "is_complex": p.is_complex,
            }
            for p in params
        ],
        "count": len(params),
    }


@router.get("/{type_name:path}")
async def get_negotiator(type_name: str):
    """Get details for a specific negotiator type.

    Args:
        type_name: Full type name of the negotiator (e.g., "negmas.sao.AspirationNegotiator")

    Returns:
        Negotiator info or 404.
    """
    info = await asyncio.to_thread(NegotiatorFactory.get_info, type_name)
    if info is None:
        return {"error": "Negotiator not found"}, 404
    return {
        "type_name": info.type_name,
        "name": info.name,
        "source": info.source,
        "group": info.group,
        "description": info.description,
        "tags": info.tags,
        "mechanisms": info.mechanisms,
        "requires_bridge": info.requires_bridge,
        "available": info.available,
        "module_path": info.module_path,
    }
