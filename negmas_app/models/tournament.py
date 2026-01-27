"""Tournament configuration and session models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class TournamentStatus(str, Enum):
    """Status of a tournament."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FinalScoreMetric(str, Enum):
    """Metrics for calculating final tournament scores."""

    ADVANTAGE = "advantage"
    UTILITY = "utility"
    WELFARE = "welfare"
    PARTNER_WELFARE = "partner_welfare"


class FinalScoreStatistic(str, Enum):
    """Statistics for calculating final tournament scores."""

    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    STD = "std"


class NegotiationEndReason(str, Enum):
    """Reason why a negotiation ended."""

    AGREEMENT = "agreement"  # Parties reached an agreement
    TIMEOUT = "timeout"  # Ran out of steps/time without agreement
    ERROR = "error"  # An error occurred during negotiation
    BROKEN = "broken"  # A negotiator raised an exception


class NormalizationMode(str, Enum):
    """Mode for normalizing utility functions in tournaments.

    - none: No normalization applied
    - scale_min: Scale so minimum utility = 1.0
    - scale_max: Scale so maximum utility = 1.0
    - normalize: Normalize to [0, 1] range (recommended)
    """

    NONE = "none"
    SCALE_MIN = "scale_min"
    SCALE_MAX = "scale_max"
    NORMALIZE = "normalize"


