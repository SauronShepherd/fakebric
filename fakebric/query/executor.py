from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from fakebric.dax import DaxEngine, FilterContext, FilterOrigin

from .backend import DuckDbArrowBackend
from .cancel import QueryCancellationToken
from .contracts import QueryRequest, ResultColumn
from .planner import QueryPlan


@dataclass(frozen=True)
class ExecutionResult:
    columns: tuple[ResultColumn, ...]
    rows: tuple[tuple, ...]
    warnings: tuple[str, ...]
    rows_read: int
    bytes_read: int
    backend: str
    execution_ms: float


def _json_value(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _type_of(value):
    if value is None:
        return "blank"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, (Decimal, float)):
        return "decimal"
    if isinstance(value, datetime):
        return "datetime"
    if isinstance(value, date):
        return "date"
    if isinstance(value, str):
        return "string"
    return "mixed"


def _column_type(values):
    kinds = {_type_of(value) for value in values if value is not None}
    if not kinds:
        return "blank"
    if kinds <= {"integer", "decimal"}:
        return "decimal" if "decimal" in kinds else "integer"
    return next(iter(kinds)) if len(kinds) == 1 else "mixed"


class QueryExecutor:
    def __init__(self, backend=None, clock=time.perf_counter, engine_factory=None) -> None:
        self.backend = backend or DuckDbArrowBackend()
        self.clock = clock
        self.engine_factory = engine_factory or DaxEngine.from_semantic_model

    def _context(self, request):
        context = FilterContext()
        for flt in request.filters:
            context = context.with_values(flt.table, flt.column, flt.values, FilterOrigin(flt.origin.value))
        return context

    def _group_sets(self, engine, request, context):
        if not request.group_by:
            return [((), ())]
        per_table = []
        order = []
        for ref in request.group_by:
            key = ref.table.casefold()
            if key not in order:
                order.append(key)
        for key in order:
            refs = [item for item in request.group_by if item.table.casefold() == key]
            table_name, rows = engine.table(refs[0].table)
            seen = []
            for index in engine.visible(table_name, context):
                values = tuple(engine.val(rows[index], ref.column, table_name) for ref in refs)
                if values not in seen:
                    seen.append(values)
            per_table.append((refs, seen))
        if any(not values for _, values in per_table):
            return []
        combinations = []
        for selected in itertools.product(*(values for _, values in per_table)):
            flat_values = []
            flat_refs = []
            for (refs, _), values in zip(per_table, selected):
                flat_refs.extend(refs)
                flat_values.extend(values)
            combinations.append((tuple(flat_refs), tuple(flat_values)))
        return combinations

    def _read_metrics(self, engine, plan, context):
        rows_read = 0
        bytes_read = 0
        for table in plan.scanned_tables:
            name, rows = engine.table(table)
            indices = engine.visible(name, context)
            rows_read += len(indices)
            for index in indices:
                bytes_read += len(json.dumps(rows[index], sort_keys=True, default=_json_value, separators=(",", ":")).encode())
        return rows_read, bytes_read

    def execute(self, model, tables, request: QueryRequest, plan: QueryPlan, token: QueryCancellationToken) -> ExecutionResult:
        started = self.clock()
        token.check()
        engine = self.engine_factory(model, tables)
        context = self._context(request)
        token.check()
        rows_read, bytes_read = self._read_metrics(engine, plan, context)
        groups = self._group_sets(engine, request, context)
        token.check()
        raw = []
        truncated = False
        for refs, values in groups:
            token.check()
            if len(raw) >= request.max_rows:
                truncated = True
                break
            scoped = context
            for ref, value in zip(refs, values):
                scoped = scoped.with_values(ref.table, ref.column, [value], FilterOrigin.VISUAL)
            measures = [engine.evaluate(item.expression, filter_context=scoped) for item in request.expressions]
            raw.append(tuple(values) + tuple(measures))
        names = [f"{item.table}.{item.column}" for item in request.group_by] + [item.name for item in request.expressions]
        token.check()
        adapted = self.backend.adapt(names, raw)
        token.check()
        columns = [ResultColumn(name=name, type=_column_type([row[index] for row in adapted.rows])) for index, name in enumerate(names)]
        normalized = tuple(tuple(_json_value(value) for value in row) for row in adapted.rows)
        warnings = list(adapted.warnings)
        if truncated:
            warnings.append("QUERY_RESULT_TRUNCATED")
        return ExecutionResult(tuple(columns), normalized, tuple(warnings), rows_read, bytes_read, adapted.backend, (self.clock() - started) * 1000)
