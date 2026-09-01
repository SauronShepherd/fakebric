FROM eclipse-temurin:17.0.20_8-jre-jammy@sha256:e17d77fb030dd4b642dc078d048a5fb9efcb3676ee20305d905949105a6ccd5a AS java-base
FROM python:3.11-slim@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0

COPY --from=java-base /opt/java/openjdk /opt/java/openjdk

ARG SPARK_VERSION=3.5.5
ARG DELTA_VERSION=3.2.1
ARG GLUTEN_VERSION=1.6.0
ARG GLUTEN_ARTIFACT=apache-gluten-1.6.0-bin-spark-3.5.tar.gz
ARG GLUTEN_URL=https://dlcdn.apache.org/gluten/1.6.0/apache-gluten-1.6.0-bin-spark-3.5.tar.gz
ARG GLUTEN_SHA512=b087e962bc244d3ba4b687a953ca508182f43da962a7674d68bd9727191d6a6d124b843acefd70836cdd00647d35a45ffacd20c8989237e0d8c92c4289093a5c
ARG GLUTEN_SHA256=90f9ec6ac964bcd73893c661a9133e46afc46f8b2fa9e17c647fb3939b8b6d43
ARG GLUTEN_SIZE=107838606
ARG VELOX_COMMIT=34338bfe5a95c895c90bb8fbbe2dfeeb04466087

ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:$PATH \
    SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark \
    PYSPARK_PYTHON=python3 \
    PYTHONUNBUFFERED=1 \
    FAKEBRIC_NATIVE_EXECUTION_ENABLED=false \
    FAKEBRIC_NATIVE_RUNTIME_PRESENT=true \
    GLUTEN_HOME=/opt/gluten

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl tini libstdc++6 libgcc-s1 libgomp1 libnuma1 \
    && rm -rf /var/lib/apt/lists/*

RUN python3.11 -m pip install --no-cache-dir \
      "pyspark==${SPARK_VERSION}" \
      "delta-spark==${DELTA_VERSION}" \
      jupyter-server ipykernel debugpy jupyter-client

RUN set -eux; \
    curl --fail --location --retry 3 --retry-delay 2 --output "/tmp/${GLUTEN_ARTIFACT}" "${GLUTEN_URL}"; \
    test "$(stat -c%s "/tmp/${GLUTEN_ARTIFACT}")" -eq "${GLUTEN_SIZE}"; \
    echo "${GLUTEN_SHA512}  /tmp/${GLUTEN_ARTIFACT}" | sha512sum -c -; \
    echo "${GLUTEN_SHA256}  /tmp/${GLUTEN_ARTIFACT}" | sha256sum -c -; \
    mkdir -p /opt/gluten; \
    tar -xzf "/tmp/${GLUTEN_ARTIFACT}" -C /opt/gluten; \
    printf '%s\n' \
      "gluten=${GLUTEN_VERSION}" \
      "velox=${VELOX_COMMIT}" \
      "artifact=${GLUTEN_ARTIFACT}" \
      "sha256=${GLUTEN_SHA256}" \
      "sha512=${GLUTEN_SHA512}" \
      > /opt/gluten/FAKEBRIC_RUNTIME_LOCK; \
    rm -f "/tmp/${GLUTEN_ARTIFACT}"

RUN useradd --create-home --uid 10001 fakebric \
    && mkdir -p /workspace /tmp/spark /opt/fakebric \
    && chown -R 10001:10001 /workspace /tmp/spark /opt/fakebric /opt/gluten

COPY runtime/execute_notebook.py /opt/fakebric/execute_notebook.py
COPY runtime/runtime_versions.py /opt/fakebric/runtime_versions.py
COPY runtime/native-sbom.spdx.json /opt/fakebric/native-sbom.spdx.json
COPY runtime/native-artifact-checksums.txt /opt/fakebric/native-artifact-checksums.txt
COPY fakebric/notebook_contract.py /opt/fakebric/notebook_contract.py
RUN chown -R 10001:10001 /opt/fakebric

USER 10001
WORKDIR /workspace
EXPOSE 8888 4040 5678
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["jupyter", "server", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.token=", "--ServerApp.password="]
