"""Scenario definitions and info."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class IssueInfo:
    """Information about a single issue in a scenario."""

    name: str
    type: str  # "discrete", "continuous", "integer"
    values: list | None = None  # For discrete issues
    min_value: float | None = None  # For continuous/integer
    max_value: float | None = None


@dataclass
class ScenarioInfo:
    """Information about a negotiation scenario."""

    # Path to scenario
    path: str

    # Display name
    name: str

    # Number of negotiators/ufuns
    n_negotiators: int

    # Issues
    issues: list[IssueInfo] = field(default_factory=list)

    # Number of possible outcomes (None if continuous)
    n_outcomes: int | None = None

    # Source (e.g., "anac2019", "user", "builtin")
    source: str = "builtin"

    # Tags
    tags: list[str] = field(default_factory=list)

    # Whether stats are cached
    has_stats: bool = False

    # Whether info is cached
    has_info: bool = False

    @property
    def n_issues(self) -> int:
        return len(self.issues)


@dataclass
class ScenarioStatsInfo:
    """Scenario statistics for API responses and display."""

    # Whether stats are available
    has_stats: bool = False

    # Opposition measure (0-1, higher = more opposing preferences)
    opposition: float | None = None

    # Utility ranges per negotiator [(min, max), ...]
    utility_ranges: list[tuple[float, float]] | None = None

    # Number of Pareto optimal outcomes
    n_pareto_outcomes: int = 0

    # Special points - utilities for each negotiator
    # Lists because there can be ties (multiple optimal points)
    nash_utils: list[list[float]] | None = None
    kalai_utils: list[list[float]] | None = None
    ks_utils: list[list[float]] | None = None
    max_welfare_utils: list[list[float]] | None = None

    # Modified variants
    modified_kalai_utils: list[list[float]] | None = None
    modified_ks_utils: list[list[float]] | None = None
    max_relative_welfare_utils: list[list[float]] | None = None

    # Pareto utilities for plotting (can be large)
    pareto_utils: list[list[float]] | None = None

    # Negotiator names (for display)
    negotiator_names: list[str] | None = None


@dataclass
class ScenarioSource:
    """A source directory for scenarios."""

    name: str
    path: Path
    is_builtin: bool = False
