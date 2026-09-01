from __future__ import annotations

import base64
import csv
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

from fakebric.semantic_model.schema import DataSource, DataSourceType, DataType, Table


class SourceError(ValueError):
    pass


class SourceSecurityError(SourceError):
    pass


class MissingColumnError(SourceError):
    pass


class ConversionError(SourceError):
    pass


@dataclass(frozen=True)
class LoadedDataset:
    rows: tuple[dict[str, Any], ...]
    fields: tuple[str, ...]


class ColumnInference(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    suggested_type: DataType = Field(alias="suggestedType")
    nullable: bool
    confidence: float = Field(ge=0.0, le=1.0)


class ColumnStatistics(BaseModel):
    rows: int
    nulls: int
    min: Any = None
    max: Any = None
    cardinality: int


class DatasetStatistics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    row_count: int = Field(alias="rowCount")
    columns: dict[str, ColumnStatistics]


class DatasetProfile(BaseModel):
    inference: list[ColumnInference]
    statistics: DatasetStatistics


def _parse_boolean(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(value)


def convert_value(value: Any, target: DataType) -> Any:
    if value is None or value == "":
        return None
    try:
        if target == DataType.STRING:
            return str(value)
        if target == DataType.INTEGER:
            if isinstance(value, bool):
                raise ValueError(value)
            if isinstance(value, int):
                return value
            text = str(value).strip()
            if any(marker in text.casefold() for marker in (".", "e")):
                raise ValueError(value)
            return int(text)
        if target == DataType.DECIMAL:
            if isinstance(value, bool):
                raise ValueError(value)
            return Decimal(str(value).strip())
        if target == DataType.BOOLEAN:
            if isinstance(value, bool):
                return value
            return _parse_boolean(str(value))
        if target == DataType.DATE:
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return date.fromisoformat(str(value).strip())
        if target == DataType.DATETIME:
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if target == DataType.BINARY:
            if isinstance(value, bytes):
                return value
            return base64.b64decode(str(value), validate=True)
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ConversionError(f"cannot convert {value!r} to {target.value}") from exc
    raise ConversionError(f"unsupported conversion target {target!r}")


def _infer_scalar(value: Any) -> DataType:
    if isinstance(value, bool):
        return DataType.BOOLEAN
    if isinstance(value, int):
        return DataType.INTEGER
    if isinstance(value, (float, Decimal)):
        return DataType.DECIMAL
    if isinstance(value, datetime):
        return DataType.DATETIME
    if isinstance(value, date):
        return DataType.DATE
    if isinstance(value, bytes):
        return DataType.BINARY
    if not isinstance(value, str):
        return DataType.STRING

    text = value.strip()
    if not text:
        return DataType.STRING
    if text.casefold() in {"true", "false", "yes", "no"}:
        return DataType.BOOLEAN
    try:
        int(text)
        return DataType.INTEGER
    except ValueError:
        pass
    try:
        Decimal(text)
        return DataType.DECIMAL
    except InvalidOperation:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if "T" in text or " " in text or parsed.time().isoformat() != "00:00:00":
            return DataType.DATETIME
    except ValueError:
        pass
    try:
        date.fromisoformat(text)
        return DataType.DATE
    except ValueError:
        return DataType.STRING


def _merge_types(types: set[DataType]) -> DataType:
    if not types:
        return DataType.STRING
    if len(types) == 1:
        return next(iter(types))
    if types <= {DataType.INTEGER, DataType.DECIMAL}:
        return DataType.DECIMAL
    if types <= {DataType.DATE, DataType.DATETIME}:
        return DataType.DATETIME
    return DataType.STRING


def infer_schema(dataset: LoadedDataset) -> list[ColumnInference]:
    suggestions: list[ColumnInference] = []
    for field in dataset.fields:
        values = [row.get(field) for row in dataset.rows]
        non_null = [value for value in values if value is not None and value != ""]
        inferred = [_infer_scalar(value) for value in non_null]
        suggested = _merge_types(set(inferred))
        confidence = 0.0 if not inferred else inferred.count(suggested) / len(inferred)
        if suggested == DataType.DECIMAL and set(inferred) <= {DataType.INTEGER, DataType.DECIMAL}:
            confidence = 1.0
        if suggested == DataType.DATETIME and set(inferred) <= {DataType.DATE, DataType.DATETIME}:
            confidence = 1.0
        if suggested == DataType.STRING and len(set(inferred)) > 1:
            confidence = max(inferred.count(kind) for kind in set(inferred)) / len(inferred)
        suggestions.append(
            ColumnInference(
                name=field,
                suggestedType=suggested,
                nullable=len(non_null) != len(values),
                confidence=confidence,
            )
        )
    return suggestions


def _hashable(value: Any) -> Any:
    if isinstance(value, bytearray):
        return bytes(value)
    try:
        hash(value)
        return value
    except TypeError:
        return json.dumps(value, sort_keys=True, default=str)


def dataset_statistics(dataset: LoadedDataset) -> DatasetStatistics:
    column_stats: dict[str, ColumnStatistics] = {}
    for field in dataset.fields:
        values = [row.get(field) for row in dataset.rows]
        non_null = [value for value in values if value is not None]
        try:
            minimum = min(non_null) if non_null else None
            maximum = max(non_null) if non_null else None
        except TypeError:
            minimum = min((str(value) for value in non_null), default=None)
            maximum = max((str(value) for value in non_null), default=None)
        column_stats[field] = ColumnStatistics(
            rows=len(values),
            nulls=len(values) - len(non_null),
            min=minimum,
            max=maximum,
            cardinality=len({_hashable(value) for value in non_null}),
        )
    return DatasetStatistics(rowCount=len(dataset.rows), columns=column_stats)


class SourceLoader:
    def __init__(
        self,
        workspace_root: str | Path,
        fakebrick_tables: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.fakebrick_tables = fakebrick_tables or {}

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        resolved = (candidate if candidate.is_absolute() else self.workspace_root / candidate).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise SourceSecurityError(f"source path escapes workspace: {path!r}") from exc
        return resolved

    def load(self, source: DataSource) -> LoadedDataset:
        if source.type == DataSourceType.FAKEBRICK:
            if source.path not in self.fakebrick_tables:
                raise SourceError(f"Fakebrick table {source.path!r} not found")
            rows = tuple(deepcopy(self.fakebrick_tables[source.path]))
            return LoadedDataset(rows=rows, fields=_ordered_fields(rows))

        path = self._resolve_path(source.path)
        if not path.is_file():
            raise SourceError(f"source file not found: {source.path!r}")
        if source.type == DataSourceType.CSV:
            return self._load_csv(path, source.options)
        if source.type == DataSourceType.JSONL:
            return self._load_jsonl(path)
        if source.type == DataSourceType.PARQUET:
            return self._load_parquet(path)
        raise SourceError(f"unsupported source type: {source.type}")

    def profile(self, source: DataSource) -> DatasetProfile:
        dataset = self.load(source)
        return DatasetProfile(
            inference=infer_schema(dataset),
            statistics=dataset_statistics(dataset),
        )

    def load_table(self, table: Table) -> LoadedDataset:
        dataset = self.load(table.source)
        expected = [column.physical_name for column in table.columns]
        missing = [name for name in expected if name not in dataset.fields]
        if missing:
            raise MissingColumnError(
                f"table {table.name!r} references missing source columns: {', '.join(missing)}"
            )
        converted: list[dict[str, Any]] = []
        for row in dataset.rows:
            output: dict[str, Any] = {}
            for column in table.columns:
                output[column.name] = convert_value(row.get(column.physical_name), column.type)
                if output[column.name] is None and not column.nullable:
                    raise ConversionError(f"column {table.name}.{column.name} is not nullable")
            converted.append(output)
        return LoadedDataset(
            rows=tuple(converted),
            fields=tuple(column.name for column in table.columns),
        )

    @staticmethod
    def _load_csv(path: Path, options: dict[str, Any]) -> LoadedDataset:
        delimiter = str(options.get("delimiter", ","))
        if len(delimiter) != 1:
            raise SourceError("CSV delimiter must be one character")
        with path.open(
            "r",
            encoding=str(options.get("encoding", "utf-8")),
            newline="",
        ) as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            fields = tuple(reader.fieldnames or ())
            rows = tuple(dict(row) for row in reader)
        return LoadedDataset(rows=rows, fields=fields)

    @staticmethod
    def _load_jsonl(path: Path) -> LoadedDataset:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SourceError(f"invalid JSONL at line {line_number}") from exc
                if not isinstance(item, dict):
                    raise SourceError(f"JSONL line {line_number} must contain an object")
                rows.append(item)
        frozen = tuple(rows)
        return LoadedDataset(rows=frozen, fields=_ordered_fields(frozen))

    @staticmethod
    def _load_parquet(path: Path) -> LoadedDataset:
        try:
            import pyarrow.parquet as parquet
        except ImportError as exc:
            raise SourceError("Parquet support requires pyarrow") from exc
        table = parquet.read_table(path)
        return LoadedDataset(
            rows=tuple(table.to_pylist()),
            fields=tuple(table.column_names),
        )


def _ordered_fields(rows: Iterable[dict[str, Any]]) -> tuple[str, ...]:
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for name in row:
            if name not in seen:
                seen.add(name)
                fields.append(name)
    return tuple(fields)
