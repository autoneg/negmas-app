"""Create mechanism instances."""

from negmas import Scenario
from negmas.sao import SAOMechanism
from negmas.gb import TAUMechanism, GBMechanism
from negmas.st import VetoSTMechanism, HillClimbingSTMechanism
from negmas.outcomes import OutcomeSpace
from negmas.mechanisms import Mechanism

from ..models import (
    MechanismType,
    MechanismConfig,
    DeadlineParams,
    SAOParams,
    TAUParams,
    GBParams,
    default_config,
)

# Map class names to mechanism classes
MECHANISM_CLASSES: dict[str, type] = {
    "SAOMechanism": SAOMechanism,
    "TAUMechanism": TAUMechanism,
    "GBMechanism": GBMechanism,
    "VetoSTMechanism": VetoSTMechanism,
    "HillClimbingSTMechanism": HillClimbingSTMechanism,
}


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
            avoid_ultimatum=params.avoid_ultimatum,
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
    def create_tau(
        outcome_space: OutcomeSpace,
        config: MechanismConfig,
    ) -> TAUMechanism:
        """Create a TAU mechanism.

        Args:
            outcome_space: The outcome space for the negotiation.
            config: Full mechanism configuration.

        Returns:
            Configured TAUMechanism instance.
        """
        deadline = config.deadline
        params = config.tau_params

        return TAUMechanism(
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
            # TAU-specific params
            accept_in_any_thread=params.accept_in_any_thread,
            parallel=params.parallel,
        )

    @staticmethod
    def create_gb(
        outcome_space: OutcomeSpace,
        config: MechanismConfig,
    ) -> GBMechanism:
        """Create a GB mechanism.

        Args:
            outcome_space: The outcome space for the negotiation.
            config: Full mechanism configuration.

        Returns:
            Configured GBMechanism instance.
        """
        deadline = config.deadline
        params = config.gb_params

        return GBMechanism(
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
            # GB-specific params
            parallel=params.parallel,
            end_on_no_response=params.end_on_no_response,
            check_offers=params.check_offers,
            enforce_issue_types=params.enforce_issue_types,
            cast_offers=params.cast_offers,
            sync_calls=params.sync_calls,
        )

    @staticmethod
    def create(
        outcome_space: OutcomeSpace,
        config: MechanismConfig | None = None,
    ) -> Mechanism:
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
            case MechanismType.TAU:
                return MechanismFactory.create_tau(outcome_space, config)
            case MechanismType.GB:
                return MechanismFactory.create_gb(outcome_space, config)
            case _:
                raise ValueError(
                    f"Mechanism type {config.mechanism_type} not yet supported"
                )

    @staticmethod
    def create_from_scenario(
        scenario: Scenario,  # type: ignore[name-defined]
        config: MechanismConfig | None = None,
    ) -> Mechanism:
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

    @staticmethod
    def create_from_params(
        outcome_space: OutcomeSpace,
        mechanism_type: str = "SAOMechanism",
        params: dict | None = None,
    ) -> Mechanism:
        """Create a mechanism from class name and params dict.

        This is the main entry point for dynamic mechanism creation from the UI.

        Args:
            outcome_space: The outcome space for the negotiation.
            mechanism_type: Class name of the mechanism (e.g. "SAOMechanism").
            params: Dictionary of parameters to pass to the mechanism constructor.

        Returns:
            Configured mechanism instance.

        Raises:
            ValueError: If mechanism type is not supported.
        """
        if mechanism_type not in MECHANISM_CLASSES:
            raise ValueError(f"Unknown mechanism type: {mechanism_type}")

        mech_class = MECHANISM_CLASSES[mechanism_type]
        params = params or {}

        # Filter params - remove None values and handle special values
        filtered_params = {}
        for key, value in params.items():
            if value is None:
                continue
            # Handle "inf" strings
            if value == "inf":
                value = float("inf")
            elif value == "-inf":
                value = float("-inf")
            filtered_params[key] = value

        # Always include outcome_space
        filtered_params["outcome_space"] = outcome_space

        return mech_class(**filtered_params)

    @staticmethod
    def create_from_scenario_params(
        scenario: Scenario,  # type: ignore[name-defined]
        mechanism_type: str = "SAOMechanism",
        params: dict | None = None,
    ) -> Mechanism:
        """Create a mechanism from scenario with class name and params.

        Args:
            scenario: Scenario with outcome space.
            mechanism_type: Class name of the mechanism.
            params: Dictionary of parameters.

        Returns:
            Configured mechanism instance.
        """
        return MechanismFactory.create_from_params(
            scenario.outcome_space, mechanism_type, params
        )
