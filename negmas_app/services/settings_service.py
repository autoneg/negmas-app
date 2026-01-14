"""Settings service for persisting app settings to ~/negmas/app/settings/."""

import io
import json
import zipfile
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path

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
    # Layout state
    LayoutState,
    LayoutConfig,
    ZoneConfig,
    ZoneSizes,
)

# Settings directory path
SETTINGS_DIR = Path.home() / "negmas" / "app" / "settings"

# Individual settings files
GENERAL_SETTINGS_FILE = SETTINGS_DIR / "general.json"
NEGOTIATION_SETTINGS_FILE = SETTINGS_DIR / "negotiation.json"
GENIUS_BRIDGE_SETTINGS_FILE = SETTINGS_DIR / "genius_bridge.json"
NEGOTIATOR_SOURCES_SETTINGS_FILE = SETTINGS_DIR / "negotiator_sources.json"
PATHS_SETTINGS_FILE = SETTINGS_DIR / "paths.json"

# Presets directories
PRESETS_DIR = SETTINGS_DIR / "presets"
SCENARIO_PRESETS_FILE = PRESETS_DIR / "scenarios.json"
NEGOTIATORS_PRESETS_FILE = PRESETS_DIR / "negotiators.json"
PARAMETERS_PRESETS_FILE = PRESETS_DIR / "parameters.json"
DISPLAY_PRESETS_FILE = PRESETS_DIR / "display.json"
SESSION_PRESETS_FILE = PRESETS_DIR / "sessions.json"
RECENT_SESSIONS_FILE = PRESETS_DIR / "recent.json"

# Max recent sessions to keep
MAX_RECENT_SESSIONS = 10


def _ensure_settings_dir() -> None:
    """Ensure the settings directory exists."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_presets_dir() -> None:
    """Ensure the presets directory exists."""
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict | None:
    """Load JSON from a file, return None if file doesn't exist."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: dict | list) -> None:
    """Save dict or list as JSON to a file."""
    _ensure_settings_dir()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _dataclass_from_dict[T](cls: type[T], data: dict | None) -> T:
    """Create a dataclass instance from a dict, using defaults for missing fields."""
    if data is None:
        return cls()  # type: ignore[return-value]

    # Only use keys that are valid fields
    valid_keys = {f.name for f in fields(cls)}  # type: ignore[arg-type]
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    return cls(**filtered)  # type: ignore[return-value]


