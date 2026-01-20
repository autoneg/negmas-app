"""Negotiator discovery and creation service.

Discovers and manages negotiators from multiple sources:
- native: Built-in negmas.sao negotiators
- genius: Genius bridge negotiators (ANAC competition agents)
- negolog: Logic-based negotiators from negmas-negolog
- genius-reimplemented: Python reimplementations from negmas-genius-agents
- llm: LLM-based negotiators from negmas-llm
- rl: Reinforcement learning negotiators from negmas-rl
- custom: User-defined sources from settings
"""

import importlib
import importlib.util
import inspect
import re
from dataclasses import dataclass

from negmas import Scenario
from negmas.sao import SAONegotiator
from negmas.preferences import UtilityFunction

from ..models import (
    NegotiatorConfig,
    NegotiatorInfo,
    NegotiatorSource,
    BUILTIN_SOURCES,
    BOAComponentInfo,
    BOANegotiatorConfig,
)
from .settings_service import SettingsService


@dataclass
class NegotiatorEntry:
    """Registry entry for a negotiator type."""

    cls: type | None  # None for lazy-loaded entries
    info: NegotiatorInfo


# Registry of discovered negotiators: full type_name -> NegotiatorEntry
NEGOTIATOR_REGISTRY: dict[str, NegotiatorEntry] = {}

# Cache for package availability checks
_PACKAGE_AVAILABLE_CACHE: dict[str, bool] = {}


def _is_package_available(package_name: str) -> bool:
    """Check if a package is importable."""
    if package_name in _PACKAGE_AVAILABLE_CACHE:
        return _PACKAGE_AVAILABLE_CACHE[package_name]

    try:
        spec = importlib.util.find_spec(package_name)
        available = spec is not None
    except (ModuleNotFoundError, ValueError):
        available = False

    _PACKAGE_AVAILABLE_CACHE[package_name] = available
    return available


def _discover_native_negotiators() -> list[NegotiatorEntry]:
    """Discover built-in negmas.sao negotiators."""
    entries = []

    # Core SAO negotiators with descriptions
    negotiators = [
        ("AspirationNegotiator", "Aspiration", "Time-based aspiration negotiator"),
        ("NaiveTitForTatNegotiator", "Naive TitForTat", "Simple tit-for-tat strategy"),
        ("SimpleTitForTatNegotiator", "Simple TitForTat", "Simplified tit-for-tat"),
        ("MiCRONegotiator", "MiCRO", "Monotonic Concession with Rational Offers"),
        ("NiceNegotiator", "Nice", "Always accepts offers above reservation"),
        ("ToughNegotiator", "Tough", "Never concedes, always offers best"),
        ("RandomNegotiator", "Random", "Random offers, random acceptance"),
        (
            "RandomAlwaysAcceptingNegotiator",
            "Random Accepting",
            "Random offers, always accepts",
        ),
        ("BoulwareTBNegotiator", "Boulware", "Concedes slowly at first, faster later"),
        ("ConcederTBNegotiator", "Conceder", "Concedes quickly at first, slower later"),
        ("LinearTBNegotiator", "Linear", "Linear time-based concession"),
        ("TimeBasedConcedingNegotiator", "Time-Based", "Generic time-based concession"),
    ]

    try:
        from negmas import sao

        for class_name, display_name, description in negotiators:
            if hasattr(sao, class_name):
                cls = getattr(sao, class_name)
                type_name = f"negmas.sao.{class_name}"
                info = NegotiatorInfo(
                    type_name=type_name,
                    name=display_name,
                    source="native",
                    group="core",
                    description=description,
                    tags=["builtin", "sao"],
                    mechanisms=["SAO", "TAU", "GAO"],
                    requires_bridge=False,
                    available=True,
                    module_path="negmas.sao",
                )
                entries.append(NegotiatorEntry(cls=cls, info=info))
    except ImportError:
        pass

    return entries


