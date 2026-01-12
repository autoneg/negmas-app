"""Load and manage negotiation scenarios."""

from pathlib import Path

from negmas import Scenario

from ..models import ScenarioInfo, IssueInfo


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
            scenario = Scenario.load(path)
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
            )
        except Exception:
            return None

    def load_scenario(self, path: str | Path) -> Scenario | None:
        """Load a full scenario from path.

        Args:
            path: Path to scenario directory.

        Returns:
            Loaded Scenario or None if loading fails.
        """
        return Scenario.load(Path(path))

    def get_scenario_info(self, path: str | Path) -> ScenarioInfo | None:
        """Get info for a specific scenario."""
        path = Path(path)
        # Determine source from path
        try:
            source = path.parent.name
        except Exception:
            source = "unknown"
        return self._load_scenario_info(path, source)
