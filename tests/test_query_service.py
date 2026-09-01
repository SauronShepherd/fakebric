from decimal import Decimal
import pytest
from fakebric.query import QueryCancellationToken,QueryCancelled,QueryRequest,QueryService
from fakebric.semantic_model.schema import SemanticModel

SALES=[{'DateKey':1,'Category':'A','Amount':Decimal('10')},{'DateKey':2,'Category':'B','Amount':Decimal('20')},{'DateKey':2,'Category':'A','Amount':Decimal('30')},{'DateKey':3,'Category':'C','Amount':Decimal('40')}]
DATES=[{'DateKey':1,'Year':2026},{'DateKey':2,'Year':2026},{'DateKey':3,'Year':2027}]

def model(revision=1):
 return SemanticModel(id='m1',name='Sales Model',revision=revision,tables=[
  {'name':'Sales','source':{'type':'fakebrick','path':'Sales'},'columns':[{'name':'DateKey','type':'integer'},{'name':'Category','type':'string'},{'name':'Amount','type':'decimal'}],'measures':[{'name':'Total','expression':'SUM(Sales[Amount])'}]},
  {'name':'Date','source':{'type':'fakebrick','path':'Date'},'columns':[{'name':'DateKey','type':'integer','isPrimaryKey':True},{'name':'Year','type':'integer'}]}
 ],relationships=[{'name':'sales-date','fromTable':'Sales','fromColumn':'DateKey','toTable':'Date','toColumn':'DateKey','cardinality':'one-to-many'}])

def request(**updates):
 data={'userId':'alice','expressions':[{'name':'Total','expression':'SUM(Sales[Amount])'}]};data.update(updates);return QueryRequest.model_validate(data)

def test_planner_has_scan_filter_join_aggregate_project():
 service=QueryService();req=request(filters=[{'table':'Date','column':'Year','values':[2026],'origin':'report'}]);plan=service.planner.plan(model(),req);kinds=[x.kind for x in plan.nodes]
 assert kinds.count('scan')==2 and 'filter' in kinds and 'join' in kinds and 'aggregate' in kinds and kinds[-1]=='project' and 'sales-date' in plan.text

def test_relationship_filter_and_versioned_metrics():
 response=QueryService().query(model(),{'Sales':SALES,'Date':DATES},request(filters=[{'table':'Date','column':'Year','values':[2026]}]))
 assert response.version=='1.0' and response.rows==[['60']] and response.columns[0].type=='decimal';assert response.metrics.rows_read==5 and response.metrics.bytes_read>0 and response.metrics.returned_rows==1

def test_stable_pagination_reuses_cached_execution():
 service=QueryService();req1=request(groupBy=[{'table':'Sales','column':'Category'}],page=1,pageSize=1);first=service.query(model(),{'Sales':SALES,'Date':DATES},req1)
 assert first.rows==[['A','40']] and first.pagination.has_more is True and first.metrics.cache_hit is False
 second=service.query(model(),{'Sales':SALES,'Date':DATES},req1.model_copy(update={'page':2}));assert second.rows==[['B','20']] and second.metrics.cache_hit is True

def test_cache_revision_and_user_isolation():
 service=QueryService();tables={'Sales':SALES,'Date':DATES};req=request();assert service.query(model(),tables,req).metrics.cache_hit is False;assert service.query(model(),tables,req).metrics.cache_hit is True;assert service.query(model(2),tables,req).metrics.cache_hit is False;assert service.query(model(),tables,req.model_copy(update={'user_id':'bob'})).metrics.cache_hit is False

def test_row_limit_is_deterministic_and_warned():
 response=QueryService().query(model(),{'Sales':SALES,'Date':DATES},request(groupBy=[{'table':'Sales','column':'Category'}],maxRows=2,pageSize=10));assert response.rows==[['A','40'],['B','20']] and 'QUERY_RESULT_TRUNCATED' in response.warnings

def test_cancel_and_timeout_are_cooperative():
 service=QueryService();tables={'Sales':SALES,'Date':DATES};req=request();token=QueryCancellationToken(1000);token.cancel()
 with pytest.raises(QueryCancelled) as cancelled:service.query(model(),tables,req,token=token)
 assert cancelled.value.code=='QUERY_CANCELLED'
 ticks=iter([0.0,0.01,0.02,0.03]);timed=QueryCancellationToken(1,clock=lambda:next(ticks))
 with pytest.raises(QueryCancelled) as timeout:service.query(model(),tables,req,token=timed)
 assert timeout.value.code=='QUERY_TIMEOUT'
