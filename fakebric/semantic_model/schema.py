from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fakebric.powerbi.common import VersionedResource


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    BINARY = "binary"


class DataSourceType(str, Enum):
    PARQUET = "parquet"
    CSV = "csv"
    JSONL = "jsonl"
    FAKEBRICK = "fakebrick"


class DataSource(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: DataSourceType
    path: str = Field(min_length=1)
    options: dict[str, Any] = Field(default_factory=dict)
    credential_ref: str | None = Field(default=None, alias="credentialRef")

    @model_validator(mode="after")
    def reject_embedded_credentials(self) -> "DataSource":
        forbidden_markers = (
            "password",
            "token",
            "secret",
            "credential",
            "api_key",
            "access_key",
            "private_key",
        )
        bad_keys = [
            key
            for key in self.options
            if any(marker in key.casefold() for marker in forbidden_markers)
        ]
        if bad_keys:
            raise ValueError(
                "credentials must be referenced with credentialRef, not embedded in options"
            )
        return self


class Column(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(min_length=1)
    type: DataType
    nullable: bool = True
    source_name: str | None = Field(default=None, alias="sourceName")

    @property
    def physical_name(self) -> str:
        return self.source_name or self.name


class Measure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    expression: str = Field(min_length=1)


class Table(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    source: DataSource
    columns: list[Column] = Field(default_factory=list)
    measures: list[Measure] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_names(self) -> "Table":
        column_names = [column.name.casefold() for column in self.columns]
        if len(column_names) != len(set(column_names)):
            raise ValueError(f"duplicate column name in table {self.name!r}")
        measure_names = [measure.name.casefold() for measure in self.measures]
        if len(measure_names) != len(set(measure_names)):
            raise ValueError(f"duplicate measure name in table {self.name!r}")
        if set(column_names).intersection(measure_names):
            raise ValueError(f"column and measure names collide in table {self.name!r}")
        return self

    def column(self, name: str) -> Column:
        normalized = name.casefold()
        for column in self.columns:
            if column.name.casefold() == normalized:
                return column
        raise KeyError(f"column {name!r} does not exist in table {self.name!r}")


class SemanticModel(VersionedResource):
    tables: list[Table] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_table_names(self) -> "SemanticModel":
        names = [table.name.casefold() for table in self.tables]
        if len(names) != len(set(names)):
            raise ValueError("duplicate table name")
        return self

    def table(self, name: str) -> Table:
        normalized = name.casefold()
        for table in self.tables:
            if table.name.casefold() == normalized:
                return table
        raise KeyError(f"table {name!r} does not exist")
