import json, os, shutil, sqlite3, uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import jwt
from .session_pod import build_session_pod

DATA=Path(os.getenv('FAKEBRIC_DATA','/tmp/fakebric')); DATA.mkdir(parents=True,exist_ok=True)
DB=os.getenv('FAKEBRIC_DB',str(DATA/'fakebric.db')); app=FastAPI(title='Fakebrick API',version='0.1.0')
MAX_UPLOAD_BYTES=int(os.getenv('FAKEBRIC_MAX_UPLOAD_BYTES',str(25*1024*1024)))
INTERNAL_TOKEN=os.getenv('FAKEBRIC_INTERNAL_TOKEN','')
AUTH_MODE=os.getenv('FAKEBRIC_AUTH_MODE','development')
JWT_SECRET=os.getenv('FAKEBRIC_JWT_SECRET','')
JWKS_URL=os.getenv('FAKEBRIC_JWKS_URL','')
OIDC_ISSUER=os.getenv('FAKEBRIC_OIDC_ISSUER')
OIDC_AUDIENCE=os.getenv('FAKEBRIC_OIDC_AUDIENCE')
AUTH_ROLE: ContextVar[str|None] = ContextVar('fakebric_auth_role',default=None)
REQUESTS_TOTAL=0
@app.middleware('http')
async def trace_requests(request: Request, call_next):
    global REQUESTS_TOTAL
    REQUESTS_TOTAL += 1
    trace_id=request.headers.get('X-Trace-Id') or str(uuid.uuid4())
    request.state.trace_id=trace_id
    if AUTH_MODE=='required' and request.url.path.startswith('/api/'):
        authorization=request.headers.get('Authorization','')
        if not authorization.startswith('Bearer ') or not (JWT_SECRET or JWKS_URL):
            return JSONResponse(status_code=401,content={'error':{'code':'UNAUTHENTICATED','message':'Bearer token required','traceId':trace_id}})
        try:
            token=authorization[7:]
            if JWKS_URL:
                key=jwt.PyJWKClient(JWKS_URL).get_signing_key_from_jwt(token).key
                request.state.claims=jwt.decode(token,key,algorithms=['RS256'],issuer=OIDC_ISSUER,audience=OIDC_AUDIENCE)
            else:
                request.state.claims=jwt.decode(token,JWT_SECRET,algorithms=['HS256'])
            claims=request.state.claims
            roles=claims.get('roles',claims.get('role',[]))
            if isinstance(roles,str): roles=[roles]
            AUTH_ROLE.set(next((r for r in roles if r in {'Workspace Admin','Contributor','Viewer'}),None))
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401,content={'error':{'code':'UNAUTHENTICATED','message':'Invalid bearer token','traceId':trace_id}})
    response=await call_next(request)
    response.headers['X-Trace-Id']=trace_id
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; connect-src 'self' ws: wss:; script-src 'self'; style-src 'self'"
    return response
@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={'error': {'code': f'HTTP_{exc.status_code}', 'message': str(exc.detail), 'traceId': getattr(request.state,'trace_id',None)}})
@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {'code': 'VALIDATION_ERROR', 'message': 'Request validation failed', 'details': exc.errors(), 'traceId': getattr(request.state,'trace_id',None)}})
class WorkspaceIn(BaseModel): displayName:str=Field(min_length=1,max_length=120)
class ItemIn(BaseModel): type:Literal['Notebook','Lakehouse','Environment','SemanticModel','Report']; displayName:str=Field(min_length=1,max_length=120); description:str=''
class ItemPatch(BaseModel): displayName:str|None=Field(default=None,min_length=1,max_length=120); description:str|None=Field(default=None,max_length=2000)
class DefinitionIn(BaseModel): content:dict[str,Any]
class SessionIn(BaseModel): action:Literal['start','stop','restart']; timeoutSeconds:int=Field(default=1200,ge=1,le=1200)
class ExecuteIn(BaseModel): timeoutSeconds:int=Field(default=1200,ge=1,le=1200)
class SessionStateIn(BaseModel): state:Literal['COMPLETED','FAILED']
class TableIn(BaseModel): name:str=Field(min_length=1,max_length=120,pattern=r'^[A-Za-z_][A-Za-z0-9_]*$'); format:Literal['delta']='delta'
class RowsIn(BaseModel): rows:list[dict[str,Any]]=Field(min_length=1,max_length=1000); mode:Literal['append','overwrite']='append'
class PublishEnvironmentIn(BaseModel): imageDigest:str=Field(pattern=r'^sha256:[0-9a-fA-F]{64}$')
def require_role(role: str, allowed: set[str]):
    if AUTH_MODE=='required': role=AUTH_ROLE.get() or ''
    if role not in allowed: raise HTTPException(403, 'Action is not allowed for this workspace role')
