"""Side-effect-free Kubernetes session PodSpec builder."""
from typing import Any


def build_session_pod(session_id: str, item_id: str, image: str = "fakebric/runtime:1.3-20260901-v5", cpu: str = "1", memory: str = "1Gi", timeout_seconds: int = 1200, data_claim: str = "fakebric-data", restart_generation: int = 0) -> dict[str, Any]:
    if not session_id or not item_id or timeout_seconds < 1:
        raise ValueError("session_id, item_id and positive timeout_seconds are required")
    name = "session-" + session_id.lower().replace("_", "-")[:45].strip("-") + "-" + str(restart_generation)
    return {"apiVersion":"v1","kind":"Pod","metadata":{"name":name,"labels":{"app":"fakebric-session","itemId":item_id,"sessionId":session_id}},"spec":{"restartPolicy":"Never","automountServiceAccountToken":False,"activeDeadlineSeconds":timeout_seconds,"securityContext":{"runAsNonRoot":True,"runAsUser":10001,"runAsGroup":10001,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"runtime","image":image,"imagePullPolicy":"IfNotPresent","workingDir":"/workspace","command":["jupyter","server","--ip=0.0.0.0","--port=8888","--no-browser","--ServerApp.token="],"env":[{"name":"FAKEBRIC_SESSION_ID","value":session_id},{"name":"FAKEBRIC_ITEM_ID","value":item_id},{"name":"FAKEBRIC_DEBUG","value":"0"},{"name":"FAKEBRIC_DEBUG_PORT","value":"5678"}],"ports":[{"name":"jupyter","containerPort":8888},{"name":"debugpy","containerPort":5678}],"resources":{"requests":{"cpu":cpu,"memory":memory},"limits":{"cpu":cpu,"memory":memory}},"securityContext":{"allowPrivilegeEscalation":False,"capabilities":{"drop":["ALL"]}},"volumeMounts":[{"name":"data","mountPath":"/workspace/data"}]}],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":data_claim}}]}}
