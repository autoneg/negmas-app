"""Module inspection service for discovering classes in Python files."""

import ast
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from negmas.inout import (
    find_domain_and_utility_files_geniusweb,
    find_domain_and_utility_files_xml,
    find_domain_and_utility_files_yaml,
)

# Parameters from base Negotiator class that should be ignored
# These are set by the app, not configured by users
IGNORED_BASE_PARAMS = frozenset(
    {
        "preferences",
        "ufun",
        "id",
        "name",
        "parent",
        "owner",
    }
)


@dataclass
class ClassInfo:
    """Information about a discovered class."""

    name: str
    module_path: str
    full_name: str  # module.ClassName format for import
    docstring: str = ""
    base_classes: list[str] = field(default_factory=list)
    is_negotiator: bool = False
    is_mechanism: bool = False
    is_boa_component: bool = False
    parameters: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ModuleInspectionResult:
    """Result of inspecting a Python module."""

    path: str
    module_name: str
    classes: list[ClassInfo] = field(default_factory=list)
    error: str | None = None


def _get_base_class_names(node: ast.ClassDef) -> list[str]:
    """Extract base class names from AST class definition."""
    bases = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            # Handle module.ClassName
            parts = []
            current = base
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            bases.append(".".join(reversed(parts)))
    return bases


def _is_negotiator_class(bases: list[str]) -> bool:
    """Check if class inherits from a negotiator base class."""
    negotiator_bases = {
        "Negotiator",
        "SAONegotiator",
        "TAUNegotiator",
        "GBNegotiator",
        "Controller",
        "SAOController",
        "NegotiationAgent",
    }
    return any(
        base in negotiator_bases or "Negotiator" in base or "Controller" in base
        for base in bases
    )


def _is_mechanism_class(bases: list[str]) -> bool:
    """Check if class inherits from a mechanism base class."""
    mechanism_bases = {
        "Mechanism",
        "SAOMechanism",
        "TAUMechanism",
        "GBMechanism",
    }
    return any(base in mechanism_bases or "Mechanism" in base for base in bases)


def _is_boa_component(bases: list[str]) -> bool:
    """Check if class is a BOA component."""
    boa_bases = {
        "AcceptanceStrategy",
        "OfferingStrategy",
        "OpponentModel",
        "AcceptancePolicy",
        "OfferingPolicy",
    }
    return any(
        base in boa_bases
        or "Acceptance" in base
        or "Offering" in base
        or "OpponentModel" in base
        for base in bases
    )