def websocket_role(websocket: WebSocket) -> str:
    if AUTH_MODE != 'required':
        return websocket.headers.get('X-Fakebric-Role','Viewer')
    authorization=websocket.headers.get('Authorization','')
    if not authorization.startswith('Bearer ') or not (JWT_SECRET or JWKS_URL):
        raise HTTPException(401,'Bearer token required')
    try:
        token=authorization[7:]
        if JWKS_URL:
            key=jwt.PyJWKClient(JWKS_URL).get_signing_key_from_jwt(token).key
            claims=jwt.decode(token,key,algorithms=['RS256'],issuer=OIDC_ISSUER,audience=OIDC_AUDIENCE)
        else:
            claims=jwt.decode(token,JWT_SECRET,algorithms=['HS256'])
        roles=claims.get('roles',claims.get('role',[])); roles=[roles] if isinstance(roles,str) else roles
        return next((r for r in roles if r in {'Workspace Admin','Contributor','Viewer'}),'')
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401,'Invalid bearer token') from exc
class ClosingConnection(sqlite3.Connection):
 def __exit__(self, exc_type, exc, tb):
  try:
   return super().__exit__(exc_type, exc, tb)
  finally:
   self.close()
def db():
 c=sqlite3.connect(DB, factory=ClosingConnection); c.row_factory=sqlite3.Row; return c
def now(): return datetime.now(timezone.utc).isoformat()
def init():
 with db() as c:
  c.executescript('CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,display_name TEXT,state TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY,workspace_id TEXT,type TEXT,display_name TEXT,description TEXT,state TEXT,revision INTEGER,definition TEXT,created_at TEXT,updated_at TEXT);CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,item_id TEXT UNIQUE,state TEXT,updated_at TEXT,timeout_seconds INTEGER NOT NULL DEFAULT 1200,restart_generation INTEGER NOT NULL DEFAULT 0);')
  columns={row['name'] for row in c.execute('PRAGMA table_info(sessions)')}
  if 'timeout_seconds' not in columns: c.execute('ALTER TABLE sessions ADD COLUMN timeout_seconds INTEGER NOT NULL DEFAULT 1200')
  if 'restart_generation' not in columns: c.execute('ALTER TABLE sessions ADD COLUMN restart_generation INTEGER NOT NULL DEFAULT 0')
init()
def out(r):
 d=dict(r)
 return {'id':d['id'],'workspaceId':d['workspace_id'],'type':d['type'],'displayName':d['display_name'],'description':d['description'],'state':d['state'],'revision':d['revision'],'definition':json.loads(d['definition']),'createdAt':d['created_at'],'updatedAt':d['updated_at']}
def validate_notebook(doc: dict[str, Any]):
    if doc.get('nbformat') != 4 or not isinstance(doc.get('cells'), list) or not isinstance(doc.get('metadata'), dict):
        raise HTTPException(422, 'Notebook must be a valid nbformat 4 document')
    allowed={'code','markdown','raw'}
    for cell in doc['cells']:
        if not isinstance(cell, dict) or cell.get('cell_type') not in allowed or not isinstance(cell.get('source',''), (str,list)):
            raise HTTPException(422, 'Notebook contains an invalid cell')
