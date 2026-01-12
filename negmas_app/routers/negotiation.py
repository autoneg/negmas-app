"""Negotiation API endpoints with SSE streaming."""

import json
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..models import NegotiatorConfig, OfferEvent, SessionInitEvent
from ..services import SessionManager

router = APIRouter(prefix="/api/negotiation", tags=["negotiation"])

# Shared session manager
_manager = SessionManager()


class NegotiatorConfigRequest(BaseModel):
    """Request model for negotiator configuration."""

    type_name: str
    name: str | None = None
    params: dict = {}


class StartNegotiationRequest(BaseModel):
    """Request model to start a negotiation."""

    scenario_path: str
    negotiators: list[NegotiatorConfigRequest]
    mechanism_type: str = "SAOMechanism"  # Class name of mechanism
    mechanism_params: dict = {}  # All mechanism parameters
    n_steps: int = 100  # Kept for backwards compatibility
    time_limit: float | None = None  # Kept for backwards compatibility
    step_delay: float = 0.1
    share_ufuns: bool = False


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
        )
        for n in request.negotiators
    ]

    # Merge mechanism_params with backwards-compatible n_steps/time_limit
    mechanism_params = request.mechanism_params.copy()
    # Only use top-level n_steps/time_limit if not in mechanism_params
    if "n_steps" not in mechanism_params:
        mechanism_params["n_steps"] = request.n_steps
    if "time_limit" not in mechanism_params:
        mechanism_params["time_limit"] = request.time_limit

    # Create session
    session = _manager.create_session(
        scenario_path=request.scenario_path,
        negotiator_configs=configs,
        mechanism_type=request.mechanism_type,
        mechanism_params=mechanism_params,
    )

    return {
        "session_id": session.id,
        "status": session.status.value,
        "stream_url": f"/api/negotiation/{session.id}/stream?step_delay={request.step_delay}&share_ufuns={str(request.share_ufuns).lower()}",
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
    session = _manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    configs = _manager.get_configs(session_id)
    if configs is None:
        raise HTTPException(status_code=404, detail="Session configs not found")

    async def event_generator():
        try:
            async for event in _manager.run_session_stream(
                session_id, configs, step_delay=step_delay, share_ufuns=share_ufuns
            ):
                if isinstance(event, SessionInitEvent):
                    # SessionInitEvent - sent at start with all initial data
                    # Convert outcome_space_data to JSON-serializable format
                    osd = event.outcome_space_data
                    osd_data = None
                    if osd is not None:
                        osd_data = {
                            "outcome_utilities": osd.outcome_utilities,
                            "pareto_utilities": osd.pareto_utilities,
                            "nash_point": osd.nash_point.utilities
                            if osd.nash_point
                            else None,
                            "kalai_point": osd.kalai_point.utilities
                            if osd.kalai_point
                            else None,
                            "kalai_smorodinsky_point": osd.kalai_smorodinsky_point.utilities
                            if osd.kalai_smorodinsky_point
                            else None,
                            "max_welfare_point": osd.max_welfare_point.utilities
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
                                "negotiator_names": event.negotiator_names,
                                "negotiator_types": event.negotiator_types,
                                "negotiator_colors": event.negotiator_colors,
                                "issue_names": event.issue_names,
                                "n_steps": event.n_steps,
                                "time_limit": event.time_limit,
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
                            }
                        ),
                    }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.post("/{session_id}/cancel")
async def cancel_negotiation(session_id: str):
    """Cancel a running negotiation."""
    success = _manager.cancel_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cancelled"}


@router.post("/{session_id}/pause")
async def pause_negotiation(session_id: str):
    """Pause a running negotiation."""
    success = _manager.pause_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "paused"}


@router.post("/{session_id}/resume")
async def resume_negotiation(session_id: str):
    """Resume a paused negotiation."""
    success = _manager.resume_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "running"}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    session = _manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "status": session.status.value,
        "scenario_path": session.scenario_path,
        "mechanism_type": session.mechanism_type,
        "negotiator_names": session.negotiator_names,
        "current_step": session.current_step,
        "n_steps": session.n_steps,
        "agreement": session.agreement_dict,
        "final_utilities": session.final_utilities,
        "end_reason": session.end_reason,
        "error": session.error,
    }