def _discover_genius_negotiators() -> list[NegotiatorEntry]:
    """Discover Genius bridge negotiators by year/category."""
    entries = []

    if not _is_package_available("negmas.genius"):
        return entries

    try:
        from negmas.genius.gnegotiators.basic import GeniusNegotiator
    except ImportError:
        return entries

    # Module names to scan
    modules = [
        "y2010",
        "y2011",
        "y2012",
        "y2013",
        "y2014",
        "y2015",
        "y2016",
        "y2017",
        "y2018",
        "y2019",
        "basic",
        "others",
    ]

    for module_name in modules:
        try:
            mod = importlib.import_module(f"negmas.genius.gnegotiators.{module_name}")

            for name, cls in inspect.getmembers(mod, inspect.isclass):
                # Skip if not a GeniusNegotiator subclass or is GeniusNegotiator itself
                if name == "GeniusNegotiator" or not issubclass(cls, GeniusNegotiator):
                    continue

                # Extract description from docstring
                description = cls.__doc__.strip() if cls.__doc__ else ""

                type_name = f"negmas.genius.gnegotiators.{module_name}.{name}"
                info = NegotiatorInfo(
                    type_name=type_name,
                    name=name,
                    source="genius",
                    group=module_name,
                    description=description,
                    tags=["genius", "bridge", module_name],
                    mechanisms=["SAO"],
                    requires_bridge=True,
                    available=True,
                    module_path=f"negmas.genius.gnegotiators.{module_name}",
                )
                entries.append(NegotiatorEntry(cls=cls, info=info))
        except ImportError:
            continue

    return entries


def _discover_from_library(
    source_id: str,
    library: str,
    pattern: str | None = None,
    module: str | None = None,
    class_names: list[str] | None = None,
    mechanisms: list[str] | None = None,
    requires_bridge: bool = False,
) -> list[NegotiatorEntry]:
    """Discover negotiators from a library using pattern or explicit class names."""
    entries = []
    mechanisms = mechanisms or ["SAO"]

    if not _is_package_available(library):
        return entries

    try:
        lib = importlib.import_module(library)
    except ImportError:
        return entries

    if class_names and module:
        # Explicit class names in a specific module
        try:
            mod = importlib.import_module(module)
            for class_name in class_names:
                if hasattr(mod, class_name):
                    cls = getattr(mod, class_name)
                    type_name = f"{module}.{class_name}"
                    info = NegotiatorInfo(
                        type_name=type_name,
                        name=class_name,
                        source=source_id,
                        group="",
                        description="",
                        tags=[source_id],
                        mechanisms=mechanisms,
                        requires_bridge=requires_bridge,
                        available=True,
                        module_path=module,
                    )
                    entries.append(NegotiatorEntry(cls=cls, info=info))
        except ImportError:
            pass
    elif module:
        # Scan a specific module for SAONegotiator subclasses
        try:
            mod = importlib.import_module(module)
            for name in dir(mod):
                obj = getattr(mod, name)
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, SAONegotiator)
                    and obj is not SAONegotiator
                    and not name.startswith("_")
                ):
                    type_name = f"{module}.{name}"
                    info = NegotiatorInfo(
                        type_name=type_name,
                        name=name,
                        source=source_id,
                        group="",
                        description="",
                        tags=[source_id],
                        mechanisms=mechanisms,
                        requires_bridge=requires_bridge,
                        available=True,
                        module_path=module,
                    )
                    entries.append(NegotiatorEntry(cls=obj, info=info))
        except ImportError:
            pass
    elif pattern:
        # Regex pattern matching across library
        regex = re.compile(pattern)
        for name in dir(lib):
            if regex.match(name):
                cls = getattr(lib, name)
                if inspect.isclass(cls):
                    type_name = f"{library}.{name}"
                    info = NegotiatorInfo(
                        type_name=type_name,
                        name=name,
                        source=source_id,
                        group="",
                        description="",
                        tags=[source_id],
                        mechanisms=mechanisms,
                        requires_bridge=requires_bridge,
                        available=True,
                        module_path=library,
                    )
                    entries.append(NegotiatorEntry(cls=cls, info=info))
    else:
        # Try to find all SAONegotiator subclasses at top level
        for name in dir(lib):
            obj = getattr(lib, name)
            if (
                inspect.isclass(obj)
                and issubclass(obj, SAONegotiator)
                and obj is not SAONegotiator
            ):
                type_name = f"{library}.{name}"
                info = NegotiatorInfo(
                    type_name=type_name,
                    name=name,
                    source=source_id,
                    group="",
                    description="",
                    tags=[source_id],
                    mechanisms=mechanisms,
                    requires_bridge=requires_bridge,
                    available=True,
                    module_path=library,
                )
                entries.append(NegotiatorEntry(cls=obj, info=info))

    return entries


