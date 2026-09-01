import json
import pytest
from fakebric.dax import DaxError,parse_dax
@pytest.mark.parametrize("expression",['__import__("os")','PYTHON("open")','Sales.Amount','1; DROP TABLE Sales','http://example.com'])
def test_arbitrary_code_and_non_dax_syntax_are_rejected(expression):
    with pytest.raises(DaxError): parse_dax(expression)
def test_ast_is_plain_json_serializable_data():
    encoded=json.dumps(parse_dax("DIVIDE(Sales[Amount], 2, BLANK())").to_dict(),sort_keys=True); assert '"name": "DIVIDE"' in encoded
