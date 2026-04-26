"""Mechanism type API endpoints."""

import asyncio

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ..services.mechanism_registry import (
    get_all_mechanisms,
    get_mechanism_info,
    get_sorted_param_groups,
    PARAM_GROUP_INFO,
)
from ..services import VirtualMechanismService


# Pydantic models for request/response validation
class VirtualMechanismCreate(BaseModel):
    """Request body for creating a virtual mechanism."""

    name: str
    base_type: str
    params: dict | None = None
    description: str = ""
    tags: list[str] | None = None


class VirtualMechanismUpdate(BaseModel):
    """Request body for updating a virtual mechanism."""

    name: str | None = None
    params: dict | None = None
    description: str | None = None
    tags: list[str] | None = None


router = APIRouter(prefix="/api/mechanisms", tags=["mechanisms"])


@router.get("")
async def list_mechanisms():
    """Get all available mechanism types with their parameters."""
    mechanisms = get_all_mechanisms()
    result = []

    for mech in mechanisms:
        # Combine base and specific params for grouping
        all_params = mech.base_params + mech.specific_params
        sorted_groups = get_sorted_param_groups(all_params)

        # Build grouped params for UI
        param_groups = []
        for group_name, group_info, params in sorted_groups:
            param_groups.append(
                {
                    "id": group_name,
                    "label": group_info["label"],
                    "icon": group_info.get("icon", "circle"),
                    "order": group_info["order"],
                    "params": [
                        {
                            "name": p.name,
                            "type": p.param_type.value,
                            "default": _serialize_default(p.default),
                            "description": p.description,
                            "required": p.required,
                            "choices": p.choices,
                            "min_value": p.min_value,
                            "max_value": p.max_value,
                        }
                        for p in params
                    ],
                }
            )

        result.append(
            {
                "name": mech.name,
                "class_name": mech.class_name,
                "module": mech.module,
                "description": mech.description,
                "full_class_path": mech.full_class_path,
                "param_groups": param_groups,
            }
        )

    return {"mechanisms": result}


# =============================================================================
# Virtual Mechanism Endpoints
# =============================================================================