def _discover_from_negmas_registry() -> list[NegotiatorEntry]:
    """Discover negotiators from negmas built-in registry.

    This provides rich metadata including tags, anac_year, etc.
    """
    entries = []
    try:
        from negmas import negotiator_registry

        for key, info in negotiator_registry.items():
            if info is None:
                continue

            # Determine source based on tags
            tags = list(info.tags) if info.tags else []

            # Extract ANAC year from tags (format: "anac-2019")
            anac_year = None
            for tag in tags:
                if tag.startswith("anac-"):
                    try:
                        anac_year = int(tag.split("-")[1])
                    except (IndexError, ValueError):
                        pass

            # Determine source based on tags
            if "genius" in tags:
                source = "genius"
                group = f"y{anac_year}" if anac_year else "other"
            elif "builtin" in tags or "native" in tags:
                source = "native"
                group = "core"
            else:
                # Use the info.source field from the registry
                source = info.source if info.source != "unknown" else "native"
                group = ""

            # Determine module_path from full_type_name
            module_path = ""
            if info.full_type_name:
                module_path = info.full_type_name.rsplit(".", 1)[0]

            # Use full_type_name as the primary type_name (this is correct and importable)
            type_name = info.full_type_name

            # Extract description
            description = ""
            if anac_year:
                description = f"ANAC {anac_year}"
            elif hasattr(info.cls, "__doc__") and info.cls.__doc__:
                # Get first line of docstring
                description = info.cls.__doc__.split("\n")[0].strip()

            # Create our NegotiatorInfo from negmas RegistryInfo
            neg_info = NegotiatorInfo(
                type_name=type_name,
                name=info.short_name
                or key.split("#")[0],  # Remove hash suffix for display
                source=source,
                group=group,
                description=description,
                tags=tags,
                mechanisms=["SAO", "TAU", "GAO"] if "sao" in tags else ["SAO"],
                requires_bridge="genius" in tags and "builtin" not in tags,
                available=True,
                module_path=module_path,
            )
            entries.append(NegotiatorEntry(cls=info.cls, info=neg_info))
    except ImportError:
        pass
    except Exception as e:
        # Log but don't fail - fall back to manual discovery
        print(f"Warning: Failed to load from negmas registry: {e}")
        import traceback

        traceback.print_exc()

    return entries


