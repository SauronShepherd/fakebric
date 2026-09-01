from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fakebric.powerbi.common import SCHEMA_VERSION

Migration = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationRegistry:
    def __init__(self) -> None:
        self._migrations: dict[tuple[str, str], Migration] = {}

    def register(self, source: str, target: str, migration: Migration) -> None:
        self._migrations[(source, target)] = migration

    def migrate(self, payload: dict[str, Any], target: str = SCHEMA_VERSION) -> dict[str, Any]:
        source = str(payload.get("version", ""))
        if source == target:
            return dict(payload)
        migration = self._migrations.get((source, target))
        if migration is None:
            raise ValueError(f"no migration registered from {source!r} to {target!r}")
        migrated = migration(dict(payload))
        migrated["version"] = target
        return migrated
