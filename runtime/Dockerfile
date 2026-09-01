FROM eclipse-temurin:11-jre-noble@sha256:c55276a409ff48855ce7011fda07da527c41d57cc63b3381533fb7fea3ae027a AS java-base
FROM python:3.11-slim@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0

COPY --from=java-base /opt/java/openjdk /opt/java/openjdk

ARG SPARK_VERSION=3.5.5
ARG DELTA_VERSION=3.2.1

ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:$PATH \
    SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark \
    PYSPARK_PYTHON=python3 \
    PYTHONUNBUFFERED=1 \
    FAKEBRIC_NATIVE_EXECUTION_ENABLED=false

RUN apt-get update && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

RUN python3.11 -m pip install --no-cache-dir \
      "pyspark==${SPARK_VERSION}" \
      "delta-spark==${DELTA_VERSION}" \
      jupyter-server ipykernel debugpy jupyter-client

RUN useradd --create-home --uid 10001 fakebric \
    && mkdir -p /workspace /tmp/spark /opt/fakebric \
    && chown -R 10001:10001 /workspace /tmp/spark /opt/fakebric

COPY runtime/execute_notebook.py /opt/fakebric/execute_notebook.py
COPY runtime/runtime_versions.py /opt/fakebric/runtime_versions.py
COPY fakebric/notebook_contract.py /opt/fakebric/notebook_contract.py
RUN chown -R 10001:10001 /opt/fakebric

USER 10001
WORKDIR /workspace
EXPOSE 8888 4040 5678
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["jupyter", "server", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.token=", "--ServerApp.password="]
