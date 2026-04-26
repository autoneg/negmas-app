"""Load and manage negotiation scenarios."""

import json
import re
import time
from pathlib import Path
from typing import Any

import yaml

from negmas import Scenario
from negmas.inout import (
    find_domain_and_utility_files_geniusweb,
    find_domain_and_utility_files_xml,
    find_domain_and_utility_files_yaml,
)
from negmas.preferences.ops import is_rational

# Try to import scenario registry features (available in dev version, not PyPI)
try:
    from negmas import scenario_registry, register_all_scenarios

    HAS_SCENARIO_REGISTRY = True
except ImportError:
    scenario_registry: Any = {}
    HAS_SCENARIO_REGISTRY = False

    def register_all_scenarios() -> None:
        """No-op stub when scenario registry is not available."""
        pass


from ..models import ScenarioInfo, IssueInfo, ScenarioStatsInfo, ScenarioDefinition
from .settings_service import SettingsService


# In-memory cache for scenario info (lightweight)
# Key: scenario path (str), Value: (ScenarioInfo, cache_time)
_SCENARIO_INFO_CACHE: dict[str, tuple[ScenarioInfo, float]] = {}

# Cache for detailed scenario info (with full issue data)
# Key: scenario path (str), Value: (ScenarioInfo with issues, cache_time)
_SCENARIO_DETAIL_CACHE: dict[str, tuple[ScenarioInfo, float]] = {}

# Cache TTL in seconds (5 minutes) - after this, we check if files changed
_CACHE_TTL = 300.0

# Regex for fast extraction of opposition from _stats.yaml without full YAML parsing
_OPPOSITION_RE = re.compile(r"^opposition:\s*([0-9.eE+-]+)", re.MULTILINE)


def clear_scenario_cache() -> None:
    """Clear the in-memory scenario info cache."""
    global _SCENARIO_INFO_CACHE, _SCENARIO_DETAIL_CACHE
    _SCENARIO_INFO_CACHE.clear()
    _SCENARIO_DETAIL_CACHE.clear()


def calculate_rational_fraction(
    scenario: Scenario, max_samples: int = 50000
) -> float | None:
    """Calculate the fraction of outcomes that are rational for all negotiators.

    An outcome is rational if its utility is >= reserved value for all negotiators.

    Args:
        scenario: The scenario to analyze.
        max_samples: Maximum number of outcomes to sample for large spaces.

    Returns:
        Fraction of rational outcomes (0.0 to 1.0), or None if calculation fails.
    """
    try:
        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=max_samples)
        )
        if not outcomes:
            return 0.0

        n_rational = sum(1 for o in outcomes if is_rational(scenario.ufuns, o))
        return n_rational / len(outcomes)
    except (KeyError, ValueError, TypeError) as e:
        # Some scenarios have malformed utility functions that can't be evaluated
        # Return None to indicate the calculation failed
        return None


