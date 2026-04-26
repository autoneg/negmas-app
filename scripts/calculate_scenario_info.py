#!/usr/bin/env python3
"""Calculate missing scenario info (_info.yaml) for all app scenarios.

This script scans all scenarios in the scenarios/ directory and calculates
missing information like n_outcomes, opposition, and rational_fraction,
saving the results to _info.yaml files alongside each scenario.

Usage:
    python scripts/calculate_scenario_info.py [--force]

Options:
    --force: Recalculate even if _info.yaml already exists
"""

import argparse
from pathlib import Path
from typing import Any

from negmas import Scenario
from negmas.preferences.ops import is_rational, opposition_level


def calculate_and_save_scenario_info(
    scenario_path: Path, force: bool = False
) -> dict[str, Any] | None | bool:
    """Calculate scenario info and save using Scenario.save_info().

    Args:
        scenario_path: Path to scenario directory
        force: Recalculate even if _info.yaml exists

    Returns:
        Info dict if calculated successfully
        None if skipped (already exists and not force)
        False if error occurred
    """
    info_file = scenario_path / "_info.yaml"

    # Skip if _info.yaml exists and force is False
    if info_file.exists() and not force:
        return None

    try:
        # Load scenario (with existing info if available)
        scenario = Scenario.load(scenario_path, load_info=True)

        # Calculate n_outcomes
        outcomes = list(
            scenario.outcome_space.enumerate_or_sample(max_cardinality=50000)
        )
        n_outcomes = len(outcomes)

        # Calculate opposition using negmas opposition_level function
        opposition = 0.0
        if len(scenario.ufuns) >= 2 and n_outcomes > 0:
            opposition = float(
                opposition_level(scenario.ufuns, outcomes=outcomes, max_tests=50000)
            )

        # Calculate rational fraction
        rational_fraction = 0.0
        if n_outcomes > 0:
            n_rational = sum(1 for o in outcomes if is_rational(scenario.ufuns, o))
            rational_fraction = n_rational / n_outcomes

        # Update scenario.info dict (preserving existing info)
        if scenario.info is None:
            scenario.info = {}

        scenario.info["n_outcomes"] = n_outcomes
        scenario.info["opposition"] = opposition
        scenario.info["rational_fraction"] = rational_fraction

        # Add description if it doesn't exist
        if "description" not in scenario.info:
            # Try to infer a description from scenario name
            name = scenario_path.name
            category = scenario_path.parent.name
            scenario.info["description"] = (
                f"{name.replace('_', ' ').title()} scenario from {category}"
            )

        # Save using Scenario's save_info method (doesn't rewrite scenario files)
        scenario.save_info(scenario_path)

        return scenario.info

    except Exception as e:
        print(f"  ERROR: Failed to calculate info for {scenario_path.name}: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate missing scenario info for all app scenarios"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recalculate even if _info.yaml already exists",
    )
    args = parser.parse_args()

    # Find scenarios directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    scenarios_root = project_root / "scenarios"

    if not scenarios_root.exists():
        print(f"ERROR: Scenarios directory not found at {scenarios_root}")
        return 1

    print(f"Scanning scenarios in {scenarios_root}...")
    print(f"Force recalculation: {args.force}")
    print()

    # Find all scenario directories
    scenario_paths = []
    for category_dir in scenarios_root.iterdir():
        if category_dir.is_dir() and not category_dir.name.startswith("."):
            for scenario_dir in category_dir.iterdir():
                if scenario_dir.is_dir() and not scenario_dir.name.startswith("."):
                    scenario_paths.append(scenario_dir)

    print(f"Found {len(scenario_paths)} scenarios")
    print()

    # Process each scenario
    processed = 0
    skipped = 0
    errors = 0

    for i, scenario_path in enumerate(scenario_paths, 1):
        rel_path = scenario_path.relative_to(scenarios_root)
        print(f"[{i}/{len(scenario_paths)}] {rel_path}...")

        result = calculate_and_save_scenario_info(scenario_path, force=args.force)

        if result is None:
            print(f"  SKIPPED: _info.yaml already exists")
            skipped += 1
        elif result is False:
            # Error occurred
            errors += 1
        elif result:
            # Success - result is the info dict
            print(
                f"  SUCCESS: n_outcomes={result['n_outcomes']}, "
                f"opposition={result['opposition']:.3f}, "
                f"rational_fraction={result['rational_fraction']:.3f}"
            )
            processed += 1

    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Processed: {processed}")
    print(f"  Skipped:   {skipped}")
    print(f"  Errors:    {errors}")
    print("=" * 60)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    exit(main())
