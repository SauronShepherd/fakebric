# Changelog

## 2026-09-01 — Power BI emulation Day 8 (ejecución anticipada)

- Added ordered report pages with bounded geometry and orientation.
- Added typed card, table, matrix, bar, column, line, pie, donut, scatter and slicer visual contracts.
- Added report query/filter references, theme and basic number/visual formatting.
- Added deterministic loading, empty, error and ready report-runtime states plus escaped accessible HTML metadata.
- Added standalone report CRUD/render API with ETag/revision concurrency.
- Added an eight-visual render fixture and generated `schemas/report.schema.json`.
- Interactions, cross-filtering, drill and export remain Day 9 scope.

## 2026-09-01 — Power BI emulation Day 7 (ejecución anticipada)

- Added versioned query contracts and `POST /api/v1/models/{id}/query`.
- Added deterministic query plans with scan/filter/join/aggregate/project nodes.
- Added bounded grouped DAX execution, DuckDB/Arrow result materialization, stable pagination, limits, cancellation, cache isolation and metrics.
- Updated stale SemanticModel schema and added query request/response schemas.

## 2026-09-01 — Power BI emulation Day 6 (ejecución anticipada)

- Added controlled DAX Level 2 filter-context execution, CALCULATE/FILTER/modifiers, context transition and relationship propagation.

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
