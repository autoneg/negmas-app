#!/usr/bin/env python3
"""Fix -inf/inf/nan reserved values in scenario utility functions.

This script scans all scenarios and replaces invalid reserved values
(inf, -inf, nan) with the minimum utility value for each ufun.

For DiscountedUtilityFunction, it also processes the inner ufun.

Usage:
    python scripts/fix_reserved_values.py [--scenarios-dir PATH] [--dry-run] [--verbose]

Examples:
    # Dry run to see what would be changed
    python scripts/fix_reserved_values.py --dry-run --verbose

    # Fix all scenarios in default location
    python scripts/fix_reserved_values.py

    # Fix scenarios in custom location
    python scripts/fix_reserved_values.py --scenarios-dir /path/to/scenarios
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from negmas.preferences import BaseUtilityFunction

# Add parent to path for imports when run as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))


def is_invalid_reserved_value(value: float | None) -> bool:
    """Check if a reserved value is invalid (inf, -inf, nan, or None)."""
    if value is None:
        return True
    try:
        return math.isinf(value) or math.isnan(value)
    except (TypeError, ValueError):
        return True


def fix_ufun_reserved_value(
    ufun: BaseUtilityFunction,
    dry_run: bool = False,
    verbose: bool = False,
    prefix: str = "",
) -> bool:
    """Fix the reserved value of a ufun if it's invalid.

    Args:
        ufun: The utility function to fix.
        dry_run: If True, don't actually modify anything.
        verbose: If True, print details.
        prefix: Prefix for log messages (for indentation).

    Returns:
        True if the ufun was modified (or would be in dry run).
    """
    from negmas.preferences import DiscountedUtilityFunction

    modified = False
    ufun_type = type(ufun).__name__

    # Check and fix the main reserved value
    current_reserved = ufun.reserved_value
    if is_invalid_reserved_value(current_reserved):
        try:
            min_val = ufun.min()
            if min_val is not None and not is_invalid_reserved_value(min_val):
                if verbose:
                    print(
                        f"{prefix}{ufun_type}: reserved_value={current_reserved} -> {min_val}"
                    )
                if not dry_run:
                    ufun.reserved_value = min_val
                modified = True
            elif verbose:
                print(
                    f"{prefix}{ufun_type}: reserved_value={current_reserved}, min()={min_val} (cannot fix)"
                )
        except Exception as e:
            if verbose:
                print(f"{prefix}{ufun_type}: error getting min(): {e}")

    # Handle DiscountedUtilityFunction - process inner ufun
    if isinstance(ufun, DiscountedUtilityFunction):
        inner_ufun = getattr(ufun, "ufun", None)
        if inner_ufun is not None:
            inner_modified = fix_ufun_reserved_value(
                inner_ufun,
                dry_run=dry_run,
                verbose=verbose,
                prefix=prefix + "  [inner] ",
            )
            modified = modified or inner_modified

    return modified


def fix_scenario_reserved_values(
    scenario_path: Path,
    dry_run: bool = False,
    verbose: bool = False,
    save: bool = True,
) -> tuple[bool, int]:
    """Fix reserved values in a scenario.

    Args:
        scenario_path: Path to the scenario directory.
        dry_run: If True, don't actually save changes.
        verbose: If True, print details.
        save: If True, save the scenario after modification (ignored if dry_run=True).

    Returns:
        Tuple of (any_modified, num_ufuns_fixed).
    """
    from negmas import Scenario

    try:
        scenario = Scenario.load(scenario_path, load_info=False, load_stats=False)
        if scenario is None:
            if verbose:
                print(f"  Could not load scenario from {scenario_path}")
            return False, 0
    except Exception as e:
        if verbose:
            print(f"  Error loading scenario {scenario_path}: {e}")
        return False, 0

    any_modified = False
    num_fixed = 0

    for i, ufun in enumerate(scenario.ufuns):
        modified = fix_ufun_reserved_value(
            ufun,
            dry_run=dry_run,
            verbose=verbose,
            prefix=f"  ufun[{i}] ",
        )
        if modified:
            any_modified = True
            num_fixed += 1

    # Save the scenario if modified
    if any_modified and not dry_run and save:
        try:
            scenario.dumpas(scenario_path, save_info=False, save_stats=False)
            if verbose:
                print(f"  Saved scenario to {scenario_path}")
        except Exception as e:
            print(f"  Error saving scenario {scenario_path}: {e}")
            return False, 0

    return any_modified, num_fixed


def ensure_finite_reserved_values_for_scenario(scenario) -> int:
    """Fix reserved values in a loaded scenario object (in-place).

    This is the function used by ScenarioCacheService during cache building.
    It modifies the scenario's ufuns in-place without saving.

    Args:
        scenario: A loaded negmas.Scenario object.

    Returns:
        Number of ufuns that were fixed.
    """
    num_fixed = 0

    for ufun in scenario.ufuns:
        modified = fix_ufun_reserved_value(
            ufun,
            dry_run=False,
            verbose=False,
            prefix="",
        )
        if modified:
            num_fixed += 1

    return num_fixed


def fix_all_scenarios(
    scenarios_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[int, int, int]:
    """Fix reserved values in all scenarios.

    Args:
        scenarios_dir: Root directory containing scenarios.
        dry_run: If True, don't actually save changes.
        verbose: If True, print details.

    Returns:
        Tuple of (scenarios_scanned, scenarios_modified, ufuns_fixed).
    """
    scenarios_scanned = 0
    scenarios_modified = 0
    total_ufuns_fixed = 0

    if not scenarios_dir.exists():
        print(f"Scenarios directory does not exist: {scenarios_dir}")
        return 0, 0, 0

    # Find all potential scenario directories
    # Scenarios are typically organized as: scenarios_dir/collection/scenario_name/
    scenario_paths = []
    for collection_dir in scenarios_dir.iterdir():
        if not collection_dir.is_dir():
            continue
        for scenario_dir in collection_dir.iterdir():
            if scenario_dir.is_dir():
                scenario_paths.append(scenario_dir)

    print(f"Found {len(scenario_paths)} potential scenario directories")

    for scenario_path in scenario_paths:
        scenarios_scanned += 1

        if verbose:
            print(f"\nProcessing: {scenario_path.relative_to(scenarios_dir)}")

        modified, num_fixed = fix_scenario_reserved_values(
            scenario_path, dry_run=dry_run, verbose=verbose
        )

        if modified:
            scenarios_modified += 1
            total_ufuns_fixed += num_fixed
            if not verbose:
                print(
                    f"  Fixed {num_fixed} ufuns in {scenario_path.relative_to(scenarios_dir)}"
                )

    return scenarios_scanned, scenarios_modified, total_ufuns_fixed


def main():
    parser = argparse.ArgumentParser(
        description="Fix -inf/inf/nan reserved values in scenario utility functions."
    )
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=Path.home() / "negmas" / "app" / "scenarios",
        help="Path to scenarios directory (default: ~/negmas/app/scenarios)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually modify files, just show what would be changed",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed information about each scenario",
    )

    args = parser.parse_args()

    print(f"Scenarios directory: {args.scenarios_dir}")
    if args.dry_run:
        print("DRY RUN - no files will be modified")
    print()

    scanned, modified, fixed = fix_all_scenarios(
        args.scenarios_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    print()
    print("=" * 50)
    print(f"Scenarios scanned: {scanned}")
    print(f"Scenarios modified: {modified}")
    print(f"Ufuns fixed: {fixed}")

    if args.dry_run and modified > 0:
        print()
        print("Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
