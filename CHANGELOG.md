# Changelog

## 2026-09-01 — Power BI emulation Day 6 (ejecución anticipada)

- Added controlled DAX Level 2 filter-context execution.
- Added `CALCULATE`, `FILTER`, `ALL`, `ALLEXCEPT`, `REMOVEFILTERS`, `KEEPFILTERS`, `VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE` and `ISFILTERED`.
- Added context transition and deterministic direct-filter ordering for report/page/visual/user origins.
- Added active relationship propagation for one-to-many and controlled many-to-many paths, including bidirectional relationships.
- Added same-column CALCULATE replacement semantics and KEEPFILTERS intersection.
- Added early rejection of cyclic/ambiguous active relationship graphs.
- Added deterministic textual evaluation-plan evidence and focused Level 2 tests.
- Query planner/executor/cache remain Day 7 scope.

## 2026-09-01 — Power BI emulation Day 5 (ejecución anticipada)

- Added DAX Level 1 evaluator over local in-memory datasets.
- Added initial per-table filter context and basic row context.
- Added column/literal evaluation and controlled `COUNTROWS(Table)` table references.
- Added `SUM`, `COUNT`, `COUNTA`, `COUNTROWS`, `DISTINCTCOUNT`, `AVERAGE`, `MIN` and `MAX`.
- Added `DIVIDE`, `IF`, `SWITCH` and `COALESCE`, BLANK/null semantics, Decimal arithmetic and measure evaluation.

## 2026-09-01 — Power BI emulation Day 4 (ejecución anticipada)

- Added controlled DAX lexer, precedence parser, immutable serializable AST, diagnostics, limits, catalog and golden/security tests.

## 2026-09-01 — Power BI emulation Day 3 (ejecución anticipada)

- Added typed relationships, filter direction, active/inactive behavior, primary/date metadata, dependencies and structured model validation.

## 2026-09-01 — Power BI emulation Day 2 (ejecución anticipada)

- Added typed semantic tables/columns/measures/data sources, supported scalar types, CSV/JSONL/Parquet/Fakebrick sources, inference, conversion, profiles and path security.

## 2026-09-01 — Power BI emulation Day 1

- Added versioned SemanticModel/Report contracts, lifecycle states, standard errors, ETags, revision repository, migration scaffold and feature flag.
