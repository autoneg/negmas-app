"""Service for managing the negmas registry integration.

This service ensures that:
1. Virtual negotiators are registered in the negmas negotiator_registry
2. Virtual mechanisms are registered in the negmas mechanism_registry
3. Custom path negotiators/mechanisms are also registered
4. All registrations happen at startup and when items are created/deleted

Uses the new negmas registry API with:
- params field for storing constructor parameters
- source field for identifying origin ("app" for virtual items)
- create() method for instantiation with params
- batch registration/unregistration
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from negmas import Mechanism, Negotiator
from negmas.registry import (
    mechanism_registry,
    negotiator_registry,
)

if TYPE_CHECKING:
    from ..models.mechanism import VirtualMechanism
    from ..models.negotiator import VirtualNegotiator


# Track what we've registered so we can unregister on delete
# Maps virtual item id -> registry key (the key returned by register())
_registered_virtual_negotiators: dict[str, str] = {}
_registered_virtual_mechanisms: dict[str, str] = {}
_registered_custom_modules: set[str] = set()


def _get_class_by_name(full_type_name: str) -> type | None:
    """Get a class by its full type name (e.g., 'negmas.sao.AspirationNegotiator')."""
    try:
        parts = full_type_name.rsplit(".", 1)
        if len(parts) == 2:
            module_name, class_name = parts
            module = importlib.import_module(module_name)
            return getattr(module, class_name, None)
        return None
    except (ImportError, AttributeError):
        return None


def _get_base_class_for_negotiator(vn: VirtualNegotiator) -> type | None:
    """Get the base class for a virtual negotiator."""
    # First try direct import
    base_cls = _get_class_by_name(vn.base_type_name)
    if base_cls is not None:
        return base_cls

    # Try from registry by full type name
    info = negotiator_registry.get_by_class(vn.base_type_name)
    if info is not None:
        return info.cls

    # Try by short name
    matches = negotiator_registry.get_by_short_name(vn.base_type_name)
    if matches:
        return matches[0].cls

    return None


def _get_base_class_for_mechanism(vm: VirtualMechanism) -> type | None:
    """Get the base class for a virtual mechanism."""
    # Map base_type to actual class
    base_type_map = {
        "sao": "negmas.sao.SAOMechanism",
        "tau": "negmas.sao.SAOMechanism",  # TAU uses SAOMechanism with different params
        "gb": "negmas.gb.GBMechanism",
    }

    full_type_name = base_type_map.get(vm.base_type, vm.base_type)
    base_cls = _get_class_by_name(full_type_name)
    if base_cls is not None:
        return base_cls

    # Try from registry
    info = mechanism_registry.get_by_class(vm.base_type)
    if info is not None:
        return info.cls

    matches = mechanism_registry.get_by_short_name(vm.base_type)
    if matches:
        return matches[0].cls

    return None


def register_virtual_negotiator(
    vn: VirtualNegotiator, source: str = "app"
) -> str | None:
    """Register a virtual negotiator in the negmas registry.

    Uses the new negmas registry API with params field to store constructor
    parameters, enabling use of registry.create() for instantiation.

    Args:
        vn: The virtual negotiator to register
        source: Source identifier (default "app", or custom name for user sources)

    Returns:
        The registry key if successful, None otherwise
    """
    if not vn.enabled:
        return None

    base_cls = _get_base_class_for_negotiator(vn)
    if base_cls is None:
        print(
            f"Warning: Could not find base class for virtual negotiator {vn.name}: {vn.base_type_name}"
        )
        return None

    try:
        # Build tags from the virtual negotiator's tags plus some defaults
        tags = set(vn.tags)
        tags.add("virtual")
        tags.add("app")

        # Get base class info to inherit some tags
        base_info = negotiator_registry.get_by_class(base_cls)
        if base_info is not None:
            # Inherit mechanism compatibility tags
            for tag in base_info.tags:
                if tag in ("sao", "gb", "tau", "propose", "respond"):
                    tags.add(tag)

        # Register using the new API with params field
        # The params will be used by registry.create() to instantiate
        key = negotiator_registry.register(
            base_cls,
            short_name=vn.name,
            source=source,
            params=dict(vn.params),
            tags=tags,
        )

        _registered_virtual_negotiators[vn.id] = key
        return key
    except Exception as e:
        print(f"Error registering virtual negotiator {vn.name}: {e}")
        return None


def unregister_virtual_negotiator(vn_id: str) -> bool:
    """Unregister a virtual negotiator from the negmas registry.

    Args:
        vn_id: The ID of the virtual negotiator to unregister

    Returns:
        True if unregistration was successful
    """
    key = _registered_virtual_negotiators.get(vn_id)
    if key is None:
        return False

    try:
        result = negotiator_registry.unregister(key)
        if result:
            del _registered_virtual_negotiators[vn_id]
        return result
    except Exception as e:
        print(f"Error unregistering virtual negotiator {vn_id}: {e}")
        return False


def register_virtual_mechanism(vm: VirtualMechanism, source: str = "app") -> str | None:
    """Register a virtual mechanism in the negmas registry.

    Args:
        vm: The virtual mechanism to register
        source: Source identifier (default "app")

    Returns:
        The registry key if successful, None otherwise
    """
    base_cls = _get_base_class_for_mechanism(vm)
    if base_cls is None:
        print(
            f"Warning: Could not find base class for virtual mechanism {vm.name}: {vm.base_type}"
        )
        return None

    try:
        tags = set(vm.tags)
        tags.add("virtual")
        tags.add("app")

        key = mechanism_registry.register(
            base_cls,
            short_name=vm.name,
            source=source,
            params=dict(vm.params),
            tags=tags,
        )

        _registered_virtual_mechanisms[vm.id] = key
        return key
    except Exception as e:
        print(f"Error registering virtual mechanism {vm.name}: {e}")
        return None


def unregister_virtual_mechanism(vm_id: str) -> bool:
    """Unregister a virtual mechanism from the negmas registry."""
    key = _registered_virtual_mechanisms.get(vm_id)
    if key is None:
        return False

    try:
        result = mechanism_registry.unregister(key)
        if result:
            del _registered_virtual_mechanisms[vm_id]
        return result
    except Exception as e:
        print(f"Error unregistering virtual mechanism {vm_id}: {e}")
        return False


def get_negotiator_registry_key(vn_id: str) -> str | None:
    """Get the registry key for a virtual negotiator.

    Args:
        vn_id: The virtual negotiator ID

    Returns:
        The registry key if registered, None otherwise
    """
    return _registered_virtual_negotiators.get(vn_id)


def get_mechanism_registry_key(vm_id: str) -> str | None:
    """Get the registry key for a virtual mechanism.

    Args:
        vm_id: The virtual mechanism ID

    Returns:
        The registry key if registered, None otherwise
    """
    return _registered_virtual_mechanisms.get(vm_id)


def create_negotiator(key_or_name: str, **override_params) -> Any:
    """Create a negotiator instance using the registry.

    This uses the registry's create() method which merges stored params
    with any override params provided.

    Args:
        key_or_name: Registry key, short name, or full type name
        **override_params: Parameters to override stored params

    Returns:
        A negotiator instance

    Raises:
        KeyError: If no registration found
    """
    return negotiator_registry.create(key_or_name, **override_params)


def create_mechanism(key_or_name: str, **override_params) -> Any:
    """Create a mechanism instance using the registry.

    Args:
        key_or_name: Registry key, short name, or full type name
        **override_params: Parameters to override stored params

    Returns:
        A mechanism instance

    Raises:
        KeyError: If no registration found
    """
    return mechanism_registry.create(key_or_name, **override_params)


def register_custom_module(module_path: str | Path, source: str = "app") -> int:
    """Register all negotiators and mechanisms from a custom module path.

    Args:
        module_path: Path to a Python file or directory containing negotiator/mechanism classes
        source: Source identifier for tracking

    Returns:
        Number of classes registered
    """
    module_path = Path(module_path)
    if not module_path.exists():
        return 0

    registered = 0

    # Add parent directory to sys.path temporarily
    parent_dir = str(module_path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        _registered_custom_modules.add(parent_dir)

    try:
        if module_path.is_file() and module_path.suffix == ".py":
            # Import single file
            module_name = module_path.stem
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                registered += _register_from_module(module, source)
        elif module_path.is_dir():
            # Import all Python files in directory
            for py_file in module_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                try:
                    module_name = py_file.stem
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                        registered += _register_from_module(module, source)
                except Exception as e:
                    print(f"Error loading module {py_file}: {e}")
    except Exception as e:
        print(f"Error registering custom module {module_path}: {e}")

    return registered


def _register_from_module(module: Any, source: str = "app") -> int:
    """Register negotiators and mechanisms from a module."""
    import inspect

    registered = 0

    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Skip private classes and imported classes
        if name.startswith("_"):
            continue
        if obj.__module__ != module.__name__:
            continue

        try:
            if (
                isinstance(obj, type)
                and issubclass(obj, Negotiator)  # type: ignore[arg-type]
                and obj is not Negotiator
            ):
                negotiator_registry.register(
                    obj, short_name=name, source=source, tags={"custom", "user"}
                )
                registered += 1
            elif (
                isinstance(obj, type)
                and issubclass(obj, Mechanism)  # type: ignore[arg-type]
                and obj is not Mechanism
            ):
                mechanism_registry.register(
                    obj, short_name=name, source=source, tags={"custom", "user"}
                )
                registered += 1
        except Exception as e:
            print(f"Error registering {name}: {e}")

    return registered


def register_all_virtual_negotiators() -> int:
    """Register all enabled virtual negotiators in the negmas registry.

    Returns:
        Number of virtual negotiators registered
    """
    from .virtual_negotiator_service import VirtualNegotiatorService

    count = 0
    for vn in VirtualNegotiatorService.list_all(include_disabled=False):
        if register_virtual_negotiator(vn):
            count += 1

    return count


def register_all_virtual_mechanisms() -> int:
    """Register all virtual mechanisms in the negmas registry.

    Returns:
        Number of virtual mechanisms registered
    """
    from .virtual_mechanism_service import VirtualMechanismService

    count = 0
    for vm in VirtualMechanismService.list_all():
        if register_virtual_mechanism(vm):
            count += 1

    return count


def register_all_custom_paths() -> int:
    """Register negotiators/mechanisms from all configured custom paths.

    Returns:
        Number of classes registered
    """
    from .settings_service import SettingsService

    sources = SettingsService.load_negotiator_sources()
    count = 0

    # Register from custom negotiator sources
    for custom_source in sources.custom_sources:
        path = getattr(custom_source, "path", None)
        if path:
            # Use the source name if available, otherwise "app"
            source_name = getattr(custom_source, "name", None) or "app"
            count += register_custom_module(path, source=source_name)

    return count


def initialize_registry() -> dict[str, int]:
    """Initialize the registry with all virtual and custom items.

    This should be called at application startup.

    Returns:
        Dict with counts of registered items by type
    """
    results = {
        "virtual_negotiators": register_all_virtual_negotiators(),
        "virtual_mechanisms": register_all_virtual_mechanisms(),
        "custom_modules": register_all_custom_paths(),
    }

    total = sum(results.values())
    if total > 0:
        print(
            f"Registry initialized: {results['virtual_negotiators']} virtual negotiators, "
            f"{results['virtual_mechanisms']} virtual mechanisms, "
            f"{results['custom_modules']} custom module classes"
        )

    return results


def get_registered_virtual_negotiators() -> dict[str, str]:
    """Get the mapping of virtual negotiator IDs to registry keys."""
    return _registered_virtual_negotiators.copy()


def get_registered_virtual_mechanisms() -> dict[str, str]:
    """Get the mapping of virtual mechanism IDs to registry keys."""
    return _registered_virtual_mechanisms.copy()


def _create_virtual_negotiator_class(vn: VirtualNegotiator) -> type | None:
    """Create a class for a virtual negotiator that applies stored params on init.

    This creates a subclass of the base negotiator that automatically applies
    the stored parameters when instantiated. This is used by negotiator_factory
    to resolve virtual negotiators.

    Args:
        vn: The virtual negotiator configuration

    Returns:
        A class that when instantiated will create a negotiator with the stored params,
        or None if the base class cannot be found.
    """
    base_cls = _get_base_class_for_negotiator(vn)
    if base_cls is None:
        return None

    # Create a subclass that applies the stored params
    stored_params = dict(vn.params)

    class VirtualNegotiatorClass(base_cls):  # type: ignore[valid-type, misc]
        """Dynamically created class for virtual negotiator."""

        # Store reference to original config for debugging
        _virtual_negotiator_id = vn.id
        _virtual_negotiator_name = vn.name

        def __init__(self, **kwargs):
            # Merge stored params with any override params
            merged = {**stored_params, **kwargs}
            super().__init__(**merged)

    # Set meaningful class name and module
    VirtualNegotiatorClass.__name__ = f"Virtual_{vn.name.replace(' ', '_')}"
    VirtualNegotiatorClass.__qualname__ = VirtualNegotiatorClass.__name__

    return VirtualNegotiatorClass


# Batch operations using the new registry API


def register_virtual_negotiators_batch(
    negotiators: list[VirtualNegotiator], source: str = "app"
) -> list[str]:
    """Register multiple virtual negotiators at once.

    Args:
        negotiators: List of virtual negotiators to register
        source: Source identifier

    Returns:
        List of registry keys for successful registrations
    """
    registrations: list[dict[str, Any]] = []
    valid_negotiators: list[VirtualNegotiator] = []

    for vn in negotiators:
        if not vn.enabled:
            continue
        base_cls = _get_base_class_for_negotiator(vn)
        if base_cls is None:
            continue

        tags: set[str] = set(vn.tags)
        tags.add("virtual")
        tags.add("app")

        # Get base class info to inherit some tags
        base_info = negotiator_registry.get_by_class(base_cls)
        if base_info is not None:
            for tag in base_info.tags:
                if tag in ("sao", "gb", "tau", "propose", "respond"):
                    tags.add(tag)

        registrations.append(
            {
                "cls": base_cls,
                "short_name": vn.name,
                "source": source,
                "params": dict(vn.params),
                "tags": tags,
            }
        )
        valid_negotiators.append(vn)

    if not registrations:
        return []

    keys = negotiator_registry.register_many(registrations)

    # Track the registrations
    for i, vn in enumerate(valid_negotiators):
        if i < len(keys):
            _registered_virtual_negotiators[vn.id] = keys[i]

    return keys


def unregister_virtual_negotiators_batch(vn_ids: list[str]) -> int:
    """Unregister multiple virtual negotiators at once.

    Args:
        vn_ids: List of virtual negotiator IDs to unregister

    Returns:
        Number of successful unregistrations
    """
    keys_to_remove: list[str] = []
    for vn_id in vn_ids:
        key = _registered_virtual_negotiators.get(vn_id)
        if key:
            keys_to_remove.append(key)

    if not keys_to_remove:
        return 0

    count = negotiator_registry.unregister_many(keys_to_remove)  # type: ignore[arg-type]

    # Update tracking
    for vn_id in vn_ids:
        _registered_virtual_negotiators.pop(vn_id, None)

    return count
