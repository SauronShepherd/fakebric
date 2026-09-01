from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fakebric.native_execution import (
    NativeBackend,
    NativeErrorCode,
    NativeExecutionConfig,
    NativeExecutionDiagnostics,
    NativeExecutionMode,
    native_effective_enabled,
)
from fakebric.native_plan import NativePlanCompatibility, NativePlanStatus

QUERY_EXECUTION_CONTRACT_VERSION = "1"
NATIVE_SELECTOR_VERSION = "2026-09-01.selector.v1"
_UNSET = object()
_RUNTIME_FALLBACK_CODES = frozenset(
    {
        NativeErrorCode.NATIVE_INIT_FAILED,
        NativeErrorCode.NATIVE_EXECUTION_FAILED,
        NativeErrorCode.NATIVE_TIMEOUT,
        NativeErrorCode.NATIVE_OOM,
    }
)


class QueryExecutionRequest(BaseModel):
    """Canonical query payload replayed unchanged across backend attempts."""

    model_config = ConfigDict(extra="forbid")

    contractVersion: str = QUERY_EXECUTION_CONTRACT_VERSION
    statement: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    filters: list[str] = Field(default_factory=list)
    orderBy: list[str] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=0)

    @field_validator("contractVersion")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        if value != QUERY_EXECUTION_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported QueryExecutionRequest contractVersion {value!r}; "
                f"expected {QUERY_EXECUTION_CONTRACT_VERSION!r}"
            )
        return value


class NativeExecutionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requestedMode: NativeExecutionMode
    requestedBackends: list[NativeBackend]
    plannedBackends: list[NativeBackend]
    effectiveBackend: NativeBackend | None = None
    fallbackAllowed: bool = False
    fallbackReason: NativeErrorCode | None = None
    comparisonRequested: bool = False
    nativeEligible: bool = False
    errorCode: NativeErrorCode | None = None


@dataclass(frozen=True)
class NativeExecutionOutcome:
    value: Any
    decision: NativeExecutionDecision
    diagnostics: NativeExecutionDiagnostics
    attemptedBackends: tuple[NativeBackend, ...]
    fallbackCount: int = 0


class NativeBackendFailure(RuntimeError):
    def __init__(self, code: NativeErrorCode):
        if code not in _RUNTIME_FALLBACK_CODES:
            raise ValueError(f"{code.value} is not a native runtime attempt failure")
        super().__init__(code.value)
        self.code = code


class NativeExecutionError(RuntimeError):
    def __init__(self, code: NativeErrorCode, diagnostics: NativeExecutionDiagnostics):
        super().__init__(code.value)
        self.code = code
        self.diagnostics = diagnostics


def _decision(
    config: NativeExecutionConfig,
    compatibility: NativePlanCompatibility,
    *,
    requested: list[NativeBackend],
    planned: list[NativeBackend],
    effective: NativeBackend | None = None,
    fallback: NativeErrorCode | None = None,
    error: NativeErrorCode | None = None,
    comparison: bool = False,
) -> NativeExecutionDecision:
    return NativeExecutionDecision(
        requestedMode=config.mode,
        requestedBackends=requested,
        plannedBackends=planned,
        effectiveBackend=effective,
        fallbackAllowed=config.mode is NativeExecutionMode.AUTO,
        fallbackReason=fallback,
        comparisonRequested=comparison,
        nativeEligible=compatibility.nativeEligible,
        errorCode=error,
    )


def select_native_execution(
    config: NativeExecutionConfig,
    compatibility: NativePlanCompatibility,
    environ: Mapping[str, str] | None = None,
) -> NativeExecutionDecision:
    mode = config.mode
    requested = (
        [NativeBackend.JVM]
        if mode is NativeExecutionMode.JVM
        else [NativeBackend.JVM, NativeBackend.NATIVE]
        if mode is NativeExecutionMode.COMPARE
        else [NativeBackend.NATIVE]
    )

    if compatibility.status is NativePlanStatus.BLOCKED:
        return _decision(
            config,
            compatibility,
            requested=requested,
            planned=[],
            error=NativeErrorCode.NATIVE_SECURITY_POLICY,
            comparison=mode is NativeExecutionMode.COMPARE,
        )

    if mode is NativeExecutionMode.JVM:
        return _decision(
            config,
            compatibility,
            requested=requested,
            planned=[NativeBackend.JVM],
            effective=NativeBackend.JVM,
        )

    enabled = native_effective_enabled(config, environ)
    supported = compatibility.status is NativePlanStatus.SUPPORTED
    unavailable = (
        NativeErrorCode.NATIVE_DISABLED
        if not enabled
        else NativeErrorCode.NATIVE_PLAN_UNSUPPORTED
        if not supported
        else None
    )

    if mode is NativeExecutionMode.NATIVE:
        if unavailable is not None:
            return _decision(
                config,
                compatibility,
                requested=requested,
                planned=[],
                error=unavailable,
            )
        return _decision(
            config,
            compatibility,
            requested=requested,
            planned=[NativeBackend.NATIVE],
            effective=NativeBackend.NATIVE,
        )

    if mode is NativeExecutionMode.AUTO:
        if unavailable is not None:
            return _decision(
                config,
                compatibility,
                requested=requested,
                planned=[NativeBackend.JVM],
                effective=NativeBackend.JVM,
                fallback=unavailable,
            )
        return _decision(
            config,
            compatibility,
            requested=requested,
            planned=[NativeBackend.NATIVE],
            effective=NativeBackend.NATIVE,
        )

    # Compare is JVM-authoritative until Day 7 can establish result equality.
    if unavailable is not None:
        return _decision(
            config,
            compatibility,
            requested=requested,
            planned=[NativeBackend.JVM],
            effective=NativeBackend.JVM,
            fallback=unavailable,
            comparison=True,
        )
    return _decision(
        config,
        compatibility,
        requested=requested,
        planned=[NativeBackend.JVM, NativeBackend.NATIVE],
        effective=NativeBackend.JVM,
        comparison=True,
    )


