"""Mechanism registry - discovers and describes all available mechanism types."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ParamType(Enum):
    """Parameter type for form rendering."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    CHOICE = "choice"
    OPTIONAL_INT = "optional_int"
    OPTIONAL_FLOAT = "optional_float"
    OPTIONAL_STRING = "optional_string"
    DICT = "dict"
    LIST = "list"
    CLASS = "class"  # For type parameters like evaluator_type


@dataclass
class ParamInfo:
    """Information about a mechanism parameter."""

    name: str
    param_type: ParamType
    default: Any
    description: str
    required: bool = False
    choices: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    group: str = "general"


@dataclass
class MechanismInfo:
    """Information about a mechanism type."""

    name: str
    class_name: str
    module: str
    description: str
    base_params: list[ParamInfo] = field(default_factory=list)
    specific_params: list[ParamInfo] = field(default_factory=list)

    @property
    def full_class_path(self) -> str:
        return f"{self.module}.{self.class_name}"


# Base Mechanism parameters (from Mechanism.__init__)
BASE_MECHANISM_PARAMS: list[ParamInfo] = [
    # Deadline/Limits group
    ParamInfo(
        "n_steps",
        ParamType.OPTIONAL_INT,
        None,
        "Maximum number of negotiation rounds (None = unlimited)",
        group="limits",
    ),
    ParamInfo(
        "time_limit",
        ParamType.OPTIONAL_FLOAT,
        None,
        "Maximum wall-clock time in seconds (None = unlimited)",
        group="limits",
    ),
    ParamInfo(
        "step_time_limit",
        ParamType.OPTIONAL_FLOAT,
        None,
        "Maximum time per round in seconds",
        group="limits",
    ),
    ParamInfo(
        "negotiator_time_limit",
        ParamType.OPTIONAL_FLOAT,
        None,
        "Maximum time per negotiator in seconds",
        group="limits",
    ),
    ParamInfo(
        "hidden_time_limit",
        ParamType.FLOAT,
        float("inf"),
        "Hidden time limit not visible to negotiators",
        group="limits",
    ),
    ParamInfo(
        "pend",
        ParamType.FLOAT,
        0.0,
        "Probability of ending negotiation at any step",
        min_value=0.0,
        max_value=1.0,
        group="limits",
    ),
    ParamInfo(
        "pend_per_second",
        ParamType.FLOAT,
        0.0,
        "Probability of ending negotiation every second",
        min_value=0.0,
        max_value=1.0,
        group="limits",
    ),
    # Negotiators group
    ParamInfo(
        "max_n_negotiators",
        ParamType.OPTIONAL_INT,
        None,
        "Maximum number of negotiators allowed",
        group="negotiators",
    ),
    ParamInfo(
        "dynamic_entry",
        ParamType.BOOL,
        False,
        "Allow negotiators to enter/leave during negotiation",
        group="negotiators",
    ),
    # Behavior group
    ParamInfo(
        "extra_callbacks",
        ParamType.BOOL,
        False,
        "Enable extra callbacks (on_round_start, etc.)",
        group="behavior",
    ),
    ParamInfo(
        "ignore_negotiator_exceptions",
        ParamType.BOOL,
        False,
        "Silently ignore exceptions from negotiators",
        group="behavior",
    ),
    ParamInfo(
        "verbosity",
        ParamType.INT,
        0,
        "Verbosity level (0=silent, higher=more output)",
        min_value=0,
        max_value=3,
        group="behavior",
    ),
    # Checkpointing group
    ParamInfo(
        "checkpoint_every",
        ParamType.INT,
        1,
        "Steps between checkpoints (<=0 to disable)",
        group="checkpointing",
    ),
    ParamInfo(
        "checkpoint_folder",
        ParamType.OPTIONAL_STRING,
        None,
        "Folder for checkpoint files",
        group="checkpointing",
    ),
    ParamInfo(
        "checkpoint_filename",
        ParamType.OPTIONAL_STRING,
        None,
        "Base filename for checkpoints",
        group="checkpointing",
    ),
    ParamInfo(
        "single_checkpoint",
        ParamType.BOOL,
        True,
        "Keep only the most recent checkpoint",
        group="checkpointing",
    ),
    # Identity group
    ParamInfo(
        "name",
        ParamType.OPTIONAL_STRING,
        None,
        "Mechanism name (auto-generated if not provided)",
        group="identity",
    ),
]

