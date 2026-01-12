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

    @property
    def n_issues(self) -> int:
        return len(self.issues)


@dataclass
class ScenarioSource:
    """A source directory for scenarios."""

    name: str
    path: Path
    is_builtin: bool = False
