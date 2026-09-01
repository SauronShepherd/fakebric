import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fakebric.native_execution import (
    NativeBackend,
    NativeErrorCode,
    NativeExecutionConfig,
)
from fakebric.native_plan import analyze_native_plan
from fakebric.native_selector import (
    NATIVE_SELECTOR_VERSION,
    NativeBackendFailure,
    NativeExecutionError,
    QueryExecutionRequest,
    execute_with_fallback_once,
    select_native_execution,
)

ROOT = Path(__file__).resolve().parents[1]

LEVEL_A_LOGICAL = """Project [id#0L, (id#0L * 3) AS triple#2L]
+- Filter ((id#0L % 2) = 0)
   +- Relation [id#0L] parquet
"""

LEVEL_A_PHYSICAL = """*(2) HashAggregate(keys=[], functions=[sum(triple#2L)])
+- Exchange SinglePartition, ENSURE_REQUIREMENTS
   +- *(1) HashAggregate(keys=[], functions=[partial_sum(triple#2L)])
      +- *(1) Project [id#0L, (id#0L * 3) AS triple#2L]
         +- *(1) Filter ((id#0L % 2) = 0)
            +- *(1) FileScan parquet [id#0L]
"""


def supported_plan():
    return analyze_native_plan(
        LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL,
        functions=["sum", "cast", "isnull"],
        data_types=["long", "double", "string"],
    )


def unsupported_plan():
    return analyze_native_plan(
        LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL + "\n+- FancyUnreviewedExec [id#0L]",
    )


def blocked_plan():
    return analyze_native_plan(
        LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL,
        spark_conf={"spark.hadoop.fs.s3a.access.key": "must-not-leak"},
    )


def query_request():
    return QueryExecutionRequest(
        statement="SELECT * FROM events WHERE tenant_id = :tenant",
        parameters={"tenant": "tenant-a", "secret": "must-not-leak"},
        filters=["tenant_id = :tenant", "is_active = true"],
        orderBy=["event_time DESC NULLS LAST"],
        limit=50,
    )


def native_config(mode="auto"):
    return NativeExecutionConfig(mode=mode, enabled=True)


def enabled_env():
    return {"FAKEBRIC_NATIVE_EXECUTION_ENABLED": "true"}


def test_selector_version_and_runtime_lock_are_pinned():
    lock = json.loads((ROOT / "runtime-1.3.lock.json").read_text(encoding="utf-8"))
    assert NATIVE_SELECTOR_VERSION == "2026-09-01.selector.v1"
    assert lock["native"]["status"] == "selector-fallback-validated"
    assert lock["native"]["executionSelector"] == "fakebric/native_selector.py"
    assert lock["native"]["selectorVersion"] == NATIVE_SELECTOR_VERSION
    assert lock["native"]["queryContractVersion"] == "1"
    assert lock["native"]["maxJvmFallbackAttempts"] == 1
    assert lock["native"]["enabledByDefault"] is False
    assert lock["native"]["defaultMode"] == "jvm"


def test_query_contract_rejects_unknown_version():
    with pytest.raises(ValidationError):
        QueryExecutionRequest(contractVersion="2", statement="SELECT 1")


def test_default_jvm_mode_stays_on_jvm():
    decision = select_native_execution(NativeExecutionConfig(), supported_plan(), {})
    assert decision.requestedBackends == [NativeBackend.JVM]
    assert decision.plannedBackends == [NativeBackend.JVM]
    assert decision.effectiveBackend is NativeBackend.JVM
    assert decision.fallbackReason is None


def test_strict_native_requires_both_opt_in_flags():
    decision = select_native_execution(
        native_config("native"), supported_plan(), {"FAKEBRIC_NATIVE_EXECUTION_ENABLED": "false"}
    )
    assert decision.plannedBackends == []
    assert decision.effectiveBackend is None
    assert decision.errorCode is NativeErrorCode.NATIVE_DISABLED


def test_strict_native_rejects_unsupported_plan_without_jvm_fallback():
    decision = select_native_execution(
        native_config("native"), unsupported_plan(), enabled_env()
    )
    assert decision.plannedBackends == []
    assert decision.errorCode is NativeErrorCode.NATIVE_PLAN_UNSUPPORTED
    assert decision.fallbackAllowed is False


