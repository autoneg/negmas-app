"""Negotiation session state and events."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Status of a negotiation session."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OfferEvent:
    """A single offer in the negotiation."""

    step: int
    proposer: str
    proposer_index: int
    offer: tuple  # The actual offer
    offer_dict: dict  # Offer as {issue: value}
    utilities: list[float]  # Utility for each negotiator
    timestamp: datetime = field(default_factory=datetime.now)
    response: str | None = None  # "accept", "reject", or None
    relative_time: float = 0.0  # Relative time (0-1) in negotiation


@dataclass
class SessionNegotiatorInfo:
    """Information about a negotiator in a session (with color assignment)."""

    name: str
    type_name: str
    index: int
    color: str  # Assigned color for display


# Default colors for negotiators (up to 8)
NEGOTIATOR_COLORS = [
    "#4a6fa5",  # Blue
    "#22a06b",  # Green
    "#9f6b0a",  # Orange/Gold
    "#943d73",  # Purple
    "#0891b2",  # Cyan
    "#dc2626",  # Red
    "#7c3aed",  # Violet
    "#059669",  # Emerald
]

# Color-blind friendly colors (Okabe-Ito palette)
# These colors are designed to be distinguishable for most forms of color blindness
# including deuteranopia, protanopia, and tritanopia
COLORBLIND_COLORS = [
    "#0072B2",  # Blue
    "#E69F00",  # Orange
    "#009E73",  # Bluish Green
    "#CC79A7",  # Reddish Purple
    "#F0E442",  # Yellow
    "#56B4E9",  # Sky Blue
    "#D55E00",  # Vermillion
    "#000000",  # Black
]

# Line styles for color-blind mode (used with markers to distinguish traces)
COLORBLIND_LINE_DASHES = [
    "solid",
    "dash",
    "dot",
    "dashdot",
    "longdash",
    "longdashdot",
    "solid",
    "dash",
]

# Marker symbols for color-blind mode
COLORBLIND_MARKERS = [
    "circle",
    "square",
    "diamond",
    "cross",
    "x",
    "triangle-up",
    "triangle-down",
    "star",
]


@dataclass
class AnalysisPoint:
    """A special point in utility space (Pareto, Nash, etc.)."""

    name: str  # "pareto", "nash", "kalai", "kalai_smorodinsky", "max_welfare"
    utilities: list[float]  # Utility values for each negotiator
    outcome: tuple | None = None  # The outcome tuple if applicable
    outcome_dict: dict | None = None


@dataclass
class OutcomeSpaceData:
    """Pre-computed outcome space data for visualization."""

    # All outcomes as utility tuples (sampled if too large)
    outcome_utilities: list[tuple[float, ...]] = field(default_factory=list)

    # Pareto frontier utilities
    pareto_utilities: list[tuple[float, ...]] = field(default_factory=list)

    # Special points
    nash_point: AnalysisPoint | None = None
    kalai_point: AnalysisPoint | None = None
    kalai_smorodinsky_point: AnalysisPoint | None = None
    max_welfare_point: AnalysisPoint | None = None

    # Metadata
    total_outcomes: int = 0
    sampled: bool = False
    sample_size: int = 0


@dataclass
class SessionInitEvent:
    """Event sent when a session starts, containing initial data for visualization."""

    session_id: str
    scenario_name: str
    scenario_path: str
    negotiator_names: list[str]
    negotiator_types: list[str]
    negotiator_colors: list[str]
    issue_names: list[str]
    n_steps: int | None
    time_limit: float | None
    n_outcomes: int | None = (
        None  # Number of outcomes in outcome space (for TAU progress)
    )
    outcome_space_data: OutcomeSpaceData | None = None


@dataclass
class NegotiationSession:
    """State of a running or completed negotiation."""

    id: str
    status: SessionStatus = SessionStatus.PENDING

    # Configuration
    scenario_path: str = ""
    scenario_name: str = ""
    mechanism_type: str = "SAOMechanism"
    negotiator_names: list[str] = field(default_factory=list)
    negotiator_types: list[str] = field(default_factory=list)
    negotiator_infos: list[SessionNegotiatorInfo] = field(default_factory=list)

    # Issue info
    issue_names: list[str] = field(default_factory=list)
    issue_values: dict[str, list] = field(
        default_factory=dict
    )  # issue -> possible values

    # Deadline/limits
    n_steps: int | None = None
    time_limit: float | None = None

    # Runtime info
    current_step: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None

    # History
    offers: list[OfferEvent] = field(default_factory=list)

    # Result
    agreement: tuple | None = None
    agreement_dict: dict | None = None
    final_utilities: list[float] | None = None
    end_reason: str | None = None
    optimality_stats: dict | None = None  # OutcomeOptimality as dict

    # Error
    error: str | None = None

    # Pre-computed analysis data (computed on session start)
    outcome_space_data: OutcomeSpaceData | None = None

    def get_negotiator_color(self, index: int) -> str:
        """Get the assigned color for a negotiator."""
        if index < len(self.negotiator_infos):
            return self.negotiator_infos[index].color
        return NEGOTIATOR_COLORS[index % len(NEGOTIATOR_COLORS)]

    def duration_seconds(self) -> float | None:
        """Get session duration in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def progress(self) -> float:
        """Get progress as 0-1 value."""
        if self.n_steps and self.n_steps > 0:
            return min(1.0, self.current_step / self.n_steps)
        if self.time_limit and self.time_limit > 0:
            duration = self.duration_seconds()
            if duration:
                return min(1.0, duration / self.time_limit)
        return 0.0


