from fastapi.testclient import TestClient
from fakebric.app import app

client=TestClient(app)
def test_runtime_manifest_is_pinned_contract():
    manifest=client.get('/api/v1/runtime/manifest').json()
    assert manifest['runtime']=='1.3'
    assert manifest['spark']=='3.5.5'
    assert manifest['delta']=='3.2.1'
    assert manifest['native']['enabledByDefault'] is False
    assert manifest['image']['digestPolicy']=='pin-before-production'

def test_workspace_list_uses_public_camel_case_contract():
    created=client.post('/api/v1/workspaces',json={'displayName':'Contract'}).json()
    listed=client.get('/api/v1/workspaces').json()
    match=next(row for row in listed if row['id']==created['id'])
    assert match=={'id':created['id'],'displayName':'Contract','state':'Ready','createdAt':match['createdAt']}
    assert 'display_name' not in match
    assert client.get('/api/v1/workspaces/not-a-workspace/items').status_code==404

def test_request_trace_id_is_propagated():
    response=client.get('/healthz',headers={'X-Trace-Id':'trace-test-001'})
    assert response.status_code==200
    assert response.headers['X-Trace-Id']=='trace-test-001'
    error=client.get('/api/v1/items/not-found',headers={'X-Trace-Id':'trace-test-002'})
    assert error.status_code==404
    assert error.json()['error']['code']=='HTTP_404'
    assert error.json()['error']['traceId']=='trace-test-002'
    assert 'fakebric_requests_total' in client.get('/metrics').text
    assert response.headers['X-Content-Type-Options']=='nosniff'
    assert response.headers['X-Frame-Options']=='DENY'
    assert response.headers['Referrer-Policy']=='no-referrer'
    assert "script-src 'self'" in response.headers['Content-Security-Policy']

def test_internal_session_queue_is_token_protected():
    import fakebric.app as module
    old=module.INTERNAL_TOKEN
    module.INTERNAL_TOKEN='test-token'
    try:
        assert client.get('/internal/v1/sessions').status_code==404
        assert client.get('/internal/v1/sessions',headers={'X-Fakebric-Internal-Token':'test-token'}).status_code==200
    finally:
        module.INTERNAL_TOKEN=old

def test_required_auth_rejects_missing_bearer():
    import fakebric.app as module
    old_mode,old_secret=module.AUTH_MODE,module.JWT_SECRET
    module.AUTH_MODE='required'; module.JWT_SECRET='test-secret-with-at-least-32-bytes'
    try:
        assert client.get('/api/v1/workspaces').status_code==401
    finally:
        module.AUTH_MODE,module.JWT_SECRET=old_mode,old_secret

def test_required_auth_without_verifier_is_not_ready():
    import fakebric.app as module
    old_mode,old_secret,old_jwks=module.AUTH_MODE,module.JWT_SECRET,module.JWKS_URL
    module.AUTH_MODE='required'; module.JWT_SECRET=''; module.JWKS_URL=''
    try:
        assert client.get('/readyz').status_code==503
    finally:
        module.AUTH_MODE,module.JWT_SECRET,module.JWKS_URL=old_mode,old_secret,old_jwks

def test_required_auth_uses_jwt_role_not_header():
    import fakebric.app as module, jwt
    old_mode,old_secret=module.AUTH_MODE,module.JWT_SECRET
    module.AUTH_MODE='required'; module.JWT_SECRET='test-secret-with-at-least-32-bytes'
    try:
        token=jwt.encode({'roles':['Viewer']},'test-secret-with-at-least-32-bytes',algorithm='HS256')
        response=client.delete('/api/v1/items/not-real',headers={'Authorization':'Bearer '+token,'X-Fakebric-Role':'Workspace Admin'})
        assert response.status_code==403
    finally:
        module.AUTH_MODE,module.JWT_SECRET=old_mode,old_secret

def test_required_auth_blocks_viewer_creation():
    import fakebric.app as module, jwt
    old_mode,old_secret=module.AUTH_MODE,module.JWT_SECRET
    module.AUTH_MODE='required'; module.JWT_SECRET='test-secret-with-at-least-32-bytes'
    try:
        token=jwt.encode({'roles':['Viewer']},'test-secret-with-at-least-32-bytes',algorithm='HS256')
        headers={'Authorization':'Bearer '+token}
        assert client.post('/api/v1/workspaces',headers=headers,json={'displayName':'Denied'}).status_code==403
    finally:
        module.AUTH_MODE,module.JWT_SECRET=old_mode,old_secret

