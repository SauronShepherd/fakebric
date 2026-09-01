from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from .ast import BinaryOp, Expression, FunctionCall, Literal, Reference, TableReference, UnaryOp
from .errors import DaxEvaluationError
from .functions import get_function
from .parser import parse_dax

BLANK = None


@dataclass(frozen=True, slots=True)
class FilterContext:
    """Visible row indices per table. Missing tables mean all rows are visible."""

    row_indices: Mapping[str, frozenset[int]] = field(default_factory=dict)

    @classmethod
    def for_table(cls, table: str, indices: Sequence[int]) -> "FilterContext":
        return cls({table.casefold(): frozenset(indices)})

    def indices_for(self, table: str, row_count: int) -> tuple[int, ...]:
        selected = self.row_indices.get(table.casefold())
        if selected is None:
            return tuple(range(row_count))
        return tuple(index for index in range(row_count) if index in selected)


@dataclass(frozen=True, slots=True)
class RowContext:
    rows: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    @classmethod
    def for_row(cls, table: str, row: Mapping[str, Any]) -> "RowContext":
        return cls({table.casefold(): row})


@dataclass(frozen=True, slots=True)
class ColumnVector:
    table: str
    column: str
    values: tuple[Any, ...]
    row_count: int


@dataclass(frozen=True, slots=True)
class TableVector:
    table: str
    rows: tuple[Mapping[str, Any], ...]