# SAOMechanism specific parameters
SAO_SPECIFIC_PARAMS: list[ParamInfo] = [
    ParamInfo(
        "end_on_no_response",
        ParamType.BOOL,
        True,
        "End negotiation if a negotiator returns NO_RESPONSE",
        group="sao_behavior",
    ),
    ParamInfo(
        "check_offers",
        ParamType.BOOL,
        False,
        "Validate offers against the outcome space",
        group="sao_behavior",
    ),
    ParamInfo(
        "enforce_issue_types",
        ParamType.BOOL,
        False,
        "Enforce that issue values match their declared types",
        group="sao_behavior",
    ),
    ParamInfo(
        "cast_offers",
        ParamType.BOOL,
        False,
        "Cast issue values to correct types",
        group="sao_behavior",
    ),
    ParamInfo(
        "offering_is_accepting",
        ParamType.BOOL,
        True,
        "Making an offer implies accepting it",
        group="sao_behavior",
    ),
    ParamInfo(
        "allow_offering_just_rejected_outcome",
        ParamType.BOOL,
        True,
        "Allow offering an outcome that was just rejected",
        group="sao_behavior",
    ),
    ParamInfo(
        "one_offer_per_step",
        ParamType.BOOL,
        False,
        "Only one offer per step (atomic steps)",
        group="sao_behavior",
    ),
    ParamInfo(
        "sync_calls",
        ParamType.BOOL,
        False,
        "Synchronize calls (disables per-call timeouts)",
        group="sao_behavior",
    ),
    ParamInfo(
        "max_wait",
        ParamType.INT,
        2**31 - 1,
        "Maximum wait iterations",
        group="sao_behavior",
    ),
]

# TAUMechanism specific parameters
TAU_SPECIFIC_PARAMS: list[ParamInfo] = [
    ParamInfo(
        "accept_in_any_thread",
        ParamType.BOOL,
        True,
        "Accept in any thread (vs. requiring all threads)",
        group="tau_behavior",
    ),
    ParamInfo(
        "parallel",
        ParamType.BOOL,
        True,
        "Run negotiation threads in parallel",
        group="tau_behavior",
    ),
    ParamInfo(
        "check_offers",
        ParamType.BOOL,
        False,
        "Validate offers against outcome space",
        group="tau_behavior",
    ),
    ParamInfo(
        "enforce_issue_types",
        ParamType.BOOL,
        False,
        "Enforce issue value types",
        group="tau_behavior",
    ),
    ParamInfo(
        "cast_offers",
        ParamType.BOOL,
        False,
        "Cast values to correct types",
        group="tau_behavior",
    ),
    ParamInfo(
        "end_on_no_response",
        ParamType.BOOL,
        True,
        "End if negotiator returns no response",
        group="tau_behavior",
    ),
    ParamInfo(
        "sync_calls", ParamType.BOOL, False, "Synchronize calls", group="tau_behavior"
    ),
]

# GBMechanism specific parameters
GB_SPECIFIC_PARAMS: list[ParamInfo] = [
    ParamInfo(
        "parallel", ParamType.BOOL, True, "Run threads in parallel", group="gb_behavior"
    ),
    ParamInfo(
        "check_offers", ParamType.BOOL, False, "Validate offers", group="gb_behavior"
    ),
    ParamInfo(
        "enforce_issue_types",
        ParamType.BOOL,
        False,
        "Enforce issue types",
        group="gb_behavior",
    ),
    ParamInfo(
        "cast_offers", ParamType.BOOL, False, "Cast offer values", group="gb_behavior"
    ),
    ParamInfo(
        "end_on_no_response",
        ParamType.BOOL,
        True,
        "End on no response",
        group="gb_behavior",
    ),
    ParamInfo(
        "sync_calls", ParamType.BOOL, False, "Synchronize calls", group="gb_behavior"
    ),
]

# VetoSTMechanism specific parameters
ST_SPECIFIC_PARAMS: list[ParamInfo] = [
    ParamInfo(
        "epsilon",
        ParamType.FLOAT,
        1e-6,
        "Epsilon for floating point comparisons",
        group="st_behavior",
    ),
]


