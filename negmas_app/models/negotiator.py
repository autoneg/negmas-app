"""Negotiator type definitions and configuration."""

from dataclasses import dataclass, field


@dataclass
class NegotiatorSource:
    """Definition of a negotiator source (where negotiators come from)."""

    # Unique identifier for this source
    id: str

    # Display name
    name: str

    # Description
    description: str = ""

    # Supported mechanism types (e.g., ["SAO", "TAU", "GAO"])
    mechanisms: list[str] = field(default_factory=lambda: ["SAO"])

    # Whether this source requires external setup (e.g., Genius bridge)
    requires_bridge: bool = False

    # Whether this source is built-in or user-defined
    builtin: bool = True

    # For custom sources: library to import from (e.g., "negmas_llm")
    library: str | None = None

    # For custom sources: regex pattern to match class names
    class_pattern: str | None = None

    # For custom sources: explicit module and class names
    module: str | None = None
    class_names: list[str] = field(default_factory=list)


# Built-in negotiator sources
BUILTIN_SOURCES: list[NegotiatorSource] = [
    NegotiatorSource(
        id="native",
        name="NegMAS Native",
        description="Built-in negotiators from negmas.sao",
        mechanisms=["SAO", "TAU", "GAO"],
        builtin=True,
    ),
    NegotiatorSource(
        id="genius",
        name="Genius (Bridge)",
        description="ANAC competition agents via Genius bridge",
        mechanisms=["SAO"],
        requires_bridge=True,
        builtin=True,
    ),
    NegotiatorSource(
        id="negolog",
        name="Negolog",
        description="Logic-based negotiators from negmas-negolog",
        mechanisms=["SAO"],
        library="negmas_negolog",
        builtin=True,
    ),
    NegotiatorSource(
        id="genius-reimplemented",
        name="Genius Reimplemented",
        description="Python reimplementations of Genius agents",
        mechanisms=["SAO"],
        library="negmas_genius_agents",
        builtin=True,
    ),
    NegotiatorSource(
        id="llm",
        name="LLM",
        description="Large Language Model based negotiators",
        mechanisms=["SAO"],
        library="negmas_llm",
        builtin=True,
    ),
    NegotiatorSource(
        id="rl",
        name="Reinforcement Learning",
        description="RL-trained negotiators from negmas-rl",
        mechanisms=["SAO"],
        library="negmas_rl",
        builtin=True,
    ),
]


@dataclass
class NegotiatorConfig:
    """Configuration for a negotiator instance."""

    # Full class path (e.g., "negmas.sao.AspirationNegotiator")
    type_name: str

    # Display name for this instance
    name: str | None = None

    # Source ID (e.g., "native", "genius", "llm")
    source: str = "native"

    # Constructor parameters
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.name is None:
            self.name = self.type_name.split(".")[-1]


@dataclass
class NegotiatorInfo:
    """Information about an available negotiator type."""

    # Full class path
    type_name: str

    # Display name
    name: str

    # Source ID
    source: str

    # Subcategory within source (e.g., "y2019" for genius agents)
    group: str = ""

    # Description
    description: str = ""

    # Tags (e.g., "anac2019", "winner", "finalist")
    tags: list[str] = field(default_factory=list)

    # Supported mechanisms
    mechanisms: list[str] = field(default_factory=lambda: ["SAO"])

    # Whether it requires special setup (e.g., Genius bridge)
    requires_bridge: bool = False

    # Whether it's available in current environment
    available: bool = True

    # Full module path for import
    module_path: str = ""


@dataclass
class BOAComponentInfo:
    """Information about a BOA (Bidding-Opponent-Acceptance) component."""

    # Class name (e.g., "ACConst", "GBoulwareOffering")
    name: str

    # Full class path for import
    type_name: str

    # Component type: "acceptance", "offering", or "model"
    component_type: str

    # Brief description
    description: str = ""

    # Module path
    module_path: str = "negmas.gb.components"


@dataclass
class BOANegotiatorConfig:
    """Configuration for a BOA-style modular negotiator."""

    # Display name for this instance
    name: str

    # Acceptance policy class name
    acceptance_policy: str

    # Offering policy class name
    offering_policy: str

    # Opponent model class name (optional)
    opponent_model: str | None = None

    # Parameters for acceptance policy
    acceptance_params: dict = field(default_factory=dict)

    # Parameters for offering policy
    offering_params: dict = field(default_factory=dict)

    # Parameters for opponent model
    model_params: dict = field(default_factory=dict)


@dataclass
class MAPNegotiatorConfig:
    """Configuration for a MAP-style modular negotiator.

    MAPNegotiator is a more flexible version of BOANegotiator that supports:
    - Multiple opponent models (not just one)
    - Extra arbitrary components
    - Control over acceptance/offering order via acceptance_first
    """

    # Display name for this instance
    name: str

    # Acceptance policy class name
    acceptance_policy: str

    # Offering policy class name
    offering_policy: str

    # List of opponent model class names (can have multiple, unlike BOA which has one)
    models: list[str] = field(default_factory=list)

    # Extra component class names (arbitrary GBComponents)
    extra_components: list[str] = field(default_factory=list)

    # If True, acceptance is evaluated before offering; if False, offering first
    acceptance_first: bool = True

    # Parameters for acceptance policy
    acceptance_params: dict = field(default_factory=dict)

    # Parameters for offering policy
    offering_params: dict = field(default_factory=dict)

    # Parameters for each model (list in same order as models)
    model_params: list[dict] = field(default_factory=list)

    # Parameters for each extra component (list in same order as extra_components)
    extra_component_params: list[dict] = field(default_factory=list)


@dataclass
class VirtualNegotiator:
    """A virtual negotiator - a saved configuration of a base negotiator with custom parameters.

    Virtual negotiators allow users to create named variants of existing negotiators
    with pre-configured parameters. They appear in the negotiator selection UI
    alongside built-in negotiators.
    """

    # Unique identifier for this virtual negotiator
    id: str

    # Display name for this virtual negotiator
    name: str

    # The base negotiator type this is built on
    base_type_name: str

    # User-friendly description
    description: str = ""

    # Tags for filtering/categorization
    tags: list[str] = field(default_factory=list)

    # Custom parameters to pass to the base negotiator's __init__
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
            "base_type_name": self.base_type_name,
            "description": self.description,
            "tags": self.tags,
            "params": self.params,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VirtualNegotiator":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            base_type_name=data["base_type_name"],
            description=data.get("description", ""),
            tags=data.get("tags", []),
            params=data.get("params", {}),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
        )