def inspect_module_ast(file_path: str) -> ModuleInspectionResult:
    """Inspect a Python module using AST (static analysis, no execution).

    This is safer but provides less information than dynamic inspection.
    """
    path = Path(file_path)
    if not path.exists():
        return ModuleInspectionResult(
            path=file_path, module_name="", error=f"File not found: {file_path}"
        )

    if not path.suffix == ".py":
        return ModuleInspectionResult(
            path=file_path, module_name="", error="Not a Python file"
        )

    module_name = path.stem

    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        classes: list[ClassInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = _get_base_class_names(node)
                docstring = ast.get_docstring(node) or ""

                # Check class type
                is_negotiator = _is_negotiator_class(bases)
                is_mechanism = _is_mechanism_class(bases)
                is_boa = _is_boa_component(bases)

                # Only include relevant classes
                if is_negotiator or is_mechanism or is_boa:
                    classes.append(
                        ClassInfo(
                            name=node.name,
                            module_path=file_path,
                            full_name=f"{module_name}.{node.name}",
                            docstring=docstring[:500] if docstring else "",
                            base_classes=bases,
                            is_negotiator=is_negotiator,
                            is_mechanism=is_mechanism,
                            is_boa_component=is_boa,
                        )
                    )

        return ModuleInspectionResult(
            path=file_path, module_name=module_name, classes=classes
        )

    except SyntaxError as e:
        return ModuleInspectionResult(
            path=file_path, module_name=module_name, error=f"Syntax error: {e}"
        )
    except Exception as e:
        return ModuleInspectionResult(
            path=file_path, module_name=module_name, error=str(e)
        )


def inspect_module_dynamic(file_path: str) -> ModuleInspectionResult:
    """Inspect a Python module by actually importing it.

    This provides more accurate information but executes the module code.
    Use with caution for untrusted code.
    """
    path = Path(file_path)
    if not path.exists():
        return ModuleInspectionResult(
            path=file_path, module_name="", error=f"File not found: {file_path}"
        )

    if not path.suffix == ".py":
        return ModuleInspectionResult(
            path=file_path, module_name="", error="Not a Python file"
        )

    module_name = path.stem

    try:
        # Import negmas to have base classes available
        try:
            from negmas.gb import GBMechanism, GBNegotiator
            from negmas.sao import SAOMechanism, SAONegotiator
        except ImportError:
            pass

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return ModuleInspectionResult(
                path=file_path, module_name=module_name, error="Could not load module"
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        classes: list[ClassInfo] = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip imported classes (only include classes defined in this module)
            if obj.__module__ != module_name:
                continue

            bases = [b.__name__ for b in obj.__mro__[1:] if b.__name__ != "object"]

            is_negotiator = _is_negotiator_class(bases)
            is_mechanism = _is_mechanism_class(bases)
            is_boa = _is_boa_component(bases)

            if is_negotiator or is_mechanism or is_boa:
                docstring = inspect.getdoc(obj) or ""

                # Get __init__ parameters
                params = []
                try:
                    sig = inspect.signature(obj.__init__)
                    for param_name, param in sig.parameters.items():
                        if param_name in ("self", "args", "kwargs"):
                            continue
                        # Skip base Negotiator class parameters
                        if param_name in IGNORED_BASE_PARAMS:
                            continue
                        params.append(
                            {
                                "name": param_name,
                                "has_default": param.default != inspect.Parameter.empty,
                                "default": (
                                    str(param.default)
                                    if param.default != inspect.Parameter.empty
                                    else None
                                ),
                            }
                        )
                except (ValueError, TypeError):
                    pass

                classes.append(
                    ClassInfo(
                        name=name,
                        module_path=file_path,
                        full_name=f"{module_name}.{name}",
                        docstring=docstring[:500] if docstring else "",
                        base_classes=bases[:5],  # Limit base classes
                        is_negotiator=is_negotiator,
                        is_mechanism=is_mechanism,
                        is_boa_component=is_boa,
                        parameters=params,
                    )
                )

        return ModuleInspectionResult(
            path=file_path, module_name=module_name, classes=classes
        )

    except Exception as e:
        return ModuleInspectionResult(
            path=file_path, module_name=module_name, error=str(e)
        )
    finally:
        # Clean up the module from sys.modules
        if module_name in sys.modules:
            del sys.modules[module_name]


def validate_scenario_path(path: str) -> dict[str, Any]:
    """Validate a scenario path (file or directory).

    Returns information about the scenario if valid.
    """
    p = Path(path)

    if not p.exists():
        return {"valid": False, "error": f"Path does not exist: {path}"}

    # Check if it's a serialized scenario file
    if p.is_file():
        if p.suffix in (".pkl", ".pickle"):
            return _validate_pickle_scenario(p)
        elif p.suffix in (".json", ".yaml", ".yml"):
            return _validate_serialized_scenario(p)
        else:
            return {
                "valid": False,
                "error": f"Unsupported file type: {p.suffix}. Expected .pkl, .json, or .yaml",
            }

    # Check if it's a scenario directory
    if p.is_dir():
        return _validate_scenario_directory(p)

    return {"valid": False, "error": "Unknown path type"}


def _validate_pickle_scenario(path: Path) -> dict[str, Any]:
    """Validate a pickled scenario file."""
    try:
        from negmas import Scenario
        from negmas.serialization import deserialize

        # Try to deserialize
        scenario = deserialize(str(path))

        if isinstance(scenario, Scenario):  # type: ignore[arg-type]
            return {
                "valid": True,
                "type": "serialized_file",
                "format": "pickle",
                "path": str(path),
                "name": path.stem,
                "n_negotiators": len(scenario.ufuns) if scenario.ufuns else 0,
            }
        else:
            return {
                "valid": False,
                "error": f"File does not contain a Scenario object (got {type(scenario).__name__})",
            }
    except Exception as e:
        return {"valid": False, "error": f"Failed to load pickle file: {e}"}


def _validate_serialized_scenario(path: Path) -> dict[str, Any]:
    """Validate a JSON/YAML serialized scenario file."""
    try:
        from negmas.serialization import deserialize

        scenario = deserialize(str(path))

        if hasattr(scenario, "outcome_space") and hasattr(scenario, "ufuns"):
            return {
                "valid": True,
                "type": "serialized_file",
                "format": path.suffix.lstrip("."),
                "path": str(path),
                "name": path.stem,
                "n_negotiators": len(scenario.ufuns) if scenario.ufuns else 0,
            }
        else:
            return {
                "valid": False,
                "error": "File does not contain a valid Scenario object",
            }
    except Exception as e:
        return {"valid": False, "error": f"Failed to load scenario file: {e}"}


def _validate_scenario_directory(path: Path) -> dict[str, Any]:
    """Validate a scenario directory."""
    try:
        # Use negmas built-in detection - try formats in order: YAML, XML (Genius), GeniusWeb
        domain_file, ufun_files = find_domain_and_utility_files_yaml(path)
        detected_format = "negmas_yaml"

        if not ufun_files:
            domain_file, ufun_files = find_domain_and_utility_files_xml(path)
            detected_format = "genius_xml"

        if not ufun_files:
            domain_file, ufun_files = find_domain_and_utility_files_geniusweb(path)
            detected_format = "geniusweb"

        if ufun_files:
            return {
                "valid": True,
                "type": "directory",
                "format": detected_format,
                "path": str(path),
                "name": path.name,
                "n_negotiators": len(ufun_files),
                "files": {
                    "domain": [str(domain_file)] if domain_file else [],
                    "ufuns": [str(f) for f in ufun_files],
                },
            }

        # Try loading with negmas Scenario.load as fallback
        from negmas import Scenario

        scenario = Scenario.load(str(path))  # type: ignore[attr-defined]
        return {
            "valid": True,
            "type": "directory",
            "format": "auto",
            "path": str(path),
            "name": path.name,
            "n_negotiators": len(scenario.ufuns) if scenario.ufuns else 0,
        }

    except Exception as e:
        return {"valid": False, "error": f"Not a valid scenario directory: {e}"}


def list_scenario_folders(base_path: str) -> list[dict[str, Any]]:
    """List potential scenario folders in a directory."""
    path = Path(base_path)
    if not path.is_dir():
        return []

    results = []
    for item in path.iterdir():
        if item.is_dir():
            validation = validate_scenario_path(str(item))
            if validation.get("valid"):
                results.append(validation)

    return results
