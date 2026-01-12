"""Outcome space analysis service - compute Pareto frontier and special points."""

import random
from collections.abc import Sequence

from negmas import (
    Scenario,
    pareto_frontier,
    nash_points,
    kalai_points,
    max_welfare_points,
)
from negmas.outcomes import Outcome
from negmas.preferences import UtilityFunction

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
) -> OutcomeSpaceData:
    """Compute full outcome space analysis data.

    Args:
        scenario: Loaded scenario with ufuns and outcome_space.
        max_samples: Maximum outcomes to sample for display.

    Returns:
        OutcomeSpaceData with all computed values.
    """
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

    # Compute special points using the Pareto frontier
    data = OutcomeSpaceData(
        outcome_utilities=outcome_utilities,
        pareto_utilities=pareto_utilities,
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
