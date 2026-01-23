"""Service for managing scenario cache files (info, stats, plots)."""

from pathlib import Path
from typing import Any

import yaml
from negmas import Scenario

from ..services.settings_service import SettingsService


class ScenarioCacheService:
    """Service for building and clearing scenario cache files."""

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

        # Load settings to respect limits
        self.settings = SettingsService.load_all()

    def _find_all_scenario_dirs(self) -> list[Path]:
        """Find all scenario directories recursively.

        Returns:
            List of paths to scenario directories.
        """
        scenario_dirs = []

        if not self.scenarios_root.exists():
            return scenario_dirs

        # Recursively find all directories that look like scenarios
        # (have domain/utility files or already have cache files)
        for item in self.scenarios_root.rglob("*"):
            if item.is_dir() and not any(p.name.startswith(".") for p in item.parents):
                # Check if this looks like a scenario directory
                has_domain_files = any(
                    f.suffix in {".yml", ".yaml", ".xml"}
                    for f in item.iterdir()
                    if f.is_file() and not f.name.startswith("_")
                )
                has_cache_files = any(
                    f.name in {"_info.yaml", "_info.yml", "_stats.yaml", "_plot.webp"}
                    for f in item.iterdir()
                    if f.is_file()
                )

                if has_domain_files or has_cache_files:
                    scenario_dirs.append(item)

        return scenario_dirs

    def build_caches(
        self,
        build_info: bool = False,
        build_stats: bool = False,
        build_plots: bool = False,
        compact: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Build cache files for all scenarios.

        Args:
            build_info: Build _info.yaml files
            build_stats: Build _stats.yaml files
            build_plots: Build plot files (_plot.webp or _plots/)
            compact: If True, exclude Pareto frontier from stats (saves space)
            refresh: If True, rebuild existing cache files (default: skip existing)

        Returns:
            Dictionary with build results and statistics.
        """
        results = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "info_created": 0,
            "stats_created": 0,
            "stats_skipped": 0,
            "plots_created": 0,
            "errors": [],
            "skipped": [],  # List of (scenario_name, reason) tuples
        }

        scenario_dirs = self._find_all_scenario_dirs()
        results["total"] = len(scenario_dirs)

        for scenario_dir in scenario_dirs:
            try:
                success = self._build_scenario_cache(
                    scenario_dir,
                    build_info=build_info,
                    build_stats=build_stats,
                    build_plots=build_plots,
                    compact=compact,
                    refresh=refresh,
                )

                if success["success"]:
                    results["successful"] += 1
                    results["info_created"] += success["info_created"]
                    results["stats_created"] += success["stats_created"]
                    results["stats_skipped"] += success.get("stats_skipped", 0)
                    results["plots_created"] += success["plots_created"]
                    if success.get("skip_reason"):
                        results["skipped"].append(
                            (scenario_dir.name, success["skip_reason"])
                        )
                else:
                    results["failed"] += 1
                    if success["error"]:
                        results["errors"].append(
                            f"{scenario_dir.name}: {success['error']}"
                        )

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{scenario_dir.name}: {str(e)}")

        return results

    def build_caches_with_progress(
        self,
        build_info: bool = False,
        build_stats: bool = False,
        build_plots: bool = False,
        compact: bool = False,
        refresh: bool = False,
        console=None,
    ) -> dict[str, Any]:
        """Build cache files for all scenarios with rich progress display.

        Args:
            build_info: Build _info.yaml files
            build_stats: Build _stats.yaml files
            build_plots: Build plot files (_plot.webp or _plots/)
            compact: If True, exclude Pareto frontier from stats (saves space)
            refresh: If True, rebuild existing cache files (default: skip existing)
            console: Rich console for output (optional)

        Returns:
            Dictionary with build results and statistics.
        """
        from rich.progress import (
            Progress,
            SpinnerColumn,
            TextColumn,
            BarColumn,
            TaskProgressColumn,
            TimeRemainingColumn,
        )

        results = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "info_created": 0,
            "stats_created": 0,
            "stats_skipped": 0,
            "plots_created": 0,
            "errors": [],
            "skipped": [],  # List of (scenario_name, reason) tuples
        }

        scenario_dirs = self._find_all_scenario_dirs()
        results["total"] = len(scenario_dirs)

        if results["total"] == 0:
            return results

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Building caches...", total=results["total"])

            for scenario_dir in scenario_dirs:
                # Update progress description with current scenario
                progress.update(
                    task, description=f"[cyan]Processing {scenario_dir.name}..."
                )

                try:
                    success = self._build_scenario_cache(
                        scenario_dir,
                        build_info=build_info,
                        build_stats=build_stats,
                        build_plots=build_plots,
                        compact=compact,
                        refresh=refresh,
                    )

                    if success["success"]:
                        results["successful"] += 1
                        results["info_created"] += success["info_created"]
                        results["stats_created"] += success["stats_created"]
                        results["stats_skipped"] += success.get("stats_skipped", 0)
                        results["plots_created"] += success["plots_created"]
                        if success.get("skip_reason"):
                            results["skipped"].append(
                                (scenario_dir.name, success["skip_reason"])
                            )
                    else:
                        results["failed"] += 1
                        if success["error"]:
                            results["errors"].append(
                                f"{scenario_dir.name}: {success['error']}"
                            )

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{scenario_dir.name}: {str(e)}")

                progress.advance(task)

        return results

    def clear_caches_with_progress(
        self,
        clear_info: bool = False,
        clear_stats: bool = False,
        clear_plots: bool = False,
        console=None,
    ) -> dict[str, Any]:
        """Clear cache files for all scenarios with rich progress display.

        Args:
            clear_info: Clear _info.yaml files
            clear_stats: Clear _stats.yaml files
            clear_plots: Clear plot files (_plot.webp or _plots/)
            console: Rich console for output (optional)

        Returns:
            Dictionary with clear results and statistics.
        """
        from rich.progress import (
            Progress,
            SpinnerColumn,
            TextColumn,
            BarColumn,
            TaskProgressColumn,
        )

        results = {
            "total": 0,
            "info_deleted": 0,
            "stats_deleted": 0,
            "plots_deleted": 0,
            "errors": [],
        }

        scenario_dirs = self._find_all_scenario_dirs()
        results["total"] = len(scenario_dirs)

        if results["total"] == 0:
            return results

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[red]Clearing caches...", total=results["total"])

            for scenario_dir in scenario_dirs:
                # Update progress description with current scenario
                progress.update(
                    task, description=f"[red]Clearing {scenario_dir.name}..."
                )

                try:
                    # Clear info
                    if clear_info:
                        for filename in ["_info.yaml", "_info.yml"]:
                            info_file = scenario_dir / filename
                            if info_file.exists():
                                info_file.unlink()
                                results["info_deleted"] += 1

                    # Clear stats
                    if clear_stats:
                        stats_file = scenario_dir / "_stats.yaml"
                        if stats_file.exists():
                            stats_file.unlink()
                            results["stats_deleted"] += 1

                    # Clear plots
                    if clear_plots:
                        # Clear bilateral plot
                        plot_file = scenario_dir / "_plot.webp"
                        if plot_file.exists():
                            plot_file.unlink()
                            results["plots_deleted"] += 1

                        # Clear multilateral plots folder
                        plots_dir = scenario_dir / "_plots"
                        if plots_dir.exists() and plots_dir.is_dir():
                            # Delete all image files in the folder
                            for img_file in plots_dir.glob("*.webp"):
                                img_file.unlink()
                                results["plots_deleted"] += 1

                            # Remove the folder if empty
                            try:
                                plots_dir.rmdir()
                            except OSError:
                                # Not empty, that's okay
                                pass

                except Exception as e:
                    results["errors"].append(f"{scenario_dir.name}: {str(e)}")

                progress.advance(task)

        return results

    def _build_scenario_cache(
        self,
        scenario_dir: Path,
        build_info: bool,
        build_stats: bool,
        build_plots: bool,
        compact: bool = False,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Build cache files for a single scenario.

        Args:
            scenario_dir: Path to scenario directory
            build_info: Build _info.yaml
            build_stats: Build _stats.yaml
            build_plots: Build plot files
            compact: If True, exclude Pareto frontier from stats
            refresh: If True, rebuild existing files (default: skip existing)

        Returns:
            Dictionary with success status and counts.
        """
        result = {
            "success": True,
            "error": None,
            "info_created": 0,
            "stats_created": 0,
            "stats_skipped": 0,
            "plots_created": 0,
            "skip_reason": None,
        }

        try:
            # Load scenario with appropriate flags
            scenario = Scenario.load(
                scenario_dir,
                load_info=build_info,
                load_stats=build_stats,
            )

            # Get outcome limit from settings
            max_outcomes_stats = self.settings.performance.max_outcomes_stats
            n_outcomes = scenario.outcome_space.cardinality

            # Check if stats should be skipped due to size
            skip_stats = False
            if (
                build_stats
                and max_outcomes_stats is not None
                and max_outcomes_stats > 0
            ):
                if n_outcomes > max_outcomes_stats:
                    skip_stats = True
                    result["skip_reason"] = (
                        f"Stats skipped: {n_outcomes:,} outcomes > limit {max_outcomes_stats:,}"
                    )

            # Build info cache
            if build_info:
                info_file = scenario_dir / "_info.yaml"
                if refresh or not info_file.exists():
                    # Check if rationality should be calculated
                    max_outcomes_rationality = (
                        self.settings.performance.max_outcomes_rationality
                    )
                    calculate_rationality = True
                    rational_fraction = None

                    if (
                        max_outcomes_rationality is not None
                        and max_outcomes_rationality > 0
                    ):
                        if n_outcomes > max_outcomes_rationality:
                            calculate_rationality = False

                    if calculate_rationality:
                        # Calculate rational fraction if within limit
                        from .scenario_loader import calculate_rational_fraction

                        rational_fraction = calculate_rational_fraction(scenario)

                    info_data = {
                        "n_outcomes": scenario.outcome_space.cardinality,
                        "n_issues": len(scenario.outcome_space.issues),
                        "n_negotiators": len(scenario.ufuns),
                        "rational_fraction": rational_fraction,  # Will be None if skipped
                        "description": scenario_dir.name,  # Use directory name as description
                    }

                    with open(info_file, "w") as f:
                        yaml.dump(info_data, f, default_flow_style=False)

                    result["info_created"] = 1

            # Build stats cache
            if build_stats and not skip_stats:
                stats_file = scenario_dir / "_stats.yaml"
                if refresh or not stats_file.exists():
                    try:
                        # Calculate stats using negmas built-in method
                        scenario.calc_stats()

                        # Save stats with include_pareto_frontier option
                        scenario.save_stats(
                            scenario_dir,
                            compact=False,
                            include_pareto_frontier=not compact,  # Exclude if compact=True
                        )

                        result["stats_created"] = 1
                    except (KeyError, ValueError, TypeError) as e:
                        # Some scenarios have malformed utility functions
                        # Skip stats but don't fail the entire build
                        result["stats_skipped"] = 1
                        skip_msg = f"Stats failed: {str(e)}"
                        if result.get("skip_reason"):
                            result["skip_reason"] = (
                                result["skip_reason"] + " " + skip_msg
                            )
                        else:
                            result["skip_reason"] = skip_msg
            elif build_stats and skip_stats:
                result["stats_skipped"] = 1

            # Build plot cache
            if build_plots:
                n_negotiators = len(scenario.ufuns)

                # Skip plotting for very large scenarios (> 1M outcomes)
                # Even with fast mode, negmas samples outcomes which is slow
                skip_plots = False
                if n_outcomes > 1_000_000:
                    skip_plots = True
                    skip_msg = f"Plots skipped: {n_outcomes:,} outcomes > 1M"
                    if result.get("skip_reason"):
                        result["skip_reason"] = result["skip_reason"] + " " + skip_msg
                    else:
                        result["skip_reason"] = skip_msg

                if skip_plots:
                    # Don't create any plots for very large scenarios
                    pass
                else:
                    # If stats are being built or already exist, ensure they're loaded
                    # so we can include special points in plots
                    if build_stats or (scenario_dir / "_stats.yaml").exists():
                        if not hasattr(scenario, "stats") or scenario.stats is None:
                            # Load stats from file if they exist
                            stats_file = scenario_dir / "_stats.yaml"
                            if stats_file.exists():
                                scenario = Scenario.load(
                                    scenario_dir, load_stats=True, load_info=False
                                )
                        # If stats are being built, they're already calculated above
                        # (scenario.calc_stats() was called)

                    try:
                        if n_negotiators == 2:
                            # Bilateral: single _plot.webp (remove _plots/ if it exists)
                            plot_file = scenario_dir / "_plot.webp"
                            plots_dir = scenario_dir / "_plots"

                            # Clean up _plots/ folder if it exists for bilateral
                            if plots_dir.exists():
                                import shutil

                                shutil.rmtree(plots_dir)

                            if refresh or not plot_file.exists():
                                self._create_bilateral_plot(scenario, plot_file)
                                result["plots_created"] = 1

                        else:
                            # Multilateral: _plots/ folder with multiple images (remove _plot.webp if it exists)
                            plots_dir = scenario_dir / "_plots"
                            plots_dir.mkdir(exist_ok=True)

                            # Clean up single _plot.webp file if it exists for multilateral
                            single_plot = scenario_dir / "_plot.webp"
                            if single_plot.exists():
                                single_plot.unlink()

                            # Get ufun names
                            ufun_names = [
                                getattr(ufun, "name", f"ufun{i}")
                                for i, ufun in enumerate(scenario.ufuns)
                            ]

                            # Create plots for consecutive pairs: 0vs1, 1vs2, 2vs3, 3vs0
                            for i in range(n_negotiators):
                                next_i = (i + 1) % n_negotiators
                                plot_name = f"{ufun_names[i]}-{ufun_names[next_i]}.webp"
                                plot_file = plots_dir / plot_name

                                if refresh or not plot_file.exists():
                                    self._create_multilateral_plot(
                                        scenario, i, next_i, plot_file
                                    )
                                    result["plots_created"] += 1
                    except (KeyError, ValueError, TypeError) as e:
                        # Plot generation failed due to malformed scenario
                        skip_msg = f"Plots failed: {str(e)}"
                        if result.get("skip_reason"):
                            result["skip_reason"] = (
                                result["skip_reason"] + " " + skip_msg
                            )
                        else:
                            result["skip_reason"] = skip_msg

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def _create_bilateral_plot(self, scenario: Scenario, output_file: Path) -> None:
        """Create a bilateral 2D utility space plot.

        Args:
            scenario: Scenario with 2 negotiators
            output_file: Path to save the plot
        """
        from .plot_utils import save_scenario_plot

        # Check outcome limit for plotting
        max_outcomes_plots = self.settings.performance.max_outcomes_plots
        n_outcomes = scenario.outcome_space.cardinality
        show_outcomes = True

        if max_outcomes_plots is not None and max_outcomes_plots > 0:
            if n_outcomes > max_outcomes_plots:
                show_outcomes = False

        # Use centralized plotting utility
        save_scenario_plot(
            scenario, output_file, ufun_indices=(0, 1), show_outcomes=show_outcomes
        )

    def _create_multilateral_plot(
        self, scenario: Scenario, idx1: int, idx2: int, output_file: Path
    ) -> None:
        """Create a 2D utility space plot for two specific negotiators.

        Args:
            scenario: Scenario with multiple negotiators
            idx1: Index of first negotiator
            idx2: Index of second negotiator
            output_file: Path to save the plot
        """
        from .plot_utils import save_scenario_plot

        # Check outcome limit for plotting
        max_outcomes_plots = self.settings.performance.max_outcomes_plots
        n_outcomes = scenario.outcome_space.cardinality
        show_outcomes = True

        if max_outcomes_plots is not None and max_outcomes_plots > 0:
            if n_outcomes > max_outcomes_plots:
                show_outcomes = False

        # Use centralized plotting utility
        save_scenario_plot(
            scenario,
            output_file,
            ufun_indices=(idx1, idx2),
            show_outcomes=show_outcomes,
        )

    def clear_caches(
        self,
        clear_info: bool = False,
        clear_stats: bool = False,
        clear_plots: bool = False,
    ) -> dict[str, Any]:
        """Clear cache files for all scenarios.

        Args:
            clear_info: Clear _info.yaml files
            clear_stats: Clear _stats.yaml files
            clear_plots: Clear plot files (_plot.webp or _plots/)

        Returns:
            Dictionary with clear results and statistics.
        """
        results = {
            "total": 0,
            "info_deleted": 0,
            "stats_deleted": 0,
            "plots_deleted": 0,
            "errors": [],
        }

        scenario_dirs = self._find_all_scenario_dirs()
        results["total"] = len(scenario_dirs)

        for scenario_dir in scenario_dirs:
            try:
                # Clear info
                if clear_info:
                    for filename in ["_info.yaml", "_info.yml"]:
                        info_file = scenario_dir / filename
                        if info_file.exists():
                            info_file.unlink()
                            results["info_deleted"] += 1

                # Clear stats
                if clear_stats:
                    stats_file = scenario_dir / "_stats.yaml"
                    if stats_file.exists():
                        stats_file.unlink()
                        results["stats_deleted"] += 1

                # Clear plots
                if clear_plots:
                    # Clear bilateral plot
                    plot_file = scenario_dir / "_plot.webp"
                    if plot_file.exists():
                        plot_file.unlink()
                        results["plots_deleted"] += 1

                    # Clear multilateral plots folder
                    plots_dir = scenario_dir / "_plots"
                    if plots_dir.exists() and plots_dir.is_dir():
                        # Delete all image files in the folder
                        for img_file in plots_dir.glob("*.webp"):
                            img_file.unlink()
                            results["plots_deleted"] += 1

                        # Remove the folder if empty
                        try:
                            plots_dir.rmdir()
                        except OSError:
                            # Not empty, that's okay
                            pass

            except Exception as e:
                results["errors"].append(f"{scenario_dir.name}: {str(e)}")

        return results
