"""Service for inspecting negotiator class parameters dynamically."""

import importlib
import inspect
from dataclasses import dataclass, field
from typing import Any, get_type_hints, get_origin, get_args, Union
from pathlib import Path
import json

# Cache for parameter info to avoid repeated inspection
_PARAMETER_CACHE: dict[str, list["ParameterInfo"]] = {}

# Cache file path
CACHE_FILE = Path.home() / "negmas" / "app" / "cache" / "negotiator_params.json"

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
class ParameterInfo:
    """Information about a class parameter."""

    name: str
    type: str  # String representation of the type
    default: Any  # Default value, or None if required
    required: bool  # Whether the parameter is required
    description: str  # Description from docstring if available

    # Type hints for UI generation
    ui_type: str  # 'int', 'float', 'bool', 'string', 'choice', 'optional_int', etc.
    choices: list[str] | None = None  # For enum/literal types
    min_value: float | None = None  # For numeric types
    max_value: float | None = None  # For numeric types

    # For nested/complex types
    is_complex: bool = False  # True if this can't be easily edited in UI


def _get_type_string(annotation: Any) -> str:
    """Convert a type annotation to a readable string."""
    if annotation is inspect.Parameter.empty:
        return "Any"

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Union:
        # Handle Optional (Union[X, None])
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return f"Optional[{_get_type_string(non_none[0])}]"
        return f"Union[{', '.join(_get_type_string(a) for a in args)}]"

    if origin is not None:
        if args:
            return f"{origin.__name__}[{', '.join(_get_type_string(a) for a in args)}]"
        return origin.__name__

    if hasattr(annotation, "__name__"):
        return annotation.__name__

    return str(annotation)


def _determine_ui_type(
    annotation: Any, default: Any
) -> tuple[str, list[str] | None, bool]:
    """Determine the UI type for a parameter.

    Returns: (ui_type, choices, is_complex)
    """
    origin = get_origin(annotation)
    args = get_args(annotation)

    # Handle None/empty annotation
    if annotation is inspect.Parameter.empty:
        # Infer from default value
        if isinstance(default, bool):
            return "bool", None, False
        if isinstance(default, int):
            return "int", None, False
        if isinstance(default, float):
            return "float", None, False
        if isinstance(default, str):
            return "string", None, False
        return "string", None, True

    # Handle Optional types
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner_type, choices, is_complex = _determine_ui_type(non_none[0], default)
            # Mark as optional
            if inner_type == "int":
                return "optional_int", choices, is_complex
            if inner_type == "float":
                return "optional_float", choices, is_complex
            if inner_type == "string":
                return "optional_string", choices, is_complex
            return inner_type, choices, is_complex
        return "string", None, True

    # Handle Literal types (choices)
    if origin is type(None):
        return "optional_string", None, False

    # Check for Literal
    try:
        from typing import Literal

        if origin is Literal:
            choices = [str(a) for a in args]
            return "choice", choices, False
    except ImportError:
        pass

    # Handle basic types
    if annotation is bool:
        return "bool", None, False
    if annotation is int:
        return "int", None, False
    if annotation is float:
        return "float", None, False
    if annotation is str:
        return "string", None, False

    # Handle list/tuple/dict as complex
    if origin in (list, tuple, dict, set, frozenset):
        return "string", None, True

    # Handle common negmas types
    type_name = _get_type_string(annotation)
    if "Callable" in type_name:
        return "string", None, True
    if "UtilityFunction" in type_name or "UFun" in type_name:
        return "string", None, True
    if "Outcome" in type_name:
        return "string", None, True

    # Default to string for unknown types
    return "string", None, True


def _parse_docstring_params(docstring: str | None) -> dict[str, str]:
    """Parse parameter descriptions from a docstring."""
    if not docstring:
        return {}

    params = {}
    lines = docstring.split("\n")
    current_param = None
    current_desc = []

    in_params_section = False

    for line in lines:
        stripped = line.strip()

        # Check for Args/Parameters section
        if stripped in ("Args:", "Arguments:", "Parameters:", "Params:"):
            in_params_section = True
            continue

        # Check for end of params section
        if (
            in_params_section
            and stripped
            and stripped.endswith(":")
            and not stripped.startswith("-")
        ):
            # New section started
            if current_param:
                params[current_param] = " ".join(current_desc).strip()
            in_params_section = False
            current_param = None
            current_desc = []
            continue

        if not in_params_section:
            continue

        # Try to match parameter line: "param_name: description" or "param_name (type): description"
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()

        # Check for new parameter
        if ":" in stripped and not stripped.startswith(" "):
            # Save previous parameter
            if current_param:
                params[current_param] = " ".join(current_desc).strip()

            # Parse new parameter
            parts = stripped.split(":", 1)
            param_part = parts[0].strip()
            desc_part = parts[1].strip() if len(parts) > 1 else ""

            # Handle "param (type)" format
            if "(" in param_part:
                param_part = param_part.split("(")[0].strip()

            current_param = param_part
            current_desc = [desc_part] if desc_part else []
        elif current_param and stripped:
            # Continuation of description
            current_desc.append(stripped)

    # Save last parameter
    if current_param:
        params[current_param] = " ".join(current_desc).strip()

    return params


