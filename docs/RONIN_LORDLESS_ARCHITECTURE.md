# Ronin — The lordless Spark Platform

> **Architectural note:** the tagline retains Spark because Spark is a first-class citizen and a major interoperability target. Ronin itself is **not Spark-bound**. The product architecture is engine-neutral by design.

## 1. Product principle: lordless by construction

Ronin must not require a particular execution engine, cloud, scheduler, catalog, table format, BI frontend, repository host, telemetry backend or AI provider.

Every major subsystem is expressed as a versioned capability contract with adapters. A deployment MAY use a single implementation or combine several. Unsupported capabilities MUST be reported deterministically; silent fallback that changes semantics is forbidden.

Core rule:

```
asset / notebook / pipeline / semantic model / dashboard
                    |
                    v
          Ronin logical contracts
                    |
     +--------------+--------------+
     |              |              |
 execution      operation      presentation
 adapters        adapters         adapters
```

## 2. Execution Plane

### 2.1 Canonical execution abstractions

Ronin defines an `EngineProfile` and `EngineCapabilities` contract. A profile declares:

- engine family and version;
- local, remote, serverless or distributed execution;
- supported languages and dataframe APIs;
- SQL dialect and pushdown capabilities;
- streaming/batch support;
- table formats;
- catalog integrations;
- cancellation, timeout and progress reporting;
- observability hooks;
- resource controls and cost metadata;
- isolation requirements;
- optional plan interchange support.

The platform planner chooses an engine only after capability resolution. Users may pin an engine or allow policy-based selection.

### 2.2 First-class engine targets

Adapters are planned for:

- Apache Spark local / Kubernetes / managed Spark;
- Spark Connect client and server targets;
- Databricks;
- Snowflake;
- Apache DataFusion, including native Rust services and Python bindings;
- Polars Python and Rust, eager and lazy/streaming modes;
- pandas for local/interoperability workloads;
- ClickHouse and native acceleration paths such as Gluten-compatible Spark execution;
- Apache Sail / Spark-compatible Rust execution where capability-compatible;
- cloud-managed engines on Azure, AWS and GCP;
- Kubernetes-native custom runtimes;
- future engines through the same adapter SDK.

An engine adapter MUST implement conformance tests for data types, null semantics, timestamps, cancellation, pagination, telemetry and declared pushdowns.

### 2.3 Arrow and portable plans

Apache Arrow is the preferred in-memory interchange format. Ronin SHOULD use portable logical-plan representations when semantics permit, including Substrait for engines that can consume or produce it.

Portable plans are an optimization and interoperability mechanism, not a requirement. Ronin retains its own versioned logical contract so a backend-specific planner may be used when necessary.

### 2.4 Dataframe interoperability

A notebook or asset may choose:

- Spark DataFrame;
- Spark Connect DataFrame;
- Polars DataFrame/LazyFrame;
- pandas DataFrame;
- DataFusion DataFrame/SQL;
- Arrow Table/RecordBatch;
- SQL against a remote engine.

Conversions MUST be explicit in the execution plan and observable. Ronin records conversion rows/bytes/time and warns when an operation forces materialization or driver-local execution.

## 3. Data Plane

### 3.1 Table formats

First-class table-format contracts:

- Delta Lake;
- Apache Iceberg;
- Apache Hudi;
- Parquet and Arrow IPC for file/interchange workloads;
- engine-native tables through adapters.

Capabilities include read, append, overwrite, merge/upsert, schema evolution, partition evolution, time travel, snapshot/version identification, compaction/maintenance and metadata/lineage extraction. Each adapter declares exactly which operations it supports.

### 3.2 Storage and catalogs

Storage adapters are independent of execution adapters. Planned targets include local/POSIX, S3-compatible stores, ADLS/Blob and GCS.

Catalog adapters are similarly decoupled. Assets refer to logical dataset identities; physical catalog identifiers are resolved by environment/profile.

## 4. Notebook and Development Plane

Notebooks are portable Ronin assets, not Spark notebooks.

A notebook declares one or more execution profiles and may switch kernels/engines at cell or session boundaries where supported. Spark Connect is a first-class remote-session mode.

