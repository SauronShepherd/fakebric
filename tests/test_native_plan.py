import copy

import pytest

from fakebric.native_execution import NativeErrorCode
from fakebric.native_plan import (
    NativePlanStatus,
    analyze_native_plan,
    load_native_plan_catalog,
    validate_native_plan_catalog,
)

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


def test_catalog_is_versioned_and_unknown_operators_fall_back():
    catalog = load_native_plan_catalog()
    assert catalog["schemaVersion"] == 1
    assert catalog["catalogVersion"] == "2026-09-01.level-a.v1"
    assert catalog["unknownOperatorPolicy"] == "fallback"
    assert catalog["requiredScanFormat"] == "parquet"


def test_level_a_parquet_plan_is_supported():
    result = analyze_native_plan(
        LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL,
        spark_conf={"spark.sql.shuffle.partitions": 8},
        functions=["sum", "cast", "isnull"],
        data_types=["long", "double", "string"],
    )
    assert result.status is NativePlanStatus.SUPPORTED
    assert result.nativeEligible is True
    assert result.errorCode is None
    assert result.logicalOperators == ["Project", "Filter", "Relation"]
    assert "HashAggregate" in result.physicalOperators
    assert "FileScan" in result.physicalOperators
    assert "supported by catalog" in result.explanation


def test_gluten_transformed_plan_markers_are_supported():
    logical = """Project [(id#0L * 3) AS triple#2L]
+- Filter ((id#0L % 2) = 0)
   +- Range (0, 100, step=1, splits=Some(1))
"""
    physical = """VeloxColumnarToRowExec
+- WholeStageTransformer
   +- ProjectExecTransformer [(id#0L * 3) AS triple#2L]
      +- FilterExecTransformer ((id#0L % 2) = 0)
         +- InputIteratorTransformer
            +- Range (0, 100, step=1, splits=1)
"""
    result = analyze_native_plan(logical, physical, data_types=["long"])
    assert result.status is NativePlanStatus.SUPPORTED
    assert "WholeStageTransformer" in result.physicalOperators
    assert "VeloxColumnarToRowExec" in result.physicalOperators


def test_unknown_operator_forces_jvm_fallback():
    result = analyze_native_plan(
        LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL + "\n+- FancyUnreviewedExec [id#0L]",
    )
    assert result.status is NativePlanStatus.FALLBACK
    assert result.nativeEligible is False
    assert result.errorCode is NativeErrorCode.NATIVE_PLAN_UNSUPPORTED
    assert any(
        reason.code == "UNKNOWN_OPERATOR" and reason.item == "FancyUnreviewedExec"
        for reason in result.reasons
    )


@pytest.mark.parametrize("marker", ["PythonUDF", "ScalaUDF", "JavaUDF", "PandasUDF"])
def test_udfs_always_force_jvm_fallback(marker):
    result = analyze_native_plan(
        LEVEL_A_LOGICAL + f"\n+- Project [{marker}(id#0L)]",
        LEVEL_A_PHYSICAL,
    )
    assert result.status is NativePlanStatus.FALLBACK
    assert result.errorCode is NativeErrorCode.NATIVE_PLAN_UNSUPPORTED
    assert any(reason.category == "udf" for reason in result.reasons)


@pytest.mark.parametrize(
    "marker",
    ["ExistingRDD", "MapPartitions", "input_file_name(", "jdbc:"],
)
def test_external_and_filesystem_network_markers_force_jvm_fallback(marker):
    result = analyze_native_plan(
        LEVEL_A_LOGICAL + f"\n+- Project [{marker}]",
        LEVEL_A_PHYSICAL,
    )
    assert result.status is NativePlanStatus.FALLBACK
    assert result.errorCode is NativeErrorCode.NATIVE_PLAN_UNSUPPORTED


def test_non_parquet_scan_forces_jvm_fallback():
    result = analyze_native_plan(
        LEVEL_A_LOGICAL.replace("parquet", "csv"),
        LEVEL_A_PHYSICAL.replace("parquet", "csv"),
    )
    assert result.status is NativePlanStatus.FALLBACK
    assert any(reason.code == "UNSUPPORTED_SCAN_FORMAT" for reason in result.reasons)


def test_unsupported_function_and_type_inventory_force_fallback():
    result = analyze_native_plan(
        LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL,
        functions=["sum", "collect_list", "mystery_fn"],
        data_types=["long", "array", "geography"],
    )
    assert result.status is NativePlanStatus.FALLBACK
    assert result.functionsChecked == ["sum", "collect_list", "mystery_fn"]
    assert result.dataTypesChecked == ["long", "array", "geography"]
    assert any(reason.item == "collect_list" for reason in result.reasons)
    assert any(reason.item == "mystery_fn" for reason in result.reasons)
    assert any(reason.item == "array" for reason in result.reasons)
    assert any(reason.item == "geography" for reason in result.reasons)


def test_forbidden_spark_config_is_blocked_and_value_is_redacted():
    secret = "dont-leak-this-value"
    result = analyze_native_plan(
        LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL,
        spark_conf={"spark.hadoop.fs.s3a.access.key": secret},
    )
    assert result.status is NativePlanStatus.BLOCKED
    assert result.nativeEligible is False
    assert result.errorCode is NativeErrorCode.NATIVE_SECURITY_POLICY
    assert "spark.hadoop.fs.s3a.access.key" in result.explanation
    assert secret not in result.explanation
    assert secret not in result.model_dump_json()


def test_write_command_is_blocked():
    result = analyze_native_plan(
        "InsertIntoHadoopFsRelationCommand /tmp/out\n+- " + LEVEL_A_LOGICAL,
        LEVEL_A_PHYSICAL,
    )
    assert result.status is NativePlanStatus.BLOCKED
    assert result.errorCode is NativeErrorCode.NATIVE_SECURITY_POLICY
    assert any(reason.code == "BLOCKED_OPERATOR" for reason in result.reasons)


def test_missing_plan_requires_fallback_instead_of_assuming_support():
    result = analyze_native_plan("", "")
    assert result.status is NativePlanStatus.FALLBACK
    assert result.errorCode is NativeErrorCode.NATIVE_PLAN_UNSUPPORTED
    assert {reason.code for reason in result.reasons} == {
        "MISSING_LOGICAL_PLAN",
        "MISSING_PHYSICAL_PLAN",
    }


def test_catalog_rejects_non_conservative_unknown_operator_policy():
    catalog = copy.deepcopy(load_native_plan_catalog())
    catalog["unknownOperatorPolicy"] = "supported"
    with pytest.raises(ValueError, match="must fall back to JVM"):
        validate_native_plan_catalog(catalog)
