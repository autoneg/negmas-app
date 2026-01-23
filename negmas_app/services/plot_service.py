"""Plot generation and caching service for scenarios."""

from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from negmas import Scenario

from .outcome_analysis import compute_outcome_utilities
from .settings_service import SettingsService


# Supported image formats for plotly (ordered by file size, smallest first)
SUPPORTED_IMAGE_FORMATS = ["webp", "png", "jpg", "svg"]


def get_plot_path(scenario_path: Path | str, format: str | None = None) -> Path:
    """Get the path to the cached plot file for a scenario.

    Args:
        scenario_path: Path to scenario directory.
        format: Image format (webp, png, jpg, svg). If None, uses settings.

    Returns:
        Path to the _plot.{format} file.
    """
    if format is None:
        performance_settings = SettingsService.load_performance()
        format = performance_settings.plot_image_format
    return Path(scenario_path) / f"_plot.{format}"


def find_existing_plot(scenario_path: Path | str) -> Path | None:
    """Find an existing plot file with any supported format.

    Args:
        scenario_path: Path to scenario directory.

    Returns:
        Path to existing plot file, or None if not found.
    """
    scenario_path = Path(scenario_path)
    for fmt in SUPPORTED_IMAGE_FORMATS:
        plot_file = scenario_path / f"_plot.{fmt}"
        if plot_file.exists():
            return plot_file
    return None


def has_cached_plot(scenario_path: Path | str) -> bool:
    """Check if a cached plot exists for a scenario.

    Args:
        scenario_path: Path to scenario directory.

    Returns:
        True if _plot file exists with any supported format.
    """
    return find_existing_plot(scenario_path) is not None


def generate_and_save_plot(
    scenario: Scenario,
    scenario_path: Path | str,
    max_samples: int = 10000,
    negotiator_x: int = 0,
    negotiator_y: int = 1,
) -> dict[str, Any]:
    """Generate a 2D utility plot and save in configured format.

    Args:
        scenario: Loaded scenario with ufuns and outcome_space.
        scenario_path: Path to scenario directory where plot will be saved.
        max_samples: Maximum number of outcomes to plot.
        negotiator_x: Index of negotiator for X-axis.
        negotiator_y: Index of negotiator for Y-axis.

    Returns:
        Dictionary with plot metadata (path, negotiator names, etc.).
    """
    scenario_path = Path(scenario_path)

    # Get image format from settings
    performance_settings = SettingsService.load_performance()
    image_format = performance_settings.plot_image_format
    plot_file = get_plot_path(scenario_path, image_format)

    # Get negotiator names
    negotiator_names = []
    for i, ufun in enumerate(scenario.ufuns):
        name = getattr(ufun, "name", None) or f"Negotiator {i + 1}"
        negotiator_names.append(name)

    # Ensure valid indices
    if negotiator_x >= len(scenario.ufuns) or negotiator_y >= len(scenario.ufuns):
        negotiator_x = 0
        negotiator_y = min(1, len(scenario.ufuns) - 1)

    # Check outcome limit for plotting
    max_outcomes_plots = performance_settings.max_outcomes_plots
    n_outcomes = scenario.outcome_space.cardinality
    show_outcomes = True

    if max_outcomes_plots is not None and max_outcomes_plots > 0:
        if n_outcomes > max_outcomes_plots:
            show_outcomes = False

    # Compute outcome utilities only if within limit
    outcomes = []
    utilities = []
    x_utils = []
    y_utils = []
    sampled = False
    sample_size = 0

    if show_outcomes:
        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=max_samples * 2)
        )
        utilities, sampled, sample_size = compute_outcome_utilities(
            scenario.ufuns, outcomes, max_samples
        )
        # Extract X and Y utilities
        x_utils = [u[negotiator_x] for u in utilities]
        y_utils = [u[negotiator_y] for u in utilities]

    # Create Plotly figure
    fig = go.Figure()

    # Add outcome scatter only if within limit
    if show_outcomes and outcomes:
        fig.add_trace(
            go.Scatter(
                x=x_utils,
                y=y_utils,
                mode="markers",
                marker=dict(
                    size=4,
                    color="rgba(100, 149, 237, 0.5)",  # Cornflower blue
                    line=dict(width=0),
                ),
                name="Outcomes",
                hovertemplate=f"{negotiator_names[negotiator_x]}: %{{x:.3f}}<br>"
                + f"{negotiator_names[negotiator_y]}: %{{y:.3f}}<extra></extra>",
            )
        )

    # Add Pareto frontier if stats are available
    if scenario.stats and scenario.stats.pareto_utils:
        pareto_x = [u[negotiator_x] for u in scenario.stats.pareto_utils]
        pareto_y = [u[negotiator_y] for u in scenario.stats.pareto_utils]

        fig.add_trace(
            go.Scatter(
                x=pareto_x,
                y=pareto_y,
                mode="markers",
                marker=dict(size=6, color="red"),
                name="Pareto Frontier",
                hovertemplate=f"{negotiator_names[negotiator_x]}: %{{x:.3f}}<br>"
                + f"{negotiator_names[negotiator_y]}: %{{y:.3f}}<extra></extra>",
            )
        )

    # Add special points if available
    special_points = []
    if scenario.stats:
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
                x=[utils[negotiator_x]],
                y=[utils[negotiator_y]],
                mode="markers",
                marker=dict(size=12, color=color, symbol="star"),
                name=name,
                hovertemplate=f"{name}<br>"
                + f"{negotiator_names[negotiator_x]}: %{{x:.3f}}<br>"
                + f"{negotiator_names[negotiator_y]}: %{{y:.3f}}<extra></extra>",
            )
        )

    # Add reservation values if available
    if scenario.ufuns:
        for idx, ufun in enumerate(scenario.ufuns):
            rv = getattr(ufun, "reserved_value", None)
            if rv is not None and rv > 0:
                if idx == negotiator_x:
                    # Vertical line for X-axis negotiator
                    fig.add_vline(
                        x=rv,
                        line_dash="dash",
                        line_color="gray",
                        annotation_text=f"{negotiator_names[idx]} RV",
                        annotation_position="top",
                    )
                elif idx == negotiator_y:
                    # Horizontal line for Y-axis negotiator
                    fig.add_hline(
                        y=rv,
                        line_dash="dash",
                        line_color="gray",
                        annotation_text=f"{negotiator_names[idx]} RV",
                        annotation_position="right",
                    )

    # Update layout
    fig.update_layout(
        title=f"Utility Space: {scenario_path.name}",
        xaxis_title=negotiator_names[negotiator_x],
        yaxis_title=negotiator_names[negotiator_y],
        width=800,
        height=800,
        plot_bgcolor="white",
        showlegend=True,
        legend=dict(x=1.05, y=1, xanchor="left", yanchor="top"),
    )

    # Make plot square (equal aspect ratio)
    fig.update_xaxes(
        scaleanchor="y",
        scaleratio=1,
        showgrid=True,
        gridcolor="lightgray",
        zeroline=True,
        zerolinecolor="black",
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="lightgray", zeroline=True, zerolinecolor="black"
    )

    # Save plot in configured format
    try:
        fig.write_image(
            str(plot_file), format=image_format, width=800, height=800, scale=1.5
        )
    except Exception as e:
        print(f"Warning: Failed to save plot to {plot_file}: {e}")
        # Continue without saving - not critical

    return {
        "plot_path": str(plot_file),
        "exists": plot_file.exists(),
        "negotiator_names": negotiator_names,
        "sampled": sampled,
        "sample_size": sample_size,
    }
