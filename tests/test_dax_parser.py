from dataclasses import FrozenInstanceError
import pytest
from fakebric.dax import DaxError, DaxLimits, FUNCTION_CATALOG, collect_references, parse_dax

def test_arithmetic_precedence_matches_golden_ast():
    ast=parse_dax("1 + 2 * 3"); assert ast.to_dict()["right"]["operator"]=="*"
def test_parentheses_override_precedence_and_ast_is_immutable():
    ast=parse_dax("(1 + 2) * 3"); assert ast.to_dict()["left"]["operator"]=="+"
    with pytest.raises(FrozenInstanceError): ast.operator="+"  # type: ignore[misc]
def test_boolean_expression_and_references():
    ast=parse_dax("Sales[Amount] > 0 && TRUE()"); assert ast.to_dict()["operator"]=="&&"; assert [(x.table,x.name) for x in collect_references(ast)]==[("Sales","Amount")]
def test_quoted_table_reference_and_escaped_string():
    data=parse_dax("IF('Sales Data'[Amount] > 0, \"a\"\"b\", BLANK())").to_dict(); assert data["arguments"][0]["left"]["table"]=="Sales Data"; assert data["arguments"][1]["value"]=='a"b'
def test_number_date_and_blank_literals_are_serializable():
    assert parse_dax("10.50").to_dict()["value"]=="10.50"; assert parse_dax('dt"2026-09-04"').to_dict()["literalType"]=="date"; assert parse_dax('dt"2026-09-04T10:30:00"').to_dict()["literalType"]=="datetime"; assert parse_dax("BLANK()").to_dict()["literalType"]=="blank"
def test_supported_function_catalog_is_published_by_level():
    assert FUNCTION_CATALOG["SUM"].level==1 and FUNCTION_CATALOG["CALCULATE"].level==2 and FUNCTION_CATALOG["DATE"].level==3
def test_unknown_function_is_rejected_deterministically():
    with pytest.raises(DaxError) as error: parse_dax("EVALUATE(Sales[Amount])")
    assert error.value.diagnostic.code=="DAX_UNSUPPORTED_FUNCTION"
def test_invalid_token_and_incomplete_expression_report_position():
    with pytest.raises(DaxError) as invalid: parse_dax("1 +\n @")
    assert (invalid.value.diagnostic.line,invalid.value.diagnostic.column,invalid.value.diagnostic.token)==(2,2,"@")
    with pytest.raises(DaxError) as incomplete: parse_dax("1 +")
    assert incomplete.value.diagnostic.code=="DAX_INCOMPLETE_EXPRESSION"
def test_ambiguous_syntax_and_wrong_arity_are_rejected():
    with pytest.raises(DaxError) as ambiguous: parse_dax("[Amount]")
    assert ambiguous.value.diagnostic.code=="DAX_AMBIGUOUS_REFERENCE"
    with pytest.raises(DaxError) as chained: parse_dax("1 < 2 < 3")
    assert chained.value.diagnostic.code=="DAX_AMBIGUOUS_COMPARISON"
    with pytest.raises(DaxError) as arity: parse_dax("SUM(Sales[Amount], Sales[Amount])")
    assert arity.value.diagnostic.code=="DAX_FUNCTION_ARITY"
def test_length_depth_token_and_complexity_limits():
    with pytest.raises(DaxError) as length: parse_dax("1"*9,DaxLimits(max_length=8))
    assert length.value.diagnostic.code=="DAX_LIMIT_LENGTH"
    with pytest.raises(DaxError) as depth: parse_dax("((((1))))",DaxLimits(max_depth=2))
    assert depth.value.diagnostic.code=="DAX_LIMIT_DEPTH"
    with pytest.raises(DaxError) as tokens: parse_dax("1+2+3",DaxLimits(max_tokens=4))
    assert tokens.value.diagnostic.code=="DAX_LIMIT_TOKENS"
    with pytest.raises(DaxError) as complexity: parse_dax("1+2+3",DaxLimits(max_nodes=4))
    assert complexity.value.diagnostic.code=="DAX_LIMIT_COMPLEXITY"
