"""Component API endpoints for BOA/MAP components."""

import asyncio

from fastapi import APIRouter

from ..services import BOAFactory


router = APIRouter(prefix="/api/components", tags=["components"])


@router.get("")
async def list_components():
    """List all available BOA/MAP components (acceptance, offering, model).

    Returns:
        Dict mapping component type to list of component names.
    """
    components = await asyncio.to_thread(BOAFactory.list_components, None)

    # Extract just the names for simplicity
    return {
        "acceptance": [c.name for c in components.get("acceptance", [])],
        "offering": [c.name for c in components.get("offering", [])],
        "model": [c.name for c in components.get("model", [])],
    }
