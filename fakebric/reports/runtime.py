from __future__ import annotations

import html
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .schema import Report, VisualState


class RenderedVisual(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    id: str
    type: str
    title: str
    state: VisualState
    aria_label: str = Field(alias="ariaLabel")
    payload: dict[str, Any]
    html: str
    error: str | None = None


class RenderedPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    order: int
    width: int
    height: int
    visuals: list[RenderedVisual]


class RenderedReport(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    report_id: str = Field(alias="reportId")
    revision: int
    theme: dict[str, Any]
    pages: list[RenderedPage]


class ReportRuntime:
    def render(self, report: Report, query_results: dict[str, Any] | None = None, loading_queries: set[str] | None = None) -> RenderedReport:
        results = query_results or {}
        loading = {item.casefold() for item in (loading_queries or set())}
        pages = []
        for page in sorted(report.pages, key=lambda item: item.order):
            visuals = [self._visual(visual, results, loading) for visual in sorted(page.visuals, key=lambda item: (item.frame.z_index, item.id.casefold()))]
            pages.append(RenderedPage(id=page.id, name=page.name, order=page.order, width=page.width, height=page.height, visuals=visuals))
        return RenderedReport(reportId=report.id, revision=report.revision, theme=report.theme.model_dump(by_alias=True), pages=pages)

    def _visual(self, visual, results, loading):
        query_id = visual.query_id
        state = VisualState.READY
        error = None
        rows = []
        columns = []
        if query_id.casefold() in loading:
            state = VisualState.LOADING
        elif query_id not in results:
            state = VisualState.ERROR
            error = "QUERY_RESULT_MISSING"
        else:
            result = results[query_id]
            if isinstance(result, Exception):
                state = VisualState.ERROR
                error = str(result)
            elif result is None:
                state = VisualState.LOADING
            else:
                if hasattr(result, "rows"):
                    rows = result.rows
                    columns = [getattr(column, "name", str(column)) for column in getattr(result, "columns", [])]
                elif isinstance(result, dict):
                    rows = result.get("rows", [])
                    columns = [column.get("name", str(column)) if isinstance(column, dict) else str(column) for column in result.get("columns", [])]
                if not rows:
                    state = VisualState.EMPTY
        payload = {"columns": columns, "rows": rows, "properties": visual.properties.model_dump(by_alias=True), "format": visual.format.model_dump(by_alias=True), "frame": visual.frame.model_dump(by_alias=True)}
        label = visual.alt_text or visual.title or f"{visual.type} visual {visual.id}"
        safe_json = html.escape(json.dumps(payload, default=str, separators=(",", ":")), quote=True)
        markup = f'<section data-visual-id="{html.escape(visual.id, quote=True)}" data-visual-type="{html.escape(visual.type, quote=True)}" data-state="{state.value}" role="group" aria-label="{html.escape(label, quote=True)}" data-payload="{safe_json}"></section>'
        return RenderedVisual(id=visual.id, type=visual.type, title=visual.title, state=state, ariaLabel=label, payload=payload, html=markup, error=error)