@app.get('/healthz')
def health(): return {'status':'ok','version':app.version}
@app.get('/metrics', include_in_schema=False)
def metrics():
    return Response(f'# HELP fakebric_requests_total Total HTTP requests\\n# TYPE fakebric_requests_total counter\\nfakebric_requests_total {REQUESTS_TOTAL}\\n', media_type='text/plain; version=0.0.4')
@app.get('/readyz')
def ready():
    try:
        if AUTH_MODE=='required' and not (JWKS_URL or JWT_SECRET): raise RuntimeError('Authentication is required but no JWT verifier is configured')
        with db() as c: c.execute('SELECT 1').fetchone()
        if not (Path(__file__).resolve().parents[1]/'runtime-1.3.lock.json').is_file(): raise RuntimeError('Runtime manifest unavailable')
    except Exception as exc: raise HTTPException(503,f'Readiness check failed: {exc}')
    return {'status':'ready','version':app.version}
@app.get('/api/v1/runtime/manifest')
def runtime_manifest():
    path=Path(__file__).resolve().parents[1]/'runtime-1.3.lock.json'
    return json.loads(path.read_text(encoding='utf-8'))
@app.get('/internal/v1/sessions')
def internal_sessions(x_fakebric_internal_token: str = Header(default='', alias='X-Fakebric-Internal-Token')):
    if not INTERNAL_TOKEN or x_fakebric_internal_token != INTERNAL_TOKEN: raise HTTPException(404,'Not found')
    with db() as c:
        return [dict(r) for r in c.execute("SELECT id,item_id,state,updated_at,timeout_seconds,restart_generation FROM sessions WHERE state IN ('READY','EXECUTE','STOPPED','COMPLETED','FAILED')")]
@app.patch('/internal/v1/sessions/{sid}')
def internal_session_state(sid:str, x:SessionStateIn, x_fakebric_internal_token: str = Header(default='', alias='X-Fakebric-Internal-Token')):
    if not INTERNAL_TOKEN or x_fakebric_internal_token != INTERNAL_TOKEN: raise HTTPException(404,'Not found')
    with db() as c:
        row=c.execute('SELECT state FROM sessions WHERE id=?',(sid,)).fetchone()
        if not row: raise HTTPException(404,'Session not found')
        if x.state=='COMPLETED' and row['state']!='EXECUTE': raise HTTPException(409,'Only an executing session can complete')
        if x.state=='FAILED' and row['state'] not in {'READY','EXECUTE'}: raise HTTPException(409,'Session is already terminal')
        c.execute('UPDATE sessions SET state=?,updated_at=? WHERE id=?',(x.state,now(),sid))
    return {'id':sid,'state':x.state}
@app.get('/api/v1/workspaces')
def workspaces():
 with db() as c:
  return [{'id':r['id'],'displayName':r['display_name'],'state':r['state'],'createdAt':r['created_at']} for r in c.execute('SELECT * FROM workspaces ORDER BY created_at DESC')]
@app.post('/api/v1/workspaces',status_code=201)
def create_workspace(x:WorkspaceIn,x_fakebric_role: str = Header(default='Workspace Admin')):
 require_role(x_fakebric_role, {'Workspace Admin'})
 i=str(uuid.uuid4()); t=now()
 with db() as c:c.execute('INSERT INTO workspaces VALUES(?,?,?,?)',(i,x.displayName,'Ready',t))
 return {'id':i,'displayName':x.displayName,'state':'Ready','createdAt':t}
@app.get('/api/v1/workspaces/{wid}/items')
def items(wid:str):
 with db() as c:
  if not c.execute('SELECT 1 FROM workspaces WHERE id=?',(wid,)).fetchone(): raise HTTPException(404,'Workspace not found')
  return [out(r) for r in c.execute('SELECT * FROM items WHERE workspace_id=? ORDER BY updated_at DESC',(wid,))]