Repository providers are pluggable and include at minimum:

- GitHub;
- GitLab;
- Bitbucket;
- Azure DevOps Repos;
- AWS CodeCommit-compatible Git endpoints and generic Git remotes.

Required repository capabilities:

- clone/fetch/pull/push;
- branch/tag/commit selection;
- diff and conflict visibility;
- asset-to-path mapping;
- optional PR/MR workflows;
- credential references only, never embedded secrets;
- audit events for mutations.

## 5. Agent and Prompt Engineering Plane

AI assistance is a platform subsystem, not a chat widget.

Supported scopes:

- cell/code assistant;
- notebook assistant;
- pipeline/job assistant;
- semantic-model assistant;
- dashboard/report assistant;
- project/workspace assistant;
- repository-aware code agent;
- full asset/project prompt engineering.

A `PromptProject` is versioned like source code and may contain system instructions, reusable prompt fragments, schemas, evaluation suites, examples, tool policies and asset context.

Agent actions MUST be tool-mediated, permission checked, auditable and bounded by workspace policy. Generated changes should be represented as proposed diffs before privileged mutations unless the caller explicitly grants autonomous write policy.

## 6. Presentation and Analytics Plane

Ronin dashboards are not limited to Power BI emulation. Power BI compatibility becomes one presentation adapter/profile.

The generic dashboard model supports:

- pages/canvases;
- charts and tables;
- KPI/cards;
- filters/slicers;
- cross-filter and brushing;
- drill actions;
- tooltips;
- text/media;
- custom visualization plugins;
- embedded notebook outputs;
- live/streaming tiles;
- accessibility metadata;
- themes and responsive layouts.

Plotting/rendering adapters MAY target Plotly, Vega/Vega-Lite, Apache ECharts, Matplotlib or other libraries without changing the canonical dashboard definition.

Dashboards can execute through any compatible Ronin query adapter, not only the semantic/DAX engine.

## 7. Scheduling and Durable Operations Plane

Scheduling is a platform primitive with adapter-based execution.

Canonical objects:

- `JobDefinition`;
- `TaskDefinition`;
- `Trigger`;
- `Schedule`;
- `Sensor` / event condition;
- `RetryPolicy`;
- `ConcurrencyPolicy`;
- `BackfillRequest`;
- `SLA` / `SLO`;
- `Run` / `TaskRun`;
- `Artifact`;
- `AlertPolicy`.

Trigger types include cron/calendar, interval, dataset update, lineage event, webhook, message/event bus, file/object arrival, metric threshold and manual/API invocation.

The orchestration layer MUST support DAG dependencies, dynamic fan-out/fan-in, retries with backoff, timeout, cancellation, idempotency keys, concurrency limits, priority, queues, backfills, catch-up policy, pause/resume and durable recovery.

Ronin should keep its orchestration contract independent from implementation. Candidate adapters include built-in lightweight scheduling, Temporal for durable workflows, Airflow-compatible execution and Dagster-compatible asset orchestration.

## 8. Monitoring, Alerts and SLOs

Monitoring is mandatory and cross-cutting.

Every run emits normalized runtime state and measurements:

- queue and startup latency;
- wall-clock and CPU time;
- memory;
- rows and bytes read/written/shuffled;
- spill;
- network I/O;
- cache hit/miss;
- engine-specific stages/operators;
- cost estimates and actual provider cost when available;
- retries/failures/cancellations;
- freshness and data-quality measurements.

Alert policies may target task/run failure, latency/SLO breach, freshness, quality, lineage breakage, cost/budget, anomalous resource use, missing telemetry, schema drift and security events.

Alert delivery is adapter-based: UI/inbox plus webhook, email, Slack/Teams or external incident systems where configured.

Deduplication, grouping, suppression, maintenance windows and acknowledgement state are part of the core model.

## 9. OpenTelemetry

OpenTelemetry is the default observability contract for traces, metrics and logs.

Ronin propagates trace context across:

control-plane request -> scheduler -> task -> engine session -> query/stage/operator -> storage/catalog calls

