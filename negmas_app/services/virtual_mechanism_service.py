"""Service for managing virtual mechanisms (saved mechanism configurations)."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..models.mechanism import VirtualMechanism

# Storage path for virtual mechanisms
VIRTUAL_MECHANISMS_FILE = Path.home() / "negmas" / "app" / "virtual_mechanisms.json"


class VirtualMechanismService:
    """Service for CRUD operations on virtual mechanisms."""

    _cache: dict[str, VirtualMechanism] | None = None

    @classmethod
    def _load_all(cls) -> dict[str, VirtualMechanism]:
        """Load all virtual mechanisms from storage."""
        if cls._cache is not None:
            return cls._cache

        cls._cache = {}
        if not VIRTUAL_MECHANISMS_FILE.exists():
            return cls._cache

        try:
            with open(VIRTUAL_MECHANISMS_FILE) as f:
                data = json.load(f)
            for item in data.get("virtual_mechanisms", []):
                vm = VirtualMechanism.from_dict(item)
                cls._cache[vm.id] = vm
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading virtual mechanisms: {e}")

        return cls._cache

    @classmethod
    def _save_all(cls) -> None:
        """Save all virtual mechanisms to storage."""
        if cls._cache is None:
            return

        VIRTUAL_MECHANISMS_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {"virtual_mechanisms": [vm.to_dict() for vm in cls._cache.values()]}
        with open(VIRTUAL_MECHANISMS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def list_all(
        cls,
        search: str | None = None,
        tags: list[str] | None = None,
        base_type: str | None = None,
    ) -> list[VirtualMechanism]:
        """List all virtual mechanisms with optional filtering.

        Args:
            search: Search string to match in name/description
            tags: Filter by tags (match any)
            base_type: Filter by base mechanism type

        Returns:
            List of matching virtual mechanisms.
        """
        all_vms = list(cls._load_all().values())

        if search:
            search_lower = search.lower()
            all_vms = [
                vm
                for vm in all_vms
                if search_lower in vm.name.lower()
                or search_lower in vm.description.lower()
                or any(search_lower in tag.lower() for tag in vm.tags)
            ]

        if tags:
            tags_lower = [t.lower() for t in tags]
            all_vms = [
                vm
                for vm in all_vms
                if any(tag.lower() in tags_lower for tag in vm.tags)
            ]

        if base_type:
            all_vms = [vm for vm in all_vms if vm.base_type == base_type]

        return sorted(all_vms, key=lambda vm: vm.name.lower())

    @classmethod
    def get(cls, vm_id: str) -> VirtualMechanism | None:
        """Get a virtual mechanism by ID."""
        return cls._load_all().get(vm_id)

    @classmethod
    def get_by_name(cls, name: str) -> VirtualMechanism | None:
        """Get a virtual mechanism by name (case-insensitive)."""
        name_lower = name.lower()
        for vm in cls._load_all().values():
            if vm.name.lower() == name_lower:
                return vm
        return None

    @classmethod
    def create(
        cls,
        name: str,
        base_type: str,
        params: dict | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ) -> VirtualMechanism:
        """Create a new virtual mechanism.

        Args:
            name: Display name for the virtual mechanism
            base_type: Base mechanism type (e.g., "sao", "tau", "gb")
            params: Custom parameters for the mechanism
            description: User-friendly description
            tags: Tags for categorization

        Returns:
            The created virtual mechanism.

        Raises:
            ValueError: If name is empty or already exists.
        """
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")

        # Check for duplicate names
        if cls.get_by_name(name):
            raise ValueError(f"A virtual mechanism named '{name}' already exists")

        now = datetime.now(timezone.utc).isoformat()
        vm = VirtualMechanism(
            id=str(uuid.uuid4()),
            name=name.strip(),
            base_type=base_type,
            description=description,
            tags=tags or [],
            params=params or {},
            created_at=now,
            modified_at=now,
        )

        cls._load_all()[vm.id] = vm
        cls._save_all()

        # Register in negmas registry
        from .registry_service import register_virtual_mechanism

        register_virtual_mechanism(vm)

        return vm

    @classmethod
    def update(
        cls,
        vm_id: str,
        name: str | None = None,
        params: dict | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> VirtualMechanism | None:
        """Update an existing virtual mechanism.

        Args:
            vm_id: ID of the virtual mechanism to update
            name: New name (optional)
            params: New parameters (optional, replaces existing)
            description: New description (optional)
            tags: New tags (optional, replaces existing)

        Returns:
            The updated virtual mechanism, or None if not found.

        Raises:
            ValueError: If new name conflicts with existing.
        """
        vm = cls.get(vm_id)
        if vm is None:
            return None

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Name cannot be empty")
            # Check for duplicate names (excluding current)
            existing = cls.get_by_name(name)
            if existing and existing.id != vm_id:
                raise ValueError(f"A virtual mechanism named '{name}' already exists")
            vm.name = name

        if params is not None:
            vm.params = params

        if description is not None:
            vm.description = description

        if tags is not None:
            vm.tags = tags

        vm.modified_at = datetime.now(timezone.utc).isoformat()
        cls._save_all()

        # Re-register in negmas registry if name or params changed
        if name is not None or params is not None:
            from .registry_service import (
                unregister_virtual_mechanism,
                register_virtual_mechanism,
            )

            unregister_virtual_mechanism(vm_id)
            register_virtual_mechanism(vm)

        return vm

    @classmethod
    def delete(cls, vm_id: str) -> bool:
        """Delete a virtual mechanism.

        Args:
            vm_id: ID of the virtual mechanism to delete

        Returns:
            True if deleted, False if not found.
        """
        cache = cls._load_all()
        if vm_id not in cache:
            return False

        del cache[vm_id]
        cls._save_all()

        # Unregister from negmas registry
        from .registry_service import unregister_virtual_mechanism

        unregister_virtual_mechanism(vm_id)

        return True

    @classmethod
    def duplicate(
        cls, vm_id: str, new_name: str | None = None
    ) -> VirtualMechanism | None:
        """Duplicate an existing virtual mechanism.

        Args:
            vm_id: ID of the virtual mechanism to duplicate
            new_name: Name for the duplicate (defaults to "Copy of <name>")

        Returns:
            The duplicated virtual mechanism, or None if original not found.
        """
        vm = cls.get(vm_id)
        if vm is None:
            return None

        if new_name is None:
            new_name = f"Copy of {vm.name}"
            # Ensure unique name
            base_name = new_name
            counter = 2
            while cls.get_by_name(new_name):
                new_name = f"{base_name} ({counter})"
                counter += 1

        return cls.create(
            name=new_name,
            base_type=vm.base_type,
            params=dict(vm.params),  # Copy params
            description=vm.description,
            tags=list(vm.tags),  # Copy tags
        )

    @classmethod
    def get_all_tags(cls) -> list[str]:
        """Get all unique tags used by virtual mechanisms."""
        all_tags = set()
        for vm in cls._load_all().values():
            all_tags.update(vm.tags)
        return sorted(all_tags)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-memory cache, forcing reload from disk."""
        cls._cache = None

    @classmethod
    def export_all(cls) -> list[dict]:
        """Export all virtual mechanisms as a list of dicts."""
        return [vm.to_dict() for vm in cls._load_all().values()]

    @classmethod
    def import_all(cls, data: list[dict], merge: bool = True) -> tuple[int, int]:
        """Import virtual mechanisms from a list of dicts.

        Args:
            data: List of virtual mechanism dicts
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
                vm = VirtualMechanism.from_dict(item)
                # Check for existing by name
                existing = cls.get_by_name(vm.name)
                if existing and merge:
                    skipped += 1
                    continue

                # Generate new ID if merging or if ID already exists
                if merge or vm.id in cache:
                    vm.id = str(uuid.uuid4())

                cache[vm.id] = vm
                imported += 1
            except (KeyError, ValueError) as e:
                print(f"Error importing virtual mechanism: {e}")
                skipped += 1

        cls._save_all()
        return imported, skipped
