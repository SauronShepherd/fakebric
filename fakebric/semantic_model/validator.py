from __future__ import annotations

from collections import deque
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from fakebric.semantic_model.schema import (
    DataType,
    DependencyKind,
    DependencyRef,
    FilterDirection,
    Relationship,
    RelationshipCardinality,
    SemanticModel,
)


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    severity: ValidationSeverity
    code: str
    location: str
    message: str
    suggested_fix: str = Field(alias="suggestedFix")


class ValidationReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_id: str = Field(alias="modelId")
    valid: bool
    issues: list[ValidationIssue]
    dependency_graph: dict[str, list[str]] = Field(alias="dependencyGraph")
    filter_graph: dict[str, list[str]] = Field(alias="filterGraph")


_NUMERIC = {DataType.INTEGER, DataType.DECIMAL}


def _issue(
    code: str,
    location: str,
    message: str,
    suggested_fix: str,
    severity: ValidationSeverity = ValidationSeverity.ERROR,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        code=code,
        location=location,
        message=message,
        suggestedFix=suggested_fix,
    )


def _compatible(left: DataType, right: DataType) -> bool:
    return left == right or {left, right} <= _NUMERIC


def _table_node(name: str) -> str:
    return f"table:{name}"


def _column_node(table: str, name: str) -> str:
    return f"column:{table}.{name}"


def _measure_node(table: str, name: str) -> str:
    return f"measure:{table}.{name}"


def _resolve_dependency(model: SemanticModel, ref: DependencyRef) -> str | None:
    try:
        table = model.table(ref.table)
    except KeyError:
        return None
    if ref.kind == DependencyKind.TABLE:
        return _table_node(table.name)
    if ref.kind == DependencyKind.COLUMN:
        try:
            return _column_node(table.name, table.column(ref.name or "").name)
        except KeyError:
            return None
    try:
        return _measure_node(table.name, table.measure(ref.name or "").name)
    except KeyError:
        return None


def build_dependency_graph(
    model: SemanticModel,
) -> tuple[dict[str, list[str]], list[ValidationIssue]]:
    graph: dict[str, list[str]] = {}
    issues: list[ValidationIssue] = []

    for table in model.tables:
        table_node = _table_node(table.name)
        graph.setdefault(table_node, [])
        members = [
            (
                _column_node(table.name, column.name),
                column.depends_on,
                f"tables[{table.name}].columns[{column.name}].dependsOn",
            )
            for column in table.columns
        ] + [
            (
                _measure_node(table.name, measure.name),
                measure.depends_on,
                f"tables[{table.name}].measures[{measure.name}].dependsOn",
            )
            for measure in table.measures
        ]
        for node, references, location in members:
            graph[node] = [table_node]
            for ref in references:
                target = _resolve_dependency(model, ref)
                if target is None:
                    issues.append(
                        _issue(
                            "DEPENDENCY_TARGET_NOT_FOUND",
                            location,
                            f"Dependency target {ref.model_dump()} does not exist",
                            "Reference an existing table, column or measure.",
                        )
                    )
                elif target not in graph[node]:
                    graph[node].append(target)

    state: dict[str, int] = {}

    def has_cycle(node: str) -> bool:
        state[node] = 1
        for target in graph.get(node, []):
            if target.startswith("table:"):
                continue
            if state.get(target) == 1:
                return True
            if state.get(target, 0) == 0 and has_cycle(target):
                return True
        state[node] = 2
        return False

    if any(state.get(node, 0) == 0 and has_cycle(node) for node in graph):
        issues.append(
            _issue(
                "DEPENDENCY_CYCLE",
                "dependencies",
                "The semantic dependency graph contains a cycle",
                "Break the circular column/measure dependency.",
            )
        )

    return {node: sorted(targets) for node, targets in sorted(graph.items())}, issues


def build_filter_graph(model: SemanticModel) -> dict[str, list[str]]:
    graph: dict[str, set[str]] = {table.name: set() for table in model.tables}
    for relationship in model.relationships:
        if not relationship.active:
            continue
        try:
            left = model.table(relationship.from_table).name
            right = model.table(relationship.to_table).name
        except KeyError:
            continue
        if relationship.cardinality == RelationshipCardinality.ONE_TO_MANY:
            graph[right].add(left)
            if relationship.filter_direction == FilterDirection.BOTH:
                graph[left].add(right)
        else:
            graph[left].add(right)
            if relationship.filter_direction == FilterDirection.BOTH:
                graph[right].add(left)
    return {name: sorted(targets) for name, targets in sorted(graph.items())}


def propagated_tables(model: SemanticModel, start_table: str) -> tuple[str, ...]:
    graph = build_filter_graph(model)
    start = model.table(start_table).name
    visited = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for target in graph.get(current, []):
            if target not in visited:
                visited.add(target)
                queue.append(target)
    return tuple(sorted(visited))


def _relationship_key(relationship: Relationship) -> tuple[str, ...]:
    return (
        relationship.from_table.casefold(),
        relationship.from_column.casefold(),
        relationship.to_table.casefold(),
        relationship.to_column.casefold(),
        relationship.cardinality.value,
    )