class CellStatus(str, Enum):
    """Status of a cell in the tournament grid."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"


# Type aliases matching negmas types
OptimizationLevel = Literal["speed", "time", "none", "balanced", "space", "max"]
StorageFormat = Literal["csv", "gzip", "parquet"]


@dataclass
class TournamentConfig:
    """Configuration for running a tournament."""

    # Required
    competitor_types: list[str]  # Negotiator type names (scored)
    scenario_paths: list[str]  # Paths to scenario directories

    # Optional opponents (if None, competitors play against each other)
    # If specified, competitors play against opponents but only competitors are scored
    opponent_types: list[str] | None = None

    # Optional negotiator parameters (one dict per competitor/opponent or None for defaults)
    competitor_params: list[dict] | None = None
    opponent_params: list[dict] | None = None

    # Tournament settings
    n_repetitions: int = 1
    rotate_ufuns: bool = True
    self_play: bool = True

    # Mechanism settings
    mechanism_type: str = "SAOMechanism"
    # n_steps can be int, (min, max) tuple for random sampling, or None for unlimited
    n_steps: int | tuple[int, int] | None = 100
    # time_limit can be float, (min, max) tuple, or None for unlimited
    time_limit: float | tuple[float, float] | None = None

    # Time limits for negotiators (all support single value or (min, max) range)
    step_time_limit: float | tuple[float, float] | None = None
    negotiator_time_limit: float | tuple[float, float] | None = None
    hidden_time_limit: float | tuple[float, float] | None = None

    # Probabilistic ending (all support single value or (min, max) range)
    pend: float | tuple[float, float] | None = None
    pend_per_second: float | tuple[float, float] | None = None

    # Scoring
    final_score_metric: str = "advantage"
    final_score_stat: str = "mean"

    # Run ordering
    randomize_runs: bool = False  # Randomize order of negotiations
    sort_runs: bool = (
        True  # Sort runs by scenario/competitors (ignored if randomize_runs)
    )

    # Information hiding
    id_reveals_type: bool = False  # Whether negotiator ID reveals its type
    name_reveals_type: bool = True  # Whether negotiator name reveals its type
    mask_scenario_names: bool = False  # Hide scenario names from negotiators

    # Self-play options
    only_failures_on_self_play: bool = False  # Only record failures for self-play

    # Save options
    save_stats: bool = True  # Save statistics (Pareto, Nash, Kalai, etc.)
    save_scenario_figs: bool = True  # Save scenario figures
    save_every: int = 1  # Save results every N negotiations (0 = only at end)
    capture_offers: bool = (
        True  # Capture offer trace for each negotiation (for viewing)
    )

    # Scenario options
    # Normalization mode: "none", "scale_min", "scale_max", "normalize"
    # - none: No normalization
    # - scale_min: Scale so minimum utility = 1.0
    # - scale_max: Scale so maximum utility = 1.0
    # - normalize: Normalize to [0, 1] range (default, recommended)
    normalization: str = NormalizationMode.NORMALIZE
    ignore_discount: bool = False  # Ignore discounting in utility functions
    ignore_reserved: bool = False  # Ignore reserved values in utility functions
    pass_opponent_ufun: bool = False  # Pass opponent utility function to negotiators
    raise_exceptions: bool = False  # Raise exceptions on negotiator errors

    # Execution
    njobs: int = -1  # -1 = serial (safer for web app), 0 = all cores

    # Monitoring
    monitor_negotiations: bool = False  # Enable live monitoring of individual negotiations (requires negmas support)

    # Output
    save_path: str | None = None  # Path to save results (None = don't save)
    verbosity: int = 0

    # Path handling when save_path already exists
    # - "continue": Continue existing tournament if path exists (default)
    # - "overwrite": Delete existing tournament and start fresh
    # - "fail": Raise error if path exists
    path_exists: str = "continue"

    # Storage and Memory Optimization
    # Controls disk space usage for tournament results:
    # - "speed"/"time"/"none": Keep all files (results/, all_scores.csv, details.csv)
    # - "balanced": Remove results/ folder after details.csv is created
    # - "space"/"max": Remove both results/ folder AND all_scores.csv
    storage_optimization: OptimizationLevel = "speed"

    # Controls RAM usage for tournament results:
    # - "speed"/"time"/"none": Keep all DataFrames in memory
    # - "balanced": Keep details + final_scores, compute scores on demand
    # - "space"/"max": Keep only final_scores, load from disk on demand
    memory_optimization: OptimizationLevel = "speed"

    # Storage format for large data files (all_scores, details):
    # - "csv": Plain CSV files (human-readable, larger size)
    # - "gzip": Gzip-compressed CSV (good compression)
    # - "parquet": Parquet binary (best compression, preserves types, fastest)
    # - None: Auto-select based on storage_optimization
    storage_format: StorageFormat | None = None


@dataclass
class CompetitorScore:
    """Score information for a single competitor in the tournament."""

    name: str  # Short name of the competitor
    type_name: str  # Full type name
    score: float  # Final score
    rank: int  # 1-based rank (1 = winner)

    # Statistics
    mean_utility: float | None = None
    mean_advantage: float | None = None
    n_negotiations: int = 0
    n_agreements: int = 0
    agreement_rate: float | None = None


@dataclass
class TournamentOffer:
    """A single offer in a tournament negotiation."""

    step: int
    proposer: str
    proposer_index: int
    offer: tuple  # The actual offer
    offer_dict: dict  # Offer as {issue: value}
    utilities: list[float]  # Utility for each negotiator


@dataclass
class NegotiationResult:
    """Result of a single negotiation in the tournament."""

    scenario: str
    partners: list[str]
    agreement: tuple | None
    utilities: list[float] | None
    advantages: list[float] | None
    has_error: bool = False
    error_details: str | None = None
    execution_time: float | None = None
    end_reason: NegotiationEndReason | None = None
    # Optional detailed trace data (populated when capture_offers=True)
    offers: list[TournamentOffer] | None = None
    issue_names: list[str] | None = None
    scenario_path: str | None = None
    n_steps: int | None = None


@dataclass
class CellUpdate:
    """Update for a cell in the tournament grid.

    The grid is organized as competitors (rows) vs opponents (columns).
    Each cell can have multiple negotiations (scenarios x repetitions x ufun_rotations).
    """

    competitor_idx: int  # Row index (which competitor)
    opponent_idx: int  # Column index (which opponent)
    scenario_idx: int  # Which scenario
    repetition: int  # Which repetition
    rotated: bool  # Whether ufuns were rotated
    status: CellStatus  # pending, running, complete
    end_reason: NegotiationEndReason | None = None  # Only set when complete
    utilities: list[float] | None = None  # Utilities achieved
    error: str | None = None  # Error message if end_reason is ERROR or BROKEN
    # Optional detailed negotiation data for viewing
    offers: list[TournamentOffer] | None = None
    issue_names: list[str] | None = None
    scenario_path: str | None = None
    n_steps: int | None = None
    agreement: tuple | None = None


@dataclass
class LeaderboardEntry:
    """A single entry in the live tournament leaderboard."""

    name: str
    score: float
    rank: int
    n_negotiations: int
    n_agreements: int
    mean_utility: float | None = None


@dataclass
class TournamentGridInit:
    """Initial grid structure sent at tournament start."""

    competitors: list[str]  # Row labels
    opponents: list[str]  # Column labels (same as competitors usually)
    scenarios: list[str]  # Scenario names
    n_repetitions: int
    rotate_ufuns: bool
    total_negotiations: int


@dataclass
class TournamentProgress:
    """Progress update for a running tournament."""

    completed: int
    total: int
    current_scenario: str | None = None
    current_partners: list[str] | None = None
    percent: float = 0.0


@dataclass
class TournamentResults:
    """Complete results from a tournament run."""

    # Final rankings (sorted by score, winner first)
    final_scores: list[CompetitorScore] = field(default_factory=list)

    # Detailed results (optional, can be large)
    negotiation_results: list[NegotiationResult] = field(default_factory=list)

    # Summary statistics
    total_negotiations: int = 0
    total_agreements: int = 0
    overall_agreement_rate: float = 0.0
    execution_time: float | None = None

    # Storage location (if saved)
    results_path: str | None = None


@dataclass
class TournamentSession:
    """State of a running or completed tournament."""

    id: str
    status: TournamentStatus = TournamentStatus.PENDING
    config: TournamentConfig | None = None

    # Progress tracking
    progress: TournamentProgress | None = None

    # Timing
    start_time: datetime | None = None
    end_time: datetime | None = None

    # Results (populated on completion)
    results: TournamentResults | None = None

    # Error info
    error: str | None = None

    def duration_seconds(self) -> float | None:
        """Get tournament duration in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
