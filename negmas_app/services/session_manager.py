"""Manage negotiation sessions with real-time streaming."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

from negmas.sao import SAOState

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


# Module-level function for running negotiations in background thread (pickle-safe)
def _run_negotiation_in_thread(
    session_id: str,
    sessions_dict: dict,
    scenario_path: str,
    mechanism_type: str,
    mechanism_params: dict,
    negotiator_configs: list,
    scenario_options: dict,
    max_outcome_samples: int,
    auto_save: bool,
    share_ufuns: bool,
):
    """
    Run negotiation synchronously in background thread.
    Module-level to avoid pickling issues.
    """
    from negmas.sao import SAOState

    session = sessions_dict[session_id]

    try:
        # Load scenario
        scenario_loader = ScenarioLoader()
        ignore_discount = scenario_options.get("ignore_discount", False)
        scenario = scenario_loader.load_scenario(scenario_path, ignore_discount)

        if scenario is None:
            session.status = SessionStatus.FAILED
            session.error = "Failed to load scenario"
            session.end_time = datetime.now()
            return

        # Apply scenario options
        ignore_reserved = scenario_options.get("ignore_reserved", False)
        if ignore_reserved:
            for ufun in scenario.ufuns:
                if hasattr(ufun, "reserved_value"):
                    ufun.reserved_value = float("-inf")

        normalize = scenario_options.get("normalize", False)
        if normalize:
            scenario.normalize()

        # Ensure one_offer_per_step for SAO
        if (
            mechanism_type == "SAOMechanism"
            and "one_offer_per_step" not in mechanism_params
        ):
            mechanism_params = {**mechanism_params, "one_offer_per_step": True}

        # Create mechanism
        mechanism = MechanismFactory.create_from_scenario_params(
            scenario, mechanism_type, mechanism_params
        )

        # Create negotiators
        negotiators = NegotiatorFactory.create_for_scenario(
            negotiator_configs, scenario
        )

        # Add negotiators with time limits
        has_unsupported_features = False
        for neg, ufun, config in zip(negotiators, scenario.ufuns, negotiator_configs):
            add_kwargs = {"ufun": ufun}

            if config.time_limit is not None:
                add_kwargs["time_limit"] = config.time_limit
            if config.n_steps is not None:
                add_kwargs["n_steps"] = config.n_steps

            try:
                mechanism.add(neg, **add_kwargs)
            except TypeError as e:
                if "time_limit" in str(e) or "n_steps" in str(e):
                    has_unsupported_features = True
                    mechanism.add(neg, ufun=ufun)
                else:
                    raise

        if has_unsupported_features:
            import warnings

            warnings.warn(
                "Negotiator-specific time constraints (time_limit, n_steps) are not supported "
                "by the installed version of negmas. Falling back to mechanism-level time constraints.",
                UserWarning,
                stacklevel=2,
            )

        # Share utility functions if requested
        if share_ufuns:
            n_negs = len(negotiators)
            if n_negs == 2:
                negotiators[0].private_info["opponent_ufun"] = scenario.ufuns[1]
                negotiators[1].private_info["opponent_ufun"] = scenario.ufuns[0]
            else:
                for i, neg in enumerate(negotiators):
                    opponent_ufuns = [
                        ufun for j, ufun in enumerate(scenario.ufuns) if j != i
                    ]
                    neg.private_info["opponent_ufuns"] = opponent_ufuns
                    if opponent_ufuns:
                        neg.private_info["opponent_ufun"] = opponent_ufuns[0]

        # Store initial data for visualization
        session.scenario_name = scenario.name or Path(scenario_path).stem
        session.negotiator_names = [
            config.name or f"Negotiator {i + 1}"
            for i, config in enumerate(negotiator_configs)
        ]
        session.negotiator_types = [config.type_name for config in negotiator_configs]
        session.negotiator_colors = NEGOTIATOR_COLORS[: len(negotiator_configs)]
        session.issue_names = [issue.name for issue in scenario.issues]
        session.n_steps = mechanism.n_steps
        session.time_limit = mechanism.time_limit

        # Compute outcome space data for visualization
        outcome_space_data = compute_outcome_space_data(scenario, max_outcome_samples)
        session.outcome_space_data = outcome_space_data

        # Run mechanism and collect history
        negotiator_id_to_idx = {
            neg.id: idx for idx, neg in enumerate(mechanism.negotiators)
        }

        for state in mechanism:
            session.current_step = state.step

            # Store new offers as OfferEvent objects
            if len(mechanism.history) > len(session.offers):
                new_history = mechanism.history[len(session.offers) :]
                for h in new_history:
                    if isinstance(h, SAOState):
                        # Calculate utilities for this offer
                        utilities = []
                        if h.current_offer is not None:
                            for ufun in scenario.ufuns:
                                try:
                                    utilities.append(float(ufun(h.current_offer)))
                                except:
                                    utilities.append(0.0)
                        else:
                            utilities = [0.0] * len(scenario.ufuns)

                        # Create OfferEvent
                        from ..models import OfferEvent

                        offer_event = OfferEvent(
                            step=h.step,
                            proposer=h.current_proposer
                            if h.current_proposer
                            else "unknown",
                            proposer_index=negotiator_id_to_idx.get(
                                h.current_proposer, 0
                            )
                            if h.current_proposer
                            else 0,
                            offer=h.current_offer
                            if h.current_offer is not None
                            else (),
                            offer_dict=dict(zip(session.issue_names, h.current_offer))
                            if h.current_offer
                            else {},
                            utilities=utilities,
                            relative_time=h.relative_time,
                        )
                        session.offers.append(offer_event)

        # Negotiation complete - store final results
        session.status = SessionStatus.COMPLETED
        session.agreement = mechanism.agreement
        session.end_time = datetime.now()

        # Calculate final utilities
        if mechanism.agreement is not None:
            session.final_utilities = [
                float(ufun(mechanism.agreement)) for ufun in scenario.ufuns
            ]

        # Compute optimality stats
        if mechanism.agreement is not None:
            try:
                session.optimality_stats = compute_optimality_stats(
                    scenario, mechanism.agreement
                )
            except Exception as e:
                print(f"Failed to compute optimality stats: {e}")
                session.optimality_stats = None

        # Auto-save if requested
        if auto_save:
            try:
                NegotiationStorageService.save_negotiation(
                    session, negotiator_configs, None, scenario_options
                )
            except Exception as e:
                print(f"Failed to auto-save negotiation {session_id}: {e}")

    except Exception as e:
        session.status = SessionStatus.FAILED
        session.error = str(e)
        session.end_time = datetime.now()
        import traceback

        traceback.print_exc()


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

    def start_negotiation_background(
        self,
        session_id: str,
        share_ufuns: bool = False,
        max_outcome_samples: int = 50000,
    ) -> None:
        """
        Start negotiation in background thread using mechanism.run().
        Non-blocking - returns immediately while negotiation runs in thread.

        Args:
            session_id: Session ID to run
            share_ufuns: If True, share utility functions between negotiators
            max_outcome_samples: Maximum samples for outcome space analysis
        """
        session = self.sessions.get(session_id)
        if session is None:
            return

        # Prevent re-running
        if session.status != SessionStatus.PENDING:
            return

        # Mark as running immediately
        session.status = SessionStatus.RUNNING
        session.start_time = datetime.now()

        # Get stored configuration
        negotiator_configs = self._configs.get(session_id, [])
        mechanism_type = self._mechanism_types.get(session_id, "SAOMechanism")
        mechanism_params = self._mechanism_params.get(session_id, {}).copy()
        scenario_options = self._scenario_options.get(session_id, {})
        auto_save = self._auto_save.get(session_id, True)

        # Start in thread (non-blocking)
        asyncio.create_task(
            asyncio.to_thread(
                _run_negotiation_in_thread,
                session_id,
                self.sessions,  # Pass dict reference
                session.scenario_path,
                mechanism_type,
                mechanism_params,
                negotiator_configs,
                scenario_options,
                max_outcome_samples,
                auto_save,
                share_ufuns,
            )
        )

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

    def remove_completed_session(self, session_id: str) -> bool:
        """Remove a completed/failed session from memory after it's been saved.

        This frees up memory by removing sessions that are already persisted to disk.
        Only removes sessions that are completed, failed, or cancelled.

        Args:
            session_id: ID of the session to remove.

        Returns:
            True if session was removed, False if not found or still running.
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        # Only remove if session is no longer running
        if session.status not in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        ):
            return False

        # Clean up all session data from memory
        self.sessions.pop(session_id, None)
        self._configs.pop(session_id, None)
        self._mechanism_params.pop(session_id, None)
        self._mechanism_types.pop(session_id, None)
        self._scenario_options.pop(session_id, None)
        self._auto_save.pop(session_id, None)
        self._cancel_flags.pop(session_id, None)
        self._pause_flags.pop(session_id, None)

        return True

    async def run_session_stream(
        self,
        session_id: str,
        negotiator_configs: list[NegotiatorConfig],
        step_delay: float = 0.1,
        share_ufuns: bool = False,
        max_outcome_samples: int = 50000,
    ) -> AsyncGenerator:
        """Run a negotiation session and stream events.

        Args:
            session_id: Session ID to run.
            negotiator_configs: List of negotiator configurations.
            step_delay: Delay between steps (seconds) for real-time visualization.
            share_ufuns: If True, share utility functions between negotiators.

        Yields:
            SessionInitEvent at start, OfferEvent for each offer, then final NegotiationSession.
        """
        session = self.sessions.get(session_id)
        if session is None:
            return

        # CRITICAL: Prevent re-running a session that has already started
        # Use atomic check-and-set to prevent race condition
        # If a session is RUNNING, COMPLETED, FAILED, or CANCELLED, it should not be re-run
        # Only PENDING sessions should be allowed to run
        if session.status != SessionStatus.PENDING:
            # Session has already run or is currently running
            # Do not create a new mechanism - this would restart from step 0!
            return

        # Immediately set to RUNNING to prevent another call from starting
        # This must happen BEFORE any await to prevent race condition
        session.status = SessionStatus.RUNNING

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

            # Add negotiators to mechanism with negotiator-specific time limits
            # Just try to pass the parameters - if they're not supported, catch the error
            has_unsupported_features = False

            for neg, ufun, config in zip(
                negotiators, scenario.ufuns, negotiator_configs
            ):
                # Build kwargs for mechanism.add() with negotiator-specific time limits
                add_kwargs = {"ufun": ufun}

                # Add negotiator-specific time limits if provided
                if config.time_limit is not None:
                    add_kwargs["time_limit"] = config.time_limit

                if config.n_steps is not None:
                    add_kwargs["n_steps"] = config.n_steps

                # Try to add with time limits - if not supported, the mechanism will ignore them
                try:
                    await asyncio.to_thread(mechanism.add, neg, **add_kwargs)
                except TypeError as e:
                    # If we get TypeError about unexpected keyword arguments, it means
                    # the mechanism doesn't support these parameters
                    if "time_limit" in str(e) or "n_steps" in str(e):
                        has_unsupported_features = True
                        # Retry without the time limit parameters
                        await asyncio.to_thread(mechanism.add, neg, ufun=ufun)
                    else:
                        raise

            # Log warning if negotiator-specific time constraints were requested but not supported
            if has_unsupported_features:
                import warnings

                warnings.warn(
                    "Negotiator-specific time constraints (time_limit, n_steps) are not supported "
                    "by the installed version of negmas. Please upgrade to a newer version to use this feature. "
                    "Falling back to mechanism-level time constraints.",
                    UserWarning,
                    stacklevel=2,
                )

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
            session.scenario_name = Path(session.scenario_path).name

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

            # Start session - set start_time (status already set to RUNNING at function entry)
            session.start_time = datetime.now()

            # Run step by step
            # Note: mechanism.state.running is False before first step, so we use True initially
            running = True
            processed_history_length = (
                0  # Track how many history entries we've processed
            )
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

                # After step(), get the latest history entries
                # mechanism.history contains deep-copied states, each with only that step's offers
                # This works correctly regardless of one_offer_per_step setting
                history = mechanism.history

                # Get current state for checking running status
                current_state = mechanism.state
                session.current_step = current_state.step
                running = current_state.running

                # Process only the new history entries we haven't seen yet
                new_history_entries = history[processed_history_length:]

                for historical_state in new_history_entries:
                    # Each historical_state.new_offers contains only offers from that specific step
                    print(
                        f"[SessionManager]   Processing history entry: step={historical_state.step}, "
                        f"offers={len(historical_state.new_offers)}"
                    )

                    for proposer_id, offer in historical_state.new_offers:
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
                            step=historical_state.step,
                            proposer=proposer_name,
                            proposer_index=proposer_idx,
                            offer=offer,
                            offer_dict=offer_dict,
                            utilities=utilities,
                            relative_time=historical_state.relative_time,
                        )

                        # Debug: Check for backwards relative_time
                        if len(session.offers) > 0:
                            last_relative_time = session.offers[-1].relative_time
                            if historical_state.relative_time < last_relative_time:
                                print(
                                    f"[SessionManager] ⚠️⚠️ BACKWARDS TIME DETECTED! ⚠️⚠️"
                                )
                                print(
                                    f"  Last offer: step={session.offers[-1].step}, time={last_relative_time:.4f}"
                                )
                                print(
                                    f"  New offer:  step={historical_state.step}, time={historical_state.relative_time:.4f}"
                                )
                                print(
                                    f"  Difference: {historical_state.relative_time - last_relative_time:.4f}"
                                )

                        session.offers.append(event)
                        yield event

                # Update processed count to current history length
                processed_history_length = len(history)

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
                    session.optimality_stats = compute_optimality_stats(
                        scenario, mechanism.agreement
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
                    scenario_options = self._scenario_options.get(session_id, {})
                    await asyncio.to_thread(
                        NegotiationStorageService.save_negotiation,
                        session,
                        configs,
                        None,  # tags
                        scenario_options,
                    )
                    # Remove from memory after successful save to free resources
                    self.remove_completed_session(session_id)
                except Exception as e:
                    print(f"Failed to auto-save negotiation {session_id}: {e}")

        except Exception as e:
            session.status = SessionStatus.FAILED
            session.error = str(e)
            session.end_time = datetime.now()

        yield session
