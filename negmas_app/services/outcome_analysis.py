"""Outcome space analysis service - compute Pareto frontier and special points."""

import random
from collections.abc import Sequence

from negmas import (
    Scenario,
    pareto_frontier,
    nash_points,
    kalai_points,
    ks_points,
    max_welfare_points,
)
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction
from negmas.preferences.ops import (
    OutcomeOptimality,
    calc_outcome_optimality,
    calc_outcome_distances,
    calc_scenario_stats,
    estimate_max_dist,
)

from ..models import AnalysisPoint, OutcomeSpaceData


def compute_outcome_utilities(
    ufuns: Sequence[UtilityFunction],
    outcomes: Sequence[Outcome],
    max_samples: int = 50000,
) -> tuple[list[tuple[float, ...]], bool, int]:
    """Compute utility values for all outcomes, sampling if needed.

    Args:
        ufuns: Utility functions for each negotiator.
        outcomes: List of all possible outcomes.
        max_samples: Maximum number of outcomes to compute (sample if more).

    Returns:
        Tuple of (utility_tuples, was_sampled, sample_size).
    """
    total = len(outcomes)
    sampled = False
    sample_size = total

    if total > max_samples:
        # Random sample
        sampled = True
        sample_size = max_samples
        outcomes = random.sample(list(outcomes), max_samples)

    utilities = []
    for outcome in outcomes:
        utils = tuple(
            float(ufun(outcome)) if ufun(outcome) is not None else 0.0 for ufun in ufuns
        )
        utilities.append(utils)

    return utilities, sampled, sample_size


def compute_outcome_space_data(
    scenario: Scenario,
    max_samples: int = 50000,
    use_cached_stats: bool = True,
) -> OutcomeSpaceData:
    """Compute full outcome space analysis data.

    Args:
        scenario: Loaded scenario with ufuns and outcome_space.
        max_samples: Maximum outcomes to sample for display.
        use_cached_stats: If True and scenario.stats exists, use cached values.

    Returns:
        OutcomeSpaceData with all computed values.
    """
    # Use cached stats if available
    if use_cached_stats and scenario.stats is not None:
        return _from_cached_stats(scenario, max_samples)

    # Otherwise compute from scratch
    return _compute_from_scratch(scenario, max_samples)


def _from_cached_stats(scenario: Scenario, max_samples: int) -> OutcomeSpaceData:
    """Build OutcomeSpaceData from cached scenario.stats."""
    stats = scenario.stats
    ufuns = scenario.ufuns
    outcome_space = scenario.outcome_space

    # Still need to compute outcome utilities for the scatter plot
    outcomes = list(outcome_space.enumerate_or_sample(max_cardinality=max_samples * 2))
    total_outcomes = outcome_space.cardinality

    outcome_utilities, sampled, sample_size = compute_outcome_utilities(
        ufuns, outcomes, max_samples
    )

    # Convert cached Pareto utilities
    pareto_utilities = []
    if stats.pareto_utils:
        for utils in stats.pareto_utils:
            pareto_utilities.append(tuple(float(u) for u in utils))

    # Extract reserved values
    reserved_values = []
    for ufun in ufuns:
        rv = getattr(ufun, "reserved_value", None)
        reserved_values.append(float(rv) if rv is not None else 0.0)

    data = OutcomeSpaceData(
        outcome_utilities=outcome_utilities,
        pareto_utilities=pareto_utilities,
        reserved_values=reserved_values,
        total_outcomes=total_outcomes if isinstance(total_outcomes, int) else 0,
        sampled=sampled,
        sample_size=sample_size,
    )

    # Map cached special points
    if stats.nash_utils and len(stats.nash_utils) > 0:
        data.nash_point = AnalysisPoint(
            name="nash",
            utilities=[float(u) for u in stats.nash_utils[0]],
        )

    if stats.kalai_utils and len(stats.kalai_utils) > 0:
        data.kalai_point = AnalysisPoint(
            name="kalai",
            utilities=[float(u) for u in stats.kalai_utils[0]],
        )

    if stats.ks_utils and len(stats.ks_utils) > 0:
        data.kalai_smorodinsky_point = AnalysisPoint(
            name="kalai_smorodinsky",
            utilities=[float(u) for u in stats.ks_utils[0]],
        )

    if stats.max_welfare_utils and len(stats.max_welfare_utils) > 0:
        data.max_welfare_point = AnalysisPoint(
            name="max_welfare",
            utilities=[float(u) for u in stats.max_welfare_utils[0]],
        )

    return data


