from __future__ import annotations

from pydantic import Field

from fakebric.powerbi.common import VersionedResource


class Report(VersionedResource):
    """Day-1 report contract; pages and visuals are intentionally deferred to day 8."""

    model_id: str | None = Field(default=None, alias="modelId")
    pages: list[dict] = Field(default_factory=list)
