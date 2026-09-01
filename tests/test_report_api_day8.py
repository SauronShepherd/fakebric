from fastapi.testclient import TestClient
import fakebric.reports.api as api
from fakebric.reports.repository import ReportRepository

def setup_function():api.repository=ReportRepository()
def client():return TestClient(api.app)
def base():return {'id':'r1','name':'Report','modelId':'m1'}
def test_crud_etag_and_revision():
 c=client();created=c.post('/api/v1/reports',json=base());assert created.status_code==201;etag=created.headers['etag'];assert c.get('/api/v1/reports').json()[0]['id']=='r1';got=c.get('/api/v1/reports/r1');assert got.headers['etag']==etag;body=got.json();body['name']='Updated';updated=c.put('/api/v1/reports/r1',json=body,headers={'If-Match':etag});assert updated.status_code==200 and updated.json()['revision']==2;assert c.put('/api/v1/reports/r1',json=body,headers={'If-Match':etag}).status_code==409;assert c.delete('/api/v1/reports/r1',headers={'If-Match':updated.headers['etag']}).status_code==204;assert c.get('/api/v1/reports/r1').status_code==404
