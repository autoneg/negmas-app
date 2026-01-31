"""Settings models for NegMAS App."""

from dataclasses import dataclass, field
from typing import Any

from negmas.plots.util import SUPPORTED_IMAGE_FORMATS


@dataclass
class NegotiationSaveOptions:
    """Options for saving negotiations using CompletedRun format.

    These options mirror Mechanism.save() parameters to provide full control
    over how negotiations are persisted to disk.
    """

    # Whether to save as a single file (just the trace) or a directory
    single_file: bool = False

    # If True, save per-negotiator trace files in a subdirectory
    # Only works with full_trace source
    per_negotiator: bool = False

    # Whether to save the scenario (ufuns, outcome space)
    save_scenario: bool = True

    # Whether to save scenario statistics (Pareto, Nash, etc.)
    save_scenario_stats: bool = False

    # Whether to save agreement optimality statistics
    save_agreement_stats: bool = True

    # Whether to save mechanism configuration
    save_config: bool = True

    # Source of history data to save
    # Options: None (auto), "history", "trace", "extended_trace", "full_trace", "full_trace_with_utils"
    source: str | None = None

    # Storage format for tables: "csv", "gzip", "parquet"
    storage_format: str = "parquet"

    # Whether to generate preview images (app-specific feature)
    generate_previews: bool = True


@dataclass
class ThemeSettings:
    """Theme and accessibility settings."""

    dark_mode: bool = False
    color_blind_mode: bool = False
    # Color-blind friendly palette (Okabe-Ito palette)
    # These colors are distinguishable for most forms of color blindness


@dataclass
class GeneralSettings:
    """General application settings."""

    dark_mode: bool = False
    color_blind_mode: bool = False
    save_negotiations: bool = True  # Whether to persist negotiations to disk
    cache_scenario_stats: bool = True  # Auto-cache computed scenario statistics


@dataclass
class NegotiationSettings:
    """Default negotiation parameters."""

    default_max_steps: int = 100
    default_step_delay_ms: int = 100
    default_time_limit: float | None = None


@dataclass
class GeniusBridgeSettings:
    """Genius bridge configuration."""

    auto_start: bool = True
    java_path: str | None = None
    port: int = 25337


@dataclass
class CustomNegotiatorSource:
    """User-defined negotiator source configuration."""

    # Unique identifier
    id: str

    # Display name
    name: str

    # Description
    description: str = ""

    # Supported mechanism types (e.g., ["SAO", "TAU", "GAO"])
    mechanisms: list[str] = field(default_factory=lambda: ["SAO"])

    # Whether this source requires the Genius bridge
    requires_bridge: bool = False

    # Library to import from (e.g., "negmas_llm", "my_negotiators")
    library: str = ""

    # Regex pattern to match class names (e.g., ".*Negotiator$")
    class_pattern: str = ""

    # Or explicit module and class names
    module: str = ""
    class_names: list[str] = field(default_factory=list)


@dataclass
class NegotiatorSourcesSettings:
    """Settings for negotiator sources."""

    # Custom user-defined sources
    custom_sources: list[CustomNegotiatorSource] = field(default_factory=list)

    # Disabled built-in sources (by ID)
    disabled_sources: list[str] = field(default_factory=list)


@dataclass
class PathSettings:
    """Custom paths for scenarios."""

    scenario_paths: list[str] = field(default_factory=list)
    # User scenarios directory for custom/created scenarios
    user_scenarios: str = "~/negmas/app/scenarios"


@dataclass
class SavedFilter:
    """A saved filter configuration."""

    # Unique identifier
    id: str

    # Display name
    name: str

    # Filter type: "scenario" or "negotiator"
    type: str

    # Filter data (all filter values)
    data: dict[str, Any] = field(default_factory=dict)

    # Description
    description: str = ""

    # Creation timestamp (ISO format)
    created_at: str = ""


@dataclass
class FilterSettings:
    """Settings for saved filters."""

    # Saved scenario filters
    scenario_filters: list[SavedFilter] = field(default_factory=list)

    # Saved negotiator filters
    negotiator_filters: list[SavedFilter] = field(default_factory=list)

    # Default filter IDs (auto-apply on view load)
    default_scenario_filter_id: str | None = None
    default_negotiator_filter_id: str | None = None


