"""Load and manage negotiation scenarios."""

from pathlib import Path
from typing import Any

from negmas import Scenario

from ..models import ScenarioInfo, IssueInfo, ScenarioStatsInfo
from .settings_service import SettingsService


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

    def list_sources(self) -> list[str]:
        """List available scenario sources (e.g., anac2019, anac2020)."""
        if not self.scenarios_root.exists():
            return []
        return sorted(
            [
                d.name
                for d in self.scenarios_root.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        )

    def list_scenarios(self, source: str | None = None) -> list[ScenarioInfo]:
        """List all scenarios, optionally filtered by source.

        Args:
            source: Filter by source (e.g., "anac2019"). None returns all.
        """
        scenarios = []

        if source:
            sources = [source] if (self.scenarios_root / source).exists() else []
        else:
            sources = self.list_sources()

        for src in sources:
            src_path = self.scenarios_root / src
            for scenario_dir in sorted(src_path.iterdir()):
                if scenario_dir.is_dir() and not scenario_dir.name.startswith("."):
                    info = self._load_scenario_info(scenario_dir, src)
                    if info:
                        scenarios.append(info)

        return scenarios

    def _load_scenario_info(self, path: Path, source: str) -> ScenarioInfo | None:
        """Load scenario info without full parsing."""
        try:
            # Load with stats and info to check if they're cached
            scenario = Scenario.load(path, load_stats=True, load_info=True)  # type: ignore[attr-defined]
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

            return ScenarioInfo(
                path=str(path),
                name=path.name,
                n_negotiators=len(scenario.ufuns),
                issues=issues,
                n_outcomes=n_outcomes,
                source=source,
                has_stats=scenario.stats is not None,
                has_info=scenario.info is not None,
            )
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
        """Get info for a specific scenario."""
        path = Path(path)
        # Determine source from path
        try:
            source = path.parent.name
        except Exception:
            source = "unknown"
        return self._load_scenario_info(path, source)

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

        # Calculate stats if needed
        if scenario.stats is None or force:
            scenario.calc_stats()

            # Save if caching is enabled
            settings = SettingsService.load_general()
            if settings.cache_scenario_stats:
                try:
                    scenario.dumpas(path, save_stats=True, save_info=True)
                except Exception:
                    pass  # Ignore save errors (e.g., read-only filesystem)

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

        # Convert numpy types to Python types for JSON serialization
        def to_list(utils: Any) -> list[list[float]] | None:
            if utils is None:
                return None
            result = []
            for u in utils:
                result.append([float(x) for x in u])
            return result if result else None

        return ScenarioStatsInfo(
            has_stats=True,
            opposition=float(stats.opposition)
            if stats.opposition is not None
            else None,
            utility_ranges=[(float(lo), float(hi)) for lo, hi in stats.utility_ranges]
            if stats.utility_ranges
            else None,
            n_pareto_outcomes=len(stats.pareto_utils) if stats.pareto_utils else 0,
            nash_utils=to_list(stats.nash_utils),
            kalai_utils=to_list(stats.kalai_utils),
            ks_utils=to_list(stats.ks_utils),
            max_welfare_utils=to_list(stats.max_welfare_utils),
            modified_kalai_utils=to_list(stats.modified_kalai_utils),
            modified_ks_utils=to_list(stats.modified_ks_utils),
            max_relative_welfare_utils=to_list(stats.max_relative_welfare_utils),
            pareto_utils=to_list(stats.pareto_utils),
            negotiator_names=negotiator_names,
        )
