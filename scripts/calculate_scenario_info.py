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
import yaml
from typing import Any

from negmas import Scenario
from negmas.preferences.ops import is_rational, opposition_level


def calculate_scenario_info(
    scenario_path: Path, force: bool = False
) -> dict[str, Any] | None:
    """Calculate scenario info and return as dict.

    Args:
        scenario_path: Path to scenario directory
        force: Recalculate even if _info.yaml exists

    Returns:
        Info dict if calculated, None if skipped
    """
    info_file = scenario_path / "_info.yaml"

    # Skip if _info.yaml exists and force is False
    if info_file.exists() and not force:
        return None

    try:
        # Load scenario
        scenario = Scenario.load(scenario_path)

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

        # Build info dict
        info = {
            "n_outcomes": n_outcomes,
            "opposition": opposition,
            "rational_fraction": rational_fraction,
        }

        # Add description if it doesn't exist
        if not info_file.exists():
            # Try to infer a description from scenario name
            name = scenario_path.name
            category = scenario_path.parent.name
            info["description"] = (
                f"{name.replace('_', ' ').title()} scenario from {category}"
            )

        return info

    except Exception as e:
        print(f"  ERROR: Failed to calculate info for {scenario_path.name}: {e}")
        return None


def save_scenario_info(scenario_path: Path, info: dict[str, Any]) -> None:
    """Save info dict to _info.yaml file.

    Args:
        scenario_path: Path to scenario directory
        info: Info dictionary to save
    """
    info_file = scenario_path / "_info.yaml"

    # If file exists, load it and merge with new info
    if info_file.exists():
        try:
            with open(info_file, "r") as f:
                existing_info = yaml.safe_load(f) or {}
        except Exception:
            existing_info = {}

        # Merge: new info takes precedence
        merged_info = {**existing_info, **info}
    else:
        merged_info = info

    # Save to file
    with open(info_file, "w") as f:
        yaml.dump(merged_info, f, default_flow_style=False, sort_keys=False)


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

        info = calculate_scenario_info(scenario_path, force=args.force)

        if info is None:
            print(f"  SKIPPED: _info.yaml already exists")
            skipped += 1
        elif info:
            save_scenario_info(scenario_path, info)
            print(
                f"  SUCCESS: n_outcomes={info['n_outcomes']}, "
                f"opposition={info['opposition']:.3f}, "
                f"rational_fraction={info['rational_fraction']:.3f}"
            )
            processed += 1
        else:
            errors += 1

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
