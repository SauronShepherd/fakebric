from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


SCHEMA_VERSION = "1.0"
POWERBI_FEATURE_FLAG = "FAKEBRIC_POWERBI_EMULATION"


class LifecycleState(str, Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    QUERY_ERROR = "QUERY_ERROR"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VersionedResource(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: str = Field(default=SCHEMA_VERSION)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    revision: int = Field(default=1, ge=1)
    state: LifecycleState = LifecycleState.DRAFT
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")

    @field_validator("version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema version: {value}")
        return value

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json", by_alias=True),
            sort_keys=True,
            separators=(",", ":"),
        )

    def etag(self) -> str:
        digest = hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
        return f'"{digest}"'


def feature_enabled(env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return source.get(POWERBI_FEATURE_FLAG, "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
