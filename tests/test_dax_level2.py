from decimal import Decimal
import pytest
from fakebric.dax import DaxEngine,DaxEvaluationError,FilterContext,FilterOrigin,RelationshipBinding

SALES=[{"DateKey":1,"Category":"A","Amount":Decimal("10")},{"DateKey":2,"Category":"B","Amount":Decimal("20")},{"DateKey":2,"Category":"A","Amount":Decimal("30")},{"DateKey":3,"Category":"C","Amount":Decimal("40")}]
DATES=[{"DateKey":1,"Year":2026},{"DateKey":2,"Year":2026},{"DateKey":3,"Year":2027}]
REL=RelationshipBinding("sales-date","Sales","DateKey","Date","DateKey","one-to-many")
def engine():return DaxEngine({"Sales":SALES,"Date":DATES},{"Sales":{"Total":"SUM(Sales[Amount])","Double":"Sales[Total] * 2"}},[REL])

def test_relationship_propagation_and_direct_filter_origin():
 ctx=FilterContext().with_values("Date","Year",[2026],FilterOrigin.REPORT);dax=engine()
 assert dax.evaluate("SUM(Sales[Amount])",filter_context=ctx)==Decimal("60")
 assert dax.evaluate("HASONEVALUE(Sales[Category])",filter_context=FilterContext().with_values("Date","Year",[2027])) is True
 assert dax.evaluate("ISFILTERED(Date[Year])",filter_context=ctx) is True
 assert dax.evaluate("ISFILTERED(Sales[Category])",filter_context=ctx) is False

def test_calculate_replace_and_keepfilters():
 dax=engine();ctx=FilterContext().with_values("Sales","Category",["A"],FilterOrigin.VISUAL)
 assert dax.evaluate('CALCULATE(SUM(Sales[Amount]), Sales[Category] = "B")',filter_context=ctx)==Decimal("20")
 assert dax.evaluate('CALCULATE(SUM(Sales[Amount]), KEEPFILTERS(Sales[Category] = "B"))',filter_context=ctx) is None

def test_filter_values_distinct_and_selectedvalue():
 dax=engine();assert dax.evaluate("COUNTROWS(FILTER(Sales, Sales[Amount] > 20))")==2
 assert dax.evaluate("COUNTROWS(VALUES(Sales[Category]))")==3
 assert dax.evaluate("COUNTROWS(DISTINCT(Sales[Category]))")==3
 assert dax.evaluate('SELECTEDVALUE(Sales[Category], "many")')=="many"
 assert dax.evaluate("SELECTEDVALUE(Sales[Category])",filter_context=FilterContext().with_values("Sales","Category",["B"]))=="B"

def test_removefilters_all_and_allexcept():
 dax=engine();ctx=FilterContext().with_values("Sales","Category",["A"],FilterOrigin.PAGE).with_values("Sales","DateKey",[2],FilterOrigin.VISUAL)
 assert dax.evaluate("SUM(Sales[Amount])",filter_context=ctx)==Decimal("30")
 assert dax.evaluate("CALCULATE(SUM(Sales[Amount]), REMOVEFILTERS(Sales[DateKey]))",filter_context=ctx)==Decimal("40")
 assert dax.evaluate("CALCULATE(SUM(Sales[Amount]), ALL(Sales))",filter_context=ctx)==Decimal("100")
 assert dax.evaluate("CALCULATE(SUM(Sales[Amount]), ALLEXCEPT(Sales, Sales[Category]))",filter_context=ctx)==Decimal("40")

def test_context_transition_and_measure_reference():
 dax=engine();assert dax.evaluate_rows("CALCULATE(SUM(Sales[Amount]))","Sales")==tuple(row["Amount"] for row in SALES)
 assert dax.evaluate_measure("Sales","Double",filter_context=FilterContext().with_values("Sales","Category",["A"]))==Decimal("80")

def test_many_to_many_and_ambiguous_relationship_guard():
 rel=RelationshipBinding("m2m","Left","Key","Right","Key","many-to-many")
 dax=DaxEngine({"Left":[{"Key":"x"},{"Key":"y"}],"Right":[{"Key":"x"},{"Key":"x"},{"Key":"y"}]},relationships=[rel])
 assert dax.evaluate("COUNTROWS(Right)",filter_context=FilterContext().with_values("Left","Key",["x"]))==2
 rels=[RelationshipBinding("ab","A","K","B","K","many-to-many"),RelationshipBinding("bc","B","K","C","K","many-to-many"),RelationshipBinding("ca","C","K","A","K","many-to-many")]
 with pytest.raises(DaxEvaluationError) as exc:DaxEngine({"A":[{"K":1}],"B":[{"K":1}],"C":[{"K":1}]},relationships=rels)
 assert exc.value.code=="DAX_EVAL_AMBIGUOUS_RELATIONSHIP"

def test_explain_plan_is_deterministic():
 p=engine().explain('CALCULATE(SUM(Sales[Amount]), Sales[Category] = "A")',filter_context=FilterContext().with_values("Date","Year",[2026],FilterOrigin.REPORT))
 assert "report -> page -> visual -> user" in p and "relationship propagation" in p and "same-column filters replace unless KEEPFILTERS" in p