@dataclass
class PanelConfig:
    """Configuration for a display panel."""

    id: str
    type: str  # "info", "offer_history", "outcome_space", "timeline", "result"
    title: str
    # Grid position (1-based, CSS grid style: row_start, col_start, row_end, col_end)
    row: int = 1
    col: int = 1
    row_end: int = 2  # Exclusive end
    col_end: int = 2  # Exclusive end
    # Legacy rowspan/colspan for backwards compat
    rowspan: int = 1
    colspan: int = 1
    # Panel-specific settings
    settings: dict = field(default_factory=dict)


@dataclass
class LayoutConfig:
    """A named layout configuration for the negotiation view."""

    name: str
    description: str = ""
    # Grid dimensions (3 or 4 for 3x3 or 4x4)
    grid_size: int = 4
    # Panel configurations
    panels: list[PanelConfig] = field(default_factory=list)
    # Metadata
    created_at: str = ""
    is_builtin: bool = False


# Panel type definitions
PANEL_TYPES = [
    {
        "id": "info",
        "type": "info",
        "title": "Negotiation Info",
        "description": "Progress, status, negotiators",
    },
    {
        "id": "outcome_space",
        "type": "outcome_space",
        "title": "Outcome Space",
        "description": "2D utility plot with Pareto frontier",
    },
    {
        "id": "offer_history",
        "type": "offer_history",
        "title": "Offer History",
        "description": "List of offers made",
    },
    {
        "id": "timeline",
        "type": "timeline",
        "title": "Utility Timeline",
        "description": "Utility values over time",
    },
    {
        "id": "result",
        "type": "result",
        "title": "Result",
        "description": "Final agreement and utilities",
    },
]


# Default layouts
def default_layout() -> LayoutConfig:
    """Create the default 4x4 layout."""
    return LayoutConfig(
        name="Default",
        description="Standard layout with all panels",
        grid_size=4,
        is_builtin=True,
        panels=[
            PanelConfig(
                id="info",
                type="info",
                title="Negotiation Info",
                row=1,
                col=1,
                row_end=2,
                col_end=3,
            ),
            PanelConfig(
                id="outcome_space",
                type="outcome_space",
                title="Outcome Space",
                row=1,
                col=3,
                row_end=3,
                col_end=5,
            ),
            PanelConfig(
                id="offer_history",
                type="offer_history",
                title="Offer History",
                row=2,
                col=1,
                row_end=3,
                col_end=3,
            ),
            PanelConfig(
                id="timeline",
                type="timeline",
                title="Utility Timeline",
                row=3,
                col=1,
                row_end=4,
                col_end=5,
            ),
            PanelConfig(
                id="result",
                type="result",
                title="Result",
                row=4,
                col=1,
                row_end=5,
                col_end=5,
            ),
        ],
    )


def timeline_focused_layout() -> LayoutConfig:
    """Create a layout focused on utility timeline."""
    return LayoutConfig(
        name="Timeline Focus",
        description="Larger timeline panel for detailed time analysis",
        grid_size=4,
        is_builtin=True,
        panels=[
            PanelConfig(
                id="info",
                type="info",
                title="Negotiation Info",
                row=1,
                col=1,
                row_end=2,
                col_end=3,
            ),
            PanelConfig(
                id="outcome_space",
                type="outcome_space",
                title="Outcome Space",
                row=1,
                col=3,
                row_end=2,
                col_end=5,
            ),
            PanelConfig(
                id="timeline",
                type="timeline",
                title="Utility Timeline",
                row=2,
                col=1,
                row_end=4,
                col_end=5,
            ),
            PanelConfig(
                id="result",
                type="result",
                title="Result",
                row=4,
                col=1,
                row_end=5,
                col_end=5,
            ),
        ],
    )


def compact_layout() -> LayoutConfig:
    """Create a compact 3x3 layout."""
    return LayoutConfig(
        name="Compact",
        description="Compact 3x3 layout",
        grid_size=3,
        is_builtin=True,
        panels=[
            PanelConfig(
                id="info",
                type="info",
                title="Negotiation Info",
                row=1,
                col=1,
                row_end=2,
                col_end=2,
            ),
            PanelConfig(
                id="outcome_space",
                type="outcome_space",
                title="Outcome Space",
                row=1,
                col=2,
                row_end=3,
                col_end=4,
            ),
            PanelConfig(
                id="offer_history",
                type="offer_history",
                title="Offer History",
                row=2,
                col=1,
                row_end=3,
                col_end=2,
            ),
            PanelConfig(
                id="timeline",
                type="timeline",
                title="Utility Timeline",
                row=3,
                col=1,
                row_end=4,
                col_end=3,
            ),
            PanelConfig(
                id="result",
                type="result",
                title="Result",
                row=3,
                col=3,
                row_end=4,
                col_end=4,
            ),
        ],
    )


BUILTIN_LAYOUTS = {
    "default": default_layout,
    "timeline": timeline_focused_layout,
    "compact": compact_layout,
}
