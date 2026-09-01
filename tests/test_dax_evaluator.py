from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from fakebric.dax import (
    BLANK,
    DaxEngine,
    DaxEvaluationError,
    FilterContext,
    TableReference,
    parse_dax,
)


SALES = [
    {"Amount": Decimal("10.50"), "Category": "A", "Flag": True, "When": date(2026, 9, 1)},
    {"Amount": Decimal("20"), "Category": "B", "Flag": False, "When": date(2026, 9, 2)},
    {"Amount": None, "Category": None, "Flag": None, "When": None},
]


def engine(rows=SALES):
    return DaxEngine(
        {"Sales": rows, "Empty": []},
        {"Sales": {"Total": "SUM(Sales[Amount])", "SafeHalf": "DIVIDE(SUM(Sales[Amount]), 2)"}},
    )


def test_sum_average_min_max_and_stable_decimal_results():
    dax = engine()
    assert dax.evaluate("SUM(Sales[Amount])") == Decimal("30.50")
    assert dax.evaluate("AVERAGE(Sales[Amount])") == Decimal("15.25")
    assert dax.evaluate("MIN(Sales[Amount])") == Decimal("10.50")
    assert dax.evaluate("MAX(Sales[Amount])") == Decimal("20")
    assert dax.evaluate("0.1 + 0.2") == Decimal("0.3")


def test_empty_aggregations_return_blank():
    dax = engine()
    assert dax.evaluate("SUM(Empty[Amount])") is BLANK
    assert dax.evaluate("COUNT(Empty[Amount])") is BLANK
    assert dax.evaluate("COUNTA(Empty[Amount])") is BLANK
    assert dax.evaluate("COUNTROWS(Empty)") is BLANK
    assert dax.evaluate("DISTINCTCOUNT(Empty[Amount])") is BLANK
    assert dax.evaluate("AVERAGE(Empty[Amount])") is BLANK
    assert dax.evaluate("MIN(Empty[Amount])") is BLANK
    assert dax.evaluate("MAX(Empty[Amount])") is BLANK


def test_count_counta_and_distinctcount_blank_semantics():
    dax = engine()
    assert dax.evaluate("COUNT(Sales[Category])") == 2
    assert dax.evaluate("COUNTA(Sales[Flag])") == 2
    assert dax.evaluate("DISTINCTCOUNT(Sales[Category])") == 3
    with pytest.raises(DaxEvaluationError, match="COUNT does not support TRUE/FALSE") as exc:
        dax.evaluate("COUNT(Sales[Flag])")
    assert exc.value.code == "DAX_EVAL_TYPE"


def test_countrows_accepts_controlled_table_reference():
    ast = parse_dax("COUNTROWS('Sales')")
    assert isinstance(ast.arguments[0], TableReference)
    assert ast.arguments[0].table == "Sales"
    assert engine().evaluate(ast) == 3


def test_filter_context_applies_to_aggregations_and_preserves_row_order():
    dax = engine()
    filtered = FilterContext.for_table("Sales", [2, 0])
    assert dax.evaluate("SUM(Sales[Amount])", filter_context=filtered) == Decimal("10.50")
    assert dax.evaluate("COUNTROWS(Sales)", filter_context=filtered) == 2
    assert dax.evaluate_rows("COALESCE(Sales[Amount], 0)", "Sales", filter_context=filtered) == (
        Decimal("10.50"),
        0,
    )


def test_row_context_evaluates_column_expressions_per_row():
    dax = engine()
    assert dax.evaluate_rows("Sales[Amount] * 2", "Sales") == (
        Decimal("21.00"),
        Decimal("40"),
        Decimal("0"),
    )


def test_column_reference_without_aggregation_is_not_scalar():
    with pytest.raises(DaxEvaluationError) as exc:
        engine().evaluate("Sales[Amount]")
    assert exc.value.code == "DAX_EVAL_COLUMN_SCALAR"