def _discover_all_negotiators() -> None:
    """Discover all negotiators from all sources and populate the registry.

    Uses negmas built-in registry as primary source (has rich metadata),
    then supplements with additional sources not in the registry.
    """
    global NEGOTIATOR_REGISTRY
    NEGOTIATOR_REGISTRY.clear()

    # Load settings to check disabled sources and custom sources
    settings = SettingsService.load_negotiator_sources()
    disabled = set(settings.disabled_sources)

    # Track which sources we've populated from registry
    registry_sources_found: set[str] = set()

    # First: Try negmas built-in registry (preferred - has rich metadata)
    if "native" not in disabled or "genius" not in disabled:
        for entry in _discover_from_negmas_registry():
            NEGOTIATOR_REGISTRY[entry.info.type_name] = entry
            registry_sources_found.add(entry.info.source)

    # Fall back to manual discovery if registry didn't have them
    # Native negotiators (if registry didn't provide)
    if "native" not in disabled and "native" not in registry_sources_found:
        for entry in _discover_native_negotiators():
            NEGOTIATOR_REGISTRY[entry.info.type_name] = entry

    # Genius bridge negotiators (if registry didn't provide)
    if "genius" not in disabled and "genius" not in registry_sources_found:
        for entry in _discover_genius_negotiators():
            NEGOTIATOR_REGISTRY[entry.info.type_name] = entry

    # Negolog - agents are in negmas_negolog.agents (requires nenv)
    if "negolog" not in disabled and _is_package_available("negmas_negolog"):
        negolog_agents = [
            ("BoulwareAgent", "Boulware time-based agent"),
            ("ConcederAgent", "Conceder time-based agent"),
            ("LinearAgent", "Linear time-based agent"),
            ("MICROAgent", "MiCRO agent"),
            ("Atlas3Agent", "Atlas3 agent (ANAC 2015)"),
            ("NiceTitForTat", "Nice Tit-for-Tat agent"),
            ("YXAgent", "YXAgent"),
            ("ParsCatAgent", "ParsCat agent"),
            ("PonPokoAgent", "PonPoko agent"),
            ("AgentGG", "AgentGG"),
            ("SAGAAgent", "SAGA agent"),
            ("CUHKAgent", "CUHK agent"),
            ("AgentKN", "AgentKN"),
            ("Rubick", "Rubick agent"),
            ("AhBuNeAgent", "AhBuNe agent"),
            ("ParsAgent", "Pars agent (ANAC 2011)"),
            ("RandomDance", "Random Dance agent"),
            ("AgentBuyog", "AgentBuyog"),
            ("Kawaii", "Kawaii agent"),
            ("Caduceus2015", "Caduceus 2015 agent"),
            ("Caduceus", "Caduceus agent"),
            ("HardHeaded", "HardHeaded agent (ANAC 2011)"),
            ("IAMhaggler", "IAMhaggler agent"),
            ("LuckyAgent2022", "Lucky Agent 2022"),
            ("HybridAgent", "Hybrid agent"),
        ]
        for class_name, description in negolog_agents:
            type_name = f"negmas_negolog.agents.{class_name}"
            info = NegotiatorInfo(
                type_name=type_name,
                name=class_name,
                source="negolog",
                group="",
                description=description,
                tags=["negolog", "logic-based"],
                mechanisms=["SAO"],
                requires_bridge=False,
                available=True,
                module_path="negmas_negolog.agents",
            )
            NEGOTIATOR_REGISTRY[type_name] = NegotiatorEntry(cls=None, info=info)  # type: ignore[arg-type]

    # Genius reimplemented
    if "genius-reimplemented" not in disabled and _is_package_available(
        "negmas_genius_agents"
    ):
        for entry in _discover_from_library(
            "genius-reimplemented", "negmas_genius_agents"
        ):
            NEGOTIATOR_REGISTRY[entry.info.type_name] = entry

    # LLM negotiators
    if "llm" not in disabled and _is_package_available("negmas_llm"):
        for entry in _discover_from_library("llm", "negmas_llm"):
            NEGOTIATOR_REGISTRY[entry.info.type_name] = entry

    # RL negotiators - create entries without importing (torch dependency)
    if "rl" not in disabled and _is_package_available("negmas_rl"):
        rl_negotiators = [
            ("AutoVudo", "Auto-tuned VUDO negotiator"),
            ("Vudo", "VUDO (Value of Utility Difference Offers) negotiator"),
            ("VudoNoObservation", "VUDO without observation"),
            ("VudoNoAction", "VUDO without action"),
            ("VudoD", "VUDO-D variant"),
            ("VudoDNoObservation", "VUDO-D without observation"),
            ("VudoDNoAction", "VUDO-D without action"),
            ("RLBoa", "RL-BOA negotiator"),
            ("RLBoaC", "RL-BOA with concession"),
            ("Sengupta", "Sengupta RL negotiator"),
            ("SenguptaD", "Sengupta-D variant"),
            ("MiPN", "MiPN negotiator"),
            ("MiPNC", "MiPN with concession"),
            ("MiPNDC", "MiPN-DC variant"),
            ("VeNAS", "VeNAS negotiator"),
            ("VeNASC", "VeNAS with concession"),
        ]
        for class_name, description in rl_negotiators:
            type_name = f"negmas_rl.negotiators.{class_name}"
            info = NegotiatorInfo(
                type_name=type_name,
                name=class_name,
                source="rl",
                group="",
                description=description,
                tags=["rl", "reinforcement-learning"],
                mechanisms=["SAO"],
                requires_bridge=False,
                available=True,
                module_path="negmas_rl.negotiators",
            )
            # Store with None cls - will be loaded on demand
            NEGOTIATOR_REGISTRY[type_name] = NegotiatorEntry(cls=None, info=info)  # type: ignore[arg-type]

    # Custom sources from settings
    for custom in settings.custom_sources:
        if custom.id in disabled:
            continue

        for entry in _discover_from_library(
            source_id=custom.id,
            library=custom.library,
            pattern=custom.class_pattern or None,
            module=custom.module or None,
            class_names=custom.class_names or None,
            mechanisms=custom.mechanisms,
            requires_bridge=custom.requires_bridge,
        ):
            NEGOTIATOR_REGISTRY[entry.info.type_name] = entry


def _get_class_for_type(type_name: str) -> type | None:
    """Get a negotiator class by type name, dynamically importing if needed."""
    # Check registry first
    if type_name in NEGOTIATOR_REGISTRY:
        entry = NEGOTIATOR_REGISTRY[type_name]
        if entry.cls is not None:
            return entry.cls
        # Lazy load - cls is None, need to import
        # Fall through to dynamic import

    # Try dynamic import
    parts = type_name.rsplit(".", 1)
    if len(parts) == 2:
        module_path, class_name = parts
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name, None)
            # Update registry if we loaded a lazy entry
            if cls is not None and type_name in NEGOTIATOR_REGISTRY:
                NEGOTIATOR_REGISTRY[type_name].cls = cls
            return cls
        except ImportError:
            return None

    return None


# Run discovery on module load
_discover_all_negotiators()