@app.post('/api/v1/workspaces/{wid}/items',status_code=201)
def create_item(wid:str,x:ItemIn,x_fakebric_role: str = Header(default='Contributor')):
 require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
 i=str(uuid.uuid4());t=now()
 with db() as c:
  if not c.execute('SELECT 1 FROM workspaces WHERE id=?',(wid,)).fetchone():raise HTTPException(404,'Workspace not found')
  definition={'schemaVersion':1}
  if x.type=='Notebook':definition={'nbformat':4,'nbformat_minor':5,'metadata':{'fakebric':{'schemaVersion':1,'runtime':'1.3','nativeExecution':'unknown'}},'cells':[]}
  elif x.type=='Lakehouse':definition={'filesRoot':str(DATA/i/'Files'),'tablesRoot':str(DATA/i/'Tables')};Path(definition['filesRoot']).mkdir(parents=True);Path(definition['tablesRoot']).mkdir(parents=True)
  elif x.type=='Environment':definition={'runtime':'1.3','spark':'3.5.5','python':'3.11','delta':'3.2.1','state':'Draft'}
  c.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?)',(i,wid,x.type,x.displayName,x.description,'Ready',1,json.dumps(definition),t,t));return out(c.execute('SELECT * FROM items WHERE id=?',(i,)).fetchone())
@app.get('/api/v1/items/{iid}')
def get_item(iid:str):
 with db() as c:
  r=c.execute('SELECT * FROM items WHERE id=?',(iid,)).fetchone()
  if not r:raise HTTPException(404,'Item not found')
  return out(r)
@app.patch('/api/v1/items/{iid}')
def patch_item(iid:str,x:ItemPatch,x_fakebric_role: str = Header(default='Contributor')):
 require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
 if x.displayName is None and x.description is None: raise HTTPException(422,'At least one item property is required')
 with db() as c:
  r=c.execute('SELECT * FROM items WHERE id=?',(iid,)).fetchone()
  if not r: raise HTTPException(404,'Item not found')
  display=x.displayName if x.displayName is not None else r['display_name']
  description=x.description if x.description is not None else r['description']
  c.execute('UPDATE items SET display_name=?,description=?,updated_at=? WHERE id=?',(display,description,now(),iid))
  return out(c.execute('SELECT * FROM items WHERE id=?',(iid,)).fetchone())
@app.get('/api/v1/items/{iid}/definition')
def get_definition(iid:str,response:Response):
 with db() as c:
  r=c.execute('SELECT id,type,revision,definition,updated_at FROM items WHERE id=?',(iid,)).fetchone()
  if not r: raise HTTPException(404,'Item not found')
  response.headers['ETag']=f'"{r["revision"]}"'
  return {'id':r['id'],'type':r['type'],'revision':r['revision'],'content':json.loads(r['definition']),'updatedAt':r['updated_at']}
@app.put('/api/v1/items/{iid}/definition')
def save(iid:str,x:DefinitionIn,response:Response,if_match:str|None=Header(default=None,alias='If-Match'),x_fakebric_role: str = Header(default='Contributor')):
 require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
 with db() as c:
  r=c.execute('SELECT * FROM items WHERE id=?',(iid,)).fetchone()
  if not r:raise HTTPException(404,'Item not found')
  if if_match and if_match.strip('"')!=str(r['revision']):raise HTTPException(409,'Definition revision conflict')
  if r['type']=='Notebook':
   validate_notebook(x.content)
  elif r['type']=='Environment':
   if json.loads(r['definition']).get('state')=='Published': raise HTTPException(409,'Published environment revisions are immutable')
   required={'runtime','spark','python','delta','state'}
   if not required.issubset(x.content) or x.content.get('state')!='Draft': raise HTTPException(422,'Environment definition must be a Draft with runtime metadata')
  else: raise HTTPException(409,'Only notebooks and environments have portable definitions')
  rev=r['revision']+1;c.execute('UPDATE items SET definition=?,revision=?,updated_at=? WHERE id=?',(json.dumps(x.content),rev,now(),iid));response.headers['ETag']=f'"{rev}"';return {'id':iid,'revision':rev,'state':'Saved'}
