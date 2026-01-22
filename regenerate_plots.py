#!/usr/bin/env python3
"""Script to regenerate all cached scenario plots with corrected Pareto frontier visualization."""

from pathlib import Path

from negmas import Scenario

from negmas_app.services.plot_service import generate_and_save_plot


def find_all_scenarios(base_path: Path) -> list[Path]:
    """Find all scenario directories containing scenario.json files.

    Args:
        base_path: Root directory to search for scenarios.

    Returns:
        List of paths to scenario directories.
    """
    scenarios = []
    if not base_path.exists():
        print(f"Warning: Path does not exist: {base_path}")
        return scenarios

    for scenario_json in base_path.rglob("scenario.json"):
        scenario_dir = scenario_json.parent
        scenarios.append(scenario_dir)

    return sorted(scenarios)


def regenerate_scenario_plot(scenario_path: Path) -> bool:
    """Regenerate the plot for a single scenario.

    Args:
        scenario_path: Path to scenario directory.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Load scenario with stats
        scenario = Scenario.load(scenario_path, load_stats=True, load_info=False)

        # Delete old plot if it exists
        plot_file = scenario_path / "_plot.webp"
        if plot_file.exists():
            plot_file.unlink()
            print(f"  Deleted old plot: {plot_file}")

        # Generate new plot
        result = generate_and_save_plot(scenario, scenario_path)

        if result["exists"]:
            print(f"  ✓ Regenerated plot: {result['plot_path']}")
            return True
        else:
            print(f"  ✗ Failed to create plot")
            return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Main entry point."""
    import sys

    # Get base path from command line or use default
    if len(sys.argv) > 1:
        base_path = Path(sys.argv[1]).expanduser()
    else:
        base_path = Path.home() / "negmas" / "scenarios"

    print(f"Searching for scenarios in: {base_path}")
    scenarios = find_all_scenarios(base_path)

    if not scenarios:
        print("No scenarios found.")
        return

    print(f"\nFound {len(scenarios)} scenarios\n")

    # Process each scenario
    success_count = 0
    for i, scenario_path in enumerate(scenarios, 1):
        print(f"[{i}/{len(scenarios)}] {scenario_path.name}")
        if regenerate_scenario_plot(scenario_path):
            success_count += 1

    print(f"\n{'=' * 60}")
    print(f"Summary: {success_count}/{len(scenarios)} plots regenerated successfully")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
