import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from fakebric.reports.schema import Report, VisualType
FIX=json.loads((Path(__file__).parent/'fixtures'/'report_day8.json').read_text())

def test_legacy_report_remains_valid():
 r=Report.model_validate({'id':'r1','name':'Executive','modelId':'m1'});assert r.model_id=='m1' and r.pages==[] and r.version=='1.0'

def test_fixture_has_eight_renderable_visual_types():
 r=Report.model_validate(FIX);assert len(r.pages[0].visuals)==8;assert {v.type for v in r.pages[0].visuals}=={'card','table','matrix','bar','column','line','pie','slicer'}

def test_all_ten_visual_property_schemas_validate():
 base={'id':'r','name':'R','queries':[{'id':'q'}]};props={'card':{'value':'x'},'table':{'columns':['x']},'matrix':{'rows':['x'],'values':['y']},'bar':{'category':'x','values':['y']},'column':{'category':'x','values':['y']},'line':{'category':'x','values':['y']},'pie':{'category':'x','value':'y'},'donut':{'category':'x','value':'y'},'scatter':{'x':'x','y':'y'},'slicer':{'field':'x'}}
 for i,(kind,p) in enumerate(props.items()):
  data={**base,'pages':[{'id':'p','name':'P','order':0,'visuals':[{'id':f'v{i}','type':kind,'queryId':'q','frame':{'x':0,'y':0,'width':10,'height':10},'properties':p}]}]};assert Report.model_validate(data).pages[0].visuals[0].type==kind
 assert set(x.value for x in VisualType)==set(props)

def test_invalid_geometry_and_properties_fail():
 bad=json.loads(json.dumps(FIX));bad['pages'][0]['visuals'][0]['frame']['x']=1200;bad['pages'][0]['visuals'][0]['frame']['width']=200
 with pytest.raises(ValidationError,match='exceeds page bounds'):Report.model_validate(bad)
 bad=json.loads(json.dumps(FIX));del bad['pages'][0]['visuals'][0]['properties']['value']
 with pytest.raises(ValidationError):Report.model_validate(bad)

def test_missing_query_and_filter_targets_fail():
 bad=json.loads(json.dumps(FIX));bad['pages'][0]['visuals'][0]['queryId']='missing'
 with pytest.raises(ValidationError,match='missing query'):Report.model_validate(bad)
 bad=json.loads(json.dumps(FIX));bad['filters']=[{'id':'f','scope':'visual','table':'Sales','column':'Category','values':['A'],'pageId':'p1','visualId':'missing'}]
 with pytest.raises(ValidationError,match='missing visual'):Report.model_validate(bad)