class SettingsService:
    """Service for loading and saving application settings."""

    @staticmethod
    def load_general() -> GeneralSettings:
        """Load general settings."""
        data = _load_json(GENERAL_SETTINGS_FILE)
        return _dataclass_from_dict(GeneralSettings, data)

    @staticmethod
    def save_general(settings: GeneralSettings) -> None:
        """Save general settings."""
        _save_json(GENERAL_SETTINGS_FILE, asdict(settings))

    @staticmethod
    def load_negotiation() -> NegotiationSettings:
        """Load negotiation settings."""
        data = _load_json(NEGOTIATION_SETTINGS_FILE)
        return _dataclass_from_dict(NegotiationSettings, data)

    @staticmethod
    def save_negotiation(settings: NegotiationSettings) -> None:
        """Save negotiation settings."""
        _save_json(NEGOTIATION_SETTINGS_FILE, asdict(settings))

    @staticmethod
    def load_genius_bridge() -> GeniusBridgeSettings:
        """Load genius bridge settings."""
        data = _load_json(GENIUS_BRIDGE_SETTINGS_FILE)
        return _dataclass_from_dict(GeniusBridgeSettings, data)

    @staticmethod
    def save_genius_bridge(settings: GeniusBridgeSettings) -> None:
        """Save genius bridge settings."""
        _save_json(GENIUS_BRIDGE_SETTINGS_FILE, asdict(settings))

    @staticmethod
    def load_paths() -> PathSettings:
        """Load path settings."""
        data = _load_json(PATHS_SETTINGS_FILE)
        return _dataclass_from_dict(PathSettings, data)

    @staticmethod
    def save_paths(settings: PathSettings) -> None:
        """Save path settings."""
        _save_json(PATHS_SETTINGS_FILE, asdict(settings))

    @staticmethod
    def load_negotiator_sources() -> NegotiatorSourcesSettings:
        """Load negotiator sources settings."""
        data = _load_json(NEGOTIATOR_SOURCES_SETTINGS_FILE)
        if data is None:
            return NegotiatorSourcesSettings()

        # Handle nested custom_sources list
        custom_sources = []
        for src in data.get("custom_sources", []):
            custom_sources.append(_dataclass_from_dict(CustomNegotiatorSource, src))

        return NegotiatorSourcesSettings(
            custom_sources=custom_sources,
            disabled_sources=data.get("disabled_sources", []),
        )

    @staticmethod
    def save_negotiator_sources(settings: NegotiatorSourcesSettings) -> None:
        """Save negotiator sources settings."""
        _save_json(NEGOTIATOR_SOURCES_SETTINGS_FILE, asdict(settings))

    @staticmethod
    def load_all() -> AppSettings:
        """Load all settings."""
        return AppSettings(
            general=SettingsService.load_general(),
            negotiation=SettingsService.load_negotiation(),
            genius_bridge=SettingsService.load_genius_bridge(),
            negotiator_sources=SettingsService.load_negotiator_sources(),
            paths=SettingsService.load_paths(),
        )

    @staticmethod
    def save_all(settings: AppSettings) -> None:
        """Save all settings."""
        SettingsService.save_general(settings.general)
        SettingsService.save_negotiation(settings.negotiation)
        SettingsService.save_genius_bridge(settings.genius_bridge)
        SettingsService.save_negotiator_sources(settings.negotiator_sources)
        SettingsService.save_paths(settings.paths)

    @staticmethod
    def get_settings_dir() -> Path:
        """Get the settings directory path."""
        return SETTINGS_DIR

    # =========================================================================
    # Preset Methods
    # =========================================================================

    @staticmethod
    def _now_iso() -> str:
        """Get current time as ISO string."""
        return datetime.now(timezone.utc).isoformat()

    # --- Scenario Presets ---

    @staticmethod
    def load_scenario_presets() -> list[ScenarioPreset]:
        """Load all scenario presets."""
        data = _load_json(SCENARIO_PRESETS_FILE)
        if not data:
            return []
        return [_dataclass_from_dict(ScenarioPreset, p) for p in data]

    @staticmethod
    def save_scenario_preset(preset: ScenarioPreset) -> None:
        """Save a scenario preset (add or update by name)."""
        _ensure_presets_dir()
        presets = SettingsService.load_scenario_presets()
        # Update existing or add new
        preset.created_at = preset.created_at or SettingsService._now_iso()
        existing = next(
            (i for i, p in enumerate(presets) if p.name == preset.name), None
        )
        if existing is not None:
            presets[existing] = preset
        else:
            presets.append(preset)
        _save_json(SCENARIO_PRESETS_FILE, [asdict(p) for p in presets])

    @staticmethod
    def delete_scenario_preset(name: str) -> bool:
        """Delete a scenario preset by name."""
        presets = SettingsService.load_scenario_presets()
        new_presets = [p for p in presets if p.name != name]
        if len(new_presets) == len(presets):
            return False
        _save_json(SCENARIO_PRESETS_FILE, [asdict(p) for p in new_presets])
        return True

    # --- Negotiators Presets ---

    @staticmethod
    def load_negotiators_presets() -> list[NegotiatorsPreset]:
        """Load all negotiators presets."""
        data = _load_json(NEGOTIATORS_PRESETS_FILE)
        if not data:
            return []
        result = []
        for p in data:
            negotiators = [
                _dataclass_from_dict(NegotiatorPreset, n)
                for n in p.get("negotiators", [])
            ]
            result.append(
                NegotiatorsPreset(
                    name=p.get("name", ""),
                    negotiators=negotiators,
                    created_at=p.get("created_at", ""),
                )
            )
        return result

    @staticmethod
    def save_negotiators_preset(preset: NegotiatorsPreset) -> None:
        """Save a negotiators preset (add or update by name)."""
        _ensure_presets_dir()
        presets = SettingsService.load_negotiators_presets()
        preset.created_at = preset.created_at or SettingsService._now_iso()
        existing = next(
            (i for i, p in enumerate(presets) if p.name == preset.name), None
        )
        if existing is not None:
            presets[existing] = preset
        else:
            presets.append(preset)
        _save_json(NEGOTIATORS_PRESETS_FILE, [asdict(p) for p in presets])

    @staticmethod
    def delete_negotiators_preset(name: str) -> bool:
        """Delete a negotiators preset by name."""
        presets = SettingsService.load_negotiators_presets()
        new_presets = [p for p in presets if p.name != name]
        if len(new_presets) == len(presets):
            return False
        _save_json(NEGOTIATORS_PRESETS_FILE, [asdict(p) for p in new_presets])
        return True

    # --- Parameters Presets ---

    @staticmethod
    def load_parameters_presets() -> list[ParametersPreset]:
        """Load all parameters presets."""
        data = _load_json(PARAMETERS_PRESETS_FILE)
        if not data:
            return []
        return [_dataclass_from_dict(ParametersPreset, p) for p in data]

    @staticmethod
    def save_parameters_preset(preset: ParametersPreset) -> None:
        """Save a parameters preset (add or update by name)."""
        _ensure_presets_dir()
        presets = SettingsService.load_parameters_presets()
        preset.created_at = preset.created_at or SettingsService._now_iso()
        existing = next(
            (i for i, p in enumerate(presets) if p.name == preset.name), None
        )
        if existing is not None:
            presets[existing] = preset
        else:
            presets.append(preset)
        _save_json(PARAMETERS_PRESETS_FILE, [asdict(p) for p in presets])

    @staticmethod
    def delete_parameters_preset(name: str) -> bool:
        """Delete a parameters preset by name."""
        presets = SettingsService.load_parameters_presets()
        new_presets = [p for p in presets if p.name != name]
        if len(new_presets) == len(presets):
            return False
        _save_json(PARAMETERS_PRESETS_FILE, [asdict(p) for p in new_presets])
        return True

    # --- Display Presets ---

    @staticmethod
    def load_display_presets() -> list[DisplayPreset]:
        """Load all display presets."""
        data = _load_json(DISPLAY_PRESETS_FILE)
        if not data:
            return []
        return [_dataclass_from_dict(DisplayPreset, p) for p in data]

    @staticmethod
    def save_display_preset(preset: DisplayPreset) -> None:
        """Save a display preset (add or update by name)."""
        _ensure_presets_dir()
        presets = SettingsService.load_display_presets()
        preset.created_at = preset.created_at or SettingsService._now_iso()
        existing = next(
            (i for i, p in enumerate(presets) if p.name == preset.name), None
        )
        if existing is not None:
            presets[existing] = preset
        else:
            presets.append(preset)
        _save_json(DISPLAY_PRESETS_FILE, [asdict(p) for p in presets])

    @staticmethod
    def delete_display_preset(name: str) -> bool:
        """Delete a display preset by name."""
        presets = SettingsService.load_display_presets()
        new_presets = [p for p in presets if p.name != name]
        if len(new_presets) == len(presets):
            return False
        _save_json(DISPLAY_PRESETS_FILE, [asdict(p) for p in new_presets])
        return True

    # --- Full Session Presets ---

    @staticmethod
    def load_session_presets() -> list[FullSessionPreset]:
        """Load all full session presets."""
        data = _load_json(SESSION_PRESETS_FILE)
        if not data:
            return []
        result = []
        for p in data:
            negotiators = [
                _dataclass_from_dict(NegotiatorPreset, n)
                for n in p.get("negotiators", [])
            ]
            preset = _dataclass_from_dict(FullSessionPreset, p)
            preset.negotiators = negotiators
            result.append(preset)
        return result

    @staticmethod
    def save_session_preset(preset: FullSessionPreset) -> None:
        """Save a full session preset (add or update by name)."""
        _ensure_presets_dir()
        presets = SettingsService.load_session_presets()
        preset.created_at = preset.created_at or SettingsService._now_iso()
        existing = next(
            (i for i, p in enumerate(presets) if p.name == preset.name), None
        )
        if existing is not None:
            presets[existing] = preset
        else:
            presets.append(preset)
        _save_json(SESSION_PRESETS_FILE, [asdict(p) for p in presets])

    @staticmethod
    def delete_session_preset(name: str) -> bool:
        """Delete a full session preset by name."""
        presets = SettingsService.load_session_presets()
        new_presets = [p for p in presets if p.name != name]
        if len(new_presets) == len(presets):
            return False
        _save_json(SESSION_PRESETS_FILE, [asdict(p) for p in new_presets])
        return True

    # --- Recent Sessions ---

    @staticmethod
    def load_recent_sessions() -> list[FullSessionPreset]:
        """Load recent session configurations (most recent first)."""
        data = _load_json(RECENT_SESSIONS_FILE)
        if not data:
            return []
        result = []
        for p in data:
            negotiators = [
                _dataclass_from_dict(NegotiatorPreset, n)
                for n in p.get("negotiators", [])
            ]
            preset = _dataclass_from_dict(FullSessionPreset, p)
            preset.negotiators = negotiators
            result.append(preset)
        return result

    @staticmethod
    def add_recent_session(session: FullSessionPreset) -> None:
        """Add a session to recent history (auto-named, limited to MAX_RECENT_SESSIONS)."""
        _ensure_presets_dir()
        recents = SettingsService.load_recent_sessions()
        session.last_used_at = SettingsService._now_iso()
        session.created_at = session.created_at or session.last_used_at
        # Remove duplicate if same scenario+negotiators combo exists
        recents = [
            r
            for r in recents
            if not (
                r.scenario_path == session.scenario_path
                and len(r.negotiators) == len(session.negotiators)
                and all(
                    rn.type_name == sn.type_name
                    for rn, sn in zip(r.negotiators, session.negotiators)
                )
            )
        ]
        # Add to front
        recents.insert(0, session)
        # Trim to max
        recents = recents[:MAX_RECENT_SESSIONS]
        _save_json(RECENT_SESSIONS_FILE, [asdict(p) for p in recents])

    @staticmethod
    def clear_recent_sessions() -> None:
        """Clear all recent sessions."""
        _ensure_presets_dir()
        _save_json(RECENT_SESSIONS_FILE, [])

    # =========================================================================
    # Layout State Methods
    # =========================================================================

    @staticmethod
    def load_layout_state() -> LayoutState:
        """Load layout state from disk."""
        layout_file = SETTINGS_DIR / "layout.json"
        data = _load_json(layout_file)
        if data is None:
            return LayoutState()

        # Parse custom layouts
        custom_layouts = []
        for layout_data in data.get("customLayouts", []):
            # Parse zones
            zones = {}
            for zone_id, zone_data in layout_data.get("zones", {}).items():
                if isinstance(zone_data, dict):
                    zones[zone_id] = ZoneConfig(**zone_data)
                else:
                    zones[zone_id] = zone_data
            # Parse zone sizes
            zone_sizes_data = layout_data.get("zoneSizes", {})
            zone_sizes = (
                ZoneSizes(**zone_sizes_data) if zone_sizes_data else ZoneSizes()
            )
            # Create layout config
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

        return LayoutState(
            version=data.get("version", 1),
            activeLayoutId=data.get("activeLayoutId", "default"),
            customLayouts=custom_layouts,
            panelCollapsed=data.get("panelCollapsed", {}),
            leftColumnWidth=data.get("leftColumnWidth"),
        )

    @staticmethod
    def save_layout_state(state: LayoutState) -> None:
        """Save layout state to disk."""
        _ensure_settings_dir()
        layout_file = SETTINGS_DIR / "layout.json"

        # Convert to dict, handling nested dataclasses
        data = {
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
                if isinstance(layout.zoneSizes, ZoneSizes)
                else layout.zoneSizes,
            }
            for zone_id, zone in layout.zones.items():
                if isinstance(zone, ZoneConfig):
                    layout_dict["zones"][zone_id] = asdict(zone)
                else:
                    layout_dict["zones"][zone_id] = zone
            data["customLayouts"].append(layout_dict)

        _save_json(layout_file, data)

    # =========================================================================
    # Export/Import Methods
    # =========================================================================

    @staticmethod
    def export_settings() -> bytes:
        """Export all settings and presets to a ZIP file.

        Returns:
            bytes: ZIP file contents containing all settings files
        """
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Export manifest with version and timestamp
            manifest = {
                "version": 1,
                "exported_at": SettingsService._now_iso(),
                "app": "negmas-app",
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Export all settings files
            settings_files = [
                GENERAL_SETTINGS_FILE,
                NEGOTIATION_SETTINGS_FILE,
                GENIUS_BRIDGE_SETTINGS_FILE,
                NEGOTIATOR_SOURCES_SETTINGS_FILE,
                PATHS_SETTINGS_FILE,
                SETTINGS_DIR / "layout.json",
            ]

            for file_path in settings_files:
                if file_path.exists():
                    # Store with relative path from settings dir
                    rel_path = file_path.relative_to(SETTINGS_DIR)
                    zf.writestr(f"settings/{rel_path}", file_path.read_text())

            # Export all preset files
            preset_files = [
                SCENARIO_PRESETS_FILE,
                NEGOTIATORS_PRESETS_FILE,
                PARAMETERS_PRESETS_FILE,
                DISPLAY_PRESETS_FILE,
                SESSION_PRESETS_FILE,
                RECENT_SESSIONS_FILE,
            ]

            for file_path in preset_files:
                if file_path.exists():
                    rel_path = file_path.relative_to(SETTINGS_DIR)
                    zf.writestr(f"settings/{rel_path}", file_path.read_text())

        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def import_settings(zip_data: bytes) -> dict[str, str | list[str]]:
        """Import settings and presets from a ZIP file.

        Args:
            zip_data: ZIP file contents

        Returns:
            dict with 'status' and 'imported' list of file names
        """
        _ensure_settings_dir()
        _ensure_presets_dir()

        imported_files: list[str] = []
        errors: list[str] = []

        try:
            buffer = io.BytesIO(zip_data)
            with zipfile.ZipFile(buffer, "r") as zf:
                # Check manifest
                if "manifest.json" not in zf.namelist():
                    return {
                        "status": "error",
                        "message": "Invalid settings file: missing manifest",
                    }

                manifest_data = zf.read("manifest.json")
                manifest = json.loads(manifest_data)

                if manifest.get("app") != "negmas-app":
                    return {
                        "status": "error",
                        "message": "Invalid settings file: not a negmas-app export",
                    }

                # Import all settings files
                for name in zf.namelist():
                    if name == "manifest.json":
                        continue

                    # Handle settings/* paths
                    if name.startswith("settings/"):
                        rel_path = name[len("settings/") :]
                        target_path = SETTINGS_DIR / rel_path

                        # Ensure parent directory exists
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        try:
                            content = zf.read(name)
                            # Validate JSON
                            json.loads(content)
                            target_path.write_bytes(content)
                            imported_files.append(rel_path)
                        except json.JSONDecodeError:
                            errors.append(f"Invalid JSON in {rel_path}")
                        except OSError as e:
                            errors.append(f"Failed to write {rel_path}: {e}")

            result: dict[str, str | list[str]] = {
                "status": "success" if not errors else "partial",
                "imported": imported_files,
            }
            if errors:
                result["errors"] = errors
            return result

        except zipfile.BadZipFile:
            return {"status": "error", "message": "Invalid ZIP file"}
        except Exception as e:
            return {"status": "error", "message": f"Import failed: {e}"}
