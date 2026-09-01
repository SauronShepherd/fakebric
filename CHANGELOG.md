# Changelog

## 2026-09-01 — Power BI emulation Day 3 (ejecución anticipada)

- Added typed relationships for one-to-one, one-to-many and many-to-many cardinalities.
- Added single/both filter direction and active/inactive relationship behavior.
- Added primary-key and date-table metadata.
- Added structured dependency references for tables, columns and measures without prematurely parsing DAX.
- Added model validation for missing tables/columns, type mismatch, duplicate relationships, cycles and ambiguous paths.
- Added dependency-cycle detection and structured diagnostics with severity, code, location and suggested fix.
- Added `POST /api/v1/models/{id}/validate` on the semantic-model service/router.
- Added propagation/filter-graph evidence and regression coverage for Day 1–2 contracts.

## 2026-09-01 — Power BI emulation Day 2 (ejecución anticipada)

- Added `Table`, `Column`, `Measure` and `DataSource` semantic contracts.
- Added string, integer, decimal, boolean, date, datetime and binary types.
- Added workspace-confined readers for CSV, JSONL and Parquet plus registered local Fakebrick tables.
- Added explicit conversion with deterministic rejection of invalid values and nullability violations.
- Added reviewable schema inference with confidence and nullable metadata.
- Added dataset profiles with row count, nulls, min, max and cardinality.
- Added duplicate-table/column/measure validation and missing-source-column diagnostics.
- Added source-path traversal protection and rejection of inline credential-like options; credentials use `credentialRef`.
- Added deterministic fixtures for inference/statistics and focused tests.
- Added `pyarrow` as the Parquet dependency.
- Relationships, DAX, query execution and report visuals remain outside this increment.

## 2026-09-01 — Power BI emulation Day 1

- Added versioned Pydantic contracts for `SemanticModel` and `Report`.
- Added lifecycle states `Draft`, `Published`, and `Archived`.
- Added standard Power BI emulation error codes.
- Added deterministic canonical serialization and SHA-256 ETags.
- Added an optimistic-concurrency revision repository and migration registry scaffolding.
- Added `FAKEBRIC_POWERBI_EMULATION`, disabled by default.
- Added JSON Schemas and focused contract tests.
