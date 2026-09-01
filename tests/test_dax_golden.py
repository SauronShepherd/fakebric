import json
from pathlib import Path
from fakebric.dax import parse_dax
GOLDEN=Path(__file__).parent/"golden"/"dax"
def test_arithmetic_ast_golden_file(): assert parse_dax("1 + 2 * 3").to_dict()==json.loads((GOLDEN/"arithmetic.json").read_text())
def test_conditional_ast_golden_file(): assert parse_dax('IF(Sales[Amount] > 0, "positive", BLANK())').to_dict()==json.loads((GOLDEN/"conditional.json").read_text())
