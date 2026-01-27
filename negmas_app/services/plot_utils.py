"""Plotting utilities for scenarios - uses negmas built-in plotting."""

from pathlib import Path

from negmas import Scenario

from .settings_service import SettingsService


def save_scenario_plot(
    scenario: Scenario,
    output_file: Path,
    ufun_indices: tuple[int, int] | None = None,
    show_outcomes: bool = True,
) -> None:
    """Save a 2D utility space plot for a scenario using negmas's built-in plotting.

    Args:
        scenario: Scenario to plot
        output_file: Path to save the plot (webp format)
        ufun_indices: Tuple of (i, j) specifying which pair of utility functions to plot.
            If None, plots the first two ufuns (indices 0 and 1).
        show_outcomes: Whether to show outcome space background (set False for large spaces)

    Important Note:
        For multilateral scenarios (>2 negotiators), there is a known discrepancy between
        cached plots and interactive plots:

        - Cached plots (this function): Uses scenario.plot() which calls negmas's plot_2dutils
          with only the 2 selected ufuns. The special solution points (Nash, Kalai, KS,
          Max Welfare) are calculated for ONLY these 2 ufuns, not for all negotiators.

        - Interactive plots (frontend): Uses pre-calculated scenario.stats which contains
          solution points calculated for ALL ufuns, then projects them to the 2D view.

        This means the solution points may appear in different locations. The interactive
        plot shows the correct global solution points, while the cached plot shows solution
        points for the 2D sub-problem.

        This is a limitation in negmas's plot_2dutils function (as of version checked),
        which recalculates solution points from the provided ufuns rather than accepting
        pre-calculated stats. A potential enhancement would be to modify negmas to accept
        optional pre-calculated stats points.
    """
    # Load performance settings to control what's shown
    settings = SettingsService.load_performance()
    n_outcomes = scenario.outcome_space.cardinality

    # Determine what to show based on outcome space size
    mark_outcomes = show_outcomes
    mark_pareto = True
    use_fast_mode = False

    # Check if we should show Pareto frontier based on size
    max_pareto = settings.max_outcomes_pareto
    if max_pareto is not None and max_pareto > 0:
        if n_outcomes > max_pareto:
            mark_pareto = False

    # For very large scenarios (> 1M outcomes), use fast mode to skip expensive calculations
    # This prevents negmas from computing Pareto/Nash/Kalai from all outcomes
    if n_outcomes > 1_000_000:
        use_fast_mode = True
        mark_pareto = False
        # Only show special points if stats were pre-computed
        mark_special_points = scenario.stats is not None
    else:
        # Special points (Nash, Kalai, etc.) are always shown if stats exist
        # since they're just single points and not expensive
        mark_special_points = True

    # Use negmas's built-in plot method with matplotlib backend
    # Hide time/steps annotations since this is a scenario cache (not a negotiation trace)
    fig = scenario.plot(
        ufun_indices=ufun_indices,
        backend="matplotlib",
        mark_all_outcomes=mark_outcomes,
        mark_pareto_points=mark_pareto,
        mark_nash_points=mark_special_points,
        mark_kalai_points=mark_special_points,
        mark_ks_points=mark_special_points,
        mark_max_welfare_points=mark_special_points,
        fast=use_fast_mode,  # Skip expensive calculations for large scenarios
        show_total_time=False,  # Hide "Total Time = 0ms" (not applicable for scenario plots)
        show_n_steps=False,  # Hide "N. Steps = 0" (not applicable for scenario plots)
    )

    # Get file extension from output_file
    ext = output_file.suffix.lstrip(".")

    # Save the figure
    fig.savefig(output_file, format=ext, dpi=100, bbox_inches="tight")

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)
