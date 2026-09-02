# Ronin Visual Pipelines & Benchmark Lab

**Status:** planned architecture contract  
**Project:** Ronin — The lordless Spark Platform  
**Principle:** Spark is first-class, but no pipeline, runtime, benchmark, observability or AI contract is Spark-bound.

## 1. Objective

Ronin should let a user design a data pipeline once as an engine-neutral semantic graph, validate its portability, choose one execution profile or compare several, and obtain reproducible correctness, performance, resource and cost evidence.

The visual editor should evolve from the architecture already present in SDP Studio rather than replacing it. SDP Studio already contains a provider-neutral intermediate representation, a typed visual DAG, capability/runtime concepts, source maps, runtime adapters, run comparison, scheduling, plugin contracts and Python/SQL backends. Ronin should generalize these boundaries so Spark becomes one compiler/runtime family among several.

A primary workflow is:

```text
Visual graph
    |
    v
Ronin Pipeline IR
    |
    +--> portability + semantic validation
    |
    +--> compile/execute on one ExecutionProfile
    |
    +--> Benchmark Lab --> profile A
                          --> profile B
                          --> profile C
                          --> profile D
                                   |
                                   v
                     normalized evidence + report
```

## 2. Keep independent dimensions independent

The central runtime abstraction is composition rather than a large enum of prebuilt engines.

### 2.1 EngineProfile

Represents the logical execution engine and engine capabilities.

Examples:

- Apache Spark Classic;
- Spark Connect;
- Apache Sail;
- Apache DataFusion;
- Polars;
- pandas;
- ClickHouse;
- Snowflake;
- Databricks compute;
- future engines through an adapter SDK.

An `EngineProfile` declares, at minimum:

- engine family;
- engine version constraint and resolved version;
- batch/streaming support;
- SQL/DataFrame/plan capabilities;
- supported logical operators;
- supported data/table formats;
- null, decimal, timestamp and timezone semantics;
- cancellation/progress support;
- telemetry facilities;
- native plan inspection capabilities;
- deployment compatibility;
- language/runtime compatibility constraints.

### 2.2 LanguageRuntimeProfile

Language runtime is independent from engine.

Python properties include:

- implementation (`cpython` initially, extensible);
- requested and resolved Python version;
- architecture;
- environment manager adapter (`venv`, `uv`, Conda/Mamba-compatible, container-only, remote-managed);
- lockfile/environment digest;
- wheel ABI/platform tags;
- dependency set and hashes;
- environment variables by reference/policy;
- free-threaded/subinterpreter capability metadata when relevant;
- diagnostic agent configuration.

JVM properties include:

- requested and resolved Java/JDK version;
- JDK distribution/vendor metadata;
- architecture;
- bytecode target requirements;
- classpath/module-path digest;
- JVM flags;
- GC selection and effective settings;
- Java agents;
- memory/container awareness settings;
- diagnostic agent configuration.

Rust/native properties may include:

- toolchain/version metadata;
- target triple;
- CPU feature policy;
- native library digest;
- allocator metadata;
- debug/profiling capabilities.

Ronin MUST NOT globally claim that every Python or Java version works with every engine. Compatibility is resolved by the selected engine/runtime adapters before execution and is recorded as evidence.

### 2.3 AcceleratorProfile

Acceleration is orthogonal to engine identity.

Examples include:

- none / reference execution;
- Apache Gluten-compatible native Spark acceleration;
- Photon when the selected Databricks profile exposes it;
- engine-native vectorization/JIT configuration;
- specialized rewrites such as `zingg-native` for eligible Zingg workloads;
- future native execution plugins.

This is important for fair comparisons such as the same Spark/PySpark version with and without native acceleration.

An accelerator declares:

- compatibility constraints;
- whether it changes only physical execution or may change logical behavior;
- activation evidence;
- native/fallback coverage evidence where available;
- configuration digest;
- fallback policy (`allow`, `warn`, `strict`);
- telemetry fields.

### 2.4 DeploymentProfile

Represents where/how execution happens:

- local process;
- local container;
- Kubernetes;
- remote Spark Connect;
- Databricks serverless/dedicated profiles;
- managed cloud services;
- remote SQL engine;
- custom runner adapter.

It includes resource requests/limits or provider sizing, region, storage/network placement, isolation policy, image/runtime digest, credentials by reference, and cost-provider metadata.

### 2.5 ExecutionProfile

An executable target composes the dimensions:

```text
ExecutionProfile =
    EngineProfile
  + LanguageRuntimeProfile(s)
  + AcceleratorProfile
  + DeploymentProfile
  + DataAccessProfile
  + ObservabilityProfile
```

A profile has a stable logical ID and an immutable resolved manifest for every run.

Example conceptual profiles:

```yaml
profiles:
  - name: sail-rust
    engine: sail
    language: rust
    accelerator: none
    deployment: kubernetes

  - name: spark4-reference
    engine: spark
    engineVersion: "4.x"
    language:
      java: "<qualified-version>"
      python: "<qualified-version>"
    accelerator: none
    deployment: kubernetes

  - name: pyspark35-native
    engine: spark
    engineVersion: "3.5.x"
    language:
      python: "<qualified-version>"
      java: "<qualified-version>"
    accelerator: gluten
    deployment: kubernetes

  - name: databricks-serverless
    engine: databricks
    deployment: serverless
    accelerator: provider-native
```

The placeholders deliberately require qualification instead of assuming a language/engine compatibility matrix.

## 3. Ronin Pipeline IR

### 3.1 Relationship to SDP Studio

SDP Studio already has a provider-neutral IR and a visual graph source of truth. Ronin should preserve the good separation and evolve it into a versioned `RoninPipelineIR` rather than coupling Ronin to generated `pyspark.pipelines` code.

The visual editor becomes a client/editor of the canonical Ronin Pipeline IR.

The IR MUST contain semantics, not implementation API calls.

Good IR operation:

```text
Filter(input, predicate)
```

Bad canonical IR operation:

```text
pyspark.sql.DataFrame.filter(...)
```

### 3.2 Core IR entities

Proposed entities:

- `Pipeline`;
- `Node`;
- `Port`;
- `Edge`;
- `Expression`;
- `DatasetRef`;
- `Source`;
- `Sink`;
- `Schema`;
- `ParameterRef`;
- `SecretRef`;
- `DataQualityRule`;
- `StreamingSemantics`;
- `SourceLocation`;
- `CapabilityRequirement`;
- `SemanticConstraint`;
- `EngineOverride`.

Every node receives a stable ID. Generated source maps and runtime telemetry map back to those IDs.

### 3.3 Generic operator contract

Each generic operator declares:

- input/output port contracts;
- logical schema transformation;
- batch/streaming support;
- deterministic/non-deterministic behavior;
- required capabilities;
- semantic requirements;
- expression dialect requirements;
- partition/order requirements;
- statefulness;
- lineage behavior;
- quality/test hooks;
- compiler support matrix.

Examples:

- read table/file/stream;
- select/project;
- filter;
- derive expression;
- cast/rename;
- join;
- aggregate;
- window;
- deduplicate;
- sort/top-N;
- explode/unnest;
- union;
- repartition/coalesce as a physical hint rather than universal semantic requirement;
- watermark/windowed streaming operations;
- CDC merge/upsert;
- write table/file/stream;
- ML/entity-resolution extension nodes through plugins.

### 3.4 Expression model

Expressions should use a portable expression AST wherever practical. Raw Python, SQL, Scala, Java or Rust snippets are escape hatches, not the canonical representation.

A node with engine-specific code is legal but carries portability metadata. Benchmark Lab may:

- reject targets that cannot compile the node;
- compare only compatible targets;
- require an alternative implementation attached to the node;
- mark the result as non-equivalent if semantics cannot be proven/tested.

### 3.5 Compiler contract

A `PipelineCompiler` consumes immutable Pipeline IR plus an `ExecutionProfile` and returns:

- generated artifact(s) or remote plan;
- source map from generated artifacts to node IDs;
- resolved capability decisions;
- optimization/translation diagnostics;
- portability warnings;
- semantic caveats;
- artifact hashes;
- executable launch contract.

Initial compiler targets should prove different architectural families rather than merely different Spark distributions:

1. Spark/PySpark compiler;
2. Spark Connect compiler/client path;
3. DataFusion/Rust or Python compiler;
4. Polars compiler;
5. Sail/Spark-compatible execution adapter;
6. generic SQL compiler with dialect adapters;
7. Databricks remote execution profile.

## 4. Visual Studio integration

Ronin should reuse/generalize SDP Studio capabilities:

- drag/drop typed DAG editor;
- operator palette and plugin discovery;
- inspector-driven node configuration;
- schema inspection;
- batch/streaming graph support;
- validation/problem codes;
- bounded node preview;
- source maps;
- run history;
- run comparison;
- Debug Lab concepts;
- Git-native project representation;
- scheduling UI;
- runtime profile selection;
- collaboration and optimistic revisions.

The Ronin UI should add an engine/runtime selector that shows portability before execution:

```text
Spark 4                Compatible
Sail                   Compatible
DataFusion             Compatible with 1 translation warning
Polars                  Incompatible: stateful streaming node N18
Databricks Serverless   Compatible
```

This capability view comes from compiler/adapter manifests, not hard-coded UI rules.

## 5. Benchmark Lab

### 5.1 Purpose

Benchmark Lab executes the same immutable logical pipeline and data snapshot using several resolved `ExecutionProfile`s and produces a reproducible comparison.

The initial UX may allow up to four active comparison profiles because four is visually usable and places a practical bound on cost/concurrency. The underlying contract SHOULD support an administrator-configurable maximum rather than encoding four into the data model.

### 5.2 BenchmarkDefinition

```text
BenchmarkDefinition
  id
  pipelineRevision
  pipelineIRHash
  datasetSnapshotRefs[]
  profiles[]
  warmupPolicy
  repetitionPolicy
  orderingPolicy
  cachePolicy
  correctnessPolicy
  resourcePolicy
  timeoutPolicy
  costBudget
  metricsPolicy
  diagnosticsPolicy
  objective
  reportPolicy
```

### 5.3 Reproducibility manifest

Every benchmark captures:

- Pipeline IR content hash;
- generated plan/artifact hashes for every target;
- source repository commit where relevant;
- exact engine/runtime/language versions;
- dependency locks;
- container image digests;
- JDK/Python/Rust details;
- accelerator state and evidence;
- machine/node architecture and relevant CPU features;
- requested/effective resource limits;
- cloud provider/service/region/runtime identifier where available;
- dataset snapshots/versions and input size;
- table-format snapshots;
- relevant configuration after secret redaction;
- benchmark methodology version;
- timestamps and environment IDs.

Without this manifest, a run is an observation, not a reproducible benchmark.

## 6. Correctness before speed

Ronin MUST NOT declare a performance winner before evaluating semantic comparability.

Each profile goes through a correctness/parity gate appropriate to the pipeline:

- schema equivalence;
- row count where meaningful;
- stable aggregate checks;
- deterministic row/content hashes for bounded outputs;
- key-based differential comparison;
- null/NaN behavior;
- decimal tolerances;
- timestamp/timezone behavior;
- ordering only where ordering is semantically required;
- floating-point tolerance configured explicitly;
- expected data-quality constraints;
- streaming output/window invariants for streaming benchmarks.

A profile may be marked:

- `PARITY_CONFIRMED`;
- `PARITY_WITH_TOLERANCE`;
- `SEMANTIC_DIFFERENCE`;
- `NOT_COMPARABLE`;
- `FAILED`.

Performance charts visually distinguish non-comparable runs and never silently rank them with valid runs.

## 7. Benchmark methodology

### 7.1 Warm-up and repetition

A benchmark policy supports:

- explicit warm-up runs;
- measured repetitions;
- minimum/maximum repetitions;
- optional confidence/stability stopping rule;
- cold-start lane;
- warm-runtime lane;
- cold-cache lane;
- warm-cache lane.

Cold and warm results are separate metrics and are never averaged together.

### 7.2 Ordering bias

Profile execution SHOULD be randomized or interleaved across repetitions when infrastructure permits:

```text
A1 B1 C1 D1
C2 A2 D2 B2
B3 D3 A3 C3
```

This reduces bias from cluster load, network conditions, provider variance and thermal/cache state.

### 7.3 Resource fairness

Benchmark Lab records both requested and effective resources.

It supports two comparison modes:

- **normalized-resource:** attempt comparable CPU/memory/executor capacity;
- **real-world-profile:** compare the actual service/profile the user would choose, including serverless differences.

Reports clearly identify which mode was used. Databricks Serverless versus a fixed local/Kubernetes engine, for example, should not be described as a controlled hardware comparison unless resources are demonstrably equivalent.

## 8. Metrics

### 8.1 Common metrics

Normalized metrics should include where evidence exists:

- end-to-end wall time;
- queue/provisioning/startup time;
- compile/planning time;
- execution time;
- input/output rows;
- bytes read/written;
- throughput;
- CPU time/utilization;
- peak and time-series memory;
- disk I/O;
- network I/O;
- shuffle bytes;
- spill bytes;
- task/operator/stage counts;
- retries/failures;
- cache behavior;
- p50/p90/p95/p99 across repetitions where sample size makes the statistic meaningful;
- provider cost or cost estimate with provenance/confidence;
- energy/carbon data only if evidence is actually available and attributable.

### 8.2 JVM metrics

With JVM evidence available:

- heap/non-heap usage;
- allocation pressure where measurable;
- GC count/time/pause distribution;
- thread state/count;
- class loading;
- serialization/I/O observations;
- executor/JVM lifecycle;
- engine-specific stages/tasks;
- JIT/native observations where a provider exposes reliable evidence.

### 8.3 Python metrics

With Python evidence available:

- interpreter identity/version;
- process CPU/memory;
- Python execution hotspots when policy enables them;
- callback/hook overhead;
- Python/JVM boundary evidence for PySpark where measurable;
- coverage gaps explicitly recorded;
- subinterpreter/free-threaded metadata where relevant.

### 8.4 Accelerator metrics

An accelerator adapter should report:

- requested activation;
- verified activation;
- eligible operations;
- accelerated/native operations;
- fallback operations;
- strictness mode;
- accelerator-specific planning/execution evidence.

No report should say “native execution enabled” merely because a configuration flag was set.

## 9. Diagnostics integrations

### 9.1 MadLava

MadLava integrates as a JVM diagnostics provider.

Ronin can inject the Java agent into local/container/Kubernetes JVM profiles where policy allows it. For managed runtimes that prohibit agents, the capability is reported unavailable and Ronin uses provider-native metrics instead.

Normalized MadLava evidence can enrich:

- JVM runtime comparison;
- GC/memory analysis;
- process-local I/O/serialization evidence;
- executor lifecycle evidence;
- Spark-specific observation when the selected MadLava version explicitly supports the Spark/JDK lane.

MadLava's own compatibility declaration is authoritative; Ronin must not infer Spark 4 support from generic JVM support.

### 9.2 MadMamba

MadMamba integrates as a Python/PySpark diagnostic provider.

Its per-interpreter runtime model maps naturally to Ronin's `LanguageRuntimeProfile`: interpreter identity, monitoring coverage and evidence stay explicit for each Python interpreter rather than being collapsed into process-global truth.

Benchmark ingestion should preserve MadMamba evidence IDs and accuracy/coverage indicators.

### 9.3 zingg-native

`zingg-native` integrates in two ways:

1. an `AcceleratorProfile` / compatibility provider for supported Zingg workloads on Databricks native paths;
2. a benchmark workload/plugin for entity-resolution experiments.

This allows comparisons such as reference Zingg versus native-rewrite/Photon/Serverless configurations while retaining the real Zingg user-facing semantics.