@dataclass
class PerformanceSettings:
    """Performance settings for limiting resource-intensive operations.

    All limits use None or 0 to indicate no limit.
    """

    # Maximum number of outcomes for running negotiations/tournaments
    # Scenarios exceeding this will be blocked from running
    max_outcomes_run: int | None = None

    # Maximum number of outcomes for calculating scenario stats
    # (Pareto, Nash, Kalai, etc.) - above this, only info is calculated
    max_outcomes_stats: int | None = 1_000_000

    # Maximum number of outcomes for generating plots with full outcome space
    # Above this, plots show special points only (no background outcome space)
    max_outcomes_plots: int | None = 500_000

    # Maximum number of outcomes for showing Pareto frontier in plots
    # Computing Pareto frontier is expensive for large outcome spaces
    max_outcomes_pareto: int | None = 1_000_000

    # Maximum number of outcomes for calculating rationality fraction
    # Above this, rationality calculation is skipped (info still calculated)
    # Note: Rationality calculation uses sampling but is still expensive for large spaces
    max_outcomes_rationality: int | None = 500_000

    # Maximum number of outcomes for showing histogram panel
    # Above this threshold, histogram is disabled for enumerated outcome spaces
    # (scenarios without named issues where histogram shows all outcomes)
    max_histogram_outcomes: int = 10_000

    # Maximum number of outcomes for auto-calculating stats in 2D utility view
    # If a scenario has fewer outcomes than this and stats are not cached,
    # stats will be computed automatically and cached (if in ~/negmas/app)
    # Set to 0 to disable auto-calculation
    max_auto_calc_stats: int = 10_000

    # Maximum number of Pareto frontier outcomes to save in cache
    # If the Pareto frontier has more outcomes than this limit, it will not be saved
    # This also affects special point outcomes (nash_outcomes, kalai_outcomes, etc.)
    # None means no limit (save all Pareto outcomes)
    max_pareto_outcomes: int | None = None

    # Maximum number of Pareto frontier utilities to save in cache
    # If the Pareto frontier has more utility points than this limit, they will not be saved
    # Independent from max_pareto_outcomes - you can save utils without outcomes or vice versa
    # None means no limit (save all Pareto utilities)
    max_pareto_utils: int | None = None

    # Image format for saving plots
    # Supported formats: SUPPORTED_IMAGE_FORMATS = {"webp", "png", "jpg", "jpeg", "svg", "pdf"}
    # webp provides best compression (5-10x smaller than PNG)
    # When loading, all supported formats are tried
    plot_image_format: str = "webp"

    # Storage format for offers data
    # Supported: "csv", "parquet" (parquet is 5-10x smaller and faster to load)
    # CSV is human-readable, parquet is optimized for storage/performance
    offers_storage_format: str = "parquet"

    def __post_init__(self) -> None:
        """Validate plot_image_format is supported."""
        if self.plot_image_format not in SUPPORTED_IMAGE_FORMATS:
            raise ValueError(
                f"plot_image_format must be one of {SUPPORTED_IMAGE_FORMATS}, "
                f"got: {self.plot_image_format}"
            )
        if self.offers_storage_format not in {"csv", "parquet"}:
            raise ValueError(
                f"offers_storage_format must be 'csv' or 'parquet', "
                f"got: {self.offers_storage_format}"
            )


# =============================================================================
# Layout State Models for Panel Layout Persistence
# =============================================================================


@dataclass
class ZoneConfig:
    """Configuration for a single zone in the layout."""

    panels: list[str] = field(default_factory=list)
    activePanel: str | None = None
    displayMode: str = "tabbed"  # 'tabbed' or 'stacked'


@dataclass
class ZoneSizes:
    """Size configuration for layout zones."""

    leftWidth: str = "35%"
    centerWidth: str = "0"
    rightWidth: str = "65%"
    bottomHeight: str = "120px"
    bottomSplit: str = "50%"