def test_auto_uses_jvm_when_native_is_disabled_without_trying_native():
    native_calls = 0

    def native_executor(_request):
        nonlocal native_calls
        native_calls += 1
        return "native"

    outcome = execute_with_fallback_once(
        query_request(),
        native_config("auto"),
        supported_plan(),
        jvm_executor=lambda _request: "jvm",
        native_executor=native_executor,
        environ={"FAKEBRIC_NATIVE_EXECUTION_ENABLED": "false"},
    )
    assert outcome.value == "jvm"
    assert native_calls == 0
    assert outcome.decision.effectiveBackend is NativeBackend.JVM
    assert outcome.diagnostics.fallbackReason == "NATIVE_DISABLED"
    assert outcome.attemptedBackends == (NativeBackend.JVM,)
    assert outcome.fallbackCount == 0


def test_auto_uses_jvm_for_unsupported_plan_without_native_attempt():
    calls = []
    outcome = execute_with_fallback_once(
        query_request(),
        native_config("auto"),
        unsupported_plan(),
        jvm_executor=lambda _request: calls.append("jvm") or "jvm",
        native_executor=lambda _request: calls.append("native") or "native",
        environ=enabled_env(),
    )
    assert calls == ["jvm"]
    assert outcome.value == "jvm"
    assert outcome.diagnostics.fallbackReason == "NATIVE_PLAN_UNSUPPORTED"
    assert outcome.diagnostics.effectiveBackend is NativeBackend.JVM


def test_security_block_is_never_bypassed_by_jvm_fallback():
    calls = []
    with pytest.raises(NativeExecutionError) as caught:
        execute_with_fallback_once(
            query_request(),
            native_config("auto"),
            blocked_plan(),
            jvm_executor=lambda _request: calls.append("jvm"),
            native_executor=lambda _request: calls.append("native"),
            environ=enabled_env(),
        )
    assert calls == []
    assert caught.value.code is NativeErrorCode.NATIVE_SECURITY_POLICY
    assert caught.value.diagnostics.effectiveBackend is None


def test_supported_auto_plan_executes_native_once():
    calls = []
    outcome = execute_with_fallback_once(
        query_request(),
        native_config("auto"),
        supported_plan(),
        jvm_executor=lambda _request: calls.append("jvm") or "jvm",
        native_executor=lambda _request: calls.append("native") or "native",
        environ=enabled_env(),
    )
    assert calls == ["native"]
    assert outcome.value == "native"
    assert outcome.decision.effectiveBackend is NativeBackend.NATIVE
    assert outcome.diagnostics.effectiveBackend is NativeBackend.NATIVE
    assert outcome.diagnostics.fallbackReason is None
    assert outcome.attemptedBackends == (NativeBackend.NATIVE,)
    assert outcome.fallbackCount == 0


def test_auto_runtime_failure_falls_back_exactly_once_and_reports_final_jvm():
    calls = []

    def native_executor(_request):
        calls.append("native")
        raise RuntimeError("native detail must not be exposed")

    def jvm_executor(_request):
        calls.append("jvm")
        return "jvm-result"

    outcome = execute_with_fallback_once(
        query_request(),
        native_config("auto"),
        supported_plan(),
        jvm_executor=jvm_executor,
        native_executor=native_executor,
        environ=enabled_env(),
    )
    assert calls == ["native", "jvm"]
    assert outcome.value == "jvm-result"
    assert outcome.decision.effectiveBackend is NativeBackend.JVM
    assert outcome.decision.fallbackReason is NativeErrorCode.NATIVE_EXECUTION_FAILED
    assert outcome.diagnostics.effectiveBackend is NativeBackend.JVM
    assert outcome.diagnostics.fallbackReason == "NATIVE_EXECUTION_FAILED"
    assert outcome.attemptedBackends == (NativeBackend.NATIVE, NativeBackend.JVM)
    assert outcome.fallbackCount == 1
    assert "native detail must not be exposed" not in outcome.diagnostics.model_dump_json()


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (NativeBackendFailure(NativeErrorCode.NATIVE_INIT_FAILED), "NATIVE_INIT_FAILED"),
        (TimeoutError("late"), "NATIVE_TIMEOUT"),
        (MemoryError("oom detail"), "NATIVE_OOM"),
    ],
)
def test_auto_maps_runtime_failures_to_exact_fallback_reason(failure, expected):
    def native_executor(_request):
        raise failure

    outcome = execute_with_fallback_once(
        query_request(),
        native_config("auto"),
        supported_plan(),
        jvm_executor=lambda _request: "jvm",
        native_executor=native_executor,
        environ=enabled_env(),
    )
    assert outcome.diagnostics.fallbackReason == expected
    assert outcome.fallbackCount == 1


