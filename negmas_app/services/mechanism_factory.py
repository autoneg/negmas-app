"""Create mechanism instances."""

from negmas import Scenario
from negmas.sao import SAOMechanism
from negmas.outcomes import OutcomeSpace

from ..models import (
    MechanismType,
    MechanismConfig,
    DeadlineParams,
    SAOParams,
    default_config,
)


class MechanismFactory:
    """Create mechanism instances from configuration."""

    @staticmethod
    def create_sao(
        outcome_space: OutcomeSpace,
        config: MechanismConfig,
    ) -> SAOMechanism:
        """Create an SAO mechanism.

        Args:
            outcome_space: The outcome space for the negotiation.
            config: Full mechanism configuration.

        Returns:
            Configured SAOMechanism instance.
        """
        deadline = config.deadline
        params = config.sao_params

        return SAOMechanism(
            outcome_space=outcome_space,
            # Deadline params
            n_steps=deadline.n_steps,
            time_limit=deadline.time_limit,
            pend=deadline.pend,
            pend_per_second=deadline.pend_per_second,
            step_time_limit=deadline.step_time_limit,
            negotiator_time_limit=deadline.negotiator_time_limit,
            hidden_time_limit=deadline.hidden_time_limit,
            # Base params
            max_n_negotiators=params.max_n_negotiators,
            dynamic_entry=params.dynamic_entry,
            verbosity=params.verbosity,
            ignore_negotiator_exceptions=params.ignore_negotiator_exceptions,
            name=params.name,
            # SAO-specific params
            end_on_no_response=params.end_on_no_response,
            check_offers=params.check_offers,
            enforce_issue_types=params.enforce_issue_types,
            cast_offers=params.cast_offers,
            offering_is_accepting=params.offering_is_accepting,
            allow_offering_just_rejected_outcome=params.allow_offering_just_rejected_outcome,
            one_offer_per_step=params.one_offer_per_step,
            sync_calls=params.sync_calls,
            max_wait=params.max_wait,
        )

    @staticmethod
    def create(
        outcome_space: OutcomeSpace,
        config: MechanismConfig | None = None,
    ) -> SAOMechanism:
        """Create a mechanism from configuration.

        Args:
            outcome_space: The outcome space for the negotiation.
            config: Mechanism configuration. Uses defaults if None.

        Returns:
            Configured mechanism instance.

        Raises:
            ValueError: If mechanism type is not supported.
        """
        if config is None:
            config = default_config()

        match config.mechanism_type:
            case MechanismType.SAO:
                return MechanismFactory.create_sao(outcome_space, config)
            case _:
                raise ValueError(
                    f"Mechanism type {config.mechanism_type} not yet supported"
                )

    @staticmethod
    def create_from_scenario(
        scenario: Scenario,  # type: ignore[name-defined]
        config: MechanismConfig | None = None,
    ) -> SAOMechanism:
        """Create a mechanism from a scenario.

        Args:
            scenario: Scenario with outcome space.
            config: Mechanism configuration. Uses defaults if None.

        Returns:
            Configured mechanism instance.
        """
        return MechanismFactory.create(scenario.outcome_space, config)

    @staticmethod
    def create_simple(
        outcome_space: OutcomeSpace,
        n_steps: int = 100,
        time_limit: float | None = None,
    ) -> SAOMechanism:
        """Create a simple SAO mechanism with minimal config.

        Convenience method for quick mechanism creation.

        Args:
            outcome_space: The outcome space for the negotiation.
            n_steps: Maximum number of steps.
            time_limit: Optional time limit in seconds.

        Returns:
            Configured SAOMechanism instance.
        """
        config = MechanismConfig(
            mechanism_type=MechanismType.SAO,
            deadline=DeadlineParams(n_steps=n_steps, time_limit=time_limit),
        )
        return MechanismFactory.create_sao(outcome_space, config)
