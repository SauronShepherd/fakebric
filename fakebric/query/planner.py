from __future__ import annotations

from dataclasses import dataclass

from fakebric.dax import BinaryOp, FunctionCall, Reference, TableReference, UnaryOp, parse_dax

from .contracts import PlanNode, QueryRequest

_AGGREGATES = {"SUM", "COUNT", "COUNTA", "COUNTROWS", "DISTINCTCOUNT", "AVERAGE", "MIN", "MAX"}


class QueryPlanningError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class QueryPlan:
    nodes: tuple[PlanNode, ...]
    text: str
    scanned_tables: tuple[str, ...]


def _walk(node):
    yield node
    if isinstance(node, UnaryOp):
        yield from _walk(node.operand)
    elif isinstance(node, BinaryOp):
        yield from _walk(node.left)
        yield from _walk(node.right)
    elif isinstance(node, FunctionCall):
        for argument in node.arguments:
            yield from _walk(argument)


def _tables_and_aggregate(expression: str):
    ast = parse_dax(expression)
    tables = set()
    aggregate = False
    for node in _walk(ast):
        if isinstance(node, (Reference, TableReference)):
            tables.add(node.table)
        if isinstance(node, FunctionCall) and node.name in _AGGREGATES:
            aggregate = True
    return ast, tables, aggregate


class QueryPlanner:
    def plan(self, model, request: QueryRequest) -> QueryPlan:
        tables = {item.table for item in request.group_by} | {item.table for item in request.filters}
        aggregate = False
        for ref in request.group_by:
            try:
                model.table(ref.table).column(ref.column)
            except KeyError as exc:
                raise QueryPlanningError("QUERY_COLUMN_NOT_FOUND", f"{ref.table}[{ref.column}]") from exc
        for flt in request.filters:
            try:
                model.table(flt.table).column(flt.column)
            except KeyError as exc:
                raise QueryPlanningError("QUERY_COLUMN_NOT_FOUND", f"{flt.table}[{flt.column}]") from exc
        for expression in request.expressions:
            ast, expression_tables, is_aggregate = _tables_and_aggregate(expression.expression)
            tables.update(expression_tables)
            aggregate |= is_aggregate
            for node in _walk(ast):
                if isinstance(node, Reference):
                    try:
                        table = model.table(node.table)
                    except KeyError as exc:
                        raise QueryPlanningError("QUERY_TABLE_NOT_FOUND", node.table) from exc
                    try:
                        table.column(node.name)
                    except KeyError:
                        try:
                            table.measure(node.name)
                        except KeyError as exc:
                            raise QueryPlanningError("QUERY_MEMBER_NOT_FOUND", f"{node.table}[{node.name}]") from exc
                elif isinstance(node, TableReference):
                    try:
                        model.table(node.table)
                    except KeyError as exc:
                        raise QueryPlanningError("QUERY_TABLE_NOT_FOUND", node.table) from exc
        canonical = []
        for name in sorted(tables, key=str.casefold):
            try:
                canonical.append(model.table(name).name)
            except KeyError as exc:
                raise QueryPlanningError("QUERY_TABLE_NOT_FOUND", name) from exc
        nodes = [PlanNode(kind="scan", detail=f"table={name}") for name in canonical]
        nodes.extend(PlanNode(kind="filter", detail=f"{flt.origin.value}:{flt.table}[{flt.column}] values={len(flt.values)}") for flt in request.filters)
        scanned = {name.casefold() for name in canonical}
        for relationship in model.relationships:
            if relationship.active and relationship.from_table.casefold() in scanned and relationship.to_table.casefold() in scanned:
                nodes.append(PlanNode(kind="join", detail=f"{relationship.name}:{relationship.from_table}[{relationship.from_column}] -> {relationship.to_table}[{relationship.to_column}] {relationship.cardinality.value}/{relationship.filter_direction.value}"))
        if request.expressions:
            nodes.append(PlanNode(kind="aggregate", detail="expressions=" + ",".join(item.name for item in request.expressions) + (":dax" if aggregate else ":scalar")))
        outputs = [f"{item.table}.{item.column}" for item in request.group_by] + [item.name for item in request.expressions]
        nodes.append(PlanNode(kind="project", detail="columns=" + ",".join(outputs)))
        text = "\n".join(f"{index:02d}. {node.kind} {node.detail}" for index, node in enumerate(nodes, 1))
        return QueryPlan(tuple(nodes), text, tuple(canonical))
