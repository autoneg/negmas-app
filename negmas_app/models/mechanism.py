"""Mechanism type definitions and parameters."""

from dataclasses import dataclass, field
from enum import Enum


class MechanismType(str, Enum):
    """Supported negotiation mechanism types."""

    SAO = "sao"
    TAU = "tau"
    GB = "gb"  # General GBMechanism


@dataclass
class MechanismTypeInfo:
    """Information about a mechanism type."""

    id: str
    name: str
    description: str
    allows_infinite: bool  # Whether the mechanism can run without a deadline
    module_path: str
    class_name: str


# Information about each mechanism type
MECHANISM_TYPES: dict[MechanismType, MechanismTypeInfo] = {
    MechanismType.SAO: MechanismTypeInfo(
        id="sao",
        name="SAO (Stacked Alternating Offers)",
        description="Sequential offers with acceptance/rejection. Most common protocol.",
        allows_infinite=False,
        module_path="negmas.sao",
        class_name="SAOMechanism",
    ),
    MechanismType.TAU: MechanismTypeInfo(
        id="tau",
        name="TAU (Threaded Alternating Ultimatums)",
        description="Parallel offers in multiple threads. Can run without deadline.",
        allows_infinite=True,
        module_path="negmas.gb",
        class_name="TAUMechanism",
    ),
    MechanismType.GB: MechanismTypeInfo(
        id="gb",
        name="GB (General Game-Based)",
        description="General game-based mechanism with configurable evaluators.",
        allows_infinite=False,
        module_path="negmas.gb",
        class_name="GBMechanism",
    ),
}


@dataclass
class DeadlineParams:
    """Deadline/termination parameters for mechanisms.

    At least one deadline must be set for mechanisms that don't allow infinite negotiation.
    """

    # Round/step limit
    n_steps: int | None = None

    # Wall-clock time limit (seconds)
    time_limit: float | None = None

    # Probabilistic ending per step
    pend: float = 0.0

    # Probabilistic ending per second
    pend_per_second: float = 0.0

    # Time limit per step (seconds)
    step_time_limit: float | None = None

    # Time limit per negotiator per step (seconds)
    negotiator_time_limit: float | None = None

    # Hidden time limit - negotiators don't know about this (seconds)
    hidden_time_limit: float | None = None

    def has_deadline(self) -> bool:
        """Check if at least one deadline is set."""
        return (
            self.n_steps is not None
            or self.time_limit is not None
            or self.pend > 0
            or self.pend_per_second > 0
            or self.hidden_time_limit is not None
        )


@dataclass
class BaseMechanismParams:
    """Base parameters shared by all mechanism types."""

    # Negotiator constraints
    max_n_negotiators: int | None = None
    dynamic_entry: bool = False

    # Logging/debugging
    verbosity: int = 0

    # Error handling
    ignore_negotiator_exceptions: bool = False

    # Session name
    name: str | None = None


@dataclass
class SAOParams(BaseMechanismParams):
    """SAO-specific mechanism parameters."""

    # Response handling
    end_on_no_response: bool = True
    avoid_ultimatum: bool = False

    # Offer validation
    check_offers: bool = False
    enforce_issue_types: bool = False
    cast_offers: bool = False

    # Offer semantics
    offering_is_accepting: bool = True
    allow_offering_just_rejected_outcome: bool = True
    one_offer_per_step: bool = True

    # Synchronization
    sync_calls: bool = False
    max_wait: int = 2**63 - 1  # Default from negmas


@dataclass
class TAUParams(BaseMechanismParams):
    """TAU-specific mechanism parameters."""

    # Whether acceptance in any thread ends negotiation
    accept_in_any_thread: bool = True

    # Run threads in parallel
    parallel: bool = True

    # Serial TAU specific (used when parallel=False)
    cardinality: int | None = None  # Max offers per thread (None = unlimited)
    min_unique: int = 0  # Min unique offers required


@dataclass
class GBParams(BaseMechanismParams):
    """GB-specific mechanism parameters."""

    # Run in parallel
    parallel: bool = True

    # Response handling
    end_on_no_response: bool = True
    check_offers: bool = False
    enforce_issue_types: bool = False
    cast_offers: bool = False

    # Synchronization
    sync_calls: bool = False


@dataclass
class DisplayParams:
    """Display/visualization parameters for the UI."""

    # Delay between steps for real-time mode (milliseconds)
    step_delay_ms: int = 100

    # Show offer history panel
    show_offer_history: bool = True

    # Show 2D utility plot
    show_utility_plot: bool = True

    # Execution mode
    realtime_mode: bool = True  # False = batch mode


@dataclass
class MechanismConfig:
    """Complete mechanism configuration."""

    # Mechanism type
    mechanism_type: MechanismType = MechanismType.SAO

    # Deadline parameters
    deadline: DeadlineParams = field(default_factory=DeadlineParams)

    # Mechanism-specific parameters (depends on mechanism_type)
    sao_params: SAOParams = field(default_factory=SAOParams)
    tau_params: TAUParams = field(default_factory=TAUParams)
    gb_params: GBParams = field(default_factory=GBParams)

    # Display parameters
    display: DisplayParams = field(default_factory=DisplayParams)

    def get_params(self) -> BaseMechanismParams:
        """Get the params for the current mechanism type."""
        match self.mechanism_type:
            case MechanismType.SAO:
                return self.sao_params
            case MechanismType.TAU:
                return self.tau_params
            case MechanismType.GB:
                return self.gb_params

    def validate(self) -> list[str]:
        """Validate the configuration. Returns list of error messages."""
        errors = []
        type_info = MECHANISM_TYPES[self.mechanism_type]

        # Check deadline requirement
        if not type_info.allows_infinite and not self.deadline.has_deadline():
            errors.append(
                f"{type_info.name} requires at least one deadline parameter "
                "(n_steps, time_limit, pend, pend_per_second, or hidden_time_limit)"
            )

        return errors


def default_config() -> MechanismConfig:
    """Create a default mechanism configuration."""
    return MechanismConfig(
        mechanism_type=MechanismType.SAO,
        deadline=DeadlineParams(n_steps=100),
    )


# Backwards compatibility alias
MechanismParams = BaseMechanismParams


@dataclass
class VirtualMechanism:
    """A virtual mechanism - a saved configuration of a base mechanism with custom parameters.

    Virtual mechanisms allow users to create named variants of existing mechanism types
    with pre-configured parameters. They appear in the mechanism selection UI
    alongside built-in mechanisms.
    """

    # Unique identifier for this virtual mechanism
    id: str

    # Display name for this virtual mechanism
    name: str

    # The base mechanism type this is built on (e.g., "sao", "tau", "gb")
    base_type: str

    # User-friendly description
    description: str = ""

    # Tags for filtering/categorization
    tags: list[str] = field(default_factory=list)

    # Custom parameters for the mechanism (deadline, specific params, etc.)
    params: dict = field(default_factory=dict)

    # Timestamp when created (ISO format string)
    created_at: str = ""

    # Timestamp when last modified (ISO format string)
    modified_at: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "base_type": self.base_type,
            "description": self.description,
            "tags": self.tags,
            "params": self.params,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VirtualMechanism":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            base_type=data["base_type"],
            description=data.get("description", ""),
            tags=data.get("tags", []),
            params=data.get("params", {}),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
        )
