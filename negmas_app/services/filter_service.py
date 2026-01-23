"""Service for managing saved filters."""

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
