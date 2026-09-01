# Fakebrick

Fabric-inspired OSS data engineering workspace. The control plane includes workspaces, extensible items, portable notebooks, lakehouse namespaces, environment revisions, session lifecycle, optimistic saves, UI shell and Minikube manifests. `runtime/` defines the reproducible Spark/Jupyter execution-plane base.

```powershell
pip install -r requirements.txt
uvicorn fakebric.app:app --reload
```

## Power BI emulation MVP

Power BI emulation is under active development on `codex/powerbi-emulation` following `POWERBI_EMULATION_SPEC.md` and `POWERBI_EMULATION_BUILD_PLAN_13_DAYS.md`. The implementation is Linux-first and intentionally exposes only documented compatible behavior.

Days 1–3 established versioned semantic/report contracts, typed tables/sources, relationships and structured model validation. Day 4 added a controlled DAX lexer/parser and immutable JSON-serializable AST with limits and structured diagnostics.

Day 5 adds local DAX Level 1 evaluation over in-memory datasets: initial filter context, row context, literals/column evaluation, `SUM`, `COUNT`, `COUNTA`, `COUNTROWS`, `DISTINCTCOUNT`, `AVERAGE`, `MIN`, `MAX`, `DIVIDE`, `IF`, `SWITCH` and `COALESCE`. Results use `Decimal` for stable numeric behavior and preserve BLANK distinctly from zero. See `docs/DAX_LEVEL1_SEMANTICS.md`.

```bash
python -m pytest -q \
  tests/test_dax_parser.py \
  tests/test_dax_golden.py \
  tests/test_dax_security.py \
  tests/test_dax_evaluator.py
```

Level 2 functions such as `CALCULATE`, `FILTER`, `ALL` and relationship-driven filter propagation parse but deliberately fail at evaluation until Day 6.

Parquet support uses `pyarrow` from `requirements.txt`. File-backed sources are resolved under a caller-supplied workspace root; traversal and absolute paths outside that root are rejected.

## Validación local y Minikube

```powershell
python -m pytest -q --cov=fakebric --cov-fail-under=75
python -m compileall -q fakebric tools tests
node --check fakebric/static/app.js
```

Semantic Model and Report are represented as extensible item types. The exact implemented/partial/unsupported scope is maintained in `REQUIREMENTS_MATRIX.md`; unsupported capabilities are deliberately not advertised as available.
