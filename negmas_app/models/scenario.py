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

    # Fraction of rational outcomes (from cached info, None if not calculated)
    rational_fraction: float | None = None

    # Opposition measure (0-1, higher = more opposing preferences)
    opposition: float | None = None

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

    # Total number of outcomes in the outcome space
    n_outcomes: int | None = None

    # Fraction of outcomes that are rational for all negotiators (0-1)
    # An outcome is rational if its utility >= reserved value for all negotiators
    rational_fraction: float | None = None

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

    # Special points - outcomes (as dicts with issue names as keys)
    nash_outcomes: list[dict] | None = None
    kalai_outcomes: list[dict] | None = None
    ks_outcomes: list[dict] | None = None
    max_welfare_outcomes: list[dict] | None = None

    # Modified variants
    modified_kalai_utils: list[list[float]] | None = None
    modified_ks_utils: list[list[float]] | None = None
    max_relative_welfare_utils: list[list[float]] | None = None

    # Note: pareto_utils intentionally omitted - too large (can be 2MB+)
    # Only n_pareto_outcomes is provided; full Pareto data computed on-demand for visualization

    # Negotiator names (for display)
    negotiator_names: list[str] | None = None

    # Issue names (for outcome display)
    issue_names: list[str] | None = None


@dataclass
class ScenarioSource:
    """A source directory for scenarios."""

    name: str
    path: Path
    is_builtin: bool = False
