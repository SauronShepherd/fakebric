# Fakebrick

Fabric-inspired OSS data engineering workspace. The control plane includes workspaces, extensible items, portable notebooks, lakehouse namespaces, environment revisions, session lifecycle, optimistic saves, UI shell and Minikube manifests. `runtime/` defines the reproducible Spark/Jupyter execution-plane base.

```powershell
pip install -r requirements.txt
uvicorn fakebric.app:app --reload
```

## Power BI emulation MVP

Power BI emulation is under active development on `codex/powerbi-emulation` following `POWERBI_EMULATION_SPEC.md` and `POWERBI_EMULATION_BUILD_PLAN_13_DAYS.md`. The implementation is Linux-first and intentionally exposes only documented compatible behavior; unsupported capabilities must fail deterministically rather than silently emulating full Power BI/PBIX compatibility.

Day 1 established versioned `SemanticModel` and `Report` Pydantic contracts, generated JSON Schemas, lifecycle states (`Draft`, `Published`, `Archived`), standard error codes, optimistic concurrency through ETags, a migration registry, immutable revision snapshots and the `FAKEBRIC_POWERBI_EMULATION` feature flag.

Day 2 added typed semantic entities (`Table`, `Column`, `Measure`, `DataSource`), supported scalar types, workspace-confined CSV/JSONL/Parquet readers, registered Fakebrick-table reads, reviewable type inference, explicit conversion and deterministic profiles.

Day 3 adds typed relationships with `one-to-one`, `one-to-many` and `many-to-many` cardinalities, `single`/`both` filter direction, active/inactive relationships, primary-key/date-table metadata, explicit semantic dependencies and a structured model validator. `POST /api/v1/models/{id}/validate` returns severity, code, location, suggested fix, dependency graph and filter graph. DAX expressions are not parsed yet; expression-derived dependencies remain reserved for the Day 4 parser.

```bash
FAKEBRIC_POWERBI_EMULATION=true python -m pytest -q \
  tests/test_semantic_model.py \
  tests/test_reports.py \
  tests/test_semantic_model_sources.py \
  tests/test_semantic_model_validation.py
```

Parquet support uses `pyarrow` from `requirements.txt`. File-backed sources are resolved under a caller-supplied workspace root; traversal and absolute paths outside that root are rejected.

## Validación local y Minikube

La comprobación reproducible del control plane es:

```powershell
python -m pytest -q --cov=fakebric --cov-fail-under=75
python -m compileall -q fakebric tools tests
node --check fakebric/static/app.js
```

Con Docker Desktop iniciado y el contexto `minikube` disponible, el flujo completo es:

```powershell
./dev-up.ps1
./scripts/minikube-e2e.ps1
```

El E2E crea workspace, lakehouse, tabla Delta, filas, notebook y sesión; exige que la ejecución termine en `COMPLETED` y que exista el resultado persistido.

For a self-contained Minikube deployment, run `make dev-up` (override `MINIKUBE_PROFILE` and `KUBE_CONTEXT` when using a different profile). On Windows without GNU Make, run `./dev-up.ps1` instead.

Semantic Model and Report are represented as extensible item types. Relationship/model validation is now partial; DAX, report rendering, RLS and later capabilities remain unsupported until their scheduled increments.

The exact implemented/partial/unsupported scope is maintained in `REQUIREMENTS_MATRIX.md`; unsupported capabilities are deliberately not advertised as available.
