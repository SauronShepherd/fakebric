# Changelog

## 2026-09-01 — Power BI emulation Day 4 (ejecución anticipada)

- Added controlled DAX lexer and precedence parser.
- Added immutable, JSON-serializable AST nodes for literals, references, unary/binary operators and function calls.
- Added qualified table/member references, strings, numbers and DAX `dt"..."` date/datetime literals.
- Added structured diagnostics with code, line, column, token and message.
- Added expression length, token, nesting-depth and AST-complexity limits.
- Added deterministic rejection of unknown functions, ambiguous references/comparisons and non-DAX syntax.
- Added published parser function catalog plus AST golden and parser-security tests.
- DAX evaluation remains intentionally unavailable until Days 5–6.

## 2026-09-01 — Power BI emulation Day 3 (ejecución anticipada)

- Added typed relationships for one-to-one, one-to-many and many-to-many cardinalities.
- Added single/both filter direction and active/inactive relationship behavior.
- Added primary-key and date-table metadata.
- Added structured dependency references and structured model validation.
- Added `POST /api/v1/models/{id}/validate` on the semantic-model service/router.

## 2026-09-01 — Power BI emulation Day 2 (ejecución anticipada)

- Added `Table`, `Column`, `Measure` and `DataSource` semantic contracts.
- Added supported scalar types, CSV/JSONL/Parquet/Fakebrick sources, inference, conversion, profiles and path security.

## 2026-09-01 — Power BI emulation Day 1

- Added versioned Pydantic contracts for `SemanticModel` and `Report`.
- Added lifecycle states, standard errors, deterministic ETags, revision repository, migration scaffold and feature flag.