def _get_class_init_params(cls: type) -> list[ParameterInfo]:
    """Get all __init__ parameters from a class and its parents."""
    params = []
    seen_names = set()

    # Get the MRO (Method Resolution Order) to include parent classes
    mro = inspect.getmro(cls)

    # Collect docstrings from all classes for parameter descriptions
    all_docstrings = {}
    for klass in mro:
        if klass is object:
            continue
        if hasattr(klass, "__init__"):
            doc = klass.__init__.__doc__
            if doc:
                all_docstrings.update(_parse_docstring_params(doc))

    # Get type hints from the class
    try:
        hints = get_type_hints(cls.__init__)
    except Exception:
        hints = {}

    # Process __init__ signature
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        return params

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "args", "kwargs"):
            continue
        if param_name.startswith("_"):
            continue
        if param_name in seen_names:
            continue
        # Skip base Negotiator class parameters that are set by the app
        if param_name in IGNORED_BASE_PARAMS:
            continue

        seen_names.add(param_name)

        # Get type annotation
        annotation = hints.get(param_name, param.annotation)

        # Get default value
        if param.default is inspect.Parameter.empty:
            default = None
            required = True
        else:
            default = param.default
            required = False

        # Determine UI type
        ui_type, choices, is_complex = _determine_ui_type(annotation, default)

        # Skip very complex parameters that can't be configured via UI
        # but still include them as info

        # Get description from docstring
        description = all_docstrings.get(param_name, "")

        param_info = ParameterInfo(
            name=param_name,
            type=_get_type_string(annotation),
            default=_serialize_default(default),
            required=required,
            description=description,
            ui_type=ui_type,
            choices=choices,
            is_complex=is_complex,
        )

        params.append(param_info)

    return params


def _serialize_default(value: Any) -> Any:
    """Serialize a default value for JSON."""
    if value is None or value is inspect.Parameter.empty:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    # For complex objects, convert to string representation
    return str(value)


def get_negotiator_parameters(
    type_name: str, use_cache: bool = True
) -> list[ParameterInfo]:
    """Get configurable parameters for a negotiator type.

    Args:
        type_name: Full class path (e.g., "negmas.sao.AspirationNegotiator")
        use_cache: Whether to use cached results

    Returns:
        List of ParameterInfo for configurable parameters.
    """
    # Check memory cache first
    if use_cache and type_name in _PARAMETER_CACHE:
        return _PARAMETER_CACHE[type_name]

    # Check file cache
    if use_cache:
        cached = _load_from_file_cache(type_name)
        if cached is not None:
            _PARAMETER_CACHE[type_name] = cached
            return cached

    # Import and inspect the class
    params = _inspect_negotiator_class(type_name)

    # Cache the results
    _PARAMETER_CACHE[type_name] = params
    _save_to_file_cache(type_name, params)

    return params


def _inspect_negotiator_class(type_name: str) -> list[ParameterInfo]:
    """Actually inspect a negotiator class for its parameters."""
    parts = type_name.rsplit(".", 1)
    if len(parts) != 2:
        return []

    module_path, class_name = parts

    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name, None)
        if cls is None:
            return []

        return _get_class_init_params(cls)
    except (ImportError, AttributeError) as e:
        print(f"Error inspecting {type_name}: {e}")
        return []


def _load_from_file_cache(type_name: str) -> list[ParameterInfo] | None:
    """Load parameter info from file cache."""
    if not CACHE_FILE.exists():
        return None

    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)

        if type_name not in cache:
            return None

        data = cache[type_name]
        return [
            ParameterInfo(
                name=p["name"],
                type=p["type"],
                default=p["default"],
                required=p["required"],
                description=p["description"],
                ui_type=p["ui_type"],
                choices=p.get("choices"),
                min_value=p.get("min_value"),
                max_value=p.get("max_value"),
                is_complex=p.get("is_complex", False),
            )
            for p in data
        ]
    except (json.JSONDecodeError, KeyError):
        return None


def _save_to_file_cache(type_name: str, params: list[ParameterInfo]) -> None:
    """Save parameter info to file cache."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing cache
    cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            cache = {}

    # Add new entry
    cache[type_name] = [
        {
            "name": p.name,
            "type": p.type,
            "default": p.default,
            "required": p.required,
            "description": p.description,
            "ui_type": p.ui_type,
            "choices": p.choices,
            "min_value": p.min_value,
            "max_value": p.max_value,
            "is_complex": p.is_complex,
        }
        for p in params
    ]

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def clear_parameter_cache() -> int:
    """Clear all cached parameter info.

    Returns:
        Number of entries cleared.
    """
    global _PARAMETER_CACHE
    count = len(_PARAMETER_CACHE)
    _PARAMETER_CACHE.clear()

    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            count = max(count, len(cache))
        except json.JSONDecodeError:
            pass
        CACHE_FILE.unlink()

    return count


def clear_parameter_cache_for_type(type_name: str) -> bool:
    """Clear cached parameter info for a specific type.

    Returns:
        True if entry was found and removed.
    """
    found = False

    if type_name in _PARAMETER_CACHE:
        del _PARAMETER_CACHE[type_name]
        found = True

    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
            if type_name in cache:
                del cache[type_name]
                with open(CACHE_FILE, "w") as f:
                    json.dump(cache, f, indent=2)
                found = True
        except json.JSONDecodeError:
            pass

    return found
