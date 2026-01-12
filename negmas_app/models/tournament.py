"""Tournament configuration and session models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


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


@dataclass
class TournamentConfig:
    """Configuration for running a tournament."""

    # Required
    competitor_types: list[str]  # Negotiator type names
    scenario_paths: list[str]  # Paths to scenario directories

    # Optional negotiator parameters (one dict per competitor or None for defaults)
    competitor_params: list[dict] | None = None

    # Tournament settings
    n_repetitions: int = 1
    rotate_ufuns: bool = True
    self_play: bool = True

    # Mechanism settings
    mechanism_type: str = "SAOMechanism"
    n_steps: int | None = 100
    time_limit: float | None = None

    # Scoring
    final_score_metric: str = "advantage"
    final_score_stat: str = "mean"

    # Execution
    njobs: int = -1  # -1 = serial (safer for web app), 0 = all cores

    # Output
    save_path: str | None = None  # Path to save results (None = don't save)
    verbosity: int = 0


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