The adapter should ingest strict/fallback evidence and provider query-history metrics where available instead of assuming rewrite coverage.

### 9.4 DataFlint and engine-native diagnostics

DataFlint remains a Spark-specific diagnostics provider. Spark UI/event logs, DataFlint, MadLava, provider metrics and OpenTelemetry can all contribute evidence to the same normalized benchmark run without becoming requirements for non-Spark engines.

DataFusion/Polars/Sail/ClickHouse and other engines get their own diagnostics adapters.

## 10. OpenTelemetry integration

A benchmark is a top-level OpenTelemetry trace.

Suggested hierarchy:

```text
benchmark.run
  profile.run[sail]
    repetition[1]
      compile
      provision
      pipeline.node[N1]
      pipeline.node[N2]
  profile.run[spark4]
  profile.run[pyspark35-native]
  profile.run[databricks-serverless]
```

Span/resource attributes include benchmark ID, pipeline revision/hash, execution profile ID, engine/runtime versions, node IDs and dataset snapshot IDs subject to cardinality policy.

Metrics/logs/traces from engine adapters, MadLava/MadMamba bridges and cloud providers are correlated using run/profile/repetition IDs.

## 11. OpenLineage integration

Every profile execution emits lineage evidence for the same logical Pipeline IR.

Ronin records both:

- logical lineage derived from Pipeline IR;
- observed physical lineage from the execution engine/provider.

Differences become diagnostics. This is useful for discovering that a compiler target materialized or bypassed datasets differently even when final outputs match.

## 12. Benchmark report

A benchmark report is a versioned Ronin asset and must include raw evidence references so charts are auditable.

Suggested report sections:

- executive comparison;
- correctness/parity gate;
- methodology and reproducibility manifest;
- end-to-end latency distributions;
- cold vs warm behavior;
- throughput;
- startup/provisioning overhead;
- CPU/memory timelines;
- GC/JVM diagnostics;
- Python diagnostics;
- I/O/shuffle/spill;
- node/stage/operator heat map;
- speedup relative to selected baseline;
- cost by run and projected workload cost where justified;
- cost-vs-latency Pareto chart;
- accelerator/native/fallback evidence;
- errors/retries/skew/anomalies;
- engine-specific appendix;
- exact resolved profiles and software versions.

Chart rendering is presentation-adapter based (Plotly/Vega-Lite/ECharts/etc.). Raw benchmark results remain independent from a charting library.

## 13. Objectives and ranking

A single universal winner is misleading. Users select an objective:

- fastest;
- cheapest;
- lowest startup latency;
- highest throughput;
- lowest peak memory;
- best cost/performance;
- best SLO compliance;
- custom weighted objective.

A profile is eligible for ranking only if the correctness policy considers it comparable.

The report should also expose the Pareto frontier so users can see profiles that are not dominated across selected dimensions.

## 14. Example four-way benchmark workflow

A user designs `customer-360` once in the visual editor.

The editor validates generic operations and then the user selects four profiles, for example:

```text
A  Sail / Rust
B  Spark 4 reference
C  PySpark 3.5 + native accelerator
D  Databricks Serverless
```

Ronin then:

1. freezes Pipeline IR and dataset snapshots;
2. checks compiler/capability compatibility for all profiles;
3. generates or submits target plans;
4. runs correctness qualification;
5. executes warmups;
6. executes measured repetitions in randomized/interleaved order;
7. collects OpenTelemetry + engine/provider + optional diagnostic evidence;
8. emits OpenLineage events;
9. normalizes metrics without destroying raw evidence;
10. computes statistical summaries and objective rankings;
11. renders the benchmark report;
12. preserves all resolved manifests and evidence hashes for later comparison.

If the user wants Spark 3.5 both with and without a native accelerator, those are two separate `ExecutionProfile`s and can occupy two of the comparison slots.

## 15. Benchmark regression monitoring

Benchmark suites can be ordinary scheduled/triggered Ronin jobs.

