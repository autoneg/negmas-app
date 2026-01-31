"""Negotiation API endpoints with SSE streaming."""

import asyncio
import json
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..models import NegotiatorConfig, OfferEvent, SessionInitEvent
from ..services import SessionManager
from ..services.negotiation_storage import NegotiationStorageService

router = APIRouter(prefix="/api/negotiation", tags=["negotiation"])

# Shared session manager (initialized lazily)
_manager: SessionManager | None = None


def get_manager() -> SessionManager:
    """Get or create the session manager instance."""
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager


def sanitize_nan_values(obj):
    """Recursively replace NaN and Inf values with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: sanitize_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_nan_values(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


class NegotiatorConfigRequest(BaseModel):
    """Request model for negotiator configuration."""

    type_name: str
    name: str | None = None
    params: dict = {}
    time_limit: float | None = None  # Negotiator-specific time limit
    n_steps: int | None = None  # Negotiator-specific step limit


class StartNegotiationRequest(BaseModel):
    """Request model to start a negotiation."""

    scenario_path: str
    negotiators: list[NegotiatorConfigRequest]
    mechanism_type: str = "SAOMechanism"  # Class name of mechanism
    mechanism_params: dict = {}  # All mechanism parameters
    step_delay: float = 0.1
    share_ufuns: bool = False
    ignore_discount: bool = False
    ignore_reserved: bool = False
    normalize: bool = False  # Whether to normalize the scenario utility functions
    auto_save: bool = True  # Whether to save negotiation on completion
    save_options: SaveOptionsRequest | None = None  # Advanced save options


class SaveOptionsRequest(BaseModel):
    """Request model for negotiation save options (mirrors Mechanism.save() params)."""

    single_file: bool = False  # Save as single trace file vs directory
    per_negotiator: bool = False  # Save per-negotiator trace files
    save_scenario: bool = True  # Save scenario (ufuns, outcome space)
    save_scenario_stats: bool = False  # Save scenario statistics
    save_agreement_stats: bool = True  # Save agreement optimality stats
    save_config: bool = True  # Save mechanism configuration
    source: str = "full_trace"  # History source: history, trace, extended_trace, full_trace, full_trace_with_utils
    storage_format: str = "parquet"  # Table format: csv, gzip, parquet
    generate_previews: bool = True  # Generate preview images (app-specific)


class TagsUpdateRequest(BaseModel):
    """Request model for updating tags."""

    tags: list[str]


class TagRequest(BaseModel):
    """Request model for adding/removing a single tag."""

    tag: str


class LoadFromPathRequest(BaseModel):
    """Request model for loading a negotiation from an external path."""

    path: str  # Path to a negotiation file or directory


class ImportNegotiationRequest(BaseModel):
    """Request model for importing a negotiation from an external path."""

    path: str  # Path to a negotiation file or directory
    tags: list[str] | None = None  # Optional tags to add to the imported negotiation


def sanitize_float(value: float) -> float | None:
    """Convert NaN/Infinity to None for JSON serialization."""
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return value


def sanitize_utilities(
    utilities: list[tuple[float, ...]] | None,
) -> list[list[float | None]] | None:
    """Sanitize utility arrays to handle NaN/Infinity values."""
    if utilities is None:
        return None
    return [[sanitize_float(v) for v in u] for u in utilities]


@router.post("/start")
async def start_negotiation(request: StartNegotiationRequest):
    """Start a new negotiation session.

    Returns session ID to use for streaming updates.
    """
    # Convert request to internal configs
    configs = [
        NegotiatorConfig(
            type_name=n.type_name,
            name=n.name,
            params=n.params,
            time_limit=n.time_limit,
            n_steps=n.n_steps,
        )
        for n in request.negotiators
    ]

    # Create session
    session = get_manager().create_session(
        scenario_path=request.scenario_path,
        negotiator_configs=configs,
        mechanism_type=request.mechanism_type,
        mechanism_params=request.mechanism_params,
        ignore_discount=request.ignore_discount,
        ignore_reserved=request.ignore_reserved,
        normalize=request.normalize,
        auto_save=request.auto_save,
        save_options=request.save_options.model_dump()
        if request.save_options
        else None,
    )

    return {
        "session_id": session.id,
        "status": session.status.value,
        "stream_url": f"/api/negotiation/{session.id}/stream?step_delay={request.step_delay}&share_ufuns={str(request.share_ufuns).lower()}",
    }


@router.post("/start_background")
async def start_negotiation_background(request: StartNegotiationRequest):
    """Start a negotiation and run it in the background without streaming.

    Returns session_id immediately. Negotiation runs in background thread.
    Client should poll GET /{session_id} for progress updates.
    """
    # Convert request to internal configs
    configs = [
        NegotiatorConfig(
            type_name=n.type_name,
            name=n.name,
            params=n.params,
            time_limit=n.time_limit,
            n_steps=n.n_steps,
        )
        for n in request.negotiators
    ]

    # Create session
    session = get_manager().create_session(
        scenario_path=request.scenario_path,
        negotiator_configs=configs,
        mechanism_type=request.mechanism_type,
        mechanism_params=request.mechanism_params,
        ignore_discount=request.ignore_discount,
        ignore_reserved=request.ignore_reserved,
        normalize=request.normalize,
        auto_save=request.auto_save,
        save_options=request.save_options.model_dump()
        if request.save_options
        else None,
    )

    # Start negotiation in background thread (non-blocking)
    get_manager().start_negotiation_background(
        session_id=session.id,
        share_ufuns=request.share_ufuns,
    )

    # Return session_id immediately
    return {
        "session_id": session.id,
        "status": "running",  # Started in background
    }


@router.get("/{session_id}/stream")
async def stream_negotiation(
    session_id: str, step_delay: float = 0.1, share_ufuns: bool = False
):
    """Stream negotiation progress via Server-Sent Events.

    Events:
    - offer: New offer made (includes utilities)
    - complete: Negotiation finished (includes result)
    - error: Error occurred
    """
    session = get_manager().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    configs = get_manager().get_configs(session_id)
    if configs is None:
        raise HTTPException(status_code=404, detail="Session configs not found")

    async def event_generator():
        try:
            async for event in get_manager().run_session_stream(
                session_id, configs, step_delay=step_delay, share_ufuns=share_ufuns
            ):
                if isinstance(event, SessionInitEvent):
                    # SessionInitEvent - sent at start with all initial data
                    # Convert outcome_space_data to JSON-serializable format
                    osd = event.outcome_space_data
                    osd_data = None
                    if osd is not None:
                        osd_data = {
                            "outcome_utilities": sanitize_utilities(
                                osd.outcome_utilities
                            ),
                            "pareto_utilities": sanitize_utilities(
                                osd.pareto_utilities
                            ),
                            "reserved_values": [
                                sanitize_float(v) for v in osd.reserved_values
                            ]
                            if osd.reserved_values
                            else None,
                            "nash_point": [
                                sanitize_float(v) for v in osd.nash_point.utilities
                            ]
                            if osd.nash_point
                            else None,
                            "kalai_point": [
                                sanitize_float(v) for v in osd.kalai_point.utilities
                            ]
                            if osd.kalai_point
                            else None,
                            "kalai_smorodinsky_point": [
                                sanitize_float(v)
                                for v in osd.kalai_smorodinsky_point.utilities
                            ]
                            if osd.kalai_smorodinsky_point
                            else None,
                            "max_welfare_point": [
                                sanitize_float(v)
                                for v in osd.max_welfare_point.utilities
                            ]
                            if osd.max_welfare_point
                            else None,
                            "total_outcomes": osd.total_outcomes,
                            "sampled": osd.sampled,
                            "sample_size": osd.sample_size,
                        }
                    yield {
                        "event": "init",
                        "data": json.dumps(
                            {
                                "session_id": event.session_id,
                                "scenario_name": event.scenario_name,
                                "scenario_path": event.scenario_path,
                                "negotiator_names": event.negotiator_names,
                                "negotiator_types": event.negotiator_types,
                                "negotiator_colors": event.negotiator_colors,
                                "issue_names": event.issue_names,
                                "n_steps": sanitize_float(event.n_steps)
                                if event.n_steps
                                else None,
                                "time_limit": sanitize_float(event.time_limit)
                                if event.time_limit
                                else None,
                                "n_outcomes": event.n_outcomes,
                                "outcome_space_data": osd_data,
                            }
                        ),
                    }
                elif isinstance(event, OfferEvent):
                    # OfferEvent
                    yield {
                        "event": "offer",
                        "data": json.dumps(
                            {
                                "step": event.step,
                                "proposer": event.proposer,
                                "proposer_index": event.proposer_index,
                                "offer": event.offer_dict,
                                "utilities": event.utilities,
                                "relative_time": event.relative_time,
                            }
                        ),
                    }
                else:
                    # NegotiationSession (final)
                    yield {
                        "event": "complete",
                        "data": json.dumps(
                            {
                                "status": event.status.value,
                                "agreement": event.agreement_dict,
                                "final_utilities": event.final_utilities,
                                "end_reason": event.end_reason,
                                "n_steps": event.current_step,
                                "error": event.error,
                                "optimality_stats": event.optimality_stats,
                            }
                        ),
                    }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.get("/{session_id}/progress")
async def get_negotiation_progress(session_id: str):
    """Get current progress of a running negotiation."""
    session = get_manager().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.id,
        "status": session.status.value,
        "current_step": session.current_step,
        "n_steps": sanitize_float(session.n_steps) if session.n_steps else None,
        "relative_time": session.offers[-1].relative_time if session.offers else 0.0,
    }


@router.post("/{session_id}/cancel")
async def cancel_negotiation(session_id: str):
    """Cancel a running negotiation."""
    success = get_manager().cancel_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cancelled"}


@router.post("/{session_id}/pause")
async def pause_negotiation(session_id: str):
    """Pause a running negotiation."""
    success = get_manager().pause_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "paused"}


@router.post("/{session_id}/resume")
async def resume_negotiation(session_id: str):
    """Resume a paused negotiation."""
    success = get_manager().resume_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "running"}


@router.get("/sessions/list")
async def list_sessions():
    """List all negotiation sessions.

    Returns sessions grouped by status (running, completed, failed).
    """
    sessions = []
    for session in get_manager().sessions.values():
        sessions.append(
            {
                "id": session.id,
                "status": session.status.value,
                "scenario_name": session.scenario_name
                or session.scenario_path.split("/")[-1]
                if session.scenario_path
                else "Unknown",
                "mechanism_type": session.mechanism_type,
                "negotiator_names": session.negotiator_names,
                "current_step": session.current_step,
                "n_steps": sanitize_float(session.n_steps) if session.n_steps else None,
                "relative_time": session.offers[-1].relative_time
                if session.offers
                else 0.0,
                "start_time": session.start_time.isoformat()
                if session.start_time
                else None,
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "agreement": session.agreement_dict is not None,
                "end_reason": session.end_reason,
            }
        )

    # Sort by start time (most recent first), with None at the end
    sessions.sort(key=lambda s: s["start_time"] or "", reverse=True)

    return {"sessions": sessions}


@router.get("/tags")
async def get_all_tags():
    """Get all unique tags used across all negotiations."""
    tags = await asyncio.to_thread(NegotiationStorageService.get_all_tags)
    return {"tags": tags}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    session = get_manager().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "status": session.status.value,
        "scenario_path": session.scenario_path,
        "scenario_name": session.scenario_name or session.scenario_path.split("/")[-1]
        if session.scenario_path
        else "Unknown",
        "mechanism_type": session.mechanism_type,
        "negotiator_names": session.negotiator_names,
        "negotiator_types": session.negotiator_types,
        "negotiator_colors": [info.color for info in session.negotiator_infos]
        if session.negotiator_infos
        else [],
        "current_step": session.current_step,
        "n_steps": sanitize_float(session.n_steps) if session.n_steps else None,
        "relative_time": session.offers[-1].relative_time if session.offers else 0.0,
        "time_limit": sanitize_float(session.time_limit)
        if session.time_limit
        else None,
        "issue_names": session.issue_names,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "agreement": session.agreement_dict,
        "final_utilities": session.final_utilities,
        "end_reason": session.end_reason,
        "error": session.error,
        "optimality_stats": sanitize_nan_values(session.optimality_stats),
        "offers": [
            {
                "step": o.step,
                "proposer": o.proposer,
                "proposer_index": o.proposer_index,
                "offer": o.offer_dict,
                "utilities": o.utilities,
                "relative_time": o.relative_time,
            }
            for o in session.offers
        ],
        "outcome_space_data": {
            "outcome_utilities": sanitize_utilities(
                session.outcome_space_data.outcome_utilities
            ),
            "pareto_utilities": sanitize_utilities(
                session.outcome_space_data.pareto_utilities
            ),
            "reserved_values": [
                sanitize_float(v) for v in session.outcome_space_data.reserved_values
            ]
            if session.outcome_space_data.reserved_values
            else None,
            "nash_point": {
                "outcome": session.outcome_space_data.nash_point.outcome_dict,
                "utilities": session.outcome_space_data.nash_point.utilities,
                "welfare": sum(session.outcome_space_data.nash_point.utilities),
            }
            if session.outcome_space_data.nash_point
            else None,
            "kalai_point": {
                "outcome": session.outcome_space_data.kalai_point.outcome_dict,
                "utilities": session.outcome_space_data.kalai_point.utilities,
                "welfare": sum(session.outcome_space_data.kalai_point.utilities),
            }
            if session.outcome_space_data.kalai_point
            else None,
            "kalai_smorodinsky_point": {
                "outcome": session.outcome_space_data.kalai_smorodinsky_point.outcome_dict,
                "utilities": session.outcome_space_data.kalai_smorodinsky_point.utilities,
                "welfare": sum(
                    session.outcome_space_data.kalai_smorodinsky_point.utilities
                ),
            }
            if session.outcome_space_data.kalai_smorodinsky_point
            else None,
            "max_welfare_point": {
                "outcome": session.outcome_space_data.max_welfare_point.outcome_dict,
                "utilities": session.outcome_space_data.max_welfare_point.utilities,
                "welfare": sum(session.outcome_space_data.max_welfare_point.utilities),
            }
            if session.outcome_space_data.max_welfare_point
            else None,
            "total_outcomes": session.outcome_space_data.total_outcomes,
            "sampled": session.outcome_space_data.sampled,
            "sample_size": session.outcome_space_data.sample_size,
        }
        if session.outcome_space_data
        else None,
    }


# =============================================================================
# Saved Negotiations Endpoints
# =============================================================================


@router.get("/saved/list")
async def list_saved_negotiations(include_archived: bool = False):
    """List all saved negotiations from disk.

    Args:
        include_archived: If True, also include archived negotiations.

    Returns summary info for each saved negotiation.
    """
    negotiations = await asyncio.to_thread(
        NegotiationStorageService.list_saved_negotiations, include_archived
    )
    return {"negotiations": negotiations, "count": len(negotiations)}


@router.get("/saved/{session_id}")
async def get_saved_negotiation(session_id: str):
    """Load a saved negotiation from disk.

    Returns full negotiation data including offers and outcome space.
    """
    session = await asyncio.to_thread(
        NegotiationStorageService.load_negotiation, session_id
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Saved negotiation not found")

    # Convert to response format
    return {
        "id": session.id,
        "status": session.status.value,
        "scenario_path": session.scenario_path,
        "scenario_name": session.scenario_name
        or (
            session.scenario_path.split("/")[-1] if session.scenario_path else "Unknown"
        ),
        "mechanism_type": session.mechanism_type,
        "negotiator_names": session.negotiator_names,
        "negotiator_types": session.negotiator_types,
        "negotiator_colors": [info.color for info in session.negotiator_infos]
        if session.negotiator_infos
        else [],
        "current_step": session.current_step,
        "n_steps": sanitize_float(session.n_steps) if session.n_steps else None,
        "relative_time": session.offers[-1].relative_time if session.offers else 0.0,
        "time_limit": sanitize_float(session.time_limit)
        if session.time_limit
        else None,
        "issue_names": session.issue_names,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "agreement": session.agreement_dict,
        "final_utilities": session.final_utilities,
        "end_reason": session.end_reason,
        "error": session.error,
        "optimality_stats": sanitize_nan_values(session.optimality_stats),
        "offers": [
            {
                "step": o.step,
                "proposer": o.proposer,
                "proposer_index": o.proposer_index,
                "offer": o.offer_dict,
                "utilities": o.utilities,
                "relative_time": o.relative_time,
            }
            for o in session.offers
        ],
        "outcome_space_data": {
            "outcome_utilities": sanitize_utilities(
                session.outcome_space_data.outcome_utilities
            ),
            "pareto_utilities": sanitize_utilities(
                session.outcome_space_data.pareto_utilities
            ),
            "reserved_values": [
                sanitize_float(v) for v in session.outcome_space_data.reserved_values
            ]
            if session.outcome_space_data.reserved_values
            else None,
            "nash_point": {
                "outcome": session.outcome_space_data.nash_point.outcome_dict,
                "utilities": session.outcome_space_data.nash_point.utilities,
                "welfare": sum(session.outcome_space_data.nash_point.utilities),
            }
            if session.outcome_space_data.nash_point
            else None,
            "kalai_point": {
                "outcome": session.outcome_space_data.kalai_point.outcome_dict,
                "utilities": session.outcome_space_data.kalai_point.utilities,
                "welfare": sum(session.outcome_space_data.kalai_point.utilities),
            }
            if session.outcome_space_data.kalai_point
            else None,
            "kalai_smorodinsky_point": {
                "outcome": session.outcome_space_data.kalai_smorodinsky_point.outcome_dict,
                "utilities": session.outcome_space_data.kalai_smorodinsky_point.utilities,
                "welfare": sum(
                    session.outcome_space_data.kalai_smorodinsky_point.utilities
                ),
            }
            if session.outcome_space_data.kalai_smorodinsky_point
            else None,
            "max_welfare_point": {
                "outcome": session.outcome_space_data.max_welfare_point.outcome_dict,
                "utilities": session.outcome_space_data.max_welfare_point.utilities,
                "welfare": sum(session.outcome_space_data.max_welfare_point.utilities),
            }
            if session.outcome_space_data.max_welfare_point
            else None,
            "total_outcomes": session.outcome_space_data.total_outcomes,
            "sampled": session.outcome_space_data.sampled,
            "sample_size": session.outcome_space_data.sample_size,
        }
        if session.outcome_space_data
        else None,
    }


@router.delete("/saved/{session_id}")
async def delete_saved_negotiation(session_id: str):
    """Delete a saved negotiation from disk."""
    success = await asyncio.to_thread(
        NegotiationStorageService.delete_negotiation, session_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Saved negotiation not found")
    return {"status": "deleted"}


@router.delete("/saved")
async def clear_all_saved_negotiations(include_archived: bool = False):
    """Delete all saved negotiations from disk.

    Args:
        include_archived: If True, also delete archived negotiations.
    """
    count = await asyncio.to_thread(
        NegotiationStorageService.clear_all_negotiations, include_archived
    )
    return {"status": "cleared", "count": count}


# =============================================================================
# Archive Endpoints
# =============================================================================


@router.post("/saved/{session_id}/archive")
async def archive_negotiation(session_id: str):
    """Move a negotiation to the archive."""
    success = await asyncio.to_thread(
        NegotiationStorageService.archive_negotiation, session_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return {"status": "archived"}


@router.post("/saved/{session_id}/unarchive")
async def unarchive_negotiation(session_id: str):
    """Restore a negotiation from the archive."""
    success = await asyncio.to_thread(
        NegotiationStorageService.unarchive_negotiation, session_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Archived negotiation not found")
    return {"status": "unarchived"}


# =============================================================================
# Tagging Endpoints
# =============================================================================


@router.put("/saved/{session_id}/tags")
async def update_tags(session_id: str, request: TagsUpdateRequest):
    """Update all tags for a negotiation."""
    success = await asyncio.to_thread(
        NegotiationStorageService.update_tags, session_id, request.tags
    )
    if not success:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return {"status": "updated", "tags": request.tags}


@router.post("/saved/{session_id}/tags")
async def add_tag(session_id: str, request: TagRequest):
    """Add a tag to a negotiation."""
    success = await asyncio.to_thread(
        NegotiationStorageService.add_tag, session_id, request.tag
    )
    if not success:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return {"status": "added", "tag": request.tag}


@router.delete("/saved/{session_id}/tags/{tag}")
async def remove_tag(session_id: str, tag: str):
    """Remove a tag from a negotiation."""
    success = await asyncio.to_thread(
        NegotiationStorageService.remove_tag, session_id, tag
    )
    if not success:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    return {"status": "removed", "tag": tag}


@router.get("/saved/{session_id}/preview/{panel_type}")
async def get_negotiation_preview(session_id: str, panel_type: str):
    """Get cached WebP preview for a specific panel type.

    Panel types: utility2d, timeline, histogram, result

    If the preview doesn't exist, returns 404.
    """
    # Validate panel type
    valid_types = ["utility2d", "timeline", "histogram", "result"]
    if panel_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid panel type. Must be one of: {', '.join(valid_types)}",
        )

    # Get session directory
    session_dir = NegotiationStorageService.get_session_dir(session_id)

    # Find existing preview with any supported format
    from ..services.negotiation_preview_service import _find_existing_preview

    preview_file = _find_existing_preview(session_dir, panel_type)

    # Check if preview exists
    if not preview_file:
        raise HTTPException(
            status_code=404,
            detail=f"Preview '{panel_type}' not found for negotiation '{session_id}'",
        )

    # Determine media type from extension
    ext = preview_file.suffix.lower()
    media_types = {
        ".webp": "image/webp",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
    }
    media_type = media_types.get(ext, "image/webp")

    # Return the image file
    return FileResponse(
        preview_file,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
        },
    )


@router.get("/saved/{session_id}/download")
async def download_negotiation_zip(session_id: str):
    """Download a saved negotiation as a ZIP file.

    The offers will always be exported as CSV for better compatibility,
    even if stored as parquet internally.

    Returns:
        ZIP file containing the complete negotiation directory.
    """
    import shutil
    import tempfile
    import zipfile
    from pathlib import Path

    # Get session directory
    session_dir = NegotiationStorageService.get_session_dir(session_id)

    if not session_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Negotiation '{session_id}' not found"
        )

    # Create temporary ZIP file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        zip_path = Path(tmp.name)

    try:
        # Create ZIP archive manually to control file formats
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add all files from session directory
            for file_path in session_dir.rglob("*"):
                if file_path.is_file():
                    # Get relative path for archive
                    arcname = file_path.relative_to(session_dir.parent)

                    # Special handling for offers: convert parquet to CSV
                    if file_path.name == "offers.parquet":
                        # Convert parquet to CSV in memory
                        try:
                            import pandas as pd

                            df = pd.read_parquet(file_path)

                            # Create CSV in memory
                            csv_buffer = df.to_csv(index=False)

                            # Write CSV to zip with different name
                            csv_arcname = str(arcname).replace(
                                "offers.parquet", "offers.csv"
                            )
                            zipf.writestr(csv_arcname, csv_buffer)
                            continue  # Skip adding the parquet file
                        except Exception as e:
                            print(f"Failed to convert parquet to CSV: {e}")
                            # Fall back to including parquet file

                    # Add file to archive
                    zipf.write(file_path, arcname)

        # Return the ZIP file
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{session_id}.zip",
            headers={"Content-Disposition": f'attachment; filename="{session_id}.zip"'},
        )
    except Exception as e:
        # Clean up temp file on error
        if zip_path.exists():
            zip_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP: {str(e)}")


@router.post("/saved/{session_id}/open-folder")
async def open_negotiation_folder(session_id: str):
    """Open the negotiation folder in the system file explorer.

    Platform-specific behavior:
    - macOS: Uses 'open' command
    - Windows: Uses 'explorer' command
    - Linux: Uses 'xdg-open' command
    """
    import platform
    import subprocess

    # Get session directory
    session_dir = NegotiationStorageService.get_session_dir(session_id)

    if not session_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Negotiation folder not found for session '{session_id}'",
        )

    # Determine the platform-specific command
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(session_dir)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", str(session_dir)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(session_dir)], check=True)
        else:
            raise HTTPException(
                status_code=500, detail=f"Unsupported platform: {system}"
            )

        return {"status": "opened", "path": str(session_dir)}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {str(e)}")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"File explorer command not found for platform: {system}",
        )


@router.post("/load-from-path")
async def load_negotiation_from_path(request: LoadFromPathRequest):
    """Load a negotiation from an external file/folder path.

    This loads the negotiation temporarily for viewing without saving it
    to the app's storage. Use /import for permanent storage.

    Returns full negotiation data that can be displayed in the UI.
    """
    from pathlib import Path

    path = Path(request.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")

    session = await asyncio.to_thread(
        NegotiationStorageService.load_from_path, request.path
    )
    if session is None:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to load negotiation from path: {request.path}",
        )

    # Convert to response format (same as get_saved_negotiation)
    return {
        "id": session.id,
        "status": session.status.value,
        "scenario_path": session.scenario_path,
        "scenario_name": session.scenario_name
        or (
            session.scenario_path.split("/")[-1] if session.scenario_path else "Unknown"
        ),
        "mechanism_type": session.mechanism_type,
        "negotiator_names": session.negotiator_names,
        "negotiator_types": session.negotiator_types,
        "negotiator_colors": [info.color for info in session.negotiator_infos]
        if session.negotiator_infos
        else [],
        "current_step": session.current_step,
        "n_steps": sanitize_float(session.n_steps) if session.n_steps else None,
        "relative_time": session.offers[-1].relative_time if session.offers else 0.0,
        "time_limit": sanitize_float(session.time_limit)
        if session.time_limit
        else None,
        "issue_names": session.issue_names,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "agreement": session.agreement_dict,
        "final_utilities": session.final_utilities,
        "end_reason": session.end_reason,
        "error": session.error,
        "optimality_stats": sanitize_nan_values(session.optimality_stats),
        "offers": [
            {
                "step": o.step,
                "proposer": o.proposer,
                "proposer_index": o.proposer_index,
                "offer": o.offer_dict,
                "utilities": o.utilities,
                "relative_time": o.relative_time,
            }
            for o in session.offers
        ],
        "outcome_space_data": {
            "outcome_utilities": sanitize_utilities(
                session.outcome_space_data.outcome_utilities
            ),
            "pareto_utilities": sanitize_utilities(
                session.outcome_space_data.pareto_utilities
            ),
            "reserved_values": [
                sanitize_float(v) for v in session.outcome_space_data.reserved_values
            ]
            if session.outcome_space_data.reserved_values
            else None,
            "nash_point": {
                "outcome": session.outcome_space_data.nash_point.outcome_dict,
                "utilities": session.outcome_space_data.nash_point.utilities,
                "welfare": sum(session.outcome_space_data.nash_point.utilities),
            }
            if session.outcome_space_data.nash_point
            else None,
            "kalai_point": {
                "outcome": session.outcome_space_data.kalai_point.outcome_dict,
                "utilities": session.outcome_space_data.kalai_point.utilities,
                "welfare": sum(session.outcome_space_data.kalai_point.utilities),
            }
            if session.outcome_space_data.kalai_point
            else None,
            "kalai_smorodinsky_point": {
                "outcome": session.outcome_space_data.kalai_smorodinsky_point.outcome_dict,
                "utilities": session.outcome_space_data.kalai_smorodinsky_point.utilities,
                "welfare": sum(
                    session.outcome_space_data.kalai_smorodinsky_point.utilities
                ),
            }
            if session.outcome_space_data.kalai_smorodinsky_point
            else None,
            "max_welfare_point": {
                "outcome": session.outcome_space_data.max_welfare_point.outcome_dict,
                "utilities": session.outcome_space_data.max_welfare_point.utilities,
                "welfare": sum(session.outcome_space_data.max_welfare_point.utilities),
            }
            if session.outcome_space_data.max_welfare_point
            else None,
            "total_outcomes": session.outcome_space_data.total_outcomes,
            "sampled": session.outcome_space_data.sampled,
            "sample_size": session.outcome_space_data.sample_size,
        }
        if session.outcome_space_data
        else None,
        "source_path": request.path,  # Include source path for reference
        "is_temporary": True,  # Flag indicating this is not saved to app storage
    }


@router.post("/import")
async def import_negotiation(request: ImportNegotiationRequest):
    """Import a negotiation from an external file/folder path.

    This loads the negotiation, saves it to the app's storage directory
    (~/negmas/app/negotiations) with import metadata, and returns the new session ID.

    The imported negotiation can then be viewed, tagged, and managed like
    any other saved negotiation.
    """
    from pathlib import Path

    path = Path(request.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")

    session = await asyncio.to_thread(
        NegotiationStorageService.import_negotiation,
        request.path,
        request.tags,
    )
    if session is None:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import negotiation from path: {request.path}",
        )

    return {
        "session_id": session.id,
        "status": "imported",
        "source_path": request.path,
        "message": f"Negotiation imported successfully as '{session.id}'",
    }


@router.post("/saved/{session_id}/rerun")
async def rerun_negotiation(session_id: str):
    """Rerun a saved negotiation with the same configuration.

    Creates a new negotiation session using the scenario, negotiators,
    and mechanism parameters from the saved negotiation.

    The negotiation runs in background and continues even if client disconnects.

    Returns session ID for the new negotiation.
    """
    # Load the saved negotiation metadata
    session_dir = NegotiationStorageService.get_session_dir(session_id)
    metadata_path = session_dir / "metadata.json"

    if not metadata_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Saved negotiation not found: {session_id}",
        )

    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read negotiation metadata: {str(e)}",
        )

    # Extract negotiator configs
    negotiator_configs_data = metadata.get("negotiator_configs")
    if not negotiator_configs_data:
        raise HTTPException(
            status_code=400,
            detail="Cannot rerun: negotiation was saved without negotiator configurations",
        )

    # Convert to internal NegotiatorConfig objects
    configs = [
        NegotiatorConfig(
            type_name=c["type_name"],
            name=c.get("name"),
            params=c.get("params", {}),
            time_limit=c.get("time_limit"),
            n_steps=c.get("n_steps"),
        )
        for c in negotiator_configs_data
    ]

    # Extract mechanism parameters from metadata
    # For backwards compatibility, default to empty dict if not present
    mechanism_params = {}
    if "n_steps" in metadata and metadata["n_steps"] is not None:
        mechanism_params["n_steps"] = metadata["n_steps"]
    if "time_limit" in metadata and metadata["time_limit"] is not None:
        mechanism_params["time_limit"] = metadata["time_limit"]

    # Create new session with same configuration
    new_session = get_manager().create_session(
        scenario_path=metadata["scenario_path"],
        negotiator_configs=configs,
        mechanism_type=metadata.get("mechanism_type", "SAOMechanism"),
        mechanism_params=mechanism_params,
        ignore_discount=False,  # Use defaults for these
        ignore_reserved=False,
        normalize=False,
        auto_save=True,
    )

    # Run negotiation in background task (continues even if client disconnects)
    async def run_negotiation_task():
        async for event in get_manager().run_session_stream(
            new_session.id, configs, step_delay=0.0, share_ufuns=False
        ):
            pass  # Just consume events, negotiation runs in background

    # Start background task
    import asyncio

    asyncio.create_task(run_negotiation_task())

    return {
        "session_id": new_session.id,
        "original_session_id": session_id,
        "status": "running",
        "stream_url": f"/api/negotiation/{new_session.id}/stream?step_delay=0.1&share_ufuns=false",
    }
