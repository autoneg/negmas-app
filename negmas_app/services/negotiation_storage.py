"""Service for persisting negotiation sessions to disk using CompletedRun format.

All saving and loading is done through negmas CompletedRun.save() and CompletedRun.load().
This ensures compatibility with all formats supported by negmas.
"""

import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from negmas.mechanisms import CompletedRun
from negmas.sao import SAOMechanism

from ..models.session import (
    NegotiationSession,
    OfferEvent,
    OutcomeSpaceData,
    AnalysisPoint,
    SessionNegotiatorInfo,
)
from ..models.negotiator import NegotiatorConfig
from .negotiation_preview_service import NegotiationPreviewService

# Storage directory paths
NEGOTIATIONS_DIR = Path.home() / "negmas" / "app" / "negotiations"
ARCHIVE_DIR = Path.home() / "negmas" / "app" / "negotiations_archive"


def _ensure_dir(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def _serialize_datetime(dt: datetime | None) -> str | None:
    """Serialize datetime to ISO string."""
    return dt.isoformat() if dt else None


def _deserialize_datetime(s: str | None) -> datetime | None:
    """Deserialize ISO string to datetime."""
    if s is None:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


class NegotiationStorageService:
    """Service for saving and loading completed negotiations using CompletedRun format.

    All save/load operations use negmas CompletedRun.save() and CompletedRun.load()
    to ensure compatibility with all supported formats.
    """

    @staticmethod
    def get_storage_dir() -> Path:
        """Get the negotiations storage directory."""
        return NEGOTIATIONS_DIR

    @staticmethod
    def get_session_dir(session_id: str) -> Path:
        """Get the directory for a specific session."""
        return NEGOTIATIONS_DIR / session_id

    @staticmethod
    def _build_metadata(
        session: NegotiationSession,
        negotiator_configs: list[NegotiatorConfig] | None = None,
        tags: list[str] | None = None,
        scenario_options: dict | None = None,
    ) -> dict[str, Any]:
        """Build metadata dict for CompletedRun's metadata.yaml.

        All app-specific data is stored in run.metadata (metadata.yaml):
        - scenario_path: path to scenario directory
        - session_id: app's unique identifier
        - tags: app categorization feature
        - archived: app archive feature
        - negotiator_infos: includes UI colors
        - start_time, end_time: absolute timestamps
        - scenario_options: normalize, ignore_discount, ignore_reserved flags
        - negotiator_configs: for rerun feature
        """
        scenario_opts = scenario_options or {}

        # Build negotiator_infos with colors
        negotiator_infos = []
        if session.negotiator_infos:
            negotiator_infos = [
                {
                    "name": info.name,
                    "type_name": info.type_name,
                    "index": info.index,
                    "color": info.color,
                }
                for info in session.negotiator_infos
            ]

        metadata: dict[str, Any] = {
            "app_version": "2.0",
            "session_id": session.id,
            "scenario_path": session.scenario_path,
            "scenario_name": session.scenario_name,
            "tags": tags or [],
            "archived": False,
            "start_time": _serialize_datetime(session.start_time),
            "end_time": _serialize_datetime(session.end_time),
            "negotiator_infos": negotiator_infos,
            # Scenario options for reloading with same settings
            "normalize": scenario_opts.get("normalize", False),
            "ignore_discount": scenario_opts.get("ignore_discount", False),
            "ignore_reserved": scenario_opts.get("ignore_reserved", False),
        }

        # Store negotiator configs if provided (needed for rerun feature)
        if negotiator_configs:
            metadata["negotiator_configs"] = [asdict(c) for c in negotiator_configs]

        return metadata

    @staticmethod
    def save_negotiation_from_mechanism(
        mechanism: SAOMechanism,
        session: NegotiationSession,
        negotiator_configs: list[NegotiatorConfig] | None = None,
        tags: list[str] | None = None,
        scenario_options: dict | None = None,
        save_options: dict | None = None,
    ) -> Path:
        """Save a negotiation using Mechanism.save() with CompletedRun format.

        This is the primary method for saving negotiations. It uses
        Mechanism.save() which internally creates a CompletedRun and saves it.

        Args:
            mechanism: The completed SAOMechanism.
            session: The negotiation session with app-specific data.
            negotiator_configs: Original negotiator configurations (optional).
            tags: Optional list of tags for categorization.
            scenario_options: Dict with normalize, ignore_discount, ignore_reserved flags.
            save_options: Dict with CompletedRun save options:
                - single_file: Save as single trace file (default False)
                - per_negotiator: Save per-negotiator traces (default False)
                - save_scenario: Save scenario data (default True)
                - save_scenario_stats: Save scenario statistics (default False)
                - save_agreement_stats: Save agreement stats (default True)
                - save_config: Save mechanism config (default True)
                - source: History source (default "full_trace")
                - storage_format: Table format (default "parquet")
                - generate_previews: Generate preview images (default True)

        Returns:
            Path to the saved file or directory.
        """
        opts = save_options or {}
        single_file = opts.get("single_file", False)
        per_negotiator = opts.get("per_negotiator", False)
        save_scenario = opts.get("save_scenario", True)
        save_scenario_stats = opts.get("save_scenario_stats", False)
        save_agreement_stats = opts.get("save_agreement_stats", True)
        save_config = opts.get("save_config", True)
        source = opts.get("source")  # None = let negmas decide
        storage_format = opts.get("storage_format", "parquet")
        generate_previews = opts.get("generate_previews", True)

        # Build metadata (all app data goes to metadata.yaml via run.metadata)
        metadata = NegotiationStorageService._build_metadata(
            session, negotiator_configs, tags, scenario_options
        )

        # Ensure storage directory exists
        _ensure_dir(NEGOTIATIONS_DIR)

        # Use Mechanism.save() to save in CompletedRun format
        saved_path = mechanism.save(
            parent=NEGOTIATIONS_DIR,
            name=session.id,
            single_file=single_file,
            per_negotiator=per_negotiator,
            save_scenario=save_scenario,
            save_scenario_stats=save_scenario_stats,
            save_agreement_stats=save_agreement_stats,
            save_config=save_config,
            source=source,  # type: ignore[arg-type] # negmas now supports None
            metadata=metadata,  # All app data goes to metadata.yaml
            overwrite=True,
            warn_if_existing=False,
            storage_format=storage_format,
        )

        # For single-file saves, wrap in a directory for previews
        if single_file:
            trace_file = saved_path
            session_dir = NEGOTIATIONS_DIR / session.id
            _ensure_dir(session_dir)
            new_trace_path = session_dir / trace_file.name
            if trace_file != new_trace_path:
                shutil.move(str(trace_file), str(new_trace_path))
            saved_path = session_dir

        # Generate preview images if requested
        session_dir = saved_path if saved_path.is_dir() else saved_path.parent
        if generate_previews and not single_file:
            try:
                NegotiationPreviewService.generate_all_previews(session, session_dir)
            except Exception as e:
                print(f"Warning: Failed to generate preview images: {e}")

        return saved_path

    @staticmethod
    def save_negotiation(
        session: NegotiationSession,
        negotiator_configs: list[NegotiatorConfig] | None = None,
        tags: list[str] | None = None,
        scenario_options: dict | None = None,
        save_options: dict | None = None,
    ) -> Path:
        """Save a completed negotiation to disk without a mechanism object.

        This method creates a CompletedRun from session data and uses
        CompletedRun.save() to persist it. Use save_negotiation_from_mechanism()
        when you have access to the mechanism for more complete data.

        Args:
            session: The negotiation session to save.
            negotiator_configs: Original negotiator configurations (optional).
            tags: Optional list of tags for categorization.
            scenario_options: Dict with normalize, ignore_discount, ignore_reserved flags.
            save_options: Dict with save options (see save_negotiation_from_mechanism).

        Returns:
            Path to the session directory.
        """
        opts = save_options or {}
        storage_format = opts.get("storage_format", "parquet")
        generate_previews = opts.get("generate_previews", True)
        save_scenario = opts.get("save_scenario", True)
        save_scenario_stats = opts.get("save_scenario_stats", False)
        save_agreement_stats = opts.get("save_agreement_stats", True)
        save_config = opts.get("save_config", True)

        # Build metadata (all app data goes to metadata.yaml via run.metadata)
        metadata = NegotiationStorageService._build_metadata(
            session, negotiator_configs, tags, scenario_options
        )

        # Build history in full_trace format from session offers
        history = []
        for offer in session.offers:
            history.append(
                {
                    "time": offer.time if hasattr(offer, "time") else 0.0,
                    "relative_time": offer.relative_time,
                    "step": offer.step,
                    "negotiator": offer.proposer,
                    "offer": offer.offer if offer.offer else None,
                    "responses": offer.response or {},
                    "state": "continuing",
                    "text": None,
                    "data": None,
                }
            )

        # Build config dict
        config = {
            "mechanism_type": session.mechanism_type,
            "n_steps": session.n_steps,
            "time_limit": session.time_limit,
            "final_step": session.current_step,
            "n_negotiators": len(session.negotiator_names),
            "negotiator_names": session.negotiator_names,
            "negotiator_types": session.negotiator_types,
            "broken": session.end_reason == "broken",
            "timedout": session.end_reason in ("timeout", "timedout"),
            "has_error": session.error is not None,
        }

        # Build outcome_stats dict
        outcome_stats = {
            "agreement": list(session.agreement) if session.agreement else None,
            "broken": session.end_reason == "broken",
            "timedout": session.end_reason in ("timeout", "timedout"),
            "utilities": session.final_utilities,
        }

        # Create CompletedRun
        run = CompletedRun(
            history=history,
            history_type="full_trace",
            agreement=session.agreement,
            scenario=None,  # Will try to load from scenario_path if save_scenario=True
            agreement_stats=None,  # Will be calculated if save_agreement_stats=True
            config=config,
            outcome_stats=outcome_stats,
            metadata=metadata,  # All app data goes to metadata.yaml
        )

        # Ensure storage directory exists
        _ensure_dir(NEGOTIATIONS_DIR)

        # Use CompletedRun.save()
        saved_path = run.save(
            parent=NEGOTIATIONS_DIR,
            name=session.id,
            single_file=False,
            save_scenario=save_scenario,
            save_scenario_stats=save_scenario_stats,
            save_agreement_stats=save_agreement_stats,
            save_config=save_config,
            overwrite=True,
            warn_if_existing=False,
            storage_format=storage_format,
        )

        # Generate preview images
        session_dir = saved_path if saved_path.is_dir() else saved_path.parent
        if generate_previews:
            try:
                NegotiationPreviewService.generate_all_previews(session, session_dir)
            except Exception as e:
                print(f"Warning: Failed to generate preview images: {e}")

        return saved_path

    @staticmethod
    def load_negotiation(session_id: str) -> NegotiationSession | None:
        """Load a negotiation session from disk.

        Uses CompletedRun.load() to load any format supported by negmas.

        Args:
            session_id: The session ID to load.

        Returns:
            The loaded session, or None if not found.
        """
        session_dir = NegotiationStorageService.get_session_dir(session_id)
        if not session_dir.exists():
            # Try archive
            session_dir = ARCHIVE_DIR / session_id
            if not session_dir.exists():
                return None

        return NegotiationStorageService.load_from_path(session_dir)

    @staticmethod
    def load_from_path(path: str | Path) -> NegotiationSession | None:
        """Load a negotiation from an arbitrary path (file or directory).

        Uses CompletedRun.load() to load any format supported by negmas.
        App metadata is read from run.metadata (metadata.yaml).

        Args:
            path: Path to a negotiation file or directory.

        Returns:
            The loaded session, or None if loading failed.
        """
        path = Path(path)
        if not path.exists():
            return None

        try:
            # Use CompletedRun.load() for all formats
            run = CompletedRun.load(
                path,
                load_scenario=True,
                load_scenario_stats=False,
                load_agreement_stats=True,
                load_config=True,
            )

            # App metadata comes from run.metadata (metadata.yaml)
            # Session ID from metadata, or fall back to directory name
            run_metadata = run.metadata or {}
            session_id = run_metadata.get("session_id", path.stem)

            return NegotiationStorageService._session_from_completed_run(
                run, session_id, str(path)
            )

        except Exception as e:
            print(f"Failed to load negotiation from {path}: {e}")
            import traceback

            traceback.print_exc()
            return None

    @staticmethod
    def _session_from_completed_run(
        run: CompletedRun,  # type: ignore[type-arg]
        session_id: str,
        source_path: str,
    ) -> NegotiationSession:
        """Convert a CompletedRun to a NegotiationSession.

        All data comes from CompletedRun:
        - config.yaml (run.config): negotiator_names, negotiator_types, mechanism_type,
          n_steps, time_limit, broken, timedout, final_step
        - metadata.yaml (run.metadata): scenario_path, session_id, tags, archived,
          negotiator_infos (with colors), start_time, end_time, scenario options
        - scenario/: issue_names from outcome_space.issues
        - outcome_stats.yaml (run.outcome_stats): utilities, broken, timedout, optimality stats
        """
        from ..models.session import SessionStatus

        config = run.config or {}
        outcome_stats = run.outcome_stats or {}
        run_metadata = run.metadata or {}

        # Get negotiator info from config (standard CompletedRun)
        negotiator_names = config.get("negotiator_names", [])
        negotiator_types = config.get("negotiator_types", [])

        # Get issue names from scenario (standard CompletedRun)
        issue_names: list[str] = []
        if run.scenario and run.scenario.outcome_space:
            try:
                issues = run.scenario.outcome_space.issues
                if isinstance(issues, (list, tuple)):
                    issue_names = [
                        getattr(issue, "name", f"issue_{i}")
                        for i, issue in enumerate(issues)
                    ]
            except Exception:
                pass

        # Determine status (app-specific, default to completed)
        status_str = run_metadata.get("status", "completed")
        try:
            status = SessionStatus(status_str)
        except ValueError:
            status = SessionStatus.COMPLETED

        # Determine end reason from config (standard CompletedRun)
        end_reason = None
        if config.get("timedout") or outcome_stats.get("timedout"):
            end_reason = "timedout"
        elif config.get("broken") or outcome_stats.get("broken"):
            end_reason = "broken"
        elif run.agreement is not None:
            end_reason = "agreement"
        else:
            end_reason = "no_agreement"

        # Get scenario path from run.metadata
        scenario_path_str = run_metadata.get("scenario_path") or source_path
        scenario_name_str = (
            run_metadata.get("scenario_name") or Path(scenario_path_str).stem
        )

        # Create session
        session = NegotiationSession(
            id=session_id,
            status=status,
            scenario_path=scenario_path_str,
            scenario_name=scenario_name_str,
            mechanism_type=config.get("mechanism_type", "SAOMechanism"),
            negotiator_names=negotiator_names,
            negotiator_types=negotiator_types,
            issue_names=issue_names,
            issue_values={},
            n_steps=config.get("n_steps"),
            time_limit=config.get("time_limit"),
            start_time=_deserialize_datetime(run_metadata.get("start_time")),
            end_time=_deserialize_datetime(run_metadata.get("end_time")),
            current_step=config.get("final_step", 0),
            error=None,
        )

        # Set agreement from run (standard CompletedRun)
        if run.agreement:
            if isinstance(run.agreement, dict):
                session.agreement_dict = run.agreement
                session.agreement = tuple(run.agreement.values())
            else:
                session.agreement = tuple(run.agreement)
                if issue_names:
                    session.agreement_dict = dict(zip(issue_names, session.agreement))

        session.final_utilities = outcome_stats.get("utilities")
        session.end_reason = end_reason

        # Set optimality stats from run.agreement_stats (extracted from outcome_stats.yaml by CompletedRun)
        if run.agreement_stats:
            session.optimality_stats = {
                "pareto_optimality": run.agreement_stats.pareto_optimality,
                "nash_optimality": run.agreement_stats.nash_optimality,
                "kalai_optimality": run.agreement_stats.kalai_optimality,
                "max_welfare_optimality": run.agreement_stats.max_welfare_optimality,
                "ks_optimality": run.agreement_stats.ks_optimality,
            }

        # Build negotiator_infos from run.metadata (includes colors)
        negotiator_infos_data = run_metadata.get("negotiator_infos", [])
        default_colors = [
            "#4a6fa5",
            "#22a06b",
            "#f59e0b",
            "#ef4444",
            "#8b5cf6",
            "#06b6d4",
        ]

        if negotiator_infos_data:
            # Use negotiator_infos from metadata (has colors)
            for info_data in negotiator_infos_data:
                session.negotiator_infos.append(
                    SessionNegotiatorInfo(
                        name=info_data.get("name", ""),
                        type_name=info_data.get("type_name", ""),
                        index=info_data.get("index", 0),
                        color=info_data.get(
                            "color",
                            default_colors[
                                info_data.get("index", 0) % len(default_colors)
                            ],
                        ),
                    )
                )
        else:
            # Fallback: build from config negotiator_names
            for i, name in enumerate(negotiator_names):
                session.negotiator_infos.append(
                    SessionNegotiatorInfo(
                        name=name,
                        type_name=negotiator_types[i]
                        if i < len(negotiator_types)
                        else "",
                        index=i,
                        color=default_colors[i % len(default_colors)],
                    )
                )

        # Parse history into offers
        ufuns_list = (
            list(run.scenario.ufuns) if run.scenario and run.scenario.ufuns else None
        )
        session.offers = NegotiationStorageService._parse_history_to_offers(
            run.history,
            run.history_type,
            negotiator_names,
            issue_names,
            ufuns_list,
        )

        # If issue_names is still empty but we have offers with tuples, generate issue names
        if not issue_names and session.offers:
            first_offer = session.offers[0].offer
            if first_offer:
                n_issues = len(first_offer)
                issue_names = [f"issue_{i}" for i in range(n_issues)]
                session.issue_names = issue_names
                # Rebuild offer_dicts with the new issue names
                for offer in session.offers:
                    if offer.offer and len(offer.offer) == n_issues:
                        offer.offer_dict = dict(zip(issue_names, offer.offer))

        # Build outcome space data from scenario if available
        scenario = run.scenario

        # If scenario not in CompletedRun, try to load from scenario_path in run.metadata
        scenario_path_from_meta = run_metadata.get("scenario_path")
        if scenario is None and scenario_path_from_meta:
            try:
                from negmas import Scenario

                scenario_path_obj = Path(scenario_path_from_meta)
                if scenario_path_obj.exists():
                    scenario = Scenario.load(  # type: ignore[attr-defined]
                        scenario_path_obj,
                        load_stats=True,
                        load_info=True,
                    )
            except Exception as e:
                print(f"Failed to load scenario from {scenario_path_from_meta}: {e}")

        if scenario:
            session.outcome_space_data = (
                NegotiationStorageService._build_outcome_space_from_scenario(scenario)
            )

        return session

    @staticmethod
    def _parse_history_to_offers(
        history: list,
        history_type: str,
        negotiator_names: list[str],
        issue_names: list[str],
        ufuns: list | None = None,
    ) -> list[OfferEvent]:
        """Parse CompletedRun history into OfferEvent objects.

        Handles all history types: full_trace, full_trace_with_utils, extended_trace, trace, history.

        The 'history' type contains raw SAOState objects which need special handling.
        """
        offers: list[OfferEvent] = []
        name_to_idx = {name: i for i, name in enumerate(negotiator_names)}

        # Handle empty history
        if not history:
            return offers

        # Debug: print history type for troubleshooting
        # print(f"[_parse_history_to_offers] history_type={history_type}, len(history)={len(history)}")

        for item in history:
            # Extract fields based on history type
            # For utilities that might be embedded in the trace
            embedded_utilities: list[float] = []

            if history_type in ("full_trace", "full_trace_with_utils"):
                if isinstance(item, dict):
                    time_val = item.get("time", 0.0)
                    step = item.get("step", 0)
                    relative_time = item.get("relative_time", 0.0)
                    proposer = item.get("negotiator", "")
                    offer_raw = item.get("offer")
                    response = item.get("responses", "")
                    # For full_trace_with_utils, utilities are in columns named after negotiators
                    if history_type == "full_trace_with_utils":
                        # First check for explicit 'utilities' key
                        if "utilities" in item:
                            embedded_utilities = item.get("utilities", [])
                        else:
                            # Extract utilities from negotiator-named columns
                            # Standard trace fields that are NOT utility columns
                            trace_fields = {
                                "time",
                                "relative_time",
                                "step",
                                "negotiator",
                                "offer",
                                "responses",
                                "state",
                                "text",
                                "data",
                            }
                            utility_keys = [
                                k for k in item.keys() if k not in trace_fields
                            ]
                            if utility_keys and negotiator_names:
                                for name in negotiator_names:
                                    found = False
                                    for uk in utility_keys:
                                        if uk == name or uk in name or name in uk:
                                            val = item.get(uk, 0.0)
                                            embedded_utilities.append(
                                                float(val) if val is not None else 0.0
                                            )
                                            found = True
                                            break
                                    if not found:
                                        embedded_utilities.append(0.0)
                            elif utility_keys:
                                # No negotiator names, use sorted keys
                                embedded_utilities = [
                                    float(item.get(k, 0.0) or 0.0)
                                    for k in sorted(utility_keys)
                                ]
                else:
                    # Named tuple or list
                    # TraceElement fields: (time, relative_time, step, negotiator, offer, responses)
                    # For full_trace_with_utils: utilities are appended at indices 6+
                    time_val = item[0] if len(item) > 0 else 0.0
                    step = item[2] if len(item) > 2 else 0
                    relative_time = item[1] if len(item) > 1 else 0.0
                    proposer = item[3] if len(item) > 3 else ""
                    offer_raw = item[4] if len(item) > 4 else None
                    response = item[5] if len(item) > 5 else ""
                    # Extract embedded utilities for full_trace_with_utils (at index 6 onwards)
                    if history_type == "full_trace_with_utils" and len(item) > 6:
                        for i in range(6, len(item)):
                            try:
                                u = float(item[i]) if item[i] is not None else 0.0
                                embedded_utilities.append(u)
                            except (ValueError, TypeError):
                                embedded_utilities.append(0.0)

            elif history_type == "extended_trace":
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
                response = ""

            elif history_type == "trace":
                if isinstance(item, dict):
                    proposer = item.get("negotiator", "")
                    offer_raw = item.get("offer")
                else:
                    proposer = item[0] if len(item) > 0 else ""
                    offer_raw = item[1] if len(item) > 1 else None
                step = len(offers)
                time_val = 0.0
                relative_time = 0.0
                response = ""

            else:
                # "history" type contains raw SAOState objects
                # Try to extract offer info from the state
                if isinstance(item, dict):
                    # SAOState as dict
                    step = item.get("step", len(offers))
                    offer_raw = item.get("current_offer")
                    proposer = item.get("current_proposer", "")
                    # Try to find proposer name if we have an index
                    if isinstance(proposer, int) and proposer < len(negotiator_names):
                        proposer = negotiator_names[proposer]
                    time_val = item.get("time", 0.0)
                    relative_time = item.get("relative_time", 0.0)
                    response = ""
                elif hasattr(item, "current_offer"):
                    # SAOState object
                    step = getattr(item, "step", len(offers))
                    offer_raw = getattr(item, "current_offer", None)
                    proposer_val = getattr(item, "current_proposer", 0)
                    proposer = (
                        negotiator_names[proposer_val]
                        if isinstance(proposer_val, int)
                        and proposer_val < len(negotiator_names)
                        else str(proposer_val)
                    )
                    time_val = getattr(item, "time", 0.0)
                    relative_time = getattr(item, "relative_time", 0.0)
                    response = ""
                else:
                    # Unknown format, skip
                    continue

            # Parse offer
            offer_tuple = None
            offer_dict: dict = {}

            if offer_raw is not None:
                if isinstance(offer_raw, str):
                    try:
                        import ast

                        parsed = ast.literal_eval(offer_raw)
                        offer_tuple = (
                            tuple(parsed) if hasattr(parsed, "__iter__") else (parsed,)
                        )
                    except (ValueError, SyntaxError):
                        offer_tuple = (offer_raw,)
                elif isinstance(offer_raw, dict):
                    offer_dict = offer_raw
                    offer_tuple = tuple(offer_raw.values())
                else:
                    try:
                        offer_tuple = tuple(offer_raw)
                    except TypeError:
                        offer_tuple = (offer_raw,)

                if offer_tuple and not offer_dict and issue_names:
                    if len(issue_names) == len(offer_tuple):
                        offer_dict = dict(zip(issue_names, offer_tuple))

            # Get proposer index
            proposer_idx = name_to_idx.get(proposer, 0)
            if proposer_idx == 0 and proposer:
                for name, idx in name_to_idx.items():
                    if name in proposer or proposer in name:
                        proposer_idx = idx
                        break

            # Calculate utilities - prefer embedded utilities from full_trace_with_utils,
            # otherwise calculate from ufuns if available
            utilities: list[float] = []
            if embedded_utilities:
                # Use pre-calculated utilities from full_trace_with_utils
                utilities = embedded_utilities
            elif ufuns and offer_tuple:
                # Calculate utilities from ufuns
                for ufun in ufuns:
                    try:
                        u = ufun(offer_tuple)
                        utilities.append(float(u) if u is not None else 0.0)
                    except Exception:
                        utilities.append(0.0)

            offers.append(
                OfferEvent(
                    step=int(step) if step else 0,
                    proposer=proposer,
                    proposer_index=proposer_idx,
                    offer=offer_tuple or (),
                    offer_dict=offer_dict,
                    utilities=utilities,
                    timestamp=datetime.now(),
                    response=str(response) if response else None,
                    relative_time=float(relative_time) if relative_time else 0.0,
                    time=float(time_val) if time_val else 0.0,
                )
            )

        return offers

    @staticmethod
    def _build_outcome_space_from_scenario(scenario) -> OutcomeSpaceData | None:  # type: ignore[type-arg]
        """Build outcome space data from a Scenario object."""
        try:
            # Calculate stats if needed (use public .stats property)
            if scenario.stats is None:
                scenario.calc_stats()

            stats = scenario.stats
            if not stats:
                return None

            # Sample outcomes
            MAX_OUTCOMES = 5000
            outcome_utilities: list[tuple[float, ...]] = []

            try:
                outcomes = list(
                    scenario.outcome_space.enumerate_or_sample(MAX_OUTCOMES)
                )
                for outcome in outcomes:
                    utils = tuple(
                        float(ufun(outcome)) if ufun(outcome) is not None else 0.0
                        for ufun in scenario.ufuns
                    )
                    outcome_utilities.append(utils)
            except Exception:
                pass

            # Get Pareto frontier
            pareto_utilities: list[tuple[float, ...]] = []
            if hasattr(stats, "pareto_utils") and stats.pareto_utils:
                pareto_utilities = [tuple(u) for u in stats.pareto_utils]

            # Get special points
            nash_point = None
            if hasattr(stats, "nash_utils") and stats.nash_utils:
                nash_point = AnalysisPoint(
                    name="nash",
                    utilities=list(stats.nash_utils[0]) if stats.nash_utils else [],
                )

            kalai_point = None
            if hasattr(stats, "kalai_utils") and stats.kalai_utils:
                kalai_point = AnalysisPoint(
                    name="kalai",
                    utilities=list(stats.kalai_utils[0]) if stats.kalai_utils else [],
                )

            ks_point = None
            if hasattr(stats, "ks_utils") and stats.ks_utils:
                ks_point = AnalysisPoint(
                    name="kalai_smorodinsky",
                    utilities=list(stats.ks_utils[0]) if stats.ks_utils else [],
                )

            max_welfare_point = None
            if hasattr(stats, "max_welfare_utils") and stats.max_welfare_utils:
                max_welfare_point = AnalysisPoint(
                    name="max_welfare",
                    utilities=list(stats.max_welfare_utils[0])
                    if stats.max_welfare_utils
                    else [],
                )

            # Get reserved values from ufuns
            reserved_values: list[float] = []
            try:
                for ufun in scenario.ufuns:
                    rv = getattr(ufun, "reserved_value", None)
                    if rv is not None:
                        reserved_values.append(float(rv))
                    else:
                        reserved_values.append(0.0)
            except Exception:
                pass

            return OutcomeSpaceData(
                outcome_utilities=outcome_utilities,
                pareto_utilities=pareto_utilities,
                nash_point=nash_point,
                kalai_point=kalai_point,
                kalai_smorodinsky_point=ks_point,
                max_welfare_point=max_welfare_point,
                reserved_values=reserved_values,
                total_outcomes=len(outcome_utilities),
                sampled=len(outcome_utilities) >= MAX_OUTCOMES,
                sample_size=len(outcome_utilities),
            )
        except Exception:
            return None

    @staticmethod
    def list_saved_negotiations(include_archived: bool = False) -> list[dict]:
        """List all saved negotiations.

        Args:
            include_archived: If True, also include archived negotiations.

        Returns:
            List of dictionaries with summary info for each negotiation.
        """
        negotiations = []

        # List from main directory
        if NEGOTIATIONS_DIR.exists():
            negotiations.extend(
                NegotiationStorageService._list_from_dir(
                    NEGOTIATIONS_DIR, archived=False
                )
            )

        # List from archive if requested
        if include_archived and ARCHIVE_DIR.exists():
            negotiations.extend(
                NegotiationStorageService._list_from_dir(ARCHIVE_DIR, archived=True)
            )

        # Sort by end_time descending (most recent first)
        negotiations.sort(key=lambda x: x.get("end_time") or "", reverse=True)

        return negotiations

    @staticmethod
    def _list_from_dir(directory: Path, archived: bool = False) -> list[dict]:
        """List negotiations from a specific directory.

        Uses CompletedRun standard files (config.yaml, metadata.yaml, outcome_stats.yaml).
        All app-specific data is in metadata.yaml (run.metadata).
        """
        negotiations = []

        for session_path in directory.iterdir():
            if not session_path.is_dir() and not session_path.suffix in (
                ".csv",
                ".parquet",
            ):
                continue

            # Try to load from CompletedRun (standard format)
            try:
                run = CompletedRun.load(
                    session_path,
                    load_scenario=False,
                    load_scenario_stats=False,
                    load_agreement_stats=False,
                    load_config=True,
                )
                config = run.config or {}
                outcome_stats = run.outcome_stats or {}
                run_metadata = run.metadata or {}

                # Get scenario info from run.metadata
                scenario_path = run_metadata.get("scenario_path", "")
                scenario_name = run_metadata.get("scenario_name") or (
                    Path(scenario_path).name if scenario_path else session_path.stem
                )

                summary = {
                    "id": run_metadata.get("session_id", session_path.stem),
                    "status": run_metadata.get("status", "completed"),
                    "scenario_name": scenario_name,
                    "scenario_path": scenario_path,
                    "mechanism_type": config.get("mechanism_type"),
                    # From config.yaml (standard CompletedRun)
                    "negotiator_names": config.get("negotiator_names", []),
                    "negotiator_types": config.get("negotiator_types", []),
                    # From metadata.yaml (run.metadata)
                    "start_time": run_metadata.get("start_time"),
                    "end_time": run_metadata.get("end_time"),
                    "n_steps": config.get("n_steps"),
                    "tags": run_metadata.get("tags", []),
                    "archived": archived or run_metadata.get("archived", False),
                    "created_at": run_metadata.get("start_time"),
                    "completed_at": run_metadata.get("end_time"),
                    # From outcome_stats.yaml (standard CompletedRun)
                    "agreement": outcome_stats.get("agreement"),
                    "has_agreement": outcome_stats.get("agreement") is not None,
                    "final_utilities": outcome_stats.get("utilities"),
                }

                negotiations.append(summary)

            except Exception:
                # If CompletedRun.load fails, skip this entry
                pass

        return negotiations

    @staticmethod
    def archive_negotiation(session_id: str) -> bool:
        """Move a negotiation to the archive."""
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            return False

        _ensure_dir(ARCHIVE_DIR)
        archive_dest = ARCHIVE_DIR / session_id
        shutil.move(str(session_dir), str(archive_dest))

        # Update metadata.yaml to mark as archived
        NegotiationStorageService._update_metadata_field(archive_dest, "archived", True)

        return True

    @staticmethod
    def unarchive_negotiation(session_id: str) -> bool:
        """Restore a negotiation from the archive."""
        archive_dir = ARCHIVE_DIR / session_id
        if not archive_dir.exists():
            return False

        _ensure_dir(NEGOTIATIONS_DIR)
        dest = NEGOTIATIONS_DIR / session_id
        shutil.move(str(archive_dir), str(dest))

        # Update metadata.yaml
        NegotiationStorageService._update_metadata_field(dest, "archived", False)

        return True

    @staticmethod
    def _update_metadata_field(session_dir: Path, field: str, value: Any) -> bool:
        """Update a field in metadata.yaml."""
        from negmas.helpers.inout import dump, load

        metadata_path = session_dir / "metadata.yaml"
        if not metadata_path.exists():
            return False

        try:
            metadata = load(metadata_path) or {}
            metadata[field] = value
            dump(metadata, metadata_path)
            return True
        except Exception as e:
            print(f"Warning: Failed to update metadata: {e}")
            return False

    @staticmethod
    def update_tags(session_id: str, tags: list[str]) -> bool:
        """Update tags for a negotiation."""
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        return NegotiationStorageService._update_metadata_field(
            session_dir, "tags", tags
        )

    @staticmethod
    def add_tag(session_id: str, tag: str) -> bool:
        """Add a tag to a negotiation."""
        from negmas.helpers.inout import load

        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / "metadata.yaml"
        if not metadata_path.exists():
            return False

        try:
            metadata = load(metadata_path) or {}
            tags = metadata.get("tags", [])
            if tag not in tags:
                tags.append(tag)
                return NegotiationStorageService._update_metadata_field(
                    session_dir, "tags", tags
                )
            return True
        except Exception:
            return False

    @staticmethod
    def remove_tag(session_id: str, tag: str) -> bool:
        """Remove a tag from a negotiation."""
        from negmas.helpers.inout import load

        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / "metadata.yaml"
        if not metadata_path.exists():
            return False

        try:
            metadata = load(metadata_path) or {}
            tags = metadata.get("tags", [])
            if tag in tags:
                tags.remove(tag)
                return NegotiationStorageService._update_metadata_field(
                    session_dir, "tags", tags
                )
            return True
        except Exception:
            return False

    @staticmethod
    def get_all_tags() -> list[str]:
        """Get all unique tags used across all negotiations."""
        all_tags: set[str] = set()

        for directory in [NEGOTIATIONS_DIR, ARCHIVE_DIR]:
            if not directory.exists():
                continue

            for session_dir in directory.iterdir():
                if not session_dir.is_dir():
                    continue

                metadata_path = session_dir / "metadata.yaml"
                if metadata_path.exists():
                    try:
                        from negmas.helpers.inout import load

                        metadata = load(metadata_path) or {}
                        all_tags.update(metadata.get("tags", []))
                    except Exception:
                        pass

        return sorted(all_tags)

    @staticmethod
    def import_negotiation(
        path: str | Path,
        tags: list[str] | None = None,
    ) -> NegotiationSession | None:
        """Import a negotiation from an external path into the app's storage.

        Loads the negotiation using CompletedRun.load(), then saves it using
        CompletedRun.save() with a new session ID.

        Args:
            path: Path to a negotiation file or directory.
            tags: Optional tags to add to the imported negotiation.

        Returns:
            The imported session with new ID, or None if import failed.
        """
        path = Path(path)
        if not path.exists():
            return None

        try:
            # Load the negotiation using CompletedRun.load()
            run = CompletedRun.load(
                path,
                load_scenario=True,
                load_scenario_stats=False,
                load_agreement_stats=True,
                load_config=True,
            )

            # Generate a new session ID with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = path.stem
            new_session_id = f"imported_{original_name}_{timestamp}"

            # Build app metadata with import info
            original_metadata = run.metadata or {}
            app_metadata = {
                "app_version": "2.0",
                "session_id": new_session_id,
                "scenario_path": original_metadata.get("scenario_path", str(path)),
                "scenario_name": original_metadata.get("scenario_name", original_name),
                "negotiator_names": original_metadata.get(
                    "negotiator_names",
                    run.config.get("negotiator_names", []) if run.config else [],
                ),
                "negotiator_types": original_metadata.get(
                    "negotiator_types",
                    run.config.get("negotiator_types", []) if run.config else [],
                ),
                "issue_names": original_metadata.get("issue_names", []),
                "start_time": original_metadata.get("start_time"),
                "end_time": original_metadata.get("end_time"),
                "tags": tags or [],
                "archived": False,
                "imported": True,
                "import_source": str(path.absolute()),
                "import_time": datetime.now().isoformat(),
            }

            # Add negotiator infos if present
            if original_metadata.get("negotiator_infos"):
                app_metadata["negotiator_infos"] = original_metadata["negotiator_infos"]

            # Create new CompletedRun with updated metadata
            imported_run = CompletedRun(
                history=run.history,
                history_type=run.history_type,
                agreement=run.agreement,
                scenario=run.scenario,
                agreement_stats=run.agreement_stats,
                config=run.config,
                outcome_stats=run.outcome_stats,
                metadata=app_metadata,  # All app data goes to metadata.yaml
            )

            # Ensure storage directory exists
            _ensure_dir(NEGOTIATIONS_DIR)

            # Save using CompletedRun.save() - metadata goes to metadata.yaml
            saved_path = imported_run.save(
                parent=NEGOTIATIONS_DIR,
                name=new_session_id,
                single_file=False,
                save_scenario=True,
                save_scenario_stats=False,
                save_agreement_stats=True,
                save_config=True,
                overwrite=True,
                warn_if_existing=False,
                storage_format="parquet",
            )

            # Load and return the session
            session_dir = saved_path if saved_path.is_dir() else saved_path.parent
            return NegotiationStorageService.load_from_path(session_dir)

        except Exception as e:
            print(f"Failed to import negotiation from {path}: {e}")
            import traceback

            traceback.print_exc()
            return None

    @staticmethod
    def delete_negotiation(session_id: str) -> bool:
        """Delete a saved negotiation."""
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        shutil.rmtree(session_dir)
        return True

    @staticmethod
    def clear_all_negotiations(include_archived: bool = False) -> int:
        """Delete all saved negotiations."""
        count = 0

        if NEGOTIATIONS_DIR.exists():
            for session_dir in NEGOTIATIONS_DIR.iterdir():
                if session_dir.is_dir():
                    shutil.rmtree(session_dir)
                    count += 1

        if include_archived and ARCHIVE_DIR.exists():
            for session_dir in ARCHIVE_DIR.iterdir():
                if session_dir.is_dir():
                    shutil.rmtree(session_dir)
                    count += 1

        return count
