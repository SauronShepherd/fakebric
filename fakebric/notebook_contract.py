import ast
import json


_DENIED_CONFIG_PARTS = ('kubernetes', 'container.image', 'master', 'secret', 'password', 'token')


def _validate_config(value) -> None:
    def walk(node, path=''):
        if isinstance(node, dict):
            for key, child in node.items():
                full=f'{path}.{key}'.lower().strip('.')
                if any(part in full for part in _DENIED_CONFIG_PARTS):
                    raise ValueError(f'%%configure property is not allowed: {full}')
                walk(child, full)
        elif isinstance(node, list):
            for child in node: walk(child, path)
    walk(value)


def apply_fakebric_magics(notebook) -> None:
    fakebric = notebook.setdefault("metadata", {}).setdefault("fakebric", {})
    configure = fakebric.setdefault("configure", {})
    sql_cells = fakebric.setdefault("sqlCells", {})
    pip_cells = fakebric.setdefault("pipCells", {})
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        source = cell.source if isinstance(cell.source, str) else "".join(cell.source)
        if source.lstrip().startswith("%%configure"):
            payload = "\n".join(source.splitlines()[1:]).strip()
            if payload:
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    parsed = ast.literal_eval(payload)
                if not isinstance(parsed, dict):
                    raise ValueError("%%configure payload must be an object")
                _validate_config(parsed)
                configure.update(parsed)
            cell.source = "# Fakebric %%configure applied by the runtime\n"
        elif source.lstrip().startswith("%%sql"):
            sql = "\n".join(source.splitlines()[1:]).strip()
            if not sql:
                raise ValueError("%%sql cell must contain a query")
            cell_id = getattr(cell, "id", None) or str(len(sql_cells))
            sql_cells[cell_id] = sql
            # JSON encoding gives a single safely quoted Python string, even
            # when SQL contains quotes, newlines or unicode. The expression
            # keeps Spark's DataFrame as the cell result for notebook renderers.
            cell.source = f"spark.sql({json.dumps(sql, ensure_ascii=False)})\n"
        elif source.lstrip().startswith("%pip"):
            command = " ".join(source.lstrip().splitlines()[0].split()[1:]).strip()
            if not command or not command.startswith("install "):
                raise ValueError("only '%pip install <packages>' is supported")
            args = command[len("install "):].strip().split()
            if not args or any(arg.startswith(('--index-url', '--extra-index-url', '--trusted-host', '-c', '--constraint')) for arg in args):
                raise ValueError("%pip requires packages and does not allow custom indexes or constraint files")
            cell_id = getattr(cell, "id", None) or str(len(pip_cells))
            pip_cells[cell_id] = args
            cell.source = "import subprocess, sys\nsubprocess.check_call([sys.executable, '-m', 'pip', 'install', " + ", ".join(repr(arg) for arg in args) + "])\n"
