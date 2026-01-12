"""Service for persisting negotiation sessions to disk."""

import csv
import json
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

# Storage directory path
NEGOTIATIONS_DIR = Path.home() / "negmas" / "app" / "negotiations"


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
    ) -> Path:
        """Save a completed negotiation to disk.

        Args:
            session: The negotiation session to save.
            negotiator_configs: Original negotiator configurations (optional).

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
    def list_saved_negotiations() -> list[dict]:
        """List all saved negotiations.

        Returns:
            List of dictionaries with summary info for each negotiation.
        """
        if not NEGOTIATIONS_DIR.exists():
            return []

        negotiations = []
        for session_dir in NEGOTIATIONS_DIR.iterdir():
            if not session_dir.is_dir():
                continue

            metadata_path = session_dir / "metadata.json"
            result_path = session_dir / "result.json"

            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)

                summary = {
                    "id": metadata.get("id"),
                    "scenario_name": metadata.get("scenario_name"),
                    "negotiator_names": metadata.get("negotiator_names", []),
                    "negotiator_types": metadata.get("negotiator_types", []),
                    "start_time": metadata.get("start_time"),
                    "end_time": metadata.get("end_time"),
                    "n_steps": metadata.get("n_steps"),
                }

                # Add result info if available
                if result_path.exists():
                    with open(result_path) as f:
                        result = json.load(f)
                    summary["has_agreement"] = result.get("agreement") is not None
                    summary["end_reason"] = result.get("end_reason")
                    summary["final_utilities"] = result.get("final_utilities")
                    summary["n_offers"] = result.get("n_offers")

                negotiations.append(summary)

            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by end_time descending (most recent first)
        negotiations.sort(key=lambda x: x.get("end_time") or "", reverse=True)

        return negotiations

    @staticmethod
    def delete_negotiation(session_id: str) -> bool:
        """Delete a saved negotiation.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        import shutil

        session_dir = NegotiationStorageService.get_session_dir(session_id)
        if not session_dir.exists():
            return False

        shutil.rmtree(session_dir)
        return True

    @staticmethod
    def clear_all_negotiations() -> int:
        """Delete all saved negotiations.

        Returns:
            Number of negotiations deleted.
        """
        import shutil

        if not NEGOTIATIONS_DIR.exists():
            return 0

        count = 0
        for session_dir in NEGOTIATIONS_DIR.iterdir():
            if session_dir.is_dir():
                shutil.rmtree(session_dir)
                count += 1

        return count
