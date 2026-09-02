# Ronin Streaming Architecture

Ronin treats streaming as a first-class execution and data plane, independent from Spark.

## Principles

- Streaming is engine-neutral and connector-neutral.
- Batch and streaming share the same asset, lineage, observability, security, scheduling and governance contracts where semantics permit.
- Delivery guarantees are explicit capabilities, never implied.
- Event-time semantics, watermarks, checkpoints and replay are part of the logical contract.
- Stateful operations must declare state backend, retention, recovery and scaling behavior.
- Every connector and engine adapter exposes conformance-tested capabilities.

## Canonical streaming objects

- `StreamDefinition`
- `StreamSource`
- `StreamSink`
- `StreamSchema`
- `StreamCheckpoint`
- `StreamStatePolicy`
- `WatermarkPolicy`
- `WindowDefinition`
- `DeliveryGuarantee`
- `ReplayPolicy`
- `DeadLetterPolicy`
- `StreamingRun`
- `StreamingMetrics`

## Engine targets

Streaming execution may be provided by adapters such as:

- Spark Structured Streaming;
- Databricks streaming runtimes;
- Apache Flink;
- Apache Beam runners;
- Kafka Streams-compatible applications;
- RisingWave/Materialize-style incremental SQL engines where supported;
- cloud-managed streaming engines on Azure, AWS and GCP;
- future Rust-native engines through the same adapter SDK.

DataFusion, Polars and pandas remain valid batch/local dataframe engines. They must not be advertised as event-stream engines unless a concrete adapter implements the required streaming contract.

## Streaming systems and transport adapters

Planned source/sink adapters include:

- Apache Kafka;
- Redpanda;
- Apache Pulsar;
- AWS Kinesis;
- Azure Event Hubs;
- Google Cloud Pub/Sub;
- NATS / JetStream;
- RabbitMQ where queue semantics are sufficient;
- HTTP/webhook ingestion;
- object-store/file arrival streams;
- change-data-capture streams, including Debezium-compatible envelopes;
- table change feeds when supported by Delta/Iceberg/Hudi or engine-native formats.

Transport and engine are separate choices. For example, a Kafka source may feed Spark, Flink or another compatible execution adapter without changing the logical stream definition.

## Semantics and guarantees

A streaming adapter must declare support for:

- processing time and event time;
- tumbling, sliding and session windows;
- watermarks and allowed lateness;
- ordered/unordered inputs;
- at-most-once, at-least-once and exactly-once/effectively-once semantics;
- idempotent sink writes;
- checkpointing and restart recovery;
- replay from offsets/timestamps/snapshots;
- backpressure;
- stateful aggregations and joins;
- deduplication;
- schema evolution;
- dead-letter routing;
- pause/resume/cancel;
- elastic rescaling where supported.

If an end-to-end guarantee depends on both source and sink, Ronin reports the weakest composed guarantee rather than the engine-local guarantee.

## Schema and contracts

Schema management is adapter-based. Ronin should integrate with schema registries and catalog contracts while retaining a canonical logical schema.

Supported compatibility policies should include backward, forward and full compatibility where the underlying registry supports them.

Schema drift must generate observable events and may trigger policy actions, alerts or automatic quarantine.

## CDC

CDC is a first-class streaming pattern. The canonical change envelope carries:

- operation type;
- source identifier;
- source position/offset;
- event/commit timestamp;
- before/after images when available;
- transaction identifier when available;
- schema version;
- provenance metadata.

Debezium-compatible envelopes are a priority interoperability target, but Ronin's internal contract is provider-neutral.

## Table sinks

Delta Lake, Apache Iceberg and Apache Hudi adapters should expose streaming sink/source capabilities independently.

Where supported, Ronin should provide:

- append streaming writes;
- upsert/merge CDC writes;
- checkpoint-linked commits;
- snapshot/commit lineage;
- compaction/clustering/maintenance policies;
- late-data handling;
- schema evolution controls.

## Scheduling and lifecycle

Long-running streaming jobs are managed through the same Operations Plane as batch jobs, with streaming-specific lifecycle states and policies:

- deploy/start;
- healthy/degraded/recovering;
- drain;
- pause/resume;
- restart from checkpoint;
- restart from explicit offset/snapshot;
- rolling upgrade;
- stop/cancel.

Schedules may start/stop streams, but event-driven streaming jobs may also be continuously active.

## Observability

OpenTelemetry is the default telemetry contract.

Streaming-specific metrics include:

- input/output records per second;
- bytes per second;
- consumer lag/backlog;
- watermark delay;
- end-to-end event latency;
- processing latency;
- checkpoint duration/size/failures;
- state size;
- late/dropped records;
- retry/redelivery rate;
- DLQ volume;
- backpressure indicators;
- rebalance/restart count;
- per-partition/shard skew;
- cost rate and projected monthly cost where available.

Trace context should propagate through message metadata when the transport permits it.

## Lineage

OpenLineage events are emitted for streaming jobs and datasets. The internal lineage graph must model long-running runs, source offsets/ranges and sink commits/snapshots.

Lineage must distinguish continuous processing evidence from batch snapshot evidence.

## Alerts and SLOs

Streaming alert policies include:

- consumer lag above threshold;
- watermark stalled;
- no-data / unexpected silence;
- throughput anomaly;
- checkpoint failure;
- repeated restart;
- state growth anomaly;
- DLQ spike;
- schema incompatibility;
- sink commit failure;
- latency SLO breach;
- cost-rate anomaly.

Policies support grouping, deduplication, suppression and maintenance windows through the common alerting subsystem.

## Dashboard integration

Streaming queries can feed live dashboard tiles through a bounded update protocol. The dashboard layer must apply throttling, sampling/downsampling and backpressure rather than rendering every raw event.

Power BI compatibility is one presentation profile; native Ronin dashboards may consume streams from any compatible engine.

## Security

- credentials are resolved by reference at runtime;
- ACL/topic/stream permissions are least-privilege;
- tenant identity propagates to stream operations;
- message payload sampling for debugging is opt-in and policy-controlled;
- PII/security labels propagate where metadata allows;
- DLQ access is separately authorized and audited;
- remote connectors are subject to network egress policy.

## Capability examples

```text
stream.source.kafka
stream.source.pulsar
stream.source.kinesis
stream.source.eventhubs
stream.source.pubsub
stream.sink.kafka
stream.event-time
stream.watermark
stream.window.session
stream.stateful
stream.checkpoint
stream.replay
stream.delivery.at-least-once
stream.delivery.exactly-once
stream.cdc
stream.schema-registry
stream.otel
stream.openlineage
```

## Initial implementation order

1. Define versioned streaming contracts and capability negotiation.
2. Implement Kafka/Redpanda source/sink contract first.
3. Implement Spark Structured Streaming adapter as the first execution backend.
4. Add checkpoint/replay lifecycle and metrics.
5. Add OpenTelemetry and OpenLineage emission.
6. Add Event Hubs, Kinesis, Pub/Sub and Pulsar adapters.
7. Add CDC/Debezium interoperability and table-format streaming sinks.
8. Add Flink adapter to prove engine neutrality for event streaming.
9. Add live dashboard subscriptions with throttling/backpressure.
10. Add streaming SLOs, cost-rate policies and automated remediation hooks.