@app.post('/api/v1/items/{iid}/publish')
def publish_environment(iid:str,x:PublishEnvironmentIn,x_fakebric_role: str = Header(default='Contributor')):
 require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
 with db() as c:
  r=c.execute('SELECT * FROM items WHERE id=?',(iid,)).fetchone()
  if not r: raise HTTPException(404,'Item not found')
  if r['type']!='Environment': raise HTTPException(409,'Only environments can be published')
  definition=json.loads(r['definition'])
  if definition.get('state')!='Draft': raise HTTPException(409,'Only Draft environments can be published')
  definition.update({'state':'Published','imageDigest':x.imageDigest})
  rev=r['revision']+1
  c.execute('UPDATE items SET definition=?,revision=?,updated_at=? WHERE id=?',(json.dumps(definition),rev,now(),iid))
  return {'id':iid,'revision':rev,'state':'Published','imageDigest':x.imageDigest}
@app.post('/api/v1/items/{iid}/session')
def command(iid:str,x:SessionIn,x_fakebric_role: str = Header(default='Contributor')):
 require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
 with db() as c:
  if not c.execute('SELECT 1 FROM items WHERE id=?',(iid,)).fetchone():raise HTTPException(404,'Item not found')
  r=c.execute('SELECT * FROM sessions WHERE item_id=?',(iid,)).fetchone();sid=r['id'] if r else str(uuid.uuid4());state={'start':'READY','stop':'STOPPED','restart':'READY'}[x.action];generation=(r['restart_generation'] if r else 0)+(1 if x.action=='restart' else 0)
  c.execute('INSERT INTO sessions(id,item_id,state,updated_at,timeout_seconds,restart_generation) VALUES(?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at,timeout_seconds=excluded.timeout_seconds,restart_generation=excluded.restart_generation',(sid,iid,state,now(),x.timeoutSeconds,generation));return {'id':sid,'itemId':iid,'state':state,'runtime':'1.3','nativeExecution':'unknown','sessionTimeoutInSeconds':x.timeoutSeconds,'restartGeneration':generation,'podSpec':build_session_pod(sid,iid,timeout_seconds=x.timeoutSeconds,restart_generation=generation) if state=='READY' else None}
@app.get('/api/v1/items/{iid}/session')
def session(iid:str):
 with db() as c:
  if not c.execute('SELECT 1 FROM items WHERE id=?',(iid,)).fetchone(): raise HTTPException(404,'Item not found')
  r=c.execute('SELECT * FROM sessions WHERE item_id=?',(iid,)).fetchone()
  if not r: return {'itemId':iid,'state':'NOT_STARTED'}
  return {'id':r['id'],'itemId':r['item_id'],'state':r['state'],'updatedAt':r['updated_at'],'timeoutSeconds':r['timeout_seconds'],'restartGeneration':r['restart_generation']}

@app.post('/api/v1/items/{iid}/session/execute', status_code=202)
def execute_notebook(iid:str, x:ExecuteIn, x_fakebric_role: str = Header(default='Contributor')):
    require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
    with db() as c:
        item=c.execute("SELECT * FROM items WHERE id=? AND type='Notebook'",(iid,)).fetchone()
        if not item: raise HTTPException(404,'Notebook not found')
        current=c.execute('SELECT id,state FROM sessions WHERE item_id=?',(iid,)).fetchone()
        if not current or current['state']!='READY': raise HTTPException(409,'Session must be READY before execution')
        sid=current['id']; job_dir=DATA/'sessions'; job_dir.mkdir(parents=True,exist_ok=True)
        job=job_dir/f'{sid}.ipynb'; job.write_text(item['definition'],encoding='utf-8')
        c.execute('UPDATE sessions SET state=?,updated_at=?,timeout_seconds=? WHERE item_id=?',('EXECUTE',now(),x.timeoutSeconds,iid))
    return {'sessionId':sid,'state':'EXECUTE','notebookPath':f'/workspace/data/sessions/{sid}.ipynb','timeoutSeconds':x.timeoutSeconds}

