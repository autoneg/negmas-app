"""Tournament storage service for loading saved tournament results."""

import ast
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


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
    def list_saved_tournaments(
        cls, archived: bool | None = None, tags: list[str] | None = None
    ) -> list[dict]:
        """List all saved tournaments from disk.

        Scans ~/negmas/app/tournaments/ for tournament result directories.

        Args:
            archived: If True, only archived; if False, only non-archived; if None, all
            tags: If provided, filter by tags (match any)

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
                # Apply filters
                if archived is not None and summary.get("archived", False) != archived:
                    continue
                if tags:
                    tournament_tags = summary.get("tags", [])
                    if not any(tag in tournament_tags for tag in tags):
                        continue
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

            # Load metadata (tags, archived status)
            metadata = cls._load_metadata(tournament_id)

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
                "tags": metadata.get("tags", []),
                "archived": metadata.get("archived", False),
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
        """Load negotiation results summary from details.csv (cartesian_tournament output)."""
        negotiations = []

        # cartesian_tournament saves to details.csv
        details_file = path / "details.csv"
        if not details_file.exists():
            # Fall back to all_results.csv for streaming tournaments
            details_file = path / "all_results.csv"

        if not details_file.exists():
            return negotiations

        try:
            with open(details_file, "r") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    # Get partners - cartesian_tournament uses 'partners' field as list string
                    partners = []
                    partners_str = row.get("partners", "")
                    if partners_str and partners_str != "[]":
                        try:
                            # Parse list like "['AspirationNegotiator', 'BoulwareTBNegotiator']"
                            partners = ast.literal_eval(partners_str)
                        except (ValueError, SyntaxError):
                            pass

                    # Fall back to individual fields
                    if not partners:
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

                    # Get utilities - cartesian_tournament uses 'utilities' field as tuple string
                    utilities = []
                    utilities_str = row.get("utilities", "")
                    if utilities_str:
                        try:
                            utils_tuple = ast.literal_eval(utilities_str)
                            utilities = (
                                list(utils_tuple)
                                if isinstance(utils_tuple, tuple)
                                else list(utils_tuple)
                            )
                        except (ValueError, SyntaxError):
                            pass

                    # Fall back to individual fields
                    if not utilities:
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
                            "raw_data": row,
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
            index: Index of the negotiation in details.csv.

        Returns:
            Full negotiation data or None if not found.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id

        # cartesian_tournament saves to details.csv
        details_file = path / "details.csv"
        if not details_file.exists():
            # Fall back to all_results.csv for streaming tournaments
            details_file = path / "all_results.csv"

        if not details_file.exists():
            return None

        try:
            with open(details_file, "r") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    if idx == index:
                        # Parse partners from list string
                        partners = []
                        partners_str = row.get("partners", "")
                        if partners_str and partners_str != "[]":
                            try:
                                partners = ast.literal_eval(partners_str)
                            except (ValueError, SyntaxError):
                                pass

                        # Fall back to individual fields
                        if not partners:
                            for k in ["negotiator0", "negotiator1", "first", "second"]:
                                if row.get(k):
                                    partners.append(row[k])

                        # Parse utilities from tuple string
                        utilities = None
                        utilities_str = row.get("utilities", "")
                        if utilities_str:
                            try:
                                utils_tuple = ast.literal_eval(utilities_str)
                                utilities = (
                                    list(utils_tuple)
                                    if isinstance(utils_tuple, tuple)
                                    else list(utils_tuple)
                                )
                            except (ValueError, SyntaxError):
                                pass

                        # Fall back to individual fields
                        if not utilities:
                            utilities = []
                            for k in ["utility0", "utility1", "u0", "u1"]:
                                if row.get(k):
                                    try:
                                        utilities.append(float(row[k]))
                                    except ValueError:
                                        pass
                            utilities = utilities if utilities else None

                        return {
                            "index": idx,
                            "raw_data": dict(row),
                            "scenario": row.get("scenario") or row.get("domain"),
                            "partners": partners,
                            "agreement": row.get("agreement"),
                            "utilities": utilities,
                            "has_agreement": row.get("agreement")
                            not in (None, "", "None"),
                        }
        except Exception as e:
            print(f"Error loading negotiation {index} from {tournament_id}: {e}")

        return None

    @classmethod
    def get_negotiation_trace(
        cls, tournament_id: str, mechanism_name: str
    ) -> dict | None:
        """Get the full negotiation trace for a specific mechanism run.

        Args:
            tournament_id: Tournament ID.
            mechanism_name: The mechanism_name from the negotiation record.

        Returns:
            Negotiation trace data with offers and responses, or None if not found.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        negotiations_dir = path / "negotiations"

        if not negotiations_dir.exists():
            return None

        # Find the negotiation CSV file by mechanism name
        # Files are named like: scenario_negotiator1_negotiator2_rep_mechanismname.csv
        try:
            matching_files = list(negotiations_dir.glob(f"*_{mechanism_name}.csv"))
            if not matching_files:
                return None

            trace_file = matching_files[0]

            # Read the negotiation trace
            trace_data = []
            with open(trace_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trace_data.append(dict(row))

            return {
                "mechanism_name": mechanism_name,
                "trace": trace_data,
                "file_name": trace_file.name,
            }
        except Exception as e:
            print(f"Error loading negotiation trace {mechanism_name}: {e}")
            return None

    @classmethod
    def list_negotiation_files(cls, tournament_id: str) -> list[dict]:
        """List all negotiation trace files in a tournament.

        Args:
            tournament_id: Tournament ID.

        Returns:
            List of dicts with file info.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        negotiations_dir = path / "negotiations"

        if not negotiations_dir.exists():
            return []

        files = []
        for file in negotiations_dir.glob("*.csv"):
            files.append(
                {
                    "name": file.name,
                    "size": file.stat().st_size,
                    "mechanism_name": file.stem.split("_")[-1],
                }
            )

        return files

    @classmethod
    def get_scenario_info(cls, tournament_id: str, scenario_name: str) -> dict | None:
        """Get scenario information from a saved tournament.

        Args:
            tournament_id: Tournament ID.
            scenario_name: Name of the scenario.

        Returns:
            Scenario info including outcome_space, issue_names, stats, etc.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        scenarios_dir = path / "scenarios"

        if not scenarios_dir.exists():
            return None

        # Find the scenario directory
        scenario_dir = scenarios_dir / scenario_name
        if not scenario_dir.exists():
            return None

        # Load the main scenario YAML
        scenario_yaml = scenario_dir / f"{scenario_name}.yml"
        if not scenario_yaml.exists():
            return None

        try:
            with open(scenario_yaml, "r") as f:
                scenario_data = yaml.safe_load(f)

            # Load stats if available
            stats_file = scenario_dir / "stats.json"
            stats = None
            if stats_file.exists():
                with open(stats_file, "r") as f:
                    stats = json.load(f)

            # Extract issue names - handle both list and dict formats
            # The YAML stores issues as a list of {name, type, values}
            issues = scenario_data.get("issues", [])
            if isinstance(issues, list):
                issue_names = [
                    iss.get("name", f"Issue{idx}") for idx, iss in enumerate(issues)
                ]
            elif isinstance(issues, dict):
                issue_names = list(issues.keys())
            else:
                issue_names = []

            return {
                "name": scenario_name,
                "issues": issues,
                "issue_names": issue_names,
                "stats": stats,
                "raw_data": scenario_data,
            }

        except Exception as e:
            print(f"Error loading scenario {scenario_name} from {tournament_id}: {e}")
            return None

    @classmethod
    def load_ufuns(cls, tournament_id: str, scenario_name: str) -> list[dict] | None:
        """Load utility functions for a scenario from saved tournament.

        Args:
            tournament_id: Tournament ID.
            scenario_name: Name of the scenario.

        Returns:
            List of ufun data dicts, or None if not found.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        scenario_dir = path / "scenarios" / scenario_name

        if not scenario_dir.exists():
            return None

        ufuns = []
        # Load 0_.yml, 1_.yml, etc. for each negotiator
        for i in range(10):  # Support up to 10 negotiators
            ufun_file = scenario_dir / f"{i}_.yml"
            if not ufun_file.exists():
                break

            try:
                with open(ufun_file, "r") as f:
                    ufun_data = yaml.safe_load(f)
                    ufuns.append(ufun_data)
            except Exception as e:
                print(f"Error loading ufun {i} for {scenario_name}: {e}")
                break

        return ufuns if ufuns else None

    @classmethod
    def calculate_utility(cls, ufun_data: dict, offer: tuple | list) -> float | None:
        """Calculate utility for an offer using a saved ufun.

        Supports LinearAdditiveUtilityFunction with TableFun values.

        Args:
            ufun_data: Parsed ufun data from YAML.
            offer: The offer as a tuple/list of values.

        Returns:
            Utility value, or None if calculation fails.
        """
        try:
            ufun_type = ufun_data.get("type", "")
            if ufun_type != "LinearAdditiveUtilityFunction":
                return None

            weights = ufun_data.get("weights", [])
            values = ufun_data.get("values", [])

            if len(weights) != len(values) or len(offer) != len(values):
                return None

            utility = 0.0
            for i, (weight, value_fun) in enumerate(zip(weights, values)):
                mapping = value_fun.get("mapping", {})
                offer_value = offer[i]
                issue_utility = mapping.get(offer_value, 0.0)
                utility += weight * issue_utility

            return utility
        except Exception as e:
            print(f"Error calculating utility: {e}")
            return None

    @classmethod
    def get_negotiation_trace_with_utilities(
        cls, tournament_id: str, mechanism_name: str, scenario_name: str
    ) -> dict | None:
        """Get negotiation trace with per-offer utility calculations.

        Args:
            tournament_id: Tournament ID.
            mechanism_name: The mechanism name (run_id) from the negotiation.
            scenario_name: The scenario name for loading ufuns.

        Returns:
            Negotiation trace with offers and calculated utilities.
        """
        # Get the raw trace
        trace_data = cls.get_negotiation_trace(tournament_id, mechanism_name)
        if not trace_data:
            return None

        # Load ufuns for this scenario
        ufuns = cls.load_ufuns(tournament_id, scenario_name)
        if not ufuns:
            # Return trace without utilities if ufuns not available
            return trace_data

        # Load scenario info to get issue names (for offer parsing order validation)
        scenario_info = cls.get_scenario_info(tournament_id, scenario_name)
        issue_names = scenario_info.get("issue_names", []) if scenario_info else []

        # Calculate utilities for each offer
        for row in trace_data.get("trace", []):
            offer_str = row.get("offer", "")
            if not offer_str:
                continue

            # Parse the offer tuple string
            try:
                offer_tuple = ast.literal_eval(offer_str)
            except (ValueError, SyntaxError):
                continue

            # Calculate utility for each negotiator
            utilities = []
            for ufun in ufuns:
                util = cls.calculate_utility(ufun, offer_tuple)
                utilities.append(util)

            row["utilities"] = utilities

        return trace_data

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

    @classmethod
    def _get_metadata_path(cls, tournament_id: str) -> Path:
        """Get path to tournament metadata file."""
        return cls.TOURNAMENTS_DIR / tournament_id / ".metadata.json"

    @classmethod
    def _load_metadata(cls, tournament_id: str) -> dict:
        """Load tournament metadata (tags, archived status, etc.)."""
        metadata_path = cls._get_metadata_path(tournament_id)
        if not metadata_path.exists():
            return {"tags": [], "archived": False}

        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata for {tournament_id}: {e}")
            return {"tags": [], "archived": False}

    @classmethod
    def _save_metadata(cls, tournament_id: str, metadata: dict) -> bool:
        """Save tournament metadata."""
        path = cls.TOURNAMENTS_DIR / tournament_id
        if not path.exists():
            return False

        metadata_path = cls._get_metadata_path(tournament_id)
        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving metadata for {tournament_id}: {e}")
            return False

    @classmethod
    def set_archived(cls, tournament_id: str, archived: bool) -> bool:
        """Set archived status for a tournament."""
        metadata = cls._load_metadata(tournament_id)
        metadata["archived"] = archived
        return cls._save_metadata(tournament_id, metadata)

    @classmethod
    def set_tags(cls, tournament_id: str, tags: list[str]) -> bool:
        """Set tags for a tournament."""
        metadata = cls._load_metadata(tournament_id)
        metadata["tags"] = tags
        return cls._save_metadata(tournament_id, metadata)

    @classmethod
    def get_tournament_config(cls, tournament_id: str) -> dict | None:
        """Get tournament configuration from config.json.

        Args:
            tournament_id: Tournament ID.

        Returns:
            Config dict or None if not found.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id / "config.json"
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config for {tournament_id}: {e}")
            return None

    @classmethod
    def get_scores_csv(cls, tournament_id: str) -> list[dict] | None:
        """Get final scores from scores.csv.

        Args:
            tournament_id: Tournament ID.

        Returns:
            List of score dicts with strategy and score.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id / "scores.csv"
        if not path.exists():
            return None

        try:
            scores = []
            with open(path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    scores.append(dict(row))
            return scores
        except Exception as e:
            print(f"Error loading scores.csv for {tournament_id}: {e}")
            return None

    @classmethod
    def get_type_scores_csv(cls, tournament_id: str) -> dict | None:
        """Get detailed type scores from type_scores.csv.

        Args:
            tournament_id: Tournament ID.

        Returns:
            Dict with headers and rows (transposed for readability).
        """
        path = cls.TOURNAMENTS_DIR / tournament_id / "type_scores.csv"
        if not path.exists():
            return None

        try:
            rows = []
            headers = []
            with open(path, "r") as f:
                reader = csv.reader(f)
                for idx, row in enumerate(reader):
                    if idx == 0:
                        # First row is metric names repeated
                        headers = row
                    elif idx == 1:
                        # Second row is stat names (count, mean, std, etc.)
                        stats = row
                    else:
                        # Data rows: index (strategy name), then values
                        rows.append({"strategy": row[0], "values": row[1:]})

            # Parse the metrics structure
            metrics = []
            current_metric = None
            stat_names = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
            for i, header in enumerate(headers[1:], start=1):  # Skip index column
                if header and header != current_metric:
                    current_metric = header
                    metrics.append({"name": header, "start_idx": i})

            return {
                "metrics": [m["name"] for m in metrics],
                "stat_names": stat_names,
                "strategies": rows,
            }
        except Exception as e:
            print(f"Error loading type_scores.csv for {tournament_id}: {e}")
            return None

    @classmethod
    def get_all_scores_csv(cls, tournament_id: str) -> list[dict] | None:
        """Get per-negotiation scores from all_scores.csv.

        Args:
            tournament_id: Tournament ID.

        Returns:
            List of per-negotiation score dicts.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id / "all_scores.csv"
        if not path.exists():
            return None

        try:
            scores = []
            with open(path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    scores.append(dict(row))
            return scores
        except Exception as e:
            print(f"Error loading all_scores.csv for {tournament_id}: {e}")
            return None

    @classmethod
    def get_details_csv(cls, tournament_id: str) -> list[dict] | None:
        """Get detailed negotiation results from details.csv.

        Args:
            tournament_id: Tournament ID.

        Returns:
            List of detailed negotiation result dicts.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id / "details.csv"
        if not path.exists():
            return None

        try:
            details = []
            with open(path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    details.append(dict(row))
            return details
        except Exception as e:
            print(f"Error loading details.csv for {tournament_id}: {e}")
            return None

    @classmethod
    def get_tournament_files(cls, tournament_id: str) -> dict:
        """Get list of available files in the tournament directory.

        Args:
            tournament_id: Tournament ID.

        Returns:
            Dict with file categories and their availability.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        if not path.exists():
            return {}

        files = {
            "config": (path / "config.json").exists(),
            "scores": (path / "scores.csv").exists(),
            "type_scores": (path / "type_scores.csv").exists(),
            "all_scores": (path / "all_scores.csv").exists(),
            "details": (path / "details.csv").exists(),
            "negotiations_dir": (path / "negotiations").exists(),
            "scenarios_dir": (path / "scenarios").exists(),
            "plots_dir": (path / "plots").exists(),
            "results_dir": (path / "results").exists(),
            "negotiator_behavior_dir": (path / "negotiator_behavior").exists(),
        }

        # Count files in subdirectories
        if files["negotiations_dir"]:
            files["negotiations_count"] = len(
                list((path / "negotiations").glob("*.csv"))
            )
        if files["scenarios_dir"]:
            files["scenarios_count"] = len(list((path / "scenarios").iterdir()))
        if files["plots_dir"]:
            files["plots_count"] = len(list((path / "plots").glob("*")))

        return files

    @classmethod
    def get_outcome_space_data(
        cls, tournament_id: str, scenario_name: str, max_samples: int = 50000
    ) -> dict | None:
        """Compute outcome space data for a saved scenario.

        This loads the scenario using negmas.Scenario.load() and computes
        the outcome_space_data including Pareto frontier and special points.

        Args:
            tournament_id: Tournament ID.
            scenario_name: Name of the scenario.
            max_samples: Maximum outcomes to sample for display.

        Returns:
            Dict with outcome_space_data in the format expected by the UI, or None.
        """
        from negmas import Scenario

        from .outcome_analysis import compute_outcome_space_data

        path = cls.TOURNAMENTS_DIR / tournament_id
        scenario_dir = path / "scenarios" / scenario_name

        if not scenario_dir.exists():
            return None

        try:
            # Load the scenario using negmas - this gives us ufuns and outcome_space
            scenario = Scenario.load(scenario_dir, load_stats=True, load_info=True)

            # Compute outcome space data
            osd = compute_outcome_space_data(
                scenario, max_samples=max_samples, use_cached_stats=True
            )

            # Convert to JSON-serializable format
            return {
                "outcome_utilities": osd.outcome_utilities,
                "pareto_utilities": osd.pareto_utilities,
                "nash_point": osd.nash_point.utilities if osd.nash_point else None,
                "kalai_point": osd.kalai_point.utilities if osd.kalai_point else None,
                "kalai_smorodinsky_point": osd.kalai_smorodinsky_point.utilities
                if osd.kalai_smorodinsky_point
                else None,
                "max_welfare_point": osd.max_welfare_point.utilities
                if osd.max_welfare_point
                else None,
                "total_outcomes": osd.total_outcomes,
                "sampled": osd.sampled,
                "sample_size": osd.sample_size,
            }

        except Exception as e:
            print(f"Error computing outcome_space_data for {scenario_name}: {e}")
            return None

    @classmethod
    def get_score_analysis(
        cls,
        tournament_id: str,
        metric: str = "utility",
        statistic: str = "mean",
        filter_scenario: str | None = None,
        filter_partner: str | None = None,
    ) -> dict | None:
        """Compute aggregated scores by strategy for a given metric and statistic.

        Args:
            tournament_id: Tournament ID.
            metric: The score metric to analyze (utility, advantage, welfare,
                   nash_optimality, kalai_optimality, ks_optimality,
                   max_welfare_optimality, pareto_optimality, partner_welfare, time).
            statistic: The aggregation statistic (mean, median, min, max, std,
                      truncated_mean, count, sum).
            filter_scenario: Optional scenario name to filter by.
            filter_partner: Optional partner strategy to filter by.

        Returns:
            Dict with leaderboard data and metadata.
        """
        import statistics
        from collections import defaultdict

        scores_data = cls.get_all_scores_csv(tournament_id)
        if not scores_data:
            return None

        # Numeric metrics that can be aggregated
        numeric_metrics = [
            "utility",
            "reserved_value",
            "advantage",
            "partner_welfare",
            "welfare",
            "time",
            "nash_optimality",
            "kalai_optimality",
            "ks_optimality",
            "max_welfare_optimality",
            "pareto_optimality",
        ]

        if metric not in numeric_metrics:
            return {"error": f"Invalid metric: {metric}. Valid: {numeric_metrics}"}

        # Group scores by strategy
        strategy_scores: dict[str, list[float]] = defaultdict(list)
        scenarios_seen: set[str] = set()
        partners_seen: set[str] = set()

        for row in scores_data:
            strategy = row.get("strategy", "Unknown")
            scenario = row.get("scenario", "")
            partners = row.get("partners", "")

            scenarios_seen.add(scenario)
            partners_seen.add(partners)

            # Apply filters
            if filter_scenario and scenario != filter_scenario:
                continue
            if filter_partner and partners != filter_partner:
                continue

            # Get the metric value
            value_str = row.get(metric, "")
            if not value_str:
                continue

            try:
                value = float(value_str)
                strategy_scores[strategy].append(value)
            except (ValueError, TypeError):
                continue

        if not strategy_scores:
            return {
                "leaderboard": [],
                "metric": metric,
                "statistic": statistic,
                "scenarios": sorted(scenarios_seen),
                "partners": sorted(partners_seen),
            }

        # Compute the requested statistic for each strategy
        def compute_stat(values: list[float], stat: str) -> float | None:
            if not values:
                return None
            try:
                if stat == "mean":
                    return statistics.mean(values)
                elif stat == "median":
                    return statistics.median(values)
                elif stat == "min":
                    return min(values)
                elif stat == "max":
                    return max(values)
                elif stat == "std":
                    return statistics.stdev(values) if len(values) > 1 else 0.0
                elif stat == "sum":
                    return sum(values)
                elif stat == "count":
                    return float(len(values))
                elif stat == "truncated_mean":
                    # Remove top and bottom 10%
                    if len(values) < 5:
                        return statistics.mean(values)
                    sorted_vals = sorted(values)
                    trim = max(1, len(sorted_vals) // 10)
                    trimmed = sorted_vals[trim:-trim] if trim > 0 else sorted_vals
                    return (
                        statistics.mean(trimmed) if trimmed else statistics.mean(values)
                    )
                else:
                    return statistics.mean(values)
            except Exception:
                return None

        # Build leaderboard
        leaderboard = []
        for strategy, values in strategy_scores.items():
            score = compute_stat(values, statistic)
            if score is not None:
                leaderboard.append(
                    {
                        "strategy": strategy,
                        "score": score,
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": statistics.mean(values),
                        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                    }
                )

        # Sort by score (descending for most metrics, ascending for time)
        reverse = metric != "time"
        leaderboard.sort(key=lambda x: x["score"], reverse=reverse)

        # Add rank
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return {
            "leaderboard": leaderboard,
            "metric": metric,
            "statistic": statistic,
            "available_metrics": numeric_metrics,
            "available_statistics": [
                "mean",
                "median",
                "min",
                "max",
                "std",
                "truncated_mean",
                "count",
                "sum",
            ],
            "scenarios": sorted(scenarios_seen),
            "partners": sorted(partners_seen),
            "filter_scenario": filter_scenario,
            "filter_partner": filter_partner,
        }
