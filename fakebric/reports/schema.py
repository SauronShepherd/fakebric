from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fakebric.powerbi.common import VersionedResource


class VisualType(str, Enum):
    CARD = "card"
    TABLE = "table"
    MATRIX = "matrix"
    BAR = "bar"
    COLUMN = "column"
    LINE = "line"
    PIE = "pie"
    DONUT = "donut"
    SCATTER = "scatter"
    SLICER = "slicer"


class VisualState(str, Enum):
    LOADING = "loading"
    EMPTY = "empty"
    ERROR = "error"
    READY = "ready"


class Orientation(str, Enum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


class ReportFilterScope(str, Enum):
    REPORT = "report"
    PAGE = "page"
    VISUAL = "visual"


class Frame(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    z_index: int = Field(default=0, ge=0, alias="zIndex")


class NumberFormat(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    decimals: int = Field(default=2, ge=0, le=8)
    thousands_separator: bool = Field(default=True, alias="thousandsSeparator")
    prefix: str = ""
    suffix: str = ""


class VisualFormat(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    background: str | None = None
    foreground: str | None = None
    show_title: bool = Field(default=True, alias="showTitle")
    number_format: NumberFormat = Field(default_factory=NumberFormat, alias="numberFormat")


class ReportTheme(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str = "Fakebrick"
    palette: list[str] = Field(default_factory=lambda: ["#2563eb", "#16a34a", "#f59e0b", "#dc2626"], min_length=1, max_length=32)
    font_family: str = Field(default="Inter, system-ui, sans-serif", alias="fontFamily")
    background: str = "#ffffff"
    foreground: str = "#111827"
    visual_background: str = Field(default="#ffffff", alias="visualBackground")


class CardProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1)
    label: str | None = None


class TableProperties(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    columns: list[str] = Field(min_length=1)
    show_headers: bool = Field(default=True, alias="showHeaders")


class MatrixProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[str] = Field(min_length=1)
    columns: list[str] = Field(default_factory=list)
    values: list[str] = Field(min_length=1)


class CartesianProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(min_length=1)
    values: list[str] = Field(min_length=1)
    stacked: bool = False


class LineProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(min_length=1)
    values: list[str] = Field(min_length=1)
    markers: bool = False


class PieProperties(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    category: str = Field(min_length=1)
    value: str = Field(min_length=1)
    show_legend: bool = Field(default=True, alias="showLegend")


class ScatterProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: str = Field(min_length=1)
    y: str = Field(min_length=1)
    size: str | None = None
    category: str | None = None


class SlicerProperties(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    field: str = Field(min_length=1)
    multi_select: bool = Field(default=True, alias="multiSelect")
    orientation: Literal["vertical", "horizontal"] = "vertical"


class VisualBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: str = Field(min_length=1)
    title: str = ""
    subtitle: str = ""
    alt_text: str = Field(default="", alias="altText")
    query_id: str = Field(min_length=1, alias="queryId")
    frame: Frame
    format: VisualFormat = Field(default_factory=VisualFormat)


class CardVisual(VisualBase):
    type: Literal["card"] = "card"
    properties: CardProperties


class TableVisual(VisualBase):
    type: Literal["table"] = "table"
    properties: TableProperties


class MatrixVisual(VisualBase):
    type: Literal["matrix"] = "matrix"
    properties: MatrixProperties


class BarVisual(VisualBase):
    type: Literal["bar"] = "bar"
    properties: CartesianProperties


class ColumnVisual(VisualBase):
    type: Literal["column"] = "column"
    properties: CartesianProperties


class LineVisual(VisualBase):
    type: Literal["line"] = "line"
    properties: LineProperties


class PieVisual(VisualBase):
    type: Literal["pie"] = "pie"
    properties: PieProperties


class DonutVisual(VisualBase):
    type: Literal["donut"] = "donut"
    properties: PieProperties


class ScatterVisual(VisualBase):
    type: Literal["scatter"] = "scatter"
    properties: ScatterProperties


class SlicerVisual(VisualBase):
    type: Literal["slicer"] = "slicer"
    properties: SlicerProperties


Visual = Annotated[Union[CardVisual, TableVisual, MatrixVisual, BarVisual, ColumnVisual, LineVisual, PieVisual, DonutVisual, ScatterVisual, SlicerVisual], Field(discriminator="type")]


class ReportQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: str = Field(min_length=1)
    expressions: list[dict[str, Any]] = Field(default_factory=list)
    group_by: list[dict[str, str]] = Field(default_factory=list, alias="groupBy")
    filters: list[dict[str, Any]] = Field(default_factory=list)


class ReportFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: str = Field(min_length=1)
    scope: ReportFilterScope
    table: str = Field(min_length=1)
    column: str = Field(min_length=1)
    values: list[Any] = Field(min_length=1)
    page_id: str | None = Field(default=None, alias="pageId")
    visual_id: str | None = Field(default=None, alias="visualId")

    @model_validator(mode="after")
    def scope_target(self) -> "ReportFilter":
        if self.scope == ReportFilterScope.PAGE and not self.page_id:
            raise ValueError("page filter requires pageId")
        if self.scope == ReportFilterScope.VISUAL and (not self.page_id or not self.visual_id):
            raise ValueError("visual filter requires pageId and visualId")
        return self


class ReportPage(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    order: int = Field(ge=0)
    width: int = Field(default=1280, gt=0, le=7680)
    height: int = Field(default=720, gt=0, le=4320)
    orientation: Orientation = Orientation.LANDSCAPE
    visuals: list[Visual] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_geometry(self) -> "ReportPage":
        ids = [visual.id.casefold() for visual in self.visuals]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate visual id on page {self.id}")
        for visual in self.visuals:
            if visual.frame.x + visual.frame.width > self.width or visual.frame.y + visual.frame.height > self.height:
                raise ValueError(f"visual {visual.id} exceeds page bounds")
        return self


class Report(VersionedResource):
    model_id: str | None = Field(default=None, alias="modelId")
    pages: list[ReportPage] = Field(default_factory=list)
    queries: list[ReportQuery] = Field(default_factory=list)
    filters: list[ReportFilter] = Field(default_factory=list)
    theme: ReportTheme = Field(default_factory=ReportTheme)

    @model_validator(mode="after")
    def validate_report(self) -> "Report":
        page_ids = [page.id.casefold() for page in self.pages]
        orders = [page.order for page in self.pages]
        query_ids = [query.id.casefold() for query in self.queries]
        if len(page_ids) != len(set(page_ids)):
            raise ValueError("duplicate report page id")
        if len(orders) != len(set(orders)):
            raise ValueError("duplicate report page order")
        if len(query_ids) != len(set(query_ids)):
            raise ValueError("duplicate report query id")
        query_set = set(query_ids)
        visual_targets = {(page.id.casefold(), visual.id.casefold()) for page in self.pages for visual in page.visuals}
        for page in self.pages:
            for visual in page.visuals:
                if visual.query_id.casefold() not in query_set:
                    raise ValueError(f"visual {visual.id} references missing query {visual.query_id}")
        for report_filter in self.filters:
            if report_filter.page_id and report_filter.page_id.casefold() not in set(page_ids):
                raise ValueError(f"filter {report_filter.id} references missing page")
            if report_filter.visual_id and (report_filter.page_id.casefold(), report_filter.visual_id.casefold()) not in visual_targets:
                raise ValueError(f"filter {report_filter.id} references missing visual")
        return self
