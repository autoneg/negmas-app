"""Service for persisting negotiation sessions to disk using CompletedRun format."""

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
from .settings_service import SettingsService

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
    """Service for saving and loading completed negotiations using CompletedRun format."""

    @staticmethod
    def get_storage_dir() -> Path:
        """Get the negotiations storage directory."""
        return NEGOTIATIONS_DIR

    @staticmethod
    def get_session_dir(session_id: str) -> Path:
        """Get the directory for a specific session."""
        return NEGOTIATIONS_DIR / session_id

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

        This is the preferred method for saving negotiations as it uses the
        standard negmas CompletedRun format that can be loaded by any tool.

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
        source = opts.get("source", "full_trace")
        storage_format = opts.get("storage_format", "parquet")
        generate_previews = opts.get("generate_previews", True)

        # Extract scenario options with defaults
        scenario_opts = scenario_options or {}
        normalize = scenario_opts.get("normalize", False)
        ignore_discount = scenario_opts.get("ignore_discount", False)
        ignore_reserved = scenario_opts.get("ignore_reserved", False)

        # Build app-specific metadata to include in the CompletedRun
        app_metadata = {
            "app_version": "2.0",  # Indicates CompletedRun format
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
            "normalize": normalize,
            "ignore_discount": ignore_discount,
            "ignore_reserved": ignore_reserved,
        }

        # Add negotiator infos with colors
        if session.negotiator_infos:
            app_metadata["negotiator_infos"] = [
                asdict(info) for info in session.negotiator_infos
            ]

        # Add negotiator configs if provided
        if negotiator_configs:
            app_metadata["negotiator_configs"] = [asdict(c) for c in negotiator_configs]

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
            source=source,
            metadata=app_metadata,
            overwrite=True,
            warn_if_existing=False,
            storage_format=storage_format,
        )

        # For single-file saves, we need to create a directory wrapper to store
        # app metadata and previews alongside the trace file
        if single_file:
            # Move the trace file into a directory
            trace_file = saved_path
            session_dir = NEGOTIATIONS_DIR / session.id
            _ensure_dir(session_dir)
            new_trace_path = session_dir / trace_file.name
            if trace_file != new_trace_path:
                shutil.move(str(trace_file), str(new_trace_path))
            saved_path = session_dir

        # Save app-specific metadata as separate file (for backward compatibility and easy access)
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
        """Save a completed negotiation to disk (legacy method without mechanism).

        This method creates a CompletedRun-compatible structure from session data.
        When possible, use save_negotiation_from_mechanism() instead.

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
        single_file = opts.get("single_file", False)
        storage_format = opts.get("storage_format", "parquet")
        generate_previews = opts.get("generate_previews", True)

        session_dir = NegotiationStorageService.get_session_dir(session.id)
        _ensure_dir(session_dir)

        # Extract scenario options with defaults
        scenario_opts = scenario_options or {}
        normalize = scenario_opts.get("normalize", False)
        ignore_discount = scenario_opts.get("ignore_discount", False)
        ignore_reserved = scenario_opts.get("ignore_reserved", False)

        # Build app metadata (this will be saved as metadata.yaml in CompletedRun format)
        app_metadata = {
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
            "normalize": normalize,
            "ignore_discount": ignore_discount,
            "ignore_reserved": ignore_reserved,
        }

        # Add negotiator infos
        if session.negotiator_infos:
            app_metadata["negotiator_infos"] = [
                asdict(info) for info in session.negotiator_infos
            ]

        # Add negotiator configs if provided
        if negotiator_configs:
            app_metadata["negotiator_configs"] = [asdict(c) for c in negotiator_configs]

        # Save app metadata
        with open(session_dir / APP_METADATA_FILE, "w") as f:
            json.dump(app_metadata, f, indent=2)

        # Save run_info.yaml (CompletedRun format)
        run_info = {
            "history_type": "full_trace",
            "agreement": list(session.agreement) if session.agreement else None,
            "storage_format": storage_format,
        }
        import yaml

        with open(session_dir / "run_info.yaml", "w") as f:
            yaml.dump(run_info, f, default_flow_style=False)

        # Save outcome_stats.yaml
        outcome_stats = {
            "agreement": list(session.agreement) if session.agreement else None,
            "broken": session.end_reason == "broken",
            "timedout": session.end_reason in ("timeout", "timedout"),
            "utilities": session.final_utilities,
        }
        with open(session_dir / "outcome_stats.yaml", "w") as f:
            yaml.dump(outcome_stats, f, default_flow_style=False)

        # Save config.yaml
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
        with open(session_dir / "config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        # Save agreement_stats.yaml if available
        if session.optimality_stats:
            with open(session_dir / "agreement_stats.yaml", "w") as f:
                yaml.dump(session.optimality_stats, f, default_flow_style=False)

        # Save offers as trace file
        if session.offers:
            NegotiationStorageService._save_trace(
                session_dir, session.offers, session.issue_names, storage_format
            )

        # Generate preview images
        if generate_previews:
            try:
                NegotiationPreviewService.generate_all_previews(session, session_dir)
            except Exception as e:
                print(f"Warning: Failed to generate preview images: {e}")

        return session_dir

    @staticmethod
    def _save_trace(
        session_dir: Path,
        offers: list[OfferEvent],
        issue_names: list[str],
        storage_format: str = "parquet",
    ) -> None:
        """Save offers as a trace file in CompletedRun format."""
        import pandas as pd

        # Build trace data in full_trace format
        data: dict[str, list[Any]] = {
            "time": [],
            "relative_time": [],
            "step": [],
            "negotiator": [],
            "offer": [],
            "responses": [],
            "state": [],
            "text": [],
            "data": [],
        }

        for offer in offers:
            data["time"].append(0.0)  # Not tracked in our format
            data["relative_time"].append(offer.relative_time)
            data["step"].append(offer.step)
            data["negotiator"].append(offer.proposer)
            data["offer"].append(str(offer.offer) if offer.offer else None)
            data["responses"].append(str(offer.response) if offer.response else "{}")
            data["state"].append("continuing")
            data["text"].append(None)
            data["data"].append(None)

        df = pd.DataFrame(data)

        # Save in requested format
        if storage_format == "parquet":
            df.to_parquet(
                session_dir / "trace.parquet",
                engine="pyarrow",
                compression="snappy",
                index=False,
            )
        elif storage_format == "gzip":
            df.to_csv(session_dir / "trace.csv.gz", index=False, compression="gzip")
        else:
            df.to_csv(session_dir / "trace.csv", index=False)

    @staticmethod
    def load_negotiation(session_id: str) -> NegotiationSession | None:
        """Load a negotiation session from disk.

        Supports both old format (metadata.json) and new CompletedRun format.

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

        # Check for new CompletedRun format (has run_info.yaml or app_metadata.json)
        if (session_dir / "run_info.yaml").exists() or (
            session_dir / APP_METADATA_FILE
        ).exists():
            return NegotiationStorageService._load_completed_run_format(session_dir)

        # Fall back to old format (metadata.json)
        if (session_dir / "metadata.json").exists():
            return NegotiationStorageService._load_legacy_format(session_dir)

        return None

    @staticmethod
    def load_from_path(path: str | Path) -> NegotiationSession | None:
        """Load a negotiation from an arbitrary path (file or directory).

        This is useful for loading negotiations from tournaments or external sources.

        Args:
            path: Path to a negotiation file or directory.

        Returns:
            The loaded session, or None if loading failed.
        """
        path = Path(path)
        if not path.exists():
            return None

        # Generate a session ID from the path
        session_id = f"external-{path.stem}"

        try:
            # Use CompletedRun.load() for standard negmas format
            run = CompletedRun.load(
                path,
                load_scenario=True,
                load_scenario_stats=False,
                load_agreement_stats=True,
                load_config=True,
            )
            return NegotiationStorageService._session_from_completed_run(
                run, session_id, str(path)
            )
        except Exception as e:
            print(f"Failed to load negotiation from {path}: {e}")
            return None

    @staticmethod
    def _load_completed_run_format(session_dir: Path) -> NegotiationSession | None:
        """Load a negotiation saved in CompletedRun format."""
        try:
            # First try to load app metadata for app-specific fields
            app_metadata: dict[str, Any] = {}
            app_metadata_path = session_dir / APP_METADATA_FILE
            if app_metadata_path.exists():
                with open(app_metadata_path) as f:
                    app_metadata = json.load(f)

            # Use CompletedRun.load() for the standard negmas data
            run = CompletedRun.load(
                session_dir,
                load_scenario=True,
                load_scenario_stats=False,
                load_agreement_stats=True,
                load_config=True,
            )

            session_id = app_metadata.get("session_id", session_dir.name)
            return NegotiationStorageService._session_from_completed_run(
                run, session_id, str(session_dir), app_metadata
            )

        except Exception as e:
            print(f"Error loading CompletedRun format from {session_dir}: {e}")
            import traceback

            traceback.print_exc()
            return None

    @staticmethod
    def _session_from_completed_run(
        run: CompletedRun,
        session_id: str,
        source_path: str,
        app_metadata: dict[str, Any] | None = None,
    ) -> NegotiationSession:
        """Convert a CompletedRun to a NegotiationSession."""
        from ..models.session import SessionStatus

        app_metadata = app_metadata or run.metadata or {}
        config = run.config or {}
        outcome_stats = run.outcome_stats or {}

        # Extract negotiator info
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

        # Create session
        session = NegotiationSession(
            id=session_id,
            status=status,
            scenario_path=app_metadata.get("scenario_path", source_path),
            scenario_name=app_metadata.get("scenario_name", Path(source_path).stem),
            mechanism_type=config.get("mechanism_type", "SAOMechanism"),
            negotiator_names=negotiator_names,
            negotiator_types=negotiator_types,
            issue_names=issue_names,
            issue_values={},  # Not stored in CompletedRun
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

        # Load negotiator infos
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
        if run.scenario:
            session.outcome_space_data = (
                NegotiationStorageService._build_outcome_space_from_scenario(
                    run.scenario
                )
            )
        elif session.offers:
            # Fall back to building from offers
            session.outcome_space_data = (
                NegotiationStorageService._build_outcome_space_from_offers(
                    session.offers
                )
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
        """Parse CompletedRun history into OfferEvent objects."""
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
                # history type - skip complex state parsing
                continue

            # Parse offer
            offer_tuple = None
            offer_dict = {}

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
    def _build_outcome_space_from_scenario(scenario) -> OutcomeSpaceData | None:
        """Build outcome space data from a Scenario object."""
        try:
            # Calculate stats if needed
            if not hasattr(scenario, "_stats") or scenario._stats is None:
                scenario.calc_stats()

            stats = scenario._stats
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

            return OutcomeSpaceData(
                outcome_utilities=outcome_utilities,
                pareto_utilities=pareto_utilities,
                nash_point=nash_point,
                kalai_point=kalai_point,
                kalai_smorodinsky_point=ks_point,
                max_welfare_point=max_welfare_point,
                total_outcomes=len(outcome_utilities),
                sampled=len(outcome_utilities) >= MAX_OUTCOMES,
                sample_size=len(outcome_utilities),
            )
        except Exception:
            return None

    @staticmethod
    def _build_outcome_space_from_offers(offers: list[OfferEvent]) -> OutcomeSpaceData:
        """Build minimal outcome space data from offers for visualization."""
        if not offers:
            return OutcomeSpaceData(
                outcome_utilities=[],
                pareto_utilities=[],
                total_outcomes=0,
                sampled=False,
                sample_size=0,
            )

        # Extract unique outcomes and their utilities
        outcome_map = {}
        for offer in offers:
            if offer.offer and offer.utilities:
                outcome_key = offer.offer
                if outcome_key not in outcome_map:
                    outcome_map[outcome_key] = tuple(offer.utilities)

        outcome_utilities = list(outcome_map.values())

        # Simple Pareto frontier approximation
        pareto_utilities = []
        for utilities in outcome_utilities:
            is_pareto = True
            for other in outcome_utilities:
                if all(o >= u for o, u in zip(other, utilities)) and any(
                    o > u for o, u in zip(other, utilities)
                ):
                    is_pareto = False
                    break
            if is_pareto:
                pareto_utilities.append(utilities)

        return OutcomeSpaceData(
            outcome_utilities=outcome_utilities,
            pareto_utilities=pareto_utilities,
            total_outcomes=len(outcome_utilities),
            sampled=True,
            sample_size=len(outcome_utilities),
            nash_point=None,
            kalai_point=None,
            kalai_smorodinsky_point=None,
            max_welfare_point=None,
        )

    @staticmethod
    def _load_legacy_format(session_dir: Path) -> NegotiationSession | None:
        """Load a negotiation saved in the legacy format (metadata.json)."""
        try:
            with open(session_dir / "metadata.json") as f:
                metadata = json.load(f)

            from ..models.session import SessionStatus

            # Use scenario_path name as fallback if scenario_name is empty
            scenario_name = metadata.get("scenario_name", "")
            if not scenario_name:
                scenario_path = metadata.get("scenario_path", "")
                if scenario_path:
                    scenario_name = Path(scenario_path).name

            session = NegotiationSession(
                id=metadata["id"],
                status=SessionStatus(metadata.get("status", "completed")),
                scenario_path=metadata.get("scenario_path", ""),
                scenario_name=scenario_name,
                mechanism_type=metadata.get("mechanism_type", "SAOMechanism"),
                negotiator_names=metadata.get("negotiator_names", []),
                negotiator_types=metadata.get("negotiator_types", []),
                issue_names=metadata.get("issue_names", []),
                issue_values=metadata.get("issue_values", {}),
                n_steps=metadata.get("n_steps"),
                time_limit=metadata.get("time_limit"),
                start_time=_deserialize_datetime(metadata.get("start_time")),
                end_time=_deserialize_datetime(metadata.get("end_time")),
                current_step=metadata.get("current_step", 0),
                error=metadata.get("error"),
            )

            # Load negotiator infos
            for info_data in metadata.get("negotiator_infos", []):
                session.negotiator_infos.append(
                    SessionNegotiatorInfo(
                        name=info_data["name"],
                        type_name=info_data["type_name"],
                        index=info_data["index"],
                        color=info_data["color"],
                    )
                )

            # Load result
            result_path = session_dir / "result.json"
            if result_path.exists():
                with open(result_path) as f:
                    result = json.load(f)
                session.agreement = (
                    tuple(result["agreement"]) if result.get("agreement") else None
                )
                session.agreement_dict = result.get("agreement_dict")
                if (
                    session.agreement_dict is None
                    and session.agreement is not None
                    and session.issue_names
                ):
                    session.agreement_dict = dict(
                        zip(session.issue_names, session.agreement)
                    )
                session.final_utilities = result.get("final_utilities")
                session.end_reason = result.get("end_reason")
                session.optimality_stats = result.get("optimality_stats")

            # Load offers from parquet or CSV
            offers_parquet = session_dir / "offers.parquet"
            offers_csv = session_dir / "offers.csv"

            if offers_parquet.exists():
                session.offers = NegotiationStorageService._load_offers_parquet(
                    offers_parquet, session.issue_names
                )
            elif offers_csv.exists():
                session.offers = NegotiationStorageService._load_offers_csv(
                    offers_csv, session.issue_names
                )

            # Load outcome space data
            outcome_path = session_dir / "outcome_space.json"
            if outcome_path.exists():
                session.outcome_space_data = (
                    NegotiationStorageService._load_outcome_space(outcome_path)
                )
            elif session.offers:
                session.outcome_space_data = (
                    NegotiationStorageService._build_outcome_space_from_offers(
                        session.offers
                    )
                )

            return session

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error loading legacy format from {session_dir}: {e}")
            return None

    @staticmethod
    def _load_offers_parquet(path: Path, issue_names: list[str]) -> list[OfferEvent]:
        """Load offers from a parquet file."""
        import pandas as pd

        offers = []
        df = pd.read_parquet(path)

        for _, row in df.iterrows():
            offer_values = tuple(
                row[name] for name in issue_names if name in df.columns
            )
            utilities = []
            i = 0
            while f"utility_{i}" in df.columns:
                utilities.append(float(row[f"utility_{i}"]))
                i += 1

            offers.append(
                OfferEvent(
                    step=int(row["step"]),
                    proposer=str(row["proposer"]),
                    proposer_index=int(row["proposer_index"]),
                    offer=offer_values if offer_values else (),
                    offer_dict=dict(zip(issue_names, offer_values))
                    if offer_values
                    else {},
                    utilities=utilities,
                    timestamp=datetime.now(),
                    response=str(row["response"])
                    if row.get("response") is not None
                    and str(row.get("response")) not in ("", "nan")
                    else None,
                    relative_time=float(row["relative_time"]),
                )
            )

        return offers

    @staticmethod
    def _load_offers_csv(path: Path, issue_names: list[str]) -> list[OfferEvent]:
        """Load offers from a CSV file."""
        import csv

        offers = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                offer_values = tuple(row[name] for name in issue_names if name in row)
                utilities = []
                i = 0
                while f"utility_{i}" in row:
                    utilities.append(float(row[f"utility_{i}"]))
                    i += 1

                offers.append(
                    OfferEvent(
                        step=int(row["step"]),
                        proposer=str(row["proposer"]),
                        proposer_index=int(row["proposer_index"]),
                        offer=offer_values if offer_values else (),
                        offer_dict=dict(zip(issue_names, offer_values))
                        if offer_values
                        else {},
                        utilities=utilities,
                        timestamp=datetime.now(),
                        response=str(row["response"]) if row.get("response") else None,
                        relative_time=float(row["relative_time"]),
                    )
                )

        return offers

    @staticmethod
    def _load_outcome_space(path: Path) -> OutcomeSpaceData:
        """Load outcome space data from JSON."""
        with open(path) as f:
            data = json.load(f)

        outcome_space = OutcomeSpaceData(
            outcome_utilities=[tuple(u) for u in data.get("outcome_utilities", [])],
            pareto_utilities=[tuple(u) for u in data.get("pareto_utilities", [])],
            total_outcomes=data.get("total_outcomes", 0),
            sampled=data.get("sampled", False),
            sample_size=data.get("sample_size", 0),
        )

        for point_name in [
            "nash_point",
            "kalai_point",
            "kalai_smorodinsky_point",
            "max_welfare_point",
        ]:
            point_data = data.get(point_name)
            if point_data:
                point = AnalysisPoint(
                    name=point_data["name"],
                    utilities=point_data["utilities"],
                    outcome=(
                        tuple(point_data["outcome"])
                        if point_data.get("outcome")
                        else None
                    ),
                    outcome_dict=point_data.get("outcome_dict"),
                )
                setattr(outcome_space, point_name, point)

        return outcome_space

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

        for session_dir in directory.iterdir():
            if not session_dir.is_dir():
                continue

            # Try new format first (app_metadata.json)
            app_metadata_path = session_dir / APP_METADATA_FILE
            metadata_path = session_dir / "metadata.json"
            run_info_path = session_dir / "run_info.yaml"

            metadata = None

            if app_metadata_path.exists():
                try:
                    with open(app_metadata_path) as f:
                        metadata = json.load(f)
                except (json.JSONDecodeError, KeyError):
                    pass

            if metadata is None and metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                except (json.JSONDecodeError, KeyError):
                    pass

            # If no metadata but has run_info.yaml, it's a CompletedRun without app metadata
            if metadata is None and run_info_path.exists():
                metadata = {
                    "id": session_dir.name,
                    "scenario_name": session_dir.name,
                }

            if metadata is None:
                continue

            try:
                # Build summary
                scenario_name = metadata.get("scenario_name")
                if not scenario_name:
                    scenario_path = metadata.get("scenario_path", "")
                    if scenario_path:
                        scenario_name = Path(scenario_path).name
                    else:
                        scenario_name = "Unknown"

                summary = {
                    "id": metadata.get("id", session_dir.name),
                    "status": metadata.get("status", "completed"),
                    "scenario_name": scenario_name,
                    "scenario_path": metadata.get("scenario_path"),
                    "mechanism_type": metadata.get("mechanism_type"),
                    "negotiator_names": metadata.get("negotiator_names", []),
                    "negotiator_types": metadata.get("negotiator_types", []),
                    "start_time": metadata.get("start_time"),
                    "end_time": metadata.get("end_time"),
                    "n_steps": metadata.get("n_steps"),
                    "tags": metadata.get("tags", []),
                    "archived": archived,
                    "created_at": metadata.get("start_time"),
                    "completed_at": metadata.get("end_time"),
                }

                # Load result info if available
                result_path = session_dir / "result.json"
                outcome_stats_path = session_dir / "outcome_stats.yaml"

                if result_path.exists():
                    with open(result_path) as f:
                        result = json.load(f)
                    summary["agreement"] = result.get("agreement")
                    summary["agreement_dict"] = result.get("agreement_dict")
                    summary["has_agreement"] = result.get("agreement") is not None
                    summary["end_reason"] = result.get("end_reason")
                    summary["final_utilities"] = result.get("final_utilities")
                    summary["n_offers"] = result.get("n_offers")
                    summary["duration_seconds"] = result.get("duration_seconds")
                elif outcome_stats_path.exists():
                    import yaml

                    with open(outcome_stats_path) as f:
                        outcome_stats = yaml.safe_load(f)
                    summary["agreement"] = outcome_stats.get("agreement")
                    summary["has_agreement"] = (
                        outcome_stats.get("agreement") is not None
                    )
                    summary["final_utilities"] = outcome_stats.get("utilities")

                negotiations.append(summary)

            except (json.JSONDecodeError, KeyError):
                continue

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

        # Update metadata to mark as archived
        for metadata_file in [APP_METADATA_FILE, "metadata.json"]:
            metadata_path = archive_dest / metadata_file
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                metadata["archived"] = True
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                break

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

        # Update metadata
        for metadata_file in [APP_METADATA_FILE, "metadata.json"]:
            metadata_path = dest / metadata_file
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                metadata["archived"] = False
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                break

        return True

    @staticmethod
    def update_tags(session_id: str, tags: list[str]) -> bool:
        """Update tags for a negotiation."""
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        for metadata_file in [APP_METADATA_FILE, "metadata.json"]:
            metadata_path = session_dir / metadata_file
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

        for metadata_file in [APP_METADATA_FILE, "metadata.json"]:
            metadata_path = session_dir / metadata_file
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

        for metadata_file in [APP_METADATA_FILE, "metadata.json"]:
            metadata_path = session_dir / metadata_file
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
        all_tags = set()

        for directory in [NEGOTIATIONS_DIR, ARCHIVE_DIR]:
            if not directory.exists():
                continue

            for session_dir in directory.iterdir():
                if not session_dir.is_dir():
                    continue

                for metadata_file in [APP_METADATA_FILE, "metadata.json"]:
                    metadata_path = session_dir / metadata_file
                    if metadata_path.exists():
                        try:
                            with open(metadata_path) as f:
                                metadata = json.load(f)
                            all_tags.update(metadata.get("tags", []))
                        except (json.JSONDecodeError, KeyError):
                            pass
                        break

        return sorted(all_tags)

    @staticmethod
    def import_negotiation(
        path: str | Path,
        tags: list[str] | None = None,
    ) -> NegotiationSession | None:
        """Import a negotiation from an external path into the app's storage.

        This loads the negotiation using load_from_path(), assigns a new session ID,
        adds import metadata, and saves it to ~/negmas/app/negotiations.

        Args:
            path: Path to a negotiation file or directory.
            tags: Optional tags to add to the imported negotiation.

        Returns:
            The imported session with new ID, or None if import failed.
        """
        path = Path(path)
        if not path.exists():
            return None

        # Load the negotiation from external path
        session = NegotiationStorageService.load_from_path(path)
        if session is None:
            return None

        # Generate a new session ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = path.stem
        new_session_id = f"imported_{original_name}_{timestamp}"

        # Update session with new ID
        old_id = session.id
        session.id = new_session_id

        # Ensure storage directory exists
        _ensure_dir(NEGOTIATIONS_DIR)
        session_dir = NEGOTIATIONS_DIR / new_session_id

        # Save the session using the existing save method
        # First, prepare app metadata with import info
        app_metadata = {
            "app_version": "2.0",
            "session_id": new_session_id,
            "scenario_path": session.scenario_path,
            "scenario_name": session.scenario_name,
            "negotiator_names": session.negotiator_names,
            "negotiator_types": session.negotiator_types,
            "issue_names": session.issue_names,
            "start_time": _serialize_datetime(session.start_time),
            "end_time": _serialize_datetime(session.end_time),
            "tags": tags or [],
            "archived": False,
            # Import-specific metadata
            "imported": True,
            "import_source": str(path.absolute()),
            "import_time": datetime.now().isoformat(),
            "original_session_id": old_id,
        }

        # Add negotiator infos
        if session.negotiator_infos:
            app_metadata["negotiator_infos"] = [
                asdict(info) for info in session.negotiator_infos
            ]

        # Create the session directory
        _ensure_dir(session_dir)

        # Save app metadata
        with open(session_dir / APP_METADATA_FILE, "w") as f:
            json.dump(app_metadata, f, indent=2)

        # Save run_info.yaml
        import yaml

        run_info = {
            "history_type": "full_trace",
            "agreement": list(session.agreement) if session.agreement else None,
            "storage_format": "parquet",
        }
        with open(session_dir / "run_info.yaml", "w") as f:
            yaml.dump(run_info, f, default_flow_style=False)

        # Save outcome_stats.yaml
        outcome_stats = {
            "agreement": list(session.agreement) if session.agreement else None,
            "broken": session.end_reason == "broken",
            "timedout": session.end_reason in ("timeout", "timedout"),
            "utilities": session.final_utilities,
        }
        with open(session_dir / "outcome_stats.yaml", "w") as f:
            yaml.dump(outcome_stats, f, default_flow_style=False)

        # Save config.yaml
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
        with open(session_dir / "config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        # Save agreement_stats.yaml if available
        if session.optimality_stats:
            with open(session_dir / "agreement_stats.yaml", "w") as f:
                yaml.dump(session.optimality_stats, f, default_flow_style=False)

        # Save offers as trace file
        if session.offers:
            NegotiationStorageService._save_trace(
                session_dir, session.offers, session.issue_names, "parquet"
            )

        # Generate preview images
        try:
            NegotiationPreviewService.generate_all_previews(session, session_dir)
        except Exception as e:
            print(f"Warning: Failed to generate preview images: {e}")

        return session

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