Every engine adapter MUST expose a mapping from native identifiers to Ronin span/resource attributes. Vendor-specific telemetry can coexist, but Ronin telemetry remains portable through OTLP exporters.

Required resource dimensions include workspace, project, asset, revision, run, task, engine profile, environment and tenant/security boundary.

High-cardinality identifiers are controlled through policy to avoid exploding metric series.

## 10. OpenLineage

OpenLineage is the preferred external lineage event contract.

Ronin maintains an internal lineage graph because not every source/engine exposes identical information. The graph records dataset, job, run, asset and column-level lineage when evidence exists.

Adapters translate engine-native lineage to the internal graph and emit OpenLineage events. Spark may use listener-based lineage integrations; non-Spark adapters emit equivalent events from planner/executor/catalog hooks.

Lineage evidence MUST record provenance and confidence. Inferred lineage is distinguished from engine-observed lineage.

## 11. Spark UI and DataFlint

For Spark-family execution, Ronin provides an enhanced Spark observability experience by default.

DataFlint integration is a Spark-specific observability adapter, not a platform dependency. Profiles may:

- expose a DataFlint-enhanced local/session UI;
- connect telemetry to a configured DataFlint server/MCP-compatible integration where available;
- fall back to native Spark UI while preserving Ronin OTEL/OpenLineage telemetry.

No DataFlint requirement applies to DataFusion, Polars, pandas, Snowflake, ClickHouse or other non-Spark engines.

## 12. Cost governance

Cost is a common platform dimension. Each execution adapter declares its cost model and confidence level.

Ronin supports:

- per-run/task/query estimates;
- budget policies by workspace/project/user/engine;
- soft warnings and hard limits;
- cost anomaly alerts;
- tags/chargeback dimensions;
- optimization recommendations;
- comparison of alternative eligible engines where sufficient evidence exists.

A cost estimate MUST never be presented as an actual billed value unless sourced from a provider billing interface.

## 13. Capability negotiation

Every adapter publishes machine-readable capabilities. Example groups:

```text
compute.batch
compute.streaming
compute.sql
compute.dataframe
compute.remote
compute.spark-connect
plan.substrait
format.delta.read
format.delta.write
format.iceberg.read
format.iceberg.write
format.hudi.read
format.hudi.write
telemetry.otel
lineage.openlineage
cancel.cooperative
cost.estimate
```

Plans are validated before execution. Missing required capabilities fail early with actionable diagnostics.

## 14. Security invariants

Engine neutrality must not weaken isolation.

- credentials are references resolved at execution time;
- adapters receive least-privilege scoped credentials;
- arbitrary host filesystem/network access is denied unless policy grants it;
- all privileged mutations are audited;
- user/tenant identity propagates to queries and caches;
- remote engines are subject to the same RLS/policy envelope where technically possible, otherwise the limitation is surfaced explicitly;
- execution plugins run under signed/approved adapter policies.

## 15. Status vocabulary

Documentation and UI use only:

- **implemented** — code and automated tests exist;
- **preview** — code exists but compatibility/operational gate is incomplete;
- **planned** — architecture/contract defined but implementation not complete;
- **unsupported** — intentionally unavailable with deterministic diagnostic.

This document defines the target architecture. It does **not** imply that every adapter listed above is implemented today.

## 16. Near-term construction order

1. Finish the current report/query roadmap without breaking its tests.
2. Introduce engine-neutral `EngineProfile`/capability contracts alongside the current Spark runtime.
3. Add table-format capability contracts and Iceberg/Hudi support.
4. Add Spark Connect as the first remote execution adapter.
5. Add DataFusion and Polars local adapters to prove non-Spark execution.
6. Introduce canonical task/run/schedule/trigger/alert contracts.
7. Instrument the control plane and runtimes with OpenTelemetry.
8. Introduce the internal lineage graph plus OpenLineage export.
9. Add DataFlint-enhanced Spark observability.
10. Generalize report definitions into dashboard/presentation contracts while preserving Power BI compatibility.
11. Add repository-provider and project/asset prompt-agent contracts.
12. Expand managed/cloud engines through conformance-tested adapters.
