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
    ufun_type = type(ufun).__name__

    # Extract detailed representation based on ufun type
    string_representation = _get_detailed_representation(ufun)

    info = {
        "name": ufun_name,
        "type": ufun_type,
        "string_representation": string_representation,
        "file_path": None,
    }

    # Get file path if scenario is folder-based
    if scenario_path.is_dir():
        info["file_path"] = _find_ufun_file(ufun_name, scenario_path)

    return info


def _get_detailed_representation(ufun) -> str:
    """Generate a detailed string representation of a utility function.

    Args:
        ufun: The utility function

    Returns:
        Detailed string representation showing weights, values, etc.
    """
    ufun_type = type(ufun).__name__
    parts = [f"Type: {ufun_type}"]

    # Extract reserved value if available
    if hasattr(ufun, "reserved_value") and ufun.reserved_value is not None:
        try:
            rv = float(ufun.reserved_value)
            parts.append(f"Reserved: {rv:.3f}")
        except (ValueError, TypeError):
            parts.append(f"Reserved: {ufun.reserved_value}")

    # Handle LinearAdditiveUtilityFunction and its variants
    if "LinearAdditive" in ufun_type or "LinearUtilityFunction" in ufun_type:
        if hasattr(ufun, "weights") and ufun.weights:
            try:
                weights_str = ", ".join(f"{float(w):.3f}" for w in ufun.weights)
                parts.append(f"Weights: [{weights_str}]")
            except (ValueError, TypeError):
                parts.append(f"Weights: {ufun.weights}")
        if hasattr(ufun, "bias") and ufun.bias is not None:
            try:
                parts.append(f"Bias: {float(ufun.bias):.3f}")
            except (ValueError, TypeError):
                parts.append(f"Bias: {ufun.bias}")

    # Handle discounted utility functions
    if "Discount" in ufun_type:
        if hasattr(ufun, "ufun") and ufun.ufun is not None:
            # Recursive call for the base ufun
            base_repr = _get_detailed_representation(ufun.ufun)
            parts.append(f"Base: ({base_repr})")
        if hasattr(ufun, "factor"):
            try:
                parts.append(f"Discount: {float(ufun.factor):.3f}")
            except (ValueError, TypeError):
                parts.append(f"Discount: {ufun.factor}")
        if hasattr(ufun, "power"):
            try:
                power = float(ufun.power)
                if power != 1.0:
                    parts.append(f"Power: {power:.3f}")
            except (ValueError, TypeError):
                pass

    # Handle hypervolume utility functions
    if "Hypervolume" in ufun_type or "HyperRectangle" in ufun_type:
        if hasattr(ufun, "outcome_ranges"):
            parts.append(f"Ranges: {len(ufun.outcome_ranges)} issues")

    # Handle nonlinear utility functions
    if hasattr(ufun, "values") and hasattr(ufun.values, "__len__"):
        # This is likely a nonlinear ufun with value functions per issue
        parts.append(f"Values: {len(ufun.values)} issues")

    # If no specific details were extracted, fall back to str()
    if len(parts) == 1:
        return str(ufun)

    return " | ".join(parts)


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
            # Convert to Path if it's a string
            ufun_file_path = (
                Path(ufun_file) if isinstance(ufun_file, str) else ufun_file
            )
            # Match by filename (usually profileA.yaml, profileB.yaml, etc.)
            if ufun_file_path.stem == ufun_name or ufun_name in ufun_file_path.stem:
                return str(ufun_file_path.relative_to(scenario_path))

    # Try XML format
    _, ufun_files = find_domain_and_utility_files_xml(scenario_path)
    if ufun_files:
        for ufun_file in ufun_files:
            ufun_file_path = (
                Path(ufun_file) if isinstance(ufun_file, str) else ufun_file
            )
            if ufun_file_path.stem == ufun_name or ufun_name in ufun_file_path.stem:
                return str(ufun_file_path.relative_to(scenario_path))

    # Try GeniusWeb format
    _, ufun_files = find_domain_and_utility_files_geniusweb(scenario_path)
    if ufun_files:
        for ufun_file in ufun_files:
            ufun_file_path = (
                Path(ufun_file) if isinstance(ufun_file, str) else ufun_file
            )
            if ufun_file_path.stem == ufun_name or ufun_name in ufun_file_path.stem:
                return str(ufun_file_path.relative_to(scenario_path))

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
        domain_path = Path(domain_path) if isinstance(domain_path, str) else domain_path
        result["domain_file"] = str(domain_path.relative_to(scenario_path))
        result["utility_files"] = [
            str((Path(f) if isinstance(f, str) else f).relative_to(scenario_path))
            for f in ufun_files
        ]
        return result

    # Try XML
    domain_path, ufun_files = find_domain_and_utility_files_xml(scenario_path)
    if domain_path:
        domain_path = Path(domain_path) if isinstance(domain_path, str) else domain_path
        result["domain_file"] = str(domain_path.relative_to(scenario_path))
        result["utility_files"] = [
            str((Path(f) if isinstance(f, str) else f).relative_to(scenario_path))
            for f in ufun_files
        ]
        return result

    # Try GeniusWeb
    domain_path, ufun_files = find_domain_and_utility_files_geniusweb(scenario_path)
    if domain_path:
        domain_path = Path(domain_path) if isinstance(domain_path, str) else domain_path
        result["domain_file"] = str(domain_path.relative_to(scenario_path))
        result["utility_files"] = [
            str((Path(f) if isinstance(f, str) else f).relative_to(scenario_path))
            for f in ufun_files
        ]
        return result

    return result
