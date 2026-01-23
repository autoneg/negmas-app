"""Service for managing saved filters."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..models.settings import SavedFilter, FilterSettings


class FilterService:
    """Manage saved filters for scenarios and negotiators."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize FilterService.

        Args:
            config_dir: Directory for storing filter config. Defaults to ~/negmas/app/
        """
        if config_dir is None:
            config_dir = Path.home() / "negmas" / "app"
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.filters_file = self.config_dir / "filters.yaml"

    def load_filters(self) -> FilterSettings:
        """Load all saved filters from disk.

        Returns:
            FilterSettings with all saved filters.
        """
        if not self.filters_file.exists():
            return FilterSettings()

        try:
            with open(self.filters_file) as f:
                data = yaml.safe_load(f) or {}

            scenario_filters = []
            for item in data.get("scenario_filters", []):
                scenario_filters.append(SavedFilter(**item))

            negotiator_filters = []
            for item in data.get("negotiator_filters", []):
                negotiator_filters.append(SavedFilter(**item))

            return FilterSettings(
                scenario_filters=scenario_filters,
                negotiator_filters=negotiator_filters,
                default_scenario_filter_id=data.get("default_scenario_filter_id"),
                default_negotiator_filter_id=data.get("default_negotiator_filter_id"),
            )
        except Exception as e:
            print(f"Warning: Failed to load filters: {e}")
            return FilterSettings()

    def save_filters(self, settings: FilterSettings) -> None:
        """Save all filters to disk.

        Args:
            settings: FilterSettings to save.
        """
        data = {
            "scenario_filters": [
                {
                    "id": f.id,
                    "name": f.name,
                    "type": f.type,
                    "data": f.data,
                    "description": f.description,
                    "created_at": f.created_at,
                }
                for f in settings.scenario_filters
            ],
            "negotiator_filters": [
                {
                    "id": f.id,
                    "name": f.name,
                    "type": f.type,
                    "data": f.data,
                    "description": f.description,
                    "created_at": f.created_at,
                }
                for f in settings.negotiator_filters
            ],
            "default_scenario_filter_id": settings.default_scenario_filter_id,
            "default_negotiator_filter_id": settings.default_negotiator_filter_id,
        }

        with open(self.filters_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def save_filter(
        self,
        name: str,
        filter_type: str,
        data: dict[str, Any],
        description: str = "",
    ) -> SavedFilter:
        """Save a new filter.

        Args:
            name: Display name for the filter.
            filter_type: "scenario" or "negotiator".
            data: Filter data (all filter values).
            description: Optional description.

        Returns:
            The newly created SavedFilter.
        """
        # Load current settings
        settings = self.load_filters()

        # Create new filter
        new_filter = SavedFilter(
            id=str(uuid.uuid4()),
            name=name,
            type=filter_type,
            data=data,
            description=description,
            created_at=datetime.utcnow().isoformat(),
        )

        # Add to appropriate list
        if filter_type == "scenario":
            settings.scenario_filters.append(new_filter)
        elif filter_type == "negotiator":
            settings.negotiator_filters.append(new_filter)
        else:
            raise ValueError(f"Invalid filter type: {filter_type}")

        # Save back to disk
        self.save_filters(settings)

        return new_filter

    def delete_filter(self, filter_id: str) -> bool:
        """Delete a saved filter by ID.

        Args:
            filter_id: ID of the filter to delete.

        Returns:
            True if filter was deleted, False if not found.
        """
        settings = self.load_filters()

        # Try to find and remove from scenario filters
        for i, f in enumerate(settings.scenario_filters):
            if f.id == filter_id:
                settings.scenario_filters.pop(i)
                self.save_filters(settings)
                return True

        # Try to find and remove from negotiator filters
        for i, f in enumerate(settings.negotiator_filters):
            if f.id == filter_id:
                settings.negotiator_filters.pop(i)
                self.save_filters(settings)
                return True

        return False

    def get_filter(self, filter_id: str) -> SavedFilter | None:
        """Get a saved filter by ID.

        Args:
            filter_id: ID of the filter to retrieve.

        Returns:
            The SavedFilter if found, None otherwise.
        """
        settings = self.load_filters()

        # Search in scenario filters
        for f in settings.scenario_filters:
            if f.id == filter_id:
                return f

        # Search in negotiator filters
        for f in settings.negotiator_filters:
            if f.id == filter_id:
                return f

        return None

    def list_filters(self, filter_type: str | None = None) -> list[SavedFilter]:
        """List all saved filters, optionally filtered by type.

        Args:
            filter_type: If provided, only return filters of this type ("scenario" or "negotiator").

        Returns:
            List of SavedFilter objects.
        """
        settings = self.load_filters()

        if filter_type == "scenario":
            return settings.scenario_filters
        elif filter_type == "negotiator":
            return settings.negotiator_filters
        elif filter_type is None:
            return settings.scenario_filters + settings.negotiator_filters
        else:
            raise ValueError(f"Invalid filter type: {filter_type}")

    def update_filter(
        self,
        filter_id: str,
        name: str | None = None,
        data: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> SavedFilter | None:
        """Update an existing filter.

        Args:
            filter_id: ID of the filter to update.
            name: New name (optional).
            data: New filter data (optional).
            description: New description (optional).

        Returns:
            The updated SavedFilter if found, None otherwise.
        """
        settings = self.load_filters()

        # Find the filter
        filter_obj = None
        for f in settings.scenario_filters + settings.negotiator_filters:
            if f.id == filter_id:
                filter_obj = f
                break

        if filter_obj is None:
            return None

        # Update fields
        if name is not None:
            filter_obj.name = name
        if data is not None:
            filter_obj.data = data
        if description is not None:
            filter_obj.description = description

        # Save back to disk
        self.save_filters(settings)

        return filter_obj

    def export_filters(
        self, filter_ids: list[str] | None = None, filter_type: str | None = None
    ) -> str:
        """Export filters to JSON format.

        Args:
            filter_ids: List of specific filter IDs to export. If None, exports all.
            filter_type: Filter by type ("scenario" or "negotiator"). If None, exports all types.

        Returns:
            JSON string containing the exported filters.
        """
        settings = self.load_filters()

        # Determine which filters to export
        if filter_ids is not None:
            # Export specific filters by ID
            filters_to_export = []
            for f in settings.scenario_filters + settings.negotiator_filters:
                if f.id in filter_ids:
                    filters_to_export.append(f)
        elif filter_type is not None:
            # Export all filters of a specific type
            filters_to_export = self.list_filters(filter_type=filter_type)
        else:
            # Export all filters
            filters_to_export = settings.scenario_filters + settings.negotiator_filters

        # Convert to exportable format
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "filters": [
                {
                    "name": f.name,
                    "type": f.type,
                    "data": f.data,
                    "description": f.description,
                }
                for f in filters_to_export
            ],
        }

        return json.dumps(export_data, indent=2)

    def import_filters(self, json_data: str, overwrite: bool = False) -> dict[str, Any]:
        """Import filters from JSON format.

        Args:
            json_data: JSON string containing filters to import.
            overwrite: If True, replaces filters with same name. If False, creates new filters with "(Imported)" suffix.

        Returns:
            Dictionary with import results: {"success": bool, "imported": int, "errors": list}.
        """
        try:
            import_data = json.loads(json_data)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "imported": 0,
                "errors": [f"Invalid JSON: {str(e)}"],
            }

        # Validate structure
        if "filters" not in import_data or not isinstance(import_data["filters"], list):
            return {
                "success": False,
                "imported": 0,
                "errors": ["Invalid format: missing 'filters' array"],
            }

        settings = self.load_filters()
        imported_count = 0
        errors = []

        for idx, filter_data in enumerate(import_data["filters"]):
            try:
                # Validate required fields
                if "name" not in filter_data or "type" not in filter_data:
                    errors.append(f"Filter {idx}: missing required fields (name, type)")
                    continue

                if filter_data["type"] not in ["scenario", "negotiator"]:
                    errors.append(f"Filter {idx}: invalid type '{filter_data['type']}'")
                    continue

                # Check if filter with same name already exists
                existing_filters = (
                    settings.scenario_filters
                    if filter_data["type"] == "scenario"
                    else settings.negotiator_filters
                )
                existing_names = [f.name for f in existing_filters]

                filter_name = filter_data["name"]
                if filter_name in existing_names:
                    if not overwrite:
                        # Add suffix to make name unique
                        base_name = filter_name
                        counter = 1
                        while filter_name in existing_names:
                            filter_name = f"{base_name} (Imported {counter})"
                            counter += 1
                    else:
                        # Delete existing filter with same name
                        for f in existing_filters:
                            if f.name == filter_name:
                                self.delete_filter(f.id)
                                break

                # Create new filter
                new_filter = SavedFilter(
                    id=str(uuid.uuid4()),
                    name=filter_name,
                    type=filter_data["type"],
                    data=filter_data.get("data", {}),
                    description=filter_data.get("description", ""),
                    created_at=datetime.utcnow().isoformat(),
                )

                # Add to appropriate list
                if filter_data["type"] == "scenario":
                    settings.scenario_filters.append(new_filter)
                else:
                    settings.negotiator_filters.append(new_filter)

                imported_count += 1

            except Exception as e:
                errors.append(f"Filter {idx}: {str(e)}")

        # Save all imported filters at once
        if imported_count > 0:
            self.save_filters(settings)

        return {
            "success": imported_count > 0 or len(errors) == 0,
            "imported": imported_count,
            "errors": errors,
        }

    def set_default_filter(self, filter_id: str, filter_type: str) -> bool:
        """Set a filter as the default for its type.

        Args:
            filter_id: ID of the filter to set as default.
            filter_type: "scenario" or "negotiator".

        Returns:
            True if successfully set, False if filter not found.
        """
        settings = self.load_filters()

        # Verify the filter exists
        filter_obj = self.get_filter(filter_id)
        if filter_obj is None or filter_obj.type != filter_type:
            return False

        # Set as default
        if filter_type == "scenario":
            settings.default_scenario_filter_id = filter_id
        elif filter_type == "negotiator":
            settings.default_negotiator_filter_id = filter_id
        else:
            return False

        self.save_filters(settings)
        return True

    def clear_default_filter(self, filter_type: str) -> bool:
        """Clear the default filter for a type.

        Args:
            filter_type: "scenario" or "negotiator".

        Returns:
            True if successfully cleared.
        """
        settings = self.load_filters()

        if filter_type == "scenario":
            settings.default_scenario_filter_id = None
        elif filter_type == "negotiator":
            settings.default_negotiator_filter_id = None
        else:
            return False

        self.save_filters(settings)
        return True

    def get_default_filter(self, filter_type: str) -> SavedFilter | None:
        """Get the default filter for a type.

        Args:
            filter_type: "scenario" or "negotiator".

        Returns:
            The default SavedFilter if set, None otherwise.
        """
        settings = self.load_filters()

        if filter_type == "scenario":
            filter_id = settings.default_scenario_filter_id
        elif filter_type == "negotiator":
            filter_id = settings.default_negotiator_filter_id
        else:
            return None

        if filter_id is None:
            return None

        return self.get_filter(filter_id)
