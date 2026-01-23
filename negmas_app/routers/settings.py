"""Settings API router for NegMAS App."""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response

from ..models.settings import (
    AppSettings,
    CustomNegotiatorSource,
    GeneralSettings,
    GeniusBridgeSettings,
    NegotiationSettings,
    NegotiatorSourcesSettings,
    PathSettings,
    PerformanceSettings,
    # Presets
    NegotiatorPreset,
    ScenarioPreset,
    NegotiatorsPreset,
    ParametersPreset,
    DisplayPreset,
    FullSessionPreset,
    TournamentPreset,
    # Layout state
    LayoutState,
    LayoutConfig,
    ZoneConfig,
    ZoneSizes,
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

    performance_data = settings.get("performance", {})
    performance_keys = {
        "max_outcomes_run",
        "max_outcomes_stats",
        "max_outcomes_plots",
        "max_outcomes_pareto",
        "max_outcomes_rationality",
    }
    performance_filtered = {
        k: v for k, v in performance_data.items() if k in performance_keys
    }

    app_settings = AppSettings(
        general=GeneralSettings(**general_filtered),
        negotiation=NegotiationSettings(**negotiation_filtered),
        genius_bridge=GeniusBridgeSettings(**genius_bridge_filtered),
        paths=PathSettings(**paths_filtered),
        performance=PerformanceSettings(**performance_filtered),
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


@router.get("/performance")
async def get_performance_settings() -> dict[str, Any]:
    """Get performance settings."""
    settings = await asyncio.to_thread(SettingsService.load_performance)
    return asdict(settings)


@router.put("/performance")
async def update_performance_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Update performance settings."""
    # Convert 0 to None for "no limit" semantics
    for key in [
        "max_outcomes_run",
        "max_outcomes_stats",
        "max_outcomes_plots",
        "max_outcomes_pareto",
        "max_outcomes_rationality",
    ]:
        if key in settings and settings[key] == 0:
            settings[key] = None
    performance = PerformanceSettings(**settings)
    await asyncio.to_thread(SettingsService.save_performance, performance)
    return asdict(performance)


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
        panels=data.get("panels", {}),
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
        panels=data.get("panels", {}),
    )
    await asyncio.to_thread(SettingsService.add_recent_session, session)
    return {"success": True}


@router.delete("/presets/recent")
async def clear_recent_sessions() -> dict[str, Any]:
    """Clear all recent sessions."""
    await asyncio.to_thread(SettingsService.clear_recent_sessions)
    return {"success": True}


# --- Tournament Presets ---


@router.get("/presets/tournaments")
async def get_tournament_presets() -> dict[str, Any]:
    """Get all tournament presets."""
    presets = await asyncio.to_thread(SettingsService.load_tournament_presets)
    return {"presets": [asdict(p) for p in presets]}


@router.post("/presets/tournaments")
async def save_tournament_preset(data: dict[str, Any]) -> dict[str, Any]:
    """Save a tournament preset."""
    preset = TournamentPreset(
        name=data["name"],
        scenario_paths=data.get("scenario_paths", []),
        competitor_types=data.get("competitor_types", []),
        competitor_configs=data.get("competitor_configs", {}),
        n_repetitions=data.get("n_repetitions", 1),
        rotate_ufuns=data.get("rotate_ufuns", True),
        self_play=data.get("self_play", True),
        mechanism_type=data.get("mechanism_type", "SAOMechanism"),
        n_steps=data.get("n_steps"),
        n_steps_min=data.get("n_steps_min"),
        n_steps_max=data.get("n_steps_max"),
        time_limit=data.get("time_limit"),
        time_limit_min=data.get("time_limit_min"),
        time_limit_max=data.get("time_limit_max"),
        step_time_limit=data.get("step_time_limit"),
        negotiator_time_limit=data.get("negotiator_time_limit"),
        hidden_time_limit=data.get("hidden_time_limit"),
        pend=data.get("pend"),
        pend_per_second=data.get("pend_per_second"),
        final_score_metric=data.get("final_score_metric", "advantage"),
        final_score_stat=data.get("final_score_stat", "mean"),
        randomize_runs=data.get("randomize_runs", False),
        sort_runs=data.get("sort_runs", True),
        id_reveals_type=data.get("id_reveals_type", False),
        name_reveals_type=data.get("name_reveals_type", True),
        mask_scenario_names=data.get("mask_scenario_names", False),
        only_failures_on_self_play=data.get("only_failures_on_self_play", False),
        save_stats=data.get("save_stats", True),
        save_scenario_figs=data.get("save_scenario_figs", False),
        save_every=data.get("save_every", 0),
    )
    await asyncio.to_thread(SettingsService.save_tournament_preset, preset)
    return asdict(preset)


@router.delete("/presets/tournaments/{name}")
async def delete_tournament_preset(name: str) -> dict[str, Any]:
    """Delete a tournament preset."""
    success = await asyncio.to_thread(SettingsService.delete_tournament_preset, name)
    return {"success": success}


# =============================================================================
# Layout State Endpoints
# =============================================================================


@router.get("/layout")
async def get_layout_state() -> dict[str, Any]:
    """Get the current layout state."""
    state = await asyncio.to_thread(SettingsService.load_layout_state)
    # Convert to dict for JSON serialization
    result = {
        "version": state.version,
        "activeLayoutId": state.activeLayoutId,
        "customLayouts": [],
        "panelCollapsed": state.panelCollapsed,
        "leftColumnWidth": state.leftColumnWidth,
    }
    for layout in state.customLayouts:
        layout_dict = {
            "id": layout.id,
            "name": layout.name,
            "builtIn": layout.builtIn,
            "topRowMode": layout.topRowMode,
            "zones": {},
            "zoneSizes": asdict(layout.zoneSizes)
            if hasattr(layout.zoneSizes, "__dataclass_fields__")
            else layout.zoneSizes,
        }
        for zone_id, zone in layout.zones.items():
            if hasattr(zone, "__dataclass_fields__"):
                layout_dict["zones"][zone_id] = asdict(zone)
            else:
                layout_dict["zones"][zone_id] = zone
        result["customLayouts"].append(layout_dict)
    return result


@router.put("/layout")
async def update_layout_state(data: dict[str, Any]) -> dict[str, Any]:
    """Update the layout state."""
    # Parse custom layouts
    custom_layouts = []
    for layout_data in data.get("customLayouts", []):
        zones = {}
        for zone_id, zone_data in layout_data.get("zones", {}).items():
            zones[zone_id] = (
                ZoneConfig(**zone_data) if isinstance(zone_data, dict) else zone_data
            )
        zone_sizes_data = layout_data.get("zoneSizes", {})
        zone_sizes = ZoneSizes(**zone_sizes_data) if zone_sizes_data else ZoneSizes()
        custom_layouts.append(
            LayoutConfig(
                id=layout_data.get("id", ""),
                name=layout_data.get("name", ""),
                builtIn=layout_data.get("builtIn", False),
                topRowMode=layout_data.get("topRowMode", "two-column"),
                zones=zones,
                zoneSizes=zone_sizes,
            )
        )

    state = LayoutState(
        version=data.get("version", 1),
        activeLayoutId=data.get("activeLayoutId", "default"),
        customLayouts=custom_layouts,
        panelCollapsed=data.get("panelCollapsed", {}),
        leftColumnWidth=data.get("leftColumnWidth"),
    )
    await asyncio.to_thread(SettingsService.save_layout_state, state)
    return {"success": True}


# =============================================================================
# Export/Import Endpoints
# =============================================================================


@router.get("/export")
async def export_settings() -> Response:
    """Export all settings and presets as a ZIP file."""
    zip_data = await asyncio.to_thread(SettingsService.export_settings)

    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"negmas_settings_{timestamp}.zip"

    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import")
async def import_settings(file: UploadFile = File(...)) -> dict[str, Any]:
    """Import settings and presets from a ZIP file."""
    if not file.filename or not file.filename.endswith(".zip"):
        return {"status": "error", "message": "Please upload a ZIP file"}

    zip_data = await file.read()
    result = await asyncio.to_thread(SettingsService.import_settings, zip_data)
    return result
