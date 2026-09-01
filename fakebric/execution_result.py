import json


def execution_succeeded(output: str | bytes) -> bool:
    """Return True only when the runtime emitted its machine-readable success record."""
    if isinstance(output, bytes):
        output = output.decode('utf-8', errors='replace')
    for line in reversed(output.splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            return record.get('status') == 'completed'
    return False
