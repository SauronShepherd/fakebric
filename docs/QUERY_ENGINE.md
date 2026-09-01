# Query engine MVP — Day 7

The Day 7 query service turns a versioned semantic model and controlled DAX expressions into bounded tabular results. It deliberately separates `query`, planner, executor, cache and transport contracts so the package can later move behind a dedicated query-service boundary.

## Plan

Every request produces deterministic `scan`, `filter`, `join`, `aggregate` and `project` evidence as applicable. The plan validates referenced model tables, columns and measures before execution. Active relationships between scanned tables are emitted as join evidence; actual filter propagation remains delegated to the Day 6 DAX engine.

## Execution

The semantic/DAX layer evaluates groups and measures first. The result is then materialized through Apache Arrow and an in-memory DuckDB connection when both dependencies are present. No caller-supplied SQL is accepted or interpolated. If DuckDB/Arrow cannot be loaded, the bounded Python result is returned with an explicit compatibility warning instead of silently changing semantics.

`duckdb==1.5.5` and `pyarrow==25.0.1` are pinned in `requirements.txt`.

## Pagination, limits and cancellation

`page` and `pageSize` paginate a stable materialized execution. `maxRows` caps generated result rows and adds `QUERY_RESULT_TRUNCATED`. `timeoutMs` is enforced by cooperative checks during planning, row/group execution and result materialization; explicit cancellation uses the same token and deterministic error code.

## Cache and isolation

Cache identity includes model id, model revision, the query/filter context, `dataRevision`, the bounded inline data payload and `userId`. Pagination and timeout are deliberately excluded so subsequent pages reuse the same materialized execution. A new model revision or different user therefore misses the previous cache entry.

## Response

`POST /api/v1/models/{id}/query` returns version `1.0`, typed columns, rows, warnings, pagination, textual/structured plan evidence and metrics for rows read, bytes read, duration, planning/execution duration, returned rows, cache hit and backend.

The endpoint currently accepts an explicit envelope containing the model and inline tables; integration with the persistent control plane and durable catalog remains Day 10 scope.
