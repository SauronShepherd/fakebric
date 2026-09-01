# Fakebrick

Fabric-inspired OSS data engineering workspace. The control plane includes workspaces, extensible items, portable notebooks, lakehouse namespaces, environment revisions, session lifecycle, optimistic saves, UI shell and Minikube manifests. `runtime/` defines the reproducible Spark/Jupyter execution-plane base.

```powershell
pip install -r requirements.txt
uvicorn fakebric.app:app --reload
```

## Power BI emulation MVP

Power BI emulation is under active development on `codex/powerbi-emulation` following `POWERBI_EMULATION_SPEC.md` and `POWERBI_EMULATION_BUILD_PLAN_13_DAYS.md`. The implementation is Linux-first and intentionally exposes only documented compatible behavior; unsupported capabilities must fail deterministically rather than silently emulating full Power BI/PBIX compatibility.

Day 1 established versioned `SemanticModel` and `Report` Pydantic contracts, generated JSON Schemas, lifecycle states (`Draft`, `Published`, `Archived`), standard error codes, optimistic concurrency through ETags, a migration registry, immutable revision snapshots and the `FAKEBRIC_POWERBI_EMULATION` feature flag.

Day 2 adds typed semantic entities (`Table`, `Column`, `Measure`, `DataSource`), the supported scalar types (`string`, `integer`, `decimal`, `boolean`, `date`, `datetime`, `binary`), workspace-confined CSV/JSONL/Parquet readers, registered Fakebrick-table reads, reviewable type inference, explicit conversion, missing-column/duplicate-name validation and deterministic row/null/min/max/cardinality profiles. Source credentials must be referenced with `credentialRef`; credential-like keys are rejected from inline source options.

```bash
FAKEBRIC_POWERBI_EMULATION=true python -m pytest -q \
  tests/test_semantic_model.py \
  tests/test_reports.py \
  tests/test_semantic_model_sources.py
```

Parquet support uses `pyarrow` from `requirements.txt`. File-backed sources are resolved under a caller-supplied workspace root; traversal and absolute paths outside that root are rejected.

## Validación local y Minikube

La comprobación reproducible del control plane es:

```powershell
python -m pytest -q --cov=fakebric --cov-fail-under=75
python -m compileall -q fakebric tools tests
node --check fakebric/static/app.js
```

Con Docker Desktop iniciado y el contexto `minikube` disponible, el flujo
completo es:

```powershell
./dev-up.ps1
./scripts/minikube-e2e.ps1
```

El E2E crea workspace, lakehouse, tabla Delta, filas, notebook y sesión; exige
que la ejecución termine en `COMPLETED` y que exista el resultado persistido.
En Windows, Docker Desktop debe exponer `dockerDesktopLinuxEngine`; como
alternativa, Minikube puede usar Hyper-V desde una consola elevada.

For a self-contained Minikube deployment, run `make dev-up` (override
`MINIKUBE_PROFILE` and `KUBE_CONTEXT` when using a different profile).
On Windows without GNU Make, run `./dev-up.ps1` instead.

Semantic Model and Report are represented as extensible item types. Their Power BI-compatible domain authoring is being added incrementally according to the 13-day plan; relationships, DAX, report rendering, RLS and later capabilities remain unsupported until their scheduled increments.

Environments are edited as `Draft` definitions and are published explicitly
with `POST /api/v1/items/{id}/publish` using a 64-hex SHA-256 OCI digest;
published revisions are immutable. The local Files/Tables facade is a
development contract and does not replace a production Delta/object-storage
provider.

The runtime image is intentionally separate from the API image. The session
controller and pod orchestration are included for local and Minikube use.
Before production, configure an external OIDC/JWKS provider, secret manager,
immutable image digests, durable object storage, monitoring and native-engine
execution evidence as described in `PRODUCTION_CHECKLIST.md`.

The exact implemented/partial/unsupported scope is maintained in
`REQUIREMENTS_MATRIX.md`; unsupported capabilities are deliberately not
advertised as available.