def _validate_date_tables(model: SemanticModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for table in model.tables:
        if not table.is_date_table:
            continue
        location = f"tables[{table.name}].dateColumn"
        if not table.date_column:
            issues.append(
                _issue(
                    "DATE_TABLE_COLUMN_REQUIRED",
                    location,
                    "A marked date table requires dateColumn",
                    "Set dateColumn to a date or datetime column in the table.",
                )
            )
            continue
        try:
            column = table.column(table.date_column)
        except KeyError:
            issues.append(
                _issue(
                    "DATE_TABLE_COLUMN_NOT_FOUND",
                    location,
                    f"Date column {table.date_column!r} does not exist",
                    "Reference an existing date/datetime column.",
                )
            )
            continue
        if column.type not in {DataType.DATE, DataType.DATETIME}:
            issues.append(
                _issue(
                    "DATE_TABLE_COLUMN_TYPE",
                    location,
                    "A date table column must use date or datetime type",
                    "Use a date/datetime column or remove the date-table marker.",
                )
            )
    return issues


def _validate_relationships(
    model: SemanticModel,
) -> tuple[list[ValidationIssue], list[tuple[int, str, str]]]:
    issues: list[ValidationIssue] = []
    active_edges: list[tuple[int, str, str]] = []
    seen: dict[tuple[str, ...], int] = {}

    for index, relationship in enumerate(model.relationships):
        location = f"relationships[{index}]"
        key = _relationship_key(relationship)
        if key in seen:
            issues.append(
                _issue(
                    "DUPLICATE_RELATIONSHIP",
                    location,
                    f"Relationship duplicates relationships[{seen[key]}]",
                    "Remove the duplicate or change its endpoints/cardinality.",
                )
            )
        else:
            seen[key] = index

        try:
            left_table = model.table(relationship.from_table)
        except KeyError:
            issues.append(
                _issue(
                    "RELATIONSHIP_TABLE_NOT_FOUND",
                    f"{location}.fromTable",
                    f"Table {relationship.from_table!r} does not exist",
                    "Reference an existing table.",
                )
            )
            continue
        try:
            right_table = model.table(relationship.to_table)
        except KeyError:
            issues.append(
                _issue(
                    "RELATIONSHIP_TABLE_NOT_FOUND",
                    f"{location}.toTable",
                    f"Table {relationship.to_table!r} does not exist",
                    "Reference an existing table.",
                )
            )
            continue
        try:
            left_column = left_table.column(relationship.from_column)
        except KeyError:
            issues.append(
                _issue(
                    "RELATIONSHIP_COLUMN_NOT_FOUND",
                    f"{location}.fromColumn",
                    f"Column {relationship.from_column!r} does not exist in {left_table.name!r}",
                    "Reference an existing column.",
                )
            )
            continue
        try:
            right_column = right_table.column(relationship.to_column)
        except KeyError:
            issues.append(
                _issue(
                    "RELATIONSHIP_COLUMN_NOT_FOUND",
                    f"{location}.toColumn",
                    f"Column {relationship.to_column!r} does not exist in {right_table.name!r}",
                    "Reference an existing column.",
                )
            )
            continue

        if not _compatible(left_column.type, right_column.type):
            issues.append(
                _issue(
                    "RELATIONSHIP_TYPE_MISMATCH",
                    location,
                    "Relationship columns use incompatible types: "
                    f"{left_column.type.value} and {right_column.type.value}",
                    "Use compatible column types or add an explicit conversion before relating them.",
                )
            )
        if (
            relationship.cardinality == RelationshipCardinality.ONE_TO_MANY
            and not right_column.is_primary_key
        ):
            issues.append(
                _issue(
                    "ONE_SIDE_NOT_MARKED_KEY",
                    f"{location}.toColumn",
                    "The one-side column is not marked as a primary key",
                    "Mark the one-side column isPrimaryKey=true when it is unique.",
                    severity=ValidationSeverity.WARNING,
                )
            )
        if relationship.active:
            active_edges.append((index, left_table.name, right_table.name))

    return issues, active_edges


def _relationship_path_issues(
    model: SemanticModel, active_edges: list[tuple[int, str, str]]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    parent = {table.name: table.name for table in model.tables}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for index, left, right in active_edges:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root
            continue
        location = f"relationships[{index}]"
        issues.extend(
            [
                _issue(
                    "RELATIONSHIP_CYCLE",
                    location,
                    f"Active relationship {left!r} -> {right!r} closes a relationship cycle",
                    "Deactivate one relationship or redesign the relationship path.",
                ),
                _issue(
                    "AMBIGUOUS_FILTER_PATH",
                    location,
                    "This active relationship creates more than one relationship path between tables",
                    "Leave only one unambiguous active filter path.",
                ),
            ]
        )
    return issues


def validate_model(model: SemanticModel) -> ValidationReport:
    dependency_graph, dependency_issues = build_dependency_graph(model)
    relationship_issues, active_edges = _validate_relationships(model)
    issues = [
        *dependency_issues,
        *_validate_date_tables(model),
        *relationship_issues,
        *_relationship_path_issues(model, active_edges),
    ]
    return ValidationReport(
        modelId=model.id,
        valid=not any(issue.severity == ValidationSeverity.ERROR for issue in issues),
        issues=issues,
        dependencyGraph=dependency_graph,
        filterGraph=build_filter_graph(model),
    )
