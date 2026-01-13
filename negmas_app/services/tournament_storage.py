"""Tournament storage service for loading saved tournament results."""

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class SavedTournamentSummary:
    """Summary info for a saved tournament."""

    id: str
    path: str
    name: str
    created_at: datetime | None
    n_scenarios: int
    n_competitors: int
    n_negotiations: int
    n_agreements: int
    agreement_rate: float


@dataclass
class TournamentNegotiationResult:
    """Result of a single negotiation from saved tournament."""

    index: int
    scenario: str
    partners: list[str]
    agreement: dict | None
    utilities: list[float] | None
    has_error: bool
    # Extra fields from CSV
    extra: dict


class TournamentStorageService:
    """Service for loading saved tournament results from cartesian_tournament."""

    TOURNAMENTS_DIR = Path.home() / "negmas" / "app" / "tournaments"

    @classmethod
    def list_saved_tournaments(cls) -> list[dict]:
        """List all saved tournaments from disk.

        Scans ~/negmas/app/tournaments/ for tournament result directories.

        Returns:
            List of tournament summary dicts.
        """
        tournaments = []

        if not cls.TOURNAMENTS_DIR.exists():
            return tournaments

        # Each tournament is a directory with results inside
        for path in cls.TOURNAMENTS_DIR.iterdir():
            if not path.is_dir():
                continue

            # Check for required files
            all_results = path / "all_results.csv"
            all_scores = path / "all_scores.csv"

            if not all_results.exists() and not all_scores.exists():
                continue

            # Try to load summary info
            summary = cls._load_tournament_summary(path)
            if summary:
                tournaments.append(summary)

        # Sort by creation time (newest first)
        tournaments.sort(key=lambda t: t.get("created_at") or "", reverse=True)
        return tournaments

    @classmethod
    def _load_tournament_summary(cls, path: Path) -> dict | None:
        """Load summary info for a tournament directory."""
        try:
            tournament_id = path.name

            # Get creation time from directory
            created_at = None
            try:
                stat = path.stat()
                created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except Exception:
                pass

            # Count negotiations from all_results.csv
            n_negotiations = 0
            n_agreements = 0
            scenarios = set()
            competitors = set()

            all_results = path / "all_results.csv"
            if all_results.exists():
                with open(all_results, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        n_negotiations += 1
                        if row.get("agreement") and row["agreement"] != "None":
                            n_agreements += 1
                        if row.get("scenario"):
                            scenarios.add(row["scenario"])
                        # Try to get competitor names
                        for key in ["negotiator0", "negotiator1", "first", "second"]:
                            if row.get(key):
                                competitors.add(row[key])

            # Try to get competitor count from all_scores.csv
            all_scores = path / "all_scores.csv"
            if all_scores.exists() and not competitors:
                with open(all_scores, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        for key in ["strategy", "name", "competitor"]:
                            if row.get(key):
                                competitors.add(row[key])
                                break

            agreement_rate = (
                n_agreements / n_negotiations if n_negotiations > 0 else 0.0
            )

            return {
                "id": tournament_id,
                "path": str(path),
                "name": tournament_id,
                "created_at": created_at,
                "n_scenarios": len(scenarios),
                "n_competitors": len(competitors),
                "n_negotiations": n_negotiations,
                "n_agreements": n_agreements,
                "agreement_rate": agreement_rate,
            }
        except Exception as e:
            print(f"Error loading tournament summary from {path}: {e}")
            return None

    @classmethod
    def load_tournament(cls, tournament_id: str) -> dict | None:
        """Load full tournament data from disk.

        Args:
            tournament_id: ID (directory name) of the tournament.

        Returns:
            Full tournament data including scores and negotiation results.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        if not path.exists():
            return None

        # Load summary
        summary = cls._load_tournament_summary(path)
        if not summary:
            return None

        # Load scores
        scores = cls._load_scores(path)

        # Load negotiation results (summary only, not full details)
        negotiations = cls._load_negotiations_summary(path)

        return {
            **summary,
            "scores": scores,
            "negotiations": negotiations,
        }

    @classmethod
    def _load_scores(cls, path: Path) -> list[dict]:
        """Load competitor scores from all_scores.csv."""
        scores = []
        all_scores = path / "all_scores.csv"

        if not all_scores.exists():
            return scores

        try:
            with open(all_scores, "r") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    # Try to find competitor name
                    name = None
                    for key in ["strategy", "name", "competitor", ""]:
                        if key == "":
                            # First column might be unnamed index
                            name = row.get("") or row.get("Unnamed: 0")
                        elif row.get(key):
                            name = row[key]
                            break

                    if not name:
                        name = f"Competitor {idx + 1}"

                    # Get score (might be in various columns)
                    score = None
                    for key in ["score", "mean", "advantage", "utility"]:
                        if row.get(key):
                            try:
                                score = float(row[key])
                                break
                            except ValueError:
                                pass

                    scores.append(
                        {
                            "name": name,
                            "rank": idx + 1,
                            "score": score,
                            "raw_data": row,
                        }
                    )

            # Sort by score descending
            scores.sort(key=lambda x: x.get("score") or 0, reverse=True)
            for idx, s in enumerate(scores):
                s["rank"] = idx + 1

        except Exception as e:
            print(f"Error loading scores from {path}: {e}")

        return scores

    @classmethod
    def _load_negotiations_summary(cls, path: Path) -> list[dict]:
        """Load negotiation results summary from all_results.csv."""
        negotiations = []
        all_results = path / "all_results.csv"

        if not all_results.exists():
            return negotiations

        try:
            with open(all_results, "r") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    # Get partners
                    partners = []
                    for key in [
                        "negotiator0",
                        "negotiator1",
                        "first",
                        "second",
                        "agent0",
                        "agent1",
                    ]:
                        if row.get(key):
                            partners.append(row[key])

                    # Get scenario
                    scenario = row.get("scenario") or row.get("domain") or "Unknown"

                    # Get agreement
                    agreement_str = row.get("agreement")
                    has_agreement = (
                        agreement_str is not None
                        and agreement_str != ""
                        and agreement_str != "None"
                    )

                    # Get utilities
                    utilities = []
                    for key in ["utility0", "utility1", "u0", "u1"]:
                        if row.get(key):
                            try:
                                utilities.append(float(row[key]))
                            except ValueError:
                                pass

                    negotiations.append(
                        {
                            "index": idx,
                            "scenario": scenario,
                            "partners": partners,
                            "has_agreement": has_agreement,
                            "utilities": utilities if utilities else None,
                        }
                    )

        except Exception as e:
            print(f"Error loading negotiations from {path}: {e}")

        return negotiations

    @classmethod
    def get_tournament_negotiation(cls, tournament_id: str, index: int) -> dict | None:
        """Get full details of a specific negotiation from a tournament.

        Args:
            tournament_id: Tournament ID.
            index: Index of the negotiation in all_results.csv.

        Returns:
            Full negotiation data or None if not found.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        all_results = path / "all_results.csv"

        if not all_results.exists():
            return None

        try:
            with open(all_results, "r") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    if idx == index:
                        # Return full row data
                        return {
                            "index": idx,
                            "raw_data": dict(row),
                            "scenario": row.get("scenario") or row.get("domain"),
                            "partners": [
                                row.get(k)
                                for k in [
                                    "negotiator0",
                                    "negotiator1",
                                    "first",
                                    "second",
                                ]
                                if row.get(k)
                            ],
                            "agreement": row.get("agreement"),
                            "utilities": [
                                float(row[k])
                                for k in ["utility0", "utility1", "u0", "u1"]
                                if row.get(k)
                            ]
                            or None,
                        }
        except Exception as e:
            print(f"Error loading negotiation {index} from {tournament_id}: {e}")

        return None

    @classmethod
    def delete_tournament(cls, tournament_id: str) -> bool:
        """Delete a saved tournament from disk.

        Args:
            tournament_id: Tournament ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        import shutil

        path = cls.TOURNAMENTS_DIR / tournament_id
        if not path.exists():
            return False

        try:
            shutil.rmtree(path)
            return True
        except Exception as e:
            print(f"Error deleting tournament {tournament_id}: {e}")
            return False