def test_invalid_table_and_column_references_are_structured_errors():
    with pytest.raises(DaxEvaluationError) as exc:
        engine().evaluate("SUM(Missing[Amount])")
    assert exc.value.code == "DAX_EVAL_TABLE_NOT_FOUND"
    with pytest.raises(DaxEvaluationError) as exc:
        engine().evaluate("SUM(Sales[Missing])")
    assert exc.value.code == "DAX_EVAL_COLUMN_NOT_FOUND"


def test_incompatible_types_are_rejected():
    with pytest.raises(DaxEvaluationError) as exc:
        engine().evaluate("SUM(Sales[Category])")
    assert exc.value.code == "DAX_EVAL_TYPE"
    with pytest.raises(DaxEvaluationError) as exc:
        engine().evaluate("MIN(Sales[Category])")
    assert exc.value.code == "DAX_EVAL_TYPE"


def test_divide_safe_semantics_and_raw_division_guard():
    dax = engine()
    assert dax.evaluate("DIVIDE(5, 2)") == Decimal("2.5")
    assert dax.evaluate("DIVIDE(5, 0)") is BLANK
    assert dax.evaluate("DIVIDE(5, BLANK(), 7)") == 7
    with pytest.raises(DaxEvaluationError) as exc:
        dax.evaluate("5 / 0")
    assert exc.value.code == "DAX_EVAL_DIVIDE_BY_ZERO"
    with pytest.raises(DaxEvaluationError) as exc:
        dax.evaluate("DIVIDE(5, 0, 1 + 1)")
    assert exc.value.code == "DAX_EVAL_ALT_NOT_CONSTANT"


def test_if_switch_and_coalesce_are_lazy_and_blank_aware():
    dax = engine()
    assert dax.evaluate("IF(TRUE(), 1, 1 / 0)") == 1
    assert dax.evaluate("IF(FALSE(), 1)") is BLANK
    assert dax.evaluate('SWITCH(2, 1, "one", 2, "two", "other")') == "two"
    assert dax.evaluate("SWITCH(9, 1, 10, 2, 20)") is BLANK
    assert dax.evaluate("COALESCE(BLANK(), BLANK(), 3)") == 3


def test_blank_arithmetic_boolean_and_comparison_semantics():
    dax = engine()
    assert dax.evaluate("BLANK() + 20") == Decimal("20")
    assert dax.evaluate("BLANK() = 0") is True
    assert dax.evaluate("!BLANK()") is True
    assert dax.evaluate("FALSE() && (1 / 0 = 0)") is False
    assert dax.evaluate("TRUE() || (1 / 0 = 0)") is True


def test_min_max_two_scalar_arguments():
    dax = engine()
    assert dax.evaluate("MIN(BLANK(), 5)") == Decimal("0")
    assert dax.evaluate("MAX(2.5, 3)") == Decimal("3")


def test_date_literals_compare_deterministically():
    dax = engine()
    assert dax.evaluate('dt"2026-09-01" < dt"2026-09-02"') is True


def test_level_2_functions_parse_but_do_not_execute_yet():
    with pytest.raises(DaxEvaluationError) as exc:
        engine().evaluate("CALCULATE(SUM(Sales[Amount]))")
    assert exc.value.code == "DAX_EVAL_UNSUPPORTED_LEVEL"


def test_measure_evaluation_uses_the_same_filter_context():
    dax = engine()
    assert dax.evaluate_measure("Sales", "Total") == Decimal("30.50")
    assert dax.evaluate_measure("Sales", "SafeHalf") == Decimal("15.25")
    assert dax.evaluate_measure(
        "Sales", "Total", filter_context=FilterContext.for_table("Sales", [1])
    ) == Decimal("20")
    with pytest.raises(DaxEvaluationError) as exc:
        dax.evaluate_measure("Sales", "Missing")
    assert exc.value.code == "DAX_EVAL_MEASURE_NOT_FOUND"


def test_golden_level1_results():
    dax = engine()
    golden = json.loads((Path(__file__).parent / "golden" / "dax_level1.json").read_text())
    for expression, expected in golden.items():
        value = dax.evaluate(expression)
        if isinstance(value, Decimal):
            value = format(value, "f")
        assert value == expected
