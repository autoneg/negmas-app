"""Manage negotiation sessions with real-time streaming."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

from negmas import Scenario
from negmas.sao import SAOMechanism, SAOState

from ..models import (
    NegotiationSession,
    SessionStatus,
    OfferEvent,
    SessionInitEvent,
    SessionNegotiatorInfo,
    NEGOTIATOR_COLORS,
    NegotiatorConfig,
)
from .scenario_loader import ScenarioLoader
from .negotiator_factory import NegotiatorFactory
from .mechanism_factory import MechanismFactory
from .outcome_analysis import compute_outcome_space_data, compute_optimality_stats
from .negotiation_storage import NegotiationStorageService


class SessionManager:
    """Manage negotiation sessions."""

    def __init__(self):
        self.sessions: dict[str, NegotiationSession] = {}
        self._configs: dict[str, list[NegotiatorConfig]] = {}
        self._mechanism_params: dict[str, dict] = {}
        self._mechanism_types: dict[str, str] = {}
        self._scenario_options: dict[
            str, dict
        ] = {}  # ignore_discount, ignore_reserved, normalize
        self._auto_save: dict[str, bool] = {}  # Whether to auto-save on completion
        self._cancel_flags: dict[str, bool] = {}
        self._pause_flags: dict[str, bool] = {}
        self.scenario_loader = ScenarioLoader()

    def create_session(
        self,
        scenario_path: str,
        negotiator_configs: list[NegotiatorConfig],
        mechanism_type: str = "SAOMechanism",
        mechanism_params: dict | None = None,
        ignore_discount: bool = False,
        ignore_reserved: bool = False,
        normalize: bool = False,
        auto_save: bool = True,
    ) -> NegotiationSession:
        """Create a new negotiation session.

        Args:
            scenario_path: Path to scenario directory.
            negotiator_configs: Configurations for each negotiator.
            mechanism_type: Class name of mechanism (e.g. "SAOMechanism").
            mechanism_params: Dictionary of mechanism parameters.
            ignore_discount: If True, ignore discount factors in utility functions.
            ignore_reserved: If True, ignore reserved values in utility functions.
            normalize: If True, normalize utility functions to [0, 1] range.
            auto_save: If True, save negotiation to disk on completion.

        Returns:
            Created session (not yet started).
        """
        session_id = str(uuid.uuid4())[:8]
        params = mechanism_params or {}
        session = NegotiationSession(
            id=session_id,
            scenario_path=scenario_path,
            mechanism_type=mechanism_type,
            negotiator_names=[c.name or c.type_name for c in negotiator_configs],
            n_steps=params.get("n_steps"),
            time_limit=params.get("time_limit"),
        )
        self.sessions[session_id] = session
        self._configs[session_id] = negotiator_configs
        self._mechanism_params[session_id] = params
        self._mechanism_types[session_id] = mechanism_type
        self._scenario_options[session_id] = {
            "ignore_discount": ignore_discount,
            "ignore_reserved": ignore_reserved,
            "normalize": normalize,
        }
        self._auto_save[session_id] = auto_save
        self._cancel_flags[session_id] = False
        self._pause_flags[session_id] = False
        return session

    def get_session(self, session_id: str) -> NegotiationSession | None:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def get_configs(self, session_id: str) -> list[NegotiatorConfig] | None:
        """Get negotiator configs for a session."""
        return self._configs.get(session_id)

    def cancel_session(self, session_id: str) -> bool:
        """Request cancellation of a running session."""
        if session_id in self._cancel_flags:
            self._cancel_flags[session_id] = True
            return True
        return False

    def pause_session(self, session_id: str) -> bool:
        """Pause a running session."""
        if session_id in self._pause_flags:
            self._pause_flags[session_id] = True
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        if session_id in self._pause_flags:
            self._pause_flags[session_id] = False
            return True
        return False

    def is_paused(self, session_id: str) -> bool:
        """Check if a session is paused."""
        return self._pause_flags.get(session_id, False)

    async def run_session_stream(
        self,
        session_id: str,
        negotiator_configs: list[NegotiatorConfig],
        step_delay: float = 0.1,
        max_outcome_samples: int = 10000,
        share_ufuns: bool = False,
    ) -> AsyncGenerator[SessionInitEvent | OfferEvent | NegotiationSession, None]:
        """Run a negotiation session with real-time streaming.

        Args:
            session_id: Session ID to run.
            negotiator_configs: Negotiator configurations.
            step_delay: Delay between steps for visualization.
            max_outcome_samples: Max outcomes to sample for outcome space analysis.
            share_ufuns: If True, share utility functions between negotiators.

        Yields:
            SessionInitEvent at start, OfferEvent for each offer, then final NegotiationSession.
        """
        session = self.sessions.get(session_id)
        if session is None:
            return

        try:
            # Get scenario loading options
            scenario_options = self._scenario_options.get(session_id, {})
            ignore_discount = scenario_options.get("ignore_discount", False)
            ignore_reserved = scenario_options.get("ignore_reserved", False)

            # Load scenario with options (run in thread pool to avoid blocking)
            scenario = await asyncio.to_thread(
                self.scenario_loader.load_scenario,
                session.scenario_path,
                ignore_discount,
            )
            if scenario is None:
                session.status = SessionStatus.FAILED
                session.error = "Failed to load scenario"
                yield session
                return

            # Apply ignore_reserved if requested
            if ignore_reserved:
                for ufun in scenario.ufuns:
                    if hasattr(ufun, "reserved_value"):
                        ufun.reserved_value = float("-inf")

            # Apply normalization if requested
            normalize = scenario_options.get("normalize", False)
            if normalize:
                scenario.normalize()

            # Get mechanism type and params stored during create_session
            mechanism_type = self._mechanism_types.get(session_id, "SAOMechanism")
            mechanism_params = self._mechanism_params.get(session_id, {}).copy()

            # Ensure one_offer_per_step for better visualization (for SAO)
            if (
                mechanism_type == "SAOMechanism"
                and "one_offer_per_step" not in mechanism_params
            ):
                mechanism_params["one_offer_per_step"] = True

            # Create mechanism using the new factory method (run in thread pool)
            mechanism = await asyncio.to_thread(
                MechanismFactory.create_from_scenario_params,
                scenario,
                mechanism_type,
                mechanism_params,
            )

            # Create negotiators and add to mechanism with ufuns (run in thread pool)
            negotiators = await asyncio.to_thread(
                NegotiatorFactory.create_for_scenario,
                negotiator_configs,
                scenario,
            )
            for neg, ufun in zip(negotiators, scenario.ufuns):
                await asyncio.to_thread(mechanism.add, neg, ufun=ufun)

            # Share utility functions if requested
            # For 2-party: each negotiator gets opponent's ufun
            # For N-party: each negotiator gets list of all other ufuns
            if share_ufuns:
                n_negs = len(negotiators)
                if n_negs == 2:
                    # Simple 2-party case
                    negotiators[0].private_info["opponent_ufun"] = scenario.ufuns[1]
                    negotiators[1].private_info["opponent_ufun"] = scenario.ufuns[0]
                else:
                    # N-party case: give each negotiator list of opponent ufuns
                    for i, neg in enumerate(negotiators):
                        opponent_ufuns = [
                            ufun for j, ufun in enumerate(scenario.ufuns) if j != i
                        ]
                        neg.private_info["opponent_ufuns"] = opponent_ufuns
                        # Also set opponent_ufun to first opponent for compatibility
                        if opponent_ufuns:
                            neg.private_info["opponent_ufun"] = opponent_ufuns[0]

            # Build ID -> index mapping for proposer lookup
            negotiator_id_to_idx = {
                neg.id: idx for idx, neg in enumerate(mechanism.negotiators)
            }

            # Populate session info
            issue_names = [i.name for i in scenario.outcome_space.issues]
            session.issue_names = issue_names
            session.negotiator_types = [c.type_name for c in negotiator_configs]

            # Create negotiator infos with colors
            negotiator_colors = []
            for idx, (name, type_name) in enumerate(
                zip(session.negotiator_names, session.negotiator_types)
            ):
                color = NEGOTIATOR_COLORS[idx % len(NEGOTIATOR_COLORS)]
                negotiator_colors.append(color)
                session.negotiator_infos.append(
                    SessionNegotiatorInfo(
                        name=name,
                        type_name=type_name,
                        index=idx,
                        color=color,
                    )
                )

            # Compute outcome space analysis data (for N-party negotiations)
            # Run in thread pool as it can be computationally expensive
            outcome_space_data = None
            try:
                outcome_space_data = await asyncio.to_thread(
                    compute_outcome_space_data,
                    scenario,
                    max_outcome_samples,
                )
                session.outcome_space_data = outcome_space_data
            except Exception:
                pass  # Non-critical, continue without analysis

            # Yield session init event with all initial data
            # Get n_outcomes for TAU progress calculation
            n_outcomes = None
            try:
                n_outcomes = scenario.outcome_space.cardinality
            except Exception:
                pass

            init_event = SessionInitEvent(
                session_id=session_id,
                scenario_name=Path(session.scenario_path).name,
                scenario_path=session.scenario_path,
                negotiator_names=session.negotiator_names,
                negotiator_types=session.negotiator_types,
                negotiator_colors=negotiator_colors,
                issue_names=issue_names,
                n_steps=session.n_steps,
                time_limit=session.time_limit,
                n_outcomes=n_outcomes,
                outcome_space_data=outcome_space_data,
            )
            yield init_event

            # Start session
            session.status = SessionStatus.RUNNING
            session.start_time = datetime.now()

            # Run step by step
            # Note: mechanism.state.running is False before first step, so we use True initially
            running = True
            while running:
                # Check for cancellation
                if self._cancel_flags.get(session_id, False):
                    session.status = SessionStatus.CANCELLED
                    session.end_reason = "cancelled"
                    break

                # Check for pause - wait while paused
                while self._pause_flags.get(session_id, False):
                    session.status = SessionStatus.PAUSED
                    await asyncio.sleep(0.1)
                    # Check for cancel while paused
                    if self._cancel_flags.get(session_id, False):
                        session.status = SessionStatus.CANCELLED
                        session.end_reason = "cancelled"
                        break

                # Break out of outer loop if cancelled while paused
                if self._cancel_flags.get(session_id, False):
                    break

                # Resume running status
                if session.status == SessionStatus.PAUSED:
                    session.status = SessionStatus.RUNNING

                # Execute one step in thread pool to avoid blocking the event loop
                # This is critical for slow negotiators that sort the outcome space
                # Use timeout to prevent hung negotiators from freezing the UI
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(mechanism.step),
                        timeout=60.0,  # 60 second timeout per step
                    )
                except asyncio.TimeoutError:
                    # Step timed out - negotiator took too long
                    session.status = SessionStatus.COMPLETED
                    session.end_reason = "timeout"
                    session.error = "Negotiation step timed out (60s limit)"
                    break

                state: SAOState = mechanism.state
                session.current_step = state.step
                running = state.running  # Update for next iteration

                # Process ALL new offers from this step
                for proposer_id, offer in state.new_offers:
                    if offer is None:
                        continue

                    # Look up proposer index from ID
                    proposer_idx = negotiator_id_to_idx.get(proposer_id, 0)
                    proposer_name = session.negotiator_names[proposer_idx]

                    # Calculate utilities for all negotiators
                    utilities = []
                    for ufun in scenario.ufuns:
                        u = ufun(offer)
                        utilities.append(float(u) if u is not None else 0.0)

                    offer_dict = dict(zip(issue_names, offer))
                    event = OfferEvent(
                        step=state.step,
                        proposer=proposer_name,
                        proposer_index=proposer_idx,
                        offer=offer,
                        offer_dict=offer_dict,
                        utilities=utilities,
                        relative_time=state.relative_time,
                    )
                    session.offers.append(event)
                    yield event

                await asyncio.sleep(step_delay)

            # Session complete
            session.end_time = datetime.now()
            if session.status == SessionStatus.RUNNING:
                session.status = SessionStatus.COMPLETED

            # Record agreement
            final_state: SAOState = mechanism.state
            if mechanism.agreement is not None:
                session.agreement = mechanism.agreement
                session.agreement_dict = dict(zip(issue_names, mechanism.agreement))
                session.final_utilities = []
                for ufun in scenario.ufuns:
                    u = ufun(mechanism.agreement)
                    session.final_utilities.append(float(u) if u is not None else 0.0)
                session.end_reason = "agreement"

                # Compute optimality stats for the agreement
                try:
                    session.optimality_stats = await asyncio.to_thread(
                        compute_optimality_stats, scenario, mechanism.agreement
                    )
                except Exception as e:
                    print(f"Failed to compute optimality stats: {e}")
                    session.optimality_stats = None
            elif session.end_reason is None:
                # Determine end reason from final state
                if final_state.timedout:
                    session.end_reason = "timeout"
                elif final_state.broken:
                    session.end_reason = "broken"
                else:
                    session.end_reason = "no_agreement"

            # Auto-save if enabled (run in thread pool to avoid blocking)
            if self._auto_save.get(session_id, False):
                try:
                    configs = self._configs.get(session_id)
                    await asyncio.to_thread(
                        NegotiationStorageService.save_negotiation, session, configs
                    )
                except Exception as e:
                    print(f"Failed to auto-save negotiation {session_id}: {e}")

        except Exception as e:
            session.status = SessionStatus.FAILED
            session.error = str(e)
            session.end_time = datetime.now()

        yield session
