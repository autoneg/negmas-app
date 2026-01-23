"""Plot generation and caching service for scenarios."""

from pathlib import Path
from typing import Any

from negmas import Scenario

from .settings_service import SettingsService


# Supported image formats for matplotlib (ordered by file size, smallest first)
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
    """Generate a 2D utility plot and save in configured format using matplotlib.

    Args:
        scenario: Loaded scenario with ufuns and outcome_space.
        scenario_path: Path to scenario directory where plot will be saved.
        max_samples: Maximum number of outcomes to plot (ignored, kept for API compatibility).
        negotiator_x: Index of negotiator for X-axis.
        negotiator_y: Index of negotiator for Y-axis.

    Returns:
        Dictionary with plot metadata (path, negotiator names, etc.).
    """
    from .plot_utils import save_scenario_plot

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

    # Use matplotlib-based plotting utility
    try:
        save_scenario_plot(
            scenario,
            plot_file,
            ufun_indices=(negotiator_x, negotiator_y),
            show_outcomes=show_outcomes,
        )
    except Exception as e:
        print(f"Warning: Failed to save plot to {plot_file}: {e}")
        # Continue without saving - not critical

    return {
        "plot_path": str(plot_file),
        "exists": plot_file.exists(),
        "negotiator_names": negotiator_names,
        "sampled": False,  # Not applicable for matplotlib plots
        "sample_size": 0,  # Not applicable for matplotlib plots
    }
