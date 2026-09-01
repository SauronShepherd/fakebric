# Changelog

## 2026-09-01 — Power BI emulation Day 7 (ejecución anticipada)

- Added versioned query contracts and `POST /api/v1/models/{id}/query`.
- Added deterministic query plans with scan/filter/join/aggregate/project nodes.
- Added bounded grouped DAX execution and typed tabular result adaptation.
- Added safe Arrow/in-memory DuckDB materialization with no caller SQL.
- Added stable pagination, maximum-row warnings and cooperative timeout/cancellation.
- Added cache identity by model/revision/query/filter context/data revision/data/user with pagination reuse.
- Added rows, bytes, duration, planning/execution, returned-row, cache-hit and backend metrics.
- Updated the stale SemanticModel JSON schema to include Day 3 relationships/dependencies and added versioned query schemas.
- Report/visual runtime remains Day 8 scope.

## 2026-09-01 — Power BI emulation Day 6 (ejecución anticipada)

- Added controlled DAX Level 2 filter-context execution.
- Added `CALCULATE`, `FILTER`, `ALL`, `ALLEXCEPT`, `REMOVEFILTERS`, `KEEPFILTERS`, `VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE` and `ISFILTERED`.
- Added context transition and deterministic direct-filter ordering for report/page/visual/user origins.
- Added active relationship propagation for one-to-many and controlled many-to-many paths, including bidirectional relationships.
- Added same-column CALCULATE replacement semantics and KEEPFILTERS intersection.
- Added early rejection of cyclic/ambiguous active relationship graphs.

## 2026-09-01 — Power BI emulation Day 5 (ejecución anticipada)

- Added DAX Level 1 evaluator, filter/row context, aggregations/logical functions, BLANK/null semantics, Decimal arithmetic and measures.

## 2026-09-01 — Power BI emulation Day 4 (ejecución anticipada)

- Added controlled DAX lexer, precedence parser, immutable serializable AST, diagnostics, limits, catalog and golden/security tests.

## 2026-09-01 — Power BI emulation Day 3 (ejecución anticipada)

- Added typed relationships, filter direction, active/inactive behavior, primary/date metadata, dependencies and structured model validation.

## 2026-09-01 — Power BI emulation Day 2 (ejecución anticipada)

- Added typed semantic tables/columns/measures/data sources, supported scalar types, CSV/JSONL/Parquet/Fakebrick sources, inference, conversion, profiles and path security.

## 2026-09-01 — Power BI emulation Day 1

- Added versioned SemanticModel/Report contracts, lifecycle states, standard errors, ETags, revision repository, migration scaffold and feature flag.