class DaxEngine:
    def __init__(
        self,
        tables: Mapping[str, Sequence[Mapping[str, Any]]],
        measures: Mapping[str, Mapping[str, str]] | None = None,
    ) -> None:
        self._tables: dict[str, tuple[str, tuple[Mapping[str, Any], ...]]] = {
            name.casefold(): (name, tuple(rows)) for name, rows in tables.items()
        }
        self._measures: dict[str, tuple[str, dict[str, tuple[str, str]]]] = {}
        for table_name, table_measures in (measures or {}).items():
            self._measures[table_name.casefold()] = (
                table_name,
                {name.casefold(): (name, expression) for name, expression in table_measures.items()},
            )
        self._measure_stack: list[tuple[str, str]] = []

    @classmethod
    def from_semantic_model(
        cls,
        model: Any,
        tables: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> "DaxEngine":
        measures = {
            table.name: {measure.name: measure.expression for measure in table.measures}
            for table in model.tables
        }
        return cls(tables, measures)

    def evaluate(
        self,
        expression: str | Expression,
        *,
        filter_context: FilterContext | None = None,
        row_context: RowContext | None = None,
    ) -> Any:
        ast = parse_dax(expression) if isinstance(expression, str) else expression
        return self._scalar(
            self._eval(ast, filter_context or FilterContext(), row_context or RowContext())
        )

    def evaluate_rows(
        self,
        expression: str | Expression,
        table: str,
        *,
        filter_context: FilterContext | None = None,
    ) -> tuple[Any, ...]:
        ast = parse_dax(expression) if isinstance(expression, str) else expression
        context = filter_context or FilterContext()
        table_name, rows = self._table(table)
        results: list[Any] = []
        for index in context.indices_for(table_name, len(rows)):
            results.append(self._scalar(self._eval(ast, context, RowContext.for_row(table_name, rows[index]))))
        return tuple(results)

    def evaluate_measure(
        self,
        table: str,
        measure: str,
        *,
        filter_context: FilterContext | None = None,
    ) -> Any:
        table_key = table.casefold()
        measure_key = measure.casefold()
        if table_key not in self._measures or measure_key not in self._measures[table_key][1]:
            raise DaxEvaluationError("DAX_EVAL_MEASURE_NOT_FOUND", f"Measure {table}.{measure} does not exist")
        _, definitions = self._measures[table_key]
        _, expression = definitions[measure_key]
        stack_key = (table_key, measure_key)
        if stack_key in self._measure_stack:
            chain = " -> ".join(f"{t}.{m}" for t, m in self._measure_stack + [stack_key])
            raise DaxEvaluationError("DAX_EVAL_MEASURE_CYCLE", f"Measure evaluation cycle: {chain}")
        self._measure_stack.append(stack_key)
        try:
            return self.evaluate(expression, filter_context=filter_context)
        finally:
            self._measure_stack.pop()

    def _table(self, table: str) -> tuple[str, tuple[Mapping[str, Any], ...]]:
        try:
            return self._tables[table.casefold()]
        except KeyError as exc:
            raise DaxEvaluationError("DAX_EVAL_TABLE_NOT_FOUND", f"Table {table!r} does not exist") from exc

    @staticmethod
    def _row_value(row: Mapping[str, Any], column: str, table: str) -> Any:
        matches = [key for key in row if key.casefold() == column.casefold()]
        if not matches:
            raise DaxEvaluationError("DAX_EVAL_COLUMN_NOT_FOUND", f"Column {table}[{column}] does not exist")
        return row[matches[0]]

    def _eval(self, node: Expression, filters: FilterContext, rows: RowContext) -> Any:
        if isinstance(node, Literal):
            if node.literal_type == "date":
                return date.fromisoformat(str(node.value))
            if node.literal_type == "datetime":
                return datetime.fromisoformat(str(node.value))
            return node.value
        if isinstance(node, Reference):
            canonical_table, table_rows = self._table(node.table)
            current_row = rows.rows.get(canonical_table.casefold())
            if current_row is not None:
                return self._row_value(current_row, node.name, canonical_table)
            indices = filters.indices_for(canonical_table, len(table_rows))
            values = tuple(self._row_value(table_rows[index], node.name, canonical_table) for index in indices)
            return ColumnVector(canonical_table, node.name, values, len(indices))
        if isinstance(node, TableReference):
            canonical_table, table_rows = self._table(node.table)
            indices = filters.indices_for(canonical_table, len(table_rows))
            return TableVector(canonical_table, tuple(table_rows[index] for index in indices))
        if isinstance(node, UnaryOp):
            value = self._scalar(self._eval(node.operand, filters, rows))
            if node.operator == "!":
                return not self._truthy(value)
            number = self._numeric(value, blank_as_zero=True)
            return number if node.operator == "+" else -number
        if isinstance(node, BinaryOp):
            return self._binary(node, filters, rows)
        if isinstance(node, FunctionCall):
            return self._function(node, filters, rows)
        raise DaxEvaluationError("DAX_EVAL_NODE", f"Unsupported AST node {type(node).__name__}")

    def _binary(self, node: BinaryOp, filters: FilterContext, rows: RowContext) -> Any:
        if node.operator == "&&":
            left = self._scalar(self._eval(node.left, filters, rows))
            return self._truthy(left) and self._truthy(self._scalar(self._eval(node.right, filters, rows)))
        if node.operator == "||":
            left = self._scalar(self._eval(node.left, filters, rows))
            return self._truthy(left) or self._truthy(self._scalar(self._eval(node.right, filters, rows)))
        left = self._scalar(self._eval(node.left, filters, rows))
        right = self._scalar(self._eval(node.right, filters, rows))
        if node.operator in {"+", "-", "*", "/", "^"}:
            a = self._numeric(left, blank_as_zero=True)
            b = self._numeric(right, blank_as_zero=True)
            if node.operator == "+": return a + b
            if node.operator == "-": return a - b
            if node.operator == "*": return a * b
            if node.operator == "/":
                if b == 0:
                    raise DaxEvaluationError("DAX_EVAL_DIVIDE_BY_ZERO", "Use DIVIDE() for safe division by zero")
                return a / b
            if b != b.to_integral_value():
                raise DaxEvaluationError("DAX_EVAL_TYPE", "Decimal exponents are not supported in the Level 1 evaluator")
            return a ** int(b)
        left, right = self._comparison_values(left, right)
        if node.operator == "=": return left == right
        if node.operator == "<>": return left != right
        try:
            if node.operator == "<": return left < right
            if node.operator == "<=": return left <= right
            if node.operator == ">": return left > right
            if node.operator == ">=": return left >= right
        except TypeError as exc:
            raise DaxEvaluationError("DAX_EVAL_TYPE", f"Cannot compare {type(left).__name__} and {type(right).__name__}") from exc
        raise DaxEvaluationError("DAX_EVAL_OPERATOR", f"Unsupported operator {node.operator}")

    def _function(self, node: FunctionCall, filters: FilterContext, rows: RowContext) -> Any:
        spec = get_function(node.name)
        if spec is None or spec.level != 1:
            raise DaxEvaluationError("DAX_EVAL_UNSUPPORTED_LEVEL", f"Function {node.name} is not executable at DAX Level 1")
        name = node.name
        if name in {"SUM", "COUNT", "COUNTA", "DISTINCTCOUNT", "AVERAGE"}:
            vector = self._column(node.arguments[0], filters, rows, name)
            if name == "SUM": return self._sum(vector)
            if name == "COUNT": return self._count(vector, allow_boolean=False)
            if name == "COUNTA": return self._count(vector, allow_boolean=True)
            if name == "DISTINCTCOUNT": return self._distinctcount(vector)
            return self._average(vector)
        if name == "COUNTROWS":
            table = self._eval(node.arguments[0], filters, rows)
            if not isinstance(table, TableVector):
                raise DaxEvaluationError("DAX_EVAL_TYPE", "COUNTROWS requires a table argument")
            return BLANK if not table.rows else len(table.rows)
        if name in {"MIN", "MAX"}:
            if len(node.arguments) == 1:
                vector = self._column(node.arguments[0], filters, rows, name)
                return self._minmax(vector, name == "MIN")
            left = self._scalar(self._eval(node.arguments[0], filters, rows))
            right = self._scalar(self._eval(node.arguments[1], filters, rows))
            a, b = self._comparison_values(left, right)
            try:
                return min(a, b) if name == "MIN" else max(a, b)
            except TypeError as exc:
                raise DaxEvaluationError("DAX_EVAL_TYPE", f"{name} arguments are not comparable") from exc
        if name == "DIVIDE":
            numerator = self._numeric(self._scalar(self._eval(node.arguments[0], filters, rows)), blank_as_zero=True)
            denominator_raw = self._scalar(self._eval(node.arguments[1], filters, rows))
            denominator = Decimal(0) if denominator_raw is BLANK else self._numeric(denominator_raw)
            if denominator == 0:
                if len(node.arguments) == 2:
                    return BLANK
                if not isinstance(node.arguments[2], Literal):
                    raise DaxEvaluationError("DAX_EVAL_ALT_NOT_CONSTANT", "DIVIDE alternate result must be a literal constant")
                return self._scalar(self._eval(node.arguments[2], filters, rows))
            return numerator / denominator
        if name == "IF":
            condition = self._truthy(self._scalar(self._eval(node.arguments[0], filters, rows)))
            if condition:
                return self._scalar(self._eval(node.arguments[1], filters, rows))
            if len(node.arguments) == 3:
                return self._scalar(self._eval(node.arguments[2], filters, rows))
            return BLANK
        if name == "SWITCH":
            expression = self._scalar(self._eval(node.arguments[0], filters, rows))
            rest = node.arguments[1:]
            has_else = len(rest) % 2 == 1
            pair_end = len(rest) - (1 if has_else else 0)
            for index in range(0, pair_end, 2):
                candidate = self._scalar(self._eval(rest[index], filters, rows))
                left, right = self._comparison_values(expression, candidate)
                if left == right:
                    return self._scalar(self._eval(rest[index + 1], filters, rows))
            return self._scalar(self._eval(rest[-1], filters, rows)) if has_else else BLANK
        if name == "COALESCE":
            for argument in node.arguments:
                value = self._scalar(self._eval(argument, filters, rows))
                if value is not BLANK:
                    return value
            return BLANK
        raise DaxEvaluationError("DAX_EVAL_FUNCTION", f"Function {name} is not implemented")

    def _column(self, argument: Expression, filters: FilterContext, rows: RowContext, function: str) -> ColumnVector:
        value = self._eval(argument, filters, rows)
        if not isinstance(value, ColumnVector):
            raise DaxEvaluationError("DAX_EVAL_TYPE", f"{function} requires a column reference")
        return value

    @staticmethod
    def _scalar(value: Any) -> Any:
        if isinstance(value, ColumnVector):
            raise DaxEvaluationError("DAX_EVAL_COLUMN_SCALAR", f"Column {value.table}[{value.column}] cannot be used as a scalar without row context or aggregation")
        if isinstance(value, TableVector):
            raise DaxEvaluationError("DAX_EVAL_TABLE_SCALAR", f"Table {value.table} cannot be used as a scalar")
        return value

    @staticmethod
    def _truthy(value: Any) -> bool:
        if value is BLANK:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, Decimal, float)):
            return value != 0
        if isinstance(value, str):
            return value != ""
        raise DaxEvaluationError("DAX_EVAL_TYPE", f"Cannot coerce {type(value).__name__} to boolean")

    @staticmethod
    def _numeric(value: Any, *, blank_as_zero: bool = False) -> Decimal:
        if value is BLANK:
            if blank_as_zero:
                return Decimal(0)
            raise DaxEvaluationError("DAX_EVAL_TYPE", "BLANK is not numeric in this context")
        if isinstance(value, bool):
            raise DaxEvaluationError("DAX_EVAL_TYPE", "Boolean values are not numeric in the Level 1 evaluator")
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))
        try:
            if isinstance(value, str) and value.strip():
                return Decimal(value)
        except InvalidOperation:
            pass
        raise DaxEvaluationError("DAX_EVAL_TYPE", f"Expected numeric value, received {type(value).__name__}")

    @classmethod
    def _comparison_values(cls, left: Any, right: Any) -> tuple[Any, Any]:
        if left is BLANK and right is BLANK:
            return Decimal(0), Decimal(0)
        if left is BLANK:
            if isinstance(right, str): return "", right
            if isinstance(right, bool): return False, right
            if isinstance(right, (int, Decimal, float)): return Decimal(0), cls._numeric(right)
            return left, right
        if right is BLANK:
            converted, other = cls._comparison_values(right, left)
            return other, converted
        if isinstance(left, (int, Decimal, float)) and not isinstance(left, bool) and isinstance(right, (int, Decimal, float)) and not isinstance(right, bool):
            return cls._numeric(left), cls._numeric(right)
        return left, right

    @classmethod
    def _sum(cls, vector: ColumnVector) -> Any:
        if vector.row_count == 0:
            return BLANK
        values = [value for value in vector.values if value is not BLANK]
        if not values:
            return BLANK
        total = Decimal(0)
        for value in values:
            total += cls._numeric(value)
        return total

    @staticmethod
    def _count(vector: ColumnVector, *, allow_boolean: bool) -> Any:
        if vector.row_count == 0:
            return BLANK
        count = 0
        for value in vector.values:
            if value is BLANK:
                continue
            if isinstance(value, bool) and not allow_boolean:
                raise DaxEvaluationError("DAX_EVAL_TYPE", "COUNT does not support TRUE/FALSE values; use COUNTA")
            count += 1
        return count

    @staticmethod
    def _distinctcount(vector: ColumnVector) -> Any:
        if vector.row_count == 0:
            return BLANK
        normalized = []
        for value in vector.values:
            if isinstance(value, (dict, list, set)):
                raise DaxEvaluationError("DAX_EVAL_TYPE", "DISTINCTCOUNT requires scalar column values")
            normalized.append(value)
        return len(set(normalized))

    @classmethod
    def _average(cls, vector: ColumnVector) -> Any:
        if vector.row_count == 0:
            return BLANK
        numeric: list[Decimal] = []
        for value in vector.values:
            if value is BLANK or isinstance(value, bool):
                continue
            if isinstance(value, str):
                return BLANK
            numeric.append(cls._numeric(value))
        if not numeric:
            return Decimal(0) if vector.row_count else BLANK
        return sum(numeric, Decimal(0)) / Decimal(len(numeric))

    @classmethod
    def _minmax(cls, vector: ColumnVector, minimum: bool) -> Any:
        if vector.row_count == 0:
            return BLANK
        values = [value for value in vector.values if value is not BLANK]
        if not values:
            return BLANK
        if any(isinstance(value, (str, bool)) for value in values):
            raise DaxEvaluationError("DAX_EVAL_TYPE", "MIN/MAX Level 1 column aggregation supports numeric/date/datetime values")
        if all(isinstance(value, (int, Decimal, float)) and not isinstance(value, bool) for value in values):
            converted = [cls._numeric(value) for value in values]
            return min(converted) if minimum else max(converted)
        try:
            return min(values) if minimum else max(values)
        except TypeError as exc:
            raise DaxEvaluationError("DAX_EVAL_TYPE", "MIN/MAX column values are not comparable") from exc