def get_all_mechanisms() -> list[MechanismInfo]:
    """Get information about all available mechanism types."""
    mechanisms = []

    # SAOMechanism - Stacked Alternating Offers
    mechanisms.append(
        MechanismInfo(
            name="SAO (Stacked Alternating Offers)",
            class_name="SAOMechanism",
            module="negmas.sao",
            description="The most common negotiation protocol where negotiators take turns making offers. Each negotiator can accept or reject the current offer and propose a counter-offer.",
            base_params=BASE_MECHANISM_PARAMS.copy(),
            specific_params=SAO_SPECIFIC_PARAMS.copy(),
        )
    )

    # TAUMechanism
    mechanisms.append(
        MechanismInfo(
            name="TAU (Threaded Alternating Ultimatums)",
            class_name="TAUMechanism",
            module="negmas.gb",
            description="A generalized bargaining mechanism where negotiators operate in parallel threads with ultimatum-style acceptance.",
            base_params=BASE_MECHANISM_PARAMS.copy(),
            specific_params=TAU_SPECIFIC_PARAMS.copy(),
        )
    )

    # GBMechanism
    mechanisms.append(
        MechanismInfo(
            name="GB (Generalized Bargaining)",
            class_name="GBMechanism",
            module="negmas.gb",
            description="A flexible bargaining mechanism supporting various evaluation strategies and constraints.",
            base_params=BASE_MECHANISM_PARAMS.copy(),
            specific_params=GB_SPECIFIC_PARAMS.copy(),
        )
    )

    # VetoSTMechanism
    mechanisms.append(
        MechanismInfo(
            name="Veto Single-Text",
            class_name="VetoSTMechanism",
            module="negmas.st",
            description="A single-text mechanism where a mediator proposes outcomes and negotiators can veto them.",
            base_params=BASE_MECHANISM_PARAMS.copy(),
            specific_params=ST_SPECIFIC_PARAMS.copy(),
        )
    )

    # HillClimbingSTMechanism
    mechanisms.append(
        MechanismInfo(
            name="Hill-Climbing Single-Text",
            class_name="HillClimbingSTMechanism",
            module="negmas.st",
            description="A single-text mechanism that uses hill climbing to explore neighboring outcomes.",
            base_params=BASE_MECHANISM_PARAMS.copy(),
            specific_params=ST_SPECIFIC_PARAMS.copy(),
        )
    )

    return mechanisms


def get_mechanism_info(class_name: str) -> MechanismInfo | None:
    """Get information about a specific mechanism type."""
    for mech in get_all_mechanisms():
        if mech.class_name == class_name:
            return mech
    return None


def get_mechanism_class(class_name: str) -> type | None:
    """Load and return the actual mechanism class."""
    info = get_mechanism_info(class_name)
    if not info:
        return None

    try:
        import importlib

        module = importlib.import_module(info.module)
        return getattr(module, info.class_name, None)
    except Exception:
        return None


def get_param_groups(params: list[ParamInfo]) -> dict[str, list[ParamInfo]]:
    """Group parameters by their group name."""
    groups: dict[str, list[ParamInfo]] = {}
    for param in params:
        if param.group not in groups:
            groups[param.group] = []
        groups[param.group].append(param)
    return groups


# Group display names and order
PARAM_GROUP_INFO = {
    "limits": {"label": "Limits & Deadlines", "order": 1, "icon": "clock"},
    "negotiators": {"label": "Negotiators", "order": 2, "icon": "users"},
    "behavior": {"label": "Behavior", "order": 3, "icon": "settings"},
    "checkpointing": {"label": "Checkpointing", "order": 4, "icon": "save"},
    "identity": {"label": "Identity", "order": 5, "icon": "tag"},
    "sao_behavior": {"label": "SAO Options", "order": 10, "icon": "sliders"},
    "tau_behavior": {"label": "TAU Options", "order": 10, "icon": "sliders"},
    "gb_behavior": {"label": "GB Options", "order": 10, "icon": "sliders"},
    "st_behavior": {"label": "Single-Text Options", "order": 10, "icon": "sliders"},
}


def get_sorted_param_groups(
    params: list[ParamInfo],
) -> list[tuple[str, dict, list[ParamInfo]]]:
    """Get parameter groups sorted by display order."""
    groups = get_param_groups(params)
    sorted_groups = []

    for group_name, param_list in groups.items():
        info = PARAM_GROUP_INFO.get(
            group_name, {"label": group_name.title(), "order": 99, "icon": "circle"}
        )
        sorted_groups.append((group_name, info, param_list))

    sorted_groups.sort(key=lambda x: x[1]["order"])
    return sorted_groups
