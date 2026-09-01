from fakebric.session_pod import build_session_pod


def test_session_pod_isolated_and_bounded():
    pod = build_session_pod("ABC_123", "item-1")
    spec = pod["spec"]
    container = spec["containers"][0]
    assert spec["activeDeadlineSeconds"] == 1200
    assert spec["securityContext"]["runAsNonRoot"] is True
    assert container["image"] == "fakebric/runtime:1.3-20260901-v5"
    assert container["resources"]["limits"] == {"cpu": "1", "memory": "1Gi"}
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert container["volumeMounts"][0]["mountPath"] == "/workspace/data"
    assert spec["volumes"][0]["persistentVolumeClaim"]["claimName"] == "fakebric-data"
    assert {port["containerPort"] for port in container["ports"]} == {8888, 5678}
    assert {env["name"] for env in container["env"]} >= {"FAKEBRIC_DEBUG", "FAKEBRIC_DEBUG_PORT"}
    assert build_session_pod("ABC_123", "item-1", restart_generation=2)["metadata"]["name"].endswith("-2")