def _diagnostics(
    decision: NativeExecutionDecision,
    compatibility: NativePlanCompatibility,
    *,
    attempted: list[NativeBackend] | None = None,
    effective: NativeBackend | None | object = _UNSET,
    fallback: NativeErrorCode | None = None,
    fallback_count: int = 0,
    error: NativeErrorCode | None = None,
) -> NativeExecutionDiagnostics:
    attempted = attempted or []
    return NativeExecutionDiagnostics(
        requestedBackend=decision.requestedMode,
        effectiveBackend=(decision.effectiveBackend if effective is _UNSET else effective),
        fallbackReason=(
            fallback.value
            if fallback is not None
            else decision.fallbackReason.value
            if decision.fallbackReason is not None
            else None
        ),
        compatibility={
            "catalogVersion": compatibility.catalogVersion,
            "status": compatibility.status.value,
            "nativeEligible": compatibility.nativeEligible,
            "reasonCodes": [reason.code for reason in compatibility.reasons],
            "requestedBackends": [backend.value for backend in decision.requestedBackends],
            "attemptedBackends": [backend.value for backend in attempted],
            "fallbackCount": fallback_count,
            "comparisonRequested": decision.comparisonRequested,
        },
        errorCode=error if error is not None else decision.errorCode,
    )


def _failure_code(exc: Exception) -> NativeErrorCode:
    if isinstance(exc, NativeBackendFailure):
        return exc.code
    if isinstance(exc, TimeoutError):
        return NativeErrorCode.NATIVE_TIMEOUT
    if isinstance(exc, MemoryError):
        return NativeErrorCode.NATIVE_OOM
    return NativeErrorCode.NATIVE_EXECUTION_FAILED


def _fresh(snapshot: dict[str, Any]) -> QueryExecutionRequest:
    return QueryExecutionRequest.model_validate(deepcopy(snapshot))


def execute_with_fallback_once(
    request: QueryExecutionRequest,
    config: NativeExecutionConfig,
    compatibility: NativePlanCompatibility,
    *,
    jvm_executor: Callable[[QueryExecutionRequest], Any],
    native_executor: Callable[[QueryExecutionRequest], Any],
    environ: Mapping[str, str] | None = None,
) -> NativeExecutionOutcome:
    """Execute a selected query; only AUTO may retry once on the JVM."""

    decision = select_native_execution(config, compatibility, environ)
    if decision.errorCode is not None:
        diagnostics = _diagnostics(decision, compatibility, error=decision.errorCode)
        raise NativeExecutionError(decision.errorCode, diagnostics)
    if decision.plannedBackends == [NativeBackend.JVM, NativeBackend.NATIVE]:
        raise ValueError("compare execution requires the Day 7 result comparator")

    snapshot = deepcopy(request.model_dump(mode="python"))
    if decision.plannedBackends == [NativeBackend.JVM]:
        value = jvm_executor(_fresh(snapshot))
        diagnostics = _diagnostics(
            decision, compatibility, attempted=[NativeBackend.JVM], effective=NativeBackend.JVM
        )
        return NativeExecutionOutcome(value, decision, diagnostics, (NativeBackend.JVM,))

    if decision.plannedBackends != [NativeBackend.NATIVE]:
        raise RuntimeError("native selector produced an invalid execution plan")

    try:
        value = native_executor(_fresh(snapshot))
    except Exception as exc:
        code = _failure_code(exc)
        if config.mode is not NativeExecutionMode.AUTO or code not in _RUNTIME_FALLBACK_CODES:
            diagnostics = _diagnostics(
                decision,
                compatibility,
                attempted=[NativeBackend.NATIVE],
                effective=None,
                error=code,
            )
            raise NativeExecutionError(code, diagnostics) from exc

        value = jvm_executor(_fresh(snapshot))
        final_decision = decision.model_copy(
            update={"effectiveBackend": NativeBackend.JVM, "fallbackReason": code}
        )
        diagnostics = _diagnostics(
            final_decision,
            compatibility,
            attempted=[NativeBackend.NATIVE, NativeBackend.JVM],
            effective=NativeBackend.JVM,
            fallback=code,
            fallback_count=1,
        )
        return NativeExecutionOutcome(
            value,
            final_decision,
            diagnostics,
            (NativeBackend.NATIVE, NativeBackend.JVM),
            1,
        )

    diagnostics = _diagnostics(
        decision, compatibility, attempted=[NativeBackend.NATIVE], effective=NativeBackend.NATIVE
    )
    return NativeExecutionOutcome(value, decision, diagnostics, (NativeBackend.NATIVE,))
