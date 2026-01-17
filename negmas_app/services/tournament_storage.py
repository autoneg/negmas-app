"""Tournament storage service for loading saved tournament results."""

from __future__ import annotations

import ast
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

import pandas as pd
import yaml

from negmas.tournaments.neg import SimpleTournamentResults

if TYPE_CHECKING:
    from .negotiation_loader import NegotiationData


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
    def _sanitize_for_json(obj: Any) -> Any:
        """Sanitize values for JSON serialization.

        Converts pandas NaN/NaT and numpy types to JSON-compatible values.
        """
        if obj is None:
            return None
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {
                k: TournamentStorageService._sanitize_for_json(v)
                for k, v in obj.items()
            }
        if isinstance(obj, (list, tuple)):
            return [TournamentStorageService._sanitize_for_json(v) for v in obj]
        # Handle pandas/numpy NaN
        if pd.isna(obj):
            return None
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
            print(f"Error loading tournament results from {path}: {e}")
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

        Uses SimpleTournamentResults.load() for robust format handling.
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

            # Try to load using SimpleTournamentResults for format-agnostic access
            results = cls._load_results(path)

            n_negotiations = 0
            n_agreements = 0
            scenarios: set[str] = set()
            competitors: set[str] = set()

            if results is not None:
                # Use the loaded results
                details_df = results.details
                if details_df is not None and len(details_df) > 0:
                    n_negotiations = len(details_df)

                    # Count agreements
                    if "agreement" in details_df.columns:
                        n_agreements = details_df["agreement"].notna().sum()
                        # Also filter out "None" strings
                        if details_df["agreement"].dtype == object:
                            n_agreements = (
                                (details_df["agreement"].notna())
                                & (details_df["agreement"] != "None")
                                & (details_df["agreement"] != "")
                            ).sum()

                    # Get scenarios
                    if "scenario" in details_df.columns:
                        scenarios = set(details_df["scenario"].dropna().unique())

                    # Get partners/competitors
                    if "partners" in details_df.columns:
                        for partners_val in details_df["partners"].dropna():
                            if isinstance(partners_val, (list, tuple)):
                                competitors.update(partners_val)
                            elif isinstance(partners_val, str):
                                try:
                                    parsed = ast.literal_eval(partners_val)
                                    if isinstance(parsed, (list, tuple)):
                                        competitors.update(parsed)
                                except (ValueError, SyntaxError):
                                    pass

                # Also check scores for competitor names
                scores_df = results.final_scores
                if scores_df is not None and len(scores_df) > 0:
                    if "strategy" in scores_df.columns:
                        competitors.update(scores_df["strategy"].dropna().unique())
            else:
                # Fallback: try to read scores.csv directly (always CSV format)
                scores_file = path / "scores.csv"
                if scores_file.exists():
                    try:
                        with open(scores_file, "r") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if row.get("strategy"):
                                    competitors.add(row["strategy"])
                    except Exception:
                        pass

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
                "n_agreements": int(n_agreements),
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
        """Load competitor scores using SimpleTournamentResults and type_scores.csv.

        Handles all storage formats automatically.
        Enriches scores with detailed statistics from type_scores.csv.
        """
        scores = []

        # Use SimpleTournamentResults for format-agnostic loading
        results = cls._load_results(path)
        if results is None:
            return scores

        try:
            # Get final scores (always in memory, small)
            final_scores_df = results.final_scores
            if final_scores_df is not None and len(final_scores_df) > 0:
                for idx, row in final_scores_df.iterrows():
                    name = row.get("strategy", str(idx))
                    score = row.get("score")

                    scores.append(
                        {
                            "name": name,
                            "rank": int(idx) + 1 if isinstance(idx, int) else 1,  # type: ignore[arg-type]
                            "score": float(score) if pd.notna(score) else None,  # type: ignore[arg-type]
                            "raw_data": cls._sanitize_for_json(row.to_dict()),
                        }
                    )

            # Sort by score descending
            scores.sort(key=lambda x: x.get("score") or 0, reverse=True)
            for idx, s in enumerate(scores):
                s["rank"] = idx + 1

            # Enrich with type_scores.csv data if available
            type_scores_path = path / "type_scores.csv"
            if type_scores_path.exists():
                try:
                    type_scores_data = cls._parse_type_scores_csv(type_scores_path)
                    for score_entry in scores:
                        strategy_name = score_entry["name"]
                        if strategy_name in type_scores_data:
                            stats = type_scores_data[strategy_name]
                            # Add key statistics to the score entry
                            score_entry["mean_utility"] = stats.get("utility", {}).get(
                                "mean"
                            )
                            score_entry["n_negotiations"] = int(
                                stats.get("utility", {}).get("count", 0)
                            )
                            score_entry["mean_advantage"] = stats.get(
                                "advantage", {}
                            ).get("mean")
                            score_entry["mean_welfare"] = stats.get("welfare", {}).get(
                                "mean"
                            )
                            score_entry["mean_nash_optimality"] = stats.get(
                                "nash_optimality", {}
                            ).get("mean")
                            score_entry["mean_pareto_optimality"] = stats.get(
                                "pareto_optimality", {}
                            ).get("mean")
                            score_entry["type_scores"] = stats
                except Exception as e:
                    print(f"Error enriching scores with type_scores: {e}")

        except Exception as e:
            print(f"Error loading scores from {path}: {e}")

        return scores

    @classmethod
    def _parse_type_scores_csv(cls, path: Path) -> dict[str, dict]:
        """Parse type_scores.csv into a structured dict.

        Args:
            path: Path to type_scores.csv file.

        Returns:
            Dict mapping strategy name to dict of metric -> {count, mean, std, min, max, ...}
        """
        result: dict[str, dict] = {}
        stat_names = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]

        try:
            with open(path, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if len(rows) < 3:
                return result

            # First row: metric names (repeated 8 times each)
            # Second row: stat names (count, mean, std, min, 25%, 50%, 75%, max)
            # Subsequent rows: strategy name, then values
            metric_row = rows[0]

            # Build metric positions
            metrics: list[tuple[str, int]] = []  # (metric_name, start_index)
            current_metric = None
            for i, header in enumerate(metric_row[1:], start=1):  # Skip index column
                if header and header != current_metric:
                    current_metric = header
                    metrics.append((header, i))

            # Parse data rows
            for row in rows[3:]:  # Skip header rows and "index" row
                if not row or not row[0] or row[0] == "index":
                    continue

                strategy_name = row[0]
                result[strategy_name] = {}

                for metric_name, start_idx in metrics:
                    metric_stats = {}
                    for j, stat_name in enumerate(stat_names):
                        value_idx = start_idx + j
                        if value_idx < len(row):
                            try:
                                val = float(row[value_idx])
                                # Sanitize inf/-inf/nan for JSON compatibility
                                if math.isnan(val) or math.isinf(val):
                                    metric_stats[stat_name] = None
                                else:
                                    metric_stats[stat_name] = val
                            except (ValueError, TypeError):
                                metric_stats[stat_name] = None
                    result[strategy_name][metric_name] = metric_stats

        except Exception as e:
            print(f"Error parsing type_scores.csv: {e}")

        return result

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
                agreement_val = row.get("agreement")
                has_agreement = (
                    agreement_val is not None
                    and str(agreement_val) != ""
                    and str(agreement_val) != "None"
                    and pd.notna(agreement_val)
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

                negotiations.append(
                    {
                        "index": idx,
                        "scenario": scenario,
                        "partners": partners,
                        "has_agreement": has_agreement,
                        "utilities": utilities if utilities else None,
                        "raw_data": cls._sanitize_for_json(
                            row.to_dict() if hasattr(row, "to_dict") else dict(row)
                        ),
                    }
                )

        except Exception as e:
            print(f"Error loading negotiations from {path}: {e}")

        return negotiations

    @classmethod
    def get_tournament_negotiation(cls, tournament_id: str, index: int) -> dict | None:
        """Get full details of a specific negotiation from a tournament.

        Uses SimpleTournamentResults for format-agnostic loading.

        Args:
            tournament_id: Tournament ID.
            index: Index of the negotiation in details.

        Returns:
            Full negotiation data or None if not found.
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
                    except (ValueError, SyntaxError):
                        pass

            # Fall back to individual fields
            if not partners:
                for k in ["negotiator0", "negotiator1", "first", "second"]:
                    if row.get(k):
                        partners.append(row[k])

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

            # Get agreement value
            agreement_val = row.get("agreement")
            has_agreement = (
                agreement_val is not None
                and str(agreement_val) != ""
                and str(agreement_val) != "None"
                and pd.notna(agreement_val)
            )

            return {
                "index": index,
                "raw_data": cls._sanitize_for_json(
                    row.to_dict() if hasattr(row, "to_dict") else dict(row)
                ),
                "scenario": row.get("scenario") or row.get("domain"),
                "partners": partners,
                "agreement": str(agreement_val) if agreement_val is not None else None,
                "utilities": utilities,
                "has_agreement": has_agreement,
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
            print(f"Error loading all_scores for {tournament_id}: {e}")
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
            print(f"Error loading details for {tournament_id}: {e}")
            return None

    @classmethod
    def _file_exists_any_format(cls, path: Path, base_name: str) -> bool:
        """Check if a file exists in any supported format (csv, gzip, parquet)."""
        for ext in (".csv", ".csv.gz", ".parquet"):
            if (path / f"{base_name}{ext}").exists():
                return True
        return False

    @classmethod
    def get_tournament_files(cls, tournament_id: str) -> dict[str, bool | int]:
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

        files: dict[str, bool | int] = {
            "config": (path / "config.json").exists(),
            "scores": (path / "scores.csv").exists(),  # Always CSV (small file)
            "type_scores": (path / "type_scores.csv").exists(),  # Always CSV
            "all_scores": cls._file_exists_any_format(path, "all_scores"),
            "details": cls._file_exists_any_format(path, "details"),
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
            scenario = Scenario.load(scenario_dir, load_stats=True, load_info=True)  # type: ignore[attr-defined]

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

                scenario = Scenario.load(scenario_dir, load_stats=True, load_info=True)  # type: ignore[attr-defined]
                if scenario:
                    ufuns = list(scenario.ufuns) if scenario.ufuns else []

                    # Compute outcome space data
                    osd = compute_outcome_space_data(
                        scenario, max_samples=50000, use_cached_stats=True
                    )
                    outcome_space_data = {
                        "outcome_utilities": osd.outcome_utilities,
                        "pareto_utilities": osd.pareto_utilities,
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
                print(f"Error loading scenario {scenario_name}: {e}")

        # Load the negotiation trace from negotiations folder
        trace = []
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
        The folder should contain a CSV trace file and optionally scenario data.

        Args:
            folder_path: Path to the folder containing negotiation data, or path to a CSV file.

        Returns:
            Complete negotiation data dict, or None if loading fails.
        """
        from pathlib import Path as P

        folder = P(folder_path)

        # If it's a file, load it directly as a trace
        if folder.is_file() and folder.suffix == ".csv":
            return cls._load_negotiation_from_csv(folder)

        # If it's a directory, look for CSV files
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
            negotiator_types = list(negotiator_ids)

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
            print(f"Error loading negotiation from {csv_path}: {e}")
            return None

    @classmethod
    def load_negotiation_as_data(
        cls, tournament_id: str, negotiation_index: int
    ) -> NegotiationData | None:
        """Load a tournament negotiation using the unified NegotiationLoader.

        This method tries to use CompletedRun.load() for newer format negotiations,
        falling back to the legacy parsing for older formats.

        Args:
            tournament_id: Tournament ID.
            negotiation_index: Index of the negotiation in details.

        Returns:
            NegotiationData ready for UI display, or None if not found.
        """
        from .negotiation_loader import NegotiationLoader

        path = cls.TOURNAMENTS_DIR / tournament_id

        # Get negotiation metadata to find the run_id
        neg_data = cls.get_tournament_negotiation(tournament_id, negotiation_index)
        if neg_data is None:
            return None

        raw_data = neg_data.get("raw_data", {})
        run_id = raw_data.get("run_id")
        scenario_name = neg_data.get("scenario") or raw_data.get(
            "effective_scenario_name", ""
        )

        if not run_id:
            # Fall back to legacy loading and convert
            legacy_data = cls.load_full_negotiation(tournament_id, negotiation_index)
            if legacy_data:
                return cls._legacy_dict_to_negotiation_data(legacy_data)
            return None

        # Find the negotiation file/folder in negotiations directory
        negotiations_dir = path / "negotiations"
        negotiation_path = None

        if negotiations_dir.exists():
            # Try different file patterns
            for pattern in [f"*{run_id}*", f"{scenario_name}*{run_id}*"]:
                matches = list(negotiations_dir.glob(pattern))
                if matches:
                    negotiation_path = matches[0]
                    break

        if not negotiation_path:
            # Fall back to legacy loading
            legacy_data = cls.load_full_negotiation(tournament_id, negotiation_index)
            if legacy_data:
                return cls._legacy_dict_to_negotiation_data(legacy_data)
            return None

        # Try to load using NegotiationLoader (CompletedRun format)
        try:
            negotiation_id = f"{tournament_id}_{negotiation_index}"
            return NegotiationLoader.from_file(
                negotiation_path,
                negotiation_id=negotiation_id,
                load_scenario_stats=True,
            )
        except Exception as e:
            print(f"Error loading negotiation via NegotiationLoader: {e}")
            # Fall back to legacy loading
            legacy_data = cls.load_full_negotiation(tournament_id, negotiation_index)
            if legacy_data:
                return cls._legacy_dict_to_negotiation_data(legacy_data)
            return None

    @classmethod
    def load_file_as_data(cls, file_path: str) -> NegotiationData | None:
        """Load a negotiation from any file path using NegotiationLoader.

        This method handles both CompletedRun format and legacy CSV format.

        Args:
            file_path: Path to negotiation file or directory.

        Returns:
            NegotiationData ready for UI display, or None if loading fails.
        """
        from .negotiation_loader import NegotiationLoader

        path = Path(file_path)
        if not path.exists():
            return None

        # Try NegotiationLoader first (handles CompletedRun format)
        try:
            return NegotiationLoader.from_file(
                path,
                negotiation_id=f"file-{path.stem}",
                load_scenario_stats=True,
            )
        except Exception as e:
            print(f"NegotiationLoader failed for {path}: {e}")

        # Fall back to legacy CSV loading
        legacy_data = cls.load_negotiation_from_folder(str(path))
        if legacy_data:
            return cls._legacy_dict_to_negotiation_data(legacy_data)

        return None

    @classmethod
    def _legacy_dict_to_negotiation_data(cls, data: dict) -> NegotiationData:
        """Convert legacy negotiation dict format to NegotiationData.

        Args:
            data: Legacy negotiation dict from load_full_negotiation or load_negotiation_from_folder.

        Returns:
            NegotiationData instance.
        """
        from .negotiation_loader import NegotiationData, NegotiationOffer
        from ..models.session import NEGOTIATOR_COLORS

        # Extract negotiator info
        negotiators = data.get("negotiators", [])
        negotiator_names = [
            n.get("name", f"Negotiator{i}") for i, n in enumerate(negotiators)
        ]
        negotiator_types = [n.get("type", "Unknown") for n in negotiators]
        n_negotiators = len(negotiators) if negotiators else 2

        negotiator_colors = [
            NEGOTIATOR_COLORS[i % len(NEGOTIATOR_COLORS)] for i in range(n_negotiators)
        ]

        # Build name to index mapping
        name_to_idx = {name: i for i, name in enumerate(negotiator_names)}

        # Convert history to NegotiationOffer objects
        offers = []
        for entry in data.get("history", []):
            proposer = entry.get("negotiator", "")
            proposer_idx = name_to_idx.get(proposer, 0)

            # Handle case where proposer might be ID with UUID
            if proposer_idx == 0 and proposer:
                for name, idx in name_to_idx.items():
                    if name in proposer or proposer in name:
                        proposer_idx = idx
                        break

            offer_val = entry.get("offer")
            offer_dict = {}
            issue_names = data.get("issue_names", [])
            if offer_val and issue_names:
                if isinstance(offer_val, dict):
                    offer_dict = offer_val
                else:
                    offer_dict = dict(zip(issue_names, offer_val))
            elif offer_val:
                offer_dict = {f"issue_{i}": v for i, v in enumerate(offer_val)}

            offers.append(
                NegotiationOffer(
                    step=entry.get("step", 0),
                    relative_time=entry.get("relative_time", 0.0),
                    proposer=proposer,
                    proposer_index=proposer_idx,
                    offer=tuple(offer_val)
                    if offer_val and not isinstance(offer_val, dict)
                    else offer_val,
                    offer_dict=offer_dict,
                    utilities=entry.get("utilities", []) or [],
                    responses={},
                    state=entry.get("state", "continuing"),
                )
            )

        # Build agreement dict
        agreement = data.get("agreement")
        agreement_dict = None
        agreement_tuple = None
        issue_names = data.get("issue_names", [])

        if agreement:
            if isinstance(agreement, dict):
                agreement_dict = agreement
                agreement_tuple = tuple(agreement.values())
            elif issue_names:
                agreement_tuple = (
                    tuple(agreement) if not isinstance(agreement, tuple) else agreement
                )
                agreement_dict = dict(zip(issue_names, agreement_tuple))
            else:
                agreement_tuple = (
                    tuple(agreement) if not isinstance(agreement, tuple) else agreement
                )
                agreement_dict = {
                    f"issue_{i}": v for i, v in enumerate(agreement_tuple)
                }

        # Build optimality stats
        optimality_stats = None
        if any(
            data.get(k) is not None
            for k in ["pareto_optimality", "nash_optimality", "kalai_optimality"]
        ):
            optimality_stats = {
                "pareto_optimality": data.get("pareto_optimality"),
                "nash_optimality": data.get("nash_optimality"),
                "kalai_optimality": data.get("kalai_optimality"),
                "ks_optimality": data.get("ks_optimality"),
                "max_welfare_optimality": data.get("max_welfare_optimality"),
            }

        # Convert outcome_space_data dict to OutcomeSpaceData if present
        outcome_space_data = None
        osd = data.get("outcome_space_data")
        if osd:
            from ..models.session import OutcomeSpaceData, AnalysisPoint

            outcome_space_data = OutcomeSpaceData(
                outcome_utilities=[tuple(u) for u in osd.get("outcome_utilities", [])],
                pareto_utilities=[tuple(u) for u in osd.get("pareto_utilities", [])],
                total_outcomes=osd.get("total_outcomes", 0),
                sampled=osd.get("sampled", False),
                sample_size=osd.get("sample_size", 0),
            )

            if osd.get("nash_point"):
                outcome_space_data.nash_point = AnalysisPoint(
                    name="nash", utilities=osd["nash_point"]
                )
            if osd.get("kalai_point"):
                outcome_space_data.kalai_point = AnalysisPoint(
                    name="kalai", utilities=osd["kalai_point"]
                )
            if osd.get("kalai_smorodinsky_point"):
                outcome_space_data.kalai_smorodinsky_point = AnalysisPoint(
                    name="kalai_smorodinsky", utilities=osd["kalai_smorodinsky_point"]
                )
            if osd.get("max_welfare_point"):
                outcome_space_data.max_welfare_point = AnalysisPoint(
                    name="max_welfare", utilities=osd["max_welfare_point"]
                )

        # Determine end reason
        end_reason = None
        if data.get("has_agreement"):
            end_reason = "agreement"
        elif data.get("status") == "completed":
            end_reason = "no_agreement"

        return NegotiationData(
            id=data.get("id", "unknown"),
            source=data.get("source", "tournament"),
            source_path=data.get("file_path"),
            scenario_name=data.get("scenario", ""),
            negotiator_names=negotiator_names,
            negotiator_types=negotiator_types,
            negotiator_colors=negotiator_colors,
            issue_names=issue_names,
            n_steps=data.get("n_steps"),
            offers=offers,
            agreement=agreement_dict,
            agreement_tuple=agreement_tuple,
            final_utilities=data.get("final_utilities"),
            end_reason=end_reason,
            final_step=data.get("current_step", 0),
            optimality_stats=optimality_stats,
            outcome_space_data=outcome_space_data,
        )
