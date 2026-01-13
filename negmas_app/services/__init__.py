"""Business logic services for NegMAS App."""

from .scenario_loader import ScenarioLoader
from .negotiator_factory import NegotiatorFactory, NEGOTIATOR_REGISTRY, BOAFactory
from .mechanism_factory import MechanismFactory
from .session_manager import SessionManager
from .outcome_analysis import compute_outcome_space_data, compute_outcome_utilities
from .parameter_inspector import (
    get_negotiator_parameters,
    clear_parameter_cache,
    clear_parameter_cache_for_type,
    ParameterInfo,
)

# Optional services that may have additional dependencies
try:
    from .negotiation_storage import NegotiationStorageService
except ImportError:
    NegotiationStorageService = None  # type: ignore

try:
    from .tournament_manager import TournamentManager
except ImportError:
    TournamentManager = None  # type: ignore

try:
    from .tournament_storage import TournamentStorageService
except ImportError:
    TournamentStorageService = None  # type: ignore

__all__ = [
    "ScenarioLoader",
    "NegotiatorFactory",
    "NEGOTIATOR_REGISTRY",
    "BOAFactory",
    "MechanismFactory",
    "SessionManager",
    "TournamentManager",
    "NegotiationStorageService",
    "TournamentStorageService",
    "compute_outcome_space_data",
    "compute_outcome_utilities",
    "get_negotiator_parameters",
    "clear_parameter_cache",
    "clear_parameter_cache_for_type",
    "ParameterInfo",
]
