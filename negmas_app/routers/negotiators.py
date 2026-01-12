"""Negotiator API endpoints."""

from fastapi import APIRouter, Query

from ..services import NegotiatorFactory, BOAFactory

router = APIRouter(prefix="/api/negotiators", tags=["negotiators"])


@router.get("")
def list_negotiators(
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
    negotiators = NegotiatorFactory.list_available(
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
def list_sources():
    """List all available negotiator sources.

    Returns:
        List of source info objects with availability status.
    """
    sources = NegotiatorFactory.get_available_sources()

    # Count negotiators per source
    all_negotiators = NegotiatorFactory.list_available()
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
def list_boa_components(
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
    components = BOAFactory.list_components(component_type)
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
def refresh_registry():
    """Refresh the negotiator registry.

    Call this after changing negotiator source settings.
    """
    NegotiatorFactory.refresh_registry()
    return {"status": "ok", "message": "Registry refreshed"}


@router.get("/{type_name:path}")
def get_negotiator(type_name: str):
    """Get details for a specific negotiator type.

    Args:
        type_name: Full type name of the negotiator (e.g., "negmas.sao.AspirationNegotiator")

    Returns:
        Negotiator info or 404.
    """
    info = NegotiatorFactory.get_info(type_name)
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
