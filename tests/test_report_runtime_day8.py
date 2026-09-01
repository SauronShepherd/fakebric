import json
from pathlib import Path
from fakebric.reports.runtime import ReportRuntime
from fakebric.reports.schema import Report,VisualState
FIX=json.loads((Path(__file__).parent/'fixtures'/'report_day8.json').read_text())
def report():return Report.model_validate(FIX)
def test_eight_visual_fixture_renders_ready_and_accessible_markup():
 out=ReportRuntime().render(report(),{'q1':{'columns':[{'name':'Total'}],'rows':[['100']]},'q2':{'columns':[{'name':'Sales.Category'},{'name':'Total'}],'rows':[['A','40'],['B','60']]}});assert len(out.pages[0].visuals)==8;assert all(v.state==VisualState.READY for v in out.pages[0].visuals);v1=next(v for v in out.pages[0].visuals if v.id=='v1');assert 'role="group"' in v1.html and 'aria-label="Total sales"' in v1.html
def test_loading_empty_and_error_states():
 rt=ReportRuntime();r=report();loading=rt.render(r,{'q2':{'rows':[]}},loading_queries={'q1'});assert next(v for v in loading.pages[0].visuals if v.id=='v1').state==VisualState.LOADING;out=rt.render(r,{'q1':{'rows':[]},'q2':{'rows':[]}});assert all(v.state==VisualState.EMPTY for v in out.pages[0].visuals);missing=rt.render(r,{});assert next(v for v in missing.pages[0].visuals if v.id=='v1').state==VisualState.ERROR
