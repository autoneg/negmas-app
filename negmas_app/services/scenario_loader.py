"""Load and manage negotiation scenarios."""

import re
import time
from pathlib import Path
from typing import Any

import yaml

from negmas import Scenario, scenario_registry, register_all_scenarios
from negmas.inout import (
    find_domain_and_utility_files_geniusweb,
    find_domain_and_utility_files_xml,
    find_domain_and_utility_files_yaml,
)
from negmas.preferences.ops import is_rational

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


def calculate_rational_fraction(scenario: Scenario, max_samples: int = 50000) -> float:
    """Calculate the fraction of outcomes that are rational for all negotiators.

    An outcome is rational if its utility is >= reserved value for all negotiators.

    Args:
        scenario: The scenario to analyze.
        max_samples: Maximum number of outcomes to sample for large spaces.

    Returns:
        Fraction of rational outcomes (0.0 to 1.0).
    """
    outcomes = list(
        scenario.outcome_space.enumerate_or_sample(max_cardinality=max_samples)
    )
    if not outcomes:
        return 0.0

    n_rational = sum(1 for o in outcomes if is_rational(scenario.ufuns, o))
    return n_rational / len(outcomes)


class ScenarioLoader:
    """Load scenarios from filesystem."""

    def __init__(self, scenarios_root: Path | None = None):
        """Initialize with scenarios root directory.

        Args:
            scenarios_root: Root directory containing scenarios.
                           Defaults to 'scenarios' folder next to negmas_app.
        """
        if scenarios_root is None:
            # Default: scenarios folder at same level as negmas_app package
            scenarios_root = Path(__file__).parent.parent.parent / "scenarios"
        self.scenarios_root = Path(scenarios_root)
        self._registered = False

    def ensure_scenarios_registered(self) -> int:
        """Register all scenarios with negmas scenario_registry if not already done.

        Returns:
            Number of scenarios registered.
        """
        if self._registered:
            return len(scenario_registry)

        from negmas import register_scenario

        # Register built-in scenarios with source="app"
        # Add all folder names from scenarios_root to scenario as tags
        total_registered = 0
        if self.scenarios_root.exists():
            for category_dir in self.scenarios_root.iterdir():
                if category_dir.is_dir() and not category_dir.name.startswith("."):
                    try:
                        # Find all scenario directories
                        for scenario_dir in category_dir.iterdir():
                            if (
                                scenario_dir.is_dir()
                                and not scenario_dir.name.startswith(".")
                            ):
                                try:
                                    # Extract tags: all folder names from scenarios/ onwards
                                    tags = {category_dir.name}  # e.g., "anac2019"
                                    register_scenario(
                                        scenario_dir,
                                        source="app",
                                        tags=tags,
                                    )
                                    total_registered += 1
                                except Exception as e:
                                    # Silently skip scenarios that can't be registered
                                    pass
                    except Exception as e:
                        print(
                            f"Warning: Failed to register scenarios from {category_dir}: {e}"
                        )

        # Register from custom scenario_paths
        # Each path gets scanned recursively, and scenarios use the folder name as source
        # TODO: Update PathSettings.scenario_paths to be list[ScenarioSource] with explicit names
        settings = SettingsService.load_paths()
        for path_str in settings.scenario_paths:
            path = Path(path_str).expanduser()
            if path.exists():
                # Use the folder name as the source name
                source_name = path.name
                total_registered += self._register_scenarios_from_path(
                    path, source=source_name
                )

        self._registered = True
        return total_registered

    def _register_scenarios_from_path(self, base_path: Path, source: str) -> int:
        """Recursively register all scenarios found under base_path with given source.

        Args:
            base_path: Directory to scan for scenarios
            source: Source name to use for all scenarios found

        Returns:
            Number of scenarios registered
        """
        from negmas import register_scenario

        count = 0
        try:
            for item in base_path.rglob("*"):
                if item.is_dir() and not any(
                    p.name.startswith(".") for p in item.parents
                ):
                    # Check if this looks like a scenario directory
                    # (has domain/utility files)
                    try:
                        # Build tags from ALL folder names in path relative to base_path
                        # This includes all subfolders leading to the scenario
                        rel_path = item.relative_to(base_path)
                        tags = set()
                        # Add all parent folder names as tags
                        for parent in rel_path.parents:
                            if parent != Path("."):
                                tags.add(parent.name)

                        register_scenario(
                            item,
                            source=source,
                            tags=tags,
                        )
                        count += 1
                    except Exception:
                        # Not a valid scenario, skip
                        pass
        except Exception as e:
            print(f"Warning: Failed to scan {base_path} for scenarios: {e}")

        return count

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
        """Convert negmas ScenarioInfo to our ScenarioInfo model."""
        try:
            # Use tags directly from registry
            tags = list(reg_info.tags) if reg_info.tags else []

            # negmas ScenarioInfo has: name, path, source, tags, n_outcomes, n_negotiators, opposition_level, description
            return ScenarioInfo(
                path=str(reg_info.path),
                name=reg_info.name,
                n_negotiators=reg_info.n_negotiators or 2,
                issues=[],  # Will be loaded on detail request
                n_outcomes=reg_info.n_outcomes,
                rational_fraction=None,  # Not in registry, loaded from _info.yaml on detail
                opposition=reg_info.opposition_level,
                source=reg_info.source or "unknown",  # Use actual source from registry
                tags=tags,  # All tags from registry (includes folder names)
                description=reg_info.description or "",  # Description from registry
                has_stats="has-stats" in reg_info.tags if reg_info.tags else False,
                has_info=False,  # Will check on detail load
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
            # Read _info.yml for n_outcomes and rational_fraction (small file, full YAML is fine)
            n_outcomes = None
            rational_fraction = None
            description = ""
            info_file = path / "_info.yml"
            if info_file.exists():
                with open(info_file) as f:
                    info_data = yaml.safe_load(f) or {}
                    n_outcomes = info_data.get("n_outcomes")
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
                issue_info = IssueInfo(
                    name=issue.name,
                    type=type(issue).__name__,
                    values=values[:20] if values and len(values) > 20 else values,
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
        max_info = perf_settings.max_outcomes_info

        # Get n_outcomes early (always calculate this)
        n_outcomes = scenario.outcome_space.cardinality

        # Determine what can be calculated based on limits
        # 0 or None means no limit
        can_calc_stats = max_stats is None or max_stats == 0 or n_outcomes <= max_stats
        can_calc_info = max_info is None or max_info == 0 or n_outcomes <= max_info

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
            # Calculate and store n_outcomes and rational_fraction in info
            if scenario.info is None:
                scenario.info = {}

            # Always set n_outcomes (this is cheap)
            scenario.info["n_outcomes"] = n_outcomes

            # Only calculate rational_fraction if within info limits
            if can_calc_info:
                rational_fraction = calculate_rational_fraction(scenario)
                scenario.info["rational_fraction"] = rational_fraction

        # Save if caching is enabled and something was calculated
        something_calculated = (needs_stats and can_calc_stats) or needs_info
        if something_calculated:
            settings = SettingsService.load_general()
            if settings.cache_scenario_stats:
                try:
                    # Use save_info and save_stats to avoid rewriting original scenario files
                    if needs_info and scenario.info:
                        scenario.save_info(path)
                    if needs_stats and can_calc_stats and scenario.stats:
                        scenario.save_stats(path)
                except Exception:
                    pass  # Ignore save errors (e.g., read-only filesystem)

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