def _compute_from_scratch(scenario: Scenario, max_samples: int) -> OutcomeSpaceData:
    """Compute outcome space data from scratch (no cache)."""
    ufuns = scenario.ufuns
    outcome_space = scenario.outcome_space
    outcomes = list(outcome_space.enumerate_or_sample(max_cardinality=max_samples * 2))
    total_outcomes = outcome_space.cardinality

    # Compute utilities for all outcomes
    outcome_utilities, sampled, sample_size = compute_outcome_utilities(
        ufuns, outcomes, max_samples
    )

    # Compute Pareto frontier
    try:
        pareto_utils, pareto_indices = pareto_frontier(
            ufuns,
            outcomes=outcomes,
            max_cardinality=max_samples,
            sort_by_welfare=True,
        )
        pareto_utilities = list(pareto_utils)
    except Exception:
        pareto_utilities = []

    # Extract reserved values
    reserved_values = []
    for ufun in ufuns:
        rv = getattr(ufun, "reserved_value", None)
        reserved_values.append(float(rv) if rv is not None else 0.0)

    # Compute special points using the Pareto frontier
    data = OutcomeSpaceData(
        outcome_utilities=outcome_utilities,
        pareto_utilities=pareto_utilities,
        reserved_values=reserved_values,
        total_outcomes=total_outcomes if isinstance(total_outcomes, int) else 0,
        sampled=sampled,
        sample_size=sample_size,
    )

    if not pareto_utilities:
        return data

    # Nash point(s) - product of utilities
    try:
        nash_results = nash_points(
            ufuns,
            frontier=pareto_utilities,
            outcome_space=outcome_space,
        )
        if nash_results:
            nash_utils, nash_idx = nash_results[0]
            data.nash_point = AnalysisPoint(
                name="nash",
                utilities=list(nash_utils),
            )
    except Exception:
        pass

    # Kalai point(s) - egalitarian, minimize max regret
    try:
        kalai_results = kalai_points(
            ufuns,
            frontier=pareto_utilities,
            outcome_space=outcome_space,
        )
        if kalai_results:
            kalai_utils, kalai_idx = kalai_results[0]
            data.kalai_point = AnalysisPoint(
                name="kalai",
                utilities=list(kalai_utils),
            )
    except Exception:
        pass

    # Kalai-Smorodinsky point(s) - proportional fairness
    try:
        ks_results = ks_points(
            ufuns,
            frontier=pareto_utilities,
            outcome_space=outcome_space,
        )
        if ks_results:
            ks_utils, ks_idx = ks_results[0]
            data.kalai_smorodinsky_point = AnalysisPoint(
                name="kalai_smorodinsky",
                utilities=list(ks_utils),
            )
    except Exception:
        pass

    # Max welfare point(s) - sum of utilities
    try:
        welfare_results = max_welfare_points(
            ufuns,
            frontier=pareto_utilities,
            outcome_space=outcome_space,
        )
        if welfare_results:
            welfare_utils, welfare_idx = welfare_results[0]
            data.max_welfare_point = AnalysisPoint(
                name="max_welfare",
                utilities=list(welfare_utils),
            )
    except Exception:
        pass

    return data


def compute_optimality_stats(
    scenario: Scenario,
    agreement: Outcome,
    max_samples: int = 50000,
) -> dict | None:
    """Compute OutcomeOptimality for an agreement.

    Args:
        scenario: Loaded scenario with ufuns and outcome_space.
        agreement: The agreed-upon outcome.
        max_samples: Maximum outcomes to consider for stats computation.

    Returns:
        Dictionary with optimality statistics, or None if computation fails.
    """
    if agreement is None:
        return None

    try:
        ufuns = scenario.ufuns
        outcome_space = scenario.outcome_space

        # Get agreement utilities
        agreement_utils = tuple(
            float(ufun(agreement)) if ufun(agreement) is not None else 0.0
            for ufun in ufuns
        )

        # Use cached stats if available, otherwise compute
        if scenario.stats is not None:
            stats = scenario.stats
        else:
            # Compute scenario stats from scratch
            outcomes = list(
                outcome_space.enumerate_or_sample(max_cardinality=max_samples)
            )
            stats = calc_scenario_stats(ufuns, outcomes)

        # Calculate distances from agreement to special points
        dists = calc_outcome_distances(agreement_utils, stats)

        # Estimate max distance for normalization
        max_dist = estimate_max_dist(ufuns)

        # Calculate optimality
        optimality: OutcomeOptimality = calc_outcome_optimality(dists, stats, max_dist)

        # Convert to dictionary
        return {
            "pareto_optimality": float(optimality.pareto_optimality),
            "nash_optimality": float(optimality.nash_optimality),
            "kalai_optimality": float(optimality.kalai_optimality),
            "modified_kalai_optimality": float(optimality.modified_kalai_optimality),
            "max_welfare_optimality": float(optimality.max_welfare_optimality),
            "ks_optimality": float(optimality.ks_optimality)
            if not (optimality.ks_optimality != optimality.ks_optimality)
            else None,  # NaN check
            "modified_ks_optimality": float(optimality.modified_ks_optimality)
            if not (
                optimality.modified_ks_optimality != optimality.modified_ks_optimality
            )
            else None,  # NaN check
        }
    except Exception as e:
        print(f"Failed to compute optimality stats: {e}")
        return None
