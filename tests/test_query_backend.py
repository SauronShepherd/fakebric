import pytest
from decimal import Decimal
from fakebric.query.backend import DuckDbArrowBackend

def test_real_duckdb_arrow_roundtrip_when_dependencies_are_present():
 pytest.importorskip('duckdb');pytest.importorskip('pyarrow');result=DuckDbArrowBackend().adapt(['x'],[(Decimal('1.25'),),(Decimal('2.50'),)])
 assert result.backend=='duckdb-arrow' and len(result.rows)==2 and result.warnings==()
