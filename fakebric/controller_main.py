import os
import time
import traceback
import requests
from kubernetes import client, config
from kubernetes.stream import stream
from .controller import ensure_session_pod, delete_session_pod, ensure_session_service, delete_session_service, pod_diagnostic
from .execution_result import execution_succeeded
from .redaction import redact_sensitive


def run_forever() -> None:
    config.load_incluster_config()
    api=client.CoreV1Api()
    base=os.getenv('FAKEBRIC_API_URL','http://fakebric-api:8000')
    headers={'X-Fakebric-Internal-Token':os.environ['FAKEBRIC_INTERNAL_TOKEN']}
    while True:
        response=requests.get(base+'/internal/v1/sessions',headers=headers,timeout=10)
        response.raise_for_status()
        for session in response.json():
            args=(api,session['id'],os.getenv('FAKEBRIC_NAMESPACE','fakebric-system'))
            if session['state'] in {'READY','EXECUTE'}:
                pod=ensure_session_pod(api,session['id'],session['item_id'],args[2],timeout_seconds=session.get('timeout_seconds',1200),restart_generation=session.get('restart_generation',0))
                ensure_session_service(api,session['id'],args[2])
                if session['state']=='EXECUTE':
                    runtime_output=''
                    try:
                        name=pod['metadata']['name']
                        deadline=time.monotonic()+30
                        while time.monotonic()<deadline:
                            current=api.read_namespaced_pod(name,args[2])
                            phase=getattr(getattr(current,'status',None),'phase',None)
                            if phase=='Running': break
                            diagnostic=pod_diagnostic(current)
                            # Pending is a normal scheduling phase; only fail immediately for
                            # terminal pod states or explicit container/image/resource errors.
                            if diagnostic and (diagnostic['code'] in {'POD_FAILED','IMAGEPULLBACKOFF','ERRIMAGEPULL','OOMKILLED'}):
                                raise RuntimeError(f"{diagnostic['code']}: {diagnostic['message']}")
                            time.sleep(1)
                        else: raise TimeoutError('session pod did not become Running within 30 seconds')
                        output=stream(api.connect_get_namespaced_pod_exec,name,args[2],command=['python','/opt/fakebric/execute_notebook.py',f'/workspace/data/sessions/{session["id"]}.ipynb'],container='runtime',stderr=True,stdin=False,stdout=True,tty=False,_preload_content=True)
                        runtime_output=redact_sensitive(output)[-4000:]
                        if not execution_succeeded(output):
                            raise RuntimeError(f'runtime did not report successful notebook execution: {runtime_output}')
                        requests.patch(base+f'/internal/v1/sessions/{session["id"]}',headers=headers,json={'state':'COMPLETED'},timeout=10).raise_for_status()
                    except Exception as exc:
                        print(redact_sensitive(f'session execution failed: {exc!r} status={getattr(exc, "status", None)} reason={getattr(exc, "reason", None)} body={getattr(exc, "body", None)}\\n{traceback.format_exc()}'), flush=True)
                        requests.patch(base+f'/internal/v1/sessions/{session["id"]}',headers=headers,json={'state':'FAILED'},timeout=10)
            else:
                delete_session_service(*args)
                delete_session_pod(*args, restart_generation=session.get('restart_generation',0))
        time.sleep(int(os.getenv('FAKEBRIC_RECONCILE_SECONDS','5')))


if __name__ == '__main__': run_forever()
