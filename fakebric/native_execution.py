from __future__ import annotations

import json
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

NATIVE_EXECUTION_CONTRACT_VERSION = "1"
NATIVE_GLOBAL_FLAG = "FAKEBRIC_NATIVE_EXECUTION_ENABLED"


class NativeExecutionMode(str, Enum):
    JVM = "jvm"
    NATIVE = "native"
    AUTO = "auto"
    COMPARE = "compare"


class NativeBackend(str, Enum):
    JVM = "jvm"
    NATIVE = "native"


class NativeErrorCode(str, Enum):
    NATIVE_DISABLED = "NATIVE_DISABLED"
    NATIVE_PLAN_UNSUPPORTED = "NATIVE_PLAN_UNSUPPORTED"
    NATIVE_INIT_FAILED = "NATIVE_INIT_FAILED"
    NATIVE_EXECUTION_FAILED = "NATIVE_EXECUTION_FAILED"
    NATIVE_RESULT_MISMATCH = "NATIVE_RESULT_MISMATCH"
    NATIVE_TIMEOUT = "NATIVE_TIMEOUT"
    NATIVE_OOM = "NATIVE_OOM"
    NATIVE_SECURITY_POLICY = "NATIVE_SECURITY_POLICY"


SAFE_SESSION_SPARK_CONF = frozenset(
    {
        "spark.sql.adaptive.enabled",
        "spark.sql.shuffle.partitions",
    }
)


class NativeExecutionConfig(BaseModel):
    """Versioned, opt-in configuration supplied by a model/session."""

    model_config = ConfigDict(extra="forbid")

    contractVersion: str = NATIVE_EXECUTION_CONTRACT_VERSION
    mode: NativeExecutionMode = NativeExecutionMode.JVM
    enabled: bool = False
    glutenVersion: str | None = None
    veloxVersion: str | None = None
    fallback: str = "jvm"
    compareResults: bool = False
    maxMemoryFraction: float = Field(default=0.6, gt=0.0, le=1.0)
    timeoutSeconds: int = Field(default=1200, ge=1, le=1200)
    sparkConf: dict[str, bool | int | float | str] = Field(default_factory=dict)

    @field_validator("contractVersion")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        if value != NATIVE_EXECUTION_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported NativeExecutionConfig contractVersion {value!r}; "
                f"expected {NATIVE_EXECUTION_CONTRACT_VERSION!r}"
            )
        return value

    @field_validator("fallback")
    @classmethod
    def validate_fallback(cls, value: str) -> str:
        if value != "jvm":
            raise ValueError("native fallback must be 'jvm'")
        return value

    @field_validator("sparkConf")
    @classmethod
    def validate_spark_conf(
        cls, value: dict[str, bool | int | float | str]
    ) -> dict[str, bool | int | float | str]:
        rejected = sorted(set(value) - SAFE_SESSION_SPARK_CONF)
        if rejected:
            raise ValueError(
                "Spark configuration is not allowed for native execution: "
                + ", ".join(rejected)
            )
        return value


class NativeExecutionDiagnostics(BaseModel):
    """Public diagnostic envelope; plans/results must be redacted by producers."""

    model_config = ConfigDict(extra="forbid")

    contractVersion: str = NATIVE_EXECUTION_CONTRACT_VERSION
    requestedBackend: NativeExecutionMode
    effectiveBackend: NativeBackend | None = None
    versions: dict[str, str] = Field(default_factory=dict)
    originalPlan: str | None = None
    convertedPlan: str | None = None
    nativeOperators: list[str] = Field(default_factory=list)
    jvmOperators: list[str] = Field(default_factory=list)
    fallbackReason: str | None = None
    phaseDurationsMs: dict[str, float] = Field(default_factory=dict)
    rowsProcessed: int | None = Field(default=None, ge=0)
    bytesProcessed: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    compatibility: dict[str, Any] = Field(default_factory=dict)
    errorCode: NativeErrorCode | None = None


_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})


def native_global_enabled(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    raw = env.get(NATIVE_GLOBAL_FLAG, "").strip().lower()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise ValueError(f"{NATIVE_GLOBAL_FLAG} must be a boolean value")


def native_effective_enabled(
    config: NativeExecutionConfig, environ: Mapping[str, str] | None = None
) -> bool:
    """Native can only be effective when both global and session flags opt in."""

    return native_global_enabled(environ) and config.enabled


_CHECKSUM_LENGTHS = {"sha256": 64, "sha512": 128}


def _validate_checksum(checksum: Any, profile_id: str) -> None:
    if not isinstance(checksum, dict):
        raise ValueError(f"profile {profile_id}: artifact checksum is required")
    algorithm = checksum.get("algorithm")
    value = checksum.get("value")
    expected = _CHECKSUM_LENGTHS.get(algorithm)
    if expected is None:
        raise ValueError(f"profile {profile_id}: unsupported checksum algorithm")
    if not isinstance(value, str) or not re.fullmatch(
        rf"[0-9a-fA-F]{{{expected}}}", value
    ):
        raise ValueError(f"profile {profile_id}: invalid {algorithm} checksum")


def validate_runtime_matrix(matrix: Mapping[str, Any]) -> None:
    if matrix.get("schemaVersion") != 1:
        raise ValueError("native runtime matrix schemaVersion must be 1")
    if matrix.get("defaultEnabled") is not False:
        raise ValueError("native runtime matrix must default to disabled")
    profiles = matrix.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("native runtime matrix requires at least one profile")

    ids: set[str] = set()
    required_versions = {"spark", "scala", "java", "gluten", "velox"}
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("native runtime matrix profiles must be objects")
        profile_id = profile.get("id")
        if not isinstance(profile_id, str) or not profile_id:
            raise ValueError("native runtime profile id is required")
        if profile_id in ids:
            raise ValueError(f"duplicate native runtime profile id: {profile_id}")
        ids.add(profile_id)

        architecture = profile.get("architecture")
        if architecture not in {"amd64", "arm64"}:
            raise ValueError(f"profile {profile_id}: unsupported architecture")

        versions = profile.get("versions")
        if not isinstance(versions, dict):
            raise ValueError(f"profile {profile_id}: versions are required")
        missing = sorted(
            key for key in required_versions if not isinstance(versions.get(key), str) or not versions[key]
        )
        if missing:
            raise ValueError(
                f"profile {profile_id}: missing required versions: {', '.join(missing)}"
            )

        artifact = profile.get("artifact")
        if not isinstance(artifact, dict) or not isinstance(artifact.get("url"), str):
            raise ValueError(f"profile {profile_id}: artifact URL is required")
        if not artifact["url"].startswith("https://"):
            raise ValueError(f"profile {profile_id}: artifact URL must use HTTPS")
        _validate_checksum(artifact.get("checksum"), profile_id)

        sha256 = artifact.get("sha256")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
            raise ValueError(f"profile {profile_id}: valid SHA-256 is required")


def load_runtime_matrix(path: str | Path) -> dict[str, Any]:
    matrix = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_runtime_matrix(matrix)
    return matrix
