"""Service for persisting negotiation sessions to disk using CompletedRun format.

All saving and loading is done through negmas CompletedRun.save() and CompletedRun.load().
This ensures compatibility with all formats supported by negmas.
"""

import json
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

# Metadata filename for app-specific data
APP_METADATA_FILE = "app_metadata.json"


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
    def _build_app_metadata(
        session: NegotiationSession,
        negotiator_configs: list[NegotiatorConfig] | None = None,
        tags: list[str] | None = None,
        scenario_options: dict | None = None,
    ) -> dict[str, Any]:
        """Build app-specific metadata dict to include in CompletedRun."""
        scenario_opts = scenario_options or {}

        app_metadata: dict[str, Any] = {
            "app_version": "2.0",
            "session_id": session.id,
            "scenario_path": session.scenario_path,
            "scenario_name": session.scenario_name,
            "negotiator_names": session.negotiator_names,
            "negotiator_types": session.negotiator_types,
            "issue_names": session.issue_names,
            "start_time": _serialize_datetime(session.start_time),
            "end_time": _serialize_datetime(session.end_time),
            "tags": tags or [],
            "archived": False,
            "normalize": scenario_opts.get("normalize", False),
            "ignore_discount": scenario_opts.get("ignore_discount", False),
            "ignore_reserved": scenario_opts.get("ignore_reserved", False),
        }

        if session.negotiator_infos:
            app_metadata["negotiator_infos"] = [
                asdict(info) for info in session.negotiator_infos
            ]

        if negotiator_configs:
            app_metadata["negotiator_configs"] = [asdict(c) for c in negotiator_configs]

        return app_metadata

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

        # Build app-specific metadata
        app_metadata = NegotiationStorageService._build_app_metadata(
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
            metadata=app_metadata,
            overwrite=True,
            warn_if_existing=False,
            storage_format=storage_format,
        )

        # For single-file saves, wrap in a directory for app metadata and previews
        if single_file:
            trace_file = saved_path
            session_dir = NEGOTIATIONS_DIR / session.id
            _ensure_dir(session_dir)
            new_trace_path = session_dir / trace_file.name
            if trace_file != new_trace_path:
                shutil.move(str(trace_file), str(new_trace_path))
            saved_path = session_dir

        # Save app-specific metadata as separate file for easy access
        session_dir = saved_path if saved_path.is_dir() else saved_path.parent
        with open(session_dir / APP_METADATA_FILE, "w") as f:
            json.dump(app_metadata, f, indent=2)

        # Generate preview images if requested
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

        # Build app-specific metadata
        app_metadata = NegotiationStorageService._build_app_metadata(
            session, negotiator_configs, tags, scenario_options
        )

        # Build history in full_trace format from session offers
        history = []
        for offer in session.offers:
            history.append(
                {
                    "time": 0.0,
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
            metadata=app_metadata,
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

        # Save app-specific metadata as separate file for easy access
        session_dir = saved_path if saved_path.is_dir() else saved_path.parent
        with open(session_dir / APP_METADATA_FILE, "w") as f:
            json.dump(app_metadata, f, indent=2)

        # Generate preview images
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

        Args:
            path: Path to a negotiation file or directory.

        Returns:
            The loaded session, or None if loading failed.
        """
        path = Path(path)
        if not path.exists():
            return None

        try:
            # Load app metadata if available (for app-specific fields like colors, tags)
            app_metadata: dict[str, Any] = {}
            if path.is_dir():
                app_metadata_path = path / APP_METADATA_FILE
                if app_metadata_path.exists():
                    with open(app_metadata_path) as f:
                        app_metadata = json.load(f)

            # Use CompletedRun.load() for all formats
            run = CompletedRun.load(
                path,
                load_scenario=True,
                load_scenario_stats=False,
                load_agreement_stats=True,
                load_config=True,
            )

            session_id = app_metadata.get("session_id", path.stem)
            return NegotiationStorageService._session_from_completed_run(
                run, session_id, str(path), app_metadata
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
        app_metadata: dict[str, Any] | None = None,
    ) -> NegotiationSession:
        """Convert a CompletedRun to a NegotiationSession."""
        from ..models.session import SessionStatus

        app_metadata = app_metadata or run.metadata or {}
        config = run.config or {}
        outcome_stats = run.outcome_stats or {}

        # Extract negotiator info - prefer app_metadata, fall back to config
        negotiator_names = app_metadata.get(
            "negotiator_names", config.get("negotiator_names", [])
        )
        negotiator_types = app_metadata.get(
            "negotiator_types", config.get("negotiator_types", [])
        )
        issue_names = app_metadata.get("issue_names", [])

        # Try to get issue names from scenario if not in metadata
        if not issue_names and run.scenario and run.scenario.outcome_space:
            try:
                issues = run.scenario.outcome_space.issues
                if isinstance(issues, (list, tuple)):
                    issue_names = [
                        getattr(issue, "name", f"issue_{i}")
                        for i, issue in enumerate(issues)
                    ]
            except Exception:
                pass

        # Determine status
        status_str = app_metadata.get("status", "completed")
        try:
            status = SessionStatus(status_str)
        except ValueError:
            status = SessionStatus.COMPLETED

        # Determine end reason
        end_reason = None
        if outcome_stats.get("timedout") or config.get("timedout"):
            end_reason = "timedout"
        elif outcome_stats.get("broken") or config.get("broken"):
            end_reason = "broken"
        elif run.agreement is not None:
            end_reason = "agreement"
        else:
            end_reason = "no_agreement"

        # Get scenario path - prefer app_metadata, then run.metadata, then source_path
        scenario_path_str = (
            app_metadata.get("scenario_path")
            or (run.metadata.get("scenario_path") if run.metadata else None)
            or source_path
        )
        scenario_name_str = (
            app_metadata.get("scenario_name") or Path(scenario_path_str).stem
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
            start_time=_deserialize_datetime(app_metadata.get("start_time")),
            end_time=_deserialize_datetime(app_metadata.get("end_time")),
            current_step=config.get("final_step", 0),
            error=None,
        )

        # Set agreement
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

        # Set optimality stats
        if run.agreement_stats:
            session.optimality_stats = {
                "pareto_optimality": run.agreement_stats.pareto_optimality,
                "nash_optimality": run.agreement_stats.nash_optimality,
                "kalai_optimality": run.agreement_stats.kalai_optimality,
                "max_welfare_optimality": run.agreement_stats.max_welfare_optimality,
                "ks_optimality": run.agreement_stats.ks_optimality,
            }

        # Load negotiator infos from app_metadata
        for info_data in app_metadata.get("negotiator_infos", []):
            session.negotiator_infos.append(
                SessionNegotiatorInfo(
                    name=info_data["name"],
                    type_name=info_data["type_name"],
                    index=info_data["index"],
                    color=info_data["color"],
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

        # Build outcome space data from scenario if available
        scenario = run.scenario

        # If scenario not in CompletedRun, try to load from scenario_path
        # Check app_metadata first, then run.metadata (negmas native metadata.yaml)
        if scenario is None:
            scenario_path = None
            if app_metadata:
                scenario_path = app_metadata.get("scenario_path")
            if not scenario_path and run.metadata:
                scenario_path = run.metadata.get("scenario_path")

            if scenario_path:
                try:
                    from negmas import Scenario

                    scenario_path_obj = Path(scenario_path)
                    if scenario_path_obj.exists():
                        scenario = Scenario.load(  # type: ignore[attr-defined]
                            scenario_path_obj,
                            load_stats=True,
                            load_info=True,
                        )
                except Exception as e:
                    print(f"Failed to load scenario from {scenario_path}: {e}")

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

        Handles all history types: full_trace, full_trace_with_utils, extended_trace, trace.
        """
        offers: list[OfferEvent] = []
        name_to_idx = {name: i for i, name in enumerate(negotiator_names)}

        for item in history:
            # Extract fields based on history type
            if history_type in ("full_trace", "full_trace_with_utils"):
                if isinstance(item, dict):
                    step = item.get("step", 0)
                    relative_time = item.get("relative_time", 0.0)
                    proposer = item.get("negotiator", "")
                    offer_raw = item.get("offer")
                    response = item.get("responses", "")
                else:
                    # Named tuple
                    step = item[2] if len(item) > 2 else 0
                    relative_time = item[1] if len(item) > 1 else 0.0
                    proposer = item[3] if len(item) > 3 else ""
                    offer_raw = item[4] if len(item) > 4 else None
                    response = item[5] if len(item) > 5 else ""

            elif history_type == "extended_trace":
                if isinstance(item, dict):
                    step = item.get("step", 0)
                    proposer = item.get("negotiator", "")
                    offer_raw = item.get("offer")
                else:
                    step = item[0] if len(item) > 0 else 0
                    proposer = item[1] if len(item) > 1 else ""
                    offer_raw = item[2] if len(item) > 2 else None
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
                relative_time = 0.0
                response = ""

            else:
                # history type (raw states) - skip complex state parsing
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

            # Calculate utilities
            utilities: list[float] = []
            if ufuns and offer_tuple:
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
        """List negotiations from a specific directory."""
        negotiations = []

        for session_path in directory.iterdir():
            if not session_path.is_dir() and not session_path.suffix in (
                ".csv",
                ".parquet",
            ):
                continue

            # Try to load app metadata for summary info
            app_metadata: dict[str, Any] = {}
            if session_path.is_dir():
                app_metadata_path = session_path / APP_METADATA_FILE
                if app_metadata_path.exists():
                    try:
                        with open(app_metadata_path) as f:
                            app_metadata = json.load(f)
                    except (json.JSONDecodeError, KeyError):
                        pass

            # Try to load basic info from CompletedRun
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

                # Merge with app_metadata (app_metadata takes precedence)
                scenario_name = app_metadata.get("scenario_name")
                if not scenario_name:
                    scenario_path = app_metadata.get("scenario_path", "")
                    if scenario_path:
                        scenario_name = Path(scenario_path).name
                    else:
                        scenario_name = session_path.stem

                summary = {
                    "id": app_metadata.get("id", session_path.stem),
                    "status": app_metadata.get("status", "completed"),
                    "scenario_name": scenario_name,
                    "scenario_path": app_metadata.get("scenario_path"),
                    "mechanism_type": config.get("mechanism_type"),
                    "negotiator_names": app_metadata.get(
                        "negotiator_names", config.get("negotiator_names", [])
                    ),
                    "negotiator_types": app_metadata.get(
                        "negotiator_types", config.get("negotiator_types", [])
                    ),
                    "start_time": app_metadata.get("start_time"),
                    "end_time": app_metadata.get("end_time"),
                    "n_steps": config.get("n_steps"),
                    "tags": app_metadata.get("tags", []),
                    "archived": archived,
                    "created_at": app_metadata.get("start_time"),
                    "completed_at": app_metadata.get("end_time"),
                    "agreement": outcome_stats.get("agreement"),
                    "has_agreement": outcome_stats.get("agreement") is not None,
                    "final_utilities": outcome_stats.get("utilities"),
                }

                negotiations.append(summary)

            except Exception:
                # If CompletedRun.load fails, try just using app_metadata
                if app_metadata:
                    summary = {
                        "id": app_metadata.get("id", session_path.stem),
                        "status": app_metadata.get("status", "completed"),
                        "scenario_name": app_metadata.get(
                            "scenario_name", session_path.stem
                        ),
                        "scenario_path": app_metadata.get("scenario_path"),
                        "negotiator_names": app_metadata.get("negotiator_names", []),
                        "negotiator_types": app_metadata.get("negotiator_types", []),
                        "start_time": app_metadata.get("start_time"),
                        "end_time": app_metadata.get("end_time"),
                        "tags": app_metadata.get("tags", []),
                        "archived": archived,
                    }
                    negotiations.append(summary)

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

        # Update app metadata to mark as archived
        metadata_path = archive_dest / APP_METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            metadata["archived"] = True
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

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

        # Update app metadata
        metadata_path = dest / APP_METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            metadata["archived"] = False
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        return True

    @staticmethod
    def update_tags(session_id: str, tags: list[str]) -> bool:
        """Update tags for a negotiation."""
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / APP_METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            metadata["tags"] = tags
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            return True

        return False

    @staticmethod
    def add_tag(session_id: str, tag: str) -> bool:
        """Add a tag to a negotiation."""
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / APP_METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            tags = metadata.get("tags", [])
            if tag not in tags:
                tags.append(tag)
                metadata["tags"] = tags
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
            return True

        return False

    @staticmethod
    def remove_tag(session_id: str, tag: str) -> bool:
        """Remove a tag from a negotiation."""
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / APP_METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            tags = metadata.get("tags", [])
            if tag in tags:
                tags.remove(tag)
                metadata["tags"] = tags
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
            return True

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

                metadata_path = session_dir / APP_METADATA_FILE
                if metadata_path.exists():
                    try:
                        with open(metadata_path) as f:
                            metadata = json.load(f)
                        all_tags.update(metadata.get("tags", []))
                    except (json.JSONDecodeError, KeyError):
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
                metadata=app_metadata,
            )

            # Ensure storage directory exists
            _ensure_dir(NEGOTIATIONS_DIR)

            # Save using CompletedRun.save()
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

            # Save app metadata as separate file for easy access
            session_dir = saved_path if saved_path.is_dir() else saved_path.parent
            with open(session_dir / APP_METADATA_FILE, "w") as f:
                json.dump(app_metadata, f, indent=2)

            # Load and return the session
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
