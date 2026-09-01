"""Kubernetes session reconciler."""
from typing import Any
from .session_pod import build_session_pod


def pod_diagnostic(pod: Any) -> dict[str, str] | None:
    status=getattr(pod,'status',None)
    phase=getattr(status,'phase',None)
    for condition in getattr(status,'container_statuses',None) or []:
        state=getattr(condition,'state',None)
        waiting=getattr(state,'waiting',None)
        if waiting and getattr(waiting,'reason',None):
            reason=waiting.reason
            return {'code':reason.upper(), 'message':getattr(waiting,'message',None) or f'Container is waiting: {reason}'}
        terminated=getattr(state,'terminated',None)
        if terminated:
            reason=getattr(terminated,'reason',None) or 'ContainerTerminated'
            return {'code':reason.upper(), 'message':getattr(terminated,'message',None) or f'Container terminated: {reason}'}
    if phase=='Pending': return {'code':'POD_PENDING','message':'Session pod is waiting for schedulable resources or image pull'}
    if phase in {'Failed','Succeeded'}: return {'code':f'POD_{phase.upper()}','message':f'Session pod reached terminal phase {phase}'}
    return None


def ensure_session_pod(core_api: Any, session_id: str, item_id: str, namespace: str = "fakebric-system", **kwargs: Any) -> dict[str, Any]:
    pod=build_session_pod(session_id,item_id,**kwargs); name=pod['metadata']['name']
    try:
        existing=core_api.read_namespaced_pod(name=name,namespace=namespace)
        phase=getattr(getattr(existing,'status',None),'phase',None)
        if phase in {'Succeeded','Failed'}:
            core_api.delete_namespaced_pod(name=name,namespace=namespace,grace_period_seconds=0)
            return core_api.create_namespaced_pod(namespace=namespace,body=pod).to_dict()
        return existing.to_dict()
    except Exception as exc:
        if getattr(exc,'status',None)!=404: raise
        return core_api.create_namespaced_pod(namespace=namespace,body=pod).to_dict()


def delete_session_pod(core_api: Any, session_id: str, namespace: str = "fakebric-system", restart_generation: int = 0) -> None:
    name=build_session_pod(session_id, 'cleanup', restart_generation=restart_generation)['metadata']['name']
    try: core_api.delete_namespaced_pod(name=name,namespace=namespace,grace_period_seconds=0)
    except Exception as exc:
        if getattr(exc,'status',None)!=404: raise


def _session_name(session_id: str) -> str:
    return 'session-'+session_id.lower().replace('_','-')[:50].strip('-')


def build_session_service(session_id: str) -> dict[str, Any]:
    name=_session_name(session_id)
    return {'apiVersion':'v1','kind':'Service','metadata':{'name':name+'-driver','labels':{'app':'fakebric-session','sessionId':session_id}},'spec':{'selector':{'app':'fakebric-session','sessionId':session_id},'ports':[{'name':'jupyter','port':8888,'targetPort':8888},{'name':'debugpy','port':5678,'targetPort':5678}], 'type':'ClusterIP'}}


def ensure_session_service(core_api: Any, session_id: str, namespace: str = "fakebric-system") -> dict[str, Any]:
    service=build_session_service(session_id); name=service['metadata']['name']
    try:
        existing=core_api.read_namespaced_service(name=name,namespace=namespace)
        return existing.to_dict()
    except Exception as exc:
        if getattr(exc,'status',None)!=404: raise
        return core_api.create_namespaced_service(namespace=namespace,body=service).to_dict()


def delete_session_service(core_api: Any, session_id: str, namespace: str = "fakebric-system") -> None:
    try: core_api.delete_namespaced_service(name=build_session_service(session_id)['metadata']['name'],namespace=namespace)
    except Exception as exc:
        if getattr(exc,'status',None)!=404: raise