Triggers may include:

- nightly/weekly schedule;
- pull request/commit;
- pipeline revision;
- engine/runtime version change;
- container image change;
- dependency lock change;
- accelerator version change;
- representative dataset snapshot refresh;
- manual/API request.

Alerts can fire for:

- correctness/parity regression;
- runtime regression above configured threshold;
- cost regression;
- memory regression;
- startup latency regression;
- throughput regression;
- new engine fallback/non-native path;
- missing telemetry;
- benchmark instability/variance increase.

Thresholds should support both absolute and relative values plus minimum effect size to reduce noisy alerts.

## 16. AI / Omnigent integration

Ronin should integrate Omnigent as an optional open-source agent meta-harness rather than building a proprietary agent runtime.

### 16.1 Boundary

Ronin owns:

- data-platform identity and authorization;
- workspace/project/asset permissions;
- Pipeline IR;
- engine/runtime adapters;
- data credentials and secret references;
- benchmark evidence;
- lineage/governance;
- audit log;
- mutation policy.

Omnigent owns/coordinates agent harness sessions according to its supported agent/model/sandbox interfaces.

### 16.2 Ronin AgentProvider contract

An `OmnigentAgentProvider` should expose operations such as:

- create/resume/cancel agent session;
- select configured harness/model through provider configuration;
- attach project/repository scope;
- stream events/messages;
- request a tool action;
- surface approval/elicitation requests;
- retrieve session artifacts/diffs;
- expose provider capabilities/version.

The adapter should be API-versioned and contract-tested against supported Omnigent releases rather than depending on internal Python imports.

### 16.3 Ronin tools for agents

Ronin can expose MCP/tool endpoints for scoped actions such as:

- inspect Pipeline IR;
- inspect schema/profile/lineage;
- validate pipeline portability;
- compile a target without running it;
- inspect benchmark evidence;
- compare benchmark runs;
- explain regression/anomaly evidence;
- propose a graph optimization;
- create a proposed pipeline diff;
- inspect repository diff;
- run permitted tests/benchmarks;
- read diagnostics;
- query documentation/catalog metadata.

Agents must not receive unrestricted underlying cloud/data credentials when a scoped Ronin tool can perform the operation instead.

### 16.4 Benchmark AI workflows

Useful agent workflows include:

- explain why one engine is faster;
- identify startup vs execution bottleneck;
- find node-level performance regressions;
- propose portable rewrites;
- detect accidental engine-specific constructs;
- compare cost/performance tradeoffs;
- recommend which profile meets an SLO/budget;
- generate a human-readable benchmark summary from evidence;
- challenge another agent's diagnosis using a second harness/model;
- propose an experiment but require user/policy approval before paid remote execution.

AI conclusions are labelled as inference and link to measured evidence. They do not overwrite measured facts.

## 17. Version/runtime management

Ronin needs a `Runtime Resolver` and immutable runtime manifests.

Resolution flow:

```text
requested profile
  -> adapter compatibility constraints
  -> dependency/runtime solver
  -> resolved language + engine + native dependencies
  -> immutable manifest
  -> build/probe
  -> qualification
  -> READY or deterministic incompatibility
```

Runtime images/environments should be cacheable by content digest.

Qualification tests include:

- process starts;
- exact versions match manifest;
- basic Arrow/data exchange;
- filesystem/object-store access policy;
- table-format capability probe;
- minimal query/DataFrame operation;
- cancellation;
- telemetry emission;
- diagnostic agent compatibility if enabled;
- no secret material persisted in manifest.

The UI should make multiple Java/Python versions easy to define without implying all Cartesian combinations are valid.

## 18. Security and cost controls

Benchmark Lab can trigger expensive remote compute, so it requires explicit controls:

- preflight estimated cost where the provider can supply one;
- per-benchmark and workspace budgets;
- maximum active profiles and repetitions;
- maximum wall time;
- concurrency limits;
- remote execution permission;
- credential references only;
- egress/data-residency checks;
- redaction before storing commands/configuration;
- audit event for profile creation and every paid execution;
- cancellation propagation;
- orphan-resource cleanup.

