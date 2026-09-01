from fakebric.controller import ensure_session_pod, delete_session_pod, ensure_session_service, delete_session_service, build_session_service, pod_diagnostic


class Missing(Exception):
    status = 404


class FakeApi:
    def __init__(self): self.created=[]; self.deleted=[]
    def read_namespaced_pod(self, **kwargs): raise Missing()
    def create_namespaced_pod(self, **kwargs): self.created.append(kwargs); return type('R', (), {'to_dict': lambda self: kwargs['body']})()
    def delete_namespaced_pod(self, **kwargs): self.deleted.append(kwargs)
    def read_namespaced_service(self, **kwargs): raise Missing()
    def create_namespaced_service(self, **kwargs): self.created.append(kwargs); return type('R', (), {'to_dict': lambda self: kwargs['body']})()
    def delete_namespaced_service(self, **kwargs): self.deleted.append(kwargs)


def test_controller_creates_and_deletes_session_pod():
    api=FakeApi()
    pod=ensure_session_pod(api,'ABC_1','item-1')
    assert pod['kind']=='Pod' and api.created[0]['namespace']=='fakebric-system'
    delete_session_pod(api,'ABC_1')
    assert api.deleted[0]['name']=='session-abc-1-0'


def test_controller_creates_service_with_exclusive_session_selector_and_cleans_it():
    api=FakeApi()
    service=ensure_session_service(api,'ABC_1')
    assert service['metadata']['name']=='session-abc-1-driver'
    assert service['spec']['selector']=={'app':'fakebric-session','sessionId':'ABC_1'}
    assert {p['port'] for p in service['spec']['ports']}=={8888,5678}
    delete_session_service(api,'ABC_1')
    assert any(item.get('name')=='session-abc-1-driver' for item in api.deleted)


def test_pod_diagnostic_classifies_actionable_container_failures():
    waiting=type('Waiting', (), {'reason':'ImagePullBackOff','message':'pull denied'})()
    state=type('State', (), {'waiting':waiting,'terminated':None})()
    container=type('Container', (), {'state':state})()
    status=type('Status', (), {'phase':'Pending','container_statuses':[container]})()
    pod=type('Pod', (), {'status':status})()
    assert pod_diagnostic(pod)=={'code':'IMAGEPULLBACKOFF','message':'pull denied'}

    status=type('Status', (), {'phase':'Pending','container_statuses':[]})()
    pod=type('Pod', (), {'status':status})()
    assert pod_diagnostic(pod)['code']=='POD_PENDING'
