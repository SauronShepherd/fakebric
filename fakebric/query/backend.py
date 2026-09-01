from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class BackendResult:
    rows: tuple[tuple[Any, ...], ...]
    backend: str
    warnings: tuple[str, ...]


class DuckDbArrowBackend:
    """Materialize safe tabular results through Arrow and in-memory DuckDB.

    No user SQL is accepted or interpolated. Semantic/DAX evaluation happens before
    this adapter; DuckDB only materializes a bounded tabular result.
    """

    def adapt(self, names: Sequence[str], rows: Sequence[Sequence[Any]]) -> BackendResult:
        try:
            import duckdb
            import pyarrow as pa
        except ImportError:
            return BackendResult(tuple(tuple(row) for row in rows), "python", ("DUCKDB_ARROW_UNAVAILABLE",))
        if not rows:
            return BackendResult((), "duckdb-arrow", ())
        try:
            payload = [{name: row[index] for index, name in enumerate(names)} for row in rows]
            table = pa.Table.from_pylist(payload)
            connection = duckdb.connect(database=":memory:")
            try:
                connection.register("query_result", table)
                output = connection.sql("SELECT * FROM query_result").to_arrow_table().to_pylist()
            finally:
                connection.close()
            converted = tuple(tuple(item.get(name) for name in names) for item in output)
            return BackendResult(converted, "duckdb-arrow", ())
        except Exception:
            return BackendResult(tuple(tuple(row) for row in rows), "python", ("DUCKDB_ARROW_FALLBACK",))
