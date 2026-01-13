"""Settings API router for NegMAS App."""

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from ..models.settings import (
    AppSettings,
    CustomNegotiatorSource,
    GeneralSettings,
    GeniusBridgeSettings,
    NegotiationSettings,
    NegotiatorSourcesSettings,
    PathSettings,
    # Presets
    NegotiatorPreset,
    ScenarioPreset,
    NegotiatorsPreset,
    ParametersPreset,
    DisplayPreset,
    FullSessionPreset,
)
from ..services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Path to JSON schema
SCHEMA_PATH = Path.home() / "negmas" / "app" / "settings" / "schema.json"


@router.get("/schema")
async def get_settings_schema() -> dict[str, Any]:
    """Get JSON schema for settings validation and documentation."""
    if SCHEMA_PATH.exists():
        try:
            return json.loads(SCHEMA_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"error": "Schema file not found"}


@router.get("")
async def get_all_settings() -> dict[str, Any]:
    """Get all application settings."""
    settings = await asyncio.to_thread(SettingsService.load_all)
    return asdict(settings)


@router.put("")
async def update_all_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Update all application settings."""
    # Filter out unknown keys from each section to avoid TypeError
    general_data = settings.get("general", {})
    general_keys = {
        "dark_mode",
        "color_blind_mode",
        "save_negotiations",
        "cache_scenario_stats",
    }
    general_filtered = {k: v for k, v in general_data.items() if k in general_keys}

    negotiation_data = settings.get("negotiation", {})
    negotiation_keys = {
        "default_max_steps",
        "default_step_delay_ms",
        "default_time_limit",
    }
    negotiation_filtered = {
        k: v for k, v in negotiation_data.items() if k in negotiation_keys
    }

    genius_bridge_data = settings.get("genius_bridge", {})
    genius_bridge_keys = {"auto_start", "java_path", "port"}
    genius_bridge_filtered = {
        k: v for k, v in genius_bridge_data.items() if k in genius_bridge_keys
    }

    paths_data = settings.get("paths", {})
    paths_keys = {"scenario_paths"}
    paths_filtered = {k: v for k, v in paths_data.items() if k in paths_keys}

    app_settings = AppSettings(
        general=GeneralSettings(**general_filtered),
        negotiation=NegotiationSettings(**negotiation_filtered),
        genius_bridge=GeniusBridgeSettings(**genius_bridge_filtered),
        paths=PathSettings(**paths_filtered),
    )
    await asyncio.to_thread(SettingsService.save_all, app_settings)
    return asdict(app_settings)


# Individual settings endpoints


@router.get("/general")
async def get_general_settings() -> dict[str, Any]:
    """Get general settings."""
    settings = await asyncio.to_thread(SettingsService.load_general)
    return asdict(settings)


@router.put("/general")
async def update_general_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Update general settings."""
    general = GeneralSettings(**settings)
    await asyncio.to_thread(SettingsService.save_general, general)
    return asdict(general)


@router.get("/negotiation")
async def get_negotiation_settings() -> dict[str, Any]:
    """Get negotiation settings."""
    settings = await asyncio.to_thread(SettingsService.load_negotiation)
    return asdict(settings)


@router.put("/negotiation")
async def update_negotiation_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Update negotiation settings."""
    negotiation = NegotiationSettings(**settings)
    await asyncio.to_thread(SettingsService.save_negotiation, negotiation)
    return asdict(negotiation)


@router.get("/genius_bridge")
async def get_genius_bridge_settings() -> dict[str, Any]:
    """Get genius bridge settings."""
    settings = await asyncio.to_thread(SettingsService.load_genius_bridge)
    return asdict(settings)


@router.put("/genius_bridge")
async def update_genius_bridge_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Update genius bridge settings."""
    genius_bridge = GeniusBridgeSettings(**settings)
    await asyncio.to_thread(SettingsService.save_genius_bridge, genius_bridge)
    return asdict(genius_bridge)


