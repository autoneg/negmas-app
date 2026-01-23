"""Service for managing scenario cache files (info, stats, plots)."""

from pathlib import Path
from typing import Any

import yaml
from negmas import Scenario


class ScenarioCacheService:
    """Service for building and clearing scenario cache files."""

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
    ) -> dict[str, Any]:
        """Build cache files for all scenarios.

        Args:
            build_info: Build _info.yaml files
            build_stats: Build _stats.yaml files
            build_plots: Build plot files (_plot.webp or _plots/)
            compact: If True, exclude Pareto frontier from stats (saves space)

        Returns:
            Dictionary with build results and statistics.
        """
        results = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "info_created": 0,
            "stats_created": 0,
            "plots_created": 0,
            "errors": [],
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
                )

                if success["success"]:
                    results["successful"] += 1
                    results["info_created"] += success["info_created"]
                    results["stats_created"] += success["stats_created"]
                    results["plots_created"] += success["plots_created"]
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
        console=None,
    ) -> dict[str, Any]:
        """Build cache files for all scenarios with rich progress display.

        Args:
            build_info: Build _info.yaml files
            build_stats: Build _stats.yaml files
            build_plots: Build plot files (_plot.webp or _plots/)
            compact: If True, exclude Pareto frontier from stats (saves space)
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
            "plots_created": 0,
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
                    )

                    if success["success"]:
                        results["successful"] += 1
                        results["info_created"] += success["info_created"]
                        results["stats_created"] += success["stats_created"]
                        results["plots_created"] += success["plots_created"]
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
    ) -> dict[str, Any]:
        """Build cache files for a single scenario.

        Args:
            scenario_dir: Path to scenario directory
            build_info: Build _info.yaml
            build_stats: Build _stats.yaml
            build_plots: Build plot files
            compact: If True, exclude Pareto frontier from stats

        Returns:
            Dictionary with success status and counts.
        """
        result = {
            "success": True,
            "error": None,
            "info_created": 0,
            "stats_created": 0,
            "plots_created": 0,
        }

        try:
            # Load scenario with appropriate flags
            scenario = Scenario.load(
                scenario_dir,
                load_info=build_info,
                load_stats=build_stats,
            )

            # Build info cache
            if build_info:
                info_file = scenario_dir / "_info.yaml"
                if not info_file.exists():
                    # Calculate rational fraction if needed
                    from .scenario_loader import calculate_rational_fraction

                    rational_fraction = calculate_rational_fraction(scenario)

                    info_data = {
                        "n_outcomes": scenario.outcome_space.cardinality,
                        "n_issues": len(scenario.outcome_space.issues),
                        "rational_fraction": rational_fraction,
                        "description": scenario_dir.name,  # Use directory name as description
                    }

                    with open(info_file, "w") as f:
                        yaml.dump(info_data, f, default_flow_style=False)

                    result["info_created"] = 1

            # Build stats cache
            if build_stats:
                stats_file = scenario_dir / "_stats.yaml"
                if not stats_file.exists():
                    # Calculate stats using negmas built-in method
                    scenario.calc_stats()

                    # Save stats with include_pareto_frontier option
                    scenario.save_stats(
                        scenario_dir,
                        compact=False,
                        include_pareto_frontier=not compact,  # Exclude if compact=True
                    )

                    result["stats_created"] = 1

            # Build plot cache
            if build_plots:
                n_negotiators = len(scenario.ufuns)

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

                if n_negotiators == 2:
                    # Bilateral: single _plot.webp
                    plot_file = scenario_dir / "_plot.webp"
                    if not plot_file.exists():
                        self._create_bilateral_plot(scenario, plot_file)
                        result["plots_created"] = 1

                else:
                    # Multilateral: _plots/ folder with multiple images
                    plots_dir = scenario_dir / "_plots"
                    plots_dir.mkdir(exist_ok=True)

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

                        if not plot_file.exists():
                            self._create_multilateral_plot(
                                scenario, i, next_i, plot_file
                            )
                            result["plots_created"] += 1

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
        import plotly.graph_objects as go

        # Sample outcomes
        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=5000)
        )

        if not outcomes:
            return

        # Calculate utilities
        utilities_0 = [scenario.ufuns[0](o) for o in outcomes]
        utilities_1 = [scenario.ufuns[1](o) for o in outcomes]

        # Create plot
        fig = go.Figure()

        # Add all outcomes
        fig.add_trace(
            go.Scatter(
                x=utilities_0,
                y=utilities_1,
                mode="markers",
                marker=dict(size=3, color="#6b7280", opacity=0.5),
                name="Outcomes",
                showlegend=False,
            )
        )

        # Add Pareto frontier if stats are available
        if (
            hasattr(scenario, "stats")
            and scenario.stats
            and scenario.stats.pareto_utils
        ):
            pareto_x = [u[0] for u in scenario.stats.pareto_utils]
            pareto_y = [u[1] for u in scenario.stats.pareto_utils]

            fig.add_trace(
                go.Scatter(
                    x=pareto_x,
                    y=pareto_y,
                    mode="markers",
                    marker=dict(size=6, color="red"),
                    name="Pareto Frontier",
                    showlegend=True,
                )
            )

        # Add special points if stats are available
        special_points = []
        if hasattr(scenario, "stats") and scenario.stats:
            if scenario.stats.nash_utils and len(scenario.stats.nash_utils) > 0:
                special_points.append(("Nash", scenario.stats.nash_utils[0], "purple"))
            if scenario.stats.kalai_utils and len(scenario.stats.kalai_utils) > 0:
                special_points.append(("Kalai", scenario.stats.kalai_utils[0], "green"))
            if scenario.stats.ks_utils and len(scenario.stats.ks_utils) > 0:
                special_points.append(("KS", scenario.stats.ks_utils[0], "orange"))
            if (
                scenario.stats.max_welfare_utils
                and len(scenario.stats.max_welfare_utils) > 0
            ):
                special_points.append(
                    ("MaxWelfare", scenario.stats.max_welfare_utils[0], "blue")
                )

        for name, utils, color in special_points:
            fig.add_trace(
                go.Scatter(
                    x=[utils[0]],
                    y=[utils[1]],
                    mode="markers",
                    marker=dict(size=12, color=color, symbol="star"),
                    name=name,
                    showlegend=True,
                )
            )

        fig.update_layout(
            xaxis_title=getattr(scenario.ufuns[0], "name", "Negotiator 0"),
            yaxis_title=getattr(scenario.ufuns[1], "name", "Negotiator 1"),
            width=600,
            height=500,
            margin=dict(l=60, r=20, t=20, b=60),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=True,
            legend=dict(x=1.05, y=1, xanchor="left", yanchor="top"),
        )

        fig.update_xaxes(gridcolor="#e0e0e0")
        fig.update_yaxes(gridcolor="#e0e0e0")

        # Save as webp
        fig.write_image(output_file, format="webp")

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
        import plotly.graph_objects as go

        # Sample outcomes
        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=5000)
        )

        if not outcomes:
            return

        # Calculate utilities for the two negotiators
        utilities_1 = [scenario.ufuns[idx1](o) for o in outcomes]
        utilities_2 = [scenario.ufuns[idx2](o) for o in outcomes]

        # Create plot
        fig = go.Figure()

        # Add all outcomes
        fig.add_trace(
            go.Scatter(
                x=utilities_1,
                y=utilities_2,
                mode="markers",
                marker=dict(size=3, color="#6b7280", opacity=0.5),
                name="Outcomes",
                showlegend=False,
            )
        )

        # Add Pareto frontier if stats are available (project to 2D)
        if (
            hasattr(scenario, "stats")
            and scenario.stats
            and scenario.stats.pareto_utils
        ):
            pareto_x = [u[idx1] for u in scenario.stats.pareto_utils]
            pareto_y = [u[idx2] for u in scenario.stats.pareto_utils]

            fig.add_trace(
                go.Scatter(
                    x=pareto_x,
                    y=pareto_y,
                    mode="markers",
                    marker=dict(size=6, color="red"),
                    name="Pareto Frontier",
                    showlegend=True,
                )
            )

        # Add special points if stats are available (project to 2D)
        special_points = []
        if hasattr(scenario, "stats") and scenario.stats:
            if scenario.stats.nash_utils and len(scenario.stats.nash_utils) > 0:
                special_points.append(("Nash", scenario.stats.nash_utils[0], "purple"))
            if scenario.stats.kalai_utils and len(scenario.stats.kalai_utils) > 0:
                special_points.append(("Kalai", scenario.stats.kalai_utils[0], "green"))
            if scenario.stats.ks_utils and len(scenario.stats.ks_utils) > 0:
                special_points.append(("KS", scenario.stats.ks_utils[0], "orange"))
            if (
                scenario.stats.max_welfare_utils
                and len(scenario.stats.max_welfare_utils) > 0
            ):
                special_points.append(
                    ("MaxWelfare", scenario.stats.max_welfare_utils[0], "blue")
                )

        for name, utils, color in special_points:
            fig.add_trace(
                go.Scatter(
                    x=[utils[idx1]],
                    y=[utils[idx2]],
                    mode="markers",
                    marker=dict(size=12, color=color, symbol="star"),
                    name=name,
                    showlegend=True,
                )
            )

        fig.update_layout(
            xaxis_title=getattr(scenario.ufuns[idx1], "name", f"Negotiator {idx1}"),
            yaxis_title=getattr(scenario.ufuns[idx2], "name", f"Negotiator {idx2}"),
            width=600,
            height=500,
            margin=dict(l=60, r=20, t=20, b=60),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=True,
            legend=dict(x=1.05, y=1, xanchor="left", yanchor="top"),
        )

        fig.update_xaxes(gridcolor="#e0e0e0")
        fig.update_yaxes(gridcolor="#e0e0e0")

        # Save as webp
        fig.write_image(output_file, format="webp")

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
