"""Tournament management service for running cartesian tournaments."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

from negmas import Scenario
from negmas.sao import SAOMechanism, SAONegotiator

from ..models.tournament import (
    TournamentConfig,
    TournamentSession,
    TournamentStatus,
    TournamentProgress,
    TournamentResults,
    CompetitorScore,
    NegotiationResult,
)
from .scenario_loader import ScenarioLoader
from .negotiator_factory import _get_class_for_type


class TournamentManager:
    """Manage tournament sessions with real-time progress updates."""

    def __init__(self):
        self.sessions: dict[str, TournamentSession] = {}
        self._cancel_flags: dict[str, bool] = {}
        self.scenario_loader = ScenarioLoader()

    def create_session(self, config: TournamentConfig) -> TournamentSession:
        """Create a new tournament session.

        Args:
            config: Tournament configuration.

        Returns:
            Created session (not yet started).
        """
        session_id = str(uuid.uuid4())[:8]
        session = TournamentSession(
            id=session_id,
            status=TournamentStatus.PENDING,
            config=config,
        )
        self.sessions[session_id] = session
        self._cancel_flags[session_id] = False
        return session

    def get_session(self, session_id: str) -> TournamentSession | None:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def cancel_session(self, session_id: str) -> bool:
        """Request cancellation of a running session."""
        if session_id in self._cancel_flags:
            self._cancel_flags[session_id] = True
            return True
        return False

    def list_sessions(self) -> list[TournamentSession]:
        """List all tournament sessions."""
        return list(self.sessions.values())

    def _get_mechanism_class(self, mechanism_type: str) -> type[SAOMechanism]:
        """Get mechanism class by name."""
        mechanism_map = {
            "SAOMechanism": SAOMechanism,
        }

        if mechanism_type in mechanism_map:
            return mechanism_map[mechanism_type]

        # Try to import from negmas.sao
        try:
            from negmas import sao

            if hasattr(sao, mechanism_type):
                return getattr(sao, mechanism_type)
        except ImportError:
            pass

        # Default to SAOMechanism
        return SAOMechanism

    async def run_tournament_stream(
        self,
        session_id: str,
    ) -> AsyncGenerator[TournamentProgress | TournamentSession, None]:
        """Run a tournament with streaming progress updates.

        This method runs negotiations serially to provide progress updates.
        For faster execution without progress updates, use run_tournament_batch().

        Yields:
            TournamentProgress updates, then final TournamentSession.
        """
        session = self.sessions.get(session_id)
        if session is None or session.config is None:
            return

        config = session.config
        session.status = TournamentStatus.RUNNING
        session.start_time = datetime.now()

        try:
            # Load scenarios (run in thread pool to avoid blocking)
            scenarios: list[Scenario] = []  # type: ignore[type-arg]
            for path in config.scenario_paths:
                scenario = await asyncio.to_thread(
                    self.scenario_loader.load_scenario, path
                )
                if scenario is not None:
                    scenarios.append(scenario)

            if not scenarios:
                session.status = TournamentStatus.FAILED
                session.error = "No valid scenarios found"
                yield session
                return

            # Get competitor classes (run in thread pool as it may import modules)
            competitor_classes: list[type[SAONegotiator]] = []
            for type_name in config.competitor_types:
                cls = await asyncio.to_thread(_get_class_for_type, type_name)
                if cls is not None:
                    competitor_classes.append(cls)  # type: ignore[arg-type]

            if len(competitor_classes) < 2:
                session.status = TournamentStatus.FAILED
                session.error = "At least 2 valid competitors required"
                yield session
                return

            # Calculate total negotiations
            n_competitors = len(competitor_classes)
            n_scenarios = len(scenarios)
            n_pairings_per_scenario = (
                n_competitors * n_competitors
                if config.self_play
                else n_competitors * (n_competitors - 1)
            )
            if config.rotate_ufuns:
                n_pairings_per_scenario *= 2  # Each pairing in both positions
            total_negotiations = (
                n_scenarios * n_pairings_per_scenario * config.n_repetitions
            )

            session.progress = TournamentProgress(
                completed=0,
                total=total_negotiations,
                percent=0.0,
            )
            yield session.progress

            # Track results
            negotiation_results: list[NegotiationResult] = []
            competitor_stats: dict[str, dict[str, Any]] = {
                cls.__name__: {
                    "utilities": [],
                    "advantages": [],
                    "n_negotiations": 0,
                    "n_agreements": 0,
                }
                for cls in competitor_classes
            }

            # Get mechanism class and params
            mechanism_class = self._get_mechanism_class(config.mechanism_type)
            mechanism_params: dict[str, Any] = {}
            if config.n_steps is not None:
                mechanism_params["n_steps"] = config.n_steps
            if config.time_limit is not None:
                mechanism_params["time_limit"] = config.time_limit

            completed = 0
            start_time = datetime.now()

            # Run all negotiations
            for scenario in scenarios:
                scenario_name = Path(scenario.outcome_space.name or "unknown").name

                for rep in range(config.n_repetitions):
                    for i, cls_i in enumerate(competitor_classes):
                        for j, cls_j in enumerate(competitor_classes):
                            # Skip self-play if disabled
                            if not config.self_play and i == j:
                                continue

                            # Run negotiation with original ufun assignment
                            result = await self._run_single_negotiation(
                                scenario=scenario,
                                competitor_classes=[cls_i, cls_j],
                                mechanism_class=mechanism_class,
                                mechanism_params=mechanism_params,
                            )
                            negotiation_results.append(result)
                            self._update_competitor_stats(
                                competitor_stats,
                                [cls_i.__name__, cls_j.__name__],
                                result,
                            )
                            completed += 1

                            # Update progress
                            session.progress = TournamentProgress(
                                completed=completed,
                                total=total_negotiations,
                                current_scenario=scenario_name,
                                current_partners=[cls_i.__name__, cls_j.__name__],
                                percent=(completed / total_negotiations) * 100,
                            )
                            yield session.progress

                            # Check for cancellation
                            if self._cancel_flags.get(session_id, False):
                                session.status = TournamentStatus.CANCELLED
                                session.end_time = datetime.now()
                                yield session
                                return

                            # Small delay to allow other tasks
                            await asyncio.sleep(0)

                            # Run with rotated ufuns if enabled
                            if config.rotate_ufuns and len(scenario.ufuns) == 2:
                                result = await self._run_single_negotiation(
                                    scenario=scenario,
                                    competitor_classes=[cls_i, cls_j],
                                    mechanism_class=mechanism_class,
                                    mechanism_params=mechanism_params,
                                    rotate_ufuns=True,
                                )
                                negotiation_results.append(result)
                                # Note: When rotated, cls_i gets ufun[1], cls_j gets ufun[0]
                                self._update_competitor_stats(
                                    competitor_stats,
                                    [cls_i.__name__, cls_j.__name__],
                                    result,
                                )
                                completed += 1

                                session.progress = TournamentProgress(
                                    completed=completed,
                                    total=total_negotiations,
                                    current_scenario=scenario_name,
                                    current_partners=[cls_i.__name__, cls_j.__name__],
                                    percent=(completed / total_negotiations) * 100,
                                )
                                yield session.progress

                                if self._cancel_flags.get(session_id, False):
                                    session.status = TournamentStatus.CANCELLED
                                    session.end_time = datetime.now()
                                    yield session
                                    return

                                await asyncio.sleep(0)

            # Calculate final scores
            final_scores = self._calculate_final_scores(
                competitor_stats,
                config.final_score_metric,
                config.final_score_stat,
            )

            # Calculate overall statistics
            total_agreements = sum(
                1 for r in negotiation_results if r.agreement is not None
            )
            execution_time = (datetime.now() - start_time).total_seconds()

            session.results = TournamentResults(
                final_scores=final_scores,
                negotiation_results=negotiation_results,
                total_negotiations=len(negotiation_results),
                total_agreements=total_agreements,
                overall_agreement_rate=total_agreements / len(negotiation_results)
                if negotiation_results
                else 0.0,
                execution_time=execution_time,
            )

            session.status = TournamentStatus.COMPLETED
            session.end_time = datetime.now()

        except Exception as e:
            session.status = TournamentStatus.FAILED
            session.error = str(e)
            session.end_time = datetime.now()

        yield session

    async def _run_single_negotiation(
        self,
        scenario: Scenario,  # type: ignore[type-arg]
        competitor_classes: list[type[SAONegotiator]],
        mechanism_class: type[SAOMechanism],
        mechanism_params: dict[str, Any],
        rotate_ufuns: bool = False,
    ) -> NegotiationResult:
        """Run a single negotiation and return the result."""
        scenario_name = scenario.outcome_space.name or "unknown"
        partners = [cls.__name__ for cls in competitor_classes]

        try:
            # Create mechanism
            mechanism = mechanism_class(
                outcome_space=scenario.outcome_space,
                **mechanism_params,
            )

            # Get ufuns (optionally rotated)
            ufuns = list(scenario.ufuns)
            if rotate_ufuns and len(ufuns) >= 2:
                ufuns = [ufuns[1], ufuns[0]]

            # Create negotiators and add to mechanism
            for cls, ufun in zip(competitor_classes, ufuns):
                negotiator = cls()
                mechanism.add(negotiator, ufun=ufun)

            # Run the negotiation (run in thread pool to avoid blocking)
            start = datetime.now()
            await asyncio.to_thread(mechanism.run)
            execution_time = (datetime.now() - start).total_seconds()

            # Get results
            agreement = mechanism.agreement
            utilities: list[float] | None = None
            advantages: list[float] | None = None

            if agreement is not None:
                # Get actual utilities (in original ufun order if rotated)
                if rotate_ufuns and len(scenario.ufuns) >= 2:
                    # Map back to original order
                    u0 = scenario.ufuns[0](agreement)
                    u1 = scenario.ufuns[1](agreement)
                    utilities = [
                        float(u1) if u1 is not None else 0.0,  # cls[0] had ufun[1]
                        float(u0) if u0 is not None else 0.0,  # cls[1] had ufun[0]
                    ]
                else:
                    utilities = []
                    for ufun in scenario.ufuns:
                        u = ufun(agreement)
                        utilities.append(float(u) if u is not None else 0.0)

                # Calculate advantages (utility - opponent's utility)
                if len(utilities) == 2:
                    advantages = [
                        utilities[0] - utilities[1],
                        utilities[1] - utilities[0],
                    ]

            return NegotiationResult(
                scenario=scenario_name,
                partners=partners,
                agreement=agreement,
                utilities=utilities,
                advantages=advantages,
                has_error=False,
                execution_time=execution_time,
            )

        except Exception as e:
            return NegotiationResult(
                scenario=scenario_name,
                partners=partners,
                agreement=None,
                utilities=None,
                advantages=None,
                has_error=True,
                error_details=str(e),
            )

    def _update_competitor_stats(
        self,
        stats: dict[str, dict[str, Any]],
        names: list[str],
        result: NegotiationResult,
    ) -> None:
        """Update competitor statistics with negotiation result."""
        for i, name in enumerate(names):
            if name not in stats:
                continue

            stats[name]["n_negotiations"] += 1

            if result.agreement is not None:
                stats[name]["n_agreements"] += 1

            if result.utilities is not None and i < len(result.utilities):
                stats[name]["utilities"].append(result.utilities[i])

            if result.advantages is not None and i < len(result.advantages):
                stats[name]["advantages"].append(result.advantages[i])

    def _calculate_final_scores(
        self,
        stats: dict[str, dict[str, Any]],
        metric: str,
        stat: str,
    ) -> list[CompetitorScore]:
        """Calculate final scores for all competitors."""
        import statistics

        scores = []

        for name, s in stats.items():
            # Get values based on metric
            if metric == "advantage":
                values = s["advantages"]
            elif metric == "utility":
                values = s["utilities"]
            elif metric == "welfare":
                # Sum of all utilities in negotiations where this competitor participated
                values = s["utilities"]  # Use utilities as proxy
            else:
                values = s["advantages"]

            # Calculate statistic
            if not values:
                score = 0.0
            elif stat == "mean":
                score = statistics.mean(values)
            elif stat == "median":
                score = statistics.median(values)
            elif stat == "min":
                score = min(values)
            elif stat == "max":
                score = max(values)
            elif stat == "std":
                score = statistics.stdev(values) if len(values) > 1 else 0.0
            else:
                score = statistics.mean(values)

            # Calculate additional statistics
            mean_utility = statistics.mean(s["utilities"]) if s["utilities"] else None
            mean_advantage = (
                statistics.mean(s["advantages"]) if s["advantages"] else None
            )
            agreement_rate = (
                s["n_agreements"] / s["n_negotiations"]
                if s["n_negotiations"] > 0
                else None
            )

            scores.append(
                CompetitorScore(
                    name=name,
                    type_name=name,  # Could be enhanced to store full type name
                    score=score,
                    rank=0,  # Will be set after sorting
                    mean_utility=mean_utility,
                    mean_advantage=mean_advantage,
                    n_negotiations=s["n_negotiations"],
                    n_agreements=s["n_agreements"],
                    agreement_rate=agreement_rate,
                )
            )

        # Sort by score (descending) and assign ranks
        scores.sort(key=lambda x: x.score, reverse=True)
        for i, s in enumerate(scores):
            s.rank = i + 1

        return scores

    async def run_tournament_batch(
        self,
        session_id: str,
    ) -> TournamentSession:
        """Run a tournament using negmas cartesian_tournament for faster execution.

        This method uses parallel execution but provides no progress updates.
        For progress updates, use run_tournament_stream().

        Returns:
            Completed TournamentSession.
        """
        session = self.sessions.get(session_id)
        if session is None or session.config is None:
            raise ValueError(f"Session not found: {session_id}")

        config = session.config
        session.status = TournamentStatus.RUNNING
        session.start_time = datetime.now()

        try:
            from negmas.tournaments.neg import cartesian_tournament

            # Load scenarios (run in thread pool to avoid blocking)
            scenarios: list[Scenario] = []  # type: ignore[type-arg]
            for path in config.scenario_paths:
                scenario = await asyncio.to_thread(
                    self.scenario_loader.load_scenario, path
                )
                if scenario is not None:
                    scenarios.append(scenario)

            if not scenarios:
                session.status = TournamentStatus.FAILED
                session.error = "No valid scenarios found"
                return session

            # Get competitor classes (run in thread pool as it may import modules)
            competitors: list[type[SAONegotiator]] = []
            for type_name in config.competitor_types:
                cls = await asyncio.to_thread(_get_class_for_type, type_name)
                if cls is not None:
                    competitors.append(cls)  # type: ignore[arg-type]

            if len(competitors) < 2:
                session.status = TournamentStatus.FAILED
                session.error = "At least 2 valid competitors required"
                return session

            # Get mechanism class
            mechanism_class = self._get_mechanism_class(config.mechanism_type)

            # Run tournament (run in thread pool - this can take hours/days)
            results = await asyncio.to_thread(
                cartesian_tournament,
                competitors=competitors,  # type: ignore[arg-type]
                scenarios=scenarios,
                competitor_params=None,
                rotate_ufuns=config.rotate_ufuns,
                n_repetitions=config.n_repetitions,
                njobs=config.njobs,
                mechanism_type=mechanism_class,  # type: ignore[arg-type]
                n_steps=config.n_steps,
                time_limit=config.time_limit,
                self_play=config.self_play,
                final_score=(config.final_score_metric, config.final_score_stat),
                verbosity=config.verbosity,
                path=Path(config.save_path) if config.save_path else None,
            )

            # Convert negmas results to our model
            final_scores: list[CompetitorScore] = []
            if results.final_scores is not None:
                for idx, row in results.final_scores.iterrows():
                    final_scores.append(
                        CompetitorScore(
                            name=str(idx),
                            type_name=str(idx),
                            score=float(row.iloc[0]) if len(row) > 0 else 0.0,
                            rank=len(final_scores) + 1,
                        )
                    )

            # Get detailed results if available
            total_negotiations = (
                len(results.details) if results.details is not None else 0
            )
            total_agreements = 0
            if results.details is not None and "agreement" in results.details.columns:
                total_agreements = int(results.details["agreement"].notna().sum())

            session.results = TournamentResults(
                final_scores=final_scores,
                total_negotiations=total_negotiations,
                total_agreements=total_agreements,
                overall_agreement_rate=total_agreements / total_negotiations
                if total_negotiations > 0
                else 0.0,
                results_path=str(results.path) if results.path else None,
            )

            session.status = TournamentStatus.COMPLETED
            session.end_time = datetime.now()

        except Exception as e:
            session.status = TournamentStatus.FAILED
            session.error = str(e)
            session.end_time = datetime.now()

        return session
