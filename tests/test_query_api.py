from fastapi.testclient import TestClient
from fakebric.semantic_model.api import app

def payload(model_id='m1'):
 return {'model':{'id':model_id,'name':'Model','tables':[{'name':'Sales','source':{'type':'fakebrick','path':'Sales'},'columns':[{'name':'Amount','type':'decimal'}]}]},'tables':{'Sales':[{'Amount':10},{'Amount':20}]},'dataRevision':'fixture-1','query':{'userId':'u1','expressions':[{'name':'Total','expression':'SUM(Sales[Amount])'}],'pageSize':10}}

def test_query_endpoint_returns_versioned_result():
 response=TestClient(app).post('/api/v1/models/m1/query',json=payload());assert response.status_code==200;body=response.json();assert body['version']=='1.0' and body['modelId']=='m1' and body['rows']==[['30']];assert [x['kind'] for x in body['plan']]==['scan','aggregate','project'];assert 'cacheHit' in body['metrics']

def test_query_endpoint_rejects_model_id_mismatch():
 response=TestClient(app).post('/api/v1/models/route/query',json=payload('body'));assert response.status_code==400 and response.json()['detail']['code']=='MODEL_ID_MISMATCH'