def test_p0_lifecycle(tmp_path,monkeypatch):
    r=client.post('/api/v1/workspaces',json={'displayName':'QA'}); assert r.status_code==201; wid=r.json()['id']
    lh=client.post(f'/api/v1/workspaces/{wid}/items',json={'type':'Lakehouse','displayName':'Lake'}).json()
    listed_items=client.get(f'/api/v1/workspaces/{wid}/items').json()
    assert listed_items[0]['displayName']=='Lake' and 'display_name' not in listed_items[0]
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/files").json()==[]
    table=client.post(f"/api/v1/lakehouses/{lh['id']}/tables",json={'name':'events'}); assert table.status_code==201
    assert table.json()['format']=='delta'
    assert client.post(f"/api/v1/lakehouses/{lh['id']}/tables",json={'name':'csv_table','format':'csv'}).status_code==422
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables").json()[0]['name']=='events'
    assert client.post(f"/api/v1/lakehouses/{lh['id']}/tables/events/rows",json={'rows':[{'id':1,'kind':'test'}]}).json()['schema']==['id','kind']
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables/events/history").json()[0]['operation']=='append'
    assert 'history' not in client.get(f"/api/v1/lakehouses/{lh['id']}/tables").json()[0]
    details=client.get(f"/api/v1/lakehouses/{lh['id']}/tables/events").json()
    assert details['name']=='events' and details['format']=='delta' and details['version']==1
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables").json()[0]['schema']==['id','kind']
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables/events/rows").json()==[{'id':1,'kind':'test'}]
    client.post(f"/api/v1/lakehouses/{lh['id']}/tables/events/rows",json={'rows':[{'id':2,'kind':'second'}]})
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables/events/rows?limit=1").json()==[{'id':1,'kind':'test'}]
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables/events/rows?limit=1&offset=1").json()==[{'id':2,'kind':'second'}]
    overwritten=client.post(f"/api/v1/lakehouses/{lh['id']}/tables/events/rows",json={'mode':'overwrite','rows':[{'id':9,'kind':'replacement'}]}).json()
    assert overwritten['mode']=='overwrite'
    assert overwritten['version']==3
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables/events/rows").json()==[{'id':9,'kind':'replacement'}]
    assert client.delete(f"/api/v1/lakehouses/{lh['id']}/tables/events").status_code==409
    assert client.delete(f"/api/v1/lakehouses/{lh['id']}/tables/events?confirm=true").status_code==204
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/tables").json()==[]
    uploaded=client.post(f"/api/v1/lakehouses/{lh['id']}/files",files={'file':('hello.txt',b'hello')}).json()
    assert uploaded['path']=='hello.txt'
    assert client.post(f"/api/v1/lakehouses/{lh['id']}/files/folders",params={'path':'curated'}).status_code==201
    assert client.post(f"/api/v1/lakehouses/{lh['id']}/files/folders",params={'path':'curated'}).status_code==409
    assert client.post(f"/api/v1/lakehouses/{lh['id']}/files/folders",params={'path':'../escape'}).status_code==400
    assert client.post(f"/api/v1/lakehouses/{lh['id']}/files",files={'file':('hello.txt',b'overwrite')}).status_code==409
    assert any(entry['name']=='hello.txt' for entry in client.get(f"/api/v1/lakehouses/{lh['id']}/files").json())
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/files?limit=1&offset=0").status_code==200
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/files?limit=1&offset=1000001").status_code==422
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/files/hello.txt").content==b'hello'
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/files/../fakebric.db").status_code==404
    assert client.get(f"/api/v1/lakehouses/{lh['id']}/files?path=../").status_code==400
    nb=client.post(f'/api/v1/workspaces/{wid}/items',json={'type':'Notebook','displayName':'Notebook'}).json()
    assert nb['definition']['metadata']['fakebric']['runtime']=='1.3'
    definition_response=client.get(f"/api/v1/items/{nb['id']}/definition")
    assert definition_response.headers['ETag']=='"1"'
    definition=definition_response.json()
    assert definition['id']==nb['id'] and definition['revision']==1 and definition['content']==nb['definition']
    renamed=client.patch(f"/api/v1/items/{nb['id']}",json={'displayName':'Renamed'}).json()
    assert renamed['id']==nb['id'] and renamed['displayName']=='Renamed' and renamed['definition']==nb['definition']
    assert client.patch(f"/api/v1/items/{nb['id']}",headers={'X-Fakebric-Role':'Viewer'},json={'displayName':'Denied'}).status_code==403
    assert client.post(f"/api/v1/items/{nb['id']}/session",json={'action':'start'},headers={'X-Fakebric-Role':'Viewer'}).status_code==403
    started=client.post(f"/api/v1/items/{nb['id']}/session",json={'action':'start','timeoutSeconds':300}).json()
    restarted=client.post(f"/api/v1/items/{nb['id']}/session",json={'action':'restart','timeoutSeconds':300}).json()
    assert restarted['id']==started['id'] and restarted['restartGeneration']==1
    assert restarted['podSpec']['metadata']['name'] != started['podSpec']['metadata']['name']
    assert started['state']=='READY'
    assert started['sessionTimeoutInSeconds']==300
    public_session=client.get(f"/api/v1/items/{nb['id']}/session").json()
    assert public_session['itemId']==nb['id'] and public_session['timeoutSeconds']==300
    assert 'item_id' not in public_session and 'updated_at' not in public_session
    assert started['podSpec']['kind']=='Pod'
    assert started['podSpec']['spec']['activeDeadlineSeconds']==300
    execution=client.post(f"/api/v1/items/{nb['id']}/session/execute",json={}).json()
    assert execution['state']=='EXECUTE'
    assert client.get(f"/api/v1/items/{nb['id']}/session/result").status_code==409
    import fakebric.app as module
    previous_token=module.INTERNAL_TOKEN; module.INTERNAL_TOKEN='test-token'
    try:
        assert client.patch(f"/internal/v1/sessions/{started['id']}",headers={'X-Fakebric-Internal-Token':'test-token'},json={'state':'COMPLETED'}).status_code==200
        assert client.patch(f"/internal/v1/sessions/{started['id']}",headers={'X-Fakebric-Internal-Token':'test-token'},json={'state':'FAILED'}).status_code==409
        assert client.get(f"/api/v1/items/{nb['id']}/session/result").status_code==200
    finally:
        module.INTERNAL_TOKEN=previous_token
    saved=client.put(f"/api/v1/items/{nb['id']}/definition",headers={'If-Match':definition_response.headers['ETag']},json={'content':{'nbformat':4,'cells':[{'cell_type':'code','source':''}],'metadata':{}}})
    assert saved.json()['revision']==2 and saved.headers['ETag']=='"2"'
    assert client.put(f"/api/v1/items/{nb['id']}/definition",headers={'If-Match':'1'},json={'content':{}}).status_code==409
    assert client.put(f"/api/v1/items/{nb['id']}/definition",headers={'If-Match':'2'},json={'content':{'nbformat':3,'cells':[],'metadata':{}}}).status_code==422
    env=client.post(f'/api/v1/workspaces/{wid}/items',json={'type':'Environment','displayName':'Env'}).json()
    assert client.put(f"/api/v1/items/{env['id']}/definition",headers={'If-Match':'1'},json={'content':{'runtime':'1.3','spark':'3.5.5','python':'3.11','delta':'3.2.1','state':'Draft'}}).json()['revision']==2
    assert client.put(f"/api/v1/items/{env['id']}/definition",headers={'If-Match':'2'},json={'content':{'runtime':'1.3','state':'Draft'}}).status_code==422
    assert client.put(f"/api/v1/items/{env['id']}/definition",headers={'X-Fakebric-Role':'Viewer'},json={'content':{'runtime':'1.3','spark':'3.5.5','python':'3.11','delta':'3.2.1','state':'Draft'}}).status_code==403
    assert client.post(f"/api/v1/items/{env['id']}/publish",json={'imageDigest':'not-a-digest'}).status_code==422
    published=client.post(f"/api/v1/items/{env['id']}/publish",json={'imageDigest':'sha256:'+'a'*64}).json()
    assert published['state']=='Published' and published['revision']==3
    assert client.post(f"/api/v1/items/{env['id']}/publish",json={'imageDigest':'sha256:'+'b'*64}).status_code==409
    assert client.put(f"/api/v1/items/{env['id']}/definition",headers={'If-Match':'3'},json={'content':{'runtime':'1.3','spark':'3.5.5','python':'3.11','delta':'3.2.1','state':'Draft'}}).status_code==409
    assert client.delete(f"/api/v1/items/{nb['id']}").status_code==403
    assert client.delete(f"/api/v1/items/{nb['id']}",headers={'X-Fakebric-Role':'Workspace Admin'}).status_code==204
    assert len(client.get(f'/api/v1/workspaces/{wid}/items').json())==2

