"""Negotiation definition service - save, load, and manage negotiation definitions."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.negotiation_definition import NegotiationDefinition


class NegotiationDefinitionService:
    """Service for managing saved negotiation definitions."""

    def __init__(self, storage_dir: Path | None = None):
        """Initialize the service.

        Args:
            storage_dir: Directory to store definitions. Defaults to ~/negmas/app/negotiations/
        """
        if storage_dir is None:
            storage_dir = Path.home() / "negmas" / "app" / "negotiations"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, definition_id: str, format: str = "yaml") -> Path:
        """Get the file path for a definition."""
        ext = "yaml" if format == "yaml" else "json"
        return self.storage_dir / f"{definition_id}.{ext}"

    def save(self, definition: NegotiationDefinition, format: str = "yaml") -> str:
        """Save a negotiation definition.

        Args:
            definition: The definition to save
            format: "yaml" or "json"

        Returns:
            The definition ID
        """
        # Generate ID if not present
        if not definition.id:
            definition.id = str(uuid.uuid4())[:8]

        # Set timestamps
        now = datetime.now().isoformat()
        if not definition.created_at:
            definition.created_at = now
        definition.updated_at = now

        # Save to file
        path = self._get_path(definition.id, format)
        definition.save(path, format)

        return definition.id

    def load(self, definition_id: str) -> NegotiationDefinition | None:
        """Load a negotiation definition by ID."""
        # Try yaml first, then json
        for ext in ("yaml", "json"):
            path = self._get_path(definition_id, ext)
            if path.exists():
                return NegotiationDefinition.load(path)
        return None

    def delete(self, definition_id: str) -> bool:
        """Delete a negotiation definition."""
        deleted = False
        for ext in ("yaml", "json"):
            path = self._get_path(definition_id, ext)
            if path.exists():
                path.unlink()
                deleted = True
        return deleted

    def list_all(self) -> list[dict[str, Any]]:
        """List all saved definitions (metadata only)."""
        definitions = []

        for path in self.storage_dir.glob("*.yaml"):
            try:
                defn = NegotiationDefinition.load(path)
                definitions.append(
                    {
                        "id": defn.id,
                        "name": defn.name,
                        "description": defn.description,
                        "mechanism": defn.mechanism.class_name,
                        "scenario": defn.scenario.path or "Custom",
                        "n_negotiators": len(defn.negotiators),
                        "tags": defn.tags,
                        "created_at": defn.created_at,
                        "updated_at": defn.updated_at,
                    }
                )
            except Exception:
                continue

        for path in self.storage_dir.glob("*.json"):
            # Skip if yaml version exists
            yaml_path = path.with_suffix(".yaml")
            if yaml_path.exists():
                continue

            try:
                defn = NegotiationDefinition.load(path)
                definitions.append(
                    {
                        "id": defn.id,
                        "name": defn.name,
                        "description": defn.description,
                        "mechanism": defn.mechanism.class_name,
                        "scenario": defn.scenario.path or "Custom",
                        "n_negotiators": len(defn.negotiators),
                        "tags": defn.tags,
                        "created_at": defn.created_at,
                        "updated_at": defn.updated_at,
                    }
                )
            except Exception:
                continue

        # Sort by updated_at descending
        definitions.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return definitions

    def duplicate(self, definition_id: str, new_name: str | None = None) -> str | None:
        """Duplicate a definition with a new ID."""
        original = self.load(definition_id)
        if not original:
            return None

        # Create copy with new ID
        original.id = None
        original.name = new_name or f"{original.name} (Copy)"
        original.created_at = None
        original.updated_at = None

        return self.save(original)

    def export(self, definition_id: str, path: Path, format: str = "yaml") -> bool:
        """Export a definition to a specific path."""
        defn = self.load(definition_id)
        if not defn:
            return False

        defn.save(path, format)
        return True

    def import_definition(self, path: Path) -> str | None:
        """Import a definition from a file."""
        try:
            defn = NegotiationDefinition.load(path)
            # Generate new ID on import
            defn.id = None
            defn.created_at = None
            return self.save(defn)
        except Exception:
            return None


# Global service instance
_definition_service: NegotiationDefinitionService | None = None


def get_definition_service() -> NegotiationDefinitionService:
    """Get the global definition service instance."""
    global _definition_service
    if _definition_service is None:
        _definition_service = NegotiationDefinitionService()
    return _definition_service