@app.get('/api/v1/items/{iid}/session/result')
def session_result(iid:str, x_fakebric_role: str = Header(default='Viewer')):
    require_role(x_fakebric_role, {'Workspace Admin','Contributor','Viewer'})
    with db() as c:
        row=c.execute("SELECT id,state FROM sessions WHERE item_id=?",(iid,)).fetchone()
        if not row: raise HTTPException(404,'Session not found')
        if row['state']!='COMPLETED': raise HTTPException(409,'Session has no completed result')
        target=DATA/'sessions'/f"{row['id']}.ipynb"
    if not target.is_file(): raise HTTPException(404,'Execution result not found')
    return FileResponse(target,media_type='application/x-ipynb+json',filename=target.name)

@app.websocket('/api/v1/items/{iid}/session/events')
async def session_events(websocket:WebSocket, iid:str):
    try:
        role=websocket_role(websocket)
    except HTTPException:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    with db() as c:
        exists=c.execute('SELECT 1 FROM items WHERE id=?',(iid,)).fetchone()
        r=c.execute('SELECT * FROM sessions WHERE item_id=?',(iid,)).fetchone()
    if not exists:
        await websocket.send_json({'type':'error','code':'NOT_FOUND','message':'Item not found'})
        await websocket.close(code=1008)
        return
    await websocket.send_json({'type':'session.state','itemId':iid,'state':r['state'] if r else 'NOT_STARTED'})
    try:
        while True:
            message=await websocket.receive_json()
            if message.get('type') != 'session.command':
                await websocket.send_json({'type':'error','code':'INVALID_MESSAGE','message':'Expected session.command'})
                continue
            if role not in {'Workspace Admin','Contributor'}:
                await websocket.send_json({'type':'error','code':'FORBIDDEN','message':'Action is not allowed for this workspace role'})
                continue
            action=message.get('action')
            if action not in {'start','stop','restart'}:
                await websocket.send_json({'type':'error','code':'INVALID_ACTION','message':'Unsupported session action'})
                continue
            state={'start':'READY','stop':'STOPPED','restart':'READY'}[action]
            with db() as c:
                current=c.execute('SELECT id,restart_generation FROM sessions WHERE item_id=?',(iid,)).fetchone()
                sid=current['id'] if current else str(uuid.uuid4())
                generation=(current['restart_generation'] if current else 0)+(1 if action=='restart' else 0)
                c.execute('INSERT INTO sessions(id,item_id,state,updated_at,timeout_seconds,restart_generation) VALUES(?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at,timeout_seconds=excluded.timeout_seconds,restart_generation=excluded.restart_generation',(sid,iid,state,now(),1200,generation))
            await websocket.send_json({'type':'session.state','itemId':iid,'sessionId':sid,'state':state,'runtime':'1.3','restartGeneration':generation})
    except WebSocketDisconnect:
        return

@app.delete('/api/v1/items/{iid}', status_code=204)
def delete_item(iid:str, x_fakebric_role: str = Header(default='Contributor')):
    require_role(x_fakebric_role, {'Workspace Admin'})
    with db() as c:
        r=c.execute('SELECT type FROM items WHERE id=?',(iid,)).fetchone()
        if not r: raise HTTPException(404,'Item not found')
        if r['type']=='Lakehouse': raise HTTPException(409,'Lakehouse deletion requires an explicit data-impact workflow')
        c.execute('DELETE FROM sessions WHERE item_id=?',(iid,)); c.execute('DELETE FROM items WHERE id=?',(iid,))