class NegotiatorFactory:
    """Create negotiator instances from configuration."""

    @staticmethod
    def refresh_registry() -> None:
        """Re-discover all negotiators. Call after settings change."""
        _discover_all_negotiators()

    @staticmethod
    def get_available_sources() -> list[NegotiatorSource]:
        """List all available negotiator sources (builtin + custom)."""
        settings = SettingsService.load_negotiator_sources()
        _disabled = set(settings.disabled_sources)

        sources = []
        for src in BUILTIN_SOURCES:
            # Check if the library is available (if required)
            _available = True
            if src.library:
                _available = _is_package_available(src.library)

            # Copy with availability info
            source = NegotiatorSource(
                id=src.id,
                name=src.name,
                description=src.description,
                mechanisms=src.mechanisms,
                requires_bridge=src.requires_bridge,
                builtin=True,
                library=src.library,
            )
            sources.append(source)

        # Add custom sources
        for custom in settings.custom_sources:
            source = NegotiatorSource(
                id=custom.id,
                name=custom.name,
                description=custom.description,
                mechanisms=custom.mechanisms,
                requires_bridge=custom.requires_bridge,
                builtin=False,
                library=custom.library,
                class_pattern=custom.class_pattern,
                module=custom.module,
                class_names=custom.class_names,
            )
            sources.append(source)

        return sources

    @staticmethod
    def is_source_available(source_id: str) -> bool:
        """Check if a source is available (library installed)."""
        for src in BUILTIN_SOURCES:
            if src.id == source_id:
                if src.library:
                    return _is_package_available(src.library)
                return True

        # Check custom sources
        settings = SettingsService.load_negotiator_sources()
        for custom in settings.custom_sources:
            if custom.id == source_id:
                if custom.library:
                    return _is_package_available(custom.library)
                return True

        return False

    @staticmethod
    def get_source_unavailable_reason(source_id: str) -> str | None:
        """Get the reason why a source is unavailable, or None if available."""
        for src in BUILTIN_SOURCES:
            if src.id == source_id:
                if src.library and not _is_package_available(src.library):
                    return f"Package '{src.library}' is not installed"
                return None

        # Check custom sources
        settings = SettingsService.load_negotiator_sources()
        for custom in settings.custom_sources:
            if custom.id == source_id:
                if custom.library and not _is_package_available(custom.library):
                    return f"Package '{custom.library}' is not installed"
                return None

        return f"Unknown source: {source_id}"

    @staticmethod
    def list_available(
        source: str | None = None,
        group: str | None = None,
        search: str | None = None,
    ) -> list[NegotiatorInfo]:
        """List available negotiators with optional filtering.

        Args:
            source: Filter by source ID (e.g., "native", "genius")
            group: Filter by group within source (e.g., "y2019")
            search: Search string to match against name/description

        Returns:
            List of matching NegotiatorInfo objects.
        """
        results = []

        for type_name, entry in NEGOTIATOR_REGISTRY.items():
            info = entry.info

            # Apply filters
            if source and info.source != source:
                continue
            if group and info.group != group:
                continue
            if search:
                search_lower = search.lower()
                if (
                    search_lower not in info.name.lower()
                    and search_lower not in info.description.lower()
                    and search_lower not in info.type_name.lower()
                ):
                    continue

            results.append(info)

        # Sort by source, then group, then name
        results.sort(key=lambda x: (x.source, x.group, x.name))
        return results

    @staticmethod
    def get_info(type_name: str) -> NegotiatorInfo | None:
        """Get info for a specific negotiator type.

        Handles both exact matches and hash-suffixed versions (e.g., Foo#abc123).
        """
        # Try exact match first
        entry = NEGOTIATOR_REGISTRY.get(type_name)
        if entry is not None:
            return entry.info

        # Try with hash suffix (newer negmas versions)
        for key, entry in NEGOTIATOR_REGISTRY.items():
            if key.startswith(type_name + "#"):
                return entry.info

        return None

    @staticmethod
    def create(
        config: NegotiatorConfig,
        ufun: UtilityFunction | None = None,
    ) -> SAONegotiator:
        """Create a negotiator instance.

        Args:
            config: Negotiator configuration.
            ufun: Utility function to assign.

        Returns:
            Configured negotiator instance.

        Raises:
            ValueError: If negotiator type is not found.
        """
        # Handle special composite negotiator types
        type_name = config.type_name

        # BOA negotiator: "BOA:AcceptPolicy/OfferPolicy" or with model "BOA:AcceptPolicy/OfferPolicy/Model"
        if type_name.startswith("BOA:"):
            return NegotiatorFactory._create_boa_negotiator(config, ufun)

        # MAP negotiator: "MAP:AcceptPolicy/OfferPolicy" with models in params
        if type_name.startswith("MAP:"):
            return NegotiatorFactory._create_map_negotiator(config, ufun)

        # Regular negotiator - look up class by type name
        cls = _get_class_for_type(type_name)
        if cls is None:
            raise ValueError(f"Unknown negotiator type: {type_name}")

        negotiator = cls(name=config.name, **config.params)
        if ufun is not None:
            negotiator.ufun = ufun
        return negotiator

    @staticmethod
    def _create_boa_negotiator(
        config: NegotiatorConfig,
        ufun: UtilityFunction | None = None,
    ) -> SAONegotiator:
        """Create a BOA-style negotiator from type_name format.

        Type format: BOA:AcceptPolicy/OfferPolicy or BOA:AcceptPolicy/OfferPolicy/Model
        Additional params can include:
          - acceptance_params: dict
          - offering_params: dict
          - model_params: dict
        """
        from negmas.gb.negotiators.modular.boa import BOANegotiator

        # Parse type_name: "BOA:ACTime/GBoulwareOffering" or "BOA:ACTime/GBoulwareOffering/FrequencyUFunModel"
        parts = config.type_name[4:].split("/")  # Remove "BOA:" prefix
        if len(parts) < 2:
            raise ValueError(f"Invalid BOA type format: {config.type_name}")

        acceptance_name = parts[0]
        offering_name = parts[1]
        model_name = parts[2] if len(parts) > 2 else None

        # Get component classes
        acc_cls = BOAFactory.get_component_class(
            f"negmas.gb.components.{acceptance_name}"
        )
        off_cls = BOAFactory.get_component_class(
            f"negmas.gb.components.{offering_name}"
        )

        if acc_cls is None:
            raise ValueError(f"Unknown acceptance policy: {acceptance_name}")
        if off_cls is None:
            raise ValueError(f"Unknown offering policy: {offering_name}")

        # Get params from config
        params = config.params or {}
        acceptance_params = params.get("acceptance_params", {})
        offering_params = params.get("offering_params", {})
        model_params = params.get("model_params", {})

        # Create components
        acceptance = acc_cls(**acceptance_params)
        offering = off_cls(**offering_params)

        # Create model if specified
        model = None
        if model_name:
            model_cls = BOAFactory.get_component_class(
                f"negmas.gb.components.{model_name}"
            )
            if model_cls is not None:
                model = model_cls(**model_params)

        # Create BOANegotiator
        negotiator = BOANegotiator(
            name=config.name,
            acceptance=acceptance,
            offering=offering,
            model=model,
        )

        if ufun is not None:
            negotiator.ufun = ufun

        return negotiator

    @staticmethod
    def _create_map_negotiator(
        config: NegotiatorConfig,
        ufun: UtilityFunction | None = None,
    ) -> SAONegotiator:
        """Create a MAP-style negotiator from type_name format.

        Type format: MAP:AcceptPolicy/OfferPolicy
        Additional params should include:
          - models: list[str] - model class names
          - extra_components: list[str] - extra component class names
          - acceptance_first: bool
          - acceptance_params: dict
          - offering_params: dict
          - model_params: list[dict] - params for each model
          - extra_component_params: list[dict] - params for each extra component
        """
        from negmas.gb.negotiators.modular.mapneg import MAPNegotiator

        # Parse type_name: "MAP:ACTime/GBoulwareOffering"
        parts = config.type_name[4:].split("/")  # Remove "MAP:" prefix
        if len(parts) < 2:
            raise ValueError(f"Invalid MAP type format: {config.type_name}")

        acceptance_name = parts[0]
        offering_name = parts[1]

        # Get component classes
        acc_cls = BOAFactory.get_component_class(
            f"negmas.gb.components.{acceptance_name}"
        )
        off_cls = BOAFactory.get_component_class(
            f"negmas.gb.components.{offering_name}"
        )

        if acc_cls is None:
            raise ValueError(f"Unknown acceptance policy: {acceptance_name}")
        if off_cls is None:
            raise ValueError(f"Unknown offering policy: {offering_name}")

        # Get params from config
        params = config.params or {}
        acceptance_params = params.get("acceptance_params", {})
        offering_params = params.get("offering_params", {})
        model_names = params.get("models", [])
        model_params_list = params.get("model_params", [])
        extra_component_names = params.get("extra_components", [])
        extra_component_params_list = params.get("extra_component_params", [])
        acceptance_first = params.get("acceptance_first", True)

        # Create acceptance and offering
        acceptance = acc_cls(**acceptance_params)
        offering = off_cls(**offering_params)

        # Create models
        models = []
        for i, model_name in enumerate(model_names):
            model_cls = BOAFactory.get_component_class(
                f"negmas.gb.components.{model_name}"
            )
            if model_cls is not None:
                mp = model_params_list[i] if i < len(model_params_list) else {}
                models.append(model_cls(**mp))

        # Create extra components
        extra_components = []
        for i, comp_name in enumerate(extra_component_names):
            comp_cls = BOAFactory.get_component_class(
                f"negmas.gb.components.{comp_name}"
            )
            if comp_cls is not None:
                cp = (
                    extra_component_params_list[i]
                    if i < len(extra_component_params_list)
                    else {}
                )
                extra_components.append(comp_cls(**cp))

        # Validate: MAP negotiators must have at least one offering and one acceptance policy
        # The components list can contain any number of each type in any order,
        # but must have at least one of each
        all_components = [acceptance, offering]
        if extra_components:
            all_components.extend(extra_components)

        # Check if we have at least one offering and one acceptance policy
        from negmas.gb.components import AcceptancePolicy, OfferingPolicy

        has_acceptance = any(isinstance(c, AcceptancePolicy) for c in all_components)
        has_offering = any(isinstance(c, OfferingPolicy) for c in all_components)

        if not has_acceptance:
            raise ValueError(
                f"MAP negotiator '{config.name}' must have at least one acceptance policy"
            )
        if not has_offering:
            raise ValueError(
                f"MAP negotiator '{config.name}' must have at least one offering policy"
            )

        # Create MAPNegotiator
        negotiator = MAPNegotiator(
            name=config.name,
            acceptance=acceptance,
            offering=offering,
            models=models if models else None,
            extra_components=extra_components if extra_components else None,
            acceptance_first=acceptance_first,
        )

        if ufun is not None:
            negotiator.ufun = ufun

        return negotiator

    @staticmethod
    def create_for_scenario(
        configs: list[NegotiatorConfig],
        scenario: Scenario,
    ) -> list[SAONegotiator]:
        """Create negotiators for a scenario, assigning ufuns.

        Args:
            configs: List of negotiator configurations.
            scenario: Scenario with utility functions.

        Returns:
            List of configured negotiators with assigned ufuns.

        Raises:
            ValueError: If config count doesn't match ufun count.
        """
        if len(configs) != len(scenario.ufuns):
            raise ValueError(
                f"Config count ({len(configs)}) != ufun count ({len(scenario.ufuns)})"
            )

        return [
            NegotiatorFactory.create(config, ufun)
            for config, ufun in zip(configs, scenario.ufuns)
        ]


