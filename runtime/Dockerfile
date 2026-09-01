FROM eclipse-temurin:11-jre-noble AS java-base
FROM python:3.11-slim

COPY --from=java-base /opt/java/openjdk /opt/java/openjdk

ARG SPARK_VERSION=3.5.5
ARG DELTA_VERSION=3.2.1

ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:$PATH \
    SPARK_HOME=/usr/local/lib/python3.11/site-packages/pyspark \
    PYSPARK_PYTHON=python3 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

RUN python3.11 -m pip install --no-cache-dir \
      "pyspark==${SPARK_VERSION}" \
      "delta-spark==${DELTA_VERSION}" \
      jupyter-server ipykernel debugpy jupyter-client

RUN useradd --create-home --uid 10001 fakebric \
    && mkdir -p /workspace /tmp/spark \
    && chown -R 10001:10001 /workspace /tmp/spark

COPY runtime/execute_notebook.py /opt/fakebric/execute_notebook.py
COPY fakebric/notebook_contract.py /opt/fakebric/notebook_contract.py
RUN chown 10001:10001 /opt/fakebric/execute_notebook.py

USER 10001
WORKDIR /workspace
EXPOSE 8888 4040 5678
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["jupyter", "server", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.token=", "--ServerApp.password="]
