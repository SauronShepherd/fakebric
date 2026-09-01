# Fakebrick

Fabric-inspired OSS data engineering workspace. The control plane includes workspaces, extensible items, portable notebooks, lakehouse namespaces, environment revisions, session lifecycle, optimistic saves, UI shell and Minikube manifests. `runtime/` defines the reproducible Spark/Jupyter execution-plane base.

```powershell
pip install -r requirements.txt
uvicorn fakebric.app:app --reload
```

## Power BI emulation MVP

Power BI emulation is under active development on `codex/powerbi-emulation` following `POWERBI_EMULATION_SPEC.md` and `POWERBI_EMULATION_BUILD_PLAN_13_DAYS.md`. The implementation is Linux-first and intentionally exposes only documented compatible behavior.

Days 1–3 established versioned semantic/report contracts, typed tables/sources, relationships and structured model validation. Day 4 added the controlled DAX parser/AST. Day 5 added Level 1 aggregation and logic evaluation. Day 6 added Level 2 filter context, context transition and relationship propagation.

Day 7 adds a separated query package with deterministic `scan/filter/join/aggregate/project` plans, bounded tabular execution, versioned query contracts, stable pagination, cooperative timeout/cancellation, per-user/revision cache isolation, rows/bytes/duration/cache metrics and `POST /api/v1/models/{id}/query`. Arrow + in-memory DuckDB materialize safe results when available; no user SQL is executed.

```bash
python -m pytest -q \
  tests/test_dax_parser.py tests/test_dax_golden.py tests/test_dax_security.py \
  tests/test_dax_evaluator.py tests/test_dax_level2.py \
  tests/test_query_service.py tests/test_query_api.py tests/test_query_backend.py tests/test_query_contracts.py
```

See `docs/DAX_LEVEL1_SEMANTICS.md`, `docs/DAX_LEVEL2_SEMANTICS.md`, `docs/DAX_FUNCTION_CATALOG.md` and `docs/QUERY_ENGINE.md`. Report pages and visual runtime remain Day 8 scope.

Parquet/Arrow support uses `pyarrow`; Day 7 additionally pins DuckDB for safe in-memory tabular materialization. File-backed sources remain confined under caller-supplied workspace roots.

## Validación local y Minikube

```powershell
python -m pytest -q --cov=fakebric --cov-fail-under=75
python -m compileall -q fakebric tools tests
node --check fakebric/static/app.js
```

Semantic Model and Report are represented as extensible item types. The exact implemented/partial/unsupported scope is maintained in `REQUIREMENTS_MATRIX.md`; unsupported capabilities are deliberately not advertised as available.