# BOA Component Registry (lazily populated)
_BOA_COMPONENTS_CACHE: dict[str, list[BOAComponentInfo]] | None = None


def _discover_boa_components() -> dict[str, list[BOAComponentInfo]]:
    """Discover BOA components from negmas.gb.components."""
    global _BOA_COMPONENTS_CACHE
    if _BOA_COMPONENTS_CACHE is not None:
        return _BOA_COMPONENTS_CACHE

    acceptance = []
    offering = []
    models = []

    try:
        from negmas.gb import components
        import inspect

        for name in dir(components):
            obj = getattr(components, name)
            if not inspect.isclass(obj) or name.startswith("_"):
                continue

            # Get base class names
            bases = [b.__name__ for b in obj.__mro__]

            if "AcceptancePolicy" in bases and name != "AcceptancePolicy":
                acceptance.append(
                    BOAComponentInfo(
                        name=name,
                        type_name=f"negmas.gb.components.{name}",
                        component_type="acceptance",
                        description=_get_component_description(name, "acceptance"),
                    )
                )
            elif "OfferingPolicy" in bases and name != "OfferingPolicy":
                offering.append(
                    BOAComponentInfo(
                        name=name,
                        type_name=f"negmas.gb.components.{name}",
                        component_type="offering",
                        description=_get_component_description(name, "offering"),
                    )
                )
            elif (
                "UFunModel" in bases
                or "OpponentModel" in bases
                or (
                    name.endswith("Model")
                    and name not in ("Model", "UFunModel", "OpponentModel")
                )
            ):
                models.append(
                    BOAComponentInfo(
                        name=name,
                        type_name=f"negmas.gb.components.{name}",
                        component_type="model",
                        description=_get_component_description(name, "model"),
                    )
                )

    except ImportError:
        pass

    _BOA_COMPONENTS_CACHE = {
        "acceptance": sorted(acceptance, key=lambda x: x.name),
        "offering": sorted(offering, key=lambda x: x.name),
        "model": sorted(models, key=lambda x: x.name),
    }
    return _BOA_COMPONENTS_CACHE