def test_fallback_replays_original_filters_parameters_order_and_limit():
    original = query_request()
    original_payload = original.model_dump(mode="python")
    observed = {}

    def native_executor(request):
        request.statement = "SELECT mutated"
        request.parameters["tenant"] = "tampered"
        request.parameters["new"] = "tampered"
        request.filters.append("tampered = true")
        request.orderBy[0] = "event_time ASC"
        request.limit = 999
        raise NativeBackendFailure(NativeErrorCode.NATIVE_INIT_FAILED)

    def jvm_executor(request):
        observed.update(request.model_dump(mode="python"))
        return "jvm"

    outcome = execute_with_fallback_once(
        original,
        native_config("auto"),
        supported_plan(),
        jvm_executor=jvm_executor,
        native_executor=native_executor,
        environ=enabled_env(),
    )
    assert observed == original_payload
    assert original.model_dump(mode="python") == original_payload
    assert outcome.diagnostics.fallbackReason == "NATIVE_INIT_FAILED"
    diagnostics_json = outcome.diagnostics.model_dump_json()
    assert "must-not-leak" not in diagnostics_json
    assert "tenant-a" not in diagnostics_json
    assert original.statement not in diagnostics_json


def test_strict_native_runtime_failure_does_not_fallback_or_claim_native_success():
    calls = []

    def native_executor(_request):
        calls.append("native")
        raise TimeoutError("detail")

    with pytest.raises(NativeExecutionError) as caught:
        execute_with_fallback_once(
            query_request(),
            native_config("native"),
            supported_plan(),
            jvm_executor=lambda _request: calls.append("jvm"),
            native_executor=native_executor,
            environ=enabled_env(),
        )
    assert calls == ["native"]
    assert caught.value.code is NativeErrorCode.NATIVE_TIMEOUT
    assert caught.value.diagnostics.effectiveBackend is None
    assert caught.value.diagnostics.errorCode is NativeErrorCode.NATIVE_TIMEOUT
    assert caught.value.diagnostics.compatibility["attemptedBackends"] == ["native"]


def test_jvm_failure_after_native_failure_is_not_retried():
    calls = []

    def native_executor(_request):
        calls.append("native")
        raise RuntimeError("native failed")

    def jvm_executor(_request):
        calls.append("jvm")
        raise RuntimeError("jvm failed")

    with pytest.raises(RuntimeError, match="jvm failed"):
        execute_with_fallback_once(
            query_request(),
            native_config("auto"),
            supported_plan(),
            jvm_executor=jvm_executor,
            native_executor=native_executor,
            environ=enabled_env(),
        )
    assert calls == ["native", "jvm"]


def test_compare_mode_plans_both_backends_but_keeps_jvm_authoritative():
    decision = select_native_execution(
        native_config("compare"), supported_plan(), enabled_env()
    )
    assert decision.requestedBackends == [NativeBackend.JVM, NativeBackend.NATIVE]
    assert decision.plannedBackends == [NativeBackend.JVM, NativeBackend.NATIVE]
    assert decision.effectiveBackend is NativeBackend.JVM
    assert decision.comparisonRequested is True


def test_compare_execution_waits_for_day_7_result_comparator():
    with pytest.raises(ValueError, match="result comparator"):
        execute_with_fallback_once(
            query_request(),
            native_config("compare"),
            supported_plan(),
            jvm_executor=lambda _request: "jvm",
            native_executor=lambda _request: "native",
            environ=enabled_env(),
        )