@router.get("/virtual")
async def list_virtual_mechanisms(
    search: str | None = Query(None, description="Search in name/description/tags"),
    tags: str | None = Query(None, description="Comma-separated tags to filter by"),
    base_type: str | None = Query(None, description="Filter by base mechanism type"),
):
    """List all virtual mechanisms with optional filtering.

    Args:
        search: Search string to match in name/description/tags
        tags: Comma-separated tags (match any)
        base_type: Filter by base mechanism type (e.g., "sao", "tau", "gb")

    Returns:
        List of virtual mechanism objects.
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    virtual_mechanisms = await asyncio.to_thread(
        VirtualMechanismService.list_all,
        search=search,
        tags=tag_list,
        base_type=base_type,
    )
    return {
        "virtual_mechanisms": [vm.to_dict() for vm in virtual_mechanisms],
        "count": len(virtual_mechanisms),
    }


@router.post("/virtual")
async def create_virtual_mechanism(data: VirtualMechanismCreate):
    """Create a new virtual mechanism.

    Args:
        data: Virtual mechanism creation data

    Returns:
        The created virtual mechanism.
    """
    try:
        vm = await asyncio.to_thread(
            VirtualMechanismService.create,
            name=data.name,
            base_type=data.base_type,
            params=data.params,
            description=data.description,
            tags=data.tags,
        )
        return {"virtual_mechanism": vm.to_dict(), "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/virtual/tags")
async def get_virtual_mechanism_tags():
    """Get all unique tags used by virtual mechanisms.

    Returns:
        List of unique tags sorted alphabetically.
    """
    tags = await asyncio.to_thread(VirtualMechanismService.get_all_tags)
    return {"tags": tags, "count": len(tags)}


@router.get("/virtual/{vm_id}")
async def get_virtual_mechanism(vm_id: str):
    """Get a virtual mechanism by ID.

    Args:
        vm_id: Virtual mechanism ID

    Returns:
        Virtual mechanism details or 404.
    """
    vm = await asyncio.to_thread(VirtualMechanismService.get, vm_id)
    if vm is None:
        raise HTTPException(status_code=404, detail="Virtual mechanism not found")
    return {"virtual_mechanism": vm.to_dict()}


@router.put("/virtual/{vm_id}")
async def update_virtual_mechanism(vm_id: str, data: VirtualMechanismUpdate):
    """Update an existing virtual mechanism.

    Args:
        vm_id: Virtual mechanism ID
        data: Fields to update

    Returns:
        The updated virtual mechanism.
    """
    try:
        vm = await asyncio.to_thread(
            VirtualMechanismService.update,
            vm_id=vm_id,
            name=data.name,
            params=data.params,
            description=data.description,
            tags=data.tags,
        )
        if vm is None:
            raise HTTPException(status_code=404, detail="Virtual mechanism not found")
        return {"virtual_mechanism": vm.to_dict(), "status": "updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/virtual/{vm_id}")
async def delete_virtual_mechanism(vm_id: str):
    """Delete a virtual mechanism.

    Args:
        vm_id: Virtual mechanism ID

    Returns:
        Deletion status.
    """
    deleted = await asyncio.to_thread(VirtualMechanismService.delete, vm_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Virtual mechanism not found")
    return {"status": "deleted", "id": vm_id}


@router.post("/virtual/{vm_id}/duplicate")
async def duplicate_virtual_mechanism(
    vm_id: str,
    new_name: str | None = Query(None, description="Name for the duplicate"),
):
    """Duplicate an existing virtual mechanism.

    Args:
        vm_id: Virtual mechanism ID to duplicate
        new_name: Optional name for the duplicate (defaults to "Copy of <name>")

    Returns:
        The duplicated virtual mechanism.
    """
    vm = await asyncio.to_thread(
        VirtualMechanismService.duplicate, vm_id, new_name=new_name
    )
    if vm is None:
        raise HTTPException(status_code=404, detail="Virtual mechanism not found")
    return {"virtual_mechanism": vm.to_dict(), "status": "duplicated"}


# =============================================================================
# Specific Mechanism Type Routes (must come after /virtual routes)
# =============================================================================


@router.get("/groups/info")
async def get_param_group_info():
    """Get metadata about parameter groups for UI rendering."""
    return {"groups": PARAM_GROUP_INFO}


@router.get("/{class_name}")
async def get_mechanism(class_name: str):
    """Get details for a specific mechanism type."""
    mech = get_mechanism_info(class_name)
    if mech is None:
        return {"error": f"Mechanism '{class_name}' not found"}

    # Combine base and specific params for grouping
    all_params = mech.base_params + mech.specific_params
    sorted_groups = get_sorted_param_groups(all_params)

    # Build grouped params for UI
    param_groups = []
    for group_name, group_info, params in sorted_groups:
        param_groups.append(
            {
                "id": group_name,
                "label": group_info["label"],
                "icon": group_info.get("icon", "circle"),
                "order": group_info["order"],
                "params": [
                    {
                        "name": p.name,
                        "type": p.param_type.value,
                        "default": _serialize_default(p.default),
                        "description": p.description,
                        "required": p.required,
                        "choices": p.choices,
                        "min_value": p.min_value,
                        "max_value": p.max_value,
                    }
                    for p in params
                ],
            }
        )

    return {
        "name": mech.name,
        "class_name": mech.class_name,
        "module": mech.module,
        "description": mech.description,
        "full_class_path": mech.full_class_path,
        "param_groups": param_groups,
    }


def _serialize_default(value):
    """Serialize default value for JSON."""
    if value is None:
        return None
    if isinstance(value, float):
        if value == float("inf"):
            return "inf"
        if value == float("-inf"):
            return "-inf"
    return value