@router.get("/paths")
async def get_path_settings() -> dict[str, Any]:
    """Get path settings."""
    settings = await asyncio.to_thread(SettingsService.load_paths)
    return asdict(settings)


@router.put("/paths")
async def update_path_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Update path settings."""
    paths = PathSettings(**settings)
    await asyncio.to_thread(SettingsService.save_paths, paths)
    return asdict(paths)


@router.get("/negotiator_sources")
async def get_negotiator_sources_settings() -> dict[str, Any]:
    """Get negotiator sources settings."""
    settings = await asyncio.to_thread(SettingsService.load_negotiator_sources)
    return asdict(settings)


@router.put("/negotiator_sources")
async def update_negotiator_sources_settings(
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Update negotiator sources settings."""
    # Parse custom_sources if present
    custom_sources = []
    for src in settings.get("custom_sources", []):
        custom_sources.append(CustomNegotiatorSource(**src))

    sources = NegotiatorSourcesSettings(
        custom_sources=custom_sources,
        disabled_sources=settings.get("disabled_sources", []),
    )
    await asyncio.to_thread(SettingsService.save_negotiator_sources, sources)
    return asdict(sources)


# =============================================================================
# Preset Endpoints
# =============================================================================


# --- Scenario Presets ---


@router.get("/presets/scenarios")
async def get_scenario_presets() -> dict[str, Any]:
    """Get all scenario presets."""
    presets = await asyncio.to_thread(SettingsService.load_scenario_presets)
    return {"presets": [asdict(p) for p in presets]}


@router.post("/presets/scenarios")
async def save_scenario_preset(data: dict[str, Any]) -> dict[str, Any]:
    """Save a scenario preset."""
    preset = ScenarioPreset(
        name=data["name"],
        scenario_path=data["scenario_path"],
        scenario_name=data["scenario_name"],
    )
    await asyncio.to_thread(SettingsService.save_scenario_preset, preset)
    return asdict(preset)


@router.delete("/presets/scenarios/{name}")
async def delete_scenario_preset(name: str) -> dict[str, Any]:
    """Delete a scenario preset."""
    success = await asyncio.to_thread(SettingsService.delete_scenario_preset, name)
    return {"success": success}


# --- Negotiators Presets ---


@router.get("/presets/negotiators")
async def get_negotiators_presets() -> dict[str, Any]:
    """Get all negotiators presets."""
    presets = await asyncio.to_thread(SettingsService.load_negotiators_presets)
    return {"presets": [asdict(p) for p in presets]}


@router.post("/presets/negotiators")
async def save_negotiators_preset(data: dict[str, Any]) -> dict[str, Any]:
    """Save a negotiators preset."""
    negotiators = [NegotiatorPreset(**n) for n in data.get("negotiators", [])]
    preset = NegotiatorsPreset(
        name=data["name"],
        negotiators=negotiators,
    )
    await asyncio.to_thread(SettingsService.save_negotiators_preset, preset)
    return asdict(preset)


@router.delete("/presets/negotiators/{name}")
async def delete_negotiators_preset(name: str) -> dict[str, Any]:
    """Delete a negotiators preset."""
    success = await asyncio.to_thread(SettingsService.delete_negotiators_preset, name)
    return {"success": success}


# --- Parameters Presets ---


@router.get("/presets/parameters")
async def get_parameters_presets() -> dict[str, Any]:
    """Get all parameters presets."""
    presets = await asyncio.to_thread(SettingsService.load_parameters_presets)
    return {"presets": [asdict(p) for p in presets]}


@router.post("/presets/parameters")
async def save_parameters_preset(data: dict[str, Any]) -> dict[str, Any]:
    """Save a parameters preset."""
    preset = ParametersPreset(
        name=data["name"],
        mechanism_type=data.get("mechanism_type", "SAOMechanism"),
        mechanism_params=data.get("mechanism_params", {}),
        share_ufuns=data.get("share_ufuns", False),
    )
    await asyncio.to_thread(SettingsService.save_parameters_preset, preset)
    return asdict(preset)


