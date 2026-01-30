"""Service for persisting negotiation sessions to disk."""

import csv
import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

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
        scenario_options: dict | None = None,
    ) -> Path:
        """Save a completed negotiation to disk.

        Args:
            session: The negotiation session to save.
            negotiator_configs: Original negotiator configurations (optional).
            tags: Optional list of tags for categorization.
            scenario_options: Dict with normalize, ignore_discount, ignore_reserved flags.

        Returns:
            Path to the session directory.
        """
        session_dir = NegotiationStorageService.get_session_dir(session.id)
        _ensure_dir(session_dir)

        # Extract scenario options with defaults
        scenario_opts = scenario_options or {}
        normalize = scenario_opts.get("normalize", False)
        ignore_discount = scenario_opts.get("ignore_discount", False)
        ignore_reserved = scenario_opts.get("ignore_reserved", False)

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
            # Scenario options needed for outcome space reconstruction
            "normalize": normalize,
            "ignore_discount": ignore_discount,
            "ignore_reserved": ignore_reserved,
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

        # Save offers in configured format (parquet or CSV)
        if session.offers:
            settings = SettingsService.load_performance()
            storage_format = settings.offers_storage_format

            if storage_format == "parquet":
                try:
                    NegotiationStorageService._save_offers_parquet(
                        session_dir / "offers.parquet",
                        session.offers,
                        session.issue_names,
                    )
                except ImportError:
                    # Fallback to CSV if pandas/pyarrow not available
                    print("Warning: pandas/pyarrow not available, falling back to CSV")
                    NegotiationStorageService._save_offers_csv(
                        session_dir / "offers.csv", session.offers, session.issue_names
                    )
            else:
                NegotiationStorageService._save_offers_csv(
                    session_dir / "offers.csv", session.offers, session.issue_names
                )

        # Note: outcome_space.json is NO LONGER SAVED
        # It can be reconstructed from the scenario when needed
        # This saves significant disk space for large outcome spaces

        # Generate preview images for panels
        try:
            NegotiationPreviewService.generate_all_previews(session, session_dir)
        except Exception as e:
            print(f"Warning: Failed to generate preview images: {e}")
            # Continue even if preview generation fails - not critical

        return session_dir

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
    def _save_offers_parquet(
        path: Path, offers: list[OfferEvent], issue_names: list[str]
    ) -> None:
        """Save offers to Parquet format for optimized storage."""
        import pandas as pd

        # Build dataframe
        n_negotiators = len(offers[0].utilities) if offers else 0

        data = {
            "step": [o.step for o in offers],
            "proposer": [o.proposer for o in offers],
            "proposer_index": [o.proposer_index for o in offers],
        }

        # Add issue columns
        for i, issue_name in enumerate(issue_names):
            data[issue_name] = [
                list(o.offer)[i] if o.offer and len(o.offer) > i else None
                for o in offers
            ]

        # Add utility columns
        for i in range(n_negotiators):
            data[f"utility_{i}"] = [
                o.utilities[i] if len(o.utilities) > i else None for o in offers
            ]

        # Add response and relative_time
        data["response"] = [o.response or "" for o in offers]
        data["relative_time"] = [o.relative_time for o in offers]

        df = pd.DataFrame(data)
        df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)

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

                # Handle legacy negotiations where agreement_dict is null but agreement exists
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

            # Load offers from parquet (preferred) or CSV fallback
            offers_parquet_path = session_dir / "offers.parquet"
            offers_csv_path = session_dir / "offers.csv"

            if offers_parquet_path.exists():
                try:
                    import pandas as pd

                    df = pd.read_parquet(offers_parquet_path)
                    for _, row in df.iterrows():
                        # Extract offer values from issue columns
                        offer_values = tuple(
                            row[name]
                            for name in session.issue_names
                            if name in df.columns
                        )

                        # Extract utilities
                        utilities = []
                        i = 0
                        while f"utility_{i}" in df.columns:
                            utilities.append(float(row[f"utility_{i}"]))
                            i += 1

                        session.offers.append(
                            OfferEvent(
                                step=int(row["step"]),
                                proposer=str(row["proposer"]),
                                proposer_index=int(row["proposer_index"]),
                                offer=offer_values if offer_values else (),
                                offer_dict=dict(zip(session.issue_names, offer_values))
                                if offer_values
                                else {},
                                utilities=utilities,
                                timestamp=datetime.now(),  # Not preserved in parquet
                                response=str(row["response"])
                                if pd.notna(row.get("response"))
                                else None,
                                relative_time=float(row["relative_time"]),
                            )
                        )
                except ImportError:
                    print(f"Warning: pandas not available, cannot load parquet offers")
            elif offers_csv_path.exists():
                # Fallback to CSV if parquet not available
                # (Old saved negotiations or when parquet saving failed)
                with open(offers_csv_path, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Extract offer values from issue columns
                        offer_values = tuple(
                            row[name] for name in session.issue_names if name in row
                        )

                        # Extract utilities
                        utilities = []
                        i = 0
                        while f"utility_{i}" in row:
                            utilities.append(float(row[f"utility_{i}"]))
                            i += 1

                        session.offers.append(
                            OfferEvent(
                                step=int(row["step"]),
                                proposer=str(row["proposer"]),
                                proposer_index=int(row["proposer_index"]),
                                offer=offer_values if offer_values else (),
                                offer_dict=dict(zip(session.issue_names, offer_values))
                                if offer_values
                                else {},
                                utilities=utilities,
                                timestamp=datetime.now(),
                                response=str(row["response"])
                                if row.get("response")
                                else None,
                                relative_time=float(row["relative_time"]),
                            )
                        )

            # Load outcome space data from scenario (reconstruct if needed)
            # Try multiple methods in order of preference:
            # 1. Load from saved file (legacy - backward compatibility)
            # 2. Reconstruct from offers (fast, doesn't need scenario)
            # 3. Reconstruct from scenario (requires scenario to be available)
            outcome_path = session_dir / "outcome_space.json"
            if outcome_path.exists():
                # Legacy: load from saved file for backward compatibility
                session.outcome_space_data = (
                    NegotiationStorageService._load_outcome_space(outcome_path)
                )
            elif session.offers:
                # Fast path: reconstruct minimal outcome_space_data from offers
                # This provides enough data for visualization without loading scenario
                try:
                    session.outcome_space_data = (
                        NegotiationStorageService._build_outcome_space_from_offers(
                            session.offers
                        )
                    )
                except Exception as e:
                    print(f"Warning: Could not build outcome space from offers: {e}")
                    session.outcome_space_data = None
            elif session.scenario_path:
                # Fallback: Reconstruct from scenario (requires scenario to exist)
                try:
                    from ..services.outcome_analysis import OutcomeAnalysisService
                    from negmas import Scenario

                    scenario = Scenario.load(
                        session.scenario_path, load_stats=True, load_info=True
                    )
                    session.outcome_space_data = (
                        OutcomeAnalysisService.analyze_outcome_space(
                            scenario=scenario,
                            normalize=metadata.get("normalize", False),
                            ignore_discount=metadata.get("ignore_discount", False),
                            ignore_reserved=metadata.get("ignore_reserved", False),
                        )
                    )
                except Exception as e:
                    print(
                        f"Warning: Could not reconstruct outcome space from scenario: {e}"
                    )
                    session.outcome_space_data = None

            return session

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Log error but return None
            print(f"Error loading negotiation {session_id}: {e}")
            return None

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
    def _build_outcome_space_from_offers(offers: list[OfferEvent]) -> OutcomeSpaceData:
        """Build minimal outcome space data from offers for visualization.

        This provides enough data for the Utility2D panel without needing
        the original scenario. It extracts unique outcomes from offers and
        uses their utilities.

        Args:
            offers: List of offer events with utilities.

        Returns:
            OutcomeSpaceData with utilities from offers only.
        """
        if not offers:
            return OutcomeSpaceData(
                outcome_utilities=[],
                pareto_utilities=[],
                total_outcomes=0,
                sampled=False,
                sample_size=0,
            )

        # Extract unique outcomes and their utilities
        outcome_map = {}  # outcome -> utilities
        for offer in offers:
            if offer.offer and offer.utilities:
                outcome_key = offer.offer  # tuple is hashable
                if outcome_key not in outcome_map:
                    outcome_map[outcome_key] = tuple(offer.utilities)

        outcome_utilities = list(outcome_map.values())

        # Simple Pareto frontier approximation from offers
        # An outcome is Pareto-efficient if no other outcome dominates it
        pareto_utilities = []
        for utilities in outcome_utilities:
            is_pareto = True
            for other in outcome_utilities:
                # Check if 'other' dominates 'utilities'
                # (better or equal in all dimensions, strictly better in at least one)
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
            sampled=True,  # We only have offers, not all outcomes
            sample_size=len(outcome_utilities),
            # Special points set to None - could compute if needed
            nash_point=None,
            kalai_point=None,
            kalai_smorodinsky_point=None,
            max_welfare_point=None,
        )

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

            metadata_path = session_dir / "metadata.json"
            result_path = session_dir / "result.json"

            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)

                # Use scenario_path name as fallback if scenario_name is empty
                scenario_name = metadata.get("scenario_name")
                if not scenario_name:
                    scenario_path = metadata.get("scenario_path", "")
                    if scenario_path:
                        scenario_name = Path(scenario_path).name
                    else:
                        scenario_name = "Unknown"

                summary = {
                    "id": metadata.get("id"),
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

                # Add result info if available
                if result_path.exists():
                    with open(result_path) as f:
                        result = json.load(f)
                    summary["agreement"] = result.get(
                        "agreement"
                    )  # Include full agreement
                    summary["agreement_dict"] = result.get("agreement_dict")
                    summary["has_agreement"] = result.get("agreement") is not None
                    summary["end_reason"] = result.get("end_reason")
                    summary["final_utilities"] = result.get("final_utilities")
                    summary["n_offers"] = result.get("n_offers")
                    summary["duration_seconds"] = result.get("duration_seconds")

                negotiations.append(summary)

            except (json.JSONDecodeError, KeyError):
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
