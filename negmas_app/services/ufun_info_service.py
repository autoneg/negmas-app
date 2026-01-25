"""Service for extracting utility function information using negmas structures."""

from pathlib import Path
from typing import Any

from negmas.inout import (
    find_domain_and_utility_files_geniusweb,
    find_domain_and_utility_files_xml,
    find_domain_and_utility_files_yaml,
)


def get_ufun_info(ufun, scenario_path: Path) -> dict[str, Any]:
    """Extract detailed information about a utility function using negmas structures.

    Args:
        ufun: The utility function (negmas BaseUtilityFunction)
        scenario_path: Path to the scenario directory or file

    Returns:
        Dictionary with ufun type, parameters, and file information
    """
    ufun_name = getattr(ufun, "name", "Unknown")

    # Use negmas' __str__ or __repr__ for parameters - it already formats them nicely
    ufun_str = str(ufun)

    info = {
        "name": ufun_name,
        "type": type(ufun).__name__.upper(),
        "string_representation": ufun_str,
        "file_path": None,
    }

    # Get file path if scenario is folder-based
    if scenario_path.is_dir():
        info["file_path"] = _find_ufun_file(ufun_name, scenario_path)

    return info


def _find_ufun_file(ufun_name: str, scenario_path: Path) -> str | None:
    """Find the utility file for a given ufun name.

    Args:
        ufun_name: Name of the utility function
        scenario_path: Path to scenario directory

    Returns:
        Relative path to the utility file, or None if not found
    """
    # Try YAML format
    _, ufun_files = find_domain_and_utility_files_yaml(scenario_path)
    if ufun_files:
        for ufun_file in ufun_files:
            # Match by filename (usually profileA.yaml, profileB.yaml, etc.)
            if ufun_file.stem == ufun_name or ufun_name in ufun_file.stem:
                return str(ufun_file.relative_to(scenario_path))

    # Try XML format
    _, ufun_files = find_domain_and_utility_files_xml(scenario_path)
    if ufun_files:
        for ufun_file in ufun_files:
            if ufun_file.stem == ufun_name or ufun_name in ufun_file.stem:
                return str(ufun_file.relative_to(scenario_path))

    # Try GeniusWeb format
    _, ufun_files = find_domain_and_utility_files_geniusweb(scenario_path)
    if ufun_files:
        for ufun_file in ufun_files:
            if ufun_file.stem == ufun_name or ufun_name in ufun_file.stem:
                return str(ufun_file.relative_to(scenario_path))

    return None


def get_scenario_files(scenario_path: Path) -> dict[str, Any]:
    """Get all relevant files for a scenario using negmas file detection.

    Args:
        scenario_path: Path to scenario directory or file

    Returns:
        Dictionary with domain file, utility files, and scenario file paths
    """
    result = {
        "domain_file": None,
        "utility_files": [],
        "scenario_file": None,
        "is_folder": scenario_path.is_dir(),
    }

    if scenario_path.is_file():
        # Single-file scenario
        result["scenario_file"] = str(scenario_path)
        return result

    # Folder-based scenario - use negmas' file detection functions
    # Try YAML
    domain_path, ufun_files = find_domain_and_utility_files_yaml(scenario_path)
    if domain_path:
        result["domain_file"] = str(domain_path.relative_to(scenario_path))
        result["utility_files"] = [
            str(f.relative_to(scenario_path)) for f in ufun_files
        ]
        return result

    # Try XML
    domain_path, ufun_files = find_domain_and_utility_files_xml(scenario_path)
    if domain_path:
        result["domain_file"] = str(domain_path.relative_to(scenario_path))
        result["utility_files"] = [
            str(f.relative_to(scenario_path)) for f in ufun_files
        ]
        return result

    # Try GeniusWeb
    domain_path, ufun_files = find_domain_and_utility_files_geniusweb(scenario_path)
    if domain_path:
        result["domain_file"] = str(domain_path.relative_to(scenario_path))
        result["utility_files"] = [
            str(f.relative_to(scenario_path)) for f in ufun_files
        ]
        return result

    return result
