from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field

from fakebric.native_execution import NativeErrorCode

NATIVE_PLAN_CATALOG_SCHEMA_VERSION = 1
DEFAULT_NATIVE_PLAN_CATALOG = (
    Path(__file__).resolve().parents[1] / "native-plan-support-catalog.json"
)


class NativePlanStatus(str, Enum):
    SUPPORTED = "supported"
    FALLBACK = "fallback"
    BLOCKED = "blocked"


class NativePlanReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    category: str
    item: str
    message: str


class NativePlanCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalogVersion: str
    status: NativePlanStatus
    nativeEligible: bool
    errorCode: NativeErrorCode | None = None
    logicalOperators: list[str] = Field(default_factory=list)
    physicalOperators: list[str] = Field(default_factory=list)
    functionsChecked: list[str] = Field(default_factory=list)
    dataTypesChecked: list[str] = Field(default_factory=list)
    reasons: list[NativePlanReason] = Field(default_factory=list)
    explanation: str


def validate_native_plan_catalog(catalog: Mapping[str, Any]) -> None:
    if catalog.get("schemaVersion") != NATIVE_PLAN_CATALOG_SCHEMA_VERSION:
        raise ValueError("native plan support catalog schemaVersion must be 1")
    version = catalog.get("catalogVersion")
    if not isinstance(version, str) or not version:
        raise ValueError("native plan support catalogVersion is required")
    if catalog.get("unknownOperatorPolicy") != "fallback":
        raise ValueError("unknown native operators must fall back to JVM")

    for section in ("logicalOperators", "physicalOperators"):
        value = catalog.get(section)
        if not isinstance(value, dict):
            raise ValueError(f"native plan catalog section {section!r} is required")
        for bucket in ("supported", "fallback", "blocked"):
            entries = value.get(bucket)
            if not isinstance(entries, list) or not all(
                isinstance(item, str) and item for item in entries
            ):
                raise ValueError(
                    f"native plan catalog {section}.{bucket} must be a string list"
                )

    expressions = catalog.get("expressions")
    if not isinstance(expressions, dict):
        raise ValueError("native plan catalog expressions section is required")
    for bucket in (
        "supportedFunctions",
        "fallbackFunctions",
        "supportedDataTypes",
        "fallbackDataTypes",
    ):
        entries = expressions.get(bucket)
        if not isinstance(entries, list) or not all(
            isinstance(item, str) and item for item in entries
        ):
            raise ValueError(
                f"native plan catalog expressions.{bucket} must be a string list"
            )

    markers = catalog.get("markers")
    if not isinstance(markers, dict):
        raise ValueError("native plan catalog markers section is required")
    for bucket in ("fallback", "blocked"):
        groups = markers.get(bucket)
        if not isinstance(groups, dict):
            raise ValueError(f"native plan catalog markers.{bucket} is required")
        for name, entries in groups.items():
            if not isinstance(name, str) or not isinstance(entries, list) or not all(
                isinstance(item, str) and item for item in entries
            ):
                raise ValueError(
                    f"native plan catalog markers.{bucket} entries must be string lists"
                )

    security = catalog.get("security")
    if not isinstance(security, dict):
        raise ValueError("native plan catalog security section is required")
    allowed = security.get("allowedSparkConf")
    if not isinstance(allowed, list) or not all(
        isinstance(item, str) and item for item in allowed
    ):
        raise ValueError("native plan catalog security.allowedSparkConf is required")


def load_native_plan_catalog(
    path: str | Path = DEFAULT_NATIVE_PLAN_CATALOG,
) -> dict[str, Any]:
    catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_native_plan_catalog(catalog)
    return catalog


_TREE_PREFIX_RE = re.compile(r"^[\s|:+\-]+")
_STAGE_PREFIX_RE = re.compile(r"^\*\(\d+\)\s*")
_OPERATOR_RE = re.compile(r"^['!]?([A-Za-z][A-Za-z0-9_]*)")


