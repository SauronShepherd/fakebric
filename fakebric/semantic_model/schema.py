from __future__ import annotations

from pydantic import Field

from fakebric.powerbi.common import VersionedResource


class SemanticModel(VersionedResource):
    """Day-1 semantic model contract; domain entities arrive in later increments."""

    tables: list[dict] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)
