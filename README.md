# Fakebrick

Fabric-inspired OSS data engineering workspace. The control plane includes workspaces, extensible items, portable notebooks, lakehouse namespaces, environment revisions, session lifecycle, optimistic saves, UI shell and Minikube manifests. `runtime/` defines the reproducible Spark/Jupyter execution-plane base.

```powershell
pip install -r requirements.txt
uvicorn fakebric.app:app --reload
```

## Power BI emulation MVP

Power BI emulation is under active development on `codex/powerbi-emulation` following `POWERBI_EMULATION_SPEC.md` and `POWERBI_EMULATION_BUILD_PLAN_13_DAYS.md`. The implementation is Linux-first and intentionally exposes only documented compatible behavior.

Days 1–3 established versioned semantic/report contracts, typed tables/sources, relationships and structured model validation.

Day 4 adds a controlled DAX lexer/parser and immutable JSON-serializable AST. It supports qualified references, literals, arithmetic/comparison/boolean operators, parentheses and a published function catalog. Diagnostics include line, column, token and error code, and parser limits cap expression length, tokens, depth and AST complexity. Unknown functions and ambiguous/non-DAX syntax fail deterministically.

**Parser acceptance does not mean execution support.** DAX evaluation and Level 1 aggregation semantics begin on Day 5. See `docs/DAX_FUNCTION_CATALOG.md` for the accepted syntax/function catalog.

```bash
python -m pytest -q tests/test_dax_parser.py tests/test_dax_golden.py tests/test_dax_security.py
```

Parquet support uses `pyarrow` from `requirements.txt`. File-backed sources are resolved under a caller-supplied workspace root; traversal and absolute paths outside that root are rejected.

## Validación local y Minikube

```powershell
python -m pytest -q --cov=fakebric --cov-fail-under=75
python -m compileall -q fakebric tools tests
node --check fakebric/static/app.js
```

Semantic Model and Report are represented as extensible item types. DAX parsing is now partial; DAX evaluation, report rendering, RLS and later capabilities remain unavailable until their scheduled increments.

The exact implemented/partial/unsupported scope is maintained in `REQUIREMENTS_MATRIX.md`; unsupported capabilities are deliberately not advertised as available.