class ScenarioLoader:
    """Load scenarios from filesystem."""

    def __init__(self, scenarios_root: Path | None = None):
        """Initialize with scenarios root directory.

        Args:
            scenarios_root: Root directory containing scenarios.
                           Defaults to user directory (~/negmas/app/scenarios/).

        Raises:
            FileNotFoundError: If scenarios_root is None and user directory doesn't exist.
                              Run 'negmas-app setup' to extract scenarios first.
        """
        if scenarios_root is None:
            # Use user directory (~/negmas/app/scenarios/)
            user_scenarios = Path.home() / "negmas" / "app" / "scenarios"
            if user_scenarios.exists():
                scenarios_root = user_scenarios
            else:
                raise FileNotFoundError(
                    f"Scenarios directory not found at {user_scenarios}. "
                    "Run 'negmas-app setup' to extract bundled scenarios first."
                )
        self.scenarios_root = Path(scenarios_root)
        self._registered = False
        self._registration_in_progress = False
        self._registration_progress = {
            "total": 0,
            "current": 0,
            "status": "not_started",
        }
        self._cache_file = Path.home() / ".negmas" / "scenario_registry_cache.json"
        self._status_file = Path.home() / ".negmas" / "scenario_statuses.json"
        self._statuses: dict[str, str] = {}  # path -> status mapping
        self._load_statuses()

    def _load_statuses(self) -> None:
        """Load scenario statuses from disk."""
        if not self._status_file.exists():
            return
        try:
            with open(self._status_file, "r") as f:
                self._statuses = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load scenario statuses: {e}")
            self._statuses = {}

    def _save_statuses(self) -> None:
        """Save scenario statuses to disk."""
        try:
            self._status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._status_file, "w") as f:
                json.dump(self._statuses, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save scenario statuses: {e}")

    def get_scenario_status(self, path: str | Path) -> str:
        """Get the status of a scenario.

        Args:
            path: Path to the scenario directory.

        Returns:
            Status: "enabled", "disabled", or "archived"
        """
        return self._statuses.get(str(path), "enabled")

    def set_scenario_status(self, path: str | Path, status: str) -> bool:
        """Set the status of a scenario.

        Args:
            path: Path to the scenario directory.
            status: New status ("enabled", "disabled", "archived")

        Returns:
            True if successful, False otherwise.
        """
        if status not in ("enabled", "disabled", "archived"):
            return False

        path_str = str(path)
        self._statuses[path_str] = status
        self._save_statuses()

        # Invalidate caches
        if path_str in _SCENARIO_INFO_CACHE:
            del _SCENARIO_INFO_CACHE[path_str]
        if path_str in _SCENARIO_DETAIL_CACHE:
            del _SCENARIO_DETAIL_CACHE[path_str]

        return True

    def delete_scenario(self, path: str | Path) -> tuple[bool, str | None]:
        """Delete a scenario from disk.

        Args:
            path: Path to the scenario directory.

        Returns:
            Tuple of (success, error_message)
        """
        import shutil

        path = Path(path)
        path_str = str(path)

        # Check if scenario exists
        if not path.exists():
            return False, "Scenario not found"

        # Check if scenario is read-only
        self.ensure_scenarios_registered()
        for reg_info in scenario_registry.values():
            if str(reg_info.path) == path_str:
                if getattr(reg_info, "read_only", False):
                    return False, "Cannot delete read-only scenario"
                break

        # Delete from disk
        try:
            shutil.rmtree(path)
        except Exception as e:
            return False, f"Failed to delete scenario: {e}"

        # Remove from status tracking
        if path_str in self._statuses:
            del self._statuses[path_str]
            self._save_statuses()

        # Invalidate caches
        if path_str in _SCENARIO_INFO_CACHE:
            del _SCENARIO_INFO_CACHE[path_str]
        if path_str in _SCENARIO_DETAIL_CACHE:
            del _SCENARIO_DETAIL_CACHE[path_str]

        # Remove from registry
        if path_str in scenario_registry:
            del scenario_registry[path_str]

        return True, None

    def _save_registry_cache(self) -> None:
        """Save the scenario registry to disk cache for fast startup."""
        try:
            # Create cache directory if it doesn't exist
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Serialize registry data
            cache_data = {"version": "1.0", "timestamp": time.time(), "scenarios": []}

            for path_str, reg_info in scenario_registry.items():
                try:
                    scenario_data = {
                        "path": str(reg_info.path),
                        "name": reg_info.name,
                        "source": reg_info.source,
                        "tags": list(reg_info.tags) if reg_info.tags else [],
                        "n_outcomes": reg_info.n_outcomes,
                        "n_negotiators": reg_info.n_negotiators,
                        "opposition_level": reg_info.opposition_level,
                        "rational_fraction": reg_info.rational_fraction,
                        "description": reg_info.description or "",
                        "read_only": getattr(reg_info, "read_only", False),
                    }
                    cache_data["scenarios"].append(scenario_data)
                except Exception as e:
                    # Skip scenarios that fail to serialize
                    print(f"Warning: Failed to cache scenario {path_str}: {e}")
                    continue

            # Write cache file
            with open(self._cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            print(f"Saved {len(cache_data['scenarios'])} scenarios to cache")
        except Exception as e:
            print(f"Warning: Failed to save registry cache: {e}")

    def _load_registry_cache(self) -> bool:
        """Load the scenario registry from disk cache.

        Returns:
            True if cache was loaded successfully, False otherwise
        """
        if not self._cache_file.exists():
            return False

        try:
            with open(self._cache_file, "r") as f:
                cache_data = json.load(f)

            # Check cache version
            if cache_data.get("version") != "1.0":
                print("Cache version mismatch, will rebuild")
                return False

            # Check if cache is stale (older than 7 days)
            cache_age = time.time() - cache_data.get("timestamp", 0)
            if cache_age > 7 * 24 * 3600:
                print("Cache is stale (>7 days), will rebuild")
                return False

            # Check if scenarios directories have been modified since cache
            # If any directory is newer than cache, invalidate
            cache_time = cache_data.get("timestamp", 0)
            if self.scenarios_root.exists():
                for category_dir in self.scenarios_root.iterdir():
                    if category_dir.is_dir() and not category_dir.name.startswith("."):
                        if category_dir.stat().st_mtime > cache_time:
                            print(
                                f"Directory {category_dir.name} modified since cache, will rebuild"
                            )
                            return False

            # Populate the negmas scenario_registry from cache
            # We need to reconstruct ScenarioInfo objects and add them to the registry
            from negmas.registry import ScenarioInfo as NegmasScenarioInfo

            loaded_count = 0
            for scenario_data in cache_data.get("scenarios", []):
                try:
                    # Reconstruct ScenarioInfo object
                    info = NegmasScenarioInfo(
                        path=Path(scenario_data["path"]),
                        name=scenario_data["name"],
                        source=scenario_data["source"],
                        tags=set(scenario_data.get("tags", [])),
                        n_outcomes=scenario_data.get("n_outcomes"),
                        n_negotiators=scenario_data.get("n_negotiators"),
                        opposition_level=scenario_data.get("opposition_level"),
                        rational_fraction=scenario_data.get("rational_fraction"),
                        description=scenario_data.get("description", ""),
                        read_only=scenario_data.get("read_only", False),
                    )

                    # Add to registry using the path as key
                    scenario_registry[str(info.path)] = info
                    loaded_count += 1

                except Exception as e:
                    print(f"Warning: Failed to load cached scenario: {e}")
                    continue

            print(f"Loaded {loaded_count} scenarios from cache")

            # Mark as registered
            self._registered = True
            self._registration_progress["status"] = "loaded_from_cache"
            self._registration_progress["total"] = 1
            self._registration_progress["current"] = 1

            return True
        except Exception as e:
            print(f"Warning: Failed to load registry cache: {e}")
            return False

    def ensure_scenarios_registered(self) -> int:
        """Register all scenarios with negmas scenario_registry if not already done.

        Returns:
            Number of scenarios registered.
        """
        if self._registered:
            return len(scenario_registry)

        if self._registration_in_progress:
            return len(scenario_registry)  # Return current count if in progress

        # Try loading from cache first (instant startup on subsequent runs)
        if self._load_registry_cache():
            return len(scenario_registry)

        self._registration_in_progress = True
        self._registration_progress["status"] = "registering"

        # Count total categories first for progress tracking
        categories = []
        if self.scenarios_root.exists():
            categories = [
                d
                for d in self.scenarios_root.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

        settings = SettingsService.load_paths()
        custom_paths = [
            Path(p).expanduser()
            for p in settings.scenario_paths
            if Path(p).expanduser().exists()
        ]

        total_categories = len(categories) + len(custom_paths)
        self._registration_progress["total"] = total_categories
        self._registration_progress["current"] = 0

        # Register built-in scenarios from ~/negmas/app/scenarios with source="app"
        # These are USER scenarios and should be editable (read_only=False)
        # Use register_all_scenarios which auto-detects format, normalized, etc.
        total_registered = 0

        for category_dir in categories:
            try:
                # Use category name as tag (e.g., "anac2019")
                # Also check if it's an ANAC directory
                tags = {category_dir.name}
                if category_dir.name.lower().startswith("anac"):
                    tags.add("anac")

                # register_all_scenarios auto-detects: format (xml/json/yaml),
                # normalized, n_outcomes, n_negotiators, bilateral/multilateral
                # read_only=False because these are user scenarios that can be edited
                infos = register_all_scenarios(
                    category_dir,
                    source="app",
                    tags=tags,
                    recursive=True,
                    read_only=False,  # User scenarios are editable
                )
                total_registered += len(infos)
                self._registration_progress["current"] += 1
            except Exception as e:
                print(f"Warning: Failed to register scenarios from {category_dir}: {e}")
                self._registration_progress["current"] += 1

        # Register from custom scenario_paths
        # Each path gets scanned recursively, and scenarios use the folder name as source
        for path in custom_paths:
            # Use the folder name as the source name
            source_name = path.name
            try:
                # Build tags from folder structure
                infos = register_all_scenarios(
                    path,
                    source=source_name,
                    recursive=True,
                )
                total_registered += len(infos)
                self._registration_progress["current"] += 1
            except Exception as e:
                print(f"Warning: Failed to register scenarios from {path}: {e}")
                self._registration_progress["current"] += 1

        self._registered = True
        self._registration_in_progress = False
        self._registration_progress["status"] = "completed"

        # Save to disk cache for instant next startup
        self._save_registry_cache()

        return total_registered

    def get_registration_status(self) -> dict:
        """Get the current registration status and progress.

        Returns:
            Dict with 'registered', 'in_progress', 'progress' keys
        """
        return {
            "registered": self._registered,
            "in_progress": self._registration_in_progress,
            "progress": self._registration_progress.copy(),
            "total_scenarios": len(scenario_registry),
        }

    def list_sources(self) -> list[str]:
        """List available scenario sources (app, user, etc.) from negmas registry."""
        self.ensure_scenarios_registered()

        # Get unique actual sources from registry
        sources = set()
        for info in scenario_registry.values():
            if info.source:
                sources.add(info.source)

        return sorted(sources)

    def _convert_registry_info(self, reg_info: Any) -> ScenarioInfo | None:
        """Convert negmas ScenarioInfo to our ScenarioInfo model.

        This is used for lightweight listing - no file I/O operations.
        All data comes from the registry which was populated during registration.
        """
        try:
            # Use tags directly from registry
            tags = list(reg_info.tags) if reg_info.tags else []

            # Use n_negotiators from registry (already accurate from registration)
            n_negotiators = reg_info.n_negotiators or 2

            # Extract normalized and format from tags
            normalized = "normalized" in tags if tags else None
            format_type = None
            for tag in tags:
                if tag in ("yaml", "xml", "json"):
                    format_type = tag
                    break

            # negmas ScenarioInfo has: name, path, source, tags, n_outcomes, n_negotiators,
            # opposition_level, rational_fraction, description, read_only

            # Get read_only status from registry (negmas package scenarios have read_only=True)
            readonly = getattr(reg_info, "read_only", False)

            # Get status from our status tracking
            status = self.get_scenario_status(reg_info.path)

            return ScenarioInfo(
                path=str(reg_info.path),
                name=reg_info.name,
                n_negotiators=n_negotiators,
                issues=[],  # Will be loaded on detail request
                n_outcomes=reg_info.n_outcomes,
                rational_fraction=reg_info.rational_fraction,  # Available in registry
                opposition=reg_info.opposition_level,
                source=reg_info.source or "unknown",  # Use actual source from registry
                tags=tags,  # All tags from registry (normalized, anac, file, xml/json/yaml, bilateral/multilateral, etc.)
                description=reg_info.description or "",  # Description from registry
                has_stats=False,  # Not needed for listing - will be loaded on detail view
                has_info=False,  # Not needed for listing - will be loaded on detail view
                normalized=normalized,
                format=format_type,
                readonly=readonly,  # Use read_only from negmas registry
                status=status,  # Include status
            )
        except Exception as e:
            print(f"Warning: Failed to convert registry info: {e}")
            return None

    def list_scenarios(self, source: str | None = None) -> list[ScenarioInfo]:
        """List all scenarios from negmas registry, optionally filtered by source.

        Args:
            source: Filter by actual source (e.g., "app", "user"). None returns all.
        """
        self.ensure_scenarios_registered()

        # Query registry by actual source
        if source:
            results = scenario_registry.query(source=source)
        else:
            results = dict(scenario_registry.items())

        # Convert negmas ScenarioInfo to our ScenarioInfo model
        scenarios = []
        for path_str, reg_info in results.items():
            info = self._convert_registry_info(reg_info)
            if info:
                scenarios.append(info)

        return scenarios

    def _load_scenario_info_lightweight(
        self, path: Path, source: str
    ) -> ScenarioInfo | None:
        """Load scenario info using lightweight file reads (no full Scenario.load).

        This reads only the _info.yml and extracts opposition from _stats.yaml
        using regex (avoiding expensive full YAML parsing of large files).
        """
        path_str = str(path)
        current_time = time.time()

        # Check cache first
        if path_str in _SCENARIO_INFO_CACHE:
            cached_info, cache_time = _SCENARIO_INFO_CACHE[path_str]
            if current_time - cache_time < _CACHE_TTL:
                return cached_info

        try:
            # Read _info.yml for n_outcomes, n_issues, and rational_fraction (small file, full YAML is fine)
            n_outcomes = None
            n_issues = None
            rational_fraction = None
            description = ""
            info_file = path / "_info.yml"
            if info_file.exists():
                with open(info_file) as f:
                    info_data = yaml.safe_load(f) or {}
                    n_outcomes = info_data.get("n_outcomes")
                    n_issues = info_data.get("n_issues")
                    rational_fraction = info_data.get("rational_fraction")
                    # Try both 'description' and 'desc' fields
                    description = (
                        info_data.get("description") or info_data.get("desc") or ""
                    )

            # Extract opposition from _stats.yaml using regex (fast, avoids full YAML parsing)
            # The _stats.yaml files can be large (2MB+) due to pareto data
            opposition = None
            has_stats = False
            stats_file = path / "_stats.yaml"
            if stats_file.exists():
                has_stats = True
                content = stats_file.read_text()
                match = _OPPOSITION_RE.search(content)
                if match:
                    opposition = float(match.group(1))

            # Count utility function files using negmas built-in detection
            # Try formats in order: YAML, XML (Genius), GeniusWeb
            _, ufun_files = find_domain_and_utility_files_yaml(path)
            if not ufun_files:
                _, ufun_files = find_domain_and_utility_files_xml(path)
            if not ufun_files:
                _, ufun_files = find_domain_and_utility_files_geniusweb(path)
            n_negotiators = len(ufun_files) if ufun_files else 2  # Default to 2

            info = ScenarioInfo(
                path=str(path),
                name=path.name,
                n_negotiators=n_negotiators,
                issues=[],  # Empty for lightweight load - filled on detail request
                n_outcomes=n_outcomes,
                rational_fraction=rational_fraction,
                opposition=opposition,
                source=source,
                description=description,
                has_stats=has_stats,
                has_info=rational_fraction is not None,
            )

            # Store in cache
            _SCENARIO_INFO_CACHE[path_str] = (info, current_time)
            return info

        except Exception:
            return None

    def _load_scenario_info_full(self, path: Path, source: str) -> ScenarioInfo | None:
        """Load full scenario info including issues (slower, for detail view)."""
        path_str = str(path)
        current_time = time.time()

        # Check detail cache first
        if path_str in _SCENARIO_DETAIL_CACHE:
            cached_info, cache_time = _SCENARIO_DETAIL_CACHE[path_str]
            if current_time - cache_time < _CACHE_TTL:
                return cached_info

        # Load full scenario - NO stats needed here, just issues/ufuns
        # Stats are only loaded on-demand in get_scenario_stats()
        try:
            scenario = Scenario.load(path, load_stats=False, load_info=True)  # type: ignore[attr-defined]
            if scenario is None:
                return None

            issues = []
            for issue in scenario.outcome_space.issues:
                values = list(issue.all) if hasattr(issue, "all") else None
                # Include min/max for continuous/integer issues
                min_value = None
                max_value = None
                if hasattr(issue, "min_value") and issue.min_value is not None:
                    min_value = float(issue.min_value)
                if hasattr(issue, "max_value") and issue.max_value is not None:
                    max_value = float(issue.max_value)

                # Limit discrete issue values to 100 to avoid huge data transfers
                if values and len(values) > 100:
                    values = values[:100]

                issue_info = IssueInfo(
                    name=issue.name,
                    type=type(issue).__name__,
                    values=values,
                    min_value=min_value,
                    max_value=max_value,
                )
                issues.append(issue_info)

            n_outcomes = None
            if hasattr(scenario.outcome_space, "cardinality"):
                n_outcomes = scenario.outcome_space.cardinality

            rational_fraction = None
            if scenario.info and "rational_fraction" in scenario.info:
                rational_fraction = float(scenario.info["rational_fraction"])

            # Extract opposition from _stats.yaml using regex (fast, avoids loading stats)
            # Stats are NOT loaded here to save memory - only loaded on-demand
            opposition = None
            has_stats = False
            stats_file = path / "_stats.yaml"
            if stats_file.exists():
                has_stats = True
                content = stats_file.read_text()
                match = _OPPOSITION_RE.search(content)
                if match:
                    opposition = float(match.group(1))

            # Get normalized from scenario.info (cached) or detect from scenario
            normalized = None
            format_type = None
            if scenario.info:
                normalized = scenario.info.get("normalized")
                format_type = scenario.info.get("format")

            # If not in cache, detect and save to cache
            needs_save = False
            if normalized is None:
                # Check if scenario has is_normalized property
                try:
                    normalized = (
                        bool(scenario.is_normalized)
                        if hasattr(scenario, "is_normalized")
                        else None
                    )
                    if normalized is not None:
                        if scenario.info is None:
                            scenario.info = {}
                        scenario.info["normalized"] = normalized
                        needs_save = True
                except Exception:
                    normalized = None

            if format_type is None:
                # Detect format from files
                if (path / "domain.xml").exists():
                    format_type = "xml"
                elif (path / "domain.json").exists():
                    format_type = "json"
                elif (path / "domain.yaml").exists() or (path / "domain.yml").exists():
                    format_type = "yaml"

                if format_type is not None:
                    if scenario.info is None:
                        scenario.info = {}
                    scenario.info["format"] = format_type
                    needs_save = True

            # Save info if we added new fields
            if needs_save:
                try:
                    scenario.save_info(path)
                except Exception:
                    pass  # Ignore save errors

            # Determine if scenario is read-only by checking the registry
            # Negmas package scenarios have read_only=True
            readonly = False
            self.ensure_scenarios_registered()
            for reg_info in scenario_registry.values():
                if str(reg_info.path) == str(path):
                    readonly = getattr(reg_info, "read_only", False)
                    break

            # Get status from our status tracking
            status = self.get_scenario_status(path)

            info = ScenarioInfo(
                path=str(path),
                name=path.name,
                n_negotiators=len(scenario.ufuns),
                issues=issues,
                n_outcomes=n_outcomes,
                rational_fraction=rational_fraction,
                opposition=opposition,
                source=source,
                has_stats=has_stats,
                has_info=scenario.info is not None
                and "rational_fraction" in scenario.info,
                normalized=normalized,
                format=format_type,
                readonly=readonly,  # Use read_only from negmas registry
                status=status,  # Include status
            )

            # Store in detail cache
            _SCENARIO_DETAIL_CACHE[path_str] = (info, current_time)

            # Also update lightweight cache (without replacing if has issues)
            if path_str not in _SCENARIO_INFO_CACHE:
                _SCENARIO_INFO_CACHE[path_str] = (info, current_time)

            return info
        except Exception:
            return None

    def load_scenario(
        self,
        path: str | Path,
        ignore_discount: bool = False,
        load_stats: bool = True,
        load_info: bool = True,
    ) -> Any:
        """Load a full scenario from path.

        Args:
            path: Path to scenario directory.
            ignore_discount: If True, ignore discount factors in utility functions.
            load_stats: If True, load cached stats if available.
            load_info: If True, load cached info if available.

        Returns:
            Loaded Scenario or None if loading fails.
        """
        return Scenario.load(
            Path(path),
            ignore_discount=ignore_discount,
            load_stats=load_stats,
            load_info=load_info,
        )  # type: ignore[attr-defined]

    def get_scenario_info(self, path: str | Path) -> ScenarioInfo | None:
        """Get info for a specific scenario (with full details including issues)."""
        path = Path(path)
        # Determine source from path
        try:
            source = path.parent.name
        except Exception:
            source = "unknown"
        return self._load_scenario_info_full(path, source)

    def get_scenario_stats(self, path: str | Path) -> ScenarioStatsInfo:
        """Get scenario statistics.

        Args:
            path: Path to scenario directory.

        Returns:
            ScenarioStatsInfo with stats if available.
        """
        scenario = self.load_scenario(path, load_stats=True, load_info=True)
        if scenario is None:
            return ScenarioStatsInfo(has_stats=False)

        return self._extract_stats(scenario)

    def calculate_and_save_stats(
        self,
        path: str | Path,
        force: bool = False,
    ) -> ScenarioStatsInfo:
        """Calculate scenario statistics and optionally save them.

        Args:
            path: Path to scenario directory.
            force: If True, recalculate even if stats exist.

        Returns:
            ScenarioStatsInfo with computed stats.
        """
        path = Path(path)
        scenario = self.load_scenario(path, load_stats=True, load_info=True)
        if scenario is None:
            return ScenarioStatsInfo(has_stats=False)

        # Load performance settings to check limits
        perf_settings = SettingsService.load_performance()
        max_stats = perf_settings.max_outcomes_stats
        max_rationality = perf_settings.max_outcomes_rationality

        # Get n_outcomes early (always calculate this)
        n_outcomes = scenario.outcome_space.cardinality

        # Determine what can be calculated based on limits
        # 0 or None means no limit
        can_calc_stats = max_stats is None or max_stats == 0 or n_outcomes <= max_stats
        can_calc_rationality = (
            max_rationality is None
            or max_rationality == 0
            or n_outcomes <= max_rationality
        )

        # Calculate stats if needed and allowed
        needs_stats = scenario.stats is None or force
        needs_info = (
            scenario.info is None
            or "n_outcomes" not in scenario.info
            or "rational_fraction" not in scenario.info
            or force
        )

        if needs_stats and can_calc_stats:
            scenario.calc_stats()
        elif needs_stats and not can_calc_stats:
            # Skip stats calculation due to limit
            pass

        if needs_info:
            # Calculate and store n_outcomes, n_issues, and rational_fraction in info
            if scenario.info is None:
                scenario.info = {}

            # Always set n_outcomes and n_issues (these are cheap)
            scenario.info["n_outcomes"] = n_outcomes
            scenario.info["n_issues"] = len(scenario.outcome_space.issues)

            # Only calculate rational_fraction if within rationality limits
            if can_calc_rationality:
                rational_fraction = calculate_rational_fraction(scenario)
                scenario.info["rational_fraction"] = rational_fraction
            else:
                # Set to None when skipped due to limit
                scenario.info["rational_fraction"] = None

        # Save if caching is enabled and something was calculated
        something_calculated = (needs_stats and can_calc_stats) or needs_info
        if something_calculated:
            settings = SettingsService.load_general()
            if settings.cache_scenario_stats:
                # Check if scenario is read-only before trying to save
                scenario_info = self.get_scenario_info(path)
                is_readonly = scenario_info.readonly if scenario_info else False

                if not is_readonly:
                    try:
                        # Determine whether to include Pareto frontier based on settings
                        perf_settings = SettingsService.load_performance()
                        max_pareto_outcomes = perf_settings.max_pareto_outcomes

                        include_pareto = True
                        if max_pareto_outcomes is not None and scenario.stats:
                            n_pareto = len(scenario.stats.pareto_outcomes or [])
                            if n_pareto > max_pareto_outcomes:
                                include_pareto = False

                        # Use scenario.update() for atomic save of info and stats
                        # This is more reliable than separate save_info() and save_stats() calls
                        scenario.update(
                            save_info=needs_info and scenario.info is not None,
                            save_stats=needs_stats
                            and can_calc_stats
                            and scenario.stats is not None,
                            save_plot=False,  # Don't save plots here
                            include_pareto_frontier=include_pareto,
                        )
                    except Exception as e:
                        # Log error but don't fail - may be filesystem issues
                        print(f"Warning: Could not save stats/info for {path}: {e}")
                else:
                    # Don't try to save for read-only scenarios
                    pass

            # Invalidate in-memory caches so next list_scenarios picks up new stats
            path_str = str(path)
            if path_str in _SCENARIO_INFO_CACHE:
                del _SCENARIO_INFO_CACHE[path_str]
            if path_str in _SCENARIO_DETAIL_CACHE:
                del _SCENARIO_DETAIL_CACHE[path_str]

        return self._extract_stats(scenario)

    def _extract_stats(self, scenario: Scenario) -> ScenarioStatsInfo:
        """Extract stats from a scenario into ScenarioStatsInfo."""
        if scenario.stats is None:
            return ScenarioStatsInfo(has_stats=False)

        stats = scenario.stats

        # Get negotiator names from ufuns if available
        negotiator_names = []
        for i, ufun in enumerate(scenario.ufuns):
            name = getattr(ufun, "name", None) or f"Negotiator {i + 1}"
            negotiator_names.append(name)

        # Get issue names from outcome space
        issue_names = [issue.name for issue in scenario.outcome_space.issues]

        # Get total outcomes count
        n_outcomes = None
        try:
            n_outcomes = scenario.outcome_space.cardinality
        except Exception:
            pass

        # Get rational_fraction from scenario.info if available
        rational_fraction = None
        if scenario.info and "rational_fraction" in scenario.info:
            rational_fraction = float(scenario.info["rational_fraction"])

        # Convert numpy types to Python types for JSON serialization
        def to_list(utils: Any) -> list[list[float]] | None:
            if utils is None:
                return None
            result = []
            for u in utils:
                result.append([float(x) for x in u])
            return result if result else None

        def outcomes_to_dicts(outcomes: Any) -> list[dict] | None:
            """Convert outcome tuples to dicts with issue names."""
            if outcomes is None:
                return None
            result = []
            for outcome in outcomes:
                if outcome is not None:
                    outcome_dict = dict(zip(issue_names, outcome))
                    result.append(outcome_dict)
            return result if result else None

        return ScenarioStatsInfo(
            has_stats=True,
            n_outcomes=n_outcomes,
            rational_fraction=rational_fraction,
            opposition=float(stats.opposition)
            if stats.opposition is not None
            else None,
            utility_ranges=[(float(lo), float(hi)) for lo, hi in stats.utility_ranges]
            if stats.utility_ranges
            else None,
            n_pareto_outcomes=len(stats.pareto_utils) if stats.pareto_utils else 0,
            nash_utils=to_list(stats.nash_utils),
            kalai_utils=to_list(stats.kalai_utils),
            ks_utils=to_list(getattr(stats, "ks_utils", None)),
            max_welfare_utils=to_list(stats.max_welfare_utils),
            nash_outcomes=outcomes_to_dicts(stats.nash_outcomes),
            kalai_outcomes=outcomes_to_dicts(stats.kalai_outcomes),
            ks_outcomes=outcomes_to_dicts(getattr(stats, "ks_outcomes", None)),
            max_welfare_outcomes=outcomes_to_dicts(stats.max_welfare_outcomes),
            modified_kalai_utils=to_list(stats.modified_kalai_utils),
            modified_ks_utils=to_list(getattr(stats, "modified_ks_utils", None)),
            max_relative_welfare_utils=to_list(stats.max_relative_welfare_utils),
            # Note: pareto_utils intentionally NOT included - too large (can be 2MB+)
            # Pareto frontier is computed on-demand for visualization in outcome_analysis.py
            negotiator_names=negotiator_names,
            issue_names=issue_names,
        )

    def create_scenario(
        self,
        definition: ScenarioDefinition,
        save_path: Path | None = None,
    ) -> tuple[Scenario | None, Path | None, str | None]:
        """Create a new scenario from a definition.

        Args:
            definition: The scenario definition.
            save_path: Where to save the scenario. If None, uses user scenarios directory.

        Returns:
            Tuple of (created Scenario, saved path, error message if failed).
        """
        from negmas.outcomes import make_issue, make_os
        from negmas.preferences import (
            LinearAdditiveUtilityFunction,
            AffineUtilityFunction,
            TableFun,
            LinearFun,
            IdentityFun,
        )

        try:
            # 1. Create issues
            issues = []
            for issue_def in definition.issues:
                if issue_def.type == "categorical":
                    if not issue_def.values:
                        return (
                            None,
                            None,
                            f"Categorical issue '{issue_def.name}' requires values",
                        )
                    issue = make_issue(name=issue_def.name, values=issue_def.values)
                elif issue_def.type == "integer":
                    if issue_def.min_value is None or issue_def.max_value is None:
                        return (
                            None,
                            None,
                            f"Integer issue '{issue_def.name}' requires min/max values",
                        )
                    # Integer range as list of values
                    issue = make_issue(
                        name=issue_def.name,
                        values=list(
                            range(
                                int(issue_def.min_value), int(issue_def.max_value) + 1
                            )
                        ),
                    )
                elif issue_def.type == "continuous":
                    if issue_def.min_value is None or issue_def.max_value is None:
                        return (
                            None,
                            None,
                            f"Continuous issue '{issue_def.name}' requires min/max values",
                        )
                    issue = make_issue(
                        name=issue_def.name,
                        values=(issue_def.min_value, issue_def.max_value),
                    )
                else:
                    return None, None, f"Unknown issue type: {issue_def.type}"
                issues.append(issue)

            # 2. Create outcome space
            outcome_space = make_os(issues, name=f"{definition.name}_domain")

            # 3. Create utility functions
            ufuns = []
            for ufun_def in definition.ufuns:
                if ufun_def.type == "linear_additive":
                    # Build value functions for each issue
                    values = []
                    if ufun_def.values:
                        for vf_def in ufun_def.values:
                            if vf_def.type == "table" and vf_def.mapping:
                                values.append(TableFun(vf_def.mapping))
                            elif vf_def.type == "linear":
                                slope = (
                                    vf_def.slope if vf_def.slope is not None else 1.0
                                )
                                intercept = (
                                    vf_def.intercept
                                    if vf_def.intercept is not None
                                    else 0.0
                                )
                                values.append(LinearFun(slope, intercept))
                            elif vf_def.type == "identity":
                                values.append(IdentityFun())
                            else:
                                # Default to identity
                                values.append(IdentityFun())
                    else:
                        # Auto-generate identity functions for each issue
                        values = [IdentityFun() for _ in issues]

                    # Use provided weights or equal weights
                    weights = ufun_def.weights or [1.0 / len(issues)] * len(issues)

                    ufun = LinearAdditiveUtilityFunction(
                        values=values,
                        weights=weights,
                        outcome_space=outcome_space,
                        reserved_value=ufun_def.reserved_value,
                        name=ufun_def.name,
                    )
                elif ufun_def.type == "affine":
                    weights = ufun_def.weights or [1.0 / len(issues)] * len(issues)
                    bias = ufun_def.bias if ufun_def.bias is not None else 0.0
                    ufun = AffineUtilityFunction(
                        weights=weights,
                        bias=bias,
                        outcome_space=outcome_space,
                        reserved_value=ufun_def.reserved_value,
                        name=ufun_def.name,
                    )
                else:
                    return None, None, f"Unknown ufun type: {ufun_def.type}"

                ufuns.append(ufun)

            # 4. Create scenario
            scenario = Scenario(outcome_space=outcome_space, ufuns=ufuns)

            # 5. Save to disk if path provided
            if save_path is None:
                # Default to user scenarios directory
                settings = SettingsService.load_paths()
                user_scenarios = Path(settings.user_scenarios).expanduser()
                user_scenarios.mkdir(parents=True, exist_ok=True)
                save_path = user_scenarios / definition.name

            # Ensure unique name
            original_path = save_path
            counter = 1
            while save_path.exists():
                save_path = original_path.parent / f"{original_path.name}_{counter}"
                counter += 1

            # Save scenario (dumpas only takes folder and type)
            scenario.dumpas(save_path)

            # Invalidate caches so the new scenario appears in lists
            path_str = str(save_path)
            if path_str in _SCENARIO_INFO_CACHE:
                del _SCENARIO_INFO_CACHE[path_str]
            if path_str in _SCENARIO_DETAIL_CACHE:
                del _SCENARIO_DETAIL_CACHE[path_str]

            return scenario, save_path, None

        except Exception as e:
            return None, None, str(e)
