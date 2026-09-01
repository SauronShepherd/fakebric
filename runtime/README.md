# Fakebrick Runtime 1.3

Fakebrick keeps two execution images separate during the Gluten + Velox rollout:

- JVM runtime: `runtime/Dockerfile`, Java 11 + Spark 3.5.5. This remains the default execution path.
- Native-capable candidate: `runtime/native.Dockerfile`, Java 17 + Spark 3.5.5 + the checksum-verified Gluten 1.6.0 distribution containing the pinned Velox integration.

Both images use immutable base-image digests and run as UID/GID 10001. Native execution remains disabled by default with `FAKEBRIC_NATIVE_EXECUTION_ENABLED=false`; merely using the native-capable image does not activate the Spark plugin.

Build locally:

```powershell
docker build -f runtime/Dockerfile -t fakebric/runtime:1.3-base .
docker build -f runtime/native.Dockerfile -t fakebric/runtime-native:1.3-gluten-1.6.0-candidate .
```

The native Dockerfile downloads exactly `apache-gluten-1.6.0-bin-spark-3.5.tar.gz`, checks its byte size, verifies the Apache SHA-512, and then verifies the pinned SHA-256 before extraction. The preliminary SPDX inventory is `runtime/native-sbom.spdx.json`; artifact hashes are also recorded in `runtime/native-artifact-checksums.txt`.

Use `/opt/fakebric/runtime_versions.py` inside either image to emit Java, Spark, Python, architecture, UID/GID, native-enabled state, and native-runtime presence. CI builds both images, checks those values, runs the notebook smoke on the JVM image, and starts a Spark JVM session inside the native-capable image while confirming that `spark.plugins` is empty.

The native image is still a candidate. Plugin initialization and a true Gluten/Velox execution smoke belong to Day 3; production publication by immutable image digest remains gated until the later release criteria are met.