@router.delete("/presets/parameters/{name}")
async def delete_parameters_preset(name: str) -> dict[str, Any]:
    """Delete a parameters preset."""
    success = await asyncio.to_thread(SettingsService.delete_parameters_preset, name)
    return {"success": success}


# --- Display Presets ---


@router.get("/presets/display")
async def get_display_presets() -> dict[str, Any]:
    """Get all display presets."""
    presets = await asyncio.to_thread(SettingsService.load_display_presets)
    return {"presets": [asdict(p) for p in presets]}


@router.post("/presets/display")
async def save_display_preset(data: dict[str, Any]) -> dict[str, Any]:
    """Save a display preset."""
    preset = DisplayPreset(
        name=data["name"],
        mode=data.get("mode", "realtime"),
        step_delay=data.get("step_delay", 100),
        show_plot=data.get("show_plot", True),
        show_offers=data.get("show_offers", True),
    )
    await asyncio.to_thread(SettingsService.save_display_preset, preset)
    return asdict(preset)


@router.delete("/presets/display/{name}")
async def delete_display_preset(name: str) -> dict[str, Any]:
    """Delete a display preset."""
    success = await asyncio.to_thread(SettingsService.delete_display_preset, name)
    return {"success": success}


# --- Full Session Presets ---


@router.get("/presets/sessions")
async def get_session_presets() -> dict[str, Any]:
    """Get all full session presets."""
    presets = await asyncio.to_thread(SettingsService.load_session_presets)
    return {"presets": [asdict(p) for p in presets]}


@router.post("/presets/sessions")
async def save_session_preset(data: dict[str, Any]) -> dict[str, Any]:
    """Save a full session preset."""
    negotiators = [NegotiatorPreset(**n) for n in data.get("negotiators", [])]
    preset = FullSessionPreset(
        name=data["name"],
        scenario_path=data["scenario_path"],
        scenario_name=data["scenario_name"],
        negotiators=negotiators,
        mechanism_type=data.get("mechanism_type", "SAOMechanism"),
        mechanism_params=data.get("mechanism_params", {}),
        share_ufuns=data.get("share_ufuns", False),
        mode=data.get("mode", "realtime"),
        step_delay=data.get("step_delay", 100),
        show_plot=data.get("show_plot", True),
        show_offers=data.get("show_offers", True),
    )
    await asyncio.to_thread(SettingsService.save_session_preset, preset)
    return asdict(preset)


@router.delete("/presets/sessions/{name}")
async def delete_session_preset(name: str) -> dict[str, Any]:
    """Delete a full session preset."""
    success = await asyncio.to_thread(SettingsService.delete_session_preset, name)
    return {"success": success}


# --- Recent Sessions ---


@router.get("/presets/recent")
async def get_recent_sessions() -> dict[str, Any]:
    """Get recent session configurations."""
    sessions = await asyncio.to_thread(SettingsService.load_recent_sessions)
    return {"sessions": [asdict(s) for s in sessions]}


@router.post("/presets/recent")
async def add_recent_session(data: dict[str, Any]) -> dict[str, Any]:
    """Add a session to recent history."""
    negotiators = [NegotiatorPreset(**n) for n in data.get("negotiators", [])]
    session = FullSessionPreset(
        name=data.get("name", f"{data['scenario_name']}"),
        scenario_path=data["scenario_path"],
        scenario_name=data["scenario_name"],
        negotiators=negotiators,
        mechanism_type=data.get("mechanism_type", "SAOMechanism"),
        mechanism_params=data.get("mechanism_params", {}),
        share_ufuns=data.get("share_ufuns", False),
        mode=data.get("mode", "realtime"),
        step_delay=data.get("step_delay", 100),
        show_plot=data.get("show_plot", True),
        show_offers=data.get("show_offers", True),
    )
    await asyncio.to_thread(SettingsService.add_recent_session, session)
    return {"success": True}


@router.delete("/presets/recent")
async def clear_recent_sessions() -> dict[str, Any]:
    """Clear all recent sessions."""
    await asyncio.to_thread(SettingsService.clear_recent_sessions)
    return {"success": True}
