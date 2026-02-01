"""Unified negotiation loading service using negmas CompletedRun format.

This service provides a single interface for loading negotiations from:
- Single negotiation files (CSV trace files)
- Negotiation directories (CompletedRun folder format)
- Tournament results (cartesian_tournament output)
- In-memory Mechanism objects

All sources are converted to a standardized NegotiationData format for the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from negmas import Scenario
from negmas.mechanisms import CompletedRun
from negmas.sao import SAOMechanism

from ..models.session import (
    NEGOTIATOR_COLORS,
    AnalysisPoint,
    OutcomeSpaceData,
)


@dataclass
class NegotiationOffer:
    """A single offer in the negotiation history."""

    step: int
    relative_time: float
    time: float  # Absolute time in seconds
    proposer: str
    proposer_index: int
    offer: tuple | dict | None  # The offer values (None for end-of-negotiation entries)
    offer_dict: dict  # Always as {issue: value}
    utilities: list[float]  # Utility for each negotiator
    responses: dict[str, str]  # Negotiator -> response
    state: str  # "continuing", "agreement", "timedout", etc.


@dataclass
class NegotiationData:
    """Standardized negotiation data for UI display.

    This is the unified format that the frontend expects, regardless of
    how the negotiation was loaded (file, tournament, live session).
    """

    # Identity
    id: str
    source: str  # "live", "file", "tournament"
    source_path: str | None = None

    # Scenario info
    scenario_name: str = ""
    scenario_path: str | None = None

    # Negotiator info
    negotiator_names: list[str] = field(default_factory=list)
    negotiator_types: list[str] = field(default_factory=list)
    negotiator_colors: list[str] = field(default_factory=list)

    # Issue info
    issue_names: list[str] = field(default_factory=list)

    # Limits
    n_steps: int | None = None
    time_limit: float | None = None

    # Offer history
    offers: list[NegotiationOffer] = field(default_factory=list)

    # Result
    agreement: dict | None = None  # As {issue: value}
    agreement_tuple: tuple | None = None
    final_utilities: list[float] | None = None
    end_reason: str | None = None  # "agreement", "timedout", "broken", "error"

    # Final state info (from mechanism config)
    final_step: int = 0
    final_time: float = 0.0
    final_relative_time: float = 0.0

    # Optimality stats
    optimality_stats: dict | None = None

    # Outcome space visualization data
    outcome_space_data: OutcomeSpaceData | None = None

    # Raw metadata from CompletedRun
    metadata: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def _sanitize_for_json(value: Any) -> Any:
        """Sanitize a value for JSON serialization (handle inf/-inf/nan)."""
        import math

        if isinstance(value, float):
            if math.isinf(value) or math.isnan(value):
                return None
        return value

    def to_frontend_dict(self) -> dict[str, Any]:
        """Convert to the dict format expected by the frontend."""
        return {
            "id": self.id,
            "source": self.source,
            "scenario": self.scenario_name,
            "scenario_path": self.scenario_path,
            "negotiator_names": self.negotiator_names,
            "negotiator_types": self.negotiator_types,
            "negotiator_colors": self.negotiator_colors,
            "issue_names": self.issue_names,
            "n_steps": self.n_steps,
            "time_limit": self._sanitize_for_json(self.time_limit),
            "offers": [
                {
                    "step": o.step,
                    "relative_time": o.relative_time,
                    "time": o.time,
                    "proposer": o.proposer,
                    "proposer_index": o.proposer_index,
                    "offer": o.offer_dict,
                    "utilities": o.utilities,
                    "responses": o.responses,
                    "state": o.state,
                }
                for o in self.offers
            ],
            "agreement": self.agreement,
            "final_utilities": self.final_utilities,
            "end_reason": self.end_reason,
            "final_step": self.final_step,
            "final_time": self.final_time,
            "final_relative_time": self.final_relative_time,
            "optimality_stats": self.optimality_stats,
            "outcome_space_data": self._outcome_space_to_dict(),
            "isSaved": self.source in ("file", "tournament"),
            "isFromTournament": self.source == "tournament",
            # Include mechanism type for display
            "mechanism_type": self.config.get("mechanism_type", "SAOMechanism"),
        }

    def _outcome_space_to_dict(self) -> dict | None:
        """Convert outcome space data to dict for frontend."""
        if not self.outcome_space_data:
            return None
        osd = self.outcome_space_data
        result: dict[str, Any] = {
            "outcome_utilities": osd.outcome_utilities,
            "pareto_utilities": osd.pareto_utilities,
            "reserved_values": osd.reserved_values,
            "total_outcomes": osd.total_outcomes,
            "sampled": osd.sampled,
            "sample_size": osd.sample_size,
        }
        if osd.nash_point:
            result["nash_point"] = osd.nash_point.utilities
        if osd.kalai_point:
            result["kalai_point"] = osd.kalai_point.utilities
        if osd.kalai_smorodinsky_point:
            result["kalai_smorodinsky_point"] = osd.kalai_smorodinsky_point.utilities
        if osd.max_welfare_point:
            result["max_welfare_point"] = osd.max_welfare_point.utilities
        return result


class NegotiationLoader:
    """Unified service for loading negotiations from various sources."""

    @classmethod
    def from_completed_run(
        cls,
        run: CompletedRun,
        negotiation_id: str,
        source: str = "file",
        source_path: str | None = None,
        scenario_name: str | None = None,
    ) -> NegotiationData:
        """Load negotiation data from a CompletedRun object.

        Args:
            run: The CompletedRun object.
            negotiation_id: Unique ID for this negotiation.
            source: Source type ("file", "tournament", "live").
            source_path: Path to the source file/directory.
            scenario_name: Override scenario name if not in run.

        Returns:
            NegotiationData ready for UI display.
        """
        # Extract config - now contains all Mechanism construction arguments
        config = run.config or {}

        # If scenario is missing, try to load from scenario_path in metadata
        scenario = run.scenario
        metadata = run.metadata or {}
        scenario_path_from_meta = metadata.get("scenario_path")

        if scenario is None and scenario_path_from_meta:
            try:
                scenario = Scenario.load(  # type: ignore[attr-defined]
                    scenario_path_from_meta,
                    load_stats=False,
                    load_info=True,
                )
            except Exception:
                pass  # Scenario loading failed, continue without it

        # Negotiator info from config
        negotiator_names = config.get("negotiator_names", [])
        negotiator_types = config.get("negotiator_types", [])
        _negotiator_ids = config.get(
            "negotiator_ids", []
        )  # Extracted for potential future use
        n_negotiators = config.get("n_negotiators", 0) or len(negotiator_names) or 2

        # Assign colors
        negotiator_colors = [
            NEGOTIATOR_COLORS[i % len(NEGOTIATOR_COLORS)] for i in range(n_negotiators)
        ]

        # Mechanism config
        _mechanism_type = config.get(
            "mechanism_type", "SAOMechanism"
        )  # Stored for metadata
        n_steps = config.get("n_steps")
        time_limit = config.get("time_limit")
        _step_time_limit = config.get("step_time_limit")  # Stored for metadata
        _negotiator_time_limit = config.get(
            "negotiator_time_limit"
        )  # Stored for metadata

        # Final state from config
        final_step = config.get("final_step", 0)
        final_time = config.get("final_time", 0.0)
        final_relative_time = config.get("final_relative_time", 0.0)
        was_broken = config.get("broken", False)
        was_timedout = config.get("timedout", False)
        has_error = config.get("has_error", False)

        # Extract issue names from scenario or metadata
        issue_names: list[str] = []

        # First try metadata (saved by our app with proper issue names)
        if run.metadata and run.metadata.get("issue_names"):
            issue_names = run.metadata["issue_names"]

        # Then try scenario outcome_space
        if not issue_names and scenario and scenario.outcome_space:
            try:
                # Try dict-style access first (CartesianOutcomeSpace)
                issue_names = list(scenario.outcome_space.issues.keys())  # type: ignore[union-attr]
            except (AttributeError, TypeError):
                try:
                    # Try tuple-style (issues is a tuple of Issue objects)
                    issues = scenario.outcome_space.issues
                    if isinstance(issues, (list, tuple)):
                        issue_names = [
                            getattr(issue, "name", f"issue_{i}")
                            for i, issue in enumerate(issues)
                        ]
                except Exception:
                    pass

        # Parse history based on history_type
        offers = cls._parse_history(
            run.history,
            run.history_type,
            negotiator_names,
            issue_names,
            scenario,
        )

        # If we still don't have issue names, try to get from first offer
        if not issue_names and offers:
            issue_names = list(offers[0].offer_dict.keys())

        # Get agreement as dict
        agreement_dict = None
        agreement_tuple_val: tuple | None = None
        raw_agreement = run.agreement
        if raw_agreement and issue_names:
            if isinstance(raw_agreement, dict):
                agreement_dict = raw_agreement
                agreement_tuple_val = tuple(raw_agreement.values())
            else:
                agreement_tuple_val = tuple(raw_agreement) if raw_agreement else None
                if agreement_tuple_val:
                    agreement_dict = dict(zip(issue_names, agreement_tuple_val))

        # Extract outcome stats
        outcome_stats = run.outcome_stats or {}
        final_utilities = outcome_stats.get("utilities")

        # Determine end reason - prefer config values (from mechanism state)
        end_reason = None
        if was_timedout:
            end_reason = "timedout"
        elif was_broken:
            end_reason = "broken"
        elif has_error:
            end_reason = "error"
        elif run.agreement is not None:
            end_reason = "agreement"
        else:
            # Fallback to outcome_stats if config doesn't have the info
            if outcome_stats.get("timedout"):
                end_reason = "timedout"
            elif outcome_stats.get("broken"):
                end_reason = "broken"

        # Build optimality stats from run.agreement_stats (extracted from outcome_stats.yaml by CompletedRun)
        optimality_stats = None
        if run.agreement_stats:
            optimality_stats = {
                "pareto_optimality": run.agreement_stats.pareto_optimality,
                "nash_optimality": run.agreement_stats.nash_optimality,
                "kalai_optimality": run.agreement_stats.kalai_optimality,
                "max_welfare_optimality": run.agreement_stats.max_welfare_optimality,
                "ks_optimality": run.agreement_stats.ks_optimality,
            }

        # Build outcome space data from scenario
        outcome_space_data = cls._build_outcome_space_data(
            scenario,
            scenario_path=scenario_path_from_meta or source_path,
        )

        # Determine scenario name
        final_scenario_name = scenario_name or ""
        if not final_scenario_name:
            final_scenario_name = run.metadata.get("scenario_name", "") or ""
            if not final_scenario_name and source_path:
                final_scenario_name = Path(source_path).stem

        return NegotiationData(
            id=negotiation_id,
            source=source,
            source_path=source_path,
            scenario_name=final_scenario_name,
            scenario_path=source_path,
            negotiator_names=negotiator_names,
            negotiator_types=negotiator_types,
            negotiator_colors=negotiator_colors,
            issue_names=issue_names,
            n_steps=n_steps,
            time_limit=time_limit,
            offers=offers,
            agreement=agreement_dict,
            agreement_tuple=agreement_tuple_val,
            final_utilities=final_utilities,
            end_reason=end_reason,
            final_step=final_step,
            final_time=final_time,
            final_relative_time=final_relative_time,
            optimality_stats=optimality_stats,
            outcome_space_data=outcome_space_data,
            metadata=run.metadata or {},
            config=config,
        )

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        negotiation_id: str | None = None,
        load_scenario_stats: bool = False,
    ) -> NegotiationData:
        """Load negotiation from a file, directory, or compressed archive.

        Supports:
        - Directories (CompletedRun folder format)
        - CSV files (trace.csv format)
        - Compressed archives (.zip, .tar.gz, .tgz, .tar.bz2)

        Args:
            path: Path to trace file (CSV), negotiation directory, or compressed archive.
            negotiation_id: Optional ID, generated from path if not provided.
            load_scenario_stats: Whether to calculate scenario statistics.

        Returns:
            NegotiationData ready for UI display.
        """
        import shutil
        import tempfile
        import tarfile
        import zipfile

        path = Path(path)
        if not negotiation_id:
            # Strip multiple extensions for compressed files
            stem = path.stem
            if stem.endswith(".tar"):
                stem = stem[:-4]
            negotiation_id = f"file-{stem}"

        # Check if this is a compressed file that needs extraction
        temp_dir = None
        load_path = path

        try:
            if path.is_file():
                suffix_lower = "".join(path.suffixes).lower()

                if suffix_lower in (".zip",):
                    # Extract zip file
                    temp_dir = Path(tempfile.mkdtemp(prefix="negmas_load_"))
                    with zipfile.ZipFile(path, "r") as zf:
                        zf.extractall(temp_dir)
                    # Find the extracted content
                    load_path = cls._find_negotiation_root(temp_dir)

                elif suffix_lower in (".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar"):
                    # Extract tar file
                    temp_dir = Path(tempfile.mkdtemp(prefix="negmas_load_"))
                    with tarfile.open(path, "r:*") as tf:
                        tf.extractall(temp_dir)
                    # Find the extracted content
                    load_path = cls._find_negotiation_root(temp_dir)

            run = CompletedRun.load(  # type: ignore[attr-defined]
                load_path,
                load_scenario=True,
                load_scenario_stats=load_scenario_stats,
                load_agreement_stats=True,
                load_config=True,
            )

            return cls.from_completed_run(
                run,
                negotiation_id=negotiation_id,
                source="file",
                source_path=str(path),  # Use original path for display
            )
        finally:
            # Clean up temp directory if created
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _find_negotiation_root(cls, extracted_dir: Path) -> Path:
        """Find the negotiation root directory within extracted content.

        The archive might contain:
        - Direct files (trace.csv, config.yaml at root)
        - A single subdirectory containing the files
        - Multiple items
        """
        items = list(extracted_dir.iterdir())

        # If single directory, use it
        if len(items) == 1 and items[0].is_dir():
            return items[0]

        # Check if current dir has negotiation files
        if (extracted_dir / "trace.csv").exists() or (
            extracted_dir / "config.yaml"
        ).exists():
            return extracted_dir

        # Look for a subdirectory with negotiation files
        for item in items:
            if item.is_dir():
                if (item / "trace.csv").exists() or (item / "config.yaml").exists():
                    return item

        # Fall back to extracted dir
        return extracted_dir

    @classmethod
    def from_tournament(
        cls,
        tournament_path: str | Path,
        negotiation_name: str,
        negotiation_id: str | None = None,
    ) -> NegotiationData:
        """Load a negotiation from a tournament results directory.

        Args:
            tournament_path: Path to tournament results directory.
            negotiation_name: Name of the negotiation (without extension).
            negotiation_id: Optional ID, generated if not provided.

        Returns:
            NegotiationData ready for UI display.
        """
        tournament_path = Path(tournament_path)
        negotiations_dir = tournament_path / "negotiations"

        # Find the negotiation file
        negotiation_file = None
        for ext in [".csv", ".csv.gz", ".parquet"]:
            candidate = negotiations_dir / f"{negotiation_name}{ext}"
            if candidate.exists():
                negotiation_file = candidate
                break

        if not negotiation_file:
            # Try as directory
            negotiation_dir = negotiations_dir / negotiation_name
            if negotiation_dir.is_dir():
                negotiation_file = negotiation_dir

        if not negotiation_file or not negotiation_file.exists():
            raise FileNotFoundError(
                f"Negotiation {negotiation_name} not found in {negotiations_dir}"
            )

        if not negotiation_id:
            negotiation_id = f"tournament-{tournament_path.name}-{negotiation_name}"

        run = CompletedRun.load(  # type: ignore[attr-defined]
            negotiation_file,
            load_scenario=True,
            load_scenario_stats=False,
            load_agreement_stats=True,
            load_config=True,
        )

        # Try to get scenario name from negotiation name (format: scenario_neg1_neg2_rep_runid)
        parts = negotiation_name.split("_")
        scenario_name = parts[0] if parts else negotiation_name

        return cls.from_completed_run(
            run,
            negotiation_id=negotiation_id,
            source="tournament",
            source_path=str(negotiation_file),
            scenario_name=scenario_name,
        )

    @classmethod
    def from_mechanism(
        cls,
        mechanism: SAOMechanism,
        negotiation_id: str,
        scenario_name: str = "",
        scenario_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NegotiationData:
        """Load negotiation data from a completed Mechanism.

        Args:
            mechanism: The completed SAOMechanism.
            negotiation_id: Unique ID for this negotiation.
            scenario_name: Name of the scenario.
            scenario_path: Path to the scenario.
            metadata: Additional metadata to include.

        Returns:
            NegotiationData ready for UI display.
        """
        run = mechanism.to_completed_run(source="full_trace", metadata=metadata)  # type: ignore[attr-defined]

        return cls.from_completed_run(
            run,
            negotiation_id=negotiation_id,
            source="live",
            source_path=scenario_path,
            scenario_name=scenario_name,
        )

    @classmethod
    def _parse_history(
        cls,
        history: list,
        history_type: str,
        negotiator_names: list[str],
        issue_names: list[str],
        scenario: Scenario | None,
    ) -> list[NegotiationOffer]:
        """Parse history data into NegotiationOffer objects."""
        offers: list[NegotiationOffer] = []

        # Create name to index mapping
        name_to_idx = {name: i for i, name in enumerate(negotiator_names)}

        # Get utility functions for calculating utilities
        ufuns = None
        if scenario:
            try:
                ufuns = scenario.ufuns
            except Exception:
                pass

        for item in history:
            if history_type == "full_trace":
                # Full trace: time, relative_time, step, negotiator, offer, responses, state, [text, data]
                if isinstance(item, dict):
                    time_val = item.get("time", 0.0)
                    step = item.get("step", 0)
                    relative_time = item.get("relative_time", 0.0)
                    proposer = item.get("negotiator", "")
                    offer_raw = item.get("offer")
                    responses = item.get("responses", {})
                    state = item.get("state", "continuing")
                else:
                    # Named tuple or regular tuple
                    time_val = item[0] if len(item) > 0 else 0.0
                    step = item[2] if len(item) > 2 else 0
                    relative_time = item[1] if len(item) > 1 else 0.0
                    proposer = item[3] if len(item) > 3 else ""
                    offer_raw = item[4] if len(item) > 4 else None
                    responses = item[5] if len(item) > 5 else {}
                    state = item[6] if len(item) > 6 else "continuing"

            elif history_type == "extended_trace":
                # Extended trace: step, negotiator, offer
                if isinstance(item, dict):
                    step = item.get("step", 0)
                    proposer = item.get("negotiator", "")
                    offer_raw = item.get("offer")
                else:
                    step = item[0] if len(item) > 0 else 0
                    proposer = item[1] if len(item) > 1 else ""
                    offer_raw = item[2] if len(item) > 2 else None
                time_val = 0.0
                relative_time = 0.0
                responses = {}
                state = "continuing"

            elif history_type == "trace":
                # Simple trace: negotiator, offer
                if isinstance(item, dict):
                    proposer = item.get("negotiator", "")
                    offer_raw = item.get("offer")
                else:
                    proposer = item[0] if len(item) > 0 else ""
                    offer_raw = item[1] if len(item) > 1 else None
                step = len(offers)
                time_val = 0.0
                relative_time = 0.0
                responses = {}
                state = "continuing"

            else:
                # History (state dicts) - skip for now as it's complex
                continue

            # Convert offer to dict
            offer_dict: dict = {}
            offer_tuple_parsed: tuple | None = None

            if offer_raw is not None:
                # Handle string literal from CSV (e.g., "('HP', '60 Gb', \"19'' LCD\")")
                if isinstance(offer_raw, str):
                    try:
                        import ast

                        parsed = ast.literal_eval(offer_raw)
                        if isinstance(parsed, tuple):
                            offer_tuple_parsed = parsed
                        elif hasattr(parsed, "__iter__") and not isinstance(
                            parsed, str
                        ):
                            offer_tuple_parsed = tuple(parsed)
                        else:
                            offer_tuple_parsed = (parsed,)
                    except (ValueError, SyntaxError):
                        # If parsing fails, treat as single value
                        offer_tuple_parsed = (offer_raw,)
                elif isinstance(offer_raw, dict):
                    offer_dict = offer_raw
                elif isinstance(offer_raw, tuple):
                    offer_tuple_parsed = offer_raw
                else:
                    # Try to convert to tuple
                    try:
                        offer_tuple_parsed = tuple(offer_raw)
                    except TypeError:
                        offer_tuple_parsed = (offer_raw,)

                # Now build offer_dict from tuple if we have one
                if offer_tuple_parsed is not None and not offer_dict:
                    if issue_names and len(issue_names) == len(offer_tuple_parsed):
                        offer_dict = dict(zip(issue_names, offer_tuple_parsed))
                    else:
                        # No issue names or length mismatch, use indices
                        offer_dict = {
                            f"issue_{i}": v for i, v in enumerate(offer_tuple_parsed)
                        }

            # Use parsed tuple for utilities calculation
            offer_for_ufun = (
                offer_tuple_parsed if offer_tuple_parsed is not None else offer_raw
            )

            # Get proposer index
            proposer_index = name_to_idx.get(proposer, 0)
            # Handle case where proposer might be full ID with UUID
            if proposer_index == 0 and proposer:
                for name, idx in name_to_idx.items():
                    if name in proposer or proposer in name:
                        proposer_index = idx
                        break

            # Calculate utilities
            utilities: list[float] = []
            if ufuns and offer_for_ufun is not None:
                for ufun in ufuns:
                    try:
                        u = ufun(offer_for_ufun)
                        utilities.append(float(u) if u is not None else 0.0)
                    except Exception:
                        utilities.append(0.0)
            else:
                # No ufuns available, use empty utilities
                utilities = [0.0] * len(negotiator_names) if negotiator_names else []

            # Parse responses - handle string from CSV (e.g., "{}" or "{'name': <ResponseType>}")
            responses_str: dict[str, str] = {}
            if responses:
                if isinstance(responses, str):
                    try:
                        import ast

                        responses = ast.literal_eval(responses)
                    except (ValueError, SyntaxError):
                        responses = {}

                if isinstance(responses, dict):
                    for neg, resp in responses.items():
                        if hasattr(resp, "name"):
                            responses_str[neg] = resp.name
                        else:
                            responses_str[neg] = str(resp)

            offers.append(
                NegotiationOffer(
                    step=int(step) if step else 0,
                    relative_time=float(relative_time) if relative_time else 0.0,
                    time=float(time_val) if time_val else 0.0,
                    proposer=proposer,
                    proposer_index=proposer_index,
                    offer=offer_tuple_parsed,  # Use parsed tuple, not raw string
                    offer_dict=offer_dict,
                    utilities=utilities,
                    responses=responses_str,
                    state=str(state) if state else "continuing",
                )
            )

        return offers

    @classmethod
    def _build_outcome_space_data(
        cls,
        scenario: Scenario | None,
        scenario_path: str | None = None,
        max_auto_calc_stats: int = 10000,
    ) -> OutcomeSpaceData | None:
        """Build outcome space visualization data from scenario.

        Args:
            scenario: The loaded scenario.
            scenario_path: Path to the scenario directory (for caching).
            max_auto_calc_stats: If scenario has fewer outcomes than this and stats
                are not cached, compute stats automatically.

        Returns:
            OutcomeSpaceData with all computed values, or None if scenario is invalid.
        """
        if not scenario or not scenario.outcome_space:
            return None

        try:
            from .outcome_analysis import compute_outcome_space_data

            return compute_outcome_space_data(
                scenario,
                max_samples=5000,
                use_cached_stats=True,
                max_auto_calc_stats=max_auto_calc_stats,
                scenario_path=scenario_path,
                cache_if_under_app_dir=True,
            )
        except Exception:
            return None
