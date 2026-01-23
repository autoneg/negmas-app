"""Setup service for initializing user directories and copying bundled resources."""

import shutil
import zipfile
from pathlib import Path
from typing import Any


class SetupService:
    """Service for setting up NegMAS App user directories and resources."""

    @staticmethod
    def get_bundled_scenarios_zip() -> Path:
        """Get the path to bundled scenarios.zip in the package.

        Returns:
            Path to the bundled scenarios.zip file.
        """
        # scenarios.zip is at the project root, next to negmas_app package
        package_dir = Path(__file__).parent.parent.parent
        zip_file = package_dir / "scenarios.zip"

        if zip_file.exists():
            return zip_file

        # If not found (e.g., in installed package), look in site-packages
        try:
            import negmas_app

            installed_package_dir = Path(negmas_app.__file__).parent.parent
            zip_file = installed_package_dir / "scenarios.zip"
            if zip_file.exists():
                return zip_file
        except Exception:
            pass

        raise FileNotFoundError("Bundled scenarios.zip file not found")

    @staticmethod
    def get_user_scenarios_path() -> Path:
        """Get the user scenarios directory path.

        Returns:
            Path to ~/negmas/app/scenarios/
        """
        return Path.home() / "negmas" / "app" / "scenarios"

    @staticmethod
    def ensure_user_directories() -> None:
        """Create the ~/negmas/app/ directory structure if it doesn't exist."""
        base_dir = Path.home() / "negmas" / "app"
        base_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (base_dir / "scenarios").mkdir(exist_ok=True)
        (base_dir / "settings").mkdir(exist_ok=True)
        (base_dir / "negotiations").mkdir(exist_ok=True)
        (base_dir / "tournaments").mkdir(exist_ok=True)

    @staticmethod
    def copy_bundled_scenarios(
        target_dir: Path | None = None,
        force: bool = False,
        skip_cache: bool = False,
    ) -> dict[str, Any]:
        """Extract bundled scenarios from scenarios.zip to user directory.

        Args:
            target_dir: Target directory (defaults to ~/negmas/app/scenarios/)
            force: If True, overwrite existing files
            skip_cache: If True, skip extracting cache files (_info.yaml, _stats.yaml, _plot.webp)

        Returns:
            Dictionary with extraction statistics:
                - total_files: Total files found in zip
                - copied: Number of files extracted
                - skipped: Number of files skipped (already exist)
                - errors: List of error messages
        """
        if target_dir is None:
            target_dir = SetupService.get_user_scenarios_path()

        zip_file = SetupService.get_bundled_scenarios_zip()

        stats = {
            "total_files": 0,
            "copied": 0,
            "skipped": 0,
            "errors": [],
        }

        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        # Cache file patterns to skip
        cache_filenames = {"_info.yaml", "_info.yml", "_stats.yaml", "_plot.webp"}

        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                for zip_info in zf.infolist():
                    # Skip directories
                    if zip_info.is_dir():
                        continue

                    # Get filename without scenarios/ prefix if present
                    filename = zip_info.filename
                    if filename.startswith("scenarios/"):
                        filename = filename[len("scenarios/") :]

                    # Skip hidden files and .DS_Store
                    if Path(filename).name.startswith("."):
                        continue

                    # Skip cache files if requested
                    if skip_cache and (
                        Path(filename).name in cache_filenames or "/_plots/" in filename
                    ):
                        continue

                    stats["total_files"] += 1

                    target_file = target_dir / filename

                    # Skip if file exists and force is False
                    if target_file.exists() and not force:
                        stats["skipped"] += 1
                        continue

                    # Extract file
                    try:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        with (
                            zf.open(zip_info) as source,
                            open(target_file, "wb") as target,
                        ):
                            shutil.copyfileobj(source, target)
                        stats["copied"] += 1
                    except Exception as e:
                        stats["errors"].append(f"{filename}: {str(e)}")

        except zipfile.BadZipFile as e:
            stats["errors"].append(f"Invalid zip file: {str(e)}")
        except Exception as e:
            stats["errors"].append(f"Error reading zip file: {str(e)}")

        return stats

    @staticmethod
    def count_scenarios(directory: Path) -> int:
        """Count the number of scenario directories recursively.

        A scenario directory is one that contains .xml, .yml, .yaml, or .json files
        (domain or utility function files).

        Args:
            directory: Directory to scan

        Returns:
            Number of scenario directories found
        """
        if not directory.exists():
            return 0

        count = 0

        # Recursively find all directories
        for item in directory.rglob("*"):
            if not item.is_dir():
                continue

            # Skip hidden directories
            if any(
                p.name.startswith(".") for p in item.parents
            ) or item.name.startswith("."):
                continue

            # Check if this directory contains scenario files
            has_scenario_files = any(
                f.suffix in {".xml", ".yml", ".yaml", ".json"}
                for f in item.iterdir()
                if f.is_file() and not f.name.startswith("_")
            )

            if has_scenario_files:
                count += 1

        return count
