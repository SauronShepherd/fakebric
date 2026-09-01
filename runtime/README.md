# Fakebrick Runtime 1.3

This image is the execution-plane base for session pods. It contains the
locked Spark, Delta, Python and Java versions plus Jupyter Server, ipykernel,
debugpy and jupyter-client. Build it with:

```powershell
docker build -f runtime/Dockerfile -t fakebric/runtime:1.3-base .
```

Before production, publish by immutable digest and put that digest in
`runtime-1.3.lock.json`. Native execution is an opt-in integration point and
must not be advertised as enabled until Gluten/Velox evidence is captured.

For batch notebook execution, the image also provides
`python /opt/fakebric/execute_notebook.py /workspace/data/job.ipynb`. The controller must
enforce the session timeout and resource limits before invoking it.