def test_session_websocket_contract():
    ws=client.post('/api/v1/workspaces',json={'displayName':'WS'}).json()
    nb=client.post(f"/api/v1/workspaces/{ws['id']}/items",json={'type':'Notebook','displayName':'NB'}).json()
    with client.websocket_connect(f"/api/v1/items/{nb['id']}/session/events", headers={'X-Fakebric-Role':'Contributor'}) as socket:
        assert socket.receive_json()['state']=='NOT_STARTED'
        socket.send_json({'type':'session.command','action':'start'})
        event=socket.receive_json()
        assert event['type']=='session.state' and event['state']=='READY' and event['restartGeneration']==0
        socket.send_json({'type':'session.command','action':'restart'})
        event=socket.receive_json()
        assert event['type']=='session.state' and event['state']=='READY' and event['restartGeneration']==1

def test_required_auth_rejects_websocket_role_spoof():
    import fakebric.app as module
    old_mode,old_secret=module.AUTH_MODE,module.JWT_SECRET
    try:
        ws=client.post('/api/v1/workspaces',json={'displayName':'Protected'}).json()
        nb=client.post(f"/api/v1/workspaces/{ws['id']}/items",json={'type':'Notebook','displayName':'NB'}).json()
        module.AUTH_MODE='required'; module.JWT_SECRET='test-secret-with-at-least-32-bytes'
        with client.websocket_connect(f"/api/v1/items/{nb['id']}/session/events", headers={'X-Fakebric-Role':'Workspace Admin'}) as socket:
            assert socket.receive_json()['type']=='error'
    except Exception as exc:
        assert '1008' in str(exc) or 'WebSocketDisconnect' in type(exc).__name__
    finally:
        module.AUTH_MODE,module.JWT_SECRET=old_mode,old_secret
