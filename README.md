# Fakebrick

Fabric-inspired OSS data engineering workspace. The control plane includes workspaces, extensible items, portable notebooks, lakehouse namespaces, environment revisions, session lifecycle, optimistic saves, UI shell and Minikube manifests. `runtime/` defines the reproducible Spark/Jupyter execution-plane base.

```powershell
pip install -r requirements.txt
uvicorn fakebric.app:app --reload
```

## Power BI emulation MVP

Power BI emulation is under active development on `codex/powerbi-emulation` following `POWERBI_EMULATION_SPEC.md` and `POWERBI_EMULATION_BUILD_PLAN_13_DAYS.md`. The implementation is Linux-first and intentionally exposes only documented compatible behavior.

Days 1–3 established versioned semantic/report contracts, typed tables/sources, relationships and structured model validation. Day 4 added the controlled DAX parser/AST. Day 5 added Level 1 aggregation and logic evaluation.

Day 6 adds the core Level 2 filter-context behavior: `CALCULATE`, `FILTER`, `ALL`, `ALLEXCEPT`, `REMOVEFILTERS`, `KEEPFILTERS`, `VALUES`, `DISTINCT`, `SELECTEDVALUE`, `HASONEVALUE` and `ISFILTERED`; context transition; report/page/visual/user direct-filter ordering; active relationship propagation; and deterministic rejection of ambiguous active relationship graphs.

```bash
python -m pytest -q \
  tests/test_dax_parser.py \
  tests/test_dax_golden.py \
  tests/test_dax_security.py \
  tests/test_dax_evaluator.py \
  tests/test_dax_level2.py
```

See `docs/DAX_LEVEL1_SEMANTICS.md`, `docs/DAX_LEVEL2_SEMANTICS.md` and `docs/DAX_FUNCTION_CATALOG.md`. Query planning, DuckDB/Arrow execution, pagination, cancellation and query caching remain Day 7 scope.

Parquet support uses `pyarrow` from `requirements.txt`. File-backed sources are resolved under a caller-supplied workspace root; traversal and absolute paths outside that root are rejected.

## Validación local y Minikube

```powershell
python -m pytest -q --cov=fakebric --cov-fail-under=75
python -m compileall -q fakebric tools tests
node --check fakebric/static/app.js
```

Semantic Model and Report are represented as extensible item types. The exact implemented/partial/unsupported scope is maintained in `REQUIREMENTS_MATRIX.md`; unsupported capabilities are deliberately not advertised as available.