A benchmark that exceeds budget policy stops according to configured hard/soft policy and records the reason.

## 19. Conformance tests

Every compiler/engine adapter should pass a common suite covering:

- schema/type mapping;
- null semantics;
- decimal behavior;
- timestamp/timezone behavior;
- filters/projections;
- joins;
- aggregations;
- window functions if declared;
- deterministic hash comparison;
- read/write formats declared by capability;
- error normalization;
- cancellation;
- timeout;
- metrics normalization;
- OpenTelemetry correlation;
- OpenLineage emission;
- source-map/node correlation;
- resource manifest evidence;
- streaming semantics separately when declared.

An adapter advertises only capabilities that have a qualification path.

## 20. Construction plan

### Phase A — contracts

- version `RoninPipelineIR`;
- define `EngineProfile`, `LanguageRuntimeProfile`, `AcceleratorProfile`, `DeploymentProfile` and composed `ExecutionProfile`;
- define compiler and diagnostics provider interfaces;
- define benchmark schemas and evidence model;
- define portability/error codes.

### Phase B — SDP Studio bridge

- map existing SDP Studio provider-neutral IR to/from Ronin Pipeline IR;
- preserve stable node IDs and source maps;
- make runtime/engine selection capability-driven;
- preserve existing Spark behavior as a compatibility backend;
- ensure legacy SDP Studio projects import deterministically.

### Phase C — multi-language runtime resolver

- Python runtime resolver/environment manifests;
- JDK resolver/manifests;
- native/Rust profile metadata;
- OCI build/cache integration;
- compatibility probes and qualification matrix.

### Phase D — non-Spark proof

- DataFusion compiler/runner;
- Polars compiler/runner;
- compare with existing Spark path using the same IR;
- add Sail adapter when its compatibility contract is pinned/tested.

### Phase E — Benchmark Lab MVP

- up to four profiles in initial UI;
- immutable pipeline/data snapshot;
- parity gate;
- warmup/repetitions/interleaving;
- normalized metrics/evidence store;
- baseline speedup and latency/resource charts;
- reproducibility manifest.

### Phase F — diagnostics

- MadLava JVM provider;
- MadMamba Python provider;
- DataFlint/Spark provider;
- `zingg-native` accelerator/workload provider;
- provider-native Databricks/cloud metrics;
- OTel correlation.

### Phase G — cost and statistical reporting

- cost provenance;
- confidence/variance reporting;
- cost-vs-performance Pareto analysis;
- regression history and scheduled suites;
- alerts/SLO integration.

### Phase H — Omnigent

- versioned Omnigent provider adapter;
- scoped Ronin MCP/tools;
- project/pipeline/benchmark context bundles;
- approval-mediated proposed graph/code changes;
- multi-agent benchmark diagnosis/evaluation workflows.

## 21. Release gates

Benchmark Lab cannot be called production-ready until:

- at least two materially different engine families execute the same Pipeline IR successfully;
- correctness gating detects intentional semantic differences;
- all displayed metrics have provenance;
- repeated-run statistics are tested;
- cold/warm states cannot be accidentally combined;
- failed/non-comparable runs cannot win a ranking;
- runtime manifests are immutable and reproducible;
- cancellation and resource cleanup are qualification-tested;
- secrets are redacted from persisted benchmark evidence;
- cost values distinguish estimates from provider-billed actuals;
- OTel correlations and lineage IDs survive cross-engine execution;
- benchmark report charts can be regenerated from stored raw normalized evidence;
- diagnostic providers can be absent without breaking benchmark execution;
- an engine adapter cannot claim an unqualified capability.

## 22. Status boundary

This document defines the target architecture. Existing SDP Studio, MadLava, MadMamba, `zingg-native` and Omnigent capabilities are integration inputs; their presence does not make the corresponding Ronin adapters implemented. Ronin UI and documentation must continue to distinguish `implemented`, `preview`, `planned` and `unsupported` capabilities.
