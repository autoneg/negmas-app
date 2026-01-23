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
    )

    # Get file extension from output_file
    ext = output_file.suffix.lstrip(".")

    # Save the figure
    fig.savefig(output_file, format=ext, dpi=100, bbox_inches="tight")

    # Clean up
    import matplotlib.pyplot as plt

    plt.close(fig)
