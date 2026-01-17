"""Service for persisting negotiation sessions to disk."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from negmas import Scenario
from negmas.sao import SAOMechanism

from ..models.session import (
    NegotiationSession,
    OfferEvent,
    OutcomeSpaceData,
    AnalysisPoint,
    SessionNegotiatorInfo,
)
from ..models.negotiator import NegotiatorConfig

if TYPE_CHECKING:
    from .negotiation_loader import NegotiationData

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
    """Service for saving and loading completed negotiations."""

    @staticmethod
    def get_storage_dir() -> Path:
        """Get the negotiations storage directory."""
        return NEGOTIATIONS_DIR

    @staticmethod
    def get_session_dir(session_id: str) -> Path:
        """Get the directory for a specific session."""
        return NEGOTIATIONS_DIR / session_id

    @staticmethod
    def save_negotiation(
        session: NegotiationSession,
        negotiator_configs: list[NegotiatorConfig] | None = None,
        tags: list[str] | None = None,
    ) -> Path:
        """Save a completed negotiation to disk.

        Args:
            session: The negotiation session to save.
            negotiator_configs: Original negotiator configurations (optional).
            tags: Optional list of tags for categorization.

        Returns:
            Path to the session directory.
        """
        session_dir = NegotiationStorageService.get_session_dir(session.id)
        _ensure_dir(session_dir)

        # Save metadata
        metadata = {
            "id": session.id,
            "status": session.status.value,
            "scenario_path": session.scenario_path,
            "scenario_name": session.scenario_name,
            "mechanism_type": session.mechanism_type,
            "negotiator_names": session.negotiator_names,
            "negotiator_types": session.negotiator_types,
            "issue_names": session.issue_names,
            "issue_values": session.issue_values,
            "n_steps": session.n_steps,
            "time_limit": session.time_limit,
            "start_time": _serialize_datetime(session.start_time),
            "end_time": _serialize_datetime(session.end_time),
            "current_step": session.current_step,
            "error": session.error,
            "tags": tags or [],
            "archived": False,
        }

        # Add negotiator infos
        if session.negotiator_infos:
            metadata["negotiator_infos"] = [
                asdict(info) for info in session.negotiator_infos
            ]

        # Add negotiator configs if provided
        if negotiator_configs:
            metadata["negotiator_configs"] = [asdict(c) for c in negotiator_configs]

        with open(session_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Save result
        result = {
            "agreement": list(session.agreement) if session.agreement else None,
            "agreement_dict": session.agreement_dict,
            "final_utilities": session.final_utilities,
            "end_reason": session.end_reason,
            "total_steps": session.current_step,
            "n_offers": len(session.offers),
            "duration_seconds": session.duration_seconds(),
            "optimality_stats": session.optimality_stats,
        }

        with open(session_dir / "result.json", "w") as f:
            json.dump(result, f, indent=2)

        # Save offers as CSV for easy analysis
        if session.offers:
            NegotiationStorageService._save_offers_csv(
                session_dir / "offers.csv", session.offers, session.issue_names
            )

        # Also save offers as JSON for full fidelity
        offers_data = []
        for offer in session.offers:
            offer_data = {
                "step": offer.step,
                "proposer": offer.proposer,
                "proposer_index": offer.proposer_index,
                "offer": list(offer.offer) if offer.offer else None,
                "offer_dict": offer.offer_dict,
                "utilities": offer.utilities,
                "timestamp": _serialize_datetime(offer.timestamp),
                "response": offer.response,
                "relative_time": offer.relative_time,
            }
            offers_data.append(offer_data)

        with open(session_dir / "offers.json", "w") as f:
            json.dump(offers_data, f, indent=2)

        # Save outcome space data if present
        if session.outcome_space_data:
            NegotiationStorageService._save_outcome_space(
                session_dir / "outcome_space.json", session.outcome_space_data
            )

        return session_dir

    @staticmethod
    def save_from_mechanism(
        mechanism: SAOMechanism,
        scenario: Scenario | None = None,
        session_id: str | None = None,
        metadata: dict | None = None,
    ) -> Path:
        """Save a completed negotiation using negmas CompletedRun format.

        This is the preferred method for saving negotiations as it uses
        the standardized negmas format that includes all mechanism config.

        Args:
            mechanism: The completed SAOMechanism.
            scenario: The scenario used (optional, saved if provided).
            session_id: Custom session ID (defaults to mechanism ID).
            metadata: Additional metadata to include.

        Returns:
            Path to the saved negotiation directory.
        """
        session_id = session_id or mechanism.id[:8]
        _ensure_dir(NEGOTIATIONS_DIR)

        # Build metadata with display-friendly info
        save_metadata = metadata or {}
        save_metadata["session_id"] = session_id
        save_metadata["saved_at"] = datetime.now().isoformat()

        # Save issue names from scenario for proper display
        if scenario and scenario.outcome_space:
            try:
                # Try dict-style access first
                save_metadata["issue_names"] = list(
                    scenario.outcome_space.issues.keys()
                )
            except (AttributeError, TypeError):
                try:
                    # Try tuple-style (issues is a tuple of Issue objects)
                    issues = scenario.outcome_space.issues
                    if isinstance(issues, (list, tuple)):
                        save_metadata["issue_names"] = [
                            getattr(issue, "name", f"issue_{i}")
                            for i, issue in enumerate(issues)
                        ]
                except Exception:
                    pass

            # Save scenario name
            if hasattr(scenario, "name") and scenario.name:
                save_metadata["scenario_name"] = scenario.name

        # If scenario provided, set it on the mechanism for saving
        # The mechanism uses its negotiators' ufuns to get the scenario
        save_scenario = scenario is not None

        # Save using mechanism's built-in save method
        saved_path = mechanism.save(  # type: ignore[attr-defined]
            parent=NEGOTIATIONS_DIR,
            name=session_id,
            save_scenario=save_scenario,
            save_scenario_stats=save_scenario,
            save_agreement_stats=True,
            save_config=True,
            source="full_trace",
            metadata=save_metadata,
        )

        return Path(saved_path)

    @staticmethod
    def _save_offers_csv(
        path: Path, offers: list[OfferEvent], issue_names: list[str]
    ) -> None:
        """Save offers to CSV format."""
        with open(path, "w", newline="") as f:
            # Build header: step, proposer, proposer_index, issue values..., utilities..., response, relative_time
            n_negotiators = len(offers[0].utilities) if offers else 0
            header = ["step", "proposer", "proposer_index"]
            header.extend(issue_names)
            header.extend([f"utility_{i}" for i in range(n_negotiators)])
            header.extend(["response", "relative_time"])

            writer = csv.writer(f)
            writer.writerow(header)

            for offer in offers:
                row = [offer.step, offer.proposer, offer.proposer_index]
                # Add offer values
                if offer.offer:
                    row.extend(list(offer.offer))
                else:
                    row.extend([""] * len(issue_names))
                # Add utilities
                row.extend(offer.utilities)
                row.extend([offer.response or "", offer.relative_time])
                writer.writerow(row)

    @staticmethod
    def _save_outcome_space(path: Path, data: OutcomeSpaceData) -> None:
        """Save outcome space data to JSON."""
        outcome_data = {
            "outcome_utilities": [list(u) for u in data.outcome_utilities],
            "pareto_utilities": [list(u) for u in data.pareto_utilities],
            "total_outcomes": data.total_outcomes,
            "sampled": data.sampled,
            "sample_size": data.sample_size,
        }

        # Add special points
        for point_name in [
            "nash_point",
            "kalai_point",
            "kalai_smorodinsky_point",
            "max_welfare_point",
        ]:
            point: AnalysisPoint | None = getattr(data, point_name)
            if point:
                outcome_data[point_name] = {
                    "name": point.name,
                    "utilities": point.utilities,
                    "outcome": list(point.outcome) if point.outcome else None,
                    "outcome_dict": point.outcome_dict,
                }

        with open(path, "w") as f:
            json.dump(outcome_data, f, indent=2)

    @staticmethod
    def load_negotiation(session_id: str) -> NegotiationSession | None:
        """Load a negotiation session from disk.

        Args:
            session_id: The session ID to load.

        Returns:
            The loaded session, or None if not found.
        """
        session_dir = NegotiationStorageService.get_session_dir(session_id)
        if not session_dir.exists():
            return None

        metadata_path = session_dir / "metadata.json"
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            # Create session from metadata
            from ..models.session import SessionStatus

            session = NegotiationSession(
                id=metadata["id"],
                status=SessionStatus(metadata.get("status", "completed")),
                scenario_path=metadata.get("scenario_path", ""),
                scenario_name=metadata.get("scenario_name", ""),
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
                session.final_utilities = result.get("final_utilities")
                session.end_reason = result.get("end_reason")
                session.optimality_stats = result.get("optimality_stats")

            # Load offers from JSON (full fidelity)
            offers_json_path = session_dir / "offers.json"
            if offers_json_path.exists():
                with open(offers_json_path) as f:
                    offers_data = json.load(f)
                for offer_data in offers_data:
                    session.offers.append(
                        OfferEvent(
                            step=offer_data["step"],
                            proposer=offer_data["proposer"],
                            proposer_index=offer_data["proposer_index"],
                            offer=(
                                tuple(offer_data["offer"])
                                if offer_data.get("offer")
                                else ()
                            ),
                            offer_dict=offer_data.get("offer_dict", {}),
                            utilities=offer_data.get("utilities", []),
                            timestamp=_deserialize_datetime(offer_data.get("timestamp"))
                            or datetime.now(),
                            response=offer_data.get("response"),
                            relative_time=offer_data.get("relative_time", 0.0),
                        )
                    )

            # Load outcome space data
            outcome_path = session_dir / "outcome_space.json"
            if outcome_path.exists():
                session.outcome_space_data = (
                    NegotiationStorageService._load_outcome_space(outcome_path)
                )

            return session

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Log error but return None
            print(f"Error loading negotiation {session_id}: {e}")
            return None

    @staticmethod
    def load_as_negotiation_data(session_id: str) -> "NegotiationData | None":
        """Load a negotiation using the unified NegotiationLoader.

        This method tries CompletedRun format first, then falls back to
        the legacy custom format.

        Args:
            session_id: The session ID to load.

        Returns:
            NegotiationData ready for UI display, or None if not found.
        """
        from .negotiation_loader import NegotiationLoader

        session_dir = NegotiationStorageService.get_session_dir(session_id)
        if not session_dir.exists():
            # Try archive
            session_dir = ARCHIVE_DIR / session_id
            if not session_dir.exists():
                return None

        # Check if this is CompletedRun format (has config.yaml/json or trace.csv/history.csv/parquet)
        config_json = session_dir / "config.json"
        config_yaml = session_dir / "config.yaml"
        trace_csv = session_dir / "trace.csv"
        history_csv = session_dir / "history.csv"
        history_parquet = session_dir / "history.parquet"

        if (
            config_json.exists()
            or config_yaml.exists()
            or trace_csv.exists()
            or history_csv.exists()
            or history_parquet.exists()
        ):
            # Use NegotiationLoader for CompletedRun format
            try:
                return NegotiationLoader.from_file(
                    session_dir,
                    negotiation_id=session_id,
                    load_scenario_stats=True,
                )
            except Exception as e:
                print(
                    f"Error loading negotiation {session_id} via NegotiationLoader: {e}"
                )
                return None

        # Fall back to legacy format - convert NegotiationSession to NegotiationData
        session = NegotiationStorageService.load_negotiation(session_id)
        if session is None:
            return None

        return NegotiationStorageService._session_to_negotiation_data(session)

    @staticmethod
    def _session_to_negotiation_data(session: NegotiationSession) -> "NegotiationData":
        """Convert a NegotiationSession to NegotiationData format."""
        from .negotiation_loader import NegotiationData, NegotiationOffer

        offers = [
            NegotiationOffer(
                step=o.step,
                relative_time=o.relative_time,
                proposer=o.proposer,
                proposer_index=o.proposer_index,
                offer=o.offer,
                offer_dict=o.offer_dict,
                utilities=o.utilities,
                responses={},  # Legacy format doesn't have detailed responses
                state="continuing",
            )
            for o in session.offers
        ]

        return NegotiationData(
            id=session.id,
            source="file",
            source_path=str(NegotiationStorageService.get_session_dir(session.id)),
            scenario_name=session.scenario_name or Path(session.scenario_path).name,
            scenario_path=session.scenario_path,
            negotiator_names=session.negotiator_names,
            negotiator_types=session.negotiator_types,
            negotiator_colors=[info.color for info in session.negotiator_infos]
            if session.negotiator_infos
            else [],
            issue_names=session.issue_names,
            n_steps=session.n_steps,
            time_limit=session.time_limit,
            offers=offers,
            agreement=session.agreement_dict,
            agreement_tuple=session.agreement,
            final_utilities=session.final_utilities,
            end_reason=session.end_reason,
            final_step=session.current_step,
            optimality_stats=session.optimality_stats,
            outcome_space_data=session.outcome_space_data,
        )

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

        # Load special points
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
        """List negotiations from a specific directory.

        Supports both legacy format (metadata.json) and CompletedRun format (metadata.yaml).
        """
        import yaml

        negotiations = []

        for session_dir in directory.iterdir():
            if not session_dir.is_dir():
                continue

            metadata_json_path = session_dir / "metadata.json"
            metadata_yaml_path = session_dir / "metadata.yaml"
            result_path = session_dir / "result.json"
            config_path = session_dir / "config.yaml"
            run_info_path = session_dir / "run_info.yaml"
            outcome_stats_path = session_dir / "outcome_stats.yaml"

            try:
                # Try legacy format first (metadata.json)
                if metadata_json_path.exists():
                    with open(metadata_json_path) as f:
                        metadata = json.load(f)

                    summary = {
                        "id": metadata.get("id"),
                        "scenario_name": metadata.get("scenario_name"),
                        "scenario_path": metadata.get("scenario_path"),
                        "mechanism_type": metadata.get("mechanism_type"),
                        "negotiator_names": metadata.get("negotiator_names", []),
                        "negotiator_types": metadata.get("negotiator_types", []),
                        "start_time": metadata.get("start_time"),
                        "end_time": metadata.get("end_time"),
                        "n_steps": metadata.get("n_steps"),
                        "tags": metadata.get("tags", []),
                        "archived": archived,
                    }

                    # Add result info if available
                    if result_path.exists():
                        with open(result_path) as f:
                            result = json.load(f)
                        summary["has_agreement"] = result.get("agreement") is not None
                        summary["end_reason"] = result.get("end_reason")
                        summary["final_utilities"] = result.get("final_utilities")
                        summary["n_offers"] = result.get("n_offers")
                        summary["duration_seconds"] = result.get("duration_seconds")

                    negotiations.append(summary)

                # Try CompletedRun format (metadata.yaml + config.yaml + run_info.yaml)
                elif metadata_yaml_path.exists() and config_path.exists():
                    with open(metadata_yaml_path) as f:
                        metadata = yaml.safe_load(f)
                    with open(config_path) as f:
                        config = yaml.safe_load(f)

                    # Extract scenario name from path
                    scenario_path = metadata.get("scenario_path", "")
                    scenario_name = (
                        Path(scenario_path).name if scenario_path else session_dir.name
                    )

                    summary = {
                        "id": metadata.get("session_id", session_dir.name),
                        "scenario_name": scenario_name,
                        "scenario_path": scenario_path,
                        "mechanism_type": config.get("mechanism_type", "SAOMechanism"),
                        "negotiator_names": config.get("negotiator_names", []),
                        "negotiator_types": config.get("negotiator_types", []),
                        "start_time": None,  # Not available in CompletedRun format
                        "end_time": metadata.get("saved_at"),
                        "n_steps": config.get("n_steps"),
                        "tags": [],  # Tags not in CompletedRun format
                        "archived": archived,
                    }

                    # Add result info from run_info.yaml and outcome_stats.yaml
                    if run_info_path.exists():
                        with open(run_info_path) as f:
                            run_info = yaml.safe_load(f)
                        summary["has_agreement"] = run_info.get("agreement") is not None

                    if outcome_stats_path.exists():
                        with open(outcome_stats_path) as f:
                            outcome_stats = yaml.safe_load(f)
                        summary["final_utilities"] = outcome_stats.get("utilities")
                        # Determine end reason from outcome stats
                        if outcome_stats.get("broken"):
                            summary["end_reason"] = "broken"
                        elif outcome_stats.get("timedout"):
                            summary["end_reason"] = "timeout"
                        elif outcome_stats.get("agreement"):
                            summary["end_reason"] = "agreement"
                        else:
                            summary["end_reason"] = "no_agreement"

                    # Add step/time info from config
                    summary["final_step"] = config.get("final_step")
                    summary["final_time"] = config.get("final_time")
                    summary["n_offers"] = config.get("final_step")  # Approximate

                    negotiations.append(summary)

            except (json.JSONDecodeError, KeyError, yaml.YAMLError):
                continue

        return negotiations

    @staticmethod
    def archive_negotiation(session_id: str) -> bool:
        """Move a negotiation to the archive.

        Args:
            session_id: The session ID to archive.

        Returns:
            True if archived, False if not found.
        """
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            return False

        _ensure_dir(ARCHIVE_DIR)
        archive_dest = ARCHIVE_DIR / session_id

        # Move to archive
        shutil.move(str(session_dir), str(archive_dest))

        # Update metadata to mark as archived
        metadata_path = archive_dest / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            metadata["archived"] = True
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        return True

    @staticmethod
    def unarchive_negotiation(session_id: str) -> bool:
        """Restore a negotiation from the archive.

        Args:
            session_id: The session ID to unarchive.

        Returns:
            True if unarchived, False if not found.
        """
        archive_dir = ARCHIVE_DIR / session_id
        if not archive_dir.exists():
            return False

        _ensure_dir(NEGOTIATIONS_DIR)
        dest = NEGOTIATIONS_DIR / session_id

        # Move back from archive
        shutil.move(str(archive_dir), str(dest))

        # Update metadata
        metadata_path = dest / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            metadata["archived"] = False
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        return True

    @staticmethod
    def update_tags(session_id: str, tags: list[str]) -> bool:
        """Update tags for a negotiation.

        Args:
            session_id: The session ID to update.
            tags: New list of tags.

        Returns:
            True if updated, False if not found.
        """
        # Check both directories
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / "metadata.json"
        if not metadata_path.exists():
            return False

        with open(metadata_path) as f:
            metadata = json.load(f)

        metadata["tags"] = tags

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return True

    @staticmethod
    def add_tag(session_id: str, tag: str) -> bool:
        """Add a tag to a negotiation.

        Args:
            session_id: The session ID.
            tag: Tag to add.

        Returns:
            True if added, False if not found.
        """
        # Check both directories
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / "metadata.json"
        if not metadata_path.exists():
            return False

        with open(metadata_path) as f:
            metadata = json.load(f)

        tags = metadata.get("tags", [])
        if tag not in tags:
            tags.append(tag)
            metadata["tags"] = tags
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        return True

    @staticmethod
    def remove_tag(session_id: str, tag: str) -> bool:
        """Remove a tag from a negotiation.

        Args:
            session_id: The session ID.
            tag: Tag to remove.

        Returns:
            True if removed, False if not found.
        """
        # Check both directories
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        metadata_path = session_dir / "metadata.json"
        if not metadata_path.exists():
            return False

        with open(metadata_path) as f:
            metadata = json.load(f)

        tags = metadata.get("tags", [])
        if tag in tags:
            tags.remove(tag)
            metadata["tags"] = tags
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        return True

    @staticmethod
    def get_all_tags() -> list[str]:
        """Get all unique tags used across all negotiations.

        Returns:
            Sorted list of unique tags.
        """
        all_tags = set()

        for directory in [NEGOTIATIONS_DIR, ARCHIVE_DIR]:
            if not directory.exists():
                continue

            for session_dir in directory.iterdir():
                if not session_dir.is_dir():
                    continue

                metadata_path = session_dir / "metadata.json"
                if not metadata_path.exists():
                    continue

                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    all_tags.update(metadata.get("tags", []))
                except (json.JSONDecodeError, KeyError):
                    continue

        return sorted(all_tags)

    @staticmethod
    def delete_negotiation(session_id: str) -> bool:
        """Delete a saved negotiation.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        # Check both directories
        session_dir = NEGOTIATIONS_DIR / session_id
        if not session_dir.exists():
            session_dir = ARCHIVE_DIR / session_id
        if not session_dir.exists():
            return False

        shutil.rmtree(session_dir)
        return True

    @staticmethod
    def clear_all_negotiations(include_archived: bool = False) -> int:
        """Delete all saved negotiations.

        Args:
            include_archived: If True, also delete archived negotiations.

        Returns:
            Number of negotiations deleted.
        """
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
