from datetime import date
from decimal import Decimal
import pytest
from fakebric.dax import BLANK,DaxEngine,DaxEvaluationError,FilterContext,TableReference,parse_dax

SALES=[{"Amount":Decimal("10.50"),"Category":"A","Flag":True,"When":date(2026,9,1)},{"Amount":Decimal("20"),"Category":"B","Flag":False,"When":date(2026,9,2)},{"Amount":None,"Category":None,"Flag":None,"When":None}]
def engine(rows=SALES):return DaxEngine({"Sales":rows,"Empty":[]},{"Sales":{"Total":"SUM(Sales[Amount])","SafeHalf":"DIVIDE(SUM(Sales[Amount]),2)"}})

def test_level1_aggregations_and_decimal_regression():
 d=engine();assert d.evaluate("SUM(Sales[Amount])")==Decimal("30.50");assert d.evaluate("AVERAGE(Sales[Amount])")==Decimal("15.25");assert d.evaluate("MIN(Sales[Amount])")==Decimal("10.50");assert d.evaluate("MAX(Sales[Amount])")==Decimal("20");assert d.evaluate("0.1+0.2")==Decimal("0.3")

def test_blank_count_and_empty_regression():
 d=engine();assert d.evaluate("COUNT(Sales[Category])")==2;assert d.evaluate("COUNTA(Sales[Flag])")==2;assert d.evaluate("DISTINCTCOUNT(Sales[Category])")==3
 for e in ["SUM(Empty[Amount])","COUNTROWS(Empty)","DISTINCTCOUNT(Empty[Amount])"]:assert d.evaluate(e) is BLANK
 with pytest.raises(DaxEvaluationError) as x:d.evaluate("COUNT(Sales[Flag])")
 assert x.value.code=="DAX_EVAL_TYPE"

def test_divide_logic_and_row_context_regression():
 d=engine();assert d.evaluate("DIVIDE(5,2)")==Decimal("2.5");assert d.evaluate("DIVIDE(5,0)") is BLANK;assert d.evaluate("IF(TRUE(),1,1/0)")==1;assert d.evaluate("COALESCE(BLANK(),3)")==3
 assert d.evaluate_rows("Sales[Amount]*2","Sales")== (Decimal("21.00"),Decimal("40"),Decimal("0"))

def test_table_reference_filter_context_and_measure_regression():
 d=engine();a=parse_dax("COUNTROWS('Sales')");assert isinstance(a.arguments[0],TableReference);assert d.evaluate(a)==3
 f=FilterContext.for_table("Sales",[1]);assert d.evaluate("SUM(Sales[Amount])",filter_context=f)==Decimal("20");assert d.evaluate_measure("Sales","SafeHalf",filter_context=f)==Decimal("10")

def test_day6_calculate_is_now_executable():
 assert engine().evaluate("CALCULATE(SUM(Sales[Amount]))")==Decimal("30.50")
