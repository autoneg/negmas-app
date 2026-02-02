"""Tournament storage service for loading saved tournament results."""

import ast
import csv
import json
import logging
import math
import shutil
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from negmas.mechanisms import CompletedRun
from negmas.tournaments.neg import SimpleTournamentResults

logger = logging.getLogger(__name__)


@dataclass
class CombineResult:
    """Result of combining tournaments."""

    success: bool
    output_path: str | None = None
    output_id: str | None = None
    n_tournaments: int = 0
    n_negotiations: int = 0
    n_scenarios: int = 0
    n_competitors: int = 0
    loaded_paths: list[str] = field(default_factory=list)
    error: str | None = None


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
    """Service for loading saved tournament results from cartesian_tournament.

    This service handles tournament results saved in any format (csv, gzip, parquet)
    by using negmas.SimpleTournamentResults.load() for robust format detection.
    """

    TOURNAMENTS_DIR = Path.home() / "negmas" / "app" / "tournaments"

    # Cache for loaded tournament results (path -> SimpleTournamentResults)
    _results_cache: dict[str, SimpleTournamentResults] = {}

    @staticmethod
    def _parse_python_list_string(s: str) -> list[str] | None:
        """Parse a Python list or tuple string representation.

        Handles formats like: "['Atlas3', 'Aspiration']" or "('Atlas3', 'Aspiration')"

        Args:
            s: String to parse

        Returns:
            List of strings or None if not a list/tuple format
        """
        if not s or not isinstance(s, str):
            return None

        s = s.strip()

        # Check if it looks like a Python list or tuple
        if (s.startswith("[") and s.endswith("]")) or (
            s.startswith("(") and s.endswith(")")
        ):
            # Remove outer brackets/parens
            inner = s[1:-1].strip()
            if not inner:
                return []

            # Split by comma, handling quoted strings properly
            items = []
            current = ""
            in_quote = False
            quote_char = None

            for i, char in enumerate(inner):
                if char in ('"', "'") and (i == 0 or inner[i - 1] != "\\"):
                    if not in_quote:
                        in_quote = True
                        quote_char = char
                    elif char == quote_char:
                        in_quote = False
                        quote_char = None
                    else:
                        current += char
                elif char == "," and not in_quote:
                    items.append(current.strip())
                    current = ""
                else:
                    current += char

            # Don't forget the last item
            if current.strip():
                items.append(current.strip())

            return items

        return None

    @staticmethod
    def _sanitize_for_json(obj: Any) -> Any:
        """Sanitize values for JSON serialization.

        Converts pandas NaN/NaT and numpy types to JSON-compatible values.
        Also parses Python list/tuple string representations into actual lists.
        """
        if obj is None:
            return None
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, int | bool):
            return obj
        if isinstance(obj, str):
            # Try to parse Python list/tuple string representations
            parsed = TournamentStorageService._parse_python_list_string(obj)
            if parsed is not None:
                return [TournamentStorageService._sanitize_for_json(v) for v in parsed]
            return obj
        if isinstance(obj, dict):
            return {
                k: TournamentStorageService._sanitize_for_json(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list | tuple):
            return [TournamentStorageService._sanitize_for_json(v) for v in obj]
        # Handle numpy arrays
        if hasattr(obj, "__array__"):
            return [
                TournamentStorageService._sanitize_for_json(item)
                for item in obj.tolist()
            ]
        # Handle numpy numeric types
        if hasattr(obj, "item"):
            try:
                val = obj.item()
                # Check for nan/inf after converting numpy to Python
                if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    return None
                return val
            except (ValueError, AttributeError):
                pass
        # Handle pandas/numpy NaN (use try/except to avoid array ambiguity)
        try:
            if pd.isna(obj):
                return None
        except (ValueError, TypeError):
            pass
        return obj

    @classmethod
    def _load_results(cls, path: Path) -> SimpleTournamentResults | None:
        """Load tournament results using SimpleTournamentResults.load().

        This handles all storage formats (csv, gzip, parquet) automatically.

        Args:
            path: Path to tournament directory.

        Returns:
            SimpleTournamentResults or None if loading fails.
        """
        path_str = str(path)
        if path_str in cls._results_cache:
            return cls._results_cache[path_str]

        try:
            # Suppress numpy/pandas warnings about empty arrays or single values
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="invalid value encountered")
                warnings.filterwarnings("ignore", message="Degrees of freedom")
                results = SimpleTournamentResults.load(
                    path,
                    must_have_details=False,
                    memory_optimization="balanced",  # Keep details in memory, compute scores on demand
                )
            cls._results_cache[path_str] = results
            return results
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error loading tournament results from {path}: {e}")
            return None

    @classmethod
    def clear_cache(cls, tournament_id: str | None = None) -> None:
        """Clear the results cache.

        Args:
            tournament_id: If provided, only clear cache for this tournament.
                          If None, clear entire cache.
        """
        if tournament_id:
            path_str = str(cls.TOURNAMENTS_DIR / tournament_id)
            cls._results_cache.pop(path_str, None)
        else:
            cls._results_cache.clear()

    @classmethod
    def _check_tournament_files_exist(cls, path: Path) -> bool:
        """Check if a directory contains tournament result files.

        Checks for scores.csv (always present) or any format of details/all_scores.
        """
        # scores.csv is always present (small file, always CSV)
        if (path / "scores.csv").exists():
            return True

        # Check for any format of details or all_scores
        for base_name in ("details", "all_scores", "all_results"):
            for ext in (".csv", ".csv.gz", ".parquet"):
                if (path / f"{base_name}{ext}").exists():
                    return True

        return False

    @classmethod
    def list_saved_tournaments(
        cls, archived: bool | None = None, tags: list[str] | None = None
    ) -> list[dict]:
        """List all saved tournaments from disk.

        Scans ~/negmas/app/tournaments/ for tournament result directories.
        Supports all storage formats (csv, gzip, parquet).

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

            # Check for required files (any format)
            if not cls._check_tournament_files_exist(path):
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
        """Load summary info for a tournament directory.

        Optimized for fast listing - only reads minimal data.
        """
        try:
            tournament_id = path.name

            # Get creation time from directory
            created_at = None
            try:
                stat = path.stat()
                created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except Exception:
                pass

            # Quick check: is tournament complete? (scores file exists)
            is_complete = (
                (path / "scores.csv").exists()
                or (path / "scores.csv.gz").exists()
                or (path / "scores.parquet").exists()
            )

            # Fast competitor count: read scores file header only
            competitors: set[str] = set()
            n_competitors = 0
            try:
                scores_file = path / "scores.csv"
                if not scores_file.exists():
                    scores_file = path / "scores.csv.gz"
                if scores_file.exists():
                    import gzip

                    if scores_file.suffix == ".gz":
                        with gzip.open(scores_file, "rt") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if row.get("strategy"):
                                    competitors.add(row["strategy"])
                    else:
                        with open(scores_file, "r") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if row.get("strategy"):
                                    competitors.add(row["strategy"])
                    n_competitors = len(competitors)
            except Exception:
                pass

            # Fast scenario count: count subdirectories in scenarios/
            n_scenarios = 0
            scenarios_dir = path / "scenarios"
            if scenarios_dir.exists() and scenarios_dir.is_dir():
                try:
                    n_scenarios = sum(1 for p in scenarios_dir.iterdir() if p.is_dir())
                except Exception:
                    pass

            # Fast negotiation count from various sources
            n_negotiations = 0

            # Priority 1: Count folders in negotiations/ directory
            negotiations_dir = path / "negotiations"
            if negotiations_dir.exists() and negotiations_dir.is_dir():
                try:
                    n_negotiations = sum(
                        1
                        for p in negotiations_dir.iterdir()
                        if p.is_dir() or p.suffix in {".json", ".gz", ".yaml"}
                    )
                except Exception:
                    pass

            # Priority 2: Read row count from details.parquet (fast metadata read)
            if n_negotiations == 0 and (path / "details.parquet").exists():
                try:
                    import pyarrow.parquet as pq

                    parquet_file = pq.ParquetFile(path / "details.parquet")
                    n_negotiations = parquet_file.metadata.num_rows
                except Exception:
                    pass

            # Priority 3: Count files in details/ directory (legacy format)
            details_dir = path / "details"
            if n_negotiations == 0 and details_dir.exists() and details_dir.is_dir():
                try:
                    n_negotiations = sum(
                        1
                        for p in details_dir.iterdir()
                        if p.is_file() and p.suffix in {".json", ".gz"}
                    )
                except Exception:
                    pass

            # Priority 4: Read line count from CSV (slower fallback)
            if n_negotiations == 0:
                details_file = None
                if (path / "details.csv").exists():
                    details_file = path / "details.csv"
                elif (path / "details.csv.gz").exists():
                    details_file = path / "details.csv.gz"

                if details_file:
                    try:
                        if details_file.suffix == ".gz":
                            import gzip

                            with gzip.open(details_file, "rt") as f:
                                n_negotiations = sum(1 for _ in f) - 1  # -1 for header
                        else:
                            with open(details_file, "r") as f:
                                n_negotiations = sum(1 for _ in f) - 1  # -1 for header
                    except Exception:
                        pass

            # Estimate agreements (skip for now to keep it fast)
            n_agreements = 0
            agreement_rate = 0.0

            # Calculate total expected negotiations for stats
            # total = n_competitors * n_competitors * n_scenarios (for self-play cartesian tournament)
            # This is an estimate - actual may vary based on n_repetitions
            total = (
                n_negotiations  # Use actual count as total since tournament is complete
            )
            completed = (
                n_negotiations  # All negotiations are completed in saved tournaments
            )
            n_errors = 0  # Would need to scan details to get this - skip for speed

            # Load metadata (tags, archived status)
            metadata = cls._load_metadata(tournament_id)

            return {
                "id": tournament_id,
                "path": str(path),
                "name": tournament_id,
                "created_at": created_at,
                "is_complete": is_complete,
                "n_scenarios": n_scenarios,
                "n_competitors": n_competitors,
                "n_negotiations": n_negotiations,
                "n_agreements": n_agreements,  # Set to 0 for fast loading
                "agreement_rate": agreement_rate,  # Set to 0 for fast loading
                "total": total,
                "completed": completed,
                "n_errors": n_errors,
                "tags": metadata.get("tags", []),
                "archived": metadata.get("archived", False),
            }
        except Exception as e:
            logger.info(f"Error loading tournament summary from {path}: {e}")
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

        # Build gridInit and cellStates for frontend
        gridInit, cellStates = cls._build_grid_structures(path, negotiations)

        # Build leaderboard from scores
        leaderboard = [
            {
                "name": s["name"],
                "rank": s["rank"],
                "score": s.get("score"),
                "mean_utility": s.get("mean_utility"),
                "n_negotiations": s.get("n_negotiations", 0),
            }
            for s in scores
        ]

        result = {
            **summary,
            "scores": scores,
            "negotiations": negotiations,
            "gridInit": gridInit,
            "cellStates": cellStates,
            "leaderboard": leaderboard,
        }

        # Also load config if available
        config = cls.get_tournament_config(tournament_id)
        if config:
            result["config"] = config

        # Sanitize for JSON serialization
        return cls._sanitize_for_json(result)

    @classmethod
    def _load_scores(cls, path: Path) -> list[dict]:
        """Load competitor scores using SimpleTournamentResults.

        Uses SimpleTournamentResults.load() which handles all storage formats
        automatically and provides final_scores and scores_summary DataFrames.
        """
        scores = []

        # Load results using SimpleTournamentResults
        results = cls._load_results(path)
        if results is None:
            logger.warning(f"Could not load tournament results from {path}")
            return scores

        try:
            # Get final scores (strategy name + score)
            final_scores_df = results.final_scores
            if final_scores_df is None or len(final_scores_df) == 0:
                logger.warning(f"No final scores found in {path}")
                return scores

            # Get scores summary for detailed stats (indexed by strategy name)
            scores_summary = results.scores_summary

            # Build scores list from final_scores
            for idx, row in final_scores_df.iterrows():
                name = str(row.get("strategy", str(idx)))
                score = row.get("score")

                # Safely convert score to float, handling None/-inf
                score_val: float | None = None
                if score is not None:
                    try:
                        score_float = float(score)
                        if pd.notna(score_float) and score_float != float("-inf"):
                            score_val = score_float
                    except (ValueError, TypeError):
                        pass

                entry: dict = {
                    "name": name,
                    "rank": int(str(idx)) if idx is not None else 0,
                    "score": score_val,
                    "raw_data": cls._sanitize_for_json(row.to_dict()),
                }

                # Enrich with scores_summary data if available
                if scores_summary is not None and name in scores_summary.index:
                    summary_row = scores_summary.loc[name]

                    # Helper to safely get stat value
                    def get_stat(metric: str, stat: str) -> float | None:
                        try:
                            val = summary_row.get((metric, stat))
                            if (
                                val is not None
                                and pd.notna(val)
                                and val != float("-inf")
                                and val != float("inf")
                            ):
                                return float(val)
                        except (KeyError, TypeError):
                            pass
                        return None

                    entry["mean_utility"] = get_stat("utility", "mean")
                    entry["n_negotiations"] = int(get_stat("utility", "count") or 0)
                    entry["mean_advantage"] = get_stat("advantage", "mean")
                    entry["mean_welfare"] = get_stat("welfare", "mean")
                    entry["mean_nash_optimality"] = get_stat("nash_optimality", "mean")
                    entry["mean_pareto_optimality"] = get_stat(
                        "pareto_optimality", "mean"
                    )

                    # Include full type_scores for detailed views
                    type_scores = {}
                    for col in scores_summary.columns:
                        metric, stat = col
                        if metric not in type_scores:
                            type_scores[metric] = {}
                        val = get_stat(metric, stat)
                        type_scores[metric][stat] = val
                    entry["type_scores"] = type_scores

                scores.append(entry)

            # Sort by score descending and reassign ranks
            scores.sort(key=lambda x: x.get("score") or float("-inf"), reverse=True)
            for idx, s in enumerate(scores):
                s["rank"] = idx + 1

        except Exception as e:
            logger.error(f"Error loading scores from {path}: {e}")

        return scores

    @classmethod
    def _build_grid_structures(
        cls, path: Path, negotiations: list[dict]
    ) -> tuple[dict, dict]:
        """Build gridInit and cellStates structures from saved tournament data.

        This reconstructs the grid data structures that the frontend expects.

        Args:
            path: Path to tournament directory.
            negotiations: List of negotiation summaries.

        Returns:
            Tuple of (gridInit, cellStates) dicts.
        """
        # Extract unique competitors and scenarios
        competitors_set = set()
        scenarios_set = set()

        for neg in negotiations:
            partners = neg.get("partners", [])
            competitors_set.update(partners)
            scenario = neg.get("scenario")
            if scenario:
                scenarios_set.add(scenario)

        competitors = sorted(list(competitors_set))
        scenarios = sorted(list(scenarios_set))
        opponents = competitors  # In cartesian tournaments, opponents = competitors

        # Build gridInit
        gridInit = {
            "competitors": competitors,
            "opponents": opponents,
            "scenarios": scenarios,
            "total_negotiations": len(negotiations),
            "n_competitors": len(competitors),
            "n_scenarios": len(scenarios),
        }

        # Build cellStates (map of cell_id -> state)
        # For completed tournaments, we aggregate multiple negotiations per cell
        # (since there can be multiple repetitions)
        cellStates = {}

        for neg in negotiations:
            partners = neg.get("partners", [])
            scenario = neg.get("scenario")

            # Create cell keys for each partner combination
            if len(partners) >= 2 and scenario:
                # In a cartesian tournament, each negotiation involves 2 partners
                competitor = partners[0]
                opponent = partners[1]

                cell_id = f"{competitor}::{opponent}::{scenario}"

                # Determine the status based on negotiation outcome
                status = "complete"
                if neg.get("has_error", False):
                    status = "error"
                elif neg.get("broken", False):
                    status = "broken"
                elif neg.get("timedout", False):
                    status = "timeout"

                # Helper to safely get boolean values (handles arrays, Series, etc.)
                def _safe_bool(value, default=False):
                    if value is None:
                        return default
                    # Handle numpy/pandas arrays or Series
                    if hasattr(value, "__iter__") and not isinstance(value, str):
                        try:
                            # Try to get first element for arrays/Series
                            return bool(value[0]) if len(value) > 0 else default
                        except (TypeError, IndexError):
                            return default
                    return bool(value)

                # Get boolean values safely
                has_agreement = _safe_bool(neg.get("has_agreement", False))
                has_error = _safe_bool(neg.get("has_error", False))
                timedout = _safe_bool(neg.get("timedout", False))
                broken = _safe_bool(neg.get("broken", False))

                # If cell doesn't exist yet, create it
                if cell_id not in cellStates:
                    cellStates[cell_id] = {
                        "status": status,
                        "cell_id": cell_id,
                        "competitor": competitor,
                        "opponent": opponent,
                        "scenario": scenario,
                        "has_agreement": has_agreement,
                        "utilities": neg.get("utilities"),
                        "total": 1,
                        "completed": 1,
                        "agreements": 1 if has_agreement else 0,
                        "errors": 1 if has_error else 0,
                        "timeouts": 1 if timedout else 0,
                        "broken": 1 if broken else 0,
                    }
                else:
                    # Aggregate multiple repetitions
                    cell = cellStates[cell_id]
                    cell["total"] += 1
                    cell["completed"] += 1
                    if has_agreement:
                        cell["agreements"] += 1
                    if has_error:
                        cell["errors"] += 1
                    if timedout:
                        cell["timeouts"] += 1
                    if broken:
                        cell["broken"] += 1

                    # Update status to worst case (error > timeout > broken > complete)
                    if cell["errors"] > 0:
                        cell["status"] = "error"
                    elif cell["timeouts"] > 0:
                        cell["status"] = "timeout"
                    elif cell["broken"] > 0:
                        cell["status"] = "broken"
                    else:
                        cell["status"] = "complete"

                    # Update has_agreement to reflect if ANY had agreement
                    if has_agreement:
                        cell["has_agreement"] = True

        return gridInit, cellStates

    @classmethod
    def _load_negotiations_summary(cls, path: Path) -> list[dict]:
        """Load negotiation results summary using SimpleTournamentResults.

        Handles all storage formats (csv, gzip, parquet) automatically.
        """
        negotiations = []

        # Use SimpleTournamentResults for format-agnostic loading
        results = cls._load_results(path)
        if results is None:
            return negotiations

        try:
            details_df = results.details
            if details_df is None or len(details_df) == 0:
                return negotiations

            for idx, row in details_df.iterrows():
                # Get partners - cartesian_tournament uses 'partners' field as list
                partners = []
                partners_val = row.get("partners")
                if partners_val is not None:
                    if isinstance(partners_val, (list, tuple)):
                        partners = list(partners_val)
                    elif isinstance(partners_val, str) and partners_val != "[]":
                        try:
                            # Parse list like "['AspirationNegotiator', 'BoulwareTBNegotiator']"
                            parsed = ast.literal_eval(partners_val)
                            if isinstance(parsed, (list, tuple)):
                                partners = list(parsed)
                        except (ValueError, SyntaxError) as e:
                            logger.warning(
                                f"Failed to parse partners string in list: {partners_val[:100]}, error: {e}"
                            )
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
                            partners.append(str(row[key]))

                # Get scenario
                scenario = row.get("scenario") or row.get("domain") or "Unknown"

                # Get agreement
                agreement_val = row.get("agreement")
                # pd.notna returns array for lists, so check scalar first
                has_agreement = agreement_val is not None and (
                    isinstance(agreement_val, (list, tuple, dict))
                    or (
                        str(agreement_val) != ""
                        and str(agreement_val) != "None"
                        and pd.notna(agreement_val)
                    )
                )

                # Get utilities - cartesian_tournament uses 'utilities' field
                utilities = []
                utilities_val = row.get("utilities")
                if utilities_val is not None:
                    if isinstance(utilities_val, (list, tuple)):
                        utilities = [float(u) for u in utilities_val if pd.notna(u)]
                    elif isinstance(utilities_val, str):
                        try:
                            utils_tuple = ast.literal_eval(utilities_val)
                            utilities = (
                                list(utils_tuple)
                                if isinstance(utils_tuple, (list, tuple))
                                else []
                            )
                        except (ValueError, SyntaxError):
                            pass

                # Fall back to individual fields
                if not utilities:
                    for key in ["utility0", "utility1", "u0", "u1"]:
                        val = row.get(key)
                        if val is not None and pd.notna(val):
                            try:
                                utilities.append(float(val))
                            except (ValueError, TypeError):
                                pass

                # Get agreement data
                agreement_val = row.get("agreement")
                # pd.notna returns array for lists, so check scalar first
                has_agreement = agreement_val is not None and (
                    isinstance(agreement_val, (list, tuple, dict))
                    or (
                        str(agreement_val) != ""
                        and str(agreement_val) != "None"
                        and pd.notna(agreement_val)
                    )
                )

                # Parse agreement dict if available
                agreement_dict = None
                if has_agreement:
                    try:
                        if isinstance(agreement_val, dict):
                            agreement_dict = agreement_val
                        elif isinstance(agreement_val, (list, tuple)):
                            # Agreement is already a list/tuple, keep as is
                            agreement_dict = list(agreement_val)
                        elif isinstance(agreement_val, str):
                            # Try to parse - could be dict, list, or tuple
                            parsed = ast.literal_eval(agreement_val)
                            agreement_dict = parsed
                    except (ValueError, SyntaxError) as e:
                        logger.warning(
                            f"Failed to parse agreement in list: {str(agreement_val)[:100]}, error: {e}"
                        )
                        # Keep as string if parsing fails
                        agreement_dict = str(agreement_val)

                # Get timestamp - check various possible fields
                timestamp = None
                for key in ["timestamp", "time", "completed_at", "end_time"]:
                    val = row.get(key)
                    if val is not None and pd.notna(val):
                        timestamp = val
                        break

                negotiations.append(
                    {
                        "index": idx,
                        "scenario": scenario,
                        "partners": partners,
                        "has_agreement": has_agreement,
                        "agreement_dict": agreement_dict,
                        "utilities": utilities if utilities else None,
                        "timestamp": timestamp,
                        "raw_data": cls._sanitize_for_json(
                            row.to_dict() if hasattr(row, "to_dict") else dict(row)
                        ),
                    }
                )

        except Exception as e:
            logger.info(f"Error loading negotiations from {path}: {e}")

        return negotiations

    @classmethod
    def get_tournament_negotiation(cls, tournament_id: str, index: int) -> dict | None:
        """Get full details of a specific negotiation from a tournament.

        Uses SimpleTournamentResults for format-agnostic loading and enriches
        with scenario data (issue_names, outcome_space_data) and negotiation history.

        Args:
            tournament_id: Tournament ID.
            index: Index of the negotiation in details.

        Returns:
            Full negotiation data with history, scenario info, and outcome_space_data, or None if not found.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id

        # Use SimpleTournamentResults for format-agnostic loading
        results = cls._load_results(path)
        if results is None:
            return None

        try:
            details_df = results.details
            if details_df is None or len(details_df) == 0:
                return None

            # Get the row at the specified index
            if index < 0 or index >= len(details_df):
                return None

            row = details_df.iloc[index]

            # Parse partners
            partners = []
            partners_val = row.get("partners")
            if partners_val is not None:
                if isinstance(partners_val, (list, tuple)):
                    partners = list(partners_val)
                elif isinstance(partners_val, str) and partners_val != "[]":
                    try:
                        parsed = ast.literal_eval(partners_val)
                        if isinstance(parsed, (list, tuple)):
                            partners = list(parsed)
                    except (ValueError, SyntaxError) as e:
                        logger.warning(
                            f"Failed to parse partners string: {partners_val[:100]}, error: {e}"
                        )
                        pass

            # Fall back to individual fields
            if not partners:
                for k in ["negotiator0", "negotiator1", "first", "second"]:
                    if row.get(k):
                        partners.append(str(row[k]))

            # Parse utilities
            utilities = None
            utilities_val = row.get("utilities")
            if utilities_val is not None:
                if isinstance(utilities_val, (list, tuple)):
                    utilities = [float(u) for u in utilities_val if pd.notna(u)]
                elif isinstance(utilities_val, str):
                    try:
                        utils_tuple = ast.literal_eval(utilities_val)
                        utilities = (
                            list(utils_tuple)
                            if isinstance(utils_tuple, (list, tuple))
                            else None
                        )
                    except (ValueError, SyntaxError):
                        pass

            # Fall back to individual fields
            if not utilities:
                utilities = []
                for k in ["utility0", "utility1", "u0", "u1"]:
                    val = row.get(k)
                    if val is not None and pd.notna(val):
                        try:
                            utilities.append(float(val))
                        except (ValueError, TypeError):
                            pass
                utilities = utilities if utilities else None

            # Get agreement value and parse it properly
            agreement_val = row.get("agreement")
            has_agreement = (
                agreement_val is not None
                and str(agreement_val) != ""
                and str(agreement_val) != "None"
                and pd.notna(agreement_val)
            )

            # Parse agreement - convert string representation to actual list/tuple
            agreement_parsed = None
            if has_agreement:
                if isinstance(agreement_val, (list, tuple)):
                    # Already a list/tuple
                    agreement_parsed = list(agreement_val)
                elif isinstance(agreement_val, str):
                    try:
                        # Try to parse string representation like "('Macintosh', '60 Gb', \"19''LCD\")"
                        parsed = ast.literal_eval(agreement_val)
                        if isinstance(parsed, (list, tuple)):
                            agreement_parsed = list(parsed)
                        else:
                            # If parsing fails or returns non-sequence, keep as string
                            agreement_parsed = agreement_val
                    except (ValueError, SyntaxError) as e:
                        logger.warning(
                            f"Failed to parse agreement string: {agreement_val[:100]}, error: {e}"
                        )
                        # Keep as string if parsing fails
                        agreement_parsed = agreement_val
                else:
                    # Other types (dict, int, etc.) - keep as is
                    agreement_parsed = agreement_val

            # Get scenario name
            scenario_name = row.get("scenario") or row.get("domain")

            # Get mechanism_name for loading trace
            mechanism_name = row.get("mechanism_name")

            # Load scenario info (issue_names, etc.)
            scenario_info = None
            issue_names = []
            if scenario_name:
                scenario_info = cls.get_scenario_info(tournament_id, scenario_name)
                if scenario_info:
                    issue_names = scenario_info.get("issue_names", [])

            # Load negotiation history/trace
            history = []
            if scenario_name and partners:
                # Try to find the negotiation trace file by scenario and partners
                trace_data = cls.get_negotiation_trace_by_partners(
                    tournament_id, scenario_name, partners
                )
                if trace_data:
                    history = trace_data.get("trace", [])
                # Fallback to mechanism_name if available
                elif mechanism_name:
                    trace_data = cls.get_negotiation_trace(
                        tournament_id, mechanism_name
                    )
                    if trace_data:
                        history = trace_data.get("trace", [])

            # Load outcome_space_data for visualization
            outcome_space_data = None
            if scenario_name:
                outcome_space_data = cls.get_outcome_space_data(
                    tournament_id, scenario_name
                )

            # Build the complete negotiation object
            negotiation = {
                "index": index,
                "raw_data": cls._sanitize_for_json(
                    row.to_dict() if hasattr(row, "to_dict") else dict(row)
                ),
                "scenario": scenario_name,
                "partners": partners,
                "agreement": agreement_parsed,  # Use parsed agreement, not str(agreement_val)
                "utilities": utilities,
                "has_agreement": has_agreement,
                "issue_names": issue_names,
                "history": history,
                "outcome_space_data": outcome_space_data,
                "source": "tournament",  # For frontend to know this is from a tournament
                "mechanism_name": mechanism_name,
            }

            return negotiation

        except Exception as e:
            logger.error(f"Error loading negotiation {index} from {tournament_id}: {e}")

        return None

    @classmethod
    def get_negotiation_path_by_run_id(
        cls, tournament_id: str, run_id: str
    ) -> Path | None:
        """Get the path to a negotiation file/folder by its run_id.

        The run_id is expected to be the full folder/file name as generated by
        negmas.tournaments.neg.simple.cartesian._get_run_file_name().

        Args:
            tournament_id: Tournament ID.
            run_id: The negotiation folder/file name (without extension).

        Returns:
            Path to the negotiation file or directory, or None if not found.
        """
        negotiations_dir = cls.TOURNAMENTS_DIR / tournament_id / "negotiations"

        if not negotiations_dir.exists():
            return None

        # run_id is the exact folder/file name - check directly
        exact_path = negotiations_dir / run_id
        if exact_path.exists():
            return exact_path

        # Try with common extensions for single-file format
        for ext in [".csv", ".csv.gz", ".parquet"]:
            file_path = negotiations_dir / f"{run_id}{ext}"
            if file_path.exists():
                return file_path

        return None

    @classmethod
    def get_negotiation_by_run_id(cls, tournament_id: str, run_id: str) -> dict | None:
        """Get full negotiation data by its run_id (mechanism identifier).

        This is the preferred method for loading negotiation data as run_id uniquely
        identifies a negotiation. Uses CompletedRun.load() to load all data.

        Args:
            tournament_id: Tournament ID.
            run_id: The unique run_id of the negotiation.

        Returns:
            Full negotiation data with history, scenario info, and outcome_space_data,
            or None if not found.
        """
        neg_path = cls.get_negotiation_path_by_run_id(tournament_id, run_id)
        if neg_path is None:
            logger.warning(f"No negotiation found with run_id: {run_id}")
            return None

        try:
            # Load using CompletedRun.load() via our helper
            trace_data = cls._load_completed_run_as_dict(
                neg_path, mechanism_name=run_id
            )
            if trace_data is None:
                return None

            # Extract scenario and partners from loaded metadata
            metadata = trace_data.get("metadata", {})
            scenario_name = metadata.get("scenario_name")
            partners = metadata.get("partner_names", [])

            # Load scenario info for issue_names
            issue_names = []
            outcome_space_data = None
            scenario_info = None
            scenario_path = None
            if scenario_name:
                scenario_info = cls.get_scenario_info(tournament_id, scenario_name)
                if scenario_info:
                    issue_names = scenario_info.get("issue_names", [])

                # Load outcome_space_data for visualization
                outcome_space_data = cls.get_outcome_space_data(
                    tournament_id, scenario_name
                )

                # Build the scenario path for the StatsModal
                scenario_path = str(
                    cls.TOURNAMENTS_DIR / tournament_id / "scenarios" / scenario_name
                )

            # Build the complete negotiation object
            negotiation = {
                "run_id": run_id,
                "path": str(neg_path),  # Include path for direct loading
                "scenario": scenario_name,
                "scenario_path": scenario_path,  # For StatsModal
                "tournament_id": tournament_id,  # For tournament-specific API calls
                "partners": partners,
                "issue_names": issue_names,
                "history": trace_data.get("trace", []),
                "agreement": trace_data.get("agreement"),
                "outcome_space_data": outcome_space_data,
                "source": "tournament",
                "metadata": metadata,
                "config": trace_data.get("config"),
                "scenario_info": scenario_info,  # Include full scenario info with stats
            }

            # Add agreement stats if available
            if trace_data.get("agreement_stats"):
                negotiation["agreement_stats"] = trace_data["agreement_stats"]

            # Sanitize for JSON (handles inf, nan, numpy types)
            return cls._sanitize_for_json(negotiation)

        except Exception as e:
            logger.error(
                f"Error loading negotiation by run_id {run_id} from {tournament_id}: {e}"
            )
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

        # Find matching negotiation (file or directory) by mechanism_name suffix
        try:
            matching = list(negotiations_dir.glob(f"*_{mechanism_name}"))
            if not matching:
                # Try with common extensions for single-file format
                for ext in [".csv", ".csv.gz", ".parquet"]:
                    matching = list(negotiations_dir.glob(f"*_{mechanism_name}{ext}"))
                    if matching:
                        break
            if not matching:
                return None

            neg_path = matching[0]
            return cls._load_completed_run_as_dict(
                neg_path, mechanism_name=mechanism_name
            )

        except Exception as e:
            logger.info(f"Error loading negotiation trace {mechanism_name}: {e}")
            return None

    @classmethod
    def get_negotiation_trace_by_partners(
        cls, tournament_id: str, scenario_name: str, partners: list[str]
    ) -> dict | None:
        """Get the negotiation trace by matching scenario and partners.

        Args:
            tournament_id: Tournament ID.
            scenario_name: Name of the scenario.
            partners: List of partner negotiator names.

        Returns:
            Negotiation trace data with offers and responses, or None if not found.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id
        negotiations_dir = path / "negotiations"

        if not negotiations_dir.exists() or not partners:
            return None

        try:
            # Try both orderings of partners
            for partner_order in [partners, list(reversed(partners))]:
                # Build pattern: {scenario}_{partner1}_{partner2}_{rep}_*
                pattern = f"{scenario_name}_{'_'.join(partner_order)}_0_*"
                matching = list(negotiations_dir.glob(pattern))

                if matching:
                    neg_path = matching[0]
                    result = cls._load_completed_run_as_dict(
                        neg_path, scenario=scenario_name, partners=partner_order
                    )
                    if result:
                        return result

            return None

        except Exception as e:
            logger.error(
                f"Error loading negotiation trace for {scenario_name} with partners {partners}: {e}"
            )
            return None

    @classmethod
    def _load_completed_run_as_dict(
        cls,
        path: Path,
        mechanism_name: str | None = None,
        scenario: str | None = None,
        partners: list[str] | None = None,
    ) -> dict | None:
        """Load a negotiation from path (file or directory) using CompletedRun.

        Args:
            path: Path to negotiation file or directory.
            mechanism_name: Optional mechanism name for metadata.
            scenario: Optional scenario name for metadata.
            partners: Optional partner list for metadata.

        Returns:
            Dict with trace data and metadata, or None if loading fails.
        """
        try:
            completed_run = CompletedRun.load(
                path, load_scenario=False, load_config=True
            )

            # Convert history to list of dicts
            trace_data = []
            for entry in completed_run.history:
                if hasattr(entry, "_asdict"):
                    trace_data.append(entry._asdict())
                elif isinstance(entry, dict):
                    trace_data.append(entry)
                else:
                    # Tuple or other - convert based on history_type
                    trace_data.append({"data": entry})

            result = {
                "trace": trace_data,
                "history_type": completed_run.history_type,
                "agreement": completed_run.agreement,
                "config": completed_run.config,
                "metadata": completed_run.metadata,
                "path": str(path),
            }

            # Add optional metadata
            if mechanism_name:
                result["mechanism_name"] = mechanism_name
            if scenario:
                result["scenario"] = scenario
            if partners:
                result["partners"] = partners

            # Add agreement stats if available
            if completed_run.agreement_stats:
                result["agreement_stats"] = {
                    "pareto_optimality": completed_run.agreement_stats.pareto_optimality,
                    "nash_optimality": completed_run.agreement_stats.nash_optimality,
                    "kalai_optimality": completed_run.agreement_stats.kalai_optimality,
                    "max_welfare_optimality": completed_run.agreement_stats.max_welfare_optimality,
                    "ks_optimality": completed_run.agreement_stats.ks_optimality,
                }

            # Add outcome stats if available
            if completed_run.outcome_stats:
                result["outcome_stats"] = completed_run.outcome_stats

            return result

        except Exception as e:
            logger.warning(f"Failed to load CompletedRun from {path}: {e}")
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
            logger.info(
                f"Error loading scenario {scenario_name} from {tournament_id}: {e}"
            )
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
                logger.info(f"Error loading ufun {i} for {scenario_name}: {e}")
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
            logger.info(f"Error calculating utility: {e}")
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
        _issue_names = scenario_info.get("issue_names", []) if scenario_info else []

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
        path = cls.TOURNAMENTS_DIR / tournament_id
        if not path.exists():
            return False

        try:
            shutil.rmtree(path)
            return True
        except Exception as e:
            logger.info(f"Error deleting tournament {tournament_id}: {e}")
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
            logger.info(f"Error loading metadata for {tournament_id}: {e}")
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
            logger.info(f"Error saving metadata for {tournament_id}: {e}")
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
            logger.info(f"Error loading config for {tournament_id}: {e}")
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
            logger.info(f"Error loading scores.csv for {tournament_id}: {e}")
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
                        _stats = row
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
            logger.info(f"Error loading type_scores.csv for {tournament_id}: {e}")
            return None

    @classmethod
    def get_all_scores_csv(cls, tournament_id: str) -> list[dict] | None:
        """Get per-negotiation scores using SimpleTournamentResults.

        Handles all storage formats (csv, gzip, parquet) automatically.

        Args:
            tournament_id: Tournament ID.

        Returns:
            List of per-negotiation score dicts.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id

        # Use SimpleTournamentResults for format-agnostic loading
        results = cls._load_results(path)
        if results is None:
            return None

        try:
            scores_df = results.scores
            if scores_df is None or len(scores_df) == 0:
                return None

            scores = []
            for _, row in scores_df.iterrows():
                scores.append(cls._sanitize_for_json(row.to_dict()))
            return scores
        except Exception as e:
            logger.info(f"Error loading all_scores for {tournament_id}: {e}")
            return None

    @classmethod
    def get_details_csv(cls, tournament_id: str) -> list[dict] | None:
        """Get detailed negotiation results using SimpleTournamentResults.

        Handles all storage formats (csv, gzip, parquet) automatically.

        Args:
            tournament_id: Tournament ID.

        Returns:
            List of detailed negotiation result dicts.
        """
        path = cls.TOURNAMENTS_DIR / tournament_id

        # Use SimpleTournamentResults for format-agnostic loading
        results = cls._load_results(path)
        if results is None:
            return None

        try:
            details_df = results.details
            if details_df is None or len(details_df) == 0:
                return None

            details = []
            for _, row in details_df.iterrows():
                details.append(cls._sanitize_for_json(row.to_dict()))
            return details
        except Exception as e:
            logger.info(f"Error loading details for {tournament_id}: {e}")
            return None

    @classmethod
    def _file_exists_any_format(cls, path: Path, base_name: str) -> bool:
        """Check if a file exists in any supported format (csv, gzip, parquet)."""
        for ext in (".csv", ".csv.gz", ".parquet"):
            if (path / f"{base_name}{ext}").exists():
                return True
        return False

    @classmethod
    def get_tournament_files(cls, tournament_id: str) -> dict:
        """Get list of available files in the tournament directory.

        Supports format-agnostic detection (csv, gzip, parquet).

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
            "scores": (path / "scores.csv").exists(),  # Always CSV (small file)
            "type_scores": (path / "type_scores.csv").exists(),  # Always CSV
            "all_scores": cls._file_exists_any_format(path, "all_scores"),
            "details": cls._file_exists_any_format(path, "details"),
            "negotiations_dir": (path / "negotiations").exists(),
            "scenarios_dir": (path / "scenarios").exists(),
            "plots_dir": (path / "plots").exists(),
            "results_dir": (path / "results").exists(),
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
                scenario,
                max_samples=max_samples,
                use_cached_stats=True,
                scenario_path=str(scenario_dir),
            )

            # Convert to JSON-serializable format
            return {
                "outcome_utilities": osd.outcome_utilities,
                "pareto_utilities": osd.pareto_utilities,
                "reserved_values": osd.reserved_values,
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
            logger.info(f"Error computing outcome_space_data for {scenario_name}: {e}")
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
        # These match the columns available in all_scores.csv from negmas tournaments
        numeric_metrics = [
            "utility",
            "reserved_value",
            "advantage",
            "partner_welfare",
            "welfare",
            "time",
            # Optimality metrics (how close to optimal points)
            "nash_optimality",
            "kalai_optimality",
            "ks_optimality",
            "max_welfare_optimality",
            "pareto_optimality",
            # Additional optimality metrics from negmas
            "fairness",  # max(nash, kalai, ks optimality)
            "modified_kalai_optimality",
            "modified_ks_optimality",
        ]

        if metric not in numeric_metrics:
            return {"error": f"Invalid metric: {metric}. Valid: {numeric_metrics}"}

        # Group scores by strategy
        strategy_scores: dict[str, list[float]] = defaultdict(list)
        scenarios_seen: set[str] = set()
        partners_seen: set[str] = set()

        # Track which metrics actually have data
        available_metrics_in_data: set[str] = set()

        for row in scores_data:
            strategy = row.get("strategy", "Unknown")
            scenario = row.get("scenario", "")
            partners = row.get("partners", "")

            scenarios_seen.add(scenario)
            partners_seen.add(partners)

            # Track which metrics have data in this row
            for m in numeric_metrics:
                if row.get(m) not in (None, "", "nan", "NaN"):
                    try:
                        float(row.get(m))
                        available_metrics_in_data.add(m)
                    except (ValueError, TypeError):
                        pass

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
            "available_metrics": sorted(available_metrics_in_data)
            if available_metrics_in_data
            else numeric_metrics,
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

    @classmethod
    def load_full_negotiation(
        cls, tournament_id: str, negotiation_index: int
    ) -> dict | None:
        """Load complete negotiation data for display in UI panels.

        This method loads all data needed to display a negotiation from a tournament
        with full panel support (trace, utilities, outcome space, etc.).

        Args:
            tournament_id: Tournament ID.
            negotiation_index: Index of the negotiation in details.

        Returns:
            Complete negotiation data dict compatible with UI display, or None.
        """
        from .outcome_analysis import compute_outcome_space_data

        path = cls.TOURNAMENTS_DIR / tournament_id

        # Get the negotiation metadata from details
        neg_data = cls.get_tournament_negotiation(tournament_id, negotiation_index)
        if neg_data is None:
            return None

        raw_data = neg_data.get("raw_data", {})
        scenario_name = neg_data.get("scenario") or raw_data.get(
            "effective_scenario_name"
        )
        run_id = raw_data.get("run_id")

        if not scenario_name:
            return None

        # Load the scenario to get ufuns and outcome space
        scenario_dir = path / "scenarios" / scenario_name
        scenario = None
        ufuns = []
        outcome_space_data = None

        if scenario_dir.exists():
            try:
                from negmas import Scenario

                scenario = Scenario.load(scenario_dir, load_stats=True, load_info=True)
                if scenario:
                    ufuns = list(scenario.ufuns) if scenario.ufuns else []

                    # Compute outcome space data
                    osd = compute_outcome_space_data(
                        scenario,
                        max_samples=50000,
                        use_cached_stats=True,
                        scenario_path=str(scenario_dir),
                    )
                    outcome_space_data = {
                        "outcome_utilities": osd.outcome_utilities,
                        "pareto_utilities": osd.pareto_utilities,
                        "reserved_values": osd.reserved_values,
                        "nash_point": osd.nash_point.utilities
                        if osd.nash_point
                        else None,
                        "kalai_point": osd.kalai_point.utilities
                        if osd.kalai_point
                        else None,
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
                logger.info(f"Error loading scenario {scenario_name}: {e}")

        # Load the negotiation trace from negotiations folder
        _trace = []
        history = []  # History in UI format

        if run_id:
            trace_data = cls.get_negotiation_trace(tournament_id, str(run_id))
            if trace_data and trace_data.get("trace"):
                raw_trace = trace_data["trace"]

                # Convert trace to history format for UI
                for row in raw_trace:
                    step = int(row.get("step", 0))
                    negotiator_id = row.get("negotiator", "")
                    offer_str = row.get("offer", "")
                    relative_time = float(row.get("relative_time", 0))

                    # Parse offer
                    offer = None
                    if offer_str:
                        try:
                            offer = ast.literal_eval(offer_str)
                            if isinstance(offer, tuple):
                                offer = list(offer)
                        except (ValueError, SyntaxError):
                            offer = None

                    # Calculate utilities for this offer
                    offer_utilities = []
                    if offer and ufuns:
                        for ufun in ufuns:
                            try:
                                u = ufun(tuple(offer)) if offer else None
                                offer_utilities.append(
                                    float(u) if u is not None else None
                                )
                            except Exception:
                                offer_utilities.append(None)

                    history.append(
                        {
                            "step": step,
                            "negotiator": negotiator_id,
                            "offer": offer,
                            "utilities": offer_utilities if offer_utilities else None,
                            "relative_time": relative_time,
                            "response": row.get("responses", ""),
                        }
                    )

        # Parse partners/negotiator info
        partners = neg_data.get("partners", [])
        negotiator_names = []
        negotiator_types = []

        if raw_data.get("negotiator_names"):
            names_val = raw_data["negotiator_names"]
            if isinstance(names_val, str):
                try:
                    negotiator_names = ast.literal_eval(names_val)
                except (ValueError, SyntaxError):
                    pass
            elif isinstance(names_val, (list, tuple)):
                negotiator_names = list(names_val)

        if raw_data.get("negotiator_types"):
            types_val = raw_data["negotiator_types"]
            if isinstance(types_val, str):
                try:
                    negotiator_types = ast.literal_eval(types_val)
                except (ValueError, SyntaxError):
                    pass
            elif isinstance(types_val, (list, tuple)):
                negotiator_types = list(types_val)

        # Get final utilities
        final_utilities = neg_data.get("utilities") or []
        if not final_utilities and raw_data.get("utilities"):
            utils_val = raw_data["utilities"]
            if isinstance(utils_val, str):
                try:
                    parsed = ast.literal_eval(utils_val)
                    final_utilities = (
                        list(parsed) if isinstance(parsed, (list, tuple)) else []
                    )
                except (ValueError, SyntaxError):
                    pass

        # Get agreement
        agreement = None
        agreement_val = raw_data.get("agreement")
        if agreement_val and str(agreement_val) not in ("", "None"):
            if isinstance(agreement_val, str):
                try:
                    agreement = ast.literal_eval(agreement_val)
                    if isinstance(agreement, tuple):
                        agreement = list(agreement)
                except (ValueError, SyntaxError):
                    agreement = agreement_val
            else:
                agreement = agreement_val

        # Get issue names from scenario
        issue_names = []
        if scenario and scenario.outcome_space:
            try:
                issue_names = list(scenario.outcome_space.issues)
                issue_names = [
                    str(iss.name) if hasattr(iss, "name") else str(iss)
                    for iss in scenario.outcome_space.issues
                ]
            except Exception:
                pass

        # Build the complete result
        result = {
            "id": f"{tournament_id}_{negotiation_index}",
            "tournament_id": tournament_id,
            "negotiation_index": negotiation_index,
            "scenario": scenario_name,
            "status": "completed",
            "has_agreement": neg_data.get("has_agreement", False),
            "agreement": agreement,
            "final_utilities": final_utilities,
            "history": history,
            "n_steps": int(raw_data.get("n_steps", 0))
            if raw_data.get("n_steps")
            else len(history),
            "current_step": int(raw_data.get("last_step", 0))
            if raw_data.get("last_step")
            else len(history),
            "negotiators": [
                {
                    "name": negotiator_names[i]
                    if i < len(negotiator_names)
                    else partners[i]
                    if i < len(partners)
                    else f"Negotiator{i}",
                    "type": negotiator_types[i]
                    if i < len(negotiator_types)
                    else partners[i]
                    if i < len(partners)
                    else "Unknown",
                    "short_type": partners[i] if i < len(partners) else "Unknown",
                }
                for i in range(max(len(partners), len(negotiator_names), 2))
            ],
            "issue_names": issue_names,
            "outcome_space_data": outcome_space_data,
            # Optimality metrics from tournament results
            "pareto_optimality": float(raw_data.get("pareto_optimality", 0))
            if raw_data.get("pareto_optimality")
            else None,
            "nash_optimality": float(raw_data.get("nash_optimality", 0))
            if raw_data.get("nash_optimality")
            else None,
            "kalai_optimality": float(raw_data.get("kalai_optimality", 0))
            if raw_data.get("kalai_optimality")
            else None,
            "ks_optimality": float(raw_data.get("ks_optimality", 0))
            if raw_data.get("ks_optimality")
            else None,
            "max_welfare_optimality": float(raw_data.get("max_welfare_optimality", 0))
            if raw_data.get("max_welfare_optimality")
            else None,
            "execution_time": float(raw_data.get("execution_time", 0))
            if raw_data.get("execution_time")
            else None,
            "source": "tournament",
        }

        return result

    @classmethod
    def load_negotiation_from_folder(cls, folder_path: str) -> dict | None:
        """Load a negotiation from a standalone folder (like those in tournament negotiations/).

        This can load negotiations saved by cartesian_tournament or similar formats.
        Supports both CompletedRun folder format and legacy CSV trace files.

        Args:
            folder_path: Path to the folder containing negotiation data, or path to a CSV file.

        Returns:
            Complete negotiation data dict, or None if loading fails.
        """
        from pathlib import Path as P

        from .negotiation_loader import NegotiationLoader

        folder = P(folder_path)

        # First, try to load using NegotiationLoader (supports CompletedRun format)
        # This handles: directories with run_info.yaml/config.yaml, CSV files, parquet files
        try:
            neg_data = NegotiationLoader.from_file(folder_path)
            return neg_data.to_frontend_dict()
        except Exception:
            pass  # Fall back to legacy CSV loading

        # Legacy fallback: If it's a file, load it directly as a trace
        if folder.is_file() and folder.suffix == ".csv":
            return cls._load_negotiation_from_csv(folder)

        # Legacy fallback: If it's a directory, look for CSV files
        if folder.is_dir():
            csv_files = list(folder.glob("*.csv"))
            if csv_files:
                # Use the first CSV file found
                return cls._load_negotiation_from_csv(csv_files[0])

        return None

    @classmethod
    def _load_negotiation_from_csv(cls, csv_path) -> dict | None:
        """Load negotiation data from a single CSV trace file.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            Negotiation data dict, or None.
        """
        from pathlib import Path as P

        csv_path = P(csv_path)
        if not csv_path.exists():
            return None

        try:
            history = []
            negotiator_ids = set()

            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    step = int(row.get("step", 0))
                    negotiator_id = row.get("negotiator", "")
                    offer_str = row.get("offer", "")
                    relative_time = (
                        float(row.get("relative_time", 0))
                        if row.get("relative_time")
                        else 0
                    )

                    negotiator_ids.add(negotiator_id)

                    # Parse offer
                    offer = None
                    if offer_str:
                        try:
                            offer = ast.literal_eval(offer_str)
                            if isinstance(offer, tuple):
                                offer = list(offer)
                        except (ValueError, SyntaxError):
                            offer = None

                    history.append(
                        {
                            "step": step,
                            "negotiator": negotiator_id,
                            "offer": offer,
                            "utilities": None,  # No ufuns available
                            "relative_time": relative_time,
                            "response": row.get("responses", ""),
                            "state": row.get("state", ""),
                        }
                    )

            # Try to parse scenario and negotiator info from filename
            # Format: scenario_neg1_neg2_rep_runid.csv
            filename = csv_path.stem
            parts = filename.rsplit("_", 2)  # Split from right to get runid, rep, rest

            scenario_name = "Unknown"
            _negotiator_types = list(negotiator_ids)

            if len(parts) >= 3:
                # Try to extract scenario and negotiators from the prefix
                prefix = parts[0]
                # This is approximate - the actual format varies
                scenario_name = prefix.split("_")[0] if "_" in prefix else prefix

            # Determine if there was an agreement (last state)
            has_agreement = False
            agreement = None
            if history:
                last_entry = history[-1]
                state = last_entry.get("state", "")
                if state in ("agreement", "ended"):
                    has_agreement = True
                    agreement = last_entry.get("offer")

            return {
                "id": csv_path.stem,
                "scenario": scenario_name,
                "status": "completed",
                "has_agreement": has_agreement,
                "agreement": agreement,
                "final_utilities": None,
                "history": history,
                "n_steps": max((h["step"] for h in history), default=0) + 1
                if history
                else 0,
                "current_step": max((h["step"] for h in history), default=0) + 1
                if history
                else 0,
                "negotiators": [
                    {"name": nid, "type": "Unknown", "short_type": "Unknown"}
                    for nid in sorted(negotiator_ids)
                ],
                "issue_names": [],
                "outcome_space_data": None,
                "source": "file",
                "file_path": str(csv_path),
            }

        except Exception as e:
            logger.info(f"Error loading negotiation from {csv_path}: {e}")
            return None

    @classmethod
    def combine_tournaments(
        cls,
        tournament_ids: list[str] | None = None,
        input_paths: list[str] | None = None,
        output_name: str | None = None,
        output_path: str | None = None,
        recursive: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> CombineResult:
        """Combine multiple tournaments into a single result.

        This method supports two modes:
        1. Combine by tournament IDs (from saved tournaments table)
        2. Combine by filesystem paths (recursively finds all tournaments)

        Args:
            tournament_ids: List of tournament IDs from saved tournaments
            input_paths: List of filesystem paths to search for tournaments
            output_name: Name for the combined tournament (used as folder name)
            output_path: Custom output path (if None, saves to tournaments dir)
            recursive: If True, recursively search input_paths for tournaments
            metadata: Additional metadata to save in config.json

        Returns:
            CombineResult with success status, output location, and statistics.
        """
        try:
            # Collect tournament paths
            paths_to_combine: list[Path] = []

            # Mode 1: Combine by tournament IDs
            if tournament_ids:
                for tid in tournament_ids:
                    tpath = cls.TOURNAMENTS_DIR / tid
                    if tpath.exists() and cls._check_tournament_files_exist(tpath):
                        paths_to_combine.append(tpath)

            # Mode 2: Combine by filesystem paths
            if input_paths:
                for input_path in input_paths:
                    p = Path(input_path)
                    if not p.exists():
                        continue
                    if p.is_file():
                        # Skip files
                        continue
                    # Check if it's a tournament directory itself
                    if cls._check_tournament_files_exist(p):
                        paths_to_combine.append(p)
                    elif recursive:
                        # Recursively find tournaments
                        for child in p.rglob("*"):
                            if child.is_dir() and cls._check_tournament_files_exist(
                                child
                            ):
                                paths_to_combine.append(child)

            if not paths_to_combine:
                return CombineResult(
                    success=False,
                    error="No valid tournament directories found",
                )

            # Remove duplicates while preserving order
            seen: set[str] = set()
            unique_paths: list[Path] = []
            for p in paths_to_combine:
                ps = str(p.absolute())
                if ps not in seen:
                    seen.add(ps)
                    unique_paths.append(p)

            # Use negmas SimpleTournamentResults.combine()
            combined_results, loaded_paths = SimpleTournamentResults.combine(
                unique_paths,
                recursive=False,  # We already did the recursion
                recalc_details=False,
                recalc_scores=False,
                must_have_details=True,
                verbosity=0,
                add_tournament_column=True,
                complete_only=True,
            )

            if combined_results is None or len(loaded_paths) == 0:
                return CombineResult(
                    success=False,
                    error="Failed to combine tournaments - no valid results found",
                )

            # Generate output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if output_name:
                # Sanitize name for filesystem
                safe_name = "".join(
                    c if c.isalnum() or c in "-_" else "_" for c in output_name
                )
                output_id = f"{safe_name}_{timestamp}"
            else:
                output_id = f"combined_{timestamp}"

            if output_path:
                final_output_path = Path(output_path)
            else:
                final_output_path = cls.TOURNAMENTS_DIR / output_id

            # Save combined results using negmas' save method
            # This handles storage_format and storage_optimization correctly
            combined_results.save(final_output_path, exist_ok=True)

            # Compute statistics from the combined results
            details_df = combined_results.details
            n_negotiations = len(details_df) if details_df is not None else 0
            n_scenarios = 0
            n_competitors = 0

            if details_df is not None and len(details_df) > 0:
                if "scenario" in details_df.columns:
                    n_scenarios = int(details_df["scenario"].nunique())
                if "partners" in details_df.columns:
                    all_partners: set[str] = set()
                    for partners_val in details_df["partners"].dropna():
                        if isinstance(partners_val, (list, tuple)):
                            all_partners.update(partners_val)
                        elif isinstance(partners_val, str):
                            try:
                                parsed = ast.literal_eval(partners_val)
                                if isinstance(parsed, (list, tuple)):
                                    all_partners.update(parsed)
                            except (ValueError, SyntaxError):
                                pass
                    n_competitors = len(all_partners)

            # Save config with metadata
            config: dict[str, Any] = {
                "combined": True,
                "combined_from": [str(p) for p in loaded_paths],
                "combined_at": datetime.now().isoformat(),
                "n_source_tournaments": len(loaded_paths),
                "n_negotiations": n_negotiations,
                "n_scenarios": n_scenarios,
                "n_competitors": n_competitors,
            }

            # Add metadata from original tournaments if available
            if combined_results.config:
                config["competitor_types"] = combined_results.config.get(
                    "competitor_types", []
                )
                config["competitor_names"] = combined_results.config.get(
                    "competitor_names", []
                )
                config["opponent_types"] = combined_results.config.get("opponent_types")
                config["opponent_names"] = combined_results.config.get("opponent_names")

            # Add custom metadata
            if metadata:
                config["metadata"] = metadata

            with open(final_output_path / "config.json", "w") as f:
                json.dump(config, f, indent=2)

            # Clear cache for the new tournament
            cls.clear_cache(output_id)

            return CombineResult(
                success=True,
                output_path=str(final_output_path),
                output_id=output_id,
                n_tournaments=len(loaded_paths),
                n_negotiations=n_negotiations,
                n_scenarios=n_scenarios,
                n_competitors=n_competitors,
                loaded_paths=[str(p) for p in loaded_paths],
            )

        except FileNotFoundError as e:
            return CombineResult(
                success=False,
                error=f"No tournaments found: {e}",
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            return CombineResult(
                success=False,
                error=f"Failed to combine tournaments: {e}",
            )

    @classmethod
    def find_tournaments_in_paths(
        cls, paths: list[str], recursive: bool = True
    ) -> list[dict]:
        """Find all tournament directories in the given paths.

        Args:
            paths: List of filesystem paths to search
            recursive: If True, search recursively

        Returns:
            List of dicts with tournament info (path, id, n_negotiations, etc.)
        """
        found: list[dict] = []
        seen: set[str] = set()

        for input_path in paths:
            p = Path(input_path)
            if not p.exists():
                continue

            # Check if it's a tournament directory itself
            if cls._check_tournament_files_exist(p):
                ps = str(p.absolute())
                if ps not in seen:
                    seen.add(ps)
                    summary = cls._load_tournament_summary(p)
                    if summary:
                        found.append(summary)

            elif recursive and p.is_dir():
                # Recursively find tournaments
                for child in p.rglob("*"):
                    if child.is_dir():
                        cs = str(child.absolute())
                        if cs not in seen and cls._check_tournament_files_exist(child):
                            seen.add(cs)
                            summary = cls._load_tournament_summary(child)
                            if summary:
                                found.append(summary)

        return found