def _get_component_description(name: str, component_type: str) -> str:
    """Get a brief description for a BOA component."""
    # Common component descriptions
    descriptions = {
        # Acceptance policies
        "ACConst": "Accepts with constant probability",
        "ACLast": "Accepts if better than last received offer",
        "ACTime": "Time-based acceptance threshold",
        "AcceptAbove": "Accepts offers above a utility threshold",
        "AcceptAnyRational": "Accepts any offer above reservation",
        "AcceptBest": "Accepts only the best possible offer",
        "AcceptBetterRational": "Accepts better than reservation value",
        "AcceptImmediately": "Accepts any offer immediately",
        "RejectAlways": "Never accepts any offer",
        "TFTAcceptancePolicy": "Tit-for-tat acceptance",
        "GACCombi": "Combined acceptance conditions",
        "RandomAcceptancePolicy": "Random acceptance",
        # Offering policies
        "GBoulwareOffering": "Boulware time-dependent offering",
        "GConcederOffering": "Conceder time-dependent offering",
        "GLinearOffering": "Linear time-dependent offering",
        "GRandomOffering": "Random offering from outcome space",
        "GTimeDependentOffering": "Generic time-dependent offering",
        "MiCROOfferingPolicy": "MiCRO offering policy",
        "RandomOfferingPolicy": "Random offering policy",
        "TFTOfferingPolicy": "Tit-for-tat offering",
        "TimeBasedOfferingPolicy": "Time-based offering policy",
        "OfferBest": "Always offers best outcome",
        "CABOfferingPolicy": "Curve-Aspiration-Based offering",
        # Opponent models
        "FrequencyUFunModel": "Frequency-based utility model",
        "GBayesianModel": "Bayesian opponent model",
        "GDefaultModel": "Default opponent model",
        "GHardHeadedFrequencyModel": "HardHeaded frequency model",
        "ZeroSumModel": "Zero-sum opponent model",
        "UFunModel": "Base utility function model",
    }
    return descriptions.get(name, f"{component_type.title()} component")