@dataclass
class LayoutConfig:
    """Configuration for a single layout."""

    id: str
    name: str
    builtIn: bool = False
    topRowMode: str = "two-column"  # 'two-column', 'three-column', 'single-column'
    zones: dict[str, ZoneConfig] = field(default_factory=dict)
    zoneSizes: ZoneSizes = field(default_factory=ZoneSizes)

    def __post_init__(self) -> None:
        # Ensure zones is a dict of ZoneConfig objects
        if self.zones:
            new_zones = {}
            for key, val in self.zones.items():
                if isinstance(val, dict):
                    new_zones[key] = ZoneConfig(**val)
                else:
                    new_zones[key] = val
            self.zones = new_zones
        # Ensure zoneSizes is a ZoneSizes object
        if isinstance(self.zoneSizes, dict):
            self.zoneSizes = ZoneSizes(**self.zoneSizes)


@dataclass
class LayoutState:
    """
    Complete layout state persisted to server.

    This mirrors the state structure used by LayoutManager in JS.
    """

    version: int = 1
    activeLayoutId: str = "default"
    # Custom layouts (built-in layouts are always available in JS)
    customLayouts: list[LayoutConfig] = field(default_factory=list)
    # Panel collapse state
    panelCollapsed: dict[str, bool] = field(default_factory=dict)
    # Column widths for resizable areas
    leftColumnWidth: str | None = None
    # Panel layout settings (for PanelLayout.vue)
    panelLayout: dict[str, Any] = field(default_factory=dict)
    # Default: leftColumnFlex: 40, panelHeights: {left: {}, right: {}}


@dataclass
class AppSettings:
    """Complete application settings."""

    general: GeneralSettings = field(default_factory=GeneralSettings)
    negotiation: NegotiationSettings = field(default_factory=NegotiationSettings)
    genius_bridge: GeniusBridgeSettings = field(default_factory=GeniusBridgeSettings)
    negotiator_sources: NegotiatorSourcesSettings = field(
        default_factory=NegotiatorSourcesSettings
    )
    paths: PathSettings = field(default_factory=PathSettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)


# =============================================================================
# Preset Models for Saving/Loading Negotiation Configurations
# =============================================================================


@dataclass
class NegotiatorPreset:
    """A negotiator configuration in a preset."""

    type_name: str
    name: str
    source: str = "native"
    requires_bridge: bool = False
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioPreset:
    """Saved scenario selection preset."""

    name: str  # Preset name
    scenario_path: str  # Path to scenario
    scenario_name: str  # Display name of scenario
    created_at: str = ""  # ISO timestamp


@dataclass
class NegotiatorsPreset:
    """Saved negotiators configuration preset."""

    name: str  # Preset name
    negotiators: list[NegotiatorPreset] = field(default_factory=list)
    created_at: str = ""  # ISO timestamp


@dataclass
class ParametersPreset:
    """Saved mechanism parameters preset."""

    name: str  # Preset name
    mechanism_type: str = "SAOMechanism"
    # All mechanism params in a single dict
    mechanism_params: dict[str, Any] = field(default_factory=dict)
    # Information sharing
    share_ufuns: bool = False
    created_at: str = ""  # ISO timestamp


@dataclass
class DisplayPreset:
    """Saved display settings preset."""

    name: str  # Preset name
    mode: str = "realtime"  # 'realtime' or 'batch'
    step_delay: int = 100  # milliseconds
    show_plot: bool = True
    show_offers: bool = True
    created_at: str = ""  # ISO timestamp


@dataclass
class FullSessionPreset:
    """Complete negotiation session preset (all settings)."""

    name: str  # Preset name
    # Scenario
    scenario_path: str
    scenario_name: str
    # Negotiators
    negotiators: list[NegotiatorPreset] = field(default_factory=list)
    # Mechanism
    mechanism_type: str = "SAOMechanism"
    mechanism_params: dict[str, Any] = field(default_factory=dict)
    # Information sharing
    share_ufuns: bool = False
    # Display
    mode: str = "realtime"
    step_delay: int = 100
    show_plot: bool = True
    show_offers: bool = True
    # Panels
    panels: dict[str, Any] = field(default_factory=dict)
    # Metadata
    created_at: str = ""  # ISO timestamp
    last_used_at: str = ""  # ISO timestamp


# =============================================================================
# Tournament Preset Models
# =============================================================================


