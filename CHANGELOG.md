# Changelog

## 2026-09-01 — Power BI emulation Day 1

- Added versioned Pydantic contracts for `SemanticModel` and `Report`.
- Added lifecycle states `Draft`, `Published`, and `Archived`.
- Added standard Power BI emulation error codes.
- Added deterministic canonical serialization and SHA-256 ETags.
- Added an optimistic-concurrency revision repository and migration registry scaffolding.
- Added `FAKEBRIC_POWERBI_EMULATION`, disabled by default.
- Added JSON Schemas and focused contract tests.
- Scope remains explicitly partial; tables, relationships, DAX, report visuals and runtime behavior are not claimed as implemented.