def _operator_records(plan: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for raw_line in plan.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("=="):
            continue
        line = _TREE_PREFIX_RE.sub("", raw_line)
        line = _STAGE_PREFIX_RE.sub("", line.lstrip())
        match = _OPERATOR_RE.match(line)
        if not match:
            continue
        records.append((match.group(1), stripped))
    return records


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _append_reason(
    reasons: list[NativePlanReason],
    seen: set[tuple[str, str]],
    *,
    code: str,
    category: str,
    item: str,
    message: str,
) -> None:
    key = (code, item.lower())
    if key in seen:
        return
    seen.add(key)
    reasons.append(
        NativePlanReason(
            code=code,
            category=category,
            item=item,
            message=message,
        )
    )


def _classify_operators(
    records: list[tuple[str, str]],
    catalog_section: Mapping[str, Any],
    reasons: list[NativePlanReason],
    seen: set[tuple[str, str]],
    *,
    plan_kind: str,
    required_scan_format: str,
) -> None:
    supported = set(catalog_section["supported"])
    fallback = set(catalog_section["fallback"])
    blocked = set(catalog_section["blocked"])
    scan_operators = set(catalog_section.get("scanOperators", []))

    if not records:
        _append_reason(
            reasons,
            seen,
            code=f"MISSING_{plan_kind.upper()}_PLAN",
            category="plan",
            item=plan_kind,
            message=f"{plan_kind} plan is required before native execution",
        )
        return

    for operator, line in records:
        if operator in blocked:
            _append_reason(
                reasons,
                seen,
                code="BLOCKED_OPERATOR",
                category=plan_kind,
                item=operator,
                message=f"{plan_kind} operator is blocked from native execution",
            )
            continue
        if operator in fallback:
            _append_reason(
                reasons,
                seen,
                code="FALLBACK_OPERATOR",
                category=plan_kind,
                item=operator,
                message=f"{plan_kind} operator requires JVM fallback",
            )
            continue
        if operator not in supported:
            _append_reason(
                reasons,
                seen,
                code="UNKNOWN_OPERATOR",
                category=plan_kind,
                item=operator,
                message=f"{plan_kind} operator is not in the audited native catalog",
            )
            continue
        if operator in scan_operators and required_scan_format not in line.lower():
            _append_reason(
                reasons,
                seen,
                code="UNSUPPORTED_SCAN_FORMAT",
                category=plan_kind,
                item=operator,
                message=f"only {required_scan_format} scans are native-audited",
            )


def _classify_markers(
    plan_text: str,
    markers: Mapping[str, list[str]],
    reasons: list[NativePlanReason],
    seen: set[tuple[str, str]],
    *,
    blocked: bool,
) -> None:
    haystack = plan_text.lower()
    reason_code = "BLOCKED_PLAN_MARKER" if blocked else "FALLBACK_PLAN_MARKER"
    action = "blocked from native execution" if blocked else "requires JVM fallback"
    for category, values in markers.items():
        for marker in values:
            if marker.lower() in haystack:
                _append_reason(
                    reasons,
                    seen,
                    code=reason_code,
                    category=category,
                    item=marker,
                    message=f"{category} marker {action}",
                )


def _classify_inventory(
    observed: Iterable[str],
    *,
    supported: set[str],
    fallback: set[str],
    category: str,
    reasons: list[NativePlanReason],
    seen: set[tuple[str, str]],
) -> list[str]:
    normalized = _unique(item.strip().lower() for item in observed if item.strip())
    for item in normalized:
        if item in supported:
            continue
        code = "FALLBACK_EXPRESSION" if item in fallback else "UNKNOWN_EXPRESSION"
        _append_reason(
            reasons,
            seen,
            code=code,
            category=category,
            item=item,
            message=f"{category} is not in the audited native Level A set",
        )
    return normalized


def _classify_spark_conf(
    spark_conf: Mapping[str, Any],
    allowed_keys: set[str],
    reasons: list[NativePlanReason],
    seen: set[tuple[str, str]],
) -> None:
    for key in sorted(spark_conf):
        if key in allowed_keys:
            continue
        _append_reason(
            reasons,
            seen,
            code="FORBIDDEN_SPARK_CONFIG",
            category="security",
            item=key,
            message="Spark configuration key is not allowed for native execution",
        )


def _status_for(reasons: list[NativePlanReason]) -> NativePlanStatus:
    blocked_codes = {
        "BLOCKED_OPERATOR",
        "BLOCKED_PLAN_MARKER",
        "FORBIDDEN_SPARK_CONFIG",
    }
    if any(reason.code in blocked_codes for reason in reasons):
        return NativePlanStatus.BLOCKED
    if reasons:
        return NativePlanStatus.FALLBACK
    return NativePlanStatus.SUPPORTED


def _explain(
    status: NativePlanStatus,
    catalog_version: str,
    reasons: list[NativePlanReason],
) -> str:
    if status is NativePlanStatus.SUPPORTED:
        return (
            f"native plan supported by catalog {catalog_version}; "
            "logical and physical operators are audited for Level A"
        )
    items = ", ".join(f"{reason.category}:{reason.item}" for reason in reasons)
    if status is NativePlanStatus.BLOCKED:
        return (
            f"native plan blocked by catalog {catalog_version}; "
            f"policy indicators: {items}"
        )
    return (
        f"native plan requires JVM fallback under catalog {catalog_version}; "
        f"compatibility indicators: {items}"
    )


def analyze_native_plan(
    logical_plan: str,
    physical_plan: str,
    *,
    spark_conf: Mapping[str, Any] | None = None,
    functions: Iterable[str] = (),
    data_types: Iterable[str] = (),
    catalog: Mapping[str, Any] | None = None,
) -> NativePlanCompatibility:
    resolved_catalog = (
        load_native_plan_catalog() if catalog is None else dict(catalog)
    )
    validate_native_plan_catalog(resolved_catalog)

    reasons: list[NativePlanReason] = []
    seen: set[tuple[str, str]] = set()
    logical_records = _operator_records(logical_plan)
    physical_records = _operator_records(physical_plan)
    scan_format = str(resolved_catalog.get("requiredScanFormat", "parquet")).lower()

    _classify_operators(
        logical_records,
        resolved_catalog["logicalOperators"],
        reasons,
        seen,
        plan_kind="logical",
        required_scan_format=scan_format,
    )
    _classify_operators(
        physical_records,
        resolved_catalog["physicalOperators"],
        reasons,
        seen,
        plan_kind="physical",
        required_scan_format=scan_format,
    )

    combined_plan = f"{logical_plan}\n{physical_plan}"
    _classify_markers(
        combined_plan,
        resolved_catalog["markers"]["blocked"],
        reasons,
        seen,
        blocked=True,
    )
    _classify_markers(
        combined_plan,
        resolved_catalog["markers"]["fallback"],
        reasons,
        seen,
        blocked=False,
    )

    expressions = resolved_catalog["expressions"]
    checked_functions = _classify_inventory(
        functions,
        supported={item.lower() for item in expressions["supportedFunctions"]},
        fallback={item.lower() for item in expressions["fallbackFunctions"]},
        category="function",
        reasons=reasons,
        seen=seen,
    )
    checked_data_types = _classify_inventory(
        data_types,
        supported={item.lower() for item in expressions["supportedDataTypes"]},
        fallback={item.lower() for item in expressions["fallbackDataTypes"]},
        category="dataType",
        reasons=reasons,
        seen=seen,
    )

    _classify_spark_conf(
        spark_conf or {},
        set(resolved_catalog["security"]["allowedSparkConf"]),
        reasons,
        seen,
    )

    status = _status_for(reasons)
    error_code = None
    if status is NativePlanStatus.BLOCKED:
        error_code = NativeErrorCode.NATIVE_SECURITY_POLICY
    elif status is NativePlanStatus.FALLBACK:
        error_code = NativeErrorCode.NATIVE_PLAN_UNSUPPORTED

    version = str(resolved_catalog["catalogVersion"])
    return NativePlanCompatibility(
        catalogVersion=version,
        status=status,
        nativeEligible=status is NativePlanStatus.SUPPORTED,
        errorCode=error_code,
        logicalOperators=_unique(operator for operator, _ in logical_records),
        physicalOperators=_unique(operator for operator, _ in physical_records),
        functionsChecked=checked_functions,
        dataTypesChecked=checked_data_types,
        reasons=reasons,
        explanation=_explain(status, version, reasons),
    )
