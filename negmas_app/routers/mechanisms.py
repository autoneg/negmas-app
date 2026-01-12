"""Mechanism type API endpoints."""

from fastapi import APIRouter

from ..services.mechanism_registry import (
    get_all_mechanisms,
    get_mechanism_info,
    get_sorted_param_groups,
    PARAM_GROUP_INFO,
)

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


@router.get("/groups/info")
async def get_param_group_info():
    """Get metadata about parameter groups for UI rendering."""
    return {"groups": PARAM_GROUP_INFO}


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
