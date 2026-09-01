import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fakebric.native_execution import (
    NativeErrorCode,
    NativeExecutionConfig,
    NativeExecutionDiagnostics,
    NativeExecutionMode,
    load_runtime_matrix,
    native_effective_enabled,
    native_global_enabled,
    validate_runtime_matrix,
)

ROOT = Path(__file__).resolve().parents[1]


def test_default_mode_is_jvm_and_disabled():
    config = NativeExecutionConfig()
    assert config.mode is NativeExecutionMode.JVM
    assert config.enabled is False
    assert config.fallback == "jvm"


def test_all_required_modes_exist():
    assert {mode.value for mode in NativeExecutionMode} == {"jvm", "native", "auto", "compare"}


def test_all_required_error_codes_exist():
    assert {code.value for code in NativeErrorCode} == {
        "NATIVE_DISABLED",
        "NATIVE_PLAN_UNSUPPORTED",
        "NATIVE_INIT_FAILED",
        "NATIVE_EXECUTION_FAILED",
        "NATIVE_RESULT_MISMATCH",
        "NATIVE_TIMEOUT",
        "NATIVE_OOM",
        "NATIVE_SECURITY_POLICY",
    }


def test_unknown_config_fields_are_rejected():
    with pytest.raises(ValidationError):
        NativeExecutionConfig(sparkMaster="local[*]")


def test_privileged_spark_master_is_rejected():
    with pytest.raises(ValidationError):
        NativeExecutionConfig(sparkConf={"spark.master": "local[*]"})


def test_credentials_and_network_configuration_are_rejected():
    with pytest.raises(ValidationError):
        NativeExecutionConfig(sparkConf={"spark.hadoop.fs.s3a.access.key": "secret"})
    with pytest.raises(ValidationError):
        NativeExecutionConfig(sparkConf={"spark.hadoop.fs.s3a.endpoint": "https://example.invalid"})


def test_identity_and_resource_configuration_are_rejected():
    with pytest.raises(ValidationError):
        NativeExecutionConfig(
            sparkConf={"spark.kubernetes.authenticate.driver.serviceAccountName": "admin"}
        )
    with pytest.raises(ValidationError):
        NativeExecutionConfig(sparkConf={"spark.executor.memory": "8g"})


def test_safe_session_spark_configuration_is_accepted():
    config = NativeExecutionConfig(
        sparkConf={"spark.sql.adaptive.enabled": False, "spark.sql.shuffle.partitions": 8}
    )
    assert config.sparkConf["spark.sql.shuffle.partitions"] == 8


def test_global_flag_defaults_to_false():
    assert native_global_enabled({}) is False


def test_native_requires_both_global_and_session_opt_in():
    enabled = NativeExecutionConfig(enabled=True, mode="auto")
    disabled = NativeExecutionConfig(enabled=False, mode="auto")
    assert native_effective_enabled(enabled, {"FAKEBRIC_NATIVE_EXECUTION_ENABLED": "true"})
    assert not native_effective_enabled(enabled, {"FAKEBRIC_NATIVE_EXECUTION_ENABLED": "false"})
    assert not native_effective_enabled(disabled, {"FAKEBRIC_NATIVE_EXECUTION_ENABLED": "true"})


def test_runtime_matrix_is_complete_and_checksum_is_valid():
    matrix = load_runtime_matrix(ROOT / "native-runtime-matrix.json")
    profile = matrix["profiles"][0]
    assert profile["versions"]["spark"] == "3.5.5"
    assert profile["versions"]["scala"] == "2.12.18"
    assert profile["versions"]["java"] == "17"
    assert profile["versions"]["gluten"] == "1.6.0"
    assert len(profile["versions"]["velox"]) == 40
    assert profile["artifact"]["checksum"]["algorithm"] == "sha512"
    assert len(profile["artifact"]["checksum"]["value"]) == 128


def test_incomplete_runtime_matrix_is_rejected():
    matrix = json.loads((ROOT / "native-runtime-matrix.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(matrix)
    del broken["profiles"][0]["versions"]["gluten"]
    with pytest.raises(ValueError, match="missing required versions"):
        validate_runtime_matrix(broken)


def test_invalid_checksum_is_rejected():
    matrix = json.loads((ROOT / "native-runtime-matrix.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(matrix)
    broken["profiles"][0]["artifact"]["checksum"]["value"] = "not-a-checksum"
    with pytest.raises(ValueError, match="invalid sha512 checksum"):
        validate_runtime_matrix(broken)


def test_diagnostics_tracks_requested_and_effective_backend():
    diagnostics = NativeExecutionDiagnostics(
        requestedBackend="auto",
        effectiveBackend="jvm",
        fallbackReason="NATIVE_PLAN_UNSUPPORTED",
    )
    payload = diagnostics.model_dump(mode="json")
    assert payload["requestedBackend"] == "auto"
    assert payload["effectiveBackend"] == "jvm"
    assert payload["fallbackReason"] == "NATIVE_PLAN_UNSUPPORTED"