def lake_root(iid: str) -> Path:
    with db() as c:
        r=c.execute("SELECT definition,type FROM items WHERE id=?",(iid,)).fetchone()
    if not r or r['type'] != 'Lakehouse': raise HTTPException(404,'Lakehouse not found')
    return (DATA/iid/'Files').resolve()

def lake_tables_root(iid: str) -> Path:
    with db() as c:
        r=c.execute("SELECT definition,type FROM items WHERE id=?",(iid,)).fetchone()
    if not r or r['type'] != 'Lakehouse': raise HTTPException(404,'Lakehouse not found')
    return (DATA/iid/'Tables').resolve()

def safe_path(root: Path, relative: str) -> Path:
    candidate=(root/relative).resolve()
    if candidate != root.resolve() and root.resolve() not in candidate.parents: raise HTTPException(400,'Path escapes lakehouse Files root')
    return candidate

@app.get('/api/v1/lakehouses/{iid}/files')
def list_files(iid:str, path:str='',limit:int=1000,offset:int=0):
    if limit<1 or limit>10000 or offset<0 or offset>1000000: raise HTTPException(422,'invalid file listing pagination')
    root=lake_root(iid); folder=safe_path(root,path)
    if not folder.exists(): raise HTTPException(404,'Path not found')
    entries=sorted(folder.iterdir(),key=lambda x:(x.is_file(),x.name.lower()))[offset:offset+limit]
    return [{'name':p.name,'path':p.relative_to(root).as_posix(),'kind':'directory' if p.is_dir() else 'file','size':p.stat().st_size if p.is_file() else None} for p in entries]

