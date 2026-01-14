"""Module inspection service for discovering classes in Python files."""

import ast
import importlib.util
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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

        if isinstance(scenario, Scenario):
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
        # Check for GENIUS XML format
        domain_xml = list(path.glob("*domain*.xml")) + list(path.glob("*Domain*.xml"))
        if domain_xml:
            ufun_files = [f for f in path.glob("*.xml") if f not in domain_xml]
            return {
                "valid": True,
                "type": "directory",
                "format": "genius_xml",
                "path": str(path),
                "name": path.name,
                "n_negotiators": len(ufun_files),
                "files": {
                    "domain": [str(f) for f in domain_xml],
                    "ufuns": [str(f) for f in ufun_files],
                },
            }

        # Check for negmas YAML format
        domain_yaml = list(path.glob("*domain*.yaml")) + list(path.glob("*domain*.yml"))
        if domain_yaml:
            ufun_files = [
                f
                for f in path.glob("*.yaml")
                if f not in domain_yaml and "_stats" not in f.name
            ]
            ufun_files += [
                f
                for f in path.glob("*.yml")
                if f not in domain_yaml and "_stats" not in f.name
            ]
            return {
                "valid": True,
                "type": "directory",
                "format": "negmas_yaml",
                "path": str(path),
                "name": path.name,
                "n_negotiators": len(ufun_files),
                "files": {
                    "domain": [str(f) for f in domain_yaml],
                    "ufuns": [str(f) for f in ufun_files],
                },
            }

        # Try loading with negmas Scenario.load
        from negmas import Scenario

        scenario = Scenario.load(str(path))
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
