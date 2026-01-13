"""Genius Bridge API endpoints."""

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from negmas.genius import (
    genius_bridge_is_installed,
    genius_bridge_is_running,
    init_genius_bridge,
)
from negmas.genius.bridge import GeniusBridge

router = APIRouter(prefix="/api/genius", tags=["genius"])

DEFAULT_PORT = 25337


class BridgeStatusResponse(BaseModel):
    """Response model for bridge status."""

    installed: bool
    running: bool
    port: int


class BridgeStartRequest(BaseModel):
    """Request model to start the bridge."""

    port: int = DEFAULT_PORT
    timeout: float = 0
    debug: bool = False


class BridgeStartResponse(BaseModel):
    """Response model for bridge start."""

    success: bool
    port: int
    message: str


class BridgeStopResponse(BaseModel):
    """Response model for bridge stop."""

    success: bool
    message: str


@router.get("/status", response_model=BridgeStatusResponse)
async def get_bridge_status(port: int = DEFAULT_PORT) -> BridgeStatusResponse:
    """Get the current status of the Genius Bridge."""
    installed = await asyncio.to_thread(genius_bridge_is_installed)
    running = await asyncio.to_thread(genius_bridge_is_running, port)
    return BridgeStatusResponse(
        installed=installed,
        running=running,
        port=port,
    )


@router.post("/start", response_model=BridgeStartResponse)
async def start_bridge(request: BridgeStartRequest) -> BridgeStartResponse:
    """Start the Genius Bridge.

    Returns:
        - port > 0: Bridge started successfully on this port
        - port = -1: Bridge already running on this port
        - port = 0: Failed to start bridge
    """
    result = await asyncio.to_thread(
        init_genius_bridge,
        port=request.port,
        timeout=request.timeout,
        debug=request.debug,
    )

    if result > 0:
        return BridgeStartResponse(
            success=True,
            port=result,
            message=f"Bridge started on port {result}",
        )
    elif result == -1:
        return BridgeStartResponse(
            success=True,
            port=request.port,
            message=f"Bridge already running on port {request.port}",
        )
    else:
        return BridgeStartResponse(
            success=False,
            port=0,
            message="Failed to start bridge. Check if Java is installed.",
        )


@router.post("/stop", response_model=BridgeStopResponse)
async def stop_bridge(port: int = DEFAULT_PORT) -> BridgeStopResponse:
    """Stop the Genius Bridge."""
    running = await asyncio.to_thread(genius_bridge_is_running, port)
    if not running:
        return BridgeStopResponse(
            success=True,
            message="Bridge is not running",
        )

    success = await asyncio.to_thread(GeniusBridge.kill, port=port, wait=True)
    if success:
        return BridgeStopResponse(
            success=True,
            message=f"Bridge stopped on port {port}",
        )
    else:
        # Try forced kill
        success = await asyncio.to_thread(
            GeniusBridge.kill_forced, port=port, wait=True
        )
        if success:
            return BridgeStopResponse(
                success=True,
                message=f"Bridge forcefully stopped on port {port}",
            )
        return BridgeStopResponse(
            success=False,
            message="Failed to stop bridge",
        )


@router.post("/restart", response_model=BridgeStartResponse)
async def restart_bridge(request: BridgeStartRequest) -> BridgeStartResponse:
    """Restart the Genius Bridge."""
    success = await asyncio.to_thread(
        GeniusBridge.restart,
        port=request.port,
        timeout=request.timeout,
        debug=request.debug,
    )

    if success:
        return BridgeStartResponse(
            success=True,
            port=request.port,
            message=f"Bridge restarted on port {request.port}",
        )
    else:
        return BridgeStartResponse(
            success=False,
            port=0,
            message="Failed to restart bridge",
        )