@dataclass
class CompetitorConfig:
    """Configuration for a competitor in a tournament."""

    type_name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class TournamentPreset:
    """Saved tournament configuration preset."""

    name: str  # Preset name
    # Scenarios
    scenario_paths: list[str] = field(default_factory=list)
    # Competitors
    competitor_types: list[str] = field(default_factory=list)
    competitor_configs: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )  # type_name -> params
    # Opponents (None means same as competitors)
    opponent_types: list[str] | None = None
    opponents_same_as_competitors: bool = True
    # Basic settings
    n_repetitions: int = 1
    rotate_ufuns: bool = True
    self_play: bool = True
    mechanism_type: str = "SAOMechanism"
    # Steps/time limits
    n_steps: int | None = 100
    n_steps_min: int | None = None
    n_steps_max: int | None = None
    time_limit: float | None = None
    time_limit_min: float | None = None
    time_limit_max: float | None = None
    # Advanced time limits
    step_time_limit: float | None = None
    negotiator_time_limit: float | None = None
    hidden_time_limit: float | None = None
    # Probabilistic ending
    pend: float | None = None
    pend_per_second: float | None = None
    # Scoring
    final_score_metric: str = "advantage"
    final_score_stat: str = "mean"
    # Run ordering
    randomize_runs: bool = False
    sort_runs: bool = True
    # Information hiding
    id_reveals_type: bool = False
    name_reveals_type: bool = True
    mask_scenario_names: bool = False
    # Self-play options
    only_failures_on_self_play: bool = False
    # Save options
    save_stats: bool = True
    save_scenario_figs: bool = True
    save_every: int = 1
    # Scenario options
    normalize: bool = True  # Normalize utility functions
    # Metadata
    created_at: str = ""  # ISO timestamp
    last_used_at: str = ""  # ISO timestamp


# =============================================================================
# Layout Preset Models for Customizable Panel Layouts
# =============================================================================


@dataclass
class PanelPlacement:
    """Defines where a panel is placed on the grid."""

    panel_id: (
        str  # e.g., 'outcome_space', 'offer_history', 'info', 'timeline', 'result'
    )
    row_start: int  # 1-based grid row start
    row_end: int  # 1-based grid row end (exclusive, CSS grid style)
    col_start: int  # 1-based grid column start
    col_end: int  # 1-based grid column end (exclusive, CSS grid style)


@dataclass
class LayoutPreset:
    """Saved layout configuration for the negotiation view."""

    name: str  # Preset name (e.g., "Default", "Compact", "Wide Timeline")
    grid_size: int = 4  # 3 or 4 (3x3 or 4x4 grid)
    panels: list[PanelPlacement] = field(default_factory=list)
    created_at: str = ""  # ISO timestamp


# Available panel types
PANEL_TYPES = [
    {
        "id": "info",
        "name": "Negotiation Info",
        "description": "Shows progress, status, and negotiator info",
    },
    {
        "id": "outcome_space",
        "name": "Outcome Space",
        "description": "2D utility plot with Pareto frontier",
    },
    {
        "id": "offer_history",
        "name": "Offer History",
        "description": "List of offers made during negotiation",
    },
    {
        "id": "timeline",
        "name": "Utility Timeline",
        "description": "Utility values over time",
    },
    {"id": "result", "name": "Result", "description": "Final agreement and utilities"},
    {
        "id": "stats",
        "name": "Scenario Stats",
        "description": "Scenario statistics: opposition, Pareto, Nash, Kalai, KS, Max Welfare",
    },
]


def get_default_layout() -> LayoutPreset:
    """Returns the default 4x4 layout."""
    return LayoutPreset(
        name="Default",
        grid_size=4,
        panels=[
            PanelPlacement(
                panel_id="info", row_start=1, row_end=2, col_start=1, col_end=3
            ),
            PanelPlacement(
                panel_id="outcome_space", row_start=1, row_end=3, col_start=3, col_end=5
            ),
            PanelPlacement(
                panel_id="offer_history", row_start=2, row_end=3, col_start=1, col_end=3
            ),
            PanelPlacement(
                panel_id="timeline", row_start=3, row_end=4, col_start=1, col_end=5
            ),
            PanelPlacement(
                panel_id="result", row_start=4, row_end=5, col_start=1, col_end=5
            ),
        ],
    )
