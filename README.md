# Ronin

![Ronin logo](docs/assets/ronin-icon.png)

**Ronin: The lordless Spark Platform**

Ronin is evolving into an open-source, engine-neutral data platform. Spark remains a first-class runtime and interoperability target, but the architecture is deliberately not bound to Spark, a specific cloud, table format, scheduler, catalog, BI frontend, telemetry backend, or repository provider.

The target architecture includes pluggable execution for Spark/Spark Connect, DataFusion, Polars, pandas, ClickHouse and managed engines; Delta Lake, Apache Iceberg and Apache Hudi; notebooks and repository-backed development; generic dashboards and Power BI compatibility; batch and streaming; scheduling and durable workflows; OpenTelemetry, OpenLineage, alerting, SLOs and cost governance; and project/asset-scoped AI agents.

> Capability status is explicit: **implemented**, **preview**, **planned**, or **unsupported**. Architecture documents do not imply that every adapter is implemented today.

## Current implementation

The existing control plane provides workspaces, extensible items, portable notebooks, lakehouse namespaces, environment revisions, session lifecycle, optimistic saves, a web UI shell and Minikube manifests. `runtime/` defines the reproducible Spark/Jupyter execution-plane base.

Power BI compatibility is under active development on `codex/powerbi-emulation` following `POWERBI_EMULATION_SPEC.md` and `POWERBI_EMULATION_BUILD_PLAN_13_DAYS.md`. It is now treated as one presentation/semantic compatibility profile within the broader Ronin platform rather than the product boundary.

## Lordless architecture

See:

- `docs/RONIN_LORDLESS_ARCHITECTURE.md`
- `docs/RONIN_STREAMING_ARCHITECTURE.md`
- `docs/QUERY_ENGINE.md`
- `docs/REPORT_RUNTIME.md`

## Development

The code namespace is being migrated from the historical `fakebric` package to `ronin`. Until that migration commit lands, development commands still use the legacy module name.

```bash
pip install -r requirements.txt
uvicorn fakebric.app:app --reload
```

Local validation currently includes:

```bash
python -m pytest -q --cov=fakebric --cov-fail-under=75
python -m compileall -q fakebric tools tests
node --check fakebric/static/app.js
```

The exact implemented/partial/unsupported scope is maintained in `REQUIREMENTS_MATRIX.md`; unsupported capabilities are deliberately not advertised as available.