class BOAFactory:
    """Factory for creating BOA-style modular negotiators."""

    @staticmethod
    def list_components(
        component_type: str | None = None,
    ) -> dict[str, list[BOAComponentInfo]]:
        """List available BOA components.

        Args:
            component_type: Filter by type ("acceptance", "offering", "model") or None for all.

        Returns:
            Dict mapping component type to list of component infos.
        """
        all_components = _discover_boa_components()
        if component_type is None:
            return all_components
        if component_type in all_components:
            return {component_type: all_components[component_type]}
        return {}

    @staticmethod
    def get_component_class(type_name: str) -> type | None:
        """Get a BOA component class by its full type name."""
        parts = type_name.rsplit(".", 1)
        if len(parts) != 2:
            return None

        module_path, class_name = parts
        try:
            mod = importlib.import_module(module_path)
            return getattr(mod, class_name, None)
        except ImportError:
            return None

    @staticmethod
    def create(
        config: BOANegotiatorConfig,
        ufun: UtilityFunction | None = None,
    ) -> SAONegotiator:
        """Create a BOA-style modular negotiator.

        Args:
            config: BOA negotiator configuration.
            ufun: Utility function to assign.

        Returns:
            Configured GBNegotiator instance.

        Raises:
            ValueError: If components cannot be created.
        """
        from negmas.gb import GBNegotiator

        # Get component classes
        acc_cls = BOAFactory.get_component_class(
            f"negmas.gb.components.{config.acceptance_policy}"
        )
        off_cls = BOAFactory.get_component_class(
            f"negmas.gb.components.{config.offering_policy}"
        )

        if acc_cls is None:
            raise ValueError(f"Unknown acceptance policy: {config.acceptance_policy}")
        if off_cls is None:
            raise ValueError(f"Unknown offering policy: {config.offering_policy}")

        # Create components
        acceptance = acc_cls(**config.acceptance_params)
        offering = off_cls(**config.offering_params)

        # Create opponent model if specified
        model = None
        if config.opponent_model:
            model_cls = BOAFactory.get_component_class(
                f"negmas.gb.components.{config.opponent_model}"
            )
            if model_cls is not None:
                model = model_cls(**config.model_params)

        # Create the negotiator
        negotiator = GBNegotiator(
            name=config.name,
            acceptance_policy=acceptance,
            offering_policy=offering,
            ufun_model=model,
        )

        if ufun is not None:
            negotiator.ufun = ufun

        return negotiator

    @staticmethod
    def refresh_cache() -> None:
        """Clear the BOA components cache to force rediscovery."""
        global _BOA_COMPONENTS_CACHE
        _BOA_COMPONENTS_CACHE = None
