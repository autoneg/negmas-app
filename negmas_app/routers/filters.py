"""API routes for filter management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.filter_service import FilterService

router = APIRouter(prefix="/filters", tags=["filters"])

# Initialize filter service
filter_service = FilterService()


class SaveFilterRequest(BaseModel):
    """Request body for saving a filter."""

    name: str
    type: str  # "scenario" or "negotiator"
    data: dict
    description: str = ""


class UpdateFilterRequest(BaseModel):
    """Request body for updating a filter."""

    name: str | None = None
    data: dict | None = None
    description: str | None = None


@router.get("/")
def list_filters(type: str | None = None):
    """List all saved filters, optionally filtered by type.

    Args:
        type: Filter by type ("scenario" or "negotiator"). Omit for all.

    Returns:
        List of saved filters.
    """
    try:
        filters = filter_service.list_filters(filter_type=type)
        return {
            "success": True,
            "filters": [
                {
                    "id": f.id,
                    "name": f.name,
                    "type": f.type,
                    "data": f.data,
                    "description": f.description,
                    "created_at": f.created_at,
                }
                for f in filters
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{filter_id}")
def get_filter(filter_id: str):
    """Get a saved filter by ID.

    Args:
        filter_id: ID of the filter to retrieve.

    Returns:
        The filter data.
    """
    filter_obj = filter_service.get_filter(filter_id)
    if filter_obj is None:
        raise HTTPException(status_code=404, detail="Filter not found")

    return {
        "success": True,
        "filter": {
            "id": filter_obj.id,
            "name": filter_obj.name,
            "type": filter_obj.type,
            "data": filter_obj.data,
            "description": filter_obj.description,
            "created_at": filter_obj.created_at,
        },
    }


@router.post("/")
def save_filter(request: SaveFilterRequest):
    """Save a new filter.

    Args:
        request: SaveFilterRequest with filter details.

    Returns:
        The newly created filter.
    """
    try:
        new_filter = filter_service.save_filter(
            name=request.name,
            filter_type=request.type,
            data=request.data,
            description=request.description,
        )
        return {
            "success": True,
            "filter": {
                "id": new_filter.id,
                "name": new_filter.name,
                "type": new_filter.type,
                "data": new_filter.data,
                "description": new_filter.description,
                "created_at": new_filter.created_at,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{filter_id}")
def update_filter(filter_id: str, request: UpdateFilterRequest):
    """Update an existing filter.

    Args:
        filter_id: ID of the filter to update.
        request: UpdateFilterRequest with fields to update.

    Returns:
        The updated filter.
    """
    try:
        updated_filter = filter_service.update_filter(
            filter_id=filter_id,
            name=request.name,
            data=request.data,
            description=request.description,
        )
        if updated_filter is None:
            raise HTTPException(status_code=404, detail="Filter not found")

        return {
            "success": True,
            "filter": {
                "id": updated_filter.id,
                "name": updated_filter.name,
                "type": updated_filter.type,
                "data": updated_filter.data,
                "description": updated_filter.description,
                "created_at": updated_filter.created_at,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filter_id}")
def delete_filter(filter_id: str):
    """Delete a saved filter.

    Args:
        filter_id: ID of the filter to delete.

    Returns:
        Success status.
    """
    success = filter_service.delete_filter(filter_id)
    if not success:
        raise HTTPException(status_code=404, detail="Filter not found")

    return {"success": True}
