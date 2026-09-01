from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fakebric.semantic_model.schema import SemanticModel

QUERY_VERSION = "1.0"


class QueryFilterOrigin(str, Enum):
    REPORT = "report"
    PAGE = "page"
    VISUAL = "visual"
    USER = "user"


class QueryColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: str = Field(min_length=1)
    column: str = Field(min_length=1)


class QueryExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    expression: str = Field(min_length=1)


class QueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table: str = Field(min_length=1)
    column: str = Field(min_length=1)
    values: list[Any] = Field(min_length=1)
    origin: QueryFilterOrigin = QueryFilterOrigin.USER


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    version: Literal["1.0"] = QUERY_VERSION
    user_id: str = Field(min_length=1, alias="userId")
    expressions: list[QueryExpression] = Field(default_factory=list)
    group_by: list[QueryColumn] = Field(default_factory=list, alias="groupBy")
    filters: list[QueryFilter] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000, alias="pageSize")
    max_rows: int = Field(default=10000, ge=1, le=100000, alias="maxRows")
    timeout_ms: int = Field(default=2000, ge=1, le=30000, alias="timeoutMs")

    @model_validator(mode="after")
    def validate_outputs(self) -> "QueryRequest":
        if not self.expressions and not self.group_by:
            raise ValueError("query requires at least one expression or groupBy column")
        expr_names = [item.name.casefold() for item in self.expressions]
        if len(expr_names) != len(set(expr_names)):
            raise ValueError("duplicate query expression name")
        groups = [(item.table.casefold(), item.column.casefold()) for item in self.group_by]
        if len(groups) != len(set(groups)):
            raise ValueError("duplicate groupBy column")
        return self


class ModelQueryEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    model: SemanticModel
    tables: dict[str, list[dict[str, Any]]]
    query: QueryRequest
    data_revision: str = Field(default="inline", min_length=1, alias="dataRevision")


class PlanNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["scan", "filter", "join", "aggregate", "project"]
    detail: str


class ResultColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    type: Literal["blank", "boolean", "integer", "decimal", "date", "datetime", "string", "mixed"]


class QueryMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    rows_read: int = Field(ge=0, alias="rowsRead")
    bytes_read: int = Field(ge=0, alias="bytesRead")
    duration_ms: float = Field(ge=0, alias="durationMs")
    planning_ms: float = Field(ge=0, alias="planningMs")
    execution_ms: float = Field(ge=0, alias="executionMs")
    returned_rows: int = Field(ge=0, alias="returnedRows")
    cache_hit: bool = Field(alias="cacheHit")
    backend: str


class QueryPagination(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, alias="pageSize")
    total_rows: int = Field(ge=0, alias="totalRows")
    has_more: bool = Field(alias="hasMore")


class QueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    version: Literal["1.0"] = QUERY_VERSION
    model_id: str = Field(alias="modelId")
    revision: int = Field(ge=1)
    columns: list[ResultColumn]
    rows: list[list[Any]]
    warnings: list[str]
    metrics: QueryMetrics
    pagination: QueryPagination
    plan: list[PlanNode]
    plan_text: str = Field(alias="planText")