@app.post('/api/v1/lakehouses/{iid}/files')
async def upload_file(iid:str, file:UploadFile=File(...), path:str=''):
    if not file.filename or Path(file.filename).name != file.filename:
        raise HTTPException(400,'File name must be a non-empty base name')
    root=lake_root(iid); target=safe_path(root,str(Path(path)/file.filename))
    if target.exists(): raise HTTPException(409,'File already exists')
    target.parent.mkdir(parents=True,exist_ok=True)
    written=0
    with target.open('wb') as output:
        while chunk := await file.read(1024*1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                target.unlink(missing_ok=True)
                raise HTTPException(413,f'File exceeds {MAX_UPLOAD_BYTES} byte limit')
            output.write(chunk)
    return {'path':target.relative_to(root).as_posix(),'size':target.stat().st_size,'state':'Saved'}

@app.post('/api/v1/lakehouses/{iid}/files/folders',status_code=201)
def create_folder(iid:str,path:str,x_fakebric_role: str = Header(default='Contributor')):
    require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
    if not path or Path(path).name in {'.','..'}: raise HTTPException(422,'Folder path is required')
    root=lake_root(iid); target=safe_path(root,path)
    if target.exists(): raise HTTPException(409,'Folder already exists')
    target.mkdir(parents=True)
    return {'path':target.relative_to(root).as_posix(),'kind':'directory','state':'Created'}

@app.get('/api/v1/lakehouses/{iid}/files/{relative_path:path}')
def download_file(iid:str, relative_path:str):
    root=lake_root(iid); target=safe_path(root,relative_path)
    if not target.is_file(): raise HTTPException(404,'File not found')
    return FileResponse(target)

@app.get('/api/v1/lakehouses/{iid}/tables')
def list_tables(iid:str):
    root=lake_tables_root(iid); root.mkdir(parents=True,exist_ok=True)
    result=[]
    for metadata in sorted(root.glob('*/_fakebric_table.json')):
        record=json.loads(metadata.read_text(encoding='utf-8'))
        record.pop('history',None)
        result.append(record)
    return result

@app.get('/api/v1/lakehouses/{iid}/tables/{name}')
def table_details(iid:str,name:str):
    metadata=table_path(iid,name)/'_fakebric_table.json'
    return json.loads(metadata.read_text(encoding='utf-8'))

@app.post('/api/v1/lakehouses/{iid}/tables',status_code=201)
def create_table(iid:str,x:TableIn):
    root=lake_tables_root(iid); table=root/x.name; metadata=table/'_fakebric_table.json'
    if metadata.exists(): raise HTTPException(409,'Table already exists')
    table.mkdir(parents=True,exist_ok=False)
    record={'name':x.name,'format':x.format,'path':table.relative_to(root).as_posix(),'state':'Ready','schema':[],'version':0,'history':[]}
    metadata.write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record

def table_path(iid: str, name: str) -> Path:
    root=lake_tables_root(iid); target=safe_path(root,name)
    metadata=target/'_fakebric_table.json'
    if not metadata.is_file(): raise HTTPException(404,'Table not found')
    return target

@app.post('/api/v1/lakehouses/{iid}/tables/{name}/rows',status_code=201)
def append_rows(iid:str,name:str,x:RowsIn):
    target=table_path(iid,name); data=target/'data.jsonl'
    try:
        encoded=[json.dumps(row,separators=(',',':'))+'\n' for row in x.rows]
    except (TypeError,ValueError) as exc:
        raise HTTPException(422,'Rows must contain JSON-serializable values') from exc
    if x.mode=='overwrite':
        data.write_text(''.join(encoded),encoding='utf-8')
    else:
        with data.open('a',encoding='utf-8') as stream:
            stream.writelines(encoded)
    metadata=target/'_fakebric_table.json'; record=json.loads(metadata.read_text(encoding='utf-8'))
    fields=[] if x.mode=='overwrite' else list(record.get('schema',[]))
    for row in x.rows:
        for key in row:
            if key not in fields: fields.append(key)
    record['schema']=fields; record['version']=int(record.get('version',0))+1
    record.setdefault('history',[]).append({'version':record['version'],'operation':x.mode,'rows':len(x.rows),'timestamp':now()})
    metadata.write_text(json.dumps(record,indent=2),encoding='utf-8')
    return {'table':name,'rowsWritten':len(x.rows),'mode':x.mode,'version':record['version'],'state':'Saved','schema':fields}

@app.get('/api/v1/lakehouses/{iid}/tables/{name}/rows')
def read_rows(iid:str,name:str,limit:int=1000,offset:int=0):
    if limit<1 or limit>10000: raise HTTPException(422,'limit must be between 1 and 10000')
    if offset<0 or offset>1000000: raise HTTPException(422,'offset must be between 0 and 1000000')
    data=table_path(iid,name)/'data.jsonl'
    if not data.is_file(): return []
    return [json.loads(line) for line in data.read_text(encoding='utf-8').splitlines()[offset:offset+limit] if line]

@app.get('/api/v1/lakehouses/{iid}/tables/{name}/history')
def table_history(iid:str,name:str,limit:int=100,offset:int=0):
    if limit<1 or limit>1000 or offset<0 or offset>100000: raise HTTPException(422,'invalid history pagination')
    metadata=table_path(iid,name)/'_fakebric_table.json'
    history=json.loads(metadata.read_text(encoding='utf-8')).get('history',[])
    return history[offset:offset+limit]

@app.delete('/api/v1/lakehouses/{iid}/tables/{name}',status_code=204)
def delete_table(iid:str,name:str,confirm:bool=False,x_fakebric_role: str = Header(default='Contributor')):
    require_role(x_fakebric_role, {'Workspace Admin','Contributor'})
    if not confirm: raise HTTPException(409,'Managed table deletion requires confirm=true')
    target=table_path(iid,name)
    shutil.rmtree(target)
static=Path(__file__).parent/'static';app.mount('/static',StaticFiles(directory=static),name='static')
@app.get('/')
def root():return FileResponse(static/'index.html')
