"""Service for managing virtual negotiators (saved negotiator configurations)."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..models.negotiator import VirtualNegotiator

# Storage path for virtual negotiators
VIRTUAL_NEGOTIATORS_FILE = Path.home() / "negmas" / "app" / "virtual_negotiators.json"


class VirtualNegotiatorService:
    """Service for CRUD operations on virtual negotiators."""

    _cache: dict[str, VirtualNegotiator] | None = None

    @classmethod
    def _load_all(cls) -> dict[str, VirtualNegotiator]:
        """Load all virtual negotiators from storage."""
        if cls._cache is not None:
            return cls._cache

        cls._cache = {}
        if not VIRTUAL_NEGOTIATORS_FILE.exists():
            return cls._cache

        try:
            with open(VIRTUAL_NEGOTIATORS_FILE) as f:
                data = json.load(f)
            for item in data.get("virtual_negotiators", []):
                vn = VirtualNegotiator.from_dict(item)
                cls._cache[vn.id] = vn
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading virtual negotiators: {e}")

        return cls._cache

    @classmethod
    def _save_all(cls) -> None:
        """Save all virtual negotiators to storage."""
        if cls._cache is None:
            return

        VIRTUAL_NEGOTIATORS_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {"virtual_negotiators": [vn.to_dict() for vn in cls._cache.values()]}
        with open(VIRTUAL_NEGOTIATORS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def list_all(
        cls,
        search: str | None = None,
        tags: list[str] | None = None,
        base_type: str | None = None,
        include_disabled: bool = False,
    ) -> list[VirtualNegotiator]:
        """List all virtual negotiators with optional filtering.

        Args:
            search: Search string to match in name/description
            tags: Filter by tags (match any)
            base_type: Filter by base negotiator type
            include_disabled: If True, include disabled virtual negotiators

        Returns:
            List of matching virtual negotiators.
        """
        all_vns = list(cls._load_all().values())

        # Filter out disabled by default
        if not include_disabled:
            all_vns = [vn for vn in all_vns if vn.enabled]

        if search:
            search_lower = search.lower()
            all_vns = [
                vn
                for vn in all_vns
                if search_lower in vn.name.lower()
                or search_lower in vn.description.lower()
                or any(search_lower in tag.lower() for tag in vn.tags)
            ]

        if tags:
            tags_lower = [t.lower() for t in tags]
            all_vns = [
                vn
                for vn in all_vns
                if any(tag.lower() in tags_lower for tag in vn.tags)
            ]

        if base_type:
            all_vns = [vn for vn in all_vns if vn.base_type_name == base_type]

        return sorted(all_vns, key=lambda vn: vn.name.lower())

    @classmethod
    def get(cls, vn_id: str) -> VirtualNegotiator | None:
        """Get a virtual negotiator by ID."""
        return cls._load_all().get(vn_id)

    @classmethod
    def get_by_name(cls, name: str) -> VirtualNegotiator | None:
        """Get a virtual negotiator by name (case-insensitive)."""
        name_lower = name.lower()
        for vn in cls._load_all().values():
            if vn.name.lower() == name_lower:
                return vn
        return None

    @classmethod
    def create(
        cls,
        name: str,
        base_type_name: str,
        params: dict | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ) -> VirtualNegotiator:
        """Create a new virtual negotiator.

        Args:
            name: Display name for the virtual negotiator
            base_type_name: Full type name of the base negotiator
            params: Custom parameters for the negotiator
            description: User-friendly description
            tags: Tags for categorization (will include "virtual" automatically)

        Returns:
            The created virtual negotiator.

        Raises:
            ValueError: If name is empty or already exists.
        """
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        # Check for duplicate names
        if cls.get_by_name(name):
            raise ValueError(f"A virtual negotiator named '{name}' already exists")

        # Ensure "virtual" tag is always present
        final_tags = list(tags) if tags else []
        if "virtual" not in final_tags:
            final_tags.insert(0, "virtual")

        now = datetime.now(timezone.utc).isoformat()
        vn = VirtualNegotiator(
            id=str(uuid.uuid4()),
            name=name.strip(),
            base_type_name=base_type_name,
            description=description,
            tags=final_tags,
            params=params or {},
            created_at=now,
            modified_at=now,
            enabled=True,
        )

        cls._load_all()[vn.id] = vn
        cls._save_all()

        # Register in negmas registry
        from .registry_service import register_virtual_negotiator

        register_virtual_negotiator(vn)

        return vn

    @classmethod
    def update(
        cls,
        vn_id: str,
        name: str | None = None,
        params: dict | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> VirtualNegotiator | None:
        """Update an existing virtual negotiator.

        Args:
            vn_id: ID of the virtual negotiator to update
            name: New name (optional)
            params: New parameters (optional, replaces existing)
            description: New description (optional)
            tags: New tags (optional, replaces existing)

        Returns:
            The updated virtual negotiator, or None if not found.

        Raises:
            ValueError: If new name conflicts with existing.
        """
        vn = cls.get(vn_id)
        if vn is None:
            return None

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Name cannot be empty")
            # Check for duplicate names (excluding current)
            existing = cls.get_by_name(name)
            if existing and existing.id != vn_id:
                raise ValueError(f"A virtual negotiator named '{name}' already exists")
            vn.name = name

        if params is not None:
            vn.params = params

        if description is not None:
            vn.description = description

        if tags is not None:
            vn.tags = tags

        vn.modified_at = datetime.now(timezone.utc).isoformat()
        cls._save_all()

        # Re-register in negmas registry if name or params changed
        if name is not None or params is not None:
            from .registry_service import (
                unregister_virtual_negotiator,
                register_virtual_negotiator,
            )

            unregister_virtual_negotiator(vn_id)
            register_virtual_negotiator(vn)

        return vn

    @classmethod
    def delete(cls, vn_id: str) -> bool:
        """Delete a virtual negotiator.

        Args:
            vn_id: ID of the virtual negotiator to delete

        Returns:
            True if deleted, False if not found.
        """
        cache = cls._load_all()
        if vn_id not in cache:
            return False

        del cache[vn_id]
        cls._save_all()

        # Unregister from negmas registry
        from .registry_service import unregister_virtual_negotiator

        unregister_virtual_negotiator(vn_id)

        return True

    @classmethod
    def set_enabled(cls, vn_id: str, enabled: bool) -> VirtualNegotiator | None:
        """Enable or disable a virtual negotiator.

        Args:
            vn_id: ID of the virtual negotiator
            enabled: New enabled state

        Returns:
            The updated virtual negotiator, or None if not found.
        """
        vn = cls.get(vn_id)
        if vn is None:
            return None

        vn.enabled = enabled
        vn.modified_at = datetime.now(timezone.utc).isoformat()
        cls._save_all()
        return vn

    @classmethod
    def list_by_base_type(
        cls, base_type: str, include_disabled: bool = True
    ) -> list[VirtualNegotiator]:
        """List all virtual negotiators based on a specific negotiator type.

        Args:
            base_type: The base negotiator type name to filter by
            include_disabled: If True, include disabled virtual negotiators

        Returns:
            List of virtual negotiators based on the specified type.
        """
        all_vns = list(cls._load_all().values())
        result = [vn for vn in all_vns if vn.base_type_name == base_type]

        if not include_disabled:
            result = [vn for vn in result if vn.enabled]

        return sorted(result, key=lambda vn: vn.name.lower())

    @classmethod
    def duplicate(
        cls, vn_id: str, new_name: str | None = None
    ) -> VirtualNegotiator | None:
        """Duplicate an existing virtual negotiator.

        Args:
            vn_id: ID of the virtual negotiator to duplicate
            new_name: Name for the duplicate (defaults to "Copy of <name>")

        Returns:
            The duplicated virtual negotiator, or None if original not found.
        """
        vn = cls.get(vn_id)
        if vn is None:
            return None

        if new_name is None:
            new_name = f"Copy of {vn.name}"
            # Ensure unique name
            base_name = new_name
            counter = 2
            while cls.get_by_name(new_name):
                new_name = f"{base_name} ({counter})"
                counter += 1

        return cls.create(
            name=new_name,
            base_type_name=vn.base_type_name,
            params=dict(vn.params),  # Copy params
            description=vn.description,
            tags=list(vn.tags),  # Copy tags
        )

    @classmethod
    def get_all_tags(cls) -> list[str]:
        """Get all unique tags used by virtual negotiators."""
        all_tags = set()
        for vn in cls._load_all().values():
            all_tags.update(vn.tags)
        return sorted(all_tags)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-memory cache, forcing reload from disk."""
        cls._cache = None

    @classmethod
    def export_all(cls) -> list[dict]:
        """Export all virtual negotiators as a list of dicts."""
        return [vn.to_dict() for vn in cls._load_all().values()]

    @classmethod
    def import_all(cls, data: list[dict], merge: bool = True) -> tuple[int, int]:
        """Import virtual negotiators from a list of dicts.

        Args:
            data: List of virtual negotiator dicts
            merge: If True, skip existing (by name); if False, replace all

        Returns:
            Tuple of (imported_count, skipped_count)
        """
        if not merge:
            cls._cache = {}

        cache = cls._load_all()
        imported = 0
        skipped = 0

        for item in data:
            try:
                vn = VirtualNegotiator.from_dict(item)
                # Check for existing by name
                existing = cls.get_by_name(vn.name)
                if existing and merge:
                    skipped += 1
                    continue

                # Generate new ID if merging or if ID already exists
                if merge or vn.id in cache:
                    vn.id = str(uuid.uuid4())

                cache[vn.id] = vn
                imported += 1
            except (KeyError, ValueError) as e:
                print(f"Error importing virtual negotiator: {e}")
                skipped += 1

        cls._save_all()
        return imported, skipped
