"""Negotiation definition models - complete definition of a negotiation setup.

Note: This module defines *Definition classes (NegotiatorDefinition, MechanismDefinition, etc.)
which are used for serialization and definition files. These are distinct from the *Config classes
in other model files (like NegotiatorConfig in negotiator.py, MechanismConfig in mechanism.py)
which are used for UI configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import json
import yaml
from datetime import datetime


@dataclass
class NegotiatorDefinition:
    """Definition of a single negotiator for negotiation definitions.

    Note: This is distinct from NegotiatorConfig in models/negotiator.py which
    is used for UI configuration. This class is for serialization/definition files.
    """

    class_name: str
    name: str | None = None  # Display name (auto-generated if None)
    module: str | None = None  # Module path (None = auto-discover)
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_name": self.class_name,
            "name": self.name,
            "module": self.module,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NegotiatorDefinition":
        return cls(
            class_name=data["class_name"],
            name=data.get("name"),
            module=data.get("module"),
            params=data.get("params", {}),
        )


@dataclass
class ScenarioDefinition:
    """Definition of the negotiation scenario.

    Note: This is distinct from ScenarioInfo/ScenarioConfig used elsewhere.
    This class is for serialization/definition files.
    """

    # Either load from path or define inline
    path: str | None = None  # Path to scenario folder

    # Or define outcome space inline
    issues: list[dict[str, Any]] | None = None  # Issue definitions

    # Utility functions - either from scenario or generated
    ufuns: list[dict[str, Any]] | None = None  # Ufun definitions (if not from scenario)
    generate_ufuns: bool = True  # Generate random ufuns if not provided
    ufun_type: str = "LinearAdditiveUtilityFunction"
    reserved_value_min: float = 0.0
    reserved_value_max: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "issues": self.issues,
            "ufuns": self.ufuns,
            "generate_ufuns": self.generate_ufuns,
            "ufun_type": self.ufun_type,
            "reserved_value_min": self.reserved_value_min,
            "reserved_value_max": self.reserved_value_max,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioDefinition":
        return cls(
            path=data.get("path"),
            issues=data.get("issues"),
            ufuns=data.get("ufuns"),
            generate_ufuns=data.get("generate_ufuns", True),
            ufun_type=data.get("ufun_type", "LinearAdditiveUtilityFunction"),
            reserved_value_min=data.get("reserved_value_min", 0.0),
            reserved_value_max=data.get("reserved_value_max", 0.5),
        )


@dataclass
class MechanismDefinition:
    """Definition of the negotiation mechanism.

    Note: This is distinct from MechanismConfig in models/mechanism.py which
    is used for UI configuration. This class is for serialization/definition files.
    """

    class_name: str = "SAOMechanism"
    module: str = "negmas.sao"

    # Base mechanism parameters
    n_steps: int | None = None
    time_limit: float | None = None
    step_time_limit: float | None = None
    negotiator_time_limit: float | None = None
    hidden_time_limit: float = float("inf")
    pend: float = 0.0
    pend_per_second: float = 0.0
    max_n_negotiators: int | None = None
    dynamic_entry: bool = False
    extra_callbacks: bool = True
    ignore_negotiator_exceptions: bool = False
    verbosity: int = 0
    checkpoint_every: int = 0  # Disabled by default
    checkpoint_folder: str | None = None
    checkpoint_filename: str | None = None
    single_checkpoint: bool = True
    name: str | None = None

    # Mechanism-specific parameters (stored as dict)
    specific_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "class_name": self.class_name,
            "module": self.module,
            "n_steps": self.n_steps,
            "time_limit": self.time_limit,
            "step_time_limit": self.step_time_limit,
            "negotiator_time_limit": self.negotiator_time_limit,
            "hidden_time_limit": self.hidden_time_limit
            if self.hidden_time_limit != float("inf")
            else None,
            "pend": self.pend,
            "pend_per_second": self.pend_per_second,
            "max_n_negotiators": self.max_n_negotiators,
            "dynamic_entry": self.dynamic_entry,
            "extra_callbacks": self.extra_callbacks,
            "ignore_negotiator_exceptions": self.ignore_negotiator_exceptions,
            "verbosity": self.verbosity,
            "checkpoint_every": self.checkpoint_every,
            "checkpoint_folder": self.checkpoint_folder,
            "checkpoint_filename": self.checkpoint_filename,
            "single_checkpoint": self.single_checkpoint,
            "name": self.name,
            "specific_params": self.specific_params,
        }
        # Remove None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MechanismDefinition":
        hidden = data.get("hidden_time_limit")
        return cls(
            class_name=data.get("class_name", "SAOMechanism"),
            module=data.get("module", "negmas.sao"),
            n_steps=data.get("n_steps"),
            time_limit=data.get("time_limit"),
            step_time_limit=data.get("step_time_limit"),
            negotiator_time_limit=data.get("negotiator_time_limit"),
            hidden_time_limit=hidden if hidden is not None else float("inf"),
            pend=data.get("pend", 0.0),
            pend_per_second=data.get("pend_per_second", 0.0),
            max_n_negotiators=data.get("max_n_negotiators"),
            dynamic_entry=data.get("dynamic_entry", False),
            extra_callbacks=data.get("extra_callbacks", True),
            ignore_negotiator_exceptions=data.get(
                "ignore_negotiator_exceptions", False
            ),
            verbosity=data.get("verbosity", 0),
            checkpoint_every=data.get("checkpoint_every", 0),
            checkpoint_folder=data.get("checkpoint_folder"),
            checkpoint_filename=data.get("checkpoint_filename"),
            single_checkpoint=data.get("single_checkpoint", True),
            name=data.get("name"),
            specific_params=data.get("specific_params", {}),
        )

    def get_init_kwargs(self) -> dict[str, Any]:
        """Get kwargs for mechanism __init__."""
        kwargs: dict[str, Any] = {}

        # Add base params if not default/None
        if self.n_steps is not None:
            kwargs["n_steps"] = self.n_steps
        if self.time_limit is not None:
            kwargs["time_limit"] = self.time_limit
        if self.step_time_limit is not None:
            kwargs["step_time_limit"] = self.step_time_limit
        if self.negotiator_time_limit is not None:
            kwargs["negotiator_time_limit"] = self.negotiator_time_limit
        if self.hidden_time_limit != float("inf"):
            kwargs["hidden_time_limit"] = self.hidden_time_limit
        if self.pend > 0:
            kwargs["pend"] = self.pend
        if self.pend_per_second > 0:
            kwargs["pend_per_second"] = self.pend_per_second
        if self.max_n_negotiators is not None:
            kwargs["max_n_negotiators"] = self.max_n_negotiators
        if self.dynamic_entry:
            kwargs["dynamic_entry"] = self.dynamic_entry
        if self.extra_callbacks:
            kwargs["extra_callbacks"] = self.extra_callbacks
        if self.ignore_negotiator_exceptions:
            kwargs["ignore_negotiator_exceptions"] = self.ignore_negotiator_exceptions
        if self.verbosity > 0:
            kwargs["verbosity"] = self.verbosity
        if self.checkpoint_every > 0:
            kwargs["checkpoint_every"] = self.checkpoint_every
            if self.checkpoint_folder:
                kwargs["checkpoint_folder"] = self.checkpoint_folder
            if self.checkpoint_filename:
                kwargs["checkpoint_filename"] = self.checkpoint_filename
            kwargs["single_checkpoint"] = self.single_checkpoint
        if self.name:
            kwargs["name"] = self.name

        # Add mechanism-specific params
        kwargs.update(self.specific_params)

        return kwargs


@dataclass
class ExecutionDefinition:
    """Definition for how to run the negotiation."""

    mode: str = "batch"  # "batch" or "realtime"
    step_delay: float = 0.3  # Delay between steps in realtime mode
    show_plot: bool = True
    show_history: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "step_delay": self.step_delay,
            "show_plot": self.show_plot,
            "show_history": self.show_history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionDefinition":
        return cls(
            mode=data.get("mode", "batch"),
            step_delay=data.get("step_delay", 0.3),
            show_plot=data.get("show_plot", True),
            show_history=data.get("show_history", True),
        )


@dataclass
class NegotiationDefinition:
    """Complete definition of a negotiation setup."""

    # Metadata
    id: str | None = None
    name: str = "Untitled Negotiation"
    description: str = ""
    created_at: str | None = None
    updated_at: str | None = None
    tags: list[str] = field(default_factory=list)

    # Configuration
    mechanism: MechanismDefinition = field(default_factory=MechanismDefinition)
    scenario: ScenarioDefinition = field(default_factory=ScenarioDefinition)
    negotiators: list[NegotiatorDefinition] = field(default_factory=list)
    execution: ExecutionDefinition = field(default_factory=ExecutionDefinition)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "mechanism": self.mechanism.to_dict(),
            "scenario": self.scenario.to_dict(),
            "negotiators": [n.to_dict() for n in self.negotiators],
            "execution": self.execution.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NegotiationDefinition":
        return cls(
            id=data.get("id"),
            name=data.get("name", "Untitled Negotiation"),
            description=data.get("description", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            tags=data.get("tags", []),
            mechanism=MechanismDefinition.from_dict(data.get("mechanism", {})),
            scenario=ScenarioDefinition.from_dict(data.get("scenario", {})),
            negotiators=[
                NegotiatorDefinition.from_dict(n) for n in data.get("negotiators", [])
            ],
            execution=ExecutionDefinition.from_dict(data.get("execution", {})),
        )

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "NegotiationDefinition":
        """Load from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, json_str: str) -> "NegotiationDefinition":
        """Load from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save(self, path: str | Path, format: str = "yaml") -> None:
        """Save to file."""
        path = Path(path)
        self.updated_at = datetime.now().isoformat()

        if format == "yaml":
            path.write_text(self.to_yaml())
        else:
            path.write_text(self.to_json())

    @classmethod
    def load(cls, path: str | Path) -> "NegotiationDefinition":
        """Load from file (auto-detects format)."""
        path = Path(path)
        content = path.read_text()

        if path.suffix in (".yaml", ".yml"):
            return cls.from_yaml(content)
        else:
            return cls.from_json(content)

    def validate(self) -> list[str]:
        """Validate the definition and return list of errors."""
        errors = []

        # Check mechanism
        if not self.mechanism.class_name:
            errors.append("Mechanism class name is required")

        # Check that we have either scenario path or issues defined
        if not self.scenario.path and not self.scenario.issues:
            errors.append("Either scenario path or issues must be defined")

        # Check negotiators
        if not self.negotiators:
            errors.append("At least one negotiator is required")

        # Check limits - at least one limit should be set
        if (
            self.mechanism.n_steps is None
            and self.mechanism.time_limit is None
            and self.mechanism.pend == 0
            and self.mechanism.pend_per_second == 0
        ):
            errors.append(
                "At least one limit (n_steps, time_limit, pend, or pend_per_second) should be set"
            )

        return errors
