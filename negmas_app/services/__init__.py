"""Business logic services for NegMAS App."""

from .scenario_loader import ScenarioLoader, clear_scenario_cache
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
from .virtual_negotiator_service import VirtualNegotiatorService
from .virtual_mechanism_service import VirtualMechanismService
from .module_inspector import (
    inspect_module_ast,
    inspect_module_dynamic,
    validate_scenario_path,
    list_scenario_folders,
    ClassInfo,
    ModuleInspectionResult,
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
    "clear_scenario_cache",
    "NegotiatorFactory",
    "NEGOTIATOR_REGISTRY",
    "BOAFactory",
    "MechanismFactory",
    "SessionManager",
    "TournamentManager",
    "NegotiationStorageService",
    "TournamentStorageService",
    "VirtualNegotiatorService",
    "VirtualMechanismService",
    "compute_outcome_space_data",
    "compute_outcome_utilities",
    "get_negotiator_parameters",
    "clear_parameter_cache",
    "clear_parameter_cache_for_type",
    "ParameterInfo",
    "inspect_module_ast",
    "inspect_module_dynamic",
    "validate_scenario_path",
    "list_scenario_folders",
    "ClassInfo",
    "ModuleInspectionResult",
]
